"""Controlled CAS Dispatch Bridge & Independent Verification Gate.

Milestone: PRODUCT-03C-P1C-04-B0-R1
Conforms strictly to:
- Mandatory fresh intake validation via MKEIntakeValidator.validate().
- Standalone literal equation exhaustiveness guard.
- Strict Win32 Job Object containment (256MB process / 512MB job / breakaway denied).
- Shared 5.0-second monotonic wall-clock execution budget.
- Independent bounded host AST affine-completeness verification.
- Domain-safe host proof checker (fails closed on variable-dependent exponent 0, 0^0, and undefined constants).
- Rigorous envelope, classification, definedness, and wire rational verification for SOLVE and CHECK_CANDIDATE.
- Exact rational arithmetic over Q.
- Lazy-loading for fail-closed non-Windows platform safety.
- Sanitized public result projection.
"""

from __future__ import annotations

import math
import re
import sys
import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mke_product.ai.ir import (
    MathIntermediateRepresentation,
    ProblemCategory,
    PublicValidationDiagnostic,
    QuestionFormat,
    ValidationResult,
)
from mke_product.ai.validator import MKEIntakeValidator
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
from mke_product.parser.errors import MKEParserError
from mke_product.parser.parser import parse_equation
from mke_product.protocol.schema import (
    OPERATION_CHECK_CANDIDATE,
    OPERATION_SOLVE,
    OPERATION_SOLVE_QUADRATIC,
    OPERATION_SOLVE_QUADRATIC_SURD,
    SCHEMA_VERSION,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
)


SYNTAX_ISSUE_CODES: Set[str] = {
    "MATH_SYNTAX_ERROR",
    "EMPTY_PRIMARY_EXPRESSION",
    "EXCESSIVE_NESTING_DEPTH",
    "SUBPART_SYNTAX_ERROR",
    "SUBPART_EXCESSIVE_NESTING_DEPTH",
    "INVALID_CONSTRAINT_SYNTAX",
    "EMPTY_RAW_QUERY",
    "OVERSIZED_INPUT",
    "EXPRESSION_TOO_LONG",
    "SUBPART_EXPRESSION_TOO_LONG",
}

SOURCE_INTEGRITY_ISSUE_CODES: Set[str] = {
    "RAW_QUERY_MISMATCH",
    "SOURCE_SPAN_OUT_OF_BOUNDS",
    "SOURCE_FRAGMENT_MISMATCH",
    "MISSING_EXPRESSION_PROVENANCE",
    "UNLINKED_EXPRESSION_PROVENANCE",
    "MISSING_CONSTRAINT_PROVENANCE",
    "CONSTRAINT_SOURCE_MISMATCH",
}


class IntakeStatus(str, Enum):
    """Lifecycle status of pre-dispatch intake validation."""
    VALIDATED = "VALIDATED"
    REJECTED_SYNTAX = "REJECTED_SYNTAX"
    REJECTED_SCOPE = "REJECTED_SCOPE"
    REJECTED_NON_EXHAUSTIVE = "REJECTED_NON_EXHAUSTIVE"


class ExecutionStatus(str, Enum):
    """Lifecycle status of worker process containment execution."""
    SUCCESS = "SUCCESS"
    ENGINE_ERROR = "ENGINE_ERROR"
    TIMEOUT = "TIMEOUT"
    NON_ZERO_EXIT = "NON_ZERO_EXIT"
    PLATFORM_UNAVAILABLE = "PLATFORM_UNAVAILABLE"
    NOT_DISPATCHED = "NOT_DISPATCHED"


class VerificationStatus(str, Enum):
    """Lifecycle status of independent mathematical verification."""
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"
    REFUTED = "REFUTED"
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RationalRoot(BaseModel):
    """Normalized, canonical rational root representation in public result."""
    model_config = ConfigDict(extra="forbid")

    numerator: int = Field(..., description="Exact integer numerator in lowest terms")
    denominator: int = Field(..., gt=0, description="Exact positive integer denominator in lowest terms")


class ControlledDispatchResult(BaseModel):
    """Authoritative public execution and verification outcome (B0 Baseline Contract)."""
    model_config = ConfigDict(extra="forbid")

    intake_status: IntakeStatus = Field(..., description="Intake validation phase outcome")
    intake_diagnostic: PublicValidationDiagnostic = Field(..., description="Sanitized intake diagnostic projection")
    execution_status: ExecutionStatus = Field(..., description="Sandboxed worker execution outcome")
    verification_status: VerificationStatus = Field(..., description="Independent mathematical verification outcome")
    is_verified: bool = Field(..., description="True ONLY when fully intake-valid, executed, and independently verified")
    solution_type: Optional[str] = Field(default=None, description="'UNIQUE_ROOT', 'ALL_REALS', 'EMPTY_SET', or None")
    verified_root: Optional[RationalRoot] = Field(default=None, description="Exact rational root if unique solution verified")
    completeness_proven: bool = Field(default=False, description="True if mathematical uniqueness/completeness is independently proven")
    error_code: Optional[str] = Field(default=None, description="Sanitized, standardized error code")


class QuadraticControlledDispatchResult(ControlledDispatchResult):
    """B1-specific outcome model carrying quadratic multi-root and discriminant properties."""
    model_config = ConfigDict(extra="forbid")

    verified_roots: List[RationalRoot] = Field(default_factory=list, description="Exact rational roots for quadratic equations")
    discriminant: Optional[RationalRoot] = Field(default=None, description="Exact rational discriminant if quadratic")


class SurdRationalComponent(BaseModel):
    """Exact integer rational component for quadratic surds in lowest terms."""
    model_config = ConfigDict(extra="forbid", strict=True)

    numerator: int = Field(..., description="Exact integer numerator in lowest terms")
    denominator: int = Field(..., description="Exact positive integer denominator in lowest terms")

    @model_validator(mode="after")
    def _validate_contract(self) -> SurdRationalComponent:
        if type(self.numerator) is not int or type(self.denominator) is not int or type(self.numerator) is bool or type(self.denominator) is bool:
            raise ValueError("SurdRationalComponent numerator and denominator must be strict integers.")
        if self.denominator <= 0:
            raise ValueError("SurdRationalComponent denominator must be strictly positive.")
        if abs(self.numerator).bit_length() > 256:
            raise ValueError("SurdRationalComponent numerator exceeds 256-bit limit.")
        if self.denominator.bit_length() > 256:
            raise ValueError("SurdRationalComponent denominator exceeds 256-bit limit.")
        if math.gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("SurdRationalComponent must be in canonical lowest terms (gcd == 1).")
        if self.numerator == 0 and self.denominator != 1:
            raise ValueError("SurdRationalComponent zero value must have canonical denominator 1.")
        return self


class QuadraticSurdRoot(BaseModel):
    """Exact quadratic irrational root in public result: rational_part + sqrt_coefficient * sqrt(radicand)."""
    model_config = ConfigDict(extra="forbid", strict=True)

    rational_part: SurdRationalComponent = Field(..., description="Rational component a in a + b*sqrt(d)")
    sqrt_coefficient: SurdRationalComponent = Field(..., description="Rational multiplier b in a + b*sqrt(d)")
    radicand: int = Field(..., description="Certified squarefree integer radicand d in [2, 2^32 - 1]")

    @model_validator(mode="after")
    def _validate_root_contract(self) -> QuadraticSurdRoot:
        if type(self.radicand) is not int or type(self.radicand) is bool:
            raise ValueError("QuadraticSurdRoot radicand must be a strict integer.")
        if not (2 <= self.radicand < (1 << 32)):
            raise ValueError("QuadraticSurdRoot radicand must satisfy 2 <= radicand < 2^32.")
        if self.sqrt_coefficient.numerator == 0:
            raise ValueError("QuadraticSurdRoot sqrt_coefficient must be non-zero for a genuine irrational root.")
        return self


