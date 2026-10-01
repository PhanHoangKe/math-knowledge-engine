# MKE MVP V1 — S2-P0-R2 Transport & Live Math Workspace Integration Preflight Specification

**Document Version:** 1.2.0 (R2 Final Wire-Contract & Transport-Taxonomy Closeout)  
**Milestone:** MVP V1 — Stage S2 Preflight Architecture  
**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Accepted S1 Baseline:** `3058b6e904f38003a650a79105ae615226bdbc17`  
**Parent S2-P0-R1 Baseline:** `93d5599c4b9a8cbdfe569133e988bcffc3074e30`  
**Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (UNTOUCHED)  
**Status:** **`PENDING INDEPENDENT S2-P0-R2 FINAL AUDIT`**

---

## 1. Executive Summary & Audited Repository Reality

The S1 milestone established an accepted, 100% deterministic Pure Python Application Service boundary:
```
SolveRequest (RAW_TEXT | COEFFICIENTS)
   ↳ solve_request()
      ↳ Normalizer / IR Gate (QuadraticProblemIR | DegenerateEquationIR)
         ↳ Degenerate Verifier (a == 0) | Method Registry & Traces (a != 0)
            ↳ Host Independent Verifier
               ↳ SolveResponseUnion (SOLVED | ANALYZED_NO_EXECUTION | ERROR)
```

### Audited Repository Reality:
1. **Frontend Assets (`ui/ui00/`):**
   - Implemented in vanilla HTML5, CSS3, and ES6 JavaScript (`ui/ui00/index.html`, `ui/ui00/styles.css`, `ui/ui00/app.js`).
   - Governed by design tokens in `ui/ui00/DESIGN_TOKENS.md` (WolframAlpha-inspired clean aesthetic, light/charcoal-dark themes, Vietnamese/English bilingual toggle, offline-vendored KaTeX math rendering).
   - Currently connects to legacy endpoints (`/api/health`, `/api/execute`, `/api/plot`) with legacy multi-engine assumptions.
2. **Current Legacy Server (`src/mke_product/cas/demo_server.py`):**
   - Built on standard library `http.server.BaseHTTPRequestHandler` / `ThreadingHTTPServer`.
   - Serves static assets from `ui/ui00/` and handles `POST /api/execute` / `POST /api/plot` via `CASRouter`.
   - Contains security/transport debt: manual socket timeout chunking loops and direct string interpolation of internal exceptions into JSON error messages (`f"Invalid JSON payload: {exc}"`).
   - Does **not** expose or connect to the accepted S1 application orchestrator `solve_request()`.
   - In S2, `demo_server.py` is strictly a standalone legacy dev server and will **never** be used by the production workspace.
3. **Dependencies (`requirements.txt` & Strategy):**
   - Base `requirements.txt` declares `pydantic>=2.6.0,<3.0.0`, `pytest>=7.0.0`, `sympy>=1.12`, `mpmath>=1.3.0`.
   - S2 production server will add `fastapi>=0.110.0,<1.0.0` and `uvicorn[standard]>=0.28.0,<1.0.0` to `requirements.txt` in S2-01.
   - S2 test suite will introduce `requirements-dev.txt` declaring `httpx>=0.27.0` for in-memory ASGI `TestClient` verification.
4. **S1 Authority Entry Point:**
   - Exclusively `mke_product.application.orchestrator.solve_request(req: SolveRequest) -> SolveResponseUnion`.
   - Strict Pydantic v2 discriminated union models in `mke_product.application.dto`.

The purpose of Stage S2 is to establish a high-fidelity, type-safe HTTP transport layer and a reactive live algebra workspace that binds directly to S1 mathematical authority without mathematical regression, shadow schema drift, or CAS bypass.

---

## 2. Legacy Server & API Inventory

The existing server endpoints in `src/mke_product/cas/demo_server.py` serve the following roles:

| Endpoint | Method | Underlying Authority | Current Status & Role in S2 |
| :--- | :--- | :--- | :--- |
| `/`, `/index.html`, `/styles.css`, `/app.js`, `/vendor/*` | `GET` | Static file serving (`UI_DIR = ui/ui00`) | Legacy static files; S2 production server serves React SPA |
| `/api/health` | `GET` | Hardcoded JSON dictionary in `demo_server.py` | Legacy dev health check; S2 introduces `/api/v1/health` |
| `/api/execute` | `POST` | Legacy `CASRouter.execute_cas_operation` (`mke_native_v1` + `sympy_cas_v0`) | Legacy CAS operations (`SIMPLIFY`, `DIFFERENTIATE`, `INTEGRATE`); segregated from S1 Algebra |
| `/api/plot` | `POST` | Legacy `CASRouter` with `default_op="PLOT_2D"` | Legacy 2D function plotter; segregated from S1 quadratic workspace |

### Authority Separation & Production Role Mandate:
- The S2 production server is a dedicated FastAPI application exposing `/api/v1/algebra/solve`, `/api/v1/health`, OpenAPI documentation, and the compiled React Single-Page Application (SPA).
- The S2 Live Algebra Workspace will **never** invoke `/api/execute` or `/api/plot`.
- Legacy CAS routes remain available solely in `demo_server.py` for legacy symbolic tests and will never act as a fallback or override for S1 quadratic solving.
- Operations from legacy CAS such as `SIMPLIFY`, `DIFFERENTIATE`, `INTEGRATE`, and `PLOT_2D` are visibly marked as "Deferred / Under Construction" or disabled in the S2 Algebra Workspace to preserve focus on verified quadratic algebra.

---

## 3. Transport Architecture Comparison & Selection

We evaluate three candidate transport architectures:

```
                    ┌──────────────────────────────────────────────┐
                    │            Transport Alternatives            │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼────────────────────────────────┐
         ▼                                 ▼                                ▼
  [ Option A ]                      [ Option B ]                     [ Option C ]
BaseHTTPRequestHandler              FastAPI (ASGI)                   Flask / WSGI
- Standard library only            - Native Pydantic v2 SSOT         - Synchronous WSGI
- Manual socket buffer chunking    - Auto OpenAPI 3.1 & Swagger UI   - Manual Pydantic integration
- Manual JSON parsing & schema     - Built-in CORS, DI, lifespan     - No native async / typed schema
- String exception leaks           - Strict discriminated unions     - Extra adapter boilerplate
- High maintenance overhead        - High testability (TestClient)   - Medium maintenance overhead
```

