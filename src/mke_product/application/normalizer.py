"""MKE MVP V1 Exact Normalizer & Bounded Polynomial Arithmetic in Q[x].

Implements:
1. PolynomialQDegree2: Exact immutable polynomial representation P in Q[x] with deg(P) <= 2.
2. normalize_expression: Recursive AST evaluation into PolynomialQDegree2 with fail-closed degree bounds.
3. normalize_equation: Evaluation of Equation AST (LHS = RHS -> LHS - RHS) yielding exact (a, b, c) in Q.
4. normalize_raw_equation: High-level entry point parsing and normalizing raw strings with typed error mapping.

Guarantees:
- Zero float arithmetic authority: uses exact Rational (p/q, gcd(|p|,q)=1, q>0).
- Zero CAS authority (no SymPy fallback, no LLM).
- Strict fail-closed intermediate degree bounding (no speculative expansion or quotient ring modulo arithmetic).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mke_product.core.rational import Rational
from mke_product.parser.ast import (
    ASTNode,
    BinaryOp,
    Equation,
    Group,
    IntegerLiteral,
    Power,
    UnaryOp,
    Variable,
)
from mke_product.parser.errors import MKEParserError, Span
from mke_product.parser.lexer import tokenize
from mke_product.parser.parser import Parser

from .errors import (
    ApplicationError,
    ApplicationErrorCode,
    map_parser_exception_to_application_error,
)


@dataclass(frozen=True, slots=True)
class PolynomialQDegree2:
    """Exact univariate polynomial P(x) = c2*x^2 + c1*x + c0 with rational coefficients in Q.

    Represents polynomials P in Q[x] with deg(P) <= 2.
    It is NOT a quotient ring Q[x]/<x^3>. Any multiplication or power yielding
    degree > 2 immediately raises DEGREE_OUT_OF_SCOPE.
    """

    c2: Rational
    c1: Rational
    c0: Rational

    def __post_init__(self) -> None:
        if not isinstance(self.c2, Rational) or not isinstance(self.c1, Rational) or not isinstance(self.c0, Rational):
            raise TypeError("PolynomialQDegree2 coefficients must be instances of core Rational (pure Q).")

    @classmethod
    def zero(cls) -> PolynomialQDegree2:
        return cls(Rational(0, 1), Rational(0, 1), Rational(0, 1))

    @classmethod
    def constant(cls, val: int | Rational) -> PolynomialQDegree2:
        r = Rational(val, 1) if isinstance(val, int) else val
        return cls(Rational(0, 1), Rational(0, 1), r)

    @classmethod
    def variable(cls) -> PolynomialQDegree2:
        return cls(Rational(0, 1), Rational(1, 1), Rational(0, 1))

    @property
    def is_zero(self) -> bool:
        return self.c2.is_zero and self.c1.is_zero and self.c0.is_zero

    @property
    def has_variable(self) -> bool:
        return (not self.c2.is_zero) or (not self.c1.is_zero)

    @property
    def degree(self) -> int:
        if not self.c2.is_zero:
            return 2
        if not self.c1.is_zero:
            return 1
        return 0

    def __neg__(self) -> PolynomialQDegree2:
        return PolynomialQDegree2(-self.c2, -self.c1, -self.c0)

    def __add__(self, other: PolynomialQDegree2) -> PolynomialQDegree2:
        if not isinstance(other, PolynomialQDegree2):
            return NotImplemented
        return PolynomialQDegree2(
            self.c2 + other.c2,
            self.c1 + other.c1,
            self.c0 + other.c0,
        )

    def __sub__(self, other: PolynomialQDegree2) -> PolynomialQDegree2:
        if not isinstance(other, PolynomialQDegree2):
            return NotImplemented
        return PolynomialQDegree2(
            self.c2 - other.c2,
            self.c1 - other.c1,
            self.c0 - other.c0,
        )

    def __mul__(self, other: PolynomialQDegree2) -> PolynomialQDegree2:
        """Exact polynomial multiplication in Q[x] with fail-closed degree bounding."""
        if not isinstance(other, PolynomialQDegree2):
            return NotImplemented

        # Exact convolution coefficients for (c2*x^2 + c1*x + c0) * (d2*x^2 + d1*x + d0):
        # x^4 coeff: c2 * d2
        # x^3 coeff: c2 * d1 + c1 * d2
        # x^2 coeff: c2 * d0 + c1 * d1 + c0 * d2
        # x^1 coeff: c1 * d0 + c0 * d1
        # x^0 coeff: c0 * d0
        coeff_x4 = self.c2 * other.c2
        coeff_x3 = self.c2 * other.c1 + self.c1 * other.c2

        if not coeff_x4.is_zero or not coeff_x3.is_zero:
            raise ApplicationError(
                error_code=ApplicationErrorCode.DEGREE_OUT_OF_SCOPE,
                message_vi="Bậc của đa thức sau khi nhân vượt quá bậc hai (deg <= 2).",
                message_en="Polynomial multiplication degree exceeds quadratic bound (deg <= 2).",
            )

        coeff_x2 = self.c2 * other.c0 + self.c1 * other.c1 + self.c0 * other.c2
        coeff_x1 = self.c1 * other.c0 + self.c0 * other.c1
        coeff_x0 = self.c0 * other.c0

        return PolynomialQDegree2(coeff_x2, coeff_x1, coeff_x0)

    def divide_by_scalar(self, scalar: Rational) -> PolynomialQDegree2:
        if not isinstance(scalar, Rational):
            raise TypeError("Scalar must be a Rational instance.")
        if scalar.is_zero:
            raise ApplicationError(
                error_code=ApplicationErrorCode.DIVISION_BY_ZERO,
                message_vi="Phép chia cho số 0 không hợp lệ.",
                message_en="Division by rational zero is undefined.",
            )
        return PolynomialQDegree2(
            self.c2 / scalar,
            self.c1 / scalar,
            self.c0 / scalar,
        )


def normalize_expression(node: ASTNode) -> PolynomialQDegree2:
    """Recursively normalize an AST expression into a bounded PolynomialQDegree2."""
    if isinstance(node, IntegerLiteral):
        return PolynomialQDegree2.constant(node.value)

    if isinstance(node, Variable):
        return PolynomialQDegree2.variable()

    if isinstance(node, Group):
        return normalize_expression(node.inner)

    if isinstance(node, UnaryOp):
        operand = normalize_expression(node.operand)
        if node.op == "+":
            return operand
        elif node.op == "-":
            return -operand
        else:
            raise ApplicationError(
                error_code=ApplicationErrorCode.SYNTAX_ERROR,
                message_vi=f"Toán tử một ngôi '{node.op}' không hợp lệ.",
                message_en=f"Unsupported unary operator '{node.op}'.",
                span=node.span,
            )

    if isinstance(node, BinaryOp):
        left = normalize_expression(node.left)
        right = normalize_expression(node.right)

        if node.op == "+":
            return left + right
        elif node.op == "-":
            return left - right
        elif node.op == "*":
            try:
                return left * right
            except ApplicationError as err:
                if err.span is None:
                    err.span = node.span
                raise err
        elif node.op == "/":
            if right.has_variable:
                raise ApplicationError(
                    error_code=ApplicationErrorCode.NON_POLYNOMIAL_INPUT,
                    message_vi="Phép chia cho biểu thức chứa biến số không thuộc phạm vi đa thức bậc hai.",
                    message_en="Division by expression containing variable 'x' is non-polynomial.",
                    span=node.span,
                )
            if right.c0.is_zero:
                raise ApplicationError(
                    error_code=ApplicationErrorCode.DIVISION_BY_ZERO,
                    message_vi="Phép chia cho số 0 không hợp lệ.",
                    message_en="Division by zero in mathematical expression.",
                    span=node.span,
                )
            return left.divide_by_scalar(right.c0)
        else:
            raise ApplicationError(
                error_code=ApplicationErrorCode.SYNTAX_ERROR,
                message_vi=f"Toán tử hai ngôi '{node.op}' không hợp lệ.",
                message_en=f"Unsupported binary operator '{node.op}'.",
                span=node.span,
            )

    if isinstance(node, Power):
        base_poly = normalize_expression(node.base)
        exp_val = node.exponent.value

        if exp_val == 0:
            # Check for indeterminate 0^0
            if base_poly.is_zero:
                raise ApplicationError(
                    error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
                    message_vi="Biểu thức lũy thừa 0^0 là dạng bất định, không hợp lệ.",
                    message_en="Indeterminate expression 0^0 is undefined.",
                    span=node.span,
                )
            return PolynomialQDegree2.constant(1)
        elif exp_val == 1:
            return base_poly
        elif exp_val == 2:
            try:
                return base_poly * base_poly
            except ApplicationError as err:
                if err.span is None:
                    err.span = node.span
                raise err
        else:
            raise ApplicationError(
                error_code=ApplicationErrorCode.DEGREE_OUT_OF_SCOPE,
                message_vi=f"Số mũ {exp_val} vượt quá bậc hai (deg <= 2).",
                message_en=f"Exponent {exp_val} exceeds quadratic degree bound.",
                span=node.span,
            )

    raise ApplicationError(
        error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
        message_vi=f"Không thể chuẩn hóa nút AST kiểu '{type(node).__name__}'.",
        message_en=f"Cannot normalize AST node of type '{type(node).__name__}'.",
    )


def normalize_equation(node: Equation) -> Tuple[Rational, Rational, Rational]:
    """Normalize an Equation AST (LHS = RHS) into canonical coefficients (a, b, c) where a*x^2 + b*x + c = 0."""
    lhs = normalize_expression(node.left)
    rhs = normalize_expression(node.right)
    diff = lhs - rhs
    return (diff.c2, diff.c1, diff.c0)


def normalize_raw_equation(text: str) -> Tuple[Rational, Rational, Rational]:
    """High-level entry point: tokenizes, parses, and normalizes a raw equation string.

    Raises typed ApplicationError with source span on any lexical, syntactic, or normalization failure.
    """
    try:
        tokens = tokenize(text)
        parser = Parser(tokens, source_text=text)
        eq_ast = parser.parse_equation()
        return normalize_equation(eq_ast)
    except ApplicationError:
        raise
    except MKEParserError as exc:
        raise map_parser_exception_to_application_error(exc) from exc
    except Exception as exc:
        raise ApplicationError(
            error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
            message_vi=f"Lỗi không xác định trong quá trình chuẩn hóa: {exc}",
            message_en=f"Unhandled error during raw equation normalization: {exc}",
        ) from exc
