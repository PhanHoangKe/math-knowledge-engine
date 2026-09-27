"""Fixed allowlisted entry point for disposable S4-B1 workers.

Reads framed JSON request from standard input, dispatches through S4-A kernel,
and writes framed JSON response to standard output.
"""

import json
import struct
import sys
from typing import Any, Dict, Union

from mke_product.protocol.dispatcher import dispatch_json
from mke_product.protocol.schema import SCHEMA_VERSION

from .constants import (
    IPC_HEADER_SIZE,
    IPC_MAX_REQUEST_BYTES,
    IPC_MAX_RESPONSE_BYTES,
    WORKER_PROTOCOL_FAILURE,
)


def _write_framed_response(response_obj: Union[str, bytes, Dict[str, Any]]) -> None:
    """Serialize and write a 4-byte length prefixed JSON response to stdout."""
    if isinstance(response_obj, bytes):
        raw_json = response_obj
    elif isinstance(response_obj, str):
        raw_json = response_obj.encode("utf-8")
    else:
        raw_json = json.dumps(response_obj, separators=(",", ":")).encode("utf-8")

    if len(raw_json) > IPC_MAX_RESPONSE_BYTES:
        err_res = {
            "schema_version": SCHEMA_VERSION,
            "operation": response_obj.get("operation", "UNKNOWN") if isinstance(response_obj, dict) else "UNKNOWN",
            "outcome": "RESOURCE_EXHAUSTED",
            "status": "ERR_RESPONSE_LIMIT_EXCEEDED",
            "definedness": None,
            "is_provisional_evidence": False,
            "error": {
                "code": "ERR_RESPONSE_LIMIT_EXCEEDED",
                "message": f"Worker serialized response size ({len(raw_json)} bytes) exceeds limit of {IPC_MAX_RESPONSE_BYTES} bytes.",
                "details": {
                    "actual_bytes": len(raw_json),
                    "max_response_bytes": IPC_MAX_RESPONSE_BYTES,
                },
            },
        }
        raw_json = json.dumps(err_res, separators=(",", ":")).encode("utf-8")

    header = struct.pack(">I", len(raw_json))
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(raw_json)
    sys.stdout.buffer.flush()


def run_worker() -> int:
    """Execute single-request lifecycle inside disposable worker."""
    try:
        header_bytes = sys.stdin.buffer.read(IPC_HEADER_SIZE)
        if len(header_bytes) < IPC_HEADER_SIZE:
            err_dict = {
                "schema_version": SCHEMA_VERSION,
                "operation": "UNKNOWN",
                "outcome": "PROTOCOL_ERROR",
                "status": WORKER_PROTOCOL_FAILURE,
                "definedness": None,
                "is_provisional_evidence": False,
                "error": {
                    "code": WORKER_PROTOCOL_FAILURE,
                    "message": "Incomplete or missing IPC header from controller.",
                    "details": {"bytes_received": len(header_bytes)},
                },
            }
            _write_framed_response(err_dict)
            return 1

        (req_length,) = struct.unpack(">I", header_bytes)
        if req_length > IPC_MAX_REQUEST_BYTES:
            err_dict = {
                "schema_version": SCHEMA_VERSION,
                "operation": "UNKNOWN",
                "outcome": "PROTOCOL_ERROR",
                "status": "ERR_PAYLOAD_TOO_LARGE",
                "definedness": None,
                "is_provisional_evidence": False,
                "error": {
                    "code": "ERR_PAYLOAD_TOO_LARGE",
                    "message": f"IPC request size ({req_length} bytes) exceeds limit of {IPC_MAX_REQUEST_BYTES} bytes.",
                    "details": {
                        "payload_bytes": req_length,
                        "max_bytes": IPC_MAX_REQUEST_BYTES,
                    },
                },
            }
            _write_framed_response(err_dict)
            return 1

        payload_bytes = sys.stdin.buffer.read(req_length)
        if len(payload_bytes) < req_length:
            err_dict = {
                "schema_version": SCHEMA_VERSION,
                "operation": "UNKNOWN",
                "outcome": "PROTOCOL_ERROR",
                "status": WORKER_PROTOCOL_FAILURE,
                "definedness": None,
                "is_provisional_evidence": False,
                "error": {
                    "code": WORKER_PROTOCOL_FAILURE,
                    "message": "Incomplete IPC request payload received.",
                    "details": {
                        "expected_bytes": req_length,
                        "received_bytes": len(payload_bytes),
                    },
                },
            }
            _write_framed_response(err_dict)
            return 1

        # Dispatch through S4-A kernel
        payload_str = payload_bytes.decode("utf-8", errors="replace")
        response_dict = dispatch_json(payload_str)
        _write_framed_response(response_dict)
        return 0

    except Exception as exc:
        err_dict = {
            "schema_version": SCHEMA_VERSION,
            "operation": "UNKNOWN",
            "outcome": "PROTOCOL_ERROR",
            "status": WORKER_PROTOCOL_FAILURE,
            "definedness": None,
            "is_provisional_evidence": False,
            "error": {
                "code": WORKER_PROTOCOL_FAILURE,
                "message": f"Unhandled exception inside worker: {exc}",
                "details": {"exception_type": type(exc).__name__},
            },
        }
        try:
            _write_framed_response(err_dict)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(run_worker())
