"""Data models and state definitions for MKE Antigravity Bridge."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


@dataclass
class BridgeTaskRequest:
    task_id: str
    prompt: str
    base_sha: str
    target_branch: str
    allowed_prefixes: List[str] = field(default_factory=lambda: ["src/mke_product/coverage/", "tests/test_thpt_cov_"])
    commit_message: str = ""
    timeout_seconds: int = 900
    callback_url: Optional[str] = None


@dataclass
class BridgeTaskRecord:
    task_id: str
    prompt: str
    base_sha: str
    target_branch: str
    allowed_prefixes: List[str]
    commit_message: str
    timeout_seconds: int
    status: TaskStatus = TaskStatus.QUEUED
    created_at: str = field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    commit_sha: Optional[str] = None
    stage: str = "init"
    error: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)
    agent_output_tail: str = ""
    test_output_tail: str = ""
    callback_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BridgeTaskRecord:
        if not isinstance(data, dict):
            raise ValueError(f"Task record data must be a dict, got {type(data).__name__}")
        if "task_id" not in data:
            raise KeyError("Missing required field 'task_id'")

        raw_status = data.get("status", TaskStatus.QUEUED.value)
        if isinstance(raw_status, TaskStatus):
            status = raw_status
        elif isinstance(raw_status, str):
            status = TaskStatus(raw_status)
        else:
            raise ValueError(f"Invalid status value: {raw_status}")

        return cls(
            task_id=str(data["task_id"]),
            prompt=str(data.get("prompt", "")),
            base_sha=str(data.get("base_sha", "")),
            target_branch=str(data.get("target_branch", "")),
            allowed_prefixes=list(data.get("allowed_prefixes") or []),
            commit_message=str(data.get("commit_message", "")),
            timeout_seconds=int(data.get("timeout_seconds", 900)),
            status=status,
            created_at=str(data.get("created_at") or utc_now_iso()),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            commit_sha=data.get("commit_sha"),
            stage=str(data.get("stage", "init")),
            error=data.get("error"),
            changed_files=list(data.get("changed_files") or []),
            agent_output_tail=str(data.get("agent_output_tail") or ""),
            test_output_tail=str(data.get("test_output_tail") or ""),
            callback_url=data.get("callback_url"),
        )
