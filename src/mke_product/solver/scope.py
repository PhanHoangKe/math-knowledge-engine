"""Pre-simplification safety inspection and scope classification for MKE Product linear solver."""

from typing import Optional, Tuple
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

    Returns:
        None if equation is safe and in-scope for linear solving.
        Tuple of (status, error_code, error_message, error_span) if out-of-scope or domain error.
    """
    for node in equation.walk():
        # 1. Variable check
        if isinstance(node, Variable):
            if node.name != "x":
                return (
                    SolverScopeStatus.OUT_OF_SCOPE,
                    "OUT_OF_SCOPE_UNSUPPORTED_VARIABLE",
                    f"Unsupported variable {node.name!r}; only 'x' is supported.",
                    node.span,
                )

        # 2. Power nodes
        elif isinstance(node, Power):
            exp_val = node.exponent.value
            has_var = contains_variable(node.base)

            if exp_val == 0:
                if has_var:
                    return (
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO",
                        "Variable-dependent base raised to exponent zero is out of scope for solver.",
                        node.span,
                    )
                else:
                    # Constant base: evaluate definedness
                    try:
                        base_val = evaluate_expression(node.base, env={}, budget=budget)
                        if base_val.is_zero:
                            return (
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                                "0^0 is undefined in Real domain according to frozen Product convention.",
                                node.span,
                            )
                    except UndefinedZeroToZeroError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.span,
                        )
                    except ZeroDenominatorEvaluationError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.span,
                        )
                    except EvaluationResourceLimitError as err:
                        return (
                            SolverScopeStatus.RESOURCE_EXHAUSTED,
                            err.code,
                            err.message,
                            err.span or node.span,
                        )

            elif exp_val == 2:
                if has_var:
                    return (
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_NONLINEAR",
                        "Variable-dependent quadratic power is out of scope for linear solver.",
                        node.span,
                    )
                else:
                    # Constant base: verify definedness
                    try:
                        evaluate_expression(node.base, env={}, budget=budget)
                    except UndefinedZeroToZeroError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.span,
                        )
                    except ZeroDenominatorEvaluationError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.span,
                        )
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
                    return (
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_NONLINEAR",
                        "Multiplication of two variable-dependent expressions is out of scope for linear solver.",
                        node.span,
                    )

            elif node.op == "/":
                if contains_variable(node.right):
                    return (
                        SolverScopeStatus.OUT_OF_SCOPE,
                        "OUT_OF_SCOPE_RATIONAL_FRACTION",
                        "Variable-dependent denominator is out of scope for linear solver.",
                        node.right.span,
                    )
                else:
                    # Constant denominator: must evaluate to non-zero
                    try:
                        den_val = evaluate_expression(node.right, env={}, budget=budget)
                        if den_val.is_zero:
                            return (
                                SolverScopeStatus.DOMAIN_ERROR,
                                "DOMAIN_ERROR_DIVISION_BY_ZERO",
                                "Constant denominator evaluates to zero in original unreduced expression.",
                                node.right.span,
                            )
                    except UndefinedZeroToZeroError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO",
                            err.message,
                            err.span or node.right.span,
                        )
                    except ZeroDenominatorEvaluationError as err:
                        return (
                            SolverScopeStatus.DOMAIN_ERROR,
                            "DOMAIN_ERROR_DIVISION_BY_ZERO",
                            err.message,
                            err.span or node.right.span,
                        )
                    except EvaluationResourceLimitError as err:
                        return (
                            SolverScopeStatus.RESOURCE_EXHAUSTED,
                            err.code,
                            err.message,
                            err.span or node.right.span,
                        )

    return None
