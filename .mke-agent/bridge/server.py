"""Dual-mode MCP and REST Server for MKE Antigravity Bridge."""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

if __package__ or "." in __name__:
    from .models import BridgeTaskRequest, TaskStatus
    from .worker import TaskWorker, find_agy
    from .keep_awake import keep_awake_service
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from bridge.models import BridgeTaskRequest, TaskStatus
    from bridge.worker import TaskWorker, find_agy
    from bridge.keep_awake import keep_awake_service

MCP_TOOLS_SPEC = [
    {
        "name": "anty_submit_task",
        "description": "Submit a coding and testing task to Antigravity. Runs agy headless in an isolated worktree, validates scope and frontend freeze, runs regression tests, and commits/pushes to GitHub.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Unique identifier for the task, e.g. THPT-COV-P2-001"},
                "prompt": {"type": "string", "description": "Detailed implementation instructions for Antigravity"},
                "base_sha": {"type": "string", "description": "Full 40-hex Git commit SHA to branch from"},
                "target_branch": {"type": "string", "description": "Target branch name to push to, e.g. product/thpt-cov-p2-polynomial-foundation"},
                "allowed_prefixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of allowed path prefixes for modified files",
                    "default": ["src/mke_product/coverage/", "tests/test_thpt_cov_"],
                },
                "commit_message": {"type": "string", "description": "Optional Git commit message"},
                "timeout_seconds": {"type": "integer", "description": "Maximum execution time in seconds", "default": 900},
                "callback_url": {"type": "string", "description": "Optional webhook URL to receive completion event"},
            },
            "required": ["task_id", "prompt", "base_sha", "target_branch"],
        },
    },
    {
        "name": "anty_task_status",
        "description": "Check current execution status, stage, and errors for a submitted Antigravity task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to inspect"}
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "anty_get_report",
        "description": "Retrieve the final execution report, commit SHA, changed files, and test output for a completed task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to inspect"}
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "anty_cancel_task",
        "description": "Cancel an active or queued Antigravity task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to cancel"}
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "anty_health",
        "description": "Check health of the Antigravity Bridge, CLI availability, Python runtime, and active tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_mcp_call(worker: TaskWorker, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name == "anty_submit_task":
        req = BridgeTaskRequest(
            task_id=arguments["task_id"],
            prompt=arguments["prompt"],
            base_sha=arguments["base_sha"],
            target_branch=arguments["target_branch"],
            allowed_prefixes=arguments.get("allowed_prefixes", ["src/mke_product/coverage/", "tests/test_thpt_cov_"]),
            commit_message=arguments.get("commit_message", ""),
            timeout_seconds=int(arguments.get("timeout_seconds", 900)),
            callback_url=arguments.get("callback_url"),
        )
        rec = worker.submit_task(req)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"status": "SUBMITTED", "task": rec.to_dict()}, indent=2),
                }
            ]
        }

    elif tool_name == "anty_task_status":
        rec = worker.get_task(arguments["task_id"])
        if not rec:
            return {"isError": True, "content": [{"type": "text", "text": f"Task {arguments['task_id']} not found."}]}
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "task_id": rec.task_id,
                        "status": rec.status.value,
                        "stage": rec.stage,
                        "started_at": rec.started_at,
                        "finished_at": rec.finished_at,
                        "error": rec.error,
                    }, indent=2),
                }
            ]
        }

    elif tool_name == "anty_get_report":
        rec = worker.get_task(arguments["task_id"])
        if not rec:
            return {"isError": True, "content": [{"type": "text", "text": f"Task {arguments['task_id']} not found."}]}
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(rec.to_dict(), indent=2),
                }
            ]
        }

    elif tool_name == "anty_cancel_task":
        success = worker.cancel_task(arguments["task_id"])
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"task_id": arguments["task_id"], "cancelled": success}),
                }
            ]
        }

    elif tool_name == "anty_health":
        try:
            agy_path = find_agy()
            agy_ok = True
        except Exception:
            agy_path = None
            agy_ok = False
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "service": "MKE Antigravity Bridge",
                        "status": "HEALTHY",
                        "agy_available": agy_ok,
                        "agy_path": agy_path,
                        "repo_path": str(worker.repo_path),
                        "active_tasks_count": len([t for t in worker.list_tasks() if t.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}]),
                    }, indent=2),
                }
            ]
        }

    raise ValueError(f"Unknown tool: {tool_name}")


