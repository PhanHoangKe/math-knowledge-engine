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
from typing import Any, Dict, Optional, Tuple, Union
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
    SCHEMA_VERSION,
)


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
    solution_type: Optional[str] = Field(default=None, description="'UNIQUE_ROOT', 'ALL_REALS', 'EMPTY_SET', or None")
    verified_root: Optional[RationalRoot] = Field(default=None, description="Exact rational root if unique solution verified")
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
            syntax_issue_codes = {
                "SYNTAX_ERROR",
                "INVALID_CHARSET",
                "NESTING_DEPTH_EXCEEDED",
                "INVALID_PRIMARY_EXPRESSION",
                "BRACKET_MISMATCH",
                "UNBALANCED_PARENTHESES",
                "RAW_QUERY_MISMATCH",
            }
            is_syntax = (
                validation.status == "INVALID"
                or any(iss.code in syntax_issue_codes for iss in validation.issues)
            )
            return ControlledDispatchResult(
                intake_status=IntakeStatus.REJECTED_SYNTAX if is_syntax else IntakeStatus.REJECTED_SCOPE,
                intake_diagnostic=diagnostic,
                execution_status=ExecutionStatus.NOT_DISPATCHED,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                is_verified=False,
                error_code="ERR_INTAKE_SYNTAX_INVALID" if is_syntax else "ERR_INTAKE_SCOPE_UNSUPPORTED",
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

        # Step 4: Host AST Syntax & Pre-Dispatch Affine Linearity Check
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

        try:
            host_A, host_B = reduce_equation_affine(eq_ast, "x")
        except NonAffineExpressionError:
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
            "schema_version": SCHEMA_VERSION,
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

        if solve_res.get("schema_version") != SCHEMA_VERSION or solve_res.get("operation") != OPERATION_SOLVE:
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
            # If host proof reduced A == 0, claiming UNIQUE_ROOT contradicts the host proof!
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
                "schema_version": SCHEMA_VERSION,
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

            if check_res.get("schema_version") != SCHEMA_VERSION or check_res.get("operation") != OPERATION_CHECK_CANDIDATE:
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
