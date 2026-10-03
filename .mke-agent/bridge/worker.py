"""Task execution engine for MKE Antigravity Bridge."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

if __package__ or "." in __name__:
    from .models import BridgeTaskRecord, BridgeTaskRequest, TaskStatus, utc_now_iso
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from bridge.models import BridgeTaskRecord, BridgeTaskRequest, TaskStatus, utc_now_iso

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


class TaskWorker:
    """Manages background task queue and worker execution."""

    def __init__(self, repo_path: Path, worktree_root: Path) -> None:
        self.repo_path = repo_path.resolve()
        self.worktree_root = worktree_root.resolve()
        self.tasks: Dict[str, BridgeTaskRecord] = {}
        self._lock = threading.Lock()
        self._active_thread: Optional[threading.Thread] = None
        self._cancel_flags: Dict[str, bool] = {}

    def submit_task(self, req: BridgeTaskRequest) -> BridgeTaskRecord:
        with self._lock:
            if req.task_id in self.tasks and self.tasks[req.task_id].status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                raise WorkerError(f"Task {req.task_id} is already in progress.")

            record = BridgeTaskRecord(
                task_id=req.task_id,
                prompt=req.prompt,
                base_sha=req.base_sha,
                target_branch=req.target_branch,
                allowed_prefixes=req.allowed_prefixes,
                commit_message=req.commit_message or f"feat(auto): execute {req.task_id}",
                timeout_seconds=req.timeout_seconds,
                callback_url=req.callback_url,
            )
            self.tasks[req.task_id] = record
            self._cancel_flags[req.task_id] = False

        thread = threading.Thread(target=self._execute_task, args=(record,), daemon=True)
        thread.start()
        return record

    def get_task(self, task_id: str) -> Optional[BridgeTaskRecord]:
        with self._lock:
            return self.tasks.get(task_id)

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
            return True

    def _execute_task(self, record: BridgeTaskRecord) -> None:
        worktree_path = self.worktree_root / record.task_id
        record.status = TaskStatus.RUNNING
        record.started_at = utc_now_iso()
        record.stage = "setup-worktree"

        try:
            # 1. Validation
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
            changed = git(worktree_path, "diff", "--name-only", record.base_sha, check=True).stdout.splitlines()
            untracked = git(worktree_path, "ls-files", "--others", "--exclude-standard", check=True).stdout.splitlines()
            all_changed = sorted(set(p.strip() for p in changed + untracked if p.strip()))

            if not all_changed:
                raise WorkerError("Antigravity completed without modifying or creating any files.")

            for path in all_changed:
                if not allowed_path(path, record.allowed_prefixes):
                    raise WorkerError(f"Scope violation: {path} is not in allowed_prefixes.")
                if path.startswith("src/frontend/") or path.startswith("ui/"):
                    raise WorkerError(f"Frontend freeze violation: {path} cannot be modified.")

            record.changed_files = all_changed

            # 5. Full Regression Tests
            record.stage = "test-regression"
            py_bin = sys.executable
            test_res = run_cmd([py_bin, "-m", "pytest", "tests/", "-q"], cwd=worktree_path, timeout=600, check=True)
            record.test_output_tail = (test_res.stdout + "\n" + test_res.stderr)[-8000:]

            # 6. Commit & Push
            record.stage = "commit-push"
            git(worktree_path, "config", "user.name", "MKE Antigravity Bridge")
            git(worktree_path, "config", "user.email", "mke-bridge@local.invalid")
            git(worktree_path, "add", "-A")
            git(worktree_path, "commit", "-m", record.commit_message)
            commit_sha = git(worktree_path, "rev-parse", "HEAD").stdout.strip()
            record.commit_sha = commit_sha

            git(worktree_path, "push", "--set-upstream", "origin", record.target_branch, timeout=300)

            # 7. Cleanup & Completion
            record.stage = "complete"
            record.status = TaskStatus.SUCCESS
            record.finished_at = utc_now_iso()
            git(self.repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)

        except Exception as exc:
            if not self._cancel_flags.get(record.task_id):
                record.status = TaskStatus.FAILED
                record.error = str(exc)
            record.finished_at = utc_now_iso()
            git(self.repo_path, "worktree", "remove", "--force", str(worktree_path), check=False)

        finally:
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
