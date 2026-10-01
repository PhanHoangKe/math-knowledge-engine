"""MKE MVP V1 — S2-02 Exhaustive Transport Acceptance & Direct-vs-HTTP Parity Test Suite.

Authoritative Acceptance Test Suite for the S2 FastAPI Transport Adapter and HTTP Boundary.
Proves that the HTTP transport preserves the accepted S1 application contract exactly,
verifies direct-vs-HTTP semantic parity, enforces transport status adapter policies,
audits OpenAPI contracts, and validates raw-ASGI streaming invariants.
"""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List
import unittest
from unittest.mock import patch
import pytest
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient
from starlette.types import Message, Scope, Receive, Send
from pydantic import TypeAdapter, ValidationError

from mke_product.transport.app import create_app
from mke_product.transport.middleware import (
    StreamPayloadLimitMiddleware,
    MediaTypeEnforcementMiddleware,
    MAX_BODY_BYTES,
    ALGEBRA_SOLVE_PATH,
    ALGEBRA_SOLVE_METHOD,
    is_algebra_solve_request,
)
from mke_product.transport.models import (
    TransportErrorCode,
    TransportErrorResponse,
    HealthResponse,
)
from mke_product.application.dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    CanonicalDegenerateProblemView,
    CanonicalQuadraticProblemView,
    DegenerateSolutionView,
    ErrorResponse,
    MethodOptionView,
    NoExecutionReasonCode,
    RawEquationInput,
    SolvedResponse,
    SolveRequest,
    SolveResponseUnion,
    VerifiedSolutionView,
)
from mke_product.application.errors import ApplicationErrorCode
from mke_product.application.orchestrator import solve_request
from mke_product.application.traces import TRACE_GENERATORS
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    RationalFraction,
    SolutionOutcome,
    SolutionRootType,
    VerificationOutcome,
)
from mke_product.domain.registry import MethodRegistry


# ============================================================================
# PARITY & NORMALIZATION HELPERS
# ============================================================================

def _normalize_snapshot(data: Any) -> Any:
    """Recursively strip ONLY intentionally nondeterministic timestamp fields (verified_at_utc)."""
    if isinstance(data, dict):
        return {
            k: _normalize_snapshot(v)
            for k, v in data.items()
            if k not in ("verified_at_utc",)
        }
    elif isinstance(data, list):
        return [_normalize_snapshot(v) for v in data]
    return data


def assert_direct_http_parity(
    client: TestClient,
    request: SolveRequest,
    expected_status: int = 200,
) -> tuple[Any, Any]:
    """Execute request directly and via HTTP, verify status, and assert normalized semantic parity."""
    # 1. Direct Python Execution
    direct_response = solve_request(request)
    direct_json = direct_response.model_dump(mode="json")

    # 2. HTTP Transport Execution
    http_raw = client.post(
        ALGEBRA_SOLVE_PATH,
        json=request.model_dump(mode="json"),
        headers={"Content-Type": "application/json"},
    )
    assert http_raw.status_code == expected_status, (
        f"Expected HTTP status {expected_status}, got {http_raw.status_code}: {http_raw.text}"
    )
    http_json = http_raw.json()

    # 3. Direct-vs-HTTP Semantic Parity (after verified_at_utc timestamp normalization)
    norm_direct = _normalize_snapshot(direct_json)
    norm_http = _normalize_snapshot(http_json)

    assert norm_direct == norm_http, (
        f"Parity mismatch:\nDirect: {json.dumps(norm_direct, indent=2)}\nHTTP: {json.dumps(norm_http, indent=2)}"
    )

    return direct_response, http_json


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ============================================================================
# 1. S1 CANONICAL 32-CASE MATRIX OVER HTTP (Q1-Q9, C1-C5, D1-D4, E1-E8, B1-B6)
# ============================================================================

