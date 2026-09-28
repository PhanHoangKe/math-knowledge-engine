"""Input validation, computational resource bounds, and safety guards for CAS operations."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
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


def evaluate_constant_ast(node: ASTNode) -> sympy.Rational:
    """Safely evaluate an ASTNode containing no variables to an exact rational value."""
    if len(node.variables()) > 0:
        raise ValueError("Node contains variables, cannot evaluate as constant.")
    if isinstance(node, IntegerLiteral):
        return sympy.Integer(node.value)
    elif isinstance(node, Group):
        return evaluate_constant_ast(node.inner)
    elif isinstance(node, UnaryOp):
        val = evaluate_constant_ast(node.operand)
        return val if node.op == "+" else -val
    elif isinstance(node, BinaryOp):
        left_val = evaluate_constant_ast(node.left)
        right_val = evaluate_constant_ast(node.right)
        if node.op == "+":
            return left_val + right_val
        elif node.op == "-":
            return left_val - right_val
        elif node.op == "*":
            return left_val * right_val
        elif node.op == "/":
            if right_val == 0:
                raise DivisionByZeroError("Division by zero constant is undefined.")
            return left_val / right_val
        else:
            raise ValueError(f"Unsupported binary operator in constant evaluation: {node.op!r}")
    elif isinstance(node, (Power, CASPower)):
        base_val = evaluate_constant_ast(node.base)
        exp_val = int(node.exponent.value)
        if base_val == 0 and exp_val == 0:
            raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
        return base_val ** exp_val
    else:
        raise TypeError(f"Unknown AST node type: {type(node).__name__}")


def inspect_ast_safety(node: ASTNode) -> None:
    """Recursively validate safety constraints on the AST node."""
    for n in node.walk():
        if isinstance(n, IntegerLiteral):
            if len(str(n.value)) > MAX_INTEGER_DIGITS:
                raise ExpressionBoundsError(
                    f"Integer literal exceeds maximum allowed size of {MAX_INTEGER_DIGITS} digits."
                )
        elif isinstance(n, (Power, CASPower)):
            # Check for 0^0 (direct or constant subtree)
            if len(n.base.variables()) == 0:
                b_val = evaluate_constant_ast(n.base)
                if b_val == 0 and n.exponent.value == 0:
                    raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
        elif isinstance(n, BinaryOp) and n.op == "/":
            # Check for constant denominator: e.g. expr / 0 or expr / (2 - 2)
            if len(n.right.variables()) == 0:
                denom_val = evaluate_constant_ast(n.right)
                if denom_val == 0:
                    raise DivisionByZeroError("Division by zero constant is undefined.")


from .cas_parser import CASPower, Inequality, LinearSystem


def extract_domain_restrictions(node: ASTNode) -> List[str]:
    """Inspect all division denominators and powers in AST to find domain restrictions (e.g., x != 1, x != 0)."""
    restrictions: List[str] = []

    for n in node.walk():
        if isinstance(n, BinaryOp) and n.op == "/":
            denom = n.right
            vars_in_denom = denom.variables()
            if vars_in_denom:
                from .ast_bridge import ast_to_sympy_expr
                try:
                    sym_denom = ast_to_sympy_expr(denom)
                    for v_name in sorted(vars_in_denom):
                        v_sym = sympy.Symbol(v_name, real=True)
                        roots = sympy.solve(sym_denom, v_sym)
                        if not isinstance(roots, (list, tuple, set)):
                            roots = [roots]
                        for root in roots:
                            if hasattr(root, "is_real") and root.is_real is True:
                                restrictions.append(f"{v_name} != {root}")
                            elif isinstance(root, (int, float, sympy.Integer, sympy.Rational)):
                                restrictions.append(f"{v_name} != {root}")
                            else:
                                try:
                                    if sympy.im(root) == 0:
                                        restrictions.append(f"{v_name} != {root}")
                                except Exception:
                                    restrictions.append(f"{sym_denom} != 0")
                except Exception:
                    restrictions.append("denominator != 0")
        elif isinstance(n, (Power, CASPower)):
            # v^0 requires v != 0 to avoid indeterminate 0^0
            if isinstance(n.base, Variable) and n.exponent.value == 0:
                restrictions.append(f"{n.base.name} != 0")

    # Deduplicate while preserving order
    seen: Set[str] = set()
    deduped: List[str] = []
    for r in restrictions:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped


def parse_safe_numeric_bound(val: Any, name: str = "bound") -> Union[int, float, sympy.Rational]:
    """Strictly parse a numeric option bound without using eval or sympify."""
    if val is None:
        raise ValueError(f"Missing required numeric value for {name}.")

    if isinstance(val, (int, sympy.Integer)):
        return int(val)

    if isinstance(val, (float, sympy.Float)):
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Invalid non-finite float value for {name}: {val}")
        return float(val)

    if isinstance(val, sympy.Rational):
        return val

    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            raise ValueError(f"Empty string provided for {name}.")

        # 1. Integer literal
        if re.match(r"^[-+]?\d+$", val_str):
            digits_only = val_str.lstrip("+-")
            if len(digits_only) > MAX_INTEGER_DIGITS:
                raise ExpressionBoundsError(f"Bound '{name}' exceeds maximum integer digits ({MAX_INTEGER_DIGITS}).")
            return int(val_str)

        # 2. Rational fraction: integer / integer
        if re.match(r"^[-+]?\d+\s*/\s*[-+]?\d+$", val_str):
            parts = val_str.split("/")
            num = int(parts[0].strip())
            denom = int(parts[1].strip())
            if denom == 0:
                raise DivisionByZeroError(f"Division by zero in bound '{name}': {val_str}")
            return sympy.Rational(num, denom)

        # 3. Floating point decimal
        if re.match(r"^[-+]?\d*\.\d+$", val_str) or re.match(r"^[-+]?\d+\.\d*$", val_str):
            f_val = float(val_str)
            if math.isnan(f_val) or math.isinf(f_val):
                raise ValueError(f"Invalid non-finite float value for {name}: {val_str}")
            return f_val

        raise ValueError(
            f"Unsupported or non-numeric expression for option '{name}': {val!r}. "
            f"Only explicit numeric literals (integers, fractions 'p/q', decimals) are allowed."
        )

    raise TypeError(f"Invalid type for option '{name}': {type(val).__name__}. Expected numeric type or numeric string.")


def sanitize_execution_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and validate all execution options passed to CAS operations."""
    if not isinstance(options, dict):
        return {}

    sanitized: Dict[str, Any] = {}

    for k, v in options.items():
        if not isinstance(k, str) or len(k) > 64:
            raise ValueError(f"Invalid option key: {k!r}")

        if k in ("lower", "upper", "x_min", "x_max"):
            sanitized[k] = parse_safe_numeric_bound(v, name=k)
        elif k in ("order", "num_points", "points"):
            bound_val = parse_safe_numeric_bound(v, name=k)
            if isinstance(bound_val, (float, sympy.Rational)) and not bound_val == int(bound_val):
                raise ValueError(f"Option '{k}' must be an integer, got: {v}")
            int_val = int(bound_val)
            if k == "order" and (int_val < 1 or int_val > 10):
                raise ValueError(f"Derivative order must be between 1 and 10, got: {int_val}")
            if k in ("num_points", "points") and (int_val < 2 or int_val > MAX_PLOT_POINTS):
                raise ValueError(f"Plot points must be between 2 and {MAX_PLOT_POINTS}, got: {int_val}")
            sanitized[k] = int_val
        elif k in ("variable", "var"):
            if not isinstance(v, str) or not re.match(r"^[a-zA-Z]$", v):
                raise ValueError(f"Invalid variable name: {v!r}. Must be a single letter.")
            sanitized["variable"] = v
        elif k in ("engine_override", "in_process", "sleep_seconds", "timeout_sec"):
            if k == "engine_override":
                if not isinstance(v, str) or not re.match(r"^[a-zA-Z0-9_-]+$", v):
                    raise ValueError(f"Invalid engine override name: {v!r}")
                sanitized[k] = v
            elif k == "in_process":
                sanitized[k] = bool(v)
            elif k in ("sleep_seconds", "timeout_sec"):
                sanitized[k] = float(v)
        else:
            raise ValueError(f"Unknown or unsupported option key: {k!r}")
    return sanitized


