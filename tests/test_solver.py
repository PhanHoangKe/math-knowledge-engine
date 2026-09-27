"""Authoritative unit test suite for MKE Product S3 exact linear equation solver.

Conforms strictly to MKE PRODUCT-01-R2 / rev0.3.1 / FREEZE_ADDENDUM.md / PRODUCT-02A-S3:
- Dependency-free standard library unittest.
- Exact rational arithmetic over Q; real domain R.
- Pre-simplification safety inspection on unreduced AST.
- Out-of-scope guards (variable exponent zero, quadratic/nonlinear, variable denominators).
- Domain errors for original constant undefinedness (1/0, 0*(1/0), 0^0).
- Independent S2 verification of unique roots with fail-closed behavior.
- Exact typed assertions (no string-based matching).
"""

import os
import sys
import unittest
from unittest.mock import patch

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation
from mke_product.evaluator.budget import EvaluationBudget
from mke_product.evaluator.evaluator import ExpressionEvaluator
from mke_product.evaluator.result import CandidateCheckResult, CandidateCheckStatus
from mke_product.solver import (
    solve_equation,
    SolverResult,
    SolverScopeStatus,
    SolutionClassification,
)
import mke_product.solver.solver as solver_mod


class TestSolverMandatoryRegressions(unittest.TestCase):
    """Mandatory representative cases specified in S3 task definition."""

    def test_linear_basic_integer_coefficients(self):
        """2*x + 3 = 7 -> UNIQUE_ROOT, x = 2."""
        eq = parse_equation("2*x + 3 = 7")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(2, 1))
        self.assertIsNotNone(res.evidence)
        self.assertEqual(res.evidence.normalized_a, Rational(2, 1))
        self.assertEqual(res.evidence.normalized_b, Rational(-4, 1))
        self.assertIsNotNone(res.evidence.candidate_check)
        self.assertEqual(res.evidence.candidate_check.status, CandidateCheckStatus.VALID)

    def test_linear_fractional_coefficients(self):
        """(1/2)*x + (3/4) = 0 -> UNIQUE_ROOT, x = -3/2."""
        eq = parse_equation("(1/2)*x + (3/4) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(-3, 2))

    def test_linear_division_by_constant(self):
        """x/2 + 1 = 0 -> UNIQUE_ROOT, x = -2."""
        eq = parse_equation("x/2 + 1 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(-2, 1))

    def test_linear_negative_coefficient(self):
        """-3*x + 9 = 0 -> UNIQUE_ROOT, x = 3."""
        eq = parse_equation("-3*x + 9 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(3, 1))

    def test_identity_variable_equals_variable(self):
        """x = x -> DomainSet(R)."""
        eq = parse_equation("x = x")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.ALL_REALS)
        self.assertTrue(res.is_all_reals)
        self.assertIsNone(res.root)

    def test_identity_zero_times_x_equals_zero(self):
        """0*x = 0 -> DomainSet(R)."""
        eq = parse_equation("0*x = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.ALL_REALS)
        self.assertTrue(res.is_all_reals)
        self.assertIsNone(res.root)

    def test_identity_constant_equals_constant(self):
        """1 = 1 -> DomainSet(R)."""
        eq = parse_equation("1 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.ALL_REALS)
        self.assertTrue(res.is_all_reals)
        self.assertIsNone(res.root)

    def test_contradiction_zero_times_x_equals_constant(self):
        """0*x = 5 -> EmptySet."""
        eq = parse_equation("0*x = 5")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.NO_SOLUTION)
        self.assertTrue(res.is_empty_set)
        self.assertIsNone(res.root)

    def test_contradiction_constant_inequality(self):
        """1 = 2 -> EmptySet."""
        eq = parse_equation("1 = 2")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_solved)
        self.assertEqual(res.classification, SolutionClassification.NO_SOLUTION)
        self.assertTrue(res.is_empty_set)
        self.assertIsNone(res.root)

    def test_out_of_scope_quadratic_expression(self):
        """x^2 - 4 = 0 -> OUT_OF_SCOPE_NONLINEAR."""
        eq = parse_equation("x^2 - 4 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertFalse(res.is_solved)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_NONLINEAR")

    def test_out_of_scope_zero_times_quadratic(self):
        """0*x^2 = 0 -> OUT_OF_SCOPE_NONLINEAR."""
        eq = parse_equation("0*(x^2) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_NONLINEAR")

    def test_out_of_scope_quadratic_cancellation(self):
        """x^2 - x^2 = 0 -> OUT_OF_SCOPE_NONLINEAR."""
        eq = parse_equation("x^2 - x^2 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_NONLINEAR")

    def test_out_of_scope_rational_fraction(self):
        """(x-1)/(x-1) = 1 -> OUT_OF_SCOPE_RATIONAL_FRACTION."""
        eq = parse_equation("(x-1)/(x-1) = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_RATIONAL_FRACTION")

    def test_out_of_scope_variable_exponent_zero(self):
        """x^0 = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x^0 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_out_of_scope_zero_times_variable_exponent_zero(self):
        """0*x^0 = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("0*(x^0) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_domain_error_literal_division_by_zero(self):
        """1/0 = 0 -> DOMAIN_ERROR."""
        eq = parse_equation("1/0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_domain_error_multiplication_by_zero_does_not_mask(self):
        """0*(1/0) = 0 -> DOMAIN_ERROR."""
        eq = parse_equation("0*(1/0) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_domain_error_constant_zero_to_zero(self):
        """0^0 = 1 -> DOMAIN_ERROR."""
        eq = parse_equation("0^0 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")


class TestSolverAlgebraicVarietiesAndProperties(unittest.TestCase):
    """Additional algebraic varieties, precedence, large coefficients, and verification."""

    def test_variable_terms_on_both_sides(self):
        """5*x + 3 = 2*x + 9 -> 3*x = 6 -> x = 2."""
        eq = parse_equation("5*x + 3 = 2*x + 9")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(2, 1))

    def test_large_rational_coefficients(self):
        """1000000*x + 2000000 = 5000000 -> x = 3."""
        eq = parse_equation("1000000*x + 2000000 = 5000000")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res.root, Rational(3, 1))

    def test_negative_signs_and_grouping(self):
        """-(2*x - 4) = 8 -> -2*x + 4 = 8 -> -2*x = 4 -> x = -2."""
        eq = parse_equation("-(2*x - 4) = 8")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res.root, Rational(-2, 1))

    def test_variable_multiplied_by_variable_expression_rejected(self):
        """x*x = 1 -> OUT_OF_SCOPE_NONLINEAR."""
        eq = parse_equation("x*x = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_NONLINEAR")

    def test_variable_subtraction_cancellation_preserves_nonlinear_rejection(self):
        """(x-x)*x = 0 -> multiplying two variable expressions is OUT_OF_SCOPE_NONLINEAR."""
        eq = parse_equation("(x-x)*x = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_NONLINEAR")

    def test_shifted_variable_raised_to_zero_rejected(self):
        """(x-1)^0 = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("(x-1)^0 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_constant_denominator_zero_expression_rejected(self):
        """x/(2-2) = 1 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("x/(2-2) = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_ast_immutability(self):
        """Solving an equation does not mutate the original AST."""
        eq = parse_equation("2*x + 1 = 5")
        original_left = eq.left
        original_right = eq.right
        res = solve_equation(eq)
        self.assertIs(res.equation.left, original_left)
        self.assertIs(res.equation.right, original_right)

    def test_operation_budget_exhaustion_in_solver(self):
        """Solver respects EvaluationBudget max_operations."""
        eq = parse_equation("x + x + x + x = 4")
        tight_budget = EvaluationBudget(max_operations=3)
        res = solve_equation(eq, budget=tight_budget)
        self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)

    def test_integer_bit_budget_exhaustion_in_solver(self):
        """Solver respects EvaluationBudget max_integer_bits."""
        eq = parse_equation("1000*x = 1")
        tight_budget = EvaluationBudget(max_integer_bits=5)
        res = solve_equation(eq, budget=tight_budget)
        self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)

    def test_independent_verification_failure_fails_closed(self):
        """Simulate S2 check_candidate returning INVALID to verify fail-closed behavior."""
        eq = parse_equation("2*x = 4")
        fake_invalid_result = CandidateCheckResult(
            status=CandidateCheckStatus.INVALID,
            candidate=Rational(2, 1),
            equation=eq,
        )
        with patch("mke_product.solver.solver.check_candidate", return_value=fake_invalid_result):
            res = solve_equation(eq)
            self.assertEqual(res.status, SolverScopeStatus.INTERNAL_VERIFICATION_FAILURE)
            self.assertEqual(res.error_code, "ERR_INTERNAL_VERIFICATION_FAILURE")
            self.assertIsNone(res.classification)

    def test_independent_verification_resource_exhaustion_fails_closed(self):
        """Simulate S2 check_candidate returning RESOURCE_EXHAUSTED to verify fail-closed behavior."""
        eq = parse_equation("2*x = 4")
        fake_res_result = CandidateCheckResult(
            status=CandidateCheckStatus.RESOURCE_EXHAUSTED,
            candidate=Rational(2, 1),
            equation=eq,
            error_code="ERR_RESOURCE_EXHAUSTED_STEP_LIMIT",
        )
        with patch("mke_product.solver.solver.check_candidate", return_value=fake_res_result):
            res = solve_equation(eq)
            self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
            self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
            self.assertIsNone(res.classification)

    def test_type_error_on_non_equation(self):
        """solve_equation raises TypeError if passed something other than an Equation AST."""
        with self.assertRaises(TypeError):
            solve_equation("2*x = 4")  # type: ignore


class TestScopePreflightRemediationS3R1(unittest.TestCase):
    """Targeted regressions for MKE PRODUCT-02A-S3-R1 scope preflight remediation."""

    def test_issue1_exponent_zero_binding_multiplication(self):
        """x*(x^0) = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x*(x^0) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_issue1_exponent_zero_binding_denominator(self):
        """1/(x^0) = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("1/(x^0) = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_issue1_exponent_zero_binding_nested_power(self):
        """(x^0)^2 = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("(x^0)^2 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_issue1_exponent_zero_binding_addition_left(self):
        """x^0 + x^2 = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x^0 + x^2 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_issue1_exponent_zero_binding_addition_right(self):
        """x^2 + x^0 = 1 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x^2 + x^0 = 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_issue2_constant_undefinedness_division_by_zero_right(self):
        """x^2 + 1/0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("x^2 + 1/0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_issue2_constant_undefinedness_division_by_zero_left(self):
        """1/0 + x^2 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("1/0 + x^2 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_issue2_constant_undefinedness_zero_to_zero_right(self):
        """x/(x-1) + 0^0 = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("x/(x-1) + 0^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_issue2_constant_undefinedness_zero_to_zero_left(self):
        """0^0 + x/(x-1) = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("0^0 + x/(x-1) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_permutation_invariance_nonlinear_and_rational(self):
        """Permutation invariance between nonlinear and rational fraction."""
        eq1 = parse_equation("x^2 + x/(x-1) = 0")
        eq2 = parse_equation("x/(x-1) + x^2 = 0")
        res1 = solve_equation(eq1)
        res2 = solve_equation(eq2)
        self.assertEqual(res1.status, res2.status)
        self.assertEqual(res1.error_code, res2.error_code)

    def test_simultaneous_exponent_zero_and_constant_undefinedness(self):
        """Equation with both x^0 and 1/0 is rejected with deterministic domain error."""
        eq1 = parse_equation("x^0 + 1/0 = 0")
        eq2 = parse_equation("1/0 + x^0 = 0")
        res1 = solve_equation(eq1)
        res2 = solve_equation(eq2)
        self.assertEqual(res1.status, res2.status)
        self.assertEqual(res1.error_code, res2.error_code)



class TestSolverFinalRemediationS3R2(unittest.TestCase):
    """Regressions for MKE PRODUCT-02A-S3-R2 final solver remediation and Owner Decision ADR-001."""

    # 1. Owner Decision A: Proven constant domain error takes precedence over x^0
    def test_owner_decision_a_exponent_zero_and_div_zero_left(self):
        """x^0 + 1/0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("x^0 + 1/0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_owner_decision_a_div_zero_and_exponent_zero_right(self):
        """1/0 + x^0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("1/0 + x^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_owner_decision_a_exponent_zero_and_zero_to_zero_left(self):
        """x^0 + 0^0 = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("x^0 + 0^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_owner_decision_a_zero_to_zero_and_exponent_zero_right(self):
        """0^0 + x^0 = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("0^0 + x^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_owner_decision_a_shifted_var_exponent_zero_and_div_zero(self):
        """(x-1)^0 + 1/(2-2) = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("(x-1)^0 + 1/(2-2) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_owner_decision_a_div_zero_and_shifted_var_exponent_zero(self):
        """1/(2-2) + (x-1)^0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("1/(2-2) + (x-1)^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    # 2. Reordered mixed-hazard expressions
    def test_mixed_hazard_nonlinear_and_div_zero_left(self):
        """x^2 + 1/0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("x^2 + 1/0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_mixed_hazard_div_zero_and_nonlinear_right(self):
        """1/0 + x^2 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("1/0 + x^2 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_mixed_hazard_rational_fraction_and_div_zero_left(self):
        """x/(x-1) + 1/0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("x/(x-1) + 1/0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_mixed_hazard_div_zero_and_rational_fraction_right(self):
        """1/0 + x/(x-1) = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("1/0 + x/(x-1) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_mixed_hazard_rational_fraction_and_zero_to_zero_left(self):
        """x/(x-1) + 0^0 = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("x/(x-1) + 0^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_mixed_hazard_zero_to_zero_and_rational_fraction_right(self):
        """0^0 + x/(x-1) = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("0^0 + x/(x-1) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    # 3. Multiple distinct proven constant-domain failures
    def test_multiple_domain_errors_preserves_domain_error_category(self):
        """1/0 + 0^0 = 0 and 0^0 + 1/0 = 0 both guarantee DOMAIN_ERROR category."""
        eq1 = parse_equation("1/0 + 0^0 = 0")
        eq2 = parse_equation("0^0 + 1/0 = 0")
        res1 = solve_equation(eq1)
        res2 = solve_equation(eq2)
        self.assertEqual(res1.status, SolverScopeStatus.DOMAIN_ERROR)
        self.assertEqual(res2.status, SolverScopeStatus.DOMAIN_ERROR)
        # AST pre-order tie-break gives leftmost domain error
        self.assertEqual(res1.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertEqual(res2.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    # 4. Variable-dependent power-zero precedence where no constant-domain violation exists
    def test_exponent_zero_precedence_over_nonlinear_multiplication(self):
        """x*(x^0) = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x*(x^0) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_exponent_zero_precedence_over_quadratic_power(self):
        """x^0 + x^2 = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x^0 + x^2 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_exponent_zero_precedence_over_quadratic_power_reversed(self):
        """x^2 + x^0 = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("x^2 + x^0 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_exponent_zero_precedence_over_rational_fraction(self):
        """(x^0)/(x-1) = 0 -> OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        eq = parse_equation("(x^0)/(x-1) = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.OUT_OF_SCOPE)
        self.assertEqual(res.error_code, "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    # 5. Shared S3 preflight/extraction resource budget
    def test_budget_exhaustion_during_preflight_traversal(self):
        """Exhausting operation budget during preflight traversal fails closed."""
        eq = parse_equation("2*x + 3 = 7")
        budget = EvaluationBudget(max_operations=2)
        res = solve_equation(eq, budget=budget)
        self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
        self.assertIsNone(res.classification)
        self.assertIsNone(res.root)

    def test_budget_exhaustion_during_preflight_constant_subexpression(self):
        """Exhausting operation budget during preflight constant subexpression evaluation fails closed."""
        eq = parse_equation("x + (1 + 1 + 1 + 1)/(2 - 2) = 0")
        # Preflight visits nodes, then tries to evaluate constant denominator which exceeds tight budget
        budget = EvaluationBudget(max_operations=6)
        res = solve_equation(eq, budget=budget)
        self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.classification)

    def test_budget_exhaustion_during_affine_extraction(self):
        """Exhausting shared operation budget during affine extraction fails closed."""
        eq = parse_equation("2*x + 3 = 4*x + 5")
        # Give enough steps for preflight (~15 steps), but not enough for full extraction (~25 steps)
        budget = EvaluationBudget(max_operations=18)
        res = solve_equation(eq, budget=budget)
        self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.classification)
        self.assertIsNone(res.root)

    def test_resource_exhaustion_never_produces_solution_classification(self):
        """Ensure RESOURCE_EXHAUSTED never returns UNIQUE_ROOT, DomainSet(R), or EmptySet."""
        ident_eq = parse_equation("x = x")
        contra_eq = parse_equation("1 = 2")
        tight_budget = EvaluationBudget(max_operations=1)

        res_ident = solve_equation(ident_eq, budget=tight_budget)
        res_contra = solve_equation(contra_eq, budget=tight_budget)

        self.assertEqual(res_ident.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res_ident.classification)
        self.assertFalse(res_ident.is_all_reals)

        self.assertEqual(res_contra.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res_contra.classification)
        self.assertFalse(res_contra.is_empty_set)

    # 6. S2 independent verification contract
    def test_s2_independent_verification_present_and_valid(self):
        """Unique root solution includes verified S2 candidate check result."""
        eq = parse_equation("3*x + 9 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res.root, Rational(-3, 1))
        self.assertIsNotNone(res.evidence)
        self.assertIsNotNone(res.evidence.candidate_check)
        self.assertEqual(res.evidence.candidate_check.status, CandidateCheckStatus.VALID)

    # 7. No regression to the three supported linear solution classifications
    def test_no_regression_unique_root(self):
        """3*x + 6 = 0 -> UNIQUE_ROOT, x = -2."""
        eq = parse_equation("3*x + 6 = 0")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_unique_root)
        self.assertEqual(res.root, Rational(-2, 1))

    def test_no_regression_all_reals(self):
        """x + 1 = x + 1 -> DomainSet(R)."""
        eq = parse_equation("x + 1 = x + 1")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_all_reals)
        self.assertEqual(res.classification, SolutionClassification.ALL_REALS)
        self.assertIsNone(res.root)

    def test_no_regression_empty_set(self):
        """x + 1 = x + 2 -> EmptySet."""
        eq = parse_equation("x + 1 = x + 2")
        res = solve_equation(eq)
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertTrue(res.is_empty_set)
        self.assertEqual(res.classification, SolutionClassification.NO_SOLUTION)
        self.assertIsNone(res.root)



class TestSolverResourceExhaustionBoundariesS3R3(unittest.TestCase):
    """Targeted boundary tests for MKE PRODUCT-02A-S3-R3 proving the precise stage of resource exhaustion."""

    def test_constant_evaluation_boundary_exhaustion(self):
        """Constant-evaluation boundary: equation x/0=0.

        Original AST has 5 nodes: Equation, BinaryOp(/), Variable(x), IntegerLiteral(0) [den], IntegerLiteral(0) [rhs].
        1. Preflight variable-dependency memoization visits all 5 nodes (ops 1-5).
        2. Preflight traversal visits Equation (op 6) and BinaryOp(/) (op 7).
        3. BinaryOp(/) triggers constant denominator evaluation of IntegerLiteral(0).
        With max_operations=7, ExpressionEvaluator.evaluate is entered at op 7 and exhausts on step 8.
        With max_operations=11, preflight completes (evaluator step 8, then remaining 3 AST nodes ops 9-11)
        and successfully returns DOMAIN_ERROR_DIVISION_BY_ZERO.
        """
        eval_calls = []
        orig_eval = ExpressionEvaluator.evaluate

        def spy_eval(eval_self, node):
            eval_calls.append((type(node).__name__, eval_self.operations_count))
            return orig_eval(eval_self, node)

        # Stage A: max_operations=7 exhausts INSIDE constant denominator evaluation
        with patch.object(ExpressionEvaluator, "evaluate", side_effect=spy_eval, autospec=True):
            eq = parse_equation("x/0 = 0")
            res7 = solve_equation(eq, budget=EvaluationBudget(max_operations=7))
            self.assertEqual(res7.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
            self.assertEqual(res7.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
            self.assertIsNone(res7.classification)
            # Verifies ExpressionEvaluator was entered exactly once with operations_count == 7
            self.assertEqual(len(eval_calls), 1)
            self.assertEqual(eval_calls[0], ("IntegerLiteral", 7))

        # Stage B: max_operations=11 permits preflight completion and returns DOMAIN_ERROR
        eval_calls.clear()
        with patch.object(ExpressionEvaluator, "evaluate", side_effect=spy_eval, autospec=True):
            eq = parse_equation("x/0 = 0")
            res11 = solve_equation(eq, budget=EvaluationBudget(max_operations=11))
            self.assertEqual(res11.status, SolverScopeStatus.DOMAIN_ERROR)
            self.assertEqual(res11.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")
            self.assertIsNone(res11.classification)
            self.assertEqual(len(eval_calls), 1)
            self.assertEqual(eval_calls[0], ("IntegerLiteral", 7))

    def test_affine_extraction_boundary_exhaustion(self):
        """Affine-extraction boundary: equation x=1.

        Original AST has 3 nodes: Equation, Variable(x), IntegerLiteral(1).
        1. Preflight memoization visits 3 nodes (ops 1-3).
        2. Preflight traversal visits 3 nodes (ops 4-6). Preflight completes at op 6.
        3. Affine extraction visits left node Variable(x) (op 7).
        4. Affine extraction visits right node IntegerLiteral(1) (attempting op 8).
        With max_operations=7, extraction of lhs succeeds, and extraction of rhs exhausts inside extract_affine.
        """
        extract_calls = []
        orig_extract = solver_mod.extract_affine

        def spy_extract(node, budget, tracker, var_memo=None):
            extract_calls.append((type(node).__name__, tracker.operations_count))
            return orig_extract(node, budget, tracker, var_memo=var_memo)

        with patch.object(solver_mod, "extract_affine", side_effect=spy_extract):
            eq = parse_equation("x = 1")
            res7 = solver_mod.solve_equation(eq, budget=EvaluationBudget(max_operations=7))
            self.assertEqual(res7.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
            self.assertEqual(res7.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
            self.assertIsNone(res7.classification)
            # Verifies extract_affine was called for lhs ('Variable' at op 6->7) and rhs ('IntegerLiteral' at op 7->fail)
            self.assertEqual(len(extract_calls), 2)
            self.assertEqual(extract_calls[0], ("Variable", 6))
            self.assertEqual(extract_calls[1], ("IntegerLiteral", 7))

    def test_root_isolation_boundary_exhaustion(self):
        """Root-isolation boundary: equation x=1.

        Operation accounting breakdown:
        - Preflight memoization (3 nodes): ops 1-3
        - Preflight traversal (3 nodes): ops 4-6
        - Affine extraction left (Variable x): op 7
        - Affine extraction right (IntegerLiteral 1): op 8
        - Affine normalization a (aff_l.a - aff_r.a): op 9
        - Affine normalization b (aff_l.b - aff_r.b): op 10
        - Root isolation (-norm_b / norm_a): op 11

        With max_operations=10, exhaustion occurs during root isolation (op 11 > 10).
        With max_operations=11, root isolation succeeds at op 11 and triggers S2 verification.
        """
        eq = parse_equation("x = 1")

        # Boundary A: max_operations=10 exhausts during root isolation
        res10 = solve_equation(eq, budget=EvaluationBudget(max_operations=10))
        self.assertEqual(res10.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
        self.assertEqual(res10.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
        self.assertIsNone(res10.classification)
        self.assertIsNone(res10.root)

        # Boundary B: max_operations=11 completes S3 and passes S2 independent verification
        res11 = solve_equation(eq, budget=EvaluationBudget(max_operations=11))
        self.assertEqual(res11.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res11.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertEqual(res11.root, Rational(1, 1))
        self.assertIsNotNone(res11.evidence)
        self.assertIsNotNone(res11.evidence.candidate_check)
        self.assertEqual(res11.evidence.candidate_check.status, CandidateCheckStatus.VALID)

    def test_s2_separate_budget_preservation(self):
        """Verify that S2 independent verification receives its own budget and is not exhausted by S3 steps."""
        eq = parse_equation("x = 1")
        # S3 finishes at op 11. S2 check_candidate requires ~6 operations to evaluate x=1.
        # If S2 shared S3's exhausted budget (remaining 0), it would fail with RESOURCE_EXHAUSTED.
        # Since S2 receives its own fresh budget(max_operations=11), it completes VALID.
        res = solve_equation(eq, budget=EvaluationBudget(max_operations=11))
        self.assertEqual(res.status, SolverScopeStatus.IN_SCOPE)
        self.assertEqual(res.classification, SolutionClassification.UNIQUE_ROOT)
        self.assertIsNotNone(res.evidence.candidate_check)
        self.assertEqual(res.evidence.candidate_check.status, CandidateCheckStatus.VALID)

    def test_resource_exhaustion_never_produces_solved_classification_exhaustive(self):
        """Verify that across all stages, resource exhaustion never yields UNIQUE_ROOT, DomainSet(R), or EmptySet."""
        cases = [
            ("x = 1", 5),    # exhausts during preflight traversal
            ("x = 1", 7),    # exhausts during affine extraction
            ("x = 1", 10),   # exhausts during root isolation
            ("x = x", 4),    # identity equation under-budget
            ("1 = 2", 4),    # contradiction equation under-budget
            ("x/0 = 0", 7),  # constant denominator under-budget
        ]
        for eq_str, max_ops in cases:
            eq = parse_equation(eq_str)
            res = solve_equation(eq, budget=EvaluationBudget(max_operations=max_ops))
            self.assertEqual(res.status, SolverScopeStatus.RESOURCE_EXHAUSTED)
            self.assertIsNone(res.classification, f"Classification was not None for {eq_str} at {max_ops} ops")
            self.assertFalse(res.is_unique_root)
            self.assertFalse(res.is_all_reals)
            self.assertFalse(res.is_empty_set)


if __name__ == "__main__":
    unittest.main()
