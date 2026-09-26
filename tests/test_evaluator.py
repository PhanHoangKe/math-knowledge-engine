"""Authoritative unit test suite for S2 exact semantic evaluation and candidate verification.

Conforms strictly to MKE PRODUCT-01-R2 / PRODUCT-02A-S2 / PRODUCT-02A-S2-R1:
- Dependency-free standard library unittest.
- Original-domain obligations checked on unreduced AST.
- 0^0 is strictly undefined in Real domain.
- Multiplication by zero does not mask undefined subtrees.
- Strict rational equality; no float tolerances or approximations.
- Global shared operation budget across L(c) and R(c).
- Bounded candidate input with ASCII rational-string grammar.
- Three-valued definedness contract (True / False / None).
"""

import os
import sys
import unittest
from fractions import Fraction

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation, parse_expression
from mke_product.parser.ast import IntegerLiteral, Variable, Power
from mke_product.evaluator import (
    check_candidate,
    evaluate_expression,
    extract_domain_obligations,
    CandidateCheckStatus,
    CandidateCheckResult,
    EvaluationBudget,
    InvalidCandidateError,
    ZeroDenominatorEvaluationError,
    UndefinedZeroToZeroError,
    EvaluationResourceLimitError,
    UnsupportedEvaluationError,
)
from mke_product.evaluator.evaluator import coerce_candidate


