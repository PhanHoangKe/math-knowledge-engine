from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "orchestrator.py"
SPEC = importlib.util.spec_from_file_location("mke_orchestrator", MODULE_PATH)
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


def task(status: str = "READY_FOR_AUDIT") -> dict:
    return {
        "task_id": "THPT-COV-P1-001",
        "attempt": 1,
        "status": status,
        "base_sha": "a" * 40,
        "target_branch": "product/thpt-cov-p1-universal-core",
        "allowed_prefixes": ["src/mke_product/coverage/", "tests/test_thpt_cov_p1_"],
        "result": {"commit_sha": "b" * 40},
    }


class OrchestratorTests(unittest.TestCase):
    def test_event_id_is_stable_and_attempt_sensitive(self) -> None:
        first = task()
        self.assertEqual(orchestrator.event_id(first), orchestrator.event_id(dict(first)))
        second = task()
        second["attempt"] = 2
        self.assertNotEqual(orchestrator.event_id(first), orchestrator.event_id(second))

    def test_scope_prefix_is_fail_closed(self) -> None:
        prefixes = task()["allowed_prefixes"]
        self.assertTrue(orchestrator.allowed_path("src/mke_product/coverage/contracts.py", prefixes))
        self.assertFalse(orchestrator.allowed_path("src/frontend/src/App.tsx", prefixes))
        self.assertFalse(orchestrator.allowed_path("src/mke_product/parser/parser.py", prefixes))

    def test_remediation_branch_is_monotonic(self) -> None:
        original = "product/thpt-cov-p1-universal-core"
        r1 = orchestrator.next_remediation_branch(original, 1)
        self.assertTrue(r1.endswith("-r1-remediation"))
        self.assertTrue(orchestrator.next_remediation_branch(r1, 2).endswith("-r2-remediation"))

    def test_remediation_prompt_preserves_trust_and_frontend_freeze(self) -> None:
        decision = {"findings": [{"severity": "high", "location": "contracts.py",
                                   "problem": "candidate is trusted early", "required_fix": "verify first"}]}
        prompt = orchestrator.remediation_prompt(task(), decision, "event")
        self.assertIn("only MKE verification grants trust", prompt)
        self.assertIn("Do not modify frontend", prompt)
        self.assertIn("contracts.py", prompt)

    def test_structured_decision_schema_is_closed(self) -> None:
        schema = orchestrator.DECISION_SCHEMA
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["decision"]["enum"], ["ACCEPT", "REMEDIATE"])
        self.assertFalse(schema["properties"]["findings"]["items"]["additionalProperties"])

    def test_accept_promotes_only_preapproved_queue_task(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            control = Path(raw)
            current = task()
            current["state_version"] = 7
            orchestrator.write_json(control / orchestrator.TASK_REL, current)
            queued = {"tasks": [{"task_id": "NEXT-001", "status": "PENDING",
                                  "base_sha": "$ACCEPTED_COMMIT", "target_branch": "product/next-001",
                                  "prompt_path": ".mke-agent/prompts/next.md", "commit_message": "test: next",
                                  "allowed_prefixes": ["tests/test_next_"]}]}
            orchestrator.write_json(control / orchestrator.QUEUE_REL, queued)
            decision = {"decision": "ACCEPT", "summary": "ok", "findings": [],
                        "trust_boundary_preserved": True, "frontend_freeze_preserved": True}
            record = {"event_id": "c" * 64}
            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
            with mock.patch.object(orchestrator, "sync_control"), mock.patch.object(orchestrator, "git", return_value=fake_git):
                orchestrator.apply_decision(control, current, decision, record, {"max_attempts_before_owner": 3})
            active = orchestrator.read_json(control / orchestrator.TASK_REL)
            self.assertEqual(active["task_id"], "NEXT-001")
            self.assertEqual(active["status"], "READY")
            self.assertEqual(active["base_sha"], "b" * 40)

    def test_third_failed_attempt_escalates_to_owner(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            control = Path(raw)
            current = task()
            current.update({"attempt": 3, "state_version": 9})
            orchestrator.write_json(control / orchestrator.TASK_REL, current)
            orchestrator.write_json(control / orchestrator.QUEUE_REL, {"tasks": []})
            decision = {"decision": "REMEDIATE", "summary": "defect", "findings": [],
                        "trust_boundary_preserved": True, "frontend_freeze_preserved": True}
            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
            with mock.patch.object(orchestrator, "sync_control"), mock.patch.object(orchestrator, "git", return_value=fake_git):
                orchestrator.apply_decision(control, current, decision, {"event_id": "d" * 64},
                                            {"max_attempts_before_owner": 3})
            active = orchestrator.read_json(control / orchestrator.TASK_REL)
            self.assertEqual(active["status"], "OWNER_REQUIRED")
            self.assertEqual(active["attempt"], 3)


if __name__ == "__main__":
    unittest.main()