def create_handler_class(worker: TaskWorker):
    browser_diagnostics: Dict[str, Any] = {}

    class BridgeHTTPHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, data: Any):
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
        def _send_html(self, status: int, html_content: str):
            body = html_content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, content: str, content_type: str = "text/plain; charset=utf-8"):
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path == "" or path == "/dashboard":
                dashboard_file = Path(__file__).parent / "dashboard.html"
                if dashboard_file.is_file():
                    self._send_html(200, dashboard_file.read_text(encoding="utf-8"))
                else:
                    self._send_html(200, "<h1>MKE Agent Bridge Active</h1><p>Dashboard HTML not found.</p>")
                return

            if path == "/api/health":
                try:
                    agy_path = find_agy()
                    agy_ok = True
                except Exception:
                    agy_path = None
                    agy_ok = False
                self._send_json(200, {
                    "service": "MKE Antigravity Bridge",
                    "status": "ok",
                    "agy_available": agy_ok,
                    "agy_path": agy_path,
                    "repo": str(worker.repo_path),
                    "total_tasks": len(worker.list_tasks()),
                    "keep_awake": keep_awake_service.get_status(),
                })
                return

            if path == "/api/keep-awake":
                self._send_json(200, keep_awake_service.get_status())
                return

            if path == "/api/tasks/list":
                self._send_json(200, [t.to_dict() for t in worker.list_tasks()])
                return

            if path == "/api/browser-diagnostics":
                self._send_json(200, browser_diagnostics)
                return

            if path == "/api/browser/autowake.user.js":
                script_path = Path(__file__).parent.parent / "browser" / "mke_chatgpt_autowake.user.js"
                if not script_path.is_file():
                    self._send_json(404, {"error": "auto-wake userscript not found"})
                else:
                    self._send_text(
                        200,
                        script_path.read_text(encoding="utf-8"),
                        "application/javascript; charset=utf-8",
                    )
                return

            if path.startswith("/api/tasks/") and path.endswith("/status"):
                task_id = path.split("/")[3]
                rec = worker.get_task(task_id)
                if not rec:
                    self._send_json(404, {"error": f"Task {task_id} not found."})
                else:
                    self._send_json(200, {
                        "task_id": rec.task_id,
                        "status": rec.status.value,
                        "stage": rec.stage,
                        "started_at": rec.started_at,
                        "finished_at": rec.finished_at,
                        "commit_sha": rec.commit_sha,
                        "error": rec.error,
                    })
                return

            if path.startswith("/api/tasks/") and path.endswith("/result"):
                task_id = path.split("/")[3]
                rec = worker.get_task(task_id)
                if not rec:
                    self._send_json(404, {"error": f"Task {task_id} not found."})
                else:
                    self._send_json(200, rec.to_dict())
                return

            self._send_json(404, {"error": f"Path not found: {path}"})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                payload = json.loads(raw_body)
            except Exception:
                payload = {}

            if path == "/api/browser-diagnostics":
                if not isinstance(payload, dict):
                    self._send_json(400, {"error": "diagnostics payload must be an object"})
                    return
                browser_diagnostics.clear()
                browser_diagnostics.update(payload)
                browser_diagnostics["received_at"] = time.time()
                self._send_json(200, {"status": "ok"})
                return

            if path == "/api/tasks/submit":
                try:
                    req = BridgeTaskRequest(
                        task_id=payload["task_id"],
                        prompt=payload["prompt"],
                        base_sha=payload["base_sha"],
                        target_branch=payload["target_branch"],
                        allowed_prefixes=payload.get("allowed_prefixes", ["src/mke_product/coverage/", "tests/test_thpt_cov_"]),
                        commit_message=payload.get("commit_message", ""),
                        timeout_seconds=int(payload.get("timeout_seconds", 900)),
                        callback_url=payload.get("callback_url"),
                    )
                    rec = worker.submit_task(req)
                    self._send_json(202, {"status": "QUEUED", "task": rec.to_dict()})
                except Exception as exc:
                    self._send_json(400, {"error": str(exc)})
                return

            if path.startswith("/api/tasks/") and path.endswith("/cancel"):
                task_id = path.split("/")[3]
                cancelled = worker.cancel_task(task_id)
                self._send_json(200, {"task_id": task_id, "cancelled": cancelled})
                return

            if path == "/api/keep-awake/toggle":
                if keep_awake_service.is_running:
                    keep_awake_service.stop()
                else:
                    keep_awake_service.start()
                self._send_json(200, keep_awake_service.get_status())
                return

            if path == "/mcp":
                # JSON-RPC 2.0 Handler for MCP over HTTP
                method = payload.get("method")
                req_id = payload.get("id")

                if method == "initialize":
                    self._send_json(200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "mke-antigravity-bridge", "version": "1.0.0"},
                        },
                    })
                    return

                if method == "tools/list":
                    self._send_json(200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": MCP_TOOLS_SPEC},
                    })
                    return

                if method == "tools/call":
                    params = payload.get("params", {})
                    name = params.get("name")
                    args = params.get("arguments", {})
                    try:
                        res = handle_mcp_call(worker, name, args)
                        self._send_json(200, {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": res,
                        })
                    except Exception as exc:
                        self._send_json(200, {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32603, "message": str(exc)},
                        })
                    return

                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method {method} not found."},
                })
                return

            self._send_json(404, {"error": f"Endpoint not found: {path}"})

    return BridgeHTTPHandler