### Detailed Evaluation Matrix:

| Evaluation Dimension | Option A: Extend `demo_server.py` (Standard Library) | Option B: Introduce FastAPI + Uvicorn (Recommended) | Option C: Introduce Flask / WSGI |
| :--- | :--- | :--- | :--- |
| **Contract Fidelity** | High risk of manual serialization drift | **Native Pydantic v2 Single Source of Truth (SSOT)** | Requires manual Pydantic adapter |
| **Discriminated Unions** | Manual parsing and `if/elif` branching | **Native polymorphic validation & discriminator routing** | Manual discriminator validation |
| **OpenAPI / Schema** | None (manual documentation) | **Automatic OpenAPI 3.1 & Interactive `/docs`** | Requires third-party extensions |
| **Request Validation** | Manual header, payload, and limit checks | **Automatic declarative body validation & custom handlers** | Manual validation decorators |
| **Error Sanitization** | High risk of string exception leakage | **Centralized exception handlers & zero internal leaks** | Requires custom error handlers |
| **Testability** | Requires socket binding & live thread fixtures | **In-memory `starlette.testclient.TestClient` (fast, deterministic)** | `Flask.test_client` (WSGI) |
| **CORS & Middleware** | Manual header injection on every response | **Standard `CORSMiddleware` & security headers** | Requires `flask-cors` |
| **Maintenance Burden** | High (custom socket loop, buffer management) | **Low (declarative routers, industry standard)** | Medium |
| **Migration Risk** | Low external dependency addition | **Zero mathematical risk; isolated transport adapter** | Medium |
| **Legacy CAS Compatibility** | Native | **Legacy endpoints isolated; zero production coupling** | Compatible |

### Architectural Decision:
**Adopt Option B (FastAPI + Uvicorn)** as the production transport adapter for MKE MVP V1.
- `requirements.txt` will add `fastapi>=0.110.0,<1.0.0` and `uvicorn[standard]>=0.28.0,<1.0.0` in S2-01.
- `requirements-dev.txt` will declare `httpx>=0.27.0` for in-memory testing.
- Existing `demo_server.py` is retained strictly for standalone legacy dev compatibility.

---

## 4. Route Namespace, Static Precedence & Health Contract

To prevent namespace collisions and routing ambiguities, S2 establishes an explicit routing topology:

```
Route Precedence Order (Top to Bottom):
1. /api/v1/algebra/solve      [POST]  -> S1 Pure Python solve_request() entry point
2. /api/v1/health             [GET]   -> Observational system health & engine capabilities
3. /docs, /redoc, /openapi.json [GET] -> OpenAPI 3.1 schemas & interactive documentation
4. /assets/*, /vendor/*, favicon.ico  -> Static asset mounts
5. /* (Excluding /api/*)      [GET]   -> SPA Fallback (index.html)
```

> [!CRITICAL]
> **API 404 vs SPA Fallback Rule:** Requests matching `/api/*` that do not resolve to a registered endpoint MUST return JSON `404 Not Found` with a structured `TransportErrorResponse` envelope. They MUST NEVER fall back to `index.html`.

### 4.1 Route Specification: `POST /api/v1/algebra/solve`
- **Request Body:** Direct JSON representation of `SolveRequest`.
- **Response Body:** Direct JSON representation of `SolveResponseUnion` (`SolvedResponse` | `AnalyzedNoExecutionResponse` | `ErrorResponse`).
- **Transport Execution Policy:**
  ```python
  @router.post(
      "/algebra/solve",
      response_model=SolveResponseUnion,
      responses={
          200: {"description": "Successful mathematical analysis or client domain error"},
          400: {"model": TransportErrorResponse, "description": "Malformed JSON payload"},
          413: {"model": TransportErrorResponse, "description": "Payload exceeds 64 KiB limit"},
          415: {"model": TransportErrorResponse, "description": "Unsupported Content-Type"},
          422: {"model": TransportErrorResponse, "description": "DTO schema validation failure"},
          500: {"model": Union[ErrorResponse, TransportErrorResponse], "description": "Internal server failure"},
      },
  )
  async def solve_equation_endpoint(request: SolveRequest) -> SolveResponseUnion:
      # Direct delegation to pure application service — ZERO transport re-solving
      return solve_request(request)
  ```
- **Invariants:**
  - Zero SymPy/CAS fallback inside this route.
  - Zero mathematical solver or AST parsing duplicated in route handler.
  - Zero method-selection logic in transport layer.

### 4.2 Route Specification: `GET /api/v1/health`
Health metadata is derived **dynamically** from the underlying domain registries at runtime:
```python
@router.get("/health", response_model=HealthResponse)
async def health_check_endpoint() -> HealthResponse:
    from mke_product.domain.registry import MethodRegistry
    from mke_product.application.traces import TRACE_GENERATORS

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
```

**Health Response Payload Example (Illustrative observed values):**
```json
{
  "status": "HEALTHY",
  "version": "1.0.0",
  "milestone": "MVP_V1_S2",
  "algebra_authority": "mke_product.application.orchestrator.solve_request",
  "supported_input_modes": ["RAW_TEXT", "COEFFICIENTS"],
  "registered_methods_count": 9,
  "executable_methods_count": 4
}
```

---

## 5. HTTP Status Semantics, Error Mapping Policy & Transport Taxonomy

Transport status codes strictly distinguish between **Transport Failures (4xx / 500 Transport)**, **Application Domain Outcomes (Category A $\to$ HTTP 200)**, and **Internal Integrity / Execution Failures (Category B $\to$ HTTP 500 Application)**:

