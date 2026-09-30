"""Adversarial and functional test suite for P1C-04-B0 Controlled CAS Dispatch Bridge.

Milestone: PRODUCT-03C-P1C-04-B0-R1
Verifies:
- Complete 11-case adversarial test matrix.
- CHECK_CANDIDATE envelope integrity (schema_version, operation, exact rational wire validation).
- Refutation of colluding/forged SOLVE + CHECK claiming UNIQUE_ROOT for identities (x = x) or contradictions (x = x + 1).
- SOLVE envelope consistency (status/classification equality, definedness is True, null root for set solutions).
- Domain-safe host proof checker (rejection of variable-dependent exponent 0, 0^0, power > 1, bit/node bounds).
- Real cumulative budget budgeting where SOLVE consumes wall-clock budget and CHECK receives the remainder.
- Sanitized public result projection with zero PII, path, AST, or trace leakage.
- Live Win32 Worker containment execution.
"""

from __future__ import annotations

import sys
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

from mke_product.ai.ir import (
    MathIntermediateRepresentation,
    ProblemCategory,
    QuestionFormat,
    SourceSpan,
)
from mke_product.cas.bridge import (
    ControlledDispatchBridge,
    ControlledDispatchResult,
    ExecutionStatus,
    IntakeStatus,
    RationalRoot,
    VerificationStatus,
    extract_affine_coefficients,
    reduce_equation_affine,
    NonAffineExpressionError,
    _parse_wire_rational,
)
from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation


