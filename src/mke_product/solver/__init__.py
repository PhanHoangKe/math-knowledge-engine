"""MKE Product linear equation solver package."""

from .errors import (
    SolverError,
    OutOfScopeError,
    OutOfScopeVariableExponentZeroError,
    OutOfScopeNonlinearError,
    OutOfScopeRationalFractionError,
)
from .result import (
    SolutionClassification,
    SolverScopeStatus,
    SolverEvidence,
    SolverResult,
)
from .affine import AffineForm, extract_affine
from .scope import check_equation_scope, contains_variable
from .solver import solve_equation

__all__ = [
    "SolverError",
    "OutOfScopeError",
    "OutOfScopeVariableExponentZeroError",
    "OutOfScopeNonlinearError",
    "OutOfScopeRationalFractionError",
    "SolutionClassification",
    "SolverScopeStatus",
    "SolverEvidence",
    "SolverResult",
    "AffineForm",
    "extract_affine",
    "check_equation_scope",
    "contains_variable",
    "solve_equation",
]
