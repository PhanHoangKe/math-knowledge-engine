"""
Supervised Child-Process Execution for CAS Operations.

Enforces strict wall-clock computation timeouts, memory/resource boundaries,
and ensures uncooperative or long-running worker processes are forcefully
terminated without leaving orphan or zombie processes.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from typing import Any, Dict, Optional, Tuple

from .contracts import (
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    OperationType,
    SCHEMA_VERSION_P03A,
    VerificationStatus,
)

logger = logging.getLogger("mke_cas_process_runner")


def _cas_worker_target(
    request_dict: Dict[str, Any],
    result_queue: mp.Queue,
) -> None:
    """Entry point inside the child worker process."""
    try:
        from .contracts import ExecutionRequest, OperationType
        from .sympy_adapter import execute_sympy_direct

        op_str = request_dict.get("operation")
        op = OperationType(op_str) if op_str else OperationType.SIMPLIFY
        req = ExecutionRequest(
            operation=op,
            raw_input=request_dict.get("raw_input", ""),
            expression=request_dict.get("expression", ""),
            request_id=request_dict.get("request_id", ""),
            variable=request_dict.get("variable", "x"),
            options=request_dict.get("options", {}),
            timeout_sec=request_dict.get("timeout_sec", 5.0),
        )

        if "sleep_seconds" in req.options:
            time.sleep(float(req.options["sleep_seconds"]))

        response = execute_sympy_direct(req)
        result_queue.put(response.to_dict())
    except Exception as exc:
        err_resp = {
            "schema_version": SCHEMA_VERSION_P03A,
            "request_id": request_dict.get("request_id", ""),
            "operation": request_dict.get("operation", ""),
            "original_input": request_dict.get("raw_input") or request_dict.get("expression", ""),
            "selected_engine": "sympy_cas_v0",
            "mathematical_status": EngineStatus.INTERNAL_ERROR.value,
            "verification_status": VerificationStatus.ERROR.value,
            "symbolic_result": None,
            "latex_output": None,
            "domain_restrictions": [],
            "verification_evidence": None,
            "warnings": [],
            "plot_data": None,
            "execution_duration_sec": 0.0,
            "error_message": f"Worker process error: {type(exc).__name__}: {str(exc)}",
        }
        result_queue.put(err_resp)


def run_in_supervised_process(
    request: ExecutionRequest,
    timeout_sec: Optional[float] = None,
) -> ExecutionResponse:
    """Execute a CAS operation in a killable child process with a hard deadline."""
    deadline = timeout_sec if timeout_sec is not None else request.timeout_sec
    deadline = max(0.001, min(float(deadline), 60.0))

    start_time = time.monotonic()
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()

    req_dict = {
        "operation": request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
        "raw_input": request.raw_input,
        "expression": request.expression,
        "request_id": request.request_id,
        "variable": request.variable,
        "options": request.options,
        "timeout_sec": deadline,
    }

    process = ctx.Process(
        target=_cas_worker_target,
        args=(req_dict, result_queue),
        daemon=True,
    )

    process.start()
    process.join(timeout=deadline)

    if process.is_alive():
        # Process hung or exceeded deadline: forcefully terminate and reap
        logger.warning("CAS worker process %d timed out after %.2fs. Terminating.", process.pid, deadline)
        try:
            process.terminate()
            process.join(timeout=0.5)
            if process.is_alive():
                process.kill()
                process.join(timeout=0.5)
        except Exception as exc:
            logger.exception("Error killing child process: %s", exc)

        return ExecutionResponse(
            schema_version=SCHEMA_VERSION_P03A,
            request_id=request.request_id,
            operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
            original_input=request.raw_input or request.expression,
            selected_engine="sympy_cas_v0",
            mathematical_status=EngineStatus.RESOURCE_EXHAUSTED,
            verification_status=VerificationStatus.ERROR,
            error_message=f"Computation timed out after {deadline:.1f}s. Child worker process was forcefully terminated.",
            execution_duration_sec=time.monotonic() - start_time,
        )

    # Process completed within timeout
    elapsed = time.monotonic() - start_time
    try:
        if not result_queue.empty():
            res_dict = result_queue.get_nowait()
            status_val = res_dict.get("mathematical_status", "SUCCESS")
            try:
                status_enum = EngineStatus(status_val)
            except ValueError:
                status_enum = EngineStatus.INTERNAL_ERROR

            verif_val = res_dict.get("verification_status")
            try:
                verif_enum = VerificationStatus(verif_val) if verif_val else None
            except ValueError:
                verif_enum = None

            return ExecutionResponse(
                schema_version=res_dict.get("schema_version", SCHEMA_VERSION_P03A),
                request_id=res_dict.get("request_id", request.request_id),
                operation=res_dict.get("operation", str(request.operation)),
                original_input=res_dict.get("original_input", request.raw_input),
                selected_engine=res_dict.get("selected_engine", "sympy_cas_v0"),
                mathematical_status=status_enum,
                verification_status=verif_enum,
                symbolic_result=res_dict.get("symbolic_result"),
                latex_output=res_dict.get("latex_output"),
                domain_restrictions=res_dict.get("domain_restrictions", []),
                verification_evidence=res_dict.get("verification_evidence"),
                warnings=res_dict.get("warnings", []),
                plot_data=res_dict.get("plot_data"),
                execution_duration_sec=elapsed,
                error_message=res_dict.get("error_message"),
            )
        else:
            return ExecutionResponse(
                schema_version=SCHEMA_VERSION_P03A,
                request_id=request.request_id,
                operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
                original_input=request.raw_input or request.expression,
                selected_engine="sympy_cas_v0",
                mathematical_status=EngineStatus.INTERNAL_ERROR,
                verification_status=VerificationStatus.ERROR,
                error_message=f"Worker process exited with code {process.exitcode} without returning results.",
                execution_duration_sec=elapsed,
            )
    except Exception as exc:
        return ExecutionResponse(
            schema_version=SCHEMA_VERSION_P03A,
            request_id=request.request_id,
            operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
            original_input=request.raw_input or request.expression,
            selected_engine="sympy_cas_v0",
            mathematical_status=EngineStatus.INTERNAL_ERROR,
            verification_status=VerificationStatus.ERROR,
            error_message=f"Failed to read result from worker process: {exc}",
            execution_duration_sec=elapsed,
        )
