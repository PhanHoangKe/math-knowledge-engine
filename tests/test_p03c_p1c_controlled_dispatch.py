"""Adversarial and functional test suite for P1C-04-B0 Controlled CAS Dispatch Bridge.

Milestone: PRODUCT-03C-P1C-04-B0
Verifies:
- 11-case adversarial test matrix
- Semantic-exhaustiveness guard
- Exact mathematical proof contracts (UNIQUE_ROOT, ALL_REALS, EMPTY_SET)
- Wire rational string validation & outcome/status taxonomy
- Shared 5.0-second monotonic wall-clock budget
- Locked containment & zero caller override in public API
- Mocked platform safety and actual Windows Job Object integration
- Public diagnostic sanitization and zero PII/path leaks
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
    NonAffineExpressionError,
    _parse_wire_rational,
)
from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation


class MockWorkerController:
    """Mock worker controller for deterministic unit testing of wire responses."""

    def __init__(self, solve_response: Optional[dict] = None, check_response: Optional[dict] = None):
        self.solve_response = solve_response
        self.check_response = check_response
        self.call_history = []

    def execute_request(self, request: dict, timeout_sec: Optional[float] = None) -> dict:
        self.call_history.append((request, timeout_sec))
        op = request.get("operation")
        if op == "SOLVE":
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
    """Verifies the exact 11-case adversarial test matrix from P1C-04-A-R2 specification."""

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
        # Extractor extracted only "x = 1"
        ir = make_valid_ir(raw, expr="x = 1")
        ctrl = MockWorkerController()

        res = ControlledDispatchBridge._dispatch_internal(raw, ir, _controller=ctrl)

        self.assertFalse(res.is_verified)
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_NON_EXHAUSTIVE)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_INTAKE_NON_EXHAUSTIVE")
        self.assertEqual(len(ctrl.call_history), 0)  # Must NOT dispatch

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
        """Case 5: Nonlinear Quadratic Equation x^2 - 4 = 0 rejected pre-dispatch."""
        raw = "x^2 - 4 = 0"
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
        # Hostile payload with mismatched raw_query
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
        self.assertEqual(res.intake_status, IntakeStatus.REJECTED_SYNTAX)
        self.assertEqual(res.execution_status, ExecutionStatus.NOT_DISPATCHED)
        self.assertEqual(res.error_code, "ERR_INTAKE_VALIDATION_FAILED")
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
                "root": {"numerator": "5", "denominator": "1"},  # Fabricated wrong root
                "definedness": True,
                "is_provisional_evidence": False,
            },
            check_response={
                "schema_version": "mke.p02a.v1",
                "operation": "CHECK_CANDIDATE",
                "outcome": "SUCCESS",
                "status": "INVALID",  # Correctly detected invalid by candidate checker
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
                # Simulate consuming remaining budget
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


class TestAffineCompletenessAnalyzer(unittest.TestCase):
    """Unit tests for the independent bounded host AST affine-completeness analyzer."""

    def test_linear_reductions(self):
        eq1 = parse_equation("2 * x + 3 = 7")
        A, B = extract_affine_coefficients(eq1.left), extract_affine_coefficients(eq1.right)
        self.assertEqual(A, (Rational(2), Rational(3)))
        self.assertEqual(B, (Rational(0), Rational(7)))

    def test_bracketed_complex_linear(self):
        eq = parse_equation("(3 * (x - 2) + 4) / 2 = x + 1")
        a_L, b_L = extract_affine_coefficients(eq.left)
        a_R, b_R = extract_affine_coefficients(eq.right)
        self.assertEqual(a_L, Rational(3, 2))
        self.assertEqual(b_L, Rational(-1, 1))
        self.assertEqual(a_R, Rational(1))
        self.assertEqual(b_R, Rational(1))

    def test_nonlinear_quadratic_rejected(self):
        eq = parse_equation("x * x = 4")
        with self.assertRaises(NonAffineExpressionError):
            extract_affine_coefficients(eq.left)

    def test_power_two_rejected(self):
        eq = parse_equation("x^2 = 9")
        with self.assertRaises(NonAffineExpressionError):
            extract_affine_coefficients(eq.left)

    def test_division_by_variable_rejected(self):
        eq = parse_equation("1 / x = 2")
        with self.assertRaises(NonAffineExpressionError):
            extract_affine_coefficients(eq.left)


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
