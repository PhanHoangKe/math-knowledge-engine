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
