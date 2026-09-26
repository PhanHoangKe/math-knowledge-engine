"""Typed, immutable results and obligations for candidate verification."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Dict, Any

from ..core.rational import Rational
from ..parser.ast import ASTNode, Equation
from ..parser.errors import Span


class CandidateCheckStatus(str, Enum):
    """Deterministic outcome taxonomy for candidate verification."""
    VALID = "VALID"
    INVALID = "INVALID"
    DOMAIN_ERROR = "DOMAIN_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class DomainObligation:
    """A symbolic domain obligation extracted from the original AST."""
    kind: str  # "NONZERO_DENOMINATOR" | "NONZERO_EXPONENT_BASE"
    target_ast: ASTNode
    span: Span
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "span": self.span.to_tuple(),
            "description": self.description,
            "target_ast": self.target_ast.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CandidateCheckResult:
    """Typed, immutable result of evaluating an exact rational candidate against an Equation.

    Fields:
        status: The check status (VALID, INVALID, DOMAIN_ERROR, RESOURCE_EXHAUSTED, UNSUPPORTED).
        candidate: The exact rational candidate c tested (or None if candidate coercion failed due to resource limits).
        equation: The original, unmodified Equation AST.
        left_value: Exact rational value of L(c), or None if undefined or error.
        right_value: Exact rational value of R(c), or None if undefined or error.
        error_code: Exact error code string if domain/resource error occurred, else None.
        error_message: Human-readable diagnostic explanation, or None.
        error_span: Source span of the offending AST node where failure occurred, else None.
        diagnostics: Immutable tuple of diagnostic key-value pairs.
    """
    status: CandidateCheckStatus
    candidate: Optional[Rational]
    equation: Equation
    left_value: Optional[Rational] = None
    right_value: Optional[Rational] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_span: Optional[Span] = None
    diagnostics: Tuple[Tuple[str, str], ...] = ()

    @property
    def is_valid(self) -> bool:
        """True if and only if both sides are well-defined and exactly equal in Q."""
        return self.status == CandidateCheckStatus.VALID

    @property
    def is_defined(self) -> Optional[bool]:
        """Explicit three-valued definedness contract:

        - True: The equation is mathematically well-defined at candidate c (status in {VALID, INVALID}).
        - False: Proven mathematical domain violation at candidate c (status == DOMAIN_ERROR).
        - None: Epistemically UNKNOWN due to evaluation resource exhaustion or unsupported constructs
                (status in {RESOURCE_EXHAUSTED, UNSUPPORTED}).
        """
        if self.status in (CandidateCheckStatus.VALID, CandidateCheckStatus.INVALID):
            return True
        if self.status == CandidateCheckStatus.DOMAIN_ERROR:
            return False
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic inspection dictionary (provisional non-normative format)."""
        return {
            "status": self.status.value,
            "candidate": self.candidate.to_dict() if self.candidate is not None else None,
            "is_valid": self.is_valid,
            "is_defined": self.is_defined,
            "left_value": self.left_value.to_dict() if self.left_value is not None else None,
            "right_value": self.right_value.to_dict() if self.right_value is not None else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_span": self.error_span.to_tuple() if self.error_span is not None else None,
            "diagnostics": dict(self.diagnostics),
        }
