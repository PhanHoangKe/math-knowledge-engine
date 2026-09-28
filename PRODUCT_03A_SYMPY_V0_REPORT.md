# MKE PRODUCT-03A: MULTI-ENGINE MATHEMATICAL PRODUCT
## SymPy CAS Integration v0 Technical Architecture & Delivery Report

---

### 1. Executive Summary & Delivery Scope

This document reports the delivery of **MKE PRODUCT-03A (SymPy CAS Integration v0)**.

The Math Knowledge Engine (MKE) has been upgraded from a narrow formal linear arithmetic kernel into an extensible **Multi-Engine Computer Algebra System (CAS)** architecture. Rather than reimplementing well-established symbolic algorithms from scratch, MKE now orchestrates specialized engines:
1. **`mke_native_v1`**: The verified, deterministic, formal proof-generating linear equation solver.
2. **`sympy_cas_v0`**: The mature SymPy 1.14.0 symbolic engine for general algebra, calculus, and function plotting.
3. **Future Extension Stubs**: Declared capability contracts for planned engines `scipy_numerical` and `sagemath_cas`.

All 349 test cases (326 baseline regression tests + 23 comprehensive multi-engine CAS acceptance tests) pass with **zero failures** on Windows.

---

### 2. Multi-Engine Architecture & Contracts

#### 2.1 Standardized Engine Interface (`MathEngine`)
Every engine implements the abstract base contract:
- `engine_id`: Unique identifier string (e.g., `"mke_native_v1"`, `"sympy_cas_v0"`).
- `get_capabilities()`: Returns an `EngineCapability` descriptor detailing supported operations, version, license, and verification status.
- `can_handle(request)`: Fast predicate inspecting whether the AST/operation is within scope.
- `execute(request)`: Executes the mathematical operation and returns an `ExecutionResponse`.

#### 2.2 Versioned Request/Response Envelopes
- **`ExecutionRequest`**: Encapsulates `operation` (`SOLVE`, `SIMPLIFY`, `DIFFERENTIATE`, `INTEGRATE`, `PLOT_2D`, `CHECK_CANDIDATE`), `raw_input`, validated `ast`, `variable`, `options`, `preferred_engine`, and `timeout_sec`.
- **`ExecutionResponse`**: Standardized JSON-serializable envelope (`schema_version: "mke.product03a.v0"`) containing `mathematical_status` (`SUCCESS`, `DOMAIN_ERROR`, `RESOURCE_EXHAUSTED`, `SECURITY_REJECTED`, `INVALID_INPUT`, `OUT_OF_SCOPE`), `symbolic_result`, `latex_output`, `domain_restrictions`, `plot_data`, `verification_evidence`, `execution_duration_sec`, and diagnostics.

#### 2.3 Deterministic Engine Routing (`EngineRouter`)
1. **Pre-flight & Security Check**: Validates input length bounds and regex security filter against forbidden Python keywords/dunders.
2. **Safe Parsing & AST Safety Guard**: Parses input using bounded tokenization and recursive descent, inspecting constant division by zero and indeterminate forms (e.g. $0^0$).
3. **Explicit Override**: If `preferred_engine` is requested, attempts execution on that engine with graceful fallback if unsupported.
4. **Deterministic Dispatch**:
   - Linear equations are routed to `mke_native_v1` for formal step generation.
   - Non-linear equations, polynomial simplification, differentiation, integration, and 2D plotting are dispatched to `sympy_cas_v0`.

---

### 3. Core Capabilities Implemented

| Operation | Input Example | Engine Used | Symbolic Output | LaTeX Output |
| :--- | :--- | :--- | :--- | :--- |
| **`SOLVE` (Quadratic)** | `x^2 - 4 = 0` | `sympy_cas_v0` | `{-2, 2}` | `\left\{-2, 2\right\}` |
| **`SOLVE` (Linear Formal)** | `2*x + 4 = 10` | `mke_native_v1` | `{3}` | `\left\{ 3 \right\}` (with formal proof steps) |
| **`DIFFERENTIATE`** | `x^2 + 3*x` | `sympy_cas_v0` | `2*x + 3` | `2 x + 3` |
| **`INTEGRATE` (Indefinite)** | `x^2` | `sympy_cas_v0` | `x^3/3 + C` | `\frac{x^{3}}{3} + C` |
| **`INTEGRATE` (Definite)** | `x^2` ($[0, 3]$) | `sympy_cas_v0` | `9` | `9` |
| **`SIMPLIFY`** | `(x+1)*(x-1)` | `sympy_cas_v0` | `x^2 - 1` | `x^{2} - 1` |
| **`SIMPLIFY` (Rational)** | `(x^2 - 1)/(x - 1)` | `sympy_cas_v0` | `x + 1` | `x + 1` (Domain: $x \neq 1$) |
| **`PLOT_2D`** | `x^2 - 1` | `sympy_cas_v0` | `x^2 - 1` | Multi-point SVG / Coordinate Segments |
| **`PLOT_2D` (Asymptote)** | `1/(x - 2)` | `sympy_cas_v0` | `1/(x - 2)` | Segments split across singularity at $x = 2$ |

