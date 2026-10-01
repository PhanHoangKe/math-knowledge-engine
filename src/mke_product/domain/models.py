"""MKE MVP V1 — Domain Models and Typed Contracts.

Defines the Python Single Source of Truth (SSOT) data models for MKE MVP V1.
All models use Pydantic v2 with strict validation and extra field rejection
to ensure mathematical integrity across the knowledge pipeline.
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mke_product.core.rational import Rational


# ============================================================================
# 1. ENUMS & TAXONOMY
# ============================================================================

class ProblemCategory(str, Enum):
    """Supported mathematical problem categories in MKE."""
    ALGEBRA_QUADRATIC = "ALGEBRA_QUADRATIC"
    ALGEBRA_LINEAR_SYSTEM = "ALGEBRA_LINEAR_SYSTEM"
    GEOMETRY_TRIANGLE = "GEOMETRY_TRIANGLE"
    UNSUPPORTED = "UNSUPPORTED"


class EquationClassificationType(str, Enum):
    """Deterministic classification of univariate polynomial equations of degree <= 2."""
    QUADRATIC = "QUADRATIC"              # a != 0
    LINEAR = "LINEAR"                    # a == 0, b != 0
    IDENTITY = "IDENTITY"                # a == 0, b == 0, c == 0 (infinitely many solutions)
    CONTRADICTION = "CONTRADICTION"      # a == 0, b == 0, c != 0 (no solution)


class SolutionOutcome(str, Enum):
    """Mathematical outcome category for equation solving."""
    TWO_DISTINCT_REAL_ROOTS = "TWO_DISTINCT_REAL_ROOTS"
    ONE_REPEATED_REAL_ROOT = "ONE_REPEATED_REAL_ROOT"
    NO_REAL_ROOTS = "NO_REAL_ROOTS"
    ONE_REAL_LINEAR_ROOT = "ONE_REAL_LINEAR_ROOT"
    INFINITE_REAL_SOLUTIONS = "INFINITE_REAL_SOLUTIONS"
    NO_REAL_SOLUTIONS_CONTRADICTION = "NO_REAL_SOLUTIONS_CONTRADICTION"


class SolutionRootType(str, Enum):
    """Representation type of a real root."""
    RATIONAL = "RATIONAL"
    REAL_SURD = "REAL_SURD"
    NO_REAL_ROOT = "NO_REAL_ROOT"


# Orthogonal Method Assessment Enums
class MathematicalApplicability(str, Enum):
    """Whether the method is mathematically sound and valid for this problem instance."""
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class SupportStatus(str, Enum):
    """Whether the method is implemented and supported in the MKE solver engine."""
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class ExecutionAvailability(str, Enum):
    """Whether the solver/worker for this method is currently available to execute."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class PedagogicalRecommendation(str, Enum):
    """Pedagogical recommendation level for Vietnamese secondary learners."""
    RECOMMENDED = "RECOMMENDED"
    NEUTRAL = "NEUTRAL"
    DISCOURAGED = "DISCOURAGED"


class VerificationCapability(str, Enum):
    """Capability of independent verification for this method's trace."""
    HOST_VERIFIABLE = "HOST_VERIFIABLE"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class VerificationOutcome(str, Enum):
    """Result of independent deterministic host verification."""
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# Geometry Enums
class PrimitiveType(str, Enum):
    """Geometric primitive types."""
    POINT = "POINT"
    LINE = "LINE"
    SEGMENT = "SEGMENT"
    TRIANGLE = "TRIANGLE"


class GeometricPredicate(str, Enum):
    """Geometric relationship and theorem predicates."""
    NON_DEGENERATE_TRIANGLE = "NON_DEGENERATE_TRIANGLE"
    EQUAL_LENGTH = "EQUAL_LENGTH"
    EQUAL_ANGLE = "EQUAL_ANGLE"
    PERPENDICULAR = "PERPENDICULAR"
    PARALLEL = "PARALLEL"
    MIDPOINT = "MIDPOINT"
    MEDIAN = "MEDIAN"
    ALTITUDE = "ALTITUDE"
    ANGLE_BISECTOR = "ANGLE_BISECTOR"
    PERPENDICULAR_BISECTOR = "PERPENDICULAR_BISECTOR"
    CONGRUENT_TRIANGLES = "CONGRUENT_TRIANGLES"


