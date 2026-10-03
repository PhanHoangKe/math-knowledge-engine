"""MKE MVP V1 — Milestone K1 Schema Contracts.

Defines the Python Single Source of Truth (SSOT) data contracts for:
- Quick Solving Tips (QuickTipKnowledge)
- Related Problem Forms (RelatedProblemFormKnowledge)
- Closed Condition DSL (ConditionExpr, PredicateId)
- Dynamic Runtime Assessment Contracts (QuickTipAssessmentView, ProblemFormAssessmentView)
- Associated K1 Enumerations (KnowledgeEntityStatus, TipCategory, DifficultyLevel, etc.)

All models use Pydantic v2 with strict validation, extra field rejection (extra="forbid"),
immutability (frozen=True), and deep immutability via immutable tuples for all collection fields.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Sequence, Set
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mke_product.knowledge.schemas import CurriculumRef, LocalizedText

# Canonical uppercase identifier regex: e.g. QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO
CANONICAL_ID_REGEX = re.compile(r"^[A-Z][A-Z0-9_]*$")
SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")


# ============================================================================
# 1. K1 ENUMERATIONS
# ============================================================================

class KnowledgeEntityStatus(str, Enum):
    """Lifecycle governance status of a K1 pedagogical knowledge entity."""

    PROVISIONAL = "PROVISIONAL"
    VERIFIED = "VERIFIED"
    DEPRECATED = "DEPRECATED"


class DifficultyLevel(str, Enum):
    """Pedagogical difficulty level of a problem form archetype."""

    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class TipCategory(str, Enum):
    """Taxonomic classification of a quick solving tip."""

    COEFFICIENT_RELATION = "COEFFICIENT_RELATION"
    REDUCED_ARITHMETIC = "REDUCED_ARITHMETIC"
    ROOT_PRODUCT_SUM = "ROOT_PRODUCT_SUM"
    SPECIAL_STRUCTURE = "SPECIAL_STRUCTURE"
    TRANSFORMATION = "TRANSFORMATION"


class TipApplicability(str, Enum):
    """Objective mathematical applicability outcome for a quick tip."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class TipRecommendation(str, Enum):
    """Pedagogical recommendation state for a quick tip."""

    RECOMMENDED = "RECOMMENDED"
    NEUTRAL = "NEUTRAL"
    DISCOURAGED = "DISCOURAGED"


