"""Deterministic Mock Model Provider Adapter for MKE AI Intake testing.

Provides zero-network, zero-GPU, fixture-driven extraction and explanation generation
with strict deterministic fixture matching, structural schema validation, and safe
explanation rendering.
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List

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


def normalize_query_key(query: str) -> str:
    """Normalize query string for deterministic exact fixture lookup."""
    return re.sub(r"\s+", " ", query.strip().lower())


# Exact deterministic mock fixtures for recognized test queries
EXACT_MOCK_FIXTURES: Dict[str, Dict[str, Any]] = {
    normalize_query_key("Giải phương trình log(x-1, 2) = 3"): {
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
    },
    normalize_query_key("2^x = 8"): {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "target_variables": ["x"],
        "parameters": [],
        "primary_expressions": ["2^x = 8"],
        "extracted_constraints": [],
        "subparts": [],
        "given_options": None,
        "model_confidence": 0.98,
        "uncertainty_flags": []
    },
    normalize_query_key("Giải phương trình 2^x = 8"): {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "target_variables": ["x"],
        "parameters": [],
        "primary_expressions": ["2^x = 8"],
        "extracted_constraints": [],
        "subparts": [],
        "given_options": None,
        "model_confidence": 0.98,
        "uncertainty_flags": []
    },
    normalize_query_key("sin(x) = 1/2"): {
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
    },
    normalize_query_key("x^2 = 4"): {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "target_variables": ["x"],
        "parameters": [],
        "primary_expressions": ["x^2 = 4"],
        "extracted_constraints": [],
        "subparts": [],
        "given_options": None,
        "model_confidence": 0.99,
        "uncertainty_flags": []
    },
    normalize_query_key("x + 1 = 2"): {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "target_variables": ["x"],
        "parameters": [],
        "primary_expressions": ["x + 1 = 2"],
        "extracted_constraints": [],
        "subparts": [],
        "given_options": None,
        "model_confidence": 0.99,
        "uncertainty_flags": []
    },
    normalize_query_key("x = 1"): {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "target_variables": ["x"],
        "parameters": [],
        "primary_expressions": ["x = 1"],
        "extracted_constraints": [],
        "subparts": [],
        "given_options": None,
        "model_confidence": 0.99,
        "uncertainty_flags": []
    }
}


class MockModelProviderAdapter(ModelProviderAdapter):
    """Deterministic Mock Adapter for AI Intake unit and integration testing.

    Safety Guarantee:
    - This adapter NEVER executes text returned by a model via exec(), eval(), or subshell.
    - All model strings remain inert data objects.
    - Mathematical AST validation and certified execution are exclusively handled by CAS dispatcher in P1C-03.
    """

    def __init__(
        self,
        model_id: str = "mock-math-v1",
        simulated_latency_seconds: float = 0.001,
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

        # 1. Prompt injection filter on raw query
        sanitized_query = sanitize_text(request.raw_query)
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(request.raw_query):
                record = TelemetryRecord(
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    latency_seconds=time.perf_counter() - start_time,
                    token_usage={"input_tokens": max(1, len(sanitized_query) // 4), "output_tokens": 0},
                    query_char_length=len(sanitized_query),
                    is_success=False,
                    error_type="SECURITY_REJECTION"
                )
                self.telemetry_history.append(record)
                raise ProviderSecurityRejectionError(
                    "Security filter blocked prompt with adversarial injection signature",
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

        # 3. Simulate latency & timeout boundary
        if timeout and self.simulated_latency_seconds > timeout:
            await asyncio.sleep(timeout)
            raise ProviderTimeoutError(
                f"Request exceeded timeout of {timeout}s",
                provider_id=self.provider_id
            )
        await asyncio.sleep(self.simulated_latency_seconds)

        # 4. Resolve response payload with strict fixture mapping (Task A)
        if self.raw_text_override is not None:
            raw_text = self.raw_text_override
            try:
                parsed_payload = json.loads(raw_text)
            except Exception as e:
                raise ProviderSchemaValidationError(
                    f"Model output is not valid JSON: {str(e)}",
                    provider_id=self.provider_id
                ) from e
        elif self.fixture_override is not None:
            parsed_payload = self.fixture_override
            raw_text = json.dumps(parsed_payload)
        else:
            # Look up exact recognized fixture
            norm_key = normalize_query_key(request.raw_query)
            if norm_key in EXACT_MOCK_FIXTURES:
                parsed_payload = EXACT_MOCK_FIXTURES[norm_key]
                raw_text = json.dumps(parsed_payload)
            else:
                # Unmatched input -> fail explicitly with fixed typed error without leaking student input
                raise ProviderError(
                    "No matching mock fixture registered for request. Use fixture_override for custom test fixtures.",
                    provider_id=self.provider_id,
                    is_retryable=False
                )

        # 5. Schema and structural type validation (Task B)
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
        """Render deterministic step-by-step Vietnamese explanation grounded in CAS evidence.

        Task 2 (Honest Explanation Output):
        - All mock responses remain explicitly marked as illustrative mock output.
        - Non-SUCCESS statuses (OUT_OF_SCOPE, INVALID_INPUT, UNRESOLVED, DOMAIN_ERROR,
          SECURITY_REJECTED, RESOURCE_EXHAUSTED, PARTIAL) and missing statuses are never
          presented as verified complete solutions.
        - For equation solving under SUCCESS, requires explicit completeness certification
          (completeness_certified == True) before using complete-solution language.
        - For non-equation operations under SUCCESS, does not infer solution-set completeness.
        - Never invents proof steps, derivations, or fictitious CAS nodes.
        """
        if not isinstance(cas_evidence, dict):
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo lỗi kiểm chứng\n"
                "- Trạng thái động cơ không xác định (thiếu mathematical_status).\n"
                "- Không thể tạo lời giải khi thiếu bằng chứng toán học."
            )

        status = cas_evidence.get("mathematical_status")
        if not status:
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo lỗi kiểm chứng\n"
                "- Trạng thái động cơ không xác định (thiếu mathematical_status).\n"
                "- Không thể tạo lời giải khi thiếu bằng chứng toán học."
            )

        status_str = str(status).upper()

        if status_str == "OUT_OF_SCOPE":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo phạm vi giải toán\n"
                "- Dạng bài toán chưa được hỗ trợ chứng minh tự động trong MKE.\n"
                "- Trạng thái động cơ: `OUT_OF_SCOPE`."
            )
        elif status_str == "INVALID_INPUT":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo dữ liệu đầu vào\n"
                "- Dữ liệu bài toán không hợp lệ hoặc cú pháp biểu thức không được chấp nhận.\n"
                "- Trạng thái động cơ: `INVALID_INPUT`."
            )
        elif status_str == "UNRESOLVED":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo kết quả\n"
                "- Động cơ toán học chưa thể xác định lời giải đóng hoàn chỉnh.\n"
                "- Trạng thái động cơ: `UNRESOLVED`."
            )
        elif status_str == "DOMAIN_ERROR":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo vi phạm miền xác định\n"
                "- Biểu thức bài toán vi phạm điều kiện xác định toán học (ví dụ: căn bậc chẵn âm, chia cho 0 hoặc logarit số không dương).\n"
                "- Trạng thái động cơ: `DOMAIN_ERROR`."
            )
        elif status_str == "SECURITY_REJECTED":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Cảnh báo an toàn\n"
                "- Yêu cầu tính toán bị từ chối do vi phạm quy tắc an toàn hoặc chứa nội dung không hợp lệ.\n"
                "- Trạng thái động cơ: `SECURITY_REJECTED`."
            )
        elif status_str == "RESOURCE_EXHAUSTED":
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo giới hạn tài nguyên\n"
                "- Quá trình tính toán vượt quá giới hạn thời gian hoặc bộ nhớ cho phép.\n"
                "- Trạng thái động cơ: `RESOURCE_EXHAUSTED`."
            )
        elif status_str == "PARTIAL":
            res = cas_evidence.get("symbolic_result")
            res_str = str(res) if res is not None else "Không có kết quả ký hiệu"
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Kết quả một phần (Chưa chứng minh tính đầy đủ)\n"
                f"- Kết quả tìm được: `{res_str}`.\n"
                "- Lưu ý: Động cơ chưa thể chứng minh tính vét cạn của toàn bộ tập nghiệm.\n"
                "- Trạng thái động cơ: `PARTIAL`."
            )
        elif status_str == "SUCCESS":
            # Determine operation type and completeness certification
            raw_result = cas_evidence.get("symbolic_result")
            has_result = raw_result is not None
            result_str = str(raw_result) if has_result else "Không có kết quả ký hiệu (thiếu symbolic_result)"

            category = str(structured_ir.get("problem_category", "EQUATION_SINGLE")).upper()
            is_equation_op = category in {"EQUATION_SINGLE", "EQUATION_SYSTEM", "INEQUALITY_SINGLE"}

            ve = cas_evidence.get("verification_evidence")
            has_ve = isinstance(ve, dict)
            cert_complete = (ve.get("completeness_certified") is True) if has_ve else False
            cert_cat = str(ve.get("completeness_category", "UNCERTIFIED")) if has_ve else "UNCERTIFIED"
            certainty = cas_evidence.get("domain_certainty", "NOT_FULLY_DETERMINED")
            exprs = structured_ir.get("primary_expressions", [])

            lines = [
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Hướng dẫn giải (GDPT 2018)",
                "1. **Điều kiện xác định (ĐKXĐ):**",
                f"   - Đánh giá miền xác định: `{certainty}`.",
                "2. **Biểu thức toán học tiếp nhận:**",
                f"   - Biểu thức: `{exprs}`.",
            ]

            if is_equation_op:
                if cert_complete and has_result:
                    lines.append("3. **Kết luận nghiệm (Đã chứng minh đầy đủ):**")
                    lines.append(f"   - Tập nghiệm: **{result_str}** (Tính đầy đủ: `True`, Phân loại: `{cert_cat}`).")
                else:
                    lines.append("3. **Kết quả tính toán (Chưa chứng minh tính đầy đủ):**")
                    lines.append(f"   - Giá trị nghiệm tìm được: **{result_str}** (Lưu ý: Chưa chứng minh tính vét cạn, Tính đầy đủ: `{cert_complete}`, Phân loại: `{cert_cat}`).")
            else:
                lines.append("3. **Kết quả biến đổi / tính toán:**")
                lines.append(f"   - Kết quả: **{result_str}** (Trạng thái: `SUCCESS`, Không áp dụng chứng nhận tập nghiệm).")

            return "\n".join(lines)
        else:
            return (
                "### [MINH HỌA MÔ PHỎNG - MOCK ONLY] Thông báo trạng thái không xác định\n"
                f"- Trạng thái động cơ `{status_str}` không được công nhận là trạng thái toán học hợp lệ."
            )

    def _validate_fixture_schema(self, payload: Any) -> None:
        """Validate presence of fundamental MKE-IR keys and basic types (Task B).

        Note: This preliminary structural validation checks JSON format and data types only.
        It does NOT prove mathematical AST safety or semantic correctness. Mathematical AST
        validation is strictly enforced by the CAS dispatcher in P1C-03.
        """
        if not isinstance(payload, dict):
            raise ProviderSchemaValidationError(
                f"Structured payload must be a dictionary, got {type(payload).__name__}",
                provider_id=self.provider_id
            )

        # 1. problem_category
        cat = payload.get("problem_category")
        if not isinstance(cat, str) or not cat.strip():
            raise ProviderSchemaValidationError(
                "Payload missing valid non-empty string 'problem_category'",
                provider_id=self.provider_id
            )

        # 2. question_format
        qf = payload.get("question_format")
        if not isinstance(qf, str) or not qf.strip():
            raise ProviderSchemaValidationError(
                "Payload missing valid non-empty string 'question_format'",
                provider_id=self.provider_id
            )

        # 3. primary_expressions
        exprs = payload.get("primary_expressions")
        if not isinstance(exprs, list) or len(exprs) == 0 or not all(isinstance(e, str) and e.strip() for e in exprs):
            raise ProviderSchemaValidationError(
                "Payload 'primary_expressions' must be a non-empty list of non-empty strings",
                provider_id=self.provider_id
            )

        # 4. target_variables (if present, must be list)
        if "target_variables" in payload:
            tvars = payload["target_variables"]
            if not isinstance(tvars, list) or not all(isinstance(v, str) for v in tvars):
                raise ProviderSchemaValidationError(
                    "Payload 'target_variables' must be a list of strings",
                    provider_id=self.provider_id
                )
