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


MAX_CONSTANT_EVAL_STEPS = 100
MAX_CONSTANT_EXPONENT = 256
MAX_CONSTANT_INTEGER_BITS = 1024


class ConstantEvalResourceLimitError(SafetyError):
    """Raised when constant arithmetic evaluation exceeds pre-dispatch resource bounds."""
    pass


def ast_nodes_structurally_equal(a: ASTNode, b: ASTNode) -> bool:
    """Check if two AST subtrees are structurally identical without evaluating arithmetic."""
    if type(a) is not type(b):
        if isinstance(a, Group):
            return ast_nodes_structurally_equal(a.inner, b)
        if isinstance(b, Group):
            return ast_nodes_structurally_equal(a, b.inner)
        if isinstance(a, (Power, CASPower)) and isinstance(b, (Power, CASPower)):
            return (
                a.exponent.value == b.exponent.value
                and ast_nodes_structurally_equal(a.base, b.base)
            )
        return False

    if isinstance(a, IntegerLiteral):
        return a.value == b.value
    elif isinstance(a, Variable):
        return a.name == b.name
    elif isinstance(a, Group):
        return ast_nodes_structurally_equal(a.inner, b.inner)
    elif isinstance(a, UnaryOp):
        return a.op == b.op and ast_nodes_structurally_equal(a.operand, b.operand)
    elif isinstance(a, BinaryOp):
        return (
            a.op == b.op
            and ast_nodes_structurally_equal(a.left, b.left)
            and ast_nodes_structurally_equal(a.right, b.right)
        )
    elif isinstance(a, (Power, CASPower)):
        return (
            a.exponent.value == b.exponent.value
            and ast_nodes_structurally_equal(a.base, b.base)
        )
    return False


def _eval_constant_bounded(
    node: ASTNode,
    steps: List[int],
    max_steps: int,
    max_exp: int,
    max_bits: int,
) -> sympy.Rational:
    """Internal bounded evaluator enforcing strict step counts, exponents, and bit lengths."""
    steps[0] += 1
    if steps[0] > max_steps:
        raise ConstantEvalResourceLimitError(
            f"Constant evaluation exceeded maximum step budget of {max_steps} steps."
        )

    if isinstance(node, IntegerLiteral):
        if node.value.bit_length() > max_bits:
            raise ConstantEvalResourceLimitError(
                f"Integer literal bit length ({node.value.bit_length()}) exceeds budget of {max_bits} bits."
            )
        return sympy.Integer(node.value)

    elif isinstance(node, Group):
        return _eval_constant_bounded(node.inner, steps, max_steps, max_exp, max_bits)

    elif isinstance(node, UnaryOp):
        val = _eval_constant_bounded(node.operand, steps, max_steps, max_exp, max_bits)
        res = val if node.op == "+" else -val
        return res

    elif isinstance(node, BinaryOp):
        left_val = _eval_constant_bounded(node.left, steps, max_steps, max_exp, max_bits)
        right_val = _eval_constant_bounded(node.right, steps, max_steps, max_exp, max_bits)

        if node.op == "+":
            res = left_val + right_val
        elif node.op == "-":
            res = left_val - right_val
        elif node.op == "*":
            res = left_val * right_val
        elif node.op == "/":
            if right_val == 0:
                raise DivisionByZeroError("Division by zero constant is undefined.")
            res = left_val / right_val
        else:
            raise ValueError(f"Unsupported binary operator in constant evaluation: {node.op!r}")

        if max(res.p.bit_length(), res.q.bit_length()) > max_bits:
            raise ConstantEvalResourceLimitError(
                f"Intermediate arithmetic result exceeds maximum bit-length budget of {max_bits} bits."
            )
        return res

    elif isinstance(node, (Power, CASPower)):
        exp_val = int(node.exponent.value)
        if exp_val < 0:
            raise ConstantEvalResourceLimitError("Negative exponents not evaluated in pre-dispatch constant check.")

        if exp_val == 0:
            base_val = _eval_constant_bounded(node.base, steps, max_steps, max_exp, max_bits)
            if base_val == 0:
                raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
            return sympy.Integer(1)

        if exp_val > max_exp:
            raise ConstantEvalResourceLimitError(
                f"Constant exponent {exp_val} exceeds maximum evaluation budget of {max_exp}."
            )

        base_val = _eval_constant_bounded(node.base, steps, max_steps, max_exp, max_bits)
        if base_val == 0:
            return sympy.Integer(0)

        est_bits = max(base_val.p.bit_length(), base_val.q.bit_length()) * exp_val
        if est_bits > max_bits:
            raise ConstantEvalResourceLimitError(
                f"Estimated exponentiation bit-length ({est_bits}) exceeds budget of {max_bits} bits."
            )

        res = base_val ** exp_val
        if max(res.p.bit_length(), res.q.bit_length()) > max_bits:
            raise ConstantEvalResourceLimitError(
                f"Exponentiation result exceeds bit-length budget of {max_bits} bits."
            )
        return res

    else:
        raise TypeError(f"Unknown AST node type: {type(node).__name__}")


