"""Unit tests for P1C-02-R2 Provider-Agnostic Mock Adapter, Validation, and Safety."""

import asyncio
import pytest
from typing import Dict, Any

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
from mke_product.ai.mock_adapter import (
    MockModelProviderAdapter,
    sanitize_text,
    PROMPT_INJECTION_PATTERNS,
)


@pytest.fixture(autouse=True)
def setup_registry():
    """Ensure registry has mock provider registered before each test."""
    ModelProviderRegistry.clear()
    ModelProviderRegistry.register("mock", MockModelProviderAdapter)
    yield
    ModelProviderRegistry.clear()


# ---------------------------------------------------------------------------
# Task 1: Protect Student Data & Strict Fixture Boundary Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exact_mock_fixture_mapping_2_pow_x_eq_8():
    """TASK 1: Verify exact fixture lookup. '2^x = 8' must NEVER return 'x^2 - 4 = 0'."""
    adapter = MockModelProviderAdapter()
    req = ModelExtractionRequest(raw_query="2^x = 8")

    resp = await adapter.extract_math_ir(req)
    assert resp.is_success is True
    assert resp.structured_payload["primary_expressions"] == ["2^x = 8"]
    assert resp.structured_payload["primary_expressions"] != ["x^2 - 4 = 0"]


@pytest.mark.asyncio
async def test_unmatched_query_fails_explicitly_without_guessing():
    """TASK 1: Unmatched queries (e.g. word problems) must fail explicitly with typed ProviderError."""
    adapter = MockModelProviderAdapter()
    req = ModelExtractionRequest(raw_query="Một người đi xe máy từ Hà Nội về Hải Phòng...")

    with pytest.raises(ProviderError) as exc_info:
        await adapter.extract_math_ir(req)
    assert "No matching mock fixture registered for request" in str(exc_info.value)
    assert "Một người đi xe máy" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_unmatched_query_with_sensitive_student_data_fails_safely():
    """TASK 1: Raw student PII and credentials must never appear in error messages or telemetry."""
    adapter = MockModelProviderAdapter()
    sensitive_query = "Học sinh Nguyễn Văn A email nguyen.van.a@school.edu.vn dùng key sk-1234567890abcdef1234567890abcdef và Bearer tok_xyz987 giải phương trình khó"
    req = ModelExtractionRequest(raw_query=sensitive_query)

    with pytest.raises(ProviderError) as exc_info:
        await adapter.extract_math_ir(req)

    error_msg = str(exc_info.value)
    assert "nguyen.van.a@school.edu.vn" not in error_msg
    assert "Nguyễn Văn A" not in error_msg
    assert "sk-1234567890abcdef1234567890abcdef" not in error_msg
    assert "tok_xyz987" not in error_msg
    assert "No matching mock fixture registered for request" in error_msg

    # Verify telemetry history does not contain student query or PII
    for record in adapter.telemetry_history:
        telemetry_str = str(record.dict())
        assert "nguyen.van.a" not in telemetry_str
        assert "sk-1234567890" not in telemetry_str
        assert "Nguyễn Văn A" not in telemetry_str


@pytest.mark.asyncio
async def test_custom_fixture_override_takes_precedence():
    """TASK 1: fixture_override allows testing arbitrary custom problem structures."""
    custom_fixture = {
        "problem_category": "EQUATION_SYSTEM",
        "question_format": "FREE_FORM",
        "target_variables": ["x", "y"],
        "primary_expressions": ["x + y = 3", "2*x - y = 0"]
    }
    adapter = MockModelProviderAdapter(fixture_override=custom_fixture)
    req = ModelExtractionRequest(raw_query="Hệ phương trình x+y=3, 2x-y=0")

    resp = await adapter.extract_math_ir(req)
    assert resp.is_success is True
    assert resp.structured_payload["primary_expressions"] == ["x + y = 3", "2*x - y = 0"]


# ---------------------------------------------------------------------------
# Schema and Structural Validation Contract Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_positive_structural_validation():
    """Valid dictionary payload passes structural validation cleanly."""
    valid_fixture = {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "primary_expressions": ["x^2 - 5*x + 6 = 0"],
        "target_variables": ["x"]
    }
    adapter = MockModelProviderAdapter(fixture_override=valid_fixture)
    req = ModelExtractionRequest(raw_query="x^2 - 5x + 6 = 0")

    resp = await adapter.extract_math_ir(req)
    assert resp.structured_payload == valid_fixture


