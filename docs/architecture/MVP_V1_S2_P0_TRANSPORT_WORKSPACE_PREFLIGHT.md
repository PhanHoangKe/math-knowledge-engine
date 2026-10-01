# MKE MVP V1 — S2-P0 Transport & Live Math Workspace Integration Preflight Specification

**Document Version:** 1.0.0  
**Milestone:** MVP V1 — Stage S2 Preflight Architecture  
**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Accepted S1 Baseline:** `3058b6e904f38003a650a79105ae615226bdbc17`  
**Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (UNTOUCHED)  
**Status:** **`PENDING INDEPENDENT S2-P0 AUDIT`**

---

## 1. Executive Summary & Audited Current Repository Reality

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
2. **Current Server (`src/mke_product/cas/demo_server.py`):**
   - Built on standard library `http.server.BaseHTTPRequestHandler` / `ThreadingHTTPServer`.
   - Serves static assets from `ui/ui00/` and handles `POST /api/execute` / `POST /api/plot` via `CASRouter`.
   - Contains security/transport debt: manual socket timeout chunking loops and direct string interpolation of internal exceptions into JSON error messages (`f"Invalid JSON payload: {exc}"`).
   - Does **not** expose or connect to the accepted S1 application orchestrator `solve_request()`.
3. **Dependencies (`requirements.txt`):**
   - Declares `pydantic>=2.6.0,<3.0.0`, `pytest>=7.0.0`, `sympy>=1.12`, `mpmath>=1.3.0`.
   - FastAPI and ASGI servers (`uvicorn`) are **not** currently declared in `requirements.txt`.
4. **S1 Authority Entry Point:**
   - Exclusively `mke_product.application.orchestrator.solve_request(req: SolveRequest) -> SolveResponseUnion`.
   - Strict Pydantic v2 discriminated union models in `mke_product.application.dto`.

The purpose of Stage S2 is to establish a high-fidelity, type-safe HTTP transport layer and a reactive live algebra workspace that binds directly to S1 mathematical authority without mathematical regression, shadow schema drift, or CAS bypass.

---

## 2. Legacy Server & API Inventory

The existing server endpoints in `src/mke_product/cas/demo_server.py` serve the following roles:

| Endpoint | Method | Underlying Authority | Current Status & Role in S2 |
| :--- | :--- | :--- | :--- |
| `/`, `/index.html`, `/styles.css`, `/app.js`, `/vendor/*` | `GET` | Static file serving (`UI_DIR = ui/ui00`) | Preserved / migrated to production static mount |
| `/api/health` | `GET` | Hardcoded JSON dictionary in `demo_server.py` | Legacy dev health check; S2 will introduce versioned `/api/v1/health` |
| `/api/execute` | `POST` | Legacy `CASRouter.execute_cas_operation` (`mke_native_v1` + `sympy_cas_v0`) | Legacy CAS operations (`SIMPLIFY`, `DIFFERENTIATE`, `INTEGRATE`); segregated from S1 Algebra |
| `/api/plot` | `POST` | Legacy `CASRouter` with `default_op="PLOT_2D"` | Legacy 2D function plotter; segregated from S1 quadratic workspace |

### Authority Separation Mandate:
- The S1 Quadratic Algebra Workspace will **never** invoke `/api/execute` or `/api/plot`.
- Legacy CAS routes remain available solely for general symbolic queries and will never act as a fallback or override for S1 quadratic solving.

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
| **Request Validation** | Manual header, payload, and limit checks | **Automatic declarative body validation & 422 handlers** | Manual validation decorators |
| **Error Sanitization** | High risk of string exception leakage | **Centralized exception handlers & zero internal leaks** | Requires custom error handlers |
| **Testability** | Requires socket binding & live thread fixtures | **In-memory `starlette.testclient.TestClient` (fast, deterministic)** | `Flask.test_client` (WSGI) |
| **CORS & Middleware** | Manual header injection on every response | **Standard `CORSMiddleware` & security headers** | Requires `flask-cors` |
| **Maintenance Burden** | High (custom socket loop, buffer management) | **Low (declarative routers, industry standard)** | Medium |
| **Migration Risk** | Low external dependency addition | **Zero mathematical risk; isolated transport adapter** | Medium |
| **Legacy CAS Compatibility** | Native | **Legacy endpoints easily mounted or routed in parallel** | Compatible |

