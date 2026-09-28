"""Deterministic mathematical request router across registered CAS engines."""

from __future__ import annotations

import re
import time
import uuid
from typing import Optional, Union

from mke_product.parser.ast import ASTNode, Equation
from mke_product.parser.errors import (
    ImplicitMultiplicationError,
    InputBoundsExceededError,
    LexerError,
    MKEParserError,
    ParserError,
)
from .cas_parser import parse_cas_equation, parse_cas_expression
from .contracts import (
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    OperationType,
    SCHEMA_VERSION_P03A,
    VerificationStatus,
)
from .registry import EngineRegistry, get_engine_registry
from .safety import (
    ASTSafetyError,
    DivisionByZeroError,
    DomainRestrictionError,
    ExpressionBoundsError,
    SafetyError,
    check_input_bounds,
    extract_domain_restrictions,
    inspect_ast_safety,
)

FORBIDDEN_SECURITY_PATTERNS = [
    r"__",
    r"\bimport\b",
    r"\beval\b",
    r"\bexec\b",
    r"\bglobals\b",
    r"\blocals\b",
    r"\bopen\b",
    r"\bsystem\b",
    r"\bdef\b",
    r"\blambda\b",
    r"\bclass\b",
    r"\bos\b",
    r"\bsys\b",
    r"\bsubprocess\b",
]


