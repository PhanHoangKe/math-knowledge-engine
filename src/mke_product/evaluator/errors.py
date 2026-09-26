"""Typed error hierarchy for exact AST evaluation and candidate verification."""

from typing import Optional
from ..core.errors import MKEProductError
from ..parser.errors import Span


class EvaluationError(MKEProductError):
    """Base exception for all AST evaluation and domain safety failures."""

    def __init__(self, message: str, code: str, span: Optional[Span] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.span = span

    def __str__(self) -> str:
        span_str = f"[{self.span.start}:{self.span.end}] " if self.span is not None else ""
        return f"{span_str}({self.code}) {self.message}"


class DomainError(EvaluationError):
    """Base exception for original-domain undefinedness at a given candidate."""
    pass


class ZeroDenominatorEvaluationError(DomainError):
    """Raised when an expression evaluates to a zero denominator in the original AST."""

    def __init__(self, message: str = "Denominator evaluates to zero in original unreduced expression.", span: Optional[Span] = None) -> None:
        super().__init__(message, code="DOMAIN_ERROR_DIVISION_BY_ZERO", span=span)


class UndefinedZeroToZeroError(DomainError):
    """Raised when an expression evaluates to 0^0, which is undefined in the Real domain."""

    def __init__(self, message: str = "0^0 is undefined in Real domain according to frozen Product convention.", span: Optional[Span] = None) -> None:
        super().__init__(message, code="DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO", span=span)


class EvaluationResourceLimitError(EvaluationError):
    """Raised when evaluation operation count or intermediate integer bit length exceeds budget."""

    def __init__(self, message: str, code: str = "ERR_RESOURCE_EXHAUSTED", span: Optional[Span] = None) -> None:
        super().__init__(message, code=code, span=span)


class UnsupportedEvaluationError(EvaluationError):
    """Raised when encountering an AST node, variable, or construct unsupported by the P02A evaluator."""

    def __init__(self, message: str, code: str = "ERR_UNSUPPORTED_EVALUATION", span: Optional[Span] = None) -> None:
        super().__init__(message, code=code, span=span)


class InvalidCandidateError(EvaluationError, TypeError, ValueError):
    """Raised when a candidate value is malformed or has a forbidden non-exact type (e.g. float)."""

    def __init__(self, message: str, code: str = "ERR_INVALID_CANDIDATE", span: Optional[Span] = None) -> None:
        super().__init__(message, code=code, span=span)
