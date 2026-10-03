"""Unit tests for MKE Antigravity Bridge."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
import subprocess
from unittest import mock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.models import BridgeTaskRecord, BridgeTaskRequest, TaskStatus
from bridge.server import MCP_TOOLS_SPEC, create_handler_class, handle_mcp_call
from bridge.worker import (
    TaskWorker,
    WorkerError,
    _atomic_write_json,
    find_npm,
    prepare_frontend,
    collect_changed_files,
    validate_scope,
    allowed_path,
)


class DummyWorker:
    def __init__(self):
        self.repo_path = Path("D:/Math Knowledge Engine")
        self.tasks = {}
        self.corrupt_records = []

    def get_corrupt_records(self):
        return list(self.corrupt_records)

    def submit_task(self, req: BridgeTaskRequest) -> BridgeTaskRecord:
        rec = BridgeTaskRecord(
            task_id=req.task_id,
            prompt=req.prompt,
            base_sha=req.base_sha,
            target_branch=req.target_branch,
            allowed_prefixes=req.allowed_prefixes,
            commit_message=req.commit_message,
            timeout_seconds=req.timeout_seconds,
            status=TaskStatus.QUEUED,
        )
        self.tasks[req.task_id] = rec
        return rec

    def get_task(self, task_id: str):
        return self.tasks.get(task_id)

    def list_tasks(self):
        return list(self.tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            return True
        return False


def test_mcp_tools_spec_has_all_five_tools():
    tool_names = {t["name"] for t in MCP_TOOLS_SPEC}
    assert "anty_submit_task" in tool_names
    assert "anty_task_status" in tool_names
    assert "anty_get_report" in tool_names
    assert "anty_cancel_task" in tool_names
    assert "anty_health" in tool_names


def test_mcp_health_tool():
    worker = DummyWorker()
    res = handle_mcp_call(worker, "anty_health", {})
    assert "content" in res
    data = json.loads(res["content"][0]["text"])
    assert data["service"] == "MKE Antigravity Bridge"
    assert data["status"] == "HEALTHY"


def test_mcp_submit_and_status_cycle():
    worker = DummyWorker()
    args = {
        "task_id": "TEST-TASK-001",
        "prompt": "Implement something",
        "base_sha": "a" * 40,
        "target_branch": "product/test-branch",
    }
    submit_res = handle_mcp_call(worker, "anty_submit_task", args)
    submit_data = json.loads(submit_res["content"][0]["text"])
    assert submit_data["status"] == "SUBMITTED"
    assert submit_data["task"]["task_id"] == "TEST-TASK-001"

    status_res = handle_mcp_call(worker, "anty_task_status", {"task_id": "TEST-TASK-001"})
    status_data = json.loads(status_res["content"][0]["text"])
    assert status_data["task_id"] == "TEST-TASK-001"
    assert status_data["status"] == "QUEUED"


def test_mcp_cancel_tool():
    worker = DummyWorker()
    worker.submit_task(BridgeTaskRequest(
        task_id="TEST-CANCEL",
        prompt="test",
        base_sha="a" * 40,
        target_branch="product/test",
    ))
    cancel_res = handle_mcp_call(worker, "anty_cancel_task", {"task_id": "TEST-CANCEL"})
    cancel_data = json.loads(cancel_res["content"][0]["text"])
    assert cancel_data["cancelled"] is True

    status_res = handle_mcp_call(worker, "anty_task_status", {"task_id": "TEST-CANCEL"})
    status_data = json.loads(status_res["content"][0]["text"])
    assert status_data["status"] == "CANCELLED"


def test_prepare_frontend_runs_ci_then_build_when_lockfile_exists(tmp_path: Path):
    fe_dir = tmp_path / "src" / "frontend"
    fe_dir.mkdir(parents=True)
    lockfile = fe_dir / "package-lock.json"
    lockfile.write_text("{}", encoding="utf-8")

    commands_executed = []

    def fake_run_cmd(cmd, cwd, timeout=None, check=True):
        commands_executed.append((list(cmd), Path(cwd)))
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=f"mock stdout for {' '.join(cmd[:3])}",
            stderr="",
        )

    with mock.patch("shutil.which", return_value="C:\\dummy\\npm.cmd"), \
         mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd):
        res = prepare_frontend(tmp_path)

    assert len(commands_executed) == 2
    assert commands_executed[0][0] == ["C:\\dummy\\npm.cmd", "ci"]
    assert commands_executed[0][1] == fe_dir
    assert commands_executed[1][0] == ["C:\\dummy\\npm.cmd", "run", "build"]
    assert commands_executed[1][1] == fe_dir
    assert "mock stdout for C:\\dummy\\npm.cmd ci" in res
    assert "mock stdout for C:\\dummy\\npm.cmd run build" in res


def test_prepare_frontend_missing_npm_fails_closed(tmp_path: Path):
    fe_dir = tmp_path / "src" / "frontend"
    fe_dir.mkdir(parents=True)
    lockfile = fe_dir / "package-lock.json"
    lockfile.write_text("{}", encoding="utf-8")

    with mock.patch("shutil.which", return_value=None):
        with pytest.raises(WorkerError, match="npm is required for frontend build but was not found on PATH"):
            prepare_frontend(tmp_path)


def test_prepare_frontend_absent_packagelock_skips_deterministically(tmp_path: Path):
    # Lockfile does not exist. Even if npm is missing, it should skip cleanly without error.
    with mock.patch("shutil.which", return_value=None):
        res = prepare_frontend(tmp_path)
    assert "package-lock absent" in res.lower()
    assert "skipping" in res.lower()


def test_prepare_frontend_command_failure_fails_closed(tmp_path: Path):
    fe_dir = tmp_path / "src" / "frontend"
    fe_dir.mkdir(parents=True)
    (fe_dir / "package-lock.json").write_text("{}", encoding="utf-8")

    def fake_run_cmd(cmd, cwd, timeout=None, check=True):
        if "build" in cmd:
            raise WorkerError("Command failed (1): npm run build\nBuild compilation failed")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="installed ok", stderr="")

    with mock.patch("shutil.which", return_value="C:\\dummy\\npm.cmd"), \
         mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd):
        with pytest.raises(WorkerError, match="Build compilation failed"):
            prepare_frontend(tmp_path)


def test_ignored_build_output_not_considered_allowed_source_change(tmp_path: Path):
    # Setup temporary git repo
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=str(tmp_path), capture_output=True, check=True)

    # Setup .gitignore with dist/ and node_modules/
    (tmp_path / ".gitignore").write_text("dist/\nnode_modules/\n", encoding="utf-8")
    prod_file = tmp_path / "src" / "mke_product" / "coverage" / "contracts.py"
    prod_file.parent.mkdir(parents=True)
    prod_file.write_text("# initial content\n", encoding="utf-8")

    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial base commit"], cwd=str(tmp_path), capture_output=True, check=True)
    base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp_path), capture_output=True, text=True, check=True).stdout.strip()

    # Simulate generated ignored build artifacts
    dist_dir = tmp_path / "src" / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<!DOCTYPE html><html></html>", encoding="utf-8")
    (dist_dir / "bundle.js").write_text("console.log('build');", encoding="utf-8")

    node_modules_dir = tmp_path / "src" / "frontend" / "node_modules" / "testpkg"
    node_modules_dir.mkdir(parents=True)
    (node_modules_dir / "index.js").write_text("module.exports = {};", encoding="utf-8")

    # 1. With only ignored build artifacts present, collect_changed_files must return empty
    changed = collect_changed_files(tmp_path, base_sha)
    assert changed == []

    # 2. validate_scope must fail closed when no allowed source modifications were made
    with pytest.raises(WorkerError, match="without modifying or creating any files"):
        validate_scope(changed, ["src/mke_product/coverage/"])

    # 3. Explicitly attempting to validate a path under src/frontend/dist must trigger frontend freeze violation
    with pytest.raises(WorkerError, match="Frontend freeze violation"):
        validate_scope(["src/frontend/dist/bundle.js"], ["src/mke_product/coverage/"])

    # 4. Now modify an allowed product file alongside the ignored build output
    prod_file.write_text("# updated product logic\n", encoding="utf-8")
    changed_after_edit = collect_changed_files(tmp_path, base_sha)
    assert changed_after_edit == ["src/mke_product/coverage/contracts.py"]
    validate_scope(changed_after_edit, ["src/mke_product/coverage/"])

    # 5. git add -A must not stage gitignored build artifacts
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=str(tmp_path), capture_output=True, text=True, check=True).stdout.splitlines()
    staged_paths = [p.strip().replace("\\", "/") for p in staged if p.strip()]
    assert staged_paths == ["src/mke_product/coverage/contracts.py"]


def test_terminal_state_persistence_and_reload(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)

    # 1. Success task
    with mock.patch.object(worker, "_execute_task"):
        success_rec = worker.submit_task(BridgeTaskRequest(
            task_id="TASK-SUCCESS",
            prompt="do work",
            base_sha="a" * 40,
            target_branch="product/test-success",
        ))
    success_rec.status = TaskStatus.SUCCESS
    success_rec.finished_at = "2026-10-04T01:00:00+00:00"
    success_rec.commit_sha = "c" * 40
    success_rec.stage = "complete"
    success_rec.changed_files = ["src/mke_product/coverage/file1.py"]
    worker._persist_task(success_rec)

    # 2. Failed task
    with mock.patch.object(worker, "_execute_task"):
        failed_rec = worker.submit_task(BridgeTaskRequest(
            task_id="TASK-FAILED",
            prompt="do failing work",
            base_sha="b" * 40,
            target_branch="product/test-fail",
        ))
    failed_rec.status = TaskStatus.FAILED
    failed_rec.finished_at = "2026-10-04T01:05:00+00:00"
    failed_rec.error = "Scope violation: outside prefix"
    worker._persist_task(failed_rec)

    # 3. Cancelled task
    with mock.patch.object(worker, "_execute_task"):
        cancel_rec = worker.submit_task(BridgeTaskRequest(
            task_id="TASK-CANCELLED",
            prompt="do cancelled work",
            base_sha="d" * 40,
            target_branch="product/test-cancel",
        ))
    worker.cancel_task("TASK-CANCELLED")

    # Verify all 3 files exist on disk
    assert (state_dir / "TASK-SUCCESS.json").is_file()
    assert (state_dir / "TASK-FAILED.json").is_file()
    assert (state_dir / "TASK-CANCELLED.json").is_file()

    # Simulate Bridge restart with fresh worker
    reloaded_worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)
    tasks = {t.task_id: t for t in reloaded_worker.list_tasks()}

    assert len(tasks) == 3

    # Verify SUCCESS remains terminal with all attributes
    s = tasks["TASK-SUCCESS"]
    assert s.status == TaskStatus.SUCCESS
    assert s.finished_at == "2026-10-04T01:00:00+00:00"
    assert s.commit_sha == "c" * 40
    assert s.stage == "complete"
    assert s.changed_files == ["src/mke_product/coverage/file1.py"]

    # Verify FAILED remains terminal
    f = tasks["TASK-FAILED"]
    assert f.status == TaskStatus.FAILED
    assert f.finished_at == "2026-10-04T01:05:00+00:00"
    assert f.error == "Scope violation: outside prefix"

    # Verify CANCELLED remains terminal
    c = tasks["TASK-CANCELLED"]
    assert c.status == TaskStatus.CANCELLED
    assert c.finished_at is not None
    assert "Cancelled" in (c.error or "")


def test_queued_recovery_after_restart(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    queued_task = {
        "task_id": "TASK-QUEUED-ORPHAN",
        "prompt": "Orphaned queued prompt",
        "base_sha": "1" * 40,
        "target_branch": "product/orphan-q",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "feat: queued",
        "timeout_seconds": 900,
        "status": "QUEUED",
        "created_at": "2026-10-04T00:00:00+00:00",
        "started_at": None,
        "finished_at": None,
        "commit_sha": None,
        "stage": "init",
        "error": None,
        "changed_files": [],
        "agent_output_tail": "",
        "test_output_tail": "",
        "callback_url": None,
    }
    (state_dir / "TASK-QUEUED-ORPHAN.json").write_text(json.dumps(queued_task), encoding="utf-8")

    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)

    recovered = worker.get_task("TASK-QUEUED-ORPHAN")
    assert recovered is not None
    assert recovered.status == TaskStatus.FAILED
    assert recovered.finished_at is not None
    assert "bridge restart/interruption" in recovered.error
    assert "QUEUED" in recovered.error

    # Verify no worker thread or subprocess was started
    assert worker._active_thread is None

    # Verify disk file is updated to FAILED state
    disk_data = json.loads((state_dir / "TASK-QUEUED-ORPHAN.json").read_text(encoding="utf-8"))
    assert disk_data["status"] == "FAILED"
    assert disk_data["finished_at"] is not None
    assert "bridge restart/interruption" in disk_data["error"]


def test_running_recovery_after_restart(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    running_task = {
        "task_id": "TASK-RUNNING-ORPHAN",
        "prompt": "Orphaned running prompt",
        "base_sha": "2" * 40,
        "target_branch": "product/orphan-r",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "feat: running",
        "timeout_seconds": 900,
        "status": "RUNNING",
        "created_at": "2026-10-04T00:00:00+00:00",
        "started_at": "2026-10-04T00:01:00+00:00",
        "finished_at": None,
        "commit_sha": None,
        "stage": "run-antigravity",
        "error": None,
        "changed_files": [],
        "agent_output_tail": "partial agent execution...",
        "test_output_tail": "",
        "callback_url": None,
    }
    (state_dir / "TASK-RUNNING-ORPHAN.json").write_text(json.dumps(running_task), encoding="utf-8")

    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)

    recovered = worker.get_task("TASK-RUNNING-ORPHAN")
    assert recovered is not None
    assert recovered.status == TaskStatus.FAILED
    assert recovered.finished_at is not None
    assert "bridge restart/interruption" in recovered.error
    assert "RUNNING" in recovered.error
    assert recovered.agent_output_tail == "partial agent execution..."

    # Subprocess/thread was not launched
    assert worker._active_thread is None

    # Disk file is updated to FAILED state
    disk_data = json.loads((state_dir / "TASK-RUNNING-ORPHAN.json").read_text(encoding="utf-8"))
    assert disk_data["status"] == "FAILED"
    assert "bridge restart/interruption" in disk_data["error"]


def test_duplicate_task_id_rejection(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)

    req = BridgeTaskRequest(
        task_id="TASK-DUP-001",
        prompt="Initial execution",
        base_sha="3" * 40,
        target_branch="product/test-dup",
    )
    with mock.patch.object(worker, "_execute_task"):
        worker.submit_task(req)

        # 1. Attempt submitting same task while in memory: must reject deterministically
        with pytest.raises(WorkerError, match="already exists"):
            worker.submit_task(req)

    task = worker.get_task("TASK-DUP-001")
    task.status = TaskStatus.SUCCESS
    task.finished_at = "2026-10-04T00:10:00+00:00"
    worker._persist_task(task)

    # 2. Attempt submitting same task while terminal in memory: must reject deterministically
    with pytest.raises(WorkerError, match="already exists"):
        worker.submit_task(req)

    # 3. Simulate bridge restart, reloading task history from disk
    worker2 = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)
    with pytest.raises(WorkerError, match="already exists"):
        worker2.submit_task(req)

    # Verify previous history is untouched and still SUCCESS
    persisted = worker2.get_task("TASK-DUP-001")
    assert persisted.status == TaskStatus.SUCCESS
    assert persisted.prompt == "Initial execution"


def test_corrupt_state_failsafe_and_quarantine(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 1. Valid task JSON
    valid_task = {
        "task_id": "TASK-VALID-001",
        "prompt": "Valid task",
        "base_sha": "4" * 40,
        "target_branch": "product/valid",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "valid",
        "timeout_seconds": 900,
        "status": "SUCCESS",
        "created_at": "2026-10-04T00:00:00+00:00",
        "finished_at": "2026-10-04T00:05:00+00:00",
        "commit_sha": "5" * 40,
        "stage": "complete",
        "error": None,
        "changed_files": [],
        "agent_output_tail": "",
        "test_output_tail": "",
        "callback_url": None,
    }
    (state_dir / "TASK-VALID-001.json").write_text(json.dumps(valid_task), encoding="utf-8")

    # 2. Syntax-corrupted JSON
    (state_dir / "TASK-CORRUPT-SYNTAX.json").write_text('{"task_id": "broken", incomplete...', encoding="utf-8")

    # 3. Schema-corrupted JSON (missing task_id)
    (state_dir / "TASK-CORRUPT-SCHEMA.json").write_text('{"invalid_field": 123}', encoding="utf-8")

    # Startup must NOT crash
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)

    # Valid task is loaded
    assert "TASK-VALID-001" in worker.tasks
    assert worker.tasks["TASK-VALID-001"].status == TaskStatus.SUCCESS

    # Corrupt files quarantined (no longer ending with .json as main file)
    assert not (state_dir / "TASK-CORRUPT-SYNTAX.json").exists()
    assert not (state_dir / "TASK-CORRUPT-SCHEMA.json").exists()

    quarantined = list(state_dir.glob("*.corrupt*"))
    assert len(quarantined) == 2

    # Diagnostic evidence recorded
    corrupt_records = worker.get_corrupt_records()
    assert len(corrupt_records) == 2
    corrupt_filenames = {c["file"] for c in corrupt_records}
    assert "TASK-CORRUPT-SYNTAX.json" in corrupt_filenames
    assert "TASK-CORRUPT-SCHEMA.json" in corrupt_filenames

    # Health check exposes corrupt tasks
    res = handle_mcp_call(worker, "anty_health", {})
    health_data = json.loads(res["content"][0]["text"])
    assert health_data["corrupt_tasks_count"] == 2
    assert len(health_data["corrupt_tasks"]) == 2


def test_atomic_replacement_and_partial_write_safety(tmp_path: Path):
    state_file = tmp_path / "runtime" / "bridge-state" / "ATOMIC-TEST.json"

    # Step 1: Initial atomic write
    initial_data = {"task_id": "ATOMIC-TEST", "status": "QUEUED", "version": 1}
    _atomic_write_json(state_file, initial_data)
    assert state_file.is_file()
    assert json.loads(state_file.read_text(encoding="utf-8")) == initial_data

    # Verify no temp files remained
    temp_files = list(state_file.parent.glob("*.tmp"))
    assert len(temp_files) == 0

    # Step 2: Simulate failure during write of updated data
    updated_data = {"task_id": "ATOMIC-TEST", "status": "SUCCESS", "version": 2}
    with mock.patch("json.dump", side_effect=IOError("Simulated write failure")):
        with pytest.raises(IOError, match="Simulated write failure"):
            _atomic_write_json(state_file, updated_data)

    # Destination file MUST still exist and contain the original, valid uncorrupted data
    assert state_file.is_file()
    assert json.loads(state_file.read_text(encoding="utf-8")) == initial_data

    # Temp files must be cleaned up in finally block
    temp_files_after = list(state_file.parent.glob("*.tmp"))
    assert len(temp_files_after) == 0

    # Step 3: Now perform successful atomic update
    _atomic_write_json(state_file, updated_data)
    assert json.loads(state_file.read_text(encoding="utf-8")) == updated_data
    assert len(list(state_file.parent.glob("*.tmp"))) == 0


def test_runtime_state_remains_outside_committed_source(tmp_path: Path):
    # Initialize a temporary git repository
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=str(tmp_path), capture_output=True, check=True)

    # Setup .mke-agent/.gitignore
    agent_dir = tmp_path / ".mke-agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / ".gitignore").write_text("logs/\nruntime/\n*.tmp\n*.corrupt*\n", encoding="utf-8")

    # Initial commit
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tmp_path), capture_output=True, text=True, check=True).stdout.strip()

    # Now create runtime state files and temp files
    runtime_state_dir = agent_dir / "runtime" / "bridge-state"
    runtime_state_dir.mkdir(parents=True)
    (runtime_state_dir / "TASK-001.json").write_text('{"task_id": "TASK-001"}', encoding="utf-8")
    (runtime_state_dir / ".tmp_TASK-001.tmp").write_text('temporary buffer', encoding="utf-8")
    (runtime_state_dir / "TASK-BAD.corrupt_20261004").write_text('corrupt buffer', encoding="utf-8")

    # 1. collect_changed_files must return empty
    changed = collect_changed_files(tmp_path, base_sha)
    assert changed == []

    # 2. git add -A must NOT stage runtime state
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True, check=True)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert staged == []


def test_api_tasks_list_includes_recovered_records(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    task_data = {
        "task_id": "RECOVERED-001",
        "prompt": "Recovered task",
        "base_sha": "5" * 40,
        "target_branch": "product/recovered",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "recovered commit",
        "timeout_seconds": 900,
        "status": "SUCCESS",
        "created_at": "2026-10-04T00:00:00+00:00",
        "finished_at": "2026-10-04T00:05:00+00:00",
        "commit_sha": "6" * 40,
        "stage": "complete",
        "error": None,
        "changed_files": ["src/mke_product/coverage/test.py"],
        "agent_output_tail": "",
        "test_output_tail": "",
        "callback_url": None,
    }
    (state_dir / "RECOVERED-001.json").write_text(json.dumps(task_data), encoding="utf-8")

    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)
    tasks = worker.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == "RECOVERED-001"
    assert tasks[0].status == TaskStatus.SUCCESS
    assert tasks[0].to_dict()["status"] == "SUCCESS"