class ProofOutcome(str, Enum):
    """Outcome of synthetic geometric deduction."""
    VERIFIED_PROOF = "VERIFIED_PROOF"
    NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM = "NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM"
    REFUTED_BY_COUNTEREXAMPLE = "REFUTED_BY_COUNTEREXAMPLE"
    INVALID_DEGENERATE_INPUT = "INVALID_DEGENERATE_INPUT"


# ============================================================================
# 2. EXACT VALUE OBJECTS & PRIMITIVES
# ============================================================================

class RationalFraction(BaseModel):
    """Canonical serializable representation of an exact rational number p/q."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    numerator: int = Field(..., description="Canonical integer numerator")
    denominator: int = Field(default=1, gt=0, description="Canonical integer denominator > 0")

    @model_validator(mode="before")
    @classmethod
    def _normalize_rational_input(cls, data: Any) -> Any:
        """Deterministic canonicalization before model construction."""
        if isinstance(data, dict):
            num = data.get("numerator")
            den = data.get("denominator", 1)
            if num is not None and den is not None:
                if isinstance(num, bool) or isinstance(den, bool) or not isinstance(num, int) or not isinstance(den, int):
                    return data
                if den == 0:
                    raise ValueError("Denominator cannot be zero in RationalFraction")
                if den < 0:
                    num = -num
                    den = -den
                if num == 0:
                    den = 1
                else:
                    g = math.gcd(abs(num), den)
                    num //= g
                    den //= g
                data = dict(data)
                data["numerator"] = num
                data["denominator"] = den
        return data

    @model_validator(mode="after")
    def _validate_canonical_form(self) -> RationalFraction:
        """Enforce canonical mathematical invariant: denominator > 0, coprime, 0/1."""
        if self.denominator <= 0:
            raise ValueError(f"Canonical denominator must be > 0, got {self.denominator}")
        if self.numerator == 0 and self.denominator != 1:
            raise ValueError(f"Canonical zero fraction must have denominator 1, got {self.denominator}")
        if self.numerator != 0:
            g = math.gcd(abs(self.numerator), self.denominator)
            if g != 1:
                raise ValueError(f"RationalFraction must be coprime, got gcd({self.numerator}, {self.denominator}) = {g}")
        return self

    @classmethod
    def from_rational(cls, r: Rational) -> RationalFraction:
        """Create from a core Rational instance."""
        return cls(numerator=r.numerator, denominator=r.denominator)

    @classmethod
    def from_int(cls, n: int) -> RationalFraction:
        """Create from an integer."""
        return cls(numerator=n, denominator=1)

    @classmethod
    def from_fraction_str(cls, s: str) -> RationalFraction:
        """Parse from string like '3/4' or '-5'."""
        r = Rational(s)
        return cls(numerator=r.numerator, denominator=r.denominator)

    def to_rational(self) -> Rational:
        """Convert to immutable core Rational instance."""
        return Rational(self.numerator, self.denominator)

    def to_latex(self) -> str:
        """Render to clean LaTeX."""
        if self.denominator == 1:
            return str(self.numerator)
        if self.numerator < 0:
            return f"-\\frac{{{abs(self.numerator)}}}{{{self.denominator}}}"
        return f"\\frac{{{self.numerator}}}{{{self.denominator}}}"

    def __str__(self) -> str:
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"


class QuadraticDiscriminant(BaseModel):
    """Exact discriminant data structure with squarefree kernel analysis."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    value: RationalFraction = Field(..., description="Exact rational value of Delta = b^2 - 4ac")
    is_positive: bool = Field(..., description="True if Delta > 0")
    is_zero: bool = Field(..., description="True if Delta == 0")
    is_negative: bool = Field(..., description="True if Delta < 0")
    is_rational_square: bool = Field(..., description="True if Delta is a square in Q")
    square_root_rational: Optional[RationalFraction] = Field(
        None, description="Exact rational sqrt(Delta) when is_rational_square is True"
    )
    squarefree_kernel: Optional[int] = Field(
        None, description="Squarefree integer d >= 1 such that Delta = s^2 * d (d=1 if rational square)"
    )
    extracted_factor: Optional[RationalFraction] = Field(
        None, description="Rational factor s >= 0 such that sqrt(Delta) = s * sqrt(d)"
    )


