"""Strict request validation and protocol boundary enforcement for MKE Product."""

from __future__ import annotations
import json
from typing import Any, Dict, Union

from .errors import (
    ProtocolPayloadTooLargeError,
    ProtocolJsonDecodeError,
    ProtocolStructureError,
    ProtocolMissingFieldError,
    ProtocolUnexpectedFieldError,
    ProtocolInvalidTypeError,
    ProtocolUnsupportedVersionError,
    ProtocolUnknownOperationError,
    ProtocolInputLimitError,
)
from .schema import (
    SCHEMA_VERSION,
    OPERATION_SOLVE,
    OPERATION_CHECK_CANDIDATE,
    SUPPORTED_OPERATIONS,
    MAX_PAYLOAD_BYTES,
    MAX_EQUATION_CHARS,
)


def parse_and_validate_raw_payload(payload: Union[str, bytes, Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect and decode raw transport payload before parsing or mathematical execution.

    Enforces:
    1. Maximum byte-length ceiling BEFORE JSON parsing.
    2. Strict JSON UTF-8 decoding.
    3. Root object must be a dict (rejects JSON arrays, primitives, null).
    """
    if isinstance(payload, (str, bytes)):
        raw_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload
        if len(raw_bytes) > MAX_PAYLOAD_BYTES:
            raise ProtocolPayloadTooLargeError(
                f"Payload size ({len(raw_bytes)} bytes) exceeds maximum limit of {MAX_PAYLOAD_BYTES} bytes."
            )
        try:
            decoded = json.loads(raw_bytes.decode("utf-8"))
        except UnicodeDecodeError as err:
            raise ProtocolJsonDecodeError(f"Payload contains invalid UTF-8 bytes: {err}")
        except json.JSONDecodeError as err:
            raise ProtocolJsonDecodeError(f"Malformed JSON payload: {err.msg}")
    elif isinstance(payload, dict):
        decoded = payload
    else:
        raise ProtocolStructureError(
            f"Payload must be a JSON string, bytes, or dict; got {type(payload).__name__}."
        )

    if not isinstance(decoded, dict):
        raise ProtocolStructureError(
            f"Request root must be a JSON object; got {type(decoded).__name__}."
        )

    return decoded


def validate_request_dict(req: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parsed request dictionary against strict version, operation, and type allowlists.

    Enforces:
    - schema_version == "mke.p02a.v1"
    - operation in ("SOLVE", "CHECK_CANDIDATE")
    - Strict field allowlists (no extra fields permitted)
    - Strict type validation (rejects bool, float, int, list, dict, null where str is expected)
    - Character length and ASCII encoding bounds.
    """
    # 1. schema_version check
    if "schema_version" not in req:
        raise ProtocolMissingFieldError("Field 'schema_version' is required.")
    sv = req["schema_version"]
    if type(sv) is not str:
        raise ProtocolInvalidTypeError(
            f"Field 'schema_version' must be a string, got {type(sv).__name__}."
        )
    if sv != SCHEMA_VERSION:
        raise ProtocolUnsupportedVersionError(
            f"Unsupported schema_version: {sv!r}; expected {SCHEMA_VERSION!r}."
        )

    # 2. operation check
    if "operation" not in req:
        raise ProtocolMissingFieldError("Field 'operation' is required.")
    op = req["operation"]
    if type(op) is not str:
        raise ProtocolInvalidTypeError(
            f"Field 'operation' must be a string, got {type(op).__name__}."
        )
    if op not in SUPPORTED_OPERATIONS:
        raise ProtocolUnknownOperationError(
            f"Unknown operation: {op!r}; supported operations are {list(SUPPORTED_OPERATIONS)}."
        )

    # 3. Operation-specific field validation
    if op == OPERATION_SOLVE:
        allowed_keys = {"schema_version", "operation", "equation"}
        extra_keys = set(req.keys()) - allowed_keys
        if extra_keys:
            raise ProtocolUnexpectedFieldError(
                f"Unexpected field(s) for SOLVE operation: {sorted(extra_keys)}.",
                operation=op,
            )

        if "equation" not in req:
            raise ProtocolMissingFieldError("Field 'equation' is required for SOLVE.", operation=op)
        eq_val = req["equation"]
        if type(eq_val) is not str:
            raise ProtocolInvalidTypeError(
                f"Field 'equation' must be a string, got {type(eq_val).__name__}.",
                operation=op,
            )
        if len(eq_val) > MAX_EQUATION_CHARS:
            raise ProtocolInputLimitError(
                f"Equation length ({len(eq_val)}) exceeds maximum limit of {MAX_EQUATION_CHARS} characters.",
                operation=op,
            )
        if not eq_val.isascii():
            raise ProtocolInputLimitError(
                "Equation must contain ASCII characters only.",
                operation=op,
            )

    elif op == OPERATION_CHECK_CANDIDATE:
        allowed_keys = {"schema_version", "operation", "equation", "candidate"}
        extra_keys = set(req.keys()) - allowed_keys
        if extra_keys:
            raise ProtocolUnexpectedFieldError(
                f"Unexpected field(s) for CHECK_CANDIDATE operation: {sorted(extra_keys)}.",
                operation=op,
            )

        if "equation" not in req:
            raise ProtocolMissingFieldError(
                "Field 'equation' is required for CHECK_CANDIDATE.",
                operation=op,
            )
        eq_val = req["equation"]
        if type(eq_val) is not str:
            raise ProtocolInvalidTypeError(
                f"Field 'equation' must be a string, got {type(eq_val).__name__}.",
                operation=op,
            )
        if len(eq_val) > MAX_EQUATION_CHARS:
            raise ProtocolInputLimitError(
                f"Equation length ({len(eq_val)}) exceeds maximum limit of {MAX_EQUATION_CHARS} characters.",
                operation=op,
            )
        if not eq_val.isascii():
            raise ProtocolInputLimitError(
                "Equation must contain ASCII characters only.",
                operation=op,
            )

        if "candidate" not in req:
            raise ProtocolMissingFieldError(
                "Field 'candidate' is required for CHECK_CANDIDATE.",
                operation=op,
            )
        c_val = req["candidate"]
        if type(c_val) is not str:
            raise ProtocolInvalidTypeError(
                f"Field 'candidate' must be an exact ASCII rational string, got {type(c_val).__name__}.",
                operation=op,
            )
        if not c_val.isascii():
            raise ProtocolInvalidTypeError(
                "Field 'candidate' must contain ASCII characters only.",
                operation=op,
            )
        if len(c_val) > MAX_EQUATION_CHARS:
            raise ProtocolInputLimitError(
                f"Candidate string length ({len(c_val)}) exceeds maximum limit of {MAX_EQUATION_CHARS} characters.",
                operation=op,
            )

    return req
