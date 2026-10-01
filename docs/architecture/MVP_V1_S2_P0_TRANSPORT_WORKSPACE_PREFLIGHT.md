# MKE MVP V1 — S2-P0-R1 Transport & Live Math Workspace Integration Preflight Specification

**Document Version:** 1.1.0 (R1 Contract Hardened)  
**Milestone:** MVP V1 — Stage S2 Preflight Architecture  
**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Accepted S1 Baseline:** `3058b6e904f38003a650a79105ae615226bdbc17`  
**Parent S2-P0 Baseline:** `b2c6b864d1665c1adbab6bffb6c347f8cf5e15cc`  
**Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (UNTOUCHED)  
**Status:** **`PENDING INDEPENDENT S2-P0-R1 AUDIT`**

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
> **API 404 vs SPA Fallback Rule:** Requests matching `/api/*` that do not resolve to a registered endpoint MUST return JSON `404 Not Found` with a structured `ErrorResponse` envelope. They MUST NEVER fall back to `index.html`.

### 4.1 Route Specification: `POST /api/v1/algebra/solve`
- **Request Body:** Direct JSON representation of `SolveRequest`.
- **Response Body:** Direct JSON representation of `SolveResponseUnion` (`SolvedResponse` | `AnalyzedNoExecutionResponse` | `ErrorResponse`).
- **Transport Execution Policy:**
  ```python
  @router.post(
      "/algebra/solve",
      response_model=SolveResponseUnion,
      responses={
          200: {"description": "Successful mathematical analysis or domain error"},
          400: {"model": ErrorResponse, "description": "Malformed JSON payload"},
          413: {"model": ErrorResponse, "description": "Payload exceeds 64 KiB limit"},
          415: {"model": ErrorResponse, "description": "Unsupported Content-Type"},
          422: {"description": "DTO schema validation failure"},
          500: {"model": ErrorResponse, "description": "Internal server execution failure"},
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
@router.get("/health")
async def health_check_endpoint() -> HealthResponse:
    from mke_product.methods.registry import MethodRegistry
    from mke_product.methods.traces import TRACE_GENERATORS

    return HealthResponse(
        status="HEALTHY",
        version="1.0.0",
        milestone="MVP_V1_S2",
        algebra_authority="mke_product.application.orchestrator.solve_request",
        supported_input_modes=["RAW_TEXT", "COEFFICIENTS"],
        registered_methods_count=len(MethodRegistry.list_all()),
        executable_methods_count=len(TRACE_GENERATORS),
    )
```

**Health Response Payload:**
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

## 5. HTTP Status Semantics & Error Mapping Policy

Transport status codes strictly distinguish between **Transport / Request Malformation (4xx)**, **Application Domain Outcomes (Category A $\to$ HTTP 200)**, and **Internal Integrity / Execution Failures (Category B $\to$ HTTP 500)**:

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
        ┌─────────────┼─────────────┐                      Bad JSON  Too Large Bad Media Pydantic
        ▼             ▼             ▼                      HTTP 400  HTTP 413  HTTP 415  HTTP 422
     SOLVED        ANALYZED       ERROR                    (Syntax)  (>64KiB)  (!=json)  (Schema)
    HTTP 200       HTTP 200      ┌──┴──┐
   (Verified)     (Degenerate/   │     │
                  Unavailable)   ▼     ▼
                            Category A Category B
                            HTTP 200   HTTP 500
                            (Client)   (Internal)
