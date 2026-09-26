"""Independent specification and developer tests for S2 Exact Semantic Evaluation and Candidate Verification.

Conforms strictly to MKE PRODUCT-01-R2 / PRODUCT-02A-S2:
- Original-domain obligations checked on unreduced AST.
- 0^0 is strictly undefined in Real domain.
- Multiplication by zero does not mask undefined subtrees.
- Strict rational equality; no float tolerances or approximations.
- Conservative resource limits and immutability guarantees.
"""
import os
import sys
from fractions import Fraction
import pytest

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


class TestMandatoryCriticalRegressions:
    """Verify all critical mathematical regressions required by S2 specification."""

    def test_rational_fraction_domain_exclusion(self):
        """(x-1)/(x-1) = 1: c=1 is DOMAIN_ERROR; c=2 is VALID."""
        eq = parse_equation("(x-1)/(x-1) = 1")

        # c = 1: denominator (1-1) = 0 -> DOMAIN_ERROR
        res1 = check_candidate(eq, 1)
        assert res1.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res1.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"
        assert not res1.is_valid
        assert not res1.is_defined
        assert res1.left_value is None

        # c = 2: (2-1)/(2-1) = 1/1 = 1 -> VALID
        res2 = check_candidate(eq, 2)
        assert res2.status == CandidateCheckStatus.VALID
        assert res2.is_valid
        assert res2.is_defined
        assert res2.left_value == Rational(1, 1)
        assert res2.right_value == Rational(1, 1)

    def test_variable_raised_to_zero(self):
        """x^0 = 1: c=0 is DOMAIN_ERROR (0^0 undefined); c=2 is VALID (2^0 = 1)."""
        eq = parse_equation("x^0 = 1")

        # c = 0: 0^0 is undefined in Real domain
        res0 = check_candidate(eq, 0)
        assert res0.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res0.error_code == "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO"
        assert not res0.is_valid
        assert not res0.is_defined

        # c = 2: 2^0 = 1 == 1 -> VALID
        res2 = check_candidate(eq, 2)
        assert res2.status == CandidateCheckStatus.VALID
        assert res2.left_value == Rational(1, 1)
        assert res2.right_value == Rational(1, 1)

    def test_grouped_expression_raised_to_zero(self):
        """(x-1)^0 = 1: c=1 is DOMAIN_ERROR (0^0); c=3 is VALID (2^0 = 1)."""
        eq = parse_equation("(x-1)^0 = 1")

        # c = 1: (1-1)^0 = 0^0 -> DOMAIN_ERROR
        res1 = check_candidate(eq, 1)
        assert res1.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res1.error_code == "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO"

        # c = 3: (3-1)^0 = 2^0 = 1 -> VALID
        res3 = check_candidate(eq, 3)
        assert res3.status == CandidateCheckStatus.VALID
        assert res3.left_value == Rational(1, 1)

    def test_quadratic_equation_candidate_checking(self):
        """x^2 - 4 = 0: c=2 is VALID, c=-2 is VALID, c=3 is INVALID."""
        eq = parse_equation("x^2 - 4 = 0")

        res_pos = check_candidate(eq, 2)
        assert res_pos.status == CandidateCheckStatus.VALID
        assert res_pos.left_value == Rational(0, 1)
        assert res_pos.right_value == Rational(0, 1)

        res_neg = check_candidate(eq, -2)
        assert res_neg.status == CandidateCheckStatus.VALID
        assert res_neg.left_value == Rational(0, 1)

        res_wrong = check_candidate(eq, 3)
        assert res_wrong.status == CandidateCheckStatus.INVALID
        assert res_wrong.is_defined
        assert not res_wrong.is_valid
        assert res_wrong.left_value == Rational(5, 1)
        assert res_wrong.right_value == Rational(0, 1)

    def test_unary_minus_power_precedence_negative_x_squared(self):
        """-x^2 = -4: parsed as -(x^2) = -4; c=2 is VALID."""
        eq = parse_equation("-x^2 = -4")
        res = check_candidate(eq, 2)
        assert res.status == CandidateCheckStatus.VALID
        assert res.left_value == Rational(-4, 1)
        assert res.right_value == Rational(-4, 1)

    def test_grouped_negative_base_squared(self):
        """(-x)^2 = 4: c=2 is VALID."""
        eq = parse_equation("(-x)^2 = 4")
        res = check_candidate(eq, 2)
        assert res.status == CandidateCheckStatus.VALID
        assert res.left_value == Rational(4, 1)
        assert res.right_value == Rational(4, 1)

    def test_unary_sign_with_multiplication(self):
        """-x*2 = -4: c=2 is VALID."""
        eq = parse_equation("-x*2 = -4")
        res = check_candidate(eq, 2)
        assert res.status == CandidateCheckStatus.VALID
        assert res.left_value == Rational(-4, 1)
        assert res.right_value == Rational(-4, 1)

    def test_identity_equation_zero_mul_x_equals_zero(self):
        """0*x = 0: every rational candidate is VALID.
        Candidate checking verifies substitution in Q, not confused with DomainSet(R).
        """
        eq = parse_equation("0*x = 0")
        for c in [0, 1, -1, 5, Rational(-13, 17), 10**50]:
            res = check_candidate(eq, c)
            assert res.status == CandidateCheckStatus.VALID
            assert res.left_value == Rational(0, 1)
            assert res.right_value == Rational(0, 1)

    def test_contradiction_equation_zero_mul_x_equals_five(self):
        """0*x = 5: every rational candidate is INVALID."""
        eq = parse_equation("0*x = 5")
        for c in [0, 1, -5, 5, Rational(1, 2)]:
            res = check_candidate(eq, c)
            assert res.status == CandidateCheckStatus.INVALID
            assert res.left_value == Rational(0, 1)
            assert res.right_value == Rational(5, 1)

    def test_strict_equality_and_tiny_residual_no_floating_approximation(self):
        """x = 0: c=1/10^100 is INVALID (not approximately valid); c=0 is VALID."""
        eq = parse_equation("x = 0")

        # c = 1 / 10^100
        tiny_c = Rational(1, 10**100)
        res_tiny = check_candidate(eq, tiny_c)
        assert res_tiny.status == CandidateCheckStatus.INVALID
        assert res_tiny.left_value == tiny_c
        assert res_tiny.right_value == Rational(0, 1)

        # c = 0
        res_zero = check_candidate(eq, 0)
        assert res_zero.status == CandidateCheckStatus.VALID

    def test_constant_zero_denominator_in_variable_expression(self):
        """1/(x-x) = 0: DOMAIN_ERROR for every rational candidate."""
        eq = parse_equation("1/(x-x) = 0")
        for c in [0, 1, 2, -10]:
            res = check_candidate(eq, c)
            assert res.status == CandidateCheckStatus.DOMAIN_ERROR
            assert res.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"