class TipExecutionAvailability(str, Enum):
    """Whether the backend engine currently provides automated execution trace for this tip."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class FormMatchStatus(str, Enum):
    """Objective mathematical match outcome for a problem form archetype."""

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNKNOWN = "UNKNOWN"


class PredicateId(str, Enum):
    """Closed enumeration of atomic mathematical condition predicates."""

    A_NONZERO = "A_NONZERO"
    A_EQ_ONE = "A_EQ_ONE"
    B_NONZERO = "B_NONZERO"
    C_NONZERO = "C_NONZERO"
    B_EVEN_INTEGER = "B_EVEN_INTEGER"
    DISCRIMINANT_NONNEGATIVE = "DISCRIMINANT_NONNEGATIVE"
    DISCRIMINANT_RATIONAL_SQUARE = "DISCRIMINANT_RATIONAL_SQUARE"
    A_PLUS_B_PLUS_C_ZERO = "A_PLUS_B_PLUS_C_ZERO"
    A_MINUS_B_PLUS_C_ZERO = "A_MINUS_B_PLUS_C_ZERO"
    B_ZERO = "B_ZERO"
    C_ZERO = "C_ZERO"
    ROOTS_ARE_INTEGERS = "ROOTS_ARE_INTEGERS"


# ============================================================================
# 2. HELPER VALIDATORS FOR STRING SEQUENCES
# ============================================================================

def _validate_id_sequence(ids: Sequence[str], field_name: str) -> None:
    """Validates that a sequence of IDs contains non-empty strings and no duplicates."""
    seen: Set[str] = set()
    for item in ids:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} must contain non-empty, non-whitespace string IDs.")
        if item in seen:
            raise ValueError(f"{field_name} contains duplicate ID: '{item}'.")
        seen.add(item)


# ============================================================================
# 3. CLOSED CONDITION DSL MODEL (DEEP IMMUTABLE)
# ============================================================================

class ConditionExpr(BaseModel):
    """
    Closed boolean predicate expression container.
    Immutable declarative data representation for static applicability/recognition conditions.
    Deeply immutable via tuple collections and frozen configuration.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
    )

    all_of: tuple[PredicateId, ...] = Field(
        default=(),
        description="All predicates in this tuple must evaluate to TRUE",
    )
    any_of: tuple[PredicateId, ...] = Field(
        default=(),
        description="If non-empty, at least one predicate in this tuple must evaluate to TRUE",
    )
    none_of: tuple[PredicateId, ...] = Field(
        default=(),
        description="All predicates in this tuple must evaluate to FALSE",
    )

    @model_validator(mode="after")
    def _validate_condition_integrity(self) -> ConditionExpr:
        total_predicates = len(self.all_of) + len(self.any_of) + len(self.none_of)
        if total_predicates == 0:
            raise ValueError("ConditionExpr must not be empty. At least one predicate must be specified.")

        # Check for duplicates inside each clause
        if len(self.all_of) != len(set(self.all_of)):
            raise ValueError("ConditionExpr.all_of contains duplicate predicates.")
        if len(self.any_of) != len(set(self.any_of)):
            raise ValueError("ConditionExpr.any_of contains duplicate predicates.")
        if len(self.none_of) != len(set(self.none_of)):
            raise ValueError("ConditionExpr.none_of contains duplicate predicates.")

        # Check for direct logical contradiction between all_of and none_of
        contradictions = set(self.all_of) & set(self.none_of)
        if contradictions:
            names = ", ".join(p.value for p in sorted(contradictions, key=lambda x: x.value))
            raise ValueError(
                f"ConditionExpr has direct logical contradiction between all_of and none_of on: {names}."
            )

        return self


# ============================================================================
# 4. STATIC KNOWLEDGE ENTITY MODELS (DEEP IMMUTABLE)
# ============================================================================

class QuickTipKnowledge(BaseModel):
    """
    Static pedagogical knowledge entity describing an authoritative solving shortcut.
    Immutable, source-backed, bilingual, and linked to machine-readable conditions.
    Deeply immutable via tuple collections and frozen configuration.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
    )

    tip_id: str = Field(
        ...,
        description="Canonical uppercase ID (e.g. QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO)",
    )
    title: LocalizedText = Field(
        ...,
        description="Bilingual title of the quick tip",
    )
    summary: LocalizedText = Field(
        ...,
        description="Concise pedagogical summary of the shortcut",
    )
    category: TipCategory = Field(
        ...,
        description="Taxonomic classification of the shortcut",
    )

    # Machine-Readable Condition Authority
    applicability_condition: ConditionExpr = Field(
        ...,
        description="Closed deterministic condition expression required for mathematical validity",
    )

    # Recognition & Mathematical Foundation
    recognition_guidance: LocalizedText = Field(
        ...,
        description="Static pedagogical explanation of how a student identifies when to consider this tip",
    )
    explanation: LocalizedText = Field(
        ...,
        description="Rigorous mathematical explanation and proof of why the shortcut is correct",
    )
    quick_steps: tuple[LocalizedText, ...] = Field(
        ...,
        description="Ordered sequence of execution steps when applying this tip",
    )

    # Domain Boundaries & Safety
    valid_scope: LocalizedText = Field(
        ...,
        description="Explicit mathematical domain and conditions where this shortcut is strictly valid",
    )
    invalid_scope: LocalizedText = Field(
        ...,
        description="Explicit boundary cases, caveats, and common misconceptions where this tip is INVALID",
    )

    # Relational Graph Foreign Keys
    related_method_ids: tuple[str, ...] = Field(
        default=(),
        description="Canonical method IDs related to this shortcut (e.g. QUAD_VIETE_SPECIAL_SUM)",
    )
    related_concept_ids: tuple[str, ...] = Field(
        default=(),
        description="Prerequisite ConceptKnowledge IDs",
    )
    formula_refs: tuple[str, ...] = Field(
        default=(),
        description="Referenced FormulaKnowledge IDs",
    )
    theorem_refs: tuple[str, ...] = Field(
        default=(),
        description="Referenced TheoremKnowledge IDs",
    )
    related_problem_form_ids: tuple[str, ...] = Field(
        default=(),
        description="Problem forms where this shortcut is applicable or candidate",
    )

    # Provenance & Curriculum
    curriculum_refs: tuple[CurriculumRef, ...] = Field(
        default=(),
        description="National curriculum standards mapping with source_locator",
    )
    provenance_refs: tuple[str, ...] = Field(
        ...,
        description="List of authoritative source IDs in centralized provenance.json",
    )

    status: KnowledgeEntityStatus = Field(
        default=KnowledgeEntityStatus.PROVISIONAL,
        description="Entity governance status (defaults to PROVISIONAL for fail-closed governance)",
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version string of the entity (e.g. '1.0.0')",
    )

    @model_validator(mode="after")
    def _validate_quick_tip_integrity(self) -> QuickTipKnowledge:
        # tip_id format validation
        if not CANONICAL_ID_REGEX.match(self.tip_id):
            raise ValueError(f"tip_id '{self.tip_id}' is invalid. Must match pattern '^[A-Z][A-Z0-9_]*$'.")

        # quick_steps must not be empty
        if len(self.quick_steps) == 0:
            raise ValueError("quick_steps must contain at least one step procedure.")

        # provenance_refs validation
        if len(self.provenance_refs) == 0:
            raise ValueError("provenance_refs must contain at least one source provenance reference.")
        _validate_id_sequence(self.provenance_refs, "provenance_refs")

        # relation ID sequence hygiene
        _validate_id_sequence(self.related_method_ids, "related_method_ids")
        _validate_id_sequence(self.related_concept_ids, "related_concept_ids")
        _validate_id_sequence(self.formula_refs, "formula_refs")
        _validate_id_sequence(self.theorem_refs, "theorem_refs")
        _validate_id_sequence(self.related_problem_form_ids, "related_problem_form_ids")

        # version format validation
        if not SEMVER_REGEX.match(self.version):
            raise ValueError(f"version '{self.version}' is invalid. Must follow 'MAJOR.MINOR.PATCH' format (e.g. '1.0.0').")

        return self


class RelatedProblemFormKnowledge(BaseModel):
    """
    Static pedagogical entity defining a problem archetype / form (Dạng bài).
    Deeply immutable via tuple collections and frozen configuration.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
    )

    form_id: str = Field(
        ...,
        description="Unique canonical form identifier (e.g. QUAD_FORM_SPECIAL_SUM_ZERO)",
    )
    title: LocalizedText = Field(
        ...,
        description="Bilingual title of the problem form",
    )
    summary: LocalizedText = Field(
        ...,
        description="Pedagogical description of the problem form",
    )
    canonical_structure_latex: str = Field(
        ...,
        description="Generalized LaTeX template (e.g. 'ax^2 + bx + c = 0 \\quad (a + b + c = 0)')",
    )
    recognition_condition: ConditionExpr = Field(
        ...,
        description="Closed deterministic condition expression for mathematical classification",
    )
    recognition_guidance: LocalizedText = Field(
        ...,
        description="Pedagogical clues for students to recognize this form",
    )

    # Strategy & Tool Connections (Distinct Semantics)
    related_method_ids: tuple[str, ...] = Field(
        default=(),
        description="Methods conceptually related or applicable to this form",
    )
    guaranteed_method_ids: tuple[str, ...] = Field(
        default=(),
        description="Methods mathematically guaranteed to solve all equations of this form",
    )
    related_tip_ids: tuple[str, ...] = Field(
        default=(),
        description="Candidate quick tips worth evaluating at runtime for instances of this form",
    )
    guaranteed_tip_ids: tuple[str, ...] = Field(
        default=(),
        description="Quick tips mathematically guaranteed by this form's recognition condition",
    )

    # Foundations
    prerequisite_concept_ids: tuple[str, ...] = Field(
        default=(),
        description="Prerequisite concept IDs",
    )
    formula_refs: tuple[str, ...] = Field(
        default=(),
        description="Formula IDs used when solving this form",
    )
    theorem_refs: tuple[str, ...] = Field(
        default=(),
        description="Theorem IDs supporting this form",
    )

    # Curated Example Reference Placeholders (Deferred Policy)
    worked_example_ids: tuple[str, ...] = Field(
        default=(),
        description="Stable IDs to curated worked examples (MUST be empty in K1-02 until Example Registry exists)",
    )
    practice_example_ids: tuple[str, ...] = Field(
        default=(),
        description="Stable IDs to curated practice problems (MUST be empty in K1-02 until Example Registry exists)",
    )

    # Curriculum & Governance
    curriculum_refs: tuple[CurriculumRef, ...] = Field(
        default=(),
        description="Curriculum standards references with source_locator",
    )
    provenance_refs: tuple[str, ...] = Field(
        ...,
        description="Authoritative source provenance IDs in centralized provenance.json",
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.BASIC,
        description="Relative pedagogical difficulty",
    )
    status: KnowledgeEntityStatus = Field(
        default=KnowledgeEntityStatus.PROVISIONAL,
        description="Entity governance status (defaults to PROVISIONAL for fail-closed governance)",
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version string of the entity (e.g. '1.0.0')",
    )

    @model_validator(mode="after")
    def _validate_problem_form_integrity(self) -> RelatedProblemFormKnowledge:
        # form_id format validation
        if not CANONICAL_ID_REGEX.match(self.form_id):
            raise ValueError(f"form_id '{self.form_id}' is invalid. Must match pattern '^[A-Z][A-Z0-9_]*$'.")

        # canonical_structure_latex must not be empty
        if not self.canonical_structure_latex.strip():
            raise ValueError("canonical_structure_latex must not be empty or whitespace.")

        # provenance_refs validation
        if len(self.provenance_refs) == 0:
            raise ValueError("provenance_refs must contain at least one source provenance reference.")
        _validate_id_sequence(self.provenance_refs, "provenance_refs")

        # relation ID sequence hygiene
        _validate_id_sequence(self.related_method_ids, "related_method_ids")
        _validate_id_sequence(self.guaranteed_method_ids, "guaranteed_method_ids")
        _validate_id_sequence(self.related_tip_ids, "related_tip_ids")
        _validate_id_sequence(self.guaranteed_tip_ids, "guaranteed_tip_ids")
        _validate_id_sequence(self.prerequisite_concept_ids, "prerequisite_concept_ids")
        _validate_id_sequence(self.formula_refs, "formula_refs")
        _validate_id_sequence(self.theorem_refs, "theorem_refs")
        _validate_id_sequence(self.worked_example_ids, "worked_example_ids")
        _validate_id_sequence(self.practice_example_ids, "practice_example_ids")

        # version format validation
        if not SEMVER_REGEX.match(self.version):
            raise ValueError(f"version '{self.version}' is invalid. Must follow 'MAJOR.MINOR.PATCH' format (e.g. '1.0.0').")

        return self


# ============================================================================
# 5. DYNAMIC RUNTIME ASSESSMENT CONTRACT DTOs (DEEP IMMUTABLE)
# ============================================================================

def _validate_predicate_partition(
    matched: Sequence[PredicateId],
    failed: Sequence[PredicateId],
    unknown: Sequence[PredicateId],
) -> None:
    """Validates that predicate evidence sequences are disjoint and contain no internal duplicates."""
    # Check internal sequence duplicates
    if len(matched) != len(set(matched)):
        raise ValueError("matched_predicates contains duplicate predicates.")
    if len(failed) != len(set(failed)):
        raise ValueError("failed_predicates contains duplicate predicates.")
    if len(unknown) != len(set(unknown)):
        raise ValueError("unknown_predicates contains duplicate predicates.")

    # Check cross-sequence overlap
    set_m = set(matched)
    set_f = set(failed)
    set_u = set(unknown)

    overlap_mf = set_m & set_f
    if overlap_mf:
        names = ", ".join(p.value for p in sorted(overlap_mf, key=lambda x: x.value))
        raise ValueError(f"Contradictory evidence: Predicates present in both matched and failed: {names}.")

    overlap_mu = set_m & set_u
    if overlap_mu:
        names = ", ".join(p.value for p in sorted(overlap_mu, key=lambda x: x.value))
        raise ValueError(f"Contradictory evidence: Predicates present in both matched and unknown: {names}.")

    overlap_fu = set_f & set_u
    if overlap_fu:
        names = ", ".join(p.value for p in sorted(overlap_fu, key=lambda x: x.value))
        raise ValueError(f"Contradictory evidence: Predicates present in both failed and unknown: {names}.")


