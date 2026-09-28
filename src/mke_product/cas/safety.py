"""Input validation, computational resource bounds, and safety guards for CAS operations."""

from __future__ import annotations

from typing import List, Optional, Set, Tuple
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
from mke_product.parser.errors import (
    InputBoundsExceededError,
    LexerError,
    MKEParserError,
    ParserError,
)
from .cas_parser import CASPower

MAX_INPUT_CHARS = 4096
MAX_INTEGER_DIGITS = 256
MAX_PLOT_POINTS = 2000
MAX_RESPONSE_BYTES = 65536


class SafetyError(Exception):
    """Raised when an input violates mathematical safety policies."""
    pass


class ASTSafetyError(SafetyError):
    """Raised when an AST violates structural safety constraints."""
    pass


class ExpressionBoundsError(SafetyError):
    """Raised when an expression exceeds length or depth bounds."""
    pass


class DomainRestrictionError(SafetyError):
    """Raised when an expression contains statically provable domain violations."""
    pass


class DivisionByZeroError(DomainRestrictionError):
    """Raised when an expression attempts static division by zero."""
    pass


def check_input_bounds(raw_input: str) -> None:
    """Validate character length before lexical analysis."""
    if len(raw_input) > MAX_INPUT_CHARS:
        raise ExpressionBoundsError(
            f"Input length ({len(raw_input)}) exceeds maximum permitted ({MAX_INPUT_CHARS} characters)."
        )


def inspect_ast_safety(node: ASTNode) -> None:
    """Recursively validate safety constraints on the AST node."""
    for n in node.walk():
        if isinstance(n, IntegerLiteral):
            if len(str(n.value)) > MAX_INTEGER_DIGITS:
                raise ExpressionBoundsError(
                    f"Integer literal exceeds maximum allowed size of {MAX_INTEGER_DIGITS} digits."
                )
        elif isinstance(n, (Power, CASPower)):
            # Check for 0^0
            if isinstance(n.base, IntegerLiteral) and n.base.value == 0:
                if isinstance(n.exponent, IntegerLiteral) and n.exponent.value == 0:
                    raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
        elif isinstance(n, BinaryOp) and n.op == "/":
            # Check for constant division by zero: e.g. expr / 0
            if isinstance(n.right, IntegerLiteral) and n.right.value == 0:
                raise DivisionByZeroError("Division by zero constant is undefined.")


def extract_domain_restrictions(node: ASTNode) -> List[str]:
    """Inspect all division denominators in AST to find domain restrictions (e.g., x != 1)."""
    restrictions: List[str] = []

    for n in node.walk():
        if isinstance(n, BinaryOp) and n.op == "/":
            denom = n.right
            # If denominator contains variable 'x', formulate restriction
            if "x" in denom.variables():
                from .ast_bridge import ast_to_sympy_expr
                try:
                    sym_denom = ast_to_sympy_expr(denom)
                    x_sym = sympy.Symbol("x", real=True)
                    # Solve sym_denom = 0 for real roots
                    roots = sympy.solve(sym_denom, x_sym)
                    for root in roots:
                        if root.is_real:
                            restrictions.append(f"x != {root}")
                        else:
                            restrictions.append(f"{sym_denom} != 0")
                except Exception:
                    restrictions.append("denominator != 0")

    # Deduplicate while preserving order
    seen: Set[str] = set()
    deduped: List[str] = []
    for r in restrictions:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped
