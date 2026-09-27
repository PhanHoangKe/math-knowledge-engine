"""Pre-simplification safety inspection and scope classification for MKE Product linear solver.

Enforces:
1. Bounded hazard collection across original unreduced AST before classification.
2. Owner Decision MKE-S3-ADR-001: Proven original constant-domain undefinedness
   takes precedence over variable-dependent exponent-zero scope abstention.
3. Binding exponent-zero guard over other out-of-scope conditions (nonlinear, rational fractions).
4. Shared operation budget and memoized variable-dependency tracking.
5. Deterministic tie-break policy for multiple independent DOMAIN_ERROR conditions:
   Category remains invariant as DOMAIN_ERROR; the leftmost violation in AST pre-order
   traversal is reported.
"""

from __future__ import annotations
from typing import Optional, Tuple, List, Dict
from ..parser.ast import (
    ASTNode,
    IntegerLiteral,
    Variable,
    Group,
    UnaryOp,
    BinaryOp,
    Power,
    Equation,
)
from ..parser.errors import Span
from ..evaluator.budget import EvaluationBudget
from ..evaluator.evaluator import ExpressionEvaluator
from ..evaluator.errors import (
    ZeroDenominatorEvaluationError,
    UndefinedZeroToZeroError,
    EvaluationResourceLimitError,
)
from .tracker import OperationTracker
from .result import SolverScopeStatus


def contains_variable(node: ASTNode) -> bool:
    """True if node or any of its descendants is a Variable AST node (standalone helper)."""
    return any(isinstance(child, Variable) for child in node.walk())


def memoized_contains_variable(
    node: ASTNode,
    tracker: OperationTracker,
    memo: Dict[int, bool],
) -> bool:
    """Check if node contains a variable, charging tracker on unmemoized visits.

    Keyed by immutable AST node identity (id(node)).
    """
    node_id = id(node)
    if node_id in memo:
        return memo[node_id]

    tracker.count_step(node.span)

    res: bool
    if isinstance(node, Variable):
        res = True
    elif isinstance(node, IntegerLiteral):
        res = False
    elif isinstance(node, Group):
        res = memoized_contains_variable(node.inner, tracker, memo)
    elif isinstance(node, UnaryOp):
        res = memoized_contains_variable(node.operand, tracker, memo)
    elif isinstance(node, BinaryOp):
        left_has = memoized_contains_variable(node.left, tracker, memo)
        right_has = memoized_contains_variable(node.right, tracker, memo)
        res = left_has or right_has
    elif isinstance(node, Power):
        res = memoized_contains_variable(node.base, tracker, memo)
    elif isinstance(node, Equation):
        left_has = memoized_contains_variable(node.left, tracker, memo)
        right_has = memoized_contains_variable(node.right, tracker, memo)
        res = left_has or right_has
    else:
        res = False

    memo[node_id] = res
    return res


