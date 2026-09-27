"""Typed, immutable results and mathematical evidence for linear equation solving."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict, Any

from ..core.rational import Rational
from ..parser.ast import Equation
from ..parser.errors import Span
from ..evaluator.result import CandidateCheckResult


class SolutionClassification(str, Enum):
    """Deterministic mathematical solution outcome for in-scope linear equations."""
    UNIQUE_ROOT = "UNIQUE_ROOT"
    ALL_REALS = "DomainSet(R)"
    NO_SOLUTION = "EmptySet"

    # Semantic aliases
    DOMAIN_SET_R = "DomainSet(R)"
    EMPTY_SET = "EmptySet"


class SolverScopeStatus(str, Enum):
    """Scope and verification outcome taxonomy for equation solving."""
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    DOMAIN_ERROR = "DOMAIN_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INTERNAL_VERIFICATION_FAILURE = "INTERNAL_VERIFICATION_FAILURE"


@dataclass(frozen=True, slots=True)
class SolverEvidence:
    """Deterministic, typed provisional mathematical evidence for solved equations."""
    equation_str: str
    left_affine: Optional[Tuple[Rational, Rational]] = None
    right_affine: Optional[Tuple[Rational, Rational]] = None
    normalized_a: Optional[Rational] = None
    normalized_b: Optional[Rational] = None
    classification: Optional[SolutionClassification] = None
    root: Optional[Rational] = None
    candidate_check: Optional[CandidateCheckResult] = None
    step_trace: Tuple[Tuple[str, str], ...] = ()
    diagnostics: Tuple[Tuple[str, str], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equation_str": self.equation_str,
            "left_affine": (
                (self.left_affine[0].to_dict(), self.left_affine[1].to_dict())
                if self.left_affine is not None else None
            ),
            "right_affine": (
                (self.right_affine[0].to_dict(), self.right_affine[1].to_dict())
                if self.right_affine is not None else None
            ),
            "normalized_a": self.normalized_a.to_dict() if self.normalized_a is not None else None,
            "normalized_b": self.normalized_b.to_dict() if self.normalized_b is not None else None,
            "classification": self.classification.value if self.classification is not None else None,
            "root": self.root.to_dict() if self.root is not None else None,
            "candidate_check": self.candidate_check.to_dict() if self.candidate_check is not None else None,
            "step_trace": [list(item) for item in self.step_trace],
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True, slots=True)
class SolverResult:
    """Typed, immutable outcome of solving a mathematical equation.

    Fields:
        status: Scope and execution status (IN_SCOPE, OUT_OF_SCOPE, DOMAIN_ERROR, etc.).
        equation: The original, unmodified Equation AST.
        classification: Solution classification if in-scope (UNIQUE_ROOT, DomainSet(R), EmptySet).
        root: Exact rational root if classification is UNIQUE_ROOT, else None.
        error_code: Deterministic error code string if out-of-scope or failure, else None.
        error_message: Human-readable diagnostic explanation, or None.
        error_span: Offending source span if error occurred, else None.
        evidence: Structured mathematical evidence payload, or None.
    """
    status: SolverScopeStatus
    equation: Equation
    classification: Optional[SolutionClassification] = None
    root: Optional[Rational] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_span: Optional[Span] = None
    evidence: Optional[SolverEvidence] = None

    @property
    def is_solved(self) -> bool:
        """True if the equation was successfully solved within in-scope linear domain."""
        return self.status == SolverScopeStatus.IN_SCOPE

    @property
    def is_unique_root(self) -> bool:
        """True if the equation has a unique root."""
        return self.classification == SolutionClassification.UNIQUE_ROOT

    @property
    def is_all_reals(self) -> bool:
        """True if every real number satisfies the equation (0*x = 0)."""
        return self.classification == SolutionClassification.ALL_REALS

    @property
    def is_empty_set(self) -> bool:
        """True if no real number satisfies the equation (0*x = c with c != 0)."""
        return self.classification == SolutionClassification.NO_SOLUTION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "classification": self.classification.value if self.classification is not None else None,
            "root": self.root.to_dict() if self.root is not None else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_span": self.error_span.to_tuple() if self.error_span is not None else None,
            "evidence": self.evidence.to_dict() if self.evidence is not None else None,
        }
