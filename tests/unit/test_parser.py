"""Unit tests for safe parser and AST construction."""

from fractions import Fraction
import pytest
import sympy

from mke.models.ast_nodes import BinaryOpNode, EquationNode, NumberNode, VariableNode
from mke.parsing.exceptions import (
    ASTDepthExceededError,
    InvalidExponentError,
    InvalidSyntaxError,
    NodeCountExceededError,
)
from mke.parsing.limits import ParserLimits
from mke.parsing.parser import Parser
from mke.parsing.sympy_converter import ast_to_sympy, X_SYM


def test_parse_simple_linear():
    parser = Parser.from_text("2*x + 3 = 0")
    eq = parser.parse_equation()
    assert isinstance(eq, EquationNode)
    assert isinstance(eq.left, BinaryOpNode)
    assert eq.left.op == "+"
    assert isinstance(eq.right, NumberNode)
    assert eq.right.value == Fraction(0, 1)


def test_parse_precedence_and_parentheses():
    # 2 + 3 * x should parse as 2 + (3 * x)
    parser1 = Parser.from_text("2 + 3 * x = 0")
    eq1 = parser1.parse_equation()
    assert eq1.left.op == "+"
    assert eq1.left.right.op == "*"

    # (2 + 3) * x should parse as (2 + 3) * x
    parser2 = Parser.from_text("(2 + 3) * x = 0")
    eq2 = parser2.parse_equation()
    assert eq2.left.op == "*"
    assert eq2.left.left.op == "+"


def test_parse_power_restrictions():
    # Exponent <= 4 is allowed
    parser = Parser.from_text("x^4 = 0")
    eq = parser.parse_equation()
    assert eq.left.op == "^"

    # Exponent > 4 is rejected
    with pytest.raises(InvalidExponentError) as exc_info:
        Parser.from_text("x^5 = 0").parse_equation()
    assert "exceeds maximum allowed exponent" in str(exc_info.value)

    # Exponent negative is rejected
    with pytest.raises(InvalidExponentError):
        Parser.from_text("x^-2 = 0").parse_equation()


def test_ast_depth_limit():
    limits = ParserLimits(max_ast_depth=3)
    # Deeply nested expression: ((((x))))
    with pytest.raises(ASTDepthExceededError):
        Parser.from_text("(((x + 1) + 2) + 3) = 0", limits=limits).parse_equation()


def test_node_count_limit():
    limits = ParserLimits(max_node_count=5)
    with pytest.raises(NodeCountExceededError):
        Parser.from_text("1 + 2 + 3 + 4 + 5 = 0", limits=limits).parse_equation()


def test_sympy_conversion_safety():
    parser = Parser.from_text("x^2 - 5*x + 6 = 0")
    ast = parser.parse_equation()
    sym_eq = ast_to_sympy(ast)

    assert isinstance(sym_eq, sympy.Eq)
    expected_expr = X_SYM**2 - 5 * X_SYM + 6
    assert sympy.simplify(sym_eq.lhs - expected_expr) == 0
    assert sym_eq.rhs == 0
