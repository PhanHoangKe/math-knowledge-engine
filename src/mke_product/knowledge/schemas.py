"""MKE MVP V1 — S3 Knowledge Schemas.

Defines the Python Single Source of Truth (SSOT) data contracts for S3
Pedagogical Knowledge entities (Method, Concept, Formula, Theorem, Provenance).
All models use Pydantic v2 with strict validation, extra field rejection,
and immutability (frozen=True).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================================
# 1. LOCALIZATION & BASE VALUE OBJECTS
# ============================================================================

class LocalizedText(BaseModel):
    """Symmetric bilingual text container requiring explicit non-empty VI and EN content."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    vi: str = Field(..., description="Vietnamese text content")
    en: str = Field(..., description="English text content")

    @model_validator(mode="after")
    def _validate_non_empty(self) -> LocalizedText:
        if not self.vi.strip():
            raise ValueError("Vietnamese text content cannot be empty or whitespace only.")
        if not self.en.strip():
            raise ValueError("English text content cannot be empty or whitespace only.")
        return self


# ============================================================================
# 2. CURRICULUM & PROVENANCE SCHEMAS
# ============================================================================

class CurriculumMappingStatus(str, Enum):
    """Verification status of curriculum alignment mapping."""

    VERIFIED_MAPPING = "VERIFIED_MAPPING"
    PROVISIONAL_MAPPING = "PROVISIONAL_MAPPING"


class CurriculumRef(BaseModel):
    """Authoritative curriculum standard reference with explicit verification status."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    framework: str = Field(..., description="Curriculum framework code, e.g. 'GDPT_2018', 'CCSS', 'IB'")
    subject: str = Field(..., description="Subject identifier, e.g. 'TOAN'")
    grade_band: str = Field(..., description="Grade level identifier, e.g. 'GRADE_9'")
    topic: str = Field(..., description="Curriculum topic code, e.g. 'PHUONG_TRINH_BAC_HAI_MOT_AN'")
    competency_ref: Optional[str] = Field(default=None, description="Specific standard code if verified")
    source_document: str = Field(..., description="Authoritative document title or circular")
    source_locator: str = Field(..., description="Chapter, section, or article locator")
    status: CurriculumMappingStatus = Field(..., description="Explicit mapping verification status")


class ProvenanceStatus(str, Enum):
    """Verification status of source provenance citation."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class SourceProvenance(BaseModel):
    """Traceable citation or academic source in centralized provenance registry."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    source_id: str = Field(..., description="Stable unique identifier, e.g. 'SRC_MKE_S1_ORCHESTRATOR'")
    source_type: str = Field(..., description="Source category, e.g. 'ENGINE_SPEC', 'TEXTBOOK', 'OFFICIAL_CURRICULUM'")
    title: str = Field(..., description="Title of source document or specification")
    author_or_institution: str = Field(..., description="Author, publisher, or institution")
    publication_year: Optional[int] = Field(default=None, description="Year of publication if applicable")
    locator: str = Field(..., description="Specific page, chapter, section, or module path locator")
    verification_status: ProvenanceStatus = Field(..., description="Explicit verification status")


# ============================================================================
# 3. STATIC KNOWLEDGE ENTITY MODELS
# ============================================================================

class FormulaKnowledge(BaseModel):
    """Canonical mathematical formula entity with exact LaTeX template."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    formula_id: str = Field(..., description="Stable unique formula identifier, e.g. 'FORMULA_QUADRATIC_STANDARD'")
    title: LocalizedText
    latex_template: str = Field(..., description="LaTeX representation of formula")
    variables_description: Dict[str, LocalizedText] = Field(default_factory=dict)
    domain_conditions: LocalizedText
    related_concept_ids: List[str] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")


class TheoremKnowledge(BaseModel):
    """Mathematical theorem entity with formal hypotheses and conclusions."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    theorem_id: str = Field(..., description="Stable unique theorem identifier, e.g. 'THEOREM_VIETA_RELATIONS'")
    title: LocalizedText
    statement: LocalizedText
    formal_statement_latex: str = Field(..., description="Formal mathematical statement in LaTeX")
    hypotheses: List[LocalizedText] = Field(default_factory=list)
    conclusions: List[LocalizedText] = Field(default_factory=list)
    related_concept_ids: List[str] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")


class ConceptKnowledge(BaseModel):
    """Mathematical concept definition across algebra, geometry, and calculus."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    concept_id: str = Field(..., description="Stable snake_case concept identifier, e.g. 'concept_discriminant'")
    title: LocalizedText
    definition: LocalizedText
    prerequisite_concept_ids: List[str] = Field(default_factory=list)
    related_concept_ids: List[str] = Field(default_factory=list)
    formula_refs: List[str] = Field(default_factory=list)
    method_refs: List[str] = Field(default_factory=list)
    curriculum_refs: List[CurriculumRef] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")


class MethodKnowledge(BaseModel):
    """Static epistemological and pedagogical definition of a solution method.

    Contains zero equation-specific state (no discriminant, no roots, no runtime applicability).
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    method_id: str = Field(..., description="Foreign key matching canonical string method_id in MethodRegistry")
    title: LocalizedText
    summary: LocalizedText
    learning_objective: LocalizedText
    formal_description: LocalizedText
    applicability_guidance: List[LocalizedText] = Field(default_factory=list)
    non_applicability_guidance: List[LocalizedText] = Field(default_factory=list)
    prerequisite_concept_ids: List[str] = Field(default_factory=list)
    formula_refs: List[str] = Field(default_factory=list)
    theorem_refs: List[str] = Field(default_factory=list)
    common_mistakes: List[LocalizedText] = Field(default_factory=list)
    diagnostic_tips: List[LocalizedText] = Field(default_factory=list)
    related_method_ids: List[str] = Field(default_factory=list)
    curriculum_refs: List[CurriculumRef] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
