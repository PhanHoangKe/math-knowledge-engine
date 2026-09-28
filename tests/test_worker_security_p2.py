"""MKE PRODUCT — S4-B2/P2: Filesystem and Network Security Isolation Verification Suite.

Empirically verifies:
- Filesystem boundary restrictions (positive controls and negative AppContainer tests).
- Staged runtime immutability (write denial in stage_root/runtime and stage_root/src).
- Network boundary restrictions (TCP/UDP loopback denial, non-loopback WAN/LAN denial).
- AppContainer capability allowlist verification (strictly zero network capabilities).
- AppContainer token, SID, Job containment, and handle isolation invariants.
"""

import base64
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from typing import Optional, Tuple

if sys.platform != "win32":
    raise unittest.SkipTest("Windows AppContainer security tests require Windows operating system.")

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.worker.appcontainer import get_appcontainer_manager
from mke_product.worker.constants import (
    WORKER_PROTOCOL_FAILURE,
    WORKER_RESOURCE_EXHAUSTED,
    WORKER_STARTUP_FAILURE,
)
from mke_product.worker.controller import (
    SafeProcessHandle,
    SafeWin32Handle,
    WorkerController,
)
from mke_product.worker.win32 import kernel32


def _make_framed_probe_worker(code_body: str) -> str:
    """Build a robust self-contained worker command that executes code_body and returns framed JSON."""
    full_script = f"""
import base64, json, os, struct, sys

# Consume IPC request frame from controller
hdr = sys.stdin.buffer.read(4)
if len(hdr) == 4:
    (req_len,) = struct.unpack(">I", hdr)
    _ = sys.stdin.buffer.read(req_len)

probe_status = "UNKNOWN"
probe_details = {{}}

{code_body}

response_envelope = {{
    "schema_version": "{SCHEMA_VERSION}",
    "operation": "SOLVE",
    "outcome": "SUCCESS",
    "status": probe_status,
    "definedness": None,
    "is_provisional_evidence": False,
    "details": probe_details,
}}

raw_json = json.dumps(response_envelope, separators=(",", ":")).encode("utf-8")
sys.stdout.buffer.write(struct.pack(">I", len(raw_json)))
sys.stdout.buffer.write(raw_json)
sys.stdout.buffer.flush()
"""
    b64_script = base64.b64encode(full_script.encode("utf-8")).decode("ascii")
    runner = f'import base64; exec(base64.b64decode(b\\"{b64_script}\\").decode(\\"utf-8\\"))'
    return f'"{sys.executable}" -c "{runner}"'


class TestAppContainerFilesystemSecurity(unittest.TestCase):
    """Phase 2: Empirical Filesystem Isolation Tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mke-sec-test-")
        self.canary_path = Path(self.temp_dir.name) / "protected_canary.txt"
        self.canary_content = "CANARY_SECRET_DATA_12345"
        self.canary_path.write_text(self.canary_content, encoding="utf-8")

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _execute_worker_probe(self, code_body: str) -> dict:
        """Helper to run a Python snippet inside the real AppContainer worker."""
        worker_cmd = _make_framed_probe_worker(code_body)
        controller = WorkerController(timeout_sec=5.0, _worker_cmd=worker_cmd)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req)
        return res

    def test_filesystem_positive_control_host_reads_and_modifies_canary(self):
        """Positive Control: Unsandboxed host process has full access to the canary file."""
        self.assertTrue(self.canary_path.exists())
        read_data = self.canary_path.read_text(encoding="utf-8")
        self.assertEqual(read_data, self.canary_content)

        # Host can modify canary
        modified_data = "MODIFIED_BY_HOST_67890"
        self.canary_path.write_text(modified_data, encoding="utf-8")
        self.assertEqual(self.canary_path.read_text(encoding="utf-8"), modified_data)

    def test_filesystem_negative_worker_cannot_read_protected_canary(self):
        """Negative Test: AppContainer worker cannot read a protected canary in user/temp directory."""
        code = f"""
target = {str(self.canary_path)!r}
try:
    with open(target, "r") as f:
        data = f.read()
    probe_status = "NOT_ISOLATED"
    probe_details = {{"data": data}}
