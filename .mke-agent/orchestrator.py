#!/usr/bin/env python3
"""Event-driven MKE auditor/orchestrator.

The implementation is deliberately standard-library-only.  The model can recommend
ACCEPT or REMEDIATE, but deterministic repository gates and compare-and-swap state
updates remain authoritative.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CONTROL_BRANCH = "automation/mke-agent-loop"
TASK_REL = Path(".mke-agent/task.json")
POLICY_REL = Path(".mke-agent/policy.json")
QUEUE_REL = Path(".mke-agent/queue.json")
INSTRUCTIONS_REL = Path(".mke-agent/audit_instructions.md")
HISTORY_REL = Path(".mke-agent/history")
PROMPTS_REL = Path(".mke-agent/prompts")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_RE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]+)")


class AuditError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact(value: str) -> str:
    return SECRET_RE.sub("[REDACTED]", value)


def log(message: str) -> None:
    print(f"[{utc_now()}] {redact(message)}", flush=True)


def run(cmd: list[str], cwd: Path, timeout: int = 300, check: bool = True) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=timeout)
    if check and cp.returncode != 0:
        raise AuditError(f"command failed ({cp.returncode}): {cmd[0]}\n{redact((cp.stdout + cp.stderr)[-8000:])}")
    return cp


def git(cwd: Path, *args: str, timeout: int = 300, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd, timeout, check)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_control(control: Path) -> None:
    git(control, "fetch", "origin", CONTROL_BRANCH, timeout=180)
    git(control, "reset", "--hard", f"origin/{CONTROL_BRANCH}", timeout=180)


def event_id(task: dict[str, Any]) -> str:
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    raw = f"{task.get('task_id')}:{task.get('attempt', 1)}:{task.get('status')}:{result.get('commit_sha', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def acquire_lock(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        return fd
    except FileExistsError as exc:
        try:
            pid = int(path.read_text(encoding="ascii"))
            if os.name == "nt":
                active = str(pid) in subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
            else:
                os.kill(pid, 0)
                active = True
        except (ValueError, OSError):
            active = False
        if active:
            raise AuditError(f"auditor already active with PID {pid}") from exc
        path.unlink(missing_ok=True)
        return acquire_lock(path)


def release_lock(path: Path, fd: int) -> None:
    os.close(fd)
    path.unlink(missing_ok=True)


def allowed_path(path: str, prefixes: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix.replace("\\", "/")) for prefix in prefixes)


def deterministic_gates(repo: Path, task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    commit = str(result.get("commit_sha", ""))
    base = str(task.get("base_sha", ""))
    branch = str(task.get("target_branch", ""))
    failures: list[str] = []
    if not SHA_RE.fullmatch(commit) or not SHA_RE.fullmatch(base):
        return {"passed": False, "failures": ["invalid base or candidate SHA"], "changed_files": []}
    git(repo, "fetch", "origin", branch, timeout=300)
    remote = git(repo, "ls-remote", "--heads", "origin", f"refs/heads/{branch}").stdout.split()
    if not remote or remote[0] != commit:
        failures.append("remote target branch head does not equal recorded candidate commit")
    if git(repo, "merge-base", "--is-ancestor", base, commit, check=False).returncode != 0:
        failures.append("candidate is not descended from the declared base SHA")
    changed = [p for p in git(repo, "diff", "--name-only", base, commit, "--").stdout.splitlines() if p]
    prefixes = task.get("allowed_prefixes") if isinstance(task.get("allowed_prefixes"), list) else []
    outside = [p for p in changed if not allowed_path(p, prefixes)]
    if not changed:
        failures.append("candidate contains no changed files")
    if outside:
        failures.append("scope violation: " + ", ".join(outside))
    if policy.get("forbid_frontend_changes_by_default", True) and not any(p.startswith("src/frontend/") for p in prefixes):
        frontend = [p for p in changed if p.startswith("src/frontend/") or p.startswith("ui/")]
        if frontend:
            failures.append("owner-approved frontend freeze violated: " + ", ".join(frontend))
    return {"passed": not failures, "failures": failures, "changed_files": changed,
            "remote_head": remote[0] if remote else None, "base_sha": base, "commit_sha": commit}


try:
    from npm_resolver import resolve_npm as _shared_resolve_npm
except ImportError:
    try:
        from .npm_resolver import resolve_npm as _shared_resolve_npm
    except (ImportError, ValueError):
        _shared_resolve_npm = None


def resolve_npm() -> str:
    """Resolve the absolute path to the npm executable.

    Uses shutil.which, checks Windows npm.cmd / npm.bat as needed,
    resolves to full executable path, and fails closed if not found.
    """
    if _shared_resolve_npm is not None:
        return _shared_resolve_npm(error_cls=AuditError)
    candidates = ["npm.cmd", "npm.bat", "npm.exe", "npm"] if os.name == "nt" else ["npm", "npm.cmd", "npm.bat"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return os.path.abspath(found)
    found = shutil.which("npm")
    if found:
        return os.path.abspath(found)
    raise AuditError("npm is required for independent frontend preparation but was not found on PATH.")


def independent_tests(repo: Path, commit: str, timeout: int) -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix="mke-audit-"))
    worktree = root / "worktree"
    try:
        git(repo, "worktree", "add", "--detach", str(worktree), commit, timeout=300)
        frontend_dir = worktree / "src" / "frontend"
        lockfile = frontend_dir / "package-lock.json"

        frontend_prep: dict[str, Any] = {
            "performed": False,
            "passed": True,
            "error": None,
            "output_tail": "",
        }

        if lockfile.is_file():
            frontend_prep["performed"] = True
            # a) resolve npm
            try:
                npm_bin = resolve_npm()
            except Exception as exc:
                err_msg = f"npm resolution failed: {exc}"
                frontend_prep["passed"] = False
                frontend_prep["error"] = err_msg
                frontend_prep["output_tail"] = redact(str(exc))
                return {
                    "passed": False,
                    "returncode": -1,
                    "classification": "AUDIT_ENVIRONMENT_FAILURE",
                    "error": err_msg,
                    "frontend_preparation": frontend_prep,
                    "pytest_evidence": {
                        "performed": False,
                        "passed": False,
                        "returncode": None,
                        "output_tail": "pytest was not executed because frontend preparation failed",
                    },
                    "frontend_output_tail": frontend_prep["output_tail"],
                    "pytest_output_tail": "",
                    "output_tail": frontend_prep["output_tail"],
                }

            # b) run npm ci
            try:
                ci_res = run([npm_bin, "ci"], cwd=frontend_dir, timeout=timeout, check=False)
                ci_out = redact((ci_res.stdout + "\n" + ci_res.stderr)[-8000:])
            except Exception as exc:
                err_msg = f"npm ci execution error: {exc}"
                frontend_prep["passed"] = False
                frontend_prep["error"] = err_msg
                frontend_prep["output_tail"] = redact(str(exc))
                return {
                    "passed": False,
                    "returncode": -1,
                    "classification": "AUDIT_ENVIRONMENT_FAILURE",
                    "error": err_msg,
                    "frontend_preparation": frontend_prep,
                    "pytest_evidence": {
                        "performed": False,
                        "passed": False,
                        "returncode": None,
                        "output_tail": "pytest was not executed because frontend preparation failed",
                    },
                    "frontend_output_tail": frontend_prep["output_tail"],
                    "pytest_output_tail": "",
                    "output_tail": frontend_prep["output_tail"],
                }

            if ci_res.returncode != 0:
                err_msg = f"npm ci failed ({ci_res.returncode})"
                frontend_prep["passed"] = False
                frontend_prep["error"] = err_msg
                frontend_prep["output_tail"] = ci_out
                return {
                    "passed": False,
                    "returncode": ci_res.returncode,
                    "classification": "AUDIT_ENVIRONMENT_FAILURE",
                    "error": err_msg,
                    "frontend_preparation": frontend_prep,
                    "pytest_evidence": {
                        "performed": False,
                        "passed": False,
                        "returncode": None,
                        "output_tail": "pytest was not executed because frontend preparation failed",
                    },
                    "frontend_output_tail": ci_out,
                    "pytest_output_tail": "",
                    "output_tail": ci_out,
                }

            # c) run npm run build
            try:
                build_res = run([npm_bin, "run", "build"], cwd=frontend_dir, timeout=timeout, check=False)
                combined_tail = redact((ci_res.stdout + "\n" + ci_res.stderr + "\n" + build_res.stdout + "\n" + build_res.stderr)[-8000:])
                frontend_prep["output_tail"] = combined_tail
            except Exception as exc:
                err_msg = f"npm run build execution error: {exc}"
                frontend_prep["passed"] = False
                frontend_prep["error"] = err_msg
                frontend_prep["output_tail"] = redact(str(exc))
                return {
                    "passed": False,
                    "returncode": -1,
                    "classification": "AUDIT_ENVIRONMENT_FAILURE",
                    "error": err_msg,
                    "frontend_preparation": frontend_prep,
                    "pytest_evidence": {
                        "performed": False,
                        "passed": False,
                        "returncode": None,
                        "output_tail": "pytest was not executed because frontend preparation failed",
                    },
                    "frontend_output_tail": frontend_prep["output_tail"],
                    "pytest_output_tail": "",
                    "output_tail": frontend_prep["output_tail"],
                }

            if build_res.returncode != 0:
                err_msg = f"npm run build failed ({build_res.returncode})"
                frontend_prep["passed"] = False
                frontend_prep["error"] = err_msg
                return {
                    "passed": False,
                    "returncode": build_res.returncode,
                    "classification": "AUDIT_ENVIRONMENT_FAILURE",
                    "error": err_msg,
                    "frontend_preparation": frontend_prep,
                    "pytest_evidence": {
                        "performed": False,
                        "passed": False,
                        "returncode": None,
                        "output_tail": "pytest was not executed because frontend preparation failed",
                    },
                    "frontend_output_tail": combined_tail,
                    "pytest_output_tail": "",
                    "output_tail": combined_tail,
                }

            frontend_prep["passed"] = True

        # d) only after successful frontend preparation run product pytest
        cp = run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=worktree, timeout=timeout, check=False)
        passed = (cp.returncode == 0)
        pytest_tail = redact((cp.stdout + "\n" + cp.stderr)[-16000:])
        res = {
            "passed": passed,
            "returncode": cp.returncode,
            "classification": None if passed else "PRODUCT_REGRESSION",
            "frontend_preparation": frontend_prep,
            "pytest_evidence": {
                "performed": True,
                "passed": passed,
                "returncode": cp.returncode,
                "output_tail": pytest_tail,
            },
            "frontend_output_tail": frontend_prep["output_tail"],
            "pytest_output_tail": pytest_tail,
            "output_tail": pytest_tail,
        }
        if not passed:
            res["error"] = f"product pytest regression failed ({cp.returncode})"
        return res
    finally:
        git(repo, "worktree", "remove", "--force", str(worktree), timeout=300, check=False)
        shutil.rmtree(root, ignore_errors=True)


def load_api_key() -> str:
    value = os.environ.get("OPENAI_API_KEY", "").strip()
    if value:
        return value
    secret_path = Path(os.environ.get("MKE_OPENAI_KEY_FILE", str(Path(os.environ.get("LOCALAPPDATA", "")) / "MKE" / "secrets" / "openai_api_key.dpapi")))
    if os.name != "nt" or not secret_path.is_file():
        raise AuditError("OPENAI_API_KEY is unset and the per-user DPAPI secret was not found")
    script = (
        "$s=Get-Content -Raw -LiteralPath $args[0] | ConvertTo-SecureString;"
        "$p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s);"
        "try{[Runtime.InteropServices.Marshal]::PtrToStringBSTR($p)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}"
    )
    cp = subprocess.run(["powershell", "-NoProfile", "-Command", script, str(secret_path)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0 or not cp.stdout.strip():
        raise AuditError("could not decrypt the per-user OpenAI API key")
    return cp.stdout.strip()


DECISION_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["ACCEPT", "REMEDIATE"]},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                           "location": {"type": "string"}, "problem": {"type": "string"},
                           "required_fix": {"type": "string"}},
            "required": ["severity", "location", "problem", "required_fix"]}},
        "trust_boundary_preserved": {"type": "boolean"},
        "frontend_freeze_preserved": {"type": "boolean"},
    },
    "required": ["decision", "summary", "findings", "trust_boundary_preserved", "frontend_freeze_preserved"],
}


def extract_output_text(response: dict[str, Any]) -> str:
    pieces: list[str] = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    pieces.append(str(content.get("text", "")))
    if not pieces:
        raise AuditError("OpenAI response contained no output_text")
    return "".join(pieces)


def call_openai(policy: dict[str, Any], instructions: str, evidence: dict[str, Any], api_key: str) -> tuple[dict[str, Any], str]:
    body = {
        "model": policy.get("audit_model", "gpt-6-astra"),
        "instructions": instructions,
        "input": json.dumps(evidence, ensure_ascii=False),
        "reasoning": {"effort": policy.get("audit_reasoning_effort", "high")},
        "text": {"format": {"type": "json_schema", "name": "mke_audit_decision", "strict": True, "schema": DECISION_SCHEMA}},
        "store": bool(policy.get("audit_store_response", False)),
        "metadata": {"system": "mke-agent-loop", "event_id": str(evidence["event_id"])[:64]},
    }
    data = json.dumps(body).encode("utf-8")
    attempts = int(policy.get("audit_api_attempts", 3))
    base_wait = int(policy.get("audit_retry_base_seconds", 5))
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request("https://api.openai.com/v1/responses", data=data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=int(policy.get("audit_timeout_seconds", 900))) as resp:
                response = json.loads(resp.read().decode("utf-8"))
            decision = json.loads(extract_output_text(response))
            return decision, str(response.get("id", ""))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, AuditError) as exc:
            last = exc
            retryable = not isinstance(exc, urllib.error.HTTPError) or exc.code in {408, 409, 429, 500, 502, 503, 504}
            if attempt == attempts or not retryable:
                break
            time.sleep(min(60, base_wait * (2 ** (attempt - 1))))
    raise AuditError(f"OpenAI audit failed after {attempts} attempt(s): {redact(str(last))}")


def build_evidence(repo: Path, control: Path, task: dict[str, Any], gates: dict[str, Any], tests: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    base, commit = str(task["base_sha"]), str(task["result"]["commit_sha"])
    max_bytes = int(policy.get("audit_max_diff_bytes", 180000))
    diff = git(repo, "diff", "--no-ext-diff", "--unified=40", base, commit, "--").stdout
    encoded = diff.encode("utf-8")
    truncated = len(encoded) > max_bytes
    if truncated:
        diff = encoded[:max_bytes].decode("utf-8", errors="replace")
    return {"event_id": event_id(task), "task": task, "deterministic_gates": gates,
            "independent_tests": tests, "diff": diff, "diff_truncated": truncated,
            "diff_stat": git(repo, "diff", "--stat", base, commit, "--").stdout}


def remediation_prompt(task: dict[str, Any], decision: dict[str, Any], audit_event: str) -> str:
    findings = "\n".join(
        f"- [{f['severity'].upper()}] {f['location']}: {f['problem']} Required: {f['required_fix']}"
        for f in decision.get("findings", [])
    ) or "- Correct the deterministic gate/test failures recorded in the audit history."
    return (
        f"MKE AUTOMATED REMEDIATION\n\nTask: {task['task_id']}\nAudit event: {audit_event}\n\n{findings}\n\n"
        "Preserve the original task contract and allowed paths. CAS outputs remain untrusted candidates; "
        "only MKE verification grants trust. Do not modify frontend, protected/default branches, or files "
        "outside allowed_prefixes. Do not perform git operations.\n"
    )


def next_remediation_branch(branch: str, attempt: int) -> str:
    root = re.sub(r"-r\d+-remediation$", "", branch)
    return f"{root}-r{attempt}-remediation"


def apply_decision(control: Path, expected: dict[str, Any], decision: dict[str, Any], record: dict[str, Any], policy: dict[str, Any]) -> None:
    sync_control(control)
    current = read_json(control / TASK_REL)
    expected_key = (expected.get("task_id"), expected.get("status"), expected.get("attempt", 1),
                    expected.get("state_version", 0), expected.get("result", {}).get("commit_sha"))
    current_key = (current.get("task_id"), current.get("status"), current.get("attempt", 1),
                   current.get("state_version", 0), current.get("result", {}).get("commit_sha"))
    if current_key != expected_key:
        raise AuditError("CAS conflict: control task changed before audit decision could be applied")
    eid = record["event_id"]
    history_path = control / HISTORY_REL / f"{eid}.json"
    if history_path.exists():
        return
    now = utc_now()
    attempt = int(current.get("attempt", 1))
    if decision["decision"] == "ACCEPT":
        queue = read_json(control / QUEUE_REL) if (control / QUEUE_REL).is_file() else {"tasks": []}
        pending = [x for x in queue.get("tasks", []) if isinstance(x, dict) and x.get("status", "PENDING") == "PENDING"]
        if pending:
            template = dict(pending[0])
            pending[0]["status"] = "QUEUED"
            pending[0]["queued_at"] = now
            template.pop("status", None)
            template["schema_version"] = "2.0"
            template["state_version"] = int(current.get("state_version", 0)) + 1
            template["status"] = "READY"
            template["attempt"] = 1
            if template.get("base_sha") == "$ACCEPTED_COMMIT":
                template["base_sha"] = current["result"]["commit_sha"]
            template["updated_at"] = now
            write_json(control / QUEUE_REL, queue)
            current = template
        else:
            current["status"] = "ACCEPTED"
            current["accepted_at"] = now
            current["audit_event_id"] = eid
            current["state_version"] = int(current.get("state_version", 0)) + 1
            current["updated_at"] = now
    elif decision["decision"] in {"BLOCKED", "AUDIT_ENVIRONMENT_FAILURE", "INFRASTRUCTURE_FAILURE"}:
        current["status"] = "BLOCKED"
        current["audit_event_id"] = eid
        current["state_version"] = int(current.get("state_version", 0)) + 1
        current["updated_at"] = now
        if "summary" in decision:
            current["blocked_reason"] = decision["summary"]
    else:
        max_attempts = int(policy.get("max_attempts_before_owner", 3))
        if attempt >= max_attempts:
            current["status"] = "OWNER_REQUIRED"
            current["owner_reason"] = f"Remediation limit reached after {attempt} attempts"
            current["audit_event_id"] = eid
            current["state_version"] = int(current.get("state_version", 0)) + 1
            current["updated_at"] = now
        else:
            new_attempt = attempt + 1
            prompt_rel = PROMPTS_REL / f"{current['task_id']}_R{new_attempt}.md"
            (control / prompt_rel).parent.mkdir(parents=True, exist_ok=True)
            (control / prompt_rel).write_text(remediation_prompt(current, decision, eid), encoding="utf-8")
            current["status"] = "READY"
            current["attempt"] = new_attempt
            candidate = current.get("result", {}).get("commit_sha")
            if candidate:
                current["base_sha"] = candidate
            current["target_branch"] = next_remediation_branch(str(current["target_branch"]), new_attempt - 1)
            current["prompt_path"] = str(prompt_rel).replace("\\", "/")
            current["commit_message"] = f"fix({current['task_id'].lower()}): audit remediation attempt {new_attempt}"
            current["previous_audit_event_id"] = eid
            current.pop("result", None)
            current.pop("started_at", None)
            current["state_version"] = int(current.get("state_version", 0)) + 1
            current["updated_at"] = now
    record["applied_at"] = now
    write_json(history_path, record)
    write_json(control / TASK_REL, current)
    git(control, "add", str(TASK_REL).replace("\\", "/"), str(QUEUE_REL).replace("\\", "/"),
        str(HISTORY_REL).replace("\\", "/"), str(PROMPTS_REL).replace("\\", "/"))
    git(control, "config", "user.name", "MKE OpenAI Auditor")
    git(control, "config", "user.email", "mke-openai-auditor@local.invalid")
    git(control, "commit", "-m", f"chore(audit): {decision['decision'].lower()} {expected['task_id']} attempt {attempt}")
    pushed = git(control, "push", "origin", f"HEAD:refs/heads/{CONTROL_BRANCH}", timeout=300, check=False)
    if pushed.returncode != 0:
        raise AuditError("control push lost a race; event remains safe to retry")


def process_event(repo: Path, control: Path) -> bool:
    sync_control(control)
    policy = read_json(control / POLICY_REL)
    task = read_json(control / TASK_REL)
    if task.get("status") not in {"READY_FOR_AUDIT", "BLOCKED"}:
        return False
    eid = event_id(task)
    if (control / HISTORY_REL / f"{eid}.json").exists():
        return False
    cache_path = control / ".mke-agent" / "runtime" / "audit-decisions" / f"{eid}.json"
    if cache_path.is_file():
        cached = read_json(cache_path)
        apply_decision(control, task, cached["decision"], cached, policy)
        return True
    if task["status"] == "BLOCKED":
        result = task.get("result", {})
        stage = str(result.get("stage", "runner"))
        error = str(result.get("error", "runner failure"))
        is_infra = (
            stage in {"frontend-baseline-build", "claim", "fetch-base", "create-worktree", "runner-recovery", "setup-worktree", "prepare-frontend"}
            or any(term in error.lower() for term in ["npm is required", "winerror", "cannot find the file", "tooling", "not found on path"])
        )
        if is_infra:
            decision = {
                "decision": "BLOCKED",
                "summary": f"Infrastructure failure at {stage}: {error}"[-4000:],
                "findings": [{"severity": "high", "location": stage,
                              "problem": error[-4000:],
                              "required_fix": "Resolve tooling or infrastructure failure before restarting runner."}],
                "trust_boundary_preserved": True,
                "frontend_freeze_preserved": True,
            }
            record = {"schema_version": "1.0", "event_id": eid, "created_at": utc_now(), "task_snapshot": task,
                      "decision": decision, "source": "infrastructure-failure",
                      "classification": "INFRASTRUCTURE_FAILURE"}
        else:
            decision = {"decision": "REMEDIATE", "summary": "Runner failed before a candidate could pass gates.",
                        "findings": [{"severity": "high", "location": stage,
                                      "problem": error[-4000:],
                                      "required_fix": "Retry within the original task scope after correcting the reported failure."}],
                        "trust_boundary_preserved": True, "frontend_freeze_preserved": True}
            record = {"schema_version": "1.0", "event_id": eid, "created_at": utc_now(), "task_snapshot": task,
                      "decision": decision, "source": "deterministic-runner-failure"}
        write_json(cache_path, record)
        apply_decision(control, task, decision, record, policy)
        return True
    gates = deterministic_gates(repo, task, policy)
    tests = {"passed": True, "skipped": True}
    if gates["passed"] and policy.get("audit_run_independent_tests", True):
        tests = independent_tests(repo, task["result"]["commit_sha"], int(policy.get("test_timeout_seconds", 2400)))

    if tests.get("classification") == "AUDIT_ENVIRONMENT_FAILURE":
        decision = {
            "decision": "BLOCKED",
            "summary": f"Audit environment failure: {tests.get('error', 'frontend preparation failed')}",
            "findings": [{
                "severity": "high",
                "location": "audit-environment",
                "problem": str(tests.get("error", "frontend preparation failed"))[-4000:],
                "required_fix": "Resolve audit environment / npm tooling before retrying independent audit.",
            }],
            "trust_boundary_preserved": True,
            "frontend_freeze_preserved": True,
        }
        record = {
            "schema_version": "1.0",
            "event_id": eid,
            "created_at": utc_now(),
            "task_snapshot": task,
            "deterministic_gates": gates,
            "independent_tests": tests,
            "decision": decision,
            "source": "audit-environment-failure",
            "classification": "AUDIT_ENVIRONMENT_FAILURE",
        }
        write_json(cache_path, record)
        apply_decision(control, task, decision, record, policy)
        return True

    if not gates["passed"] or not tests.get("passed", False):
        failures = list(gates.get("failures", []))
        if not tests.get("passed", False):
            failures.append("independent full regression failed")
        decision = {"decision": "REMEDIATE", "summary": "; ".join(failures),
                    "findings": [{"severity": "high", "location": "deterministic-gates", "problem": item,
                                  "required_fix": "Correct the failure without broadening the original allowed scope."} for item in failures],
                    "trust_boundary_preserved": not any("trust" in x.lower() for x in failures),
                    "frontend_freeze_preserved": not any("frontend" in x.lower() for x in failures)}
        response_id = ""
        source = "deterministic-gates"
    else:
        evidence = build_evidence(repo, control, task, gates, tests, policy)
        decision, response_id = call_openai(policy, (control / INSTRUCTIONS_REL).read_text(encoding="utf-8"), evidence, load_api_key())
        if not decision.get("trust_boundary_preserved") or not decision.get("frontend_freeze_preserved"):
            decision["decision"] = "REMEDIATE"
        source = "openai-responses-api"
    record = {"schema_version": "1.0", "event_id": eid, "created_at": utc_now(), "task_snapshot": task,
              "deterministic_gates": gates, "independent_tests": tests, "decision": decision,
              "source": source, "openai_response_id": response_id}
    write_json(cache_path, record)
    apply_decision(control, task, decision, record, policy)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="MKE event-driven OpenAI auditor/orchestrator")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    repo, control = Path(args.repo).resolve(), Path(args.control).resolve()
    lock = control / ".mke-agent" / "runtime" / "auditor.lock"
    fd = acquire_lock(lock)
    try:
        changed = process_event(repo, control)
        log("audit event processed" if changed else "no auditable event")
        return 0
    finally:
        release_lock(lock, fd)


if __name__ == "__main__":
    raise SystemExit(main())
