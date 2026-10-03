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

from bridge.models import (
    BridgeTaskRecord,
    BridgeTaskRequest,
    TaskStatus,
    SUPPORTED_VALIDATION_PROFILES,
    VALIDATION_PROFILE_AUTO,
    VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND,
)
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
    check_frozen_frontend_allowed_prefixes,
)


class DummyWorker:
    def __init__(self):
        self.repo_path = Path("D:/Math Knowledge Engine")
        self.tasks = {}
        self.corrupt_records = []

    def get_corrupt_records(self):
        return list(self.corrupt_records)

    def submit_task(self, req: BridgeTaskRequest) -> BridgeTaskRecord:
        if req.validation_profile not in SUPPORTED_VALIDATION_PROFILES:
            raise WorkerError(f"Invalid validation_profile: {req.validation_profile}")
        if req.validation_profile == VALIDATION_PROFILE_BACKEND_FROZEN_FRONTEND:
            check_frozen_frontend_allowed_prefixes(req.allowed_prefixes)
        rec = BridgeTaskRecord(
            task_id=req.task_id,
            prompt=req.prompt,
            base_sha=req.base_sha,
            target_branch=req.target_branch,
            allowed_prefixes=req.allowed_prefixes,
            commit_message=req.commit_message,
            timeout_seconds=req.timeout_seconds,
            status=TaskStatus.QUEUED,
            validation_profile=req.validation_profile,
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


def test_old_request_and_record_defaults_to_auto():
    # 1. BridgeTaskRequest defaults to "auto"
    req = BridgeTaskRequest(
        task_id="TEST-DEFAULT-001",
        prompt="Test prompt",
        base_sha="a" * 40,
        target_branch="product/test-default",
    )
    assert req.validation_profile == "auto"

    # 2. BridgeTaskRecord defaults to "auto"
    rec = BridgeTaskRecord(
        task_id="TEST-DEFAULT-001",
        prompt="Test prompt",
        base_sha="a" * 40,
        target_branch="product/test-default",
        allowed_prefixes=["src/mke_product/coverage/"],
        commit_message="feat: default",
        timeout_seconds=900,
    )
    assert rec.validation_profile == "auto"

    # 3. Old persisted dictionary without validation_profile field loads as "auto"
    old_data = {
        "task_id": "TEST-OLD-001",
        "prompt": "Old task",
        "base_sha": "b" * 40,
        "target_branch": "product/test-old",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "feat: old",
        "timeout_seconds": 900,
        "status": "SUCCESS",
    }
    rec_from_old = BridgeTaskRecord.from_dict(old_data)
    assert rec_from_old.validation_profile == "auto"

    # 4. Explicit None or empty string also defaults to "auto"
    data_with_none = dict(old_data, validation_profile=None)
    assert BridgeTaskRecord.from_dict(data_with_none).validation_profile == "auto"
    data_with_empty = dict(old_data, validation_profile="")
    assert BridgeTaskRecord.from_dict(data_with_empty).validation_profile == "auto"


def test_durable_round_trip_and_recovery_preserves_validation_profile(tmp_path: Path):
    state_dir = tmp_path / "runtime" / "bridge-state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 1. Round-trip serialization with validation_profile
    rec = BridgeTaskRecord(
        task_id="TASK-PROFILE-RT",
        prompt="Task prompt",
        base_sha="c" * 40,
        target_branch="product/test-rt",
        allowed_prefixes=["src/mke_product/coverage/"],
        commit_message="feat: profile rt",
        timeout_seconds=900,
        status=TaskStatus.SUCCESS,
        finished_at="2026-10-04T02:00:00+00:00",
        validation_profile="backend_frozen_frontend",
    )
    rec_dict = rec.to_dict()
    assert rec_dict["validation_profile"] == "backend_frozen_frontend"

    # Save to disk
    _atomic_write_json(state_dir / "TASK-PROFILE-RT.json", rec_dict)

    # Write an old record without validation_profile to test recovery
    old_task = {
        "task_id": "TASK-OLD-RECOVERED",
        "prompt": "Old task without profile",
        "base_sha": "d" * 40,
        "target_branch": "product/test-old",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "commit_message": "feat: old",
        "timeout_seconds": 900,
        "status": "SUCCESS",
        "finished_at": "2026-10-04T02:05:00+00:00",
    }
    (state_dir / "TASK-OLD-RECOVERED.json").write_text(json.dumps(old_task), encoding="utf-8")

    # Recover state with fresh worker
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=state_dir)
    loaded_rt = worker.get_task("TASK-PROFILE-RT")
    assert loaded_rt is not None
    assert loaded_rt.validation_profile == "backend_frozen_frontend"
    assert loaded_rt.status == TaskStatus.SUCCESS

    loaded_old = worker.get_task("TASK-OLD-RECOVERED")
    assert loaded_old is not None
    assert loaded_old.validation_profile == "auto"
    assert loaded_old.status == TaskStatus.SUCCESS