class RealRootValue(BaseModel):
    """Exact representation of a real root in Q or Q(sqrt(d))."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    root_type: SolutionRootType
    rational_value: Optional[RationalFraction] = None
    surd_base: Optional[RationalFraction] = Field(None, description="Rational base u in u + v*sqrt(d)")
    surd_factor: Optional[RationalFraction] = Field(None, description="Rational coefficient v in u + v*sqrt(d)")
    radicand: Optional[int] = Field(None, description="Squarefree radicand d > 1")
    approximate_float: Optional[float] = Field(None, description="Floating-point approximation for visualization only")
    latex_str: str = Field(..., description="Canonical LaTeX representation of the root")


# ============================================================================
# 3. PROBLEM IR HIERARCHY
# ============================================================================

class Assumption(BaseModel):
    """Mathematical domain assumption."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    symbol: str
    domain: str = Field(default="REAL", description="REAL, POSITIVE_REAL, NON_ZERO")
    description_vi: Optional[str] = None


class ProblemIR(BaseModel):
    """Root polymorphic container for mathematical problems in MKE."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_id: str = Field(..., description="Deterministic unique identifier")
    raw_query: str = Field(..., description="Original input query text or formula")
    category: ProblemCategory = Field(..., description="Classified mathematical category")
    assumptions: List[Assumption] = Field(default_factory=list)
    raw_query_provenance: str = Field(default="USER_TEXT", description="USER_TEXT, OCR, DEMO")
    schema_version: str = Field(default="1.0.0", description="MKE schema contract version")
    semantic_revision_hash: str = Field(..., description="Deterministic SHA-256 over semantic truth fields")


class QuadraticProblemIR(ProblemIR):
    """Authoritative representation of a univariate quadratic equation ax^2 + bx + c = 0 with a != 0."""
    target_variable: str = Field(default="x", min_length=1, max_length=10)
    a: RationalFraction = Field(..., description="Leading coefficient a != 0")
    b: RationalFraction = Field(..., description="Linear coefficient b")
    c: RationalFraction = Field(..., description="Constant term c")
    coefficient_domain: str = Field(default="Q", description="Coefficient ring: Q (Rationals)")
    solution_domain: str = Field(default="R", description="Target solution field: R (Real numbers)")
    equation_string: str = Field(..., description="Normalized equation string e.g. x^2 - 5*x + 6 = 0")
    discriminant: QuadraticDiscriminant
    classification: EquationClassificationType = Field(
        default=EquationClassificationType.QUADRATIC,
        description="Always QUADRATIC for valid QuadraticProblemIR instances"
    )

    @model_validator(mode="after")
    def _validate_quadratic_invariants(self) -> QuadraticProblemIR:
        """Enforce semantic mathematical invariants for QuadraticProblemIR."""
        if self.a.numerator == 0:
            raise ValueError("Leading coefficient 'a' cannot be zero in QuadraticProblemIR (a != 0 is required).")
        if self.category != ProblemCategory.ALGEBRA_QUADRATIC:
            raise ValueError(f"Category for QuadraticProblemIR must be ALGEBRA_QUADRATIC, got '{self.category}'.")
        if self.classification != EquationClassificationType.QUADRATIC:
            raise ValueError(f"Classification for QuadraticProblemIR must be QUADRATIC, got '{self.classification}'.")
        if self.coefficient_domain != "Q":
            raise ValueError(f"Coefficient domain for QuadraticProblemIR must be 'Q', got '{self.coefficient_domain}'.")
        if self.solution_domain != "R":
            raise ValueError(f"Solution domain for QuadraticProblemIR must be 'R', got '{self.solution_domain}'.")

        # Verify exact discriminant consistency with canonical b^2 - 4ac computation
        from mke_product.domain.exact import compute_quadratic_discriminant
        expected_disc = compute_quadratic_discriminant(
            self.a.to_rational(), self.b.to_rational(), self.c.to_rational()
        )
        if self.discriminant != expected_disc:
            raise ValueError(
                f"Forged or inconsistent discriminant: provided {self.discriminant} does not match canonical calculation {expected_disc}."
            )
        return self


class DegenerateEquationIR(ProblemIR):
    """Representation of degenerate equations with a == 0."""
    target_variable: str = Field(default="x", min_length=1, max_length=10)
    a: RationalFraction = Field(default_factory=lambda: RationalFraction(numerator=0, denominator=1))
    b: RationalFraction
    c: RationalFraction
    classification: EquationClassificationType = Field(
        ..., description="LINEAR, IDENTITY, or CONTRADICTION"
    )
    linear_root: Optional[RationalFraction] = Field(
        None, description="Exact rational root -c/b when classification is LINEAR"
    )

    @model_validator(mode="after")
    def _validate_degenerate_invariants(self) -> DegenerateEquationIR:
        """Enforce semantic mathematical invariants for DegenerateEquationIR."""
        if self.a.numerator != 0:
            raise ValueError(f"Leading coefficient 'a' must be 0 in DegenerateEquationIR, got {self.a}.")
        b_rat = self.b.to_rational()
        c_rat = self.c.to_rational()

        if not b_rat.is_zero:
            # Linear equation: bx + c = 0 with b != 0 -> root = -c/b
            if self.classification != EquationClassificationType.LINEAR:
                raise ValueError(
                    f"Degenerate equation with b != 0 must have classification LINEAR, got '{self.classification}'."
                )
            expected_root = RationalFraction.from_rational(-c_rat / b_rat)
            if self.linear_root is None or self.linear_root.to_rational() != expected_root.to_rational():
                raise ValueError(
                    f"Linear equation root must equal -c/b = {expected_root}, got {self.linear_root}."
                )
        elif c_rat.is_zero:
            # Identity equation: 0x + 0 = 0 -> infinitely many solutions
            if self.classification != EquationClassificationType.IDENTITY:
                raise ValueError(
                    f"Degenerate equation with b == 0 and c == 0 must have classification IDENTITY, got '{self.classification}'."
                )
            if self.linear_root is not None:
                raise ValueError(
                    f"Identity equation (0 = 0) cannot have a discrete linear root, got {self.linear_root}."
                )
        else:
            # Contradiction equation: 0x + c = 0 with c != 0 -> no solution
            if self.classification != EquationClassificationType.CONTRADICTION:
                raise ValueError(
                    f"Degenerate equation with b == 0 and c != 0 must have classification CONTRADICTION, got '{self.classification}'."
                )
            if self.linear_root is not None:
                raise ValueError(
                    f"Contradiction equation (0 = {c_rat}) cannot have a linear root, got {self.linear_root}."
                )
        return self


# ============================================================================
# 4. METHOD REGISTRY & ORTHOGONAL METHOD ASSESSMENT
# ============================================================================

class PrerequisiteStatus(BaseModel):
    """Evaluation status for a single pedagogical/method prerequisite."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    prerequisite_id: str
    is_satisfied: bool
    description_vi: str


