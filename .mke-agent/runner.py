#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

CONTROL_BRANCH = "automation/mke-agent-loop"
TASK_REL = Path(".mke-agent/task.json")
POLICY_REL = Path(".mke-agent/policy.json")
TASK_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,120}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{3,180}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LOG_PATH: Path | None = None


class RunnerError(RuntimeError):
    pass


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def log(message: str) -> None:
    line = f"[{utc_now()}] {message}"
    print(line, flush=True)
    if LOG_PATH is not None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def run(cmd: list[str], *, cwd: Path, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("RUN " + " ".join(cmd[:4]) + (" ..." if len(cmd) > 4 else ""))
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"Command timed out after {timeout}s: {cmd[0]}") from exc
    if check and cp.returncode != 0:
        output_tail = (cp.stdout + "\n" + cp.stderr)[-8000:]
        raise RunnerError(f"Command failed ({cp.returncode}): {cmd[0]}\n{output_tail}")
    return cp


def git(cwd: Path, *args: str, timeout: int = 300, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd, timeout=timeout, check=check)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tail(text: str, size: int = 12000) -> str:
    return text[-size:] if text else ""


def find_agy() -> str:
    found = shutil.which("agy")
    if found:
        return found
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
    if local.is_file():
        return str(local)
    raise RunnerError("Antigravity CLI 'agy' not found. Run the one-time installer.")


def sync_control(control: Path) -> None:
    git(control, "fetch", "origin", CONTROL_BRANCH, timeout=180)
    git(control, "reset", "--hard", f"origin/{CONTROL_BRANCH}", timeout=180)


def validate_task(task: dict, control: Path) -> None:
    required = {"task_id", "status", "base_sha", "target_branch", "prompt_path", "commit_message", "allowed_prefixes"}
    missing = sorted(required - set(task))
    if missing:
        raise RunnerError(f"Task missing fields: {missing}")
    if not TASK_ID_RE.fullmatch(str(task["task_id"])):
        raise RunnerError("Invalid task_id")
    if task["status"] != "READY":
        raise RunnerError("Task is not READY")
    if not SHA_RE.fullmatch(str(task["base_sha"])):
        raise RunnerError("base_sha must be a full lowercase 40-hex SHA")
    if not BRANCH_RE.fullmatch(str(task["target_branch"])):
        raise RunnerError("Invalid target_branch")
    if task["target_branch"] in {"main", "master", "dev02a-method-knowledge-base"}:
        raise RunnerError("Refusing protected/default branch target")
    prompt_path = (control / str(task["prompt_path"])).resolve()
    try:
        prompt_path.relative_to(control.resolve())
    except ValueError as exc:
        raise RunnerError("prompt_path escapes control worktree") from exc
    if not prompt_path.is_file():
        raise RunnerError(f"Prompt file not found: {prompt_path}")
    prefixes = task["allowed_prefixes"]
    if not isinstance(prefixes, list) or not prefixes or not all(isinstance(x, str) and x for x in prefixes):
        raise RunnerError("allowed_prefixes must be a non-empty string list")