def run_stdio_mcp(worker: TaskWorker):
    """Run MCP server over standard input/output JSON-RPC."""
    keep_awake_service.start()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            method = payload.get("method")
            req_id = payload.get("id")

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mke-antigravity-bridge", "version": "1.0.0"},
                    },
                }
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": MCP_TOOLS_SPEC},
                }
            elif method == "tools/call":
                params = payload.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                res = handle_mcp_call(worker, name, args)
                resp = {"jsonrpc": "2.0", "id": req_id, "result": res}
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method {method} not found"}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="MKE Antigravity Bridge Server")
    parser.add_argument("--repo", default="D:\\Math Knowledge Engine", help="Repository root path")
    parser.add_argument("--worktrees", default="D:\\mke_agent_worktrees", help="Worktree root path")
    parser.add_argument("--port", type=int, default=8765, help="HTTP/REST server port")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP server host")
    parser.add_argument("--stdio", action="store_true", help="Run MCP stdio JSON-RPC server")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    worktrees = Path(args.worktrees).resolve()
    worker = TaskWorker(repo, worktrees)

    # Automatically start the 24/7 keep-awake anti-sleep daemon
    keep_awake_service.start()

    if args.stdio:
        run_stdio_mcp(worker)
        return

    handler_class = create_handler_class(worker)
    server = ThreadingHTTPServer((args.host, args.port), handler_class)
    print(f"[MKE BRIDGE] Server active on http://{args.host}:{args.port}")
    print(f"[MKE BRIDGE] Web Dashboard: http://{args.host}:{args.port}/dashboard")
    print(f"[MKE BRIDGE] REST API: http://{args.host}:{args.port}/api/health")
    print(f"[MKE BRIDGE] MCP Endpoint: http://{args.host}:{args.port}/mcp")
    print(f"[MKE BRIDGE] Keep-Awake 24/7 Anti-Sleep: ACTIVE (15 min interval)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[MKE BRIDGE] Shutting down...")
        keep_awake_service.stop()
        server.shutdown()


if __name__ == "__main__":
    main()