### Architectural Decision:
**Adopt Option B (FastAPI + Uvicorn)** as the production transport adapter for MKE MVP V1.
- `requirements.txt` will add `fastapi>=0.110.0,<1.0.0` and `uvicorn>=0.28.0,<1.0.0`.
- Existing `demo_server.py` is retained strictly for legacy dev/test backwards compatibility without serving as the S1 mathematical transport.

---

## 4. Route Namespace & Versioned Transport Contract

To prevent namespace collisions with legacy CAS routes (`/api/execute`, `/api/plot`), S2 establishes an explicit versioned API namespace:

```
/api/v1/
  ├── health                 [GET]   -> System health, version, engine capabilities
  └── algebra/
        └── solve            [POST]  -> S1 Pure Python solve_request() entry point
```

### 4.1 Route Specification: `POST /api/v1/algebra/solve`
- **Request Body:** Direct JSON representation of `SolveRequest`.
- **Response Body:** Direct JSON representation of `SolveResponseUnion` (`SolvedResponse` | `AnalyzedNoExecutionResponse` | `ErrorResponse`).
- **Transport Execution Policy:**
  ```python
  @router.post("/algebra/solve", response_model=SolveResponseUnion)
  async def solve_equation_endpoint(request: SolveRequest) -> SolveResponseUnion:
      # Direct delegation to pure application service — ZERO transport re-solving
      return solve_request(request)
  ```
- **Invariants:**
  - Zero SymPy/CAS fallback inside this route.
  - Zero mathematical solver or AST parsing duplicated in route handler.
  - Zero method-selection logic in transport layer.

### 4.2 Route Specification: `GET /api/v1/health`
- **Response:**
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

Transport status codes must strictly distinguish between **Transport / Request Malformation (4xx/5xx)** and **Mathematical Application States (HTTP 200)**:

```
                               ┌─────────────────────────────┐
                               │   Incoming HTTP Request     │
                               └──────────────┬──────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
             [ Valid JSON DTO ]                               [ Malformed Request ]
                     │                                                 │
          solve_request(SolveRequest)                       ┌──────────┴──────────┐
                     │                                      ▼                     ▼
       ┌─────────────┼─────────────┐                  Invalid JSON          DTO Validation
       ▼             ▼             ▼                  HTTP 400              HTTP 422
    SOLVED        ANALYZED       ERROR                (Malformed)           (Pydantic Error)
   HTTP 200       HTTP 200      HTTP 200
  (Verified)     (Degenerate/   (Syntax/Scope/
                 Unavailable)   Domain Error)
```

### Exact Status Code Matrix:

| Condition | HTTP Status Code | Response Payload Schema | Client UI Handling |
| :--- | :--- | :--- | :--- |
| **Equation Solved & Verified** | `200 OK` | `SolvedResponse` (`response_status="SOLVED"`) | Render solution card, roots, and step trace |
| **Analyzed (Degenerate $a=0$)** | `200 OK` | `AnalyzedNoExecutionResponse` (`reason_code="DEGENERATE_EXACT_SOLUTION"`) | Render degenerate solution card ($x=-c/b$, $\mathbb{R}$, $\emptyset$) |
| **Analyzed (Method Not Executable)** | `200 OK` | `AnalyzedNoExecutionResponse` (`reason_code="METHOD_NOT_EXECUTABLE"`) | Render method assessment & pedagogy note |
| **Analyzed (Method Not Applicable)** | `200 OK` | `AnalyzedNoExecutionResponse` (`reason_code="METHOD_NOT_APPLICABLE"`) | Render why-not-applicable explanation |
| **Application Domain Error** | `200 OK` | `ErrorResponse` (`error_code="SYNTAX_ERROR"`, `"DEGREE_OUT_OF_SCOPE"`, etc.) | Render inline error panel with error code & span |
| **Malformed JSON Body** | `400 Bad Request` | Standard FastAPI JSON error: `{"detail": "Malformed JSON payload"}` | Toast / banner: "Invalid JSON format" |
| **DTO Schema Validation Failure** | `422 Unprocessable Entity` | Standard FastAPI validation error (Pydantic `ValidationError`) | Form field error highlight |
| **Request Payload > 64 KB** | `413 Payload Too Large` | `{"detail": "Payload exceeds 65536 bytes limit"}` | Toast: "Input too large" |
| **Unsupported Media Type** | `415 Unsupported Media Type` | `{"detail": "Content-Type must be application/json"}` | Client network error |
| **Uncaught Transport Exception** | `500 Internal Server Error` | Sanitized error: `{"detail": "Internal server error occurred"}` | Toast: "Server temporarily unavailable" |

