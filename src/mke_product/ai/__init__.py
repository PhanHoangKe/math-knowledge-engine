"""MKE AI Intake Module.

Provides provider-agnostic LLM adapters, intermediate representations, and verification bridges.
"""

from mke_product.ai.contracts import (
    ModelExtractionRequest,
    ModelExtractionResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderAuthenticationError,
    ProviderSchemaValidationError,
    ProviderSecurityRejectionError,
    RetryPolicy,
    TelemetryRecord,
)
from mke_product.ai.adapter import ModelProviderAdapter
from mke_product.ai.registry import ModelProviderRegistry
from mke_product.ai.mock_adapter import MockModelProviderAdapter

__all__ = [
    "ModelExtractionRequest",
    "ModelExtractionResponse",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
    "ProviderAuthenticationError",
    "ProviderSchemaValidationError",
    "ProviderSecurityRejectionError",
    "RetryPolicy",
    "TelemetryRecord",
    "ModelProviderAdapter",
    "ModelProviderRegistry",
    "MockModelProviderAdapter",
]
