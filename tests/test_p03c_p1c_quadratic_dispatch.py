"""Unit, integration, and protocol tests for P1C-04-B1 quadratic solver and dispatcher.

Milestone: PRODUCT-03C-P1C-04-B1
Author: Antigravity (Implementation Engineer)
Auditor: ChatGPT
"""

import json
from typing import Any, Dict, List, Optional, Tuple
import pytest

from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation
from mke_product.protocol.dispatcher import dispatch_request
from mke_product.protocol.errors import (
    ProtocolInputLimitError,
    ProtocolMissingFieldError,
    ProtocolUnexpectedFieldError,
    ProtocolUnknownOperationError,
    ProtocolUnsupportedVersionError,
)
from mke_product.protocol.schema import (
    OPERATION_CHECK_CANDIDATE,
    OPERATION_SOLVE,
    OPERATION_SOLVE_QUADRATIC,
    OPERATION_SOLVE_QUADRATIC_SURD,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
)
from mke_product.protocol.validator import validate_request_dict
from mke_product.solver.quadratic import (
    NonQuadraticExpressionError,
    extract_quadratic_coefficients,
    reduce_equation_quadratic,
    solve_quadratic_equation,
)


class TestProtocolVersionOperationMatrix:
    """Validate strict schema version and operation matrix enforcement."""

    def test_v1_solve_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        val = validate_request_dict(req)
        assert val["operation"] == OPERATION_SOLVE

    def test_v1_check_candidate_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "2*x + 4 = 0",
            "candidate": "-2",
        }
        val = validate_request_dict(req)
        assert val["operation"] == OPERATION_CHECK_CANDIDATE

    def test_v1_solve_quadratic_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v1'" in str(exc_info.value)

    def test_v2_solve_quadratic_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        val = validate_request_dict(req)
        assert val["schema_version"] == SCHEMA_VERSION_V2
        assert val["operation"] == OPERATION_SOLVE_QUADRATIC

    def test_v2_solve_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v2'" in str(exc_info.value)

    def test_v2_check_candidate_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 4 = 0",
            "candidate": "2",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v2'" in str(exc_info.value)

    def test_unknown_schema_version_rejected(self):
        req = {
            "schema_version": "mke.p99.v1",
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        with pytest.raises(ProtocolUnsupportedVersionError):
            validate_request_dict(req)

    def test_v2_extra_field_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
            "options": {"timeout": 5},
        }
        with pytest.raises(ProtocolUnexpectedFieldError):
            validate_request_dict(req)

    def test_v2_non_ascii_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 – 4 = 0",  # en-dash
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)

    def test_v2_oversized_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 + " + "1 + " * 100 + "0 = 0",
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)


