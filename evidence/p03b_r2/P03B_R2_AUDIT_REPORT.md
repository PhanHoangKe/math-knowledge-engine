# MKE PRODUCT-03B-R2: Targeted Soundness & Resource Isolation Remediation Audit Report

**Date:** 2026-09-28  
**Milestone:** PRODUCT-03B-R2  
**Repository:** `https://github.com/PhanHoangKe/math-knowledge-engine`  
**Baseline Commit:** [`18b30a4f05143fd7fdf2cd240150883c05c06ff9`](https://github.com/PhanHoangKe/math-knowledge-engine/commit/18b30a4f05143fd7fdf2cd240150883c05c06ff9)  
**Branch:** `product/p03b-r2-remediation`  
**Tested Source Commit:** `d3e14f93b57341f7202aa42e9ef16a2b3db259e7`  

---

## 1. Executive Summary

This audit report documents the remediation and verification of **MKE PRODUCT-03B-R2 — Targeted Soundness & Resource Isolation Remediation**.

All four mandate objectives have been fully satisfied:
1. **HTTP Hardening:** Reject negative, zero, malformed, and oversized `Content-Length` headers deterministically before reading the socket. Reject non-object top-level JSON payloads (arrays, strings, numbers, booleans, null) without crashing the request handler. Comprehensive adversarial tests (including bounded raw TCP socket tests) verify zero hangs or server unresponsiveness.
2. **Original AST Variable Scope:** Free variable counts for `SOLVE_SYSTEM` ($\le 2$ variables) and `SOLVE_INEQUALITY` ($\le 1$ variable) are enforced strictly on the **original AST** before algebraic cancellation or simplification. Expressions like `x + 0*z = 1, y = 2` and `x - x + y > 0` are rejected as `OUT_OF_SCOPE`.
3. **Auditable Domain Certainty Proof:** Replaced pattern matching heuristics with a mathematical completeness audit (`is_domain_determination_complete()`). The domain is classified as `EXPLICIT_EXCLUSIONS` if and only if all denominators are proven univariate polynomials with exact, exhaustively accounted rational roots. Incomplete cases (irrational roots, degree $> 2$, multivariate expressions, radical functions) return `NOT_FULLY_DETERMINED`.
4. **Evidence & Reproducibility:** Full Windows regression test suite executed (456 passed, 0 failed, 18 subtests passed in 113.45s). Tested source commit and final evidence commit are cleanly separated and tracked.

---

## 2. Objective Implementation Details

### Objective 1 — HTTP Hardening (`src/mke_product/cas/demo_server.py`)
- **Content-Length Validation:**
  - Missing `Content-Length`: HTTP 400 `INVALID_INPUT`.
  - Non-numeric / malformed `Content-Length`: HTTP 400 `INVALID_INPUT`.
  - Negative or zero `Content-Length` ($\le 0$): HTTP 400 `INVALID_INPUT` (evaluated prior to calling `rfile.read()`).
  - Oversized `Content-Length` ($> 65536$): HTTP 413 `RESOURCE_EXHAUSTED` (evaluated prior to reading body).
- **Top-Level JSON Type Validation:**
  - Verified `isinstance(payload, dict)`. Arrays (`[...]`), primitive strings (`"..."`), numbers, booleans (`true`), and `null` are rejected with HTTP 400 `INVALID_INPUT` without uncaught exceptions or socket stalls.
- **Client Execution Options Enforcement:**
  - Forbidden keys (`in_process`, `sleep_seconds`, `engine_override`, `timeout_sec`, `simulate`, `direct`, `internal`) are rejected with HTTP 400 `INVALID_INPUT`.

### Objective 2 — Original AST Variable Scope (`src/mke_product/cas/sympy_adapter.py`)
- In `_execute_solve_system`:
  - `orig_vars = sorted(list(ast_node.variables()))`
  - If `len(orig_vars) > 2`, immediately returns `OUT_OF_SCOPE` (`Linear system has N variables in original input; maximum 2 variables supported in v0`).
- In `_execute_solve_inequality`:
  - `orig_vars = sorted(list(ast_node.variables()))`
  - If `len(orig_vars) > 1`, immediately returns `OUT_OF_SCOPE` (`Multivariate inequalities with N variables in original input are out of scope for v0 single-variable inequality solver`).

### Objective 3 — Auditable Domain Certainty Proof (`src/mke_product/cas/safety.py`)
- Implemented `is_domain_determination_complete(node: Optional[ASTNode], restrictions: List[str]) -> bool`:
  1. Expression must be univariate or constant (`len(node.variables()) <= 1`).
  2. Every denominator must be a polynomial of degree $\le 2$ with rational coefficients:
     - Linear ($ax+b$): root $-b/a \in \mathbb{Q}$ must be in `restrictions`.
     - Quadratic ($ax^2+bx+c$): discriminant $\Delta = b^2 - 4ac$:
       - $\Delta < 0$: 0 real roots $\to$ no exclusions needed (e.g. $1/(x^2+1) \implies \text{PROVEN\_REALS}$).
       - $\Delta == 0$: 1 real root $-b/(2a) \in \mathbb{Q} \to$ must be in `restrictions`.
       - $\Delta > 0$: 2 real roots $\to$ permitted only if $\sqrt{\Delta} \in \mathbb{Q}$ and both rational roots are in `restrictions`. If $\sqrt{\Delta} \notin \mathbb{Q}$, returns `NOT_FULLY_DETERMINED`.
     - Degree $> 2$ or non-polynomial: returns `NOT_FULLY_DETERMINED`.
  3. No radical functions, transcendental functions, or unsupported AST nodes.
  4. Exponent 0 base checks ($x^0 \implies x \neq 0$).
  5. Required exclusions must exactly match provided `restrictions`.

---

## 3. Before/After Counterexample & Soundness Matrix

| Scenario / Counterexample | Input | Expected Outcome | R1 Status | R2 Status (Current) | Rationale |
|---|---|---|---|---|---|
| **AST Scope (System)** | `x + 0*z = 1, y = 2` | `OUT_OF_SCOPE` | `SUCCESS` (bypass via cancel) | **`OUT_OF_SCOPE`** | Original AST has $\{x, y, z\}$ (3 vars $> 2$) |
| **AST Scope (Inequality)** | `x - x + y > 0` | `OUT_OF_SCOPE` | `SUCCESS` (bypass via cancel) | **`OUT_OF_SCOPE`** | Original AST has $\{x, y\}$ (2 vars $> 1$) |
| **Valid System** | `2*x + 3*y = 5, x - y = 1` | `SUCCESS` ($x = 8/5, y = 3/5$) | `SUCCESS` | **`SUCCESS`** | 2 variables in original AST |
| **Valid Inequality** | `x^2 - 4 > 0` | `SUCCESS` | `SUCCESS` | **`SUCCESS`** | 1 variable in original AST |
| **Negative Content-Length** | Raw socket `Content-Length: -25` | HTTP 400 `INVALID_INPUT` | Unhandled / Hung | **HTTP 400 `INVALID_INPUT`** | Validated before stream read |
| **Zero Content-Length** | Raw socket `Content-Length: 0` | HTTP 400 `INVALID_INPUT` | 400 (partial) | **HTTP 400 `INVALID_INPUT`** | Strict positive integer check |
| **Non-Object JSON (Array)** | `[{"operation": "SOLVE"}]` | HTTP 400 `INVALID_INPUT` | 400 (AttributeError) | **HTTP 400 `INVALID_INPUT`** | Strict top-level type check |
| **Non-Object JSON (String)** | `"just a string"` | HTTP 400 `INVALID_INPUT` | 400 (AttributeError) | **HTTP 400 `INVALID_INPUT`** | Strict top-level type check |
| **Domain (Reducible Quad)** | `1 / (x^2 - 4)` | `EXPLICIT_EXCLUSIONS` | String pattern match | **`EXPLICIT_EXCLUSIONS`** | Statically proven exhaustive ($\Delta=16$) |
| **Domain (Irreducible Quad)** | `1 / (x^2 + 1)` | `PROVEN_REALS` | Regex fallback | **`PROVEN_REALS`** | Statically proven 0 real roots ($\Delta=-4$) |
| **Domain (Irrational Roots)** | `1 / (x^2 - 2)` | `NOT_FULLY_DETERMINED` | Regex fallback | **`NOT_FULLY_DETERMINED`** | $\Delta=8$, $\sqrt{8} \notin \mathbb{Q}$ |
| **Domain (Multivariate)** | `(x + y) / (x - y)` | `NOT_FULLY_DETERMINED` | Pattern match | **`NOT_FULLY_DETERMINED`** | 2 variables in denominator |

---

## 4. Modified-File Inventory

| File | Type | Description of Changes |
|---|---|---|
| [`src/mke_product/cas/demo_server.py`](file:///D:/mke-product-ui-r4/src/mke_product/cas/demo_server.py) | Source | Strict Content-Length validation ($\le 0$, malformed, $>65536$) and top-level JSON dict validation. |
| [`src/mke_product/cas/sympy_adapter.py`](file:///D:/mke-product-ui-r4/src/mke_product/cas/sympy_adapter.py) | Source | Original AST variable scope enforcement for `SOLVE_SYSTEM` and `SOLVE_INEQUALITY`. |
| [`src/mke_product/cas/safety.py`](file:///D:/mke-product-ui-r4/src/mke_product/cas/safety.py) | Source | Mathematical completeness audit function `is_domain_determination_complete()`. |
| [`tests/test_cas_http_integration.py`](file:///D:/mke-product-ui-r4/tests/test_cas_http_integration.py) | Test | Added raw socket negative/zero/malformed Content-Length tests, top-level payload tests, option tests. |
| [`tests/test_cas_product03b_expansion.py`](file:///D:/mke-product-ui-r4/tests/test_cas_product03b_expansion.py) | Test | Added tests for `x+0*z=1, y=2`, `x-x+y>0`, and auditable domain certainty proofs. |
| [`scripts/run_and_log_p03b_r2_tests.py`](file:///D:/mke-product-ui-r4/scripts/run_and_log_p03b_r2_tests.py) | Script | Test runner and structured evidence generator for P03B-R2. |

---

## 5. Verification Test Suite Results

- **Test Suite Runner:** `scripts/run_and_log_p03b_r2_tests.py`
- **Total Tests Collected & Run:** 456
- **Passed:** 456
- **Failed:** 0
- **Subtests Passed:** 18
- **Duration:** 113.45s
- **Exit Code:** 0
- **Environment:** Windows (win32), Python 3.10.11, pytest-9.1.1
- **Log Files:**
  - `evidence/p03b_r2/p03b_r2_test_suite_raw.log`
  - `evidence/p03b_r2/p03b_r2_test_results.json`

---

## 6. Residual Risks & Future Milestones

1. **Higher-Degree Polynomial Denominators:** Denominators with degree $\ge 3$ or irrational roots are safely and conservatively classified as `NOT_FULLY_DETERMINED` in v0. Future milestones (Product-03C+) can expand algebraic root isolation and interval arithmetic.
2. **Multivariate Denominators:** Multivariate rational domain restrictions represent geometric curves / hypersurfaces (e.g. $x \neq y$) and are properly classified as `NOT_FULLY_DETERMINED` in v0.
3. **Branch Publishing:** This milestone is strictly isolated on branch `product/p03b-r2-remediation` and preserves the R1 baseline without merging.
