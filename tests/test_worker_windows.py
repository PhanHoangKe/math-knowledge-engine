"""Windows Job Object and Worker Process Containment Tests (S4-B1).

Verifies:
A. Suspended startup and pre-execution Job Object assignment.
B. Process memory limit enforcement and controlled failure observation.
C. Job aggregate memory limit enforcement.
D. Breakaway prevention (CREATE_BREAKAWAY_FROM_JOB rejected).
E. Kill on Job close termination of disposable processes.
F. Fail-closed failure injection and handle cleanup.
G. Mathematical regression parity through the sandboxed worker.
H. Timeout and framing bounds.
"""

import base64
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path

# Platform gating: All tests require real Windows runtime
if sys.platform != "win32":
    raise unittest.SkipTest("Windows Job Object tests require Windows operating system.")

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import ctypes
from ctypes import wintypes

import time

from mke_product.protocol.dispatcher import dispatch_request
from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.worker.constants import (
    CREATE_BREAKAWAY_FROM_JOB,
    CREATE_SUSPENDED,
    DEFAULT_WORKER_TIMEOUT_SEC,
    HANDLE_FLAG_PROTECT_FROM_CLOSE,
    IPC_MAX_RESPONSE_BYTES,
    JOB_OBJECT_LIMIT_BREAKAWAY_OK,
    JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK,
    PROCESS_MEMORY_LIMIT_BYTES,
    STARTF_USESTDHANDLES,
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    WORKER_ASSIGNMENT_FAILURE,
    WORKER_EXIT_FAILURE,
    WORKER_PROTOCOL_FAILURE,
    WORKER_RESOURCE_EXHAUSTED,
    WORKER_STARTUP_FAILURE,
    WORKER_TIMEOUT,
)
from mke_product.worker.controller import (
    CLOSE_EVIDENCE_CONFIRMED_CLOSED,
    CLOSE_EVIDENCE_INJECTED_BEFORE_CLOSE,
    CLOSE_EVIDENCE_INVALID_HANDLE,
    CLOSE_EVIDENCE_NATIVE_FAILURE,
    HANDLE_INVALID,
    HANDLE_VALID,
    SafeProcessHandle,
    SafeWin32Handle,
    WorkerController,
    dispatch_via_worker,
)
from mke_product.worker.appcontainer import get_appcontainer_manager
from mke_product.worker.win32 import (
    PROCESS_INFORMATION,
    SECURITY_ATTRIBUTES,
    STARTUPINFOW,
    assign_and_verify_process_in_job,
    create_configured_job_object,
    get_current_process_handle_count,
    get_unresolved_job_object_cleanup_failures,
    kernel32,
    query_job_limits,
    query_job_peak_memory,
    query_job_pids,
    safe_close_handle,
)


class TestWindowsSuspendedStartup(unittest.TestCase):
    """Test A: Prove worker is assigned to Job Object before primary thread resumes."""

    def test_worker_assigned_to_job_before_thread_resumed(self):
        h_job, job_err = create_configured_job_object()
        self.assertIsNotNone(h_job, f"CreateJobObject failed with error {job_err}")

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        cmd = f'"{sys.executable}" -c "import time; time.sleep(0.5)"'
        try:
            cp_ok = kernel32.CreateProcessW(
                None,
                ctypes.create_unicode_buffer(cmd),
                None,
                None,
                False,
                CREATE_SUSPENDED,
                None,
                None,
                ctypes.byref(si),
                ctypes.byref(pi),
            )
            self.assertTrue(cp_ok, f"CreateProcessW failed with error {ctypes.get_last_error()}")

            # 1. While thread is STILL suspended, verify assignment
            assign_ok, assign_err = assign_and_verify_process_in_job(h_job, pi.hProcess)
            self.assertTrue(assign_ok, f"Assignment verification failed with error {assign_err}")

            # 2. Query PID list from Job Object to verify process inclusion
            pids, pid_err = query_job_pids(h_job)
            self.assertEqual(pid_err, 0)
            self.assertIn(pi.dwProcessId, pids)

            # 3. Resume thread: return value must be 1 (proving it was indeed suspended)
            prev_suspend_count = kernel32.ResumeThread(pi.hThread)
            self.assertEqual(prev_suspend_count, 1)

            # 4. Wait for normal completion
            wait_res = kernel32.WaitForSingleObject(pi.hProcess, 5000)
            self.assertEqual(wait_res, WAIT_OBJECT_0)

        finally:
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)


class TestWindowsProcessMemoryLimit(unittest.TestCase):
    """Test B: Controlled allocation exceeding 256 MiB committed memory in disposable worker."""

    def test_process_memory_limit_exceeded_disposable_worker(self):
        """Worker attempting 300 MiB commit fails closed as WORKER_RESOURCE_EXHAUSTED."""
        h_job, job_err = create_configured_job_object(
            process_memory_limit=256 * 1024 * 1024,
            job_memory_limit=512 * 1024 * 1024,
        )
        self.assertIsNotNone(h_job)

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        alloc_code = """
import sys
try:
    buf = bytearray(300 * 1024 * 1024)
    for i in range(0, len(buf), 4096):
        buf[i] = 1
    sys.exit(0)
except MemoryError:
    sys.exit(42)
except Exception:
    sys.exit(99)
"""
        b64 = base64.b64encode(alloc_code.encode()).decode("ascii")
        cmd = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64}\'))"'

        try:
            cp_ok = kernel32.CreateProcessW(
                None, ctypes.create_unicode_buffer(cmd), None, None, False,
                CREATE_SUSPENDED, None, None, ctypes.byref(si), ctypes.byref(pi)
            )
            self.assertTrue(cp_ok)

            assign_ok, _ = assign_and_verify_process_in_job(h_job, pi.hProcess)
            self.assertTrue(assign_ok)

            kernel32.ResumeThread(pi.hThread)
            kernel32.WaitForSingleObject(pi.hProcess, 10000)

            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))

            # Observed Windows kernel behavior: memory commitment denied, CRT fails, MemoryError raised -> exit code 42
            self.assertEqual(exit_code.value, 42)

            peak_proc, peak_job, _ = query_job_peak_memory(h_job)
            self.assertGreater(peak_proc, 0)
            self.assertLessEqual(peak_proc, 256 * 1024 * 1024 + 16 * 1024 * 1024)

        finally:
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)

    def test_process_memory_within_limit_succeeds(self):
        """Worker allocating 50 MiB within 256 MiB limit succeeds cleanly."""
        h_job, _ = create_configured_job_object(process_memory_limit=256 * 1024 * 1024)
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        alloc_code = """
import sys
buf = bytearray(50 * 1024 * 1024)
for i in range(0, len(buf), 4096):
    buf[i] = 1
sys.exit(0)
"""
        b64 = base64.b64encode(alloc_code.encode()).decode("ascii")
        cmd = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64}\'))"'

        try:
            kernel32.CreateProcessW(
                None, ctypes.create_unicode_buffer(cmd), None, None, False,
                CREATE_SUSPENDED, None, None, ctypes.byref(si), ctypes.byref(pi)
            )
            assign_and_verify_process_in_job(h_job, pi.hProcess)
            kernel32.ResumeThread(pi.hThread)
            kernel32.WaitForSingleObject(pi.hProcess, 10000)

            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
            self.assertEqual(exit_code.value, 0)

        finally:
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)