```
                                ┌─────────────────────────────┐
                                │   Incoming HTTP Request     │
                                └──────────────┬──────────────┘
                                               │
                      ┌────────────────────────┴────────────────────────┐
                      ▼                                                 ▼
              [ Valid Request Body ]                          [ Transport / Schema Error ]
                      │                                                 │
           solve_request(SolveRequest)                        ┌─────────┼─────────┬─────────┐
                      │                                       ▼         ▼         ▼         ▼
        ┌─────────────┼─────────────┐                      Bad JSON  Too Large Bad Media Validation
        ▼             ▼             ▼                      HTTP 400  HTTP 413  HTTP 415  HTTP 422
     SOLVED        ANALYZED       ERROR                    (Syntax)  (>64KiB)  (!=json)  (Schema)
    HTTP 200       HTTP 200      ┌──┴──┐                      │         │         │         │
   (Verified)     (Degenerate/   │     │                      └─────────┴────┬────┴─────────┘
                  Unavailable)   ▼     ▼                                     ▼
                            Category A Category B                  TransportErrorResponse
                            HTTP 200   HTTP 500
                            (Client)   (Internal)
                               │          │
                               ▼          ▼
                        SolveResponse  ErrorResponse
```

### 5.1 Transport Error Taxonomy

To prevent namespace contamination between mathematical errors and HTTP transport failures, S2 freezes a dedicated `TransportErrorResponse` schema:

```python
class TransportErrorCode(str, Enum):
    MALFORMED_JSON = "MALFORMED_JSON"
    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    API_NOT_FOUND = "API_NOT_FOUND"
    INTERNAL_TRANSPORT_ERROR = "INTERNAL_TRANSPORT_ERROR"


class TransportErrorResponse(BaseModel):
    transport_status: Literal["ERROR"] = "ERROR"
    transport_error_code: str
    message_vi: str
    message_en: str
    details: Optional[Dict[str, Any]] = None
```

### 5.2 Transport & Application Error Matrix:

| Category | Trigger / Condition | HTTP Status | Response Schema | Description & Client Handling |
| :--- | :--- | :--- | :--- | :--- |
| **Mathematical Success** | `response_status="SOLVED"` | `200 OK` | `SolvedResponse` | Solved & verified; render solution card, roots, and trace |
| **Mathematical Analysis** | `response_status="ANALYZED_NO_EXECUTION"` | `200 OK` | `AnalyzedNoExecutionResponse` | Degenerate ($a=0$) or deferred method; render explanation |
| **Category A: Client Domain Error** | `SYNTAX_ERROR`<br>`UNSUPPORTED_VARIABLE`<br>`UNSUPPORTED_SYNTAX`<br>`IMPLICIT_MULTIPLICATION_UNSUPPORTED`<br>`DEGREE_OUT_OF_SCOPE`<br>`NON_POLYNOMIAL_INPUT`<br>`DIVISION_BY_ZERO`<br>`INPUT_LIMIT_EXCEEDED`<br>`METHOD_NOT_FOUND` | `200 OK` | `ErrorResponse` | Mathematical/input errors caused by client query; render inline error panel with error code and span highlight |
| **Category B: Internal Application Failure** | `NORMALIZATION_ERROR` (internal)<br>`DOMAIN_CONTRACT_ERROR`<br>`METHOD_EXECUTION_FAILED`<br>`VERIFICATION_FAILED`<br>`INTERNAL_ERROR` | `500 Internal Server Error` | `ErrorResponse` (sanitized) | Engine invariant violation or internal execution failure; render server error banner without leaking internal stack trace |
| **Transport: Malformed JSON** | JSON body parse failure (`json_invalid`) | `400 Bad Request` | `TransportErrorResponse` (`MALFORMED_JSON`) | Body is not valid JSON; custom exception handler returns HTTP 400 |
| **Transport: Schema Validation** | Pydantic `ValidationError` | `422 Unprocessable Entity` | `TransportErrorResponse` (`REQUEST_VALIDATION_FAILED`) | Request body does not conform to `SolveRequest` schema |
| **Transport: Payload Exceeded** | Cumulative stream body > 65,536 bytes | `413 Payload Too Large` | `TransportErrorResponse` (`PAYLOAD_TOO_LARGE`) | Payload exceeds 64 KiB limit |
| **Transport: Unsupported Media** | `Content-Type` is not `application/json` | `415 Unsupported Media Type` | `TransportErrorResponse` (`UNSUPPORTED_MEDIA_TYPE`) | Media type rejected before body processing |
| **Transport: Unknown API Route** | Nonexistent `/api/*` route | `404 Not Found` | `TransportErrorResponse` (`API_NOT_FOUND`) | API route not found (isolated from SPA fallback) |
| **Transport: Internal Transport Error** | Unhandled middleware / ASGI crash | `500 Internal Server Error` | `TransportErrorResponse` (`INTERNAL_TRANSPORT_ERROR`) | Transport-level exception before application orchestrator |

### 5.3 Malformed JSON vs Schema Validation Exception Handlers:
FastAPI by default groups JSON parse errors and Pydantic validation errors under `RequestValidationError` (returning HTTP 422). S2 implements a custom exception handler:
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Check if any error is due to malformed JSON body
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            return JSONResponse(
                status_code=400,
                content=TransportErrorResponse(
                    transport_error_code=TransportErrorCode.MALFORMED_JSON.value,
                    message_vi="Định dạng JSON trong yêu cầu không hợp lệ.",
                    message_en="Malformed JSON request body.",
                    details={"error_type": "json_invalid", "loc": err.get("loc")},
                ).model_dump(mode="json"),
            )
    # Standard Pydantic schema validation failures return HTTP 422 with normalized TransportErrorResponse
    return JSONResponse(
        status_code=422,
        content=TransportErrorResponse(
            transport_error_code=TransportErrorCode.REQUEST_VALIDATION_FAILED.value,
            message_vi="Dữ liệu yêu cầu không khớp với schema định nghĩa.",
            message_en="Request body failed schema validation.",
            details={"validation_errors": exc.errors()},
        ).model_dump(mode="json"),
    )
