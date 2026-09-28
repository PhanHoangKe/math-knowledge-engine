# MKE PRODUCT-03B-R1: Resource Isolation & Mathematical Soundness Audit Report

**Date:** 2026-09-28  
**Milestone:** PRODUCT-03B-R1  
**Branch:** `product/p03b-r1-soundness`  
**Repository:** `https://github.com/PhanHoangKe/math-knowledge-engine`  
**Baseline Commit:** `7b59a35a0cead8f1e070b5ec0df0e351f0d0ec6a`  
**Tested Source Commit:** `aceacfff2916d5f3bfa09408771ea1606d87eed8`  

---

## 1. Executive Summary

This audit report documents the implementation and verification of **MKE PRODUCT-03B-R1: Resource Isolation & Mathematical Soundness**. 

All requirements established in the gate specification have been strictly implemented and verified:
1. **Resource Isolation & Option Protection:** Client-supplied options from untrusted HTTP endpoints are strictly sanitized using `sanitize_client_options()`. Client attempts to inject internal supervisor options (`in_process`, `sleep_seconds`, `timeout_sec`, `engine_override`) are rejected with HTTP 400 `INVALID_INPUT`.
2. **Original Domain Mathematical Soundness:** Mathematical scope rules are now enforced on the **original AST** prior to algebraic cancellation (`sympy.cancel()`). Expressions with variable denominators (e.g. `(x-1)/(x-1)`) are rejected as `OUT_OF_SCOPE` for v0 polynomial inequality and linear system solvers, preventing incorrect real domain claims.
3. **Domain Certainty Contract:** `assess_domain_certainty()` now strictly requires verifiable point exclusions for `EXPLICIT_EXCLUSIONS`, outputs `PROVEN_REALS` only for valid polynomial expressions without restrictions, and defaults to `NOT_FULLY_DETERMINED` for multivariate or unproven domains.
4. **Canonical UI Notation:** The UI presentation for `SOLVE_SYSTEM` in `ui/ui00/app.js` now renders clean equation assignments without redundant variable prefixes (preventing `(x, y) = x = 8/5, y = 3/5`).
5. **Full Test Suite & Non-Regression:** The complete automated test suite (436 passed, 0 failed, 18 subtests passed) executed cleanly on Windows.

---

## 2. Reproduction of Defects (Preflight)

Prior to implementing the corrections, both audit defects were reproduced and confirmed:

### Defect 1: Removable Singularity Domain Corruption
- **Input:** `(x - 1) / (x - 1) > 0`
- **Previous Behavior:** The solver performed `sympy.cancel()` before scope checks, transforming `(x - 1)/(x - 1)` into `1`, solving `1 > 0`, and returning `(-oo, oo)` with `PROVEN_REALS`.
- **Mathematical Invalidation:** At $x = 1$, the original expression is undefined. Treating it as $(-\infty, \infty)$ violated domain soundness.

### Defect 2: Untrusted Client Option Injection
- **Input:** Public HTTP POST `/api/execute` with payload `{"operation": "SOLVE", "input": "x = 1", "options": {"in_process": true, "sleep_seconds": 60}}`
- **Previous Behavior:** The demo server forwarded the raw client `options` dict directly to `EngineRouter.execute()`, allowing external clients to bypass process containment or induce sleep timeouts.

---

## 3. Implementation Details

### A. Client Option Sanitization (`src/mke_product/cas/safety.py` & `src/mke_product/cas/demo_server.py`)
- Created `FORBIDDEN_CLIENT_OPTION_KEYS = {"in_process", "sleep_seconds", "engine_override", "timeout_sec", "simulate", "direct", "internal"}`.
- Added `sanitize_client_options(options: Dict[str, Any]) -> Dict[str, Any]` which raises `ValueError` if any forbidden key is present in client HTTP payloads.
- Updated `CASDemoHTTPRequestHandler.do_POST` to strictly validate `options` and `preferred_engine`, rejecting unauthorized options with HTTP 400 `INVALID_INPUT` and unknown engines with HTTP 400 `OUT_OF_SCOPE`.