def test_rest_and_mcp_submit_accepts_validation_profile(tmp_path: Path):
    worker = DummyWorker()

    # 1. MCP submit accepts validation_profile
    mcp_args = {
        "task_id": "MCP-SUBMIT-PROFILE",
        "prompt": "Test MCP submit with profile",
        "base_sha": "e" * 40,
        "target_branch": "product/mcp-profile",
        "validation_profile": "backend_frozen_frontend",
    }
    mcp_res = handle_mcp_call(worker, "anty_submit_task", mcp_args)
    mcp_data = json.loads(mcp_res["content"][0]["text"])
    assert mcp_data["status"] == "SUBMITTED"
    assert mcp_data["task"]["validation_profile"] == "backend_frozen_frontend"
    assert worker.get_task("MCP-SUBMIT-PROFILE").validation_profile == "backend_frozen_frontend"

    # 2. REST submit accepts validation_profile
    import io
    handler_cls = create_handler_class(worker)
    rest_body = json.dumps({
        "task_id": "REST-SUBMIT-PROFILE",
        "prompt": "Test REST submit with profile",
        "base_sha": "f" * 40,
        "target_branch": "product/rest-profile",
        "validation_profile": "backend_frozen_frontend",
    }).encode("utf-8")

    handler = handler_cls.__new__(handler_cls)
    handler.rfile = io.BytesIO(rest_body)
    handler.wfile = io.BytesIO()
    handler.headers = {"Content-Length": str(len(rest_body))}
    handler.path = "/api/tasks/submit"
    responses = []
    headers = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda k, v: headers.append((k, v))
    handler.end_headers = lambda: None

    handler.do_POST()
    assert responses == [202]
    rest_resp = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert rest_resp["status"] == "QUEUED"
    assert rest_resp["task"]["validation_profile"] == "backend_frozen_frontend"
    assert worker.get_task("REST-SUBMIT-PROFILE").validation_profile == "backend_frozen_frontend"

    # Test GET /api/tasks/{task_id}/status includes validation_profile
    get_handler = handler_cls.__new__(handler_cls)
    get_handler.rfile = io.BytesIO()
    get_handler.wfile = io.BytesIO()
    get_handler.headers = {"Content-Length": "0"}
    get_handler.path = "/api/tasks/REST-SUBMIT-PROFILE/status"
    get_responses = []
    get_handler.send_response = lambda code: get_responses.append(code)
    get_handler.send_header = lambda k, v: None
    get_handler.end_headers = lambda: None

    get_handler.do_GET()
    assert get_responses == [200]
    status_resp = json.loads(get_handler.wfile.getvalue().decode("utf-8"))
    assert status_resp["validation_profile"] == "backend_frozen_frontend"