def evaluate_constant_ast(
    node: ASTNode,
    max_steps: int = MAX_CONSTANT_EVAL_STEPS,
    max_exp: int = MAX_CONSTANT_EXPONENT,
    max_bits: int = MAX_CONSTANT_INTEGER_BITS,
) -> sympy.Rational:
    """Safely evaluate an ASTNode containing no variables to an exact rational value within bounded budgets."""
    if len(node.variables()) > 0:
        raise ValueError("Node contains variables, cannot evaluate as constant.")
    steps = [0]
    return _eval_constant_bounded(node, steps, max_steps, max_exp, max_bits)


def prove_constant_zero_status(node: ASTNode) -> str:
    """Conservatively prove whether a constant AST subtree is 'ZERO', 'NONZERO', or 'UNDECIDABLE'.

    Guarantees:
    - Never triggers giant integer exponentiations (e.g. 2^1000000000000) or unbounded memory allocation.
    - Proves non-zero constant powers in O(1) without integer expansion.
    - Proves structural cancellations like A - A in O(tree size) without expansion.
    - Falls back to bounded evaluation within strict step and bit limits.
    - Returns 'UNDECIDABLE' if exact determination exceeds budgets.
    """
    if len(node.variables()) > 0:
        return "UNDECIDABLE"

    # 1. Structural reasoning pass (zero arithmetic computation)
    if isinstance(node, IntegerLiteral):
        return "ZERO" if node.value == 0 else "NONZERO"

    elif isinstance(node, Group):
        return prove_constant_zero_status(node.inner)

    elif isinstance(node, UnaryOp):
        return prove_constant_zero_status(node.operand)

    elif isinstance(node, (Power, CASPower)):
        exp_val = int(node.exponent.value)
        if exp_val == 0:
            b_status = prove_constant_zero_status(node.base)
            if b_status == "ZERO":
                raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
            elif b_status == "NONZERO":
                return "NONZERO"
            return "UNDECIDABLE"
        elif exp_val > 0:
            b_status = prove_constant_zero_status(node.base)
            if b_status == "ZERO":
                return "ZERO"
            elif b_status == "NONZERO":
                # For any real b != 0 and integer e > 0, b^e != 0
                return "NONZERO"
            return "UNDECIDABLE"

    elif isinstance(node, BinaryOp):
        if node.op == "-":
            if ast_nodes_structurally_equal(node.left, node.right):
                return "ZERO"
        elif node.op == "*":
            l_status = prove_constant_zero_status(node.left)
            r_status = prove_constant_zero_status(node.right)
            if l_status == "NONZERO" and r_status == "NONZERO":
                return "NONZERO"
            if l_status == "ZERO" or r_status == "ZERO":
                return "ZERO"
        elif node.op == "/":
            r_status = prove_constant_zero_status(node.right)
            if r_status == "ZERO":
                raise DivisionByZeroError("Division by zero constant is undefined.")
            if r_status == "NONZERO":
                l_status = prove_constant_zero_status(node.left)
                if l_status == "ZERO":
                    return "ZERO"
                elif l_status == "NONZERO":
                    return "NONZERO"

    # 2. Bounded arithmetic evaluation fallback
    try:
        val = evaluate_constant_ast(node)
        return "ZERO" if val == 0 else "NONZERO"
    except (DomainRestrictionError, DivisionByZeroError):
        raise
    except Exception:
        return "UNDECIDABLE"


def inspect_ast_safety(node: ASTNode) -> None:
    """Recursively validate structural and constant safety constraints on the AST node.

    CRITICAL RESOURCE-ISOLATION INVARIANT:
    This function runs in the unsupervised pre-dispatch path (router and entrypoints).
    It executes only lightweight structural checks and bounded constant reasoning.
    It NEVER invokes unconstrained symbolic operations on variable subtrees, nor does it
    perform unbounded integer exponentiation or arithmetic on giant constant subtrees.
    All expensive or undecidable constant computations are safely deferred to supervised execution.
    """
    for n in node.walk():
        if isinstance(n, IntegerLiteral):
            if len(str(n.value)) > MAX_INTEGER_DIGITS:
                raise ExpressionBoundsError(
                    f"Integer literal exceeds maximum allowed size of {MAX_INTEGER_DIGITS} digits."
                )
        elif isinstance(n, (Power, CASPower)):
            # Check for statically provable 0^0 on constant subtrees
            if n.exponent.value == 0 and len(n.base.variables()) == 0:
                zero_status = prove_constant_zero_status(n.base)
                if zero_status == "ZERO":
                    raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
        elif isinstance(n, BinaryOp) and n.op == "/":
            # Check for statically provable division by zero on constant subtrees
            if len(n.right.variables()) == 0:
                zero_status = prove_constant_zero_status(n.right)
                if zero_status == "ZERO":
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
            # B(x)^0 requires B(x) != 0 to avoid indeterminate 0^0
            if n.exponent.value == 0:
                vars_in_base = n.base.variables()
                if vars_in_base:
                    from .ast_bridge import ast_to_sympy_expr
                    try:
                        sym_base = ast_to_sympy_expr(n.base)
                        for v_name in sorted(vars_in_base):
                            v_sym = sympy.Symbol(v_name, real=True)
                            roots = sympy.solve(sym_base, v_sym)
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
                                        restrictions.append(f"{sym_base} != 0")
                    except Exception:
                        restrictions.append("base != 0")

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


