"""MKE Product versioned request protocol and mathematical dispatch package."""

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
    MAX_RESPONSE_BYTES,
    MIN_RESPONSE_BYTES,
    MAX_JSON_NESTING_DEPTH,
    serialize_rational,
    serialize_span,
)
from .validator import parse_and_validate_raw_payload, validate_request_dict
from .dispatcher import dispatch_request, dispatch_json

__all__ = [
    "ProtocolError",
    "ProtocolPayloadTooLargeError",
    "ProtocolJsonDecodeError",
    "ProtocolStructureError",
    "ProtocolMissingFieldError",
    "ProtocolUnexpectedFieldError",
    "ProtocolInvalidTypeError",
    "ProtocolUnsupportedVersionError",
    "ProtocolUnknownOperationError",
    "ProtocolInputLimitError",
    "SCHEMA_VERSION",
    "OPERATION_SOLVE",
    "OPERATION_CHECK_CANDIDATE",
    "SUPPORTED_OPERATIONS",
    "MAX_PAYLOAD_BYTES",
    "MAX_EQUATION_CHARS",
    "MAX_RESPONSE_BYTES",
    "MIN_RESPONSE_BYTES",
    "MAX_JSON_NESTING_DEPTH",
    "serialize_rational",
    "serialize_span",
    "parse_and_validate_raw_payload",
    "validate_request_dict",
    "dispatch_request",
    "dispatch_json",
]