```

### 5.4 Pure ASGI Streaming 64 KiB Payload Limit Middleware:
To prevent memory exhaustion without buffering unbounded bodies, S2 implements a pure ASGI middleware wrapping the `receive` callable:
```python
class StreamPayloadLimitMiddleware:
    MAX_BYTES = 65536  # 64 KiB

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length_raw = headers.get(b"content-length")

        # 1. Early rejection when Content-Length header is present and > 65536
        if content_length_raw:
            try:
                if int(content_length_raw.decode("latin1")) > self.MAX_BYTES:
                    await self._send_413_response(send)
                    return
            except ValueError:
                pass

        # 2. Wrap receive callable with byte accumulator for streaming/chunked requests
        cumulative_bytes = 0

        async def limited_receive() -> Message:
            nonlocal cumulative_bytes
            message = await receive()
            if message["type"] == "http.request":
                body_chunk = message.get("body", b"")
                cumulative_bytes += len(body_chunk)
                if cumulative_bytes > self.MAX_BYTES:
                    # Short-circuit without loading unbounded body
                    raise PayloadTooLargeException()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except PayloadTooLargeException:
            await self._send_413_response(send)

    async def _send_413_response(self, send: Send) -> None:
        payload = TransportErrorResponse(
            transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE.value,
            message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
            message_en="Request payload exceeds 64 KiB limit.",
            details={"limit_bytes": self.MAX_BYTES},
        ).model_dump(mode="json")
        body = json.dumps(payload).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin1")),
            ],
        })
        await send({"type": "http.response.body", "body": body})
```

### 5.5 Content-Type Header Parsing & Media-Type Enforcement:
For all POST requests under `/api/`, the `Content-Type` header is extracted, stripped of parameters, and checked:
```python
def extract_media_type(raw_header: str) -> str:
    # Extracts portion before first ';', trimmed and lowercased
    return raw_header.split(";")[0].strip().lower()

class MediaTypeEnforcementMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"].startswith("/api/"):
            headers = dict(scope.get("headers", []))
            raw_content_type = headers.get(b"content-type", b"").decode("latin1")
            media_type = extract_media_type(raw_content_type)

            # Accept strictly "application/json" (with optional parameters such as charset)
            if media_type != "application/json":
                payload = TransportErrorResponse(
                    transport_error_code=TransportErrorCode.UNSUPPORTED_MEDIA_TYPE.value,
                    message_vi="Tiêu đề Content-Type phải là 'application/json'.",
                    message_en="Content-Type header must be 'application/json'.",
                    details={"received_content_type": raw_content_type},
                ).model_dump(mode="json")
                body = json.dumps(payload).encode("utf-8")

                await send({
                    "type": "http.response.start",
                    "status": 415,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("latin1")),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)
