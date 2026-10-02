"""Production composition ASGI application for Math Knowledge Engine (MKE) MVP V1.

Composes:
1. Accepted FastAPI Transport Application (/api/*, /openapi.json, /docs*, /redoc*) -> API authority
2. Built React Frontend Static Distribution (/ -> index.html, /assets/*, /vendor/*) -> StaticFiles
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from mke_product.transport.app import create_app as create_transport_app

# Default repository-local frontend distribution path: <repo>/src/frontend/dist
DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def get_frontend_dist_path() -> Path:
    """Resolve the frontend dist directory path with optional environment override support."""
    env_path = os.getenv("MKE_FRONTEND_DIST")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_FRONTEND_DIST


class MKEProductASGIApp:
    """Production ASGI dispatcher composing FastAPI transport and built React frontend."""

    def __init__(
        self,
        transport_app: Optional[ASGIApp] = None,
        frontend_dist_path: Optional[Path] = None,
    ) -> None:
        self.transport_app: ASGIApp = transport_app or create_transport_app()
        self.frontend_dist_path: Path = (
            frontend_dist_path if frontend_dist_path is not None else get_frontend_dist_path()
        )
        self._static_app: Optional[StaticFiles] = None

    def _get_static_app(self) -> Optional[StaticFiles]:
        """Lazily initialize StaticFiles handler when dist/index.html is verified to exist."""
        if not self.frontend_dist_path.is_dir() or not (self.frontend_dist_path / "index.html").is_file():
            return None
        if self._static_app is None:
            self._static_app = StaticFiles(
                directory=str(self.frontend_dist_path),
                html=True,
                check_dir=False,
            )
        return self._static_app

    @staticmethod
    def is_api_or_docs_path(path: str) -> bool:
        """Check if request path belongs strictly to the FastAPI transport app."""
        return (
            path == "/api"
            or path.startswith("/api/")
            or path == "/openapi.json"
            or path == "/docs"
            or path.startswith("/docs/")
            or path == "/redoc"
            or path.startswith("/redoc/")
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope_type = scope.get("type")

        if scope_type == "lifespan":
            await self.transport_app(scope, receive, send)
            return

        if scope_type == "http":
            path = scope.get("path", "")

            # 1. API and Docs routes are delegated unconditionally to FastAPI
            if self.is_api_or_docs_path(path):
                await self.transport_app(scope, receive, send)
                return

            # 2. Frontend / Static routes
            static_app = self._get_static_app()
            if static_app is None:
                response = PlainTextResponse(
                    "Frontend build not found. Run npm ci && npm run build in src/frontend.",
                    status_code=503,
                )
                await response(scope, receive, send)
                return

            try:
                await static_app(scope, receive, send)
            except StarletteHTTPException as exc:
                err_resp = PlainTextResponse(exc.detail or "Not Found", status_code=exc.status_code)
                await err_resp(scope, receive, send)
            return

        # For websocket or other protocols, delegate to transport app
        await self.transport_app(scope, receive, send)


def create_product_app(
    transport_app: Optional[ASGIApp] = None,
    frontend_dist_path: Optional[Path] = None,
) -> MKEProductASGIApp:
    """Factory creating the composite product ASGI application."""
    return MKEProductASGIApp(
        transport_app=transport_app,
        frontend_dist_path=frontend_dist_path,
    )


app = create_product_app()