class MethodDefinition(BaseModel):
    """First-class registry definition of a solution technique."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str = Field(..., description="Language-independent unique method identifier")
    problem_family: ProblemCategory
    title_vi: str = Field(..., description="Vietnamese pedagogical title")
    description_vi: str
    curriculum_level: str = Field(
        default="VIETNAM_SECONDARY_TO_BE_VERIFIED",
        description="Curriculum reference tag (to be verified against authoritative MoET curriculum mapping)"
    )
    relative_complexity: int = Field(default=1, ge=1, le=5, description="1=Direct, 5=Advanced")
    prerequisite_ids: List[str] = Field(default_factory=list)
    verification_capability: VerificationCapability = Field(default=VerificationCapability.HOST_VERIFIABLE)


class MethodAssessment(BaseModel):
    """Orthogonal multi-dimensional assessment of a method for a specific problem instance."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    problem_family: ProblemCategory
    mathematical_applicability: MathematicalApplicability
    support_status: SupportStatus
    execution_availability: ExecutionAvailability
    pedagogical_recommendation: PedagogicalRecommendation
    verification_capability: VerificationCapability
    reasons: List[str] = Field(default_factory=list, description="Explanations for status or recommendation")
    prerequisite_status: List[PrerequisiteStatus] = Field(default_factory=list)
    pedagogical_priority: int = Field(default=1, description="Sort priority in UI (1 = highest)")