```

> [!NOTE]
> **Media Type Policy for MVP V1:** `application/*+json` is explicitly unsupported for S2. Requests must specify `Content-Type: application/json` (with optional parameters like `charset=utf-8`).

---

## 6. DTO JSON Contract & Exact Serialization Specification

The DTO models in `mke_product.application.dto` serve as the Single Source of Truth (SSOT).

### Contract Formatting Rules:
- `semantic_revision_hash`: Raw 64-character SHA-256 lowercase hex string (e.g. `"8f4a1c0d2e3b4a5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"`). **No `sha256_` prefix**.
- `problem_id`: `"prob_" + semantic_revision_hash[:16]` (e.g. `"prob_8f4a1c0d2e3b4a5c"`).
- `certificate_id`: Exact 16 lowercase hex characters without `"cert_"` prefix:
  - Quadratic: `SHA256("cert:" + problem_hash + ":" + cert_sig).hexdigest()[:16]`
  - Degenerate: `SHA256("cert:degenerate:" + problem_hash + ":" + cert_sig).hexdigest()[:16]`
- `verified_at_utc`: Pydantic ISO-8601 UTC timestamp generated from naive `datetime.utcnow()` without trailing `Z` suffix (e.g. `"2026-10-01T22:00:00"`). Preserved in S2 transport without mutation.
- `available_methods`: Array of 9 `MethodOptionView` entries for quadratic equations, empty for degenerate equations.

### 6.1 Request JSON Payloads

#### A. RAW_TEXT Mode:
```json
{
  "input_payload": {
    "input_mode": "RAW_TEXT",
    "raw_query": "x^2 - 5*x + 6 = 0",
    "target_variable": "x"
  },
  "selected_method_id": null,
  "schema_version": "1.0.0"
}
```

#### B. COEFFICIENTS Mode:
```json
{
  "input_payload": {
    "input_mode": "COEFFICIENTS",
    "a": {"numerator": 1, "denominator": 1},
    "b": {"numerator": -5, "denominator": 1},
    "c": {"numerator": 6, "denominator": 1},
    "target_variable": "x"
  },
  "selected_method_id": "QUAD_FORMULA_REDUCED",
  "schema_version": "1.0.0"
}
```

### 6.2 Response JSON Payloads

#### A. SOLVED Response Example:
```json
{
  "response_status": "SOLVED",
  "problem": {
    "problem_type": "QUADRATIC",
    "problem_id": "prob_8f4a1c0d2e3b4a5c",
    "raw_query": "x^2 - 5*x + 6 = 0",
    "equation_latex": "x^2 - 5x + 6 = 0",
    "category": "ALGEBRA_QUADRATIC",
    "classification": "QUADRATIC",
    "a": {"numerator": 1, "denominator": 1},
    "b": {"numerator": -5, "denominator": 1},
    "c": {"numerator": 6, "denominator": 1},
    "discriminant": {
      "value": {"numerator": 1, "denominator": 1},
      "is_positive": true,
      "is_zero": false,
      "is_negative": false,
      "is_rational_square": true,
      "square_root_rational": {"numerator": 1, "denominator": 1},
      "squarefree_kernel": 1,
      "extracted_factor": {"numerator": 1, "denominator": 1}
    },
    "semantic_revision_hash": "8f4a1c0d2e3b4a5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"
  },
  "available_methods": [
    {
      "method_id": "QUAD_FORMULA_STANDARD",
      "title_vi": "Công thức nghiệm chuẩn (Biệt thức Δ)",
      "mathematical_applicability": "APPLICABLE",
      "support_status": "SUPPORTED",
      "execution_availability": "AVAILABLE",
      "pedagogical_recommendation": "RECOMMENDED",
      "verification_capability": "HOST_VERIFIABLE",
      "reasons": [],
      "prerequisites": [],
      "has_trace_available": true,
      "pedagogical_priority": 1
    },
    {
      "method_id": "QUAD_FORMULA_REDUCED",
      "title_vi": "Công thức nghiệm thu gọn (Biệt thức Δ')",
      "mathematical_applicability": "NOT_APPLICABLE",
      "support_status": "SUPPORTED",
      "execution_availability": "AVAILABLE",
      "pedagogical_recommendation": "NOT_RECOMMENDED",
      "verification_capability": "HOST_VERIFIABLE",
      "reasons": ["COEFFICIENT_B_NOT_EVEN"],
      "prerequisites": [],
      "has_trace_available": true,
      "pedagogical_priority": 2
    }
    /* ABRIDGED EXAMPLE — full array contains all 9 registered methods */
  ],
  "selected_method_id": "QUAD_FORMULA_STANDARD",
  "solution": {
    "method_id": "QUAD_FORMULA_STANDARD",
    "outcome": "TWO_DISTINCT_REAL_ROOTS",
    "roots": [
      {
        "root_type": "RATIONAL",
        "rational_value": {"numerator": 2, "denominator": 1},
        "surd_base": null,
        "surd_factor": null,
        "radicand": null,
        "approximate_float": 2.0,
        "latex_str": "2"
      },
      {
        "root_type": "RATIONAL",
        "rational_value": {"numerator": 3, "denominator": 1},
        "surd_base": null,
        "surd_factor": null,
        "radicand": null,
        "approximate_float": 3.0,
        "latex_str": "3"
      }
    ],
    "final_answer_latex": "S = \\left\\{ 2, 3 \\right\\}",
    "trace": {
      "method_id": "QUAD_FORMULA_STANDARD",
      "solution_outcome": "TWO_DISTINCT_REAL_ROOTS",
      "roots": [
        {
          "root_type": "RATIONAL",
          "rational_value": {"numerator": 2, "denominator": 1},
          "latex_str": "2"
        },
        {
          "root_type": "RATIONAL",
          "rational_value": {"numerator": 3, "denominator": 1},
          "latex_str": "3"
        }
      ],
      "steps": [
        {
          "step_number": 1,
          "latex_expression": "\\Delta = b^2 - 4ac = (-5)^2 - 4(1)(6) = 1",
          "explanation_vi": "Tính biệt thức Delta",
          "rule_or_theorem_used": "DEFINITION_DISCRIMINANT",
          "intermediate_substitutions": {"b": "-5", "a": "1", "c": "6"},
          "why_this_step_vi": "Xác định số lượng và tính chất nghiệm"
        }
      ],
      "final_answer_latex": "S = \\left\\{ 2, 3 \\right\\}"
    },
    "verification_scope": "FINAL_SOLUTION",
    "certificate": {
      "certificate_id": "c1d2e3f4a5b6c7d8",
      "problem_hash": "8f4a1c0d2e3b4a5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f901a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "verified_at_utc": "2026-10-01T22:00:00"
    }
  }
}
```

#### B. ANALYZED_NO_EXECUTION Response Example (Degenerate $a=0$):
```json
{
  "response_status": "ANALYZED_NO_EXECUTION",
  "problem": {
    "problem_type": "DEGENERATE",
    "problem_id": "prob_d1e2f3a4b5c6d7e8",
    "raw_query": "2*x - 4 = 0",
    "equation_latex": "2x - 4 = 0",
    "category": "ALGEBRA_QUADRATIC",
    "classification": "LINEAR",
    "a": {"numerator": 0, "denominator": 1},
    "b": {"numerator": 2, "denominator": 1},
    "c": {"numerator": -4, "denominator": 1},
    "linear_root": {"numerator": 2, "denominator": 1},
    "semantic_revision_hash": "d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2"
  },
  "available_methods": [],
  "selected_method_id": null,
  "degenerate_solution": {
    "classification": "LINEAR",
    "outcome": "ONE_REAL_LINEAR_ROOT",
    "linear_root": {"numerator": 2, "denominator": 1},
    "final_answer_latex": "x = 2",
    "verification_scope": "FINAL_SOLUTION",
    "certificate": {
      "certificate_id": "f1e2d3c4b5a69788",
      "problem_hash": "d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "f1e2d3c4b5a69788796a5b4c3d2e1f001a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "verified_at_utc": "2026-10-01T22:00:00"
    }
  },
  "reason_code": "DEGENERATE_EXACT_SOLUTION",
  "analysis_message_vi": "Hệ số a = 0. Phương trình suy biến thành phương trình bậc nhất có nghiệm duy nhất x = 2."
}
```

#### C. ERROR Response Example (Category A Client Domain Error):
```json
{
  "response_status": "ERROR",
  "error_code": "SYNTAX_ERROR",
  "message_vi": "Cú pháp phương trình không hợp lệ.",
  "message_en": "Syntax error in mathematical equation.",
  "span": {
    "start": 6,
    "end": 7
  },
  "details": {
    "token": "="
  }
}
```

#### D. Transport Error Response Example (HTTP 400 / 413 / 415 / 422):
```json
{
  "transport_status": "ERROR",
  "transport_error_code": "MALFORMED_JSON",
  "message_vi": "Định dạng JSON trong yêu cầu không hợp lệ.",
  "message_en": "Malformed JSON request body.",
  "details": {
    "error_type": "json_invalid",
    "loc": ["body", 12]
  }
}
```

---

## 7. OpenAPI $\to$ TypeScript Schema Generation Pipeline

To eliminate manual shadow schema duplication and prevent client-server drift:

```
┌─────────────────────────────────────────────────────────┐
│     Pydantic v2 DTOs (mke_product.application.dto)      │
└────────────────────────────┬────────────────────────────┘
                             │ (FastAPI automatic reflection)
                             ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI OpenAPI 3.1 (/openapi.json)          │
└────────────────────────────┬────────────────────────────┘
                             │ (npx openapi-typescript)
                             ▼