class TestDomainSafetyAndSubtreeMasking:
    """Rigorous tests ensuring domain undefinedness is never masked by arithmetic operations."""

    def test_multiplication_by_zero_does_not_mask_division_by_zero(self):
        """0 * (1/x) = 0 at x=0 must be DOMAIN_ERROR, not VALID."""
        eq = parse_equation("0*(1/x) = 0")
        res = check_candidate(eq, 0)
        assert res.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"

    def test_multiplication_with_zero_on_right_does_not_mask_division_by_zero(self):
        """(1/x)*0 = 0 at x=0 must be DOMAIN_ERROR."""
        eq = parse_equation("(1/x)*0 = 0")
        res = check_candidate(eq, 0)
        assert res.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"

    def test_multiplication_by_zero_does_not_mask_zero_to_zero(self):
        """0 * (x^0) = 0 at x=0 must be DOMAIN_ERROR because 0^0 is undefined."""
        eq = parse_equation("0*(x^0) = 0")
        res = check_candidate(eq, 0)
        assert res.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res.error_code == "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO"

    def test_addition_and_subtraction_do_not_mask_domain_errors(self):
        """0 + (1/x) = 0 and 0 - (x^0) = 0 at x=0 must be DOMAIN_ERROR."""
        eq_add = parse_equation("0 + (1/x) = 0")
        assert check_candidate(eq_add, 0).status == CandidateCheckStatus.DOMAIN_ERROR

        eq_sub = parse_equation("0 - (x^0) = 0")
        assert check_candidate(eq_sub, 0).status == CandidateCheckStatus.DOMAIN_ERROR

    def test_literal_division_by_zero(self):
        """Literal 1/0 in expression causes DOMAIN_ERROR."""
        eq = parse_equation("x = 1/0")
        res = check_candidate(eq, 5)
        assert res.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"

    def test_nested_denominators(self):
        """1/(1/(x-2)) = 1: x=2 is DOMAIN_ERROR; x=3 is VALID."""
        eq = parse_equation("1/(1/(x-2)) = 1")

        # c = 2: inner denominator (2-2) = 0 -> DOMAIN_ERROR
        res2 = check_candidate(eq, 2)
        assert res2.status == CandidateCheckStatus.DOMAIN_ERROR
        assert res2.error_code == "DOMAIN_ERROR_DIVISION_BY_ZERO"

        # c = 3: 1/(1/(3-2)) = 1/1 = 1 -> VALID
        res3 = check_candidate(eq, 3)
        assert res3.status == CandidateCheckStatus.VALID


