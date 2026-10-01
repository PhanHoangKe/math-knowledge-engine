"""FastAPI Application factory and ASGI entrypoint for MKE Product Transport."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from mke_product.transport.routers.algebra import router as algebra_router
from mke_product.transport.handlers import (
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from mke_product.transport.middleware import (
    StreamPayloadLimitMiddleware,
    MediaTypeEnforcementMiddleware,
)


def create_app() -> FastAPI:
    """Create and configure the production FastAPI transport application."""
    fastapi_app = FastAPI(
        title="Math Knowledge Engine - Algebra Transport API",
        version="1.0.0",
        description="Production FastAPI transport adapter for MKE MVP V1 Algebra Workspace",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Register API routers
    fastapi_app.include_router(algebra_router)

    # Register centralized exception handlers
    fastapi_app.add_exception_handler(RequestValidationError, validation_exception_handler)
    fastapi_app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    fastapi_app.add_exception_handler(Exception, unhandled_exception_handler)

    # Register pure ASGI middlewares in correct outer wrapping order:
    # Outer: StreamPayloadLimitMiddleware -> MediaTypeEnforcementMiddleware -> FastAPI
    fastapi_app.add_middleware(MediaTypeEnforcementMiddleware)
    fastapi_app.add_middleware(StreamPayloadLimitMiddleware)

    return fastapi_app


app = create_app()
