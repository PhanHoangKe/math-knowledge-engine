# MKE MVP V1 — Production & Development Run Guide

**Math Knowledge Engine (MKE) MVP V1**  
*Deterministic Formal Symbolic Reasoning & Exact Rational Mathematics on $\mathbb{R}$ with Arithmetic on $\mathbb{Q}$*

---

## 1. System Requirements

- **Operating System:** Windows 10/11, Linux (Ubuntu 20.04+), or macOS (12+)
- **Python:** Version `3.10` or higher (`3.10.x` / `3.11.x` / `3.12.x`)
- **Node.js:** Version `18.x` or higher (with `npm 9+`)
- **Browser & Driver (for E2E tests):** Google Chrome and matching ChromeDriver installed on `PATH`

---

## 2. Fresh Installation & Setup

### 2.1 Clone & Python Virtual Environment
```bash
# Clone the repository
git clone https://github.com/PhanHoangKe/math-knowledge-engine.git
cd math-knowledge-engine

# Create and activate Python virtual environment
# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS (Bash):
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install fastapi uvicorn starlette pydantic httpx pytest selenium
```

### 2.2 Frontend Dependencies & Production Build
```bash
cd src/frontend
npm ci
npm run build
cd ../..
```

*Note:* `npm run build` generates the production static bundle in `src/frontend/dist` with bundled offline KaTeX fonts, CSS, and JS assets.

---

## 3. Running MKE MVP V1

### 3.1 Production Mode (Single Combined ASGI Server)
The production ASGI application (`src/mke_product/product_app.py`) serves both the FastAPI `/api/v1/*` backend endpoints and the compiled React SPA static assets from a single unified server instance:

```bash
uvicorn mke_product.product_app:app --host 127.0.0.1 --port 8000
```

- **Application URL:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **API Documentation (OpenAPI / Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Redoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3.2 Development Mode (Dual-Process Live Reload)
For local development with Hot Module Replacement (HMR) and backend auto-reload:

**Terminal 1 — Backend FastAPI Server:**
```bash
uvicorn mke_product.transport.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend Vite Dev Server:**
```bash
cd src/frontend
npm run dev
```
Vite proxy forwards all `/api/*` calls from `http://127.0.0.1:5173/` directly to `http://127.0.0.1:8000/`.

---

## 4. Test Suite Execution & Verification

### 4.1 Frontend Verification Gates
```bash
cd src/frontend

# 1. API Contract Verification (15 tests)
npm run check:api

# 2. TypeScript Strict Typecheck (0 errors)
npm run typecheck

# 3. Unit & Component Test Suite (100 tests)
npm test

cd ../..
```

### 4.2 Backend Transport & Core Algebra Gates
```bash
# 1. FastAPI Transport Contract & Acceptance Suites (149 tests)
pytest -q tests/test_transport_fastapi_s2_smoke.py tests/test_transport_fastapi_s2_acceptance.py

# 2. Core S1 Mathematical Engine & Domain Invariants (278 tests)
pytest -q tests/test_application_s1_acceptance.py tests/test_application_orchestrator_s1.py tests/test_application_traces_s1.py tests/test_application_degenerate_s1.py tests/test_application_normalizer_s1.py tests/test_domain_core_s0.py
```

### 4.3 Production Composition & Real Browser E2E Gates
```bash
# 1. Production ASGI Product App Composition (13 tests)
pytest -q tests/test_mvp_v1_product_app.py

# 2. Real Browser Headless Chrome E2E Suite (11 tests)
pytest -q tests/test_mvp_v1_react_e2e.py
```

### 4.4 Full Regression Suite
```bash
pytest tests/ -q
```

---

## 5. Mathematical Scope, Boundaries & Invariants

| Category | In-Scope & Frozen (MVP V1) | Out-of-Scope / Explicit Non-Goals |
| :--- | :--- | :--- |
| **Equation Classes** | Standard Quadratic ($ax^2 + bx + c = 0, a \neq 0$) & Degenerate Linear ($0x^2 + bx + c = 0, b \neq 0$) | Cubic, Quartic, Trigonometric, Transcendental, Calculus, Geometry |
| **Number Field** | Real field $\mathbb{R}$ with exact rational arithmetic on $\mathbb{Q}$ ($\text{gcd}$-reduced, canonical signs, zero-denominator rejected) | Complex roots $\mathbb{C}$, floating-point approximations in solver core |
| **Methods Catalog** | 9 frozen method IDs (`QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_FACTORIZATION_Q`, `QUAD_FACTORIZATION_R`, `QUAD_COMPLETE_SQUARE`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`, `QUAD_VIETE_SUM_PRODUCT`, `QUAD_GRAPHICAL_ANALYSIS`) | Dynamic method injection, uncertified external solvers |
| **Executable Methods** | `QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF` | Remaining 5 methods return `ANALYZED_NO_EXECUTION` with truthful pedagogical reasons |
| **Verification** | Independent host verifiers (`MKE_QUADRATIC_HOST_VERIFIER_V1`, `MKE_DEGENERATE_HOST_VERIFIER_V1`) producing SHA-256 certificate fingerprints | Client-side self-verification, LLM-generated proofs |
| **UI Rendering** | 100% offline KaTeX font bundle, reactive coefficient editor with 350ms debounce, revision history, VI/EN i18n, light/dark themes | External CDN font fetches, Canvas/WebGL graphing library |