@pytest.mark.asyncio
async def test_negative_structural_validation_non_dict_payload():
    """Non-dict payload raises ProviderSchemaValidationError."""
    adapter = MockModelProviderAdapter(raw_text_override='"A plain string JSON"')
    req = ModelExtractionRequest(raw_query="x = 1")

    with pytest.raises(ProviderSchemaValidationError) as exc_info:
        await adapter.extract_math_ir(req)
    assert "must be a dictionary" in str(exc_info.value)


@pytest.mark.asyncio
async def test_negative_structural_validation_primary_expressions_as_string():
    """primary_expressions as str instead of list raises ProviderSchemaValidationError."""
    invalid_fixture = {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "primary_expressions": "x^2 = 4",  # Invalid type (should be list)
        "target_variables": ["x"]
    }
    adapter = MockModelProviderAdapter(fixture_override=invalid_fixture)
    req = ModelExtractionRequest(raw_query="x^2 = 4")

    with pytest.raises(ProviderSchemaValidationError) as exc_info:
        await adapter.extract_math_ir(req)
    assert "'primary_expressions' must be a non-empty list of non-empty strings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_negative_structural_validation_empty_primary_expressions():
    """Empty primary_expressions list raises ProviderSchemaValidationError."""
    invalid_fixture = {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "primary_expressions": [],
        "target_variables": ["x"]
    }
    adapter = MockModelProviderAdapter(fixture_override=invalid_fixture)
    req = ModelExtractionRequest(raw_query="x^2 = 4")

    with pytest.raises(ProviderSchemaValidationError) as exc_info:
        await adapter.extract_math_ir(req)
    assert "'primary_expressions' must be a non-empty list of non-empty strings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_negative_structural_validation_invalid_target_variables_type():
    """target_variables as non-list raises ProviderSchemaValidationError."""
    invalid_fixture = {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "primary_expressions": ["x = 1"],
        "target_variables": "x"  # Invalid type (should be list)
    }
    adapter = MockModelProviderAdapter(fixture_override=invalid_fixture)
    req = ModelExtractionRequest(raw_query="x = 1")

    with pytest.raises(ProviderSchemaValidationError) as exc_info:
        await adapter.extract_math_ir(req)
    assert "'target_variables' must be a list of strings" in str(exc_info.value)


@pytest.mark.asyncio
async def test_malicious_math_string_remains_inert():
    """Adversarial code string in payload is deserialized as plain text without execution."""
    malicious_fixture = {
        "problem_category": "EQUATION_SINGLE",
        "question_format": "FREE_FORM",
        "primary_expressions": ["__import__('os').system('echo hacked')"],
        "target_variables": ["x"]
    }
    adapter = MockModelProviderAdapter(fixture_override=malicious_fixture)
    req = ModelExtractionRequest(raw_query="x = 1")

    resp = await adapter.extract_math_ir(req)
    assert resp.structured_payload["primary_expressions"] == ["__import__('os').system('echo hacked')"]


# ---------------------------------------------------------------------------
# Task 2: Honest Explanation Output Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_explanation_illustrative_mock_banner_present():
    """TASK 2: All mock explanations must remain explicitly marked as illustrative mock output."""
    adapter = MockModelProviderAdapter()
    raw_query = "x^2 = 4"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x^2 = 4"]}
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "symbolic_result": "{-2, 2}",
        "domain_certainty": "PROVEN_REALS",
        "verification_evidence": {
            "completeness_certified": True,
            "completeness_category": "CERTIFIED_POLYNOMIAL_DEGREE_2"
        }
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "[MINH HỌA MÔ PHỎNG - MOCK ONLY]" in explanation


@pytest.mark.asyncio
async def test_explanation_missing_status_fails_safely():
    """TASK 2: Missing mathematical_status returns error notice rather than solution."""
    adapter = MockModelProviderAdapter()
    raw_query = "x^2 = 4"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x^2 = 4"]}

    # Missing status in dict
    explanation = await adapter.render_explanation(raw_query, structured_ir, {})
    assert "Thông báo lỗi kiểm chứng" in explanation
    assert "thiếu mathematical_status" in explanation
    assert "[MINH HỌA MÔ PHỎNG - MOCK ONLY]" in explanation

    # None cas_evidence
    explanation_none = await adapter.render_explanation(raw_query, structured_ir, None)
    assert "Thông báo lỗi kiểm chứng" in explanation_none


