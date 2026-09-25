"""Mathematical Knowledge Base and Dataset Schemas for Math Knowledge Engine (MKE).

Defines typed Pydantic models for:
- Method Templates and Method Instances (M1 - M5 catalogue representation).
- Family Records with Split Groups and Cross-Family Dependencies.
- Problem Records preserving original expressions, AST, and domain.
- Method Annotations with strict admissibility decoupling.
- Transfer Pairs modeling source-target candidate transfers.
- Dataset Manifests and Validation Reports.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mke.models.enums import (
    MethodAdmissibility,
    MethodId,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    Split,
    TransferValidity,
)


class ReviewStatus(str, Enum):
    """Rigorous academic review status for knowledge base records and annotations.

    Levels:
    - PROVISIONAL: Generated / candidate annotation before independent expert audit.
    - CANDIDATE: Machine-checked and submitted for review.
    - REVIEWED_GOLD: Fully audited and approved by independent human domain expert.
    """
    PROVISIONAL = "PROVISIONAL"
    CANDIDATE = "CANDIDATE"
    REVIEWED_GOLD = "REVIEWED_GOLD"


class TransferCategory(str, Enum):
    """Categorization of problem variants and transfer relationships."""
    POSITIVE = "POSITIVE"
    METHOD_NEAR_MISS = "METHOD_NEAR_MISS"
    TRANSFER_NEAR_MISS = "TRANSFER_NEAR_MISS"
    BOUNDARY_CASE = "BOUNDARY_CASE"
    MULTI_METHOD = "MULTI_METHOD"
    INAPPLICABLE_INSTANCE = "INAPPLICABLE_INSTANCE"


class EquationClass(str, Enum):
    """Mathematical equation classifications in MKE scope."""
    LINEAR = "LINEAR"
    QUADRATIC = "QUADRATIC"
    FACTORIZATION = "FACTORIZATION"
    RATIONAL = "RATIONAL"
    BIQUADRATIC = "BIQUADRATIC"


class MethodTemplate(BaseModel):
    """General, abstract representation of an algebraic solving method template."""
    method_id: MethodId
    method_version: str = "1.0.0"
    name_vi: str
    name_en: str
    mathematical_scope: str
    structural_preconditions: List[str] = Field(default_factory=list)
    mathematical_preconditions: List[str] = Field(default_factory=list)
    required_proof_obligations: List[ObligationId] = Field(default_factory=list)
    parameterization_schema: Dict[str, Any] = Field(default_factory=dict)
    expected_transformation_type: str
    possible_failure_modes: List[str] = Field(default_factory=list)
    supported_equation_classes: List[EquationClass] = Field(default_factory=list)
    prerequisite_mathematical_concepts: List[str] = Field(default_factory=list)
    human_readable_explanation: str
    source_and_provenance: str = "DEV01_CORE_CATALOGUE"
    review_status: ReviewStatus = ReviewStatus.PROVISIONAL


class MethodInstance(BaseModel):
    """A method template instantiated with concrete parameters for a problem."""
    instance_id: str
    method_id: MethodId
    method_version: str = "1.0.0"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""


class FamilyRecord(BaseModel):
    """Metadata representing a seed family of related equation variants."""
    family_id: str
    name: str
    description: str
    equation_class: EquationClass
    split_group_id: str
    dependent_family_ids: List[str] = Field(default_factory=list)
    supported_methods: List[MethodId] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.PROVISIONAL


class ProblemRecord(BaseModel):
    """Complete research data record for an equation problem instance."""
    problem_id: str
    family_id: str
    variant_id: str
    split: Split = Split.DEV
    original_expression: str
    canonical_representation: str
    raw_ast: Dict[str, Any] = Field(default_factory=dict)
    domain_str: str = "R"
    excluded_points: List[str] = Field(default_factory=list)
    equation_class: EquationClass
    near_miss_category: TransferCategory = TransferCategory.POSITIVE
    expected_roots: Optional[List[str]] = None
    is_identity_on_domain: bool = False
    is_empty_domain: bool = False
    provenance: str = "DEV02A_PILOT_HANDCRAFTED"
    license_status: str = "CC-BY-4.0"
    review_status: ReviewStatus = ReviewStatus.PROVISIONAL


class MethodAnnotation(BaseModel):
    """Annotated relationship between a problem and a candidate method."""
    annotation_id: str
    problem_id: str
    method_id: MethodId
    method_version: str = "1.0.0"
    method_instance_id: Optional[str] = None
    admissibility: MethodAdmissibility = MethodAdmissibility.UNKNOWN
    structural_guards: List[Dict[str, Any]] = Field(default_factory=list)
    mathematical_guards: List[Dict[str, Any]] = Field(default_factory=list)
    proof_obligations: List[ObligationId] = Field(default_factory=list)
    explanation: str = ""
    annotation_evidence: str = ""
    review_status: ReviewStatus = ReviewStatus.PROVISIONAL
    provenance: str = "DEV02A_PILOT_ANNOTATION"


class TransferPairRecord(BaseModel):
    """Record modeling candidate transfer from a source problem to a target problem."""
    pair_id: str
    source_problem_id: str
    target_problem_id: str
    method_id: MethodId
    method_version: str = "1.0.0"
    proposed_method_instance: Optional[Dict[str, Any]] = None
    transfer_category: TransferCategory
    guard_obligations: List[ObligationId] = Field(default_factory=list)
    proposed_transfer_status: TransferValidity
    annotation_evidence: str
    review_status: ReviewStatus = ReviewStatus.PROVISIONAL
    provenance: str = "DEV02A_PILOT_TRANSFER"


class DatasetManifest(BaseModel):
    """Cryptographic and inventory manifest for dataset integrity."""
    manifest_version: str = "1.0.0"
    dataset_name: str
    split: Split = Split.DEV
    file_hashes: Dict[str, str] = Field(default_factory=dict)
    record_counts: Dict[str, int] = Field(default_factory=dict)
    schema_version: str = "2.0.0"
    created_at: str = ""
