"""MKE MVP V1 — Application DTOs and Discriminated State Machine.

Defines the Pydantic v2 Single Source of Truth (SSOT) request, response, and problem view
data transfer objects for the MKE MVP V1 algebra application layer.
All models use strict validation, extra-field prohibition, and immutable frozen configurations.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mke_product.application.errors import ApplicationErrorCode
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    PedagogicalRecommendation,
    PrerequisiteStatus,
    ProblemCategory,
    QuadraticDiscriminant,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionTrace,
    SupportStatus,
    VerificationCapability,
    VerificationCertificate,
    VerificationOutcome,
)
from mke_product.parser.errors import Span


# ============================================================================
# 1. REQUEST DTOS
# ============================================================================

class RawEquationInput(BaseModel):
    """Raw mathematical text equation input mode."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["RAW_TEXT"] = "RAW_TEXT"
    raw_query: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Raw equation string e.g. 'x^2 - 5*x + 6 = 0'",
    )
    target_variable: Literal["x"] = "x"


class CanonicalCoefficientInput(BaseModel):
    """Direct canonical coefficient parameter input mode for live editing and method switching."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["COEFFICIENTS"] = "COEFFICIENTS"
    a: RationalFraction = Field(..., description="Leading coefficient a")
    b: RationalFraction = Field(..., description="Linear coefficient b")
    c: RationalFraction = Field(..., description="Constant term c")
    target_variable: Literal["x"] = "x"


InputPayloadUnion = Annotated[
    Union[RawEquationInput, CanonicalCoefficientInput],
    Field(discriminator="input_mode"),
]


class SolveRequest(BaseModel):
    """Application intake request container for equation analysis and solving."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_payload: InputPayloadUnion
    selected_method_id: Optional[str] = Field(
        default=None,
        description="Explicit method selection ID. If None, highest-priority applicable method is executed.",
    )
    schema_version: Literal["1.0.0"] = "1.0.0"


# ============================================================================
# 2. CANONICAL PROBLEM VIEWS
# ============================================================================

class CanonicalQuadraticProblemView(BaseModel):
    """Canonical problem representation for true quadratic equations (a != 0)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_type: Literal["QUADRATIC"] = "QUADRATIC"
    problem_id: str
    raw_query: Optional[str] = None
    equation_latex: str = Field(..., description="Canonical LaTeX equation e.g. 'x^2 - 5x + 6 = 0'")
    category: Literal[ProblemCategory.ALGEBRA_QUADRATIC] = ProblemCategory.ALGEBRA_QUADRATIC
    classification: Literal[EquationClassificationType.QUADRATIC] = EquationClassificationType.QUADRATIC
    a: RationalFraction
    b: RationalFraction
    c: RationalFraction
    discriminant: QuadraticDiscriminant
    semantic_revision_hash: str

    @model_validator(mode="after")
    def _validate_quadratic_view(self) -> CanonicalQuadraticProblemView:
        if self.a.numerator == 0:
            raise ValueError("Leading coefficient 'a' cannot be zero in CanonicalQuadraticProblemView.")
        return self


class CanonicalDegenerateProblemView(BaseModel):
    """Canonical problem representation for degenerate equations (a == 0). Zero discriminant invented."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_type: Literal["DEGENERATE"] = "DEGENERATE"
    problem_id: str
    raw_query: Optional[str] = None
    equation_latex: str = Field(..., description="Canonical LaTeX equation e.g. '2x - 4 = 0'")
    category: Literal[ProblemCategory.ALGEBRA_QUADRATIC] = ProblemCategory.ALGEBRA_QUADRATIC
    classification: Literal[
        EquationClassificationType.LINEAR,
        EquationClassificationType.IDENTITY,
        EquationClassificationType.CONTRADICTION,
    ]
    a: RationalFraction = Field(default_factory=lambda: RationalFraction(numerator=0, denominator=1))
    b: RationalFraction
    c: RationalFraction
    linear_root: Optional[RationalFraction] = None
    semantic_revision_hash: str

    @model_validator(mode="after")
    def _validate_degenerate_view(self) -> CanonicalDegenerateProblemView:
        if self.a.numerator != 0:
            raise ValueError(f"Leading coefficient 'a' must be 0 in CanonicalDegenerateProblemView, got {self.a}.")
        return self


CanonicalProblemUnion = Annotated[
    Union[CanonicalQuadraticProblemView, CanonicalDegenerateProblemView],
    Field(discriminator="problem_type"),
]


# ============================================================================
# 3. METHOD ASSESSMENT & SOLUTION VIEWS
# ============================================================================

