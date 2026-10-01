"""MKE MVP V1 — S1-05 End-to-End Application Acceptance Suite.

Authoritative Acceptance Test Suite for the S1 Pure Python Application Service boundary.
Treats `solve_request(SolveRequest(...))` as the System Under Test (SUT).

Sections:
1. Canonical 32-Case Acceptance Matrix (Q1-Q9, C1-C5, D1-D4, E1-E8, B1-B6).
2. Raw / Raw-Equivalent / Coefficient Semantic Equivalence.
3. Method-Switch Reactivity Contract.
4. Coefficient-Edit Reactivity Contract (including Quadratic -> Degenerate transition).
5. All Four Executable Methods & All Unavailable Methods Rejection.
6. Deterministic Response Semantics & Stable Identity Snapshots.
7. Serialization Round-Trip & Polymorphic Discriminator Preservation.
8. State-Machine Invariant & Impossibility Rejections.
9. Strict Client Error Sanitization (Zero Sentinel / Leakage).
10. Authoritative Domain IR Gate Verification.
11. Method Catalog 9-Option Order & 11-Field Parity.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict
import unittest
from unittest.mock import patch

from pydantic import TypeAdapter, ValidationError

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
from mke_product.application.traces.base import (
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
)
from mke_product.core.rational import Rational
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    MethodAssessment,
    PedagogicalRecommendation,
    PrerequisiteStatus,
    ProblemCategory,
    QuadraticDiscriminant,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
    SolutionStep,
    SolutionTrace,
    SupportStatus,
    VerificationCapability,
    VerificationCertificate,
    VerificationOutcome,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.domain.verifier import HostIndependentVerifier


# ============================================================================
# 1. CANONICAL 32-ROW ACCEPTANCE MATRIX (Q1-Q9, C1-C5, D1-D4, E1-E8, B1-B6)
# ============================================================================

class TestS1Acceptance32CaseMatrix(unittest.TestCase):
    """Canonical 32-row acceptance matrix exercising solve_request boundary."""

    # --- QUADRATIC ACCEPTANCE (Q1 - Q9) ---

    def test_q1_distinct_rational_roots(self):
        """Q1: x^2 - 5*x + 6 = 0 -> SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.classification, EquationClassificationType.QUADRATIC)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(resp.problem.discriminant.value, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(resp.solution.roots), 2)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(2))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(3))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots, resp.solution.trace.roots)
        self.assertEqual(resp.selected_method_id, resp.solution.method_id)
        selected_opt = next(m for m in resp.available_methods if m.method_id == resp.selected_method_id)
        self.assertEqual(selected_opt.mathematical_applicability, MathematicalApplicability.APPLICABLE)
        self.assertEqual(selected_opt.execution_availability, ExecutionAvailability.AVAILABLE)
        self.assertTrue(selected_opt.has_trace_available)
        self.assertTrue(bool(resp.problem.semantic_revision_hash))
        self.assertTrue(bool(resp.problem.problem_id))

    def test_q2_exact_real_surd_roots(self):
        """Q2: x^2 - 2 = 0 -> SOLVED, roots {-sqrt(2), sqrt(2)}, discriminant 8."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 2 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.problem.discriminant.value, RationalFraction.from_int(8))
        self.assertEqual(len(resp.solution.roots), 2)
        self.assertEqual(resp.solution.roots[0].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(resp.solution.roots[0].radicand, 2)
        self.assertEqual(resp.solution.roots[0].surd_factor, RationalFraction.from_int(-1))
        self.assertEqual(resp.solution.roots[1].surd_factor, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots, resp.solution.trace.roots)

    def test_q3_repeated_real_root(self):
        """Q3: x^2 - 2*x + 1 = 0 -> SOLVED, root {1}, discriminant 0."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 2*x + 1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(resp.problem.discriminant.value, RationalFraction.from_int(0))
        self.assertEqual(len(resp.solution.roots), 1)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots, resp.solution.trace.roots)

    def test_q4_no_real_roots(self):
        """Q4: x^2 + 1 = 0 -> SOLVED, roots empty, discriminant -4."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.NO_REAL_ROOTS)
        self.assertEqual(resp.problem.discriminant.value, RationalFraction.from_int(-4))
        self.assertEqual(resp.solution.roots, [])
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots, resp.solution.trace.roots)

    def test_q5_non_monic_distinct_rational_roots(self):
        """Q5: 2*x^2 - 5*x + 2 = 0 -> SOLVED, roots {1/2, 2}, discriminant 9."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x^2 - 5*x + 2 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.problem.discriminant.value, RationalFraction.from_int(9))
        self.assertEqual(len(resp.solution.roots), 2)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction(numerator=1, denominator=2))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(2))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q6_rearranged_quadratic(self):
        """Q6: x^2 + 6 = 5*x -> SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 6 = 5*x"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(len(resp.solution.roots), 2)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(2))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(3))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q7_factored_product_quadratic(self):
        """Q7: (x - 2)*(x - 3) = 0 -> SOLVED, roots {2, 3}, discriminant 1."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x - 2)*(x - 3) = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(2))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(3))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q8_squared_linear_quadratic(self):
        """Q8: (x + 1)^2 = 0 -> SOLVED, root {-1}, discriminant 0."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x + 1)^2 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(2))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(1))
        self.assertEqual(len(resp.solution.roots), 1)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(-1))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q9_fractional_coefficients_quadratic(self):
        """Q9: (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> SOLVED, roots {1, 3/2}, discriminant 1/16."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(1/2)*x^2 - (5/4)*x + 3/4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.problem.a, RationalFraction(numerator=1, denominator=2))
        self.assertEqual(resp.problem.b, RationalFraction(numerator=-5, denominator=4))
        self.assertEqual(resp.problem.c, RationalFraction(numerator=3, denominator=4))
        self.assertEqual(resp.problem.discriminant.value, RationalFraction(numerator=1, denominator=16))
        self.assertEqual(len(resp.solution.roots), 2)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction(numerator=3, denominator=2))
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    # --- METHOD / COEFFICIENT ACCEPTANCE (C1 - C5) ---

    def test_c1_canonical_coefficients_default_selection(self):
        """C1: COEFFICIENTS 1, -5, 6, default selection -> SOLVED, standard formula."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id=None,
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.selected_method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp.solution.method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)

    def test_c2_canonical_coefficients_explicit_reduced_formula(self):
        """C2: COEFFICIENTS 1, -5, 6, explicit QUAD_FORMULA_REDUCED -> SOLVED with reduced trace."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_FORMULA_REDUCED",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.selected_method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp.solution.method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp.solution.trace.method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)

    def test_c3_canonical_coefficients_unknown_method_id(self):
        """C3: COEFFICIENTS 1, -5, 6, explicit QUAD_UNKNOWN_ID -> ERROR / METHOD_NOT_FOUND."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_UNKNOWN_ID",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.METHOD_NOT_FOUND)

    def test_c4_canonical_coefficients_non_applicable_method(self):
        """C4: COEFFICIENTS 2, 3, 4, explicit QUAD_VIETE_SPECIAL_SUM (non-applicable) -> ANALYZED / METHOD_NOT_APPLICABLE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(2),
                b=RationalFraction.from_int(3),
                c=RationalFraction.from_int(4),
            ),
            selected_method_id="QUAD_VIETE_SPECIAL_SUM",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.METHOD_NOT_APPLICABLE)
        self.assertEqual(resp.selected_method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertIsNone(resp.degenerate_solution)

    def test_c5_canonical_coefficients_unavailable_method(self):
        """C5: COEFFICIENTS 1, -5, 6, explicit QUAD_COMPLETE_SQUARE (applicable but unavailable) -> ANALYZED / METHOD_NOT_EXECUTABLE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_COMPLETE_SQUARE",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.METHOD_NOT_EXECUTABLE)
        self.assertEqual(resp.selected_method_id, "QUAD_COMPLETE_SQUARE")
        self.assertIsNone(resp.degenerate_solution)

    # --- DEGENERATE ACCEPTANCE (D1 - D4) ---

    def test_d1_degenerate_linear_raw_text(self):
        """D1: 2*x - 4 = 0 -> ANALYZED / DEGENERATE_EXACT_SOLUTION, LINEAR, root=2, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x - 4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)
        self.assertIsInstance(resp.problem, CanonicalDegenerateProblemView)
        self.assertEqual(resp.problem.classification, EquationClassificationType.LINEAR)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(0))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(2))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(-4))
        self.assertEqual(resp.available_methods, [])
        self.assertIsNone(resp.selected_method_id)
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(resp.degenerate_solution.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)
        self.assertEqual(resp.degenerate_solution.linear_root, RationalFraction.from_int(2))
        self.assertEqual(resp.degenerate_solution.final_answer_latex, "x = 2")
        self.assertEqual(resp.degenerate_solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_d2_degenerate_identity_raw_text(self):
        """D2: 0 = 0 -> ANALYZED / DEGENERATE_EXACT_SOLUTION, IDENTITY, S=R, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="0 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)
        self.assertEqual(resp.problem.classification, EquationClassificationType.IDENTITY)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNone(resp.selected_method_id)
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(resp.degenerate_solution.outcome, SolutionOutcome.INFINITE_REAL_SOLUTIONS)
        self.assertIsNone(resp.degenerate_solution.linear_root)
        self.assertEqual(resp.degenerate_solution.final_answer_latex, "S = \\mathbb{R}")
        self.assertEqual(resp.degenerate_solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_d3_degenerate_contradiction_raw_text(self):
        """D3: 1 = 0 -> ANALYZED / DEGENERATE_EXACT_SOLUTION, CONTRADICTION, S=empty, VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)
        self.assertEqual(resp.problem.classification, EquationClassificationType.CONTRADICTION)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNone(resp.selected_method_id)
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(resp.degenerate_solution.outcome, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION)
        self.assertIsNone(resp.degenerate_solution.linear_root)
        self.assertEqual(resp.degenerate_solution.final_answer_latex, "S = \\emptyset")
        self.assertEqual(resp.degenerate_solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_d4_degenerate_linear_canonical_coefficients(self):
        """D4: COEFFICIENTS a=0, b=2, c=-4 -> ANALYZED / DEGENERATE_EXACT_SOLUTION, root=2, VERIFIED_COMPLETE."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)
        self.assertEqual(resp.problem.classification, EquationClassificationType.LINEAR)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNone(resp.selected_method_id)
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(resp.degenerate_solution.linear_root, RationalFraction.from_int(2))
        self.assertEqual(resp.degenerate_solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    # --- ERROR / SCOPE ACCEPTANCE (E1 - E8) ---

    def test_e1_syntax_error(self):
        """E1: x^2 + = 0 -> ERROR / SYNTAX_ERROR."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.SYNTAX_ERROR)
        self.assertIsNotNone(resp.span)

    def test_e2_degree_out_of_scope_cubic(self):
        """E2: x^3 - 2*x + 1 = 0 -> ERROR / DEGREE_OUT_OF_SCOPE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^3 - 2*x + 1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_e3_degree_out_of_scope_intermediate_product(self):
        """E3: (x^2 + 1)*(x + 1) = 0 -> ERROR / DEGREE_OUT_OF_SCOPE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x^2 + 1)*(x + 1) = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_e4_unsupported_variable(self):
        """E4: y^2 - 4 = 0 -> ERROR / UNSUPPORTED_VARIABLE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="y^2 - 4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.UNSUPPORTED_VARIABLE)

    def test_e5_non_polynomial_input(self):
        """E5: 1/x = 0 -> ERROR / NON_POLYNOMIAL_INPUT."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1/x = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.NON_POLYNOMIAL_INPUT)

    def test_e6_division_by_zero(self):
        """E6: x^2 / 0 = 0 -> ERROR / DIVISION_BY_ZERO."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 / 0 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DIVISION_BY_ZERO)

    def test_e7_unsupported_syntax(self):
        """E7: sin(x) = 0 -> ERROR / UNSUPPORTED_SYNTAX."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="sin(x) = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.UNSUPPORTED_SYNTAX)

    def test_e8_implicit_multiplication_unsupported(self):
        """E8: 2x = 4 -> ERROR / IMPLICIT_MULTIPLICATION_UNSUPPORTED."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2x = 4"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED)

    # --- RESOURCE BOUNDS ACCEPTANCE (B1 - B6) ---

    def test_b1_max_length_256_passes(self):
        """B1: Exactly 256 characters -> DTO accepted and reaches service."""
        fixed = "x^2  = 0"
        needed = 256 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 256)

        req = SolveRequest(input_payload=RawEquationInput(raw_query=padded))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

    def test_b2_max_length_257_fails_at_dto_boundary(self):
        """B2: 257 characters -> ValidationError at RawEquationInput boundary (not ErrorResponse)."""
        fixed = "x^2  = 0"
        needed = 257 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 257)

        with self.assertRaises(ValidationError):
            RawEquationInput(raw_query=padded)

    def test_b3_max_depth_16_passes(self):
        """B3: Nesting depth = 16 -> Resource layer permits, solves successfully."""
        nested = "(" * 16 + "x^2 - 1" + ")" * 16 + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)

    def test_b4_max_depth_17_fails(self):
        """B4: Nesting depth = 17 -> ERROR / INPUT_LIMIT_EXCEEDED."""
        nested = "(" * 17 + "x^2 - 1" + ")" * 17 + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)

    def test_b5_max_tokens_64_passes(self):
        """B5: Exactly 64 non-EOF tokens -> Permitted and processed."""
        terms = ["+x"] + ["x"] * 30
        expr = " + ".join(terms) + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)

    def test_b6_max_tokens_65_fails(self):
        """B6: 65 non-EOF tokens -> ERROR / INPUT_LIMIT_EXCEEDED."""
        expr = " + ".join(["x"] * 32) + " = 0"
        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)


# ============================================================================
# 2. RAW / RAW-EQUIVALENT / COEFFICIENT SEMANTIC EQUIVALENCE META-TESTS
# ============================================================================

class TestSemanticEquivalenceAcceptance(unittest.TestCase):
    """Verifies that RAW, rearranged RAW, and COEFFICIENT intakes produce identical mathematical truth."""

    def test_raw_raw_equivalent_and_coefficients_parity(self):
        """RAW 'x^2 - 5*x + 6 = 0', RAW 'x^2 + 6 = 5*x', and COEFFICIENTS (1,-5,6) must match on all mathematical fields."""
        req_raw1 = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        req_raw2 = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 6 = 5*x"))
        req_coeff = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        resp_raw1 = solve_request(req_raw1)
        resp_raw2 = solve_request(req_raw2)
        resp_coeff = solve_request(req_coeff)

        self.assertIsInstance(resp_raw1, SolvedResponse)
        self.assertIsInstance(resp_raw2, SolvedResponse)
        self.assertIsInstance(resp_coeff, SolvedResponse)

        # 1. Exact Coefficients
        self.assertEqual(resp_raw1.problem.a, resp_coeff.problem.a)
        self.assertEqual(resp_raw1.problem.b, resp_coeff.problem.b)
        self.assertEqual(resp_raw1.problem.c, resp_coeff.problem.c)
        self.assertEqual(resp_raw2.problem.a, resp_coeff.problem.a)
        self.assertEqual(resp_raw2.problem.b, resp_coeff.problem.b)
        self.assertEqual(resp_raw2.problem.c, resp_coeff.problem.c)

        # 2. Classification & Discriminant
        self.assertEqual(resp_raw1.problem.classification, resp_coeff.problem.classification)
        self.assertEqual(resp_raw1.problem.discriminant, resp_coeff.problem.discriminant)
        self.assertEqual(resp_raw2.problem.discriminant, resp_coeff.problem.discriminant)

        # 3. Canonical Problem ID & Semantic Revision Hash
        self.assertEqual(resp_raw1.problem.problem_id, resp_coeff.problem.problem_id)
        self.assertEqual(resp_raw2.problem.problem_id, resp_coeff.problem.problem_id)
        self.assertEqual(resp_raw1.problem.semantic_revision_hash, resp_coeff.problem.semantic_revision_hash)
        self.assertEqual(resp_raw2.problem.semantic_revision_hash, resp_coeff.problem.semantic_revision_hash)

        # 4. 9 Available Methods Catalog Parity (all 11 fields)
        self.assertEqual(len(resp_raw1.available_methods), 9)
        self.assertEqual(len(resp_coeff.available_methods), 9)
        for m_raw, m_coeff in zip(resp_raw1.available_methods, resp_coeff.available_methods):
            self.assertEqual(m_raw.method_id, m_coeff.method_id)
            self.assertEqual(m_raw.title_vi, m_coeff.title_vi)
            self.assertEqual(m_raw.mathematical_applicability, m_coeff.mathematical_applicability)
            self.assertEqual(m_raw.support_status, m_coeff.support_status)
            self.assertEqual(m_raw.execution_availability, m_coeff.execution_availability)
            self.assertEqual(m_raw.pedagogical_recommendation, m_coeff.pedagogical_recommendation)
            self.assertEqual(m_raw.verification_capability, m_coeff.verification_capability)
            self.assertEqual(m_raw.reasons, m_coeff.reasons)
            self.assertEqual(m_raw.prerequisites, m_coeff.prerequisites)
            self.assertEqual(m_raw.pedagogical_priority, m_coeff.pedagogical_priority)
            self.assertEqual(m_raw.has_trace_available, m_coeff.has_trace_available)

        # 5. Selected Method, Solution Outcome & Exact Roots
        self.assertEqual(resp_raw1.selected_method_id, resp_coeff.selected_method_id)
        self.assertEqual(resp_raw2.selected_method_id, resp_coeff.selected_method_id)
        self.assertEqual(resp_raw1.solution.outcome, resp_coeff.solution.outcome)
        self.assertEqual(resp_raw1.solution.roots, resp_coeff.solution.roots)
        self.assertEqual(resp_raw2.solution.roots, resp_coeff.solution.roots)
        self.assertEqual(resp_raw1.solution.final_answer_latex, resp_coeff.solution.final_answer_latex)


# ============================================================================
# 3. METHOD-SWITCH REACTIVITY CONTRACT META-TESTS
# ============================================================================

class TestMethodSwitchReactivityContract(unittest.TestCase):
    """Verifies that switching solving methods preserves mathematical problem identity while updating trace strategy."""

    def test_method_switch_preserves_identity_and_updates_trace(self):
        """Switching from STANDARD to REDUCED formula maintains problem_id/hash/roots but changes trace."""
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

        resp_std = solve_request(req_standard)
        resp_red = solve_request(req_reduced)

        self.assertIsInstance(resp_std, SolvedResponse)
        self.assertIsInstance(resp_red, SolvedResponse)

        # Invariant Mathematical Identity
        self.assertEqual(resp_std.problem.problem_id, resp_red.problem.problem_id)
        self.assertEqual(resp_std.problem.semantic_revision_hash, resp_red.problem.semantic_revision_hash)
        self.assertEqual(resp_std.problem.a, resp_red.problem.a)
        self.assertEqual(resp_std.problem.b, resp_red.problem.b)
        self.assertEqual(resp_std.problem.c, resp_red.problem.c)
        self.assertEqual(resp_std.problem.discriminant, resp_red.problem.discriminant)
        self.assertEqual(resp_std.solution.roots, resp_red.solution.roots)
        self.assertEqual(resp_std.solution.outcome, resp_red.solution.outcome)

        # Distinct Presentation Strategy
        self.assertEqual(resp_std.selected_method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp_red.selected_method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp_std.solution.method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp_red.solution.method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp_std.solution.trace.method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp_red.solution.trace.method_id, "QUAD_FORMULA_REDUCED")
        self.assertNotEqual(resp_std.solution.trace.steps, resp_red.solution.trace.steps)


# ============================================================================
# 4. COEFFICIENT-EDIT REACTIVITY CONTRACT META-TESTS
# ============================================================================

class TestCoefficientEditReactivityContract(unittest.TestCase):
    """Verifies live coefficient mutation contract without lexer/parser involvement."""

    def test_coefficient_edit_alters_semantic_identity_and_solution_truth(self):
        """Mutating c from 6 to 7 produces a distinct problem_id, hash, discriminant, and solution."""
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
            resp_c6 = solve_request(req_c6)
            resp_c7 = solve_request(req_c7)
            # Zero parser invocation for direct coefficient intake
            mock_norm.assert_not_called()

        self.assertIsInstance(resp_c6, SolvedResponse)
        self.assertIsInstance(resp_c7, SolvedResponse)

        self.assertNotEqual(resp_c6.problem.problem_id, resp_c7.problem.problem_id)
        self.assertNotEqual(resp_c6.problem.semantic_revision_hash, resp_c7.problem.semantic_revision_hash)
        self.assertEqual(resp_c6.problem.discriminant.value, RationalFraction.from_int(1))
        self.assertEqual(resp_c7.problem.discriminant.value, RationalFraction.from_int(-3))
        self.assertEqual(resp_c6.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp_c7.solution.outcome, SolutionOutcome.NO_REAL_ROOTS)

    def test_coefficient_edit_quadratic_to_degenerate_transition(self):
        """Mutating a from 1 to 0 transitions from QUADRATIC to DEGENERATE without parser invocation."""
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
            resp_quad = solve_request(req_quad)
            resp_deg = solve_request(req_deg)
            mock_norm.assert_not_called()

        self.assertIsInstance(resp_quad, SolvedResponse)
        self.assertIsInstance(resp_deg, AnalyzedNoExecutionResponse)
        self.assertEqual(resp_quad.problem.problem_type, "QUADRATIC")
        self.assertEqual(resp_deg.problem.problem_type, "DEGENERATE")
        self.assertEqual(resp_deg.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)
        self.assertEqual(resp_deg.degenerate_solution.linear_root, RationalFraction.from_int(2))


# ============================================================================
# 5. ALL FOUR EXECUTABLE METHODS & UNAVAILABLE REJECTION META-TESTS
# ============================================================================

class TestAllExecutableAndUnavailableMethods(unittest.TestCase):
    """Verifies all 4 executable trace generators and the rejection of all 5 unavailable methods."""

    def test_quad_formula_standard_execution(self):
        """QUAD_FORMULA_STANDARD generates verified complete trace."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"),
            selected_method_id="QUAD_FORMULA_STANDARD",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertGreater(len(resp.solution.trace.steps), 0)

    def test_quad_formula_reduced_execution(self):
        """QUAD_FORMULA_REDUCED generates verified complete trace."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 4*x + 3 = 0"),
            selected_method_id="QUAD_FORMULA_REDUCED",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.method_id, "QUAD_FORMULA_REDUCED")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertGreater(len(resp.solution.trace.steps), 0)

    def test_quad_viete_special_sum_execution(self):
        """QUAD_VIETE_SPECIAL_SUM (a+b+c=0) generates verified complete trace."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 3*x + 2 = 0"),
            selected_method_id="QUAD_VIETE_SPECIAL_SUM",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(2))

    def test_quad_viete_special_dif_execution(self):
        """QUAD_VIETE_SPECIAL_DIF (a-b+c=0) generates verified complete trace."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 + 3*x + 2 = 0"),
            selected_method_id="QUAD_VIETE_SPECIAL_DIF",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.method_id, "QUAD_VIETE_SPECIAL_DIF")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(resp.solution.roots[0].rational_value, RationalFraction.from_int(-2))
        self.assertEqual(resp.solution.roots[1].rational_value, RationalFraction.from_int(-1))

    def test_all_unavailable_methods_cannot_be_executed(self):
        """All 5 UNAVAILABLE methods return ANALYZED_NO_EXECUTION / METHOD_NOT_EXECUTABLE."""
        unavailable_ids = [
            "QUAD_FACTORIZATION_Q",
            "QUAD_FACTORIZATION_R",
            "QUAD_COMPLETE_SQUARE",
            "QUAD_VIETE_SUM_PRODUCT",
            "QUAD_GRAPHICAL_ANALYSIS",
        ]
        for m_id in unavailable_ids:
            req = SolveRequest(
                input_payload=CanonicalCoefficientInput(
                    a=RationalFraction.from_int(1),
                    b=RationalFraction.from_int(-5),
                    c=RationalFraction.from_int(6),
                ),
                selected_method_id=m_id,
            )
            resp = solve_request(req)
            self.assertIsInstance(
                resp,
                AnalyzedNoExecutionResponse,
                f"Method {m_id} unexpectedly did not return AnalyzedNoExecutionResponse",
            )
            self.assertEqual(resp.reason_code, NoExecutionReasonCode.METHOD_NOT_EXECUTABLE)
            self.assertEqual(resp.selected_method_id, m_id)


# ============================================================================
# 6. DETERMINISTIC RESPONSE SEMANTICS META-TESTS
# ============================================================================

class TestDeterministicResponseSemantics(unittest.TestCase):
    """Verifies that solve_request produces 100% deterministic response snapshots."""

    def _normalize_snapshot(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively strip nondeterministic timestamps."""
        if isinstance(d, dict):
            return {
                k: self._normalize_snapshot(v)
                for k, v in d.items()
                if k not in ("verified_at_utc",)
            }
        elif isinstance(d, list):
            return [self._normalize_snapshot(v) for v in d]
        return d

    def test_repeated_runs_deterministic_snapshots(self):
        """Repeated solve_request calls produce identical semantic response snapshots."""
        queries = [
            RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"),   # Rational distinct
            RawEquationInput(raw_query="x^2 - 2 = 0"),         # Surd distinct
            RawEquationInput(raw_query="x^2 - 3*x + 2 = 0"),   # Viète special sum
            RawEquationInput(raw_query="2*x - 4 = 0"),         # Degenerate linear
        ]

        for inp in queries:
            req = SolveRequest(input_payload=inp)
            resp1 = solve_request(req)
            resp2 = solve_request(req)

            snap1 = self._normalize_snapshot(resp1.model_dump())
            snap2 = self._normalize_snapshot(resp2.model_dump())

            self.assertEqual(snap1, snap2)
            self.assertEqual(
                resp1.problem.semantic_revision_hash,
                resp2.problem.semantic_revision_hash,
            )
            self.assertEqual(resp1.problem.problem_id, resp2.problem.problem_id)


