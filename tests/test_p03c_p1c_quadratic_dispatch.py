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
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
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

    def test_adv04_irrational_roots_fail_closed_pre_dispatch(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert len(mock.call_history) == 0  # Zero worker spawn

    def test_adv05_positive_non_square_fractional_discriminant_fail_closed(self):
        from mke_product.cas.bridge import ControlledDispatchBridge, ExecutionStatus, IntakeStatus, VerificationStatus
        ir = make_test_ir("2*x^2 - 1 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="2*x^2 - 1 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.NOT_DISPATCHED
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert len(mock.call_history) == 0

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

