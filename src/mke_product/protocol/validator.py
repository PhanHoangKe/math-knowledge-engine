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
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SUPPORTED_SCHEMA_VERSIONS,
    OPERATION_SOLVE,
    OPERATION_CHECK_CANDIDATE,
    OPERATION_SOLVE_QUADRATIC,
    SUPPORTED_OPERATIONS,
    MAX_PAYLOAD_BYTES,
    MAX_EQUATION_CHARS,
    MAX_JSON_NESTING_DEPTH,
)


def _validate_no_surrogates(val: Any) -> None:
    """Validate that value contains no isolated Unicode surrogates (U+D800 - U+DFFF).

    Raises:
        ProtocolJsonDecodeError: if an isolated surrogate is found.
    """
    if isinstance(val, str):
        for ch in val:
            cp = ord(ch)
            if 0xD800 <= cp <= 0xDFFF:
                raise ProtocolJsonDecodeError(
                    f"JSON payload contains invalid Unicode scalar value (isolated surrogate: U+{cp:04X})."
                )
    elif isinstance(val, list):
        for item in val:
            _validate_no_surrogates(item)
    elif isinstance(val, dict):
        for k, v in val.items():
            _validate_no_surrogates(k)
            _validate_no_surrogates(v)


def _reject_duplicate_keys_hook(pairs: List[Tuple[Any, Any]]) -> Dict[Any, Any]:
    """Strict JSON object hook rejecting duplicate keys and isolated surrogates."""
    d: Dict[Any, Any] = {}
    for key, value in pairs:
        if key in d:
            raise ProtocolStructureError(f"Duplicate JSON object key detected: {key!r}")
        _validate_no_surrogates(key)
        _validate_no_surrogates(value)
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


def _measure_json_string_bytes(s: str) -> int:
    r"""Calculate the exact UTF-8 byte length of string `s` as encoded in JSON, including surrounding quotes.

    Accounts for:
    - Surrounding quotes: 2 bytes
    - Escaped quotes `\"` and backslashes `\\`: 2 bytes each
    - Single-character escapes (`\b`, `\t`, `\n`, `\f`, `\r`): 2 bytes each
    - 6-byte hex escapes (`\u00XX`) for all other control characters (< 0x20): 6 bytes each
    - Multibyte UTF-8 characters: exact UTF-8 encoded byte count
    - Isolated surrogates: raises ProtocolJsonDecodeError
    """
    total = 2  # surrounding double quotes
    for ch in s:
        cp = ord(ch)
        if cp < 0x20:
            if ch in ("\b", "\t", "\n", "\f", "\r"):
                total += 2
            else:
                total += 6  # \u00XX
        elif ch in ('"', "\\"):
            total += 2  # \" or \\
        elif 0xD800 <= cp <= 0xDFFF:
            raise ProtocolJsonDecodeError(
                f"Dictionary string contains invalid Unicode scalar value (isolated surrogate: U+{cp:04X})."
            )
        elif cp <= 0x7F:
            total += 1
        elif cp <= 0x7FF:
            total += 2
        elif cp <= 0xFFFF:
            total += 3
        else:
            total += 4
    return total


def _measure_value_bytes(
    val: Any,
    current_depth: int,
    max_depth: int,
    max_bytes: int = MAX_PAYLOAD_BYTES,
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
        return _measure_json_string_bytes(val)
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
            max_bytes=max_bytes,
        )
    elif isinstance(val, list):
        return _measure_list_bytes(
            val,
            current_depth=current_depth + 1,
            max_depth=max_depth,
            max_bytes=max_bytes,
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
    first = True
    for item in lst:
        item_len = _measure_value_bytes(item, current_depth=current_depth, max_depth=max_depth, max_bytes=max_bytes)
        if not first:
            total += 1  # comma
        else:
            first = False
        total += item_len
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
    first = True
    for k, v in d.items():
        if type(k) is not str:
            raise ProtocolInvalidTypeError(
                f"Dictionary keys must be strings, got {type(k).__name__}."
            )
        k_len = _measure_json_string_bytes(k)
        v_len = _measure_value_bytes(v, current_depth=current_depth, max_depth=max_depth, max_bytes=max_bytes)
        entry_len = k_len + 1 + v_len  # "k":v
        if not first:
            entry_len += 1  # comma
        else:
            first = False
        total += entry_len
        if total > max_bytes:
            raise ProtocolPayloadTooLargeError(
                f"Dict payload size ({total} bytes) exceeds maximum limit of {max_bytes} bytes."
            )
    return total


def parse_and_validate_raw_payload(payload: Union[str, bytes, Dict[str, Any]]) -> Dict[str, Any]:
    """Inspect and decode raw transport payload before parsing or mathematical execution.

    Enforces:
    1. Maximum byte-length ceiling BEFORE JSON parsing.
    2. Conservative, escape-aware UTF-8 byte calculation on dict inputs without unbounded serialization.
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

        _validate_no_surrogates(decoded)

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
    if sv not in SUPPORTED_SCHEMA_VERSIONS:
        raise ProtocolUnsupportedVersionError(
            f"Unsupported schema_version: {sv!r}; supported versions are {list(SUPPORTED_SCHEMA_VERSIONS)}."
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

    # 3. Version-Operation matrix enforcement
    if sv == SCHEMA_VERSION_V1:
        if op not in (OPERATION_SOLVE, OPERATION_CHECK_CANDIDATE):
            raise ProtocolUnknownOperationError(
                f"Operation {op!r} is not supported in schema version {SCHEMA_VERSION_V1!r}; use {SCHEMA_VERSION_V2!r}.",
                operation=op,
            )
    elif sv == SCHEMA_VERSION_V2:
        if op != OPERATION_SOLVE_QUADRATIC:
            raise ProtocolUnknownOperationError(
                f"Operation {op!r} is not supported in schema version {SCHEMA_VERSION_V2!r}; use {SCHEMA_VERSION_V1!r}.",
                operation=op,
            )

    # 4. Operation-specific field validation
    if op in (OPERATION_SOLVE, OPERATION_SOLVE_QUADRATIC):
        allowed_keys = {"schema_version", "operation", "equation"}
        extra_keys = set(req.keys()) - allowed_keys
        if extra_keys:
            raise ProtocolUnexpectedFieldError(
                f"Unexpected field(s) for {op} operation: {sorted(extra_keys)}.",
                operation=op,
            )

        if "equation" not in req:
            raise ProtocolMissingFieldError(f"Field 'equation' is required for {op}.", operation=op)
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
