"""Deterministic Mock Model Provider Adapter for MKE AI Intake testing.

Provides zero-network, zero-GPU, fixture-driven extraction and explanation generation
with configurable fault injection (malformed JSON, timeouts, retries, security rejections).
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List, Callable

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
    TelemetryRecord,
)
from mke_product.ai.adapter import ModelProviderAdapter


# Common adversarial injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"__import__", re.IGNORECASE),
    re.compile(r"os\.system", re.IGNORECASE),
    re.compile(r"subprocess\.", re.IGNORECASE),
]

# Sensitive PII / Credential scrubbing regexes
PII_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CREDENTIAL_KEY_PATTERN = re.compile(r"(sk-[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9_.-]+|api_key\s*=\s*['\"][^'\"]+['\"])", re.IGNORECASE)


def sanitize_text(text: str) -> str:
    """Sanitize raw text by redacting emails, API keys, and sensitive auth tokens."""
    sanitized = PII_EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    sanitized = CREDENTIAL_KEY_PATTERN.sub("[REDACTED_CREDENTIAL]", sanitized)
    return sanitized


class MockModelProviderAdapter(ModelProviderAdapter):
    """Deterministic Mock Adapter for AI Intake unit and integration testing."""

    def __init__(
        self,
        model_id: str = "mock-math-v1",
        simulated_latency_seconds: float = 0.01,
        fixture_override: Optional[Dict[str, Any]] = None,
        raw_text_override: Optional[str] = None,
        fault_mode: Optional[str] = None,
        transient_failures_remaining: int = 0,
        **kwargs
    ):
        self._model_id = model_id
        self.simulated_latency_seconds = simulated_latency_seconds
        self.fixture_override = fixture_override
        self.raw_text_override = raw_text_override
        self.fault_mode = fault_mode
        self.transient_failures_remaining = transient_failures_remaining
        self.call_count = 0
        self.telemetry_history: List[TelemetryRecord] = []

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return self._model_id

    async def extract_math_ir(
        self,
        request: ModelExtractionRequest,
        timeout: Optional[float] = None
    ) -> ModelExtractionResponse:
        """Extract structured mathematical intermediate representation deterministically."""
        start_time = time.perf_counter()
        self.call_count += 1

        # 1. Check prompt injection in raw query
        sanitized_query = sanitize_text(request.raw_query)
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(request.raw_query):
                record = TelemetryRecord(
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    latency_seconds=time.perf_counter() - start_time,
                    token_usage={"input_tokens": len(sanitized_query) // 4, "output_tokens": 0},
                    query_char_length=len(sanitized_query),
                    is_success=False,
                    error_type="SECURITY_REJECTION"
                )
                self.telemetry_history.append(record)
                raise ProviderSecurityRejectionError(
                    f"Security filter blocked prompt with adversarial injection signature",
                    provider_id=self.provider_id
                )

        # 2. Simulate configured fault injection modes
        if self.transient_failures_remaining > 0:
            self.transient_failures_remaining -= 1
            if self.fault_mode == "rate_limit":
                raise ProviderRateLimitError("Simulated 429 Rate Limit", provider_id=self.provider_id)
            raise ProviderUnavailableError("Simulated 503 Service Unavailable", provider_id=self.provider_id)

        if self.fault_mode == "timeout":
            if timeout:
                await asyncio.sleep(timeout + 0.1)
            else:
                await asyncio.sleep(0.5)
            raise ProviderTimeoutError("Simulated provider timeout", provider_id=self.provider_id)

        if self.fault_mode == "auth_error":
            raise ProviderAuthenticationError("Simulated 401 Invalid Authentication", provider_id=self.provider_id)

        # 3. Simulate latency
        if timeout and self.simulated_latency_seconds > timeout:
            await asyncio.sleep(timeout)
            raise ProviderTimeoutError(
                f"Request exceeded timeout of {timeout}s",
                provider_id=self.provider_id
            )
        await asyncio.sleep(self.simulated_latency_seconds)

        # 4. Determine response payload
        if self.raw_text_override is not None:
            raw_text = self.raw_text_override
            try:
                parsed_payload = json.loads(raw_text)
            except Exception as e:
                # Malformed JSON mode
                raise ProviderSchemaValidationError(
                    f"Model output is not valid JSON: {str(e)}",
                    provider_id=self.provider_id
                ) from e
        elif self.fixture_override is not None:
            parsed_payload = self.fixture_override
            raw_text = json.dumps(parsed_payload)
        else:
            # Default deterministic mock extraction for standard queries
            parsed_payload = self._generate_default_fixture(request.raw_query)
            raw_text = json.dumps(parsed_payload)

        # 5. Schema validation check on required keys
        self._validate_fixture_schema(parsed_payload)

        latency = time.perf_counter() - start_time
        token_usage = {
            "input_tokens": max(1, len(sanitized_query) // 4),
            "output_tokens": max(1, len(raw_text) // 4),
            "total_tokens": (len(sanitized_query) + len(raw_text)) // 4
        }

        # 6. Record sanitized telemetry
        record = TelemetryRecord(
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_seconds=latency,
            token_usage=token_usage,
            query_char_length=len(sanitized_query),
            is_success=True
        )
        self.telemetry_history.append(record)

        return ModelExtractionResponse(
            raw_response_text=raw_text,
            structured_payload=parsed_payload,
            latency_seconds=latency,
            token_usage=token_usage,
            provider_id=self.provider_id,
            model_id=self.model_id,
            is_success=True
        )

    async def render_explanation(
        self,
        raw_query: str,
        structured_ir: Dict[str, Any],
        cas_evidence: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> str:
        """Render deterministic step-by-step Vietnamese explanation grounded in CAS evidence."""
        status = cas_evidence.get("mathematical_status", "UNKNOWN")
        result = cas_evidence.get("symbolic_result", "None")
        certainty = cas_evidence.get("domain_certainty", "NOT_FULLY_DETERMINED")

        if status == "OUT_OF_SCOPE":
            return (
                "### Thông báo phạm vi giải toán\n"
                "- Bài toán thuộc dạng chưa được hỗ trợ chứng minh tự động trong MKE.\n"
                f"- Trạng thái động cơ: `OUT_OF_SCOPE`."
            )

        explanation_lines = [
            "### Hướng dẫn giải chi tiết (GDPT 2018)",
            "1. **Điều kiện xác định (ĐKXĐ):**",
            f"   - Đánh giá miền xác định: `{certainty}`.",
            "2. **Các bước biến đổi đại số:**",
            f"   - Phương trình / biểu thức chính: `{structured_ir.get('primary_expressions', [])}`.",
            "3. **Đối chiếu điều kiện & Kết luận:**",
            f"   - Tập nghiệm / Kết quả: **{result}** (Trạng thái: `{status}`)."
        ]
        return "\n".join(explanation_lines)

    def _generate_default_fixture(self, raw_query: str) -> Dict[str, Any]:
        """Generate a realistic deterministic MKE-IR fixture based on simple heuristic cues."""
        if "log" in raw_query.lower() or "ln" in raw_query.lower():
            return {
                "problem_category": "EQUATION_SINGLE",
                "question_format": "FREE_FORM",
                "target_variables": ["x"],
                "parameters": [],
                "primary_expressions": ["log(x-1, 2) = 3"],
                "extracted_constraints": [
                    {"variable": "x", "relation": ">", "bound_expression": "1"}
                ],
                "subparts": [],
                "given_options": None,
                "model_confidence": 0.95,
                "uncertainty_flags": []
            }
        elif "sin" in raw_query.lower() or "cos" in raw_query.lower() or "tan" in raw_query.lower():
            return {
                "problem_category": "EQUATION_SINGLE",
                "question_format": "FREE_FORM",
                "target_variables": ["x"],
                "parameters": [],
                "primary_expressions": ["sin(x) = 1/2"],
                "extracted_constraints": [],
                "subparts": [],
                "given_options": None,
                "model_confidence": 0.92,
                "uncertainty_flags": []
            }
        else:
            return {
                "problem_category": "EQUATION_SINGLE",
                "question_format": "FREE_FORM",
                "target_variables": ["x"],
                "parameters": [],
                "primary_expressions": ["x^2 - 4 = 0"],
                "extracted_constraints": [],
                "subparts": [],
                "given_options": None,
                "model_confidence": 0.98,
                "uncertainty_flags": []
            }

    def _validate_fixture_schema(self, payload: Dict[str, Any]) -> None:
        """Validate presence of fundamental MKE-IR keys."""
        required_keys = ["problem_category", "question_format", "primary_expressions"]
        for k in required_keys:
            if k not in payload:
                raise ProviderSchemaValidationError(
                    f"Structured payload missing required key: '{k}'",
                    provider_id=self.provider_id
                )