class MethodOptionView(BaseModel):
    """Orthogonal assessment profile of a single registered mathematical method."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    title_vi: str
    mathematical_applicability: MathematicalApplicability
    support_status: SupportStatus
    execution_availability: ExecutionAvailability
    pedagogical_recommendation: PedagogicalRecommendation
    verification_capability: VerificationCapability
    reasons: List[str] = Field(default_factory=list)
    prerequisites: List[PrerequisiteStatus] = Field(default_factory=list)
    has_trace_available: bool
    pedagogical_priority: int = 1


class VerifiedSolutionView(BaseModel):
    """Verified execution result and step-by-step trace."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    outcome: SolutionOutcome
    roots: List[RealRootValue] = Field(default_factory=list)
    final_answer_latex: str
    trace: SolutionTrace
    verification_scope: Literal["FINAL_SOLUTION"] = "FINAL_SOLUTION"
    certificate: VerificationCertificate

    @model_validator(mode="after")
    def _validate_verified_solution(self) -> VerifiedSolutionView:
        if self.certificate.outcome != VerificationOutcome.VERIFIED_COMPLETE:
            raise ValueError("VerifiedSolutionView certificate must have outcome VERIFIED_COMPLETE.")
        if self.trace.method_id != self.method_id:
            raise ValueError(
                f"Trace method_id '{self.trace.method_id}' does not match VerifiedSolutionView method_id '{self.method_id}'."
            )
        if self.trace.solution_outcome != self.outcome:
            raise ValueError(
                f"Trace solution_outcome '{self.trace.solution_outcome}' does not match VerifiedSolutionView outcome '{self.outcome}'."
            )
        if self.trace.final_answer_latex != self.final_answer_latex:
            raise ValueError(
                f"Trace final_answer_latex '{self.trace.final_answer_latex}' does not match VerifiedSolutionView '{self.final_answer_latex}'."
            )
        return self


class DegenerateSolutionView(BaseModel):
    """Immutable verified solution presentation for degenerate equations (a == 0)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    classification: Literal[
        EquationClassificationType.LINEAR,
        EquationClassificationType.IDENTITY,
        EquationClassificationType.CONTRADICTION,
    ]
    outcome: Literal[
        SolutionOutcome.ONE_REAL_LINEAR_ROOT,
        SolutionOutcome.INFINITE_REAL_SOLUTIONS,
        SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
    ]
    linear_root: Optional[RationalFraction] = Field(
        default=None,
        description="Exact rational root -c/b when outcome is ONE_REAL_LINEAR_ROOT",
    )
    final_answer_latex: str = Field(..., description="Canonical LaTeX representation of the solution set")
    verification_scope: Literal["FINAL_SOLUTION"] = "FINAL_SOLUTION"
    certificate: VerificationCertificate

    @model_validator(mode="after")
    def _validate_degenerate_solution_invariants(self) -> DegenerateSolutionView:
        if self.certificate.outcome != VerificationOutcome.VERIFIED_COMPLETE:
            raise ValueError("DegenerateSolutionView certificate must have outcome VERIFIED_COMPLETE.")
        if self.outcome == SolutionOutcome.ONE_REAL_LINEAR_ROOT:
            if self.classification != EquationClassificationType.LINEAR:
                raise ValueError("Outcome ONE_REAL_LINEAR_ROOT requires classification LINEAR.")
            if self.linear_root is None:
                raise ValueError("linear_root must be provided when outcome is ONE_REAL_LINEAR_ROOT.")
        elif self.outcome == SolutionOutcome.INFINITE_REAL_SOLUTIONS:
            if self.classification != EquationClassificationType.IDENTITY:
                raise ValueError("Outcome INFINITE_REAL_SOLUTIONS requires classification IDENTITY.")
            if self.linear_root is not None:
                raise ValueError(f"linear_root must be None when outcome is {self.outcome}.")
        elif self.outcome == SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION:
            if self.classification != EquationClassificationType.CONTRADICTION:
                raise ValueError("Outcome NO_REAL_SOLUTIONS_CONTRADICTION requires classification CONTRADICTION.")
            if self.linear_root is not None:
                raise ValueError(f"linear_root must be None when outcome is {self.outcome}.")
        return self


# ============================================================================
# 4. RESPONSE ENUMS & STATE MACHINE MODELS
# ============================================================================

class NoExecutionReasonCode(str, Enum):
    """Machine-readable reason for why no trace execution occurred in analyzed response."""

    METHOD_NOT_APPLICABLE = "METHOD_NOT_APPLICABLE"
    METHOD_NOT_EXECUTABLE = "METHOD_NOT_EXECUTABLE"
    DEGENERATE_EXACT_SOLUTION = "DEGENERATE_EXACT_SOLUTION"


class SolvedResponse(BaseModel):
    """Response state when problem is analyzed AND an applicable/available method is verified."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["SOLVED"] = "SOLVED"
    problem: CanonicalQuadraticProblemView
    available_methods: List[MethodOptionView]
    selected_method_id: str
    solution: VerifiedSolutionView


class AnalyzedNoExecutionResponse(BaseModel):
    """Response state when problem is analyzed but no trace executed (e.g. unavailable method selected or degenerate linear)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["ANALYZED_NO_EXECUTION"] = "ANALYZED_NO_EXECUTION"
    problem: CanonicalProblemUnion
    available_methods: List[MethodOptionView] = Field(default_factory=list)
    selected_method_id: Optional[str] = None
    degenerate_solution: Optional[DegenerateSolutionView] = None
    reason_code: NoExecutionReasonCode
    analysis_message_vi: str


class ErrorResponse(BaseModel):
    """Response state when a fatal intake, parse, normalization, or invariant error occurs."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["ERROR"] = "ERROR"
    error_code: ApplicationErrorCode
    message_vi: str
    message_en: str
    span: Optional[Span] = None
    details: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_span(cls, data: Any) -> Any:
        if isinstance(data, dict):
            span_val = data.get("span")
            if isinstance(span_val, (tuple, list)) and len(span_val) == 2:
                data = dict(data)
                data["span"] = Span(start=int(span_val[0]), end=int(span_val[1]))
        return data


SolveResponseUnion = Annotated[
    Union[SolvedResponse, AnalyzedNoExecutionResponse, ErrorResponse],
    Field(discriminator="response_status"),
]
