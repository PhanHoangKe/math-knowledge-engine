"""Operation tracker for S3 linear solver budget accounting."""

from __future__ import annotations
from typing import Optional

from ..parser.errors import Span
from ..evaluator.budget import EvaluationBudget
from ..evaluator.errors import EvaluationResourceLimitError


class OperationTracker:
    """Tracks operations and enforces operation budget across S3 solver execution.

    Accounting policy:
    1. Preflight AST traversal: Each visited node is charged 1 operation.
    2. Variable-dependency inspection: Nodes inspected during bottom-up/memoized
       variable-dependency collection are charged 1 operation on initial visit;
       memoized lookups are $O(1)$.
    3. Constant subexpression evaluation: Exact evaluations during preflight or
       extraction are charged step-by-step using shared operation counters.
    4. Affine extraction: Each AST node processed during affine extraction charges 1 operation.
    5. Reduction arithmetic: Normalized coefficient subtractions ($a_L - a_R$, $b_L - b_R$)
       and root division ($-b / a$) charge 1 operation each.

    Note on isolation: Software operation and bit-length budgets bound algorithm
    computation within the Python interpreter to prevent unbounded execution, algorithmic
    complexity spikes, and excessive memory allocations. They do NOT implement
    OS-level process sandbox or hardware isolation.
    """

    __slots__ = ("operations_count", "budget")

    def __init__(self, budget: EvaluationBudget, initial_operations: int = 0) -> None:
        self.operations_count = initial_operations
        self.budget = budget

    def count_step(self, span: Optional[Span] = None) -> None:
        """Count a single atomic solver step (e.g. node inspection, AST visit, arithmetic)."""
        self.operations_count += 1
        if self.operations_count > self.budget.max_operations:
            raise EvaluationResourceLimitError(
                f"Operation budget exceeded ({self.budget.max_operations} steps) during solver execution.",
                code="ERR_RESOURCE_EXHAUSTED_STEP_LIMIT",
                span=span,
            )

    def charge(self, count: int, span: Optional[Span] = None) -> None:
        """Charge multiple steps (e.g. from constant subexpression evaluation)."""
        self.operations_count += count
        if self.operations_count > self.budget.max_operations:
            raise EvaluationResourceLimitError(
                f"Operation budget exceeded ({self.budget.max_operations} steps) during solver execution.",
                code="ERR_RESOURCE_EXHAUSTED_STEP_LIMIT",
                span=span,
            )