┌─────────────────────────────────────────────────────────┐
│  src/frontend/src/types/api.generated.ts (100% SSOT)   │
└─────────────────────────────────────────────────────────┘
```

### OpenAPI $\to$ TypeScript Union Strategy:
- `SolveResponseUnion` is defined in Python as an `Annotated[Union[...], Field(discriminator='response_status')]`.
- **Preferred Approach:** In frontend TypeScript code, derive the union type directly from the OpenAPI operation response:
  ```typescript
  import type { operations, components } from "./types/api.generated";

  export type SolveResponseUnion =
    operations["solve_equation_endpoint"]["responses"]["200"]["content"]["application/json"];
  export type SolvedResponse = components["schemas"]["SolvedResponse"];
  export type AnalyzedNoExecutionResponse = components["schemas"]["AnalyzedNoExecutionResponse"];
  export type ErrorResponse = components["schemas"]["ErrorResponse"];
  export type TransportErrorResponse = components["schemas"]["TransportErrorResponse"];
  ```
- **S2-01 Implementation Option:** If a named component schema is found to simplify tooling, introduce a Pydantic `RootModel[SolveResponseUnion]` transport schema alias whose wire JSON remains bit-for-bit identical.

---

## 8. Frontend Architecture & Version Policy

### Framework Decision: React + TypeScript + Vite
- **Architecture Family:** React 18 / 19, TypeScript, Vite.
- **Version Pinning Policy:** Exact package versions will be deterministically pinned in `package.json` and locked via `package-lock.json` at stage S2-03 initialization.
- **Zero Node.js Runtime in Production:** Vite compiles to static assets (`dist/`) served directly by the FastAPI static mount.

### UI00 Visual Identity Preservation Map:
```
ui/ui00/ Assets                        Production React Architecture
─────────────────────────────────      ───────────────────────────────────────
DESIGN_TOKENS.md               ─────>  src/styles/tokens.css (CSS variables)
styles.css                     ─────>  Scoped CSS Modules / Component styles
Vendor KaTeX (offline)         ─────>  Vendored in public/vendor/katex
Iconography & SVGs             ─────>  Typed SVG React Icon components
Capsule search bar             ─────>  <EquationInput /> component
4-Column topic grid            ─────>  <TopicExplorer /> component
Theme/Language Popover         ─────>  <SettingsPopover /> component
```

---

## 9. Live Algebra Workspace State Model & Reactive Flows

The workspace state is structured as an immutable, unidirectional state machine driven by server response DTOs:

```typescript
import type { operations, components } from "./types/api.generated";

export type SolveResponseUnion =
  operations["solve_equation_endpoint"]["responses"]["200"]["content"]["application/json"];
export type SolvedResponse = components["schemas"]["SolvedResponse"];
export type AnalyzedNoExecutionResponse = components["schemas"]["AnalyzedNoExecutionResponse"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];
export type RationalFraction = components["schemas"]["RationalFraction"];

interface WorkspaceState {
  // Input State
  inputMode: "RAW_TEXT" | "COEFFICIENTS";
  rawQuery: string;
  coefficients: {
    a: RationalFraction;
    b: RationalFraction;
    c: RationalFraction;
  };
  selectedMethodId: string | null;

  // Server Response State (SSOT)
  responseStatus: "IDLE" | "LOADING" | "SOLVED" | "ANALYZED_NO_EXECUTION" | "ERROR";
  solvedData: SolvedResponse | null;
  analyzedData: AnalyzedNoExecutionResponse | null;
  errorData: ErrorResponse | null;
}
```

### Reactive Flows:
1. **Flow A (RAW Text Solve):** User enters equation $\to$ dispatches `RAW_TEXT` $\to$ server returns `SolvedResponse` $\to$ updates $a, b, c$, available methods, and solution trace.
2. **Flow B (Method Switch):** User clicks another applicable method $\to$ dispatches `COEFFICIENTS` solve with `selected_method_id` $\to$ returns new trace without re-parsing text.
3. **Flow C (Live Coefficient Edit):** User edits $a, b, c$ steppers $\to$ dispatches `COEFFICIENTS` solve with `selected_method_id=null` $\to$ updates discriminant, roots, and recommended method.
4. **Flow D (Quadratic $\to$ Degenerate Transition $a \to 0$):** User sets $a=0$ $\to$ server returns `ANALYZED_NO_EXECUTION` (`DEGENERATE_EXACT_SOLUTION`) $\to$ UI seamlessly transitions to linear solution view.

---

## 10. Workspace Component Architecture

```
                               ┌─────────────────────────────┐
                               │     <AlgebraWorkspace />    │
                               └──────────────┬──────────────┘
                                               │
         ┌────────────────────────────────────┼────────────────────────────────────┐
         ▼                                    ▼                                    ▼
┌──────────────────┐               ┌──────────────────────┐             ┌─────────────────────┐
│  <HeaderBar />   │               │   <WorkspaceBody />  │             │   <FooterBanner />  │
└──────────────────┘               └──────────┬───────────┘             └─────────────────────┘
                                              │
       ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
       ▼                      ▼                               ▼                      ▼
┌──────────────┐      ┌────────────────┐             ┌─────────────────┐     ┌────────────────┐
│<EquationInput│      │<CoefficientEdit│             │<CanonicalProblem│     │ <ErrorPanel /> │
│     />       │      │      />        │             │     Card />     │     │ (Span + Code)  │
└──────────────┘      └────────────────┘             └────────┬────────┘     └────────────────┘
                                                              │
                              ┌───────────────────────────────┴───────────────────────────────┐
                              ▼                                                               ▼
                   ┌──────────────────────┐                                       ┌───────────────────────┐
                   │  <MethodSelector />  │                                       │   <SolutionPanel />   │
                   │ (9 Method Catalog)   │                                       │ (Trace, Roots, Badge) │
                   └──────────────────────┘                                       └───────────────────────┘