class QuadraticSurdControlledDispatchResult(ControlledDispatchResult):
    """B2-specific outcome model carrying quadratic irrational multi-root and surd properties."""
    model_config = ConfigDict(extra="forbid")

    verified_surd_roots: List[QuadraticSurdRoot] = Field(..., description="Exact quadratic surd roots pair [r_minus, r_plus]")
    discriminant: RationalRoot = Field(..., description="Exact rational discriminant")
    radicand: int = Field(..., description="Certified squarefree radicand d")
    representation: Literal["QUADRATIC_SURD"] = Field(default="QUADRATIC_SURD", description="Representation tag")

    @model_validator(mode="after")
    def _validate_surd_result_contract(self) -> QuadraticSurdControlledDispatchResult:
        if type(self.radicand) is not int:
            raise ValueError("QuadraticSurdControlledDispatchResult radicand must be a strict integer.")
        if not (2 <= self.radicand < (1 << 32)):
            raise ValueError("QuadraticSurdControlledDispatchResult radicand must satisfy 2 <= radicand < 2^32.")
        if not isinstance(self.verified_surd_roots, list) or len(self.verified_surd_roots) != 2:
            raise ValueError("QuadraticSurdControlledDispatchResult must contain exactly two roots.")
        r1, r2 = self.verified_surd_roots
        if r1.rational_part != r2.rational_part:
            raise ValueError("QuadraticSurdControlledDispatchResult roots must have identical rational parts.")
        if r1.radicand != self.radicand or r2.radicand != self.radicand:
            raise ValueError("QuadraticSurdControlledDispatchResult roots must share the top-level radicand.")
        if r1.sqrt_coefficient.numerator >= 0 or r2.sqrt_coefficient.numerator <= 0:
            raise ValueError("QuadraticSurdControlledDispatchResult canonical root pair order requires negative sqrt_coeff first and positive second.")
        if abs(r1.sqrt_coefficient.numerator) != r2.sqrt_coefficient.numerator or r1.sqrt_coefficient.denominator != r2.sqrt_coefficient.denominator:
            raise ValueError("QuadraticSurdControlledDispatchResult root coefficients must have equal magnitude and opposite sign.")
        return self


class NonAffineExpressionError(Exception):
    """Raised when expression AST cannot be reduced to affine linear form ax + b."""
    pass