class QuickTipAssessmentView(BaseModel):
    """
    Runtime assessment DTO representing the evaluation of a quick tip against a specific normalized equation.
    Immutable, strictly typed, with disjoint evidence partition validation and deep immutability.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
    )

    tip_id: str = Field(..., description="Target tip identifier")
    mathematical_applicability: TipApplicability = Field(..., description="Objective mathematical applicability")
    pedagogical_recommendation: TipRecommendation = Field(..., description="Pedagogical recommendation state")
    execution_availability: TipExecutionAvailability = Field(..., description="Backend execution availability")
    matched_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to TRUE")
    failed_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to FALSE")
    unknown_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to UNKNOWN")
    reason_codes: tuple[str, ...] = Field(default=(), description="Canonical deterministic reason codes")

    @model_validator(mode="after")
    def _validate_assessment_integrity(self) -> QuickTipAssessmentView:
        if not CANONICAL_ID_REGEX.match(self.tip_id):
            raise ValueError(f"tip_id '{self.tip_id}' is invalid. Must match pattern '^[A-Z][A-Z0-9_]*$'.")

        _validate_predicate_partition(self.matched_predicates, self.failed_predicates, self.unknown_predicates)
        _validate_id_sequence(self.reason_codes, "reason_codes")
        return self


class ProblemFormAssessmentView(BaseModel):
    """
    Runtime assessment DTO representing the evaluation of a problem archetype against a specific equation.
    Immutable, strictly typed, with disjoint evidence partition validation and deep immutability.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
    )

    form_id: str = Field(..., description="Target form identifier")
    mathematical_match: FormMatchStatus = Field(..., description="Whether equation matches this form archetype")
    matched_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to TRUE")
    failed_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to FALSE")
    unknown_predicates: tuple[PredicateId, ...] = Field(default=(), description="Predicates that evaluated to UNKNOWN")
    reason_codes: tuple[str, ...] = Field(default=(), description="Canonical deterministic reason codes")

    @model_validator(mode="after")
    def _validate_assessment_integrity(self) -> ProblemFormAssessmentView:
        if not CANONICAL_ID_REGEX.match(self.form_id):
            raise ValueError(f"form_id '{self.form_id}' is invalid. Must match pattern '^[A-Z][A-Z0-9_]*$'.")

        _validate_predicate_partition(self.matched_predicates, self.failed_predicates, self.unknown_predicates)
        _validate_id_sequence(self.reason_codes, "reason_codes")
        return self
