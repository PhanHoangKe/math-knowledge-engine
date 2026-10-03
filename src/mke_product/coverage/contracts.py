"""MKE THPT Universal Coverage Engine — Core Universal Contracts.

Defines typed, deeply immutable models for:
- ProblemKind and common mathematical enums
- Domain specifications and typed assumptions
- ProblemPayload discriminated union
- Universal ProblemIR
- CandidateSolution and untrusted CAS metadata
- VerificationLevel, VerificationDisposition, and VerificationReport
- SolutionTrace and TraceStep
- Strict truth-table invariant validation and fail-closed security.
"""

from __future__ import annotations

import hashlib
import json
import math
from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence, Set, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mke_product.core.rational import Rational
from mke_product.domain.models import RationalFraction
from mke_product.parser.ast import ASTNode


# ---------------------------------------------------------------------------
# Common Enums
# ---------------------------------------------------------------------------

class ProblemKind(str, Enum):
    """Authoritative mathematical problem family taxonomy for Vietnamese THPT."""
    # Algebra
    ALGEBRA_EQUATION = "ALGEBRA_EQUATION"
    ALGEBRA_INEQUALITY = "ALGEBRA_INEQUALITY"
    ALGEBRA_SYSTEM = "ALGEBRA_SYSTEM"

    # Transcendental
    EXPONENTIAL_EQUATION = "EXPONENTIAL_EQUATION"
    EXPONENTIAL_INEQUALITY = "EXPONENTIAL_INEQUALITY"
    LOGARITHMIC_EQUATION = "LOGARITHMIC_EQUATION"
    LOGARITHMIC_INEQUALITY = "LOGARITHMIC_INEQUALITY"
    TRIGONOMETRIC_EQUATION = "TRIGONOMETRIC_EQUATION"
    TRIGONOMETRIC_INEQUALITY = "TRIGONOMETRIC_INEQUALITY"

    # Calculus & Analysis
    FUNCTION_ANALYSIS = "FUNCTION_ANALYSIS"
    DERIVATIVE = "DERIVATIVE"
    LIMIT = "LIMIT"
    ANTIDERIVATIVE = "ANTIDERIVATIVE"
    DEFINITE_INTEGRAL = "DEFINITE_INTEGRAL"
    OPTIMIZATION = "OPTIMIZATION"

    # Linear Algebra & Vectors
    COMPLEX_NUMBER = "COMPLEX_NUMBER"
    MATRIX = "MATRIX"
    VECTOR = "VECTOR"

    # Coordinate Geometry
    COORDINATE_GEOMETRY_2D = "COORDINATE_GEOMETRY_2D"
    COORDINATE_GEOMETRY_3D = "COORDINATE_GEOMETRY_3D"

    # Discrete Math & Statistics
    COMBINATORICS = "COMBINATORICS"
    PROBABILITY = "PROBABILITY"
    STATISTICS = "STATISTICS"

    # Higher-Order & Text
    WORD_PROBLEM = "WORD_PROBLEM"
    GEOMETRY_TEXT = "GEOMETRY_TEXT"
    UNKNOWN = "UNKNOWN"


class SourceInputKind(str, Enum):
    """Origin format of the input."""
    RAW_TEXT = "RAW_TEXT"
    LATEX = "LATEX"
    AST = "AST"
    AI_EXTRACTED = "AI_EXTRACTED"
    STRUCTURED_IR = "STRUCTURED_IR"


class ProblemTarget(str, Enum):
    """Objective of the problem."""
    SOLVE = "SOLVE"
    SIMPLIFY = "SIMPLIFY"
    PROVE = "PROVE"
    COMPUTE_EXTREMA = "COMPUTE_EXTREMA"
    EVALUATE = "EVALUATE"


class DomainCategory(str, Enum):
    """Mathematical domain / number field."""
    REALS = "REALS"
    COMPLEXES = "COMPLEXES"
    RATIONALS = "RATIONALS"
    INTEGERS = "INTEGERS"
    POSITIVE_REALS = "POSITIVE_REALS"


class ConstraintRelation(str, Enum):
    """Relation operator for mathematical assumptions/constraints."""
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    LE = "LE"
    GT = "GT"
    GE = "GE"
    IN_SET = "IN_SET"
    NOT_IN_SET = "NOT_IN_SET"


