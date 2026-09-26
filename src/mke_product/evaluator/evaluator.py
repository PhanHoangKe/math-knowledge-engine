"""Deterministic exact AST evaluator and independent candidate verifier.

Enforces:
1. Strict original-domain safety on unreduced ASTs.
2. Shared evaluation budget covering the entire candidate check.
3. Bounded candidate input validation with strict ASCII rational grammar.
4. Epistemically precise three-valued definedness contract.
"""

from __future__ import annotations
import math
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


def _validate_and_parse_int(part: str, is_denominator: bool, budget: EvaluationBudget) -> int:
    """Validate and parse an integer component according to ASCII rational grammar.

    Enforces component digit count ceiling BEFORE constructing int.
    Forbids leading zeros on multi-digit numbers.
    Forbids zero denominator.
    """
    if not part:
        raise InvalidCandidateError(
            "Empty numeric component in candidate string.",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    if part[0] in ("+", "-"):
        sign = -1 if part[0] == "-" else 1
        digits = part[1:]
    else:
        sign = 1
        digits = part

    if not digits:
        raise InvalidCandidateError(
            f"Missing digits after sign in candidate component: {part!r}",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    # Validate ASCII digits only (reject Unicode digits)
    if not all("0" <= ch <= "9" for ch in digits):
        raise InvalidCandidateError(
            f"Invalid characters in candidate component; ASCII digits only: {part!r}",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    # Component-size ceiling BEFORE integer construction
    # For N bits, max decimal digits ~ ceil(N * log10(2)) + 2
    max_component_digits = math.ceil(budget.max_candidate_bits * 0.30103) + 2
    if len(digits) > max_component_digits:
        raise EvaluationResourceLimitError(
            f"Candidate component digit count ({len(digits)}) exceeds component ceiling of {max_component_digits} digits.",
            code="ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT",
        )

    # Reject leading zeros on multi-digit numbers (e.g. '02', '00', '007')
    if len(digits) > 1 and digits.startswith("0"):
        raise InvalidCandidateError(
            f"Leading zeros are forbidden in numeric candidate: {part!r}",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    # Denominator cannot be zero
    if is_denominator and digits == "0":
        raise InvalidCandidateError(
            "Denominator cannot be zero in rational candidate string.",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    val = int(digits) * sign
    return val


def parse_ascii_rational_string(candidate: str, budget: EvaluationBudget) -> Rational:
    """Parse candidate string according to strict ASCII rational-string grammar.

    Grammar:
        candidate_string ::= [ sign ] integer_part [ "/" [ sign ] denominator_part ]
        sign             ::= "+" | "-"
        integer_part     ::= "0" | non_zero_digit { digit }
        denominator_part ::= non_zero_digit { digit }
        digit            ::= "0" | "1" | ... | "9"
        non_zero_digit   ::= "1" | "2" | ... | "9"

    Enforces input-length and component-size ceilings BEFORE integer construction.
    """
    # Enforce overall string length ceiling BEFORE any parsing
    max_string_length = budget.max_candidate_bits
    if len(candidate) > max_string_length:
        raise EvaluationResourceLimitError(
            f"Candidate string length ({len(candidate)}) exceeds input ceiling ({max_string_length} characters).",
            code="ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT",
        )

    # Enforce ASCII encoding
    if not candidate.isascii():
        raise InvalidCandidateError(
            "Candidate string contains non-ASCII characters.",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    s = candidate.strip()
    if not s:
        raise InvalidCandidateError(
            "Candidate string cannot be empty.",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    if any(ch in s for ch in (" ", "\t", "\n", "\r")):
        raise InvalidCandidateError(
            "Candidate string must not contain interior whitespace.",
            code="ERR_INVALID_CANDIDATE_MALFORMED",
        )

    if "/" in s:
        parts = s.split("/")
        if len(parts) != 2:
            raise InvalidCandidateError(
                f"Malformed fraction string with multiple '/': {candidate!r}",
                code="ERR_INVALID_CANDIDATE_MALFORMED",
            )
        num_part, den_part = parts[0], parts[1]
    else:
        num_part, den_part = s, "1"

    num = _validate_and_parse_int(num_part, is_denominator=False, budget=budget)
    den = _validate_and_parse_int(den_part, is_denominator=True, budget=budget)

    # Validate bit length
    if (
        abs(num).bit_length() > budget.max_candidate_bits
        or den.bit_length() > budget.max_candidate_bits
    ):
        raise EvaluationResourceLimitError(
            f"Candidate integer bit length exceeds budget limit ({budget.max_candidate_bits} bits).",
            code="ERR_RESOURCE_EXHAUSTED_CANDIDATE_LIMIT",
        )

    return Rational(num, den)


def coerce_candidate(candidate: Any, budget: EvaluationBudget) -> Rational:
    """Coerce candidate to exact Rational with strict type validation.

    Supported types: Rational, int, fractions.Fraction, and valid ASCII rational strings.
    Strictly rejected types: float, bool, complex, malformed strings, and oversize components.
    """
    # Reject bool explicitly (in Python, bool is a subclass of int)
    if isinstance(candidate, bool):
        raise InvalidCandidateError(
            "Boolean candidates are strictly forbidden in exact rational evaluation.",
            code="ERR_INVALID_CANDIDATE_TYPE",
        )

    if isinstance(candidate, float):
        raise InvalidCandidateError(
            "Floating-point candidates are strictly forbidden in exact rational evaluation.",
            code="ERR_INVALID_CANDIDATE_FLOAT",
        )

    if isinstance(candidate, str):
        return parse_ascii_rational_string(candidate, budget)

    c: Rational
    if isinstance(candidate, Rational):
        c = candidate
    elif isinstance(candidate, int):
        c = Rational(candidate, 1)
    elif isinstance(candidate, Fraction):
        c = Rational(candidate.numerator, candidate.denominator)
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

    def __init__(
        self,
        env: Mapping[str, Rational],
        budget: EvaluationBudget,
        initial_operations: int = 0,
    ) -> None:
        self.env = env
        self.budget = budget
        self.operations_count = initial_operations

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

    Guarantees:
    - Global operation budget covering the COMPLETE candidate check across both sides.
    - Input-length and component-size ceilings BEFORE integer construction.
    - Explicit three-valued definedness semantics (True/False/None).
    - Accurate left/right and total operation count diagnostics.
    """
    if not isinstance(equation, Equation):
        raise TypeError(f"check_candidate requires an Equation AST, got: {type(equation).__name__}")

    effective_budget = budget if budget is not None else EvaluationBudget()

    try:
        c_rat = coerce_candidate(candidate, effective_budget)
    except EvaluationResourceLimitError as err:
        return CandidateCheckResult(
            status=CandidateCheckStatus.RESOURCE_EXHAUSTED,
            candidate=None,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
            diagnostics=(
                ("stage", "CANDIDATE_COERCION"),
                ("reason", "CANDIDATE_RESOURCE_LIMIT"),
            ),
        )

    env = {"x": c_rat}

    # Shared evaluator covering BOTH left and right sides
    evaluator = ExpressionEvaluator(env=env, budget=effective_budget)

    # 1. Left side evaluation L(c)
    left_val: Optional[Rational] = None
    try:
        left_val = evaluator.evaluate(equation.left)
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
                ("steps_left", str(evaluator.operations_count)),
                ("steps_right", "0"),
                ("total_steps", str(evaluator.operations_count)),
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
                ("steps_left", str(evaluator.operations_count)),
                ("steps_right", "0"),
                ("total_steps", str(evaluator.operations_count)),
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
                ("steps_left", str(evaluator.operations_count)),
                ("steps_right", "0"),
                ("total_steps", str(evaluator.operations_count)),
            ),
        )

    steps_left = evaluator.operations_count

    # 2. Right side evaluation R(c) using the SAME evaluator instance
    right_val: Optional[Rational] = None
    try:
        right_val = evaluator.evaluate(equation.right)
    except DomainError as err:
        steps_right = evaluator.operations_count - steps_left
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
                ("steps_left", str(steps_left)),
                ("steps_right", str(steps_right)),
                ("total_steps", str(evaluator.operations_count)),
            ),
        )
    except EvaluationResourceLimitError as err:
        steps_right = evaluator.operations_count - steps_left
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
                ("steps_left", str(steps_left)),
                ("steps_right", str(steps_right)),
                ("total_steps", str(evaluator.operations_count)),
            ),
        )
    except UnsupportedEvaluationError as err:
        steps_right = evaluator.operations_count - steps_left
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
                ("steps_left", str(steps_left)),
                ("steps_right", str(steps_right)),
                ("total_steps", str(evaluator.operations_count)),
            ),
        )

    steps_right = evaluator.operations_count - steps_left
    total_steps = evaluator.operations_count

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
            ("steps_left", str(steps_left)),
            ("steps_right", str(steps_right)),
            ("total_steps", str(total_steps)),
        ),
    )
