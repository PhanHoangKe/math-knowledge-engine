"""Comprehensive test suite for S1-01 Exact Normalizer & Typed Intake Error Mapping.

Verifies:
1. Exact AST polynomial normalization in Q[x] for degree <= 2.
2. Canonical coefficient extraction (a, b, c) for quadratic and degenerate equations.
3. Fail-closed rejection of high-degree products, non-polynomial division, division by zero, and 0^0.
4. Deterministic typed parser error hierarchy (UnsupportedVariableError, UnsupportedSyntaxError, UnsupportedExponentError).
5. Deterministic parser-exception to application-error mapping without string inspection.
6. Exact resource boundaries: length 256/257, nesting 16/17, token count 64/65.
7. Adversarial invariant checks (no float authority, span preservation, algebraic equivalence).
"""

from __future__ import annotations

import os
import sys
import unittest

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.application.errors import (
    ApplicationError,
    ApplicationErrorCode,
    map_parser_exception_to_application_error,
)
from mke_product.application.normalizer import (
    PolynomialQDegree2,
    normalize_equation,
    normalize_expression,
    normalize_raw_equation,
)
from mke_product.core.rational import Rational
from mke_product.parser import (
    ImplicitMultiplicationError,
    InputBoundsExceededError,
    LexerError,
    MAX_TOKEN_COUNT,
    ParserError,
    Span,
    Token,
    TokenType,
    UnsupportedExponentError,
    UnsupportedSyntaxError,
    UnsupportedVariableError,
    parse,
    tokenize,
)


class TestApplicationNormalizerMandatoryCases(unittest.TestCase):
    """Tests for all mandatory normalization cases specified in the directive."""

    def test_standard_monic_quadratic(self):
        # x^2 - 5*x + 6 = 0 -> (1, -5, 6)
        a, b, c = normalize_raw_equation("x^2 - 5*x + 6 = 0")
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(b, Rational(-5, 1))
        self.assertEqual(c, Rational(6, 1))

    def test_unnormalized_quadratic_sides(self):
        # x^2 + 6 = 5*x -> (1, -5, 6)
        a, b, c = normalize_raw_equation("x^2 + 6 = 5*x")
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(b, Rational(-5, 1))
        self.assertEqual(c, Rational(6, 1))

    def test_factored_form_quadratic(self):
        # (x - 2)*(x - 3) = 0 -> (1, -5, 6)
        a, b, c = normalize_raw_equation("(x - 2)*(x - 3) = 0")
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(b, Rational(-5, 1))
        self.assertEqual(c, Rational(6, 1))

    def test_perfect_square_quadratic(self):
        # (x + 1)^2 = 0 -> (1, 2, 1)
        a, b, c = normalize_raw_equation("(x + 1)^2 = 0")
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(b, Rational(2, 1))
        self.assertEqual(c, Rational(1, 1))

    def test_fractional_coefficients_quadratic(self):
        # (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> (1/2, -5/4, 3/4)
        a, b, c = normalize_raw_equation("(1/2)*x^2 - (5/4)*x + 3/4 = 0")
        self.assertEqual(a, Rational(1, 2))
        self.assertEqual(b, Rational(-5, 4))
        self.assertEqual(c, Rational(3, 4))

    def test_degenerate_linear(self):
        # 2*x - 4 = 0 -> (0, 2, -4)
        a, b, c = normalize_raw_equation("2*x - 4 = 0")
        self.assertEqual(a, Rational(0, 1))
        self.assertEqual(b, Rational(2, 1))
        self.assertEqual(c, Rational(-4, 1))

    def test_degenerate_identity(self):
        # 0 = 0 -> (0, 0, 0)
        a, b, c = normalize_raw_equation("0 = 0")
        self.assertEqual(a, Rational(0, 1))
        self.assertEqual(b, Rational(0, 1))
        self.assertEqual(c, Rational(0, 1))

    def test_degenerate_contradiction(self):
        # 1 = 0 -> (0, 0, 1)
        a, b, c = normalize_raw_equation("1 = 0")
        self.assertEqual(a, Rational(0, 1))
        self.assertEqual(b, Rational(0, 1))
        self.assertEqual(c, Rational(1, 1))