# ============================================================================
# 7. SERIALIZATION ROUND-TRIP META-TESTS
# ============================================================================

class TestSerializationRoundTrip(unittest.TestCase):
    """Verifies complete Pydantic v2 serialization, JSON compatibility, and discriminator preservation."""

    def test_solved_response_round_trip(self):
        """SolvedResponse round-trips through model_dump and JSON TypeAdapter."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        dumped = resp.model_dump()
        adapter = TypeAdapter(SolveResponseUnion)
        restored = adapter.validate_python(dumped)

        self.assertIsInstance(restored, SolvedResponse)
        self.assertEqual(restored.response_status, "SOLVED")
        self.assertEqual(restored.problem.problem_type, "QUADRATIC")
        self.assertEqual(restored.problem.semantic_revision_hash, resp.problem.semantic_revision_hash)

        # JSON String round-trip
        json_str = resp.model_dump_json()
        parsed_json = json.loads(json_str)
        self.assertEqual(parsed_json["response_status"], "SOLVED")
        self.assertEqual(parsed_json["problem"]["problem_type"], "QUADRATIC")
        restored_from_json = adapter.validate_json(json_str)
        self.assertIsInstance(restored_from_json, SolvedResponse)

    def test_analyzed_response_round_trip(self):
        """AnalyzedNoExecutionResponse round-trips cleanly through JSON."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x - 4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)

        dumped = resp.model_dump()
        adapter = TypeAdapter(SolveResponseUnion)
        restored = adapter.validate_python(dumped)

        self.assertIsInstance(restored, AnalyzedNoExecutionResponse)
        self.assertEqual(restored.response_status, "ANALYZED_NO_EXECUTION")
        self.assertEqual(restored.problem.problem_type, "DEGENERATE")
        self.assertEqual(restored.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION)

    def test_error_response_round_trip(self):
        """ErrorResponse round-trips cleanly through JSON."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)

        dumped = resp.model_dump()
        adapter = TypeAdapter(SolveResponseUnion)
        restored = adapter.validate_python(dumped)

        self.assertIsInstance(restored, ErrorResponse)
        self.assertEqual(restored.response_status, "ERROR")
        self.assertEqual(restored.error_code, ApplicationErrorCode.SYNTAX_ERROR)


# ============================================================================
# 8. STATE-MACHINE IMPOSSIBILITY META-TESTS
# ============================================================================

class TestStateMachineImpossibility(unittest.TestCase):
    """Adversarial tests proving impossible state combinations are rejected by Pydantic validators."""

    def test_solved_response_rejects_unverified_certificate(self):
        """SolvedResponse rejects certificate with outcome != VERIFIED_COMPLETE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        tampered_cert = VerificationCertificate(
            certificate_id="cert_bad",
            problem_hash="hash_bad",
            outcome=VerificationOutcome.VERIFICATION_FAILED,
            integrity_fingerprint="fp_bad",
            verified_at_utc=datetime.utcnow(),
        )
        tampered_sol = resp.solution.model_copy(update={"certificate": tampered_cert})

        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id=resp.selected_method_id,
                solution=tampered_sol,
            )

    def test_solved_response_rejects_mismatched_method_id(self):
        """SolvedResponse rejects selected_method_id != solution.method_id."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_REDUCED",
                solution=resp.solution,  # method_id == QUAD_FORMULA_STANDARD
            )

    def test_analyzed_rejects_applicable_method_as_not_applicable(self):
        """AnalyzedNoExecutionResponse rejects METHOD_NOT_APPLICABLE when method is actually APPLICABLE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                reason_code=NoExecutionReasonCode.METHOD_NOT_APPLICABLE,
                analysis_message_vi="Test",
            )

    def test_analyzed_rejects_available_method_as_not_executable(self):
        """AnalyzedNoExecutionResponse rejects METHOD_NOT_EXECUTABLE when method is AVAILABLE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Test",
            )

    def test_analyzed_rejects_degenerate_solution_on_quadratic_problem(self):
        """AnalyzedNoExecutionResponse rejects DEGENERATE_EXACT_SOLUTION on CanonicalQuadraticProblemView."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        cert_d = VerificationCertificate(
            certificate_id="cert_d",
            problem_hash="hash_d",
            outcome=VerificationOutcome.VERIFIED_COMPLETE,
            integrity_fingerprint="fp_d",
        )
        deg_sol = DegenerateSolutionView(
            classification=EquationClassificationType.LINEAR,
            outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
            linear_root=RationalFraction.from_int(2),
            final_answer_latex="x = 2",
            certificate=cert_d,
        )

        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,  # CanonicalQuadraticProblemView
                available_methods=[],
                selected_method_id=None,
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )


# ============================================================================
# 9. ERROR SANITIZATION ACCEPTANCE META-TESTS
# ============================================================================

class TestErrorSanitizationAcceptance(unittest.TestCase):
    """Verifies that injected secret sentinels in internal components never leak to client responses."""

    def test_normalizer_exception_sanitization(self):
        """Internal normalizer exception does not leak secret sentinel."""
        secret = "SECRET_NORMALIZER_INTRUSION_TOKEN"
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))

        with patch("mke_product.application.orchestrator.normalize_raw_equation") as mock_norm:
            mock_norm.side_effect = RuntimeError(secret)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.NORMALIZATION_ERROR)
            self.assertNotIn(secret, resp.message_vi)
            self.assertNotIn(secret, resp.message_en)
            self.assertNotIn(secret, str(resp.details))

    def test_quadratic_verifier_exception_sanitization(self):
        """Host quadratic verifier exception fails closed as VERIFICATION_FAILED without sentinel leak."""
        secret = "SECRET_QUADRATIC_VERIFIER_TOKEN"
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))

        with patch("mke_product.domain.verifier.HostIndependentVerifier.verify_quadratic_solution") as mock_ver:
            mock_ver.side_effect = RuntimeError(secret)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.VERIFICATION_FAILED)
            self.assertNotIn(secret, resp.message_vi)
            self.assertNotIn(secret, resp.message_en)
            self.assertNotIn(secret, str(resp.details))

    def test_degenerate_verifier_exception_sanitization(self):
        """Degenerate verifier exception fails closed as VERIFICATION_FAILED without sentinel leak."""
        secret = "SECRET_DEGENERATE_VERIFIER_TOKEN"
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )

        with patch("mke_product.application.orchestrator.verify_degenerate_solution") as mock_deg:
            mock_deg.side_effect = RuntimeError(secret)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.VERIFICATION_FAILED)
            self.assertNotIn(secret, resp.message_vi)
            self.assertNotIn(secret, resp.message_en)
            self.assertNotIn(secret, str(resp.details))

    def test_trace_generator_generic_exception_sanitization(self):
        """Generic trace generation exception fails closed as METHOD_EXECUTION_FAILED without sentinel leak."""
        secret = "SECRET_TRACE_GENERATOR_TOKEN"
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        with patch("mke_product.application.orchestrator.generate_solution_trace") as mock_tr:
            mock_tr.side_effect = TraceGenerationError(secret)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.METHOD_EXECUTION_FAILED)
            self.assertNotIn(secret, resp.message_vi)
            self.assertNotIn(secret, resp.message_en)
            self.assertNotIn(secret, str(resp.details))