def update_control_state(control: Path, task_id: str, status: str, result: dict) -> None:
    sync_control(control)
    task_path = control / TASK_REL
    current = read_json(task_path)
    if current.get("task_id") != task_id:
        raise RunnerError("Control task changed while worker was running; refusing overwrite")
    if current.get("status") not in {"READY", "RUNNING", "BLOCKED"}:
        raise RunnerError(f"Unexpected control status while finalizing: {current.get('status')}")
    current["status"] = status
    current["result"] = result
    current["updated_at"] = utc_now()
    write_json(task_path, current)
    git(control, "add", str(TASK_REL).replace("\\", "/"))
    staged = git(control, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return
    git(control, "config", "user.name", "MKE Agent Runner")
    git(control, "config", "user.email", "mke-agent-runner@local.invalid")
    git(control, "commit", "-m", f"chore(agent): {status.lower()} {task_id}", timeout=180)
    git(control, "push", "origin", f"HEAD:refs/heads/{CONTROL_BRANCH}", timeout=300)


def mark_running(control: Path, task: dict) -> None:
    sync_control(control)
    task_path = control / TASK_REL
    current = read_json(task_path)
    if current.get("task_id") != task["task_id"] or current.get("status") != "READY":
        raise RunnerError("Task no longer READY after sync")
    current["status"] = "RUNNING"
    current["started_at"] = utc_now()
    write_json(task_path, current)
    git(control, "add", str(TASK_REL).replace("\\", "/"))
    git(control, "config", "user.name", "MKE Agent Runner")
    git(control, "config", "user.email", "mke-agent-runner@local.invalid")
    git(control, "commit", "-m", f"chore(agent): start {task['task_id']}")
    git(control, "push", "origin", f"HEAD:refs/heads/{CONTROL_BRANCH}", timeout=300)


def all_changed_paths(worktree: Path, base_sha: str) -> list[str]:
    tracked = git(worktree, "diff", "--name-only", base_sha, "--", timeout=180).stdout.splitlines()
    untracked = git(worktree, "ls-files", "--others", "--exclude-standard", timeout=180).stdout.splitlines()
    return sorted({p.strip().replace("\\", "/") for p in [*tracked, *untracked] if p.strip()})


def enforce_scope(paths: Iterable[str], allowed_prefixes: list[str]) -> None:
    normalized = [p.replace("\\", "/") for p in allowed_prefixes]
    bad = [path for path in paths if not any(path.startswith(prefix) for prefix in normalized)]
    if bad:
        raise RunnerError("Scope violation. Files outside allowed prefixes: " + ", ".join(bad))


def ensure_frontend_dist(worktree: Path, timeout: int) -> str:
    frontend = worktree / "src" / "frontend"
    lockfile = frontend / "package-lock.json"
    if not lockfile.is_file():
        return "frontend package-lock absent; no build performed"
    if shutil.which("npm") is None:
        raise RunnerError("npm is required for full regression but was not found")
    install = run(["npm", "ci"], cwd=frontend, timeout=timeout)
    build = run(["npm", "run", "build"], cwd=frontend, timeout=timeout)
    return tail(install.stdout + "\n" + install.stderr + "\n" + build.stdout + "\n" + build.stderr)


def run_full_tests(worktree: Path, timeout: int) -> str:
    cp = run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=worktree, timeout=timeout)
    return tail(cp.stdout + "\n" + cp.stderr)


def remote_branch_exists(repo: Path, branch: str) -> bool:
    cp = git(repo, "ls-remote", "--heads", "origin", f"refs/heads/{branch}", check=False)
    return bool(cp.stdout.strip())


def local_branch_exists(repo: Path, branch: str) -> bool:
    cp = git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    return cp.returncode == 0