class TestApplicationNormalizerFailClosedCases(unittest.TestCase):
    """Tests confirming strict fail-closed rejection of non-polynomial and out-of-scope expressions."""

    def test_reject_variable_in_denominator(self):
        # 1/x = 0 -> NON_POLYNOMIAL_INPUT
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("1/x = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.NON_POLYNOMIAL_INPUT)

    def test_reject_expression_with_variable_denominator(self):
        # 2/(x + 1) = 0 -> NON_POLYNOMIAL_INPUT
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("2/(x + 1) = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.NON_POLYNOMIAL_INPUT)

    def test_reject_division_by_zero_literal(self):
        # x^2 / 0 = 0 -> DIVISION_BY_ZERO
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("x^2 / 0 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DIVISION_BY_ZERO)

    def test_reject_division_by_zero_expression(self):
        # x^2 / (3 - 3) = 0 -> DIVISION_BY_ZERO
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("x^2 / (3 - 3) = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DIVISION_BY_ZERO)

    def test_reject_degree_3_product(self):
        # (x^2 + 1)*(x + 1) = 0 -> DEGREE_OUT_OF_SCOPE
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("(x^2 + 1)*(x + 1) = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_reject_degree_4_product(self):
        # (x^2 + 1)*(x^2 - 1) = 0 -> DEGREE_OUT_OF_SCOPE
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("(x^2 + 1)*(x^2 - 1) = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_reject_degree_4_power(self):
        # (x^2 + 1)^2 = 0 -> DEGREE_OUT_OF_SCOPE
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("(x^2 + 1)^2 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)

    def test_reject_zero_to_zero_indeterminate(self):
        # 0^0 = 0 -> NORMALIZATION_ERROR (0^0 is indeterminate)
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("0^0 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.NORMALIZATION_ERROR)

    def test_reject_zero_expression_to_zero(self):
        # (x - x)^0 = 1 -> NORMALIZATION_ERROR
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("(x - x)^0 = 1")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.NORMALIZATION_ERROR)

    def test_valid_nonzero_base_to_zero(self):
        # (x + 1)^0 = 1 -> 1 = 1 -> (0, 0, 0)
        a, b, c = normalize_raw_equation("(x + 1)^0 = 1")
        self.assertEqual(a, Rational(0, 1))
        self.assertEqual(b, Rational(0, 1))
        self.assertEqual(c, Rational(0, 1))


class TestTypedParserErrorClassification(unittest.TestCase):
    """Tests verifying typed parser exception hierarchy and mapping without string inspection."""

    def test_unsupported_variable_classification(self):
        # y^2 - 4 = 0 -> UnsupportedVariableError -> UNSUPPORTED_VARIABLE
        with self.assertRaises(UnsupportedVariableError):
            tokenize("y^2 - 4 = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("y^2 - 4 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.UNSUPPORTED_VARIABLE)
        self.assertEqual(ctx.exception.span, Span(0, 1))

    def test_unsupported_single_variable_t(self):
        # 2*t + 1 = 0 -> UnsupportedVariableError
        with self.assertRaises(UnsupportedVariableError):
            tokenize("2*t + 1 = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("2*t + 1 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.UNSUPPORTED_VARIABLE)
        self.assertEqual(ctx.exception.span, Span(2, 3))

    def test_unsupported_syntax_function_name(self):
        # sin(x) = 0 -> UnsupportedSyntaxError -> UNSUPPORTED_SYNTAX
        with self.assertRaises(UnsupportedSyntaxError):
            tokenize("sin(x) = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("sin(x) = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.UNSUPPORTED_SYNTAX)
        self.assertEqual(ctx.exception.span, Span(0, 3))

    def test_unsupported_syntax_multi_char_identifier(self):
        # foo = 0 -> UnsupportedSyntaxError
        with self.assertRaises(UnsupportedSyntaxError):
            tokenize("foo = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("foo = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.UNSUPPORTED_SYNTAX)
        self.assertEqual(ctx.exception.span, Span(0, 3))

    def test_unsupported_exponent_value(self):
        # x^3 = 0 -> UnsupportedExponentError -> DEGREE_OUT_OF_SCOPE
        with self.assertRaises(UnsupportedExponentError):
            parse("x^3 = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("x^3 = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.DEGREE_OUT_OF_SCOPE)
        self.assertEqual(ctx.exception.span, Span(2, 3))

    def test_implicit_multiplication_error(self):
        # 2x = 4 -> ImplicitMultiplicationError -> IMPLICIT_MULTIPLICATION_UNSUPPORTED
        with self.assertRaises(ImplicitMultiplicationError):
            tokenize("2x = 4")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("2x = 4")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED)

    def test_syntax_error_malformed_equation(self):
        # x^2 + = 0 -> ParserError -> SYNTAX_ERROR
        with self.assertRaises(ParserError):
            parse("x^2 + = 0")

        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation("x^2 + = 0")
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.SYNTAX_ERROR)


class TestResourceBoundaries(unittest.TestCase):
    """Explicit tests for parser and application resource boundaries."""

    def test_length_boundary_256_passes(self):
        # Length exactly 256 chars (x^2 followed by whitespace and " = 0")
        fixed = "x^2  = 0"
        needed = 256 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 256)
        a, b, c = normalize_raw_equation(padded)
        self.assertEqual(a, Rational(1, 1))

    def test_length_boundary_257_fails(self):
        # Length 257 chars -> INPUT_LIMIT_EXCEEDED
        fixed = "x^2  = 0"
        needed = 257 - len(fixed)
        padded = "x^2 " + (" " * needed) + " = 0"
        self.assertEqual(len(padded), 257)
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation(padded)
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)

    def test_nesting_depth_boundary_16_passes(self):
        # Depth exactly 16 pairs of parens
        nested = "(" * 16 + "x^2 - 1" + ")" * 16 + " = 0"
        a, b, c = normalize_raw_equation(nested)
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(c, Rational(-1, 1))

    def test_nesting_depth_boundary_17_fails(self):
        # Depth 17 pairs of parens -> INPUT_LIMIT_EXCEEDED
        nested = "(" * 17 + "x^2 - 1" + ")" * 17 + " = 0"
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation(nested)
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)

    def test_token_count_boundary_64_passes(self):
        # Exact 64 non-EOF tokens:
        # 1 leading unary '+' + 31 variable 'x' + 30 binary '+' + 1 '=' + 1 integer '0' = 64 non-EOF tokens.
        terms = ["+x"] + ["x"] * 30
        expr = " + ".join(terms) + " = 0"
        tokens = tokenize(expr)
        # Token list contains 64 non-EOF tokens + 1 EOF token = 65 tokens total
        self.assertEqual(len(tokens) - 1, MAX_TOKEN_COUNT)
        self.assertEqual(len(tokens) - 1, 64)
        self.assertEqual(tokens[-1].type, TokenType.EOF)

        a, b, c = normalize_raw_equation(expr)
        self.assertEqual(a, Rational(0, 1))
        self.assertEqual(b, Rational(31, 1))
        self.assertEqual(c, Rational(0, 1))

    def test_token_count_boundary_65_fails(self):
        # Exact 65 non-EOF tokens:
        # 32 'x' + 31 binary '+' + 1 '=' + 1 '0' = 65 non-EOF tokens > 64 limit
        expr = " + ".join(["x"] * 32) + " = 0"
        with self.assertRaises(ApplicationError) as ctx:
            normalize_raw_equation(expr)
        self.assertEqual(ctx.exception.error_code, ApplicationErrorCode.INPUT_LIMIT_EXCEEDED)


class TestAdversarialAndInvariantChecks(unittest.TestCase):
    """Adversarial checks proving mathematical purity, no float authority, and span accuracy."""

    def test_no_float_authority_in_polynomial(self):
        # PolynomialQDegree2 must strictly reject float coefficients with TypeError
        with self.assertRaises(TypeError):
            PolynomialQDegree2(1.0, Rational(0, 1), Rational(0, 1))  # type: ignore

        with self.assertRaises(TypeError):
            PolynomialQDegree2(Rational(1, 1), 0.5, Rational(0, 1))  # type: ignore

    def test_exact_rational_scalar_division(self):
        # (2*x^2 - 4*x + 6) / 2 = 0 -> (1, -2, 3)
        a, b, c = normalize_raw_equation("(2*x^2 - 4*x + 6) / 2 = 0")
        self.assertEqual(a, Rational(1, 1))
        self.assertEqual(b, Rational(-2, 1))
        self.assertEqual(c, Rational(3, 1))

    def test_algebraic_equivalence_invariance(self):
        # Multiple syntactically different expressions of (x - 2)(x - 3) = 0 must normalize to identical Rational tuples
        r1 = normalize_raw_equation("x^2 - 5*x + 6 = 0")
        r2 = normalize_raw_equation("x^2 + 6 = 5*x")
        r3 = normalize_raw_equation("(x - 2)*(x - 3) = 0")
        r4 = normalize_raw_equation("x*x - 3*x - 2*x + 6 = 0")
        self.assertEqual(r1, r2)
        self.assertEqual(r2, r3)
        self.assertEqual(r3, r4)

    def test_error_mapping_without_message_inspection(self):
        # Even if exception message is manipulated, type-based mapping is deterministic
        custom_exc = UnsupportedVariableError("completely arbitrary message", Span(5, 6))
        app_err = map_parser_exception_to_application_error(custom_exc)
        self.assertEqual(app_err.error_code, ApplicationErrorCode.UNSUPPORTED_VARIABLE)
        self.assertEqual(app_err.span, Span(5, 6))


if __name__ == "__main__":
    unittest.main()
