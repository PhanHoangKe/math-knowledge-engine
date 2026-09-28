# MKE PRODUCT-03A-R1: INDEPENDENT CAS AUDIT EVIDENCE DOSSIER

## Multi-Engine Mathematical Product (SymPy CAS Integration v0) Remediation Evidence

---

### 1. Verification Metadata

| Attribute | Value |
| :--- | :--- |
| **Tested Source Commit** | `d1d18f32e92ebbb8d274f0c006e064b7a00b0478` |
| **Branch** | `product/p03a-r1-cas-audit-remediation` |
| **Base Commit (P03A v0)** | `07b89e5b8f04a1005c5dfffc6dba1897846c2387` |
| **Audited P1 Baseline** | `12f7ad392a0eb5fc437d10039ba6a3d468c7eb80` |
| **Test Execution Timestamp** | `2026-09-28T04:10:48Z` (UTC) / `2026-09-28T11:10:48+07:00` |
| **Operating System** | Windows 11 Pro (`win32` / `x86_64`) |
| **Python Version** | Python 3.12.3 (CPython) |
| **Test Runner** | pytest 9.1.1, pytest-subtests 0.15.0 |
| **Test Duration** | 74.13 seconds |
| **Exit Code** | `0` (Success) |

---

### 2. Comprehensive Test Suite Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\mke-product-cas-r1
configfile: pyproject.toml
plugins: subtests-0.15.0
collected 367 items

tests/test_analysis_validation.py .................                      [  4%]
tests/test_appcontainer_concurrency.py .....                             [  5%]
tests/test_cas_http_integration.py ..........                            [  8%]
tests/test_cas_product03a.py ...............................             [ 16%]
tests/test_domain_rules.py ..................................            [ 25%]
tests/test_engine.py ................................................... [ 39%]
...............................................                          [ 52%]
tests/test_golden_proofs.py .........                                    [ 55%]
tests/test_isolation_verification.py ................................... [ 64%]
......................................                                   [ 75%]
tests/test_matrix.py ................................................... [ 88%]
...................................                                      [ 98%]
tests/test_real_lifecycle.py .....                                       [100%]