except PermissionError as ex:
    probe_status = "ACCESS_DENIED"
    probe_details = {{"error": "PermissionError", "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
        res = self._execute_worker_probe(code)
        self.assertEqual(res.get("status"), "ACCESS_DENIED", f"Unexpected access result: {res}")

    def test_filesystem_negative_worker_cannot_modify_protected_canary(self):
        """Negative Test: AppContainer worker cannot modify or overwrite a protected canary."""
        code = f"""
target = {str(self.canary_path)!r}
try:
    with open(target, "w") as f:
        f.write("TAMPERED_BY_SANDBOX")
    probe_status = "NOT_ISOLATED"
except PermissionError as ex:
    probe_status = "ACCESS_DENIED"
    probe_details = {{"error": "PermissionError", "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
        res = self._execute_worker_probe(code)
        self.assertEqual(res.get("status"), "ACCESS_DENIED", f"Unexpected modification result: {res}")
        # Verify canary was not modified on disk
        self.assertEqual(self.canary_path.read_text(encoding="utf-8"), self.canary_content)

    def test_filesystem_negative_worker_cannot_write_into_staged_runtime(self):
        """Negative Test: Staged runtime directory is read-only (write operations fail)."""
        code = """
try:
    test_target = os.path.join(sys.path[0], "tamper_test.txt")
    with open(test_target, "w") as f:
        f.write("ILLEGAL_WRITE")
    probe_status = "NOT_ISOLATED"
except (PermissionError, OSError) as ex:
    probe_status = "ACCESS_DENIED"
    probe_details = {"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {"error": str(type(ex).__name__)}
"""
        res = self._execute_worker_probe(code)
        self.assertEqual(res.get("status"), "ACCESS_DENIED", f"Staged runtime write succeeded unexpectedly: {res}")

    def test_filesystem_negative_worker_cannot_access_host_repository(self):
        """Negative Test: AppContainer worker cannot access the host source repository."""
        host_repo_file = Path(__file__).resolve().parents[1] / "src" / "mke_product" / "worker" / "entrypoint.py"
        self.assertTrue(host_repo_file.exists())

        code = f"""
target = {str(host_repo_file)!r}
try:
    with open(target, "r") as f:
        content = f.read()
    probe_status = "NOT_ISOLATED"
except (PermissionError, FileNotFoundError, OSError) as ex:
    probe_status = "ACCESS_DENIED"
    probe_details = {{"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
        res = self._execute_worker_probe(code)
        self.assertEqual(res.get("status"), "ACCESS_DENIED", f"Host repository accessed unexpectedly: {res}")

    def test_filesystem_positive_worker_reads_staged_modules_and_solves_equations(self):
        """Positive Test: Worker cleanly reads staged modules and solves mathematical equations."""
        controller = WorkerController(timeout_sec=5.0)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "SOLVE",
            "equation": "2*x + 4 = 10",
        }
        res = controller.execute_request(req)
        self.assertEqual(res.get("status"), "UNIQUE_ROOT")
        self.assertEqual(res.get("outcome"), "SUCCESS")
        self.assertEqual(res.get("root"), {"numerator": "3", "denominator": "1"})


class TestAppContainerNetworkSecurity(unittest.TestCase):
    """Phase 3: Empirical Network Isolation Tests."""

    def _start_tcp_server(self) -> Tuple[socket.socket, int, threading.Event]:
        """Start a local TCP echo server on loopback."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        port = srv.getsockname()[1]
        stop_event = threading.Event()

        def _server_loop():
            srv.settimeout(0.5)
            while not stop_event.is_set():
                try:
                    conn, _ = srv.accept()
                    data = conn.recv(1024)
                    if data:
                        conn.sendall(b"ECHO:" + data)
                    conn.close()
                except (socket.timeout, OSError):
                    pass
            srv.close()

        t = threading.Thread(target=_server_loop, daemon=True)
        t.start()
        return srv, port, stop_event

    def _start_udp_server(self) -> Tuple[socket.socket, int, threading.Event]:
        """Start a local UDP receiver on loopback."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        stop_event = threading.Event()

        def _server_loop():
            srv.settimeout(0.5)
            while not stop_event.is_set():
                try:
                    data, addr = srv.recvfrom(1024)
                    if data:
                        srv.sendto(b"UDP_ECHO:" + data, addr)
                except (socket.timeout, OSError):
                    pass
            srv.close()

        t = threading.Thread(target=_server_loop, daemon=True)
        t.start()
        return srv, port, stop_event

    def test_network_positive_control_host_loopback_tcp(self):
        """Positive Control: Host process can connect to and communicate with loopback TCP server."""
        srv, port, stop_event = self._start_tcp_server()
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(2.0)
            client.connect(("127.0.0.1", port))
            client.sendall(b"HELLO_HOST")
            resp = client.recv(1024)
            client.close()
            self.assertEqual(resp, b"ECHO:HELLO_HOST")
        finally:
            stop_event.set()

    def test_network_negative_worker_loopback_tcp_denied(self):
        """Negative Test: AppContainer worker is blocked from connecting to loopback TCP server."""
        srv, port, stop_event = self._start_tcp_server()
        try:
            # Positive control first: verify server is listening and responsive
            pos_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pos_client.settimeout(2.0)
            pos_client.connect(("127.0.0.1", port))
            pos_client.sendall(b"PING")
            pos_resp = pos_client.recv(1024)
            pos_client.close()
            self.assertEqual(pos_resp, b"ECHO:PING")

            # AppContainer worker test: attempt loopback TCP connect
            code = f"""
import socket
port = {port}
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(("127.0.0.1", port))
    s.sendall(b"SANDBOX_ATTACK")
    resp = s.recv(1024)
    s.close()
    probe_status = "NOT_ISOLATED"
    probe_details = {{"resp": resp.decode("latin1")}}
except (PermissionError, OSError) as ex:
    probe_status = "NET_ACCESS_DENIED"
    probe_details = {{"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
            worker_cmd = _make_framed_probe_worker(code)
            controller = WorkerController(timeout_sec=5.0, _worker_cmd=worker_cmd)
            req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
            res = controller.execute_request(req)
            self.assertEqual(res.get("status"), "NET_ACCESS_DENIED", f"Loopback TCP access succeeded unexpectedly: {res}")
        finally:
            stop_event.set()

    def test_network_positive_control_host_loopback_udp(self):
        """Positive Control: Host process can send/recv UDP packets on loopback."""
        srv, port, stop_event = self._start_udp_server()
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(2.0)
            client.sendto(b"UDP_PING", ("127.0.0.1", port))
            resp, _ = client.recvfrom(1024)
            client.close()
            self.assertEqual(resp, b"UDP_ECHO:UDP_PING")
        finally:
            stop_event.set()

    def test_network_negative_worker_loopback_udp_denied(self):
        """Negative Test: AppContainer worker is blocked from sending UDP packets on loopback."""
        srv, port, stop_event = self._start_udp_server()
        try:
            code = f"""
import socket
port = {port}
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    s.sendto(b"SANDBOX_UDP", ("127.0.0.1", port))
    resp, _ = s.recvfrom(1024)
    s.close()
    probe_status = "NOT_ISOLATED"
    probe_details = {{"resp": resp.decode("latin1")}}
except (PermissionError, OSError) as ex:
    probe_status = "NET_ACCESS_DENIED"
    probe_details = {{"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
            worker_cmd = _make_framed_probe_worker(code)
            controller = WorkerController(timeout_sec=5.0, _worker_cmd=worker_cmd)
            req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
            res = controller.execute_request(req)
            self.assertEqual(res.get("status"), "NET_ACCESS_DENIED", f"Loopback UDP access succeeded unexpectedly: {res}")
        finally:
            stop_event.set()

    def test_network_negative_worker_non_loopback_tcp_denied(self):
        """Negative Test: AppContainer worker is blocked from connecting to non-loopback TCP destinations."""
        code = """
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(("192.0.2.1", 80))
    s.close()
    probe_status = "NOT_ISOLATED"
    probe_details = {"connected": True}
except (PermissionError, OSError) as ex:
    probe_status = "NET_ACCESS_DENIED"
    probe_details = {"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {"error": str(type(ex).__name__)}
"""
        worker_cmd = _make_framed_probe_worker(code)
        controller = WorkerController(timeout_sec=5.0, _worker_cmd=worker_cmd)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req)
        self.assertEqual(res.get("status"), "NET_ACCESS_DENIED", f"Non-loopback TCP access succeeded unexpectedly: {res}")

    def test_network_ipv6_loopback_tcp_denied_if_supported(self):
        """Negative Test: AppContainer worker is blocked from connecting to IPv6 loopback if supported."""
        try:
            srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            srv.bind(("::1", 0))
            srv.listen(5)
            port = srv.getsockname()[1]
        except (OSError, socket.error):
            self.skipTest("IPv6 loopback not supported on this host environment.")
            return

        stop_event = threading.Event()

        def _server_loop():
            srv.settimeout(0.5)
            while not stop_event.is_set():
                try:
                    conn, _ = srv.accept()
                    conn.close()
                except (socket.timeout, OSError):
                    pass
            srv.close()

        t = threading.Thread(target=_server_loop, daemon=True)
        t.start()
        try:
            # Positive control: host can connect over IPv6 loopback
            pos_client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            pos_client.settimeout(2.0)
            pos_client.connect(("::1", port))
            pos_client.close()

            # Worker negative test: AppContainer worker cannot connect over IPv6 loopback
            code = f"""
import socket
port = {port}
try:
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(("::1", port))
    s.close()
    probe_status = "NOT_ISOLATED"
    probe_details = {{"connected": True}}
except (PermissionError, OSError) as ex:
    probe_status = "NET_ACCESS_DENIED"
    probe_details = {{"error": str(type(ex).__name__), "errno": getattr(ex, "winerror", None)}}
except Exception as ex:
    probe_status = "OTHER_ERROR"
    probe_details = {{"error": str(type(ex).__name__)}}
"""
            worker_cmd = _make_framed_probe_worker(code)
            controller = WorkerController(timeout_sec=5.0, _worker_cmd=worker_cmd)
            req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
            res = controller.execute_request(req)
            self.assertEqual(res.get("status"), "NET_ACCESS_DENIED", f"IPv6 loopback access succeeded unexpectedly: {res}")
        finally:
            stop_event.set()

    def test_network_capability_allowlist_is_strictly_empty(self):
        """Security Invariant: AppContainer security capabilities have zero network capabilities."""
        manager = get_appcontainer_manager()
        manager.prepare()
        sec_caps = manager.security_capabilities()
        self.assertEqual(sec_caps.CapabilityCount, 0)
        self.assertFalse(bool(sec_caps.Capabilities))


class TestAppContainerSecurityInvariants(unittest.TestCase):
    """Phase 4: Security Invariants, Token Integrity & Fail-Closed Enforcement."""

    def test_appcontainer_token_and_sid_verification_pre_resume(self):
        """Worker process token is verified as authentic AppContainer with exact SID before primary thread resume."""
        controller = WorkerController(timeout_sec=5.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req)
        self.assertEqual(res.get("status"), "UNIQUE_ROOT")

        evidence = controller.get_last_appcontainer_evidence()
        self.assertIsNotNone(evidence)
        self.assertTrue(evidence.get("query_ok"))
        self.assertTrue(evidence.get("is_appcontainer"))
        self.assertFalse(evidence.get("elevated"))
        self.assertTrue(evidence.get("sid_matches_profile"))
        self.assertTrue(evidence.get("verified_before_resume"))
        self.assertTrue(evidence.get("job_assignment_verified"))
        self.assertTrue(evidence.get("process_was_resumed"))

    def test_security_violation_injected_sid_mismatch_fails_closed_immediately(self):
        """Token SID mismatch aborts immediately, terminates child before resume, and never falls back."""
        controller = WorkerController(timeout_sec=5.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req, _inject_sid_mismatch=True)
        self.assertEqual(res.get("status"), WORKER_STARTUP_FAILURE)
        self.assertEqual(res.get("outcome"), "PROTOCOL_ERROR")

        evidence = controller.get_last_appcontainer_evidence()
        self.assertIsNotNone(evidence)
        self.assertFalse(evidence.get("accepted"))
        self.assertFalse(evidence.get("process_was_resumed"))

    def test_security_violation_injected_appcontainer_attribute_failure_fails_closed(self):
        """Inability to apply AppContainer attribute fails closed without starting unrestricted worker."""
        controller = WorkerController(timeout_sec=5.0)
        req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        res = controller.execute_request(req, _inject_appcontainer_attribute_failure=True)
        self.assertEqual(res.get("status"), WORKER_STARTUP_FAILURE)
        self.assertEqual(res.get("outcome"), "PROTOCOL_ERROR")
