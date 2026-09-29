"""Strict, typed Mathematical Intermediate Representation (MKE-IR) models.

Phase 1 & 2: Versioned Pydantic models for structured intake of Vietnamese math problems.
Prohibits extra fields, mandates strict types, and preserves source provenance.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProblemCategory(str, Enum):
    """Categorization of mathematical problem intake."""
    EQUATION_SINGLE = "EQUATION_SINGLE"
    EQUATION_SYSTEM = "EQUATION_SYSTEM"
    INEQUALITY_SINGLE = "INEQUALITY_SINGLE"
    EXPRESSION_SIMPLIFY = "EXPRESSION_SIMPLIFY"
    DIFFERENTIATION = "DIFFERENTIATION"
    INTEGRATION = "INTEGRATION"
    PARAMETER_ANALYSIS = "PARAMETER_ANALYSIS"
    WORD_PROBLEM = "WORD_PROBLEM"
    UNKNOWN_UNSUPPORTED = "UNKNOWN_UNSUPPORTED"


class QuestionFormat(str, Enum):
    """Structural format of the Vietnamese math problem (GDPT 2018)."""
    FREE_FORM = "FREE_FORM"
    MULTIPLE_CHOICE_4 = "MULTIPLE_CHOICE_4"
    TRUE_FALSE_4 = "TRUE_FALSE_4"
    SHORT_ANSWER = "SHORT_ANSWER"
    MULTI_PART_STEM = "MULTI_PART_STEM"


class SourceSpan(BaseModel):
    """Character span in the original student query establishing source fidelity."""
    model_config = ConfigDict(extra="forbid")

    start_char: int = Field(..., ge=0, description="0-indexed start character offset in raw_query")
    end_char: int = Field(..., ge=0, description="0-indexed end character offset (exclusive) in raw_query")
    source_fragment: str = Field(..., min_length=1, description="Exact substring from raw_query")
    semantic_role: str = Field(..., min_length=1, description="Role: STEM, EQUATION, CONSTRAINT, OPTION_A, etc.")


class ExtractedConstraint(BaseModel):
    """Mathematical constraint (e.g. real-domain restrictions x > 1, x != 0)."""
    model_config = ConfigDict(extra="forbid")

    variable: str = Field(..., min_length=1, description="Constrained variable identifier (e.g. 'x')")
    relation: str = Field(..., min_length=1, description="Relation: '>', '>=', '<', '<=', '!=', '=', 'in'")
    bound_expression: str = Field(..., min_length=1, description="Bound expression or interval (e.g. '0', '[1, +oo)')")
    source_span: Optional[SourceSpan] = Field(default=None, description="Span in raw query if explicitly stated")
    is_inferred: bool = Field(default=False, description="True if model assumed/inferred rather than explicitly stated")


class QuestionSubpart(BaseModel):
    """Individual subpart of a multi-part or True/False question."""
    model_config = ConfigDict(extra="forbid")

    subpart_id: str = Field(..., min_length=1, description="Identifier (e.g. 'a', 'b', 'c', 'd')")
    statement: str = Field(..., min_length=1, description="Subpart text statement")
    extracted_expression: Optional[str] = Field(default=None, description="Mathematical expression for this subpart")
    source_span: Optional[SourceSpan] = Field(default=None, description="Source text span for this subpart")
    is_supported: bool = Field(default=True, description="Whether this subpart is within supported CAS scope")


class UncertaintyFlag(BaseModel):
    """Explicit ambiguity, uncertainty, or unverified assumption flag."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, description="Machine-readable error/uncertainty code")
    message: str = Field(..., min_length=1, description="Human-readable non-sensitive description")
    severity: str = Field(default="WARNING", description="'WARNING', 'ERROR', 'CRITICAL'")


class ValidationIssue(BaseModel):
    """Deterministic validation diagnostic emitted by MKEIntakeValidator."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, description="Standardized error code")
    message: str = Field(..., min_length=1, description="Non-sensitive error description")
    field_path: str = Field(default="", description="JSON field path (e.g. 'primary_expressions[0]')")
    is_fatal: bool = Field(default=True, description="Whether this issue blocks CAS routing")


class MathIntermediateRepresentation(BaseModel):
    """Strict typed Intermediate Representation (MKE-IR) for mathematical problem intake."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="mke.ir.v1", description="MKE-IR schema version")
    problem_category: ProblemCategory = Field(..., description="Mathematical category")
    question_format: QuestionFormat = Field(default=QuestionFormat.FREE_FORM, description="Question structure format")
    raw_query: str = Field(..., min_length=1, max_length=4000, description="Original, unedited student text")
    primary_expressions: List[str] = Field(..., min_length=1, description="Core mathematical expressions/equations/systems")
    target_variables: List[str] = Field(default_factory=list, description="Target variables to solve/differentiate/integrate for")
    parameters: List[str] = Field(default_factory=list, description="Parameters (e.g. 'm', 'k')")
    extracted_constraints: List[ExtractedConstraint] = Field(default_factory=list, description="Explicit and inferred constraints")
    subparts: List[QuestionSubpart] = Field(default_factory=list, description="Subparts for multi-part / true-false questions")
    given_options: Optional[Dict[str, str]] = Field(default=None, description="Multiple choice options (A, B, C, D)")
    source_spans: List[SourceSpan] = Field(default_factory=list, description="Source text character spans")
    uncertainty_flags: List[UncertaintyFlag] = Field(default_factory=list, description="Uncertainty / ambiguity flags")
    model_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Uncalibrated model confidence heuristic")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual caller metadata")


class ValidationResult(BaseModel):
    """Deterministic outcome of pre-dispatch intake validation."""
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if valid for downstream CAS routing")
    status: str = Field(..., description="'VALID', 'INVALID', 'UNSUPPORTED', 'AMBIGUOUS'")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues and diagnostics")
    uncertainties: List[UncertaintyFlag] = Field(default_factory=list, description="Uncertainty flags")
    validated_ir: Optional[MathIntermediateRepresentation] = Field(default=None, description="Validated MKE-IR model")
    target_operation: Optional[str] = Field(default=None, description="Target CAS OperationType name if valid")
