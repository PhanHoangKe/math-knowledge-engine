"""
MKE Multi-Engine CAS Web Demo Server (v0/R1).

Lightweight HTTP server serving the interactive web UI and dispatching
CAS operations via the multi-engine router using the canonical ExecutionResponse schema.
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from mke_product.cas.contracts import EngineStatus, ExecutionRequest, OperationType
from mke_product.cas.router import execute_cas_operation

logger = logging.getLogger("mke_cas_demo_server")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class CASDemoHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "MKECASDemo/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/" or path == "/index.html":
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            relative_name = path[len("/static/"):]
            file_path = (STATIC_DIR / relative_name).resolve()
            if not str(file_path).startswith(str(STATIC_DIR)):
                self.send_error(403, "Forbidden")
                return
            if not file_path.is_file():
                self.send_error(404, "File not found")
                return
            mime_type, _ = mimetypes.guess_type(str(file_path))
            self._serve_file(file_path, mime_type or "application/octet-stream")
        elif path == "/api/health":
            self._send_json(200, {
                "status": "HEALTHY",
                "version": "0.1.0-r1",
                "engines": ["mke_native_v1", "sympy_cas_v0"],
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        if self.path == "/api/execute":
            self._handle_execute()
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

    def _handle_execute(self) -> None:
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            self._send_json(400, {
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "error_message": "Missing Content-Length header",
            })
            return

        try:
            content_length = int(content_length_header)
            if content_length > 65536:
                self._send_json(413, {
                    "mathematical_status": EngineStatus.RESOURCE_EXHAUSTED.value,
                    "error_message": "Payload exceeds maximum allowed size of 65536 bytes.",
                })
                return
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            self._send_json(400, {
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "error_message": f"Invalid JSON payload: {exc}",
            })
            return

        operation_str = payload.get("operation")
        input_text = payload.get("input") or payload.get("expression") or ""
        options = payload.get("options", {})
        preferred_engine = payload.get("engine") or payload.get("preferred_engine")

        if not operation_str or not input_text:
            self._send_json(400, {
                "mathematical_status": EngineStatus.INVALID_INPUT.value,
                "error_message": "Both 'operation' and 'input' (or 'expression') fields are required.",
            })
            return

        try:
            op_type = OperationType(str(operation_str).upper())
        except ValueError:
            self._send_json(400, {
                "mathematical_status": EngineStatus.OUT_OF_SCOPE.value,
                "error_message": f"Unsupported operation: '{operation_str}'.",
            })
            return

        request = ExecutionRequest(
            operation=op_type,
            raw_input=str(input_text),
            options=options if isinstance(options, dict) else {},
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


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    server_address = (host, port)
    httpd = HTTPServer(server_address, CASDemoHTTPRequestHandler)
    logger.info("Starting MKE CAS Demo Server at http://%s:%d/", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down CAS Demo Server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MKE Multi-Engine CAS Web Demo Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