```

### 5.1 Error Categorization Matrix:

| Category | Outcome / Error Code | HTTP Status | Response Schema | Description & UI Handling |
| :--- | :--- | :--- | :--- | :--- |
| **Mathematical Success** | `response_status="SOLVED"` | `200 OK` | `SolvedResponse` | Solved & verified; render solution card, roots, and trace |
| **Mathematical Analysis** | `response_status="ANALYZED_NO_EXECUTION"` | `200 OK` | `AnalyzedNoExecutionResponse` | Degenerate ($a=0$) or deferred method; render explanation |
| **Category A: Client Domain Error** | `SYNTAX_ERROR`<br>`UNSUPPORTED_VARIABLE`<br>`UNSUPPORTED_SYNTAX`<br>`IMPLICIT_MULTIPLICATION_UNSUPPORTED`<br>`DEGREE_OUT_OF_SCOPE`<br>`NON_POLYNOMIAL_INPUT`<br>`DIVISION_BY_ZERO`<br>`INPUT_LIMIT_EXCEEDED`<br>`METHOD_NOT_FOUND` | `200 OK` | `ErrorResponse` | Mathematical/input errors caused by client request; render inline error panel with error code and span highlight |
| **Category B: Internal Execution Failure** | `NORMALIZATION_ERROR` (internal)<br>`DOMAIN_CONTRACT_ERROR`<br>`METHOD_EXECUTION_FAILED`<br>`VERIFICATION_FAILED`<br>`INTERNAL_ERROR` | `500 Internal Server Error` | `ErrorResponse` (sanitized) | Engine invariant violation or unexpected failure; render localized server error banner without leaking internal trace |
| **Transport: Malformed JSON** | `json_invalid` | `400 Bad Request` | `ErrorResponse` | Body is not valid JSON; custom exception handler returns HTTP 400 |
| **Transport: Schema Validation** | `ValidationError` | `422 Unprocessable Entity` | Standard FastAPI / Pydantic validation error | Schema constraint violation (e.g. string > 256 chars, missing field) |
| **Transport: Payload Exceeded** | `StreamPayloadLimitExceeded` | `413 Payload Too Large` | `ErrorResponse` | Body exceeds 65,536 bytes limit |
| **Transport: Unsupported Media** | `UnsupportedMediaType` | `415 Unsupported Media Type` | `ErrorResponse` | `Content-Type` is not `application/json` |

### 5.2 Malformed JSON vs Schema Validation Exception Handlers:
FastAPI by default groups JSON parse errors and Pydantic validation errors under `RequestValidationError` (returning HTTP 422). S2 implements a custom exception handler:
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Check if any error is due to malformed JSON body
    for err in exc.errors():
        if err.get("type") == "json_invalid":
            return JSONResponse(
                status_code=400,
                content={
                    "response_status": "ERROR",
                    "error_code": "SYNTAX_ERROR",
                    "message_vi": "Định dạng JSON trong yêu cầu không hợp lệ.",
                    "message_en": "Malformed JSON request body.",
                    "span": None,
                    "details": {"error_type": "json_invalid"},
                },
            )
    # Standard Pydantic schema validation failures return HTTP 422
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
```

### 5.3 Streaming 64 KiB Payload Limit Middleware:
To prevent memory exhaustion via chunked transfer or omitted `Content-Length`:
```python
class PayloadLimitMiddleware(BaseHTTPMiddleware):
    MAX_BYTES = 65536  # 64 KiB

    async def dispatch(self, request: Request, call_next):
        # 1. Early rejection via Content-Length header
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "response_status": "ERROR",
                    "error_code": "INPUT_LIMIT_EXCEEDED",
                    "message_vi": "Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                    "message_en": "Request payload exceeds 64 KiB limit.",
                    "span": None,
                    "details": {"limit_bytes": self.MAX_BYTES},
                },
            )
        # 2. Chunk-counting stream validator for chunked/unbounded transfers
        # (Stream-level byte counter aborts connection if cumulative chunks exceed MAX_BYTES)
        return await call_next(request)
```

### 5.4 Unsupported Media Type Middleware:
```python
class MediaTypeEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/"):
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={
                        "response_status": "ERROR",
                        "error_code": "UNSUPPORTED_SYNTAX",
                        "message_vi": "Tiêu đề Content-Type phải là 'application/json'.",
                        "message_en": "Content-Type header must be 'application/json'.",
                        "span": None,
                        "details": {"received_content_type": content_type},
                    },
                )
        return await call_next(request)
```

---

## 6. DTO JSON Contract & Exact Serialization Specification

The DTO models in `mke_product.application.dto` serve as the Single Source of Truth (SSOT).

