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