# ============================================================================
# 5. SOLUTION TRACES & STEPS
# ============================================================================

class SolutionStep(BaseModel):
    """Step in a verified solution trace."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    step_number: int = Field(..., ge=1)
    latex_expression: str
    explanation_vi: str
    rule_or_theorem_used: Optional[str] = None
    why_this_step_vi: Optional[str] = None
    sub_steps: List[SolutionStep] = Field(default_factory=list)


class SolutionTrace(BaseModel):
    """Complete structured solution trace for an algebraic problem."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    solution_outcome: SolutionOutcome
    roots: List[RealRootValue] = Field(default_factory=list)
    steps: List[SolutionStep] = Field(default_factory=list)
    final_answer_latex: str
    is_complete: bool = True


# ============================================================================
# 6. GEOMETRY DOMAIN CONTRACTS
# ============================================================================

class GeometricPrimitive(BaseModel):
    """Semantic geometric object."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: str = Field(..., description="e.g. 'A', 'B', 'C', 'M', 'BC', 'triangle_ABC'")
    type: PrimitiveType
    parent_ids: List[str] = Field(default_factory=list)


class GeometricRelation(BaseModel):
    """Semantic relationship or constraint in geometric theorem environment."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    predicate: GeometricPredicate
    target_ids: List[str] = Field(..., description="Referenced primitive IDs")
    parameters: Dict[str, str] = Field(default_factory=dict)


class GeometryProblemIR(ProblemIR):
    """Semantic geometry problem representation without Cartesian coordinate bias."""
    primitives: List[GeometricPrimitive]
    givens: List[GeometricRelation]
    goals: List[GeometricRelation]


class ProofStep(BaseModel):
    """Deductive step in a geometric proof."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    step_id: str
    canonical_rule_id: str = Field(..., description="e.g. 'RULE_TRIANGLE_CONGRUENCE_SSS'")
    statement_vi: str
    deduction_latex: str
    premise_step_ids: List[str] = Field(default_factory=list)


class ProofTrace(BaseModel):
    """Synthetic geometric deduction proof trace DAG."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    proof_method_id: str
    outcome: ProofOutcome
    steps: List[ProofStep] = Field(default_factory=list)
    qed_conclusion_vi: Optional[str] = None
    is_valid_dag: bool = True


# ============================================================================
# 7. INDEPENDENT VERIFICATION CERTIFICATES
# ============================================================================

class VerificationCertificate(BaseModel):
    """Tamper-evident token certifying independent host mathematical verification."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    certificate_id: str
    problem_hash: str
    outcome: VerificationOutcome
    verifier_name: str = Field(default="MKE_HOST_INDEPENDENT_VERIFIER_V1")
    verifier_version: str = Field(default="1.0.0")
    verified_at_utc: datetime = Field(default_factory=datetime.utcnow)
    algebraic_identities_passed: List[str] = Field(default_factory=list)
    residual_checks: List[str] = Field(default_factory=list)
    vieta_relations_checked: bool = False
    multiplicity_verified: bool = False
    no_real_roots_verified: bool = False
    integrity_fingerprint: str = Field(
        ...,
        description="Deterministic unkeyed SHA-256 digest of canonical certificate verification payload (content identifier, not a digital signature)"
    )
    certificate_signature: Optional[str] = Field(
        default=None,
        description="Deprecated alias for integrity_fingerprint. Note: this is an unkeyed SHA-256 digest, NOT a cryptographic signature."
    )


# ============================================================================
# 8. DEPENDENCY GRAPH STRUCTURES
# ============================================================================

class DependencyNode(BaseModel):
    """Node in the reactive workspace dependency DAG."""
    model_config = ConfigDict(extra="forbid", strict=True)

    node_id: str
    name: str
    node_type: str = Field(default="COMPUTED", description="INPUT, COMPUTED, PRESENTATION")
    is_valid: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