class TestEvaluatorMandatoryRepresentativeCases(unittest.TestCase):
    """Mandatory representative cases specified in frozen PRODUCT-01 rev0.3.1 and S2."""

    def test_linear_equation_valid_candidate(self):
        """2*x + 3 = 7 at x=2 evaluates to 7=7 -> VALID."""
        eq = parse_equation("2*x + 3 = 7")
        res = check_candidate(eq, 2)
        self.assertEqual(res.status, CandidateCheckStatus.VALID)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(7, 1))
        self.assertEqual(res.right_value, Rational(7, 1))

    def test_linear_equation_invalid_candidate(self):
        """2*x + 3 = 7 at x=3 evaluates to 9=7 -> INVALID."""
        eq = parse_equation("2*x + 3 = 7")
        res = check_candidate(eq, 3)
        self.assertEqual(res.status, CandidateCheckStatus.INVALID)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(9, 1))
        self.assertEqual(res.right_value, Rational(7, 1))

    def test_rational_fraction_division_by_zero_at_singularity(self):
        """(x-1)/(x-1) = 1 at x=1 must fail with DOMAIN_ERROR_DIVISION_BY_ZERO."""
        eq = parse_equation("(x-1)/(x-1) = 1")
        res = check_candidate(eq, 1)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_defined)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertIsNone(res.left_value)

    def test_rational_fraction_valid_away_from_singularity(self):
        """(x-1)/(x-1) = 1 at x=2 evaluates to 1=1 -> VALID."""
        eq = parse_equation("(x-1)/(x-1) = 1")
        res = check_candidate(eq, 2)
        self.assertEqual(res.status, CandidateCheckStatus.VALID)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(1, 1))
        self.assertEqual(res.right_value, Rational(1, 1))

    def test_variable_raised_to_zero_at_singularity(self):
        """x^0 = 1 at x=0 must fail with DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("x^0 = 1")
        res = check_candidate(eq, 0)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_defined)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_variable_raised_to_zero_away_from_singularity(self):
        """x^0 = 1 at x=2 evaluates to 1=1 -> VALID."""
        eq = parse_equation("x^0 = 1")
        res = check_candidate(eq, 2)
        self.assertEqual(res.status, CandidateCheckStatus.VALID)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(1, 1))
        self.assertEqual(res.right_value, Rational(1, 1))

    def test_shifted_variable_raised_to_zero_at_singularity(self):
        """(x-1)^0 = 1 at x=1 must fail with DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        eq = parse_equation("(x-1)^0 = 1")
        res = check_candidate(eq, 1)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_defined)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_multiplication_by_zero_does_not_mask_division_by_zero_left(self):
        """0 * (1/x) = 0 at x=0 must NEVER mask the division by zero in the right operand."""
        eq = parse_equation("0*(1/x) = 0")
        res = check_candidate(eq, 0)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_defined)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_multiplication_by_zero_does_not_mask_division_by_zero_right(self):
        """(1/x) * 0 = 0 at x=0 must NEVER mask the division by zero in the left operand."""
        eq = parse_equation("(1/x)*0 = 0")
        res = check_candidate(eq, 0)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertFalse(res.is_valid)
        self.assertFalse(res.is_defined)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_quadratic_equation_both_roots(self):
        """x^2 - 4 = 0: x=2 and x=-2 are valid solutions."""
        eq = parse_equation("x^2 - 4 = 0")

        res_pos = check_candidate(eq, 2)
        self.assertEqual(res_pos.status, CandidateCheckStatus.VALID)
        self.assertTrue(res_pos.is_valid)
        self.assertEqual(res_pos.left_value, Rational(0, 1))

        res_neg = check_candidate(eq, -2)
        self.assertEqual(res_neg.status, CandidateCheckStatus.VALID)
        self.assertTrue(res_neg.is_valid)
        self.assertEqual(res_neg.left_value, Rational(0, 1))

    def test_quadratic_equation_non_root(self):
        """x^2 - 4 = 0 at x=1 evaluates to -3=0 -> INVALID."""
        eq = parse_equation("x^2 - 4 = 0")
        res = check_candidate(eq, 1)
        self.assertEqual(res.status, CandidateCheckStatus.INVALID)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(-3, 1))
        self.assertEqual(res.right_value, Rational(0, 1))

    def test_negated_x_squared(self):
        """-x^2 = 1 parsed as -(x^2). At x=1, left is -1, right is 1 -> INVALID."""
        eq = parse_equation("-x^2 = 1")
        res = check_candidate(eq, 1)
        self.assertEqual(res.status, CandidateCheckStatus.INVALID)
        self.assertEqual(res.left_value, Rational(-1, 1))
        self.assertEqual(res.right_value, Rational(1, 1))

    def test_grouped_negated_x_squared(self):
        """(-x)^2 = 1 at x=1 evaluates to (-1)^2 = 1 -> VALID."""
        eq = parse_equation("(-x)^2 = 1")
        res = check_candidate(eq, 1)
        self.assertEqual(res.status, CandidateCheckStatus.VALID)
        self.assertEqual(res.left_value, Rational(1, 1))
        self.assertEqual(res.right_value, Rational(1, 1))

    def test_constant_zero_to_zero_fails_domain(self):
        """0^0 = 1 parsed with constant 0^0 must fail with DOMAIN_ERROR."""
        eq = parse_equation("0^0 = 1")
        res = check_candidate(eq, 5)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_multiplication_by_zero_does_not_mask_zero_to_zero(self):
        """0 * (x^0) = 0 at x=0 must be DOMAIN_ERROR because 0^0 is undefined."""
        eq = parse_equation("0*(x^0) = 0")
        res = check_candidate(eq, 0)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_addition_and_subtraction_do_not_mask_domain_errors(self):
        """0 + (1/x) = 0 and 0 - (x^0) = 0 at x=0 must be DOMAIN_ERROR."""
        eq_add = parse_equation("0 + (1/x) = 0")
        self.assertEqual(check_candidate(eq_add, 0).status, CandidateCheckStatus.DOMAIN_ERROR)

        eq_sub = parse_equation("0 - (x^0) = 0")
        self.assertEqual(check_candidate(eq_sub, 0).status, CandidateCheckStatus.DOMAIN_ERROR)

    def test_literal_division_by_zero(self):
        """Literal 1/0 in expression causes DOMAIN_ERROR."""
        eq = parse_equation("x = 1/0")
        res = check_candidate(eq, 5)
        self.assertEqual(res.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertEqual(res.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

    def test_nested_denominators(self):
        """1/(1/(x-2)) = 1: x=2 is DOMAIN_ERROR; x=3 is VALID."""
        eq = parse_equation("1/(1/(x-2)) = 1")

        # c = 2: inner denominator (2-2) = 0 -> DOMAIN_ERROR
        res2 = check_candidate(eq, 2)
        self.assertEqual(res2.status, CandidateCheckStatus.DOMAIN_ERROR)
        self.assertEqual(res2.error_code, "DOMAIN_ERROR_DIVISION_BY_ZERO")

        # c = 3: 1/(1/(3-2)) = 1/1 = 1 -> VALID
        res3 = check_candidate(eq, 3)
        self.assertEqual(res3.status, CandidateCheckStatus.VALID)


class TestCandidateInputValidation(unittest.TestCase):
    """Verify deterministic candidate coercion and strict type rejection."""

    def test_accept_rational_candidate(self):
        eq = parse_equation("2*x = 3")
        res = check_candidate(eq, Rational(3, 2))
        self.assertEqual(res.status, CandidateCheckStatus.VALID)

    def test_accept_integer_candidate(self):
        eq = parse_equation("2*x = 4")
        res = check_candidate(eq, 2)
        self.assertEqual(res.status, CandidateCheckStatus.VALID)

    def test_accept_fraction_candidate(self):
        eq = parse_equation("2*x = 1")
        res = check_candidate(eq, Fraction(1, 2))
        self.assertEqual(res.status, CandidateCheckStatus.VALID)

    def test_accept_string_candidate(self):
        eq = parse_equation("2*x = 5")
        res = check_candidate(eq, "5/2")
        self.assertEqual(res.status, CandidateCheckStatus.VALID)

    def test_strictly_reject_float_candidate(self):
        eq = parse_equation("x = 2")
        with self.assertRaises(InvalidCandidateError) as cm:
            check_candidate(eq, 2.0)
        self.assertIn("Floating-point candidates are strictly forbidden", str(cm.exception))
        self.assertEqual(cm.exception.code, "ERR_INVALID_CANDIDATE_FLOAT")

    def test_strictly_reject_boolean_candidate(self):
        """In Python, bool is a subclass of int. It must be rejected."""
        eq = parse_equation("x = 1")
        with self.assertRaises(InvalidCandidateError):
            check_candidate(eq, True)

    def test_reject_malformed_string_candidate(self):
        eq = parse_equation("x = 2")
        with self.assertRaises(InvalidCandidateError) as cm:
            check_candidate(eq, "not_a_number")
        self.assertEqual(cm.exception.code, "ERR_INVALID_CANDIDATE_MALFORMED")

    def test_reject_unsupported_candidate_types(self):
        eq = parse_equation("x = 2")
        for bad in [None, [], {}, object()]:
            with self.assertRaises(InvalidCandidateError) as cm:
                check_candidate(eq, bad)
            self.assertEqual(cm.exception.code, "ERR_INVALID_CANDIDATE_TYPE")

    def test_reject_non_equation_ast(self):
        expr = parse_expression("2*x + 1")
        with self.assertRaises(TypeError) as cm:
            check_candidate(expr, 1)  # type: ignore
        self.assertIn("check_candidate requires an Equation AST", str(cm.exception))


class TestResourceBoundsAndImmutability(unittest.TestCase):
    """Verify evaluation budgets, error spans, and AST immutability."""

    def test_operation_budget_exhaustion(self):
        eq = parse_equation("x + x + x + x = 4*x")
        tight_budget = EvaluationBudget(max_operations=3)
        res = check_candidate(eq, 1, budget=tight_budget)
        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")

    def test_integer_bit_budget_exhaustion(self):
        eq = parse_equation("x^2 = 1")
        tight_budget = EvaluationBudget(max_integer_bits=10)
        res = check_candidate(eq, 1000, budget=tight_budget)
        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT")

    def test_candidate_bit_budget_exhaustion(self):
        eq = parse_equation("x = 1")
        tight_budget = EvaluationBudget(max_candidate_bits=10)
        res = check_candidate(eq, 2048, budget=tight_budget)
        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT")

    def test_ast_immutability_preservation(self):
        eq = parse_equation("x^2 - 4 = 0")
        original_left = eq.left
        check_candidate(eq, 2)
        self.assertIs(eq.left, original_left)

    def test_static_extraction_of_domain_obligations(self):
        eq = parse_equation("(x-1)/(x-2) + x^0 = 1")
        obligations = extract_domain_obligations(eq)
        self.assertEqual(len(obligations), 2)
        kinds = {ob.kind for ob in obligations}
        self.assertEqual(kinds, {"NONZERO_DENOMINATOR", "NONZERO_EXPONENT_BASE"})


class TestDirectExpressionEvaluator(unittest.TestCase):
    """Direct tests for evaluate_expression helper."""

    def test_evaluate_linear_expression(self):
        expr = parse_expression("2*x + 5")
        val = evaluate_expression(expr, {"x": Rational(3, 1)})
        self.assertEqual(val, Rational(11, 1))

    def test_evaluate_unbound_variable_raises(self):
        expr = parse_expression("x + 1")
        with self.assertRaises(UnsupportedEvaluationError) as cm:
            evaluate_expression(expr, {})
        self.assertEqual(cm.exception.code, "ERR_UNSUPPORTED_EVALUATION")

    def test_evaluate_unsupported_ast_node_raises(self):
        class DummyNode:
            span = None
        with self.assertRaises(UnsupportedEvaluationError):
            evaluate_expression(DummyNode(), {})  # type: ignore


class TestEvaluationRemediationS2R1(unittest.TestCase):
    """Targeted regressions specified in MKE PRODUCT-02A-S2-R1."""

    def test_mandatory_regression_shared_operation_budget(self):
        """Mandatory regression:
        Equation: x+x=x+x
        Candidate: x=1
        Budget max_operations=4 -> RESOURCE_EXHAUSTED
        Budget max_operations=6 -> VALID
        """
        eq = parse_equation("x+x=x+x")

        # 1. Budget max_operations=4 -> RESOURCE_EXHAUSTED
        res4 = check_candidate(eq, 1, budget=EvaluationBudget(max_operations=4))
        self.assertEqual(res4.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res4.is_defined)
        diag4 = dict(res4.diagnostics)
        self.assertEqual(diag4.get("branch"), "RIGHT_SIDE")
        self.assertEqual(diag4.get("steps_left"), "3")
        self.assertEqual(diag4.get("steps_right"), "2")
        self.assertEqual(diag4.get("total_steps"), "5")

        # 2. Budget max_operations=6 -> VALID
        res6 = check_candidate(eq, 1, budget=EvaluationBudget(max_operations=6))
        self.assertEqual(res6.status, CandidateCheckStatus.VALID)
        self.assertTrue(res6.is_valid)
        self.assertTrue(res6.is_defined)
        diag6 = dict(res6.diagnostics)
        self.assertEqual(diag6.get("exact_equality"), "True")
        self.assertEqual(diag6.get("steps_left"), "3")
        self.assertEqual(diag6.get("steps_right"), "3")
        self.assertEqual(diag6.get("total_steps"), "6")

    def test_evaluation_budget_parameter_validation(self):
        """Validate EvaluationBudget configuration: positive integers only, reject bool."""
        # Positive integer limits succeed
        b = EvaluationBudget(max_operations=100, max_integer_bits=512, max_candidate_bits=256)
        self.assertEqual(b.max_operations, 100)
        self.assertEqual(b.max_integer_bits, 512)
        self.assertEqual(b.max_candidate_bits, 256)

        # Reject bool
        with self.assertRaises(TypeError):
            EvaluationBudget(max_operations=True)
        with self.assertRaises(TypeError):
            EvaluationBudget(max_integer_bits=False)
        with self.assertRaises(TypeError):
            EvaluationBudget(max_candidate_bits=True)

        # Reject non-int
        with self.assertRaises(TypeError):
            EvaluationBudget(max_operations="1000")  # type: ignore
        with self.assertRaises(TypeError):
            EvaluationBudget(max_operations=10.5)  # type: ignore

        # Reject <= 0
        with self.assertRaises(ValueError):
            EvaluationBudget(max_operations=0)
        with self.assertRaises(ValueError):
            EvaluationBudget(max_operations=-5)
        with self.assertRaises(ValueError):
            EvaluationBudget(max_integer_bits=0)
        with self.assertRaises(ValueError):
            EvaluationBudget(max_candidate_bits=-10)

    def test_candidate_string_extremely_long_ceiling(self):
        """Classify oversize input as a resource failure before integer construction."""
        eq = parse_equation("x = 1")
        budget = EvaluationBudget(max_candidate_bits=256)

        # Candidate string length exceeds ceiling
        huge_str = "1" * 1000
        res = check_candidate(eq, huge_str, budget=budget)
        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT")

        # Leading-zero oversize abuse
        huge_zeros = "0" * 1000 + "1"
        res_zeros = check_candidate(eq, huge_zeros, budget=budget)
        self.assertEqual(res_zeros.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res_zeros.is_defined)

    def test_candidate_string_leading_zero_abuse(self):
        """Leading zeros on multi-digit numbers are forbidden by strict grammar."""
        eq = parse_equation("x = 1")
        for bad_zero in ["02", "00", "-05", "+007", "1/02", "1/00", "-00/3"]:
            with self.assertRaises(InvalidCandidateError) as cm:
                check_candidate(eq, bad_zero)
            self.assertEqual(cm.exception.code, "ERR_INVALID_CANDIDATE_MALFORMED")

        # Single zero and signed single zero are valid
        self.assertEqual(coerce_candidate("0", EvaluationBudget()), Rational(0, 1))
        self.assertEqual(coerce_candidate("-0", EvaluationBudget()), Rational(0, 1))
        self.assertEqual(coerce_candidate("+0", EvaluationBudget()), Rational(0, 1))

    def test_candidate_string_malformed_fractions(self):
        """Reject malformed, multiple-slash, non-ASCII, and whitespace strings."""
        eq = parse_equation("x = 1")
        malformed_inputs = [
            "1/2/3",
            "/5",
            "5/",
            "1/-",
            "++1",
            "--1",
            "1/0",
            "1 / 2",
            "1\t/2",
            "",
            "   ",
            "\u0661",  # Arabic-Indic digit 1
            "\uff11",  # Fullwidth digit 1
            "3.14",
            "abc",
        ]
        for bad in malformed_inputs:
            with self.assertRaises(InvalidCandidateError) as cm:
                check_candidate(eq, bad)
            self.assertEqual(cm.exception.code, "ERR_INVALID_CANDIDATE_MALFORMED")

    def test_candidate_string_valid_small_signed_rationals(self):
        """Valid small signed ASCII rational strings parse accurately into Rational."""
        b = EvaluationBudget()
        self.assertEqual(coerce_candidate("3", b), Rational(3, 1))
        self.assertEqual(coerce_candidate("+5", b), Rational(5, 1))
        self.assertEqual(coerce_candidate("-7", b), Rational(-7, 1))
        self.assertEqual(coerce_candidate("3/4", b), Rational(3, 4))
        self.assertEqual(coerce_candidate("-3/4", b), Rational(-3, 4))
        self.assertEqual(coerce_candidate("+5/2", b), Rational(5, 2))
        self.assertEqual(coerce_candidate("6/-8", b), Rational(-3, 4))
        self.assertEqual(coerce_candidate("-10/-2", b), Rational(5, 1))

    def test_three_valued_definedness_contract(self):
        """Verify three-valued definedness contract:
        - VALID / INVALID -> True
        - DOMAIN_ERROR -> False
        - RESOURCE_EXHAUSTED / UNSUPPORTED -> None (UNKNOWN)
        """
        eq = parse_equation("x = 1")

        # VALID -> True
        res_valid = check_candidate(eq, 1)
        self.assertIs(res_valid.is_defined, True)

        # INVALID -> True
        res_invalid = check_candidate(eq, 2)
        self.assertIs(res_invalid.is_defined, True)

        # DOMAIN_ERROR -> False
        eq_div0 = parse_equation("1/x = 1")
        res_domain = check_candidate(eq_div0, 0)
        self.assertIs(res_domain.is_defined, False)

        # RESOURCE_EXHAUSTED -> None (UNKNOWN)
        res_resource = check_candidate(eq, 1, budget=EvaluationBudget(max_operations=1))
        self.assertIs(res_resource.is_defined, None)

        # Direct test on CandidateCheckResult with UNSUPPORTED
        unsupported_res = CandidateCheckResult(
            status=CandidateCheckStatus.UNSUPPORTED,
            candidate=Rational(1, 1),
            equation=eq,
        )
        self.assertIs(unsupported_res.is_defined, None)


class TestResidualBudgetRemediationS2R2(unittest.TestCase):
    """Targeted regressions for S2-R2 bounded residual arithmetic."""

    def test_residual_exceeding_integer_bit_budget_returns_resource_exhausted(self):
        """Required regression:
        Equation x = 1/7, candidate 1/5, max_integer_bits=4.
        Both evaluated sides fit the budget, but residual 2/35 (35 requires 6 bits) exceeds max_integer_bits=4.
        Result must be RESOURCE_EXHAUSTED with definedness UNKNOWN (None).
        """
        eq = parse_equation("x = 1/7")
        budget = EvaluationBudget(max_integer_bits=4)
        res = check_candidate(eq, "1/5", budget=budget)

        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.left_value, Rational(1, 5))
        self.assertEqual(res.right_value, Rational(1, 7))
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT")
        self.assertIn("Diagnostic residual integer bit length", res.error_message or "")
        diag = dict(res.diagnostics)
        self.assertEqual(diag.get("stage"), "RESIDUAL_CALCULATION")

    def test_equal_values_with_tight_budget(self):
        """Equal values yield residual 0, which safely fits tight integer bit budget."""
        eq = parse_equation("x = 1/7")
        budget = EvaluationBudget(max_integer_bits=4)
        res = check_candidate(eq, "1/7", budget=budget)

        self.assertEqual(res.status, CandidateCheckStatus.VALID)
        self.assertTrue(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(1, 7))
        self.assertEqual(res.right_value, Rational(1, 7))
        diag = dict(res.diagnostics)
        self.assertEqual(diag.get("exact_equality"), "True")
        self.assertEqual(diag.get("residual"), "0")

    def test_negative_residual_difference_exceeding_budget(self):
        """Negative difference (left < right):
        Equation x = 1/5, candidate 1/7, max_integer_bits=4.
        left - right = 1/7 - 1/5 = -2/35.
        Residual abs(-2/35) = 2/35 exceeds max_integer_bits=4 -> RESOURCE_EXHAUSTED.
        """
        eq = parse_equation("x = 1/5")
        budget = EvaluationBudget(max_integer_bits=4)
        res = check_candidate(eq, "1/7", budget=budget)

        self.assertEqual(res.status, CandidateCheckStatus.RESOURCE_EXHAUSTED)
        self.assertIsNone(res.is_defined)
        self.assertEqual(res.left_value, Rational(1, 7))
        self.assertEqual(res.right_value, Rational(1, 5))
        self.assertEqual(res.error_code, "ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT")

    def test_negative_residual_difference_fitting_budget(self):
        """Negative difference (left < right) fitting normal budget:
        Equation x = 5, candidate 2, max_integer_bits=10.
        left - right = 2 - 5 = -3.
        Residual abs(-3) = 3 fits budget -> INVALID with definedness True.
        """
        eq = parse_equation("x = 5")
        budget = EvaluationBudget(max_integer_bits=10)
        res = check_candidate(eq, 2, budget=budget)

        self.assertEqual(res.status, CandidateCheckStatus.INVALID)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(2, 1))
        self.assertEqual(res.right_value, Rational(5, 1))
        diag = dict(res.diagnostics)
        self.assertEqual(diag.get("exact_equality"), "False")
        self.assertEqual(diag.get("residual"), "3")

    def test_normal_budget_invalid_candidate(self):
        """Normal budget with x = 1/7, candidate 1/5:
        Residual 2/35 fits within default max_integer_bits (4096).
        Returns INVALID with definedness True.
        """
        eq = parse_equation("x = 1/7")
        res = check_candidate(eq, "1/5")

        self.assertEqual(res.status, CandidateCheckStatus.INVALID)
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_defined)
        self.assertEqual(res.left_value, Rational(1, 5))
        self.assertEqual(res.right_value, Rational(1, 7))
        diag = dict(res.diagnostics)
        self.assertEqual(diag.get("exact_equality"), "False")
        self.assertEqual(diag.get("residual"), "2/35")


if __name__ == "__main__":
    unittest.main()
