"""MKE MVP V1 — Comprehensive Test Suite for S1-04 Application Orchestrator & Discriminated DTOs.

Validates:
1. End-to-end Pure Python Application Service pipeline (solve_request).
2. RAW_TEXT vs COEFFICIENTS intake invariance & semantic identity equivalence.
3. Strict single method-selection authority and resolution policy.
4. Comprehensive 32-case Acceptance Matrix (Q1-Q9, C1-C5, D1-D4, E1-E8, B1-B6).
5. Degenerate equation exact verification & discriminated response modeling.
6. Multi-method orthogonal assessment mapping & trace execution.
7. Host independent verification and tamper-evident certificate attachment.
8. Pydantic v2 discriminated union serialization, immutability, and adversarial invariant rejection.
"""

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
from mke_product.core.rational import Rational
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    PedagogicalRecommendation,
    ProblemCategory,
    RationalFraction,
    SolutionOutcome,
    SolutionRootType,
    SupportStatus,
    VerificationCapability,
    VerificationOutcome,
)
from mke_product.parser.errors import Span


class TestApplicationOrchestratorS1(unittest.TestCase):
    """Full test suite for MKE MVP V1 Application Orchestrator."""

    # ========================================================================
    # 1. INTAKE EQUIVALENCE & SEMANTIC IDENTITY INVARIANCE
    # ========================================================================

    def test_semantic_identity_and_root_invariance_raw_vs_coefficients(self):
        """Verify that RAW_TEXT and COEFFICIENTS intake produce identical semantic hashes and solutions."""
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

        resp_raw = solve_request(req_raw)
        resp_coeff = solve_request(req_coeff)

        self.assertIsInstance(resp_raw, SolvedResponse)
        self.assertIsInstance(resp_coeff, SolvedResponse)

        # Semantic revision hash must be strictly identical
        self.assertEqual(
            resp_raw.problem.semantic_revision_hash,
            resp_coeff.problem.semantic_revision_hash,
        )
        self.assertEqual(resp_raw.problem.problem_id, resp_coeff.problem.problem_id)
        self.assertEqual(resp_raw.solution.outcome, resp_coeff.solution.outcome)
        self.assertEqual(
            resp_raw.solution.final_answer_latex, resp_coeff.solution.final_answer_latex
        )
        self.assertEqual(
            resp_raw.solution.certificate.outcome, VerificationOutcome.VERIFIED_COMPLETE
        )
        self.assertEqual(
            resp_coeff.solution.certificate.outcome,
            VerificationOutcome.VERIFIED_COMPLETE,
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
    # 2. ACCEPTANCE MATRIX: QUADRATIC RAW_TEXT (Q1 - Q9)
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
    # 3. ACCEPTANCE MATRIX: DIRECT COEFFICIENTS & METHOD SWITCHING (C1 - C5)
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
    # 4. ACCEPTANCE MATRIX: DEGENERATE EQUATIONS (D1 - D4)
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
        self.assertEqual(
            resp.degenerate_solution.linear_root, RationalFraction.from_int(2)
        )

    # ========================================================================
    # 5. ACCEPTANCE MATRIX: ERROR / SCOPE CASES (E1 - E8)
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
    # 6. ACCEPTANCE MATRIX: RESOURCE BOUNDS (B1 - B6)
    # ========================================================================

    def test_b1_max_length_256_passes(self):
        """B1: Exactly 256 characters -> Passes."""
        fixed = "x^2  = 0"
        needed = 256 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 256)

        req = SolveRequest(input_payload=RawEquationInput(raw_query=padded))
        resp = solve_request(req)
        self.assertIsInstance(resp, SolvedResponse)

    def test_b2_max_length_257_fails(self):
        """B2: 257 characters -> ValidationError at DTO boundary."""
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
    # 7. ADVERSARIAL & INVARIANT TESTS
    # ========================================================================

    def test_pydantic_extra_forbid(self):
        """Verify that extra fields are rejected on all DTO models."""
        with self.assertRaises(ValidationError):
            RawEquationInput(raw_query="x^2 = 0", unexpected_field=123)  # type: ignore

        with self.assertRaises(ValidationError):
            CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(0),
                c=RationalFraction.from_int(0),
                extra_param="disallowed",  # type: ignore
            )

    def test_quadratic_problem_view_rejects_zero_a(self):
        """CanonicalQuadraticProblemView rejects leading coefficient a == 0."""
        from mke_product.domain.exact import compute_quadratic_discriminant

        disc = compute_quadratic_discriminant(
            Rational(1, 1), Rational(0, 1), Rational(0, 1)
        )
        with self.assertRaises(ValidationError):
            CanonicalQuadraticProblemView(
                problem_id="prob_123",
                equation_latex="0 = 0",
                a=RationalFraction.from_int(0),
                b=RationalFraction.from_int(0),
                c=RationalFraction.from_int(0),
                discriminant=disc,
                semantic_revision_hash="hash123",
            )

    def test_degenerate_problem_view_rejects_nonzero_a(self):
        """CanonicalDegenerateProblemView rejects leading coefficient a != 0."""
        with self.assertRaises(ValidationError):
            CanonicalDegenerateProblemView(
                problem_id="prob_123",
                equation_latex="x^2 = 0",
                classification=EquationClassificationType.LINEAR,
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(2),
                c=RationalFraction.from_int(-4),
                linear_root=RationalFraction.from_int(2),
                semantic_revision_hash="hash123",
            )

    def test_verifier_failure_handling(self):
        """If host verification returns failure, orchestrator returns ErrorResponse(VERIFICATION_FAILED)."""
        req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_int(1),
                b=RationalFraction.from_int(-5),
                c=RationalFraction.from_int(6),
            )
        )

        with patch(
            "mke_product.domain.verifier.HostIndependentVerifier.verify_quadratic_solution"
        ) as mock_ver:
            from mke_product.domain.models import VerificationCertificate

            mock_ver.return_value = VerificationCertificate(
                certificate_id="cert_fail",
                problem_hash="fake_hash",
                outcome=VerificationOutcome.VERIFICATION_FAILED,
                integrity_fingerprint="fail_fp",
            )
            resp = solve_request(req)
            self.assertIsInstance(resp, ErrorResponse)
            self.assertEqual(
                resp.error_code, ApplicationErrorCode.VERIFICATION_FAILED
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