def test_backend_frozen_frontend_rejects_frontend_and_ui_allowed_prefixes(tmp_path: Path):
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")

    # 1. Direct submit_task with src/frontend/ prefix
    with pytest.raises(WorkerError, match="rejects frontend/ui prefix"):
        worker.submit_task(BridgeTaskRequest(
            task_id="TASK-REJECT-PREF-1",
            prompt="test",
            base_sha="a" * 40,
            target_branch="product/rej-1",
            allowed_prefixes=["src/frontend/"],
            validation_profile="backend_frozen_frontend",
        ))

    # 2. Direct submit_task with ui/ prefix
    with pytest.raises(WorkerError, match="rejects frontend/ui prefix"):
        worker.submit_task(BridgeTaskRequest(
            task_id="TASK-REJECT-PREF-2",
            prompt="test",
            base_sha="a" * 40,
            target_branch="product/rej-2",
            allowed_prefixes=["ui/"],
            validation_profile="backend_frozen_frontend",
        ))

    # 3. Direct submit_task with src/frontend sub-directory prefix
    with pytest.raises(WorkerError, match="rejects frontend/ui prefix"):
        worker.submit_task(BridgeTaskRequest(
            task_id="TASK-REJECT-PREF-3",
            prompt="test",
            base_sha="a" * 40,
            target_branch="product/rej-3",
            allowed_prefixes=["src/mke_product/coverage/", "src/frontend/components/"],
            validation_profile="backend_frozen_frontend",
        ))

    # 4. REST submit with ui/ prefix fails closed with 400
    import io
    handler_cls = create_handler_class(worker)
    rest_body = json.dumps({
        "task_id": "REST-REJECT-UI",
        "prompt": "test",
        "base_sha": "a" * 40,
        "target_branch": "product/rej-ui",
        "allowed_prefixes": ["ui/components/"],
        "validation_profile": "backend_frozen_frontend",
    }).encode("utf-8")

    handler = handler_cls.__new__(handler_cls)
    handler.rfile = io.BytesIO(rest_body)
    handler.wfile = io.BytesIO()
    handler.headers = {"Content-Length": str(len(rest_body))}
    handler.path = "/api/tasks/submit"
    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None

    handler.do_POST()
    assert responses == [400]
    resp_data = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "rejects frontend/ui prefix" in resp_data["error"]


def test_backend_frozen_frontend_rejects_actual_frontend_and_ui_diff(tmp_path: Path):
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")

    # 1. Test rejection when actual diff touches src/frontend/
    rec = BridgeTaskRecord(
        task_id="TASK-DIFF-FE",
        prompt="test",
        base_sha="1" * 40,
        target_branch="product/diff-fe",
        allowed_prefixes=["src/mke_product/coverage/"],
        commit_message="feat: test",
        timeout_seconds=900,
        validation_profile="backend_frozen_frontend",
    )
    worker.tasks[rec.task_id] = rec

    with mock.patch("bridge.worker.git"), \
         mock.patch("bridge.worker.find_agy", return_value="agy"), \
         mock.patch("bridge.worker.run_cmd", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")), \
         mock.patch("bridge.worker.collect_changed_files", return_value=["src/mke_product/coverage/test.py", "src/frontend/App.tsx"]):
        worker._execute_task(rec)

    assert rec.status == TaskStatus.FAILED
    assert "Frontend freeze violation" in rec.error
    assert "src/frontend/App.tsx" in rec.error

    # 2. Test rejection when actual diff touches ui/
    rec_ui = BridgeTaskRecord(
        task_id="TASK-DIFF-UI",
        prompt="test",
        base_sha="2" * 40,
        target_branch="product/diff-ui",
        allowed_prefixes=["src/mke_product/coverage/"],
        commit_message="feat: test",
        timeout_seconds=900,
        validation_profile="backend_frozen_frontend",
    )
    worker.tasks[rec_ui.task_id] = rec_ui

    with mock.patch("bridge.worker.git"), \
         mock.patch("bridge.worker.find_agy", return_value="agy"), \
         mock.patch("bridge.worker.run_cmd", return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")), \
         mock.patch("bridge.worker.collect_changed_files", return_value=["ui/index.html"]):
        worker._execute_task(rec_ui)

    assert rec_ui.status == TaskStatus.FAILED
    assert "Frontend freeze violation" in rec_ui.error
    assert "ui/index.html" in rec_ui.error


def test_backend_profile_does_not_call_prepare_frontend_and_invokes_exact_command(tmp_path: Path):
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")

    rec = BridgeTaskRecord(
        task_id="TASK-BACKEND-PASS",
        prompt="backend product task",
        base_sha="3" * 40,
        target_branch="product/backend-task",
        allowed_prefixes=["src/mke_product/coverage/", "tests/test_thpt_cov_"],
        commit_message="feat(coverage): backend only",
        timeout_seconds=900,
        validation_profile="backend_frozen_frontend",
    )
    worker.tasks[rec.task_id] = rec

    commands_executed = []

    def fake_run_cmd(cmd, cwd, timeout=None, check=True):
        commands_executed.append((list(cmd), Path(cwd)))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="12 backend tests passed\n", stderr="")

    def fake_git(cwd, *args, **kwargs):
        if args and args[0] == "rev-parse":
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="c" * 40 + "\n", stderr="")
        if args and args[0] == "diff" and "--cached" in args:
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="src/mke_product/coverage/math.py\n", stderr="")
        return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

    with mock.patch("bridge.worker.git", side_effect=fake_git), \
         mock.patch("bridge.worker.find_agy", return_value="agy"), \
         mock.patch("bridge.worker.prepare_frontend") as mock_prep, \
         mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd), \
         mock.patch("bridge.worker.collect_changed_files", return_value=["src/mke_product/coverage/math.py"]), \
         mock.patch("bridge.worker.cleanup_test_side_effects", return_value=["src/mke_product/coverage/math.py"]):
        worker._execute_task(rec)

    # 1. prepare_frontend must NOT be called
    mock_prep.assert_not_called()

    # 2. Task must succeed
    assert rec.status == TaskStatus.SUCCESS
    assert rec.commit_sha == "c" * 40

    # 3. Exact regression command with the two ignores must be executed
    expected_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-q",
        "--ignore=tests/test_mvp_v1_product_app.py",
        "--ignore=tests/test_mvp_v1_react_e2e.py",
    ]
    pytest_calls = [c[0] for c in commands_executed if "-m" in c[0] and "pytest" in c[0]]
    assert len(pytest_calls) == 1
    assert pytest_calls[0] == expected_cmd

    # 4. Marker must be present in test_output_tail
    assert "[validation_profile: backend_frozen_frontend]" in rec.test_output_tail
    assert "12 backend tests passed" in rec.test_output_tail