> [!IMPORTANT]
> Mathematical outcomes such as "No real roots" ($\Delta < 0$) or "Linear degenerate" ($a=0$) are valid mathematical truths, **not** HTTP errors, and return `HTTP 200 OK`.

---

## 6. DTO JSON Contract & Serialization Specification

The DTO models in `mke_product.application.dto` serve as the Single Source of Truth (SSOT). The transport layer performs zero transformations on these models.

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

#### B. COEFFICIENTS Mode (Direct Parametric / Live Edit):
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
    "problem_id": "prob_8f4a1c0d",
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
    "semantic_revision_hash": "sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
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
    }
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
          "explanation_vi": "Tính biệt thức Delta"
        }
      ],
      "final_answer_latex": "S = \\left\\{ 2, 3 \\right\\}"
    },
    "verification_scope": "FINAL_SOLUTION",
    "certificate": {
      "certificate_id": "cert_a91b2c3d",
      "problem_hash": "sha256_e3b0c442...",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "fp_7d8e9f...",
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
    "problem_id": "prob_deg_123",
    "raw_query": "2*x - 4 = 0",
    "equation_latex": "2x - 4 = 0",
    "category": "ALGEBRA_QUADRATIC",
    "classification": "LINEAR",
    "a": {"numerator": 0, "denominator": 1},
    "b": {"numerator": 2, "denominator": 1},
    "c": {"numerator": -4, "denominator": 1},
    "linear_root": {"numerator": 2, "denominator": 1},
    "semantic_revision_hash": "sha256_d1e2f3..."
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
      "certificate_id": "cert_deg_456",
      "problem_hash": "sha256_d1e2f3...",
      "outcome": "VERIFIED_COMPLETE",
      "integrity_fingerprint": "fp_deg_789",
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

## 7. Frontend Architecture Evaluation & Decision

We evaluate frontend technical options for the MKE Live Algebra Workspace:

```
                    ┌──────────────────────────────────────────────┐
                    │        Frontend Framework Evaluation         │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼────────────────────────────────┐
         ▼                                 ▼                                ▼
  [ Option 1 ]                      [ Option 2 ]                     [ Option 3 ]
React + TypeScript + Vite         Next.js (App Router)              Vanilla JS (UI00)
- Single Page App (SPA)           - Fullstack SSR/SSG framework     - No build toolchain
- Instant HMR dev server          - Requires Node.js server         - High UI state complexity
- Offline/Desktop packaging       - Complex hybrid runtime          - Difficult component reuse
- Clean boundary with Python API  - Heavy bundle overhead           - Weak type safety for DTOs
- Zero Node.js runtime in prod    - Unnecessary for local engine    - Poor maintainability
```

### Comparison Matrix:

| Evaluation Criterion | React + TypeScript + Vite (Recommended) | Next.js (App Router / SSR) | Vanilla JS (`ui/ui00`) |
| :--- | :--- | :--- | :--- |
| **Need for SSR** | None (client-side interactive algebra app) | Unnecessary overhead for local desktop/web SPA | None |
| **Routing Complexity** | Simple client-side routing / tab view | File-system routing with server components | Manual DOM swapping |
| **Offline / Local Deploy** | **Static build (`dist/`) servable by Python/FastAPI** | Requires active Node.js server runtime | Static files |
| **Python API Integration** | **Clean REST client against FastAPI `/api/v1`** | Server-side proxy or dual-server orchestration | Fetch API in `app.js` |
| **Build Complexity** | Minimal, instant Vite HMR (<50ms) | High (Webpack/Turbopack, server bundles) | None |
| **Type Safety with DTOs** | **Full TypeScript types auto-generated from Pydantic** | Full TypeScript support | No type safety (JSDoc only) |
| **Desktop Packaging** | **Trivial (Electron / Tauri / WebView / PyWebView)** | Complex due to Node.js backend dependency | Simple |
| **State Management** | Clean unidirectional state (Zustand / React Context) | Server Actions / Client State split | Global mutable state |

### Architectural Decision:
**Adopt React 18 + TypeScript + Vite** for the production MKE Live Algebra Workspace.
- Retains existing design tokens, color palette, typography, and WolframAlpha atmospheric aesthetics from `ui/ui00/DESIGN_TOKENS.md`.
- Static output build (`npm run build` -> `dist/`) is served directly by FastAPI in production or standalone during local dev via Vite proxy.

---

## 8. UI00 Visual Identity Preservation & Migration Map

The visual design established in `ui/ui00/` represents significant, accepted aesthetic investment. S2 will strictly preserve and adapt these assets rather than discarding them:

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

### Preservation Triage:
- **PRESERVED (100%):**
  - All color tokens (`--bg-canvas`, `--bg-surface`, `--border-accent`, 4 column domain colors).
  - Typography stacks (`Charter`, `Cambria Math`, `Cascadia Code`).
  - Capsule search box styling with violet 2px border and `=` compute capsule button.
  - Bilingual i18n dictionary structure (`vi` default, `en` toggle).
  - Offline-first vendored KaTeX distribution (`public/vendor/katex/`).
- **ADAPTED (Refactored to Component State):**
  - Result view layout refactored into modular React components (`<CanonicalProblemCard>`, `<MethodSelector>`, `<SolutionTrace>`, `<VerificationBadge>`).
  - Topic grid cards refactored to populate template expressions into the active state model.
- **DEPRECATED (Removed):**
  - 1500+ lines of imperative DOM manipulation in `ui/ui00/app.js`.
  - Manual innerHTML string concatenations and legacy `CASRouter` payload formatting.

---

## 9. Live Algebra Workspace State Model & Reactive Flows

The workspace state is structured as an immutable, unidirectional state machine driven by server response DTOs:

```typescript
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
  problem: CanonicalProblemUnion | null;
  availableMethods: MethodOptionView[];
  solution: VerifiedSolutionView | null;
  degenerateSolution: DegenerateSolutionView | null;
  noExecutionReason: NoExecutionReasonCode | null;
  error: ErrorResponse | null;
}
```

### 9.1 Flow A: RAW Text Solve
```
User types "x^2 - 5*x + 6 = 0" ➔ Click [ = ]
  ↳ POST /api/v1/algebra/solve { input_payload: { input_mode: "RAW_TEXT", raw_query: "..." } }
  ↳ Response: SolvedResponse (HTTP 200)
  ↳ State updates:
      - inputMode = "RAW_TEXT"
      - coefficients = { a: 1/1, b: -5/1, c: 6/1 } (from problem.a, b, c)
      - availableMethods = 9 methods
      - selectedMethodId = "QUAD_FORMULA_STANDARD"
      - solution = VerifiedSolutionView
```

### 9.2 Flow B: Method Switch (Zero Reparsing)
```
User clicks "Công thức nghiệm thu gọn (Δ')" in MethodSelector
  ↳ POST /api/v1/algebra/solve {
        input_payload: { input_mode: "COEFFICIENTS", a: {1,1}, b: {-5,1}, c: {6,1} },
        selected_method_id: "QUAD_FORMULA_REDUCED"
    }
  ↳ Response: SolvedResponse (HTTP 200)
  ↳ State updates:
      - problem.semantic_revision_hash remains IDENTICAL
      - solution.trace updates to QUAD_FORMULA_REDUCED steps
      - zero lexer/parser invocation
```

### 9.3 Flow C: Live Coefficient Edit
```
User edits coefficient `c` from 6 to 7 in CoefficientEditor
  ↳ POST /api/v1/algebra/solve {
        input_payload: { input_mode: "COEFFICIENTS", a: {1,1}, b: {-5,1}, c: {7,1} },
        selected_method_id: null
    }
  ↳ Response: SolvedResponse (HTTP 200, outcome="NO_REAL_ROOTS", Delta=-3)
  ↳ State updates:
      - problem.semantic_revision_hash is NEW
      - discriminant updates to -3
      - roots update to empty list
      - all dependent panels re-render automatically
```

### 9.4 Flow D: Quadratic $\to$ Degenerate Transition ($a \to 0$)
```
User edits coefficient `a` from 1 to 0 (with b=2, c=-4)
  ↳ POST /api/v1/algebra/solve {
        input_payload: { input_mode: "COEFFICIENTS", a: {0,1}, b: {2,1}, c: {-4,1} }
    }
  ↳ Response: AnalyzedNoExecutionResponse (reason_code="DEGENERATE_EXACT_SOLUTION")
  ↳ State updates:
      - problem.problem_type switches to "DEGENERATE"
      - availableMethods = []
      - degenerateSolution renders linear root x = 2 with VERIFIED_COMPLETE badge
      - Method selector panel safely unmounts or displays "Not applicable to linear equations"
```

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

### Component Responsibility Specifications:
1. **`<EquationInput />`**: Capsule text field with instant quick-keys (`^2`, `*`, `( )`), clear button, and submit handler dispatching `RAW_TEXT` solve.
2. **`<CoefficientEditor />`**: Interactive numeric/fraction parameter steppers for $a, b, c$. Allows direct live coefficient mutation without string typing.
3. **`<CanonicalProblemCard />`**: Displays the canonical LaTeX equation, classification badge, leading terms, and exact discriminant ($\Delta$, $\Delta'$).
4. **`<MethodSelector />`**: Renders all 9 registered methods with visual distinction between available/recommended, unavailable, and non-applicable methods.
5. **`<SolutionTrace />`**: Step-by-step accordion rendering exact intermediate LaTeX expressions and Vietnamese step explanations.
6. **`<VerificationBadge />`**: Displays the host independent verification certificate ID, timestamp, and tamper-evident green status shield.
7. **`<DegenerateResult />`**: Renders verified linear, identity, or contradiction solutions for $a=0$ boundaries.
8. **`<ErrorPanel />`**: Highlights syntax/domain errors with exact span offsets and localized guidance.

---

## 11. Method Selector UX Contract

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

### UX Selection Rules:
1. **Available + Applicable Selected:** Immediately requests and renders step-by-step trace.
2. **Unavailable Method Selected:** Requests `COEFFICIENTS` solve $\implies$ returns `ANALYZED_NO_EXECUTION` with `reason_code="METHOD_NOT_EXECUTABLE"` $\implies$ displays pedagogical guidance and explanation why execution is deferred.
3. **Non-Applicable Method Selected:** Requests `COEFFICIENTS` solve $\implies$ returns `ANALYZED_NO_EXECUTION` with `reason_code="METHOD_NOT_APPLICABLE"` $\implies$ displays mathematical prerequisite explanation (e.g. why $a+b+c \neq 0$).

---

## 12. Graph & Knowledge Integration Boundaries

### 12.1 Graph Integration Boundary (Deferred to S3)
- **Mathematical Authority:** Graph rendering will consume **only** canonical coefficients ($a, b, c$) and exact roots from `CanonicalQuadraticProblemView`.
- **Legacy Replacement:** The legacy `POST /api/plot` (which generates ad-hoc CAS images) will **not** be used for the quadratic workspace.
- **Future Renderer:** A deterministic 2D Canvas / SVG parabola renderer calculating vertex $(-\frac{b}{2a}, -\frac{\Delta}{4a})$, axis of symmetry, $y$-intercept $(0, c)$, and exact real $x$-intercepts directly from canonical S1 data.

### 12.2 Knowledge, Prerequisites & Tips Boundary (Deferred to S3)
- **Pedagogical Anchors:** Knowledge cards, theorem explanations, and remedial tips will bind strictly to stable domain identifiers:
  - `method_id` (e.g. `QUAD_FORMULA_STANDARD`)
  - `prerequisite_id` (e.g. `PREREQ_RADICALS`, `PREREQ_VIETE_SUM`)
  - `step.explanation_vi`
- **Zero Free-Form LLM Authority:** Remedial cards will be curated, deterministic pedagogical assets linked to rule IDs rather than unverified LLM generations.

---

## 13. Security, Resource & Transport Debt Findings

### Audited Debt in Legacy Transport (`demo_server.py`):
1. **Raw Exception Leakage:**
   - Line 268: `"error_message": f"Error reading request body: {exc}"`
   - Line 287: `"error_message": f"Invalid JSON payload: {exc}"`
   - Line 336: `"error_message": f"Invalid client execution options: {exc}"`
2. **Socket Buffer Deadlocks:** Manual monotonic deadline loops on slow trickle streams rather than standard ASGI timeout managers.
3. **HTTP Status Conflation:** Mathematical errors mapped to HTTP 422/408/500 rather than clean domain response envelopes.

### Production FastAPI Transport Security Architecture:
1. **Strict 64 KB Payload Limit:** Enforced by ASGI middleware before parsing.
2. **Zero Exception Leakage:** Global exception handler catches all unhandled exceptions and returns a generic, localized JSON error without stack traces or exception strings.
3. **Strict CORS Policy:** Configurable allowed origins (`http://localhost:5173`, `http://127.0.0.1:8080`).
4. **Header Validation:** Enforces `Content-Type: application/json`.

---

## 14. Implementation Acceptance Test Plan for S2

The future Stage S2 implementation must satisfy the following test suites:

### 14.1 Transport Integration Tests (`tests/test_transport_fastapi_s2.py`):
- `test_api_solve_raw_text_solved_parity`: HTTP `POST /api/v1/algebra/solve` matches direct `solve_request()` output bit-for-bit.
- `test_api_solve_coefficients_solved_parity`: HTTP `COEFFICIENTS` solve matches direct Python execution.
- `test_api_method_switch_reactivity`: Switching methods over HTTP updates trace while preserving `semantic_revision_hash`.
- `test_api_degenerate_solution_linear`: Linear equation returns HTTP 200 with `DEGENERATE_EXACT_SOLUTION`.
- `test_api_syntax_error_returns_http_200_error_response`: Mathematical syntax errors return HTTP 200 `ErrorResponse` with span.
- `test_api_invalid_json_returns_http_400`: Malformed JSON returns HTTP 400.
- `test_api_pydantic_validation_failure_returns_http_422`: Schema violations (e.g. invalid enum) return HTTP 422.
- `test_api_input_length_257_rejected_http_422`: 257-char string rejected at DTO boundary over HTTP.
- `test_api_payload_exceeding_64kb_returns_http_413`: Payloads > 64 KB return HTTP 413.
- `test_api_health_endpoint`: `GET /api/v1/health` returns healthy engine status.
- `test_api_zero_exception_leakage`: Injected server exception returns generic message without sentinel leak.

### 14.2 Live Workspace Browser Tests (`tests/test_browser_live_workspace_s2.py`):
- `test_workspace_raw_solve_flow`: User types equation, clicks compute, views solution card and step trace.
- `test_workspace_method_switch_flow`: User switches method tabs, trace updates without page reload or reparsing.
- `test_workspace_coefficient_editor_flow`: User modifies $c$, discriminant and roots update reactively.
- `test_workspace_quadratic_to_degenerate_transition`: User modifies $a \to 0$, UI switches to degenerate linear card.
- `test_workspace_9_methods_visibility`: All 9 methods appear in catalog with correct availability badges.
- `test_workspace_error_highlight`: Syntax error displays inline error panel with error code and span marker.

---

## 15. Staged S2 Implementation Roadmap

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Stage S2 Implementation Sequence                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-01: FastAPI Transport Adapter & Route Namespace Implementation                      │
│        - Add fastapi/uvicorn to requirements.txt                                       │
│        - Implement src/mke_product/transport/app.py & routers/algebra.py               │
│        - Connect /api/v1/algebra/solve directly to solve_request()                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-02: Transport Acceptance & Direct-vs-HTTP Parity Verification Suite                 │
│        - Implement tests/test_transport_fastapi_s2.py using TestClient                 │
│        - Prove 100% mathematical parity between direct Python and HTTP responses       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ S2-03: Production Frontend Shell Migration (React + TypeScript + Vite)                 │
│        - Initialize frontend package structure with Vite, React 18, TypeScript         │
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

The following capabilities are explicitly deferred to Stage S3 or subsequent milestones:
1. **Interactive 2D Parabola Canvas Plotter:** Function plotters and vertex/intercept drag handles (deferred to S3).
2. **Pedagogical Knowledge & Prerequisite Cards:** Curated formula cards, remediation tips, and related problem generators (deferred to S3).
3. **Database Persistence & Session Storage:** Problem history, user profiles, and PostgreSQL/SQLite integration (deferred).
4. **Photo / OCR Intake Pipeline:** Camera capture and handwritten image segmentation (deferred).
5. **Execution of Deferred Methods:** Factoring by grouping, AC method, completing the square, Viète root guessing, and graphical analysis execution workers (deferred).
6. **Synthetic Geometry Deduction UI:** Geometry canvas and synthetic theorem prover interface (deferred).

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

This preflight specification resolves all transport, state management, UI migration, and security integration requirements for MKE MVP V1 Stage S2.

**Milestone Status:** **`PENDING INDEPENDENT S2-P0 AUDIT`**
