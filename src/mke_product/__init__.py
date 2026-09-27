"""MKE Product root package."""

from .core.rational import Rational
from .parser.parser import parse_equation, parse_expression
from .evaluator import (
    evaluate_expression,
    check_candidate,
    extract_domain_obligations,
    CandidateCheckResult,
    CandidateCheckStatus,
    EvaluationBudget,
)
from .solver import (
    solve_equation,
    SolverResult,
    SolverScopeStatus,
    SolutionClassification,
    SolverEvidence,
    AffineForm,
)

__version__ = "0.2.0-s3"

__all__ = [
    "Rational",
    "parse_equation",
    "parse_expression",
    "evaluate_expression",
    "check_candidate",
    "extract_domain_obligations",
    "CandidateCheckResult",
    "CandidateCheckStatus",
    "EvaluationBudget",
    "solve_equation",
    "SolverResult",
    "SolverScopeStatus",
    "SolutionClassification",
    "SolverEvidence",
    "AffineForm",
]