class TestS2Canonical32CaseMatrixOverHTTP:
    """Mirrors the accepted S1 canonical 32-row matrix through the HTTP transport."""

    # --- QUADRATIC ACCEPTANCE (Q1 - Q9) ---

    def test_q1_distinct_rational_roots(self, client: TestClient):
        """Q1: x^2 - 5*x + 6 = 0 -> HTTP 200 SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["problem"]["classification"] == "QUADRATIC"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": 1, "denominator": 1}
        assert len(http_json["solution"]["roots"]) == 2
        assert http_json["solution"]["certificate"]["outcome"] == "VERIFIED_COMPLETE"
        assert len(http_json["available_methods"]) == 9

    def test_q2_exact_real_surd_roots(self, client: TestClient):
        """Q2: x^2 - 2 = 0 -> HTTP 200 SOLVED, roots {-sqrt(2), sqrt(2)}, discriminant 8."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 2 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": 8, "denominator": 1}
        assert len(http_json["solution"]["roots"]) == 2
        assert http_json["solution"]["roots"][0]["root_type"] == "REAL_SURD"
        assert http_json["solution"]["roots"][0]["radicand"] == 2

    def test_q3_repeated_real_root(self, client: TestClient):
        """Q3: x^2 - 2*x + 1 = 0 -> HTTP 200 SOLVED, root {1}, discriminant 0."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 2*x + 1 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["outcome"] == "ONE_REPEATED_REAL_ROOT"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": 0, "denominator": 1}
        assert len(http_json["solution"]["roots"]) == 1

    def test_q4_no_real_roots(self, client: TestClient):
        """Q4: x^2 + 1 = 0 -> HTTP 200 SOLVED, roots empty, discriminant -4."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 1 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["outcome"] == "NO_REAL_ROOTS"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": -4, "denominator": 1}
        assert http_json["solution"]["roots"] == []

    def test_q5_non_monic_distinct_rational_roots(self, client: TestClient):
        """Q5: 2*x^2 - 5*x + 2 = 0 -> HTTP 200 SOLVED, roots {1/2, 2}, discriminant 9."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x^2 - 5*x + 2 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["outcome"] == "TWO_DISTINCT_REAL_ROOTS"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": 9, "denominator": 1}
        assert len(http_json["solution"]["roots"]) == 2

    def test_q6_rearranged_quadratic(self, client: TestClient):
        """Q6: x^2 + 6 = 5*x -> HTTP 200 SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 6 = 5*x"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["problem"]["a"] == {"numerator": 1, "denominator": 1}
        assert http_json["problem"]["b"] == {"numerator": -5, "denominator": 1}
        assert http_json["problem"]["c"] == {"numerator": 6, "denominator": 1}

    def test_q7_factored_product_quadratic(self, client: TestClient):
        """Q7: (x - 2)*(x - 3) = 0 -> HTTP 200 SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x - 2)*(x - 3) = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["roots"][0]["rational_value"] == {"numerator": 2, "denominator": 1}
        assert http_json["solution"]["roots"][1]["rational_value"] == {"numerator": 3, "denominator": 1}

    def test_q8_squared_linear_quadratic(self, client: TestClient):
        """Q8: (x + 1)^2 = 0 -> HTTP 200 SOLVED, root {-1}, discriminant 0."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x + 1)^2 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["roots"][0]["rational_value"] == {"numerator": -1, "denominator": 1}

    def test_q9_fractional_coefficients_quadratic(self, client: TestClient):
        """Q9: (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> HTTP 200 SOLVED, roots {1, 3/2}, discriminant 1/16."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(1/2)*x^2 - (5/4)*x + 3/4 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["problem"]["discriminant"]["value"] == {"numerator": 1, "denominator": 16}

    # --- METHOD / COEFFICIENT ACCEPTANCE (C1 - C5) ---

    def test_c1_canonical_coefficients_default_selection(self, client: TestClient):
        """C1: COEFFICIENTS 1, -5, 6, default selection -> HTTP 200 SOLVED, standard formula."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id=None,
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["selected_method_id"] == "QUAD_FORMULA_STANDARD"

    def test_c2_canonical_coefficients_explicit_reduced_formula(self, client: TestClient):
        """C2: COEFFICIENTS 1, -5, 6, explicit QUAD_FORMULA_REDUCED -> HTTP 200 SOLVED with reduced trace."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_FORMULA_REDUCED",
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["selected_method_id"] == "QUAD_FORMULA_REDUCED"
        assert http_json["solution"]["method_id"] == "QUAD_FORMULA_REDUCED"

    def test_c3_canonical_coefficients_unknown_method_id(self, client: TestClient):
        """C3: COEFFICIENTS 1, -5, 6, explicit QUAD_UNKNOWN_ID -> HTTP 200 ErrorResponse(METHOD_NOT_FOUND)."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_UNKNOWN_ID",
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "METHOD_NOT_FOUND"

    def test_c4_canonical_coefficients_non_applicable_method(self, client: TestClient):
        """C4: COEFFICIENTS 2, 3, 4, explicit QUAD_VIETE_SPECIAL_SUM -> HTTP 200 ANALYZED_NO_EXECUTION / METHOD_NOT_APPLICABLE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(2),
                b=RationalFraction.from_int(3),
                c=RationalFraction.from_int(4),
            ),
            selected_method_id="QUAD_VIETE_SPECIAL_SUM",
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["reason_code"] == "METHOD_NOT_APPLICABLE"
        assert http_json["selected_method_id"] == "QUAD_VIETE_SPECIAL_SUM"

    def test_c5_canonical_coefficients_unavailable_method(self, client: TestClient):
        """C5: COEFFICIENTS 1, -5, 6, explicit QUAD_COMPLETE_SQUARE -> HTTP 200 ANALYZED_NO_EXECUTION / METHOD_NOT_EXECUTABLE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_COMPLETE_SQUARE",
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["reason_code"] == "METHOD_NOT_EXECUTABLE"
        assert http_json["selected_method_id"] == "QUAD_COMPLETE_SQUARE"

    # --- DEGENERATE ACCEPTANCE (D1 - D4) ---

    def test_d1_degenerate_linear_raw_text(self, client: TestClient):
        """D1: 2*x - 4 = 0 -> HTTP 200 ANALYZED_NO_EXECUTION, LINEAR, root=2, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x - 4 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["reason_code"] == "DEGENERATE_EXACT_SOLUTION"
        assert http_json["problem"]["classification"] == "LINEAR"
        assert http_json["available_methods"] == []
        assert http_json["selected_method_id"] is None
        assert http_json["degenerate_solution"]["linear_root"] == {"numerator": 2, "denominator": 1}
        assert http_json["degenerate_solution"]["certificate"]["outcome"] == "VERIFIED_COMPLETE"

    def test_d2_degenerate_identity_raw_text(self, client: TestClient):
        """D2: 0 = 0 -> HTTP 200 ANALYZED_NO_EXECUTION, IDENTITY, S=R, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="0 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["problem"]["classification"] == "IDENTITY"
        assert http_json["degenerate_solution"]["outcome"] == "INFINITE_REAL_SOLUTIONS"
        assert http_json["degenerate_solution"]["final_answer_latex"] == "S = \\mathbb{R}"

    def test_d3_degenerate_contradiction_raw_text(self, client: TestClient):
        """D3: 1 = 0 -> HTTP 200 ANALYZED_NO_EXECUTION, CONTRADICTION, S=empty, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["problem"]["classification"] == "CONTRADICTION"
        assert http_json["degenerate_solution"]["outcome"] == "NO_REAL_SOLUTIONS_CONTRADICTION"
        assert http_json["degenerate_solution"]["final_answer_latex"] == "S = \\emptyset"

    def test_d4_degenerate_linear_canonical_coefficients(self, client: TestClient):
        """D4: COEFFICIENTS a=0, b=2, c=-4 -> HTTP 200 ANALYZED_NO_EXECUTION, root=2, VERIFIED_COMPLETE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["problem"]["classification"] == "LINEAR"
        assert http_json["degenerate_solution"]["linear_root"] == {"numerator": 2, "denominator": 1}

    # --- ERROR / SCOPE ACCEPTANCE (E1 - E8) ---

    def test_e1_syntax_error(self, client: TestClient):
        """E1: x^2 + = 0 -> HTTP 200 ErrorResponse(SYNTAX_ERROR)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "SYNTAX_ERROR"
        assert http_json["span"] is not None

    def test_e2_degree_out_of_scope_cubic(self, client: TestClient):
        """E2: x^3 - 2*x + 1 = 0 -> HTTP 200 ErrorResponse(DEGREE_OUT_OF_SCOPE)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^3 - 2*x + 1 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "DEGREE_OUT_OF_SCOPE"

    def test_e3_degree_out_of_scope_intermediate_product(self, client: TestClient):
        """E3: (x^2 + 1)*(x + 1) = 0 -> HTTP 200 ErrorResponse(DEGREE_OUT_OF_SCOPE)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x^2 + 1)*(x + 1) = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "DEGREE_OUT_OF_SCOPE"

    def test_e4_unsupported_variable(self, client: TestClient):
        """E4: y^2 - 4 = 0 -> HTTP 200 ErrorResponse(UNSUPPORTED_VARIABLE)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="y^2 - 4 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "UNSUPPORTED_VARIABLE"

    def test_e5_non_polynomial_input(self, client: TestClient):
        """E5: 1/x = 0 -> HTTP 200 ErrorResponse(NON_POLYNOMIAL_INPUT)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1/x = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "NON_POLYNOMIAL_INPUT"

    def test_e6_division_by_zero(self, client: TestClient):
        """E6: x^2 / 0 = 0 -> HTTP 200 ErrorResponse(DIVISION_BY_ZERO)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 / 0 = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "DIVISION_BY_ZERO"

    def test_e7_unsupported_syntax(self, client: TestClient):
        """E7: sin(x) = 0 -> HTTP 200 ErrorResponse(UNSUPPORTED_SYNTAX)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="sin(x) = 0"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "UNSUPPORTED_SYNTAX"

    def test_e8_implicit_multiplication_unsupported(self, client: TestClient):
        """E8: 2x = 4 -> HTTP 200 ErrorResponse(IMPLICIT_MULTIPLICATION_UNSUPPORTED)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2x = 4"))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "IMPLICIT_MULTIPLICATION_UNSUPPORTED"

    # --- RESOURCE BOUNDS ACCEPTANCE (B1 - B6) ---

    def test_b1_max_length_256_passes(self, client: TestClient):
        """B1: Exactly 256 characters -> Reaches application, HTTP 200 SOLVED, parity holds."""
        fixed = "x^2  = 0"
        needed = 256 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        assert len(padded) == 256

        req = SolveRequest(input_payload=RawEquationInput(raw_query=padded))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"

    def test_b2_max_length_257_fails_at_dto_boundary(self, client: TestClient):
        """B2: 257 characters -> HTTP 422 TransportErrorResponse(REQUEST_VALIDATION_FAILED)."""
        fixed = "x^2  = 0"
        needed = 257 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        assert len(padded) == 257

        payload = {
            "input_payload": {
                "input_mode": "RAW_TEXT",
                "raw_query": padded,
                "target_variable": "x",
            },
            "selected_method_id": None,
            "schema_version": "1.0.0",
        }
        response = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert response.status_code == 422
        data = response.json()
        assert data["transport_status"] == "ERROR"
        assert data["transport_error_code"] == "REQUEST_VALIDATION_FAILED"

    def test_b3_max_depth_16_passes(self, client: TestClient):
        """B3: Nesting depth = 16 -> HTTP 200 SOLVED, parity holds."""
        nested = "(" * 16 + "x^2 - 1" + ")" * 16 + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"

    def test_b4_max_depth_17_fails(self, client: TestClient):
        """B4: Nesting depth = 17 -> HTTP 200 ErrorResponse(INPUT_LIMIT_EXCEEDED)."""
        nested = "(" * 17 + "x^2 - 1" + ")" * 17 + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "INPUT_LIMIT_EXCEEDED"

    def test_b5_max_tokens_64_passes(self, client: TestClient):
        """B5: Exactly 64 non-EOF tokens -> HTTP 200 ANALYZED_NO_EXECUTION, parity holds."""
        terms = ["+x"] + ["x"] * 30
        expr = " + ".join(terms) + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"

    def test_b6_max_tokens_65_fails(self, client: TestClient):
        """B6: 65 non-EOF tokens -> HTTP 200 ErrorResponse(INPUT_LIMIT_EXCEEDED)."""
        expr = " + ".join(["x"] * 32) + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == "INPUT_LIMIT_EXCEEDED"


