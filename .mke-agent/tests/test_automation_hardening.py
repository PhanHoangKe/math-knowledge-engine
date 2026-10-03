"""Focused tests for Windows npm resolution and audit environment classification."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1]))

import npm_resolver
from npm_resolver import NpmResolverError, resolve_npm as shared_resolve_npm
import runner
from runner import RunnerError
import orchestrator
from orchestrator import AuditError
from bridge.worker import WorkerError, find_npm, prepare_frontend, resolve_npm as worker_resolve_npm


def sample_task(status: str = "READY_FOR_AUDIT", attempt: int = 1) -> dict:
    return {
        "schema_version": "2.0",
        "state_version": 1,
        "task_id": "TEST-HARDEN-001",
        "attempt": attempt,
        "status": status,
        "base_sha": "a" * 40,
        "target_branch": "product/test-harden-001",
        "allowed_prefixes": ["src/mke_product/coverage/"],
        "prompt_path": ".mke-agent/prompts/test.md",
        "commit_message": "feat: test hardening",
        "result": {"commit_sha": "b" * 40, "status": "PASS"},
    }


def sample_policy() -> dict:
    return {
        "schema_version": "2.0",
        "control_branch": "automation/mke-agent-loop",
        "poll_seconds": 60,
        "agent_timeout_seconds": 3600,
        "test_timeout_seconds": 600,
        "max_attempts_before_owner": 3,
        "audit_run_independent_tests": True,
        "forbid_frontend_changes_by_default": True,
    }


class NpmResolutionTests(unittest.TestCase):
    def test_resolver_returns_full_npm_cmd_path_when_which_provides_it(self) -> None:
        cmd_path = r"C:\Program Files\nodejs\npm.cmd"
        with mock.patch("shutil.which", return_value=cmd_path):
            self.assertEqual(shared_resolve_npm(), os.path.abspath(cmd_path))
            self.assertEqual(worker_resolve_npm(), os.path.abspath(cmd_path))
            self.assertEqual(find_npm(), os.path.abspath(cmd_path))
            self.assertEqual(runner.resolve_npm(), os.path.abspath(cmd_path))
            self.assertEqual(orchestrator.resolve_npm(), os.path.abspath(cmd_path))

    def test_resolver_returns_full_npm_bat_path_when_cmd_missing(self) -> None:
        bat_path = r"C:\tools\npm.bat"

        def fake_which(name: str):
            if name in {"npm.bat"}:
                return bat_path
            return None

        with mock.patch("shutil.which", side_effect=fake_which):
            self.assertEqual(shared_resolve_npm(), os.path.abspath(bat_path))
            self.assertEqual(worker_resolve_npm(), os.path.abspath(bat_path))
            self.assertEqual(runner.resolve_npm(), os.path.abspath(bat_path))
            self.assertEqual(orchestrator.resolve_npm(), os.path.abspath(bat_path))

    def test_resolver_fails_closed_with_specific_errors_when_no_executable(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(NpmResolverError):
                shared_resolve_npm()
            with self.assertRaises(WorkerError):
                worker_resolve_npm()
            with self.assertRaises(RunnerError):
                runner.resolve_npm()
            with self.assertRaises(AuditError):
                orchestrator.resolve_npm()

    def test_worker_and_runner_subprocess_calls_use_resolved_path_not_literal_npm(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"
        with tempfile.TemporaryDirectory() as td:
            worktree = Path(td)
            fe_dir = worktree / "src" / "frontend"
            fe_dir.mkdir(parents=True)
            (fe_dir / "package-lock.json").write_text("{}", encoding="utf-8")

            # 1. worker.prepare_frontend
            worker_cmds = []

            def fake_run_cmd(cmd, cwd, timeout=None, check=True):
                worker_cmds.append(list(cmd))
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch("bridge.worker.run_cmd", side_effect=fake_run_cmd):
                prepare_frontend(worktree)

            self.assertEqual(len(worker_cmds), 2)
            self.assertEqual(worker_cmds[0], [cmd_path, "ci"])
            self.assertEqual(worker_cmds[1], [cmd_path, "run", "build"])
            self.assertNotIn("npm", [c[0] for c in worker_cmds])

            # 2. runner.ensure_frontend_dist
            runner_cmds = []

            def fake_runner_run(cmd, cwd, timeout=None, check=True):
                runner_cmds.append(list(cmd))
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch("runner.run", side_effect=fake_runner_run):
                runner.ensure_frontend_dist(worktree, timeout=60)

            self.assertEqual(len(runner_cmds), 2)
            self.assertEqual(runner_cmds[0], [cmd_path, "ci"])
            self.assertEqual(runner_cmds[1], [cmd_path, "run", "build"])
            self.assertNotIn("npm", [c[0] for c in runner_cmds])

    def test_runner_npm_ci_then_run_build_ordering_and_fail_closed(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"
        with tempfile.TemporaryDirectory() as td:
            worktree = Path(td)
            fe_dir = worktree / "src" / "frontend"
            fe_dir.mkdir(parents=True)
            (fe_dir / "package-lock.json").write_text("{}", encoding="utf-8")

            call_order = []

            def fake_failing_ci(cmd, cwd, timeout=None, check=True):
                call_order.append(cmd[1])
                if cmd[1] == "ci":
                    raise RunnerError("npm ci failed (1)")
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch("runner.run", side_effect=fake_failing_ci):
                with self.assertRaises(RunnerError) as ctx:
                    runner.ensure_frontend_dist(worktree, timeout=60)
                self.assertIn("npm ci failed", str(ctx.exception))

            # run build must never have been called
            self.assertEqual(call_order, ["ci"])


class OrchestratorAuditHardeningTests(unittest.TestCase):
    def test_clean_audit_runs_frontend_prep_before_pytest_when_lockfile_exists(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"
        commands_executed = []

        def fake_git(cwd, *args, **kwargs):
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            commands_executed.append((list(cmd), Path(cwd)))
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="out ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            def fake_git_add(cwd, *args, **kwargs):
                if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                    wt = Path(args[3])
                    fe = wt / "src" / "frontend"
                    fe.mkdir(parents=True)
                    (fe / "package-lock.json").write_text("{}", encoding="utf-8")
                return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertTrue(res["passed"])
            self.assertIsNone(res["classification"])
            self.assertTrue(res["frontend_preparation"]["performed"])
            self.assertTrue(res["frontend_preparation"]["passed"])
            self.assertTrue(res["pytest_evidence"]["performed"])
            self.assertTrue(res["pytest_evidence"]["passed"])

            # Verify command execution sequence: [npm.cmd, ci] -> [npm.cmd, run, build] -> pytest
            self.assertEqual(len(commands_executed), 3)
            self.assertEqual(commands_executed[0][0], [cmd_path, "ci"])
            self.assertEqual(commands_executed[1][0], [cmd_path, "run", "build"])
            self.assertEqual(commands_executed[2][0], [sys.executable, "-m", "pytest", "tests/", "-q"])

    def test_clean_audit_skips_frontend_prep_when_no_lockfile(self) -> None:
        commands_executed = []

        def fake_git_no_lock(cwd, *args, **kwargs):
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            commands_executed.append(list(cmd))
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="pytest ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch.object(orchestrator, "git", side_effect=fake_git_no_lock), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertTrue(res["passed"])
            self.assertFalse(res["frontend_preparation"]["performed"])
            self.assertEqual(len(commands_executed), 1)
            self.assertEqual(commands_executed[0], [sys.executable, "-m", "pytest", "tests/", "-q"])

    def test_missing_npm_classified_as_audit_environment_failure(self) -> None:
        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=None), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertTrue(res["frontend_preparation"]["performed"])
            self.assertFalse(res["frontend_preparation"]["passed"])
            self.assertFalse(res["pytest_evidence"]["performed"])
            self.assertIn("npm is required", res["frontend_preparation"]["error"])

    def test_npm_ci_failure_classified_as_audit_environment_failure(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            if cmd[1] == "ci":
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="npm ci ERESOLVE")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertIn("npm ci failed (1)", res["error"])
            self.assertFalse(res["pytest_evidence"]["performed"])

    def test_pytest_failure_after_successful_prep_remains_product_regression(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            if "pytest" in cmd:
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="1 failed in test_core.py", stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="build ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "PRODUCT_REGRESSION")
            self.assertTrue(res["frontend_preparation"]["passed"])
            self.assertTrue(res["pytest_evidence"]["performed"])
            self.assertFalse(res["pytest_evidence"]["passed"])
            self.assertIn("1 failed", res["pytest_evidence"]["output_tail"])

    def test_process_event_audit_environment_failure_blocks_fail_closed_without_remediate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            control = Path(td) / "control"
            repo = Path(td) / "repo"
            control.mkdir()
            repo.mkdir()

            t = sample_task("READY_FOR_AUDIT", attempt=1)
            orchestrator.write_json(control / orchestrator.TASK_REL, t)
            orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
            mock_gates = {"passed": True, "failures": [], "changed_files": ["src/mke_product/coverage/c.py"]}
            mock_tests = {
                "passed": False,
                "returncode": -1,
                "classification": "AUDIT_ENVIRONMENT_FAILURE",
                "error": "npm is required for independent frontend preparation but was not found on PATH.",
                "frontend_preparation": {"performed": True, "passed": False},
                "pytest_evidence": {"performed": False},
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_tests), \
                 mock.patch.object(orchestrator, "call_openai") as mock_openai:
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            mock_openai.assert_not_called()

            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Fail closed: must be BLOCKED, attempt must NOT increment, must NOT yield ACCEPT
            self.assertEqual(updated["status"], "BLOCKED")
            self.assertEqual(updated["attempt"], 1)
            self.assertIn("Audit environment failure", updated["blocked_reason"])
            # History record must record audit environment classification
            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertEqual(history["decision"]["decision"], "BLOCKED")

    def test_process_event_runner_infrastructure_failure_blocks_fail_closed_without_remediate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            control = Path(td) / "control"
            repo = Path(td) / "repo"
            control.mkdir()
            repo.mkdir()

            t = sample_task("BLOCKED", attempt=1)
            t["result"] = {
                "task_id": "TEST-HARDEN-001",
                "attempt": 1,
                "status": "BLOCKED",
                "stage": "frontend-baseline-build",
                "error": "npm is required for full regression but was not found on PATH.",
            }
            orchestrator.write_json(control / orchestrator.TASK_REL, t)
            orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git):
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Must remain BLOCKED, attempt must NOT increment to 2, must NOT convert to product REMEDIATE
            self.assertEqual(updated["status"], "BLOCKED")
            self.assertEqual(updated["attempt"], 1)
            self.assertIn("Infrastructure failure at frontend-baseline-build", updated["blocked_reason"])

    def test_process_event_product_regression_generates_remediate_and_increments_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            control = Path(td) / "control"
            repo = Path(td) / "repo"
            control.mkdir()
            repo.mkdir()

            t = sample_task("READY_FOR_AUDIT", attempt=1)
            orchestrator.write_json(control / orchestrator.TASK_REL, t)
            orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
            mock_gates = {"passed": True, "failures": [], "changed_files": ["src/mke_product/coverage/c.py"]}
            mock_tests = {
                "passed": False,
                "returncode": 1,
                "classification": "PRODUCT_REGRESSION",
                "error": "product pytest regression failed (1)",
                "frontend_preparation": {"performed": True, "passed": True},
                "pytest_evidence": {"performed": True, "passed": False},
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_tests):
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Product regression must transition to READY with attempt 2 for remediation
            self.assertEqual(updated["status"], "READY")
            self.assertEqual(updated["attempt"], 2)
            self.assertTrue(updated["target_branch"].endswith("-r1-remediation"))
            self.assertTrue((control / updated["prompt_path"]).is_file())

    def test_fail_closed_no_accept_on_incomplete_validation(self) -> None:
        fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
        mock_gates = {"passed": True, "failures": [], "changed_files": ["src/mke_product/coverage/c.py"]}

        # 1. Incomplete/failing validation must NEVER yield ACCEPT or invoke OpenAI
        for idx, incomplete_tests in enumerate([
            {"passed": False, "classification": "AUDIT_ENVIRONMENT_FAILURE", "error": "tooling missing"},
            {"passed": False, "classification": "PRODUCT_REGRESSION", "error": "pytest failed"},
            {"passed": False, "classification": None, "error": "unknown failure"},
        ]):
            with tempfile.TemporaryDirectory() as td:
                control = Path(td) / "control"
                repo = Path(td) / "repo"
                control.mkdir()
                repo.mkdir()

                t = sample_task("READY_FOR_AUDIT", attempt=1)
                t["task_id"] = f"TEST-INCOMPLETE-{idx}"
                orchestrator.write_json(control / orchestrator.TASK_REL, t)
                orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

                with mock.patch.object(orchestrator, "sync_control"), \
                     mock.patch.object(orchestrator, "git", return_value=fake_git), \
                     mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                     mock.patch.object(orchestrator, "independent_tests", return_value=incomplete_tests), \
                     mock.patch.object(orchestrator, "call_openai") as mock_openai, \
                     mock.patch.object(orchestrator, "apply_decision") as mock_apply:
                    orchestrator.process_event(repo, control)
                    mock_openai.assert_not_called()
                    applied_decision = mock_apply.call_args[0][2]["decision"]
                    self.assertNotEqual(applied_decision, "ACCEPT")

        # 2. Even if gates failed, independent tests and OpenAI are never invoked
        bad_gates = {"passed": False, "failures": ["scope violation: src/bad.py"], "changed_files": ["src/bad.py"]}
        with tempfile.TemporaryDirectory() as td:
            control = Path(td) / "control"
            repo = Path(td) / "repo"
            control.mkdir()
            repo.mkdir()

            t = sample_task("READY_FOR_AUDIT", attempt=1)
            t["task_id"] = "TEST-BAD-GATES"
            orchestrator.write_json(control / orchestrator.TASK_REL, t)
            orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=bad_gates), \
                 mock.patch.object(orchestrator, "independent_tests") as mock_indep, \
                 mock.patch.object(orchestrator, "call_openai") as mock_openai, \
                 mock.patch.object(orchestrator, "apply_decision") as mock_apply:
                orchestrator.process_event(repo, control)
                mock_indep.assert_not_called()
                mock_openai.assert_not_called()
                applied_decision = mock_apply.call_args[0][2]["decision"]
                self.assertEqual(applied_decision, "REMEDIATE")


if __name__ == "__main__":
    unittest.main()

