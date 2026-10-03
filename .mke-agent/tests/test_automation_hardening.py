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

    def test_npm_run_build_launch_exception_classified_as_audit_environment_failure(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            if len(cmd) >= 3 and cmd[1] == "run" and cmd[2] == "build":
                raise OSError("Tool execution launch error: [WinError 193] %1 is not a valid Win32 application")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ci ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertIn("npm run build execution error", res["error"])
            self.assertFalse(res["pytest_evidence"]["performed"])

    def test_npm_ci_launch_exception_classified_as_audit_environment_failure(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            if len(cmd) >= 2 and cmd[1] == "ci":
                raise FileNotFoundError("npm binary not found at launch")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ci ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertIn("npm ci execution error", res["error"])
            self.assertFalse(res["pytest_evidence"]["performed"])

    def test_npm_run_build_tooling_infrastructure_failure_classified_as_audit_environment_failure(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        tooling_outputs = [
            ("npm ERR! missing script: build\n", 1),
            ("'tsc' is not recognized as an internal or external command,\noperable program or batch file.\n", 1),
            ("sh: 1: tsc: not found\n", 127),
            ("npm ERR! code ENOENT\nnpm ERR! syscall spawn tsc\n", 1),
        ]

        for out_text, ret_code in tooling_outputs:
            def fake_run(cmd, cwd, timeout=300, check=True, text=out_text, code=ret_code):
                if len(cmd) >= 3 and cmd[1] == "run" and cmd[2] == "build":
                    return subprocess.CompletedProcess(args=cmd, returncode=code, stdout="", stderr=text)
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ci ok", stderr="")

            with tempfile.TemporaryDirectory() as td:
                repo = Path(td) / "repo"
                repo.mkdir()

                with mock.patch("shutil.which", return_value=cmd_path), \
                     mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                     mock.patch.object(orchestrator, "run", side_effect=fake_run):
                    res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

                self.assertFalse(res["passed"])
                self.assertEqual(res["classification"], "AUDIT_ENVIRONMENT_FAILURE")
                self.assertFalse(res["pytest_evidence"]["performed"])

    def test_npm_run_build_returns_2_with_tsc_diagnostics_is_product_build_regression(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"
        commands_executed = []

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        tsc_output = (
            "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "src/App.tsx:20:10 - error TS2304: Cannot find name 'badIdentifier'.\n"
            "Found 2 errors in 2 files.\n"
        )

        def fake_run(cmd, cwd, timeout=300, check=True):
            commands_executed.append(list(cmd))
            if len(cmd) >= 3 and cmd[1] == "run" and cmd[2] == "build":
                return subprocess.CompletedProcess(args=cmd, returncode=2, stdout="", stderr=tsc_output)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ci ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.independent_tests(repo, "b" * 40, timeout=120)

            self.assertFalse(res["passed"])
            self.assertEqual(res["classification"], "PRODUCT_BUILD_REGRESSION")
            self.assertEqual(res["returncode"], 2)
            self.assertFalse(res["frontend_preparation"]["passed"])
            self.assertIn("error TS2322", res["frontend_output_tail"])

            # Verify pytest was NOT executed
            self.assertFalse(res["pytest_evidence"]["performed"])
            executed_command_names = [c[0] for c in commands_executed]
            self.assertNotIn(sys.executable, executed_command_names)
            for c in commands_executed:
                self.assertNotIn("pytest", c)

    def test_process_event_maps_product_build_regression_to_remediate_not_blocked(self) -> None:
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
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_preparation": {
                    "performed": True,
                    "passed": False,
                    "error": "frontend build regression (2)",
                    "output_tail": "error TS2322: Type 'string' is not assignable to type 'number'.",
                },
                "pytest_evidence": {
                    "performed": False,
                    "passed": False,
                    "returncode": None,
                    "output_tail": "pytest was not executed because frontend preparation failed",
                },
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
            # Must map to REMEDIATE: status READY, attempt 2, new remediation branch, remediation prompt exists
            self.assertEqual(updated["status"], "READY")
            self.assertEqual(updated["attempt"], 2)
            self.assertTrue(updated["target_branch"].endswith("-r1-remediation"))
            self.assertTrue((control / updated["prompt_path"]).is_file())

            # Verify history record
            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "PRODUCT_BUILD_REGRESSION")
            self.assertEqual(history["decision"]["decision"], "REMEDIATE")
            self.assertTrue(history["decision"]["frontend_freeze_preserved"])

    def test_classify_frontend_build_failure_patterns_and_fallbacks(self) -> None:
        classify = orchestrator.classify_frontend_build_failure

        # 1. Source / compiler diagnostics => PRODUCT_BUILD_REGRESSION
        self.assertEqual(
            classify("src/index.ts:1:1 error TS2304: Cannot find name 'x'", "", 2),
            "PRODUCT_BUILD_REGRESSION",
        )
        self.assertEqual(
            classify("", "Found 1 error in src/index.ts:1", 2),
            "PRODUCT_BUILD_REGRESSION",
        )
        self.assertEqual(
            classify("Rollup failed to resolve import 'missing' from 'src/main.ts'", "", 1),
            "PRODUCT_BUILD_REGRESSION",
        )
        self.assertEqual(
            classify("Module not found: Can't resolve './file'", "", 1),
            "PRODUCT_BUILD_REGRESSION",
        )
        self.assertEqual(
            classify("SyntaxError: Unexpected token", "", 1),
            "PRODUCT_BUILD_REGRESSION",
        )

        # 2. Exit code 2 (tsc error) even without matching message => PRODUCT_BUILD_REGRESSION
        self.assertEqual(classify("", "", 2), "PRODUCT_BUILD_REGRESSION")

        # 3. Tooling / infrastructure failure patterns => AUDIT_ENVIRONMENT_FAILURE
        self.assertEqual(
            classify("", "npm ERR! missing script: build", 1),
            "AUDIT_ENVIRONMENT_FAILURE",
        )
        self.assertEqual(
            classify("", "'tsc' is not recognized as an internal or external command", 1),
            "AUDIT_ENVIRONMENT_FAILURE",
        )
        self.assertEqual(
            classify("", "sh: 1: tsc: not found", 127),
            "AUDIT_ENVIRONMENT_FAILURE",
        )
        self.assertEqual(
            classify("", "npm ERR! code ENOENT\nspawn tsc ENOENT", 1),
            "AUDIT_ENVIRONMENT_FAILURE",
        )
        self.assertEqual(
            classify("", "npm ERR! code EACCES", 1),
            "AUDIT_ENVIRONMENT_FAILURE",
        )

        # 4. Standard shell error exit codes => AUDIT_ENVIRONMENT_FAILURE
        self.assertEqual(classify("", "", 127), "AUDIT_ENVIRONMENT_FAILURE")
        self.assertEqual(classify("", "", 126), "AUDIT_ENVIRONMENT_FAILURE")
        self.assertEqual(classify("", "", -9), "AUDIT_ENVIRONMENT_FAILURE")

    def test_fail_closed_no_accept_on_incomplete_validation(self) -> None:
        fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
        mock_gates = {"passed": True, "failures": [], "changed_files": ["src/mke_product/coverage/c.py"]}

        # 1. Incomplete/failing validation must NEVER yield ACCEPT or invoke OpenAI
        for idx, incomplete_tests in enumerate([
            {"passed": False, "classification": "AUDIT_ENVIRONMENT_FAILURE", "error": "tooling missing"},
            {"passed": False, "classification": "PRODUCT_REGRESSION", "error": "pytest failed"},
            {"passed": False, "classification": "PRODUCT_BUILD_REGRESSION", "error": "frontend build regression"},
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


class BaselineAttributionTests(unittest.TestCase):
    def test_diagnostics_normalization_deduplicates_windows_and_timestamps_to_exact_count(self) -> None:
        """Focused test for Task 013 retry: ensure 2 Windows/timestamp diagnostics yield exactly 2 signatures."""
        raw = (
            "[10:00:00 AM] C:\\repo\\worktree\\src\\frontend\\src\\index.ts(14,5): error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "[10:00:00 AM] C:\\repo\\worktree\\src\\frontend\\src\\App.tsx(20,10): error TS2304: Cannot find name 'badIdentifier'.\n"
            "Found 2 errors in 2 files.\n"
        )
        sigs = orchestrator.normalize_diagnostics(raw)
        self.assertEqual(len(sigs), 2, f"Expected exactly 2 signatures, got {len(sigs)}: {sigs}")
        self.assertEqual(sigs[0], "src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'.")
        self.assertEqual(sigs[1], "src/App.tsx: error TS2304: Cannot find name 'badIdentifier'.")
        self.assertNotIn("Found 2 errors in 2 files.", sigs)

    def test_diagnostics_normalization_canonicalizes_windows_unix_colon_and_parentheses_identically(self) -> None:
        expected = "src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'."
        variants = [
            # Windows parenthesized with timestamp and drive
            r"[12:00:00 PM] C:\worktree\src\frontend\src\index.ts(14,5): error TS2322: Type 'string' is not assignable to type 'number'.",
            # Unix colon format without timestamp
            "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.",
            # Relative with src/frontend and colon
            "src/frontend/src/index.ts:14:5: error TS2322: Type 'string' is not assignable to type 'number'.",
            # Windows relative with backslashes and parentheses
            r"src\index.ts(14,5): error TS2322: Type 'string' is not assignable to type 'number'.",
            # Unix with ISO timestamp
            "2026-10-04T00:43:06.123Z [ERROR] src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.",
        ]
        for variant in variants:
            sigs = orchestrator.normalize_diagnostics(variant)
            self.assertEqual(len(sigs), 1, f"Expected 1 signature for '{variant}', got {len(sigs)}: {sigs}")
            self.assertEqual(sigs[0], expected, f"Variant '{variant}' did not match canonical signature")

    def test_generic_fallback_skips_primary_lines_and_uses_same_canonical_path(self) -> None:
        raw = (
            "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
            '[plugin:vite:resolve] Failed to resolve import "missing" from "src/frontend/src/App.tsx". Does the file exist?\n'
            "Found 1 error in 1 file.\n"
        )
        sigs = orchestrator.normalize_diagnostics(raw)
        self.assertEqual(len(sigs), 2, f"Expected exactly 2 signatures, got {len(sigs)}: {sigs}")
        self.assertEqual(sigs[0], "src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'.")
        self.assertTrue(sigs[1].startswith("src/App.tsx:"), f"Expected canonical path src/App.tsx, got {sigs[1]}")
        self.assertNotIn("src/frontend/src/App.tsx", sigs[1])

    def test_summary_lines_ignored_when_specific_diagnostics_extracted_but_used_as_fallback(self) -> None:
        with_diags = (
            "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.\n"
            "Found 1 error in 1 file.\n"
        )
        sigs = orchestrator.normalize_diagnostics(with_diags)
        self.assertEqual(len(sigs), 1)
        self.assertNotIn("Found 1 error", sigs[0])

        summary_only = "Found 2 errors in 2 files."
        sigs_fallback = orchestrator.normalize_diagnostics(summary_only)
        self.assertEqual(len(sigs_fallback), 1)
        self.assertEqual(sigs_fallback[0], "Found 2 errors in 2 files.")

    def test_identical_base_candidate_diagnostics_and_no_frontend_diff_blocks_without_remediate(self) -> None:
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

            tsc_diag = "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'."
            mock_candidate_tests = {
                "passed": False,
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_output_tail": tsc_diag,
                "normalized_signatures": ["src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'."],
                "fingerprint": "cand_fp",
                "frontend_preparation": {
                    "performed": True,
                    "passed": False,
                    "error": "frontend build regression (2)",
                    "output_tail": tsc_diag,
                },
                "pytest_evidence": {"performed": False, "passed": False},
            }

            mock_baseline_check = {
                "performed": True,
                "passed": False,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "returncode": 2,
                "error": "baseline frontend build regression (2)",
                "output_tail": tsc_diag,
                "normalized_signatures": ["src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'."],
                "fingerprint": "base_fp",
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_candidate_tests), \
                 mock.patch.object(orchestrator, "baseline_build_check", return_value=mock_baseline_check) as mock_base, \
                 mock.patch.object(orchestrator, "call_openai") as mock_openai:
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            mock_openai.assert_not_called()
            mock_base.assert_called_once()

            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Rule 4A: Preexisting baseline regression => BLOCKED, no attempt burn, no remediation prompt
            self.assertEqual(updated["status"], "BLOCKED")
            self.assertEqual(updated["attempt"], 1)
            self.assertIn("Pre-existing baseline frontend build regression", updated["blocked_reason"])
            self.assertFalse((control / ".mke-agent" / "prompts" / "TEST-HARDEN-001_R2.md").exists())

            # Verify history record
            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "PREEXISTING_BASELINE_BUILD_REGRESSION")
            self.assertEqual(history["attribution"], "PREEXISTING_BASELINE_BUILD_REGRESSION")
            self.assertEqual(history["decision"]["decision"], "BLOCKED")
            self.assertTrue(history["baseline_build_attribution"]["performed"])
            self.assertFalse(history["baseline_build_attribution"]["candidate_has_frontend_diff"])
            self.assertTrue(history["baseline_build_attribution"]["comparison"]["is_equivalent"])

    def test_baseline_passes_while_candidate_fails_yields_remediate(self) -> None:
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

            mock_candidate_tests = {
                "passed": False,
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_output_tail": "src/index.ts:14:5 - error TS2322: Type 'string' is not assignable to type 'number'.",
                "normalized_signatures": ["src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'."],
                "fingerprint": "cand_fp",
                "frontend_preparation": {"performed": True, "passed": False},
                "pytest_evidence": {"performed": False},
            }

            mock_baseline_check = {
                "performed": True,
                "passed": True,
                "classification": None,
                "returncode": 0,
                "error": None,
                "output_tail": "build passed",
                "normalized_signatures": [],
                "fingerprint": "",
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_candidate_tests), \
                 mock.patch.object(orchestrator, "baseline_build_check", return_value=mock_baseline_check) as mock_base:
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            mock_base.assert_called_once()

            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Rule 4B: Candidate caused regression => REMEDIATE, attempt 2, remediation prompt
            self.assertEqual(updated["status"], "READY")
            self.assertEqual(updated["attempt"], 2)
            self.assertTrue(updated["target_branch"].endswith("-r1-remediation"))
            self.assertTrue((control / updated["prompt_path"]).is_file())

            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "PRODUCT_BUILD_REGRESSION")
            self.assertEqual(history["attribution"], "CANDIDATE_BUILD_REGRESSION")
            self.assertEqual(history["decision"]["decision"], "REMEDIATE")

    def test_candidate_with_frontend_diff_skips_baseline_check_and_yields_remediate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            control = Path(td) / "control"
            repo = Path(td) / "repo"
            control.mkdir()
            repo.mkdir()

            t = sample_task("READY_FOR_AUDIT", attempt=1)
            orchestrator.write_json(control / orchestrator.TASK_REL, t)
            orchestrator.write_json(control / orchestrator.POLICY_REL, sample_policy())

            fake_git = SimpleNamespace(returncode=0, stdout="", stderr="")
            mock_gates = {"passed": True, "failures": [], "changed_files": ["src/frontend/src/App.tsx"]}

            mock_candidate_tests = {
                "passed": False,
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_output_tail": "src/App.tsx:20:10 - error TS2304: Cannot find name 'x'.",
                "normalized_signatures": ["src/App.tsx: error TS2304: Cannot find name 'x'."],
                "fingerprint": "cand_fp",
                "frontend_preparation": {"performed": True, "passed": False},
                "pytest_evidence": {"performed": False},
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_candidate_tests), \
                 mock.patch.object(orchestrator, "baseline_build_check") as mock_base:
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            # Rule 1: candidate changed frontend => baseline check SKIPPED
            mock_base.assert_not_called()

            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            self.assertEqual(updated["status"], "READY")
            self.assertEqual(updated["attempt"], 2)

            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertFalse(history["baseline_build_attribution"]["performed"])
            self.assertTrue(history["baseline_build_attribution"]["candidate_has_frontend_diff"])
            self.assertEqual(history["decision"]["decision"], "REMEDIATE")

    def test_materially_different_diagnostics_yields_remediate(self) -> None:
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

            mock_candidate_tests = {
                "passed": False,
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_output_tail": "src/index.ts:14:5 - error TS2322\nsrc/models.ts:1:1 - error TS2305",
                "normalized_signatures": [
                    "src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'.",
                    "src/models.ts: error TS2305: Module has no exported member 'Foo'.",
                ],
                "fingerprint": "cand_fp",
                "frontend_preparation": {"performed": True, "passed": False},
                "pytest_evidence": {"performed": False},
            }

            mock_baseline_check = {
                "performed": True,
                "passed": False,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "returncode": 2,
                "error": "baseline frontend build regression (2)",
                "output_tail": "src/index.ts:14:5 - error TS2322",
                "normalized_signatures": [
                    "src/index.ts: error TS2322: Type 'string' is not assignable to type 'number'.",
                ],
                "fingerprint": "base_fp",
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_candidate_tests), \
                 mock.patch.object(orchestrator, "baseline_build_check", return_value=mock_baseline_check):
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Rule 4B: Candidate introduced new diagnostics => REMEDIATE
            self.assertEqual(updated["status"], "READY")
            self.assertEqual(updated["attempt"], 2)

            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "PRODUCT_BUILD_REGRESSION")
            self.assertEqual(history["attribution"], "CANDIDATE_BUILD_REGRESSION")
            self.assertEqual(history["decision"]["decision"], "REMEDIATE")
            self.assertIn("TS2305", history["decision"]["summary"])

    def test_baseline_attribution_tooling_failure_blocks_without_attempt_burn(self) -> None:
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

            mock_candidate_tests = {
                "passed": False,
                "returncode": 2,
                "classification": "PRODUCT_BUILD_REGRESSION",
                "error": "frontend build regression (2)",
                "frontend_output_tail": "src/index.ts:14:5 - error TS2322",
                "normalized_signatures": ["src/index.ts: error TS2322: Type 'string' is not assignable."],
                "fingerprint": "cand_fp",
                "frontend_preparation": {"performed": True, "passed": False},
                "pytest_evidence": {"performed": False},
            }

            mock_baseline_check = {
                "performed": True,
                "passed": False,
                "classification": "AUDIT_ENVIRONMENT_FAILURE",
                "returncode": -1,
                "error": "npm is required for frontend build but was not found on PATH.",
                "output_tail": "npm not found",
                "normalized_signatures": [],
                "fingerprint": "",
            }

            with mock.patch.object(orchestrator, "sync_control"), \
                 mock.patch.object(orchestrator, "git", return_value=fake_git), \
                 mock.patch.object(orchestrator, "deterministic_gates", return_value=mock_gates), \
                 mock.patch.object(orchestrator, "independent_tests", return_value=mock_candidate_tests), \
                 mock.patch.object(orchestrator, "baseline_build_check", return_value=mock_baseline_check):
                processed = orchestrator.process_event(repo, control)

            self.assertTrue(processed)
            updated = orchestrator.read_json(control / orchestrator.TASK_REL)
            # Rule 4C: Tooling failure at baseline => BLOCKED infra, attempt remains 1
            self.assertEqual(updated["status"], "BLOCKED")
            self.assertEqual(updated["attempt"], 1)

            eid = orchestrator.event_id(t)
            history = orchestrator.read_json(control / orchestrator.HISTORY_REL / f"{eid}.json")
            self.assertEqual(history["classification"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertEqual(history["attribution"], "AUDIT_ENVIRONMENT_FAILURE")
            self.assertEqual(history["decision"]["decision"], "BLOCKED")

    def test_baseline_build_check_executes_npm_ci_then_build_and_never_pytest(self) -> None:
        cmd_path = r"C:\nodejs\npm.cmd"
        commands_executed = []

        def fake_git_add(cwd, *args, **kwargs):
            if len(args) >= 3 and args[0] == "worktree" and args[1] == "add":
                wt = Path(args[3])
                fe = wt / "src" / "frontend"
                fe.mkdir(parents=True)
                (fe / "package-lock.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

        def fake_run(cmd, cwd, timeout=300, check=True):
            commands_executed.append((list(cmd), Path(cwd)))
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="out ok", stderr="")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()

            with mock.patch("shutil.which", return_value=cmd_path), \
                 mock.patch.object(orchestrator, "git", side_effect=fake_git_add), \
                 mock.patch.object(orchestrator, "run", side_effect=fake_run):
                res = orchestrator.baseline_build_check(repo, "a" * 40, timeout=120)

            self.assertTrue(res["passed"])
            self.assertTrue(res["performed"])
            self.assertEqual(len(commands_executed), 2)
            self.assertEqual(commands_executed[0][0], [cmd_path, "ci"])
            self.assertEqual(commands_executed[1][0], [cmd_path, "run", "build"])

            # Verify pytest is NEVER executed during baseline build attribution
            for cmd_tuple in commands_executed:
                cmd_list = cmd_tuple[0]
                self.assertNotIn("pytest", cmd_list)
                self.assertNotIn(sys.executable, cmd_list)


if __name__ == "__main__":
    unittest.main()