# ============================================================================
# 2. CATEGORY-A COMPLETE STATUS MATRIX (HTTP 200)
# ============================================================================

class TestCategoryAStatusMatrix:
    """Independently proves EVERY frozen Category-A error code maps to HTTP 200 with ErrorResponse."""

    @pytest.mark.parametrize(
        ("code", "query"),
        [
            (ApplicationErrorCode.SYNTAX_ERROR, "x^2 + = 0"),
            (ApplicationErrorCode.UNSUPPORTED_VARIABLE, "y^2 - 4 = 0"),
            (ApplicationErrorCode.UNSUPPORTED_SYNTAX, "sin(x) = 0"),
            (ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED, "2x = 4"),
            (ApplicationErrorCode.DEGREE_OUT_OF_SCOPE, "x^3 - 2*x + 1 = 0"),
            (ApplicationErrorCode.NON_POLYNOMIAL_INPUT, "1/x = 0"),
            (ApplicationErrorCode.DIVISION_BY_ZERO, "x^2 / 0 = 0"),
            (ApplicationErrorCode.INPUT_LIMIT_EXCEEDED, "(" * 17 + "x^2 - 1" + ")" * 17 + " = 0"),
        ],
    )
    def test_category_a_real_path_codes_return_http_200(self, client: TestClient, code: ApplicationErrorCode, query: str):
        """Real input paths for Category-A errors return HTTP 200 with matching error_code."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query=query))
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == code.value

    def test_category_a_method_not_found_real_path_returns_http_200(self, client: TestClient):
        """Real path for METHOD_NOT_FOUND returns HTTP 200 ErrorResponse."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="NON_EXISTENT_METHOD",
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ERROR"
        assert http_json["error_code"] == ApplicationErrorCode.METHOD_NOT_FOUND.value

    @pytest.mark.parametrize(
        "cat_a_code",
        [
            ApplicationErrorCode.SYNTAX_ERROR,
            ApplicationErrorCode.UNSUPPORTED_VARIABLE,
            ApplicationErrorCode.UNSUPPORTED_SYNTAX,
            ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED,
            ApplicationErrorCode.DEGREE_OUT_OF_SCOPE,
            ApplicationErrorCode.NON_POLYNOMIAL_INPUT,
            ApplicationErrorCode.DIVISION_BY_ZERO,
            ApplicationErrorCode.INPUT_LIMIT_EXCEEDED,
            ApplicationErrorCode.METHOD_NOT_FOUND,
        ],
    )
    def test_category_a_isolated_adapter_preserves_body_and_200(self, monkeypatch, client: TestClient, cat_a_code: ApplicationErrorCode):
        """Adapter-isolation test: Monkeypatched Category-A responses return HTTP 200 and unmutated ErrorResponse."""
        simulated_error = ErrorResponse(
            error_code=cat_a_code,
            message_vi="Thông điệp lỗi Category-A giả lập.",
            message_en="Simulated Category-A error message.",
            span=(5, 10),
            details={"sentinel": "CATEGORY_A_UNMUTATED_SENTINEL"},
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
        response = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["response_status"] == "ERROR"
        assert data["error_code"] == cat_a_code.value
        assert data["span"] == {"start": 5, "end": 10}
        assert data["details"] == {"sentinel": "CATEGORY_A_UNMUTATED_SENTINEL"}


# ============================================================================
# 3. CATEGORY-B COMPLETE STATUS MATRIX (HTTP 500)
# ============================================================================

class TestCategoryBStatusMatrix:
    """Proves EVERY frozen Category-B error code maps to HTTP 500 with unmutated ErrorResponse body."""

    @pytest.mark.parametrize(
        "cat_b_code",
        [
            ApplicationErrorCode.NORMALIZATION_ERROR,
            ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
            ApplicationErrorCode.METHOD_EXECUTION_FAILED,
            ApplicationErrorCode.VERIFICATION_FAILED,
            ApplicationErrorCode.INTERNAL_ERROR,
        ],
    )
    def test_category_b_codes_map_to_http_500_with_body_preservation(self, monkeypatch, client: TestClient, cat_b_code: ApplicationErrorCode):
        """Category-B codes map to HTTP 500 while preserving full ErrorResponse payload and sentinel details."""
        simulated_error = ErrorResponse(
            error_code=cat_b_code,
            message_vi="Lỗi hệ thống nội bộ Category-B giả lập.",
            message_en="Simulated Category-B internal error.",
            span=None,
            details={"category_b_sentinel": "PRESERVE_ME_IN_500"},
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
        response = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["response_status"] == "ERROR"
        assert data["error_code"] == cat_b_code.value
        assert data["message_vi"] == "Lỗi hệ thống nội bộ Category-B giả lập."
        assert data["message_en"] == "Simulated Category-B internal error."
        assert data["details"] == {"category_b_sentinel": "PRESERVE_ME_IN_500"}


# ============================================================================
# 4. REACTIVE METHOD-SWITCH & COEFFICIENT-EDIT OVER HTTP
# ============================================================================

class TestReactivityOverHTTP:
    """Verifies live method switching and coefficient mutation over the HTTP transport."""

    def test_reactive_method_switch_over_http(self, client: TestClient):
        """Switching from STANDARD to REDUCED formula maintains problem_id/hash/roots but changes trace over HTTP."""
        req_standard = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_FORMULA_STANDARD",
        )
        req_reduced = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_FORMULA_REDUCED",
        )

        _, http_std = assert_direct_http_parity(client, req_standard, 200)
        _, http_red = assert_direct_http_parity(client, req_reduced, 200)

        # Invariant Mathematical Identity
        assert http_std["problem"]["problem_id"] == http_red["problem"]["problem_id"]
        assert http_std["problem"]["semantic_revision_hash"] == http_red["problem"]["semantic_revision_hash"]
        assert http_std["problem"]["a"] == http_red["problem"]["a"]
        assert http_std["problem"]["b"] == http_red["problem"]["b"]
        assert http_std["problem"]["c"] == http_red["problem"]["c"]
        assert http_std["problem"]["discriminant"] == http_red["problem"]["discriminant"]
        assert http_std["solution"]["roots"] == http_red["solution"]["roots"]

        # Distinct Method & Trace Strategy
        assert http_std["selected_method_id"] == "QUAD_FORMULA_STANDARD"
        assert http_red["selected_method_id"] == "QUAD_FORMULA_REDUCED"
        assert http_std["solution"]["method_id"] == "QUAD_FORMULA_STANDARD"
        assert http_red["solution"]["method_id"] == "QUAD_FORMULA_REDUCED"
        assert http_std["solution"]["trace"]["method_id"] == "QUAD_FORMULA_STANDARD"
        assert http_red["solution"]["trace"]["method_id"] == "QUAD_FORMULA_REDUCED"
        assert http_std["solution"]["trace"]["steps"] != http_red["solution"]["trace"]["steps"]

    def test_coefficient_edit_over_http_proves_zero_parser_invocation(self, client: TestClient):
        """Mutating c from 6 to 7 produces distinct problem identity without invoking raw equation normalizer."""
        req_c6 = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )
        req_c7 = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(7),
            )
        )

        with patch("mke_product.application.orchestrator.normalize_raw_equation") as mock_norm:
            _, http_c6 = assert_direct_http_parity(client, req_c6, 200)
            _, http_c7 = assert_direct_http_parity(client, req_c7, 200)
            mock_norm.assert_not_called()

        assert http_c6["problem"]["problem_id"] != http_c7["problem"]["problem_id"]
        assert http_c6["problem"]["semantic_revision_hash"] != http_c7["problem"]["semantic_revision_hash"]
        assert http_c6["problem"]["discriminant"]["value"] == {"numerator": 1, "denominator": 1}
        assert http_c7["problem"]["discriminant"]["value"] == {"numerator": -3, "denominator": 1}
        assert http_c6["solution"]["outcome"] == "TWO_DISTINCT_REAL_ROOTS"
        assert http_c7["solution"]["outcome"] == "NO_REAL_ROOTS"

    def test_quadratic_to_degenerate_transition_over_http(self, client: TestClient):
        """Mutating a from 1 to 0 transitions from QUADRATIC to DEGENERATE without raw parser invocation."""
        req_quad = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )
        req_deg = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )

        with patch("mke_product.application.orchestrator.normalize_raw_equation") as mock_norm:
            _, http_quad = assert_direct_http_parity(client, req_quad, 200)
            _, http_deg = assert_direct_http_parity(client, req_deg, 200)
            mock_norm.assert_not_called()

        assert http_quad["response_status"] == "SOLVED"
        assert http_quad["problem"]["problem_type"] == "QUADRATIC"
        assert http_deg["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_deg["problem"]["problem_type"] == "DEGENERATE"
        assert http_deg["reason_code"] == "DEGENERATE_EXACT_SOLUTION"
        assert http_deg["degenerate_solution"]["linear_root"] == {"numerator": 2, "denominator": 1}


# ============================================================================
# 5. FOUR EXECUTABLE METHODS & FIVE UNAVAILABLE METHODS OVER HTTP
# ============================================================================

class TestMethodAvailabilityOverHTTP:
    """Verifies all four executable methods solve correctly and all five unavailable methods reject without fallback."""

    @pytest.mark.parametrize(
        ("method_id", "query", "expected_roots"),
        [
            ("QUAD_FORMULA_STANDARD", "x^2 - 5*x + 6 = 0", [{"numerator": 2, "denominator": 1}, {"numerator": 3, "denominator": 1}]),
            ("QUAD_FORMULA_REDUCED", "x^2 - 4*x + 3 = 0", [{"numerator": 1, "denominator": 1}, {"numerator": 3, "denominator": 1}]),
            ("QUAD_VIETE_SPECIAL_SUM", "x^2 - 3*x + 2 = 0", [{"numerator": 1, "denominator": 1}, {"numerator": 2, "denominator": 1}]),
            ("QUAD_VIETE_SPECIAL_DIF", "x^2 + 3*x + 2 = 0", [{"numerator": -2, "denominator": 1}, {"numerator": -1, "denominator": 1}]),
        ],
    )
    def test_four_executable_methods_solve_over_http(self, client: TestClient, method_id: str, query: str, expected_roots: List[Dict[str, int]]):
        """All 4 executable methods execute over HTTP with verified complete trace and direct parity."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query=query),
            selected_method_id=method_id,
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "SOLVED"
        assert http_json["solution"]["method_id"] == method_id
        assert http_json["solution"]["certificate"]["outcome"] == "VERIFIED_COMPLETE"
        assert len(http_json["solution"]["trace"]["steps"]) > 0
        roots = [r["rational_value"] for r in http_json["solution"]["roots"]]
        assert roots == expected_roots

    @pytest.mark.parametrize(
        "unavailable_id",
        [
            "QUAD_FACTORIZATION_Q",
            "QUAD_FACTORIZATION_R",
            "QUAD_COMPLETE_SQUARE",
            "QUAD_VIETE_SUM_PRODUCT",
            "QUAD_GRAPHICAL_ANALYSIS",
        ],
    )
    def test_five_unavailable_methods_reject_over_http(self, client: TestClient, unavailable_id: str):
        """All 5 unavailable methods return ANALYZED_NO_EXECUTION / METHOD_NOT_EXECUTABLE without fallback."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id=unavailable_id,
        )
        direct_resp, http_json = assert_direct_http_parity(client, req, 200)
        assert http_json["response_status"] == "ANALYZED_NO_EXECUTION"
        assert http_json["reason_code"] == "METHOD_NOT_EXECUTABLE"
        assert http_json["selected_method_id"] == unavailable_id