def test_auto_product_profile_calls_frontend_prep_and_full_tests(tmp_path: Path):
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")

    rec = BridgeTaskRecord(
        task_id="TASK-AUTO-PRODUCT",
        prompt="auto product task",
        base_sha="4" * 40,
        target_branch="product/auto-task",
        allowed_prefixes=["src/mke_product/coverage/", "tests/test_thpt_cov_"],
        commit_message="feat(coverage): auto product",
        timeout_seconds=900,
        validation_profile="auto",
    )
    worker.tasks[rec.task_id] = rec

    commands_executed = []

    def fake_run_cmd(cmd, cwd, timeout=None, check=True):
        commands_executed.append((list(cmd), Path(cwd)))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="all tests passed\n", stderr="")

    def fake_git(cwd, *args, **kwargs):
        if args and args[0] == "rev-parse":
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="d" * 40 + "\n", stderr="")
        if args and args[0] == "diff" and "--cached" in args:
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="src/mke_product/coverage/algo.py\n", stderr="")
        return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

    with mock.patch("bridge.worker.git", side_effect=fake_git), \
         mock.patch("bridge.worker.find_agy", return_value="agy"), \
         mock.patch("bridge.worker.prepare_frontend", return_value="mock frontend build tail") as mock_prep, \
         mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd), \
         mock.patch("bridge.worker.collect_changed_files", return_value=["src/mke_product/coverage/algo.py"]), \
         mock.patch("bridge.worker.cleanup_test_side_effects", return_value=["src/mke_product/coverage/algo.py"]):
        worker._execute_task(rec)

    # 1. prepare_frontend MUST be called for auto product task
    mock_prep.assert_called_once()

    # 2. Pytest command must be full tests without ignores
    expected_full_cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
    pytest_calls = [c[0] for c in commands_executed if "-m" in c[0] and "pytest" in c[0]]
    assert len(pytest_calls) == 1
    assert pytest_calls[0] == expected_full_cmd

    # 3. Status is SUCCESS and frontend prep tail is in test_output_tail
    assert rec.status == TaskStatus.SUCCESS
    assert "[frontend-prepare]" in rec.test_output_tail
    assert "mock frontend build tail" in rec.test_output_tail


