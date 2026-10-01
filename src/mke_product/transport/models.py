"""Transport-specific data models and error taxonomy."""

from enum import Enum
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, ConfigDict, Field


class TransportErrorCode(str, Enum):
    """Specific error codes for transport/HTTP failures occurring prior to or around application execution."""

    MALFORMED_JSON = "MALFORMED_JSON"
    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    API_NOT_FOUND = "API_NOT_FOUND"
    INTERNAL_TRANSPORT_ERROR = "INTERNAL_TRANSPORT_ERROR"


class TransportErrorResponse(BaseModel):
    """Strict, immutable transport error envelope."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    transport_status: Literal["ERROR"] = "ERROR"
    transport_error_code: TransportErrorCode
    message_vi: str
    message_en: str
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Observational system health response schema."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    status: str
    version: str
    milestone: str
    algebra_authority: str
    supported_input_modes: List[str]
    registered_methods_count: int
    executable_methods_count: int
