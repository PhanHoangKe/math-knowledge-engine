"""MKE MVP V1 — Comprehensive Test Suite for S1-04-R2 Application Orchestrator & Discriminated DTOs.

Validates:
1. End-to-end Pure Python Application Service pipeline (solve_request).
2. Authoritative Domain IR Gate (QuadraticProblemIR, DegenerateEquationIR).
3. RAW_TEXT vs COEFFICIENTS intake invariance & semantic identity equivalence.
4. Clean parseable canonical source string formatting.
5. Strict single method-selection authority and resolution policy with stable insertion-order tie-breaking.
6. Comprehensive 32-case Acceptance Matrix (Q1-Q9, C1-C5, D1-D4, E1-E8, B1-B6).
7. Degenerate equation fail-closed exact verification & discriminated response modeling.
8. Multi-method orthogonal assessment mapping & trace execution with fail-closed contract mapping.
9. Host independent verification and tamper-evident certificate attachment.
10. Strict client-facing error message sanitization (zero internal exception leakage).
11. Pydantic v2 discriminated union cross-field validators and complete adversarial invariant rejection.
"""

from datetime import datetime
import unittest
from unittest.mock import patch
from pydantic import TypeAdapter, ValidationError

from mke_product.application.dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    CanonicalDegenerateProblemView,
    CanonicalProblemUnion,
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
from mke_product.application.orchestrator import (
    format_canonical_source_equation,
    format_equation_latex,
    solve_request,
)
from mke_product.application.traces.base import (
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
)
from mke_product.core.rational import Rational
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    MethodAssessment,
    PedagogicalRecommendation,
    PrerequisiteStatus,
    ProblemCategory,
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
from mke_product.parser.errors import Span