class CalculusOpKind(str, Enum):
    """Calculus operation kind."""
    DERIVATIVE = "DERIVATIVE"
    LIMIT = "LIMIT"
    ANTIDERIVATIVE = "ANTIDERIVATIVE"
    DEFINITE_INTEGRAL = "DEFINITE_INTEGRAL"


class MatrixOpKind(str, Enum):
    """Matrix operation kind."""
    INVERSE = "INVERSE"
    DETERMINANT = "DETERMINANT"
    RANK = "RANK"
    TRANSPOSE = "TRANSPOSE"


class GeometricElementKind(str, Enum):
    """Coordinate geometry element kind."""
    POINT = "POINT"
    LINE = "LINE"
    PLANE = "PLANE"
    CIRCLE = "CIRCLE"
    SPHERE = "SPHERE"
    CONIC = "CONIC"


class VerificationLevel(str, Enum):
    """Exact 5-tier verification level taxonomy."""
    EXACT_VERIFIED = "EXACT_VERIFIED"
    SYMBOLIC_VERIFIED = "SYMBOLIC_VERIFIED"
    CROSS_CHECKED = "CROSS_CHECKED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


class VerificationDisposition(str, Enum):
    """Explicit verification disposition."""
    ACCEPTED = "ACCEPTED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    UNSUPPORTED = "UNSUPPORTED"


# ---------------------------------------------------------------------------
# Typed Assumption and Domain Specifications
# ---------------------------------------------------------------------------

class DomainSpecification(BaseModel):
    """Mathematical domain constraints."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    primary_domain: DomainCategory = DomainCategory.REALS
    custom_restrictions: Tuple[str, ...] = Field(default_factory=tuple)


class AssumptionSpec(BaseModel):
    """Deeply immutable typed mathematical assumption/constraint."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    variable: str = Field(..., min_length=1, description="Target variable or parameter identifier")
    relation: ConstraintRelation = Field(..., description="Constraint relation operator")
    bound_expression: Optional[ASTNode] = Field(default=None, description="Bound expression AST")
    target_domain: Optional[DomainCategory] = Field(default=None, description="Target set")
    description_vi: str = Field(default="", description="Display-only Vietnamese description")


