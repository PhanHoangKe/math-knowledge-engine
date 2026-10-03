"""Unit tests for MKE Antigravity Bridge."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.models import BridgeTaskRecord, BridgeTaskRequest, TaskStatus
from bridge.server import MCP_TOOLS_SPEC, create_handler_class, handle_mcp_call
from bridge.worker import TaskWorker


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
