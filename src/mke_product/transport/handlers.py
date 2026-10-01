"""FastAPI centralized exception handlers for transport errors."""

from typing import Any, Dict, List
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from mke_product.transport.models import TransportErrorCode, TransportErrorResponse


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors, separating malformed JSON (400) from DTO schema violations (422)."""
    # 1. Check if error is due to malformed JSON body
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            error_response = TransportErrorResponse(
                transport_error_code=TransportErrorCode.MALFORMED_JSON,
                message_vi="Định dạng JSON trong yêu cầu không hợp lệ.",
                message_en="Malformed JSON request body.",
                details={"error_type": "json_invalid", "loc": list(err.get("loc", []))},
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response.model_dump(mode="json"),
            )

    # 2. Sanitize validation errors: include ONLY safe fields (type, loc, msg)
    # Exclude raw request input, ctx, url, exception instances, and unparsed sentinels
    sanitized_errors: List[Dict[str, Any]] = [
        {
            "type": e.get("type"),
            "loc": list(e.get("loc", [])),
            "msg": e.get("msg"),
        }
        for e in exc.errors()
    ]

    error_response = TransportErrorResponse(
        transport_error_code=TransportErrorCode.REQUEST_VALIDATION_FAILED,
        message_vi="Dữ liệu yêu cầu không khớp với schema định nghĩa.",
        message_en="Request body failed schema validation.",
        details={"validation_errors": sanitized_errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions such as 404 on API paths."""
    if request.url.path.startswith("/api/") and exc.status_code == status.HTTP_404_NOT_FOUND:
        error_response = TransportErrorResponse(
            transport_error_code=TransportErrorCode.API_NOT_FOUND,
            message_vi="Endpoint API không tồn tại.",
            message_en="API endpoint not found.",
            details={"path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response.model_dump(mode="json"),
        )

    # Generic HTTP exception fallback (strictly sanitized, zero exc.detail / traceback leakage)
    error_response = TransportErrorResponse(
        transport_error_code=TransportErrorCode.INTERNAL_TRANSPORT_ERROR,
        message_vi="Lỗi yêu cầu HTTP.",
        message_en="HTTP request error.",
        details={"status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all unhandled exception handler returning sanitized HTTP 500 without leaking stack traces."""
    error_response = TransportErrorResponse(
        transport_error_code=TransportErrorCode.INTERNAL_TRANSPORT_ERROR,
        message_vi="Đã xảy ra lỗi máy chủ nội bộ trong quá trình truyền tải.",
        message_en="An internal server error occurred in the transport layer.",
        details={},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )
