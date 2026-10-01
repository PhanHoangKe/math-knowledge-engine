"""Versioned Algebra REST API router for MKE MVP V1."""

from typing import Union
from fastapi import APIRouter, Response, status
from mke_product.application.orchestrator import solve_request
from mke_product.application.dto import (
    SolveRequest,
    SolveResponseUnion,
    ErrorResponse,
)
from mke_product.application.errors import ApplicationErrorCode
from mke_product.transport.models import TransportErrorResponse, HealthResponse
from mke_product.domain.registry import MethodRegistry
from mke_product.application.traces import TRACE_GENERATORS

router = APIRouter(prefix="/api/v1", tags=["Algebra"])

INTERNAL_APPLICATION_CODES: frozenset[ApplicationErrorCode] = frozenset({
    ApplicationErrorCode.NORMALIZATION_ERROR,
    ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
    ApplicationErrorCode.METHOD_EXECUTION_FAILED,
    ApplicationErrorCode.VERIFICATION_FAILED,
    ApplicationErrorCode.INTERNAL_ERROR,
})


@router.post(
    "/algebra/solve",
    operation_id="solve_algebra_v1",
    response_model=SolveResponseUnion,
    responses={
        200: {"description": "Successful mathematical analysis or client domain error"},
        400: {"model": TransportErrorResponse, "description": "Malformed JSON payload"},
        413: {"model": TransportErrorResponse, "description": "Payload exceeds 64 KiB limit"},
        415: {"model": TransportErrorResponse, "description": "Unsupported Content-Type"},
        422: {"model": TransportErrorResponse, "description": "DTO schema validation failure"},
        500: {"model": Union[ErrorResponse, TransportErrorResponse], "description": "Internal application or transport failure"},
    },
)
async def solve_equation_endpoint(request: SolveRequest, response: Response) -> SolveResponseUnion:
    """Solve or analyze an algebraic equation via the pure S1 application service."""
    application_response = solve_request(request)

    # Category-B Internal Execution Failures map to HTTP 500 without mutating ErrorResponse body
    if isinstance(application_response, ErrorResponse):
        if application_response.error_code in INTERNAL_APPLICATION_CODES:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            response.status_code = status.HTTP_200_OK

    return application_response


@router.get(
    "/health",
    operation_id="health_v1",
    response_model=HealthResponse,
    responses={
        200: {"model": HealthResponse, "description": "System health and runtime registry metadata"},
    },
)
async def health_check_endpoint() -> HealthResponse:
    """Observational health check deriving counts dynamically from underlying domain registries."""
    registry = MethodRegistry()
    return HealthResponse(
        status="HEALTHY",
        version="1.0.0",
        milestone="MVP_V1_S2",
        algebra_authority="mke_product.application.orchestrator.solve_request",
        supported_input_modes=["RAW_TEXT", "COEFFICIENTS"],
        registered_methods_count=len(registry.list_all()),
        executable_methods_count=len(TRACE_GENERATORS),
    )