# ============================================================================
# 10. DOMAIN IR GATE ACCEPTANCE META-TESTS
# ============================================================================

class TestDomainIRGateAcceptance(unittest.TestCase):
    """Verifies that QuadraticProblemIR and DegenerateEquationIR act as mandatory authoritative gates."""

    def test_quadratic_problem_ir_gate_enforcement(self):
        """Injected validation failure in QuadraticProblemIR yields DOMAIN_CONTRACT_ERROR."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))

        with patch("mke_product.application.orchestrator.QuadraticProblemIR") as mock_ir:
            mock_ir.side_effect = ValueError("Injected Domain IR contract violation")
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.DOMAIN_CONTRACT_ERROR)

    def test_degenerate_equation_ir_gate_enforcement(self):
        """Injected validation failure in DegenerateEquationIR yields DOMAIN_CONTRACT_ERROR."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x - 4 = 0"))

        with patch("mke_product.application.orchestrator.DegenerateEquationIR") as mock_deg_ir:
            mock_deg_ir.side_effect = ValueError("Injected Degenerate IR contract violation")
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(resp.error_code, ApplicationErrorCode.DOMAIN_CONTRACT_ERROR)


# ============================================================================
# 11. METHOD CATALOG 9-OPTION ORDER & 11-FIELD PARITY META-TESTS
# ============================================================================

