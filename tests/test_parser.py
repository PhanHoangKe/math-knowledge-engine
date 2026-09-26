"""Comprehensive unit test suite for the mathematical lexer, parser, and immutable AST.

Covers:
- Mandatory representative cases:
    * 2*x + 3 = 7
    * -x^2 = 1 (parsed as -(x^2))
    * (-x)^2 = 1 (parsed as ((-x))^2)
    * 1/2x = 1 (REJECTED as implicit multiplication)
    * 2x = 4 (REJECTED as implicit multiplication)
    * (x-1)/(x-1) = 1 (PARSED, preserves both quotient subtrees)
    * x^0 = 1 (PARSED, preserves power node)
    * 0^0 = 1 (PARSED, definedness deferred to later stage)
    * x^2 - 4 = 0 (PARSED, quadratic expression retained)
    * x^3 = 1 (REJECTED, exponent not in {0, 1, 2})
- Operator precedence and associativity (left-associative +, -, *, /).
- Exact frozen unary sign placement: unary operators only at expression level, not after binary operators without grouping.
- Source spans for tokens and AST nodes.
- AST immutability and node walking.
- Input bounds enforcement (length, token count, parentheses nesting depth).
- Deterministic typed errors (LexerError, ParserError, ImplicitMultiplicationError, InputBoundsExceededError).
"""

import os
import sys
import unittest

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.parser import (
    parse,
    tokenize,
    Token,
    TokenType,
    Span,
    Equation,
    BinaryOp,
    UnaryOp,
    Power,
    Group,
    Variable,
    IntegerLiteral,
    LexerError,
    ParserError,
    ImplicitMultiplicationError,
    InputBoundsExceededError,
)


class TestParserMandatoryRepresentativeCases(unittest.TestCase):
    """Tests for the 10 mandatory representative cases specified in the S1 task."""

    def test_case_linear_explicit(self):
        # Case 1: 2*x + 3 = 7
        eq = parse("2*x + 3 = 7")
        self.assertIsInstance(eq, Equation)
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "+")
        self.assertIsInstance(eq.left.left, BinaryOp)
        self.assertEqual(eq.left.left.op, "*")
        self.assertEqual(eq.left.left.left, IntegerLiteral(2, Span(0, 1)))
        self.assertEqual(eq.left.left.right, Variable("x", Span(2, 3)))
        self.assertEqual(eq.left.right, IntegerLiteral(3, Span(6, 7)))
        self.assertEqual(eq.right, IntegerLiteral(7, Span(10, 11)))

    def test_case_neg_x_squared(self):
        # Case 2: -x^2 = 1 must mean -(x^2)
        eq = parse("-x^2 = 1")
        self.assertIsInstance(eq.left, UnaryOp)
        self.assertEqual(eq.left.op, "-")
        self.assertIsInstance(eq.left.operand, Power)
        self.assertEqual(eq.left.operand.base, Variable("x", Span(1, 2)))
        self.assertEqual(eq.left.operand.exponent, IntegerLiteral(2, Span(3, 4)))
        self.assertEqual(eq.right, IntegerLiteral(1, Span(7, 8)))

    def test_case_grouped_neg_x_squared(self):
        # Case 3: (-x)^2 = 1 must retain the grouped negative base
        eq = parse("(-x)^2 = 1")
        self.assertIsInstance(eq.left, Power)
        self.assertIsInstance(eq.left.base, Group)
        self.assertIsInstance(eq.left.base.inner, UnaryOp)
        self.assertEqual(eq.left.base.inner.op, "-")
        self.assertEqual(eq.left.base.inner.operand, Variable("x", Span(2, 3)))
        self.assertEqual(eq.left.exponent, IntegerLiteral(2, Span(5, 6)))
        self.assertEqual(eq.right, IntegerLiteral(1, Span(9, 10)))

    def test_case_implicit_multiplication_fractional(self):
        # Case 4: 1/2x = 1 must be REJECTED as implicit multiplication
        with self.assertRaises(ImplicitMultiplicationError) as ctx:
            parse("1/2x = 1")
        self.assertIn("implicit multiplication", str(ctx.exception).lower())

    def test_case_implicit_multiplication_simple(self):
        # Case 5: 2x = 4 must be REJECTED as implicit multiplication
        with self.assertRaises(ImplicitMultiplicationError) as ctx:
            parse("2x = 4")
        self.assertIn("implicit multiplication", str(ctx.exception).lower())

    def test_case_rational_fraction_preservation(self):
        # Case 6: (x-1)/(x-1) = 1 must parse and preserve both subtrees
        eq = parse("(x-1)/(x-1) = 1")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "/")
        self.assertIsInstance(eq.left.left, Group)
        self.assertIsInstance(eq.left.right, Group)
        # Left group: x - 1
        self.assertIsInstance(eq.left.left.inner, BinaryOp)
        self.assertEqual(eq.left.left.inner.op, "-")
        # Right group: x - 1
        self.assertIsInstance(eq.left.right.inner, BinaryOp)
        self.assertEqual(eq.left.right.inner.op, "-")
        self.assertEqual(eq.right, IntegerLiteral(1, Span(14, 15)))

    def test_case_variable_exponent_zero(self):
        # Case 7: x^0 = 1 must parse and preserve the power node
        eq = parse("x^0 = 1")
        self.assertIsInstance(eq.left, Power)
        self.assertEqual(eq.left.base, Variable("x", Span(0, 1)))
        self.assertEqual(eq.left.exponent, IntegerLiteral(0, Span(2, 3)))
        self.assertEqual(eq.right, IntegerLiteral(1, Span(6, 7)))

    def test_case_constant_indeterminate_zero_to_zero(self):
        # Case 8: 0^0 = 1 must parse; definedness belongs to later stage
        eq = parse("0^0 = 1")
        self.assertIsInstance(eq.left, Power)
        self.assertEqual(eq.left.base, IntegerLiteral(0, Span(0, 1)))
        self.assertEqual(eq.left.exponent, IntegerLiteral(0, Span(2, 3)))
        self.assertEqual(eq.right, IntegerLiteral(1, Span(6, 7)))

    def test_case_quadratic_equation(self):
        # Case 9: x^2 - 4 = 0 must parse (not yet SOLVE)
        eq = parse("x^2 - 4 = 0")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "-")
        self.assertIsInstance(eq.left.left, Power)
        self.assertEqual(eq.left.left.base, Variable("x", Span(0, 1)))
        self.assertEqual(eq.left.left.exponent, IntegerLiteral(2, Span(2, 3)))
        self.assertEqual(eq.left.right, IntegerLiteral(4, Span(6, 7)))
        self.assertEqual(eq.right, IntegerLiteral(0, Span(10, 11)))

    def test_case_unsupported_exponent_value(self):
        # Case 10: x^3 = 1 must be REJECTED (exponent not in {0, 1, 2})
        with self.assertRaises(ParserError) as ctx:
            parse("x^3 = 1")
        self.assertIn("Unsupported exponent value 3", str(ctx.exception))


