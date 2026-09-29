"""MKE AI Intake Module.

Provides provider-agnostic LLM adapters, mathematical intermediate representations (MKE-IR),
and deterministic pre-dispatch validation bridges.
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
from mke_product.ai.ir import (
    SUPPORTED_MKE_IR_SCHEMA_VERSION,
    ProblemCategory,
    QuestionFormat,
    SemanticVerificationStatus,
    SourceSpan,
    ExtractedConstraint,
    QuestionSubpart,
    UncertaintyFlag,
    ValidationIssue,
    ValidationResult,
    PublicValidationDiagnostic,
    MathIntermediateRepresentation,
)
from mke_product.ai.validator import MKEIntakeValidator

__all__ = [
    # Contracts
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
    # Adapters & Registry
    "ModelProviderAdapter",
    "ModelProviderRegistry",
    "MockModelProviderAdapter",
    # MKE-IR Models & Validation
    "SUPPORTED_MKE_IR_SCHEMA_VERSION",
    "ProblemCategory",
    "QuestionFormat",
    "SemanticVerificationStatus",
    "SourceSpan",
    "ExtractedConstraint",
    "QuestionSubpart",
    "UncertaintyFlag",
    "ValidationIssue",
    "ValidationResult",
    "PublicValidationDiagnostic",
    "MathIntermediateRepresentation",
    "MKEIntakeValidator",
]