### B. Original AST Polynomial Scope Enforcement (`src/mke_product/cas/sympy_adapter.py`)
- Imported `is_polynomial_ast` in `sympy_adapter.py`.
- Added original AST scope checks in `_execute_solve_system` and `_execute_solve_inequality`:
  ```python
  if not is_polynomial_ast(ast_node):
      response.mathematical_status = EngineStatus.OUT_OF_SCOPE
      response.error_message = "Expressions with variable denominators or non-polynomial terms are out of scope for v0 polynomial solver"
      return
  ```
- Evaluated prior to `sympy.cancel()`, ensuring expressions with removable singularities are rejected as `OUT_OF_SCOPE` rather than incorrectly simplified.

### C. Domain Certainty Hardening (`src/mke_product/cas/safety.py`)
- `assess_domain_certainty(node, restrictions)`:
  - If `is_polynomial_ast(node)` and no restrictions: returns `PROVEN_REALS`.
  - If restrictions exist and all match single-point exclusions (e.g., `x != a`): returns `EXPLICIT_EXCLUSIONS`.
  - Otherwise (multivariate denominators, unverified branches, node is None): returns `NOT_FULLY_DETERMINED`.

### D. UI Notation Refinement (`ui/ui00/app.js`)
- Cleared `solutionVar` and `solutionEq` text for `SOLVE_SYSTEM` operations, allowing KaTeX to render clean assignments ($x = \frac{8}{5},\; y = \frac{3}{5}$) without redundant coordinate prefixes.

---

## 4. Counterexample & Soundness Verification Matrix

| ID | Input / Scenario | Expected Status | Actual Status | Result / Output |
|---|---|---|---|---|
| **Counterexample A** | `(x-1)/(x-1) > 0` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | Rejected (Variable denominator) |
| **Counterexample B** | `(x-1)/(x-1) >= 0` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | Rejected (Variable denominator) |
| **Counterexample C** | `(x-1)/(x-1) = 1, y = 2` | `OUT_OF_SCOPE` | `OUT_OF_SCOPE` | Rejected (Variable denominator) |
| **Counterexample D** | `2*x + 3*y = 5, x - y = 1` | `SUCCESS` | `SUCCESS` | $x = 8/5,\; y = 3/5$ (`sympy_cas_v0`) |
| **Counterexample E** | `x^2 - 4 > 0` | `SUCCESS` | `SUCCESS` | $(-\infty, -2) \cup (2, \infty)$ (`PROVEN_REALS`) |
| **Option Bypass 1** | `options={"in_process": True}` via HTTP | HTTP 400 `INVALID_INPUT` | HTTP 400 `INVALID_INPUT` | Forbidden option rejected |
| **Option Bypass 2** | `options={"sleep_seconds": 60}` via HTTP | HTTP 400 `INVALID_INPUT` | HTTP 400 `INVALID_INPUT` | Forbidden option rejected |
| **Option Bypass 3** | `options={"engine_override": "mke_native_v1"}` | HTTP 400 `INVALID_INPUT` | HTTP 400 `INVALID_INPUT` | Forbidden option rejected |

---

## 5. Verification Test Suite Results

- **Test Suite Runner:** `scripts/run_and_log_p03b_r1_tests.py`
- **Total Tests Collected & Run:** 436
- **Passed:** 436
- **Failed:** 0
- **Subtests Passed:** 18
- **Execution Time:** 108.50s
- **Exit Code:** 0
- **Log Files:**
  - `evidence/p03b_r1/p03b_r1_test_suite_raw.log`
  - `evidence/p03b_r1/p03b_r1_test_results.json`

---

## 6. Conclusion & Gate Approval

The implementation satisfies all criteria for **MKE PRODUCT-03B-R1**. Mathematical soundness is preserved across algebraic cancellations, resource isolation options cannot be manipulated by untrusted API clients, domain certainty reporting is fully truthful, and canonical UI rendering is clean and accurate.
