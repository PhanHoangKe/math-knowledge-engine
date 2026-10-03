"""Task execution engine for MKE Antigravity Bridge."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

if __package__ or "." in __name__:
    from .models import (
        BridgeTaskRecord,
        BridgeTaskRequest,
        TaskStatus,
        utc_now_iso,
        SUPPORTED_VALIDATION_PROFILES,
        VALIDATION_PROFILE_AUTO,
        VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND,
    )
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from bridge.models import (
        BridgeTaskRecord,
        BridgeTaskRequest,
        TaskStatus,
        utc_now_iso,
        SUPPORTED_VALIDATION_PROFILES,
        VALIDATION_PROFILE_AUTO,
        VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND,
    )



def _atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomically writes JSON data to file_path using a temporary file in the same directory."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.parent / f".tmp_{file_path.name}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        for attempt in range(5):
            try:
                os.replace(temp_path, file_path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{3,180}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class WorkerError(RuntimeError):
    pass


def find_agy() -> str:
    found = shutil.which("agy")
    if found:
        return found
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
    if local.is_file():
        return str(local)
    raise WorkerError("Antigravity CLI 'agy' not found.")


def run_cmd(cmd: list[str], cwd: Path, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
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
    if check and cp.returncode != 0:
        tail = (cp.stdout + "\n" + cp.stderr)[-8000:]
        raise WorkerError(f"Command failed ({cp.returncode}): {cmd[0]}\n{tail}")
    return cp


def git(cwd: Path, *args: str, timeout: int = 300, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run_cmd(["git", *args], cwd=cwd, timeout=timeout, check=check)


def allowed_path(path: str, prefixes: List[str]) -> bool:
    norm = path.replace("\\", "/")
    return any(norm.startswith(p.replace("\\", "/")) for p in prefixes)


def check_frozen_frontend_allowed_prefixes(allowed_prefixes: List[str]) -> None:
    """Fails closed if allowed_prefixes contains frontend or ui paths."""
    for prefix in allowed_prefixes:
        norm = prefix.replace("\\", "/").strip()
        if (
            norm == "src/frontend"
            or norm.startswith("src/frontend/")
            or "src/frontend/" in norm
            or norm == "ui"
            or norm.startswith("ui/")
            or "ui/" in norm
        ):
            raise WorkerError(
                f"backend_frozen_frontend validation profile rejects frontend/ui prefix in allowed_prefixes: {prefix}"
            )



try:
    from npm_resolver import resolve_npm as _shared_resolve_npm
except ImportError:
    try:
        from ..npm_resolver import resolve_npm as _shared_resolve_npm
    except (ImportError, ValueError):
        _shared_resolve_npm = None


def resolve_npm() -> str:
    """Resolve the absolute path to the npm executable.

    Uses shutil.which, checks Windows npm.cmd / npm.bat as needed,
    resolves to full executable path, and fails closed if not found.
    """
    if _shared_resolve_npm is not None:
        return _shared_resolve_npm(error_cls=WorkerError)
    candidates = ["npm.cmd", "npm.bat", "npm.exe", "npm"] if os.name == "nt" else ["npm", "npm.cmd", "npm.bat"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return os.path.abspath(found)
    found = shutil.which("npm")
    if found:
        return os.path.abspath(found)
    raise WorkerError("npm is required for frontend build but was not found on PATH.")


find_npm = resolve_npm


def prepare_frontend(worktree_path: Path, timeout: int = 600) -> str:
    """Prepares frontend build artifacts if package-lock.json is present.

    Fails closed if package-lock is present but npm is missing or commands fail.
    Returns diagnostic output tail.
    """
    frontend_dir = worktree_path / "src" / "frontend"
    lockfile = frontend_dir / "package-lock.json"
    if not lockfile.is_file():
        return "frontend package-lock absent; skipping frontend build preparation"

    npm_bin = resolve_npm()
    ci_res = run_cmd([npm_bin, "ci"], cwd=frontend_dir, timeout=timeout, check=True)
    build_res = run_cmd([npm_bin, "run", "build"], cwd=frontend_dir, timeout=timeout, check=True)
    combined = (ci_res.stdout + "\n" + ci_res.stderr + "\n" + build_res.stdout + "\n" + build_res.stderr).strip()
    return combined[-8000:]


def collect_changed_files(worktree_path: Path, base_sha: str) -> List[str]:
    """Collects changed git-tracked and untracked (non-ignored) source files."""
    changed = git(worktree_path, "diff", "--name-only", base_sha, check=True).stdout.splitlines()
    untracked = git(worktree_path, "ls-files", "--others", "--exclude-standard", check=True).stdout.splitlines()
    return sorted(set(p.strip().replace("\\", "/") for p in changed + untracked if p.strip()))


def is_control_plane_only(changed_files: List[str]) -> bool:
    """True when a task changes only automation/control-plane files."""
    return bool(changed_files) and all(
        path.replace("\\", "/").startswith(".mke-agent/")
        for path in changed_files
    )


def validate_scope(all_changed: List[str], allowed_prefixes: List[str]) -> None:
    """Validates that modified files are within allowed prefixes and respect frontend freeze."""
    if not all_changed:
        raise WorkerError("Antigravity completed without modifying or creating any files.")

    for path in all_changed:
        norm = path.replace("\\", "/")
        if norm.startswith("src/frontend/") or norm.startswith("ui/"):
            raise WorkerError(f"Frontend freeze violation: {path} cannot be modified.")
        if not allowed_path(norm, allowed_prefixes):
            raise WorkerError(f"Scope violation: {path} is not in allowed_prefixes.")


def cleanup_test_side_effects(worktree_path: Path, base_sha: str, allowed_prefixes: List[str]) -> List[str]:
    """Remove only out-of-scope filesystem changes introduced after pre-test scope validation.

    Before regression tests run, validate_scope() has already established that all task-authored
    changes are inside allowed_prefixes. Therefore any newly observed out-of-scope changes after
    tests are test-harness side effects, not authorized task output. Revert tracked paths to the
    baseline and delete untracked paths, then return the remaining changed-file set.
    """
    changed = collect_changed_files(worktree_path, base_sha)
    for rel in changed:
        norm = rel.replace("\\", "/")
        if allowed_path(norm, allowed_prefixes):
            continue

        tracked = git(
            worktree_path, "ls-files", "--error-unmatch", "--", norm,
            check=False,
        ).returncode == 0

        if tracked:
            git(worktree_path, "restore", "--source", base_sha, "--", norm, check=True)
            continue

        target = (worktree_path / Path(norm)).resolve()
        try:
            target.relative_to(worktree_path.resolve())
        except ValueError as exc:
            raise WorkerError(f"Unsafe test side-effect path outside worktree: {norm}") from exc

        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()

    remaining = collect_changed_files(worktree_path, base_sha)
    validate_scope(remaining, allowed_prefixes)
    return remaining


class TaskWorker:
    """Manages background task queue and worker execution."""

    def __init__(
        self,
        repo_path: Path,
        worktree_root: Path,
        state_dir: Optional[Path] = None,
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.worktree_root = worktree_root.resolve()
        if state_dir is None:
            self.state_dir = (self.repo_path / ".mke-agent" / "runtime" / "bridge-state").resolve()
        else:
            self.state_dir = Path(state_dir).resolve()
        self.tasks: Dict[str, BridgeTaskRecord] = {}
        self.corrupt_records: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._active_thread: Optional[threading.Thread] = None
        self._cancel_flags: Dict[str, bool] = {}
        self._recover_state()

    def _task_file_path(self, task_id: str) -> Path:
        safe_name = urllib.parse.quote(task_id, safe=".-_") + ".json"
        return self.state_dir / safe_name

    def _persist_task(self, record: BridgeTaskRecord) -> None:
        with self._lock:
            target = self._task_file_path(record.task_id)
            _atomic_write_json(target, record.to_dict())

    def _recover_state(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        json_files = sorted(self.state_dir.glob("*.json"))
        loaded_records: List[BridgeTaskRecord] = []

        for fpath in json_files:
            if fpath.name.startswith(".tmp"):
                continue
            try:
                raw_text = fpath.read_text(encoding="utf-8")
                data = json.loads(raw_text)
                if not isinstance(data, dict):
                    raise ValueError(f"Task record JSON must be an object, got {type(data).__name__}")
                record = BridgeTaskRecord.from_dict(data)

                # Requirement 4:
                # - SUCCESS/FAILED/CANCELLED remain terminal;
                # - any persisted QUEUED or RUNNING task is recovered FAIL-CLOSED as FAILED;
                # - recovered record gets finished_at and explicit error such as bridge restart/interruption;
                # - never silently restart an orphaned Anty subprocess.
                if record.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                    prev_status = record.status.value
                    record.status = TaskStatus.FAILED
                    if not record.finished_at:
                        record.finished_at = utc_now_iso()
                    interruption_msg = f"Recovered fail-closed after bridge restart/interruption while {prev_status}."
                    if record.error:
                        record.error = f"{interruption_msg} Prior error: {record.error}"
                    else:
                        record.error = interruption_msg
                    self._persist_task(record)

                loaded_records.append(record)

            except Exception as exc:
                # Requirement 6:
                # - corrupt/unparseable task-state file must NOT crash Bridge startup;
                # - quarantine/rename or skip it with diagnosable evidence;
                # - expose diagnostic count/details through existing health information.
                ts_str = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
                quarantine_name = f"{fpath.name}.corrupt_{ts_str}"
                quarantine_path = fpath.parent / quarantine_name
                try:
                    os.replace(fpath, quarantine_path)
                except Exception:
                    quarantine_path = fpath

                self.corrupt_records.append({
                    "file": fpath.name,
                    "quarantined_as": quarantine_path.name,
                    "error": str(exc),
                    "timestamp": utc_now_iso(),
                })

        for cpath in sorted(self.state_dir.glob("*.corrupt*")):
            if not any(c.get("quarantined_as") == cpath.name for c in self.corrupt_records):
                self.corrupt_records.append({
                    "file": cpath.name.split(".corrupt")[0],
                    "quarantined_as": cpath.name,
                    "error": "Previously quarantined corrupt state file",
                    "timestamp": utc_now_iso(),
                })

        loaded_records.sort(key=lambda r: r.created_at or "")
        with self._lock:
            for rec in loaded_records:
                if rec.task_id not in self.tasks:
                    self.tasks[rec.task_id] = rec

    def get_corrupt_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.corrupt_records)

    def submit_task(self, req: BridgeTaskRequest) -> BridgeTaskRecord:
        with self._lock:
            task_file = self._task_file_path(req.task_id)
            if req.task_id in self.tasks or task_file.exists():
                raise WorkerError(f"Task '{req.task_id}' already exists.")

            if req.validation_profile not in SUPPORTED_VALIDATION_PROFILES:
                raise WorkerError(
                    f"Invalid validation_profile '{req.validation_profile}'. Supported values: {sorted(SUPPORTED_VALIDATION_PROFILES)}"
                )

            if req.validation_profile == VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND:
                check_frozen_frontend_allowed_prefixes(req.allowed_prefixes)

            record = BridgeTaskRecord(
                task_id=req.task_id,
                prompt=req.prompt,
                base_sha=req.base_sha,
                target_branch=req.target_branch,
                allowed_prefixes=req.allowed_prefixes,
                commit_message=req.commit_message or f"feat(auto): execute {req.task_id}",
                timeout_seconds=req.timeout_seconds,
                callback_url=req.callback_url,
                validation_profile=req.validation_profile,
            )
            self.tasks[req.task_id] = record
            self._cancel_flags[req.task_id] = False
            self._persist_task(record)

        thread = threading.Thread(target=self._execute_task, args=(record,), daemon=True)
        self._active_thread = thread
        thread.start()
        return record

    def get_task(self, task_id: str) -> Optional[BridgeTaskRecord]:
        with self._lock:
            if task_id in self.tasks:
                return self.tasks[task_id]
            fpath = self._task_file_path(task_id)
            if fpath.is_file():
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    rec = BridgeTaskRecord.from_dict(data)
                    self.tasks[task_id] = rec
                    return rec
                except Exception:
                    return None
            return None

    def list_tasks(self) -> List[BridgeTaskRecord]:
        with self._lock:
            return list(self.tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            record = self.tasks.get(task_id)
            if not record or record.status not in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                return False
            self._cancel_flags[task_id] = True
            record.status = TaskStatus.CANCELLED
            record.finished_at = utc_now_iso()
            record.error = "Cancelled by user / client request."
            self._persist_task(record)
            return True

    def _execute_task(self, record: BridgeTaskRecord) -> None:
        worktree_path = self.worktree_root / record.task_id
        record.status = TaskStatus.RUNNING
        record.started_at = utc_now_iso()
        record.stage = "setup-worktree"
        self._persist_task(record)

        try:
            # 1. Validation
            if record.validation_profile not in SUPPORTED_VALIDATION_PROFILES:
                raise WorkerError(f"Unsupported validation_profile: {record.validation_profile}")
            if record.validation_profile == VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND:
                check_frozen_frontend_allowed_prefixes(record.allowed_prefixes)
            if not SHA_RE.fullmatch(record.base_sha):
                raise WorkerError("base_sha must be a full 40-character hex string.")
            if not BRANCH_RE.fullmatch(record.target_branch):
                raise WorkerError(f"Invalid target_branch: {record.target_branch}")
            if record.target_branch in {"main", "master"}:
                raise WorkerError("Target branch cannot be main/master.")

            # 2. Worktree preparation
            self.worktree_root.mkdir(parents=True, exist_ok=True)
            if worktree_path.exists():
                git(self.repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)
                shutil.rmtree(worktree_path, ignore_errors=True)

            git(self.repo_path, "fetch", "--all", "--prune")
            git(self.repo_path, "cat-file", "-e", f"{record.base_sha}^{{commit}}")
            git(self.repo_path, "worktree", "add", "-B", record.target_branch, str(worktree_path), record.base_sha)

            if self._cancel_flags.get(record.task_id):
                raise WorkerError("Task cancelled before agent run.")

            # 3. Agent Execution
            record.stage = "run-antigravity"
            self._persist_task(record)
            agy_bin = find_agy()
            wrapper = (
                "AUTOMATED MKE BRIDGE POLICY:\n"
                "- Edit only files within the allowed scope prefixes.\n"
                "- Do not execute git checkout, git commit, or git push.\n"
                "- Do not modify the frontend directory.\n\n"
            )
            full_prompt = wrapper + record.prompt
            agent_res = run_cmd(
                [agy_bin, "-p", full_prompt, "--output-format", "json"],
                cwd=worktree_path,
                timeout=record.timeout_seconds,
                check=True,
            )
            record.agent_output_tail = (agent_res.stdout + "\n" + agent_res.stderr)[-8000:]

            if self._cancel_flags.get(record.task_id):
                raise WorkerError("Task cancelled after agent run.")

            # 4. Scope & Frontend Check
            record.stage = "scope-validation"
            self._persist_task(record)
            all_changed = collect_changed_files(worktree_path, record.base_sha)
            validate_scope(all_changed, record.allowed_prefixes)
            if record.validation_profile == VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND:
                for path in all_changed:
                    norm = path.replace("\\", "/")
                    if (
                        norm == "src/frontend"
                        or norm.startswith("src/frontend/")
                        or "src/frontend/" in norm
                        or norm == "ui"
                        or norm.startswith("ui/")
                        or "ui/" in norm
                    ):
                        raise WorkerError(
                            f"Frontend freeze violation in backend_frozen_frontend profile: {path} cannot be modified."
                        )
            record.changed_files = all_changed
            self._persist_task(record)

            # 5. Validation profile
            py_bin = sys.executable
            if record.validation_profile == VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND:
                record.stage = "test-backend-frozen-frontend"
                self._persist_task(record)
                test_res = run_cmd(
                    [
                        py_bin,
                        "-m",
                        "pytest",
                        "tests/",
                        "-q",
                        "--ignore=tests/test_mvp_v1_product_app.py",
                        "--ignore=tests/test_mvp_v1_react_e2e.py",
                    ],
                    cwd=worktree_path,
                    timeout=600,
                    check=False,
                )
                marker = "[validation_profile: backend_frozen_frontend]\n"
                record.test_output_tail = (marker + test_res.stdout + "\n" + test_res.stderr)[-8000:]
                if test_res.returncode != 0:
                    raise WorkerError(
                        f"Backend regression tests failed ({test_res.returncode}):\n{record.test_output_tail}"
                    )
                record.changed_files = cleanup_test_side_effects(
                    worktree_path, record.base_sha, record.allowed_prefixes
                )
                self._persist_task(record)
            elif record.validation_profile == VALIDATION_PROFILE_AUTO:
                if is_control_plane_only(record.changed_files):
                    # Control-plane-only tasks cannot affect product/frontend behavior. Running the
                    # product build here can fail on unrelated baseline defects and falsely blame
                    # the automation change. Validate the control plane itself instead.
                    record.stage = "test-control-plane"
                    self._persist_task(record)
                    test_res = run_cmd(
                        [py_bin, "-m", "pytest", ".mke-agent/tests", "-q"],
                        cwd=worktree_path,
                        timeout=300,
                        check=True,
                    )
                    record.test_output_tail = (test_res.stdout + "\n" + test_res.stderr)[-8000:]
                    record.changed_files = cleanup_test_side_effects(
                        worktree_path, record.base_sha, record.allowed_prefixes
                    )
                    self._persist_task(record)
                else:
                    # Product tasks keep the full fail-closed validation path.
                    record.stage = "prepare-frontend"
                    self._persist_task(record)
                    frontend_prep_tail = prepare_frontend(worktree_path)

                    # Post-build scope verification: ensure build artifacts / node_modules didn't add un-ignored changes
                    post_build_changed = collect_changed_files(worktree_path, record.base_sha)
                    validate_scope(post_build_changed, record.allowed_prefixes)

                    record.stage = "test-regression"
                    self._persist_task(record)
                    test_res = run_cmd(
                        [py_bin, "-m", "pytest", "tests/", "-q"],
                        cwd=worktree_path,
                        timeout=600,
                        check=True,
                    )
                    prep_header = f"[frontend-prepare]\n{frontend_prep_tail}\n\n" if frontend_prep_tail else ""
                    record.test_output_tail = (prep_header + test_res.stdout + "\n" + test_res.stderr)[-8000:]

                    # Regression tests may create screenshots/evidence/cache files outside the task scope.
                    # Pre-test scope validation already proved task-authored changes were allowed, so
                    # clean only those post-test out-of-scope side effects before staging.
                    record.changed_files = cleanup_test_side_effects(
                        worktree_path, record.base_sha, record.allowed_prefixes
                    )
                    self._persist_task(record)
            else:
                raise WorkerError(f"Unsupported validation_profile: {record.validation_profile}")

            # 6. Commit & Push
            record.stage = "commit-push"
            self._persist_task(record)
            git(worktree_path, "config", "user.name", "MKE Antigravity Bridge")
            git(worktree_path, "config", "user.email", "mke-bridge@local.invalid")
            git(worktree_path, "add", "-A")

            # Verify that only allowed files are staged and no frontend files are committed
            staged = git(worktree_path, "diff", "--cached", "--name-only", check=True).stdout.splitlines()
            staged_paths = sorted(set(p.strip().replace("\\", "/") for p in staged if p.strip()))
            if not staged_paths:
                raise WorkerError("No staged changes to commit after test execution.")
            for p in staged_paths:
                if p.startswith("src/frontend/") or p.startswith("ui/"):
                    raise WorkerError(f"Frontend freeze violation in staged files: {p} cannot be committed.")
                if not allowed_path(p, record.allowed_prefixes):
                    raise WorkerError(f"Scope violation in staged files: {p} is not in allowed_prefixes.")

            git(worktree_path, "commit", "-m", record.commit_message)
            commit_sha = git(worktree_path, "rev-parse", "HEAD").stdout.strip()
            record.commit_sha = commit_sha
            self._persist_task(record)

            git(worktree_path, "push", "--set-upstream", "origin", record.target_branch, timeout=300)

            # 7. Cleanup & Completion
            record.stage = "complete"
            record.status = TaskStatus.SUCCESS
            record.finished_at = utc_now_iso()
            self._persist_task(record)
            git(self.repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)

        except Exception as exc:
            if not self._cancel_flags.get(record.task_id):
                record.status = TaskStatus.FAILED
                record.error = str(exc)
            record.finished_at = utc_now_iso()
            self._persist_task(record)
            git(self.repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)

        finally:
            self._persist_task(record)
            # Trigger callback webhook if registered
            if record.callback_url:
                try:
                    payload = json.dumps(record.to_dict()).encode("utf-8")
                    req = urllib.request.Request(
                        record.callback_url,
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=10)
                except Exception:
                    pass
