"""
MKE Product Unified Server (v0/R2).

Serves the canonical MKE product web interface (inspired by WolframAlpha)
and dispatches mathematical operations via the multi-engine CAS router
(Native MKE linear solver + SymPy CAS symbolic engine).
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.cas.contracts import EngineStatus, ExecutionRequest, OperationType
from mke_product.cas.router import execute_cas_operation

logger = logging.getLogger("mke_product_server")

UI_DIR = REPO_ROOT / "ui" / "ui00"
DEV_STATIC_DIR = Path(__file__).resolve().parent / "static"


class MKEProductHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "MKEProductServer/0.3"

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        
        # Favicon
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Primary Canonical Product Interface (ui/ui00)
        if path in ("/", "/index.html"):
            self._serve_file(UI_DIR / "index.html", "text/html; charset=utf-8")
        elif path in ("/styles.css", "/app.js", "/DESIGN_TOKENS.md", "/README.md"):
            rel_name = path.lstrip("/")
            mime_type, _ = mimetypes.guess_type(rel_name)
            self._serve_file(UI_DIR / rel_name, mime_type or "text/plain; charset=utf-8")
        elif path.startswith("/screenshots/"):
            rel_name = path[len("/screenshots/"):]
            file_path = (UI_DIR / "screenshots" / rel_name).resolve()
            if not str(file_path).startswith(str(UI_DIR)):
                self.send_error(403, "Forbidden")
                return
            if not file_path.is_file():
                self.send_error(404, "File not found")
                return
            mime_type, _ = mimetypes.guess_type(str(file_path))
            self._serve_file(file_path, mime_type or "image/png")
        elif path.startswith("/ui/"):
            rel_name = path[len("/ui/"):]
            file_path = (UI_DIR / rel_name).resolve()
            if not str(file_path).startswith(str(UI_DIR)):
                self.send_error(403, "Forbidden")
                return
            if not file_path.is_file():
                self.send_error(404, "File not found")
                return
            mime_type, _ = mimetypes.guess_type(str(file_path))
        elif path.startswith("/vendor/"):
            rel_name = path[len("/vendor/"):]
            file_path = (UI_DIR / "vendor" / rel_name).resolve()
            if not str(file_path).startswith(str((UI_DIR / "vendor").resolve())):
                self.send_error(403, "Forbidden")
                return
            if not file_path.is_file():
                self.send_error(404, "File not found")
                return
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if str(file_path).endswith(".woff2"):
                mime_type = "font/woff2"
            elif str(file_path).endswith(".woff"):
                mime_type = "font/woff"
            elif str(file_path).endswith(".ttf"):
                mime_type = "font/ttf"
            elif str(file_path).endswith(".css"):
                mime_type = "text/css; charset=utf-8"
            elif str(file_path).endswith(".js"):
                mime_type = "application/javascript; charset=utf-8"
            self._serve_file(file_path, mime_type or "application/octet-stream")
        
        # Internal Development Tool (Preserved)
        elif path == "/dev/demo" or path == "/dev/demo/":
            self._serve_file(DEV_STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            rel_name = path[len("/static/"):]
            file_path = (DEV_STATIC_DIR / rel_name).resolve()
            if not str(file_path).startswith(str(DEV_STATIC_DIR)):
                self.send_error(403, "Forbidden")
                return
            if not file_path.is_file():
                self.send_error(404, "File not found")
                return
            mime_type, _ = mimetypes.guess_type(str(file_path))
            self._serve_file(file_path, mime_type or "application/octet-stream")
        
        # API Health Endpoint
        elif path == "/api/health":
            self._send_json(200, {
                "status": "HEALTHY",
                "version": "0.2.0-r2",
                "canonical_ui": "ui/ui00 (WolframAlpha atmosphere)",
                "engines": ["mke_native_v1", "sympy_cas_v0"],
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        if self.path in ("/api/execute", "/api/plot"):
            self._handle_execute(default_op="PLOT_2D" if self.path == "/api/plot" else None)
        else:
            self.send_error(404, "Endpoint not found")

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as exc:
            logger.exception("Error serving file: %s", exc)
            self.send_error(500, "Internal Server Error")

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _handle_execute(self, default_op: str | None = None) -> None:
        content_length_header = self.headers.get("Content-Length")
        if content_length_header is None:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": "Missing Content-Length header.",
            })
            return

        try:
            content_length = int(content_length_header.strip())
        except (ValueError, TypeError, AttributeError):
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Malformed Content-Length header: {content_length_header!r}.",
            })
            return

        if content_length <= 0:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Invalid Content-Length: {content_length}. Content-Length must be a strictly positive integer.",
            })
            return

        if content_length > 65536:
            self._send_json(413, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.RESOURCE_EXHAUSTED.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": "Payload exceeds maximum allowed size of 65536 bytes.",
            })
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Invalid JSON payload: {exc}",
            })
            return

        if not isinstance(payload, dict):
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Invalid top-level JSON payload: expected an object (JSON dictionary), got {type(payload).__name__}.",
            })
            return

        operation_str = payload.get("operation") or default_op
        input_text = payload.get("input") or payload.get("expression") or ""
        raw_options = payload.get("options")
        preferred_engine = payload.get("engine") or payload.get("preferred_engine")

        if not operation_str or not input_text:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": "Both 'operation' and 'input' (or 'expression') fields are required.",
            })
            return

        try:
            op_type = OperationType(str(operation_str).upper())
        except ValueError:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.OUT_OF_SCOPE.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Unsupported operation: '{operation_str}'.",
            })
            return

        from mke_product.cas.safety import sanitize_client_options
        try:
            client_options = sanitize_client_options(raw_options if raw_options is not None else {})
        except (ValueError, TypeError) as exc:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Invalid client execution options: {exc}",
            })
            return

        # Sanitize preferred_engine: only public known engines or None
        valid_public_engines = {"mke_native_v1", "sympy_cas_v0"}
        if preferred_engine and str(preferred_engine) not in valid_public_engines:
            self._send_json(400, {
                "schema_version": "mke.product03a.v0",
                "mathematical_status": EngineStatus.OUT_OF_SCOPE.value,
                "verification_status": "ERROR",
                "domain_certainty": "NOT_APPLICABLE",
                "error_message": f"Requested engine '{preferred_engine}' is not a valid public mathematical engine.",
            })
            return

        request = ExecutionRequest(
            operation=op_type,
            raw_input=str(input_text),
            options=client_options,
            preferred_engine=str(preferred_engine) if preferred_engine else None,
        )

        response = execute_cas_operation(request)

        # Map mathematical status to appropriate HTTP status code
        if response.status == EngineStatus.SUCCESS:
            http_status = 200
        elif response.status == EngineStatus.SECURITY_REJECTED:
            http_status = 403
        elif response.status == EngineStatus.RESOURCE_EXHAUSTED:
            http_status = 408
        elif response.status in (EngineStatus.INVALID_INPUT, EngineStatus.DOMAIN_ERROR):
            http_status = 400
        elif response.status == EngineStatus.OUT_OF_SCOPE:
            http_status = 422
        else:
            http_status = 500

        # Return canonical response dictionary directly
        self._send_json(http_status, response.to_dict())


# Backwards compatibility alias for CAS test suite
CASDemoHTTPRequestHandler = MKEProductHTTPRequestHandler


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, MKEProductHTTPRequestHandler)
    logger.info("Starting Canonical MKE Product Server at http://%s:%d/", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down MKE Product Server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MKE Product Multi-Engine Unified Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