FORBIDDEN_CLIENT_OPTION_KEYS = {
    "in_process",
    "sleep_seconds",
    "engine_override",
    "timeout_sec",
    "simulate",
    "direct",
    "internal",
}


def sanitize_client_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """Strictly sanitize untrusted client options from HTTP API requests.
    
    Rejects any internal execution controls (in_process, sleep_seconds, timeout_sec, engine_override).
    Only permits safe mathematical parameters: plotting bounds, sampling points, derivative orders, variables.
    """
    if not isinstance(options, dict):
        raise ValueError("'options' must be a JSON object dictionary.")

    for k in options:
        if k in FORBIDDEN_CLIENT_OPTION_KEYS:
            raise ValueError(f"Client-supplied internal execution option '{k}' is forbidden.")

    return sanitize_execution_options(options, allow_internal=False)


def sanitize_execution_options(options: Dict[str, Any], allow_internal: bool = True) -> Dict[str, Any]:
    """Sanitize and validate all execution options passed to CAS operations."""
    if not isinstance(options, dict):
        return {}

    sanitized: Dict[str, Any] = {}

    for k, v in options.items():
        if not isinstance(k, str) or len(k) > 64:
            raise ValueError(f"Invalid option key: {k!r}")

        if k in ("lower", "upper", "lower_bound", "upper_bound", "x_min", "x_max"):
            sanitized[k] = parse_safe_numeric_bound(v, name=k)
        elif k in ("order", "num_points", "points", "samples"):
            bound_val = parse_safe_numeric_bound(v, name=k)
            if isinstance(bound_val, (float, sympy.Rational)) and not bound_val == int(bound_val):
                raise ValueError(f"Option '{k}' must be an integer, got: {v}")
            int_val = int(bound_val)
            if k == "order" and (int_val < 1 or int_val > 10):
                raise ValueError(f"Derivative order must be between 1 and 10, got: {int_val}")
            if k in ("num_points", "points", "samples") and (int_val < 2 or int_val > MAX_PLOT_POINTS):
                raise ValueError(f"Plot points must be between 2 and {MAX_PLOT_POINTS}, got: {int_val}")
            sanitized[k] = int_val
        elif k in ("variable", "var"):
            if not isinstance(v, str) or not re.match(r"^[a-zA-Z]$", v):
                raise ValueError(f"Invalid variable name: {v!r}. Must be a single letter.")
            sanitized["variable"] = v
        elif allow_internal and k in ("engine_override", "in_process", "sleep_seconds", "timeout_sec"):
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


