"""Exact semantic evaluator and candidate verifier package."""

from .errors import (
    EvaluationError,
    DomainError,
    ZeroDenominatorEvaluationError,
    UndefinedZeroToZeroError,
    EvaluationResourceLimitError,
    UnsupportedEvaluationError,
    InvalidCandidateError,
)
from .budget import EvaluationBudget
from .result import (
    CandidateCheckStatus,
    CandidateCheckResult,
    DomainObligation,
)
from .evaluator import (
    coerce_candidate,
    evaluate_expression,
    extract_domain_obligations,
    check_candidate,
)

__all__ = [
    "EvaluationError",
    "DomainError",
    "ZeroDenominatorEvaluationError",
    "UndefinedZeroToZeroError",
    "EvaluationResourceLimitError",
    "UnsupportedEvaluationError",
    "InvalidCandidateError",
    "EvaluationBudget",
    "CandidateCheckStatus",
    "CandidateCheckResult",
    "DomainObligation",
    "coerce_candidate",
    "evaluate_expression",
    "extract_domain_obligations",
    "check_candidate",
]
