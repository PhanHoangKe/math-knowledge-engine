"""
End-to-End HTTP Integration Test Suite for MKE Multi-Engine CAS Demo Server.

Tests the live HTTP endpoints, canonical response schema, status code mappings,
CORS headers, static asset serving, and adversarial request rejection.
"""

from __future__ import annotations

import json
import pathlib
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from typing import Any, Dict, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.cas.contracts import EngineStatus
from mke_product.cas.demo_server import CASDemoHTTPRequestHandler


class TestCASHTTPIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Bind to ephemeral port on loopback
        cls.server = HTTPServer(("127.0.0.1", 0), CASDemoHTTPRequestHandler)
        cls.host, cls.port = cls.server.server_address
        cls.base_url = f"http://{cls.host}:{cls.port}"

        # Run server in background daemon thread
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=1.0)

    def _post_json(self, endpoint: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status_code = resp.status
                data = json.loads(resp.read().decode("utf-8"))
                return status_code, data
        except urllib.error.HTTPError as err:
            status_code = err.code
            try:
                data = json.loads(err.read().decode("utf-8"))
            except Exception:
                data = {"raw_error": str(err)}
            return status_code, data

    def _get(self, endpoint: str) -> Tuple[int, bytes, Dict[str, str]]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                headers = dict(resp.headers)
                return resp.status, resp.read(), headers
        except urllib.error.HTTPError as err:
            return err.code, err.read(), dict(err.headers)

    # -------------------------------------------------------------------------
    # Static Assets & Health
    # -------------------------------------------------------------------------
    def test_get_root_serves_html(self):
        status, body, headers = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        self.assertIn(b"Math Knowledge Engine", body)
        self.assertIn("text/html", headers.get("Content-Type", ""))

    def test_get_dev_demo_serves_html(self):
        status, body, headers = self._get("/dev/demo")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        self.assertIn(b"MKE Multi-Engine CAS Platform", body)
        self.assertIn("text/html", headers.get("Content-Type", ""))

    def test_get_static_assets(self):
        status_css, body_css, _ = self._get("/styles.css")
        self.assertEqual(status_css, 200)
        self.assertGreater(len(body_css), 100)

        status_js, body_js, _ = self._get("/app.js")
        self.assertEqual(status_js, 200)
        self.assertGreater(len(body_js), 100)

    def test_get_katex_vendor_assets(self):
        status_css, body_css, h_css = self._get("/vendor/katex/katex.min.css")
        self.assertEqual(status_css, 200)
        self.assertIn("text/css", h_css.get("Content-Type", ""))
        self.assertGreater(len(body_css), 1000)

        status_js, body_js, h_js = self._get("/vendor/katex/katex.min.js")
        self.assertEqual(status_js, 200)
        self.assertIn("application/javascript", h_js.get("Content-Type", ""))
        self.assertGreater(len(body_js), 1000)

    def test_get_health_endpoint(self):
        status, body, headers = self._get("/api/health")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "HEALTHY")
        self.assertIn("mke_native_v1", data.get("engines", []))
        self.assertIn("sympy_cas_v0", data.get("engines", []))

    # -------------------------------------------------------------------------
    # Mathematical E2E Endpoints (Canonical Schema Verification)
    # -------------------------------------------------------------------------
    def test_http_solve_quadratic(self):
        payload = {
            "operation": "SOLVE",
            "input": "x^2 - 4 = 0",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertEqual(data["selected_engine"], "sympy_cas_v0")
        self.assertEqual(data["symbolic_result"], "{-2, 2}")
        self.assertIn("latex_output", data)
        self.assertIn("schema_version", data)
        self.assertIn("execution_duration_sec", data)

    def test_http_differentiate(self):
        payload = {
            "operation": "DIFFERENTIATE",
            "input": "x^2 + 3*x",
            "options": {"variable": "x"},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertEqual(data["symbolic_result"], "2*x + 3")

    def test_http_definite_integration(self):
        payload = {
            "operation": "INTEGRATE",
            "input": "x^2",
            "options": {"lower": 0, "upper": 3},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertEqual(data["symbolic_result"], "9")

    def test_http_domain_preservation_removable_singularity(self):
        payload = {
            "operation": "SOLVE",
            "input": "(x-1)/(x-1) = 1",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertIn("x != 1", data["domain_restrictions"])
        self.assertIn("All real numbers except x != 1", data["symbolic_result"])

    def test_http_plot_2d_with_asymptotes(self):
        payload = {
            "operation": "PLOT_2D",
            "input": "1 / (x - 2)",
            "options": {"x_min": 0, "x_max": 4, "num_points": 100},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertIsNotNone(data["plot_data"])
        self.assertGreaterEqual(len(data["plot_data"]["segments"]), 2)
        self.assertIn(2.0, [round(d, 1) for d in data["plot_data"]["discontinuities"]])

    # -------------------------------------------------------------------------
    # Adversarial & Negative HTTP Tests
    # -------------------------------------------------------------------------
    def test_http_reject_malicious_code_injection(self):
        payload = {
            "operation": "SIMPLIFY",
            "input": "__import__('os').system('dir')",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 403)
        self.assertEqual(data["mathematical_status"], "SECURITY_REJECTED")

    def test_http_reject_malicious_option_bound(self):
        payload = {
            "operation": "INTEGRATE",
            "input": "x^2",
            "options": {"lower": "__import__('os')", "upper": 3},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("Unsupported or non-numeric", data["error_message"])

    def test_http_reject_division_by_zero(self):
        payload = {
            "operation": "SIMPLIFY",
            "input": "1 / 0",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertIn(data["mathematical_status"], ["INVALID_INPUT", "DOMAIN_ERROR"])
        self.assertEqual(data["verification_status"], "ERROR")

    def test_http_verification_status_native_evidence(self):
        payload = {
            "operation": "SOLVE",
            "input": "2*x + 4 = 10",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["selected_engine"], "mke_native_v1")
        self.assertEqual(data["verification_status"], "VERIFIED_WITH_EVIDENCE")

    def test_http_verification_status_sympy_computed(self):
        payload = {
            "operation": "SOLVE",
            "input": "x^2 - 9 = 0",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["selected_engine"], "sympy_cas_v0")
        self.assertEqual(data["verification_status"], "COMPUTED")

    def test_http_reject_out_of_scope_operation(self):
        payload = {
            "operation": "UNKNOWN_OP",
            "input": "x + 1",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["verification_status"], "ERROR")
        self.assertEqual(data.get("domain_certainty"), "NOT_APPLICABLE")

    def test_http_domain_certainty_proven_reals(self):
        payload = {
            "operation": "SOLVE",
            "input": "2*x + 4 = 10",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["domain_certainty"], "PROVEN_REALS")

    def test_http_domain_certainty_explicit_exclusions(self):
        payload = {
            "operation": "SIMPLIFY",
            "input": "(x^2 - 1)/(x - 1)",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["domain_certainty"], "EXPLICIT_EXCLUSIONS")
        self.assertIn("x != 1", data["domain_restrictions"])

    def test_http_solve_linear_system_e2e(self):
        payload = {
            "operation": "SOLVE_SYSTEM",
            "input": "2*x + 3*y = 5, x - y = 1",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertIn("x = 8/5", data["symbolic_result"])
        self.assertEqual(data["selected_engine"], "sympy_cas_v0")
        self.assertEqual(data["verification_status"], "COMPUTED")

    def test_http_solve_inequality_e2e(self):
        payload = {
            "operation": "SOLVE_INEQUALITY",
            "input": "x^2 - 4 > 0",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertEqual(data["symbolic_result"], "(-oo, -2) U (2, oo)")
        self.assertEqual(data["selected_engine"], "sympy_cas_v0")
        self.assertEqual(data["verification_status"], "COMPUTED")

    def _raw_socket_request(self, request_bytes: bytes, timeout: float = 3.0) -> bytes:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((self.host, self.port))
            s.sendall(request_bytes)
            response = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except (socket.timeout, ConnectionResetError):
                    break
            return response
        finally:
            s.close()

    def test_http_reject_in_process_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x + 1 = 0",
            "options": {"in_process": True},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_sleep_seconds_option(self):
        payload = {
            "operation": "SIMPLIFY",
            "input": "x + x",
            "options": {"sleep_seconds": 60},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_engine_override_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x^2 - 4 = 0",
            "options": {"engine_override": "mke_native_v1"},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_timeout_sec_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x = 1",
            "options": {"timeout_sec": 5.0},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_simulate_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x = 1",
            "options": {"simulate": True},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_direct_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x = 1",
            "options": {"direct": True},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_internal_option(self):
        payload = {
            "operation": "SOLVE",
            "input": "x = 1",
            "options": {"internal": True},
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("forbidden", data["error_message"].lower())

    def test_http_reject_invalid_preferred_engine(self):
        payload = {
            "operation": "SOLVE",
            "input": "x + 1 = 0",
            "preferred_engine": "malicious_eval_engine",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "OUT_OF_SCOPE")
        self.assertIn("not a valid public mathematical engine", data["error_message"])

    # -------------------------------------------------------------------------
    # Content-Length & Malformed Payload Hardening
    # -------------------------------------------------------------------------
    def test_http_negative_content_length_raw_socket(self):
        raw_req = (
            f"POST /api/execute HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: -25\r\n"
            f"\r\n"
            f'{{"operation": "SOLVE", "input": "x = 1"}}'
        ).encode("utf-8")
        resp = self._raw_socket_request(raw_req)
        self.assertTrue(resp.startswith(b"HTTP/1.0 400") or resp.startswith(b"HTTP/1.1 400"))
        self.assertIn(b"INVALID_INPUT", resp)
        self.assertIn(b"strictly positive integer", resp)

    def test_http_zero_content_length_raw_socket(self):
        raw_req = (
            f"POST /api/execute HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        ).encode("utf-8")
        resp = self._raw_socket_request(raw_req)
        self.assertTrue(resp.startswith(b"HTTP/1.0 400") or resp.startswith(b"HTTP/1.1 400"))
        self.assertIn(b"INVALID_INPUT", resp)
        self.assertIn(b"strictly positive integer", resp)

    def test_http_malformed_content_length_raw_socket(self):
        raw_req = (
            f"POST /api/execute HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: not_a_number\r\n"
            f"\r\n"
            f'{{"operation": "SOLVE", "input": "x = 1"}}'
        ).encode("utf-8")
        resp = self._raw_socket_request(raw_req)
        self.assertTrue(resp.startswith(b"HTTP/1.0 400") or resp.startswith(b"HTTP/1.1 400"))
        self.assertIn(b"INVALID_INPUT", resp)
        self.assertIn(b"Malformed Content-Length header", resp)

    def test_http_oversized_content_length(self):
        raw_req = (
            f"POST /api/execute HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: 70000\r\n"
            f"\r\n"
            f'{{"operation": "SOLVE", "input": "x = 1"}}'
        ).encode("utf-8")
        resp = self._raw_socket_request(raw_req)
        self.assertTrue(resp.startswith(b"HTTP/1.0 413") or resp.startswith(b"HTTP/1.1 413"))
        self.assertIn(b"RESOURCE_EXHAUSTED", resp)

    def test_http_reject_array_top_level_payload(self):
        payload = [{"operation": "SOLVE", "input": "x + 1 = 0"}]
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("expected an object", data["error_message"].lower())

    def test_http_reject_string_top_level_payload(self):
        payload = "just a raw string"
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("expected an object", data["error_message"].lower())

    def test_http_reject_number_top_level_payload(self):
        payload = 12345
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("expected an object", data["error_message"].lower())

    def test_http_reject_boolean_top_level_payload(self):
        payload = True
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("expected an object", data["error_message"].lower())

    def test_http_reject_null_top_level_payload(self):
        payload = None
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(data["mathematical_status"], "INVALID_INPUT")
        self.assertIn("expected an object", data["error_message"].lower())

    def test_http_incomplete_request_body_socket_timeout(self):
        """Client declares Content-Length: 100 but sends only 20 bytes and holds connection open."""
        raw_req = (
            f"POST /api/execute HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: 100\r\n"
            f"\r\n"
            f'{{"operation": "SOLVE"'
        ).encode("utf-8")
        start_t = time.monotonic()
        resp = self._raw_socket_request(raw_req, timeout=4.0)
        elapsed = time.monotonic() - start_t
        self.assertLess(elapsed, 3.5, f"Server hung for {elapsed:.2f}s on incomplete request body")
        self.assertTrue(b"408" in resp or b"400" in resp or len(resp) == 0)

    def test_http_incomplete_request_body_early_eof(self):
        """Client declares Content-Length: 100 but sends only 20 bytes and closes connection."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        try:
            s.connect((self.host, self.port))
            raw_req = (
                f"POST /api/execute HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: 100\r\n"
                f"\r\n"
                f'{{"operation": "SOLVE"'
            ).encode("utf-8")
            s.sendall(raw_req)
            s.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            self.assertTrue(response.startswith(b"HTTP/1.0 400") or response.startswith(b"HTTP/1.1 400"))
            self.assertIn(b"Truncated request body", response)
        finally:
            s.close()

    def test_http_liveness_after_adversarial_requests(self):
        """Verify the HTTP server remains fully functional and responsive after malformed payloads."""
        payload = {
            "operation": "SOLVE",
            "input": "3*x - 9 = 0",
        }
        status, data = self._post_json("/api/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["mathematical_status"], "SUCCESS")
        self.assertEqual(data["symbolic_result"], "{3}")


if __name__ == "__main__":
    unittest.main()




