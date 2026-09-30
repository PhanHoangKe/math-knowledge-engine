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

import re
import sys
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

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
    SCHEMA_VERSION,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
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
    """Authoritative public execution and verification outcome."""
    model_config = ConfigDict(extra="forbid")

    intake_status: IntakeStatus = Field(..., description="Intake validation phase outcome")
    intake_diagnostic: PublicValidationDiagnostic = Field(..., description="Sanitized intake diagnostic projection")
    execution_status: ExecutionStatus = Field(..., description="Sandboxed worker execution outcome")
    verification_status: VerificationStatus = Field(..., description="Independent mathematical verification outcome")
    is_verified: bool = Field(..., description="True ONLY when fully intake-valid, executed, and independently verified")
    solution_type: Optional[str] = Field(default=None, description="'UNIQUE_ROOT', 'ALL_REALS', 'EMPTY_SET', 'NO_REAL_ROOT', 'UNIQUE_REAL_ROOT', 'TWO_DISTINCT_REAL_ROOTS', or None")
    verified_root: Optional[RationalRoot] = Field(default=None, description="Exact rational root if unique solution verified")
    verified_roots: Optional[List[RationalRoot]] = Field(default=None, description="Exact rational roots for multi-root or quadratic equations")
    discriminant: Optional[RationalRoot] = Field(default=None, description="Exact rational discriminant if quadratic")
    completeness_proven: bool = Field(default=False, description="True if mathematical uniqueness/completeness is independently proven")
    error_code: Optional[str] = Field(default=None, description="Sanitized, standardized error code")


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
    - Strict 256-bit integer bounds on all intermediate numerators and denominators.
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
            raise NonQuadraticExpressionError("Integer bit length exceeded in literal.")
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
            if (
                c2.numerator.bit_length() > max_bits
                or c1.numerator.bit_length() > max_bits
                or c0.numerator.bit_length() > max_bits
            ):
                raise NonQuadraticExpressionError("Integer bit length exceeded in unary negation.")
            return (-c2, -c1, -c0)
        raise NonQuadraticExpressionError(f"Unsupported unary operator: {node.op!r}")

    elif isinstance(node, BinaryOp):
        l2, l1, l0 = extract_quadratic_coefficients_host(
            node.left, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )
        r2, r1, r0 = extract_quadratic_coefficients_host(
            node.right, target_var, max_nodes, max_depth, max_bits, _current_depth + 1, _node_counter
        )

        for val in (l2, l1, l0, r2, r1, r0):
            if val.numerator.bit_length() > max_bits or val.denominator.bit_length() > max_bits:
                raise NonQuadraticExpressionError("Integer bit length exceeded before binary operation.")

        if node.op == "+":
            res2 = l2 + r2
            res1 = l1 + r1
            res0 = l0 + r0
        elif node.op == "-":
            res2 = l2 - r2
            res1 = l1 - r1
            res0 = l0 - r0
        elif node.op == "*":
            # Check Cauchy product terms for degree > 2
            deg4 = l2 * r2
            deg3 = l2 * r1 + l1 * r2
            if not deg4.is_zero or not deg3.is_zero:
                raise NonQuadraticExpressionError("Polynomial degree exceeds 2 in multiplication.")

            res2 = l2 * r0 + l1 * r1 + l0 * r2
            res1 = l1 * r0 + l0 * r1
            res0 = l0 * r0
        elif node.op == "/":
            if not r2.is_zero or not r1.is_zero:
                raise NonQuadraticExpressionError("Division by variable-dependent expression is not permitted.")
            if r0.is_zero:
                raise NonQuadraticExpressionError("Division by zero constant in expression.")
            res2 = l2 / r0
            res1 = l1 / r0
            res0 = l0 / r0
        else:
            raise NonQuadraticExpressionError(f"Unsupported binary operator: {node.op!r}")

        for res in (res2, res1, res0):
            if res.numerator.bit_length() > max_bits or res.denominator.bit_length() > max_bits:
                raise NonQuadraticExpressionError("Integer bit length exceeded after binary operation.")

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
            res2 = b1 * b1
            res1 = Rational(2) * b1 * b0
            res0 = b0 * b0
            for res in (res2, res1, res0):
                if res.numerator.bit_length() > max_bits or res.denominator.bit_length() > max_bits:
                    raise NonQuadraticExpressionError("Integer bit length exceeded after power operation.")
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
                raise NonQuadraticExpressionError("Integer bit length exceeded during constant power evaluation.")
            return (Rational(0), Rational(0), Rational(b0.numerator ** exp_val, b0.denominator ** exp_val))

    else:
        raise NonQuadraticExpressionError(f"Unsupported AST node type: {type(node).__name__}")


