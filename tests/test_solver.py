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
from mke_product.evaluator.result import CandidateCheckResult, CandidateCheckStatus
from mke_product.solver import (
    solve_equation,
    SolverResult,
    SolverScopeStatus,
    SolutionClassification,
)


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


if __name__ == "__main__":
    unittest.main()