@pytest.mark.asyncio
async def test_explanation_unexpected_or_unsupported_status():
    """TASK 2: Unexpected / uncertified statuses return unconfirmed status notice."""
    adapter = MockModelProviderAdapter()
    raw_query = "test"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x = 1"]}

    explanation = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "SUPER_RESOLVED"})
    assert "Thông báo trạng thái không xác định" in explanation
    assert "SUPER_RESOLVED" in explanation
    assert "không được công nhận là trạng thái toán học hợp lệ" in explanation


@pytest.mark.asyncio
async def test_explanation_success_without_verification_evidence():
    """TASK 2: SUCCESS without verification_evidence must NOT imply complete solution."""
    adapter = MockModelProviderAdapter()
    raw_query = "2^x = 8"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["2^x = 8"]}
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "symbolic_result": "{3}",
        "domain_certainty": "PROVEN_REALS"
        # verification_evidence omitted
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "Chưa chứng minh tính đầy đủ" in explanation
    assert "Chưa chứng minh tính vét cạn" in explanation
    assert "Tính đầy đủ: `False`" in explanation
    assert "Đã chứng minh đầy đủ" not in explanation


@pytest.mark.asyncio
async def test_explanation_success_with_completeness_certified_false():
    """TASK 2: SUCCESS with completeness_certified=False must state completeness is uncertified."""
    adapter = MockModelProviderAdapter()
    raw_query = "2^x + 3^x = 7"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["2^x + 3^x = 7"]}
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "symbolic_result": "{1.5}",
        "domain_certainty": "PROVEN_REALS",
        "verification_evidence": {
            "completeness_certified": False,
            "completeness_category": "UNCERTIFIED"
        }
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "Chưa chứng minh tính đầy đủ" in explanation
    assert "Tính đầy đủ: `False`" in explanation
    assert "UNCERTIFIED" in explanation
    assert "Đã chứng minh đầy đủ" not in explanation


@pytest.mark.asyncio
async def test_explanation_success_with_missing_symbolic_result():
    """TASK 2: SUCCESS with missing symbolic_result must explicitly flag absence."""
    adapter = MockModelProviderAdapter()
    raw_query = "x = 1"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x = 1"]}
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "domain_certainty": "PROVEN_REALS",
        "verification_evidence": {
            "completeness_certified": True,
            "completeness_category": "CERTIFIED_LINEAR"
        }
        # symbolic_result omitted
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "thiếu symbolic_result" in explanation


@pytest.mark.asyncio
async def test_explanation_success_certified_equation():
    """TASK 2: SUCCESS with certified completeness properly reports full verified solution."""
    adapter = MockModelProviderAdapter()
    raw_query = "x^2 = 4"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x^2 = 4"]}
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "symbolic_result": "{-2, 2}",
        "domain_certainty": "PROVEN_REALS",
        "verification_evidence": {
            "completeness_certified": True,
            "completeness_category": "CERTIFIED_POLYNOMIAL_DEGREE_2",
            "root_count": 2,
            "roots": ["-2", "2"]
        }
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "Đã chứng minh đầy đủ" in explanation
    assert "{-2, 2}" in explanation
    assert "Tính đầy đủ: `True`" in explanation
    assert "CERTIFIED_POLYNOMIAL_DEGREE_2" in explanation


@pytest.mark.asyncio
async def test_explanation_non_equation_operation_does_not_infer_completeness():
    """TASK 2: For non-equation operations, do not infer solution-set completeness from SUCCESS."""
    adapter = MockModelProviderAdapter()
    raw_query = "Rút gọn biểu thức (x+1)^2"
    structured_ir = {
        "problem_category": "EXPRESSION_SIMPLIFY",
        "primary_expressions": ["(x+1)^2"]
    }
    cas_evidence = {
        "mathematical_status": "SUCCESS",
        "symbolic_result": "x^2 + 2*x + 1",
        "domain_certainty": "PROVEN_REALS"
    }

    explanation = await adapter.render_explanation(raw_query, structured_ir, cas_evidence)
    assert "Kết quả biến đổi / tính toán" in explanation
    assert "x^2 + 2*x + 1" in explanation
    assert "Không áp dụng chứng nhận tập nghiệm" in explanation
    assert "Tập nghiệm" not in explanation


