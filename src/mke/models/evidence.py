"""Evidence, guards, obligations, and verification models."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mke.models.enums import (
    ExactVerificationStatus,
    MethodAdmissibility,
    MethodId,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    TransferValidity,
)


class GuardResult(BaseModel):
    """Result of checking a structural or mathematical guard."""

    guard_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ExactProofCertificate(BaseModel):
    """Rigorous certificate verifying whether a candidate root satisfies an equation."""

    status: ExactVerificationStatus
    is_exact_pass: bool
    candidate_root: str
    residue: str
    method: str
    diagnostic: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class CompletenessCertificate(BaseModel):
    """Structured certificate verifying completeness of a solution set."""

    certificate_id: str
    algorithm: str
    polynomial_degree: int
    coefficients: Dict[str, str] = Field(default_factory=dict)
    canonical_roots: List[str] = Field(default_factory=list)
    verified_roots: List[str] = Field(default_factory=list)
    missing_roots: List[str] = Field(default_factory=list)
    extraneous_roots: List[str] = Field(default_factory=list)
    status: ObligationStatus
    details: Dict[str, Any] = Field(default_factory=dict)


class ProofObligation(BaseModel):
    """Evaluation record of a mathematical proof obligation."""

    obligation_id: ObligationId
    status: ObligationStatus
    description: str
    evidence: str
    counterexample: Optional[str] = None
    certificate: Optional[Dict[str, Any]] = None


class SolutionCandidate(BaseModel):
    """Evaluation of an individual candidate root."""

    value_str: str
    in_domain: bool
    satisfies_equation: bool
    is_valid_root: bool
    evidence: str
    exact_status: Optional[ExactVerificationStatus] = None


class MethodInstance(BaseModel):
    """Instantiation of a method on a concrete equation instance."""

    method_id: MethodId
    version: str
    equation_raw: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    structural_guards: List[GuardResult] = Field(default_factory=list)
    mathematical_guards: List[GuardResult] = Field(default_factory=list)
    admissibility: MethodAdmissibility = MethodAdmissibility.UNKNOWN
    admissibility_reason: str = ""


class VerificationResult(BaseModel):
    """Comprehensive verification output for an equation and method."""

    problem_raw: str
    domain_str: str
    is_all_reals_domain: bool
    excluded_points: List[str] = Field(default_factory=list)
    normalization_trace: List[str] = Field(default_factory=list)

    method_instance: Optional[MethodInstance] = None
    is_verified_method: bool = False
    is_verified_solution: bool = False

    solution_status: SolutionProofStatus = SolutionProofStatus.UNDETERMINED
    candidate_solutions: List[SolutionCandidate] = Field(default_factory=list)
    verified_roots: List[str] = Field(default_factory=list)
    unverified_candidates: List[str] = Field(default_factory=list)
    is_identity_on_domain: bool = False  # e.g., (x-2)/(x-2)=1 holds for all x in Domain

    obligations: List[ProofObligation] = Field(default_factory=list)
    completeness_certificate: Optional[CompletenessCertificate] = None
    transfer_validity: Optional[TransferValidity] = None
    counterexample: Optional[str] = None
    explanation: str = ""

    def summary(self) -> str:
        status_line = (
            f"Method Verified: {self.is_verified_method} | "
            f"Solution Verified: {self.is_verified_solution} | "
            f"Status: {self.solution_status.value}"
        )
        domain_line = f"Domain: {self.domain_str}"
        sol_line = f"Roots: {{{', '.join(self.verified_roots)}}}" if not self.is_identity_on_domain else f"Roots: All x in {self.domain_str}"
        return f"{status_line}\n{domain_line}\n{sol_line}\nExplanation: {self.explanation}"
