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

### 2.1 Clone & Python Environment
```powershell
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
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install selenium
```

### 2.2 Frontend Dependencies & Production Build
```bash
cd src/frontend
npm ci
npm run build
cd ../..
```

*Note:* `npm run build` compiles TypeScript and bundles the production React application into `src/frontend/dist` with bundled offline KaTeX fonts, CSS, and JS assets.

---

## 3. Running MKE MVP V1

### 3.1 Production Mode (Single Combined ASGI Server)
The production ASGI application (`src/mke_product/product_app.py`) serves both the FastAPI `/api/v1/*` backend endpoints and the compiled React static assets from `src/frontend/dist`:

```powershell
uvicorn --app-dir src mke_product.product_app:app --host 127.0.0.1 --port 8000
```

- **Application URL:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **API Health Check:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Documentation (ReDoc):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

*Routing Semantics:* Root `/` and built static assets (`/assets/*`, `/vendor/*`, `favicon.ico`) are served directly. No broad client-side route fallback for arbitrary unmapped URLs is promised in MVP V1.

### 3.2 Development Mode (Dual-Process Live Reload)
For local development with Hot Module Replacement (HMR) and backend auto-reload:

**Terminal 1 — Backend FastAPI Server:**
```powershell
uvicorn --app-dir src mke_product.transport.app:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend Vite Dev Server:**
```powershell
cd src/frontend
npm run dev
```
Vite dev server proxies `/api/*` calls from `http://127.0.0.1:5173/` to `http://127.0.0.1:8000/`.

---

## 4. Test Suite Execution & Verification

### 4.1 Frontend Verification Gates
```powershell
cd src/frontend

# 1. API Contract Verification
npm run generate:api
npm run check:api

# 2. TypeScript Strict Typecheck (0 errors)
npm run typecheck

# 3. Unit & Component Test Suite (100 tests in 14 files)
npm test

# 4. Production Build Verification
npm run build

cd ../..
```

### 4.2 Backend Transport & Core Algebra Gates
```powershell
# 1. FastAPI Transport Contract & Acceptance Suites (149 tests)
pytest -q tests/test_transport_fastapi_s2_smoke.py tests/test_transport_fastapi_s2_acceptance.py

# 2. Core S1 Mathematical Engine & Domain Invariants (278 tests)
pytest -q tests/test_application_s1_acceptance.py tests/test_application_orchestrator_s1.py tests/test_application_traces_s1.py tests/test_application_degenerate_s1.py tests/test_application_normalizer_s1.py tests/test_domain_core_s0.py
```

### 4.3 Production Composition & Real Browser E2E Gates
```powershell
# 1. Production ASGI Product App Composition (16 tests)
pytest -q tests/test_mvp_v1_product_app.py

# 2. Real Browser Headless Chrome E2E Suite (11 tests)
pytest -q tests/test_mvp_v1_react_e2e.py
```

### 4.4 Full Regression Suite
```powershell
pytest tests/ -q
```

---

## 5. Mathematical Scope, Boundaries & Invariants

| Category | In-Scope & Frozen (MVP V1) | Out-of-Scope / Explicit Non-Goals |
| :--- | :--- | :--- |
| **Equation Classes** | True Quadratic ($ax^2 + bx + c = 0, a \neq 0$) & Degenerate (`LINEAR`, `IDENTITY`, `CONTRADICTION`) produced via intake/normalization | Cubic, Quartic, Trigonometric, Transcendental, Calculus, Geometry |
| **Number Field** | Real field $\mathbb{R}$ with exact arithmetic on $\mathbb{Q}$ ($\text{gcd}$-reduced, canonical signs, zero-denominator rejected) | Complex roots $\mathbb{C}$, floating-point approximations in solver core |
| **Methods Catalog** | 9 frozen method IDs (`QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_FACTORIZATION_Q`, `QUAD_FACTORIZATION_R`, `QUAD_COMPLETE_SQUARE`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`, `QUAD_VIETE_SUM_PRODUCT`, `QUAD_GRAPHICAL_ANALYSIS`) | Dynamic method injection, uncertified external solvers |
| **Executable Methods** | `QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF` | Remaining 5 methods return `ANALYZED_NO_EXECUTION` with truthful pedagogical reasons |
| **Verification** | Independent host verifiers (`MKE_QUADRATIC_HOST_VERIFIER_V1`, `MKE_DEGENERATE_HOST_VERIFIER_V1`) producing unkeyed SHA-256 integrity fingerprints | Cryptographic signatures (deprecated), client-side self-verification, LLM proofs |
| **UI & Assets** | 100% offline same-origin KaTeX font bundle, reactive coefficient editor (350ms debounce), revision history, VI/EN i18n, light/dark themes | External CDN font fetches, Canvas/WebGL graphing library |