---

### 4. Security Invariants & AST Bridge

1. **No Code Injection / No `eval()` / No `sympify()` on Raw Strings**:
   Untrusted user input is NEVER evaluated as Python code or passed to raw `sympify()` / `parse_expr()`. Input is strictly tokenized by MKE's lexer and parsed into an immutable typed AST (`IntegerLiteral`, `Variable`, `UnaryOp`, `BinaryOp`, `Group`, `Power`, `CASPower`, `Equation`). The AST bridge (`ast_bridge.py`) constructs SymPy objects directly by traversing typed AST nodes.
2. **Pre-Simplification Domain Restriction Preservation**:
   Expressions with denominators (e.g. `(x-1)/(x-1) = 1` or `(x^2-1)/(x-1)`) extract root singularities prior to algebraic cancellation, preserving domain warnings ($x \neq 1$) and LaTeX output ($\mathbb{R} \setminus \{ 1 \}$).
3. **Bounded Computation**:
   - Max input length: 4,096 characters.
   - Max integer literal size: 256 digits.
   - Max parentheses nesting depth: 16 levels.
   - Plot sampling bound: 1,000 points maximum.

---

### 5. Interactive Demo Web UI & Server

A standalone lightweight HTTP demo server is included in `src/mke_product/cas/demo_server.py`:
- Serves static assets (`src/mke_product/cas/static/index.html`).
- KaTeX integration for real-time mathematical typography rendering.
- Embedded interactive SVG canvas for 2D curve plotting with automatic domain singularity splitting.
- Quick test chips covering quadratic solve, derivative, integral, rational simplification, asymptote plotting, and malicious input rejection.
- Zero extra web dependencies: runs using Python's standard library `http.server`.

---

### 6. Deliverable Inventory

- `src/mke_product/cas/__init__.py`: Package export interface.
- `src/mke_product/cas/contracts.py`: Multi-engine data contracts, enums, capability descriptors.
- `src/mke_product/cas/safety.py`: Bounds checking, AST safety inspector, domain extraction.
- `src/mke_product/cas/cas_parser.py`: Safe recursive-descent parser for general polynomial expressions.
- `src/mke_product/cas/ast_bridge.py`: Strict AST-to-SymPy conversion bridge.
- `src/mke_product/cas/serialization.py`: Mathematical formatting (`^` power formatting, LaTeX generation, $+ C$).
- `src/mke_product/cas/sympy_adapter.py`: SymPy engine adapter implementing CAS operations.
- `src/mke_product/cas/native_adapter.py`: Formal verified MKE linear engine adapter.
- `src/mke_product/cas/registry.py`: Engine registry with active engines and future stubs.
- `src/mke_product/cas/router.py`: Deterministic multi-engine dispatcher.
- `src/mke_product/cas/demo_server.py`: Interactive HTTP server and REST API.
- `src/mke_product/cas/static/index.html`: Web interface with KaTeX and SVG plotting.
- `tests/test_cas_product03a.py`: Comprehensive acceptance test suite.
- `scripts/run_and_log_cas_tests.py`: Official test runner and evidence capture script.
- `evidence/p03a_v0/cas_test_suite_raw.log`: Full raw console log.
- `evidence/p03a_v0/cas_test_results.json`: Machine-readable test execution report.

---

### 7. Final Status

- **Tested Git Revision**: Branch `product/p03a-sympy-cas-v0` (Worktree `D:\mke-product-cas-v0`).
- **Full Test Suite**: **349 / 349 tests PASS (100%)**.
- **Delivery Status**: **`PENDING INDEPENDENT PRODUCT-03A AUDIT`**.