def reduce_equation_quadratic(
    eq_ast: Equation, target_var: str = "x"
) -> Tuple[Rational, Rational, Rational]:
    """Reduce Equation(LHS, RHS) to A*x^2 + B*x + C = 0 where A = l2 - r2, B = l1 - r1, C = l0 - r0."""
    l2, l1, l0 = extract_quadratic_coefficients_host(eq_ast.left, target_var)
    r2, r1, r0 = extract_quadratic_coefficients_host(eq_ast.right, target_var)
    return (l2 - r2, l1 - r1, l0 - r0)


def _parse_wire_rational(val: Any) -> Optional[Rational]:
    """Parse and validate wire rational dictionary {"numerator": "<str>", "denominator": "<str>"}.

    Rejects non-string digits, booleans, floats, negative denominators, and uncanonical representations.
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
        rat = Rational(num, den)
        # Canonical wire check: string must match reduced form
        if str(rat.numerator) != num_str or str(rat.denominator) != den_str:
            return None
        return rat
    except Exception:
        return None


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
            # Check quadratic capability
            try:
                host_A_quad, host_B_quad, host_C_quad = reduce_equation_quadratic(eq_ast, "x")
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

            # Degenerate quadratic with A == 0 (e.g. 0*x^2 + x = 1, x^2 - x^2 = 0)
            # Since it was not affine in AST, it must fail closed as REJECTED_SCOPE.
            if host_A_quad.is_zero:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.REJECTED_SCOPE,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            # True quadratic equation (A != 0). Compute discriminant.
            try:
                b_sq = host_B_quad * host_B_quad
                four_ac = Rational(4) * host_A_quad * host_C_quad
                host_delta = b_sq - four_ac
            except Exception:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.REJECTED_SCOPE,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.NOT_DISPATCHED,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_OUT_OF_SCOPE",
                )

            # If Δ > 0, verify rational square before worker dispatch
            if host_delta.numerator > 0:
                p = host_delta.numerator
                q = host_delta.denominator
                import math
                sp = math.isqrt(p)
                sq = math.isqrt(q)
                if sp * sp != p or sq * sq != q:
                    # Non-square positive discriminant -> irrational roots fail closed pre-dispatch
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.NOT_DISPATCHED,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION",
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

            # Step 7: Validate SOLVE Response Envelope & Wire Contract
            if not isinstance(solve_res, dict):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
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

            solve_outcome = solve_res.get("outcome")
            solve_status = solve_res.get("status")
            solve_classification = solve_res.get("classification")
            solve_definedness = solve_res.get("definedness")
            raw_root = solve_res.get("root")

            if solve_outcome == "RESOURCE_EXHAUSTED" or solve_status in ("WORKER_TIMEOUT", "ERR_RESOURCE_EXHAUSTED"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
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

            # Classification must strictly match status for successful SOLVE
            if solve_classification != solve_status:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Definedness must be True for SUCCESS
            if solve_definedness is not True:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            # Step 8: Verification Gate by Outcome Type
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

                # Mathematical contradiction guard:
                if host_A.is_zero:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                # Check expected root against host reduction
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

                # Step 8a: Candidate Membership Proof via CHECK_CANDIDATE
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
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
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

                check_outcome = check_res.get("outcome")
                check_status = check_res.get("status")

                if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_TIMEOUT", "ERR_RESOURCE_EXHAUSTED"):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
                    )

                exact_eq = check_res.get("exact_equality")
                defined = check_res.get("definedness")
                wire_residual = _parse_wire_rational(check_res.get("residual"))
                wire_cand = _parse_wire_rational(check_res.get("candidate"))

                # Contradictory evidence or invalid candidate
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

                # Verified unique root with complete mathematical proof
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

            # Fallback
            return ControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.ENGINE_ERROR,
                verification_status=VerificationStatus.VERIFICATION_FAILED,
                is_verified=False,
                error_code="ERR_SOLVER_FAILURE",
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

            if not isinstance(solve_res, dict):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            solve_outcome = solve_res.get("outcome")
            solve_status = solve_res.get("status")

            if solve_outcome == "RESOURCE_EXHAUSTED" or solve_status in ("WORKER_TIMEOUT", "ERR_RESOURCE_EXHAUSTED"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.TIMEOUT,
                    verification_status=VerificationStatus.NOT_APPLICABLE,
                    is_verified=False,
                    error_code="ERR_TIMEOUT",
                )

            if solve_status in ("WORKER_EXIT_FAILURE", "ERR_PAYLOAD_TOO_LARGE", "ERR_RESPONSE_LIMIT_EXCEEDED", "PROTOCOL_ERROR"):
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
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

            if solve_res.get("schema_version") != SCHEMA_VERSION_V2 or solve_res.get("operation") != OPERATION_SOLVE_QUADRATIC:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            if solve_outcome != "SUCCESS":
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_SOLVER_FAILURE",
                )

            if solve_res.get("definedness") is not True:
                return ControlledDispatchResult(
                    intake_status=IntakeStatus.VALIDATED,
                    intake_diagnostic=diagnostic,
                    execution_status=ExecutionStatus.ENGINE_ERROR,
                    verification_status=VerificationStatus.VERIFICATION_FAILED,
                    is_verified=False,
                    error_code="ERR_MALFORMED_WORKER_RESPONSE",
                )

            if solve_status not in ("NO_REAL_ROOT", "UNIQUE_REAL_ROOT", "TWO_DISTINCT_REAL_ROOTS"):
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
                return ControlledDispatchResult(
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
                expected_root = -host_B / (Rational(2) * host_A)
                if w_root != expected_root:
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
                    )

                # Vieta check
                if (Rational(2) * w_root != -host_B / host_A) or (w_root * w_root != host_C / host_A):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
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
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_MALFORMED_WORKER_RESPONSE",
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

                check_outcome = check_res.get("outcome")
                check_status = check_res.get("status")

                if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_TIMEOUT", "ERR_RESOURCE_EXHAUSTED"):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.TIMEOUT,
                        verification_status=VerificationStatus.NOT_APPLICABLE,
                        is_verified=False,
                        error_code="ERR_TIMEOUT",
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
                return ControlledDispatchResult(
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

                import math
                sp = math.isqrt(host_delta.numerator)
                sq = math.isqrt(host_delta.denominator)
                k = Rational(sp, sq)
                r1 = (-host_B - k) / (Rational(2) * host_A)
                r2 = (-host_B + k) / (Rational(2) * host_A)
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

                # Vieta checks
                if (w1 + w2 != -host_B / host_A) or (w1 * w2 != host_C / host_A):
                    return ControlledDispatchResult(
                        intake_status=IntakeStatus.VALIDATED,
                        intake_diagnostic=diagnostic,
                        execution_status=ExecutionStatus.SUCCESS,
                        verification_status=VerificationStatus.VERIFICATION_FAILED,
                        is_verified=False,
                        error_code="ERR_VERIFICATION_MISMATCH",
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
                            verification_status=VerificationStatus.VERIFICATION_FAILED,
                            is_verified=False,
                            error_code="ERR_MALFORMED_WORKER_RESPONSE",
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

                    check_outcome = check_res.get("outcome")
                    check_status = check_res.get("status")

                    if check_outcome == "RESOURCE_EXHAUSTED" or check_status in ("WORKER_TIMEOUT", "ERR_RESOURCE_EXHAUSTED"):
                        return ControlledDispatchResult(
                            intake_status=IntakeStatus.VALIDATED,
                            intake_diagnostic=diagnostic,
                            execution_status=ExecutionStatus.TIMEOUT,
                            verification_status=VerificationStatus.NOT_APPLICABLE,
                            is_verified=False,
                            error_code="ERR_TIMEOUT",
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
                return ControlledDispatchResult(
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
