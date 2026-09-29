"""Contracts, data models, error taxonomies, and telemetry models for MKE AI Intake."""

import datetime
from typing import Dict, Any, Optional, List, Tuple, Type
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data Models for Intake Requests and Responses
# ---------------------------------------------------------------------------

class ModelExtractionRequest(BaseModel):
    """Input payload representing a raw student math query."""
    raw_query: str = Field(..., min_length=1, description="Raw student text / math question")
    target_locale: str = Field(default="vi_VN", description="Language locale")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional caller context")


class ModelExtractionResponse(BaseModel):
    """Structured response from an LLM extraction adapter."""
    raw_response_text: str = Field(..., description="Raw text returned by model")
    structured_payload: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON payload")
    latency_seconds: float = Field(default=0.0, ge=0.0, description="End-to-end execution time in seconds")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Input/Output token counts")
    provider_id: str = Field(default="", description="Identifier of the serving provider")
    model_id: str = Field(default="", description="Model ID used for extraction")
    is_success: bool = Field(default=True, description="True if extraction succeeded")
    error_message: Optional[str] = Field(default=None, description="Error detail if is_success is False")


# ---------------------------------------------------------------------------
# Provider Error Taxonomy
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Base exception for all AI provider adapter operations."""
    def __init__(self, message: str, provider_id: str = "", is_retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id
        self.is_retryable = is_retryable


class ProviderTimeoutError(ProviderError):
    """Raised when an external or local provider request exceeds configured timeout."""
    def __init__(self, message: str = "Provider request timed out", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=True)


class ProviderRateLimitError(ProviderError):
    """Raised when provider returns HTTP 429 / Rate Limit exceeded."""
    def __init__(self, message: str = "Provider rate limit exceeded", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=True)


class ProviderUnavailableError(ProviderError):
    """Raised when provider returns HTTP 503 / Network connection error."""
    def __init__(self, message: str = "Provider service unavailable", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=True)


class ProviderAuthenticationError(ProviderError):
    """Raised on invalid credentials or authorization failure (permanent)."""
    def __init__(self, message: str = "Provider authentication failed", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=False)


class ProviderSchemaValidationError(ProviderError):
    """Raised when model returns malformed JSON or invalid schema (permanent)."""
    def __init__(self, message: str = "Model output failed schema validation", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=False)


class ProviderSecurityRejectionError(ProviderError):
    """Raised when prompt injection or unsafe content is detected (permanent)."""
    def __init__(self, message: str = "Prompt injection or safety violation detected", provider_id: str = ""):
        super().__init__(message, provider_id=provider_id, is_retryable=False)


# ---------------------------------------------------------------------------
# Retry Policy Specification
# ---------------------------------------------------------------------------

class RetryPolicy(BaseModel):
    """Configurable retry policy for transient provider failures."""
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retry attempts")
    initial_delay_seconds: float = Field(default=0.1, ge=0.0, description="Initial backoff delay in seconds")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, description="Exponential backoff factor")
    max_delay_seconds: float = Field(default=5.0, ge=0.0, description="Maximum backoff cap in seconds")


# ---------------------------------------------------------------------------
# Sanitized Minimal Telemetry Record
# ---------------------------------------------------------------------------

class TelemetryRecord(BaseModel):
    """Sanitized telemetry record omitting raw student PII and authentication credentials."""
    timestamp_iso: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    provider_id: str
    model_id: str
    latency_seconds: float
    token_usage: Dict[str, int]
    query_char_length: int
    is_success: bool
    error_type: Optional[str] = None