class TestWorkerQuadraticSolverKernel:
    """Validate mathematical correctness and containment of pure-Python quadratic solver."""

    def test_two_distinct_rational_roots(self):
        eq = parse_equation("x^2 - 4 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-2), Rational(2)]
        assert res.discriminant == Rational(16)

    def test_two_distinct_fractional_roots(self):
        eq = parse_equation("3*x^2 - 5*x + 2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(2, 3), Rational(1)]
        assert res.discriminant == Rational(1)

    def test_unique_repeated_root(self):
        eq = parse_equation("(x - 1)^2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "UNIQUE_REAL_ROOT"
        assert res.roots == [Rational(1)]
        assert res.discriminant == Rational(0)

    def test_no_real_roots_negative_discriminant(self):
        eq = parse_equation("x^2 + 1 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "NO_REAL_ROOT"
        assert res.roots == []
        assert res.discriminant == Rational(-4)

    def test_multiplication_quadratic(self):
        eq = parse_equation("(x + 1)*(x - 1) = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-1), Rational(1)]
        assert res.discriminant == Rational(4)

    def test_repeated_variable_multiplication(self):
        eq = parse_equation("x*x = 4")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-2), Rational(2)]

    def test_irrational_roots_fail_closed(self):
        eq = parse_equation("x^2 - 2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert res.roots == []

    def test_positive_non_square_fractional_discriminant_fail_closed(self):
        # 2*x^2 + 2*x + 0 = 0 -> Delta = 4 (square)
        # x^2 + x - 1/2 = 0 -> Delta = 1 - 4(1)(-1/2) = 3 (non-square)
        eq = parse_equation("2*x^2 + 2*x - 1 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"

    def test_degenerate_affine_rejected(self):
        eq = parse_equation("0*x^2 + x = 1")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_DEGENERATE_AFFINE_EQUATION"

    def test_pure_linear_rejected(self):
        eq = parse_equation("2*x + 4 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_DEGENERATE_AFFINE_EQUATION"

    def test_degree_3_rejected(self):
        eq = parse_equation("x*x*x = 1")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"

    def test_variable_denominator_rejected(self):
        eq = parse_equation("1/(x - 1) = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"

    def test_division_by_zero_constant_domain_error(self):
        eq = parse_equation("x^2 + 1/0 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_DIV_ZERO"

    def test_zero_power_zero_domain_error(self):
        eq = parse_equation("x^2 + 0^0 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_ZERO_POWER_ZERO"


class TestDispatcherQuadraticIntegration:
    """Validate dispatcher execution for v2 SOLVE_QUADRATIC and v1 regression."""

    def test_v2_solve_quadratic_two_roots(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["operation"] == OPERATION_SOLVE_QUADRATIC
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "TWO_DISTINCT_REAL_ROOTS"
        assert res["roots"] == [
            {"numerator": "-2", "denominator": "1"},
            {"numerator": "2", "denominator": "1"},
        ]
        assert res["discriminant"] == {"numerator": "16", "denominator": "1"}
        assert res["definedness"] is True
        assert res["error"] is None

    def test_v2_solve_quadratic_no_real_root(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 + 1 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["operation"] == OPERATION_SOLVE_QUADRATIC
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "NO_REAL_ROOT"
        assert res["roots"] == []
        assert res["discriminant"] == {"numerator": "-4", "denominator": "1"}

    def test_v2_solve_quadratic_unique_root(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "(x - 1)^2 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "UNIQUE_REAL_ROOT"
        assert res["roots"] == [{"numerator": "1", "denominator": "1"}]
        assert res["discriminant"] == {"numerator": "0", "denominator": "1"}

    def test_v2_solve_quadratic_irrational_roots(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 2 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["outcome"] == "OUT_OF_SCOPE"
        assert res["status"] == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert res["roots"] is None

    def test_v1_solve_regression_unchanged(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V1
        assert res["operation"] == OPERATION_SOLVE
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "UNIQUE_ROOT"
        assert res["root"] == {"numerator": "-2", "denominator": "1"}

    def test_v1_check_candidate_on_quadratic(self):
        # Existing S2 evaluator evaluates x^2 - 4 at x = 2
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 4 = 0",
            "candidate": "2",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V1
        assert res["operation"] == OPERATION_CHECK_CANDIDATE
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "VALID"
        assert res["exact_equality"] is True
        assert res["residual"] == {"numerator": "0", "denominator": "1"}


class MockBridgeWorkerController:
    """Mock worker controller for testing bridge quadratic execution."""

    def __init__(
        self,
        solve_res: Optional[dict] = None,
        check_res: Optional[dict] = None,
        check_res_list: Optional[list] = None,
        solve_delay_sec: float = 0.0,
    ):
        self.solve_res = solve_res
        self.check_res = check_res
        self.check_res_list = check_res_list or []
        self.solve_delay_sec = solve_delay_sec
        self.call_history = []

    def execute_request(self, req: dict, timeout_sec: Optional[float] = None) -> dict:
        self.call_history.append((req, timeout_sec))
        op = req.get("operation")
        if self.solve_delay_sec > 0:
            import time
            time.sleep(self.solve_delay_sec)

        if op == OPERATION_SOLVE:
            if self.solve_res is not None:
                return self.solve_res
            return {
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE,
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": False,
            }
        elif op == OPERATION_SOLVE_QUADRATIC:
            if self.solve_res is not None:
                return self.solve_res
            return {
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        elif op == OPERATION_SOLVE_QUADRATIC_SURD:
            if self.solve_res is not None:
                return self.solve_res
            return {
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "2"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "2"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        elif op == OPERATION_CHECK_CANDIDATE:
            if self.check_res_list:
                return self.check_res_list.pop(0)
            if self.check_res is not None:
                return self.check_res
            cand = req.get("candidate")
            # Parse candidate to return matching wire candidate
            if "/" in cand:
                n, d = cand.split("/")
            else:
                n, d = cand, "1"
            return {
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_CHECK_CANDIDATE,
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": n, "denominator": d},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "left_value": {"numerator": "0", "denominator": "1"},
                "right_value": {"numerator": "0", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            }
        return {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": op,
            "outcome": "PROTOCOL_ERROR",
            "status": "ERR_UNKNOWN_OPERATION",
        }


def make_test_ir(expr: str):
    """Helper to create a validated IR dict for bridge dispatch."""
    from mke_product.ai.ir import (
        MathIntermediateRepresentation,
        ProblemCategory,
        QuestionFormat,
        SourceSpan,
    )
    return MathIntermediateRepresentation(
        problem_category=ProblemCategory.EQUATION_SINGLE,
        question_format=QuestionFormat.FREE_FORM,
        raw_query=expr,
        primary_expressions=[expr],
        target_variables=["x"],
        source_spans=[
            SourceSpan(
                start_char=0,
                end_char=len(expr),
                source_fragment=expr,
                semantic_role="EQUATION",
            )
        ],
    ).model_dump()


class TestHostQuadraticExtractorAndReducer:
    """Test independent host AST quadratic analysis."""

    def test_host_extract_simple(self):
        from mke_product.cas.bridge import extract_quadratic_coefficients_host
        eq = parse_equation("x^2 - 4 = 0")
        c2, c1, c0 = extract_quadratic_coefficients_host(eq.left)
        assert c2 == Rational(1)
        assert c1 == Rational(0)
        assert c0 == Rational(-4)

    def test_host_reduce_quadratic(self):
        from mke_product.cas.bridge import reduce_equation_quadratic
        eq = parse_equation("3*x^2 - 5*x + 2 = 0")
        A, B, C = reduce_equation_quadratic(eq)
        assert A == Rational(3)
        assert B == Rational(-5)
        assert C == Rational(2)

    def test_host_rejects_degree_3(self):
        from mke_product.cas.bridge import extract_quadratic_coefficients_host, NonQuadraticExpressionError
        eq = parse_equation("x*x*x = 1")
        with pytest.raises(NonQuadraticExpressionError):
            extract_quadratic_coefficients_host(eq.left)

    def test_host_rejects_variable_denominator(self):
        from mke_product.cas.bridge import extract_quadratic_coefficients_host, NonQuadraticExpressionError
        eq = parse_equation("1/(x - 1) = 0")
        with pytest.raises(NonQuadraticExpressionError):
            extract_quadratic_coefficients_host(eq.left)


class TestControlledDispatchBridgeQuadratic:
    """Test end-to-end controlled dispatch bridge with quadratic equations and adversarial cases."""

    def test_adv01_two_distinct_real_roots(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert res.discriminant.numerator == 16
        assert len(res.verified_roots) == 2
        assert res.verified_roots[0].numerator == -2
        assert res.verified_roots[1].numerator == 2
        assert res.completeness_proven is True
        assert len(mock.call_history) == 3  # 1 SOLVE_QUADRATIC + 2 CHECK_CANDIDATE

    def test_adv02_unique_real_root(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("(x - 1)^2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "UNIQUE_REAL_ROOT",
                "roots": [{"numerator": "1", "denominator": "1"}],
                "discriminant": {"numerator": "0", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="(x - 1)^2 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "UNIQUE_REAL_ROOT"
        assert res.discriminant.numerator == 0
        assert len(res.verified_roots) == 1
        assert res.verified_roots[0].numerator == 1
        assert res.verified_root.numerator == 1
        assert res.completeness_proven is True
        assert len(mock.call_history) == 2  # 1 SOLVE_QUADRATIC + 1 CHECK_CANDIDATE

    def test_adv03_no_real_root(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x^2 + 1 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "NO_REAL_ROOT",
                "roots": [],
                "discriminant": {"numerator": "-4", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 + 1 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "NO_REAL_ROOT"
        assert res.discriminant.numerator == -4
        assert res.verified_roots == []
        assert res.completeness_proven is True
        assert len(mock.call_history) == 1  # 1 SOLVE_QUADRATIC only (no candidate check for EmptySet)

    def test_adv04_uncertified_large_remainder_surd_fails_closed_pre_dispatch(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        p = 65537
        c_val = p * p
        expr = f"2*x^2 - {c_val} = 0"
        ir = make_test_ir(expr)
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT"
        assert len(mock.call_history) == 0  # Zero worker spawn

    def test_adv05_positive_non_square_discriminant_dispatches_surd(self):
        from mke_product.cas.bridge import (
            ControlledDispatchBridge,
            ExecutionStatus,
            IntakeStatus,
            VerificationStatus,
            QuadraticSurdControlledDispatchResult,
        )
        ir = make_test_ir("2*x^2 - 1 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="2*x^2 - 1 = 0", ir_payload=ir, _controller=mock)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert res.radicand == 2
        assert len(mock.call_history) == 1

    def test_adv06_degree_3_rejected_scope(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x*x*x = 1")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x*x*x = 1", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.REJECTED_SCOPE
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_OUT_OF_SCOPE"
        assert len(mock.call_history) == 0

    def test_adv07_var_denominator_rejected_scope(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("1/(x - 1) = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="1/(x - 1) = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.REJECTED_SCOPE
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_OUT_OF_SCOPE"
        assert len(mock.call_history) == 0

    def test_adv08_forged_cardinality_mismatch(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "UNIQUE_REAL_ROOT",
                "roots": [{"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv09_forged_extra_root(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                    {"numerator": "0", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv10_unsorted_worker_roots(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "2", "denominator": "1"},
                    {"numerator": "-2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv11_forged_duplicate_roots(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv12_forged_worker_discriminant(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "99", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv13_schema_version_mismatch_rejected(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_adv14_candidate_check_refuted(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            check_res={
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_CHECK_CANDIDATE,
                "outcome": "SUCCESS",
                "status": "INVALID",
                "candidate": {"numerator": "-2", "denominator": "1"},
                "exact_equality": False,
                "residual": {"numerator": "5", "denominator": "1"},
                "left_value": {"numerator": "5", "denominator": "1"},
                "right_value": {"numerator": "0", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"

    def test_adv15_degenerate_quadratic_rejected_scope(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("0*x^2 + x = 1")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="0*x^2 + x = 1", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.REJECTED_SCOPE
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_OUT_OF_SCOPE"
        assert len(mock.call_history) == 0

    def test_adv16_affine_identity_regression(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x = x")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE,
                "outcome": "SUCCESS",
                "status": "DomainSet(R)",
                "classification": "DomainSet(R)",
                "root": None,
                "definedness": True,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x = x", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "ALL_REALS"
        assert res.completeness_proven is True

    def test_adv17_affine_contradiction_regression(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x = x + 1")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE,
                "outcome": "SUCCESS",
                "status": "EmptySet",
                "classification": "EmptySet",
                "root": None,
                "definedness": True,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x = x + 1", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "EMPTY_SET"
        assert res.completeness_proven is True

    def test_adv18_fractional_roots(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("4*x^2 - 1 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-1", "denominator": "2"},
                    {"numerator": "1", "denominator": "2"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="4*x^2 - 1 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert len(res.verified_roots) == 2
        assert res.verified_roots[0].numerator == -1 and res.verified_roots[0].denominator == 2
        assert res.verified_roots[1].numerator == 1 and res.verified_roots[1].denominator == 2


class TestLiveWindowsWorkerQuadraticIntegration:
    """Live Win32 Worker containment tests executing actual subprocess."""

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_live_worker_quadratic_two_roots(self):
        import sys
        if sys.platform != "win32":
            pytest.skip("Win32 containment only")
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        res = ControlledDispatchBridge.dispatch(raw_query="x^2 - 4 = 0", ir_payload=ir)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert len(res.verified_roots) == 2
        assert res.verified_roots[0].numerator == -2
        assert res.verified_roots[1].numerator == 2

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_live_worker_quadratic_unique_root(self):
        import sys
        if sys.platform != "win32":
            pytest.skip("Win32 containment only")
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("(x - 3)^2 = 0")
        res = ControlledDispatchBridge.dispatch(raw_query="(x - 3)^2 = 0", ir_payload=ir)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "UNIQUE_REAL_ROOT"
        assert len(res.verified_roots) == 1
        assert res.verified_roots[0].numerator == 3

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_live_worker_quadratic_no_real_root(self):
        import sys
        if sys.platform != "win32":
            pytest.skip("Win32 containment only")
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 + 9 = 0")
        res = ControlledDispatchBridge.dispatch(raw_query="x^2 + 9 = 0", ir_payload=ir)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "NO_REAL_ROOT"
        assert res.verified_roots == []


class TestB0SerializationAndFieldCompatibility:
    """Verify ControlledDispatchResult exact field layout and B0 backward compatibility."""

    def test_base_result_field_set(self):
        from mke_product.cas.bridge import (
            ControlledDispatchResult,
            ExecutionStatus,
            IntakeStatus,
            PublicValidationDiagnostic,
            VerificationStatus,
        )
        res = ControlledDispatchResult(
            intake_status=IntakeStatus.VALIDATED,
            intake_diagnostic=PublicValidationDiagnostic(
                is_valid=True,
                is_cas_ready=True,
                status="VALID",
            ),
            execution_status=ExecutionStatus.SUCCESS,
            verification_status=VerificationStatus.VERIFIED_COMPLETE,
            is_verified=True,
            solution_type="UNIQUE_ROOT",
            verified_root=None,
            completeness_proven=True,
            error_code=None,
        )
        dumped = res.model_dump()
        expected_keys = {
            "intake_status",
            "intake_diagnostic",
            "execution_status",
            "verification_status",
            "is_verified",
            "solution_type",
            "verified_root",
            "completeness_proven",
            "error_code",
        }
        assert set(dumped.keys()) == expected_keys
        assert len(dumped) == 9

    def test_b0_linear_query_serialization_backward_compat(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ControlledDispatchResult, QuadraticControlledDispatchResult
        for expr in ["x = 1", "x = x", "x = x + 1"]:
            ir = make_test_ir(expr)
            res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=MockBridgeWorkerController())
            assert type(res) is ControlledDispatchResult
            assert not isinstance(res, QuadraticControlledDispatchResult)
            dumped = res.model_dump()
            assert len(dumped) == 9
            assert "verified_roots" not in dumped
            assert "discriminant" not in dumped

    def test_quadratic_result_inheritance_and_fields(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ControlledDispatchResult, QuadraticControlledDispatchResult
        ir = make_test_ir("x^2 - 4 = 0")
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=MockBridgeWorkerController())
        assert isinstance(res, QuadraticControlledDispatchResult)
        assert isinstance(res, ControlledDispatchResult)
        dumped = res.model_dump()
        assert "verified_roots" in dumped
        assert "discriminant" in dumped
        assert len(dumped) == 11


class TestWireRational256BitLimit:
    """Verify exact 256-bit limit on wire rational parsing."""

    def test_wire_rational_exact_256_bit_accepted(self):
        from mke_product.cas.bridge import _parse_wire_rational
        val_256 = (1 << 256) - 1
        assert val_256.bit_length() == 256
        wire = {"numerator": str(val_256), "denominator": "1"}
        rat = _parse_wire_rational(wire)
        assert rat is not None
        assert rat.numerator == val_256
        assert rat.denominator == 1

    def test_wire_rational_257_bit_numerator_rejected(self):
        from mke_product.cas.bridge import _parse_wire_rational
        val_257 = 1 << 256
        assert val_257.bit_length() == 257
        wire = {"numerator": str(val_257), "denominator": "1"}
        assert _parse_wire_rational(wire) is None

    def test_wire_rational_257_bit_denominator_rejected(self):
        from mke_product.cas.bridge import _parse_wire_rational
        val_257 = 1 << 256
        wire = {"numerator": "1", "denominator": str(val_257)}
        assert _parse_wire_rational(wire) is None

    def test_wire_rational_huge_negative_numerator_rejected(self):
        from mke_product.cas.bridge import _parse_wire_rational
        val_neg_257 = -(1 << 256)
        wire = {"numerator": str(val_neg_257), "denominator": "1"}
        assert _parse_wire_rational(wire) is None

    def test_wire_rational_80_digit_exceeding_256_bits_rejected(self):
        from mke_product.cas.bridge import _parse_wire_rational
        val_80_digits = int("9" * 80)
        assert val_80_digits.bit_length() > 256
        wire = {"numerator": str(val_80_digits), "denominator": "1"}
        assert _parse_wire_rational(wire) is None


class TestStrictV2SuccessEnvelopeAdversarial:
    """Verify strict exact-equality field set validation on v2 success responses."""

    def test_v2_success_missing_error_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_missing_is_provisional_evidence_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_missing_discriminant_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_missing_roots_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_unexpected_extra_field_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
                "unexpected_sidecar_payload": 12345,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_is_provisional_evidence_null_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": None,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_is_provisional_evidence_string_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": "false",
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_v2_success_non_null_error_fails_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [{"numerator": "-2", "denominator": "1"}, {"numerator": "2", "denominator": "1"}],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": "ERR_SOMETHING",
                "is_provisional_evidence": False,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"


class TestHostArithmeticResourceLimits:
    """Verify host proof bounded arithmetic overflow triggers ERR_RESOURCE_EXHAUSTED_HOST_PROOF."""

    def test_host_helpers_valid_256_bit_arithmetic(self):
        from mke_product.cas.bridge import (
            _host_add,
            _host_sub,
            _host_mul,
            _host_div,
            _host_neg,
            _host_check_rational_bounds,
        )
        r1 = Rational(100, 3)
        r2 = Rational(50, 7)
        assert _host_add(r1, r2) == Rational(850, 21)
        assert _host_sub(r1, r2) == Rational(550, 21)
        assert _host_mul(r1, r2) == Rational(5000, 21)
        assert _host_div(r1, r2) == Rational(14, 3)
        assert _host_neg(r1) == Rational(-100, 3)
        assert _host_check_rational_bounds(r1) == r1

    def test_host_helpers_overflow_raises_limit_error(self):
        from mke_product.cas.bridge import (
            _host_add,
            _host_sub,
            _host_mul,
            _host_div,
            _host_neg,
            _host_check_rational_bounds,
            HostQuadraticResourceLimitError,
        )
        huge = 1 << 257
        r_huge = Rational(huge, 1)
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_check_rational_bounds(r_huge)
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_neg(r_huge)
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_add(Rational(1 << 255, 1), Rational(1 << 255, 1))
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_sub(Rational(-(1 << 255), 1), Rational(1 << 255, 1))
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_mul(Rational(1 << 130, 1), Rational(1 << 130, 1))
        with pytest.raises(HostQuadraticResourceLimitError):
            _host_div(Rational(1 << 255, 1), Rational(1, 1 << 10))

    def test_host_overflow_intake_large_coefficient(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        huge = 2**260
        expr = f"{huge}*x^2 - 1 = 0"
        ir = make_test_ir(expr)
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_HOST_PROOF"
        assert len(mock.call_history) == 0

    def test_host_overflow_b_squared(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        b = 1 << 130
        expr = f"x^2 + {b}*x + 1 = 0"
        ir = make_test_ir(expr)
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_HOST_PROOF"
        assert len(mock.call_history) == 0

    def test_host_overflow_four_a_c(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        a = 1 << 130
        c = 1 << 130
        expr = f"{a}*x^2 + x + {c} = 0"
        ir = make_test_ir(expr)
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_HOST_PROOF"
        assert len(mock.call_history) == 0

    def test_host_overflow_delta_computation(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        b = 1 << 127
        a = 1 << 127
        c = -(1 << 127)
        expr = f"{a}*x^2 + {b}*x + ({c}) = 0"
        ir = make_test_ir(expr)
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query=expr, ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_HOST_PROOF"
        assert len(mock.call_history) == 0


class TestWorkerInfrastructureTaxonomy:
    """Verify all worker infrastructure failure taxonomies are strictly mapped."""

    @pytest.mark.parametrize(
        "worker_status,expected_exec,expected_err",
        [
            ("WORKER_TIMEOUT", "TIMEOUT", "ERR_TIMEOUT"),
            ("WORKER_RESOURCE_EXHAUSTED", "ENGINE_ERROR", "ERR_RESOURCE_EXHAUSTED"),
            ("WORKER_STARTUP_FAILURE", "ENGINE_ERROR", "ERR_WORKER_STARTUP_FAILURE"),
            ("WORKER_ASSIGNMENT_FAILURE", "ENGINE_ERROR", "ERR_WORKER_ASSIGNMENT_FAILURE"),
            ("WORKER_EXIT_FAILURE", "ENGINE_ERROR", "ERR_WORKER_EXIT_FAILURE"),
            ("WORKER_PROTOCOL_FAILURE", "ENGINE_ERROR", "ERR_WORKER_PROTOCOL_FAILURE"),
            ("ERR_RESOURCE_EXHAUSTED", "ENGINE_ERROR", "ERR_RESOURCE_EXHAUSTED"),
            ("ERR_PAYLOAD_TOO_LARGE", "ENGINE_ERROR", "ERR_PAYLOAD_TOO_LARGE"),
            ("ERR_RESPONSE_LIMIT_EXCEEDED", "ENGINE_ERROR", "ERR_RESPONSE_LIMIT_EXCEEDED"),
            ("PROTOCOL_ERROR", "ENGINE_ERROR", "ERR_PROTOCOL_ERROR"),
        ],
    )
    def test_worker_infrastructure_errors_solve_quadratic(self, worker_status, expected_exec, expected_err):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "status": worker_status,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == getattr(ExecutionStatus, expected_exec)
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == expected_err

    def test_worker_direct_v2_resource_exhaustion_outcome(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "RESOURCE_EXHAUSTED",
                "status": "ERR_RESOURCE_EXHAUSTED",
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED"


class TestCollusiveWorkerVerificationDefeat:
    """Verify that even if worker colludes in both solve and candidate check, host proof prevents false verification."""

    def test_collusive_wrong_root_with_fake_check_success(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "1", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            },
            check_res={
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_CHECK_CANDIDATE,
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "left_value": {"numerator": "0", "denominator": "1"},
                "right_value": {"numerator": "0", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            },
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.is_verified is False
        assert res.error_code == "ERR_VERIFICATION_MISMATCH"


class TestCumulativeDeadlineStrictBudget:
    """Verify monotonic decreasing budget passed across all worker invocations."""

    def test_cumulative_deadline_3_calls(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, VerificationStatus
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController(solve_delay_sec=0.05)
        res = ControlledDispatchBridge._dispatch_internal(
            raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock, _budget_sec=5.0
        )
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert len(mock.call_history) == 3
        req1, to1 = mock.call_history[0]
        req2, to2 = mock.call_history[1]
        req3, to3 = mock.call_history[2]
        assert to1 is not None and to2 is not None and to3 is not None
        assert to1 <= 5.0
        assert to2 < to1
        assert to3 < to2
        assert to3 > 0.0


class TestBridgeHostArchitectureIndependence:
    """Verify architectural boundary: bridge.py must NOT import mke_product.solver.quadratic."""

    def test_bridge_does_not_import_solver_quadratic(self):
        import inspect
        from mke_product.cas import bridge
        source = inspect.getsource(bridge)
        assert "from mke_product.solver.quadratic" not in source
        assert "import mke_product.solver.quadratic" not in source
        assert "solve_quadratic_equation" not in source


