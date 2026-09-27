"""Strict request validation and protocol boundary enforcement for MKE Product."""

from __future__ import annotations
import json
from typing import Any, Dict, Union, List, Tuple

from .errors import (
    ProtocolError,
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
    MAX_JSON_NESTING_DEPTH,
)


def _reject_duplicate_keys_hook(pairs: List[Tuple[Any, Any]]) -> Dict[Any, Any]:
    """Strict JSON object hook rejecting duplicate keys before dispatch."""
    d: Dict[Any, Any] = {}
    for key, value in pairs:
        if key in d:
            raise ProtocolStructureError(f"Duplicate JSON object key detected: {key!r}")
        d[key] = value
    return d


def check_json_nesting_depth(json_str: str, max_depth: int = MAX_JSON_NESTING_DEPTH) -> None:
    """Scan JSON string to ensure object/array nesting depth does not exceed ceiling.

    Raises:
        ProtocolStructureError: if nesting depth exceeds max_depth.
    """
    depth = 0
    in_string = False
    escape = False
    for ch in json_str:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{" or ch == "[":
                depth += 1
                if depth > max_depth:
                    raise ProtocolStructureError(
                        f"JSON nesting depth exceeds maximum limit of {max_depth} levels."
                    )
            elif ch == "}" or ch == "]":
                if depth > 0:
                    depth -= 1


def _measure_value_bytes(
    val: Any,
    current_depth: int,
    max_depth: int,
) -> int:
    """Conservatively calculate UTF-8 byte representation for a dictionary value.

    Raises:
        ProtocolStructureError: if nesting depth exceeds max_depth.
        ProtocolInvalidTypeError: if value type is unsupported.
        ProtocolJsonDecodeError: if string contains unencodable surrogates.
    """
    if current_depth > max_depth:
        raise ProtocolStructureError(
            f"JSON nesting depth exceeds maximum limit of {max_depth} levels."
        )

    if isinstance(val, str):
        try:
            b = val.encode("utf-8")
            return len(b) + 2  # including quotes
        except UnicodeEncodeError as err:
            raise ProtocolJsonDecodeError(
                f"Dictionary string value contains unencodable Unicode surrogates: {err}"
            )
    elif isinstance(val, bool):
        return 4 if val else 5  # true / false
    elif isinstance(val, (int, float)):
        return len(str(val).encode("utf-8"))
    elif val is None:
        return 4  # null
    elif isinstance(val, dict):
        return _measure_dict_bytes(
            val,
            current_depth=current_depth + 1,
            max_depth=max_depth,
            max_bytes=MAX_PAYLOAD_BYTES,
        )
    elif isinstance(val, list):
        return _measure_list_bytes(
            val,
            current_depth=current_depth + 1,
            max_depth=max_depth,
            max_bytes=MAX_PAYLOAD_BYTES,
        )
    else:
        raise ProtocolInvalidTypeError(
            f"Unsupported value type in request dictionary: {type(val).__name__}."
        )


def _measure_list_bytes(
    lst: List[Any],
    current_depth: int,
    max_depth: int,
    max_bytes: int = MAX_PAYLOAD_BYTES,
) -> int:
    if current_depth > max_depth:
        raise ProtocolStructureError(
            f"JSON nesting depth exceeds maximum limit of {max_depth} levels."
        )
    total = 2  # '[]'
    for item in lst:
        total += _measure_value_bytes(item, current_depth=current_depth, max_depth=max_depth) + 1
        if total > max_bytes:
            raise ProtocolPayloadTooLargeError(
                f"Dict payload size ({total} bytes) exceeds maximum limit of {max_bytes} bytes."
            )
    return total


def _measure_dict_bytes(
    d: Dict[Any, Any],
    current_depth: int = 1,
    max_depth: int = MAX_JSON_NESTING_DEPTH,
    max_bytes: int = MAX_PAYLOAD_BYTES,
) -> int:
    if current_depth > max_depth:
        raise ProtocolStructureError(
            f"JSON nesting depth exceeds maximum limit of {max_depth} levels."
        )
    total = 2  # '{}'
    for k, v in d.items():
        if type(k) is not str:
            raise ProtocolInvalidTypeError(
                f"Dictionary keys must be strings, got {type(k).__name__}."
            )
        try:
            k_bytes = k.encode("utf-8")
        except UnicodeEncodeError as err:
            raise ProtocolJsonDecodeError(
                f"Dictionary key contains unencodable Unicode surrogates: {err}"
            )
        k_len = len(k_bytes) + 2  # "key"
        v_len = _measure_value_bytes(v, current_depth=current_depth, max_depth=max_depth)
        total += k_len + 1 + v_len + 1  # "key":val,
        if total > max_bytes:
            raise ProtocolPayloadTooLargeError(
                f"Dict payload size ({total} bytes) exceeds maximum limit of {max_bytes} bytes."
            )
    return total


def parse_and_validate_raw_payload(payload: Union[str, bytes, Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect and decode raw transport payload before parsing or mathematical execution.

    Enforces:
    1. Maximum byte-length ceiling BEFORE JSON parsing.
    2. Genuinely enforceable UTF-8 byte calculation on dict inputs without unbounded serialization.
    3. Strict JSON UTF-8 decoding with duplicate key rejection.
    4. Safe handling of excessive JSON nesting and isolated Unicode surrogates.
    5. Root object must be a dict with string keys (rejects JSON arrays, primitives, null).
    """
    if isinstance(payload, (str, bytes)):
        if isinstance(payload, str):
            try:
                raw_bytes = payload.encode("utf-8")
            except UnicodeEncodeError as err:
                raise ProtocolJsonDecodeError(
                    f"Payload string contains unencodable Unicode surrogates: {err}"
                )
        else:
            raw_bytes = payload

        if len(raw_bytes) > MAX_PAYLOAD_BYTES:
            raise ProtocolPayloadTooLargeError(
                f"Payload size ({len(raw_bytes)} bytes) exceeds maximum limit of {MAX_PAYLOAD_BYTES} bytes."
            )

        try:
            decoded_str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise ProtocolJsonDecodeError(f"Payload contains invalid UTF-8 bytes: {err}")

        # Enforce documented JSON nesting depth before parsing
        check_json_nesting_depth(decoded_str, max_depth=MAX_JSON_NESTING_DEPTH)

        try:
            decoded = json.loads(decoded_str, object_pairs_hook=_reject_duplicate_keys_hook)
        except ProtocolError:
            raise
        except json.JSONDecodeError as err:
            raise ProtocolJsonDecodeError(f"Malformed JSON payload: {err.msg}")
        except (RecursionError, ValueError) as err:
            raise ProtocolStructureError(f"Excessive nesting or malformed JSON structure: {err}")

    elif isinstance(payload, dict):
        # Strict dictionary validation with exact UTF-8 byte calculation
        _measure_dict_bytes(
            payload,
            current_depth=1,
            max_depth=MAX_JSON_NESTING_DEPTH,
            max_bytes=MAX_PAYLOAD_BYTES,
        )
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
    - Candidate rational grammar without whitespace.
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
        if c_val != c_val.strip() or any(ch.isspace() for ch in c_val):
            raise ProtocolInvalidTypeError(
                f"Candidate string must conform strictly to rational grammar without whitespace: {c_val!r}.",
                operation=op,
            )
        if len(c_val) > MAX_EQUATION_CHARS:
            raise ProtocolInputLimitError(
                f"Candidate string length ({len(c_val)}) exceeds maximum limit of {MAX_EQUATION_CHARS} characters.",
                operation=op,
            )

    return req
