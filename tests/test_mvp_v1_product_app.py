"""Contract and behavior tests for MKE MVP V1 Product Composition ASGI Application."""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from mke_product.product_app import create_product_app, DEFAULT_FRONTEND_DIST


@pytest.fixture
def product_client():
    """Client for product app using default built frontend dist."""
    app = create_product_app()
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# 1. FRONTEND STATIC SERVING (Requirements A & B)
# ============================================================================

def test_product_app_serves_frontend_root_index_html(product_client: TestClient):
    """GET / serves the built React index.html."""
    response = product_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert '<div id="root">' in response.text or "<!doctype html>" in response.text.lower()


def test_product_app_serves_known_frontend_asset(product_client: TestClient):
    """GET /assets/* serves built static JS/CSS assets without vacuous skips."""
    assets_dir = DEFAULT_FRONTEND_DIST / "assets"
    assert assets_dir.is_dir(), f"Frontend assets directory not found at {assets_dir}"
    asset_files = [f for f in assets_dir.iterdir() if f.is_file()]
    assert len(asset_files) > 0, f"No asset files found in {assets_dir}"
    asset_name = asset_files[0].name
    response = product_client.get(f"/assets/{asset_name}")
    assert response.status_code == 200
    assert len(response.content) > 0


def test_product_app_serves_katex_css_static_asset(product_client: TestClient):
    """GET /vendor/katex/katex.min.css returns HTTP 200 with CSS content type."""
    response = product_client.get("/vendor/katex/katex.min.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert ".katex" in response.text


def test_product_app_serves_katex_woff2_font_asset(product_client: TestClient):
    """GET /vendor/katex/fonts/KaTeX_Main-Regular.woff2 returns HTTP 200 with valid font/woff2 MIME."""
    response = product_client.get("/vendor/katex/fonts/KaTeX_Main-Regular.woff2")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "font/woff2" in content_type or "application/font-woff2" in content_type or "font" in content_type
    assert len(response.content) > 0


# ============================================================================
# 2. SAME-ORIGIN FASTAPI API DELEGATION (Requirements C & D)
# ============================================================================

def test_product_app_delegates_health_endpoint(product_client: TestClient):
    """GET /api/v1/health returns HTTP 200 with HEALTHY status from transport app."""
    response = product_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "1.0.0"
    assert data["milestone"] == "MVP_V1_S2"
    assert data["algebra_authority"] == "mke_product.application.orchestrator.solve_request"


def test_product_app_delegates_solve_endpoint(product_client: TestClient):
    """POST /api/v1/algebra/solve returns HTTP 200 with SOLVED result from S1 engine."""
    payload = {
        "input_payload": {
            "input_mode": "RAW_TEXT",
            "raw_query": "x^2 - 5*x + 6 = 0",
            "target_variable": "x",
        },
        "selected_method_id": None,
        "schema_version": "1.0.0",
    }
    response = product_client.post("/api/v1/algebra/solve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_status"] == "SOLVED"
    assert data["problem"]["classification"] == "QUADRATIC"
    assert len(data["solution"]["roots"]) == 2


# ============================================================================
# 3. STRUCTURED API 404 ISOLATION (Requirements E & F)
# ============================================================================

def test_product_app_unknown_api_get_returns_structured_404(product_client: TestClient):
    """Unknown GET /api/v1/* returns structured API 404, never swallowed by frontend."""
    response = product_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "API_NOT_FOUND"


def test_product_app_unknown_api_post_returns_structured_404(product_client: TestClient):
    """Unknown POST /api/v1/* returns structured API 404."""
    response = product_client.post("/api/v1/does-not-exist", json={"dummy": True})
    assert response.status_code == 404
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "API_NOT_FOUND"


# ============================================================================
# 4. TRANSPORT ERROR ENFORCEMENT ON SOLVE ROUTE (Requirements G, H, I)
# ============================================================================

def test_product_app_oversized_payload_returns_413(product_client: TestClient):
    """Declared body > 64 KiB on solve route returns HTTP 413 PAYLOAD_TOO_LARGE."""
    response = product_client.post(
        "/api/v1/algebra/solve",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": "65537"},
    )
    assert response.status_code == 413
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "PAYLOAD_TOO_LARGE"


def test_product_app_wrong_media_type_returns_415(product_client: TestClient):
    """Content-Type: text/plain on solve route returns HTTP 415 UNSUPPORTED_MEDIA_TYPE."""
    response = product_client.post(
        "/api/v1/algebra/solve",
        content=b"x^2 - 5*x + 6 = 0",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_product_app_malformed_json_returns_400(product_client: TestClient):
    """Malformed JSON payload on solve route returns HTTP 400 MALFORMED_JSON."""
    response = product_client.post(
        "/api/v1/algebra/solve",
        content=b'{"unclosed": ',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["transport_status"] == "ERROR"
    assert data["transport_error_code"] == "MALFORMED_JSON"


# ============================================================================
# 5. MISSING DIST RESILIENCE & PATH SECURITY (Requirements J & K)
# ============================================================================

def test_product_app_missing_dist_returns_safe_503(tmp_path: Path):
    """When frontend dist is missing, GET / returns safe HTTP 503 while /api remains operational."""
    empty_dist = tmp_path / "nonexistent_dist"
    app = create_product_app(frontend_dist_path=empty_dist)
    client = TestClient(app, raise_server_exceptions=False)

    # 1. Frontend root request returns safe 503
    root_resp = client.get("/")
    assert root_resp.status_code == 503
    assert "Frontend build not found" in root_resp.text
    assert "npm run build" in root_resp.text

    # 2. API endpoints remain 100% operational
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "HEALTHY"


def test_product_app_path_traversal_protection(product_client: TestClient):
    """Path traversal attempts cannot escape the configured frontend dist root."""
    traversal_paths = [
        "/../../etc/passwd",
        "/..\\..\\windows\\system32",
        "/static/../../mke_product/product_app.py",
    ]
    for path in traversal_paths:
        response = product_client.get(path)
        # Must return 404 or 400, never leaking source files
        assert response.status_code in (400, 404)
        assert "MKEProductASGIApp" not in response.text


# ============================================================================
# 6. OPENAPI SCHEMA PURITY & AUTHORITY ISOLATION (Section 12 & 13)
# ============================================================================

def test_product_app_openapi_endpoint_unchanged(product_client: TestClient):
    """GET /openapi.json delegates directly to transport app without contamination."""
    response = product_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/algebra/solve" in spec["paths"]
    assert "/api/v1/health" in spec["paths"]
    # Static routes MUST NOT contaminate OpenAPI spec
    assert "/" not in spec["paths"]
    assert "/assets" not in spec["paths"]


def test_product_app_contains_no_mathematics():
    """Static inspection verifying zero CAS or mathematical authority in product_app module."""
    import mke_product.product_app as prod_mod
    import inspect

    source = inspect.getsource(prod_mod)
    forbidden_symbols = [
        "sympy",
        "solve_request",
        "discriminant",
        "solve_quadratic",
        "CASRouter",
        "MethodRegistry",
        "RationalValue",
    ]
    for symbol in forbidden_symbols:
        assert symbol not in source, f"Forbidden symbol '{symbol}' detected in product_app.py"


def test_product_app_delegates_docs_and_redoc_endpoints(product_client: TestClient):
    """GET /docs and /redoc return HTTP 200 from FastAPI transport layer."""
    docs_resp = product_client.get("/docs")
    assert docs_resp.status_code == 200
    assert "text/html" in docs_resp.headers.get("content-type", "")

    redoc_resp = product_client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "text/html" in redoc_resp.headers.get("content-type", "")

