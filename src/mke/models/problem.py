"""Problem record and dataset schema for Math Knowledge Engine."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mke.models.enums import (
    MethodAdmissibility,
    MethodId,
    SolutionProofStatus,
    Split,
    TransferValidity,
)
from mke.models.evidence import (
    GuardResult,
    MethodInstance,
    ProofObligation,
    SolutionCandidate,
)


class ProblemRecord(BaseModel):
    """Complete research data record for an equation problem instance."""

    # Identifiers and Partition
    family_id: str
    problem_id: str
    split: Split = Split.DEV

    # Raw Inputs and Unreduced Representations
    raw_input: str
    raw_ast: Dict[str, Any]

    # Domain Preservation
    domain_conditions: List[Dict[str, Any]] = Field(default_factory=list)
    domain_str: str = "R"
    excluded_points: List[str] = Field(default_factory=list)

    # Normalization Trace
    normalization_trace: List[str] = Field(default_factory=list)

    # Method Association
    method_id: Optional[MethodId] = None
    method_version: Optional[str] = None
    instantiation: Optional[Dict[str, Any]] = None

    # Guards and Admissibility
    structural_guards: List[GuardResult] = Field(default_factory=list)
    mathematical_guards: List[GuardResult] = Field(default_factory=list)
    admissibility: MethodAdmissibility = MethodAdmissibility.UNKNOWN

    # Proof Obligations and Evidence
    obligations: List[ProofObligation] = Field(default_factory=list)

    # Evaluation Labels
    is_verified_method: bool = False
    is_verified_solution: bool = False
    transfer_validity: Optional[TransferValidity] = None
    solution_status: SolutionProofStatus = SolutionProofStatus.UNDETERMINED

    # Solution Details
    exact_solution: Optional[List[str]] = None
    is_identity_on_domain: bool = False
    candidate_solutions: List[SolutionCandidate] = Field(default_factory=list)

    # Rigorous Explanations and Auditing
    completeness_explanation: str = ""
    counterexample: Optional[str] = None
    reviewer_log: List[str] = Field(default_factory=list)
    provenance: str = "DEV01_SYNTHETIC_SUITE"
    license_status: str = "CC-BY-4.0"