class TestWindowsJobMemoryLimit(unittest.TestCase):
    """Test C: Multi-process aggregate memory ceiling (JobMemoryLimit)."""

    def test_job_memory_limit_isolated_control_succeeds(self):
        """Isolated control: prove identical Worker 2 allocation succeeds under 80 MiB per-process limit with generous Job limit."""
        # 80 MiB per-process limit, 200 MiB generous Job limit
        h_job, _ = create_configured_job_object(
            process_memory_limit=80 * 1024 * 1024,
            job_memory_limit=200 * 1024 * 1024,
        )
        self.assertIsNotNone(h_job)

        w2_code = """
import sys
try:
    buf = bytearray(55 * 1024 * 1024)
    for i in range(0, len(buf), 4096):
        buf[i] = 1
    sys.exit(0)
except MemoryError:
    sys.exit(42)
except Exception:
    sys.exit(99)
"""
        b64_2 = base64.b64encode(w2_code.encode()).decode("ascii")
        cmd2 = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64_2}\'))"'

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        try:
            kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd2), None, None, False, CREATE_SUSPENDED, None, None, ctypes.byref(si), ctypes.byref(pi))
            assign_ok, _ = assign_and_verify_process_in_job(h_job, pi.hProcess)
            self.assertTrue(assign_ok)

            pids, _ = query_job_pids(h_job)
            self.assertIn(pi.dwProcessId, pids)

            kernel32.ResumeThread(pi.hThread)
            kernel32.WaitForSingleObject(pi.hProcess, 10000)

            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
            # Isolated Worker 2 succeeds with exit code 0 under 80 MiB process limit
            self.assertEqual(exit_code.value, 0)
        finally:
            kernel32.TerminateProcess(pi.hProcess, 0)
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)

    def test_job_memory_limit_exceeded_aggregate(self):
        """Two concurrent processes in same Job Object: second process exceeds aggregate Job limit with readiness handshake."""
        # 100 MiB Job limit, 80 MiB Process limit
        h_job, _ = create_configured_job_object(
            process_memory_limit=80 * 1024 * 1024,
            job_memory_limit=100 * 1024 * 1024,
        )
        self.assertIsNotNone(h_job)

        # Worker 1: allocates 55 MiB, touches pages, writes handshake to stdout, and sleeps
        w1_code = """
import sys, time
buf = bytearray(55 * 1024 * 1024)
for i in range(0, len(buf), 4096):
    buf[i] = 1
sys.stdout.write("READY\\n")
sys.stdout.flush()
time.sleep(10)
sys.exit(0)
"""
        b64_1 = base64.b64encode(w1_code.encode()).decode("ascii")
        cmd1 = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64_1}\'))"'

        # Worker 2: requests 55 MiB (< 80 MiB process limit, but aggregate 55+55 = 110 > 100 MiB Job limit)
        w2_code = """
import sys
try:
    buf = bytearray(55 * 1024 * 1024)
    for i in range(0, len(buf), 4096):
        buf[i] = 1
    sys.exit(0)
except MemoryError:
    sys.exit(42)
except Exception:
    sys.exit(99)
"""
        b64_2 = base64.b64encode(w2_code.encode()).decode("ascii")
        cmd2 = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64_2}\'))"'

        # Pipe for Worker 1 stdout handshake
        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.bInheritHandle = True
        h_read = wintypes.HANDLE()
        h_write = wintypes.HANDLE()
        kernel32.CreatePipe(ctypes.byref(h_read), ctypes.byref(h_write), ctypes.byref(sa), 0)
        kernel32.SetHandleInformation(h_read, 1, 0)

        si1 = STARTUPINFOW()
        si1.cb = ctypes.sizeof(STARTUPINFOW)
        si1.dwFlags = STARTF_USESTDHANDLES
        si1.hStdOutput = h_write
        si1.hStdError = h_write
        pi1 = PROCESS_INFORMATION()

        si2 = STARTUPINFOW()
        si2.cb = ctypes.sizeof(STARTUPINFOW)
        pi2 = PROCESS_INFORMATION()

        try:
            # Start Worker 1
            kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd1), None, None, True, CREATE_SUSPENDED, None, None, ctypes.byref(si1), ctypes.byref(pi1))
            safe_close_handle(h_write)
            h_write = wintypes.HANDLE()

            assign_ok1, _ = assign_and_verify_process_in_job(h_job, pi1.hProcess)
            self.assertTrue(assign_ok1)
            kernel32.ResumeThread(pi1.hThread)

            # Explicit readiness handshake: bounded wait for READY\n from Worker 1
            handshake_deadline = time.monotonic() + 5.0
            handshake = ""
            while time.monotonic() < handshake_deadline:
                avail = wintypes.DWORD(0)
                if kernel32.PeekNamedPipe(h_read, None, 0, None, ctypes.byref(avail), None) and avail.value > 0:
                    buf = ctypes.create_string_buffer(32)
                    bytes_read = wintypes.DWORD(0)
                    if kernel32.ReadFile(h_read, buf, min(32, avail.value), ctypes.byref(bytes_read), None):
                        handshake = buf.raw[: bytes_read.value].decode("ascii", errors="replace")
                        if "READY" in handshake:
                            break
                time.sleep(0.02)
            self.assertIn("READY", handshake)

            # Confirm both processes are tracked in Job Object
            pids1, _ = query_job_pids(h_job)
            self.assertIn(pi1.dwProcessId, pids1)

            # Verify peak memory of job is at least 50 MiB
            peak_proc1, peak_job1, _ = query_job_peak_memory(h_job)
            self.assertGreaterEqual(peak_job1, 50 * 1024 * 1024)

            # Start Worker 2 in the same Job Object
            kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd2), None, None, False, CREATE_SUSPENDED, None, None, ctypes.byref(si2), ctypes.byref(pi2))
            assign_ok2, _ = assign_and_verify_process_in_job(h_job, pi2.hProcess)
            self.assertTrue(assign_ok2)

            pids2, _ = query_job_pids(h_job)
            self.assertIn(pi1.dwProcessId, pids2)
            self.assertIn(pi2.dwProcessId, pids2)

            kernel32.ResumeThread(pi2.hThread)
            kernel32.WaitForSingleObject(pi2.hProcess, 10000)

            exit_code2 = wintypes.DWORD()
            kernel32.GetExitCodeProcess(pi2.hProcess, ctypes.byref(exit_code2))

            # Worker 2 alone requested 55 MiB (less than its 80 MiB process limit)
            # It failed with code 42 (MemoryError) strictly because aggregate JobMemoryLimit was exhausted
            self.assertEqual(exit_code2.value, 42)

        finally:
            safe_close_handle(h_read)
            safe_close_handle(h_write)
            kernel32.TerminateProcess(pi1.hProcess, 0)
            kernel32.TerminateProcess(pi2.hProcess, 0)
            safe_close_handle(pi1.hThread)
            safe_close_handle(pi1.hProcess)
            safe_close_handle(pi2.hThread)
            safe_close_handle(pi2.hProcess)
            safe_close_handle(h_job)


class TestWindowsBreakawayRejection(unittest.TestCase):
    """Test D: Prove CREATE_BREAKAWAY_FROM_JOB is rejected."""

    def test_breakaway_from_job_rejected(self):
        h_job, _ = create_configured_job_object()
        self.assertIsNotNone(h_job)

        # 1. Verify Job Object configuration: neither breakaway flag is enabled
        limits, err = query_job_limits(h_job)
        self.assertEqual(err, 0)
        self.assertIsNotNone(limits)
        flags = limits.BasicLimitInformation.LimitFlags
        self.assertEqual(flags & JOB_OBJECT_LIMIT_BREAKAWAY_OK, 0)
        self.assertEqual(flags & JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK, 0)

        # 2. Worker attempts CreateProcess with CREATE_BREAKAWAY_FROM_JOB using full Win32 STARTUPINFOW struct
        breakaway_code = """
import sys, ctypes
from ctypes import wintypes
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

k32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)
]
k32.CreateProcessW.restype = wintypes.BOOL

si = STARTUPINFOW()
si.cb = ctypes.sizeof(STARTUPINFOW)
pi = PROCESS_INFORMATION()

CREATE_BREAKAWAY_FROM_JOB = 0x01000000
cmd = sys.executable + ' -c "import sys; sys.exit(0)"'
res = k32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None, False, CREATE_BREAKAWAY_FROM_JOB, None, None, ctypes.byref(si), ctypes.byref(pi))
err = ctypes.get_last_error()
# If res is 0 and err is ERROR_ACCESS_DENIED (5), exit with 55
if not res and err == 5:
    sys.exit(55)
elif res:
    sys.exit(99)
else:
    sys.exit(err)
"""
        b64 = base64.b64encode(breakaway_code.encode()).decode("ascii")
        cmd = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64}\'))"'

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        try:
            kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None, False, CREATE_SUSPENDED, None, None, ctypes.byref(si), ctypes.byref(pi))
            assign_and_verify_process_in_job(h_job, pi.hProcess)
            kernel32.ResumeThread(pi.hThread)

            kernel32.WaitForSingleObject(pi.hProcess, 10000)
            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))

            # Exit code 55 proves CreateProcess with CREATE_BREAKAWAY_FROM_JOB failed specifically with ERROR_ACCESS_DENIED (5)
            self.assertEqual(exit_code.value, 55)

        finally:
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)


class TestWindowsKillOnJobClose(unittest.TestCase):
    """Test E: Prove closing last Job Object handle terminates worker processes."""

    def test_kill_on_job_close_terminates_worker(self):
        h_job, _ = create_configured_job_object()
        self.assertIsNotNone(h_job)

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        pi = PROCESS_INFORMATION()

        cmd = f'"{sys.executable}" -c "import time; time.sleep(60)"'

        try:
            kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmd), None, None, False, CREATE_SUSPENDED, None, None, ctypes.byref(si), ctypes.byref(pi))
            assign_and_verify_process_in_job(h_job, pi.hProcess)
            kernel32.ResumeThread(pi.hThread)

            # Verify process is actively running
            wait1 = kernel32.WaitForSingleObject(pi.hProcess, 100)
            self.assertEqual(wait1, WAIT_TIMEOUT)

            # Close last handle to Job Object
            safe_close_handle(h_job)
            h_job = None

            # Process must terminate within 5 seconds
            wait2 = kernel32.WaitForSingleObject(pi.hProcess, 5000)
            self.assertEqual(wait2, WAIT_OBJECT_0)

        finally:
            safe_close_handle(pi.hThread)
            safe_close_handle(pi.hProcess)
            safe_close_handle(h_job)