class EngineRouter:
    """Deterministic mathematical engine dispatcher."""

    def __init__(self, registry: Optional[EngineRegistry] = None) -> None:
        self.registry = registry or get_engine_registry()

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Alias for route_and_execute."""
        return self.route_and_execute(request)

    def route_and_execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Route request to the most appropriate engine and execute."""
        start_time = time.monotonic()

        if not request.request_id:
            request.request_id = str(uuid.uuid4())

        input_str = request.raw_input or request.expression

        # 0. Check for malicious code injection patterns
        for pattern in FORBIDDEN_SECURITY_PATTERNS:
            if re.search(pattern, input_str):
                return ExecutionResponse(
                    schema_version=SCHEMA_VERSION_P03A,
                    request_id=request.request_id,
                    operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                    original_input=input_str,
                    selected_engine="security_guard",
                    mathematical_status=EngineStatus.SECURITY_REJECTED,
                    verification_status=VerificationStatus.ERROR,
                    error_message=f"Input rejected by security policy: forbidden pattern '{pattern}' detected.",
                    execution_duration_sec=time.monotonic() - start_time,
                )

        # 1. Check length bounds
        try:
            check_input_bounds(input_str)
        except ExpressionBoundsError as ex:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=input_str,
                selected_engine="security_guard",
                mathematical_status=EngineStatus.RESOURCE_EXHAUSTED,
                verification_status=VerificationStatus.ERROR,
                error_message=str(ex),
                execution_duration_sec=time.monotonic() - start_time,
            )

        # 2. Parse AST if needed
        try:
            if request.ast is None:
                if request.operation in {OperationType.SOLVE, OperationType.CHECK_CANDIDATE} and "=" in input_str:
                    request.ast = parse_cas_equation(input_str)
                else:
                    request.ast = parse_cas_expression(input_str)

            inspect_ast_safety(request.ast)

        except (InputBoundsExceededError, ExpressionBoundsError) as ex:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=input_str,
                selected_engine="router",
                mathematical_status=EngineStatus.RESOURCE_EXHAUSTED,
                verification_status=VerificationStatus.ERROR,
                error_message=str(ex),
                execution_duration_sec=time.monotonic() - start_time,
            )
        except (DomainRestrictionError, DivisionByZeroError) as ex:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=input_str,
                selected_engine="router",
                mathematical_status=EngineStatus.INVALID_INPUT,
                verification_status=VerificationStatus.ERROR,
                error_message=str(ex),
                warnings=[str(ex)],
                execution_duration_sec=time.monotonic() - start_time,
            )
        except (LexerError, ParserError) as ex:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=input_str,
                selected_engine="router",
                mathematical_status=EngineStatus.INVALID_INPUT,
                verification_status=VerificationStatus.ERROR,
                error_message=f"Syntax Error: {str(ex)}",
                execution_duration_sec=time.monotonic() - start_time,
            )
        except Exception as ex:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=input_str,
                selected_engine="router",
                mathematical_status=EngineStatus.INTERNAL_ERROR,
                verification_status=VerificationStatus.ERROR,
                error_message=f"Parser Error: {str(ex)}",
                execution_duration_sec=time.monotonic() - start_time,
            )

        # 3. Check for explicit engine override
        engine_override = request.options.get("engine_override") or request.preferred_engine
        if engine_override:
            engine = self.registry.get_engine(engine_override)
            if engine and engine.can_handle(request):
                return engine.execute(request)
            elif engine:
                # Fallback to SymPy if the requested engine cannot handle it
                sympy_engine = self.registry.get_engine("sympy_cas_v0")
                if sympy_engine and sympy_engine.can_handle(request):
                    return sympy_engine.execute(request)
                return ExecutionResponse(
                    schema_version=SCHEMA_VERSION_P03A,
                    request_id=request.request_id,
                    operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                    original_input=input_str,
                    selected_engine=engine_override,
                    mathematical_status=EngineStatus.OUT_OF_SCOPE,
                    verification_status=VerificationStatus.ERROR,
                    error_message=f"Engine '{engine_override}' cannot handle operation '{request.operation}'.",
                    execution_duration_sec=time.monotonic() - start_time,
                )
            else:
                return ExecutionResponse(
                    schema_version=SCHEMA_VERSION_P03A,
                    request_id=request.request_id,
                    operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                    original_input=input_str,
                    selected_engine=engine_override,
                    mathematical_status=EngineStatus.OUT_OF_SCOPE,
                    verification_status=VerificationStatus.ERROR,
                    error_message=f"Requested engine '{engine_override}' is not available or not installed.",
                    execution_duration_sec=time.monotonic() - start_time,
                )

        # 4. Deterministic Routing:
        # Prefer native formal MKE engine for linear equation solving
        native_engine = self.registry.get_engine("mke_native_v1")
        if native_engine and native_engine.can_handle(request):
            native_res = native_engine.execute(request)
            if native_res.status == EngineStatus.SUCCESS:
                return native_res

        # Fallback to SymPy for symbolic algebra, nonlinear, calculus, and plotting
        sympy_engine = self.registry.get_engine("sympy_cas_v0")
        if sympy_engine and sympy_engine.can_handle(request):
            return sympy_engine.execute(request)

        return ExecutionResponse(
            schema_version=SCHEMA_VERSION_P03A,
            request_id=request.request_id,
            operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
            original_input=input_str,
            selected_engine="none",
            mathematical_status=EngineStatus.OUT_OF_SCOPE,
            verification_status=VerificationStatus.ERROR,
            error_message=f"No available registered engine can handle operation '{request.operation}'.",
            execution_duration_sec=time.monotonic() - start_time,
        )


CASRouter = EngineRouter


def execute_cas_operation(
    request_or_op: Union[ExecutionRequest, OperationType, str],
    input_text: Optional[str] = None,
    *,
    variable: str = "x",
    options: Optional[dict] = None,
    preferred_engine: Optional[str] = None,
) -> ExecutionResponse:
    """Convenience entry point for executing CAS operations."""
    router = EngineRouter()
    if isinstance(request_or_op, ExecutionRequest):
        return router.route_and_execute(request_or_op)

    op_val = request_or_op
    if isinstance(op_val, str):
        op_val = OperationType(op_val.upper())

    req = ExecutionRequest(
        request_id=str(uuid.uuid4()),
        operation=op_val,
        raw_input=input_text or "",
        variable=variable,
        options=options or {},
        preferred_engine=preferred_engine,
    )
    return router.route_and_execute(req)
