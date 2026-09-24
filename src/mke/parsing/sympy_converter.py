"""Safe conversion of validated AST to SymPy expressions using only allowed constructors.

SECURITY CRITICAL:
This module NEVER calls eval(), exec(), sympy.sympify(str), or sympy.parsing.sympy_parser.parse_expr().
Every SymPy node is constructed purely from explicitly whitelisted constructors on validated AST nodes.
"""

from fractions import Fraction
import sympy

from mke.models.ast_nodes import (
    ASTNode,
    BinaryOpNode,
    EquationNode,
    NumberNode,
    UnaryOpNode,
    VariableNode,
)

# Canonical real symbol for 'x'
X_SYM = sympy.Symbol("x", real=True)


def ast_to_sympy(node: ASTNode) -> sympy.Expr | sympy.Eq:
    """Recursively convert an AST node to a SymPy object via whitelisted constructors."""
    if isinstance(node, NumberNode):
        val: Fraction = node.value
        if val.denominator == 1:
            return sympy.Integer(val.numerator)
        return sympy.Rational(val.numerator, val.denominator)

    elif isinstance(node, VariableNode):
        return X_SYM

    elif isinstance(node, UnaryOpNode):
        operand_sym = ast_to_sympy(node.operand)
        if node.op == "+":
            return operand_sym
        elif node.op == "-":
            return sympy.Mul(sympy.Integer(-1), operand_sym)
        else:
            raise ValueError(f"Unsupported unary operator for SymPy conversion: {node.op}")

    elif isinstance(node, BinaryOpNode):
        left_sym = ast_to_sympy(node.left)
        right_sym = ast_to_sympy(node.right)

        if node.op == "+":
            return sympy.Add(left_sym, right_sym)
        elif node.op == "-":
            return sympy.Add(left_sym, sympy.Mul(sympy.Integer(-1), right_sym))
        elif node.op == "*":
            return sympy.Mul(left_sym, right_sym)
        elif node.op == "/":
            # l / r = l * (r ** -1)
            inv_r = sympy.Pow(right_sym, sympy.Integer(-1))
            return sympy.Mul(left_sym, inv_r)
        elif node.op == "^":
            return sympy.Pow(left_sym, right_sym)
        else:
            raise ValueError(f"Unsupported binary operator for SymPy conversion: {node.op}")

    elif isinstance(node, EquationNode):
        left_sym = ast_to_sympy(node.left)
        right_sym = ast_to_sympy(node.right)
        return sympy.Eq(left_sym, right_sym)

    else:
        raise TypeError(f"Unknown AST node type for SymPy conversion: {type(node)}")