class TestWindowsFailurePaths(unittest.TestCase):
    """Test F: Inject failures into lifecycle stages, asserting fail-closed behavior and cleanup."""

    def setUp(self):
        self.controller = WorkerController()
        self.sample_req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=1",
        }

    def test_injected_job_creation_failure(self):
        res = self.controller.execute_request(self.sample_req, _inject_job_creation_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNone(res["definedness"])

    def test_injected_job_config_failure(self):
        res = self.controller.execute_request(self.sample_req, _inject_job_config_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNone(res["definedness"])

    def test_combined_real_job_config_and_native_cleanup_failure_retains_owner(self):
        """ERROR_INVALID_PARAMETER plus protected CloseHandle failure remains owned and fails closed."""
        controller = WorkerController(process_memory_limit=0, job_memory_limit=0)
        res = controller.execute_request(
            self.sample_req,
            _inject_protected_job_config_cleanup_failure=True,
        )

        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        details = res["error"]["details"]
        self.assertFalse(details["safe_cleanup"])
        self.assertEqual(details["job_creation_failure"]["configuration_error"], 87)
        self.assertNotEqual(details["job_creation_failure"]["cleanup_error"], 0)
        self.assertEqual(
            details["job_creation_failure"]["cleanup_error"],
            details["job_close_error"],
        )
        self.assertTrue(details["job_creation_failure"]["handle_valid_after_failure"])
        self.assertIn("job_object", details["cleanup_failures"])
        self.assertEqual(get_unresolved_job_object_cleanup_failures(), [])

        owners = controller.get_unresolved_job_handles()
        self.assertEqual(len(owners), 1)
        owner = owners[0]
        self.assertEqual(owner.close_evidence, CLOSE_EVIDENCE_NATIVE_FAILURE)
        attempts = owner.close_attempts
        controller.reconcile_unresolved_resources()
        self.assertEqual(owner.close_attempts, attempts)

        flags = wintypes.DWORD()
        self.assertTrue(bool(kernel32.GetHandleInformation(owner.handle, ctypes.byref(flags))))
        self.assertTrue(flags.value & HANDLE_FLAG_PROTECT_FROM_CLOSE)
        self.assertTrue(bool(kernel32.SetHandleInformation(
            owner.handle,
            HANDLE_FLAG_PROTECT_FROM_CLOSE,
            0,
        )))
        self.assertTrue(owner.recover_native_close())
        controller.reconcile_unresolved_resources()
        self.assertEqual(controller.get_unresolved_count(), 0)

    def test_injected_process_creation_failure(self):
        res = self.controller.execute_request(self.sample_req, _inject_process_creation_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNone(res["definedness"])

    def test_injected_assignment_failure(self):
        res = self.controller.execute_request(self.sample_req, _inject_assignment_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_ASSIGNMENT_FAILURE)
        self.assertIsNone(res["definedness"])

    def test_injected_resume_failure(self):
        res = self.controller.execute_request(self.sample_req, _inject_resume_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNone(res["definedness"])


class TestWindowsMathematicalRegression(unittest.TestCase):
    """Test G: Route mathematical requests through worker, proving exact parity with direct S4-A dispatch."""

    def _assert_worker_matches_direct(self, req):
        direct_res = dispatch_request(req)
        worker_res = dispatch_via_worker(req)

        self.assertEqual(worker_res["schema_version"], direct_res["schema_version"])
        self.assertEqual(worker_res["operation"], direct_res["operation"])
        self.assertEqual(worker_res["outcome"], direct_res["outcome"])
        self.assertEqual(worker_res["status"], direct_res["status"])
        self.assertEqual(worker_res["definedness"], direct_res["definedness"])
        if "root" in direct_res:
            self.assertEqual(worker_res["root"], direct_res["root"])
        if "classification" in direct_res:
            self.assertEqual(worker_res["classification"], direct_res["classification"])

    def test_solve_linear_unique_root(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "2*x + 3 = 7"}
        self._assert_worker_matches_direct(req)

    def test_solve_linear_fractional_coefficients(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "(1/2)*x + (3/4) = 0"}
        self._assert_worker_matches_direct(req)

    def test_solve_identity_all_reals(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x + 1 = x + 1"}
        self._assert_worker_matches_direct(req)

    def test_solve_contradiction_empty_set(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x + 1 = x + 2"}
        self._assert_worker_matches_direct(req)

    def test_solve_out_of_scope_nonlinear(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x^2 = 1"}
        self._assert_worker_matches_direct(req)

    def test_solve_domain_error_div_zero(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "1/0 = 0"}
        self._assert_worker_matches_direct(req)

    def test_check_candidate_valid(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "CHECK_CANDIDATE", "equation": "2*x + 3 = 7", "candidate": "2"}
        self._assert_worker_matches_direct(req)

    def test_check_candidate_invalid(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "CHECK_CANDIDATE", "equation": "2*x + 3 = 7", "candidate": "3"}
        self._assert_worker_matches_direct(req)

    def test_check_candidate_domain_error(self):
        req = {"schema_version": SCHEMA_VERSION, "operation": "CHECK_CANDIDATE", "equation": "1/(x-2) = 0", "candidate": "2"}
        self._assert_worker_matches_direct(req)


class TestWindowsTimeoutAndFraming(unittest.TestCase):
    """Test H: Bounded execution, framing ceilings, and payload limits."""

    def test_worker_payload_too_large(self):
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=" + "1" * 5000,
        }
        res = dispatch_via_worker(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_worker_timeout_fails_closed(self):
        """Dedicated blocking fixture: prove worker timeout strictly fails closed without race."""
        blocking_cmd = f'"{sys.executable}" -c "import time; time.sleep(5.0)"'
        controller = WorkerController(timeout_sec=0.2, _worker_cmd=blocking_cmd)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        t0 = time.monotonic()
        res = controller.execute_request(req)
        elapsed = time.monotonic() - t0

        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertEqual(res.get("error", {}).get("details", {}).get("timeout_phase"), "READ")
        self.assertIsNone(res["definedness"])
        self.assertLess(elapsed, 1.5)


    def test_worker_timeout_during_ipc_write_non_reading_worker(self):
        """Dedicated non-reading worker fixture: prove full-lifecycle timeout covers IPC write phase."""
        non_reading_cmd = f'"{sys.executable}" -c "import time; time.sleep(10)"'
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=non_reading_cmd,
            _stdin_pipe_buffer_size=1024,
        )
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=" + "1" * 4000,
        }
        t0 = time.monotonic()
        res = controller.execute_request(req)
        elapsed = time.monotonic() - t0

        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertEqual(res.get("error", {}).get("details", {}).get("timeout_phase"), "WRITE")
        self.assertTrue(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertIsNotNone(controller._last_write_info)
        self.assertTrue(controller._last_write_info["duplicate_handle_success"])
        self.assertTrue(controller._last_write_info["write_entered"])
        self.assertTrue(controller._last_write_info["write_blocked_at_deadline"])
        self.assertTrue(controller._last_write_info["cancellation_requested"])
        self.assertTrue(controller._last_write_info["cancel_synchronous_io_called"])
        self.assertTrue(controller._last_write_info["cancel_synchronous_io_return"])
        self.assertTrue(controller._last_write_info["writer_thread_alive_before_cancel"])
        self.assertFalse(controller._last_write_info["writer_thread_alive_after_join"])
        self.assertTrue(controller._last_write_info["writer_exited"])
        self.assertTrue(controller._last_write_info["all_handles_safely_released"])
        self.assertIn(controller._last_write_info["write_file_status"], ("ABORTED", "BROKEN_PIPE"))
        self.assertIsNone(res["definedness"])
        self.assertLess(elapsed, 1.5)


class TestWindowsControllerInputBoundary(unittest.TestCase):
    """Test I: Robustness of controller input pre-validation before worker IPC."""

    def setUp(self):
        self.controller = WorkerController()

    def test_controller_rejects_cyclic_dictionary(self):
        d = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE"}
        d["self"] = d
        res = self.controller.execute_request(d)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertIn(res["status"], ("ERR_PAYLOAD_TOO_LARGE", "ERR_PROTOCOL_MALFORMED_STRUCTURE"))
        self.assertIsNone(res["definedness"])

    def test_controller_rejects_non_string_keys(self):
        d = {"schema_version": SCHEMA_VERSION, 123: "val"}
        res = self.controller.execute_request(d)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res["definedness"])

    def test_controller_rejects_unsupported_types(self):
        d = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": {1, 2, 3}}
        res = self.controller.execute_request(d)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res["definedness"])

    def test_controller_rejects_oversized_payload(self):
        d = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 5000}
        res = self.controller.execute_request(d)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_controller_rejects_isolated_surrogates(self):
        d = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "\ud800"}
        res = self.controller.execute_request(d)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])

    def test_controller_rejects_chinese_chars_exceeding_byte_limit_before_job_creation(self):
        """Reproduce Chinese character byte expansion: 1400 chars (4200 bytes) rejected before Job creation."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=1",
            "unexpected": "\u4e2d" * 1400,
        }
        # Injected failure on Job creation proves rejection occurred before Job creation
        res = self.controller.execute_request(req, _inject_job_creation_failure=True)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_controller_accepts_chinese_chars_within_byte_limit_before_worker(self):
        """700 repetitions of U+4E2D (2100 bytes) serializes within 4096 bytes and reaches Job creation."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=1",
            "unexpected": "\u4e2d" * 700,
        }
        res = self.controller.execute_request(req, _inject_job_creation_failure=True)
        # Reaching the injected job creation failure proves it passed serialization validation
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)

    def test_controller_rejects_oversized_operation_and_bounds_error_envelope(self):
        """Oversized untrusted operation string (>16 KiB) is rejected, normalized to UNKNOWN, and response is bounded."""
        huge_op = "SOLVE_" + "A" * 50000
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": huge_op,
            "equation": "x=1",
        }
        res = self.controller.execute_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertEqual(res["operation"], "UNKNOWN")
        self.assertNotIn("A" * 100, json.dumps(res))
        serialized = json.dumps(res, ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(serialized), IPC_MAX_RESPONSE_BYTES)

    def test_controller_rejects_raw_string_oversized_operation_bounded(self):
        """Oversized raw string request is rejected, normalized to UNKNOWN, and response strictly <= IPC_MAX_RESPONSE_BYTES."""
        raw_req = json.dumps({
            "schema_version": SCHEMA_VERSION,
            "operation": "X" * 20000,
            "equation": "x=1",
        })
        res = self.controller.execute_request(raw_req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertEqual(res["operation"], "UNKNOWN")
        self.assertNotIn("X" * 100, json.dumps(res))
        serialized = json.dumps(res, ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(serialized), IPC_MAX_RESPONSE_BYTES)

    def test_controller_bounds_error_envelope_under_huge_details(self):
        """Internal error builder truncates or falls back so serialized error never exceeds IPC_MAX_RESPONSE_BYTES."""
        from mke_product.worker.controller import _build_controller_error
        huge_details = {"leak": "Z" * 30000}
        envelope = _build_controller_error(
            "ERR_INTERNAL",
            "Something failed",
            details=huge_details,
            operation="ATTACK_" + "B" * 1000,
        )
        self.assertEqual(envelope["operation"], "UNKNOWN")
        serialized = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(serialized), IPC_MAX_RESPONSE_BYTES)


class TestWindowsStrictUtf8Ipc(unittest.TestCase):
    """Test J: Strict UTF-8 validation across IPC without lossy character replacement."""

    def test_strict_utf8_payload_rejection(self):
        controller = WorkerController()
        # Invalid UTF-8 byte 0xFF inside payload
        raw_invalid_utf8 = b'{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "x=\xff"}'
        res = controller.execute_request(raw_invalid_utf8)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])


class TestWindowsHandleConfinement(unittest.TestCase):
    """Test K: Prove unallowlisted inheritable handles are not inherited by worker."""

    def test_unallowlisted_handle_not_inherited(self):
        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.bInheritHandle = True
        decoy = kernel32.CreateEventW(ctypes.byref(sa), True, False, None)
        self.assertTrue(decoy)
        try:
            h = int(decoy)

            child_code = f"""
import json, struct, sys, _winapi
header = sys.stdin.buffer.read(4)
size = struct.unpack('>I', header)[0]
sys.stdin.buffer.read(size)
cur = _winapi.GetCurrentProcess()
dup = None
dup_error = 0
file_type = -1
file_type_error = 0
try:
    dup = _winapi.DuplicateHandle(cur, {h}, cur, 0, False, _winapi.DUPLICATE_SAME_ACCESS)
    file_type = int(_winapi.GetFileType(dup))
    file_type_error = _winapi.GetLastError()
    _winapi.CloseHandle(dup)
except OSError as exc:
    dup_error = int(getattr(exc, 'winerror', 6) or 6)

result = {{
    'decoy_event_accessible': dup is not None and file_type == 0 and file_type_error == 0,
    'dup_error': dup_error,
    'candidate_file_type': file_type,
    'candidate_error': file_type_error,
}}
raw = json.dumps(result).encode('utf-8')
sys.stdout.buffer.write(struct.pack('>I', len(raw)) + raw)
sys.stdout.buffer.flush()
"""
            b64 = base64.b64encode(child_code.encode()).decode("ascii")
            cmd = f'"{sys.executable}" -c "import base64; exec(base64.b64decode(\'{b64}\'))"'

            controller = WorkerController(_worker_cmd=cmd)
            res = controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
            # A typed operation on the Event avoids false positives when an
            # allowlisted pipe happens to reuse the same numeric handle value.
            self.assertIn("decoy_event_accessible", res, res)
            self.assertFalse(res["decoy_event_accessible"], res)
        finally:
            safe_close_handle(decoy)