```

---

## 11. Method Selector UX Contract (9 Methods)

The method selection UI must present the complete **9-method pedagogical catalog** defined in S0/S1 without concealing unavailable methods:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             CHỌN PHƯƠNG PHÁP GIẢI (9 PHƯƠNG PHÁP)                         │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ [●] Công thức nghiệm chuẩn (Δ)        [KHẢ DỤNG]   [KHUYÊN DÙNG]  [ĐÃ KIỂM ĐỊNH]          │
│ [○] Công thức nghiệm thu gọn (Δ')     [KHẢ DỤNG]   [KHUYÊN DÙNG]  [ĐÃ KIỂM ĐỊNH]          │
│ [○] Nhẩm nghiệm Viète (a + b + c = 0) [KHẢ DỤNG]   [ƯU TIÊN 1]    [ĐÃ KIỂM ĐỊNH]          │
│ [○] Nhẩm nghiệm Viète (a - b + c = 0) [KHẢ DỤNG]   [ƯU TIÊN 1]    [ĐÃ KIỂM ĐỊNH]          │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ [ ] Phân tích đa thức thành nhân tử (Q) [ĐANG HOÀN THIỆN]  [XEM HƯỚNG DẪN]               │
│ [ ] Phân tích đa thức thành nhân tử (R) [ĐANG HOÀN THIỆN]  [XEM HƯỚNG DẪN]               │
│ [ ] Phương pháp biến đổi thêm bớt (bình phương hoàn chỉnh) [ĐANG HOÀN THIỆN]              │
│ [ ] Nhẩm nghiệm tổng - tích Viète (S, P) [ĐANG HOÀN THIỆN] [XEM HƯỚNG DẪN]               │
│ [ ] Khảo sát đồ thị & Tọa độ giao điểm  [ĐANG HOÀN THIỆN]  [XEM HƯỚNG DẪN]               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. S3 Graph & Knowledge Authority Boundaries

### 12.1 Graph Authority Boundary (Stage S3):
- **Backend Graph Model SSOT:** In Stage S3, graph data is derived entirely on the backend and transported as a deterministic `GraphModel` DTO:
  - Canonical coefficients ($a, b, c$) and `semantic_revision_hash`.
  - Vertex coordinates: $(-\frac{b}{2a}, -\frac{\Delta}{4a})$.
  - Axis of symmetry: $x = -\frac{b}{2a}$.
  - $y$-intercept: $(0, c)$.
  - Real $x$-intercepts: exact roots from `CanonicalQuadraticProblemView`.
- **Frontend Pure Renderer:** The frontend `GraphPanel` acts exclusively as an SVG / Canvas renderer. It does not compute or derive mathematical invariants.

### 12.2 Knowledge & Remediation Anchors (Stage S3):
- **Stable Knowledge Anchors:** Remedial tips, knowledge cards, and prerequisite links must bind strictly to stable domain identifiers:
  - `method_id` (e.g. `QUAD_FORMULA_STANDARD`)
  - `PrerequisiteStatus.prerequisite_id` (e.g. `PREREQ_RADICALS`, `PREREQ_VIETE_SUM`)
  - `SolutionStep.rule_or_theorem_used` (e.g. `DEFINITION_DISCRIMINANT`, `THEOREM_QUADRATIC_FORMULA`)
- **Presentation Strings:** `step.explanation_vi` and `why_this_step_vi` are human-readable presentation text only and must never be used as foreign key anchors.

---

## 13. Direct-vs-HTTP Semantic Parity Specification

Parity between direct Python execution `solve_request(req)` and HTTP transport `POST /api/v1/algebra/solve` is defined as:

> **"Semantic parity after normalization of intentionally nondeterministic metadata."**

### Parity Verification Procedure:
1. Obtain direct Python execution dictionary:
   ```python
   direct_resp = solve_request(req)
   direct_dict = direct_resp.model_dump(mode="json")
   ```
2. Obtain HTTP response dictionary:
   ```python
   http_resp = test_client.post("/api/v1/algebra/solve", json=req.model_dump(mode="json"))
   assert http_resp.status_code == 200
   http_dict = http_resp.json()
   ```
3. Normalize only intentionally nondeterministic metadata fields:
   - Mask `verified_at_utc` in both dictionaries (e.g. `direct_dict["solution"]["certificate"]["verified_at_utc"] = "NORMALIZED"`).
4. Assert exact semantic equality:
   ```python
   assert direct_dict == http_dict
   ```

### Parity Invariants:
Strict bit-for-bit equality is required across:
- `response_status`
- Canonical problem fields (`problem_id`, `equation_latex`, $a, b, c$, `discriminant`, `classification`)
- `semantic_revision_hash`
- `available_methods` (all 9 items and their properties)
- `selected_method_id`
- Solution outcome, exact roots, and formatting
- Complete step-by-step trace intermediate expressions and rules
- Verification outcome, `integrity_fingerprint`, and `certificate_id`

---

## 14. Implementation Acceptance Test Plan for S2

The future Stage S2 implementation must satisfy the following comprehensive test suites:

### 14.1 Transport Integration Tests (`tests/test_transport_fastapi_s2.py`):
- `test_api_solve_raw_text_solved_parity`: HTTP `POST /api/v1/algebra/solve` achieves semantic parity with direct `solve_request()` after timestamp normalization.
- `test_api_solve_coefficients_solved_parity`: HTTP `COEFFICIENTS` solve matches direct execution.
- `test_api_method_switch_reactivity`: Method switch preserves `semantic_revision_hash` and updates trace.
- `test_api_degenerate_solution_linear`: Linear equation returns HTTP 200 with `DEGENERATE_EXACT_SOLUTION`.
- `test_api_syntax_error_returns_http_200_error_response`: Category A client errors return HTTP 200 `ErrorResponse` with span.
- `test_api_invalid_json_returns_http_400_custom_handler`: Malformed JSON returns HTTP 400 with `TransportErrorResponse(MALFORMED_JSON)`.
- `test_api_pydantic_validation_failure_returns_http_422`: Schema violations return HTTP 422 with `TransportErrorResponse(REQUEST_VALIDATION_FAILED)`.
- `test_api_unsupported_media_type_text_plain_returns_http_415`: `text/plain` returns HTTP 415 `TransportErrorResponse(UNSUPPORTED_MEDIA_TYPE)`.
- `test_api_unsupported_media_type_invalid_suffix_returns_http_415`: `application/json-not-really` returns HTTP 415.
- `test_api_supported_media_type_application_json_accepted`: `application/json` returns HTTP 200.
- `test_api_supported_media_type_with_charset_accepted`: `application/json; charset=utf-8` returns HTTP 200.
- `test_api_stream_limit_header_rejection_returns_http_413`: Declared `Content-Length: 65537` returns HTTP 413 `TransportErrorResponse(PAYLOAD_TOO_LARGE)`.
- `test_api_stream_limit_streamed_chunks_returns_http_413`: Streamed chunks > 64 KiB without `Content-Length` return HTTP 413.
- `test_api_stream_limit_deceptive_header_returns_http_413`: Declared `Content-Length: 10` but stream sending > 64 KiB returns HTTP 413.
- `test_api_stream_limit_exact_65536_boundary_accepted`: Exactly 65,536 bytes payload accepted.
- `test_api_internal_execution_failure_returns_http_500_application_error`: Category B internal failures return sanitized HTTP 500 `ErrorResponse`.
- `test_api_internal_transport_failure_returns_http_500_transport_error`: Transport-level failures return HTTP 500 `TransportErrorResponse`.
- `test_api_nonexistent_api_route_returns_json_404_no_spa_fallback`: `/api/*` routes return JSON 404 and never SPA `index.html`.
- `test_api_health_endpoint_derived_dynamically`: `GET /api/v1/health` verifies counts match `len(MethodRegistry().list_all())` and `len(TRACE_GENERATORS)` dynamically via monkeypatching.
- `test_openapi_schema_drift_check`: Generated TypeScript types match FastAPI `/openapi.json` without drift.

### 14.2 Live Workspace Browser Tests (`tests/test_browser_live_workspace_s2.py`):
- `test_workspace_raw_solve_flow`: End-to-end RAW text solve flow renders card, roots, and trace.
- `test_workspace_method_switch_flow`: Switching method tabs updates trace reactively without reload.
- `test_workspace_coefficient_editor_flow`: Modifying $c$ updates discriminant and roots dynamically.
- `test_workspace_quadratic_to_degenerate_transition`: Modifying $a \to 0$ transitions UI to degenerate linear card.
- `test_workspace_9_methods_visibility`: All 9 methods visible in selector with appropriate availability badges.
- `test_workspace_error_highlight`: Syntax errors render inline error panel with exact span highlight.

---

## 15. Staged S2 Implementation Roadmap

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Stage S2 Implementation Sequence                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-01: FastAPI Transport Adapter & Route Namespace Implementation                      │
│        - Add fastapi/uvicorn to requirements.txt & httpx to requirements-dev.txt       │
│        - Implement src/mke_product/transport/app.py & routers/algebra.py               │
│        - Implement pure ASGI streaming 64 KiB limit & media type enforcement           │
│        - Implement TransportErrorResponse & custom 400/413/415/422/500 handlers        │
│        - Connect /api/v1/algebra/solve directly to solve_request()                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-02: Transport Acceptance & Direct-vs-HTTP Parity Verification Suite                 │
│        - Implement tests/test_transport_fastapi_s2.py using TestClient / ASGI harness  │
│        - Prove 100% mathematical semantic parity between direct Python & HTTP          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-03: Production Frontend Shell Migration (React + TypeScript + Vite)                 │
│        - Initialize frontend package structure with Vite, React 18/19, TypeScript      │
│        - Set up openapi-typescript pipeline and generate api.generated.ts              │
│        - Port DESIGN_TOKENS.md CSS variables and offline KaTeX vendor assets           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-04: Live Algebra Workspace Component Implementation                                 │
│        - Implement <EquationInput />, <CoefficientEditor />, <CanonicalProblemCard />  │
│        - Implement <MethodSelector />, <SolutionTrace />, <VerificationBadge />        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-05: Live Reactive State Binding & Interactive Flows                                 │
│        - Implement Flows A, B, C, D in workspace state machine                         │
│        - Connect API client to /api/v1/algebra/solve with loading/error handling       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-06: Stage S2 End-to-End Acceptance & Browser Verification Closeout                  │
│        - Implement tests/test_browser_live_workspace_s2.py                             │
│        - Generate MVP_V1_S2_ACCEPTANCE_REPORT.md and freeze S2 baseline                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 16. Explicit Deferred Scope (Post-S2)

1. **Interactive 2D Parabola Canvas Plotter:** Drag handles and curve plotting (deferred to S3).
2. **Pedagogical Knowledge & Prerequisite Cards:** Curated formula cards and remediation tips (deferred to S3).
3. **Database Persistence & Session Storage:** Problem history and user accounts (deferred).
4. **Photo / OCR Intake Pipeline:** Camera capture and OCR (deferred).
5. **Execution of Deferred Methods:** Factoring, completing the square, Viète root guessing, and graph analysis execution workers (deferred).
6. **Synthetic Geometry Deduction UI:** Synthetic theorem prover interface (deferred).

---

## 17. Unresolved Architectural Questions & Adjudications

| Question | Evaluation | Adjudication / Preflight Decision |
| :--- | :--- | :--- |
| **Q1: Should legacy `demo_server.py` be immediately deleted?** | Deleting it would break legacy CAS tests (`test_cas_http_integration.py`). | **Retain `demo_server.py` for legacy compatibility**; production app uses new FastAPI transport. |
| **Q2: Should Vite dev server proxy to FastAPI or should FastAPI serve static build?** | Vite dev proxy provides instant HMR (<50ms) during development; FastAPI static mount serves `dist/` in production. | **Support both**: Vite proxy for development, FastAPI static mount for production distribution. |
| **Q3: Should `input_mode` be sent in every request?** | Explicit discriminator prevents payload ambiguity. | **Yes**: `SolveRequest.input_payload` strictly discriminates `RAW_TEXT` vs `COEFFICIENTS`. |

---

## 18. Parked B3 Baseline Preservation

- **Parked B3 Branch:** `product/p03c-p1c-04-b3-exact-complex-preflight`
- **Parked B3 Baseline SHA:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`
- **Integrity Status:** **UNTOUCHED**. No changes, merges, or rebases have occurred from or to the parked B3 complex solver branch.

---

## 19. Conclusion & Stage Status

This preflight specification resolves all transport, error handling, state management, schema generation, and UI migration requirements for MKE MVP V1 Stage S2.

**Milestone Status:** **`PENDING INDEPENDENT S2-P0-R2 FINAL AUDIT`**
