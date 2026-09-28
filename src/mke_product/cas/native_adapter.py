"""Native MKE solver adapter wrapping the formal verified kernel."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from mke_product.core.rational import Rational
from mke_product.parser.ast import ASTNode, BinaryOp, Equation, Power, Variable
from mke_product.parser.parser import parse_equation
from mke_product.solver.errors import OutOfScopeError, SolverError
from mke_product.solver.result import SolutionClassification, SolverScopeStatus
from mke_product.solver.solver import solve_equation
from .contracts import (
    EngineCapability,
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    MathEngine,
    OperationType,
    SCHEMA_VERSION_P03A,
)
from .cas_parser import CASPower
from .safety import extract_domain_restrictions, inspect_ast_safety


class NativeMKEAdapter(MathEngine):
    """Adapter for the native formal proof-producing MKE kernel."""

    ENGINE_ID = "mke_native_v1"

    @property
    def engine_id(self) -> str:
        return self.ENGINE_ID

    def get_capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.ENGINE_ID,
            engine_name="Native MKE Formal Kernel",
            version="1.0.0",
            license="Proprietary / MKE Product Core",
            supported_operations={
                OperationType.SOLVE,
                OperationType.CHECK_CANDIDATE,
            },
            is_installed=True,
            is_verified_kernel=True,
            description="Formal proof-producing deterministic solver for linear rational arithmetic equations.",
        )

    def can_handle(self, request: ExecutionRequest) -> bool:
        if request.operation not in {OperationType.SOLVE, OperationType.CHECK_CANDIDATE}:
            return False
        try:
            ast_node = request.ast
            if ast_node is None:
                if "=" not in (request.raw_input or request.expression):
                    return False
                from .cas_parser import parse_cas_equation
                ast_node = parse_cas_equation(request.raw_input or request.expression)
            if not isinstance(ast_node, Equation):
                return False
            # Check for non-linear powers (e.g. x^0, x^2, x^3) or variable denominators
            for n in ast_node.walk():
                if isinstance(n, (Power, CASPower)) and isinstance(n.base, Variable) and n.exponent.value != 1:
                    return False
                if isinstance(n, BinaryOp) and n.op == "/" and "x" in n.right.variables():
                    return False
            return True
        except Exception:
            return False

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        start_time = time.monotonic()
        response = ExecutionResponse(
            schema_version=SCHEMA_VERSION_P03A,
            request_id=request.request_id,
            operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
            original_input=request.raw_input,
            selected_engine=self.ENGINE_ID,
        )

        try:
            ast_node = request.ast
            if ast_node is None:
                ast_node = parse_equation(request.raw_input)

            inspect_ast_safety(ast_node)
            response.domain_restrictions = extract_domain_restrictions(ast_node)

            if not isinstance(ast_node, Equation):
                response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                response.error_message = "Native MKE solver requires an Equation AST."
                return response

            # Execute native solver
            solver_res = solve_equation(ast_node)

            if solver_res.status == SolverScopeStatus.IN_SCOPE:
                if solver_res.is_unique_root:
                    root_val = solver_res.root
                    response.mathematical_status = EngineStatus.SUCCESS
                    response.symbolic_result = f"{{{root_val}}}"
                    if root_val.denominator == 1:
                        response.latex_output = f"\\left\\{{ {root_val.numerator} \\right\\}}"
                    else:
                        response.latex_output = f"\\left\\{{ \\frac{{{root_val.numerator}}}{{{root_val.denominator}}} \\right\\}}"
                elif solver_res.is_all_reals:
                    response.mathematical_status = EngineStatus.SUCCESS
                    if response.domain_restrictions:
                        excluded_str = ", ".join(response.domain_restrictions)
                        response.symbolic_result = f"All real numbers except {excluded_str}"
                        response.latex_output = "\\mathbb{R} \\setminus \\{ " + ", ".join([r.replace("x != ", "") for r in response.domain_restrictions]) + " \\}"
                    else:
                        response.symbolic_result = "All real numbers"
                        response.latex_output = "\\mathbb{R}"
                elif solver_res.is_empty_set:
                    response.mathematical_status = EngineStatus.SUCCESS
                    response.symbolic_result = "{}"
                    response.latex_output = "\\emptyset"
            else:
                response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                response.error_message = solver_res.error_message or solver_res.error_code

            evidence_dict = solver_res.evidence.to_dict() if solver_res.evidence else {}
            if solver_res.is_unique_root and solver_res.root:
                evidence_dict["solution_set"] = [str(solver_res.root)]
            if "step_trace" in evidence_dict and "steps" not in evidence_dict:
                evidence_dict["steps"] = evidence_dict["step_trace"]
            response.verification_evidence = evidence_dict

        except OutOfScopeError as ex:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.error_message = f"Out of native linear scope: {str(ex)}"
        except Exception as ex:
            response.mathematical_status = EngineStatus.INTERNAL_ERROR
            response.error_message = f"{type(ex).__name__}: {str(ex)}"
        finally:
            response.execution_duration_sec = time.monotonic() - start_time

        return response