class TestWindowsAppContainerIntegration(unittest.TestCase):
    """S4-B2/P1: real worker execution under the verified AppContainer identity."""

    request = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

    def test_real_solve_worker_is_verified_before_resume(self):
        controller = WorkerController(timeout_sec=5.0)
        result = controller.execute_request(self.request)
        self.assertEqual(result["outcome"], "SUCCESS")
        self.assertEqual(result["status"], "UNIQUE_ROOT")
        self.assertEqual(result["root"]["numerator"], "1")
        self.assertEqual(result["root"]["denominator"], "1")
        evidence = controller.get_last_appcontainer_evidence()
        self.assertTrue(evidence["accepted"])
        self.assertTrue(evidence["is_appcontainer"])
        self.assertTrue(evidence["sid_matches_profile"])
        self.assertFalse(evidence["elevated"])
        self.assertTrue(evidence["job_assignment_verified"])
        self.assertTrue(evidence["verified_before_resume"])
        self.assertTrue(evidence["process_was_resumed"])

    def test_token_identity_mismatch_is_rejected_while_suspended(self):
        controller = WorkerController(timeout_sec=5.0)
        result = controller.execute_request(self.request, _inject_token_mismatch=True)
        self.assertEqual(result["status"], WORKER_STARTUP_FAILURE)
        evidence = controller.get_last_appcontainer_evidence()
        self.assertFalse(evidence["accepted"])
        self.assertFalse(evidence["is_appcontainer"])
        self.assertFalse(evidence["process_was_resumed"])

    def test_profile_sid_mismatch_is_rejected_while_suspended(self):
        controller = WorkerController(timeout_sec=5.0)
        result = controller.execute_request(self.request, _inject_sid_mismatch=True)
        self.assertEqual(result["status"], WORKER_STARTUP_FAILURE)
        evidence = controller.get_last_appcontainer_evidence()
        self.assertFalse(evidence["accepted"])
        self.assertFalse(evidence["sid_matches_profile"])
        self.assertFalse(evidence["process_was_resumed"])

    def test_security_capabilities_attribute_failure_is_fail_closed(self):
        controller = WorkerController(timeout_sec=5.0)
        result = controller.execute_request(
            self.request, _inject_appcontainer_attribute_failure=True
        )
        self.assertEqual(result["status"], WORKER_STARTUP_FAILURE)
        self.assertIn("security capabilities", result["error"]["message"])

    def test_repeated_appcontainer_workers_do_not_accumulate_handles(self):
        controller = WorkerController(timeout_sec=5.0)
        before = get_current_process_handle_count()
        for _ in range(8):
            result = controller.execute_request(self.request)
            self.assertEqual(result["outcome"], "SUCCESS")
        controller.settle_quarantine(timeout=1.0)
        after = get_current_process_handle_count()
        self.assertLessEqual(after, before + 4)
        self.assertEqual(controller.get_unresolved_count(), 0)

    def test_profile_cleanup_refuses_active_child_lease_then_recovers(self):
        manager = get_appcontainer_manager()
        lease = manager.acquire()
        try:
            refused = manager.cleanup()
            self.assertEqual(refused["state"], "REFUSED_ACTIVE_CHILDREN")
            self.assertGreaterEqual(refused["active_children"], 1)
        finally:
            lease.release()
        cleaned = manager.cleanup()
        self.assertEqual(cleaned["state"], "CLEANED")
        self.assertEqual(cleaned["active_children"], 0)

    def test_staging_directory_deletion_failure_preserves_state_and_recovers(self):
        manager = get_appcontainer_manager()
        manager.prepare()
        stage_root = manager.stage_root
        self.assertIsNotNone(stage_root)
        self.assertTrue(stage_root.exists())

        failed = manager.cleanup(_inject_stage_deletion_failure=True)
        self.assertEqual(failed["state"], "CLEANUP_FAILED")
        self.assertFalse(failed["stage_removed"])
        self.assertIsNotNone(manager.stage_root)
        self.assertTrue(manager.has_unresolved_cleanup())

        recovered = manager.cleanup(_inject_stage_deletion_failure=False)
        self.assertEqual(recovered["state"], "CLEANED")
        self.assertTrue(recovered["stage_removed"])
        self.assertIsNone(manager.stage_root)
        self.assertFalse(manager.has_unresolved_cleanup())

    def test_profile_deletion_failure_preserves_sid_and_recovers(self):
        manager = get_appcontainer_manager()
        manager.prepare()
        self.assertTrue(manager.sid)

        failed = manager.cleanup(_inject_profile_deletion_failure=True)
        self.assertEqual(failed["state"], "CLEANUP_FAILED")
        self.assertNotEqual(failed["delete_hresult"], 0)
        self.assertTrue(manager.sid)
        self.assertTrue(manager.has_unresolved_cleanup())

        recovered = manager.cleanup(_inject_profile_deletion_failure=False)
        self.assertEqual(recovered["state"], "CLEANED")
        self.assertEqual(recovered["delete_hresult"], 0)
        self.assertFalse(manager.has_unresolved_cleanup())

    def test_partial_preparation_failure_cleans_up_or_preserves_diagnostics(self):
        from mke_product.worker.appcontainer import AppContainerManager
        mgr = AppContainerManager()
        with mock.patch.object(mgr, "_grant_read_execute", side_effect=OSError("Injected permission error")):
            with self.assertRaises(OSError):
                mgr.prepare()
        self.assertIn(mgr._last_cleanup["state"], ("CLEANED", "CLEANUP_FAILED"))

    def test_cleanup_idempotent_when_already_cleaned(self):
        manager = get_appcontainer_manager()
        manager.prepare()
        res1 = manager.cleanup()
        self.assertEqual(res1["state"], "CLEANED")
        res2 = manager.cleanup()
        self.assertEqual(res2["state"], "CLEANED")
        self.assertEqual(res2["delete_hresult"], 0)
        self.assertTrue(res2["stage_removed"])

    def test_unresolved_cleanup_prevents_unsafe_profile_reuse(self):
        manager = get_appcontainer_manager()
        manager.prepare()
        failed = manager.cleanup(_inject_stage_deletion_failure=True)
        self.assertEqual(failed["state"], "CLEANUP_FAILED")
        self.assertTrue(manager.has_unresolved_cleanup())

        with mock.patch("shutil.rmtree", side_effect=OSError("Access denied")):
            with self.assertRaises(RuntimeError) as ctx:
                manager.prepare()
            self.assertIn("unresolved cleanup state exists", str(ctx.exception))

        recovered = manager.cleanup()
        self.assertEqual(recovered["state"], "CLEANED")
        self.assertFalse(manager.has_unresolved_cleanup())

    def test_real_appcontainer_process_lease_gating_and_termination_recovery(self):
        """Phase 2: Genuine AppContainer child process under Job containment with controlled termination uncertainty."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        manager = get_appcontainer_manager()

        res = controller.execute_request(
            self.request,
            _inject_terminate_process_failure=True,
            _inject_termination_wait_timeout=True,
            _inject_job_close_failure=True,
        )
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)

        process_owners = [h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)]
        self.assertEqual(len(process_owners), 1)
        proc_owner = process_owners[0]
        job_owners = controller.get_unresolved_job_handles()
        self.assertEqual(len(job_owners), 1)
        job_owner = job_owners[0]

        self.assertEqual(kernel32.WaitForSingleObject(proc_owner.handle, 0), WAIT_TIMEOUT)
        refused = manager.cleanup()
        self.assertEqual(refused["state"], "REFUSED_ACTIVE_CHILDREN")
        self.assertGreaterEqual(refused["active_children"], 1)

        self.assertTrue(job_owner.close(_inject_failure=False))
        self.assertEqual(kernel32.WaitForSingleObject(proc_owner.handle, 5000), WAIT_OBJECT_0)

        controller.reconcile_unresolved_resources()
        self.assertEqual(controller.get_unresolved_count(), 0)
        self.assertEqual(manager.active_children, 0)

        cleaned = manager.cleanup()
        self.assertEqual(cleaned["state"], "CLEANED")
        self.assertEqual(cleaned["active_children"], 0)

    def test_concurrent_lease_release_is_strictly_idempotent_and_thread_safe(self):
        """Concurrent calls to release() on the same AppContainerLease instance decrement count exactly once."""
        manager = get_appcontainer_manager()
        lease = manager.acquire()
        initial_children = manager.active_children
        self.assertGreaterEqual(initial_children, 1)

        errors = []

        def worker_release():
            try:
                lease.release()
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=worker_release) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        self.assertEqual(len(errors), 0)
        self.assertEqual(manager.active_children, initial_children - 1)
        self.assertTrue(lease._released)

    def test_atomic_lease_acquisition_prevents_cleanup_interleaving(self):
        """Atomic lock in acquire() ensures concurrent cleanup cannot delete the profile between preparation and lease registration."""
        from mke_product.worker.appcontainer import AppContainerManager
        mgr = AppContainerManager()

        cleanup_observed_states = []
        barrier = threading.Barrier(2)

        original_prepare = mgr.prepare

        def synchronized_prepare():
            with mgr._lock:
                original_prepare()
                try:
                    barrier.wait(timeout=1.0)
                except threading.BrokenBarrierError:
                    pass

        def attempt_concurrent_cleanup():
            try:
                barrier.wait(timeout=1.0)
            except threading.BrokenBarrierError:
                pass
            res = mgr.cleanup()
            cleanup_observed_states.append(res)

        mgr.prepare = synchronized_prepare
        cleaner_thread = threading.Thread(target=attempt_concurrent_cleanup)
        cleaner_thread.start()

        lease = mgr.acquire()
        cleaner_thread.join(timeout=3.0)

        try:
            self.assertEqual(len(cleanup_observed_states), 1)
            self.assertEqual(cleanup_observed_states[0]["state"], "REFUSED_ACTIVE_CHILDREN")
            self.assertEqual(cleanup_observed_states[0]["active_children"], 1)
            self.assertTrue(mgr._prepared)
            self.assertIsNotNone(mgr.stage_root)
        finally:
            lease.release()
            cleaned = mgr.cleanup()
            self.assertEqual(cleaned["state"], "CLEANED")

    def test_uncertain_termination_preserves_lease_and_refuses_cleanup(self):
        """Reconciliation never releases child lease or deletes profile while termination is unconfirmed."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        manager = get_appcontainer_manager()

        res = controller.execute_request(
            self.request,
            _inject_terminate_process_failure=True,
            _inject_termination_wait_timeout=True,
            _inject_job_close_failure=True,
        )
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)

        # Confirm child is alive and handles are unresolved
        proc_owners = [h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)]
        job_owners = controller.get_unresolved_job_handles()
        self.assertEqual(len(proc_owners), 1)
        self.assertEqual(len(job_owners), 1)
        proc_owner = proc_owners[0]
        job_owner = job_owners[0]

        try:
            self.assertEqual(kernel32.WaitForSingleObject(proc_owner.handle, 0), WAIT_TIMEOUT)

            # First reconciliation: job_owner is safely closed and settled, but proc_owner is still running
            # so proc_owner is NOT settled and child lease is NOT released.
            settled = controller.reconcile_unresolved_resources()
            self.assertEqual(settled, 1)  # Only Job Object settled
            self.assertEqual(controller.get_unresolved_count(), 1)  # proc_owner remains unresolved
            self.assertGreaterEqual(manager.active_children, 1)

            # Attempt cleanup while lease is active -> must refuse and preserve staging directory
            refused = manager.cleanup()
            self.assertEqual(refused["state"], "REFUSED_ACTIVE_CHILDREN")
            self.assertIsNotNone(manager.stage_root)
            self.assertTrue(manager.stage_root.exists())

            # Wait for KILL_ON_JOB_CLOSE termination to complete
            self.assertEqual(kernel32.WaitForSingleObject(proc_owner.handle, 5000), WAIT_OBJECT_0)

            # Now reconcile -> confirms termination, releases lease, and settles process handle
            settled_proc = controller.reconcile_unresolved_resources()
            self.assertEqual(settled_proc, 1)
            self.assertEqual(controller.get_unresolved_count(), 0)
            self.assertEqual(manager.active_children, 0)

            # Final cleanup succeeds
            cleaned = manager.cleanup()
            self.assertEqual(cleaned["state"], "CLEANED")
        finally:
            if proc_owner and not proc_owner.is_confirmed_closed():
                kernel32.TerminateProcess(proc_owner.handle, 0)
                kernel32.WaitForSingleObject(proc_owner.handle, 2000)
            controller.reconcile_unresolved_resources()
            if manager.active_children == 0:
                manager.cleanup()


    def test_harness_safe_recovery_never_force_releases_active_leases_on_uncertainty(self):
        """Emergency recovery never force-releases leases or deletes runtime if termination remains unconfirmed."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        manager = get_appcontainer_manager()

        res = controller.execute_request(
            self.request,
            _inject_terminate_process_failure=True,
            _inject_termination_wait_timeout=True,
            _inject_job_close_failure=True,
        )
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)

        proc_owners = [h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)]
        job_owners = controller.get_unresolved_job_handles()
        proc_owner = proc_owners[0]
        job_owner = job_owners[0]

        # Simulate safe emergency recovery under uncertain termination (Job close failure simulated)
        emergency_state = None
        try:
            # Reconcile without closing Job (child remains alive)
            controller.reconcile_unresolved_resources()
            if manager.active_children == 0:
                manager.cleanup()
            else:
                emergency_state = "ACTIVE_LEASES_RETAINED_TERMINATION_UNCONFIRMED"
        finally:
            # Verify the invariant: lease was NOT force-released, profile was NOT deleted
            self.assertEqual(emergency_state, "ACTIVE_LEASES_RETAINED_TERMINATION_UNCONFIRMED")
            self.assertGreaterEqual(manager.active_children, 1)
            self.assertTrue(manager.stage_root.exists())

            # Now safely terminate and reconcile
            job_owner.close(_inject_failure=False)
            kernel32.WaitForSingleObject(proc_owner.handle, 5000)
            controller.reconcile_unresolved_resources()
            self.assertEqual(manager.active_children, 0)
            cleaned = manager.cleanup()
            self.assertEqual(cleaned["state"], "CLEANED")





class TestWindowsCancellationAndHandleOwnership(unittest.TestCase):
    """Test L: Failure handling for IPC cancellation and strict handle ownership."""

    def test_duplicate_handle_failure_aborts_before_write(self):
        """If DuplicateHandle fails, WriteFile is never entered, request fails closed cleanly."""
        controller = WorkerController()
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req, _inject_duplicate_handle_failure=True)

        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNotNone(controller._last_write_info)
        self.assertFalse(controller._last_write_info["duplicate_handle_success"])
        self.assertFalse(controller._last_write_info["write_entered"])
        self.assertFalse(controller._last_write_info["cancellation_requested"])
        self.assertTrue(controller._last_write_info["writer_exited"])
        self.assertTrue(controller._last_write_info["all_handles_safely_released"])
        self.assertEqual(controller._last_write_info["write_file_status"], "DUPLICATE_HANDLE_FAILED")

    def test_cancel_synchronous_io_failure_handled_safely(self):
        """If CancelSynchronousIo returns False, telemetry records failure and worker is terminated."""
        non_reading_cmd = f'"{sys.executable}" -c "import time; time.sleep(10)"'
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=non_reading_cmd,
            _stdin_pipe_buffer_size=1024,
        )
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=" + "1" * 4000,
        }
        res = controller.execute_request(req, _inject_cancel_io_failure=True)

        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertIsNotNone(controller._last_write_info)
        self.assertTrue(controller._last_write_info["cancellation_requested"])
        self.assertFalse(controller._last_write_info["cancel_synchronous_io_return"])
        self.assertEqual(controller._last_write_info["cancel_synchronous_io_last_error"], 1168)
        # TerminateProcess caused child pipe break, allowing writer thread to exit safely
        self.assertTrue(controller._last_write_info["writer_exited"])
        self.assertTrue(controller._last_write_info["all_handles_safely_released"])

    def test_delayed_writer_termination_quarantines_handle(self):
        """If writer thread does not exit within join deadline, handle is not closed and cleanup is not falsely claimed."""
        non_reading_cmd = f'"{sys.executable}" -c "import time; time.sleep(10)"'
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=non_reading_cmd,
            _stdin_pipe_buffer_size=1024,
        )
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "x=" + "1" * 4000,
        }
        res = controller.execute_request(req, _inject_writer_join_timeout=True)

        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertFalse(res.get("error", {}).get("details", {}).get("writer_exited"))
        self.assertIsNotNone(controller._last_write_info)
        self.assertFalse(controller._last_write_info["writer_exited"])
        self.assertFalse(controller._last_write_info["all_handles_safely_released"])

    def test_no_double_close_on_pipe_handle(self):
        """Verify that controller pipe handles are closed exactly once, never double-closed."""
        closed_handles = []
        original_close_handle = kernel32.CloseHandle

        def _tracking_close_handle(handle):
            if handle and handle != wintypes.HANDLE(0).value and handle != wintypes.HANDLE(-1).value:
                closed_handles.append(handle if isinstance(handle, int) else handle.value)
            return original_close_handle(handle)

        with mock.patch.object(kernel32, "CloseHandle", side_effect=_tracking_close_handle):
            controller = WorkerController(
                timeout_sec=0.2,
                _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
                _stdin_pipe_buffer_size=1024,
            )
            req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000}
            res = controller.execute_request(req)
            self.assertEqual(res["status"], WORKER_TIMEOUT)

        # Check for duplicate handle IDs in closed_handles
        duplicates = [h for h in closed_handles if closed_handles.count(h) > 1]
        self.assertEqual(duplicates, [], f"Detected double-closed handles: {duplicates}")

    def test_independent_repeated_requests_reset_telemetry(self):
        """Repeated requests on the same controller reset telemetry cleanly without stale state."""
        controller = WorkerController(
            timeout_sec=0.2,
            _stdin_pipe_buffer_size=1024,
        )
        # Warmup request to initialize lazy Win32 DLL structures
        controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
        time.sleep(0.5)
        controller.settle_quarantine(timeout=0.5)
        import gc
        gc.collect()

        handles_start = get_current_process_handle_count()

        # Request 1: triggers timeout with quarantined handle on the controller
        res1 = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _inject_writer_join_timeout=True,
        )
        self.assertEqual(res1["status"], WORKER_TIMEOUT)
        self.assertTrue(controller._last_write_info["cancellation_requested"])
        self.assertFalse(controller._last_write_info["writer_exited"])
        self.assertFalse(controller._last_write_info["all_handles_safely_released"])
        self.assertTrue(controller._last_write_info["handle_quarantined"])

        # Verify quarantine record was added to controller
        recs1 = controller.get_quarantine_records()
        self.assertGreaterEqual(len(recs1), 1)

        # Allow writer thread to finish sleeping
        time.sleep(0.4)

        # Request 2: normal solve ON THE SAME CONTROLLER INSTANCE
        res2 = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"},
            timeout_sec=2.0,
        )
        self.assertEqual(res2["outcome"], "SUCCESS")
        self.assertIsNotNone(controller._last_write_info)
        self.assertFalse(controller._last_write_info["cancellation_requested"])
        self.assertFalse(controller._last_write_info["write_blocked_at_deadline"])
        self.assertTrue(controller._last_write_info["writer_exited"])
        self.assertTrue(controller._last_write_info["all_handles_safely_released"])
        self.assertFalse(controller._last_write_info["handle_quarantined"])

        # Prior quarantine records are preserved on the same controller and settled
        recs2 = controller.get_quarantine_records()
        self.assertGreaterEqual(len(recs2), 1)
        self.assertTrue(recs2[0]["settled"])
        self.assertTrue(recs2[0]["handle_closed"])

        # Allow worker process tombstone release and settle quarantine
        time.sleep(0.5)
        controller.settle_quarantine(timeout=0.5)
        gc.collect()

        # Process handle count remains strictly stable
        handles_end = get_current_process_handle_count()
        self.assertEqual(handles_end - handles_start, 0, f"Handle leak: start={handles_start}, end={handles_end}")

    def test_quarantined_handle_released_after_delayed_writer_eventual_exit(self):
        """Quarantined handle is safely released when delayed writer thread eventually finishes."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _stdin_pipe_buffer_size=1024,
        )
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _inject_writer_join_timeout=True,
        )
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertTrue(res.get("error", {}).get("details", {}).get("handle_quarantined"))

        # Verify active quarantine record exists
        recs = controller.get_quarantine_records()
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertFalse(rec["settled"])

        # Wait for writer thread to finish sleep(0.3)
        time.sleep(0.4)

        # Reaping/settling verifies handle is closed and marks record settled
        settled_count = controller.settle_quarantine(timeout=0.1)
        self.assertGreaterEqual(settled_count, 0)
        recs_after = controller.get_quarantine_records()
        self.assertTrue(recs_after[0]["settled"])
        self.assertTrue(recs_after[0]["handle_closed"])
        self.assertEqual(controller.get_active_quarantine_count(), 0)

    def test_repeated_write_timeouts_no_kernel_handle_leak(self):
        """Repeated write timeouts on the same controller do not leak Windows kernel handles (0 delta)."""
        controller = WorkerController(
            timeout_sec=0.15,
            _stdin_pipe_buffer_size=1024,
        )
        # Warmup single request
        controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
        time.sleep(0.1)
        controller.settle_quarantine(timeout=0.2)
        import gc
        gc.collect()

        baseline_handles = get_current_process_handle_count()
        self.assertGreater(baseline_handles, 0)

        # Execute 5 repeated write timeouts with quarantined handles
        for _ in range(5):
            res = controller.execute_request(
                {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
                _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
                _inject_writer_join_timeout=True,
            )
            self.assertEqual(res["status"], WORKER_TIMEOUT)

        # Allow all writer threads to finish sleeping
        time.sleep(0.5)
        controller.settle_quarantine(timeout=0.5)
        gc.collect()

        # Settle check: all records settled
        self.assertEqual(controller.get_active_quarantine_count(), 0)

        final_handles = get_current_process_handle_count()
        handle_diff = final_handles - baseline_handles
        self.assertEqual(handle_diff, 0, f"Handle leak detected: baseline={baseline_handles}, final={final_handles}")

    def test_normal_write_completion_guards_active_writer(self):
        """Normal write completion fails closed and quarantines handle if writer thread is still active."""
        controller = WorkerController(timeout_sec=1.0)
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"},
            _inject_normal_write_join_timeout=True,
        )
        # Must fail closed instead of returning premature SUCCESS with active writer thread
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertTrue(res.get("error", {}).get("details", {}).get("handle_quarantined"))

        # Verify handle was quarantined
        self.assertEqual(controller.get_active_quarantine_count(), 1)

        # Wait for thread to finish delayed exit
        time.sleep(0.4)
        controller.settle_quarantine(timeout=0.1)
        self.assertEqual(controller.get_active_quarantine_count(), 0)
        self.assertTrue(controller.get_quarantine_records()[-1]["settled"])

    def test_error_envelope_deterministic_fallback_on_serialization_failure(self):
        """_build_controller_error returns a minimal deterministic envelope when JSON serialization fails."""
        from mke_product.worker.controller import _build_controller_error
        # Non-serializable object inside details
        fallback = _build_controller_error(
            "ERR_INTERNAL",
            "Initial failure",
            details={"unserializable": object()},
            operation="SOLVE",
        )
        self.assertEqual(fallback["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(fallback["status"], "ERR_INTERNAL")
        self.assertEqual(fallback["operation"], "SOLVE")
        self.assertEqual(fallback["error"]["message"], "Error serialization failed.")
        serialized = json.dumps(fallback).encode("utf-8")
        self.assertLessEqual(len(serialized), IPC_MAX_RESPONSE_BYTES)

    def test_writer_setup_hang_quarantines_handle(self):
        """Writer setup hang/timeout quarantines handle and avoids premature close while writer is active."""
        controller = WorkerController(timeout_sec=1.0)
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"},
            _inject_writer_setup_hang=True,
        )
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertTrue(res.get("error", {}).get("details", {}).get("setup_timed_out"))
        self.assertTrue(res.get("error", {}).get("details", {}).get("handle_quarantined"))

        # Active quarantine queue contains 1 record
        self.assertEqual(controller.get_active_quarantine_count(), 1)
        recs = controller.get_quarantine_records()
        self.assertEqual(len(recs), 1)
        self.assertFalse(recs[0]["settled"])

        # Settle once writer thread completes its sleep
        time.sleep(0.2)
        controller.settle_quarantine(timeout=0.1)
        self.assertEqual(controller.get_active_quarantine_count(), 0)
        self.assertTrue(controller.get_quarantine_records()[0]["settled"])
        self.assertTrue(controller.get_quarantine_records()[0]["handle_closed"])

    def test_quarantine_capacity_limit_rejects_requests(self):
        """Active quarantine queue bounded at MAX_ACTIVE_QUARANTINE (32) rejects new requests with WORKER_RESOURCE_EXHAUSTED."""
        from mke_product.worker.controller import (
            MAX_ACTIVE_QUARANTINE,
            QuarantineRecord,
            SafePipeHandle,
            SafeThreadHandle,
        )
        controller = WorkerController(timeout_sec=1.0)

        created_pipes = []
        threads = []

        try:
            with controller._quarantine_lock:
                for i in range(MAX_ACTIVE_QUARANTINE):
                    sa = SECURITY_ATTRIBUTES()
                    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
                    sa.bInheritHandle = False
                    h_read = wintypes.HANDLE()
                    h_write = wintypes.HANDLE()
                    kernel32.CreatePipe(ctypes.byref(h_read), ctypes.byref(h_write), ctypes.byref(sa), 0)
                    created_pipes.append((h_read, h_write))

                    pipe_owner = SafePipeHandle(h_write)
                    pipe_owner.quarantine()

                    th = threading.Thread(target=lambda: time.sleep(10), daemon=True)
                    th.start()
                    threads.append(th)

                    controller._quarantine_counter += 1
                    rec = QuarantineRecord(
                        record_id=controller._quarantine_counter,
                        thread=th,
                        handle=pipe_owner,
                        thread_handle=None,
                        created_at=time.monotonic(),
                        settled=False,
                        settled_at=None,
                        handle_val=int(h_write.value),
                        thread_handle_val=None,
                        handle_closed=False,
                        thread_handle_closed=True,
                        handle_close_error=0,
                        thread_handle_close_error=0,
                    )
                    controller._quarantine.append(rec)

            self.assertEqual(controller.get_active_quarantine_count(), MAX_ACTIVE_QUARANTINE)

            # Attempt to execute request must be rejected with WORKER_RESOURCE_EXHAUSTED
            res = controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
            self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
            self.assertIn("capacity exceeded", res.get("error", {}).get("message", "").lower())
        finally:
            with controller._quarantine_lock:
                for rec in controller._quarantine:
                    if rec.handle:
                        rec.handle.close()
                controller._quarantine.clear()
            for h_r, h_w in created_pipes:
                safe_close_handle(h_r)
                safe_close_handle(h_w)

    def test_safe_win32_handle_four_state_lifecycle(self):
        """SafeWin32Handle transitions through distinct states: OPEN -> CLOSING -> CONFIRMED_CLOSED / CLOSE_FAILED."""
        from mke_product.worker.controller import (
            SafePipeHandle,
            STATE_OPEN,
            STATE_CLOSING,
            STATE_CONFIRMED_CLOSED,
            STATE_CLOSE_FAILED,
        )

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.bInheritHandle = False
        h_read = wintypes.HANDLE()
        h_write = wintypes.HANDLE()
        kernel32.CreatePipe(ctypes.byref(h_read), ctypes.byref(h_write), ctypes.byref(sa), 0)

        pipe = SafePipeHandle(h_write)
        self.assertEqual(pipe.state, STATE_OPEN)
        self.assertFalse(pipe.is_confirmed_closed())
        self.assertFalse(pipe.is_close_failed())

        # Test failure injection
        pipe._inject_close_failure = True
        ok = pipe.close()
        self.assertFalse(ok)
        self.assertEqual(pipe.state, STATE_CLOSE_FAILED)
        self.assertFalse(pipe.is_confirmed_closed())
        self.assertTrue(pipe.is_close_failed())
        self.assertEqual(pipe.close_success, False)
        self.assertNotEqual(pipe.close_error, 0)
        # Handle reference is preserved on failure
        self.assertIsNotNone(pipe.raw_handle)

        # Clear failure injection and retry close: successfully closes
        pipe._inject_close_failure = False
        ok2 = pipe.close()
        self.assertTrue(ok2)
        self.assertEqual(pipe.state, STATE_CONFIRMED_CLOSED)
        self.assertTrue(pipe.is_confirmed_closed())
        self.assertFalse(pipe.is_close_failed())
        self.assertEqual(pipe.close_success, True)
        self.assertEqual(pipe.close_error, 0)
        self.assertIsNone(pipe.raw_handle)

        # Idempotent close after confirmed closed
        ok3 = pipe.close()
        self.assertTrue(ok3)
        self.assertEqual(pipe.state, STATE_CONFIRMED_CLOSED)

        safe_close_handle(h_read)

    def test_injected_close_handle_failure_preserves_quarantine_diagnostics(self):
        """When CloseHandle fails on quarantined handle, quarantine record remains unsettled with diagnostics."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _stdin_pipe_buffer_size=1024,
        )
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _inject_writer_join_timeout=True,
            _inject_close_handle_failure=True,
        )
        self.assertEqual(res["status"], WORKER_TIMEOUT)
        self.assertTrue(res.get("error", {}).get("details", {}).get("handle_quarantined"))

        # Wait for writer thread to finish
        time.sleep(0.4)

        # Settle attempt will try to close the handle, but close failure is injected
        settled_count = controller.settle_quarantine(timeout=0.1)
        self.assertEqual(settled_count, 0)

        # Record remains UNSETTLED and diagnostics are preserved
        recs = controller.get_quarantine_records()
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertFalse(rec["settled"])
        self.assertFalse(rec["handle_closed"])
        self.assertNotEqual(rec["handle_close_error"], 0)
        self.assertIsNotNone(rec["handle_val"])

        # Now remove failure injection on both handles and retry settlement
        with controller._quarantine_lock:
            for r in controller._quarantine:
                if r.handle:
                    r.handle._inject_close_failure = False
                if r.thread_handle:
                    r.thread_handle._inject_close_failure = False

        settled_count2 = controller.settle_quarantine(timeout=0.1)
        self.assertEqual(settled_count2, 1)
        self.assertEqual(controller.get_active_quarantine_count(), 0)
        self.assertTrue(controller.get_quarantine_records()[0]["settled"])
        self.assertTrue(controller.get_quarantine_records()[0]["handle_closed"])

    def test_normal_execution_pipe_close_failure_quarantines_and_fails_closed(self):
        """Normal completion with injected pipe close failure fails closed and registers quarantine diagnostics."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req, _inject_close_handle_failure=True)

        # Must NOT return SUCCESS; must fail closed with WORKER_RESOURCE_EXHAUSTED
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertTrue(res.get("error", {}).get("details", {}).get("handle_quarantined"))

        # Quarantine ledger contains unclosed handle records (for thread handle and pipe handle)
        recs = controller.get_quarantine_records()
        self.assertGreaterEqual(len(recs), 1)
        unsettled = [r for r in recs if not r["settled"]]
        self.assertGreaterEqual(len(unsettled), 1)
        for u in unsettled:
            if u["handle_val"]:
                self.assertFalse(u["handle_closed"])
                self.assertNotEqual(u["handle_close_error"], 0)
            if u["thread_handle_val"]:
                self.assertFalse(u["thread_handle_closed"])
                self.assertNotEqual(u["thread_handle_close_error"], 0)

        # Cleanup: release failure injection and settle
        with controller._quarantine_lock:
            for r in controller._quarantine:
                if r.handle:
                    r.handle._inject_close_failure = False
                if r.thread_handle:
                    r.thread_handle._inject_close_failure = False
        controller.settle_quarantine(timeout=0.1)
        self.assertEqual(controller.get_active_quarantine_count(), 0)

    def test_actual_late_duplication_sequence_exit_after_quarantine(self):
        """Interleaving D (Actual Late Duplication): Writer paused at barrier, controller quarantines before releasing writer."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _stdin_pipe_buffer_size=1024,
        )
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _inject_late_duplicate_handle=True,
        )
        self.assertEqual(res["status"], WORKER_STARTUP_FAILURE)
        self.assertIsNotNone(controller._last_write_info)
        self.assertTrue(controller._last_write_info["handle_quarantined"])

        # Immediately after execute_request returns, quarantine record is registered and active
        self.assertEqual(controller.get_active_quarantine_count(), 1)
        recs_initial = controller.get_quarantine_records()
        self.assertEqual(len(recs_initial), 1)
        self.assertFalse(recs_initial[0]["settled"])

        # Settle quarantine: writer finishes post-abort duplicate handle, closes both handles, and exits
        settled_count = controller.settle_quarantine(timeout=0.5)
        self.assertEqual(settled_count, 1)
        self.assertEqual(controller.get_active_quarantine_count(), 0)

        info = controller._last_write_info
        self.assertTrue(info["duplicate_handle_invoked"])
        self.assertGreater(info["duplicate_handle_raw_val"], 0)
        self.assertEqual(info["write_file_status"], "ABORTED_BEFORE_WRITE")
        self.assertEqual(info["bytes_written"], 0)

        recs = controller.get_quarantine_records()
        self.assertTrue(recs[0]["settled"])
        self.assertTrue(recs[0]["handle_closed"])
        self.assertTrue(recs[0]["thread_handle_closed"])
        self.assertGreater(recs[0]["thread_handle_val"], 0)

    def test_job_object_close_failure_fails_closed_and_preserves_diagnostics(self):
        """Job Object CloseHandle failure fails closed with WORKER_RESOURCE_EXHAUSTED and preserves unclosed handle ownership."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req, _inject_job_close_failure=True)

        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertEqual(res.get("error", {}).get("details", {}).get("job_close_error"), 5)
        self.assertIn("job_object", res.get("error", {}).get("details", {}).get("cleanup_failures", {}))

        # Verify resource ownership was NOT lost: Job Object handle remains tracked and open in test double
        self.assertIsNotNone(controller._last_job_owner)
        job_owner = controller._last_job_owner
        raw_val = job_owner.raw_value()
        self.assertGreater(raw_val, 0)
        self.assertTrue(job_owner.is_close_failed())
        self.assertEqual(job_owner.close_error, 5)
        self.assertFalse(job_owner.is_confirmed_closed())
        self.assertEqual(len(controller.get_unresolved_job_handles()), 1)

        # Confirm native handle status using Win32 API: handle is genuinely OPEN in Windows kernel
        flags = wintypes.DWORD()
        is_handle_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_val), ctypes.byref(flags))
        self.assertTrue(bool(is_handle_valid))

        # Automatic reconciliation on subsequent request WITHOUT manually closing the handle in the test
        res2 = controller.execute_request(req)
        self.assertEqual(res2["outcome"], "SUCCESS")
        self.assertEqual(res2["status"], "UNIQUE_ROOT")
        self.assertEqual(len(controller.get_unresolved_job_handles()), 0)
        self.assertTrue(job_owner.is_confirmed_closed())

        # Confirm native handle status: handle is now CONFIRMED CLOSED in Windows kernel
        is_handle_still_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_val), ctypes.byref(flags))
        self.assertFalse(bool(is_handle_still_valid))
        self.assertEqual(ctypes.get_last_error(), 6)  # ERROR_INVALID_HANDLE

    def test_stdout_pipe_close_failure_fails_closed_and_preserves_ownership(self):
        """Stdout pipe close failure fails closed and preserves unclosed handle in persistent ledger."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

        res = controller.execute_request(req, _inject_stdout_close_failure=True)
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        self.assertIn("stdout_read", res.get("error", {}).get("details", {}).get("cleanup_failures", {}))

        # Verify handle is tracked in unresolved handles ledger
        unresolved = controller.get_unresolved_handles()
        self.assertEqual(len(unresolved), 1)
        pipe_owner = unresolved[0]
        raw_val = pipe_owner.raw_value()
        self.assertGreater(raw_val, 0)
        self.assertTrue(pipe_owner.is_close_failed())

        # Native verification: handle is genuinely OPEN in OS
        flags = wintypes.DWORD()
        is_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_val), ctypes.byref(flags))
        self.assertTrue(bool(is_valid))

        # Subsequent request automatically reconciles without manual intervention
        res2 = controller.execute_request(req)
        self.assertEqual(res2["outcome"], "SUCCESS")
        self.assertEqual(len(controller.get_unresolved_handles()), 0)
        self.assertTrue(pipe_owner.is_confirmed_closed())

        # Native verification: handle is now confirmed closed
        is_still_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_val), ctypes.byref(flags))
        self.assertFalse(bool(is_still_valid))
        self.assertEqual(ctypes.get_last_error(), 6)

    def test_process_and_thread_handle_close_failure_fails_closed_and_preserves_ownership(self):
        """Process and primary thread handle close failure fails closed and preserves ownership."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

        res = controller.execute_request(
            req,
            _inject_process_close_failure=True,
            _inject_thread_close_failure=True,
        )
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        self.assertFalse(res.get("error", {}).get("details", {}).get("safe_cleanup"))
        failures = res.get("error", {}).get("details", {}).get("cleanup_failures", {})
        self.assertIn("process_handle", failures)
        self.assertIn("thread_handle", failures)

        # Verify both handles tracked in unresolved ledger
        unresolved = controller.get_unresolved_handles()
        self.assertEqual(len(unresolved), 2)

        # Subsequent request automatically reconciles without manual intervention
        res2 = controller.execute_request(req)
        self.assertEqual(res2["outcome"], "SUCCESS")
        self.assertEqual(len(controller.get_unresolved_handles()), 0)

    def test_safe_win32_handle_native_handle_verification(self):
        """SafeWin32Handle verifies genuine native handle state transitions with Win32 APIs."""
        raw_event = kernel32.CreateEventW(None, True, False, None)
        self.assertGreater(raw_event, 0)

        # Wrap in SafeWin32Handle with injected failure
        h_safe = SafeWin32Handle(raw_event, _inject_close_failure=True)
        self.assertTrue(h_safe.is_open())
        self.assertEqual(h_safe.raw_value(), raw_event)

        # Close with injected failure: does NOT close OS handle, transitions to CLOSE_FAILED
        ok = h_safe.close()
        self.assertFalse(ok)
        self.assertTrue(h_safe.is_close_failed())
        self.assertEqual(h_safe.close_error, 5)
        self.assertEqual(h_safe.close_evidence, CLOSE_EVIDENCE_INJECTED_BEFORE_CLOSE)
        self.assertFalse(h_safe.native_close_attempted)
        self.assertEqual(h_safe.raw_value(), raw_event)

        # Verify with OS API: handle is still valid and open
        flags = wintypes.DWORD()
        is_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_event), ctypes.byref(flags))
        self.assertTrue(bool(is_valid))

        # Reconcile / close cleanly without failure injection
        ok2 = h_safe.close(_inject_failure=False)
        self.assertTrue(ok2)
        self.assertTrue(h_safe.is_confirmed_closed())
        self.assertEqual(h_safe.close_error, 0)
        self.assertEqual(h_safe.close_evidence, CLOSE_EVIDENCE_CONFIRMED_CLOSED)

        # Verify with OS API: handle is now invalid / closed
        is_still_valid = kernel32.GetHandleInformation(wintypes.HANDLE(raw_event), ctypes.byref(flags))
        self.assertFalse(bool(is_still_valid))
        self.assertEqual(ctypes.get_last_error(), 6)

        # Double close is idempotent and does not error
        ok3 = h_safe.close()
        self.assertTrue(ok3)

    def test_genuine_native_close_failure_is_not_blindly_retried(self):
        """A protected real handle produces native failure and requires explicit recovery."""
        raw_event = kernel32.CreateEventW(None, True, False, None)
        self.assertGreater(raw_event, 0)
        owner = SafeWin32Handle(raw_event)

        protected = kernel32.SetHandleInformation(
            wintypes.HANDLE(raw_event),
            HANDLE_FLAG_PROTECT_FROM_CLOSE,
            HANDLE_FLAG_PROTECT_FROM_CLOSE,
        )
        self.assertTrue(bool(protected))

        self.assertFalse(owner.close())
        self.assertEqual(owner.close_evidence, CLOSE_EVIDENCE_NATIVE_FAILURE)
        self.assertTrue(owner.native_close_attempted)
        self.assertEqual(owner.validity_before_close, HANDLE_VALID)
        self.assertEqual(owner.validity_after_close, HANDLE_VALID)
        first_attempts = owner.close_attempts

        flags = wintypes.DWORD()
        self.assertTrue(bool(kernel32.GetHandleInformation(owner.handle, ctypes.byref(flags))))
        self.assertTrue(flags.value & HANDLE_FLAG_PROTECT_FROM_CLOSE)

        # The persistent ledger does not issue a second native CloseHandle.
        controller = WorkerController()
        controller._unresolved_handles.append(owner)
        self.assertEqual(controller.reconcile_unresolved_resources(), 0)
        self.assertIn(owner, controller.get_unresolved_handles())
        self.assertEqual(owner.close_attempts, first_attempts)

        unprotected = kernel32.SetHandleInformation(
            owner.handle,
            HANDLE_FLAG_PROTECT_FROM_CLOSE,
            0,
        )
        self.assertTrue(bool(unprotected))
        # Correcting the external condition is insufficient without explicit authorization.
        self.assertFalse(owner.close())
        self.assertEqual(owner.close_attempts, first_attempts)
        self.assertTrue(owner.recover_native_close())
        self.assertEqual(owner.close_evidence, CLOSE_EVIDENCE_CONFIRMED_CLOSED)
        self.assertTrue(owner.is_confirmed_closed())
        self.assertEqual(controller.reconcile_unresolved_resources(), 1)
        self.assertEqual(controller.get_unresolved_count(), 0)

        ctypes.set_last_error(0)
        self.assertFalse(bool(kernel32.GetHandleInformation(wintypes.HANDLE(raw_event), ctypes.byref(flags))))
        self.assertEqual(ctypes.get_last_error(), 6)

    def test_invalid_stale_handle_is_recorded_not_closed_or_retried(self):
        """A stale numeric value is not treated as proof of ownership or successful cleanup."""
        raw_event = kernel32.CreateEventW(None, True, False, None)
        self.assertGreater(raw_event, 0)
        owner = SafeWin32Handle(raw_event)
        # Construct the owner first so its lock allocation cannot reuse the just-closed value.
        self.assertTrue(bool(kernel32.CloseHandle(wintypes.HANDLE(raw_event))))

        self.assertFalse(owner.close())
        self.assertEqual(owner.close_evidence, CLOSE_EVIDENCE_INVALID_HANDLE)
        self.assertEqual(owner.validity_before_close, HANDLE_INVALID)
        self.assertFalse(owner.native_close_attempted)
        self.assertFalse(owner.is_confirmed_closed())
        self.assertEqual(owner.close_error, 6)
        first_attempts = owner.close_attempts
        self.assertFalse(owner.close(_inject_failure=False))
        self.assertEqual(owner.close_attempts, first_attempts)

    def test_combined_uncertain_termination_and_job_close_failure_fails_closed(self):
        """Unconfirmed termination plus Job close failure retains containment ownership."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(
            req,
            _inject_termination_wait_timeout=True,
            _inject_job_close_failure=True,
        )

        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        details = res["error"]["details"]
        self.assertFalse(details["safe_cleanup"])
        self.assertIn("process_termination", details["cleanup_failures"])
        self.assertIn("job_object", details["cleanup_failures"])
        evidence = details["process_termination"]
        self.assertEqual(evidence["state"], "TERMINATION_UNCERTAIN_OR_FAILED")
        self.assertEqual(evidence["termination_request_state"], "REQUESTED_SUCCESSFULLY")
        self.assertEqual(evidence["termination_confirmation_state"], "UNCERTAIN_OR_FAILED")
        self.assertTrue(evidence["termination_requested"])
        self.assertTrue(evidence["termination_request_succeeded"])
        self.assertFalse(evidence["termination_confirmed"])
        self.assertEqual(evidence["wait_result"], WAIT_TIMEOUT)

        jobs = controller.get_unresolved_job_handles()
        handles = controller.get_unresolved_handles()
        self.assertEqual(len(jobs), 1)
        process_owners = [h for h in handles if isinstance(h, SafeProcessHandle)]
        self.assertEqual(len(process_owners), 1)
        process_owner = process_owners[0]
        self.assertEqual(process_owner.close_blocked_reason, "PROCESS_TERMINATION_UNCONFIRMED")

        flags = wintypes.DWORD()
        self.assertTrue(bool(kernel32.GetHandleInformation(jobs[0].handle, ctypes.byref(flags))))
        self.assertTrue(bool(kernel32.GetHandleInformation(process_owner.handle, ctypes.byref(flags))))

        # The real termination request was issued; establish raw evidence before recovery.
        self.assertEqual(kernel32.WaitForSingleObject(process_owner.handle, 5000), WAIT_OBJECT_0)
        controller.reconcile_unresolved_resources()
        self.assertEqual(controller.get_unresolved_count(), 0)
        self.assertTrue(jobs[0].is_confirmed_closed())
        self.assertTrue(process_owner.is_confirmed_closed())

    def test_failed_termination_wait_is_not_confirmation(self):
        """WAIT_FAILED is retained as uncertainty until Job containment recovery completes."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(
            req,
            _inject_termination_wait_failure=True,
            _inject_job_close_failure=True,
        )

        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        evidence = res["error"]["details"]["process_termination"]
        self.assertEqual(evidence["state"], "TERMINATION_UNCERTAIN_OR_FAILED")
        self.assertEqual(evidence["termination_request_state"], "REQUESTED_SUCCESSFULLY")
        self.assertEqual(evidence["termination_confirmation_state"], "UNCERTAIN_OR_FAILED")
        self.assertEqual(evidence["wait_result"], 0xFFFFFFFF)
        self.assertFalse(evidence["termination_confirmed"])
        process_owner = next(
            h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)
        )
        self.assertEqual(kernel32.WaitForSingleObject(process_owner.handle, 5000), WAIT_OBJECT_0)
        controller.reconcile_unresolved_resources()
        self.assertEqual(controller.get_unresolved_count(), 0)

    def test_failed_termination_request_retains_job_containment(self):
        """A failed termination request leaves the live child owned by the unresolved Job."""
        controller = WorkerController(
            timeout_sec=0.2,
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
        )
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(
            req,
            _inject_terminate_process_failure=True,
            _inject_termination_wait_timeout=True,
            _inject_job_close_failure=True,
        )

        self.assertEqual(res["status"], WORKER_RESOURCE_EXHAUSTED)
        evidence = res["error"]["details"]["process_termination"]
        self.assertEqual(evidence["termination_request_state"], "REQUEST_FAILED")
        self.assertEqual(evidence["termination_confirmation_state"], "UNCERTAIN_OR_FAILED")
        self.assertFalse(evidence["termination_request_succeeded"])
        self.assertFalse(evidence["termination_confirmed"])
        self.assertEqual(evidence["terminate_error"], 5)

        job_owner = controller.get_unresolved_job_handles()[0]
        process_owner = next(
            h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)
        )
        self.assertEqual(kernel32.WaitForSingleObject(process_owner.handle, 0), WAIT_TIMEOUT)

        # Explicitly recover the pre-call injected Job close. KILL_ON_JOB_CLOSE then
        # terminates the still-contained child; only after proof may its handle close.
        self.assertTrue(job_owner.close(_inject_failure=False))
        self.assertEqual(kernel32.WaitForSingleObject(process_owner.handle, 5000), WAIT_OBJECT_0)
        controller.reconcile_unresolved_resources()
        self.assertEqual(controller.get_unresolved_count(), 0)

    def test_recovery_following_cleanup_failure(self):
        """WorkerController successfully recovers and executes subsequent requests on the same instance after cleanup failure."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

        # Request 1: Injected Job Object close failure fails closed
        res1 = controller.execute_request(req, _inject_job_close_failure=True)
        self.assertEqual(res1["status"], WORKER_RESOURCE_EXHAUSTED)
        self.assertFalse(res1.get("error", {}).get("details", {}).get("safe_cleanup"))

        # Request 2: Normal request on the same controller instance succeeds cleanly WITHOUT ANY manual intervention
        res2 = controller.execute_request(req)
        self.assertEqual(res2["outcome"], "SUCCESS")
        self.assertEqual(res2["status"], "UNIQUE_ROOT")
        self.assertEqual(res2.get("root", {}).get("numerator"), "1")
        self.assertEqual(res2.get("root", {}).get("denominator"), "1")

    def test_persistent_job_ledger_tracks_multiple_unresolved_handles(self):
        """Persistent Job ledger maintains bounded tracking across multiple requests without orphaning handles."""
        controller = WorkerController(timeout_sec=2.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

        # Request 1: Injected Job close failure fails closed and records Job 1
        res1 = controller.execute_request(req, _inject_job_close_failure=True)
        self.assertEqual(res1["status"], WORKER_RESOURCE_EXHAUSTED)
        job1 = controller._last_job_owner
        self.assertIsNotNone(job1)
        raw_job1 = job1.raw_value()
        self.assertEqual(len(controller.get_unresolved_job_handles()), 1)

        # Now simulate permanent unclosable state on Job 1 by patching close to fail
        with mock.patch.object(job1, "close", return_value=False):
            # Request 2: Normal request fails closed because Job 1 cannot be reconciled
            res2 = controller.execute_request(req)
            self.assertEqual(res2["status"], WORKER_RESOURCE_EXHAUSTED)
            self.assertFalse(res2.get("error", {}).get("details", {}).get("safe_cleanup"))
            self.assertIn("unresolved native handle(s)", res2.get("error", {}).get("message", ""))
            # Job 1 is still tracked and not orphaned
            self.assertIn(job1, controller._unresolved_job_handles)

        # Request 3: When Job 1 is reconcilable, subsequent request succeeds cleanly
        res3 = controller.execute_request(req)
        self.assertEqual(res3["outcome"], "SUCCESS")
        self.assertEqual(len(controller.get_unresolved_job_handles()), 0)
        self.assertTrue(job1.is_confirmed_closed())

    def test_single_request_contract_concurrent_execution_rejected(self):
        """WorkerController rejects concurrent execute_request calls atomically with WORKER_RESOURCE_EXHAUSTED."""
        controller = WorkerController(timeout_sec=2.0)
        results = []

        def worker_req(eq, sleep_before=0.0):
            if sleep_before > 0:
                time.sleep(sleep_before)
            res = controller.execute_request(
                {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": eq}
            )
            results.append(res)

        # Thread 1 starts request that takes a moment
        t1 = threading.Thread(target=worker_req, args=("x=1", 0.0))
        # Thread 2 immediately attempts concurrent request
        t2 = threading.Thread(target=worker_req, args=("x=2", 0.001))

        t1.start()
        t2.start()
        t1.join(timeout=3.0)
        t2.join(timeout=3.0)

        self.assertEqual(len(results), 2)
        statuses = [r["status"] for r in results]
        outcomes = [r["outcome"] for r in results]
        # One must succeed and one must be rejected for concurrency violation
        self.assertIn("SUCCESS", outcomes)
        self.assertIn(WORKER_RESOURCE_EXHAUSTED, statuses)


if __name__ == "__main__":
    unittest.main()
