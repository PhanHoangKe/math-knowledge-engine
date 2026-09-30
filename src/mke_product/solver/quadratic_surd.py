"""Deterministic pure-Python quadratic surd equation solver kernel for MKE Product worker.

Milestone: PRODUCT-03C-P1C-04-B2
Strict Containment & Soundness Guarantees:
- Pure integer and exact Rational arithmetic over Q.
- Zero SymPy imports or dependencies.
- Zero floating-point arithmetic.
- Independent AST polynomial reduction to (c2, c1, c0) representing c2*x^2 + c1*x + c0.
- Hard 256-bit integer bounds on all input literals and intermediate arithmetic operations.
- Special 512-bit normalization working integer product M = p * q.
- Independent prime sieve establishing complete primes up to 65536 (exactly 6542 primes).
- Strict 32-bit ceiling on unfactored remainder R < 2^32 for certified squarefree radicand d.
- Fail-closed on uncertified radicands (ERR_SURD_NORMALIZATION_RESOURCE_LIMIT).
- Canonical root ordering: [a - b0*sqrt(d), a + b0*sqrt(d)] with b0 > 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.rational import Rational
from ..evaluator.budget import EvaluationBudget
from ..evaluator.errors import DomainError, EvaluationResourceLimitError
from ..parser.ast import (
    ASTNode,
    BinaryOp,
    Equation,
    Group,
    IntegerLiteral,
    Power,
    UnaryOp,
    Variable,
)
from ..parser.errors import Span


class NonQuadraticSurdExpressionError(Exception):
    """Raised when an expression AST cannot be reduced to a quadratic polynomial in x."""

    def __init__(self, message: str, span: Optional[Span] = None, code: str = "ERR_OUT_OF_SCOPE"):
        super().__init__(message)
        self.message = message
        self.span = span
        self.code = code


@dataclass(frozen=True)
class QuadraticSurd:
    """Exact quadratic irrational root representation a + b*sqrt(d) in Q(sqrt(d))."""

    rational_part: Rational
    sqrt_coefficient: Rational
    radicand: int

    def to_wire(self) -> Dict[str, Any]:
        """Convert to wire dictionary format with decimal strings."""
        return {
            "rational_part": {
                "numerator": str(self.rational_part.numerator),
                "denominator": str(self.rational_part.denominator),
            },
            "sqrt_coefficient": {
                "numerator": str(self.sqrt_coefficient.numerator),
                "denominator": str(self.sqrt_coefficient.denominator),
            },
            "radicand": str(self.radicand),
        }


@dataclass(frozen=True)
class QuadraticSurdSolverResult:
    """Authoritative result structure for in-worker quadratic surd equation solving."""

    status: str  # "SUCCESS", "OUT_OF_SCOPE", "DOMAIN_ERROR", "RESOURCE_EXHAUSTED"
    classification: Optional[str]  # "TWO_DISTINCT_REAL_ROOTS" or None
    roots: List[QuadraticSurd]
    discriminant: Optional[Rational]
    radicand: Optional[int]
    a: Optional[Rational] = None
    b: Optional[Rational] = None
    c: Optional[Rational] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_span: Optional[Span] = None


def generate_worker_prime_table() -> List[int]:
    """Generate complete list of primes <= 65536 using independent Sieve of Eratosthenes."""
    limit = 65536
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            for i in range(p * p, limit + 1, p):
                sieve[i] = False
    primes = [p for p in range(2, limit + 1) if sieve[p]]
    if len(primes) != 6542 or primes[0] != 2 or primes[-1] != 65521:
        raise RuntimeError("Worker prime sieve verification failed.")
    return primes


WORKER_PRIMES_UP_TO_65536: List[int] = generate_worker_prime_table()


def _check_rational_bits(r: Rational, max_bits: int = 256, op_name: str = "intermediate") -> Rational:
    """Ensure integer bit length of numerator and denominator does not exceed max_bits."""
    if r.numerator.bit_length() > max_bits or r.denominator.bit_length() > max_bits:
        raise EvaluationResourceLimitError(
            f"Integer bit length exceeded in {op_name} (max {max_bits} bits)."
        )
    return r


def extract_quadratic_coefficients(
    node: ASTNode,
    target_var: str = "x",
    max_nodes: int = 100,
    max_depth: int = 20,
    max_bits: int = 256,
    _current_depth: int = 0,
    _node_counter: Optional[list] = None,
) -> Tuple[Rational, Rational, Rational]:
    """Reduce an AST node to canonical quadratic coefficients (c2, c1, c0) representing c2*x^2 + c1*x + c0.

    Guarantees:
    - Pure integer/Rational arithmetic over Q.
    - Strict 256-bit integer ceiling on all intermediates.
    - Zero in-process SymPy or floating-point operations.
    - Domain-safety: fail closed on variable-dependent exponent 0, 0^0, and division by zero.
    - Rejects nonlinear expressions with degree > 2, variable denominators, and unsupported nodes.
    """
    if _node_counter is None:
        _node_counter = [0]

    _node_counter[0] += 1
    if _node_counter[0] > max_nodes:
        raise NonQuadraticSurdExpressionError(
            "AST node budget exceeded during quadratic analysis.",
            code="ERR_OUT_OF_SCOPE",
        )

    if _current_depth > max_depth:
        raise NonQuadraticSurdExpressionError(
            "AST recursion depth exceeded during quadratic analysis.",
            code="ERR_OUT_OF_SCOPE",
        )

    if isinstance(node, IntegerLiteral):
        if node.value.bit_length() > max_bits:
            raise EvaluationResourceLimitError("Integer bit length exceeded in literal.")
        return (Rational(0), Rational(0), Rational(node.value))

    elif isinstance(node, Variable):
        if node.name == target_var:
            return (Rational(0), Rational(1), Rational(0))
        raise NonQuadraticSurdExpressionError(
            f"Unexpected variable {node.name!r} during single-variable quadratic analysis.",
            code="ERR_OUT_OF_SCOPE",
        )

    elif isinstance(node, Group):
        return extract_quadratic_coefficients(
            node.inner, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

    elif isinstance(node, UnaryOp):
        c2, c1, c0 = extract_quadratic_coefficients(
            node.operand, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        if node.op == "+":
            return (c2, c1, c0)
        elif node.op == "-":
            _check_rational_bits(c2, max_bits, "unary negation c2")
            _check_rational_bits(c1, max_bits, "unary negation c1")
            _check_rational_bits(c0, max_bits, "unary negation c0")
            return (-c2, -c1, -c0)
        raise NonQuadraticSurdExpressionError(f"Unsupported unary operator: {node.op!r}")

    elif isinstance(node, BinaryOp):
        a2, a1, a0 = extract_quadratic_coefficients(
            node.left, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        b2, b1, b0 = extract_quadratic_coefficients(
            node.right, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

        if node.op == "+":
            r2 = _check_rational_bits(a2 + b2, max_bits, "addition c2")
            r1 = _check_rational_bits(a1 + b1, max_bits, "addition c1")
            r0 = _check_rational_bits(a0 + b0, max_bits, "addition c0")
            return (r2, r1, r0)

        elif node.op == "-":
            r2 = _check_rational_bits(a2 - b2, max_bits, "subtraction c2")
            r1 = _check_rational_bits(a1 - b1, max_bits, "subtraction c1")
            r0 = _check_rational_bits(a0 - b0, max_bits, "subtraction c0")
            return (r2, r1, r0)

        elif node.op == "*":
            # Degree > 2 detection in convolution
            if not a2.is_zero and (not b2.is_zero or not b1.is_zero):
                raise NonQuadraticSurdExpressionError(
                    "Polynomial degree > 2 detected in multiplication.",
                    code="ERR_OUT_OF_SCOPE",
                )
            if not a1.is_zero and not b2.is_zero:
                raise NonQuadraticSurdExpressionError(
                    "Polynomial degree > 2 detected in multiplication.",
                    code="ERR_OUT_OF_SCOPE",
                )

            # Degree 2 coefficient: a2*b0 + a1*b1 + a0*b2
            t1 = _check_rational_bits(a2 * b0, max_bits, "mult a2*b0")
            t2 = _check_rational_bits(a1 * b1, max_bits, "mult a1*b1")
            t3 = _check_rational_bits(a0 * b2, max_bits, "mult a0*b2")
            r2 = _check_rational_bits(t1 + t2 + t3, max_bits, "mult c2")

            # Degree 1 coefficient: a1*b0 + a0*b1
            t4 = _check_rational_bits(a1 * b0, max_bits, "mult a1*b0")
            t5 = _check_rational_bits(a0 * b1, max_bits, "mult a0*b1")
            r1 = _check_rational_bits(t4 + t5, max_bits, "mult c1")

            # Degree 0 coefficient: a0*b0
            r0 = _check_rational_bits(a0 * b0, max_bits, "mult c0")

            return (r2, r1, r0)

        elif node.op == "/":
            if not b2.is_zero or not b1.is_zero:
                raise NonQuadraticSurdExpressionError(
                    "Division by expression containing variable is unsupported.",
                    code="ERR_OUT_OF_SCOPE",
                )
            if b0.is_zero:
                raise DomainError(
                    "Division by zero constant in expression.",
                    code="ERR_DOMAIN_DIV_ZERO",
                )
            r2 = _check_rational_bits(a2 / b0, max_bits, "div c2")
            r1 = _check_rational_bits(a1 / b0, max_bits, "div c1")
            r0 = _check_rational_bits(a0 / b0, max_bits, "div c0")
            return (r2, r1, r0)

        else:
            raise NonQuadraticSurdExpressionError(f"Unsupported binary operator: {node.op!r}")

    elif isinstance(node, Power):
        exp_val = node.exponent.value
        if exp_val < 0:
            raise NonQuadraticSurdExpressionError(
                "Negative exponent is unsupported in quadratic scope.",
                code="ERR_OUT_OF_SCOPE",
            )
        elif exp_val == 0:
            a2, a1, a0 = extract_quadratic_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not a2.is_zero or not a1.is_zero:
                raise NonQuadraticSurdExpressionError(
                    "Variable-dependent base raised to power 0 is domain-unsafe.",
                    code="ERR_OUT_OF_SCOPE",
                )
            if a0.is_zero:
                raise DomainError(
                    "Undefined constant expression 0^0 detected.",
                    code="ERR_DOMAIN_ZERO_POWER_ZERO",
                )
            return (Rational(0), Rational(0), Rational(1))

        elif exp_val == 1:
            return extract_quadratic_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )

        elif exp_val == 2:
            a2, a1, a0 = extract_quadratic_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not a2.is_zero:
                raise NonQuadraticSurdExpressionError(
                    "Squaring expression with degree >= 2 produces degree >= 4.",
                    code="ERR_OUT_OF_SCOPE",
                )
            r2 = _check_rational_bits(a1 * a1, max_bits, "power2 c2")
            two_a1 = _check_rational_bits(Rational(2) * a1, max_bits, "power2 2*a1")
            r1 = _check_rational_bits(two_a1 * a0, max_bits, "power2 c1")
            r0 = _check_rational_bits(a0 * a0, max_bits, "power2 c0")
            return (r2, r1, r0)

        else:
            a2, a1, a0 = extract_quadratic_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not a2.is_zero or not a1.is_zero:
                raise NonQuadraticSurdExpressionError(
                    f"Power of variable expression with exponent {exp_val} has degree > 2.",
                    code="ERR_OUT_OF_SCOPE",
                )
            if exp_val > 10:
                raise NonQuadraticSurdExpressionError(
                    f"Constant exponent {exp_val} exceeds allowable maximum of 10.",
                    code="ERR_OUT_OF_SCOPE",
                )
            if (
                a0.numerator.bit_length() * exp_val > max_bits
                or a0.denominator.bit_length() * exp_val > max_bits
            ):
                raise EvaluationResourceLimitError("Integer bit length exceeded during constant power evaluation.")
            return (Rational(0), Rational(0), Rational(a0.numerator ** exp_val, a0.denominator ** exp_val))

    else:
        raise NonQuadraticSurdExpressionError(
            f"Unsupported AST node type for quadratic analysis: {type(node).__name__}",
            code="ERR_OUT_OF_SCOPE",
        )


def reduce_equation_quadratic_surd(
    eq_ast: Equation, target_var: str = "x", max_bits: int = 256
) -> Tuple[Rational, Rational, Rational]:
    """Reduce Equation(LHS, RHS) to A*x^2 + B*x + C = 0 where A = a2_L - a2_R, B = a1_L - a1_R, C = a0_L - a0_R."""
    a2_L, a1_L, a0_L = extract_quadratic_coefficients(eq_ast.left, target_var, max_bits=max_bits)
    a2_R, a1_R, a0_R = extract_quadratic_coefficients(eq_ast.right, target_var, max_bits=max_bits)

    A = _check_rational_bits(a2_L - a2_R, max_bits, "equation reduction A")
    B = _check_rational_bits(a1_L - a1_R, max_bits, "equation reduction B")
    C = _check_rational_bits(a0_L - a0_R, max_bits, "equation reduction C")

    return (A, B, C)


def solve_quadratic_surd_equation(
    equation: Equation,
    budget: Optional[EvaluationBudget] = None,
    max_bits: int = 256,
) -> QuadraticSurdSolverResult:
    """Solve an exact univariate real quadratic equation A*x^2 + B*x + C = 0 over Q returning exact surd roots in Q(sqrt(d)).

    Guarantees:
    - Pure-Python integer and exact Rational arithmetic.
    - True quadratic requirement: A != 0. If A == 0, returns OUT_OF_SCOPE.
    - Exact deterministic discriminant computation: Delta = B^2 - 4*A*C.
    - Delta <= 0 or Delta is rational square: returns OUT_OF_SCOPE (handled by v2).
    - Delta > 0 and non-rational square:
      - Independent squarefree decomposition with prime trial limit 65536.
      - If remainder R < 2^32, returns SUCCESS with [r_minus, r_plus].
      - If remainder R >= 2^32, returns RESOURCE_EXHAUSTED (ERR_SURD_NORMALIZATION_RESOURCE_LIMIT).
    """
    if not isinstance(equation, Equation):
        raise TypeError(f"solve_quadratic_surd_equation requires an Equation AST, got: {type(equation).__name__}")

    try:
        A, B, C = reduce_equation_quadratic_surd(equation, "x", max_bits=max_bits)
    except NonQuadraticSurdExpressionError as err:
        return QuadraticSurdSolverResult(
            status="OUT_OF_SCOPE",
            classification=None,
            roots=[],
            discriminant=None,
            radicand=None,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
        )
    except DomainError as err:
        return QuadraticSurdSolverResult(
            status="DOMAIN_ERROR",
            classification=None,
            roots=[],
            discriminant=None,
            radicand=None,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
        )
    except EvaluationResourceLimitError as err:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=None,
            radicand=None,
            error_code="ERR_RESOURCE_EXHAUSTED",
            error_message=str(err),
        )

    # True quadratic check: A != 0
    if A.is_zero:
        return QuadraticSurdSolverResult(
            status="OUT_OF_SCOPE",
            classification=None,
            roots=[],
            discriminant=None,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_DEGENERATE_AFFINE_EQUATION",
            error_message="Equation has degree <= 1 (A == 0) and is not a true quadratic.",
        )

    # Compute Discriminant Delta = B^2 - 4*A*C
    try:
        B2 = _check_rational_bits(B * B, max_bits, "B^2")
        four_A = _check_rational_bits(Rational(4) * A, max_bits, "4*A")
        four_AC = _check_rational_bits(four_A * C, max_bits, "4*A*C")
        Delta = _check_rational_bits(B2 - four_AC, max_bits, "Delta = B^2 - 4*A*C")
        two_A = _check_rational_bits(Rational(2) * A, max_bits, "2*A")
    except EvaluationResourceLimitError as err:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=None,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_RESOURCE_EXHAUSTED",
            error_message=str(err),
        )

    # Surd solver is for strictly positive non-square discriminants only
    if Delta <= Rational(0):
        return QuadraticSurdSolverResult(
            status="OUT_OF_SCOPE",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_OUT_OF_SCOPE",
            error_message="Discriminant is <= 0; surd solver only handles positive non-square discriminants.",
        )

    p = Delta.numerator
    q = Delta.denominator

    if p.bit_length() > max_bits or q.bit_length() > max_bits:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_RESOURCE_EXHAUSTED",
            error_message="Discriminant integer bit length exceeded.",
        )

    # Normalization working product M = p * q
    M = p * q
    if M.bit_length() > 512:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_SURD_NORMALIZATION_RESOURCE_LIMIT",
            error_message="Normalization working integer product exceeds 512 bits.",
        )

    square_factor = 1
    R = M
    extraction_count = 0
    max_extractions = min(256, M.bit_length() // 2)

    for p_i in WORKER_PRIMES_UP_TO_65536:
        p_sq = p_i * p_i
        if p_sq > R:
            break
        while R % p_sq == 0:
            R //= p_sq
            square_factor *= p_i
            extraction_count += 1
            if square_factor.bit_length() > max_bits or extraction_count > max_extractions:
                return QuadraticSurdSolverResult(
                    status="RESOURCE_EXHAUSTED",
                    classification=None,
                    roots=[],
                    discriminant=Delta,
                    radicand=None,
                    a=A,
                    b=B,
                    c=C,
                    error_code="ERR_SURD_NORMALIZATION_RESOURCE_LIMIT",
                    error_message="Square factor bit length or extraction budget exceeded.",
                )

    if R == 1:
        # Exact rational square discriminant: belongs to v2
        return QuadraticSurdSolverResult(
            status="OUT_OF_SCOPE",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_RATIONAL_QUADRATIC_IN_SURD_SOLVER",
            error_message="Discriminant is an exact rational square; rational quadratic equations belong to schema v2.",
        )

    if R.bit_length() > 32:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_SURD_NORMALIZATION_RESOURCE_LIMIT",
            error_message="Squarefreeness cannot be certified within the bounded B2 normalization contract.",
        )

    # Certified squarefree radicand d = R
    d = R

    try:
        s = Rational(square_factor, q)
        _check_rational_bits(s, max_bits, "s = square_factor / q")

        # a = -B / (2A)
        neg_B = _check_rational_bits(-B, max_bits, "-B")
        rat_part = _check_rational_bits(neg_B / two_A, max_bits, "rat_part = -B / (2A)")

        # b0 = s / (2|A|)
        two_abs_A = _check_rational_bits(Rational(2) * abs(A), max_bits, "2*|A|")
        b0 = _check_rational_bits(s / two_abs_A, max_bits, "b0 = s / (2|A|)")

        neg_b0 = _check_rational_bits(-b0, max_bits, "-b0")

        root_minus = QuadraticSurd(rational_part=rat_part, sqrt_coefficient=neg_b0, radicand=d)
        root_plus = QuadraticSurd(rational_part=rat_part, sqrt_coefficient=b0, radicand=d)

        return QuadraticSurdSolverResult(
            status="SUCCESS",
            classification="TWO_DISTINCT_REAL_ROOTS",
            roots=[root_minus, root_plus],
            discriminant=Delta,
            radicand=d,
            a=A,
            b=B,
            c=C,
        )

    except EvaluationResourceLimitError as err:
        return QuadraticSurdSolverResult(
            status="RESOURCE_EXHAUSTED",
            classification=None,
            roots=[],
            discriminant=Delta,
            radicand=None,
            a=A,
            b=B,
            c=C,
            error_code="ERR_RESOURCE_EXHAUSTED",
            error_message=str(err),
        )
