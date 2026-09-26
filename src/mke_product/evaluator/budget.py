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

    def __post_init__(self) -> None:
        """Validate that all budget parameters are strictly positive integers."""
        for field_name in ("max_operations", "max_integer_bits", "max_candidate_bits"):
            val = getattr(self, field_name)
            # In Python, bool is a subclass of int; reject bool explicitly
            if isinstance(val, bool) or not isinstance(val, int):
                raise TypeError(
                    f"{field_name} must be an integer, got {type(val).__name__}: {val!r}"
                )
            if val <= 0:
                raise ValueError(
                    f"{field_name} must be a strictly positive integer, got: {val}"
                )