class MockWorkerController:
    """Mock worker controller for deterministic unit testing of wire responses."""

    def __init__(
        self,
        solve_response: Optional[dict] = None,
        check_response: Optional[dict] = None,
        solve_delay_sec: float = 0.0,
    ):
        self.solve_response = solve_response
        self.check_response = check_response
        self.solve_delay_sec = solve_delay_sec
        self.call_history = []

    def execute_request(self, request: dict, timeout_sec: Optional[float] = None) -> dict:
        self.call_history.append((request, timeout_sec))
        op = request.get("operation")
        if op == "SOLVE":
            if self.solve_delay_sec > 0:
                time.sleep(self.solve_delay_sec)
            return self.solve_response if self.solve_response is not None else {
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": False,
            }
        elif op == "CHECK_CANDIDATE":
            return self.check_response if self.check_response is not None else {
                "schema_version": "mke.p02a.v1",
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "left_value": {"numerator": "1", "denominator": "1"},
                "right_value": {"numerator": "1", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            }
        return {
            "schema_version": "mke.p02a.v1",
            "operation": op,
            "outcome": "PROTOCOL_ERROR",
            "status": "ERR_UNKNOWN_OPERATION",
        }


def make_valid_ir(
    raw_query: str,
    expr: Optional[str] = None,
    target_var: str = "x",
) -> MathIntermediateRepresentation:
    """Construct a well-formed MKE-IR model for testing."""
    primary_expr = expr if expr is not None else raw_query
    span_start = raw_query.find(primary_expr)
    span_end = span_start + len(primary_expr) if span_start != -1 else len(raw_query)

    spans = []
    if span_start != -1:
        spans.append(
            SourceSpan(
                start_char=span_start,
                end_char=span_end,
                source_fragment=primary_expr,
                semantic_role="EQUATION",
            )
        )

    return MathIntermediateRepresentation(
        problem_category=ProblemCategory.EQUATION_SINGLE,
        question_format=QuestionFormat.FREE_FORM,
        raw_query=raw_query,
        primary_expressions=[primary_expr],
        target_variables=[target_var] if target_var else [],
        source_spans=spans,
    )


class TestControlledDispatchPreflightMatrix(unittest.TestCase):
    """Verifies the 11-case adversarial test matrix and baseline functional scenarios."""

    def test_case_01_canonical_linear_equation(self):
        """Case 1: Canonical Linear Equation x = 1 (Verified Complete)."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.VALIDATED)
        self.assertEqual(res.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_COMPLETE)
        self.assertEqual(res.solution_type, "UNIQUE_ROOT")
        self.assertEqual(res.verified_root, RationalRoot(numerator=1, denominator=1))
        self.assertTrue(res.completeness_proven)
        self.assertEqual(len(ctrl.call_history), 2)  # SOLVE + CHECK_CANDIDATE

    def test_case_02_affine_identity_all_reals(self):
        """Case 2: Affine Identity x = x (All Reals Verified Complete)."""
        raw = "x = x"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "DomainSet(R)",
                "classification": "DomainSet(R)",
                "root": None,
                "definedness": True,
                "is_provisional_evidence": False,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.VALIDATED)
        self.assertEqual(res.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_COMPLETE)
        self.assertEqual(res.solution_type, "ALL_REALS")
        self.assertTrue(res.completeness_proven)
        self.assertIsNone(res.verified_root)

    def test_case_03_affine_contradiction_empty_set(self):
        """Case 3: Affine Contradiction x = x + 1 (Empty Set Verified Complete)."""
        raw = "x = x + 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "EmptySet",
                "classification": "EmptySet",
                "root": None,
                "definedness": True,
                "is_provisional_evidence": False,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.VALIDATED)
        self.assertEqual(res.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_COMPLETE)
        self.assertEqual(res.solution_type, "EMPTY_SET")
        self.assertTrue(res.completeness_proven)
        self.assertIsNone(res.verified_root)

    def test_case_04_semantic_exhaustiveness_rejection_clause(self):
        """Case 4: Semantic exhaustiveness rejection with natural language clause 'x = 1 với x > 2'."""
        raw = "x = 1 với x > 2"
        ir = make_valid_ir(raw, expr="x = 1")
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_04b_semantic_exhaustiveness_rejection_second_equation(self):
        """Case 4b: Semantic exhaustiveness rejection with unextracted equation 'x = 1 và x = 2'."""
        raw = "x = 1 và x = 2"
        ir = make_valid_ir(raw, expr="x = 1")
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_05_nonlinear_quadratic_equation_pre_dispatch(self):
        """Case 5: Nonlinear degree >= 3 equation x*x*x = 1 rejected pre-dispatch."""
        raw = "x*x*x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SCOPE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_OUT_OF_SCOPE")
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_06_protocol_length_overflow(self):
        """Case 6: Protocol character limit overflow (> 256 chars)."""
        raw = "x + " + "1 + " * 100 + "1 = 0"
        self.assertGreater(len(raw), 256)
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SCOPE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_PROTOCOL_BOUNDS_EXCEEDED")
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_07_non_ascii_mathematical_notation(self):
        """Case 7: Non-ASCII mathematical character (Unicode minus \u2212)."""
        raw = "x \u2212 1 = 0"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertIn(res.intake_status, (IntakeStatus.REJECTED_SYNTAX, IntakeStatus.REJECTED_SCOPE))
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_08_fabricated_intake_bypass_attempt(self):
        """Case 8: Fabricated or ungrounded input failing intake validation."""
        raw = "x = 1"
        bad_payload = {
            "schema_version": "mke.ir.v1",
            "problem_category": "EQUATION_SINGLE",
            "question_format": "FREE_FORM",
            "raw_query": "y = 100",  # Mismatch with authoritative raw_query
            "primary_expressions": ["x = 1"],
            "target_variables": ["x"],
            "source_spans": [{"start_char": 0, "end_char": 5, "source_fragment": "x = 1", "semantic_role": "EQUATION"}],
        }
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, bad_payload, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(len(ctrl.call_history), 0)

    def test_case_09_contradictory_forged_worker_evidence(self):
        """Case 9: Worker claims root x=5 for x = 1; candidate check refutes it."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "5", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": False,
            },
            check_response={
                "schema_version": "mke.p02a.v1",
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "INVALID",
                "candidate": {"numerator": "5", "denominator": "1"},
                "exact_equality": False,
                "residual": {"numerator": "4", "denominator": "1"},
                "left_value": {"numerator": "5", "denominator": "1"},
                "right_value": {"numerator": "1", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            },
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFICATION_FAILED)
        self.assertEqual(res.error_code, "ERR_VERIFICATION_MISMATCH")

    def test_case_10_cumulative_budget_timeout(self):
        """Case 10: Cumulative budget exceeded across multi-step execution."""
        raw = "x = 1"
        ir = make_valid_ir(raw)

        class HangingMockController:
            def execute_request(self, request, timeout_sec=None):
                time.sleep(0.15)
                return {
                    "schema_version": "mke.p02a.v1",
                    "operation": "SOLVE",
                    "outcome": "RESOURCE_EXHAUSTED",
                    "status": "WORKER_TIMEOUT",
                }

        ctrl = HangingMockController()
        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl, _budget_sec=0.1)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.TIMEOUT)
        self.assertEqual(res.error_code, "ERR_TIMEOUT")

    def test_case_11_non_windows_platform_fail_closed(self):
        """Case 11: Non-Windows platform cleanly returns ERR_PLATFORM_NOT_SUPPORTED."""
        raw = "x = 1"
        ir = make_valid_ir(raw)

        with patch("sys.platform", "linux"):
            res = ControlledDispatchBridge.dispatch(raw, ir)

            self.assertFalse(res.is_verified)
            self.assertEqual(res.intake_status, IntakeStatus.VALIDATED)
            self.assertEqual(res.execution_status, ExecutionStatus.PLATFORM_UNAVAILABLE)
            self.assertEqual(res.error_code, "ERR_PLATFORM_NOT_SUPPORTED")