def is_polynomial_ast(node: ASTNode) -> bool:
    """Check if AST represents a polynomial with no variable denominators or non-integer powers."""
    if isinstance(node, IntegerLiteral):
        return True
    if isinstance(node, Variable):
        return True
    if isinstance(node, Group):
        return is_polynomial_ast(node.inner)
    if isinstance(node, UnaryOp):
        return is_polynomial_ast(node.operand)
    if isinstance(node, BinaryOp):
        if node.op in ("+", "-", "*"):
            return is_polynomial_ast(node.left) and is_polynomial_ast(node.right)
        elif node.op == "/":
            # Division by non-zero constant is polynomial (rational coefficient)
            return len(node.right.variables()) == 0 and is_polynomial_ast(node.left)
        return False
    if isinstance(node, (Power, CASPower)):
        if isinstance(node.exponent, IntegerLiteral) and node.exponent.value > 0:
            return is_polynomial_ast(node.base)
        return False
    if isinstance(node, Equation):
        return is_polynomial_ast(node.left) and is_polynomial_ast(node.right)
    if isinstance(node, Inequality):
        return is_polynomial_ast(node.left) and is_polynomial_ast(node.right)
    if isinstance(node, LinearSystem):
        return all(is_polynomial_ast(eq) for eq in node.equations)
    return False


def assess_domain_certainty(node: Optional[ASTNode], restrictions: List[str]) -> str:
    """Classify mathematical domain certainty for expression/equation."""
    if node is None:
        return "NOT_FULLY_DETERMINED"
    if restrictions:
        return "EXPLICIT_EXCLUSIONS"
    if is_polynomial_ast(node):
        return "PROVEN_REALS"
    return "NOT_FULLY_DETERMINED"