def extract_affine_coefficients(
    node: ASTNode,
    target_var: str = "x",
    max_nodes: int = 100,
    max_depth: int = 20,
    max_bits: int = 256,
    _current_depth: int = 0,
    _node_counter: Optional[list] = None,
) -> Tuple[Rational, Rational]:
    """Reduce an AST node to canonical affine coefficients (a, b) representing a*x + b over Q.

    Guarantees:
    - Bounded recursion depth, node count, and integer bit width.
    - Zero in-process CAS or SymPy execution.
    - Exact rational arithmetic via Rational.
    - Domain safety: fail closed on variable-dependent exponent 0, 0^0, and constant division by zero.
    - Strict fail-closed on nonlinear terms, powers > 1 of variable, function calls, divisions by variable expressions.
    """
    if _node_counter is None:
        _node_counter = [0]

    _node_counter[0] += 1
    if _node_counter[0] > max_nodes:
        raise NonAffineExpressionError("AST node budget exceeded during affine analysis.")

    if _current_depth > max_depth:
        raise NonAffineExpressionError("AST recursion depth exceeded during affine analysis.")

    if isinstance(node, IntegerLiteral):
        if node.value.bit_length() > max_bits:
            raise NonAffineExpressionError("Integer bit length exceeded in literal.")
        return (Rational(0), Rational(node.value))

    elif isinstance(node, Variable):
        if node.name == target_var:
            return (Rational(1), Rational(0))
        raise NonAffineExpressionError(f"Unexpected variable {node.name!r} during single-variable affine analysis.")

    elif isinstance(node, Group):
        return extract_affine_coefficients(
            node.inner, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

    elif isinstance(node, UnaryOp):
        a, b = extract_affine_coefficients(
            node.operand, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        if node.op == "+":
            return (a, b)
        elif node.op == "-":
            if a.numerator.bit_length() > max_bits or b.numerator.bit_length() > max_bits:
                raise NonAffineExpressionError("Integer bit length exceeded in unary negation.")
            return (-a, -b)
        raise NonAffineExpressionError(f"Unsupported unary operator: {node.op!r}")

    elif isinstance(node, BinaryOp):
        a1, b1 = extract_affine_coefficients(
            node.left, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        a2, b2 = extract_affine_coefficients(
            node.right, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

        if (
            a1.numerator.bit_length() > max_bits
            or b1.numerator.bit_length() > max_bits
            or a2.numerator.bit_length() > max_bits
            or b2.numerator.bit_length() > max_bits
        ):
            raise NonAffineExpressionError("Integer bit length exceeded before binary operation.")

        if node.op == "+":
            res_a = a1 + a2
            res_b = b1 + b2
        elif node.op == "-":
            res_a = a1 - a2
            res_b = b1 - b2
        elif node.op == "*":
            if not a1.is_zero and not a2.is_zero:
                # Quadratic term a1*a2*x^2
                raise NonAffineExpressionError("Nonlinear quadratic term detected in multiplication.")
            if a1.is_zero:
                # Left is constant b1
                res_a = b1 * a2
                res_b = b1 * b2
            else:
                # Right is constant b2
                res_a = b2 * a1
                res_b = b2 * b1
        elif node.op == "/":
            if not a2.is_zero:
                # Division by variable expression
                raise NonAffineExpressionError("Division by expression containing variable is nonlinear.")
            if b2.is_zero:
                raise NonAffineExpressionError("Division by zero constant in expression.")
            res_a = a1 / b2
            res_b = b1 / b2
        else:
            raise NonAffineExpressionError(f"Unsupported binary operator: {node.op!r}")

        if (
            res_a.numerator.bit_length() > max_bits
            or res_a.denominator.bit_length() > max_bits
            or res_b.numerator.bit_length() > max_bits
            or res_b.denominator.bit_length() > max_bits
        ):
            raise NonAffineExpressionError("Integer bit length exceeded after binary operation.")

        return (res_a, res_b)

    elif isinstance(node, Power):
        exp_val = node.exponent.value
        if exp_val < 0:
            raise NonAffineExpressionError("Negative exponent is not supported in affine scope.")
        elif exp_val == 0:
            # Check base
            a_base, b_base = extract_affine_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not a_base.is_zero:
                # Variable-dependent base raised to power 0 is domain-unsafe (undefined at root of base)
                raise NonAffineExpressionError("Variable-dependent base raised to power 0 is domain-unsafe.")
            if b_base.is_zero:
                # 0^0 is undefined
                raise NonAffineExpressionError("Undefined constant expression 0^0 detected.")
            return (Rational(0), Rational(1))
        elif exp_val == 1:
            return extract_affine_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
        else:
            # Exponent >= 2
            a_base, b_base = extract_affine_coefficients(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not a_base.is_zero:
                raise NonAffineExpressionError(f"Power of variable expression with exponent {exp_val} is nonlinear.")
            if exp_val > 10:
                raise NonAffineExpressionError(f"Constant exponent {exp_val} exceeds allowable maximum of 10.")
            if (
                b_base.numerator.bit_length() * exp_val > max_bits
                or b_base.denominator.bit_length() * exp_val > max_bits
            ):
                raise NonAffineExpressionError("Integer bit length exceeded during constant power evaluation.")
            return (Rational(0), Rational(b_base.numerator ** exp_val, b_base.denominator ** exp_val))

    else:
        raise NonAffineExpressionError(f"Unsupported AST node type for affine analysis: {type(node).__name__}")


def reduce_equation_affine(
    eq_ast: Equation, target_var: str = "x"
) -> Tuple[Rational, Rational]:
    """Reduce Equation(LHS, RHS) to A*x + B = 0 where A = a_L - a_R, B = b_L - b_R."""
    a_L, b_L = extract_affine_coefficients(eq_ast.left, target_var)
    a_R, b_R = extract_affine_coefficients(eq_ast.right, target_var)
    return (a_L - a_R, b_L - b_R)


class NonQuadraticExpressionError(Exception):
    """Raised when expression AST cannot be reduced to quadratic form Ax^2 + Bx + C."""
    pass


class HostQuadraticResourceLimitError(Exception):
    """Raised when host quadratic proof intermediate exceeds 256-bit integer bounds."""
    pass


def _host_check_rational_bounds(val: Rational, max_bits: int = 256) -> Rational:
    """Validate that rational numerator and denominator strictly respect max_bits."""
    if val.numerator.bit_length() > max_bits or val.denominator.bit_length() > max_bits:
        raise HostQuadraticResourceLimitError(f"Host rational intermediate exceeded {max_bits} bits limit.")
    return val


def _host_add(a: Rational, b: Rational, max_bits: int = 256) -> Rational:
    _host_check_rational_bounds(a, max_bits)
    _host_check_rational_bounds(b, max_bits)
    res = a + b
    return _host_check_rational_bounds(res, max_bits)


def _host_sub(a: Rational, b: Rational, max_bits: int = 256) -> Rational:
    _host_check_rational_bounds(a, max_bits)
    _host_check_rational_bounds(b, max_bits)
    res = a - b
    return _host_check_rational_bounds(res, max_bits)


def _host_mul(a: Rational, b: Rational, max_bits: int = 256) -> Rational:
    _host_check_rational_bounds(a, max_bits)
    _host_check_rational_bounds(b, max_bits)
    res = a * b
    return _host_check_rational_bounds(res, max_bits)


def _host_div(a: Rational, b: Rational, max_bits: int = 256) -> Rational:
    _host_check_rational_bounds(a, max_bits)
    _host_check_rational_bounds(b, max_bits)
    if b.is_zero:
        raise NonQuadraticExpressionError("Host division by zero rational.")
    res = a / b
    return _host_check_rational_bounds(res, max_bits)


def _host_neg(a: Rational, max_bits: int = 256) -> Rational:
    _host_check_rational_bounds(a, max_bits)
    res = -a
    return _host_check_rational_bounds(res, max_bits)


def extract_quadratic_coefficients_host(
    node: ASTNode,
    target_var: str = "x",
    max_nodes: int = 100,
    max_depth: int = 20,
    max_bits: int = 256,
    _current_depth: int = 0,
    _node_counter: Optional[list] = None,
) -> Tuple[Rational, Rational, Rational]:
    """Reduce an AST node to canonical quadratic coefficients (c2, c1, c0) representing c2*x^2 + c1*x + c0 over Q.

    Guarantees:
    - Independent verification implementation (never imports or calls mke_product.solver.quadratic).
    - Strict 256-bit integer bounds checked on every arithmetic intermediate.
    - Bounded recursion depth (20) and AST node count (100).
    - Domain safe: fails closed on variable-dependent power 0, 0^0, and zero constant division.
    - Pure Python exact rational arithmetic over Q.
    """
    if _node_counter is None:
        _node_counter = [0]

    _node_counter[0] += 1
    if _node_counter[0] > max_nodes:
        raise NonQuadraticExpressionError("AST node budget exceeded during quadratic analysis.")

    if _current_depth > max_depth:
        raise NonQuadraticExpressionError("AST recursion depth exceeded during quadratic analysis.")

    if isinstance(node, IntegerLiteral):
        if node.value.bit_length() > max_bits:
            raise HostQuadraticResourceLimitError("Integer bit length exceeded in literal.")
        return (Rational(0), Rational(0), Rational(node.value))

    elif isinstance(node, Variable):
        if node.name == target_var:
            return (Rational(0), Rational(1), Rational(0))
        raise NonQuadraticExpressionError(f"Unexpected variable {node.name!r} during single-variable analysis.")

    elif isinstance(node, Group):
        return extract_quadratic_coefficients_host(
            node.inner, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

    elif isinstance(node, UnaryOp):
        c2, c1, c0 = extract_quadratic_coefficients_host(
            node.operand, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        if node.op == "+":
            return (c2, c1, c0)
        elif node.op == "-":
            return (_host_neg(c2, max_bits), _host_neg(c1, max_bits), _host_neg(c0, max_bits))
        raise NonQuadraticExpressionError(f"Unsupported unary operator: {node.op!r}")

    elif isinstance(node, BinaryOp):
        l2, l1, l0 = extract_quadratic_coefficients_host(
            node.left, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        r2, r1, r0 = extract_quadratic_coefficients_host(
            node.right, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

        for val in (l2, l1, l0, r2, r1, r0):
            _host_check_rational_bounds(val, max_bits)

        if node.op == "+":
            res2 = _host_add(l2, r2, max_bits)
            res1 = _host_add(l1, r1, max_bits)
            res0 = _host_add(l0, r0, max_bits)
        elif node.op == "-":
            res2 = _host_sub(l2, r2, max_bits)
            res1 = _host_sub(l1, r1, max_bits)
            res0 = _host_sub(l0, r0, max_bits)
        elif node.op == "*":
            # Check Cauchy product terms for degree > 2 using structural degree checks
            if not l2.is_zero and not r2.is_zero:
                raise NonQuadraticExpressionError("Polynomial degree exceeds 2 in multiplication.")
            if not l2.is_zero and not r1.is_zero:
                raise NonQuadraticExpressionError("Polynomial degree exceeds 2 in multiplication.")
            if not l1.is_zero and not r2.is_zero:
                raise NonQuadraticExpressionError("Polynomial degree exceeds 2 in multiplication.")

            # res2 = l2 * r0 + l1 * r1 + l0 * r2
            term2_a = _host_mul(l2, r0, max_bits)
            term2_b = _host_mul(l1, r1, max_bits)
            term2_c = _host_mul(l0, r2, max_bits)
            res2 = _host_add(_host_add(term2_a, term2_b, max_bits), term2_c, max_bits)

            # res1 = l1 * r0 + l0 * r1
            term1_a = _host_mul(l1, r0, max_bits)
            term1_b = _host_mul(l0, r1, max_bits)
            res1 = _host_add(term1_a, term1_b, max_bits)

            # res0 = l0 * r0
            res0 = _host_mul(l0, r0, max_bits)
        elif node.op == "/":
            if not r2.is_zero or not r1.is_zero:
                raise NonQuadraticExpressionError("Division by variable-dependent expression is not permitted.")
            if r0.is_zero:
                raise NonQuadraticExpressionError("Division by zero constant in expression.")
            res2 = _host_div(l2, r0, max_bits)
            res1 = _host_div(l1, r0, max_bits)
            res0 = _host_div(l0, r0, max_bits)
        else:
            raise NonQuadraticExpressionError(f"Unsupported binary operator: {node.op!r}")

        return (res2, res1, res0)

    elif isinstance(node, Power):
        exp_val = node.exponent.value
        if exp_val < 0:
            raise NonQuadraticExpressionError("Negative exponent is not supported.")
        elif exp_val == 0:
            b2, b1, b0 = extract_quadratic_coefficients_host(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not b2.is_zero or not b1.is_zero:
                raise NonQuadraticExpressionError("Variable-dependent base raised to power 0 is domain-unsafe.")
            if b0.is_zero:
                raise NonQuadraticExpressionError("Undefined constant expression 0^0 detected.")
            return (Rational(0), Rational(0), Rational(1))
        elif exp_val == 1:
            return extract_quadratic_coefficients_host(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
        elif exp_val == 2:
            b2, b1, b0 = extract_quadratic_coefficients_host(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not b2.is_zero:
                raise NonQuadraticExpressionError("Power of quadratic expression with exponent 2 yields degree 4.")
            # (b1*x + b0)^2 = b1^2 * x^2 + 2*b1*b0 * x + b0^2
            res2 = _host_mul(b1, b1, max_bits)
            res1 = _host_mul(_host_mul(Rational(2), b1, max_bits), b0, max_bits)
            res0 = _host_mul(b0, b0, max_bits)
            return (res2, res1, res0)
        else:
            b2, b1, b0 = extract_quadratic_coefficients_host(
                node.base, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
            )
            if not b2.is_zero or not b1.is_zero:
                raise NonQuadraticExpressionError(f"Power of variable expression with exponent {exp_val} is degree > 2.")
            if exp_val > 10:
                raise NonQuadraticExpressionError(f"Constant exponent {exp_val} exceeds allowable maximum of 10.")
            if (
                b0.numerator.bit_length() * exp_val > max_bits
                or b0.denominator.bit_length() * exp_val > max_bits
            ):
                raise HostQuadraticResourceLimitError("Integer bit length exceeded during constant power evaluation.")
            res0 = Rational(b0.numerator ** exp_val, b0.denominator ** exp_val)
            _host_check_rational_bounds(res0, max_bits)
            return (Rational(0), Rational(0), res0)

    else:
        raise NonQuadraticExpressionError(f"Unsupported AST node type: {type(node).__name__}")


def reduce_equation_quadratic(
    eq_ast: Equation, target_var: str = "x", max_bits: int = 256
) -> Tuple[Rational, Rational, Rational]:
    """Reduce Equation(LHS, RHS) to A*x^2 + B*x + C = 0 where A = l2 - r2, B = l1 - r1, C = l0 - r0."""
    l2, l1, l0 = extract_quadratic_coefficients_host(eq_ast.left, target_var, max_bits=max_bits)
    r2, r1, r0 = extract_quadratic_coefficients_host(eq_ast.right, target_var, max_bits=max_bits)
    A = _host_sub(l2, r2, max_bits)
    B = _host_sub(l1, r1, max_bits)
    C = _host_sub(l0, r0, max_bits)
    return (A, B, C)


def _parse_wire_rational(val: Any) -> Optional[Rational]:
    """Parse and validate wire rational dictionary {"numerator": "<str>", "denominator": "<str>"}.

    Rejects non-string digits, booleans, floats, negative denominators, values >256 bits, and uncanonical representations.
    """
    if not isinstance(val, dict):
        return None
    num_str = val.get("numerator")
    den_str = val.get("denominator")

    if not isinstance(num_str, str) or not isinstance(den_str, str):
        return None

    # Strict regex for bounded decimal integer strings
    if not re.match(r"^[+-]?[0-9]{1,80}$", num_str):
        return None
    if not re.match(r"^[1-9][0-9]{0,79}$", den_str):
        return None

    try:
        num = int(num_str)
        den = int(den_str)
        if den <= 0:
            return None
        if abs(num).bit_length() > 256 or den.bit_length() > 256:
            return None
        rat = Rational(num, den)
        # Canonical wire check: string must match reduced form
        if str(rat.numerator) != num_str or str(rat.denominator) != den_str:
            return None
        return rat
    except Exception:
        return None


class HostQuadraticSurdResourceLimitError(Exception):
    """Raised when host surd normalization or proof arithmetic exceeds resource ceiling."""
    pass


def generate_host_prime_table() -> List[int]:
    """Generate complete list of primes <= 65536 using independent Sieve of Eratosthenes on host."""
    limit = 65536
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            for i in range(p * p, limit + 1, p):
                sieve[i] = False
    primes = [p for p in range(2, limit + 1) if sieve[p]]
    if len(primes) != 6542 or primes[0] != 2 or primes[-1] != 65521:
        raise RuntimeError("Host prime sieve verification failed.")
    return primes


HOST_PRIMES_UP_TO_65536: List[int] = generate_host_prime_table()


def _host_normalize_discriminant_squarefree(
    delta: Rational,
    max_bits: int = 256,
) -> Tuple[Rational, int]:
    """Host-independent deterministic squarefree normalization of rational Delta = p/q.

    Returns:
        (s, d) where Delta = s^2 * d, s in Q, d in Z^+ certified squarefree with d < 2^32.

    Raises:
        HostQuadraticSurdResourceLimitError: if Delta <= 0, bit bounds exceeded, or R >= 2^32.
    """
    if delta <= Rational(0):
        raise HostQuadraticSurdResourceLimitError("Discriminant must be strictly positive for surd normalization.")

    p = delta.numerator
    q = delta.denominator

    if p.bit_length() > max_bits or q.bit_length() > max_bits:
        raise HostQuadraticSurdResourceLimitError("Discriminant numerator or denominator bit length exceeded 256 bits.")

    M = p * q
    if M.bit_length() > 512:
        raise HostQuadraticSurdResourceLimitError("Normalization product M = p * q exceeds 512 bits.")

    square_factor = 1
    R = M
    extraction_count = 0
    max_extractions = min(256, M.bit_length() // 2)

    for p_i in HOST_PRIMES_UP_TO_65536:
        p_sq = p_i * p_i
        if p_sq > R:
            break
        while R % p_sq == 0:
            R //= p_sq
            square_factor *= p_i
            extraction_count += 1
            if square_factor.bit_length() > max_bits or extraction_count > max_extractions:
                raise HostQuadraticSurdResourceLimitError("Square factor bit length or extraction count exceeded limit.")

    if R == 1:
        # Rational square
        s = Rational(square_factor, q)
        _host_check_rational_bounds(s, max_bits)
        return (s, 1)

    if R.bit_length() > 32:
        raise HostQuadraticSurdResourceLimitError(
            f"Unfactored radicand remainder ({R.bit_length()} bits) exceeds 32-bit certification bound."
        )

    d = R
    s = Rational(square_factor, q)
    _host_check_rational_bounds(s, max_bits)
    return (s, d)


def _parse_wire_surd_root(val: Any) -> Optional[Tuple[Rational, Rational, int]]:
    """Parse wire dictionary representation of QuadraticSurd into (rational_part, sqrt_coeff, radicand).

    Rejects malformed keys, non-canonical decimal strings, out-of-bound values, and non-canonical signs.
    """
    if not isinstance(val, dict):
        return None
    if set(val.keys()) != {"rational_part", "sqrt_coefficient", "radicand"}:
        return None

    rat_part = _parse_wire_rational(val.get("rational_part"))
    sqrt_coeff = _parse_wire_rational(val.get("sqrt_coefficient"))
    rad_str = val.get("radicand")

    if rat_part is None or sqrt_coeff is None:
        return None
    if sqrt_coeff.is_zero:
        return None
    if not isinstance(rad_str, str) or not re.match(r"^[1-9][0-9]{0,9}$", rad_str):
        return None

    try:
        rad = int(rad_str)
        if rad < 2 or rad >= (1 << 32):
            return None
        if str(rad) != rad_str:
            return None
        return (rat_part, sqrt_coeff, rad)
    except Exception:
        return None


WORKER_INFRASTRUCTURE_ERRORS: Dict[str, Tuple[ExecutionStatus, str]] = {
    "WORKER_TIMEOUT": (ExecutionStatus.TIMEOUT, "ERR_TIMEOUT"),
    "WORKER_RESOURCE_EXHAUSTED": (ExecutionStatus.ENGINE_ERROR, "ERR_RESOURCE_EXHAUSTED"),
    "WORKER_STARTUP_FAILURE": (ExecutionStatus.ENGINE_ERROR, "ERR_WORKER_STARTUP_FAILURE"),
    "WORKER_ASSIGNMENT_FAILURE": (ExecutionStatus.ENGINE_ERROR, "ERR_WORKER_ASSIGNMENT_FAILURE"),
    "WORKER_EXIT_FAILURE": (ExecutionStatus.ENGINE_ERROR, "ERR_WORKER_EXIT_FAILURE"),
    "WORKER_PROTOCOL_FAILURE": (ExecutionStatus.ENGINE_ERROR, "ERR_WORKER_PROTOCOL_FAILURE"),
    "ERR_RESOURCE_EXHAUSTED": (ExecutionStatus.ENGINE_ERROR, "ERR_RESOURCE_EXHAUSTED"),
    "ERR_PAYLOAD_TOO_LARGE": (ExecutionStatus.ENGINE_ERROR, "ERR_PAYLOAD_TOO_LARGE"),
    "ERR_RESPONSE_LIMIT_EXCEEDED": (ExecutionStatus.ENGINE_ERROR, "ERR_RESPONSE_LIMIT_EXCEEDED"),
    "PROTOCOL_ERROR": (ExecutionStatus.ENGINE_ERROR, "ERR_PROTOCOL_ERROR"),
}


class ControlledDispatchBridge:
    """Deterministic pre-dispatch bridge connecting validated MKE-IR to sandboxed worker."""

    BRIDGE_TOTAL_BUDGET_SEC: float = 5.0
    MAX_PROTOCOL_CHARS: int = 256

    @classmethod
    def dispatch(
        cls,
        raw_query: str,
        ir_payload: Union[Dict[str, Any], MathIntermediateRepresentation],
    ) -> ControlledDispatchResult:
        """Execute authoritative intake validation, semantic checks, and contained execution.

        Locked Public Signature:
        - Accepts strictly raw_query and ir_payload.
        - Prohibits caller-supplied controllers, timeouts, or engine overrides.
        """
        return cls._dispatch_internal(raw_query=raw_query, ir_payload=ir_payload)

    @classmethod
    def _dispatch_internal(
        cls,
        raw_query: str,
        ir_payload: Union[Dict[str, Any], MathIntermediateRepresentation],
        _controller: Optional[Any] = None,
        _budget_sec: float = 5.0,
    ) -> ControlledDispatchResult:
        """Internal execution path supporting private test fixtures and containment budget."""
        start_time = time.monotonic()

        # Step 1: Fresh Authoritative Intake Validation
        validation = MKEIntakeValidator.validate(raw_query=raw_query, ir_payload=ir_payload)
        diagnostic = validation.to_public_diagnostic()

        if not validation.is_cas_ready:
            issue_codes = {iss.code for iss in validation.issues}

            if any(c in SYNTAX_ISSUE_CODES for c in issue_codes):
                intake_status = IntakeStatus.REJECTED_SYNTAX
                error_code = "ERR_INTAKE_SYNTAX_INVALID"
            elif any(c in SOURCE_INTEGRITY_ISSUE_CODES for c in issue_codes) or validation.status in ("UNVERIFIED_SEMANTICS", "AMBIGUOUS"):
                intake_status = IntakeStatus.REJECTED_NON_EXHAUSTIVE
                error_code = "ERR_INTAKE_NON_EXHAUSTIVE"
            else:
                intake_status = IntakeStatus.REJECTED_SCOPE
                error_code = "ERR_INTAKE_SCOPE_UNSUPPORTED"

            return ControlledDispatchResult(
                intake_status=intake_status,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code=error_code,
            )

        ir = validation.validated_ir
        if ir is None or not ir.primary_expressions:
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_SYNTAX,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_INTAKE_SYNTAX_INVALID",
            )

        # Step 2: Semantic-Exhaustiveness & Scope Guard
        clean_raw = raw_query.strip()
        clean_expr = ir.primary_expressions[0].strip()

        if clean_raw != clean_expr:
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_NON_EXHAUSTIVE,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_INTAKE_NON_EXHAUSTIVE",
            )

        # Check provenance span matching full expression
        has_matching_span = any(
            span.source_fragment == ir.primary_expressions[0]
            for span in ir.source_spans
        )
        if not has_matching_span:
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_NON_EXHAUSTIVE,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_INTAKE_NON_EXHAUSTIVE",
            )

        if (
            len(ir.primary_expressions) != 1
            or ir.target_variables != ["x"]
            or ir.problem_category != ProblemCategory.EQUATION_SINGLE
            or ir.question_format != QuestionFormat.FREE_FORM
            or bool(ir.parameters)
            or bool(ir.extracted_constraints)
            or bool(ir.subparts)
            or bool(ir.given_options)
            or bool(ir.uncertainty_flags)
        ):
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_SCOPE,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_OUT_OF_SCOPE",
            )

        # Step 3: Protocol Bounds Check
        expr_str = ir.primary_expressions[0]
        if len(expr_str) > cls.MAX_PROTOCOL_CHARS or not expr_str.isascii():
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_SCOPE,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_PROTOCOL_BOUNDS_EXCEEDED",
            )

        # Step 4: Host AST Syntax & Pre-Dispatch Linearity/Quadratic Classification
        try:
            eq_ast = parse_equation(expr_str)
        except MKEParserError:
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_SYNTAX,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_SYNTAX_ERROR",
            )

        # Check if AST is affine linear (degree <= 1 without powers >= 2 or nonlinear products)
        is_affine = False
        host_A_aff: Optional[Rational] = None
        host_B_aff: Optional[Rational] = None
        try:
            host_A_aff, host_B_aff = reduce_equation_affine(eq_ast, "x")
            is_affine = True
        except NonAffineExpressionError:
            is_affine = False

        host_A_quad: Optional[Rational] = None
        host_B_quad: Optional[Rational] = None
        host_C_quad: Optional[Rational] = None
        host_delta: Optional[Rational] = None

        if not is_affine:
            # Check quadratic capability with strict host-bounded arithmetic
            try:
                host_A_quad, host_B_quad, host_C_quad = reduce_equation_quadratic(eq_ast, "x")
                if host_A_quad.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.REJECTED_SCOPE,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.NOT_DISPATCHED,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_OUT_OF_SCOPE",
                    )

                b_sq = _host_mul(host_B_quad, host_B_quad)
                four_a = _host_mul(Rational(4), host_A_quad)
                four_ac = _host_mul(four_a, host_C_quad)
                host_delta = _host_sub(b_sq, four_ac)
            except HostQuadraticResourceLimitError:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_RESOURCE_EXHAUSTED_HOST_PROOF",
                )
            except NonQuadraticExpressionError:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.REJECTED_SCOPE,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )
            except Exception:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.REJECTED_SCOPE,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            # Discriminant analysis: rational square vs certified surd
            is_quadratic_surd = False
            host_s_surd: Optional[Rational] = None
            host_d_surd: Optional[int] = None

            if host_delta.numerator > 0:
                p = host_delta.numerator
                q = host_delta.denominator
                import math
                sp = math.isqrt(p)
                sq = math.isqrt(q)
                if sp * sp == p and sq * sq == q:
                    # Rational square -> B1 rational quadratic path
                    is_quadratic_surd = False
                else:
                    # Positive non-square -> B2 exact quadratic surd path
                    is_quadratic_surd = True
                    try:
                        host_s_surd, host_d_surd = _host_normalize_discriminant_squarefree(host_delta)
                        if host_d_surd == 1:
                            is_quadratic_surd = False
                    except HostQuadraticSurdResourceLimitError:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.NOT_DISPATCHED,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_SURD_NORMALIZATION_RESOURCE_LIMIT",
                        )

        # Step 5: Platform Confinement & Worker Controller Initialization
        if sys.platform != "win32" and _controller is None:
            return ControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.PLATFORM_UNAVAILABLE,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_PLATFORM_NOT_SUPPORTED",
            )

        controller = _controller
        if controller is None:
            from mke_product.worker.controller import WorkerController
            controller = WorkerController()

        if is_affine:
            assert host_A_aff is not None and host_B_aff is not None
            host_A = host_A_aff
            host_B = host_B_aff

            # Step 6: Step 1 Solver Dispatch (SOLVE) with Remaining Wall-Clock Budget
            elapsed = time.monotonic() - start_time
            remaining_budget = max(0.0, _budget_sec - elapsed)
            if remaining_budget <= 0.05:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            solve_req = {
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE,
                "equation": expr_str,
            }

            solve_res = controller.execute_request(solve_req, timeout_sec=remaining_budget)

            # Step 7: Handle Infrastructure Failures before validation
            if not isinstance(solve_res, dict):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            solve_outcome = solve_res.get("outcome")
            solve_status = solve_res.get("status")

            if solve_status == "WORKER_TIMEOUT":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            if solve_outcome == "RESOURCE_EXHAUSTED" or solve_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_RESOURCE_EXHAUSTED",
                )

            if solve_status in WORKER_INFRASTRUCTURE_ERRORS:
                exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[solve_status]
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=exec_st,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code=err_c,
                )

            if solve_outcome == "OUT_OF_SCOPE":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            if solve_res.get("schema_version") != SCHEMA_VERSION_V1 or solve_res.get("operation") != OPERATION_SOLVE:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            solve_classification = solve_res.get("classification")
            solve_definedness = solve_res.get("definedness")
            raw_root = solve_res.get("root")

            if solve_outcome != "SUCCESS":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_SOLVER_FAILURE",
                )

            if solve_status not in ("UNIQUE_ROOT", "DomainSet(R)", "EmptySet"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            if solve_classification != solve_status or solve_definedness is not True:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Step 8: Verification Gate for Affine
            if solve_status == "UNIQUE_ROOT":
                worker_root = _parse_wire_rational(raw_root)
                if worker_root is None:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )

                if host_A.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                host_root = -host_B / host_A
                if host_root != worker_root:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                # Step 8a: Candidate Check via CHECK_CANDIDATE
                elapsed = time.monotonic() - start_time
                remaining_budget = max(0.0, _budget_sec - elapsed)
                if remaining_budget <= 0.05:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
                    )

                cand_str = f"{worker_root.numerator}/{worker_root.denominator}" if worker_root.denominator != 1 else str(worker_root.numerator)
                check_req = {
                    "schema_version": SCHEMA_VERSION_V1,
                    "operation": OPERATION_CHECK_CANDIDATE,
                    "equation": expr_str,
                    "candidate": cand_str,
                }

                check_res = controller.execute_request(check_req, timeout_sec=remaining_budget)

                if not isinstance(check_res, dict):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )

                check_status = check_res.get("status")
                check_outcome = check_res.get("outcome")

                if check_status == "WORKER_TIMEOUT":
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
                    )

                if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_RESOURCE_EXHAUSTED",
                    )

                if check_status in WORKER_INFRASTRUCTURE_ERRORS:
                    exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[check_status]
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=exec_st,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code=err_c,
                    )

                if check_res.get("schema_version") != SCHEMA_VERSION_V1 or check_res.get("operation") != OPERATION_CHECK_CANDIDATE:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )

                exact_eq = check_res.get("exact_equality")
                defined = check_res.get("definedness")
                wire_residual = _parse_wire_rational(check_res.get("residual"))
                wire_cand = _parse_wire_rational(check_res.get("candidate"))

                if (
                    check_outcome != "SUCCESS"
                    or check_status != "VALID"
                    or exact_eq is not True
                    or defined is not True
                    or wire_cand != worker_root
                    or wire_residual is None
                    or not wire_residual.is_zero
                ):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFIED_COMPLETE,
                    is_verified=True,
                    solution_type="UNIQUE_ROOT",
                    verified_root=RationalRoot(
                        numerator=worker_root.numerator,
                        denominator=worker_root.denominator,
                    ),
                    completeness_proven=True,
                )

            elif solve_status == "DomainSet(R)":
                if raw_root is not None:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )
                if host_A.is_zero and host_B.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFIED_COMPLETE,
                        is_verified=True,
                        solution_type="ALL_REALS",
                        completeness_proven=True,
                    )
                else:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.UNVERIFIED_CLAIM,
                        is_verified=False,
                        error_code="ERR_UNVERIFIED_IDENTITY",
                    )

            elif solve_status == "EmptySet":
                if raw_root is not None:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )
                if host_A.is_zero and not host_B.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFIED_COMPLETE,
                        is_verified=True,
                        solution_type="EMPTY_SET",
                        completeness_proven=True,
                    )
                else:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.UNVERIFIED_CLAIM,
                        is_verified=False,
                        error_code="ERR_UNVERIFIED_CONTRADICTION",
                    )

            return ControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.ENGINE_ERROR,
                verification_status=VerificationStatus.VERIFICATION_FAILED,
                is_verified=False,
                error_code="ERR_SOLVER_FAILURE",
            )

        elif is_quadratic_surd:
            # Quadratic Surd execution path (mke.p02a.v3 / SOLVE_QUADRATIC_SURD)
            assert host_A_quad is not None and host_B_quad is not None and host_C_quad is not None and host_delta is not None
            assert host_s_surd is not None and host_d_surd is not None
            host_A = host_A_quad
            host_B = host_B_quad
            host_C = host_C_quad
            host_s = host_s_surd
            host_d = host_d_surd

            # Pre-dispatch Host Algebraic Derivation & Proof over Q(sqrt(d))
            try:
                two_A = _host_mul(Rational(2), host_A)
                neg_B = _host_neg(host_B)
                a_host = _host_div(neg_B, two_A)

                two_abs_A = _host_mul(Rational(2), abs(host_A))
                b0_host = _host_div(host_s, two_abs_A)
                neg_b0_host = _host_neg(b0_host)

                # Expected root pair: [r_minus, r_plus]
                exp_r_minus = (a_host, neg_b0_host, host_d)
                exp_r_plus = (a_host, b0_host, host_d)

                # Vieta Proof Identities:
                # 1. Sum: r1 + r2 == -B/A <=> 2*A*a + B == 0
                two_A_a = _host_mul(two_A, a_host)
                sum_check = _host_add(two_A_a, host_B)
                if not sum_check.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.NOT_DISPATCHED,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_SURD_VERIFICATION_MISMATCH",
                    )

                # 2. Product: r1 * r2 == C/A <=> A*(a^2 - b0^2*d) - C == 0
                a_sq = _host_mul(a_host, a_host)
                b0_sq = _host_mul(b0_host, b0_host)
                b0_sq_d = _host_mul(b0_sq, Rational(host_d))
                prod_diff = _host_sub(a_sq, b0_sq_d)
                A_prod = _host_mul(host_A, prod_diff)
                prod_check = _host_sub(A_prod, host_C)
                if not prod_check.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.NOT_DISPATCHED,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_SURD_VERIFICATION_MISMATCH",
                    )

                # 3. Exact Polynomial Residual in Q(sqrt(d)):
                # Rational part: A*(a^2 + b0^2*d) + B*a + C == 0
                A_sum_part = _host_mul(host_A, _host_add(a_sq, b0_sq_d))
                B_a = _host_mul(host_B, a_host)
                sum_part1 = _host_add(A_sum_part, B_a)
                residual_rational = _host_add(sum_part1, host_C)

                # Radical part: b0*(2*A*a + B) == 0
                residual_radical = _host_mul(b0_host, sum_check)

                if not residual_rational.is_zero or not residual_radical.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.NOT_DISPATCHED,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_SURD_VERIFICATION_MISMATCH",
                    )

            except (HostQuadraticResourceLimitError, HostQuadraticSurdResourceLimitError):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_RESOURCE_EXHAUSTED_HOST_PROOF",
                )

            # Step 6: Dispatch v3 Worker with Remaining Budget
            elapsed = time.monotonic() - start_time
            remaining_budget = max(0.0, _budget_sec - elapsed)
            if remaining_budget <= 0.05:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            solve_req = {
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "equation": expr_str,
            }
            solve_res = controller.execute_request(solve_req, timeout_sec=remaining_budget)

            # Step 7: Handle Infrastructure Failures before v3 envelope validation
            if not isinstance(solve_res, dict):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            solve_outcome = solve_res.get("outcome")
            solve_status = solve_res.get("status")

            if solve_status == "WORKER_TIMEOUT":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            if solve_outcome == "RESOURCE_EXHAUSTED" or solve_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_RESOURCE_EXHAUSTED",
                )

            if solve_status in WORKER_INFRASTRUCTURE_ERRORS:
                exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[solve_status]
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=exec_st,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code=err_c,
                )

            if solve_outcome == "OUT_OF_SCOPE":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            # Strict v3 success response envelope exact field set check
            EXACT_V3_SUCCESS_RESPONSE_FIELDS = {
                "schema_version",
                "operation",
                "outcome",
                "status",
                "roots",
                "discriminant",
                "radicand",
                "definedness",
                "error",
                "is_provisional_evidence",
            }
            if set(solve_res.keys()) != EXACT_V3_SUCCESS_RESPONSE_FIELDS:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            if (
                solve_res.get("schema_version") != SCHEMA_VERSION_V3
                or solve_res.get("operation") != OPERATION_SOLVE_QUADRATIC_SURD
                or solve_res.get("outcome") != "SUCCESS"
                or solve_res.get("status") != "TWO_DISTINCT_REAL_ROOTS"
                or solve_res.get("definedness") is not True
                or solve_res.get("error") is not None
                or type(solve_res.get("is_provisional_evidence")) is not bool
                or solve_res.get("is_provisional_evidence") is not True
            ):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Step 8: Parse wire discriminant and radicand
            worker_delta = _parse_wire_rational(solve_res.get("discriminant"))
            if worker_delta is None or worker_delta != host_delta:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_SURD_VERIFICATION_MISMATCH",
                )

            rad_val = solve_res.get("radicand")
            if not isinstance(rad_val, str) or not re.match(r"^[1-9][0-9]{0,9}$", rad_val):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )
            try:
                worker_rad = int(rad_val)
                if worker_rad < 2 or worker_rad >= (1 << 32):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )
                if worker_rad != host_d or str(worker_rad) != rad_val:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_SURD_VERIFICATION_MISMATCH",
                    )
            except Exception:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Step 9: Parse and match worker surd roots
            raw_roots = solve_res.get("roots")
            if not isinstance(raw_roots, list) or len(raw_roots) != 2:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            parsed_r1 = _parse_wire_surd_root(raw_roots[0])
            parsed_r2 = _parse_wire_surd_root(raw_roots[1])
            if parsed_r1 is None or parsed_r2 is None:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            w1_a, w1_b, w1_d = parsed_r1
            w2_a, w2_b, w2_d = parsed_r2

            # Canonical symmetry and sign check:
            # w1_b < 0, w2_b > 0, -w1_b == w2_b, w1_a == w2_a, w1_d == w2_d == host_d
            if (
                w1_d != host_d
                or w2_d != host_d
                or w1_a != a_host
                or w2_a != a_host
                or not (w1_b < Rational(0))
                or not (w2_b > Rational(0))
                or w1_b != neg_b0_host
                or w2_b != b0_host
            ):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_SURD_VERIFICATION_MISMATCH",
                )

            public_root1 = QuadraticSurdRoot(
                rational_part=SurdRationalComponent(numerator=w1_a.numerator, denominator=w1_a.denominator),
                sqrt_coefficient=SurdRationalComponent(numerator=w1_b.numerator, denominator=w1_b.denominator),
                radicand=w1_d,
            )
            public_root2 = QuadraticSurdRoot(
                rational_part=SurdRationalComponent(numerator=w2_a.numerator, denominator=w2_a.denominator),
                sqrt_coefficient=SurdRationalComponent(numerator=w2_b.numerator, denominator=w2_b.denominator),
                radicand=w2_d,
            )

            return QuadraticSurdControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED_COMPLETE,
                is_verified=True,
                solution_type="TWO_DISTINCT_REAL_ROOTS",
                verified_surd_roots=[public_root1, public_root2],
                discriminant=RationalRoot(
                    numerator=host_delta.numerator,
                    denominator=host_delta.denominator,
                ),
                radicand=host_d,
                completeness_proven=True,
            )

        else:
            # Quadratic execution path (mke.p02a.v2 / SOLVE_QUADRATIC)
            assert host_A_quad is not None and host_B_quad is not None and host_C_quad is not None and host_delta is not None
            host_A = host_A_quad
            host_B = host_B_quad
            host_C = host_C_quad

            elapsed = time.monotonic() - start_time
            remaining_budget = max(0.0, _budget_sec - elapsed)
            if remaining_budget <= 0.05:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            solve_req = {
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "equation": expr_str,
            }
            solve_res = controller.execute_request(solve_req, timeout_sec=remaining_budget)

            # Step 7: Handle Infrastructure Failures before v2 validation
            if not isinstance(solve_res, dict):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            solve_outcome = solve_res.get("outcome")
            solve_status = solve_res.get("status")

            if solve_status == "WORKER_TIMEOUT":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            if solve_outcome == "RESOURCE_EXHAUSTED" or solve_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_RESOURCE_EXHAUSTED",
                )

            if solve_status in WORKER_INFRASTRUCTURE_ERRORS:
                exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[solve_status]
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=exec_st,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code=err_c,
                )

            if solve_outcome == "OUT_OF_SCOPE":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            # Strict v2 success response envelope exact field set check
            EXACT_V2_SUCCESS_RESPONSE_FIELDS = {
                "schema_version",
                "operation",
                "outcome",
                "status",
                "roots",
                "discriminant",
                "definedness",
                "error",
                "is_provisional_evidence",
            }
            if set(solve_res.keys()) != EXACT_V2_SUCCESS_RESPONSE_FIELDS:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            if (
                solve_res.get("schema_version") != SCHEMA_VERSION_V2
                or solve_res.get("operation") != OPERATION_SOLVE_QUADRATIC
                or solve_outcome != "SUCCESS"
                or solve_res.get("definedness") is not True
                or solve_res.get("error") is not None
                or type(solve_res.get("is_provisional_evidence")) is not bool
                or solve_status not in ("NO_REAL_ROOT", "UNIQUE_REAL_ROOT", "TWO_DISTINCT_REAL_ROOTS")
            ):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Discriminant check
            raw_disc = solve_res.get("discriminant")
            worker_disc = _parse_wire_rational(raw_disc)
            if worker_disc is None or worker_disc != host_delta:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_VERIFICATION_MISMATCH",
                )

            # Roots list check
            raw_roots = solve_res.get("roots")
            if not isinstance(raw_roots, list):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            worker_roots: List[Rational] = []
            for r in raw_roots:
                pr = _parse_wire_rational(r)
                if pr is None:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )
                worker_roots.append(pr)

            # Verify by mathematical case
            if host_delta.numerator < 0:
                if solve_status != "NO_REAL_ROOT" or len(worker_roots) != 0:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )
                return QuadraticControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFIED_COMPLETE,
                    is_verified=True,
                    solution_type="NO_REAL_ROOT",
                    verified_roots=[],
                    discriminant=RationalRoot(
                        numerator=host_delta.numerator,
                        denominator=host_delta.denominator,
                    ),
                    completeness_proven=True,
                )

            elif host_delta.is_zero:
                if solve_status != "UNIQUE_REAL_ROOT" or len(worker_roots) != 1:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                w_root = worker_roots[0]
                try:
                    two_a = _host_mul(Rational(2), host_A)
                    neg_b = _host_neg(host_B)
                    expected_root = _host_div(neg_b, two_a)

                    if w_root != expected_root:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.SUCCESS,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_VERIFICATION_MISMATCH",
                        )

                    # Vieta checks: 2*w == -B/A, w^2 == C/A
                    two_w = _host_mul(Rational(2), w_root)
                    neg_b_over_a = _host_div(neg_b, host_A)
                    w_sq = _host_mul(w_root, w_root)
                    c_over_a = _host_div(host_C, host_A)

                    if two_w != neg_b_over_a or w_sq != c_over_a:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.SUCCESS,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_VERIFICATION_MISMATCH",
                        )
                except HostQuadraticResourceLimitError:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_RESOURCE_EXHAUSTED_HOST_PROOF",
                    )

                # Candidate check via v1 CHECK_CANDIDATE
                elapsed = time.monotonic() - start_time
                remaining_budget = max(0.0, _budget_sec - elapsed)
                if remaining_budget <= 0.05:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
                    )

                cand_str = f"{w_root.numerator}/{w_root.denominator}" if w_root.denominator != 1 else str(w_root.numerator)
                check_req = {
                    "schema_version": SCHEMA_VERSION_V1,
                    "operation": OPERATION_CHECK_CANDIDATE,
                    "equation": expr_str,
                    "candidate": cand_str,
                }
                check_res = controller.execute_request(check_req, timeout_sec=remaining_budget)

                if not isinstance(check_res, dict):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )

                check_status = check_res.get("status")
                check_outcome = check_res.get("outcome")

                if check_status == "WORKER_TIMEOUT":
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
                    )

                if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_RESOURCE_EXHAUSTED",
                    )

                if check_status in WORKER_INFRASTRUCTURE_ERRORS:
                    exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[check_status]
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=exec_st,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code=err_c,
                    )

                if check_res.get("schema_version") != SCHEMA_VERSION_V1 or check_res.get("operation") != OPERATION_CHECK_CANDIDATE:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.ENGINE_ERROR,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
                    )

                exact_eq = check_res.get("exact_equality")
                defined = check_res.get("definedness")
                wire_residual = _parse_wire_rational(check_res.get("residual"))
                wire_cand = _parse_wire_rational(check_res.get("candidate"))

                if (
                    check_outcome != "SUCCESS"
                    or check_status != "VALID"
                    or exact_eq is not True
                    or defined is not True
                    or wire_cand != w_root
                    or wire_residual is None
                    or not wire_residual.is_zero
                ):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                root_obj = RationalRoot(numerator=w_root.numerator, denominator=w_root.denominator)
                return QuadraticControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFIED_COMPLETE,
                    is_verified=True,
                    solution_type="UNIQUE_REAL_ROOT",
                    verified_root=root_obj,
                    verified_roots=[root_obj],
                    discriminant=RationalRoot(
                        numerator=host_delta.numerator,
                        denominator=host_delta.denominator,
                    ),
                    completeness_proven=True,
                )

            else:
                # host_delta.numerator > 0 (Rational square)
                if solve_status != "TWO_DISTINCT_REAL_ROOTS" or len(worker_roots) != 2:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                w1, w2 = worker_roots[0], worker_roots[1]
                # Strictly ascending sort required
                if not (w1 < w2):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                try:
                    import math
                    sp = math.isqrt(host_delta.numerator)
                    sq = math.isqrt(host_delta.denominator)
                    k = _host_check_rational_bounds(Rational(sp, sq))
                    neg_b = _host_neg(host_B)
                    two_a = _host_mul(Rational(2), host_A)

                    neg_b_minus_k = _host_sub(neg_b, k)
                    neg_b_plus_k = _host_add(neg_b, k)

                    r1 = _host_div(neg_b_minus_k, two_a)
                    r2 = _host_div(neg_b_plus_k, two_a)
                    exp_low, exp_high = (r1, r2) if r1 < r2 else (r2, r1)

                    if w1 != exp_low or w2 != exp_high:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.SUCCESS,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_VERIFICATION_MISMATCH",
                        )

                    # Vieta checks: w1 + w2 == -B/A, w1 * w2 == C/A
                    w_sum = _host_add(w1, w2)
                    w_prod = _host_mul(w1, w2)
                    neg_b_over_a = _host_div(neg_b, host_A)
                    c_over_a = _host_div(host_C, host_A)

                    if w_sum != neg_b_over_a or w_prod != c_over_a:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.SUCCESS,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_VERIFICATION_MISMATCH",
                        )
                except HostQuadraticResourceLimitError:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_RESOURCE_EXHAUSTED_HOST_PROOF",
                    )

                # Candidate checks for both roots
                for w in (w1, w2):
                    elapsed = time.monotonic() - start_time
                    remaining_budget = max(0.0, _budget_sec - elapsed)
                    if remaining_budget <= 0.05:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.TIMEOUT,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_TIMEOUT",
                        )

                    cand_str = f"{w.numerator}/{w.denominator}" if w.denominator != 1 else str(w.numerator)
                    check_req = {
                        "schema_version": SCHEMA_VERSION_V1,
                        "operation": OPERATION_CHECK_CANDIDATE,
                        "equation": expr_str,
                        "candidate": cand_str,
                    }
                    check_res = controller.execute_request(check_req, timeout_sec=remaining_budget)

                    if not isinstance(check_res, dict):
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.ENGINE_ERROR,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_MALFORMED_WORKER_RESPONSE",
                        )

                    check_status = check_res.get("status")
                    check_outcome = check_res.get("outcome")

                    if check_status == "WORKER_TIMEOUT":
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.TIMEOUT,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_TIMEOUT",
                        )

                    if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_RESOURCE_EXHAUSTED", "ERR_RESOURCE_EXHAUSTED"):
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.ENGINE_ERROR,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_RESOURCE_EXHAUSTED",
                        )

                    if check_status in WORKER_INFRASTRUCTURE_ERRORS:
                        exec_st, err_c = WORKER_INFRASTRUCTURE_ERRORS[check_status]
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=exec_st,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code=err_c,
                        )

                    if check_res.get("schema_version") != SCHEMA_VERSION_V1 or check_res.get("operation") != OPERATION_CHECK_CANDIDATE:
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.ENGINE_ERROR,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_MALFORMED_WORKER_RESPONSE",
                        )

                    exact_eq = check_res.get("exact_equality")
                    defined = check_res.get("definedness")
                    wire_residual = _parse_wire_rational(check_res.get("residual"))
                    wire_cand = _parse_wire_rational(check_res.get("candidate"))

                    if (
                        check_outcome != "SUCCESS"
                        or check_status != "VALID"
                        or exact_eq is not True
                        or defined is not True
                        or wire_cand != w
                        or wire_residual is None
                        or not wire_residual.is_zero
                    ):
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.SUCCESS,
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_VERIFICATION_MISMATCH",
                        )

                roots_objs = [
                    RationalRoot(numerator=w1.numerator, denominator=w1.denominator),
                    RationalRoot(numerator=w2.numerator, denominator=w2.denominator),
                ]
                return QuadraticControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.SUCCESS,
                    verification_status=VerificationStatus.VERIFIED_COMPLETE,
                    is_verified=True,
                    solution_type="TWO_DISTINCT_REAL_ROOTS",
                    verified_root=None,
                    verified_roots=roots_objs,
                    discriminant=RationalRoot(
                        numerator=host_delta.numerator,
                        denominator=host_delta.denominator,
                    ),
                    completeness_proven=True,
                )
