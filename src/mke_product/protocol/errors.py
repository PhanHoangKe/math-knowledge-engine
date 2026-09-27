"""Typed exceptions for MKE Product versioned protocol and request validation."""

from __future__ import annotations
from typing import Optional


class ProtocolError(Exception):
    """Base exception for protocol framing, schema validation, and transport errors."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_PROTOCOL_ERROR",
        operation: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.operation = operation

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "span": None,
        }


class ProtocolPayloadTooLargeError(ProtocolError):
    """Raised when raw payload byte length exceeds configured transport ceiling."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PAYLOAD_TOO_LARGE",
            operation=operation,
        )


class ProtocolJsonDecodeError(ProtocolError):
    """Raised when request payload is not valid UTF-8 JSON."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_JSON_DECODE",
            operation=operation,
        )


class ProtocolStructureError(ProtocolError):
    """Raised when request root is not a JSON object / dict."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_MALFORMED_STRUCTURE",
            operation=operation,
        )


class ProtocolMissingFieldError(ProtocolError):
    """Raised when a required protocol field is missing from request."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_MISSING_FIELD",
            operation=operation,
        )


class ProtocolUnexpectedFieldError(ProtocolError):
    """Raised when unknown/disallowed fields are present in request (strict allowlist)."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_UNEXPECTED_FIELD",
            operation=operation,
        )


class ProtocolInvalidTypeError(ProtocolError):
    """Raised when a field value violates strict typed schema (e.g. float or bool instead of str)."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_INVALID_TYPE",
            operation=operation,
        )


class ProtocolUnsupportedVersionError(ProtocolError):
    """Raised when request schema_version is unrecognized."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_UNSUPPORTED_VERSION",
            operation=operation,
        )


class ProtocolUnknownOperationError(ProtocolError):
    """Raised when request operation is unrecognized."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_UNKNOWN_OPERATION",
            operation=operation,
        )


class ProtocolInputLimitError(ProtocolError):
    """Raised when an individual field exceeds length limits (e.g. equation length > 256 chars)."""

    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            code="ERR_PROTOCOL_INPUT_LIMIT",
            operation=operation,
        )
