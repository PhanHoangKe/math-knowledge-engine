"""Strict, typed Mathematical Intermediate Representation (MKE-IR) models.

Phase 1 & 2: Versioned Pydantic models for structured intake of Vietnamese math problems.
Prohibits extra fields, mandates strict types, and preserves source provenance.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field


SUPPORTED_MKE_IR_SCHEMA_VERSION = "mke.ir.v1"

ALLOWLISTED_STATUSES: Set[str] = {
    "VALID",
    "INVALID",
    "UNSUPPORTED",
    "AMBIGUOUS",
    "UNVERIFIED_SEMANTICS",
}

ALLOWLISTED_OPERATIONS: Set[str] = {
    "SOLVE",
    "SOLVE_SYSTEM",
    "SOLVE_INEQUALITY",
    "SIMPLIFY",
    "DIFFERENTIATE",
    "INTEGRATE",
}

ALLOWLISTED_ISSUE_DEFINITIONS: Dict[str, str] = {
    "EMPTY_RAW_QUERY": "Raw student query must be a non-empty string.",
    "OVERSIZED_INPUT": "Raw student query length exceeds maximum allowed character limit.",
    "RAW_QUERY_MISMATCH": "Payload raw_query does not match authoritative input query.",
    "SCHEMA_VALIDATION_ERROR": "Payload failed MKE-IR schema validation. Structure does not conform to specification.",
    "INVALID_PAYLOAD_TYPE": "Payload must be a dictionary or MathIntermediateRepresentation instance.",
    "UNSUPPORTED_SCHEMA_VERSION": "MKE-IR schema version is unsupported.",
    "EXCESSIVE_METADATA_ENTRIES": "Metadata dictionary exceeds maximum allowed entry count.",
    "MISSING_OPTIONS": "Multiple choice question format requires 4 options (A, B, C, D).",
    "INVALID_OPTION_KEYS": "Multiple choice question options must contain exactly keys 'A', 'B', 'C', and 'D'.",
    "EMPTY_OPTION_TEXT": "Multiple choice option text cannot be empty.",
    "OPTION_TEXT_TOO_LONG": "Multiple choice option text exceeds maximum allowed character length.",
    "INVALID_TRUE_FALSE_SUBPARTS_COUNT": "Four-part True/False question must have exactly 4 subparts (a, b, c, d).",
    "INVALID_TRUE_FALSE_SUBPART_IDS": "Four-part True/False subparts must have IDs 'a', 'b', 'c', and 'd'.",
    "EMPTY_SUBPART_STATEMENT": "Subpart statement cannot be empty.",
    "SUBPART_STATEMENT_TOO_LONG": "Subpart statement exceeds maximum allowed character length.",
    "MISSING_SUBPARTS": "Multi-part stem question format requires at least one subpart.",
    "DUPLICATE_SUBPART_ID": "Duplicate subpart ID detected in multi-part question.",
    "INVALID_EXPRESSION_CARDINALITY": "Single mathematical operation category requires exactly one primary expression.",
    "MISSING_TARGET_VARIABLE": "Problem category requires explicit target_variables.",
    "INVALID_VARIABLE_IDENTIFIER": "Target variable contains invalid identifier characters.",
    "INVALID_PARAMETER_IDENTIFIER": "Parameter contains invalid identifier characters.",
    "OVERLAPPING_VARIABLES_AND_PARAMETERS": "Target variables and parameters must be disjoint sets.",
    "INVALID_CONSTRAINT_VARIABLE": "Constraint variable identifier is invalid.",
    "INVALID_CONSTRAINT_RELATION": "Constraint relation is not supported.",
    "EMPTY_CONSTRAINT_BOUND": "Constraint bound expression cannot be empty.",
    "CONSTRAINT_BOUND_TOO_LONG": "Constraint bound expression exceeds maximum allowed character length.",
    "INVALID_CONSTRAINT_SYNTAX": "Constraint bound expression failed syntax parsing.",
    "MISSING_CONSTRAINT_PROVENANCE": "Explicit student constraint lacks required source span evidence.",
    "INVALID_CONSTRAINT_ROLE": "Constraint source span semantic role is not allowed for constraints.",
    "CONSTRAINT_SOURCE_MISMATCH": "Explicit constraint does not match source span text.",
    "SOURCE_SPAN_OUT_OF_BOUNDS": "Source span character offsets exceed raw query bounds.",
    "SOURCE_FRAGMENT_MISMATCH": "Source fragment text does not match character range in raw query.",
    "MISSING_EXPRESSION_PROVENANCE": "Primary mathematical expression lacks required source span provenance.",
    "UNLINKED_EXPRESSION_PROVENANCE": "Primary expression has no corresponding source span reference.",
    "UNSUPPORTED_PROBLEM_CATEGORY": "Problem category is not supported for automated CAS proof.",
    "EMPTY_PRIMARY_EXPRESSION": "Primary mathematical expression cannot be empty.",
    "EXPRESSION_TOO_LONG": "Primary expression exceeds maximum allowed character length.",
    "EXCESSIVE_NESTING_DEPTH": "Expression exceeds maximum allowed bracket nesting depth.",
    "MATH_SYNTAX_ERROR": "Primary expression failed mathematical syntax parsing.",
    "SUBPART_EXPRESSION_TOO_LONG": "Subpart expression exceeds maximum allowed character length.",
    "SUBPART_EXCESSIVE_NESTING_DEPTH": "Subpart expression exceeds maximum allowed bracket nesting depth.",
    "SUBPART_SYNTAX_ERROR": "Subpart expression failed mathematical syntax parsing.",
    "GENERIC_VALIDATION_ERROR": "Validation check failed specification criteria.",
}

ALLOWLISTED_UNCERTAINTIES: Dict[str, Dict[str, str]] = {
    "UNCONFIRMED_INFERRED_CONSTRAINT": {
        "severity": "ERROR",
        "message": "Model-inferred mathematical constraint is unconfirmed and blocks automatic CAS execution.",
    },
    "UNVERIFIED_SEMANTIC_TRANSFORMATION": {
        "severity": "WARNING",
        "message": "Primary expression is a normalized or inferred transformation.",
    },
    "MULTI_PART_AWAITING_STAGE": {
        "severity": "WARNING",
        "message": "Multi-part and multiple-choice questions are structurally validated but require downstream stage evaluation.",
    },
    "AMBIGUOUS_VARIABLE_BINDING": {
        "severity": "WARNING",
        "message": "Variable binding in problem statement has potential ambiguity.",
    },
    "ASSUMED_REAL_DOMAIN": {
        "severity": "WARNING",
        "message": "Real domain evaluation assumed for expressions without explicit domain.",
    },
    "UNSUPPORTED_NOTATION_NORMALIZED": {
        "severity": "WARNING",
        "message": "Non-standard mathematical notation was normalized during intake.",
    },
    "GENERIC_EXTRACTION_UNCERTAINTY": {
        "severity": "ERROR",
        "message": "Extraction contains unverified assumptions or unreviewed uncertainty.",
    },
}

SEVERITY_ORDER: Dict[str, int] = {"WARNING": 1, "ERROR": 2, "CRITICAL": 3}

ALLOWLISTED_FIXED_PATHS: Set[str] = {
    "root",
    "raw_query",
    "problem_category",
    "question_format",
    "schema_version",
    "metadata",
    "primary_expressions",
    "target_variables",
    "parameters",
    "extracted_constraints",
    "subparts",
    "given_options",
    "source_spans",
    "uncertainty_flags",
    "given_options.A",
    "given_options.B",
    "given_options.C",
    "given_options.D",
}

ALLOWLISTED_INDEXED_PATH_PATTERNS: List[re.Pattern] = [
    re.compile(r"^primary_expressions\[([0-9]{1,3})\]$"),
    re.compile(r"^target_variables\[([0-9]{1,3})\]$"),
    re.compile(r"^parameters\[([0-9]{1,3})\]$"),
    re.compile(r"^extracted_constraints\[([0-9]{1,3})\]$"),
    re.compile(r"^extracted_constraints\[([0-9]{1,3})\]\.(variable|relation|bound_expression|source_span|is_inferred)$"),
    re.compile(r"^subparts\[([0-9]{1,3})\]$"),
    re.compile(r"^subparts\[([0-9]{1,3})\]\.(subpart_id|statement|extracted_expression|source_span)$"),
    re.compile(r"^source_spans\[([0-9]{1,3})\]$"),
    re.compile(r"^source_spans\[([0-9]{1,3})\]\.(start_char|end_char|source_fragment|semantic_role)$"),
    re.compile(r"^uncertainty_flags\[([0-9]{1,3})\]$"),
]


def sanitize_public_field_path(field_path: str) -> str:
    """Ensure field_path conforms strictly to allowlisted validator path schemas."""
    if not isinstance(field_path, str) or not field_path.strip():
        return "root"
    clean = field_path.strip()
    if clean in ALLOWLISTED_FIXED_PATHS:
        return clean
    for pattern in ALLOWLISTED_INDEXED_PATH_PATTERNS:
        m = pattern.match(clean)
        if m:
            idx = int(m.group(1))
            if 0 <= idx < 100:  # safe bounded index limit
                return clean
    return "root"




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


class SemanticVerificationStatus(str, Enum):
    """Provenance and semantic verification state of extracted mathematical expressions."""
    VERIFIED_LITERAL = "VERIFIED_LITERAL"
    UNVERIFIED_TRANSFORMATION = "UNVERIFIED_TRANSFORMATION"
    UNVERIFIED_SYNTHESIS = "UNVERIFIED_SYNTHESIS"
    UNLINKED = "UNLINKED"


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

    variable: str = Field(..., min_length=1, max_length=30, description="Constrained variable identifier (e.g. 'x')")
    relation: str = Field(..., min_length=1, max_length=10, description="Relation: '>', '>=', '<', '<=', '!=', '=', 'in'")
    bound_expression: str = Field(..., min_length=1, max_length=1000, description="Bound expression or interval (e.g. '0', '[1, +oo)')")
    source_span: Optional[SourceSpan] = Field(default=None, description="Span in raw query if explicitly stated")
    is_inferred: bool = Field(default=False, description="True if model assumed/inferred rather than explicitly stated")


class QuestionSubpart(BaseModel):
    """Individual subpart of a multi-part or True/False question."""
    model_config = ConfigDict(extra="forbid")

    subpart_id: str = Field(..., min_length=1, max_length=30, description="Identifier (e.g. 'a', 'b', 'c', 'd')")
    statement: str = Field(..., min_length=1, max_length=2000, description="Subpart text statement")
    extracted_expression: Optional[str] = Field(default=None, max_length=1000, description="Mathematical expression for this subpart")
    source_span: Optional[SourceSpan] = Field(default=None, description="Source text span for this subpart")
    is_supported: bool = Field(default=True, description="Whether this subpart is within supported CAS scope")


class UncertaintyFlag(BaseModel):
    """Explicit ambiguity, uncertainty, or unverified assumption flag."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=60, description="Machine-readable error/uncertainty code")
    message: str = Field(..., min_length=1, max_length=300, description="Human-readable non-sensitive description")
    severity: str = Field(default="WARNING", description="'WARNING', 'ERROR', 'CRITICAL'")


class ValidationIssue(BaseModel):
    """Deterministic validation diagnostic emitted by MKEIntakeValidator."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=60, description="Standardized error code")
    message: str = Field(..., min_length=1, max_length=300, description="Non-sensitive error description")
    field_path: str = Field(default="", max_length=100, description="JSON field path (e.g. 'primary_expressions[0]')")
    is_fatal: bool = Field(default=True, description="Whether this issue blocks CAS routing")


class MathIntermediateRepresentation(BaseModel):
    """Strict typed Intermediate Representation (MKE-IR) for mathematical problem intake."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SUPPORTED_MKE_IR_SCHEMA_VERSION, description="MKE-IR schema version")
    problem_category: ProblemCategory = Field(..., description="Mathematical category")
    question_format: QuestionFormat = Field(default=QuestionFormat.FREE_FORM, description="Question structure format")
    raw_query: str = Field(..., min_length=1, max_length=4000, description="Original, unedited student text")
    raw_query_provenance: str = Field(default="EXTRACTED", description="'EXTRACTED', 'SYSTEM_POPULATED', 'USER_EXPLICIT'")
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


class PublicValidationDiagnostic(BaseModel):
    """Sanitized, student-facing diagnostic projection of validation results.

    SECURITY BOUNDARY:
    This model excludes all internal pipeline data such as full mathematical IR,
    raw student query text, caller metadata, and character source spans.
    Only standardized, allowlisted issues and sanitized uncertainty flags are exposed.
    """
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if mathematically valid and CAS-ready")
    is_cas_ready: bool = Field(..., description="True if eligible for future CAS dispatch")
    status: str = Field(..., description="'VALID', 'INVALID', 'UNSUPPORTED', 'AMBIGUOUS', 'UNVERIFIED_SEMANTICS'")
    target_operation: Optional[str] = Field(default=None, description="Target CAS operation name if valid")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Sanitized validation issues")
    uncertainties: List[UncertaintyFlag] = Field(default_factory=list, description="Sanitized uncertainty flags")