### Contract Formatting Rules:
- `semantic_revision_hash`: Raw 64-character SHA-256 lowercase hex string (e.g. `"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"`). **No `sha256_` prefix**.
- `problem_id`: `"prob_" + semantic_revision_hash[:16]` (e.g. `"prob_e3b0c44298fc1c14"`).
- `certificate_id`: `"cert_" + problem_hash[:16]`.
- `verified_at_utc`: Pydantic ISO-8601 UTC timestamp (e.g. `"2026-10-01T22:00:00Z"`).
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
      "certificate_id": "cert_8f4a1c0d2e3b4a5c",
      "problem_hash": "8f4a1c0d2e3b4a5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "a1b2c3d4e5f60718293a4b5c6d7e8f901a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "verified_at_utc": "2026-10-01T22:00:00Z"
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
      "certificate_id": "cert_d1e2f3a4b5c6d7e8",
      "problem_hash": "d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "f1e2d3c4b5a69788796a5b4c3d2e1f001a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "verified_at_utc": "2026-10-01T22:00:00Z"
    }
  },
  "reason_code": "DEGENERATE_EXACT_SOLUTION",
  "analysis_message_vi": "Hệ số a = 0. Phương trình suy biến thành phương trình bậc nhất có nghiệm duy nhất x = 2."
}
```

#### C. ERROR Response Example:
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

### Automation & CI Drift Check Strategy:
1. **Generation Command:**
   ```bash
   npm run generate:api-types
   # Executes: openapi-typescript http://127.0.0.1:8000/openapi.json -o src/frontend/src/types/api.generated.ts
   ```
2. **CI Drift Check Command:**
   ```bash
   npm run check:api-types
   # Dumps schema, generates types to a temporary file, and verifies git diff == 0
   ```
3. **No Shadow Types:** Frontend code must import exclusively from `api.generated.ts`. Zero manual hand-written interface definitions for backend DTOs.

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
import type { components } from "./types/api.generated";

type SolveResponseUnion = components["schemas"]["SolveResponseUnion"];
type SolvedResponse = components["schemas"]["SolvedResponse"];
type AnalyzedNoExecutionResponse = components["schemas"]["AnalyzedNoExecutionResponse"];
type ErrorResponse = components["schemas"]["ErrorResponse"];
type RationalFraction = components["schemas"]["RationalFraction"];

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

### Parity Invariants:
1. All mathematical structures (`problem`, `classification`, $a, b, c$, `discriminant`, `roots`, `trace`, `available_methods`, `semantic_revision_hash`) must match bit-for-bit.
2. The only field permitted to vary across invocations is `verified_at_utc` in the verification certificate (which reflects the invocation wall clock).
3. Test suites assert equality by masking or normalizing `verified_at_utc` prior to assertion.

---

## 14. Implementation Acceptance Test Plan for S2

The future Stage S2 implementation must satisfy the following comprehensive test suites:

### 14.1 Transport Integration Tests (`tests/test_transport_fastapi_s2.py`):
- `test_api_solve_raw_text_solved_parity`: HTTP `POST /api/v1/algebra/solve` achieves semantic parity with direct `solve_request()`.
- `test_api_solve_coefficients_solved_parity`: HTTP `COEFFICIENTS` solve matches direct execution.
- `test_api_method_switch_reactivity`: Method switch preserves `semantic_revision_hash` and updates trace.
- `test_api_degenerate_solution_linear`: Linear equation returns HTTP 200 with `DEGENERATE_EXACT_SOLUTION`.
- `test_api_syntax_error_returns_http_200_error_response`: Category A client errors return HTTP 200 `ErrorResponse` with span.
- `test_api_invalid_json_returns_http_400_custom_handler`: Malformed JSON returns HTTP 400 with custom error envelope.
- `test_api_pydantic_validation_failure_returns_http_422`: Schema violations return HTTP 422.
- `test_api_unsupported_media_type_returns_http_415`: Non-JSON requests return HTTP 415.
- `test_api_payload_exceeding_64kb_stream_returns_http_413`: Payloads > 64 KiB rejected via early header or stream counter.
- `test_api_internal_execution_failure_returns_http_500`: Category B internal failures return sanitized HTTP 500 `ErrorResponse`.
- `test_api_nonexistent_api_route_returns_json_404_no_spa_fallback`: `/api/*` routes return JSON 404 and never SPA `index.html`.
- `test_api_health_endpoint_derived_counts`: `GET /api/v1/health` returns dynamically derived counts (9 registered, 4 executable).
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
│        - Implement 400/413/415/500 handlers, streaming middleware & CORS               │
│        - Connect /api/v1/algebra/solve directly to solve_request()                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-02: Transport Acceptance & Direct-vs-HTTP Parity Verification Suite                 │
│        - Implement tests/test_transport_fastapi_s2.py using TestClient                 │
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

**Milestone Status:** **`PENDING INDEPENDENT S2-P0-R1 AUDIT`**