def process_task(repo: Path, control: Path, worktree_root: Path) -> None:
    policy = read_json(control / POLICY_REL)
    task = read_json(control / TASK_REL)
    if task.get("status") != "READY":
        return
    validate_task(task, control)
    task_id = task["task_id"]
    stage = "claim"
    worktree = worktree_root / task_id
    result: dict = {"task_id": task_id, "attempt": task.get("attempt", 1), "started_at": utc_now()}
    try:
        mark_running(control, task)

        stage = "fetch-base"
        git(repo, "fetch", "--all", "--prune", timeout=300)
        base_sha = task["base_sha"]
        git(repo, "cat-file", "-e", f"{base_sha}^{{commit}}", timeout=60)

        target_branch = task["target_branch"]
        if remote_branch_exists(repo, target_branch):
            raise RunnerError(f"Remote target branch already exists: {target_branch}")
        if local_branch_exists(repo, target_branch):
            raise RunnerError(f"Local target branch already exists: {target_branch}")
        if worktree.exists():
            raise RunnerError(f"Task worktree already exists: {worktree}")

        stage = "create-worktree"
        worktree_root.mkdir(parents=True, exist_ok=True)
        git(repo, "worktree", "add", "-b", target_branch, str(worktree), base_sha, timeout=300)

        stage = "frontend-baseline-build"
        result["baseline_frontend_build_tail"] = ensure_frontend_dist(worktree, int(policy["test_timeout_seconds"]))

        stage = "baseline-regression"
        result["baseline_test_tail"] = run_full_tests(worktree, int(policy["test_timeout_seconds"]))

        stage = "run-antigravity"
        agy = find_agy()
        prompt_file = (control / task["prompt_path"]).resolve()
        prompt = prompt_file.read_text(encoding="utf-8")
        wrapper = (
            "AUTOMATED RUNNER POLICY:\n"
            "- Edit only files needed by the task and inside the allowed scope.\n"
            "- Do not perform git commit/push/checkout/reset/rebase.\n"
            "- Do not alter the frontend unless the task explicitly allows it.\n"
            "- The runner performs regression tests, scope validation, commit and push.\n"
            "- Do not use --dangerously-skip-permissions or attempt to change global permissions.\n\n"
        )
        agent = run(
            [agy, "-p", wrapper + prompt, "--output-format", "json"],
            cwd=worktree,
            timeout=int(policy["agent_timeout_seconds"]),
        )
        result["agent_stdout_tail"] = tail(agent.stdout)
        result["agent_stderr_tail"] = tail(agent.stderr)

        stage = "scope-validation"
        paths = all_changed_paths(worktree, base_sha)
        if not paths:
            raise RunnerError("Antigravity completed without producing source/test changes")
        enforce_scope(paths, list(task["allowed_prefixes"]))
        result["changed_files"] = paths

        stage = "final-regression"
        result["final_test_tail"] = run_full_tests(worktree, int(policy["test_timeout_seconds"]))

        stage = "commit"
        git(worktree, "config", "user.name", "MKE Antigravity Runner")
        git(worktree, "config", "user.email", "mke-antigravity-runner@local.invalid")
        git(worktree, "add", "-A")
        staged = git(worktree, "diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            raise RunnerError("No staged changes after successful agent run")
        git(worktree, "commit", "-m", task["commit_message"], timeout=180)
        commit_sha = git(worktree, "rev-parse", "HEAD").stdout.strip()

        stage = "push"
        git(worktree, "push", "--set-upstream", "origin", target_branch, timeout=300)

        result.update({
            "status": "PASS",
            "finished_at": utc_now(),
            "target_branch": target_branch,
            "commit_sha": commit_sha,
            "stage": "complete",
        })
        update_control_state(control, task_id, "READY_FOR_AUDIT", result)
        log(f"Task {task_id} completed: {commit_sha}")

        git(repo, "worktree", "remove", "--force", str(worktree), timeout=300, check=False)

    except Exception as exc:
        result.update({
            "status": "BLOCKED",
            "finished_at": utc_now(),
            "stage": stage,
            "error": str(exc)[-12000:],
            "worktree_path": str(worktree),
        })
        log(f"Task {task_id} BLOCKED at {stage}: {exc}")
        try:
            update_control_state(control, task_id, "BLOCKED", result)
        except Exception as state_exc:
            log(f"Could not publish BLOCKED state: {state_exc}")


def daemon(repo: Path, control: Path, once: bool) -> int:
    global LOG_PATH
    LOG_PATH = control / ".mke-agent" / "logs" / "runner.log"
    policy = read_json(control / POLICY_REL)
    poll = int(policy.get("poll_seconds", 60))
    worktree_root = repo.parent / "mke_agent_worktrees"
    log(f"MKE runner started. repo={repo} control={control}")
    while True:
        try:
            sync_control(control)
            task = read_json(control / TASK_REL)
            if task.get("status") == "READY":
                process_task(repo, control, worktree_root)
        except Exception as exc:
            log(f"Runner loop error: {exc}")
        if once:
            return 0
        time.sleep(max(15, poll))


def main() -> int:
    parser = argparse.ArgumentParser(description="MKE GitHub/Antigravity automation runner")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    control = Path(args.control).expanduser().resolve()
    cp = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-dir"], capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(f"Not a git repository: {repo}")
    if not (control / TASK_REL).is_file():
        raise SystemExit(f"Control worktree missing task file: {control}")
    if not (control / POLICY_REL).is_file():
        raise SystemExit(f"Control worktree missing policy file: {control}")
    return daemon(repo, control, once=args.once or not args.daemon)


if __name__ == "__main__":
    raise SystemExit(main())