def test_control_plane_profile_remains_unchanged(tmp_path: Path):
    worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")

    rec = BridgeTaskRecord(
        task_id="TASK-CONTROL-PLANE",
        prompt="control plane task",
        base_sha="5" * 40,
        target_branch="automation/test-cp",
        allowed_prefixes=[".mke-agent/"],
        commit_message="chore(agent): control plane",
        timeout_seconds=900,
        validation_profile="auto",
    )
    worker.tasks[rec.task_id] = rec

    commands_executed = []

    def fake_run_cmd(cmd, cwd, timeout=None, check=True):
        commands_executed.append((list(cmd), Path(cwd)))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="control plane tests passed\n", stderr="")

    def fake_git(cwd, *args, **kwargs):
        if args and args[0] == "rev-parse":
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="e" * 40 + "\n", stderr="")
        if args and args[0] == "diff" and "--cached" in args:
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout=".mke-agent/bridge/models.py\n", stderr="")
        return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

    with mock.patch("bridge.worker.git", side_effect=fake_git), \
         mock.patch("bridge.worker.find_agy", return_value="agy"), \
         mock.patch("bridge.worker.prepare_frontend") as mock_prep, \
         mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd), \
         mock.patch("bridge.worker.collect_changed_files", return_value=[".mke-agent/bridge/models.py"]), \
         mock.patch("bridge.worker.cleanup_test_side_effects", return_value=[".mke-agent/bridge/models.py"]):
        worker._execute_task(rec)

    # 1. prepare_frontend must NOT be called for control-plane
    mock_prep.assert_not_called()

    # 2. Pytest command must target .mke-agent/tests
    expected_cp_cmd = [sys.executable, "-m", "pytest", ".mke-agent/tests", "-q"]
    pytest_calls = [c[0] for c in commands_executed if "-m" in c[0] and "pytest" in c[0]]
    assert len(pytest_calls) == 1
    assert pytest_calls[0] == expected_cp_cmd
    assert rec.status == TaskStatus.SUCCESS


def test_invalid_validation_profile_fails_closed(tmp_path: Path):
    # 1. BridgeTaskRequest rejects invalid profile
    with pytest.raises(ValueError, match="Invalid validation_profile"):
        BridgeTaskRequest(
            task_id="TASK-INVALID-1",
            prompt="test",
            base_sha="a" * 40,
            target_branch="product/test",
            validation_profile="unsupported_profile",
        )

    # 2. BridgeTaskRecord rejects invalid profile
    with pytest.raises(ValueError, match="Invalid validation_profile"):
        BridgeTaskRecord(
            task_id="TASK-INVALID-2",
            prompt="test",
            base_sha="a" * 40,
            target_branch="product/test",
            allowed_prefixes=["src/"],
            commit_message="test",
            timeout_seconds=900,
            validation_profile="invalid_profile",
        )

    # 3. from_dict rejects invalid profile
    with pytest.raises(ValueError, match="Invalid validation_profile"):
        BridgeTaskRecord.from_dict({
            "task_id": "TASK-INVALID-3",
            "prompt": "test",
            "base_sha": "a" * 40,
            "target_branch": "product/test",
            "allowed_prefixes": ["src/"],
            "commit_message": "test",
            "timeout_seconds": 900,
            "validation_profile": "unsupported_xyz",
        })

    # 4. REST submit rejects invalid profile with 400
    import io
    worker = DummyWorker()
    handler_cls = create_handler_class(worker)
    rest_body = json.dumps({
        "task_id": "REST-INVALID-PROFILE",
        "prompt": "test",
        "base_sha": "a" * 40,
        "target_branch": "product/test",
        "validation_profile": "bad_profile",
    }).encode("utf-8")

    handler = handler_cls.__new__(handler_cls)
    handler.rfile = io.BytesIO(rest_body)
    handler.wfile = io.BytesIO()
    handler.headers = {"Content-Length": str(len(rest_body))}
    handler.path = "/api/tasks/submit"
    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None

    handler.do_POST()
    assert responses == [400]
    resp_data = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "Invalid validation_profile" in resp_data["error"]

    # 5. _execute_task fails closed if record somehow had unsupported profile
    real_worker = TaskWorker(tmp_path, tmp_path / "worktrees", state_dir=tmp_path / "state")
    rec = BridgeTaskRecord(
        task_id="TASK-EXEC-INVALID",
        prompt="test",
        base_sha="a" * 40,
        target_branch="product/test",
        allowed_prefixes=["src/"],
        commit_message="test",
        timeout_seconds=900,
    )
    object.__setattr__(rec, "validation_profile", "unsupported_profile_direct")
    real_worker.tasks[rec.task_id] = rec

    real_worker._execute_task(rec)
    assert rec.status == TaskStatus.FAILED
    assert "Unsupported validation_profile" in rec.error