class TestApplicationOrchestratorS1(unittest.TestCase):
    """Full test suite for MKE MVP V1 Application Orchestrator & Discriminated DTOs."""

    # ========================================================================
    # 1. CANONICAL SOURCE FORMATTER TESTS
    # ========================================================================

    def test_canonical_source_formatter_exact_strings(self):
        """Verify deterministic clean parseable formatting across canonical test fixtures."""
        # a=1, b=-5, c=6 -> x^2 - 5*x + 6 = 0
        s1 = format_canonical_source_equation(
            RationalFraction.from_int(1),
            RationalFraction.from_int(-5),
            RationalFraction.from_int(6),
        )
        self.assertEqual(s1, "x^2 - 5*x + 6 = 0")

        # a=-1, b=3, c=-2 -> -x^2 + 3*x - 2 = 0
        s2 = format_canonical_source_equation(
            RationalFraction.from_int(-1),
            RationalFraction.from_int(3),
            RationalFraction.from_int(-2),
        )
        self.assertEqual(s2, "-x^2 + 3*x - 2 = 0")

        # a=0, b=2, c=-4 -> 2*x - 4 = 0
        s3 = format_canonical_source_equation(
            RationalFraction.from_int(0),
            RationalFraction.from_int(2),
            RationalFraction.from_int(-4),
        )
        self.assertEqual(s3, "2*x - 4 = 0")

        # a=0, b=0, c=0 -> 0 = 0
        s4 = format_canonical_source_equation(
            RationalFraction.from_int(0),
            RationalFraction.from_int(0),
            RationalFraction.from_int(0),
        )
        self.assertEqual(s4, "0 = 0")

        # a=0, b=0, c=1 -> 1 = 0
        s5 = format_canonical_source_equation(
            RationalFraction.from_int(0),
            RationalFraction.from_int(0),
            RationalFraction.from_int(1),
        )
        self.assertEqual(s5, "1 = 0")

        # a=1/2, b=-5/4, c=3/4 -> (1/2)*x^2 - (5/4)*x + 3/4 = 0
        s6 = format_canonical_source_equation(
            RationalFraction(numerator=1, denominator=2),
            RationalFraction(numerator=-5, denominator=4),
            RationalFraction(numerator=3, denominator=4),
        )
        self.assertEqual(s6, "(1/2)*x^2 - (5/4)*x + 3/4 = 0")

    # ========================================================================
    # 2. INTAKE EQUIVALENCE & SEMANTIC IDENTITY INVARIANCE
    # ========================================================================

    def test_strong_intake_equivalence_raw_vs_coefficients(self):
        """Verify complete equality of problem views, assessments, and solutions across intake modes."""
        req_raw = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )
        req_coeff = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )
        req_raw_unreduced = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 + 6 = 5*x")
        )

        resp_raw = solve_request(req_raw)
        resp_coeff = solve_request(req_coeff)
        resp_unred = solve_request(req_raw_unreduced)

        self.assertIsInstance(resp_raw, SolvedResponse)
        self.assertIsInstance(resp_coeff, SolvedResponse)
        self.assertIsInstance(resp_unred, SolvedResponse)

        # Mathematical coefficients equality
        self.assertEqual(resp_raw.problem.a, resp_coeff.problem.a)
        self.assertEqual(resp_raw.problem.b, resp_coeff.problem.b)
        self.assertEqual(resp_raw.problem.c, resp_coeff.problem.c)
        self.assertEqual(resp_raw.problem.discriminant, resp_coeff.problem.discriminant)
        self.assertEqual(resp_raw.problem.classification, resp_coeff.problem.classification)

        # Semantic revision hash & deterministic problem_id equality
        self.assertEqual(
            resp_raw.problem.semantic_revision_hash,
            resp_coeff.problem.semantic_revision_hash,
        )
        self.assertEqual(
            resp_raw.problem.semantic_revision_hash,
            resp_unred.problem.semantic_revision_hash,
        )
        self.assertEqual(resp_raw.problem.problem_id, resp_coeff.problem.problem_id)
        self.assertEqual(resp_raw.problem.problem_id, resp_unred.problem.problem_id)

        # Method assessment catalog equality (all 11 fields for every method)
        self.assertEqual(len(resp_raw.available_methods), len(resp_coeff.available_methods))
        for m_raw, m_coeff in zip(resp_raw.available_methods, resp_coeff.available_methods):
            self.assertEqual(m_raw.method_id, m_coeff.method_id)
            self.assertEqual(m_raw.title_vi, m_coeff.title_vi)
            self.assertEqual(m_raw.mathematical_applicability, m_coeff.mathematical_applicability)
            self.assertEqual(m_raw.support_status, m_coeff.support_status)
            self.assertEqual(m_raw.execution_availability, m_coeff.execution_availability)
            self.assertEqual(m_raw.pedagogical_recommendation, m_coeff.pedagogical_recommendation)
            self.assertEqual(m_raw.verification_capability, m_coeff.verification_capability)
            self.assertEqual(m_raw.reasons, m_coeff.reasons)
            self.assertEqual(m_raw.prerequisites, m_coeff.prerequisites)
            self.assertEqual(m_raw.has_trace_available, m_coeff.has_trace_available)
            self.assertEqual(m_raw.pedagogical_priority, m_coeff.pedagogical_priority)

        # Solution equality
        self.assertEqual(resp_raw.selected_method_id, resp_coeff.selected_method_id)
        self.assertEqual(resp_raw.solution.outcome, resp_coeff.solution.outcome)
        self.assertEqual(resp_raw.solution.roots, resp_coeff.solution.roots)
        self.assertEqual(
            resp_raw.solution.final_answer_latex, resp_coeff.solution.final_answer_latex
        )

    def test_coefficients_mode_bypasses_parser(self):
        """Verify that COEFFICIENTS input mode executes without invoking the lexer/parser."""
        req_coeff = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        with patch(
            "mke_product.application.orchestrator.normalize_raw_equation"
        ) as mock_norm:
            resp = solve_request(req_coeff)
            mock_norm.assert_not_called()
            self.assertIsInstance(resp, SolvedResponse)

    # ========================================================================
    # 3. ACCEPTANCE MATRIX: QUADRATIC RAW_TEXT (Q1 - Q9)
    # ========================================================================

    def test_q1_standard_two_distinct_roots(self):
        """Q1: x^2 - 5*x + 6 = 0 -> Two distinct real roots {2, 3}."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.classification, EquationClassificationType.QUADRATIC)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.solution.final_answer_latex, "S = \\left\\{ 2, 3 \\right\\}")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(len(resp.available_methods), 9)

    def test_q2_irrational_surd_roots(self):
        """Q2: x^2 - 2 = 0 -> Two distinct surd roots {-sqrt(2), sqrt(2)}."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 2 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(resp.solution.roots[0].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(
            resp.solution.final_answer_latex,
            "S = \\left\\{ -\\sqrt{2}, \\sqrt{2} \\right\\}",
        )
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q3_repeated_root(self):
        """Q3: x^2 - 2*x + 1 = 0 -> One repeated real root {1}."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 2*x + 1 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(resp.solution.final_answer_latex, "x = 1")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q4_no_real_roots(self):
        """Q4: x^2 + 1 = 0 -> No real roots (S = empty)."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.NO_REAL_ROOTS)
        self.assertEqual(resp.solution.final_answer_latex, "S = \\emptyset")
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q5_non_monic_quadratic(self):
        """Q5: 2*x^2 - 5*x + 2 = 0 -> Two distinct roots {1/2, 2}."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="2*x^2 - 5*x + 2 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(
            resp.solution.final_answer_latex,
            "S = \\left\\{ \\frac{1}{2}, 2 \\right\\}",
        )
        self.assertEqual(resp.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_q6_unreduced_equation(self):
        """Q6: x^2 + 6 = 5*x -> Normalizes to x^2 - 5*x + 6 = 0 -> roots {2, 3}."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + 6 = 5*x"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(resp.solution.final_answer_latex, "S = \\left\\{ 2, 3 \\right\\}")

    def test_q7_factored_product_equation(self):
        """Q7: (x - 2)*(x - 3) = 0 -> Normalizes to x^2 - 5*x + 6 = 0 -> roots {2, 3}."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="(x - 2)*(x - 3) = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(-5))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(6))
        self.assertEqual(resp.solution.final_answer_latex, "S = \\left\\{ 2, 3 \\right\\}")

    def test_q8_squared_binomial_equation(self):
        """Q8: (x + 1)^2 = 0 -> Normalizes to x^2 + 2*x + 1 = 0 -> repeated root {-1}."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="(x + 1)^2 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.a, RationalFraction.from_int(1))
        self.assertEqual(resp.problem.b, RationalFraction.from_int(2))
        self.assertEqual(resp.problem.c, RationalFraction.from_int(1))
        self.assertEqual(resp.solution.final_answer_latex, "x = -1")

    def test_q9_fractional_coefficients(self):
        """Q9: (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> Roots {1, 3/2}."""
        req = SolveRequest(
            input_payload=RawEquationInput(
                raw_query="(1/2)*x^2 - (5/4)*x + 3/4 = 0"
            )
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.problem.a, RationalFraction(numerator=1, denominator=2))
        self.assertEqual(resp.problem.b, RationalFraction(numerator=-5, denominator=4))
        self.assertEqual(resp.problem.c, RationalFraction(numerator=3, denominator=4))
        self.assertEqual(
            resp.solution.final_answer_latex,
            "S = \\left\\{ 1, \\frac{3}{2} \\right\\}",
        )

    # ========================================================================
    # 4. ACCEPTANCE MATRIX: DIRECT COEFFICIENTS & METHOD SWITCHING (C1 - C5)
    # ========================================================================

    def test_c1_direct_coefficients_default_method(self):
        """C1: a=1, b=-5, c=6, selected_method_id=None -> Solved via QUAD_FORMULA_STANDARD."""
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

    def test_c2_method_switch_reduced_formula(self):
        """C2: a=1, b=-5, c=6, selected_method_id='QUAD_FORMULA_REDUCED' -> Solved via QUAD_FORMULA_REDUCED."""
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

    def test_c3_method_switch_unknown_method_id(self):
        """C3: a=1, b=-5, c=6, selected_method_id='QUAD_UNKNOWN_ID' -> ErrorResponse(METHOD_NOT_FOUND)."""
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
        self.assertEqual(resp.details.get("requested_method_id"), "QUAD_UNKNOWN_ID")

    def test_c4_method_switch_not_applicable_method(self):
        """C4: a=1, b=-5, c=6, selected_method_id='QUAD_VIETE_SPECIAL_SUM' -> AnalyzedNoExecutionResponse(METHOD_NOT_APPLICABLE)."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_VIETE_SPECIAL_SUM",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(resp.reason_code, NoExecutionReasonCode.METHOD_NOT_APPLICABLE)
        self.assertEqual(resp.selected_method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertIn("không áp dụng được", resp.analysis_message_vi)

    def test_c5_method_switch_unavailable_method(self):
        """C5: a=1, b=-5, c=6, selected_method_id='QUAD_COMPLETE_SQUARE' -> AnalyzedNoExecutionResponse(METHOD_NOT_EXECUTABLE)."""
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
        self.assertIn("chưa hỗ trợ", resp.analysis_message_vi)

    # ========================================================================
    # 5. ACCEPTANCE MATRIX: DEGENERATE EQUATIONS (D1 - D4)
    # ========================================================================

    def test_d1_degenerate_linear_raw_text(self):
        """D1: 2*x - 4 = 0 -> AnalyzedNoExecutionResponse with LINEAR exact solution {2}."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2*x - 4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )
        self.assertIsInstance(resp.problem, CanonicalDegenerateProblemView)
        self.assertEqual(
            resp.problem.classification, EquationClassificationType.LINEAR
        )
        self.assertIsNone(resp.selected_method_id)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(
            resp.degenerate_solution.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT
        )
        self.assertEqual(
            resp.degenerate_solution.linear_root, RationalFraction.from_int(2)
        )
        self.assertEqual(resp.degenerate_solution.final_answer_latex, "x = 2")
        self.assertEqual(
            resp.degenerate_solution.certificate.outcome,
            VerificationOutcome.VERIFIED_COMPLETE,
        )

    def test_d2_degenerate_identity_raw_text(self):
        """D2: 0 = 0 -> AnalyzedNoExecutionResponse with IDENTITY infinite solutions."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="0 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )
        self.assertEqual(
            resp.problem.classification, EquationClassificationType.IDENTITY
        )
        self.assertIsNone(resp.selected_method_id)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(
            resp.degenerate_solution.outcome, SolutionOutcome.INFINITE_REAL_SOLUTIONS
        )
        self.assertIsNone(resp.degenerate_solution.linear_root)
        self.assertEqual(
            resp.degenerate_solution.final_answer_latex, "S = \\mathbb{R}"
        )
        self.assertEqual(
            resp.degenerate_solution.certificate.outcome,
            VerificationOutcome.VERIFIED_COMPLETE,
        )

    def test_d3_degenerate_contradiction_raw_text(self):
        """D3: 1 = 0 -> AnalyzedNoExecutionResponse with CONTRADICTION no solutions."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )
        self.assertEqual(
            resp.problem.classification, EquationClassificationType.CONTRADICTION
        )
        self.assertIsNone(resp.selected_method_id)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(
            resp.degenerate_solution.outcome,
            SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
        )
        self.assertIsNone(resp.degenerate_solution.linear_root)
        self.assertEqual(
            resp.degenerate_solution.final_answer_latex, "S = \\emptyset"
        )
        self.assertEqual(
            resp.degenerate_solution.certificate.outcome,
            VerificationOutcome.VERIFIED_COMPLETE,
        )

    def test_d4_degenerate_linear_coefficients_mode(self):
        """D4: a=0, b=2, c=-4 -> Degenerate linear root x=2 via COEFFICIENTS mode."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )
        self.assertIsNone(resp.selected_method_id)
        self.assertEqual(resp.available_methods, [])
        self.assertEqual(
            resp.degenerate_solution.linear_root, RationalFraction.from_int(2)
        )

    def test_degenerate_ignores_explicit_selected_method_id(self):
        """Degenerate equation (a=0) does not execute or retain requested quadratic method."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            ),
            selected_method_id="QUAD_FORMULA_STANDARD",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )
        self.assertIsNone(resp.selected_method_id)
        self.assertEqual(resp.available_methods, [])
        self.assertIsNotNone(resp.degenerate_solution)
        self.assertEqual(
            resp.degenerate_solution.linear_root, RationalFraction.from_int(2)
        )

    def test_degenerate_verification_exception_fails_closed(self):
        """If degenerate verification raises an exception, return ErrorResponse(VERIFICATION_FAILED) without leaking strings."""
        secret_sentinel = "SECRET_DEGENERATE_SENTINEL_TOKEN"
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
            )
        )

        with patch(
            "mke_product.application.orchestrator.verify_degenerate_solution"
        ) as mock_deg_ver:
            mock_deg_ver.side_effect = RuntimeError(secret_sentinel)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.VERIFICATION_FAILED
            )
            # Ensure sentinel is strictly absent from messages and details
            self.assertNotIn(secret_sentinel, resp.message_vi)
            self.assertNotIn(secret_sentinel, resp.message_en)
            self.assertNotIn(secret_sentinel, str(resp.details))

    # ========================================================================
    # 6. ACCEPTANCE MATRIX: ERROR / SCOPE CASES (E1 - E8)
    # ========================================================================

    def test_e1_syntax_error(self):
        """E1: x^2 + = 0 -> SYNTAX_ERROR."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.SYNTAX_ERROR)
        self.assertIsNotNone(resp.span)

    def test_e2_degree_out_of_scope_cubic_literal(self):
        """E2: x^3 - 2*x + 1 = 0 -> DEGREE_OUT_OF_SCOPE."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^3 - 2*x + 1 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_e3_degree_out_of_scope_intermediate_product(self):
        """E3: (x^2 + 1)*(x + 1) = 0 -> DEGREE_OUT_OF_SCOPE."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="(x^2 + 1)*(x + 1) = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_e4_unsupported_variable(self):
        """E4: y^2 - 4 = 0 -> UNSUPPORTED_VARIABLE."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="y^2 - 4 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.UNSUPPORTED_VARIABLE)

    def test_e5_non_polynomial_input(self):
        """E5: 1/x = 0 -> NON_POLYNOMIAL_INPUT."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="1/x = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.NON_POLYNOMIAL_INPUT)

    def test_e6_division_by_zero(self):
        """E6: x^2 / 0 = 0 -> DIVISION_BY_ZERO."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 / 0 = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.DIVISION_BY_ZERO)

    def test_e7_unsupported_transcendental_syntax(self):
        """E7: sin(x) = 0 -> UNSUPPORTED_SYNTAX."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="sin(x) = 0"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.UNSUPPORTED_SYNTAX)

    def test_e8_implicit_multiplication_unsupported(self):
        """E8: 2x = 4 -> IMPLICIT_MULTIPLICATION_UNSUPPORTED."""
        req = SolveRequest(input_payload=RawEquationInput(raw_query="2x = 4"))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(
            resp.error_code, ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED
        )

    # ========================================================================
    # 7. ACCEPTANCE MATRIX: RESOURCE BOUNDS (B1 - B6)
    # ========================================================================

    def test_b1_max_length_256_passes(self):
        """B1: Exactly 256 characters -> Passes into orchestrator."""
        fixed = "x^2  = 0"
        needed = 256 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 256)

        req = SolveRequest(input_payload=RawEquationInput(raw_query=padded))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

    def test_b2_max_length_257_fails_at_dto_boundary(self):
        """B2: 257 characters -> ValidationError at Request DTO boundary."""
        fixed = "x^2  = 0"
        needed = 257 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 257)

        # RawEquationInput validates max_length <= 256 at model boundary
        with self.assertRaises(ValidationError):
            RawEquationInput(raw_query=padded)

    def test_b3_max_depth_16_passes(self):
        """B3: Nesting depth = 16 -> Passes."""
        nested = "(" * 16 + "x^2 - 1" + ")" * 16 + " = 0"

        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        self.assertEqual(resp.solution.outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)

    def test_b4_max_depth_17_fails(self):
        """B4: Nesting depth = 17 -> INPUT_LIMIT_EXCEEDED."""
        nested = "(" * 17 + "x^2 - 1" + ")" * 17 + " = 0"

        req = SolveRequest(input_payload=RawEquationInput(raw_query=nested))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)

    def test_b5_max_tokens_64_passes(self):
        """B5: Exactly 64 non-EOF tokens -> Passes."""
        terms = ["+x"] + ["x"] * 30
        expr = " + ".join(terms) + " = 0"

        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)
        self.assertEqual(
            resp.reason_code, NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION
        )

    def test_b6_max_tokens_65_fails(self):
        """B6: 65 non-EOF tokens -> INPUT_LIMIT_EXCEEDED."""
        expr = " + ".join(["x"] * 32) + " = 0"

        req = SolveRequest(input_payload=RawEquationInput(raw_query=expr))
        resp = solve_request(req)
        self.assertIsInstance(resp, ErrorResponse)
        self.assertEqual(resp.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)

    # ========================================================================
    # 8. METHOD SELECTION & CATALOG CONSISTENCY TESTS
    # ========================================================================

    def test_special_viete_default_selection(self):
        """Default method selection chooses QUAD_VIETE_SPECIAL_SUM when a+b+c=0 (priority 1)."""
        # x^2 - 3*x + 2 = 0 -> a=1, b=-3, c=2 -> a+b+c = 0
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 3*x + 2 = 0"),
            selected_method_id=None,
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)
        # QUAD_VIETE_SPECIAL_SUM has priority 1, whereas standard formula has priority 2
        self.assertEqual(resp.selected_method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertEqual(resp.solution.method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertEqual(resp.solution.final_answer_latex, "S = \\left\\{ 1, 2 \\right\\}")

    def test_stable_insertion_order_tie_break(self):
        """When multiple candidates share the same pedagogical_priority, stable sort preserves registry order."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id=None,
        )

        with patch("mke_product.domain.registry.MethodRegistry.assess_quadratic") as mock_assess:
            # Create two synthetic assessments with identical pedagogical_priority = 1
            assessments = [
                MethodAssessment(
                    method_id="QUAD_FORMULA_STANDARD",
                    problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                    mathematical_applicability=MathematicalApplicability.APPLICABLE,
                    support_status=SupportStatus.SUPPORTED,
                    execution_availability=ExecutionAvailability.AVAILABLE,
                    pedagogical_recommendation=PedagogicalRecommendation.RECOMMENDED,
                    verification_capability=VerificationCapability.HOST_VERIFIABLE,
                    pedagogical_priority=1,
                ),
                MethodAssessment(
                    method_id="QUAD_FORMULA_REDUCED",
                    problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                    mathematical_applicability=MathematicalApplicability.APPLICABLE,
                    support_status=SupportStatus.SUPPORTED,
                    execution_availability=ExecutionAvailability.AVAILABLE,
                    pedagogical_recommendation=PedagogicalRecommendation.RECOMMENDED,
                    verification_capability=VerificationCapability.HOST_VERIFIABLE,
                    pedagogical_priority=1,
                ),
            ]
            mock_assess.return_value = assessments

            resp = solve_request(req)
            self.assertIsInstance(resp, SolvedResponse)
            # First item in insertion order MUST win tie-break
            self.assertEqual(resp.selected_method_id, "QUAD_FORMULA_STANDARD")

    def test_full_9_method_option_catalog_order_and_consistency(self):
        """Method catalog in SolvedResponse matches MethodRegistry definition order and all 11 fields exactly."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        registry = MethodRegistry()
        all_defs = registry.list_all()
        assessments = registry.assess_quadratic(Rational(1, 1), Rational(-5, 1), Rational(6, 1))
        assess_dict = {a.method_id: a for a in assessments}

        self.assertEqual(len(resp.available_methods), 9)
        self.assertEqual(len(all_defs), 9)
        seen_ids = set()

        from mke_product.application.traces import TRACE_GENERATORS

        for option_view, method_def in zip(resp.available_methods, all_defs):
            self.assertNotIn(option_view.method_id, seen_ids)
            seen_ids.add(option_view.method_id)

            assess = assess_dict[option_view.method_id]

            # Field-by-field check across definition and assessment
            self.assertEqual(option_view.method_id, method_def.method_id)
            self.assertEqual(option_view.title_vi, method_def.title_vi)
            self.assertEqual(option_view.mathematical_applicability, assess.mathematical_applicability)
            self.assertEqual(option_view.support_status, assess.support_status)
            self.assertEqual(option_view.execution_availability, assess.execution_availability)
            self.assertEqual(option_view.pedagogical_recommendation, assess.pedagogical_recommendation)
            self.assertEqual(option_view.verification_capability, assess.verification_capability)
            self.assertEqual(option_view.reasons, assess.reasons)
            self.assertEqual(option_view.prerequisites, assess.prerequisite_status)
            self.assertEqual(option_view.pedagogical_priority, assess.pedagogical_priority)
            self.assertEqual(
                option_view.has_trace_available,
                option_view.method_id in TRACE_GENERATORS,
            )

    def test_zero_candidates_automatic_selection_returns_domain_contract_error(self):
        """If automatic selection finds 0 APPLICABLE+AVAILABLE candidates, returns DOMAIN_CONTRACT_ERROR."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id=None,
        )

        with patch("mke_product.domain.registry.MethodRegistry.assess_quadratic") as mock_assess:
            # Force all methods to be UNAVAILABLE
            assessments = [
                MethodAssessment(
                    method_id="QUAD_FORMULA_STANDARD",
                    problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                    mathematical_applicability=MathematicalApplicability.APPLICABLE,
                    support_status=SupportStatus.SUPPORTED,
                    execution_availability=ExecutionAvailability.UNAVAILABLE,
                    pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                    verification_capability=VerificationCapability.HOST_VERIFIABLE,
                    pedagogical_priority=1,
                )
            ]
            mock_assess.return_value = assessments
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.DOMAIN_CONTRACT_ERROR
            )

    # ========================================================================
    # 9. DOMAIN IR GATE & ADVERSARIAL ERROR HANDLING
    # ========================================================================

    def test_domain_ir_construction_failure_returns_domain_contract_error(self):
        """If Domain IR construction fails, orchestrator safely returns DOMAIN_CONTRACT_ERROR."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )

        with patch(
            "mke_product.application.orchestrator.QuadraticProblemIR"
        ) as mock_ir:
            mock_ir.side_effect = ValueError("Injected Domain IR contract violation")
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.DOMAIN_CONTRACT_ERROR
            )
            self.assertIn("hợp đồng miền", resp.message_vi)

    def test_trace_contract_violation_returns_domain_contract_error(self):
        """If trace generator raises TraceMethodNotApplicableError / TraceInvariantError, returns DOMAIN_CONTRACT_ERROR."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        with patch(
            "mke_product.application.orchestrator.generate_solution_trace"
        ) as mock_trace:
            mock_trace.side_effect = TraceMethodNotApplicableError(
                "Injected trace applicability violation"
            )
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.DOMAIN_CONTRACT_ERROR
            )

    def test_trace_generation_error_returns_method_execution_failed(self):
        """If trace generator raises generic TraceGenerationError, returns METHOD_EXECUTION_FAILED."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        with patch(
            "mke_product.application.orchestrator.generate_solution_trace"
        ) as mock_trace:
            mock_trace.side_effect = TraceGenerationError(
                "Generic execution step failure"
            )
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.METHOD_EXECUTION_FAILED
            )

    def test_client_error_sanitization_no_internal_exception_leak(self):
        """Verify that internal exception strings (SECRET_INTERNAL_SENTINEL) are never leaked to client."""
        secret_msg = "SECRET_INTERNAL_SENTINEL_DB_PASSWORD"
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )

        with patch(
            "mke_product.domain.verifier.HostIndependentVerifier.verify_quadratic_solution"
        ) as mock_ver:
            mock_ver.side_effect = RuntimeError(secret_msg)
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.VERIFICATION_FAILED
            )

            # Ensure secret string is strictly absent
            self.assertNotIn(secret_msg, resp.message_vi)
            self.assertNotIn(secret_msg, resp.message_en)
            self.assertNotIn(secret_msg, str(resp.details))

    # ========================================================================
    # 10. PYDANTIC V2 RUNTIME CROSS-FIELD INVARIANT TESTS
    # ========================================================================

    def test_verified_solution_view_rejects_mismatched_roots(self):
        """VerifiedSolutionView raises ValidationError if trace.roots != roots."""
        cert = VerificationCertificate(
            certificate_id="cert1",
            problem_hash="hash1",
            outcome=VerificationOutcome.VERIFIED_COMPLETE,
            integrity_fingerprint="fp1",
            verified_at_utc=datetime.utcnow(),
        )
        step = SolutionStep(
            step_number=1,
            latex_expression="x = 1",
            explanation_vi="Step",
        )
        real_root = RealRootValue(
            root_type=SolutionRootType.RATIONAL,
            rational_value=RationalFraction.from_int(1),
            latex_str="1",
        )
        other_root = RealRootValue(
            root_type=SolutionRootType.RATIONAL,
            rational_value=RationalFraction.from_int(2),
            latex_str="2",
        )
        trace = SolutionTrace(
            method_id="QUAD_FORMULA_STANDARD",
            solution_outcome=SolutionOutcome.ONE_REPEATED_REAL_ROOT,
            roots=[real_root],
            steps=[step],
            final_answer_latex="x = 1",
        )

        with self.assertRaises(ValidationError):
            VerifiedSolutionView(
                method_id="QUAD_FORMULA_STANDARD",
                outcome=SolutionOutcome.ONE_REPEATED_REAL_ROOT,
                roots=[other_root],  # Forged mismatch with trace.roots
                final_answer_latex="x = 1",
                trace=trace,
                certificate=cert,
            )

    def test_solved_response_cross_field_validators_complete(self):
        """SolvedResponse enforces cross-field consistency across all 6 invariant dimensions."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

        # A. selected_method_id is NOT_APPLICABLE in available_methods
        not_app_methods = [
            MethodOptionView(
                method_id="QUAD_FORMULA_STANDARD",
                title_vi="Test",
                mathematical_applicability=MathematicalApplicability.NOT_APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                has_trace_available=True,
                pedagogical_priority=1,
            )
        ]
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=not_app_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                solution=resp.solution,
            )

        # B. selected_method_id is UNAVAILABLE
        unavail_methods = [
            MethodOptionView(
                method_id="QUAD_FORMULA_STANDARD",
                title_vi="Test",
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.UNAVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                has_trace_available=True,
                pedagogical_priority=1,
            )
        ]
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=unavail_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                solution=resp.solution,
            )

        # C. support_status != SUPPORTED
        unsupported_methods = [
            MethodOptionView(
                method_id="QUAD_FORMULA_STANDARD",
                title_vi="Test",
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.UNSUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                has_trace_available=True,
                pedagogical_priority=1,
            )
        ]
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=unsupported_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                solution=resp.solution,
            )

        # D. has_trace_available == False
        no_trace_methods = [
            MethodOptionView(
                method_id="QUAD_FORMULA_STANDARD",
                title_vi="Test",
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                has_trace_available=False,
                pedagogical_priority=1,
            )
        ]
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=no_trace_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",
                solution=resp.solution,
            )

        # E. selected_method_id absent from available_methods
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=[],
                selected_method_id=resp.selected_method_id,
                solution=resp.solution,
            )

        # F. selected_method_id != solution.method_id
        with self.assertRaises(ValidationError):
            SolvedResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_REDUCED",  # Mismatched ID
                solution=resp.solution,
            )

    def test_analyzed_no_execution_adversarial_rejections(self):
        """AnalyzedNoExecutionResponse rejects all contradictory configurations."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            ),
            selected_method_id="QUAD_VIETE_SPECIAL_SUM",
        )
        resp = solve_request(req)
        self.assertIsInstance(resp, AnalyzedNoExecutionResponse)

        deg_problem = CanonicalDegenerateProblemView(
            problem_id="prob_deg",
            equation_latex="2x - 4 = 0",
            classification=EquationClassificationType.LINEAR,
            a=RationalFraction.from_int(0),
            b=RationalFraction.from_int(2),
            c=RationalFraction.from_int(-4),
            linear_root=RationalFraction.from_int(2),
            semantic_revision_hash="hash_deg",
        )
        cert_deg = VerificationCertificate(
            certificate_id="cert_d",
            problem_hash="hash_deg",
            outcome=VerificationOutcome.VERIFIED_COMPLETE,
            integrity_fingerprint="fp_d",
        )
        deg_sol = DegenerateSolutionView(
            classification=EquationClassificationType.LINEAR,
            outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
            linear_root=RationalFraction.from_int(2),
            final_answer_latex="x = 2",
            certificate=cert_deg,
        )

        # --- METHOD_NOT_APPLICABLE ---
        # 1. selected_method_id is None
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id=None,
                reason_code=NoExecutionReasonCode.METHOD_NOT_APPLICABLE,
                analysis_message_vi="Test",
            )
        # 2. selected method is actually APPLICABLE
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",  # Standard formula is APPLICABLE!
                reason_code=NoExecutionReasonCode.METHOD_NOT_APPLICABLE,
                analysis_message_vi="Test",
            )
        # 3. degenerate_solution populated on METHOD_NOT_APPLICABLE
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_VIETE_SPECIAL_SUM",
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.METHOD_NOT_APPLICABLE,
                analysis_message_vi="Test",
            )

        # --- METHOD_NOT_EXECUTABLE ---
        # 1. selected_method_id is None
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id=None,
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Test",
            )
        # 2. selected method is AVAILABLE
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_FORMULA_STANDARD",  # Standard formula is AVAILABLE!
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Test",
            )
        # 3. selected method is NOT_APPLICABLE (must be rejected from METHOD_NOT_EXECUTABLE)
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_VIETE_SPECIAL_SUM",  # Viète is NOT_APPLICABLE!
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Test",
            )
        # 4. degenerate_solution populated on METHOD_NOT_EXECUTABLE
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,
                available_methods=resp.available_methods,
                selected_method_id="QUAD_COMPLETE_SQUARE",
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Test",
            )

        # --- DEGENERATE_EXACT_SOLUTION ---
        # 1. Quadratic problem on DEGENERATE_EXACT_SOLUTION
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=resp.problem,  # Quadratic view
                available_methods=[],
                selected_method_id=None,
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )
        # 2. available_methods non-empty
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=deg_problem,
                available_methods=resp.available_methods,  # Non-empty
                selected_method_id=None,
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )
        # 3. selected_method_id non-None
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=deg_problem,
                available_methods=[],
                selected_method_id="QUAD_FORMULA_STANDARD",
                degenerate_solution=deg_sol,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )
        # 4. degenerate_solution missing
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=deg_problem,
                available_methods=[],
                selected_method_id=None,
                degenerate_solution=None,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )
        # 5. classification mismatch
        deg_sol_identity = DegenerateSolutionView(
            classification=EquationClassificationType.IDENTITY,
            outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
            linear_root=None,
            final_answer_latex="S = \\mathbb{R}",
            certificate=cert_deg,
        )
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=deg_problem,  # LINEAR problem
                available_methods=[],
                selected_method_id=None,
                degenerate_solution=deg_sol_identity,  # IDENTITY solution
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )
        # 6. LINEAR root mismatch
        deg_sol_wrong_root = DegenerateSolutionView(
            classification=EquationClassificationType.LINEAR,
            outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
            linear_root=RationalFraction.from_int(999),  # Mismatch with problem.linear_root = 2
            final_answer_latex="x = 999",
            certificate=cert_deg,
        )
        with self.assertRaises(ValidationError):
            AnalyzedNoExecutionResponse(
                problem=deg_problem,
                available_methods=[],
                selected_method_id=None,
                degenerate_solution=deg_sol_wrong_root,
                reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
                analysis_message_vi="Test",
            )

    def test_discriminated_union_adapter_validation(self):
        """Verify that SolveResponseUnion deserializes polymorphically via Pydantic TypeAdapter."""
        req = SolveRequest(
            input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0")
        )
        resp = solve_request(req)
        dumped = resp.model_dump()

        adapter = TypeAdapter(SolveResponseUnion)
        reconstructed = adapter.validate_python(dumped)
        self.assertIsInstance(reconstructed, SolvedResponse)
        self.assertEqual(
            reconstructed.problem.semantic_revision_hash,
            resp.problem.semantic_revision_hash,
        )


if __name__ == "__main__":
    unittest.main()
