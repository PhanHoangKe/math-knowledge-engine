"""Safe conversion from validated immutable MKE AST to SymPy expressions.

CRITICAL SECURITY INVARIANT:
This bridge explicitly constructs SymPy objects directly from typed AST nodes.
It NEVER calls eval(), exec(), sympify(), or parse_expr().
"""

from __future__ import annotations

from typing import Union
import sympy

from mke_product.parser.ast import (
    ASTNode,
    BinaryOp,
    Equation,
    Group,
    IntegerLiteral,
    Power,
    UnaryOp,
    Variable,
)
from .cas_parser import CASPower, Inequality, LinearSystem
from .safety import DomainRestrictionError, inspect_ast_safety


def ast_to_sympy(node: ASTNode) -> Union[sympy.Expr, sympy.Eq, sympy.Rel, List[sympy.Eq]]:
    """Convert an arbitrary valid MKE AST node (Expression, Equation, Inequality, or LinearSystem) to SymPy."""
    inspect_ast_safety(node)

    if isinstance(node, Equation):
        left_sym = ast_to_sympy_expr(node.left)
        right_sym = ast_to_sympy_expr(node.right)
        return sympy.Eq(left_sym, right_sym, evaluate=False)
    elif isinstance(node, Inequality):
        left_sym = ast_to_sympy_expr(node.left)
        right_sym = ast_to_sympy_expr(node.right)
        if node.op == "<":
            return sympy.Lt(left_sym, right_sym, evaluate=False)
        elif node.op in ("<=", "≤"):
            return sympy.Le(left_sym, right_sym, evaluate=False)
        elif node.op == ">":
            return sympy.Gt(left_sym, right_sym, evaluate=False)
        elif node.op in (">=", "≥"):
            return sympy.Ge(left_sym, right_sym, evaluate=False)
        else:
            raise ValueError(f"Unsupported inequality operator: {node.op!r}")
    elif isinstance(node, LinearSystem):
        return [sympy.Eq(ast_to_sympy_expr(eq.left), ast_to_sympy_expr(eq.right), evaluate=False) for eq in node.equations]
    else:
        return ast_to_sympy_expr(node)


def ast_to_sympy_expr(node: ASTNode) -> sympy.Expr:
    """Convert an expression AST node to a SymPy Expr object."""
    if isinstance(node, IntegerLiteral):
        return sympy.Integer(node.value)

    elif isinstance(node, Variable):
        return sympy.Symbol(node.name, real=True)

    elif isinstance(node, Group):
        return ast_to_sympy_expr(node.inner)

    elif isinstance(node, UnaryOp):
        operand_sym = ast_to_sympy_expr(node.operand)
        if node.op == "+":
            return operand_sym
        elif node.op == "-":
            return sympy.Mul(sympy.Integer(-1), operand_sym, evaluate=False)
        else:
            raise ValueError(f"Unsupported unary operator: {node.op!r}")

    elif isinstance(node, BinaryOp):
        left_sym = ast_to_sympy_expr(node.left)
        right_sym = ast_to_sympy_expr(node.right)
        if node.op == "+":
            return sympy.Add(left_sym, right_sym, evaluate=False)
        elif node.op == "-":
            neg_right = sympy.Mul(sympy.Integer(-1), right_sym, evaluate=False)
            return sympy.Add(left_sym, neg_right, evaluate=False)
        elif node.op == "*":
            return sympy.Mul(left_sym, right_sym, evaluate=False)
        elif node.op == "/":
            if right_sym == sympy.Integer(0):
                raise DomainRestrictionError("Division by zero constant is undefined.")
            inv_right = sympy.Pow(right_sym, sympy.Integer(-1), evaluate=False)
            return sympy.Mul(left_sym, inv_right, evaluate=False)
        else:
            raise ValueError(f"Unsupported binary operator: {node.op!r}")

    elif isinstance(node, (Power, CASPower)):
        base_sym = ast_to_sympy_expr(node.base)
        exp_sym = sympy.Integer(node.exponent.value)
        if base_sym == sympy.Integer(0) and exp_sym == sympy.Integer(0):
            raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
        return sympy.Pow(base_sym, exp_sym, evaluate=False)

    else:
        raise TypeError(f"Unknown AST node type: {type(node).__name__}")
