"""Pre-simplification safety inspection and scope classification for MKE Product linear solver.

Enforces:
1. Bounded hazard collection across original unreduced AST before classification.
2. Permutation-invariant scope resolution.
3. Binding exponent-zero guard over other out-of-scope conditions.
4. Priority of proven original constant-domain violations over out-of-scope constructs.
"""

from typing import Optional, Tuple, List
from ..parser.ast import (
    ASTNode,
    Variable,
    Power,
    BinaryOp,
    Equation,
)
from ..parser.errors import Span
from ..evaluator.budget import EvaluationBudget
from ..evaluator.evaluator import evaluate_expression
from ..evaluator.errors import (
    ZeroDenominatorEvaluationError,
    UndefinedZeroToZeroError,
    EvaluationResourceLimitError,
)
from .result import SolverScopeStatus


def contains_variable(node: ASTNode) -> bool:
    """True if node or any of its descendants is a Variable AST node."""
    return any(isinstance(child, Variable) for child in node.walk())


def check_equation_scope(
    equation: Equation,
    budget: EvaluationBudget,
) -> Optional[Tuple[SolverScopeStatus, str, str, Optional[Span]]]:
    """Inspects the original unreduced Equation AST for scope and domain violations.

    Collects all hazards across the entire AST in a single bounded pass before
    classifying. This guarantees permutation-invariance and avoids order-dependent
    classification discrepancies.

    Priority hierarchy:
    1. Resource limit exhaustion (fail immediately).
    2. Proven original constant-domain violations (DOMAIN_ERROR).
    3. Variable-dependent base raised to exponent zero (OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO).
    4. Variable-dependent denominators (OUT_OF_SCOPE_RATIONAL_FRACTION).
    5. Nonlinear powers and variable multiplications (OUT_OF_SCOPE_NONLINEAR).
    6. Unsupported variables (OUT_OF_SCOPE_UNSUPPORTED_VARIABLE).

    Returns:
        None if equation is safe and in-scope for linear solving.
        Tuple of (status, error_code, error_message, error_span) if out-of-scope or domain error.
    """
    domain_errors: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    exponent_zero_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    rational_fraction_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    nonlinear_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []
    unsupported_var_hazards: List[Tuple[SolverScopeStatus, str, str, Optional[Span]]] = []

    for node in equation.walk():
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
            has_var = contains_variable(node.base)

            if exp_val == 0:
                if has_var:
                    exponent_zero_hazards.append((
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO",
                        "Variable-dependent base raised to exponent zero is out of scope for solver.",
                        node.span,
                    ))
                else:
                    # Constant base: evaluate definedness
                    try:
                        base_val = evaluate_expression(node.base, env={}, budget=budget)
                        if base_val.is_zero:
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                "0^0 is undefined in Real domain according to frozen Product convention.",
                                node.span,
                            ))
                    except UndefinedZeroToZeroError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.span,
                        ))
                    except ZeroDenominatorEvaluationError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.span,
                        ))
                    except EvaluationResourceLimitError as err:
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
                    # Constant base: verify definedness
                    try:
                        evaluate_expression(node.base, env={}, budget=budget)
                    except UndefinedZeroToZeroError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.span,
                        ))
                    except ZeroDenominatorEvaluationError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.span,
                        ))
                    except EvaluationResourceLimitError as err:
                        return (
                            SolverScopeStatus.RESOURCE_EXHAUSTED,
                            err.code,
                            err.message,
                            err.span or node.span,
                        )

        # 3. Binary operators
        elif isinstance(node, BinaryOp):
            if node.op == "*":
                if contains_variable(node.left) and contains_variable(node.right):
                    nonlinear_hazards.append((
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_NONLINEAR",
                        "Multiplication of two variable-dependent expressions is out of scope for linear solver.",
                        node.span,
                    ))

            elif node.op == "/":
                if contains_variable(node.right):
                    rational_fraction_hazards.append((
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_RATIONAL_FRACTION",
                        "Variable-dependent denominator is out of scope for linear solver.",
                        node.right.span,
                    ))
                else:
                    # Constant denominator: must evaluate to non-zero
                    try:
                        den_val = evaluate_expression(node.right, env={}, budget=budget)
                        if den_val.is_zero:
                            domain_errors.append((
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                "Constant denominator evaluates to zero in original unreduced expression.",
                                node.right.span,
                            ))
                    except UndefinedZeroToZeroError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.right.span,
                        ))
                    except ZeroDenominatorEvaluationError as err:
                        domain_errors.append((
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.right.span,
                        ))
                    except EvaluationResourceLimitError as err:
                        return (
                            SolverScopeStatus.RESOURCE_EXHAUSTED,
                            err.code,
                            err.message,
                            err.span or node.right.span,
                        )

    # Classification by authoritative priority:
    # 1. Proven constant domain violations take precedence over general out-of-scope constructs
    if domain_errors:
        return domain_errors[0]

    # 2. Binding exponent-zero guard takes precedence over all other out-of-scope conditions
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