class TestAdversarialWireIntegrityAndEnvelopeValidation(unittest.TestCase):
    """Adversarial suite verifying wire response envelope integrity and anti-collusion."""

    def test_check_candidate_wrong_schema_version(self):
        """Worker returns wrong schema_version in CHECK_CANDIDATE -> reject."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            check_response={
                "schema_version": "mke.p03a.v99",  # Wrong schema version
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.ENGINE_ERROR)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFICATION_FAILED)
        self.assertEqual(res.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_check_candidate_wrong_operation_echo(self):
        """Worker returns wrong operation in CHECK_CANDIDATE -> reject."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            check_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",  # Wrong operation echo
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.ENGINE_ERROR)
        self.assertEqual(res.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_colluding_forged_solve_and_check_unique_root_on_identity(self):
        """Worker colludes on x = x claiming UNIQUE_ROOT with root=1; CHECK also says valid -> MUST REFUTE."""
        raw = "x = x"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": True,
            },
            check_response={
                "schema_version": "mke.p02a.v1",
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "definedness": True,
            },
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        # Host proof proves A == 0, B == 0 (identity), so UNIQUE_ROOT is refuted!
        self.assertFalse(res.is_verified)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFICATION_FAILED)
        self.assertEqual(res.error_code, "ERR_VERIFICATION_MISMATCH")

    def test_colluding_forged_solve_and_check_unique_root_on_contradiction(self):
        """Worker colludes on x = x + 1 claiming UNIQUE_ROOT with root=1; CHECK also forged -> MUST REFUTE."""
        raw = "x = x + 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": True,
            },
            check_response={
                "schema_version": "mke.p02a.v1",
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": "1", "denominator": "1"},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "definedness": True,
            },
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        # Host proof proves A == 0, B == -1 (contradiction), so UNIQUE_ROOT is refuted!
        self.assertFalse(res.is_verified)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFICATION_FAILED)
        self.assertEqual(res.error_code, "ERR_VERIFICATION_MISMATCH")

    def test_solve_status_classification_mismatch(self):
        """SOLVE status and classification contradict each other -> reject."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "DomainSet(R)",  # Contradicts status
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.ENGINE_ERROR)
        self.assertEqual(res.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_unique_root_definedness_false_or_missing_root(self):
        """UNIQUE_ROOT with definedness False or missing root -> reject."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        # 1. definedness False
        ctrl1 = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "1", "denominator": "1"},
                "definedness": False,  # Illegal for SUCCESS
            }
        )
        res1 = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl1)
        self.assertFalse(res1.is_verified)
        self.assertEqual(res1.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

        # 2. missing root
        ctrl2 = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": None,  # Missing root for UNIQUE_ROOT
                "definedness": True,
            }
        )
        res2 = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl2)
        self.assertFalse(res2.is_verified)
        self.assertEqual(res2.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_domainset_r_with_unexpected_root_or_wrong_classification(self):
        """DomainSet(R) returning a non-null root -> reject."""
        raw = "x = x"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "DomainSet(R)",
                "classification": "DomainSet(R)",
                "root": {"numerator": "0", "denominator": "1"},  # Illegal root for DomainSet(R)
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.ENGINE_ERROR)
        self.assertEqual(res.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_emptyset_with_unexpected_root_or_wrong_classification(self):
        """EmptySet returning a non-null root -> reject."""
        raw = "x = x + 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "EmptySet",
                "classification": "EmptySet",
                "root": {"numerator": "0", "denominator": "1"},  # Illegal root for EmptySet
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.execution_status, ExecutionStatus.ENGINE_ERROR)
        self.assertEqual(res.error_code, "ERR_MALFORMED_WORKER_RESPONSE")

    def test_real_cumulative_budget_consumption(self):
        """SOLVE consumes 0.2s of a 1.0s budget; CHECK_CANDIDATE receives remainder <= 0.8s."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(solve_delay_sec=0.2)

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl, _budget_sec=1.0)

        self.assertTrue(res.is_verified)
        self.assertEqual(len(ctrl.call_history), 2)
        solve_call, solve_budget = ctrl.call_history[0]
        check_call, check_budget = ctrl.call_history[1]
        self.assertAlmostEqual(solve_budget, 1.0, delta=0.05)
        # Check budget must reflect elapsed time from SOLVE
        self.assertLessEqual(check_budget, 0.85)
        self.assertGreaterEqual(check_budget, 0.5)


class TestDomainSafeHostProofChecker(unittest.TestCase):
    """Unit tests for domain safety in independent host affine AST analyzer."""

    def test_variable_dependent_exponent_zero_rejected(self):
        """x^0 = 1 or (x + 1)^0 = 1 is domain-unsafe and rejected pre-dispatch."""
        with self.assertRaises(NonAffineExpressionError):
            eq = parse_equation("x^0 = 1")
            extract_affine_coefficients(eq.left)

        with self.assertRaises(NonAffineExpressionError):
            eq = parse_equation("(x + 2)^0 = 1")
            extract_affine_coefficients(eq.left)

    def test_zero_power_zero_rejected(self):
        """0^0 is undefined and rejected."""
        with self.assertRaises(NonAffineExpressionError):
            eq = parse_equation("0^0 = 1")
            extract_affine_coefficients(eq.left)

    def test_constant_non_zero_power_zero_accepted(self):
        """2^0 is safe constant 1."""
        eq = parse_equation("2^0 = 1")
        a, b = extract_affine_coefficients(eq.left)
        self.assertEqual(a, Rational(0))
        self.assertEqual(b, Rational(1))

    def test_constant_power_two_accepted_with_bit_bounds(self):
        """Constant 3^2 evaluates safely to 9."""
        eq = parse_equation("3^2 = 9")
        a, b = extract_affine_coefficients(eq.left)
        self.assertEqual(a, Rational(0))
        self.assertEqual(b, Rational(9))

    def test_variable_power_two_rejected(self):
        """Variable x^2 is rejected as nonlinear."""
        with self.assertRaises(NonAffineExpressionError):
            eq = parse_equation("x^2 = 4")
            extract_affine_coefficients(eq.left)

    def test_bounded_bit_length_overflow_guard(self):
        """Large integer arithmetic exceeding 256 bits fails closed."""
        large_val = (1 << 300)
        from mke_product.parser.ast import IntegerLiteral
        lit = IntegerLiteral(value=large_val)
        with self.assertRaises(NonAffineExpressionError):
            extract_affine_coefficients(lit)

    def test_forged_domainset_for_x_pow_zero_fails_closed(self):
        """Worker claiming DomainSet(R) for x^0 = 1 fails closed at host gate."""
        raw = "x^0 = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController(
            solve_response={
                "schema_version": "mke.p02a.v1",
                "operation": "SOLVE",
                "outcome": "SUCCESS",
                "status": "DomainSet(R)",
                "classification": "DomainSet(R)",
                "root": None,
                "definedness": True,
            }
        )

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SCOPE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_OUT_OF_SCOPE")


class TestWireRationalParsingAndValidation(unittest.TestCase):
    """Unit tests for wire rational string validation."""

    def test_valid_wire_rationals(self):
        r1 = _parse_wire_rational({"numerator": "3", "denominator": "4"})
        self.assertEqual(r1, Rational(3, 4))

        r2 = _parse_wire_rational({"numerator": "-5", "denominator": "1"})
        self.assertEqual(r2, Rational(-5, 1))

        r3 = _parse_wire_rational({"numerator": "0", "denominator": "1"})
        self.assertEqual(r3, Rational(0, 1))

    def test_rejected_wire_rationals(self):
        # Float rejected
        self.assertIsNone(_parse_wire_rational({"numerator": 3.5, "denominator": 1}))
        # Integer type rejected (wire must use string digits)
        self.assertIsNone(_parse_wire_rational({"numerator": 3, "denominator": 4}))
        # Non-positive denominator
        self.assertIsNone(_parse_wire_rational({"numerator": "1", "denominator": "0"}))
        self.assertIsNone(_parse_wire_rational({"numerator": "1", "denominator": "-1"}))
        # Non-reduced uncanonical wire string
        self.assertIsNone(_parse_wire_rational({"numerator": "2", "denominator": "4"}))
        # Non-digits / NaN
        self.assertIsNone(_parse_wire_rational({"numerator": "NaN", "denominator": "1"}))
        self.assertIsNone(_parse_wire_rational({"numerator": "1", "denominator": "inf"}))


class TestPublicSignatureLockAndDiagnosticSanitization(unittest.TestCase):
    """Verifies that the public API signature is locked and strips sensitive details."""

    def test_public_dispatch_signature_is_locked(self):
        import inspect
        sig = inspect.signature(ControlledDispatchBridge.dispatch)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["raw_query", "ir_payload"])

    def test_public_result_does_not_leak_ast_or_raw_traceback(self):
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)
        res_dict = res.model_dump()

        self.assertNotIn("ast", res_dict)
        self.assertNotIn("raw_traceback", res_dict)
        self.assertNotIn("C:\\", str(res_dict))
        self.assertNotIn("D:\\", str(res_dict))


class TestRealIntakeTaxonomyClassification(unittest.TestCase):
    """Targeted tests using REAL MKEIntakeValidator outcomes verifying precise public intake taxonomy."""

    def test_real_validator_malformed_math_syntax_rejected_syntax(self):
        """Malformed mathematical syntax (e.g. invalid operator sequences) -> REJECTED_SYNTAX."""
        raw = "x ++ 1 = 0"
        ir = make_valid_ir(raw)
        res = ControlledDispatchBridge.dispatch(raw, ir)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SYNTAX)
        self.assertEqual(res.error_code, "ERR_INTAKE_SYNTAX_INVALID")
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.verification_status, VerificationStatus.NOT_APPLICABLE)

    def test_real_validator_missing_target_variable_rejected_scope(self):
        """Missing target variable is a capability/scope failure -> REJECTED_SCOPE."""
        raw = "x = 1"
        ir_dict = make_valid_ir(raw).model_dump()
        ir_dict["target_variables"] = []
        res = ControlledDispatchBridge.dispatch(raw, ir_dict)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SCOPE)
        self.assertEqual(res.error_code, "ERR_INTAKE_SCOPE_UNSUPPORTED")
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.verification_status, VerificationStatus.NOT_APPLICABLE)

    def test_real_validator_unsupported_category_rejected_scope(self):
        """Unsupported problem category is a capability/scope failure -> REJECTED_SCOPE."""
        raw = "x = 1"
        ir_dict = make_valid_ir(raw).model_dump()
        ir_dict["problem_category"] = "GEOMETRY_ANALYTIC"
        res = ControlledDispatchBridge.dispatch(raw, ir_dict)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SCOPE)
        self.assertEqual(res.error_code, "ERR_INTAKE_SCOPE_UNSUPPORTED")
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.verification_status, VerificationStatus.NOT_APPLICABLE)

    def test_real_validator_raw_query_mismatch_fails_closed_non_exhaustive(self):
        """Source integrity failure (raw query mismatch) fails closed as REJECTED_NON_EXHAUSTIVE without dispatch."""
        raw = "x = 1"
        ir_dict = make_valid_ir(raw).model_dump()
        ir_dict["raw_query"] = "y = 100"
        res = ControlledDispatchBridge.dispatch(raw, ir_dict)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.verification_status, VerificationStatus.NOT_APPLICABLE)

    def test_real_validator_source_fragment_mismatch_fails_closed_non_exhaustive(self):
        """Source span mismatch against raw query fails closed as REJECTED_NON_EXHAUSTIVE."""
        raw = "x = 1"
        ir_dict = make_valid_ir(raw).model_dump()
        ir_dict["source_spans"][0]["source_fragment"] = "x = 2"
        res = ControlledDispatchBridge.dispatch(raw, ir_dict)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.verification_status, VerificationStatus.NOT_APPLICABLE)

    def test_real_validator_canonical_equation_verified_complete(self):
        """Canonical equation x = 1 passes all intake gates and reaches VERIFIED_COMPLETE."""
        raw = "x = 1"
        ir = make_valid_ir(raw)
        ctrl = MockWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.VALIDATED)
        self.assertEqual(res.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_COMPLETE)
        self.assertEqual(res.solution_type, "UNIQUE_ROOT")
        self.assertEqual(res.verified_root, RationalRoot(numerator=1, denominator=1))
        self.assertTrue(res.completeness_proven)


@unittest.skipUnless(sys.platform == "win32", "Windows Job Object integration requires native Win32 runtime")
class TestLiveWindowsWorkerIntegration(unittest.TestCase):
    """Live execution tests against the actual Win32 WorkerController."""

    def test_live_worker_solve_linear(self):
        raw = "x = 5"
        ir = make_valid_ir(raw)
        res = ControlledDispatchBridge.dispatch(raw, ir)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.solution_type, "UNIQUE_ROOT")
        self.assertEqual(res.verified_root, RationalRoot(numerator=5, denominator=1))
        self.assertTrue(res.completeness_proven)

    def test_live_worker_solve_identity(self):
        raw = "x = x"
        ir = make_valid_ir(raw)
        res = ControlledDispatchBridge.dispatch(raw, ir)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.solution_type, "ALL_REALS")
        self.assertTrue(res.completeness_proven)

    def test_live_worker_solve_contradiction(self):
        raw = "x = x + 1"
        ir = make_valid_ir(raw)
        res = ControlledDispatchBridge.dispatch(raw, ir)

        self.assertTrue(res.is_verified)
        self.assertEqual(res.solution_type, "EMPTY_SET")
        self.assertTrue(res.completeness_proven)


if __name__ == "__main__":
    unittest.main()