@pytest.mark.asyncio
async def test_explanation_adversarial_statuses():
    """TASK 2: Non-SUCCESS statuses must never be presented as verified solutions."""
    adapter = MockModelProviderAdapter()
    raw_query = "test query"
    structured_ir = {"problem_category": "EQUATION_SINGLE", "primary_expressions": ["x = 1"]}

    # 1. OUT_OF_SCOPE
    oos = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "OUT_OF_SCOPE"})
    assert "OUT_OF_SCOPE" in oos
    assert "chưa được hỗ trợ chứng minh tự động" in oos

    # 2. INVALID_INPUT
    inv = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "INVALID_INPUT"})
    assert "INVALID_INPUT" in inv
    assert "không hợp lệ hoặc cú pháp biểu thức không được chấp nhận" in inv

    # 3. UNRESOLVED
    unres = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "UNRESOLVED"})
    assert "UNRESOLVED" in unres
    assert "chưa thể xác định lời giải đóng hoàn chỉnh" in unres

    # 4. DOMAIN_ERROR
    dom = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "DOMAIN_ERROR"})
    assert "DOMAIN_ERROR" in dom
    assert "vi phạm điều kiện xác định toán học" in dom

    # 5. SECURITY_REJECTED
    sec = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "SECURITY_REJECTED"})
    assert "SECURITY_REJECTED" in sec
    assert "vi phạm quy tắc an toàn" in sec

    # 6. RESOURCE_EXHAUSTED
    res = await adapter.render_explanation(raw_query, structured_ir, {"mathematical_status": "RESOURCE_EXHAUSTED"})
    assert "RESOURCE_EXHAUSTED" in res
    assert "vượt quá giới hạn thời gian hoặc bộ nhớ" in res

    # 7. PARTIAL
    part = await adapter.render_explanation(
        raw_query, structured_ir, {"mathematical_status": "PARTIAL", "symbolic_result": "{1}"}
    )
    assert "PARTIAL" in part
    assert "Chưa chứng minh tính đầy đủ" in part


# ---------------------------------------------------------------------------
# Cancellation and Error Propagation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_asyncio_cancellation_propagates_cleanly():
    """Verify CancelledError propagates without being swallowed."""
    adapter = MockModelProviderAdapter(simulated_latency_seconds=1.0)
    req = ModelExtractionRequest(raw_query="x = 1")

    task = asyncio.create_task(adapter.extract_math_ir(req))
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_retry_policy_retries_transient_and_stops_on_permanent():
    """Verify RetryPolicy retries transient errors and fails on permanent errors."""
    # Transient rate limit recovers:
    adapter = MockModelProviderAdapter(
        fault_mode="rate_limit",
        transient_failures_remaining=2,
        fixture_override={"problem_category": "EQUATION_SINGLE", "question_format": "FREE_FORM", "primary_expressions": ["x = 1"]}
    )
    req = ModelExtractionRequest(raw_query="x = 1")
    policy = RetryPolicy(max_retries=3, initial_delay_seconds=0.001)

    resp = await adapter.execute_with_retry(lambda: adapter.extract_math_ir(req), retry_policy=policy)
    assert resp.is_success is True
    assert adapter.call_count == 3

    # Permanent auth error halts immediately:
    adapter_auth = MockModelProviderAdapter(fault_mode="auth_error")
    with pytest.raises(ProviderAuthenticationError):
        await adapter_auth.execute_with_retry(lambda: adapter_auth.extract_math_ir(req), retry_policy=policy)
    assert adapter_auth.call_count == 1


def test_pii_and_credential_sanitization():
    """Verify email and token patterns are scrubbed from telemetry."""
    dirty = "Query from user.test@domain.com with auth key sk-987654321098765432109876"
    clean = sanitize_text(dirty)
    assert "[REDACTED_EMAIL]" in clean
    assert "[REDACTED_CREDENTIAL]" in clean
    assert "user.test@domain.com" not in clean
    assert "sk-987654321098765432109876" not in clean
