"""
MKE Multi-Engine CAS Web Demo Server (v0).

Lightweight HTTP server serving the interactive web UI and dispatching
CAS operations via the multi-engine router.
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

from mke_product.cas.contracts import ExecutionRequest, OperationType
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
            self._send_json(200, {"status": "HEALTHY", "version": "0.1.0", "engines": ["mke_native_v1", "sympy_cas_v0"]})
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
        self.end_headers()
        self.wfile.write(body)

    def _handle_execute(self) -> None:
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            self._send_json(400, {"error": "Missing Content-Length header", "status": "ERROR"})
            return

        try:
            content_length = int(content_length_header)
            if content_length > 65536:
                self._send_json(413, {"error": "Payload too large", "status": "SECURITY_REJECTED"})
                return
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            self._send_json(400, {"error": f"Invalid JSON payload: {exc}", "status": "ERROR"})
            return

        operation_str = payload.get("operation")
        expression = payload.get("expression", "")
        options = payload.get("options", {})
        preferred_engine = payload.get("engine")

        if not operation_str or not expression:
            self._send_json(400, {"error": "Both 'operation' and 'expression' fields are required", "status": "ERROR"})
            return

        try:
            op_type = OperationType(operation_str.upper())
        except ValueError:
            self._send_json(400, {"error": f"Unsupported operation: '{operation_str}'", "status": "UNSUPPORTED_OPERATION"})
            return

        request = ExecutionRequest(
            operation=op_type,
            expression=str(expression),
            options=options if isinstance(options, dict) else {},
            preferred_engine=str(preferred_engine) if preferred_engine else None,
        )

        response = execute_cas_operation(request)

        result_dict = {
            "status": response.status.value,
            "engine_used": response.engine_used,
            "timing_ms": round(response.timing_ms, 3),
            "result_str": response.result_str,
            "latex_str": response.latex_str,
            "solution_set": response.solution_set,
            "plot_data": response.plot_data,
            "domain_notes": response.domain_notes,
            "error_message": response.error_message,
            "details": response.details,
        }

        status_code = 200 if response.status.value == "SUCCESS" else 400
        self._send_json(status_code, result_dict)


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
