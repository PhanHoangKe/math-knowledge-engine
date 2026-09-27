"""Typed exception hierarchy for the MKE Product linear equation solver."""

from typing import Optional
from ..core.errors import MKEProductError
from ..parser.errors import Span


class SolverError(MKEProductError):
    """Base exception for all linear solver errors and scope failures."""

    def __init__(self, message: str, code: str, span: Optional[Span] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.span = span

    def __str__(self) -> str:
        span_str = f"[{self.span.start}:{self.span.end}] " if self.span is not None else ""
        return f"{span_str}({self.code}) {self.message}"


class OutOfScopeError(SolverError):
    """Raised when an equation contains structures outside the P02A linear solver scope."""
    pass


class OutOfScopeVariableExponentZeroError(OutOfScopeError):
    """Raised when a variable-dependent base is raised to exponent 0."""

    def __init__(
        self,
        message: str = "Variable-dependent base raised to exponent zero is out of scope for solver.",
        span: Optional[Span] = None,
    ) -> None:
        super().__init__(message, code="OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO", span=span)


class OutOfScopeNonlinearError(OutOfScopeError):
    """Raised when quadratic or higher-degree terms, or variable products are present."""

    def __init__(
        self,
        message: str = "Nonlinear expression or variable multiplication is out of scope for linear solver.",
        span: Optional[Span] = None,
    ) -> None:
        super().__init__(message, code="OUT_OF_SCOPE_NONLINEAR", span=span)


class OutOfScopeRationalFractionError(OutOfScopeError):
    """Raised when a denominator contains the variable x."""

    def __init__(
        self,
        message: str = "Variable-dependent denominator is out of scope for linear solver.",
        span: Optional[Span] = None,
    ) -> None:
        super().__init__(message, code="OUT_OF_SCOPE_RATIONAL_FRACTION", span=span)