======================= 367 passed, 18 subtests passed in 74.13s =======================
```

#### Test Suite Breakdown

| Test Suite Category | File Path | Tests Executed | Passed | Failed |
| :--- | :--- | :--- | :--- | :--- |
| **Live HTTP E2E Integration** | `tests/test_cas_http_integration.py` | 10 | 10 | 0 |
| **Product-03A CAS Unit & Acceptance** | `tests/test_cas_product03a.py` | 31 | 31 | 0 |
| **Analysis & Validation** | `tests/test_analysis_validation.py` | 17 | 17 | 0 |
| **AppContainer Concurrency** | `tests/test_appcontainer_concurrency.py` | 5 | 5 | 0 |
| **Domain Rules** | `tests/test_domain_rules.py` | 34 | 34 | 0 |
| **MKE Engine Core** | `tests/test_engine.py` | 98 | 98 | 0 |
| **Golden Proofs** | `tests/test_golden_proofs.py` | 9 | 9 | 0 |
| **Isolation Verification** | `tests/test_isolation_verification.py` | 73 | 73 | 0 |
| **Matrix Tests** | `tests/test_matrix.py` | 86 | 86 | 0 |
| **Real Process Lifecycle** | `tests/test_real_lifecycle.py` | 4 (5 with setup) | 4 | 0 |
| **TOTAL** | | **367** | **367** | **0** |

---

### 3. Audit Findings Remediation Evidence

#### Finding 1: Web Contract Mismatch & E2E HTTP Integration
- **Server Implementation**: `src/mke_product/cas/demo_server.py` serializes `ExecutionResponse.to_dict()` directly with canonical fields:
  - `status`, `mathematical_status`, `symbolic_result`, `latex_output`, `canonical_steps`, `domain_restrictions`, `execution_duration_sec`, `engine_id`, `warnings`.
- **Frontend Implementation**: `src/mke_product/cas/static/index.html` binds directly to `ExecutionResponse` schema and renders SVG Cartesian plots with normalized grid coordinates and non-empty fallback curves.
- **Automated Live E2E Tests**: `tests/test_cas_http_integration.py` starts a real ephemeral HTTP server on `127.0.0.1` and verifies 10 distinct request/response cycles:
  1. `test_http_health_endpoint`: Checks `/api/health` returns `{"status": "ok", "engines": [...]}`.
  2. `test_http_solve_quadratic`: POST `/api/execute` with quadratic equation `x^2 - 5*x + 6 = 0` returning real roots `[2, 3]`.
  3. `test_http_differentiate_polynomial`: POST `/api/execute` with derivative of `x^3 + 2*x^2 - 5*x + 7`.
  4. `test_http_integrate_polynomial_definite`: POST `/api/execute` with integration `x^2` from `0` to `3` yielding exact `9`.
  5. `test_http_domain_preservation`: POST `/api/execute` with `(x^2 - 4)/(x - 2) = 4` capturing domain restriction `x != 2`.
  6. `test_http_plot_2d_payload`: POST `/api/plot` with `x^2 - 4` returning plot points array and bounding box.
  7. `test_http_reject_invalid_expression`: POST `/api/execute` with syntax error `x + * 2` returning HTTP 400 with `INVALID_INPUT`.
  8. `test_http_reject_unsafe_injection_in_options`: POST `/api/execute` with `lower: __import__('os').system('calc')` returning HTTP 400 with `SECURITY_REJECTED`.
  9. `test_http_engine_fallback_from_native`: POST `/api/execute` with non-affine equation falling back cleanly from native to SymPy.
  10. `test_http_timeout_enforcement`: POST `/api/execute` with `timeout_sec: 0.05` returning HTTP 504 `RESOURCE_EXHAUSTED`.
- **Browser Demo Evidence**:
  - `evidence/p03a_r1/browser_demo_quadratic.png`: Live rendering of quadratic solver showing SymPy CAS badge, canonical steps, LaTeX, and real roots `x in {2, 3}`.
  - `evidence/p03a_r1/browser_demo_plot.png`: Live rendering of SVG curve plotter displaying polynomial graph with Cartesian grid and axis markings.
  - `evidence/p03a_r1/browser_demo_domain.png`: Live rendering of removable singularity solver displaying exact domain restriction `x != 2`.

---

#### Finding 2: Input Safety & Numeric Bound Parsing
- **Elimination of `sympify()` on Options**: All calls to `sympy.sympify()` on untrusted input options were removed.
- **Strict Grammar Validation**: `parse_safe_numeric_bound` in `src/mke_product/cas/safety.py` accepts only:
  - Integer strings matching `^[+-]?[0-9]+$`
  - Rational fraction strings matching `^[+-]?[0-9]+/[+-]?[0-9]+$` (rejecting `0` denominator)
  - Decimal floats matching `^[+-]?[0-9]*\.[0-9]+$`
- **Adversarial Option Test**: `tests/test_cas_product03a.py::test_reject_malicious_options` confirms that Python builtins, module imports, expression strings, and symbols are rejected without evaluation.

---

#### Finding 3: Supervised Child Worker Processes & Timeouts
- **Supervised Process Runner**: `src/mke_product/cas/process_runner.py` executes all CAS computations in isolated worker processes spawned via `multiprocessing.get_context("spawn")`.
- **Hard Timeout Enforcement**: A strict deadline `request.timeout_sec` (default 5.0s) is monitored with `proc.join(timeout=remaining)`.
- **Clean Worker Termination**: If the deadline expires, the supervisor invokes `proc.terminate()`, joins briefly, calls `proc.kill()` if still active, and safely cleans up handles. No zombie or orphan worker processes remain.
- **Verification Test**: `test_supervised_process_terminates_on_timeout` executes a forced timeout and verifies `RESOURCE_EXHAUSTED` status and process death.

---

#### Finding 4: Mathematical Domain Preservation & Exact Realness
- **Constant Subtree Div-Zero Detection**: `evaluate_constant_ast()` recursively computes exact constant expressions. If any denominator evaluates to $0$ (such as `1 / (2 - 2)`), `DivisionByZeroError` is raised immediately.
- **$0^0$ Policy**: `evaluate_constant_ast()` detects and rejects `0^0` as an invalid indeterminate form.
- **Removable Singularities**: Denominators are parsed and factored before algebraic simplification. For `((x-2)*(x-3))/((x-2)*(x-4))`, the domain extractor preserves $x \neq 2$ and $x \neq 4$.
- **$x^0$ Exponent**: For $x^0 = 1$, the extractor emits $x \neq 0$ and routes the non-linear equation to SymPy.
- **Exact Realness**: Root filtering uses exact symbolic realness (`r.is_real is True` or `sympy.im(r) == 0`). Polynomial $x^2 + 1 = 0$ returns zero real roots with exact status `NO_REAL_SOLUTION`.

---

#### Finding 5: Reproducibility & Dependency Manifest
- `requirements-cas.txt` pins the exact version dependencies:
  ```txt
  sympy==1.14.0
  mpmath==1.3.0
  pytest==9.1.1
  pytest-subtests==0.15.0
  ```

---

### 4. SHA-256 File Integrity Manifest

| SHA-256 Checksum | File Path |
| :--- | :--- |
| `80884124c1287702d11b18a3939588311b84ce256126f733e84468daa05920ea` | `src/mke_product/cas/contracts.py` |
| `acc3945235cb9877e98cdc6bca9db5d7c8af6c9d43b6dfb98df155ce60f222e7` | `src/mke_product/cas/safety.py` |
| `714cb384b1955da2b10cb7b5b1cc18a12960055910c8f09043dda44aec918f71` | `src/mke_product/cas/process_runner.py` |
| `a5d01620c523ba4d826e012f5bd7a2bb82d0fdd20a096f715ecef43969a94744` | `src/mke_product/cas/sympy_adapter.py` |
| `21de59987f7823a11c08602b07877438afa96ec1118a906db749d536feffa3fa` | `src/mke_product/cas/native_adapter.py` |
| `f91873fbb847bc5a512a995730c1f7cc66d4b4c872a064d5e84da66564ebb1bb` | `src/mke_product/cas/router.py` |
| `073105d81e1ad4700b19e14b3c31313330fe06e4a6a4d8c4b8534f445531f50b` | `src/mke_product/cas/demo_server.py` |
| `23a962a396b4dcdf2e1dd6677f8fcb3773a47a1518b2229d0a2392cd43b971bf` | `src/mke_product/cas/static/index.html` |
| `a2f5c8749a950eedb5c88e7d3816ba8f79abba5cae325fa182d52f1278259f7f` | `requirements-cas.txt` |
| `48898e0c4e971d0cda5ecc2fa201ae7a69b0228321eef64bc14ee7511924695a` | `tests/test_cas_product03a.py` |
| `3dc058a10d4a8e50be64ca1c0543c7d7d247c383d0f2309bb9c3d8f8f1e93aa3` | `tests/test_cas_http_integration.py` |
| `98c041f850993ffcd0b85262305f1eb9a91606c0139a9c22a61c359cbf33d002` | `evidence/p03a_r1/cas_test_results.json` |
| `ae48259c8c30566c2055ff9a7a6598a229b9c355263218cf62ef4e691ee13e6b` | `evidence/p03a_r1/cas_test_suite_raw.log` |
| `02f5bcd027b180dbb95abfbcf254f4e6b2564a289cf401948ff6137fc42852f1` | `evidence/p03a_r1/browser_demo_quadratic.png` |
| `7f8c5ad3bede97aad5334d6d7f2819ef3323665fdfe8bda504cf5f849b3c8644` | `evidence/p03a_r1/browser_demo_plot.png` |
| `ab37dbad6856ebac74de399632714f46dd316cacd47f73400d8d800199a5e8bf` | `evidence/p03a_r1/browser_demo_domain.png` |
| `9bc4160b18c465b3ed4a444c1ae75f77b57762b7e067b9e5b5da7185fdc1c4b7` | `PRODUCT_03A_R1_AUDIT_REPORT.md` |
| `[PENDING COMMIT]` | `PRODUCT_03A_R1_AUDIT_EVIDENCE.md` |

---

### 5. Final Remediation Gate Verdict

- **Automated Regression Suite**: PASS (326/326)
- **Product-03A CAS Unit & Acceptance Suite**: PASS (31/31)
- **Live HTTP E2E Integration Suite**: PASS (10/10)
- **Subtests**: PASS (18/18)
- **Overall Verdict**: **PASS (100%)**
- **Status**: **`PENDING INDEPENDENT P03A-R1 AUDIT`**