class IntervalSpec(BaseModel):
    """Typed real interval specification."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    lower_bound: Optional[ASTNode] = None
    upper_bound: Optional[ASTNode] = None
    lower_closed: bool = False
    upper_closed: bool = False


class GeometricElementSpec(BaseModel):
    """Typed geometric element in Oxy or Oxyz."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    element_id: str
    kind: GeometricElementKind
    coordinates_or_equation: Tuple[ASTNode, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Discriminated Problem Payloads
# ---------------------------------------------------------------------------

class PayloadKind(str, Enum):
    """Discriminator enum for problem payloads."""
    SINGLE_EQUATION = "SINGLE_EQUATION"
    SYSTEM_OF_EQUATIONS = "SYSTEM_OF_EQUATIONS"
    SINGLE_INEQUALITY = "SINGLE_INEQUALITY"
    FUNCTION_ANALYSIS = "FUNCTION_ANALYSIS"
    CALCULUS_OPERATION = "CALCULUS_OPERATION"
    MATRIX_OPERATION = "MATRIX_OPERATION"
    GEOMETRY_COORDINATE = "GEOMETRY_COORDINATE"


class SingleEquationPayload(BaseModel):
    """Payload for a single algebraic or transcendental equation."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.SINGLE_EQUATION] = PayloadKind.SINGLE_EQUATION
    left: ASTNode
    right: ASTNode
    target_variable: str = "x"


class SystemOfEquationsPayload(BaseModel):
    """Payload for a system of equations."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.SYSTEM_OF_EQUATIONS] = PayloadKind.SYSTEM_OF_EQUATIONS
    equations: Tuple[Tuple[ASTNode, ASTNode], ...] = Field(..., description="Tuple of (left, right) equation pairs")
    target_variables: Tuple[str, ...] = Field(..., min_length=1)


class SingleInequalityPayload(BaseModel):
    """Payload for a single inequality."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.SINGLE_INEQUALITY] = PayloadKind.SINGLE_INEQUALITY
    left: ASTNode
    right: ASTNode
    relation: ConstraintRelation
    target_variable: str = "x"


class FunctionAnalysisPayload(BaseModel):
    """Payload for function analysis (domain, monotonicity, extrema, asymptotes)."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.FUNCTION_ANALYSIS] = PayloadKind.FUNCTION_ANALYSIS
    expression: ASTNode
    variable: str = "x"
    target_interval: Optional[IntervalSpec] = None


class CalculusOperationPayload(BaseModel):
    """Payload for calculus operations (derivative, limit, integral)."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.CALCULUS_OPERATION] = PayloadKind.CALCULUS_OPERATION
    expression: ASTNode
    operation: CalculusOpKind
    variable: str = "x"
    point_or_lower_bound: Optional[ASTNode] = None
    upper_bound: Optional[ASTNode] = None


class MatrixOperationPayload(BaseModel):
    """Payload for matrix operations."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.MATRIX_OPERATION] = PayloadKind.MATRIX_OPERATION
    matrix_elements: Tuple[Tuple[ASTNode, ...], ...]
    operation: MatrixOpKind


class GeometryCoordinatePayload(BaseModel):
    """Payload for 2D/3D coordinate geometry problems."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    payload_kind: Literal[PayloadKind.GEOMETRY_COORDINATE] = PayloadKind.GEOMETRY_COORDINATE
    dimension: int = Field(..., ge=2, le=3)
    elements: Tuple[GeometricElementSpec, ...] = Field(default_factory=tuple)
    query_target: str = ""


ProblemPayload = Annotated[
    Union[
        SingleEquationPayload,
        SystemOfEquationsPayload,
        SingleInequalityPayload,
        FunctionAnalysisPayload,
        CalculusOperationPayload,
        MatrixOperationPayload,
        GeometryCoordinatePayload,
    ],
    Field(discriminator="payload_kind"),
]


# ---------------------------------------------------------------------------
# ProblemKind -> PayloadKind Authoritative Mapping
# ---------------------------------------------------------------------------

PROBLEM_KIND_TO_PAYLOAD_KIND: Dict[ProblemKind, PayloadKind] = {
    ProblemKind.ALGEBRA_EQUATION: PayloadKind.SINGLE_EQUATION,
    ProblemKind.EXPONENTIAL_EQUATION: PayloadKind.SINGLE_EQUATION,
    ProblemKind.LOGARITHMIC_EQUATION: PayloadKind.SINGLE_EQUATION,
    ProblemKind.TRIGONOMETRIC_EQUATION: PayloadKind.SINGLE_EQUATION,

    ProblemKind.ALGEBRA_INEQUALITY: PayloadKind.SINGLE_INEQUALITY,
    ProblemKind.EXPONENTIAL_INEQUALITY: PayloadKind.SINGLE_INEQUALITY,
    ProblemKind.LOGARITHMIC_INEQUALITY: PayloadKind.SINGLE_INEQUALITY,
    ProblemKind.TRIGONOMETRIC_INEQUALITY: PayloadKind.SINGLE_INEQUALITY,

    ProblemKind.ALGEBRA_SYSTEM: PayloadKind.SYSTEM_OF_EQUATIONS,

    ProblemKind.FUNCTION_ANALYSIS: PayloadKind.FUNCTION_ANALYSIS,

    ProblemKind.DERIVATIVE: PayloadKind.CALCULUS_OPERATION,
    ProblemKind.LIMIT: PayloadKind.CALCULUS_OPERATION,
    ProblemKind.ANTIDERIVATIVE: PayloadKind.CALCULUS_OPERATION,
    ProblemKind.DEFINITE_INTEGRAL: PayloadKind.CALCULUS_OPERATION,

    ProblemKind.MATRIX: PayloadKind.MATRIX_OPERATION,

    ProblemKind.COORDINATE_GEOMETRY_2D: PayloadKind.GEOMETRY_COORDINATE,
    ProblemKind.COORDINATE_GEOMETRY_3D: PayloadKind.GEOMETRY_COORDINATE,
}


class ProblemProvenance(BaseModel):
    """Typed deeply immutable provenance metadata."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_name: str = ""
    source_reference: str = ""
    license_or_rights: str = ""
    citation_text: str = ""
    tags: Tuple[Tuple[str, str], ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Universal ProblemIR Model
# ---------------------------------------------------------------------------

class ProblemIR(BaseModel):
    """Authoritative Universal Mathematical Problem Intermediate Representation."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    problem_id: str = Field(..., min_length=1, description="Unique deterministic identifier")
    ir_version: str = Field(default="mke.problem_ir.v1", description="Schema version")
    problem_kind: ProblemKind = Field(..., description="Discriminated mathematical problem family")
    source_input_kind: SourceInputKind = Field(default=SourceInputKind.STRUCTURED_IR)
    target: ProblemTarget = Field(default=ProblemTarget.SOLVE)
    variables: Tuple[str, ...] = Field(default_factory=tuple)
    parameters: Tuple[str, ...] = Field(default_factory=tuple)
    domain_spec: DomainSpecification = Field(default_factory=DomainSpecification)
    assumptions: Tuple[AssumptionSpec, ...] = Field(default_factory=tuple)
    payload: ProblemPayload = Field(..., description="Discriminated mathematical payload")
    ast_payload: Optional[ASTNode] = Field(default=None, description="Optional root AST node")
    raw_source_text: str = Field(default="", description="Provenance/display only. NEVER parsed by math authority.")
    provenance: Optional[ProblemProvenance] = None  # Typed immutable provenance metadata
    normalization_trace: Tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_payload_consistency(self) -> ProblemIR:
        expected_payload_kind = PROBLEM_KIND_TO_PAYLOAD_KIND.get(self.problem_kind)
        if expected_payload_kind is None:
            raise ValueError(
                f"ProblemKind {self.problem_kind.value!r} has no supported payload contract in P1. Fail-closed."
            )
        if self.payload.payload_kind != expected_payload_kind:
            raise ValueError(
                f"Payload mismatch: ProblemKind {self.problem_kind.value!r} requires payload_kind "
                f"{expected_payload_kind.value!r}, but got {self.payload.payload_kind.value!r}."
            )
        return self


# ---------------------------------------------------------------------------
# Symbolic Entity Contracts
# ---------------------------------------------------------------------------

class RationalScalarEntity(BaseModel):
    """Exact rational root or scalar value."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["RATIONAL_SCALAR"] = "RATIONAL_SCALAR"
    numerator: int
    denominator: int = Field(..., gt=0)
    latex: str = ""

    @property
    def to_rational(self) -> Rational:
        return Rational(self.numerator, self.denominator)

    @classmethod
    def from_rational(cls, r: Rational, latex: str = "") -> RationalScalarEntity:
        return cls(numerator=r.numerator, denominator=r.denominator, latex=latex or str(r))


class RealQuadraticSurdEntity(BaseModel):
    """Exact quadratic surd root: (p + q*sqrt(d))/r."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["REAL_QUADRATIC_SURD"] = "REAL_QUADRATIC_SURD"
    p: int
    q: int
    d: int = Field(..., gt=0)
    r: int = Field(..., gt=0)
    latex: str = ""


class FiniteRootCollectionEntity(BaseModel):
    """Finite set of verified or candidate roots."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["FINITE_ROOT_COLLECTION"] = "FINITE_ROOT_COLLECTION"
    roots: Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...] = Field(default_factory=tuple)
    cardinality: int = 0

    @model_validator(mode="after")
    def sync_cardinality(self) -> FiniteRootCollectionEntity:
        object.__setattr__(self, "cardinality", len(self.roots))
        return self


class EmptyRealSolutionEntity(BaseModel):
    """Represents no real solutions (empty solution set)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["EMPTY_REAL_SOLUTION"] = "EMPTY_REAL_SOLUTION"
    explanation: str = "Phương trình vô nghiệm trên ℝ"


class AllRealSolutionEntity(BaseModel):
    """Represents identity / all real numbers as solutions."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["ALL_REAL_SOLUTION"] = "ALL_REAL_SOLUTION"
    explanation: str = "Phương trình nghiệm đúng với mọi x ∈ ℝ"


class AllRealsExceptFiniteEntity(BaseModel):
    """Represents identity with finite excluded points, e.g. ℝ \\ {x_1, x_2, ...}."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["ALL_REALS_EXCEPT_FINITE"] = "ALL_REALS_EXCEPT_FINITE"
    excluded_points: Tuple[Union[RationalScalarEntity, RealQuadraticSurdEntity], ...] = Field(default_factory=tuple)
    explanation: str = "Phương trình nghiệm đúng với mọi x ∈ ℝ loại trừ các điểm gián đoạn"

    @property
    def cardinality_excluded(self) -> int:
        return len(self.excluded_points)



def _decompose_int_squarefree(n: int) -> Tuple[int, int]:
    """Decompose non-negative integer n into k^2 * d where d is squarefree."""
    if n <= 0:
        return 0, 0
    k = 1
    d = n
    p = 2
    while p * p <= d:
        while d % (p * p) == 0:
            k *= p
            d //= (p * p)
        p += 1
    return k, d


def _to_u_v_d(
    ent: Union[RationalScalarEntity, RealQuadraticSurdEntity]
) -> Tuple[Rational, Rational, int]:
    """Convert rational or surd entity to canonical (u, v, d) where d is squarefree."""
    if isinstance(ent, RationalScalarEntity):
        return ent.to_rational, Rational(0, 1), 1
    if isinstance(ent, RealQuadraticSurdEntity):
        if ent.r <= 0 or ent.d <= 0:
            raise ValueError(f"Invalid surd parameters: r={ent.r}, d={ent.d}")
        u = Rational(ent.p, ent.r)
        if ent.q == 0:
            return u, Rational(0, 1), 1
        v = Rational(ent.q, ent.r)
        if v.is_zero:
            return u, Rational(0, 1), 1
        s = math.isqrt(ent.d)
        if s * s == ent.d:
            return u + v * Rational(s, 1), Rational(0, 1), 1
        k, d_sqf = _decompose_int_squarefree(ent.d)
        if d_sqf == 1:
            return u + v * Rational(k, 1), Rational(0, 1), 1
        return u, v * Rational(k, 1), d_sqf
    raise TypeError(f"Unsupported algebraic entity: {type(ent).__name__}")


def _compare_u_v_d(
    u1: Rational, v1: Rational, d1: int,
    u2: Rational, v2: Rational, d2: int,
) -> int:
    """Exact comparison of u1 + v1*sqrt(d1) and u2 + v2*sqrt(d2) with zero float.
    
    Returns -1 if val1 < val2, 0 if val1 == val2, 1 if val1 > val2.
    """
    if v1.is_zero and v2.is_zero:
        if u1 < u2:
            return -1
        elif u1 > u2:
            return 1
        return 0

    if v1.is_zero and not v2.is_zero:
        w = u1 - u2
        if v2.is_positive:
            if not w.is_positive:
                return -1
            w_sq = w * w
            surd_sq = v2 * v2 * Rational(d2, 1)
            if w_sq < surd_sq:
                return -1
            elif w_sq > surd_sq:
                return 1
            return 0
        else:
            if not w.is_negative:
                return 1
            w_sq = w * w
            surd_sq = v2 * v2 * Rational(d2, 1)
            if w_sq > surd_sq:
                return -1
            elif w_sq < surd_sq:
                return 1
            return 0

    if not v1.is_zero and v2.is_zero:
        return -_compare_u_v_d(u2, v2, d2, u1, v1, d1)

    if d1 == d2:
        w = u1 - u2
        v = v1 - v2
        if v.is_zero:
            if w < Rational(0, 1):
                return -1
            elif w > Rational(0, 1):
                return 1
            return 0
        return _compare_u_v_d(w, Rational(0, 1), 1, Rational(0, 1), -v, d1)

    # d1 != d2 (both > 1, squarefree)
    u = u1 - u2
    if v1.is_positive and v2.is_negative:
        if not u.is_negative:
            return 1
        pos_v2 = -v2
        base_s2 = v1 * v1 * Rational(d1, 1) + pos_v2 * pos_v2 * Rational(d2, 1)
        cross_coeff = Rational(2, 1) * v1 * pos_v2
        rem = u * u - base_s2
        k_cross, d_cross = _decompose_int_squarefree(d1 * d2)
        eff_cross = cross_coeff * Rational(k_cross, 1)
        cmp_res = _compare_u_v_d(rem, Rational(0, 1), 1, Rational(0, 1), eff_cross, d_cross)
        if cmp_res < 0:
            return 1
        elif cmp_res > 0:
            return -1
        return 0

    if v1.is_negative and v2.is_positive:
        return -_compare_u_v_d(u2, v2, d2, u1, v1, d1)

    if v1.is_positive and v2.is_positive:
        lhs_sign = _compare_u_v_d(u, v1, d1, Rational(0, 1), Rational(0, 1), 1)
        if lhs_sign <= 0:
            return -1
        lhs_base = u * u + v1 * v1 * Rational(d1, 1)
        lhs_cross = Rational(2, 1) * u * v1
        rhs_val = v2 * v2 * Rational(d2, 1)
        return _compare_u_v_d(lhs_base, lhs_cross, d1, rhs_val, Rational(0, 1), 1)

    # Both negative: v1 < 0, v2 < 0
    return _compare_u_v_d(-u2, -v2, d2, -u1, -v1, d1)


def _compare_algebraic_entities(
    e1: Union[RationalScalarEntity, RealQuadraticSurdEntity],
    e2: Union[RationalScalarEntity, RealQuadraticSurdEntity],
) -> int:
    """Exact deterministic comparison of two algebraic root/scalar entities."""
    u1, v1, d1 = _to_u_v_d(e1)
    u2, v2, d2 = _to_u_v_d(e2)
    return _compare_u_v_d(u1, v1, d1, u2, v2, d2)


class RealIntervalEntity(BaseModel):
    """Exact real interval [a, b], (a, b), [a, b), (a, b], (-inf, b], [a, +inf), or (-inf, +inf)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["REAL_INTERVAL"] = "REAL_INTERVAL"
    lower_bound: Optional[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = None
    upper_bound: Optional[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = None
    lower_closed: bool = False
    upper_closed: bool = False

    @model_validator(mode="after")
    def validate_endpoints(self) -> RealIntervalEntity:
        if self.lower_bound is None and self.lower_closed:
            raise ValueError("Infinite lower endpoint must be open (lower_closed=False).")
        if self.upper_bound is None and self.upper_closed:
            raise ValueError("Infinite upper endpoint must be open (upper_closed=False).")
        if self.lower_bound is not None and self.upper_bound is not None:
            cmp = _compare_algebraic_entities(self.lower_bound, self.upper_bound)
            if cmp > 0:
                raise ValueError("Interval lower_bound cannot be strictly greater than upper_bound.")
            if cmp == 0:
                if not (self.lower_closed and self.upper_closed):
                    raise ValueError("Degenerate interval [r, r] must be closed on both ends.")
        return self

    def to_latex(self) -> str:
        left_bracket = "[" if self.lower_closed else "("
        right_bracket = "]" if self.upper_closed else ")"
        lb = "-\\infty" if self.lower_bound is None else (self.lower_bound.latex or str(self.lower_bound.to_rational if isinstance(self.lower_bound, RationalScalarEntity) else self.lower_bound))
        ub = "+\\infty" if self.upper_bound is None else (self.upper_bound.latex or str(self.upper_bound.to_rational if isinstance(self.upper_bound, RationalScalarEntity) else self.upper_bound))
        return f"{left_bracket}{lb}; {ub}{right_bracket}"


class RealIntervalUnionEntity(BaseModel):
    """Authoritative immutable real interval union solution set."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    entity_kind: Literal["REAL_INTERVAL_UNION"] = "REAL_INTERVAL_UNION"
    intervals: Tuple[RealIntervalEntity, ...] = Field(default_factory=tuple)

    def to_latex(self) -> str:
        if not self.intervals:
            return "\\emptyset"
        return " \\cup ".join(i.to_latex() for i in self.intervals)


SymbolicEntity = Union[
    RationalScalarEntity,
    RealQuadraticSurdEntity,
    FiniteRootCollectionEntity,
    EmptyRealSolutionEntity,
    AllRealSolutionEntity,
    AllRealsExceptFiniteEntity,
    RealIntervalUnionEntity,
]


# ---------------------------------------------------------------------------
# CandidateSolution & Untrusted Metadata
# ---------------------------------------------------------------------------

class CandidateMetadata(BaseModel):
    """Deeply immutable typed metadata for candidate generation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    engine_version: str = ""
    transformation_steps: Tuple[str, ...] = Field(default_factory=tuple)
    flags: Tuple[Tuple[str, str], ...] = Field(default_factory=tuple)


class CandidateSolution(BaseModel):
    """Untrusted candidate solution generated by CAS or algorithm.
    
    Contains NO truth flags (no is_correct, no trusted=True).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str = Field(..., min_length=1)
    generator_engine: str = Field(..., description="e.g. 'mke.legacy_quadratic', 'sympy.solveset'")
    raw_symbolic_output: str = Field(..., description="DIAGNOSTIC ONLY. Never reparsed as math authority.")
    parsed_entities: Tuple[SymbolicEntity, ...] = Field(..., description="Authoritative structured mathematical entities")
    assumptions_used: Tuple[AssumptionSpec, ...] = Field(default_factory=tuple)
    execution_time_ms: float = Field(default=0.0, ge=0.0)
    metadata: CandidateMetadata = Field(default_factory=CandidateMetadata)


# ---------------------------------------------------------------------------
# Verification Report & Invariants
# ---------------------------------------------------------------------------

class ProofObligationResult(BaseModel):
    """Individual proof obligation verification record."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    obligation_id: str
    description: str
    passed: bool
    details: str = ""


class ResidualCheck(BaseModel):
    """Residual evaluation for a candidate point."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    point_desc: str
    residual_value: str
    is_exact_zero: bool


class DomainCheck(BaseModel):
    """Domain restriction check."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_desc: str
    satisfied: bool


class VerificationReport(BaseModel):
    """Authoritative deterministic verification report."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    verification_id: str = Field(..., min_length=1)
    verifier_name: str = Field(..., description="e.g. 'MKE_HOST_INDEPENDENT_VERIFIER_V1'")
    verification_level: VerificationLevel
    disposition: VerificationDisposition
    proof_obligations: Tuple[ProofObligationResult, ...] = Field(default_factory=tuple)
    identities_checked: Tuple[str, ...] = Field(default_factory=tuple)
    counterexamples: Tuple[str, ...] = Field(default_factory=tuple)
    residual_evaluations: Tuple[ResidualCheck, ...] = Field(default_factory=tuple)
    domain_boundary_checks: Tuple[DomainCheck, ...] = Field(default_factory=tuple)
    certificate_hash: str = Field(..., description="Deterministic unkeyed SHA-256 integrity fingerprint")
    details: str = ""

    @model_validator(mode="after")
    def enforce_truth_table_invariants(self) -> VerificationReport:
        level = self.verification_level
        disp = self.disposition

        # Invariant 1: EXACT_VERIFIED, SYMBOLIC_VERIFIED, CROSS_CHECKED require ACCEPTED
        if level in (VerificationLevel.EXACT_VERIFIED, VerificationLevel.SYMBOLIC_VERIFIED, VerificationLevel.CROSS_CHECKED):
            if disp != VerificationDisposition.ACCEPTED:
                raise ValueError(
                    f"Contradictory state: VerificationLevel {level.value} requires disposition ACCEPTED, got {disp.value}."
                )

        # Invariant 2: PARTIAL requires PARTIAL disposition
        elif level == VerificationLevel.PARTIAL:
            if disp != VerificationDisposition.PARTIAL:
                raise ValueError(
                    f"Contradictory state: VerificationLevel PARTIAL requires disposition PARTIAL, got {disp.value}."
                )

        # Invariant 3: UNSUPPORTED requires UNSUPPORTED or REJECTED
        elif level == VerificationLevel.UNSUPPORTED:
            if disp not in (VerificationDisposition.UNSUPPORTED, VerificationDisposition.REJECTED):
                raise ValueError(
                    f"Contradictory state: VerificationLevel UNSUPPORTED cannot have disposition {disp.value}."
                )

        return self


# ---------------------------------------------------------------------------
# Solution Trace Contracts
# ---------------------------------------------------------------------------

class TraceStep(BaseModel):
    """Step in a pedagogical solution trace."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_id: str
    sequence_index: int = Field(..., ge=0)
    operation_kind: str
    title_vi: str
    title_en: str = ""
    explanation_vi: str
    explanation_en: str = ""
    input_expression_latex: str = ""
    output_expression_latex: str = ""
    formula_refs: Tuple[str, ...] = Field(default_factory=tuple)
    verification_note: str = ""


class SolutionTrace(BaseModel):
    """Complete structured solution trace."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str
    method_id: str
    method_name_vi: str
    method_name_en: str = ""
    steps: Tuple[TraceStep, ...] = Field(default_factory=tuple)
    conclusion_vi: str
    conclusion_en: str = ""
    certificate_hash: str = ""