def is_domain_determination_complete(node: Optional[ASTNode], restrictions: List[str]) -> bool:
    """Mathematically audit whether the domain restriction set is proven exhaustive and complete.
    
    Conditions for verified domain completeness in v0:
    1. Node must be univariate or constant (len(node.variables()) <= 1).
    2. Every denominator must be a univariate polynomial with degree <= 2 where all real roots
       are algebraically determined as exact rational point exclusions.
    3. Every variable base raised to exponent 0 must have its zero exclusion accounted for.
    4. No radical, transcendental, piecewise, or unverified functions exist in the AST.
    5. The set of required real exclusions must exactly match the provided restrictions.
    """
    if node is None:
        return False

    vars_in_expr = node.variables()
    if len(vars_in_expr) > 1:
        # Multivariate domains are curves/surfaces and cannot be complete univariate point exclusions
        return False

    var_name = sorted(list(vars_in_expr))[0] if vars_in_expr else "x"
    v_sym = sympy.Symbol(var_name, real=True)
    required_exclusions: Set[str] = set()

    for n in node.walk():
        # Check function calls / unsupported non-algebraic nodes
        if hasattr(n, "func_name") or not isinstance(
            n, (IntegerLiteral, Variable, Group, UnaryOp, BinaryOp, Power, CASPower, Equation, Inequality, LinearSystem)
        ):
            return False

        if isinstance(n, BinaryOp) and n.op == "/":
            denom = n.right
            if not is_polynomial_ast(denom):
                return False

            denom_vars = denom.variables()
            if not denom_vars:
                # Constant denominator: must be provably non-zero to assert real domain
                zero_status = prove_constant_zero_status(denom)
                if zero_status != "NONZERO":
                    return False
                continue

            # Univariate polynomial denominator
            from .ast_bridge import ast_to_sympy_expr
            try:
                sym_denom = ast_to_sympy_expr(denom)
                poly = sympy.Poly(sym_denom, v_sym)
                deg = poly.degree()
                if deg == 1:
                    coeffs = poly.all_coeffs()
                    # a*x + b = 0 => x = -b/a
                    a, b = coeffs[0], coeffs[1]
                    root = -b / a
                    required_exclusions.add(f"{var_name} != {root}")
                elif deg == 2:
                    coeffs = poly.all_coeffs()
                    a, b, c = coeffs[0], coeffs[1], coeffs[2]
                    disc = b**2 - 4*a*c
                    if disc < 0:
                        # No real roots (e.g. x^2 + 1)
                        pass
                    elif disc == 0:
                        root = -b / (2*a)
                        required_exclusions.add(f"{var_name} != {root}")
                    else:
                        sqrt_disc = sympy.sqrt(disc)
                        if isinstance(sqrt_disc, (int, sympy.Integer, sympy.Rational)) or (hasattr(sqrt_disc, "is_rational") and sqrt_disc.is_rational):
                            r1 = (-b - sqrt_disc) / (2*a)
                            r2 = (-b + sqrt_disc) / (2*a)
                            required_exclusions.add(f"{var_name} != {r1}")
                            required_exclusions.add(f"{var_name} != {r2}")
                        else:
                            # Irrational roots cannot be audited as exact rational point exclusions in v0
                            return False
                else:
                    # Degree > 2 polynomial roots cannot be audited as exhaustive rational exclusions in v0
                    return False
            except Exception:
                return False

        elif isinstance(n, (Power, CASPower)):
            if isinstance(n.exponent, IntegerLiteral):
                if n.exponent.value == 0:
                    base_vars = n.base.variables()
                    if not base_vars:
                        # Constant base: must be provably non-zero to assert real domain
                        zero_status = prove_constant_zero_status(n.base)
                        if zero_status != "NONZERO":
                            return False
                        continue
                    if not is_polynomial_ast(n.base):
                        return False
                    from .ast_bridge import ast_to_sympy_expr
                    try:
                        sym_base = ast_to_sympy_expr(n.base)
                        poly = sympy.Poly(sym_base, v_sym)
                        deg = poly.degree()
                        if deg == 1:
                            coeffs = poly.all_coeffs()
                            a, b = coeffs[0], coeffs[1]
                            root = -b / a
                            required_exclusions.add(f"{var_name} != {root}")
                        elif deg == 2:
                            coeffs = poly.all_coeffs()
                            a, b, c = coeffs[0], coeffs[1], coeffs[2]
                            disc = b**2 - 4*a*c
                            if disc < 0:
                                # No real roots (e.g. x^2 + 1)
                                pass
                            elif disc == 0:
                                root = -b / (2*a)
                                required_exclusions.add(f"{var_name} != {root}")
                            else:
                                sqrt_disc = sympy.sqrt(disc)
                                if isinstance(sqrt_disc, (int, sympy.Integer, sympy.Rational)) or (hasattr(sqrt_disc, "is_rational") and sqrt_disc.is_rational):
                                    r1 = (-b - sqrt_disc) / (2*a)
                                    r2 = (-b + sqrt_disc) / (2*a)
                                    required_exclusions.add(f"{var_name} != {r1}")
                                    required_exclusions.add(f"{var_name} != {r2}")
                                else:
                                    # Irrational roots
                                    return False
                        else:
                            # Degree > 2 base
                            return False
                    except Exception:
                        return False
                elif n.exponent.value < 0:
                    return False
            else:
                return False

    # Check if provided restrictions match required exclusions
    restr_set = set(restrictions)
    return restr_set == required_exclusions


def assess_domain_certainty(node: Optional[ASTNode], restrictions: List[str]) -> str:
    """Classify mathematical domain certainty for expression/equation/system/inequality."""
    if node is None:
        return "NOT_FULLY_DETERMINED"
    
    if is_polynomial_ast(node) and not restrictions:
        return "PROVEN_REALS"
    
    if is_domain_determination_complete(node, restrictions):
        if not restrictions:
            return "PROVEN_REALS"
        return "EXPLICIT_EXCLUSIONS"
    
    return "NOT_FULLY_DETERMINED"


