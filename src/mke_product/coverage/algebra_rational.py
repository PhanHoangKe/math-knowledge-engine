"""MKE THPT Universal Coverage Engine — Rational Equation Domain Adapter.

Authoritative adapter for single-variable rational equations in Q(x)
with degree <= 2 proof capability, original-domain preservation,
and independent deterministic verification.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from mke_product.core.rational import Rational
from mke_product.coverage.adapters import (
    DifficultyLevel,
    DomainAdapter,
    DomainClassification,
    ExecutionOptions,
    MethodAssessment as CoverageMethodAssessment,
)
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
    AllRealsExceptFiniteEntity,
    CandidateMetadata,
    CandidateSolution,
    DomainCheck,
    EmptyRealSolutionEntity,
    FiniteRootCollectionEntity,
    ProblemIR,
    ProblemKind,
    ProofObligationResult,
    RationalScalarEntity,
    RealQuadraticSurdEntity,
    ResidualCheck,
    SingleEquationPayload,
    SolutionTrace,
    SymbolicEntity,
    TraceStep,
    VerificationDisposition,
    VerificationLevel,
    VerificationReport,
)
from mke_product.coverage.legacy_quadratic import LegacyQuadraticAdapter
from mke_product.domain.exact import (
    _format_surd_latex,
    compute_quadratic_discriminant,
)
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


class RationalAlgebraError(Exception):
    """Base error for rational equation operations."""
    pass


class DegreeOutOfScopeError(RationalAlgebraError):
    """Raised when polynomial/rational degree exceeds quadratic proof envelope (deg <= 2)."""
    pass


class UnsupportedNodeError(RationalAlgebraError):
    """Raised when AST contains unsupported node types (Radical, FunctionCall, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Exact Polynomial in Q[x]
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PolyQ:
    """Exact univariate polynomial P(x) = sum(coeffs[i] * x^i) with coefficients in Q."""
    coeffs: Tuple[Rational, ...]  # coeffs[0] + coeffs[1]*x + ...

    def __post_init__(self) -> None:
        c_list = list(self.coeffs)
        while len(c_list) > 1 and c_list[-1].is_zero:
            c_list.pop()
        object.__setattr__(self, "coeffs", tuple(c_list))

    @classmethod
    def zero(cls) -> PolyQ:
        return cls((Rational(0, 1),))

    @classmethod
    def constant(cls, val: int | Rational) -> PolyQ:
        r = Rational(val, 1) if isinstance(val, int) else val
        return cls((r,))

    @classmethod
    def variable(cls) -> PolyQ:
        return cls((Rational(0, 1), Rational(1, 1)))

    @property
    def is_zero(self) -> bool:
        return len(self.coeffs) == 1 and self.coeffs[0].is_zero

    @property
    def degree(self) -> int:
        if self.is_zero:
            return 0
        return len(self.coeffs) - 1

    @property
    def leading_coeff(self) -> Rational:
        return self.coeffs[-1]

    def coeff(self, i: int) -> Rational:
        if 0 <= i < len(self.coeffs):
            return self.coeffs[i]
        return Rational(0, 1)

    def __neg__(self) -> PolyQ:
        return PolyQ(tuple(-c for c in self.coeffs))

    def __add__(self, other: PolyQ) -> PolyQ:
        max_len = max(len(self.coeffs), len(other.coeffs))
        new_coeffs = tuple(self.coeff(i) + other.coeff(i) for i in range(max_len))
        return PolyQ(new_coeffs)

    def __sub__(self, other: PolyQ) -> PolyQ:
        max_len = max(len(self.coeffs), len(other.coeffs))
        new_coeffs = tuple(self.coeff(i) - other.coeff(i) for i in range(max_len))
        return PolyQ(new_coeffs)

    def __mul__(self, other: PolyQ) -> PolyQ:
        if self.is_zero or other.is_zero:
            return PolyQ.zero()
        res_len = len(self.coeffs) + len(other.coeffs) - 1
        new_coeffs = [Rational(0, 1)] * res_len
        for i, c1 in enumerate(self.coeffs):
            if c1.is_zero:
                continue
            for j, c2 in enumerate(other.coeffs):
                new_coeffs[i + j] = new_coeffs[i + j] + c1 * c2
        return PolyQ(tuple(new_coeffs))

    def scale(self, scalar: Rational) -> PolyQ:
        if scalar.is_zero:
            return PolyQ.zero()
        return PolyQ(tuple(c * scalar for c in self.coeffs))

    def divmod_poly(self, other: PolyQ) -> Tuple[PolyQ, PolyQ]:
        if other.is_zero:
            raise ZeroDivisionError("Polynomial division by zero polynomial")
        rem = self
        if rem.is_zero or rem.degree < other.degree:
            return PolyQ.zero(), rem
        quot_len = rem.degree - other.degree + 1
        quot_coeffs = [Rational(0, 1)] * quot_len
        while not rem.is_zero and rem.degree >= other.degree:
            deg_diff = rem.degree - other.degree
            lead_quot = rem.leading_coeff / other.leading_coeff
            quot_coeffs[deg_diff] = lead_quot
            term_coeffs = [Rational(0, 1)] * deg_diff + [lead_quot * c for c in other.coeffs]
            rem = rem - PolyQ(tuple(term_coeffs))
        return PolyQ(tuple(quot_coeffs)), rem

    def gcd_poly(self, other: PolyQ) -> PolyQ:
        a = self
        b = other
        while not b.is_zero:
            _, rem = a.divmod_poly(b)
            a, b = b, rem
        if a.is_zero:
            return a
        return a.scale(Rational(1, 1) / a.leading_coeff)

    def eval_at_rational(self, r: Rational) -> Rational:
        res = Rational(0, 1)
        for c in reversed(self.coeffs):
            res = res * r + c
        return res

    def to_latex(self, var: str = "x") -> str:
        if self.is_zero:
            return "0"
        parts: List[str] = []
        for i in reversed(range(len(self.coeffs))):
            c = self.coeffs[i]
            if c.is_zero:
                continue
            if i == 0:
                parts.append(str(c))
            elif i == 1:
                if c == Rational(1, 1):
                    parts.append(var)
                elif c == Rational(-1, 1):
                    parts.append(f"-{var}")
                else:
                    parts.append(f"{c}*{var}")
            else:
                if c == Rational(1, 1):
                    parts.append(f"{var}^{i}")
                elif c == Rational(-1, 1):
                    parts.append(f"-{var}^{i}")
                else:
                    parts.append(f"{c}*{var}^{i}")
        res = " + ".join(parts).replace(" + -", " - ")
        return res if res else "0"


# ---------------------------------------------------------------------------
# Exact Number Field Q(sqrt(d)) for Residual Evaluation
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NumberFieldElement:
    """Exact element u + v*sqrt(d) in Q(sqrt(d)). If d == 1, purely in Q."""
    u: Rational
    v: Rational
    d: int = 1

    @classmethod
    def from_rational(cls, r: Rational, d: int = 1) -> NumberFieldElement:
        return cls(r, Rational(0, 1), d)

    @classmethod
    def from_surd_entity(cls, ent: RealQuadraticSurdEntity) -> NumberFieldElement:
        if ent.r <= 0 or ent.d <= 0:
            raise ValueError(f"Invalid surd parameters: r={ent.r}, d={ent.d}")
        u = Rational(ent.p, ent.r)
        if ent.q == 0:
            return cls.from_rational(u)
        v = Rational(ent.q, ent.r)
        if v.is_zero:
            return cls.from_rational(u)
        s = math.isqrt(ent.d)
        if s * s == ent.d:
            val = u + v * Rational(s, 1)
            return cls.from_rational(val)
        return cls(u, v, ent.d)

    @property
    def is_zero(self) -> bool:
        return self.u.is_zero and self.v.is_zero

    def __neg__(self) -> NumberFieldElement:
        return NumberFieldElement(-self.u, -self.v, self.d)

    def __add__(self, other: NumberFieldElement) -> NumberFieldElement:
        if self.d != other.d and not self.v.is_zero and not other.v.is_zero:
            raise ValueError("Incompatible quadratic fields")
        d = self.d if not self.v.is_zero else other.d
        return NumberFieldElement(self.u + other.u, self.v + other.v, d)

    def __sub__(self, other: NumberFieldElement) -> NumberFieldElement:
        return self + (-other)

    def __mul__(self, other: NumberFieldElement) -> NumberFieldElement:
        if self.d != other.d and not self.v.is_zero and not other.v.is_zero:
            raise ValueError("Incompatible quadratic fields")
        d = self.d if not self.v.is_zero else other.d
        new_u = self.u * other.u + self.v * other.v * Rational(d, 1)
        new_v = self.u * other.v + self.v * other.u
        return NumberFieldElement(new_u, new_v, d)

    def __truediv__(self, other: NumberFieldElement) -> NumberFieldElement:
        if other.is_zero:
            raise ZeroDivisionError("Field division by algebraic zero")
        d = other.d if not other.v.is_zero else self.d
        denom = other.u * other.u - other.v * other.v * Rational(d, 1)
        if denom.is_zero:
            raise ZeroDivisionError("Field division by algebraic zero")
        num_u = self.u * other.u - self.v * other.v * Rational(d, 1)
        num_v = self.v * other.u - self.u * other.v
        return NumberFieldElement(num_u / denom, num_v / denom, d)


# ---------------------------------------------------------------------------
# Exact Rational Function in Q(x)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RationalFractionQ:
    """Exact rational fraction P(x) / Q(x) in Q(x) preserving common denominator."""
    num: PolyQ
    den: PolyQ

    def __post_init__(self) -> None:
        if self.den.is_zero:
            raise ZeroDivisionError("Denominator polynomial cannot be zero")

    @classmethod
    def from_poly(cls, p: PolyQ) -> RationalFractionQ:
        return cls(p, PolyQ.constant(1))

    @classmethod
    def zero(cls) -> RationalFractionQ:
        return cls(PolyQ.zero(), PolyQ.constant(1))

    @classmethod
    def constant(cls, val: int | Rational) -> RationalFractionQ:
        return cls(PolyQ.constant(val), PolyQ.constant(1))

    @classmethod
    def variable(cls) -> RationalFractionQ:
        return cls(PolyQ.variable(), PolyQ.constant(1))

    def __neg__(self) -> RationalFractionQ:
        return RationalFractionQ(-self.num, self.den)

    def __add__(self, other: RationalFractionQ) -> RationalFractionQ:
        g = self.den.gcd_poly(other.den)
        d1_div_g, _ = self.den.divmod_poly(g)
        d2_div_g, _ = other.den.divmod_poly(g)
        new_num = self.num * d2_div_g + other.num * d1_div_g
        new_den = d1_div_g * other.den
        return RationalFractionQ(new_num, new_den)

    def __sub__(self, other: RationalFractionQ) -> RationalFractionQ:
        g = self.den.gcd_poly(other.den)
        d1_div_g, _ = self.den.divmod_poly(g)
        d2_div_g, _ = other.den.divmod_poly(g)
        new_num = self.num * d2_div_g - other.num * d1_div_g
        new_den = d1_div_g * other.den
        return RationalFractionQ(new_num, new_den)

    def __mul__(self, other: RationalFractionQ) -> RationalFractionQ:
        return RationalFractionQ(self.num * other.num, self.den * other.den)

    def __truediv__(self, other: RationalFractionQ) -> RationalFractionQ:
        if other.num.is_zero:
            raise ZeroDivisionError("Division by zero rational function")
        return RationalFractionQ(self.num * other.den, self.den * other.num)


# ---------------------------------------------------------------------------
# AST Walkers and Evaluation
# ---------------------------------------------------------------------------

def ast_to_rational_fraction(node: ASTNode, target_var: str) -> RationalFractionQ:
    """Recursively normalize an AST node into an exact RationalFractionQ."""
    if isinstance(node, IntegerLiteral):
        return RationalFractionQ.constant(node.value)

    if isinstance(node, Variable):
        if node.name != target_var:
            raise UnsupportedNodeError(f"Unsupported variable {node.name!r} (expected {target_var!r})")
        return RationalFractionQ.variable()

    if isinstance(node, Group):
        return ast_to_rational_fraction(node.inner, target_var)

    if isinstance(node, UnaryOp):
        operand = ast_to_rational_fraction(node.operand, target_var)
        if node.op == "+":
            return operand
        elif node.op == "-":
            return -operand
        raise UnsupportedNodeError(f"Unsupported unary operator {node.op!r}")

    if isinstance(node, BinaryOp):
        left = ast_to_rational_fraction(node.left, target_var)
        right = ast_to_rational_fraction(node.right, target_var)
        if node.op == "+":
            return left + right
        elif node.op == "-":
            return left - right
        elif node.op == "*":
            return left * right
        elif node.op == "/":
            return left / right
        raise UnsupportedNodeError(f"Unsupported binary operator {node.op!r}")

    if isinstance(node, Power):
        base = ast_to_rational_fraction(node.base, target_var)
        exp = node.exponent.value
        if exp == 0:
            if base.num.is_zero:
                raise ZeroDivisionError("Indeterminate expression 0^0 is undefined")
            return RationalFractionQ.constant(1)
        elif exp == 1:
            return base
        elif exp == 2:
            return base * base
        raise DegreeOutOfScopeError(f"Exponent {exp} exceeds quadratic bound <= 2")

    raise UnsupportedNodeError(f"Unsupported AST node type '{type(node).__name__}'")


def eval_ast_at_point(node: ASTNode, point: NumberFieldElement, target_var: str) -> NumberFieldElement:
    """Exact AST evaluation at a number field element."""
    if isinstance(node, IntegerLiteral):
        return NumberFieldElement.from_rational(Rational(node.value, 1), point.d)

    if isinstance(node, Variable):
        if node.name != target_var:
            raise UnsupportedNodeError(f"Unexpected variable {node.name!r}")
        return point

    if isinstance(node, Group):
        return eval_ast_at_point(node.inner, point, target_var)

    if isinstance(node, UnaryOp):
        operand = eval_ast_at_point(node.operand, point, target_var)
        if node.op == "+":
            return operand
        elif node.op == "-":
            return -operand
        raise UnsupportedNodeError(f"Unsupported unary op {node.op!r}")

    if isinstance(node, BinaryOp):
        l_val = eval_ast_at_point(node.left, point, target_var)
        r_val = eval_ast_at_point(node.right, point, target_var)
        if node.op == "+":
            return l_val + r_val
        elif node.op == "-":
            return l_val - r_val
        elif node.op == "*":
            return l_val * r_val
        elif node.op == "/":
            if r_val.is_zero:
                raise ZeroDivisionError("Denominator evaluated to zero at point")
            return l_val / r_val
        raise UnsupportedNodeError(f"Unsupported binary op {node.op!r}")

    if isinstance(node, Power):
        base_val = eval_ast_at_point(node.base, point, target_var)
        exp = node.exponent.value
        if exp == 0:
            if base_val.is_zero:
                raise ZeroDivisionError("0^0 is undefined")
            return NumberFieldElement.from_rational(Rational(1, 1), point.d)
        elif exp == 1:
            return base_val
        elif exp == 2:
            return base_val * base_val
        raise DegreeOutOfScopeError(f"Exponent {exp} exceeds bound")

    raise UnsupportedNodeError(f"Unsupported AST node {type(node).__name__}")


# ---------------------------------------------------------------------------
# Algebraic Solvers and Root Deduplication
# ---------------------------------------------------------------------------

def solve_poly_degree_le_2(
    p: PolyQ,
) -> Tuple[str, Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...]]:
    """Solve P(x) = 0 for deg(P) <= 2.
    
    Returns (classification_string, tuple_of_roots).
    """
    if p.is_zero:
        return ("IDENTITY", ())
    if p.degree == 0:
        return ("CONTRADICTION", ())
    if p.degree == 1:
        c0 = p.coeff(0)
        c1 = p.coeff(1)
        root = -c0 / c1
        return ("LINEAR", (RationalScalarEntity.from_rational(root),))
    if p.degree == 2:
        c0 = p.coeff(0)
        c1 = p.coeff(1)
        c2 = p.coeff(2)
        disc = compute_quadratic_discriminant(c2, c1, c0)
        if disc.is_negative:
            return ("QUADRATIC", ())
        two_a = Rational(2, 1) * c2
        if disc.is_zero:
            r = -c1 / two_a
            return ("QUADRATIC", (RationalScalarEntity.from_rational(r),))
        if disc.is_rational_square and disc.extracted_factor is not None:
            s = disc.extracted_factor.to_rational()
            r1 = (-c1 - s) / two_a
            r2 = (-c1 + s) / two_a
            if r2 < r1:
                r1, r2 = r2, r1
            return (
                "QUADRATIC",
                (
                    RationalScalarEntity.from_rational(r1),
                    RationalScalarEntity.from_rational(r2),
                ),
            )
        elif disc.extracted_factor is not None and disc.squarefree_kernel is not None:
            s = disc.extracted_factor.to_rational()
            d = disc.squarefree_kernel
            u = -c1 / two_a
            v = abs(s / two_a)
            common_denom = math.lcm(u.denominator, v.denominator)
            p_val = u.numerator * (common_denom // u.denominator)
            q_val = v.numerator * (common_denom // v.denominator)
            ent_minus = RealQuadraticSurdEntity(
                p=p_val,
                q=-q_val,
                d=d,
                r=common_denom,
                latex=_format_surd_latex(u, -v, d),
            )
            ent_plus = RealQuadraticSurdEntity(
                p=p_val,
                q=q_val,
                d=d,
                r=common_denom,
                latex=_format_surd_latex(u, v, d),
            )
            return ("QUADRATIC", (ent_minus, ent_plus))

    raise DegreeOutOfScopeError(f"Polynomial degree {p.degree} exceeds quadratic bound <= 2")


def _normalize_root_for_comparison(
    r: Any,
) -> Union[Rational, Tuple[Rational, Rational, int]]:
    """Normalize a root entity to either exact Rational or (u, v, d) where d is non-square and v != 0."""
    if isinstance(r, RationalScalarEntity):
        return r.to_rational
    if isinstance(r, RealQuadraticSurdEntity):
        if r.r <= 0 or r.d <= 0:
            raise ValueError(f"Invalid surd parameters: r={r.r}, d={r.d}")
        u = Rational(r.p, r.r)
        if r.q == 0:
            return u
        v = Rational(r.q, r.r)
        if v.is_zero:
            return u
        s = math.isqrt(r.d)
        if s * s == r.d:
            return u + v * Rational(s, 1)
        return (u, v, r.d)
    raise TypeError(f"Unsupported root entity type: {type(r).__name__}")


def are_roots_equal(
    r1: Any,
    r2: Any,
) -> bool:
    """Exact mathematical equality check between two algebraic root entities."""
    try:
        norm1 = _normalize_root_for_comparison(r1)
        norm2 = _normalize_root_for_comparison(r2)
    except Exception:
        return False

    # Rational vs Rational compares exact rational values
    if isinstance(norm1, Rational) and isinstance(norm2, Rational):
        return norm1 == norm2

    # Rational vs non-rational surd is unequal
    if isinstance(norm1, Rational) or isinstance(norm2, Rational):
        return False

    # Two non-rational surds: (u, v, d)
    u1, v1, d1 = norm1
    u2, v2, d2 = norm2

    # Require u1 == u2
    if u1 != u2:
        return False

    # g = gcd(d1, d2), a = d1/g, b = d2/g
    g = math.gcd(d1, d2)
    a = d1 // g
    b = d2 // g

    sa = math.isqrt(a)
    sb = math.isqrt(b)

    # d1/d2 is a rational square iff a and b are both perfect squares (use isqrt only)
    if sa * sa != a or sb * sb != b:
        return False

    # Compare v1*sqrt(a) == v2*sqrt(b) exactly as Rational coefficients
    return v1 * Rational(sa, 1) == v2 * Rational(sb, 1)


def is_root_in_collection(
    r: Any,
    collection: Sequence[Any],
) -> bool:
    return any(are_roots_equal(r, item) for item in collection)


def deduplicate_roots(
    roots: Sequence[Union[RationalScalarEntity, RealQuadraticSurdEntity]],
) -> Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...]:
    unique: List[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = []
    for r in roots:
        if not is_root_in_collection(r, unique):
            unique.append(r)
    return tuple(unique)


# ---------------------------------------------------------------------------
# Verifier-Only Exact Algebraic Certificate Helpers
# ---------------------------------------------------------------------------

def distinct_real_root_count(poly: PolyQ) -> int:
    """Verifier-only exact distinct real root count for deg <= 2 without solving roots."""
    if poly.is_zero:
        raise ValueError("Zero polynomial does not have a finite root count")
    if poly.degree == 0:
        return 0
    if poly.degree == 1:
        return 1
    if poly.degree == 2:
        c0 = poly.coeff(0)
        c1 = poly.coeff(1)
        c2 = poly.coeff(2)
        delta = c1 * c1 - Rational(4, 1) * c2 * c0
        if delta.is_negative:
            return 0
        if delta.is_zero:
            return 1
        return 2
    raise DegreeOutOfScopeError(f"Polynomial degree {poly.degree} > 2 exceeds quadratic proof envelope")


def poly_lcm(p1: PolyQ, p2: PolyQ) -> PolyQ:
    """Compute monic least common multiple of two polynomials in Q[x]."""
    if p1.is_zero or p2.is_zero:
        return PolyQ.zero()
    if p1.degree == 0:
        return p2.scale(Rational(1, 1) / p2.leading_coeff)
    if p2.degree == 0:
        return p1.scale(Rational(1, 1) / p1.leading_coeff)
    g = p1.gcd_poly(p2)
    p1_div_g, _ = p1.divmod_poly(g)
    prod = p1_div_g * p2
    return prod.scale(Rational(1, 1) / prod.leading_coeff)


def poly_squarefree(p: PolyQ) -> PolyQ:
    """Make a polynomial in Q[x] square-free for deg <= 2."""
    if p.is_zero or p.degree <= 1:
        return p if p.is_zero else p.scale(Rational(1, 1) / p.leading_coeff)
    if p.degree == 2:
        c0 = p.coeff(0)
        c1 = p.coeff(1)
        c2 = p.coeff(2)
        delta = c1 * c1 - Rational(4, 1) * c2 * c0
        if delta.is_zero:
            r = -c1 / (Rational(2, 1) * c2)
            return PolyQ((-r, Rational(1, 1)))
        return p.scale(Rational(1, 1) / p.leading_coeff)
    return p


def eval_poly_at_point(poly: PolyQ, pt: NumberFieldElement) -> NumberFieldElement:
    """Exact polynomial evaluation at a NumberFieldElement."""
    res = NumberFieldElement.from_rational(Rational(0, 1), pt.d)
    for c in reversed(poly.coeffs):
        res = res * pt + NumberFieldElement.from_rational(c, pt.d)
    return res



# ---------------------------------------------------------------------------
# AlgebraRationalAdapter Implementation
# ---------------------------------------------------------------------------

class AlgebraRationalAdapter(DomainAdapter):
    """Authoritative domain adapter for verified rational equations in Q(x)."""

    ADAPTER_ID: str = "mke.adapter.algebra_rational.v1"

    @property
    def adapter_id(self) -> str:
        return self.ADAPTER_ID

    @property
    def supported_problem_kinds(self) -> Tuple[ProblemKind, ...]:
        return (ProblemKind.ALGEBRA_EQUATION,)

    def _has_variable_denominator(self, ir: ProblemIR) -> bool:
        """Check if equation has any variable-bearing division denominator."""
        if not isinstance(ir.payload, SingleEquationPayload):
            return False
        target = ir.payload.target_variable
        for root_node in (ir.payload.left, ir.payload.right):
            for n in root_node.walk():
                if isinstance(n, BinaryOp) and n.op == "/":
                    if target in n.right.variables():
                        return True
        return False

    def _has_variable_exponent_zero_guard(self, ir: ProblemIR) -> bool:
        """Check if equation has any variable-bearing exponent-zero base."""
        if not isinstance(ir.payload, SingleEquationPayload):
            return False
        target = ir.payload.target_variable
        for root_node in (ir.payload.left, ir.payload.right):
            for n in root_node.walk():
                if isinstance(n, Power) and n.exponent.value == 0:
                    if target in n.base.variables():
                        return True
        return False

    def _extract_candidate_guards(self, ir: ProblemIR) -> List[ASTNode]:
        """Candidate-side structural guard traversal collecting variable-bearing
        division denominators and variable-bearing exponent-zero bases.
        """
        if not isinstance(ir.payload, SingleEquationPayload):
            return []
        guards: List[ASTNode] = []
        target = ir.payload.target_variable

        for root_node in (ir.payload.left, ir.payload.right):
            for n in root_node.walk():
                if isinstance(n, BinaryOp) and n.op == "/":
                    if target in n.right.variables():
                        guards.append(n.right)
                elif isinstance(n, Power) and n.exponent.value == 0:
                    if target in n.base.variables():
                        guards.append(n.base)
        return guards

    def _extract_verifier_guards(self, ir: ProblemIR) -> List[ASTNode]:
        """Independent verifier-side structural guard traversal.
        
        Strict Invariant: Verifier must not trust candidate-side guard collection.
        Collects variable-bearing division denominators and variable-bearing exponent-zero bases.
        """
        if not isinstance(ir.payload, SingleEquationPayload):
            return []
        guards: List[ASTNode] = []
        target = ir.payload.target_variable

        for root_node in (ir.payload.left, ir.payload.right):
            for n in root_node.walk():
                if isinstance(n, BinaryOp) and n.op == "/":
                    if target in n.right.variables():
                        guards.append(n.right)
                elif isinstance(n, Power) and n.exponent.value == 0:
                    if target in n.base.variables():
                        guards.append(n.base)
        return guards

    def _extract_denominators(self, ir: ProblemIR) -> List[ASTNode]:
        """Collect all denominator AST nodes present in the equation."""
        if not isinstance(ir.payload, SingleEquationPayload):
            return []
        denoms: List[ASTNode] = []
        target = ir.payload.target_variable

        for root_node in (ir.payload.left, ir.payload.right):
            for n in root_node.walk():
                if isinstance(n, BinaryOp) and n.op == "/":
                    if target in n.right.variables():
                        denoms.append(n.right)
        return denoms

    def can_handle(self, ir: ProblemIR) -> bool:
        """Predicate checking if ProblemIR is a supported single-variable rational or guarded equation."""
        if ir.problem_kind != ProblemKind.ALGEBRA_EQUATION:
            return False
        if not isinstance(ir.payload, SingleEquationPayload):
            return False

        target_var = ir.payload.target_variable
        all_vars = ir.payload.left.variables() | ir.payload.right.variables()
        if not all_vars or not all_vars.issubset({target_var}):
            return False

        if ir.variables and not set(ir.variables).issubset({target_var}):
            return False

        # Must have either a variable-bearing denominator OR a variable-bearing exponent-zero guard
        has_denom = self._has_variable_denominator(ir)
        has_exp0 = self._has_variable_exponent_zero_guard(ir)
        if not (has_denom or has_exp0):
            return False

        # Must not claim pure polynomial equations owned by LegacyQuadraticAdapter
        try:
            if LegacyQuadraticAdapter().can_handle(ir):
                return False
        except Exception:
            pass

        return True

    def _analyze_equation(
        self, ir: ProblemIR
    ) -> Tuple[
        RationalFractionQ,
        Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...],
        Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...],
    ]:
        """Normalize difference equation and extract domain exclusions and verified roots.
        
        Returns:
            (diff_fraction, excluded_points, true_roots)
        """
        if not isinstance(ir.payload, SingleEquationPayload):
            raise ValueError("Expected SingleEquationPayload")

        target_var = ir.payload.target_variable
        left_frac = ast_to_rational_fraction(ir.payload.left, target_var)
        right_frac = ast_to_rational_fraction(ir.payload.right, target_var)
        diff_frac = left_frac - right_frac

        # Extract domain exclusions from ALL variable guards in original AST
        raw_guards = self._extract_candidate_guards(ir)
        guard_polys: List[PolyQ] = []
        all_exclusions: List[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = []

        for g_node in raw_guards:
            g_frac = ast_to_rational_fraction(g_node, target_var)
            if g_frac.num.degree > 2 or g_frac.den.degree > 2:
                raise DegreeOutOfScopeError(
                    f"Guard degree exceeds quadratic bound: num={g_frac.num.degree}, den={g_frac.den.degree}"
                )
            if not g_frac.num.is_zero and g_frac.num.degree >= 1:
                guard_polys.append(g_frac.num)
                _, g_roots = solve_poly_degree_le_2(g_frac.num)
                all_exclusions.extend(g_roots)
            if not g_frac.den.is_zero and g_frac.den.degree >= 1:
                guard_polys.append(g_frac.den)

        # Also include any zeros of the common denominator in diff_frac
        if diff_frac.den.degree > 2:
            raise DegreeOutOfScopeError(f"Common denominator degree {diff_frac.den.degree} > 2")
        if not diff_frac.den.is_zero and diff_frac.den.degree >= 1:
            guard_polys.append(diff_frac.den)
            _, den_roots = solve_poly_degree_le_2(diff_frac.den)
            all_exclusions.extend(den_roots)

        domain_poly = PolyQ.constant(1)
        for gp in guard_polys:
            domain_poly = poly_lcm(domain_poly, gp)
            domain_poly = poly_squarefree(domain_poly)

        if domain_poly.degree > 2:
            raise DegreeOutOfScopeError(
                f"Domain exclusion polynomial degree {domain_poly.degree} exceeds quadratic bound <= 2"
            )

        unique_exclusions = deduplicate_roots(all_exclusions)

        # Solve cleared numerator
        if diff_frac.num.degree > 2:
            raise DegreeOutOfScopeError(f"Cleared numerator degree {diff_frac.num.degree} > 2")

        _, num_roots = solve_poly_degree_le_2(diff_frac.num)
        true_roots = tuple(r for r in num_roots if not is_root_in_collection(r, unique_exclusions))

        return diff_frac, unique_exclusions, true_roots

    def normalize(self, ir: ProblemIR) -> ProblemIR:
        """Perform domain-specific canonical normalization on the ProblemIR."""
        try:
            diff_frac, exclusions, _ = self._analyze_equation(ir)
            ex_str = ", ".join(f"x != {r.latex}" for r in exclusions) if exclusions else "none"
            trace_entry = (
                f"Normalized rational equation to cleared numerator {diff_frac.num.to_latex()} = 0 "
                f"with preserved domain exclusions: {ex_str}"
            )
        except Exception as exc:
            trace_entry = f"Failed exact bounded rational normalization: {exc}"

        return ir.model_copy(
            update={
                "normalization_trace": ir.normalization_trace + (trace_entry,),
            }
        )

    def classify(self, ir: ProblemIR) -> DomainClassification:
        """Classify equation sub-form, difficulty, and applicable methods."""
        try:
            diff_frac, exclusions, true_roots = self._analyze_equation(ir)
            num = diff_frac.num

            if num.is_zero:
                sub_form = "RATIONAL_IDENTITY_WITH_EXCLUSIONS" if exclusions else "RATIONAL_IDENTITY_UNRESTRICTED"
                diff = "MEDIUM" if exclusions else "EASY"
            elif num.degree == 0 or (len(true_roots) == 0):
                sub_form = "RATIONAL_CONTRADICTION"
                diff = "EASY"
            elif num.degree == 1:
                sub_form = "RATIONAL_LINEAR_NUMERATOR"
                diff = "EASY" if len(exclusions) <= 1 else "MEDIUM"
            elif num.degree == 2:
                sub_form = "RATIONAL_QUADRATIC_NUMERATOR"
                diff = "MEDIUM"
            else:
                sub_form = "RATIONAL_OUT_OF_SCOPE"
                diff = "HARD"
        except (DegreeOutOfScopeError, UnsupportedNodeError, Exception):
            return DomainClassification(
                problem_kind=ProblemKind.ALGEBRA_EQUATION,
                sub_form="RATIONAL_OUT_OF_SCOPE",
                difficulty="HARD",
                applicable_methods=(),
            )

        methods = (
            CoverageMethodAssessment(
                method_id="DOMAIN_THEN_CLEAR_DENOMINATORS",
                method_name_vi="Tìm điều kiện xác định và quy đồng khử mẫu",
                method_name_en="Find domain conditions and clear denominators",
                is_applicable=True,
                is_recommended=True,
                selection_reason="Phương pháp chuẩn sư phạm cho phương trình phân thức hữu tỉ",
            ),
            CoverageMethodAssessment(
                method_id="FACTOR_NUMERATOR_WITH_DOMAIN_FILTER",
                method_name_vi="Phân tích nhân tử và đối chiếu điều kiện",
                method_name_en="Factor numerator and filter with domain conditions",
                is_applicable=(sub_form in ("RATIONAL_LINEAR_NUMERATOR", "RATIONAL_QUADRATIC_NUMERATOR")),
                is_recommended=False,
                selection_reason="Áp dụng thuận tiện khi vế phải bằng 0 và tử số dễ phân tích",
            ),
        )

        return DomainClassification(
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            sub_form=sub_form,
            difficulty=diff,
            applicable_methods=methods,
        )

    def solve_candidates(
        self, ir: ProblemIR, options: Optional[ExecutionOptions] = None
    ) -> Tuple[CandidateSolution, ...]:
        """Generate typed candidate solutions."""
        try:
            diff_frac, exclusions, true_roots = self._analyze_equation(ir)
        except Exception as exc:
            # Fall back to empty candidate solution marked out of scope
            cand = CandidateSolution(
                candidate_id=f"cand_{ir.problem_id}",
                generator_engine="mke.algebra_rational.solver",
                raw_symbolic_output=f"UNSUPPORTED: {exc}",
                parsed_entities=(),
                execution_time_ms=0.1,
                metadata=CandidateMetadata(
                    engine_version="1.0.0",
                    transformation_steps=("error_fail_closed",),
                ),
            )
            return (cand,)

        parsed_entities: List[SymbolicEntity] = []
        if diff_frac.num.is_zero:
            if exclusions:
                parsed_entities.append(AllRealsExceptFiniteEntity(excluded_points=exclusions))
                raw_out = f"x \\in \\mathbb{{R}} \\setminus \\{{{', '.join(e.latex for e in exclusions)}\\}}"
            else:
                parsed_entities.append(AllRealSolutionEntity())
                raw_out = "x \\in \\mathbb{R}"
        elif not true_roots:
            parsed_entities.append(EmptyRealSolutionEntity())
            raw_out = "S = \\emptyset"
        else:
            parsed_entities.append(FiniteRootCollectionEntity(roots=true_roots))
            raw_out = f"S = \\{{{', '.join(r.latex for r in true_roots)}\\}}"

        cand = CandidateSolution(
            candidate_id=f"cand_{ir.problem_id}",
            generator_engine="mke.algebra_rational.solver",
            raw_symbolic_output=raw_out,
            parsed_entities=tuple(parsed_entities),
            execution_time_ms=0.5,
            metadata=CandidateMetadata(
                engine_version="1.0.0",
                transformation_steps=(
                    "original_domain_extraction",
                    "cleared_numerator_solve",
                    "domain_exclusion_filter",
                ),
            ),
        )
        return (cand,)

    def verify(self, ir: ProblemIR, candidate: CandidateSolution) -> VerificationReport:
        """Independently verify candidate solution using deterministic MKE logic."""
        # 1. Validate IR / payload shape enough to inspect the typed AST
        if ir.problem_kind != ProblemKind.ALGEBRA_EQUATION:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_kind_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Requires ALGEBRA_EQUATION problem kind",
            )

        if not isinstance(ir.payload, SingleEquationPayload):
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_payload_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Requires SingleEquationPayload",
            )

        target_var = ir.payload.target_variable
        all_vars = ir.payload.left.variables() | ir.payload.right.variables()
        if not all_vars or not all_vars.issubset({target_var}):
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_vars_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Equation variables {all_vars} incompatible with target variable {target_var!r}",
            )

        # 2 & 3. Independently normalize/rebuild the exact rational equation and
        # determine whether it is inside the supported proof envelope.
        # If the problem itself is outside the proof envelope (unsupported AST node,
        # degree overflow, etc.), return UNSUPPORTED / UNSUPPORTED regardless of candidate.
        try:
            left_frac = ast_to_rational_fraction(ir.payload.left, target_var)
            right_frac = ast_to_rational_fraction(ir.payload.right, target_var)
            diff_frac = left_frac - right_frac
            cleared_num = diff_frac.num

            guard_nodes = self._extract_verifier_guards(ir)
            guard_polys: List[PolyQ] = []
            for g_node in guard_nodes:
                g_frac = ast_to_rational_fraction(g_node, target_var)
                if g_frac.num.degree > 2 or g_frac.den.degree > 2:
                    raise DegreeOutOfScopeError(
                        f"Guard degree exceeds quadratic bound: num={g_frac.num.degree}, den={g_frac.den.degree}"
                    )
                if not g_frac.num.is_zero and g_frac.num.degree >= 1:
                    guard_polys.append(g_frac.num)
                if not g_frac.den.is_zero and g_frac.den.degree >= 1:
                    guard_polys.append(g_frac.den)

            if diff_frac.den.degree > 2:
                raise DegreeOutOfScopeError(
                    f"Common denominator degree {diff_frac.den.degree} exceeds quadratic bound <= 2"
                )
            if not diff_frac.den.is_zero and diff_frac.den.degree >= 1:
                guard_polys.append(diff_frac.den)

            domain_poly = PolyQ.constant(1)
            for gp in guard_polys:
                domain_poly = poly_lcm(domain_poly, gp)
                domain_poly = poly_squarefree(domain_poly)

            if not cleared_num.is_zero and cleared_num.degree > 2:
                raise DegreeOutOfScopeError(
                    f"Cleared numerator degree {cleared_num.degree} exceeds quadratic bound <= 2"
                )
            if domain_poly.degree > 2:
                raise DegreeOutOfScopeError(
                    f"Domain exclusion polynomial degree {domain_poly.degree} exceeds quadratic bound <= 2"
                )

        except (DegreeOutOfScopeError, UnsupportedNodeError, ZeroDivisionError, Exception) as exc:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                proof_obligations=(
                    ProofObligationResult(
                        obligation_id="PROOF_ENVELOPE",
                        description="Rational equation within Q(x) deg <= 2 proof envelope",
                        passed=False,
                        details=str(exc),
                    ),
                ),
                certificate_hash=hashlib.sha256(f"out_of_scope_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Problem outside proof envelope: {exc}",
            )

        # 4. ONLY AFTER the problem is proven inside the supported proof envelope,
        # validate candidate shape and content.
        if len(candidate.parsed_entities) != 1:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.REJECTED,
                proof_obligations=(
                    ProofObligationResult(
                        obligation_id="SINGLE_AUTHORITATIVE_ENTITY",
                        description="Candidate solution must contain exactly one parsed entity",
                        passed=False,
                        details=f"Found {len(candidate.parsed_entities)} entities",
                    ),
                ),
                certificate_hash=hashlib.sha256(f"entity_count_mismatch_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Expected exactly 1 parsed solution entity, found {len(candidate.parsed_entities)}",
            )

        cand_entity = candidate.parsed_entities[0]

        # -------------------------------------------------------------------
        # Case 1: Candidate is FiniteRootCollectionEntity
        # -------------------------------------------------------------------
        if isinstance(cand_entity, FiniteRootCollectionEntity):
            all_in_domain = True
            all_satisfied = True
            residuals: List[ResidualCheck] = []
            domain_checks: List[DomainCheck] = []

            for idx, r in enumerate(cand_entity.roots):
                if isinstance(r, RationalScalarEntity):
                    pt = NumberFieldElement.from_rational(r.to_rational)
                elif isinstance(r, RealQuadraticSurdEntity):
                    try:
                        pt = NumberFieldElement.from_surd_entity(r)
                    except Exception:
                        all_in_domain = False
                        all_satisfied = False
                        domain_checks.append(
                            DomainCheck(
                                condition_desc=f"Root {idx} malformed surd entity",
                                satisfied=False,
                            )
                        )
                        continue
                else:
                    all_in_domain = False
                    all_satisfied = False
                    domain_checks.append(
                        DomainCheck(
                            condition_desc=f"Root {idx} of unsupported type {type(r).__name__}",
                            satisfied=False,
                        )
                    )
                    continue

                # 1. Exact-check original domain
                in_dom = True
                try:
                    dp_val = eval_poly_at_point(domain_poly, pt)
                    if dp_val.is_zero:
                        in_dom = False

                    if in_dom:
                        for g_node in guard_nodes:
                            g_val = eval_ast_at_point(g_node, pt, target_var)
                            if g_val.is_zero:
                                in_dom = False
                                break

                    if in_dom:
                        lhs_val = eval_ast_at_point(ir.payload.left, pt, target_var)
                        rhs_val = eval_ast_at_point(ir.payload.right, pt, target_var)
                except ZeroDivisionError:
                    in_dom = False
                except Exception:
                    in_dom = False

                domain_checks.append(
                    DomainCheck(
                        condition_desc=f"Root {idx} ({r.latex}) in valid domain",
                        satisfied=in_dom,
                    )
                )
                if not in_dom:
                    all_in_domain = False

                # 2. Exact-check original AST equation satisfaction
                is_zero = False
                if in_dom:
                    try:
                        diff_val = lhs_val - rhs_val
                        is_zero = diff_val.is_zero
                    except Exception:
                        is_zero = False

                residuals.append(
                    ResidualCheck(
                        point_desc=f"Candidate root {idx} ({r.latex})",
                        residual_value="0 (EXACT_ZERO)" if is_zero else "NON_ZERO",
                        is_exact_zero=is_zero,
                    )
                )
                if not is_zero:
                    all_satisfied = False

            # If any candidate root violates domain or equation, reject immediately
            if not all_in_domain or not all_satisfied:
                obligations = [
                    ProofObligationResult(
                        obligation_id="ORIGINAL_DOMAIN_CONSTRAINTS",
                        description="Candidate roots lie in the original domain",
                        passed=all_in_domain,
                    ),
                    ProofObligationResult(
                        obligation_id="EQUATION_SATISFACTION",
                        description="Candidate roots satisfy original LHS = RHS",
                        passed=all_satisfied,
                    ),
                ]
                cert_hash = hashlib.sha256(f"rej_{ir.problem_id}".encode("utf-8")).hexdigest()
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    proof_obligations=tuple(obligations),
                    residual_evaluations=tuple(residuals),
                    domain_boundary_checks=tuple(domain_checks),
                    certificate_hash=cert_hash,
                    details="Candidate root violates domain condition or equation equality",
                )

            cand_unique = deduplicate_roots(cand_entity.roots)

            # Section C: Identity vs finite candidate handling
            if cleared_num.is_zero:
                # For identity, FiniteRootCollectionEntity can never be complete.
                # All supplied points are valid solutions on domain, so result is at most PARTIAL/PARTIAL.
                # An empty finite set on an identity must never be EXACT_VERIFIED.
                obligations = [
                    ProofObligationResult(
                        obligation_id="ORIGINAL_DOMAIN_CONSTRAINTS",
                        description="All accepted roots satisfy original domain constraints",
                        passed=True,
                    ),
                    ProofObligationResult(
                        obligation_id="EQUATION_SATISFACTION",
                        description="All accepted roots satisfy original LHS = RHS",
                        passed=True,
                    ),
                    ProofObligationResult(
                        obligation_id="SOLUTION_COMPLETENESS",
                        description="Finite root collection cannot be complete for an identity",
                        passed=False,
                        details="Identity equation has infinitely many solutions on its domain",
                    ),
                ]
                cert_payload = {
                    "problem_id": ir.problem_id,
                    "verifier": "MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    "level": VerificationLevel.PARTIAL.value,
                    "disposition": VerificationDisposition.PARTIAL.value,
                    "roots": [r.model_dump() for r in cand_unique],
                }
                cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.PARTIAL,
                    disposition=VerificationDisposition.PARTIAL,
                    proof_obligations=tuple(obligations),
                    residual_evaluations=tuple(residuals),
                    domain_boundary_checks=tuple(domain_checks),
                    certificate_hash=cert_hash,
                    details="Identity equation has infinite solutions; finite root set is at most partial",
                )

            # Section D point 6: Non-zero cleared numerator completeness certificate
            num_root_count = distinct_real_root_count(cleared_num)
            g_poly = cleared_num.gcd_poly(domain_poly)
            g_root_count = distinct_real_root_count(g_poly)
            expected_valid_count = num_root_count - g_root_count

            is_complete = (len(cand_unique) == expected_valid_count)

            obligations = [
                ProofObligationResult(
                    obligation_id="ORIGINAL_DOMAIN_CONSTRAINTS",
                    description="All accepted roots satisfy original domain constraints",
                    passed=True,
                ),
                ProofObligationResult(
                    obligation_id="EQUATION_SATISFACTION",
                    description="All accepted roots satisfy original LHS = RHS",
                    passed=True,
                ),
                ProofObligationResult(
                    obligation_id="EXCLUSIONS_PRESERVED",
                    description="All denominator exclusions are preserved and rejected",
                    passed=True,
                ),
                ProofObligationResult(
                    obligation_id="SOLUTION_COMPLETENESS",
                    description="Candidate solution set is complete for Q[x] degree <= 2",
                    passed=is_complete,
                    details=f"Candidate roots {len(cand_unique)}, expected valid roots {expected_valid_count}",
                ),
            ]

            if is_complete:
                level = VerificationLevel.EXACT_VERIFIED
                disp = VerificationDisposition.ACCEPTED
                details = "Exact verified complete rational root set"
            else:
                level = VerificationLevel.PARTIAL
                disp = VerificationDisposition.PARTIAL
                details = "Candidate solution is incomplete (missing valid roots)"

            cert_payload = {
                "problem_id": ir.problem_id,
                "verifier": "MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                "level": level.value,
                "disposition": disp.value,
                "roots": [r.model_dump() for r in cand_unique],
            }
            cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()

            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=level,
                disposition=disp,
                proof_obligations=tuple(obligations),
                residual_evaluations=tuple(residuals),
                domain_boundary_checks=tuple(domain_checks),
                certificate_hash=cert_hash,
                details=details,
            )

        # -------------------------------------------------------------------
        # Case 2: Candidate is EmptyRealSolutionEntity
        # -------------------------------------------------------------------
        elif isinstance(cand_entity, EmptyRealSolutionEntity):
            if cleared_num.is_zero:
                obligations = [
                    ProofObligationResult(
                        obligation_id="CONTRADICTION_OR_NO_ROOTS",
                        description="Equation has no real solutions on domain",
                        passed=False,
                        details="Cleared numerator is identically zero (identity, not empty set)",
                    ),
                ]
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    proof_obligations=tuple(obligations),
                    certificate_hash=hashlib.sha256(f"empty_claim_identity_{ir.problem_id}".encode("utf-8")).hexdigest(),
                    details="False empty set claim: equation is an identity on its domain",
                )

            num_root_count = distinct_real_root_count(cleared_num)
            g_poly = cleared_num.gcd_poly(domain_poly)
            g_root_count = distinct_real_root_count(g_poly)
            expected_valid_count = num_root_count - g_root_count

            is_truly_empty = (expected_valid_count == 0)
            obligations = [
                ProofObligationResult(
                    obligation_id="CONTRADICTION_OR_NO_ROOTS",
                    description="Equation has no real solutions on domain",
                    passed=is_truly_empty,
                    details="Cleared equation has no valid roots on domain" if is_truly_empty else f"Equation has {expected_valid_count} valid roots",
                ),
            ]

            if is_truly_empty:
                level = VerificationLevel.EXACT_VERIFIED
                disp = VerificationDisposition.ACCEPTED
                details = "Verified no real solutions on original domain"
            else:
                level = VerificationLevel.UNSUPPORTED
                disp = VerificationDisposition.REJECTED
                details = "False empty set claim: equation has valid roots"

            cert_payload = {
                "problem_id": ir.problem_id,
                "verifier": "MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                "level": level.value,
                "disposition": disp.value,
                "outcome": "EMPTY_SET",
            }
            cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()

            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=level,
                disposition=disp,
                proof_obligations=tuple(obligations),
                certificate_hash=cert_hash,
                details=details,
            )

        # -------------------------------------------------------------------
        # Case 3: Candidate is AllRealsExceptFiniteEntity
        # -------------------------------------------------------------------
        elif isinstance(cand_entity, AllRealsExceptFiniteEntity):
            if not cleared_num.is_zero:
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    certificate_hash=hashlib.sha256(f"false_identity_{ir.problem_id}".encode("utf-8")).hexdigest(),
                    details="False identity claim: cleared numerator is not identically zero",
                )

            cand_exclusions = deduplicate_roots(cand_entity.excluded_points)

            # Each candidate exclusion must actually invalidate the original domain
            all_exclusions_valid = True
            for idx, e in enumerate(cand_exclusions):
                if isinstance(e, RationalScalarEntity):
                    pt = NumberFieldElement.from_rational(e.to_rational)
                elif isinstance(e, RealQuadraticSurdEntity):
                    try:
                        pt = NumberFieldElement.from_surd_entity(e)
                    except Exception:
                        all_exclusions_valid = False
                        break
                else:
                    all_exclusions_valid = False
                    break

                invalidates_domain = False
                try:
                    dp_val = eval_poly_at_point(domain_poly, pt)
                    if dp_val.is_zero:
                        invalidates_domain = True

                    if not invalidates_domain:
                        for g_node in guard_nodes:
                            g_val = eval_ast_at_point(g_node, pt, target_var)
                            if g_val.is_zero:
                                invalidates_domain = True
                                break

                    if not invalidates_domain:
                        _ = eval_ast_at_point(ir.payload.left, pt, target_var)
                        _ = eval_ast_at_point(ir.payload.right, pt, target_var)
                except ZeroDivisionError:
                    invalidates_domain = True
                except Exception:
                    pass

                if not invalidates_domain:
                    all_exclusions_valid = False
                    break

            if not all_exclusions_valid:
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    certificate_hash=hashlib.sha256(f"invalid_exclusion_{ir.problem_id}".encode("utf-8")).hexdigest(),
                    details="Candidate excluded point does not invalidate the original domain",
                )

            # Independently certify candidate excluded points exactly cover all real zeros of domain constraints
            expected_exclusion_count = distinct_real_root_count(domain_poly)
            exclusions_exact_match = (len(cand_exclusions) == expected_exclusion_count)

            obligations = [
                ProofObligationResult(
                    obligation_id="IDENTITY_ON_DOMAIN",
                    description="Cleared numerator is identically zero",
                    passed=True,
                ),
                ProofObligationResult(
                    obligation_id="DOMAIN_EXCLUSIONS_MATCH",
                    description="All domain exclusions are accurately and completely identified",
                    passed=exclusions_exact_match,
                    details=f"Candidate exclusions: {len(cand_exclusions)}, expected: {expected_exclusion_count}",
                ),
            ]

            if exclusions_exact_match:
                level = VerificationLevel.EXACT_VERIFIED
                disp = VerificationDisposition.ACCEPTED
                details = "Verified identity on domain with exact finite exclusions"
            else:
                level = VerificationLevel.UNSUPPORTED
                disp = VerificationDisposition.REJECTED
                details = "Domain exclusions mismatch: missing or extra excluded points"

            cert_payload = {
                "problem_id": ir.problem_id,
                "verifier": "MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                "level": level.value,
                "disposition": disp.value,
                "exclusions": [e.model_dump() for e in cand_exclusions],
            }
            cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()

            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=level,
                disposition=disp,
                proof_obligations=tuple(obligations),
                certificate_hash=cert_hash,
                details=details,
            )

        # -------------------------------------------------------------------
        # Case 4: Candidate is AllRealSolutionEntity
        # -------------------------------------------------------------------
        elif isinstance(cand_entity, AllRealSolutionEntity):
            if not cleared_num.is_zero:
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    certificate_hash=hashlib.sha256(f"false_all_real_not_id_{ir.problem_id}".encode("utf-8")).hexdigest(),
                    details="False identity claim: cleared numerator is not identically zero",
                )

            exclusion_count = distinct_real_root_count(domain_poly)
            if exclusion_count == 0:
                level = VerificationLevel.EXACT_VERIFIED
                disp = VerificationDisposition.ACCEPTED
                details = "Verified identity on all of R with zero domain exclusions"
                passed = True
            else:
                level = VerificationLevel.UNSUPPORTED
                disp = VerificationDisposition.REJECTED
                details = f"Domain violation: equation has {exclusion_count} real excluded points"
                passed = False

            obligations = [
                ProofObligationResult(
                    obligation_id="UNRESTRICTED_DOMAIN_VALID",
                    description="Original domain has zero real excluded points",
                    passed=passed,
                    details=details,
                ),
            ]
            cert_hash = hashlib.sha256(f"all_real_{ir.problem_id}_{level.value}".encode("utf-8")).hexdigest()
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=level,
                disposition=disp,
                proof_obligations=tuple(obligations),
                certificate_hash=cert_hash,
                details=details,
            )

        else:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_RATIONAL_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.REJECTED,
                certificate_hash=hashlib.sha256(f"unhandled_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Unhandled candidate entity kind: {type(cand_entity).__name__}",
            )


    def build_trace(
        self,
        ir: ProblemIR,
        candidate: CandidateSolution,
        verification: VerificationReport,
        selected_method_id: Optional[str] = None,
    ) -> SolutionTrace:
        """Construct structured step-by-step pedagogical solution trace."""
        try:
            diff_frac, exclusions, true_roots = self._analyze_equation(ir)
            num = diff_frac.num
            target_var = ir.payload.target_variable if isinstance(ir.payload, SingleEquationPayload) else "x"
        except Exception as exc:
            # Fall back trace for out of scope
            return SolutionTrace(
                trace_id=f"trace_{ir.problem_id}",
                method_id="DOMAIN_THEN_CLEAR_DENOMINATORS",
                method_name_vi="Tìm điều kiện xác định và quy đồng khử mẫu",
                method_name_en="Find domain conditions and clear denominators",
                steps=(
                    TraceStep(
                        step_id="step_1",
                        sequence_index=1,
                        operation_kind="ERROR",
                        title_vi="Không thuộc phạm vi giải tích hợp lệ",
                        title_en="Outside proof envelope",
                        explanation_vi=f"Phương trình không thể giải trong phạm vi bậc hai: {exc}",
                        explanation_en=f"Equation outside proof envelope: {exc}",
                    ),
                ),
                conclusion_vi="Không thể giải trong phạm vi hỗ trợ.",
                conclusion_en="",
                certificate_hash=verification.certificate_hash,
            )

        # 1. Điều kiện xác định
        if exclusions:
            conds_latex = ", ".join(f"{target_var} \\ne {r.latex}" for r in exclusions)
            conds_vi = f"Điều kiện để các mẫu thức và cơ số lũy thừa bậc 0 khác 0: {', '.join(f'{target_var} ≠ {r.latex}' for r in exclusions)}."
        else:
            conds_latex = f"{target_var} \\in \\mathbb{{R}}"
            conds_vi = "Phương trình xác định với mọi số thực x."

        step1 = TraceStep(
            step_id="step_1",
            sequence_index=1,
            operation_kind="DOMAIN_CONDITIONS",
            title_vi="Tìm điều kiện xác định (ĐKXĐ)",
            title_en="Find domain conditions",
            explanation_vi=f"Điều kiện xác định của phương trình: {conds_vi}",
            explanation_en=f"Domain conditions for the equation: {conds_latex}",
            output_expression_latex=conds_latex,
        )

        # 2. Quy đồng và khử mẫu
        cleared_eq_latex = f"{num.to_latex(target_var)} = 0"
        step2 = TraceStep(
            step_id="step_2",
            sequence_index=2,
            operation_kind="CLEAR_DENOMINATORS",
            title_vi="Quy đồng và khử mẫu",
            title_en="Clear denominators",
            explanation_vi="Với điều kiện xác định trên, quy đồng mẫu số và khử mẫu hai vế của phương trình:",
            explanation_en="Under the domain conditions, multiply by the common denominator to obtain the polynomial equation:",
            output_expression_latex=cleared_eq_latex,
        )

        # 3. Giải phương trình đại số thu gọn
        if num.is_zero:
            step3_expl = "Phương trình 0 = 0 nghiệm đúng với mọi số thực."
            step3_latex = "0 = 0"
        elif num.degree == 0:
            step3_expl = f"Phương trình {num.to_latex(target_var)} = 0 vô nghiệm do hằng số khác 0."
            step3_latex = "\\text{Vô nghiệm}"
        else:
            _, raw_num_roots = solve_poly_degree_le_2(num)
            roots_str = " hoặc ".join(f"{target_var} = {r.latex}" for r in raw_num_roots)
            step3_expl = f"Giải phương trình thu gọn ta được các nghiệm: {roots_str}."
            step3_latex = ", ".join(f"{target_var} = {r.latex}" for r in raw_num_roots)

        step3 = TraceStep(
            step_id="step_3",
            sequence_index=3,
            operation_kind="SOLVE_NUMERATOR",
            title_vi="Giải phương trình thu gọn",
            title_en="Solve cleared equation",
            explanation_vi=step3_expl,
            explanation_en="",
            output_expression_latex=step3_latex,
        )

        # 4. Đối chiếu điều kiện xác định
        if num.is_zero:
            if exclusions:
                step4_expl = f"Đối chiếu ĐKXĐ: Nghiệm đúng với mọi x ngoại trừ: {', '.join(f'x = {e.latex}' for e in exclusions)}."
                step4_latex = conds_latex
            else:
                step4_expl = "Phương trình xác định và nghiệm đúng với mọi số thực x."
                step4_latex = "S = \\mathbb{R}"
        elif num.degree == 0:
            step4_expl = "Phương trình vô nghiệm nên không có nghiệm nào thỏa mãn ĐKXĐ."
            step4_latex = "S = \\emptyset"
        else:
            _, raw_num_roots = solve_poly_degree_le_2(num)
            filter_details: List[str] = []
            for r in raw_num_roots:
                if is_root_in_collection(r, exclusions):
                    filter_details.append(f"{target_var} = {r.latex} (loại vì vi phạm ĐKXĐ)")
                else:
                    filter_details.append(f"{target_var} = {r.latex} (nhận thỏa mãn ĐKXĐ)")
            step4_expl = "Đối chiếu các nghiệm tìm được với điều kiện xác định:\n" + "\n".join(f"- {d}" for d in filter_details)
            step4_latex = f"S = \\{{{', '.join(r.latex for r in true_roots)}\\}}" if true_roots else "S = \\emptyset"

        step4 = TraceStep(
            step_id="step_4",
            sequence_index=4,
            operation_kind="FILTER_EXCLUSIONS",
            title_vi="Đối chiếu điều kiện xác định",
            title_en="Filter with domain conditions",
            explanation_vi=step4_expl,
            explanation_en="",
            output_expression_latex=step4_latex,
        )

        # 5. Kết luận tập nghiệm
        if num.is_zero:
            if exclusions:
                conclusion_vi = f"Vậy tập nghiệm của phương trình là: S = ℝ \\ {{{', '.join(e.latex for e in exclusions)}}}."
                conclusion_latex = f"S = \\mathbb{{R}} \\setminus \\{{{', '.join(e.latex for e in exclusions)}\\}}"
            else:
                conclusion_vi = "Vậy tập nghiệm của phương trình là: S = ℝ."
                conclusion_latex = "S = \\mathbb{R}"
        elif not true_roots:
            conclusion_vi = "Vậy phương trình vô nghiệm: S = ∅."
            conclusion_latex = "S = \\emptyset"
        else:
            conclusion_vi = f"Vậy tập nghiệm của phương trình là: S = {{{', '.join(r.latex for r in true_roots)}}}."
            conclusion_latex = f"S = \\{{{', '.join(r.latex for r in true_roots)}\\}}"

        step5 = TraceStep(
            step_id="step_5",
            sequence_index=5,
            operation_kind="VERIFIED_CONCLUSION",
            title_vi="Kết luận tập nghiệm",
            title_en="Conclusion",
            explanation_vi=conclusion_vi,
            explanation_en="",
            output_expression_latex=conclusion_latex,
        )

        return SolutionTrace(
            trace_id=f"trace_{ir.problem_id}",
            method_id="DOMAIN_THEN_CLEAR_DENOMINATORS",
            method_name_vi="Tìm điều kiện xác định và quy đồng khử mẫu",
            method_name_en="Find domain conditions and clear denominators",
            steps=(step1, step2, step3, step4, step5),
            conclusion_vi=conclusion_vi,
            conclusion_en="",
            certificate_hash=verification.certificate_hash,
        )

    def supported_methods(self, ir: ProblemIR) -> Tuple[CoverageMethodAssessment, ...]:
        """List available pedagogical methods for this problem."""
        return self.classify(ir).applicable_methods

    def limitations(self) -> Tuple[str, ...]:
        return (
            "Supports univariate rational equations in single target variable where cleared numerator, denominators, and exponent-zero bases have degree <= 2 over Q.",
            "Radical, trigonometric, exponential, and logarithmic expressions are not supported.",
            "Equations whose cleared numerator degree exceeds 2 are out of scope for Pack 1-A.",
            "Strictly preserves all domain exclusions and rejects extraneous roots.",
        )