class TestImplicitMultiplicationVarieties(unittest.TestCase):
    """Exhaustive tests for rejecting various implicit multiplication forms."""

    def test_reject_variable_parentheses(self):
        # x(x+1) = 0
        with self.assertRaises(ImplicitMultiplicationError):
            parse("x(x+1) = 0")

    def test_reject_parentheses_parentheses(self):
        # (x)(x+1) = 0
        with self.assertRaises(ImplicitMultiplicationError):
            parse("(x)(x+1) = 0")

    def test_reject_parentheses_variable(self):
        # (x)x = 0
        with self.assertRaises(ImplicitMultiplicationError):
            parse("(x)x = 0")

    def test_reject_parentheses_number(self):
        # (x)2 = 0
        with self.assertRaises(ImplicitMultiplicationError):
            parse("(x)2 = 0")

    def test_reject_number_parentheses(self):
        # 3(x+1) = 0
        with self.assertRaises(ImplicitMultiplicationError):
            parse("3(x+1) = 0")

    def test_reject_spaced_implicit(self):
        # 2 x = 4
        with self.assertRaises(ImplicitMultiplicationError):
            parse("2 x = 4")


class TestOperatorPrecedenceAndAssociativity(unittest.TestCase):
    """Tests confirming standard mathematical operator precedence and associativity."""

    def test_mul_precedes_add(self):
        # 1 + 2 * 3 = 7 => 1 + (2 * 3)
        eq = parse("1 + 2 * 3 = 7")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "+")
        self.assertEqual(eq.left.left, IntegerLiteral(1, Span(0, 1)))
        self.assertIsInstance(eq.left.right, BinaryOp)
        self.assertEqual(eq.left.right.op, "*")

    def test_power_precedes_mul(self):
        # 2 * x^2 = 8 => 2 * (x^2)
        eq = parse("2 * x^2 = 8")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "*")
        self.assertEqual(eq.left.left, IntegerLiteral(2, Span(0, 1)))
        self.assertIsInstance(eq.left.right, Power)

    def test_subtraction_left_associative(self):
        # 10 - 3 - 2 = 5 => (10 - 3) - 2
        eq = parse("10 - 3 - 2 = 5")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "-")
        self.assertIsInstance(eq.left.left, BinaryOp)
        self.assertEqual(eq.left.left.op, "-")
        self.assertEqual(eq.left.left.left, IntegerLiteral(10, Span(0, 2)))
        self.assertEqual(eq.left.left.right, IntegerLiteral(3, Span(5, 6)))
        self.assertEqual(eq.left.right, IntegerLiteral(2, Span(9, 10)))

    def test_division_left_associative(self):
        # 24 / 6 / 2 = 2 => (24 / 6) / 2
        eq = parse("24 / 6 / 2 = 2")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "/")
        self.assertIsInstance(eq.left.left, BinaryOp)
        self.assertEqual(eq.left.left.op, "/")
        self.assertEqual(eq.left.left.left, IntegerLiteral(24, Span(0, 2)))
        self.assertEqual(eq.left.left.right, IntegerLiteral(6, Span(5, 6)))
        self.assertEqual(eq.left.right, IntegerLiteral(2, Span(9, 10)))

    def test_mixed_add_sub_mul_div(self):
        # 2 * 3 + 8 / 4 = 8 => (2 * 3) + (8 / 4)
        eq = parse("2 * 3 + 8 / 4 = 8")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertEqual(eq.left.op, "+")
        self.assertEqual(eq.left.left.op, "*")
        self.assertEqual(eq.left.right.op, "/")