# ============================================================================
# 6. TRANSPORT FAILURE & PRECEDENCE MATRIX
# ============================================================================

class TestTransportFailureAndPrecedenceMatrix:
    """Freezes transport-only error responses, status codes, and middleware precedence."""

    def test_malformed_json_returns_400(self, client: TestClient):
        """Malformed JSON returns HTTP 400 MALFORMED_JSON."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b'{"input_payload": {"raw_query": ',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json()["transport_error_code"] == "MALFORMED_JSON"

    def test_dto_schema_validation_failure_returns_422(self, client: TestClient):
        """Invalid DTO enum returns HTTP 422 REQUEST_VALIDATION_FAILED."""
        payload = {"input_payload": {"input_mode": "INVALID_MODE"}, "schema_version": "1.0.0"}
        response = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert response.status_code == 422
        assert response.json()["transport_error_code"] == "REQUEST_VALIDATION_FAILED"

    def test_text_plain_on_solve_route_returns_415(self, client: TestClient):
        """text/plain on solve route returns HTTP 415 UNSUPPORTED_MEDIA_TYPE."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"x^2 - 5*x + 6 = 0",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code == 415
        assert response.json()["transport_error_code"] == "UNSUPPORTED_MEDIA_TYPE"

    def test_missing_content_type_on_solve_route_returns_415(self, client: TestClient):
        """Missing Content-Type on solve route returns HTTP 415 UNSUPPORTED_MEDIA_TYPE."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"{}",
            headers={},  # Missing Content-Type
        )
        assert response.status_code == 415
        assert response.json()["transport_error_code"] == "UNSUPPORTED_MEDIA_TYPE"

    def test_invalid_content_length_on_solve_route_returns_400(self, client: TestClient):
        """Invalid Content-Length: abc on solve route returns HTTP 400 REQUEST_VALIDATION_FAILED."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "abc"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["transport_error_code"] == "REQUEST_VALIDATION_FAILED"
        assert data["details"] == {"header": "Content-Length", "reason": "INVALID_CONTENT_LENGTH"}

    def test_declared_content_length_over_64k_returns_413(self, client: TestClient):
        """Declared Content-Length: 65537 returns HTTP 413 PAYLOAD_TOO_LARGE."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "65537"},
        )
        assert response.status_code == 413
        assert response.json()["transport_error_code"] == "PAYLOAD_TOO_LARGE"

    def test_unknown_api_path_returns_404(self, client: TestClient):
        """Unknown /api/* path returns HTTP 404 API_NOT_FOUND."""
        response = client.get("/api/v1/nonexistent_path")
        assert response.status_code == 404
        assert response.json()["transport_error_code"] == "API_NOT_FOUND"

    # --- PRECEDENCE TESTS ---

    def test_precedence_solve_route_text_plain_small_body(self, client: TestClient):
        """Precedence A: Solve route text/plain with small body -> 415."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"x=1",
            headers={"Content-Type": "text/plain", "Content-Length": "3"},
        )
        assert response.status_code == 415

    def test_precedence_solve_route_text_plain_oversized_declared_header(self, client: TestClient):
        """Precedence B: Solve route text/plain with declared Content-Length > 65536 -> 413 (size middleware is outermost)."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"x=1",
            headers={"Content-Type": "text/plain", "Content-Length": "70000"},
        )
        assert response.status_code == 413

    def test_precedence_solve_route_application_json_oversized(self, client: TestClient):
        """Precedence C: Solve route application/json oversized -> 413."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "70000"},
        )
        assert response.status_code == 413

    def test_precedence_unknown_api_route_text_plain_oversized(self, client: TestClient):
        """Precedence D: Unknown API route text/plain oversized reaches routing -> 404."""
        response = client.post(
            "/api/v1/nonexistent",
            content=b"x=1",
            headers={"Content-Type": "text/plain", "Content-Length": "70000"},
        )
        assert response.status_code == 404
        assert response.json()["transport_error_code"] == "API_NOT_FOUND"

    def test_precedence_unknown_api_route_malformed_content_length(self, client: TestClient):
        """Precedence E: Unknown API route malformed Content-Length reaches routing -> 404."""
        response = client.post(
            "/api/v1/nonexistent",
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "abc"},
        )
        assert response.status_code == 404
        assert response.json()["transport_error_code"] == "API_NOT_FOUND"


# ============================================================================
# 7. RAW-ASGI BODY LIMIT & BOUNDED REPLAY ACCEPTANCE
# ============================================================================

class TestRawASGIBodyLimitAcceptance:
    """Direct raw-ASGI tests exercising bounded pre-read, replay, and single-response guarantees."""

    @pytest.mark.asyncio
    async def test_raw_asgi_missing_content_length_over_64k_rejected_413(self):
        """Raw ASGI: Missing Content-Length with chunks > 64 KiB emits exactly one 413 response; downstream never invoked."""
        downstream_called = False

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called
            downstream_called = True

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        chunks = [b"a" * 10000 for _ in range(7)]  # 70,000 bytes
        idx = 0

        async def mock_receive() -> Message:
            nonlocal idx
            if idx < len(chunks):
                body = chunks[idx]
                idx += 1
                return {"type": "http.request", "body": body, "more_body": idx < len(chunks)}
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json")],
        }

        await middleware(scope, mock_receive, mock_send)

        assert downstream_called is False
        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        body_msgs = [m for m in sent if m["type"] == "http.response.body"]
        assert len(start_msgs) == 1
        assert start_msgs[0]["status"] == 413
        assert len(body_msgs) == 1
        assert body_msgs[0].get("more_body", False) is False

    @pytest.mark.asyncio
    async def test_raw_asgi_deceptive_low_content_length_rejected_413(self):
        """Raw ASGI: Deceptive Content-Length: 10 with actual body > 64 KiB fails 413; downstream never invoked."""
        downstream_called = False

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called
            downstream_called = True

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        chunks = [b"b" * 10000 for _ in range(7)]  # 70,000 bytes
        idx = 0

        async def mock_receive() -> Message:
            nonlocal idx
            if idx < len(chunks):
                body = chunks[idx]
                idx += 1
                return {"type": "http.request", "body": body, "more_body": idx < len(chunks)}
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json"), (b"content-length", b"10")],
        }

        await middleware(scope, mock_receive, mock_send)
        assert downstream_called is False
        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        assert len(start_msgs) == 1
        assert start_msgs[0]["status"] == 413

    @pytest.mark.asyncio
    async def test_raw_asgi_exact_65536_bytes_replayed_completely(self):
        """Raw ASGI: Exactly 65,536 bytes passes size guard and is replayed completely to downstream."""
        downstream_called = False
        replayed_body = b""

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called, replayed_body
            downstream_called = True
            msg = await receive()
            replayed_body += msg.get("body", b"")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK", "more_body": False})

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        expected_body = b"x" * MAX_BODY_BYTES
        chunks = [expected_body[i * 16384 : (i + 1) * 16384] for i in range(4)]
        idx = 0

        async def mock_receive() -> Message:
            nonlocal idx
            if idx < len(chunks):
                body = chunks[idx]
                idx += 1
                return {"type": "http.request", "body": body, "more_body": idx < len(chunks)}
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json")],
        }

        await middleware(scope, mock_receive, mock_send)
        assert downstream_called is True
        assert len(replayed_body) == MAX_BODY_BYTES
        assert replayed_body == expected_body

    @pytest.mark.asyncio
    async def test_raw_asgi_65537_bytes_rejected_413(self):
        """Raw ASGI: Exactly 65,537 bytes (1 byte over limit) is rejected with 413."""
        downstream_called = False

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called
            downstream_called = True

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        oversized_body = b"y" * (MAX_BODY_BYTES + 1)

        async def mock_receive() -> Message:
            return {"type": "http.request", "body": oversized_body, "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json")],
        }

        await middleware(scope, mock_receive, mock_send)
        assert downstream_called is False
        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        assert len(start_msgs) == 1
        assert start_msgs[0]["status"] == 413

    @pytest.mark.asyncio
    async def test_raw_asgi_zero_content_length_with_valid_body_replayed_completely(self):
        """Raw ASGI: Content-Length: 0 with small actual body passes guard and replays completely."""
        downstream_called = False
        replayed_body = b""

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called, replayed_body
            downstream_called = True
            msg = await receive()
            replayed_body += msg.get("body", b"")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK", "more_body": False})

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        small_payload = b'{"input_payload":{"input_mode":"RAW_TEXT","raw_query":"x^2-1=0"}}'

        async def mock_receive() -> Message:
            return {"type": "http.request", "body": small_payload, "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json"), (b"content-length", b"0")],
        }

        await middleware(scope, mock_receive, mock_send)
        assert downstream_called is True
        assert replayed_body == small_payload

    @pytest.mark.asyncio
    async def test_raw_asgi_zero_content_length_with_oversized_stream_rejected_413(self):
        """Raw ASGI: Content-Length: 0 with actual stream > 64 KiB is caught by pre-read and rejected with 413."""
        downstream_called = False

        async def sentinel_app(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal downstream_called
            downstream_called = True

        middleware = StreamPayloadLimitMiddleware(sentinel_app)
        chunks = [b"z" * 10000 for _ in range(7)]  # 70,000 bytes
        idx = 0

        async def mock_receive() -> Message:
            nonlocal idx
            if idx < len(chunks):
                body = chunks[idx]
                idx += 1
                return {"type": "http.request", "body": body, "more_body": idx < len(chunks)}
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: List[Message] = []
        async def mock_send(msg: Message) -> None:
            sent.append(msg)

        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": ALGEBRA_SOLVE_PATH,
            "headers": [(b"content-type", b"application/json"), (b"content-length", b"0")],
        }

        await middleware(scope, mock_receive, mock_send)
        assert downstream_called is False
        start_msgs = [m for m in sent if m["type"] == "http.response.start"]
        assert len(start_msgs) == 1
        assert start_msgs[0]["status"] == 413



# ============================================================================
# 8. SECURITY & ERROR SANITIZATION ACCEPTANCE
# ============================================================================

class TestSecurityAndErrorSanitization:
    """Verifies that no sensitive input sentinels, exception reprs, or tracebacks leak into client responses."""

    def test_request_validation_sanitization_no_sentinel_leak(self, client: TestClient):
        """Schema violations (422) expose only type/loc/msg; raw input and sentinels are strictly stripped."""
        malicious_payload = {
            "input_payload": {
                "input_mode": "UNKNOWN_INJECTION_MODE",
                "malicious_sentinel": "SECRET_REQUEST_SENTINEL_STRING",
            },
            "selected_method_id": "INJECTED_METHOD_SENTINEL",
            "schema_version": "1.0.0",
        }
        response = client.post(ALGEBRA_SOLVE_PATH, json=malicious_payload)
        assert response.status_code == 422
        data = response.json()
        assert data["transport_status"] == "ERROR"
        assert data["transport_error_code"] == "REQUEST_VALIDATION_FAILED"
        errors = data["details"]["validation_errors"]
        assert len(errors) > 0
        for err in errors:
            assert set(err.keys()) == {"type", "loc", "msg"}
            assert "SECRET_REQUEST_SENTINEL_STRING" not in str(err)
            assert "INJECTED_METHOD_SENTINEL" not in str(err)
            assert "input" not in err
            assert "ctx" not in err

    def test_http_exception_sanitization_no_sentinel_leak(self):
        """Generic HTTPException (e.g. 418) sanitizes response and never echoes exc.detail or internal class names."""
        app = create_app()
        test_router = APIRouter()

        @test_router.get("/api/v1/test-sentinel-leak")
        def leak_route():
            raise HTTPException(
                status_code=418,
                detail="SECRET_HTTP_SENTINEL_DETAIL_STRING",
            )

        app.include_router(test_router)
        test_client = TestClient(app, raise_server_exceptions=False)

        response = test_client.get("/api/v1/test-sentinel-leak")
        assert response.status_code == 418
        data = response.json()
        assert data["transport_status"] == "ERROR"
        assert data["transport_error_code"] == "INTERNAL_TRANSPORT_ERROR"
        assert data["details"] == {"status_code": 418}

        sentinel = "SECRET_HTTP_SENTINEL_DETAIL_STRING"
        assert sentinel not in data["message_vi"]
        assert sentinel not in data["message_en"]
        assert sentinel not in str(data["details"])
        assert sentinel not in response.text

    def test_unhandled_transport_crash_sanitization_no_sentinel_leak(self, monkeypatch):
        """Unhandled internal crash returns HTTP 500 INTERNAL_TRANSPORT_ERROR with zero stack trace or sentinel leaks."""
        app = create_app()
        test_client = TestClient(app, raise_server_exceptions=False)

        import mke_product.transport.routers.algebra as algebra_mod
        def crash(req):
            raise RuntimeError("SECRET_TRANSPORT_CRASH_SENTINEL_STRING")

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
        response = test_client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["transport_status"] == "ERROR"
        assert data["transport_error_code"] == "INTERNAL_TRANSPORT_ERROR"
        assert data["details"] == {}
        assert "SECRET_TRANSPORT_CRASH_SENTINEL_STRING" not in str(data)
        assert "Traceback" not in response.text


# ============================================================================
# 9. OPENAPI CONTRACT AUDIT
# ============================================================================

class TestOpenAPIContractAudit:
    """Audits the generated OpenAPI 3.1.0 schema for stable operation IDs, status codes, and schema models."""

    def test_openapi_operation_ids_and_documented_responses(self, client: TestClient):
        """OpenAPI schema contains stable operation IDs and documents all transport status codes."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()

        paths = spec["paths"]
        assert ALGEBRA_SOLVE_PATH in paths
        assert paths[ALGEBRA_SOLVE_PATH]["post"]["operationId"] == "solve_algebra_v1"

        solve_responses = paths[ALGEBRA_SOLVE_PATH]["post"]["responses"]
        for status_code in ("200", "400", "413", "415", "422", "500"):
            assert status_code in solve_responses, f"Missing {status_code} in solve route OpenAPI responses"

        assert "/api/v1/health" in paths
        assert paths["/api/v1/health"]["get"]["operationId"] == "health_v1"

    def test_openapi_transport_error_taxonomy_and_model_properties(self, client: TestClient):
        """OpenAPI schema reflects exactly 6 TransportErrorCode enum values and model constraints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        schemas = spec.get("components", {}).get("schemas", {})

        assert "TransportErrorCode" in schemas
        enum_values = schemas["TransportErrorCode"]["enum"]
        expected_enums = [
            "MALFORMED_JSON",
            "REQUEST_VALIDATION_FAILED",
            "PAYLOAD_TOO_LARGE",
            "UNSUPPORTED_MEDIA_TYPE",
            "API_NOT_FOUND",
            "INTERNAL_TRANSPORT_ERROR",
        ]
        assert set(enum_values) == set(expected_enums)
        assert len(enum_values) == 6

        assert "TransportErrorResponse" in schemas
        assert "HealthResponse" in schemas

    def test_openapi_solve_200_polymorphic_discriminator_contract(self, client: TestClient):
        """POST /api/v1/algebra/solve 200 schema defines oneOf with discriminator property response_status."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()

        solve_200_schema = spec["paths"][ALGEBRA_SOLVE_PATH]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert "oneOf" in solve_200_schema
        assert len(solve_200_schema["oneOf"]) == 3

        discriminator = solve_200_schema.get("discriminator")
        assert discriminator is not None
        assert discriminator["propertyName"] == "response_status"
        mapping = discriminator.get("mapping", {})
        assert mapping.get("SOLVED") == "#/components/schemas/SolvedResponse"
        assert mapping.get("ANALYZED_NO_EXECUTION") == "#/components/schemas/AnalyzedNoExecutionResponse"
        assert mapping.get("ERROR") == "#/components/schemas/ErrorResponse"

    def test_openapi_solve_request_input_payload_discriminator_contract(self, client: TestClient):
        """SolveRequest.input_payload defines oneOf with discriminator property input_mode."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        schemas = spec["components"]["schemas"]

        assert "SolveRequest" in schemas
        solve_req = schemas["SolveRequest"]
        assert solve_req.get("additionalProperties") is False

        input_payload_schema = solve_req["properties"]["input_payload"]
        assert "oneOf" in input_payload_schema
        assert len(input_payload_schema["oneOf"]) == 2

        discriminator = input_payload_schema.get("discriminator")
        assert discriminator is not None
        assert discriminator["propertyName"] == "input_mode"
        mapping = discriminator.get("mapping", {})
        assert mapping.get("RAW_TEXT") == "#/components/schemas/RawEquationInput"
        assert mapping.get("COEFFICIENTS") == "#/components/schemas/CanonicalCoefficientInput"

    def test_openapi_error_and_transport_schemas_contract(self, client: TestClient):
        """Error status codes 400, 413, 415, 422 reference TransportErrorResponse; 500 references ErrorResponse and TransportErrorResponse."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        schemas = spec["components"]["schemas"]

        assert schemas["TransportErrorResponse"].get("additionalProperties") is False
        assert schemas["RawEquationInput"].get("additionalProperties") is False
        assert schemas["CanonicalCoefficientInput"].get("additionalProperties") is False

        responses = spec["paths"][ALGEBRA_SOLVE_PATH]["post"]["responses"]
        for status in ("400", "413", "415", "422"):
            schema_ref = responses[status]["content"]["application/json"]["schema"]["$ref"]
            assert schema_ref == "#/components/schemas/TransportErrorResponse"

        resp_500_schema = responses["500"]["content"]["application/json"]["schema"]
        assert "anyOf" in resp_500_schema
        refs = [item["$ref"] for item in resp_500_schema["anyOf"]]
        assert "#/components/schemas/ErrorResponse" in refs
        assert "#/components/schemas/TransportErrorResponse" in refs


# ============================================================================
# 10. HEALTH OBSERVABILITY ACCEPTANCE
# ============================================================================

class TestHealthObservabilityAcceptance:
    """Verifies that the health endpoint reports accurate, derived method counts."""

    def test_health_endpoint_derived_counts(self, client: TestClient):
        """GET /api/v1/health returns HTTP 200 with dynamically derived counts."""
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

        # Validate with HealthResponse model
        health_model = HealthResponse.model_validate(data)
        assert health_model.status == "HEALTHY"

    def test_health_endpoint_count_is_dynamically_derived(self, monkeypatch, client: TestClient):
        """Proves registered_methods_count and executable_methods_count are derived rather than hard-coded."""
        import mke_product.transport.routers.algebra as algebra_router_mod

        class DummyRegistry:
            def list_all(self):
                return ["MOCK_1", "MOCK_2", "MOCK_3"]

        monkeypatch.setattr(algebra_router_mod, "MethodRegistry", DummyRegistry)
        monkeypatch.setattr(algebra_router_mod, "TRACE_GENERATORS", {"MOCK_1": None, "MOCK_2": None})

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["registered_methods_count"] == 3
        assert data["executable_methods_count"] == 2


# ============================================================================
# 11. HTTP DETERMINISM & SERIALIZATION ROUND-TRIP
# ============================================================================

class TestHTTPDeterminismAndRoundTrip:
    """Verifies response determinism over HTTP and polymorphic DTO round-trip validation."""

    @pytest.mark.parametrize(
        "query",
        [
            "x^2 - 5*x + 6 = 0",   # Rational distinct
            "x^2 - 2 = 0",         # Surd distinct
            "x^2 - 3*x + 2 = 0",   # Viète special sum
            "2*x - 4 = 0",         # Degenerate linear
        ],
    )
    def test_repeated_http_requests_are_deterministic(self, client: TestClient, query: str):
        """Repeated HTTP requests produce identical certificate_id, fingerprints, and semantic payloads."""
        payload = {
            "input_payload": {
                "input_mode": "RAW_TEXT",
                "raw_query": query,
                "target_variable": "x",
            },
            "selected_method_id": None,
            "schema_version": "1.0.0",
        }

        resp1 = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        resp2 = client.post(ALGEBRA_SOLVE_PATH, json=payload)
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        data1 = resp1.json()
        data2 = resp2.json()

        # Certificate ID and integrity fingerprint must be 100% identical between runs
        if data1.get("response_status") == "SOLVED":
            assert data1["solution"]["certificate"]["certificate_id"] == data2["solution"]["certificate"]["certificate_id"]
            assert data1["solution"]["certificate"]["integrity_fingerprint"] == data2["solution"]["certificate"]["integrity_fingerprint"]
        elif data1.get("response_status") == "ANALYZED_NO_EXECUTION" and data1.get("degenerate_solution"):
            assert data1["degenerate_solution"]["certificate"]["certificate_id"] == data2["degenerate_solution"]["certificate"]["certificate_id"]

        # Normalized semantic snapshots must match identically
        assert _normalize_snapshot(data1) == _normalize_snapshot(data2)

    def test_application_response_polymorphic_round_trip(self, client: TestClient):
        """HTTP responses for SOLVED, ANALYZED_NO_EXECUTION, and ERROR round-trip via TypeAdapter(SolveResponseUnion)."""
        adapter = TypeAdapter(SolveResponseUnion)

        test_payloads = [
            {"input_payload": {"input_mode": "RAW_TEXT", "raw_query": "x^2 - 5*x + 6 = 0"}},   # SOLVED
            {"input_payload": {"input_mode": "RAW_TEXT", "raw_query": "2*x - 4 = 0"}},         # ANALYZED_NO_EXECUTION
            {"input_payload": {"input_mode": "RAW_TEXT", "raw_query": "x^2 + = 0"}},           # ERROR
        ]

        for p in test_payloads:
            resp = client.post(ALGEBRA_SOLVE_PATH, json=p)
            assert resp.status_code == 200
            data = resp.json()

            # Validate raw JSON string from HTTP response through polymorphic union adapter
            parsed_model = adapter.validate_json(resp.text)
            assert parsed_model.response_status == data["response_status"]

    def test_transport_error_response_round_trip(self, client: TestClient):
        """Transport error responses round-trip cleanly through TransportErrorResponse."""
        resp = client.post(ALGEBRA_SOLVE_PATH, content=b"x=1", headers={"Content-Type": "text/plain"})
        assert resp.status_code == 415
        error_model = TransportErrorResponse.model_validate_json(resp.text)
        assert error_model.transport_error_code == TransportErrorCode.UNSUPPORTED_MEDIA_TYPE


# ============================================================================
# 12. CONTENT-TYPE & CONTENT-LENGTH EXHAUSTIVE MATRIX
# ============================================================================

class TestContentNegotiationAndHeaderMatrix:
    """Exhaustively validates Content-Type and Content-Length permutations on the solve route."""

    @pytest.mark.parametrize(
        ("ct_header", "expected_status"),
        [
            ("application/json", 200),
            ("application/json; charset=utf-8", 200),
            ("APPLICATION/JSON", 200),
            ("application/json-not-really", 415),
            ("application/problem+json", 415),
            ("text/plain", 415),
        ],
    )
    def test_content_type_matrix_on_solve_route(self, client: TestClient, ct_header: str, expected_status: int):
        """Content-Type headers are strictly validated on the solve route."""
        payload = {
            "input_payload": {"input_mode": "RAW_TEXT", "raw_query": "x^2 - 5*x + 6 = 0"},
            "schema_version": "1.0.0",
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=body_bytes,
            headers={"Content-Type": ct_header},
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("cl_header", "expected_status", "expected_code"),
        [
            ("-1", 400, "REQUEST_VALIDATION_FAILED"),
            ("abc", 400, "REQUEST_VALIDATION_FAILED"),
            ("12.5", 400, "REQUEST_VALIDATION_FAILED"),
            (" 10 20 ", 400, "REQUEST_VALIDATION_FAILED"),
            ("65537", 413, "PAYLOAD_TOO_LARGE"),
        ],
    )
    def test_content_length_matrix_on_solve_route(self, client: TestClient, cl_header: str, expected_status: int, expected_code: str):
        """Content-Length headers are validated on the solve route."""
        response = client.post(
            ALGEBRA_SOLVE_PATH,
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": cl_header},
        )
        assert response.status_code == expected_status
        data = response.json()
        assert data["transport_error_code"] == expected_code


# ============================================================================
# 13. STRENGTHENED PURITY & AUTHORITY AUDIT
# ============================================================================

class TestStrengthenedPurityAndAuthorityAudit:
    """Scans all transport source files to prove absence of mathematical execution authority imports."""

    def test_transport_source_files_have_no_execution_authority_references(self):
        """Assert zero imports/references to CASRouter, sympy, normalizer, traces, or verifiers in transport files."""
        transport_dir = Path(__file__).resolve().parent.parent / "src" / "mke_product" / "transport"
        assert transport_dir.is_dir(), f"Transport directory not found at {transport_dir}"

        forbidden_execution_symbols = [
            "CASRouter",
            "execute_cas_operation",
            "sympy",
            "normalize_raw_equation",
            "generate_solution_trace",
            "get_trace_generator",
            "HostIndependentVerifier",
            "DegenerateHostVerifier",
        ]

        transport_py_files = list(transport_dir.rglob("*.py"))
        assert len(transport_py_files) >= 4, f"Expected at least 4 transport files, found {len(transport_py_files)}"

        for py_file in transport_py_files:
            file_content = py_file.read_text(encoding="utf-8")
            for symbol in forbidden_execution_symbols:
                assert symbol not in file_content, (
                    f"Purity violation: Forbidden execution authority symbol '{symbol}' found in {py_file.name}"
                )

    def test_transport_source_files_ast_import_purity(self):
        """Parse all transport source files with Python AST and verify no forbidden modules or symbols are imported."""
        transport_dir = Path(__file__).resolve().parent.parent / "src" / "mke_product" / "transport"
        assert transport_dir.is_dir(), f"Transport directory not found at {transport_dir}"

        forbidden_import_modules = {
            "sympy",
            "mke_product.domain.verifier",
            "mke_product.domain.cas_router",
            "mke_product.application.normalizer",
        }
        forbidden_import_names = {
            "CASRouter",
            "execute_cas_operation",
            "normalize_raw_equation",
            "generate_solution_trace",
            "get_trace_generator",
            "HostIndependentVerifier",
            "DegenerateHostVerifier",
        }

        transport_py_files = list(transport_dir.rglob("*.py"))
        for py_file in transport_py_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden_mod in forbidden_import_modules:
                            assert not alias.name.startswith(forbidden_mod), (
                                f"AST Purity violation: Forbidden import '{alias.name}' found in {py_file.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    for forbidden_mod in forbidden_import_modules:
                        assert not mod_name.startswith(forbidden_mod), (
                            f"AST Purity violation: Forbidden import from '{mod_name}' found in {py_file.name}"
                        )
                    for alias in node.names:
                        assert alias.name not in forbidden_import_names, (
                            f"AST Purity violation: Forbidden imported symbol '{alias.name}' from '{mod_name}' found in {py_file.name}"
                        )