class TestCandidateInputValidation:
    """Verify deterministic candidate coercion and strict type rejection."""

    def test_accept_rational_candidate(self):
        eq = parse_equation("2*x = 3")
        res = check_candidate(eq, Rational(3, 2))
        assert res.status == CandidateCheckStatus.VALID

    def test_accept_integer_candidate(self):
        eq = parse_equation("2*x = 4")
        res = check_candidate(eq, 2)
        assert res.status == CandidateCheckStatus.VALID

    def test_accept_fraction_candidate(self):
        eq = parse_equation("2*x = 1")
        res = check_candidate(eq, Fraction(1, 2))
        assert res.status == CandidateCheckStatus.VALID

    def test_accept_string_candidate(self):
        eq = parse_equation("2*x = 5")
        res = check_candidate(eq, "5/2")
        assert res.status == CandidateCheckStatus.VALID

    def test_strictly_reject_float_candidate(self):
        eq = parse_equation("x = 2")
        with pytest.raises(InvalidCandidateError) as exc_info:
            check_candidate(eq, 2.0)
        assert "Floating-point candidates are strictly forbidden" in str(exc_info.value)
        assert exc_info.value.code == "ERR_INVALID_CANDIDATE_FLOAT"

    def test_strictly_reject_boolean_candidate(self):
        """In Python, bool is a subclass of int. It must be rejected."""
        eq = parse_equation("x = 1")
        with pytest.raises(InvalidCandidateError):
            check_candidate(eq, True)

    def test_reject_malformed_string_candidate(self):
        eq = parse_equation("x = 2")
        with pytest.raises(InvalidCandidateError) as exc_info:
            check_candidate(eq, "not_a_number")
        assert exc_info.value.code == "ERR_INVALID_CANDIDATE_MALFORMED"

    def test_reject_unsupported_candidate_types(self):
        eq = parse_equation("x = 2")
        for bad in [None, [], {}, object()]:
            with pytest.raises(InvalidCandidateError) as exc_info:
                check_candidate(eq, bad)
            assert exc_info.value.code == "ERR_INVALID_CANDIDATE_TYPE"

    def test_reject_non_equation_ast(self):
        expr = parse_expression("2*x + 1")
        with pytest.raises(TypeError) as exc_info:
            check_candidate(expr, 1)  # type: ignore
        assert "check_candidate requires an Equation AST" in str(exc_info.value)


class TestResourceBoundsAndImmutability:
    """Verify evaluation budgets, error spans, and AST immutability."""

    def test_operation_budget_exhaustion(self):
        """When evaluation steps exceed budget, return RESOURCE_EXHAUSTED."""
        eq = parse_equation("x + x + x + x + x + x = 6")
        tiny_budget = EvaluationBudget(max_operations=3)
        res = check_candidate(eq, 1, budget=tiny_budget)
        assert res.status == CandidateCheckStatus.RESOURCE_EXHAUSTED
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT"
        assert not res.is_valid
        assert not res.is_defined

    def test_integer_bit_budget_exhaustion(self):
        """When intermediate integers exceed bit budget, return RESOURCE_EXHAUSTED."""
        eq = parse_equation("x = 1000")
        tiny_budget = EvaluationBudget(max_integer_bits=8)  # 255 max
        res = check_candidate(eq, 1000, budget=tiny_budget)
        assert res.status == CandidateCheckStatus.RESOURCE_EXHAUSTED
        assert res.error_code == "ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT"

    def test_candidate_bit_budget_exhaustion(self):
        """When candidate integers exceed candidate bit budget, raise EvaluationResourceLimitError."""
        eq = parse_equation("x = 0")
        tiny_budget = EvaluationBudget(max_candidate_bits=10)
        with pytest.raises(EvaluationResourceLimitError) as exc_info:
            check_candidate(eq, 2**20, budget=tiny_budget)
        assert exc_info.value.code == "ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT"

    def test_ast_immutability_preservation(self):
        """Evaluation must not mutate the AST nodes or their spans in any way."""
        eq = parse_equation("2*x + 3 = 7")
        dict_before = eq.to_dict()

        res = check_candidate(eq, 2)
        assert res.status == CandidateCheckStatus.VALID

        dict_after = eq.to_dict()
        assert dict_before == dict_after

    def test_static_extraction_of_domain_obligations(self):
        """extract_domain_obligations statically extracts denominator and power-0 obligations."""
        eq = parse_equation("(x-1)/(x-2) + (x+3)^0 = 0")
        obligations = extract_domain_obligations(eq)

        assert len(obligations) == 2
        kinds = {ob.kind for ob in obligations}
        assert kinds == {"NONZERO_DENOMINATOR", "NONZERO_EXPONENT_BASE"}

        # Obligations report correct spans
        for ob in obligations:
            d = ob.to_dict()
            assert "span" in d
            assert "target_ast" in d
            assert "description" in d


class TestDirectExpressionEvaluator:
    """Direct tests for evaluate_expression function."""

    def test_evaluate_linear_expression(self):
        expr = parse_expression("3*x + 5")
        val = evaluate_expression(expr, {"x": Rational(2, 1)})
        assert val == Rational(11, 1)

    def test_evaluate_unbound_variable_raises(self):
        expr = parse_expression("x + 1")
        with pytest.raises(UnsupportedEvaluationError) as exc_info:
            evaluate_expression(expr, {})
        assert "Unbound variable" in str(exc_info.value)

    def test_evaluate_unsupported_ast_node_raises(self):
        # Construct an artificial ASTNode
        from mke_product.parser.ast import ASTNode
        from mke_product.parser.errors import Span

        class FakeNode(ASTNode):
            @property
            def span(self):
                return Span(0, 0)
            def walk(self):
                yield self
            def variables(self):
                return set()
            def to_dict(self):
                return {}

        with pytest.raises(UnsupportedEvaluationError):
            evaluate_expression(FakeNode(), {})