class TestUnaryPlacementAndGrammarConstraints(unittest.TestCase):
    """Tests ensuring unary sign placement adheres strictly to the frozen EBNF."""

    def test_valid_unary_leading_expression(self):
        eq = parse("+x = 1")
        self.assertIsInstance(eq.left, UnaryOp)
        self.assertEqual(eq.left.op, "+")

        eq2 = parse("-x = 1")
        self.assertIsInstance(eq2.left, UnaryOp)
        self.assertEqual(eq2.left.op, "-")

    def test_valid_unary_in_grouped_expression(self):
        eq = parse("2 * (-3) = 0")
        self.assertIsInstance(eq.left, BinaryOp)
        self.assertIsInstance(eq.left.right, Group)
        self.assertIsInstance(eq.left.right.inner, UnaryOp)

    def test_reject_unary_after_binary_without_grouping(self):
        # In the frozen EBNF, factor ::= power; primary does not accept unary signs directly.
        # 2 * -3 = 0 is invalid without grouping.
        with self.assertRaises(ParserError):
            parse("2 * -3 = 0")

        with self.assertRaises(ParserError):
            parse("x + * 2 = 3")


class TestMalformedInputsAndInvalidSymbols(unittest.TestCase):
    """Tests verifying rejection of invalid characters, malformed parens, and bad equations."""

    def test_unsupported_variable(self):
        with self.assertRaises(LexerError) as ctx:
            parse("2*y + 1 = 3")
        self.assertIn("Illegal character 'y'", str(ctx.exception))

    def test_invalid_characters(self):
        with self.assertRaises(LexerError):
            parse("2*x $ 3 = 5")

        with self.assertRaises(LexerError):
            parse("2*x + 3# = 5")

    def test_unmatched_parentheses(self):
        with self.assertRaises(ParserError):
            parse("(2*x + 3 = 7")

        with self.assertRaises(ParserError):
            parse("2*x + 3) = 7")

    def test_missing_equation_equals(self):
        with self.assertRaises(ParserError):
            parse("2*x + 3")

    def test_multiple_equation_equals(self):
        with self.assertRaises(ParserError):
            parse("2*x = 3 = 4")

    def test_empty_equation_sides(self):
        with self.assertRaises(ParserError):
            parse("= 7")

        with self.assertRaises(ParserError):
            parse("2*x =")


class TestASTImmutabilityAndInspection(unittest.TestCase):
    """Tests verifying AST nodes are immutable, track spans, and provide deterministic inspection."""

    def test_ast_immutability(self):
        eq = parse("2*x + 3 = 7")
        with self.assertRaises(AttributeError):
            eq.left = IntegerLiteral(0, Span(0, 1))

        lit = IntegerLiteral(5, Span(0, 1))
        with self.assertRaises(AttributeError):
            lit.value = 10

    def test_ast_traversal_and_variables(self):
        eq = parse("2*x + 3 = 7")
        all_nodes = list(eq.walk())
        self.assertEqual(len(all_nodes), 7)  # Equation, BinaryOp(+), BinaryOp(*), 2, x, 3, 7 (total nodes)
        self.assertEqual(eq.variables(), {"x"})

        const_eq = parse("2 + 3 = 5")
        self.assertEqual(const_eq.variables(), set())

    def test_inspection_dict(self):
        eq = parse("x^2 = 4")
        d = eq.to_dict()
        self.assertEqual(d["type"], "Equation")
        self.assertEqual(d["left"]["type"], "Power")
        self.assertEqual(d["left"]["base"]["name"], "x")
        self.assertEqual(d["left"]["exponent"]["value"], 2)


class TestInputBoundsSafety(unittest.TestCase):
    """Tests verifying input length, token count, and nesting depth limits."""

    def test_max_input_length_exceeded(self):
        # Limit is 256
        long_input = "x + " * 70 + "1 = 0"  # > 280 chars
        with self.assertRaises(InputBoundsExceededError) as ctx:
            parse(long_input)
        self.assertIn("exceeds maximum allowed limit of 256", str(ctx.exception))

    def test_max_nesting_depth_exceeded(self):
        # Limit is 16
        deep = "(" * 17 + "x" + ")" * 17 + " = 0"
        with self.assertRaises(InputBoundsExceededError) as ctx:
            parse(deep)
        self.assertIn("nesting depth exceeds maximum limit of 16", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