class TestMethodCatalogParity(unittest.TestCase):
    """Verifies exact 9-method catalog presentation order and 11-field parity with domain truth."""

    def test_full_9_method_catalog_parity(self):
        """Every SolvedResponse available_methods list matches MethodRegistry and TRACE_GENERATORS across all 11 fields."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        registry = MethodRegistry()
        all_defs = registry.list_all()
        assessments = registry.assess_quadratic(Rational(1, 1), Rational(-5, 1), Rational(6, 1))
        assess_dict = {a.method_id: a for a in assessments}

        self.assertEqual(len(resp.available_methods), 9)
        self.assertEqual(len(all_defs), 9)

        seen_ids = set()
        for opt_view, m_def in zip(resp.available_methods, all_defs):
            self.assertNotIn(opt_view.method_id, seen_ids)
            seen_ids.add(opt_view.method_id)

            assess = assess_dict[opt_view.method_id]

            # All 11 orthogonal fields
            self.assertEqual(opt_view.method_id, m_def.method_id)
            self.assertEqual(opt_view.title_vi, m_def.title_vi)
            self.assertEqual(opt_view.mathematical_applicability, assess.mathematical_applicability)
            self.assertEqual(opt_view.support_status, assess.support_status)
            self.assertEqual(opt_view.execution_availability, assess.execution_availability)
            self.assertEqual(opt_view.pedagogical_recommendation, assess.pedagogical_recommendation)
            self.assertEqual(opt_view.verification_capability, assess.verification_capability)
            self.assertEqual(opt_view.reasons, assess.reasons)
            self.assertEqual(opt_view.prerequisites, assess.prerequisite_status)
            self.assertEqual(opt_view.pedagogical_priority, assess.pedagogical_priority)
            self.assertEqual(opt_view.has_trace_available, opt_view.method_id in TRACE_GENERATORS)


if __name__ == "__main__":
    unittest.main()