def check_equation_scope(
    equation: Equation,
    budget: EvaluationBudget,
    tracker: Optional[OperationTracker] = None,
    var_memo: Optional[Dict[int, bool]] = None,
) -> Optional[Tuple[SolverScopeStatus, str, str, Optional[Span]]]:
    """Inspects the original unreduced Equation AST for scope and domain violations.

    Collects all hazards across the entire AST in a single bounded pass before
    classifying. This guarantees permutation-invariance and avoids order-dependent
    classification discrepancies.

    Priority hierarchy (per Owner Decision MKE-S3-ADR-001):
    1. Resource limit exhaustion (fail closed immediately as RESOURCE_EXHAUSTED).
    2. Proven original constant-domain violations (DOMAIN_ERROR).
    3. Variable-dependent base raised to exponent zero (OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO).
    4. Variable-dependent denominators (OUT_OF_SCOPE_RATIONAL_FRACTION).
    5. Nonlinear powers and variable multiplications (OUT_OF_SCOPE_NONLINEAR).
    6. Unsupported variables (OUT_OF_SCOPE_UNSUPPORTED_VARIABLE).

    Deterministic tie-break policy for multiple DOMAIN_ERROR hazards:
    When valid operand reordering exposes different constant-domain errors (e.g. 1/0 vs 0^0),
    the status is invariant as DOMAIN_ERROR. The reported specific code and span correspond
    to the first domain violation encountered during AST pre-order traversal.

    Returns:
        None if equation is safe and in-scope for linear solving.
        Tuple of (status, error_code, error_message, error_span) if out-of-scope or domain error.
    """
    effective_tracker = tracker if tracker is not None else OperationTracker(budget)
    effective_memo = var_memo if var_memo is not None else {}

    domain_errors: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    exponent_zero_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    rational_fraction_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    nonlinear_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    unsupported_var_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []

    try:
        # Prepopulate variable-dependency memoization with operation tracking
        memoized_contains_variable(equation, effective_tracker, effective_memo)

        for node in equation.walk():
            effective_tracker.count_step(node.span)

            # 1. Variable check
            if isinstance(node, Variable):
                if node.name != "x":
                    unsupported_var_hazards.append((
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_UNSUPPORTED_VARIABLE",
                        f"Unsupported variable {node.name!r}; only 'x' is supported.",
                        node.span,
                    ))

            # 2. Power nodes
            elif isinstance(node, Power):
                exp_val = node.exponent.value
                has_var = memoized_contains_variable(node.base, effective_tracker, effective_memo)

                if exp_val == 0:
                    if has_var:
                        exponent_zero_hazards.append((
                            SolverScopeStatus.OUT_OF_SCOPE,
                            "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO",
                            "Variable-dependent base raised to exponent zero is out of scope for solver.",
                            node.span,
                        ))
                    else:
                        # Constant base: evaluate definedness using shared operation budget
                        evaluator = ExpressionEvaluator(
                            env={},
                            budget=budget,
                            initial_operations=effective_tracker.operations_count,
                        )
                        try:
                            base_val = evaluator.evaluate(node.base)
                            effective_tracker.operations_count = evaluator.operations_count
                            if base_val.is_zero:
                                domain_errors.append((
                                    SolverScopeStatus.DOMAIN_ERROR,
                                    "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                    "0^0 is undefined in Real domain according to frozen Product convention.",
                                    node.span,
                                ))
                        except UndefinedZeroToZeroError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                err.message,
                                err.span or node.span,
                            ))
                        except ZeroDenominatorEvaluationError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                err.message,
                                err.span or node.span,
                            ))
                        except EvaluationResourceLimitError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            return (
                                SolverScopeStatus.RESOURCE_EXHAUSTED,
                                err.code,
                                err.message,
                                err.span or node.span,
                            )

                elif exp_val == 2:
                    if has_var:
                        nonlinear_hazards.append((
                            SolverScopeStatus.OUT_OF_SCOPE,
                            "OUT_OF_SCOPE_NONLINEAR",
                            "Variable-dependent quadratic power is out of scope for linear solver.",
                            node.span,
                        ))
                    else:
                        # Constant base: verify definedness using shared operation budget
                        evaluator = ExpressionEvaluator(
                            env={},
                            budget=budget,
                            initial_operations=effective_tracker.operations_count,
                        )
                        try:
                            evaluator.evaluate(node.base)
                            effective_tracker.operations_count = evaluator.operations_count
                        except UndefinedZeroToZeroError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                err.message,
                                err.span or node.span,
                            ))
                        except ZeroDenominatorEvaluationError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                err.message,
                                err.span or node.span,
                            ))
                        except EvaluationResourceLimitError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            return (
                                SolverScopeStatus.RESOURCE_EXHAUSTED,
                                err.code,
                                err.message,
                                err.span or node.span,
                            )

            # 3. Binary operators
            elif isinstance(node, BinaryOp):
                if node.op == "*":
                    left_has = memoized_contains_variable(node.left, effective_tracker, effective_memo)
                    right_has = memoized_contains_variable(node.right, effective_tracker, effective_memo)
                    if left_has and right_has:
                        nonlinear_hazards.append((
                            SolverScopeStatus.OUT_OF_SCOPE,
                            "OUT_OF_SCOPE_NONLINEAR",
                            "Multiplication of two variable-dependent expressions is out of scope for linear solver.",
                            node.span,
                        ))

                elif node.op == "/":
                    if memoized_contains_variable(node.right, effective_tracker, effective_memo):
                        rational_fraction_hazards.append((
                            SolverScopeStatus.OUT_OF_SCOPE,
                            "OUT_OF_SCOPE_RATIONAL_FRACTION",
                            "Variable-dependent denominator is out of scope for linear solver.",
                            node.right.span,
                        ))
                    else:
                        # Constant denominator: must evaluate to non-zero using shared operation budget
                        evaluator = ExpressionEvaluator(
                            env={},
                            budget=budget,
                            initial_operations=effective_tracker.operations_count,
                        )
                        try:
                            den_val = evaluator.evaluate(node.right)
                            effective_tracker.operations_count = evaluator.operations_count
                            if den_val.is_zero:
                                domain_errors.append((
                                    SolverScopeStatus.DOMAIN_ERROR,
                                    "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                    "Constant denominator evaluates to zero in original unreduced expression.",
                                    node.right.span,
                                ))
                        except UndefinedZeroToZeroError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                err.message,
                                err.span or node.right.span,
                            ))
                        except ZeroDenominatorEvaluationError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                err.message,
                                err.span or node.right.span,
                            ))
                        except EvaluationResourceLimitError as err:
                            effective_tracker.operations_count = evaluator.operations_count
                            return (
                                SolverScopeStatus.RESOURCE_EXHAUSTED,
                                err.code,
                                err.message,
                                err.span or node.right.span,
                            )

    except EvaluationResourceLimitError as err:
        return (
            SolverScopeStatus.RESOURCE_EXHAUSTED,
            err.code,
            err.message,
            err.span or equation.span,
        )

    # Classification by authoritative priority:
    # 1. Proven constant domain violations take precedence (MKE-S3-ADR-001)
    if domain_errors:
        return domain_errors[0]

    # 2. Binding exponent-zero guard takes precedence over other scope classifications
    if exponent_zero_hazards:
        return exponent_zero_hazards[0]

    # 3. Rational fraction (variable denominator)
    if rational_fraction_hazards:
        return rational_fraction_hazards[0]

    # 4. Nonlinear powers and multiplications
    if nonlinear_hazards:
        return nonlinear_hazards[0]

    # 5. Unsupported variables
    if unsupported_var_hazards:
        return unsupported_var_hazards[0]

    return None
