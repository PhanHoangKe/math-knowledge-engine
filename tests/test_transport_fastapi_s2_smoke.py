"""Focused transport implementation and contract tests for S2-01 FastAPI adapter."""

import asyncio
import json
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient
from starlette.types import Message
from pydantic import ValidationError

from mke_product.transport.app import create_app
from mke_product.transport.models import TransportErrorCode, TransportErrorResponse
from mke_product.application.dto import (
    SolveRequest,
    RawEquationInput,
    CanonicalCoefficientInput,
    ErrorResponse,
)
from mke_product.application.errors import ApplicationErrorCode
from mke_product.domain.registry import MethodRegistry
from mke_product.application.traces import TRACE_GENERATORS


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ============================================================================
# 1. HEALTH ENDPOINT & REGISTRY OBSERVABILITY
# ============================================================================

def test_api_health_endpoint_derived_counts(client: TestClient):
    """GET /api/v1/health returns HTTP 200 and dynamically derived registry counts."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    registry = MethodRegistry()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "1.0.0"
    assert data["milestone"] == "MVP_V1_S2"
    assert data["algebra_authority"] == "mke_product.application.orchestrator.solve_request"
    assert data["supported_input_modes"] == ["RAW_TEXT", "COEFFICIENTS"]
    assert data["registered_methods_count"] == len(registry.list_all())
    assert data["executable_methods_count"] == len(TRACE_GENERATORS)


# ============================================================================
# 2. ALGEBRA SOLVE ENDPOINT - MATHEMATICAL INTEGRATION (CATEGORY A / SOLVED)
# ============================================================================

def test_api_solve_raw_text_success(client: TestClient):
    """POST /api/v1/algebra/solve with RAW_TEXT returns HTTP 200 SOLVED."""
    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_status"] == "SOLVED"
    assert data["problem"]["classification"] == "QUADRATIC"
    assert len(data["solution"]["roots"]) == 2
    assert len(data["available_methods"]) == 9
    assert data["solution"]["certificate"]["outcome"] == "VERIFIED_COMPLETE"


def test_api_solve_coefficients_success(client: TestClient):
    """POST /api/v1/algebra/solve with COEFFICIENTS returns HTTP 200 SOLVED."""
    payload = {
        "input_payload": {
            "input_mode": "COEFFICIENTS",
            "a": {"numerator": 1, "denominator": 1},
            "b": {"numerator": -5, "denominator": 1},
            "c": {"numerator": 6, "denominator": 1},
            "target_variable": "x",
        },
        "selected_method_id": "QUAD_FORMULA_REDUCED",
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_status"] == "SOLVED"
    assert data["selected_method_id"] == "QUAD_FORMULA_REDUCED"
    assert data["solution"]["method_id"] == "QUAD_FORMULA_REDUCED"


def test_api_solve_mathematical_syntax_error_returns_http_200(client: TestClient):
    """Category-A Client domain errors (e.g. SYNTAX_ERROR) return HTTP 200 with ErrorResponse."""
    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 + = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_status"] == "ERROR"
    assert data["error_code"] == "SYNTAX_ERROR"
    assert data["span"] is not None


# ============================================================================
# 3. CATEGORY-B INTERNAL APPLICATION ERROR STATUS ADAPTER (HTTP 500)
# ============================================================================

@pytest.mark.parametrize(
    "internal_code",
    [
        ApplicationErrorCode.NORMALIZATION_ERROR,
        ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
        ApplicationErrorCode.METHOD_EXECUTION_FAILED,
        ApplicationErrorCode.VERIFICATION_FAILED,
        ApplicationErrorCode.INTERNAL_ERROR,
    ],
)
def test_api_category_b_application_errors_map_to_http_500(monkeypatch, client: TestClient, internal_code: ApplicationErrorCode):
    """Category-B internal failures return HTTP 500 with unmutated ErrorResponse body."""
    simulated_error = ErrorResponse(
        error_code=internal_code,
        message_vi="Lỗi kiểm định nội bộ giả lập.",
        message_en="Simulated internal verification error.",
        span=None,
        details={"simulated": True},
    )

    import mke_product.transport.routers.algebra as algebra_mod
    monkeypatch.setattr(algebra_mod, "solve_request", lambda req: simulated_error)

    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert data["response_status"] == "ERROR"
    assert data["error_code"] == internal_code.value
    assert data["message_vi"] == "Lỗi kiểm định nội bộ giả lập."
    assert data["details"] == {"simulated": True}


# ============================================================================
# 4. MALFORMED JSON & SANITIZED REQUEST VALIDATION (HTTP 400 & 422)
# ============================================================================

def test_api_malformed_json_returns_http_400(client: TestClient):
    """Malformed JSON returns HTTP 400 with TransportErrorResponse(MALFORMED_JSON)."""
    malformed_body = b'{"input_payload": {"input_mode": "RAW_TEXT", "raw_query": '  # truncated
    response = client.post(
        "/api/v1/algebra/solve",
        content=malformed_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "MALFORMED_JSON"
    assert "Định dạng JSON trong yêu cầu không hợp lệ." in data["message_vi"]


def test_api_dto_validation_failure_sanitized_422(client: TestClient):
    """Schema violations return HTTP 422 with sanitized details (type/loc/msg only, no sentinel/input leaks)."""
    invalid_dto_body = {
        "input_payload": {
            "input_mode": "UNKNOWN_MODE",  # Invalid enum value
            "secret_sentinel": "LEAK_ME_IF_UNSANITIZED",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=invalid_dto_body)
    assert response.status_code == 422
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "REQUEST_VALIDATION_FAILED"
    assert "validation_errors" in data["details"]
    errors = data["details"]["validation_errors"]
    assert len(errors) > 0
    for err in errors:
        assert set(err.keys()) == {"type", "loc", "msg"}
        # Ensure raw input object or secret sentinels are not present
        assert "LEAK_ME_IF_UNSANITIZED" not in str(err)
        assert "input" not in err
        assert "ctx" not in err


# ============================================================================
# 5. MEDIA TYPE ENFORCEMENT (HTTP 415)
# ============================================================================

def test_api_media_type_text_plain_rejected_415(client: TestClient):
    """Content-Type: text/plain returns HTTP 415 TransportErrorResponse(UNSUPPORTED_MEDIA_TYPE)."""
    response = client.post(
        "/api/v1/algebra/solve",
        content=b"x^2 - 5*x + 6 = 0",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_api_media_type_invalid_suffix_rejected_415(client: TestClient):
    """Content-Type: application/json-not-really returns HTTP 415."""
    response = client.post(
        "/api/v1/algebra/solve",
        content=b"{}",
        headers={"Content-Type": "application/json-not-really"},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["transport_error_code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_api_media_type_with_charset_accepted_200(client: TestClient):
    """Content-Type: application/json; charset=utf-8 is accepted."""
    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post(
        "/api/v1/algebra/solve",
        content=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    assert response.status_code == 200
    assert response.json()["response_status"] == "SOLVED"


# ============================================================================
# 6. PAYLOAD SIZE LIMITS (64 KiB = 65,536 BYTES) & EXACT BOUNDARY (HTTP 413)
# ============================================================================

def test_api_payload_limit_declared_header_rejected_413(client: TestClient):
    """Declared Content-Length: 65537 returns HTTP 413 TransportErrorResponse(PAYLOAD_TOO_LARGE)."""
    response = client.post(
        "/api/v1/algebra/solve",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "65537"},
    )
    assert response.status_code == 413
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "PAYLOAD_TOO_LARGE"


def test_api_payload_limit_exact_65536_boundary_accepted(client: TestClient):
    """Exact 65,536-byte valid JSON body passes payload limit middleware and returns HTTP 200."""
    base_dict = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    base_bytes = json.dumps(base_dict).encode("utf-8")
    padding_len = 65536 - len(base_bytes)
    assert padding_len > 0

    padded_json = (
        '{"input_payload": {"input_mode": "RAW_TEXT", "raw_query": "x^2 - 5*x + 6 = 0", "target_variable": "x"}, '
        '"selected_method_id": null, "schema_version": "1.0.0"' + (' ' * padding_len) + '}'
    )
    padded_bytes = padded_json.encode("utf-8")
    diff = 65536 - len(padded_bytes)
    if diff != 0:
        padded_json = (
            '{"input_payload": {"input_mode": "RAW_TEXT", "raw_query": "x^2 - 5*x + 6 = 0", "target_variable": "x"}, '
            '"selected_method_id": null, "schema_version": "1.0.0"' + (' ' * (padding_len + diff)) + '}'
        )
        padded_bytes = padded_json.encode("utf-8")

    assert len(padded_bytes) == 65536

    response = client.post(
        "/api/v1/algebra/solve",
        content=padded_bytes,
        headers={"Content-Type": "application/json", "Content-Length": "65536"},
    )
    assert response.status_code == 200
    assert response.json()["response_status"] == "SOLVED"


@pytest.mark.asyncio
async def test_raw_asgi_streaming_chunks_over_64k_rejected_413():
    """Direct ASGI test: Streamed request chunks exceeding 65,536 bytes without Content-Length trigger HTTP 413."""
    app = create_app()

    # Create chunks totaling 70,000 bytes (7 chunks of 10,000 bytes)
    chunks = [b"a" * 10000 for _ in range(7)]
    chunk_index = 0

    async def mock_receive() -> Message:
        nonlocal chunk_index
        if chunk_index < len(chunks):
            body = chunks[chunk_index]
            chunk_index += 1
            return {
                "type": "http.request",
                "body": body,
                "more_body": chunk_index < len(chunks),
            }
        return {"type": "http.request", "body": b"", "more_body": False}

    sent_messages: List[Dict[str, Any]] = []

    async def mock_send(msg: Message) -> None:
        sent_messages.append(msg)

    scope: Dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/algebra/solve",
        "headers": [
            (b"content-type", b"application/json"),
            # No content-length header!
        ],
    }

    await app(scope, mock_receive, mock_send)

    # Verify that HTTP 413 was emitted
    start_msg = next((m for m in sent_messages if m["type"] == "http.response.start"), None)
    assert start_msg is not None
    assert start_msg["status"] == 413

    body_msg = next((m for m in sent_messages if m["type"] == "http.response.body"), None)
    assert body_msg is not None
    body_data = json.loads(body_msg["body"].decode("utf-8"))
    assert body_data["transport_status"] == "ERROR"
    assert body_data["transport_error_code"] == "PAYLOAD_TOO_LARGE"


# ============================================================================
# 7. API 404 ISOLATION & UNEXPECTED TRANSPORT ERRORS
# ============================================================================

def test_api_unknown_route_returns_json_404(client: TestClient):
    """Unknown /api/* paths return JSON HTTP 404 TransportErrorResponse(API_NOT_FOUND)."""
    response = client.get("/api/v1/nonexistent_path")
    assert response.status_code == 404
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "API_NOT_FOUND"


def test_api_unhandled_transport_exception_returns_http_500(monkeypatch):
    """Unhandled internal transport/framework crash returns sanitized HTTP 500 without stack trace leaks."""
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    import mke_product.transport.routers.algebra as algebra_mod
    def crash(req):
        raise RuntimeError("CRITICAL_INTERNAL_TRANSPORT_CRASH_SECRET")

    monkeypatch.setattr(algebra_mod, "solve_request", crash)

    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "INTERNAL_TRANSPORT_ERROR"
    assert "CRITICAL_INTERNAL_TRANSPORT_CRASH_SECRET" not in str(data)


# ============================================================================
# 8. OPENAPI OPERATION IDS & TRANSPORT MODEL RIGIDITY
# ============================================================================

def test_openapi_operation_ids_and_schemas(client: TestClient):
    """GET /openapi.json contains stable operation IDs solve_algebra_v1 and health_v1."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]

    assert "/api/v1/algebra/solve" in paths
    assert paths["/api/v1/algebra/solve"]["post"]["operationId"] == "solve_algebra_v1"

    assert "/api/v1/health" in paths
    assert paths["/api/v1/health"]["get"]["operationId"] == "health_v1"


def test_transport_error_model_extra_forbid():
    """TransportErrorResponse rejects extra fields and invalid TransportErrorCode."""
    # Valid model
    valid_resp = TransportErrorResponse(
        transport_error_code=TransportErrorCode.MALFORMED_JSON,
        message_vi="Lỗi JSON",
        message_en="JSON error",
        details={},
    )
    assert valid_resp.transport_status == "ERROR"

    # Extra field rejected
    with pytest.raises(ValidationError):
        TransportErrorResponse(
            transport_error_code=TransportErrorCode.MALFORMED_JSON,
            message_vi="Lỗi JSON",
            message_en="JSON error",
            details={},
            unauthorized_field="illegal",
        )

    # Invalid enum rejected
    with pytest.raises(ValidationError):
        TransportErrorResponse(
            transport_error_code="INVALID_ERROR_CODE",
            message_vi="Lỗi",
            message_en="Error",
            details={},
        )


# ============================================================================
# 9. MATHEMATICAL AUTHORITY PURITY AUDIT
# ============================================================================

def test_transport_purity_authority_boundary():
    """Verify transport package does NOT import CASRouter, sympy, normalizer, traces, or verifier directly."""
    import sys
    import mke_product.transport.routers.algebra as algebra_router_mod
    import mke_product.transport.app as app_mod
    import mke_product.transport.middleware as middleware_mod
    import mke_product.transport.handlers as handlers_mod

    transport_modules = [algebra_router_mod, app_mod, middleware_mod, handlers_mod]

    forbidden_symbols = [
        "CASRouter",
        "execute_cas_operation",
        "sympy",
        "normalize_raw_equation",
        "generate_solution_trace",
        "HostIndependentVerifier",
        "DegenerateHostVerifier",
    ]

    for mod in transport_modules:
        mod_dict = mod.__dict__
        for sym in forbidden_symbols:
            assert sym not in mod_dict, f"Purity violation: {sym} found in transport module {mod.__name__}"
