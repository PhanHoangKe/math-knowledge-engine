"""Deterministic exact AST evaluator and independent candidate verifier."""

from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping, Optional, Tuple, Union

from ..core.rational import Rational
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
from .errors import (
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


def coerce_candidate(candidate: Any, budget: EvaluationBudget) -> Rational:
    """Coerce candidate to exact Rational with strict type validation.
    
    Rejects floats and unsupported types deterministically.
    """
    if isinstance(candidate, float):
        raise InvalidCandidateError(
            "Floating-point candidates are strictly forbidden in exact rational evaluation.",
            code="ERR_INVALID_CANDIDATE_FLOAT",
        )

    c: Rational
    if isinstance(candidate, Rational):
        c = candidate
    elif isinstance(candidate, int) and not isinstance(candidate, bool):
        c = Rational(candidate, 1)
    elif isinstance(candidate, Fraction):
        c = Rational(candidate.numerator, candidate.denominator)
    elif isinstance(candidate, str):
        try:
            c = Rational(candidate)
        except Exception as err:
            raise InvalidCandidateError(
                f"Cannot parse candidate rational string: {candidate!r}",
                code="ERR_INVALID_CANDIDATE_MALFORMED",
            ) from err
    else:
        raise InvalidCandidateError(
            f"Unsupported candidate type: {type(candidate).__name__}",
            code="ERR_INVALID_CANDIDATE_TYPE",
        )

    # Validate candidate size against budget
    if (
        abs(c.numerator).bit_length() > budget.max_candidate_bits
        or c.denominator.bit_length() > budget.max_candidate_bits
    ):
        raise EvaluationResourceLimitError(
            f"Candidate bit length exceeds budget limit ({budget.max_candidate_bits} bits).",
            code="ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT",
        )

    return c


class ExpressionEvaluator:
    """Stateful evaluator tracking operation budgets and enforcing original domain obligations."""

    __slots__ = ("env", "budget", "operations_count")

    def __init__(self, env: Mapping[str, Rational], budget: EvaluationBudget) -> None:
        self.env = env
        self.budget = budget
        self.operations_count = 0

    def evaluate(self, node: ASTNode) -> Rational:
        """Recursively evaluate an ASTNode in exact rational arithmetic."""
        self.operations_count += 1
        if self.operations_count > self.budget.max_operations:
            raise EvaluationResourceLimitError(
                f"Evaluation operation budget exceeded ({self.budget.max_operations} steps).",
                code="ERR_RESOURCE_EXHAUSTED_STEP_LIMIT",
                span=node.span,
            )

        res: Rational

        if isinstance(node, IntegerLiteral):
            res = Rational(node.value, 1)

        elif isinstance(node, Variable):
            if node.name not in self.env:
                raise UnsupportedEvaluationError(
                    f"Unbound variable: {node.name!r}",
                    span=node.span,
                )
            res = self.env[node.name]

        elif isinstance(node, Group):
            res = self.evaluate(node.inner)

        elif isinstance(node, UnaryOp):
            operand_val = self.evaluate(node.operand)
            if node.op == "+":
                res = operand_val
            elif node.op == "-":
                res = -operand_val
            else:
                raise UnsupportedEvaluationError(
                    f"Unsupported unary operator: {node.op!r}",
                    span=node.span,
                )

        elif isinstance(node, BinaryOp):
            # MANDATORY RULE: Evaluate BOTH subtrees unconditionally.
            # Multiplication by zero must NEVER hide an undefined subtree.
            left_val = self.evaluate(node.left)
            right_val = self.evaluate(node.right)

            if node.op == "+":
                res = left_val + right_val
            elif node.op == "-":
                res = left_val - right_val
            elif node.op == "*":
                res = left_val * right_val
            elif node.op == "/":
                if right_val.is_zero:
                    raise ZeroDenominatorEvaluationError(
                        "Denominator evaluates to zero in original unreduced expression.",
                        span=node.right.span,
                    )
                res = left_val / right_val
            else:
                raise UnsupportedEvaluationError(
                    f"Unsupported binary operator: {node.op!r}",
                    span=node.span,
                )

        elif isinstance(node, Power):
            base_val = self.evaluate(node.base)
            exp_val = node.exponent.value

            if exp_val == 0:
                if base_val.is_zero:
                    raise UndefinedZeroToZeroError(
                        "0^0 is undefined in Real domain according to frozen Product convention.",
                        span=node.span,
                    )
                res = Rational(1, 1)
            elif exp_val == 1:
                res = base_val
            elif exp_val == 2:
                res = base_val * base_val
            else:
                raise UnsupportedEvaluationError(
                    f"Unsupported exponent value: {exp_val}",
                    span=node.exponent.span,
                )

        else:
            raise UnsupportedEvaluationError(
                f"Unsupported AST node type: {type(node).__name__}",
                span=node.span,
            )

        # Enforce intermediate rational bit budget
        if (
            abs(res.numerator).bit_length() > self.budget.max_integer_bits
            or res.denominator.bit_length() > self.budget.max_integer_bits
        ):
            raise EvaluationResourceLimitError(
                f"Intermediate rational integer bit length exceeded budget limit ({self.budget.max_integer_bits} bits).",
                code="ERR_RESOURCE_EXHAUSTED_INTEGER_LIMIT",
                span=node.span,
            )

        return res


def evaluate_expression(
    node: ASTNode,
    env: Mapping[str, Rational],
    budget: Optional[EvaluationBudget] = None,
) -> Rational:
    """Evaluate an AST expression node exactly with variable substitution.
    
    Raises typed EvaluationError on domain, resource, or unbound variable failures.
    """
    effective_budget = budget if budget is not None else EvaluationBudget()
    evaluator = ExpressionEvaluator(env=env, budget=effective_budget)
    return evaluator.evaluate(node)


def extract_domain_obligations(node: ASTNode) -> Tuple[DomainObligation, ...]:
    """Statically inspect an AST and extract all original domain obligations.
    
    Extracts:
    - Denominators that must evaluate to non-zero.
    - Bases of power-0 expressions that must evaluate to non-zero.
    
    Note: This is static inspection and does not claim to solve real-domain solution sets.
    """
    obligations = []
    for child in node.walk():
        if isinstance(child, BinaryOp) and child.op == "/":
            obligations.append(
                DomainObligation(
                    kind="NONZERO_DENOMINATOR",
                    target_ast=child.right,
                    span=child.right.span,
                    description=f"Denominator must evaluate to non-zero at span [{child.right.span.start}:{child.right.span.end}]",
                )
            )
        elif isinstance(child, Power) and child.exponent.value == 0:
            obligations.append(
                DomainObligation(
                    kind="NONZERO_EXPONENT_BASE",
                    target_ast=child.base,
                    span=child.base.span,
                    description=f"Base of power 0 must evaluate to non-zero at span [{child.base.span.start}:{child.base.span.end}]",
                )
            )
    return tuple(obligations)


def check_candidate(
    equation: Equation,
    candidate: Union[Rational, int, Fraction, str],
    budget: Optional[EvaluationBudget] = None,
) -> CandidateCheckResult:
    """Independently verify an exact rational candidate against an original Equation AST.
    
    Strict guarantees:
    - Validates candidate belongs to exact Rational numbers Q.
    - Evaluates original L(c) and R(c) independently without polynomial reduction.
    - Preserves all original-domain obligations (e.g., zero denominators, 0^0).
    - Multiplications by zero do not hide undefined subtrees.
    - Returns strictly typed, immutable CandidateCheckResult.
    """
    if not isinstance(equation, Equation):
        raise TypeError(f"check_candidate requires an Equation AST, got: {type(equation).__name__}")

    effective_budget = budget if budget is not None else EvaluationBudget()
    c_rat = coerce_candidate(candidate, effective_budget)
    env = {"x": c_rat}

    # Evaluate Left-Hand Side L(c)
    left_evaluator = ExpressionEvaluator(env=env, budget=effective_budget)
    left_val: Optional[Rational] = None
    try:
        left_val = left_evaluator.evaluate(equation.left)
    except DomainError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.DOMAIN_ERROR,
            candidate=c_rat,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "LEFT_SIDE"),
                ("steps", str(left_evaluator.operations_count)),
            ),
        )
    except EvaluationResourceLimitError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.RESOURCE_EXHAUSTED,
            candidate=c_rat,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "LEFT_SIDE"),
                ("steps", str(left_evaluator.operations_count)),
            ),
        )
    except UnsupportedEvaluationError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.UNSUPPORTED,
            candidate=c_rat,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "LEFT_SIDE"),
                ("steps", str(left_evaluator.operations_count)),
            ),
        )

    # Evaluate Right-Hand Side R(c)
    right_evaluator = ExpressionEvaluator(env=env, budget=effective_budget)
    right_val: Optional[Rational] = None
    try:
        right_val = right_evaluator.evaluate(equation.right)
    except DomainError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.DOMAIN_ERROR,
            candidate=c_rat,
            equation=equation,
            left_value=left_val,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "RIGHT_SIDE"),
                ("steps_left", str(left_evaluator.operations_count)),
                ("steps_right", str(right_evaluator.operations_count)),
            ),
        )
    except EvaluationResourceLimitError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.RESOURCE_EXHAUSTED,
            candidate=c_rat,
            equation=equation,
            left_value=left_val,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "RIGHT_SIDE"),
                ("steps_left", str(left_evaluator.operations_count)),
                ("steps_right", str(right_evaluator.operations_count)),
            ),
        )
    except UnsupportedEvaluationError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.UNSUPPORTED,
            candidate=c_rat,
            equation=equation,
            left_value=left_val,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("branch", "RIGHT_SIDE"),
                ("steps_left", str(left_evaluator.operations_count)),
                ("steps_right", str(right_evaluator.operations_count)),
            ),
        )

    # Strict Equality Comparison in Q
    is_equal = left_val == right_val
    status = CandidateCheckStatus.VALID if is_equal else CandidateCheckStatus.INVALID
    residual = abs(left_val - right_val)

    return CandidateCheckResult(
        status=status,
        candidate=c_rat,
        equation=equation,
        left_value=left_val,
        right_value=right_val,
        diagnostics=(
            ("exact_equality", str(is_equal)),
            ("residual", str(residual)),
            ("steps_left", str(left_evaluator.operations_count)),
            ("steps_right", str(right_evaluator.operations_count)),
        ),
    )