class ValidationResult(BaseModel):
    """Internal deterministic outcome of pre-dispatch intake validation.

    INTERNAL PIPELINE USE ONLY:
    Contains `validated_ir` which preserves the mathematical expressions, variables,
    constraints, raw query, metadata, and character spans necessary for mathematical solving.
    For public/student-facing API serialization, callers MUST use `.to_public_diagnostic()`.
    """
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if valid and CAS-ready")
    is_structurally_valid: bool = Field(default=False, description="True if schema and types conform strictly")
    is_syntactically_valid: bool = Field(default=False, description="True if mathematical expressions parse cleanly")
    is_source_faithful: bool = Field(default=False, description="True if raw query and spans match strictly")
    semantic_status: SemanticVerificationStatus = Field(default=SemanticVerificationStatus.UNLINKED, description="Expression provenance verification state")
    is_cas_ready: bool = Field(default=False, description="True if eligible for future CAS dispatch")
    status: str = Field(..., description="'VALID', 'INVALID', 'UNSUPPORTED', 'AMBIGUOUS', 'UNVERIFIED_SEMANTICS'")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues and diagnostics")
    uncertainties: List[UncertaintyFlag] = Field(default_factory=list, description="Uncertainty flags")
    validated_ir: Optional[MathIntermediateRepresentation] = Field(default=None, description="Validated MKE-IR model (INTERNAL USE ONLY)")
    target_operation: Optional[str] = Field(default=None, description="Target CAS OperationType name if valid")

    @property
    def is_ready_for_cas(self) -> bool:
        """Compatibility property matching is_cas_ready."""
        return self.is_cas_ready

    def to_public_diagnostic(self) -> PublicValidationDiagnostic:
        """Project the internal validation result to a safe, allowlisted public diagnostic representation.

        Guarantees that untrusted contents, malformed codes, hostile messages, or unapproved
        statuses/operations cannot bypass the public security boundary.
        """
        # 1. Sanitize status
        safe_status = self.status if (isinstance(self.status, str) and self.status in ALLOWLISTED_STATUSES) else "INVALID"

        # 2. Sanitize target_operation
        safe_op = self.target_operation if (isinstance(self.target_operation, str) and self.target_operation in ALLOWLISTED_OPERATIONS) else None

        # 3. Sanitize issues with allowlisted codes, fixed messages, and safe field paths
        sanitized_issues: List[ValidationIssue] = []
        for issue in self.issues:
            code = issue.code if isinstance(issue.code, str) else ""
            if code in ALLOWLISTED_ISSUE_DEFINITIONS:
                msg = ALLOWLISTED_ISSUE_DEFINITIONS[code]
                safe_code = code
                safe_path = sanitize_public_field_path(issue.field_path)
            else:
                safe_code = "GENERIC_VALIDATION_ERROR"
                msg = ALLOWLISTED_ISSUE_DEFINITIONS["GENERIC_VALIDATION_ERROR"]
                safe_path = "root"
            is_fatal = bool(issue.is_fatal)
            sanitized_issues.append(ValidationIssue(
                code=safe_code,
                message=msg,
                field_path=safe_path,
                is_fatal=is_fatal
            ))

        # 4. Sanitize uncertainties with allowlisted codes, fixed messages, and resolved severities
        sanitized_uncertainties: List[UncertaintyFlag] = []
        for u in self.uncertainties:
            u_code = u.code if isinstance(u.code, str) else ""
            if u_code in ALLOWLISTED_UNCERTAINTIES:
                defn = ALLOWLISTED_UNCERTAINTIES[u_code]
                auth_val = SEVERITY_ORDER.get(defn["severity"], 2)
                cand_val = SEVERITY_ORDER.get(u.severity, 1) if isinstance(u.severity, str) else 1
                sev = u.severity if (isinstance(u.severity, str) and cand_val >= auth_val and u.severity in SEVERITY_ORDER) else defn["severity"]
                msg = defn["message"]
                safe_u_code = u_code
            else:
                safe_u_code = "GENERIC_EXTRACTION_UNCERTAINTY"
                msg = ALLOWLISTED_UNCERTAINTIES["GENERIC_EXTRACTION_UNCERTAINTY"]["message"]
                sev = "ERROR"
            sanitized_uncertainties.append(UncertaintyFlag(
                code=safe_u_code,
                message=msg,
                severity=sev
            ))

        # 5. Conservative public readiness fail-closed evaluation
        has_fatal_issues = any(i.is_fatal for i in sanitized_issues)
        has_blocking_uncertainties = any(u.severity in ("ERROR", "CRITICAL") for u in sanitized_uncertainties)
        is_status_valid = (safe_status == "VALID")
        has_valid_operation = (safe_op is not None and safe_op in ALLOWLISTED_OPERATIONS)

        public_cas_ready = bool(
            self.is_cas_ready
            and self.is_valid
            and is_status_valid
            and has_valid_operation
            and not has_fatal_issues
            and not has_blocking_uncertainties
        )
        public_is_valid = bool(
            self.is_valid
            and is_status_valid
            and not has_fatal_issues
            and not has_blocking_uncertainties
        )

        return PublicValidationDiagnostic(
            is_valid=public_is_valid,
            is_cas_ready=public_cas_ready,
            status=safe_status,
            target_operation=safe_op,
            issues=sanitized_issues,
            uncertainties=sanitized_uncertainties
        )

    def to_public_dict(self) -> Dict[str, Any]:
        """Serialize safe public diagnostic representation as dictionary."""
        return self.to_public_diagnostic().model_dump()



