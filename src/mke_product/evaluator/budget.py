"""Evaluation budget and resource limits for deterministic exact evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationBudget:
    """Explicit, conservative resource budgets for AST evaluation and candidate checking.
    
    Attributes:
        max_operations: Maximum number of AST node visits / evaluation steps.
        max_integer_bits: Maximum bit length of intermediate rational numerators and denominators.
        max_candidate_bits: Maximum bit length of supplied rational candidate components.
    """
    max_operations: int = 10_000
    max_integer_bits: int = 4096
    max_candidate_bits: int = 4096
