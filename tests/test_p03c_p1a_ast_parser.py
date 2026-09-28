"""Unit tests for P03C-P1A AST and Parser extensions (Radicals, Absolute Values, and Delimiters)."""

import unittest
from mke_product.cas.cas_parser import (
    CASTokenType,
    parse_cas_equation,
    parse_cas_expression,
    tokenize_cas,
)
from mke_product.parser.ast import (
    AbsoluteValue,
    BinaryOp,
    Equation,
    Group,
    IntegerLiteral,
    Power,
    Radical,
    UnaryOp,
    Variable,
)
from mke_product.parser.errors import (
    ImplicitMultiplicationError,
    InputBoundsExceededError,
    LexerError,
    ParserError,
)


class TestP03CP1AASTParser(unittest.TestCase):
    """Test AST nodes and parser rules for radicals and absolute values."""

    def test_radical_tokenization_and_parsing_standard(self):
        ast = parse_cas_expression("sqrt(x + 1)")
        self.assertIsInstance(ast, Radical)
        self.assertIsInstance(ast.radicand, BinaryOp)
        self.assertEqual(ast.radicand.op, "+")
        self.assertEqual(ast.variables(), {"x"})
        d = ast.to_dict()
        self.assertEqual(d["type"], "Radical")
        self.assertEqual(d["radicand"]["type"], "BinaryOp")

    def test_radical_tokenization_and_parsing_latex(self):
        ast = parse_cas_expression(r"\sqrt{2*x - 3}")
        self.assertIsInstance(ast, Radical)
        self.assertIsInstance(ast.radicand, BinaryOp)
        self.assertEqual(ast.variables(), {"x"})

    def test_absolute_value_tokenization_and_parsing_named(self):
        ast = parse_cas_expression("abs(2*x - 5)")
        self.assertIsInstance(ast, AbsoluteValue)
        self.assertIsInstance(ast.inner, BinaryOp)
        self.assertEqual(ast.variables(), {"x"})
        d = ast.to_dict()
        self.assertEqual(d["type"], "AbsoluteValue")

    def test_absolute_value_tokenization_and_parsing_pipe(self):
        ast = parse_cas_expression("|x - 3|")
        self.assertIsInstance(ast, AbsoluteValue)
        self.assertIsInstance(ast.inner, BinaryOp)
        self.assertEqual(ast.variables(), {"x"})

    def test_nested_radical_and_absolute_value(self):
        ast = parse_cas_expression("sqrt(|x| + 1)")
        self.assertIsInstance(ast, Radical)
        self.assertIsInstance(ast.radicand, BinaryOp)
        self.assertIsInstance(ast.radicand.left, AbsoluteValue)

    def test_nested_pipe_absolute_values(self):
        ast = parse_cas_expression("||x| - 1|")
        self.assertIsInstance(ast, AbsoluteValue)
        self.assertIsInstance(ast.inner, BinaryOp)
        self.assertIsInstance(ast.inner.left, AbsoluteValue)

    def test_radical_equation_parsing(self):
        eq = parse_cas_equation("sqrt(x + 3) = x + 1")
        self.assertIsInstance(eq, Equation)
        self.assertIsInstance(eq.left, Radical)
        self.assertIsInstance(eq.right, BinaryOp)
        self.assertEqual(eq.variables(), {"x"})

    def test_dual_radical_equation_parsing(self):
        eq = parse_cas_equation("sqrt(2*x - 1) = sqrt(x + 4)")
        self.assertIsInstance(eq, Equation)
        self.assertIsInstance(eq.left, Radical)
        self.assertIsInstance(eq.right, Radical)

    def test_absolute_value_equation_parsing(self):
        eq = parse_cas_equation("|2*x - 3| = x + 1")
        self.assertIsInstance(eq, Equation)
        self.assertIsInstance(eq.left, AbsoluteValue)

    def test_implicit_multiplication_rejections(self):
        with self.assertRaises(ImplicitMultiplicationError):
            tokenize_cas("2sqrt(x)")

        with self.assertRaises(ImplicitMultiplicationError):
            tokenize_cas("2|x|")

        with self.assertRaises(ImplicitMultiplicationError):
            tokenize_cas("x sqrt(x)")

        with self.assertRaises(ImplicitMultiplicationError):
            tokenize_cas("(x+1)sqrt(x)")

        with self.assertRaises(ImplicitMultiplicationError):
            tokenize_cas("|x|2")

    def test_syntax_error_unclosed_radical_and_abs(self):
        with self.assertRaises(ParserError):
            parse_cas_expression("sqrt(x + 1")

        with self.assertRaises(ParserError):
            parse_cas_expression(r"\sqrt{x + 1")

        with self.assertRaises(ParserError):
            parse_cas_expression("abs(x")

        with self.assertRaises(ParserError):
            parse_cas_expression("|x + 1")


if __name__ == "__main__":
    unittest.main()
