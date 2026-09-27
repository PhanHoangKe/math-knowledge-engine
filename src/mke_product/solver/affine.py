"""Exact affine representation and AST extraction for the MKE Product linear solver."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ..core.rational import Rational
from ..parser.ast import (
    ASTNode,
    IntegerLiteral,
    Variable,
    Group,
    UnaryOp,
    BinaryOp,
    Power,
)
from ..parser.errors import Span
from ..evaluator.budget import EvaluationBudget
from ..evaluator.evaluator import evaluate_expression
from ..evaluator.errors import (
    ZeroDenominatorEvaluationError,
    UndefinedZeroToZeroError,
    EvaluationResourceLimitError,
)
from .errors import (
    OutOfScopeError,
    OutOfScopeVariableExponentZeroError,
    OutOfScopeNonlinearError,
    OutOfScopeRationalFractionError,
)
from .scope import contains_variable


@dataclass(frozen=True, slots=True)
class AffineForm:
    """Exact affine polynomial representation a*x + b with a, b in Q."""
    a: Rational  # coefficient of x
    b: Rational  # constant term


class OperationTracker:
    """Tracks operations and enforces operation budget during solver execution."""

    __slots__ = ("operations_count", "budget")

    def __init__(self, budget: EvaluationBudget) -> None:
        self.operations_count = 0
        self.budget = budget

    def count_step(self, span: Optional[Span] = None) -> None:
        self.operations_count += 1
        if self.operations_count > self.budget.max_operations:
            raise EvaluationResourceLimitError(
                f"Operation budget exceeded ({self.budget.max_operations} steps) during solver extraction.",
                code="ERR_RESOURCE_EXHAUSTED_STEP_LIMIT",
                span=span,
            )


def _check_bits(val: Rational, budget: EvaluationBudget, span: Optional[Span] = None) -> None:
    """Validate that integer numerator and denominator bit lengths do not exceed budget."""
    if (
        abs(val.numerator).bit_length() > budget.max_integer_bits
        or val.denominator.bit_length() > budget.max_integer_bits
    ):
        raise EvaluationResourceLimitError(
            f"Intermediate rational integer bit length exceeded budget limit ({budget.max_integer_bits} bits).",
            code="ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT",
            span=span,
        )


def extract_affine(
    node: ASTNode,
    budget: EvaluationBudget,
    tracker: OperationTracker,
) -> AffineForm:
    """Extract exact affine form a*x + b from verified in-scope AST node.

    Preserves original AST and source spans.
    Enforces resource budgets throughout arithmetic operations.
    """
    tracker.count_step(node.span)

    if isinstance(node, IntegerLiteral):
        r = Rational(node.value, 1)
        _check_bits(r, budget, node.span)
        return AffineForm(a=Rational(0, 1), b=r)

    elif isinstance(node, Variable):
        if node.name != "x":
            raise OutOfScopeError(
                f"Unsupported variable {node.name!r}; only 'x' is supported.",
                code="OUT_OF_SCOPE_UNSUPPORTED_VARIABLE",
                span=node.span,
            )
        return AffineForm(a=Rational(1, 1), b=Rational(0, 1))

    elif isinstance(node, Group):
        return extract_affine(node.inner, budget, tracker)

    elif isinstance(node, UnaryOp):
        inner = extract_affine(node.operand, budget, tracker)
        if node.op == "+":
            return inner
        elif node.op == "-":
            a = -inner.a
            b = -inner.b
            _check_bits(a, budget, node.span)
            _check_bits(b, budget, node.span)
            return AffineForm(a=a, b=b)
        else:
            raise OutOfScopeError(
                f"Unsupported unary operator {node.op!r}.",
                code="OUT_OF_SCOPE_UNSUPPORTED_OPERATOR",
                span=node.span,
            )

    elif isinstance(node, BinaryOp):
        if node.op == "+":
            left_aff = extract_affine(node.left, budget, tracker)
            right_aff = extract_affine(node.right, budget, tracker)
            a = left_aff.a + right_aff.a
            b = left_aff.b + right_aff.b
            _check_bits(a, budget, node.span)
            _check_bits(b, budget, node.span)
            return AffineForm(a=a, b=b)

        elif node.op == "-":
            left_aff = extract_affine(node.left, budget, tracker)
            right_aff = extract_affine(node.right, budget, tracker)
            a = left_aff.a - right_aff.a
            b = left_aff.b - right_aff.b
            _check_bits(a, budget, node.span)
            _check_bits(b, budget, node.span)
            return AffineForm(a=a, b=b)

        elif node.op == "*":
            left_aff = extract_affine(node.left, budget, tracker)
            right_aff = extract_affine(node.right, budget, tracker)

            if not left_aff.a.is_zero and not right_aff.a.is_zero:
                raise OutOfScopeNonlinearError(
                    "Multiplication of two variable-dependent terms is out of scope.",
                    span=node.span,
                )

            if left_aff.a.is_zero and right_aff.a.is_zero:
                b = left_aff.b * right_aff.b
                _check_bits(b, budget, node.span)
                return AffineForm(a=Rational(0, 1), b=b)
            elif left_aff.a.is_zero:
                a = left_aff.b * right_aff.a
                b = left_aff.b * right_aff.b
                _check_bits(a, budget, node.span)
                _check_bits(b, budget, node.span)
                return AffineForm(a=a, b=b)
            else:
                a = left_aff.a * right_aff.b
                b = left_aff.b * right_aff.b
                _check_bits(a, budget, node.span)
                _check_bits(b, budget, node.span)
                return AffineForm(a=a, b=b)

        elif node.op == "/":
            if contains_variable(node.right):
                raise OutOfScopeRationalFractionError(
                    "Variable-dependent denominator is out of scope for linear solver.",
                    span=node.right.span,
                )
            left_aff = extract_affine(node.left, budget, tracker)
            right_aff = extract_affine(node.right, budget, tracker)

            if not right_aff.a.is_zero:
                raise OutOfScopeRationalFractionError(
                    "Variable-dependent denominator is out of scope for linear solver.",
                    span=node.right.span,
                )
            if right_aff.b.is_zero:
                raise ZeroDenominatorEvaluationError(
                    "Denominator evaluates to zero in original unreduced expression.",
                    span=node.right.span,
                )

            a = left_aff.a / right_aff.b
            b = left_aff.b / right_aff.b
            _check_bits(a, budget, node.span)
            _check_bits(b, budget, node.span)
            return AffineForm(a=a, b=b)

        else:
            raise OutOfScopeError(
                f"Unsupported binary operator {node.op!r}.",
                code="OUT_OF_SCOPE_UNSUPPORTED_OPERATOR",
                span=node.span,
            )

    elif isinstance(node, Power):
        exp_val = node.exponent.value
        if exp_val == 0:
            if contains_variable(node.base):
                raise OutOfScopeVariableExponentZeroError(
                    "Variable-dependent base raised to exponent zero is out of scope for solver.",
                    span=node.span,
                )
            base_val = evaluate_expression(node.base, env={}, budget=budget)
            if base_val.is_zero:
                raise UndefinedZeroToZeroError(
                    "0^0 is undefined in Real domain according to frozen Product convention.",
                    span=node.span,
                )
            return AffineForm(a=Rational(0, 1), b=Rational(1, 1))

        elif exp_val == 1:
            return extract_affine(node.base, budget, tracker)

        elif exp_val == 2:
            if contains_variable(node.base):
                raise OutOfScopeNonlinearError(
                    "Variable-dependent quadratic power is out of scope for linear solver.",
                    span=node.span,
                )
            base_val = evaluate_expression(node.base, env={}, budget=budget)
            b = base_val * base_val
            _check_bits(b, budget, node.span)
            return AffineForm(a=Rational(0, 1), b=b)

        else:
            raise OutOfScopeError(
                f"Unsupported exponent {exp_val}.",
                code="OUT_OF_SCOPE_UNSUPPORTED_EXPONENT",
                span=node.exponent.span,
            )

    else:
        raise OutOfScopeError(
            f"Unsupported AST node type: {type(node).__name__}",
            code="OUT_OF_SCOPE_UNSUPPORTED_NODE",
            span=node.span,
        )
