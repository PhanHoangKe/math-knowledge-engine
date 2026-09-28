# MKE PRODUCT — CANONICAL UI INTEGRATION EVIDENCE DOSSIER

## Verification & Visual Continuity Evidence (Milestone: PRODUCT-P03A-R2)

---

### 1. Verification Metadata

| Attribute | Value |
| :--- | :--- |
| **Tested Source Commit** | `f8d1682290dacef0180f000861ca0dab37de07e1` |
| **Branch** | `product/p03a-r2-original-ui-integration` |
| **Base Commit (P03A-R1)** | `1ec8d698a53699bea7b515a21b1d13b065ce5723` |
| **Audited P1 Baseline** | `12f7ad392a0eb5fc437d10039ba6a3d468c7eb80` |
| **Original UI Commit** | `d5fae73` (`feat(ui-00): align visual atmosphere with wolframalpha colors icons and typography`) |
| **Execution Timestamp** | `2026-09-28T05:01:53Z` (UTC) / `2026-09-28T12:01:53+07:00` |
| **Operating System** | Windows 11 Pro (`win32` / `x86_64`) |
| **Python Version** | Python 3.10.11 / Python 3.12.3 (CPython) |
| **Test Runner** | pytest 9.1.1, pytest-subtests 0.15.0 |
| **Test Duration** | 63.73 seconds |
| **Exit Code** | `0` (Success) |

---

### 2. Full Test Suite Console Execution

```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\mke-product-ui-r2
plugins: anyio-3.7.1, asyncio-1.4.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 369 items

tests/test_cas_http_integration.py ............                          [  3%]
tests/test_cas_product03a.py ...............................             [ 11%]
tests/test_evaluator.py ...............................................  [ 24%]
tests/test_parser.py .........................................           [ 35%]
tests/test_protocol.py ................................................. [ 48%]
.............                                                            [ 52%]
tests/test_rational.py ........................                          [ 58%]
tests/test_solver.py ................................................... [ 72%]
.....................                                                    [ 78%]
tests/test_worker_windows.py ........................................... [ 89%]
.........................................                                [100%]

============= 369 passed, 18 subtests passed in 63.73s (0:01:03) ==============
```

---

### 3. Visual Continuity & Browser Evidence Matrix

| Evidence ID | Description | File Path | Verification Outcome |
| :--- | :--- | :--- | :--- |
| **A. Before Integration (Light)** | Original UI-00 prototype before backend connection (Light). | `evidence/ui_r2/before_desktop_light.png` | Authentic Wolfram capsule search, 4-column domain cards, violet borders. |
| **B. Before Integration (Dark)** | Original UI-00 prototype before backend connection (Charcoal Dark). | `evidence/ui_r2/before_desktop_dark.png` | Warm charcoal `#262626` background, mathematical typography. |
| **C. Active Home Screen** | Live application home screen after integration. | `evidence/ui_r2/ui_home_screen.png` | Shows MKE Product v0 live connection banner, quick math keys, and responsive 4-column cards. |
| **D. Linear Solver & Steps** | Linear equation $2x + 3 = 7$ solved by `mke_native_v1`. | `evidence/ui_r2/ui_solve_linear_native.png` | Exact solution $x = 2$, canonical verified step trace rendered. |
| **E. Quadratic Solver** | Quadratic $x^2 - 5x + 6 = 0$ solved by `sympy_cas_v0`. | `evidence/ui_r2/ui_solve_quadratic.png` | Real solution set $x \in \{2, 3\}$, domain $\mathbb{R}$, timing 1.20 ms. |
| **F. Differentiation** | Derivative of $x^3 + 2x^2 - 5x + 7$ via `DIFFERENTIATE`. | `evidence/ui_r2/ui_differentiation.png` | Symbolic derivative $\frac{\mathrm{d}}{\mathrm{d}x} = 3x^2 + 4x - 5$. |
| **G. Integration** | Symbolic integral of $x^3 + 2x^2 - 5x + 7$ via `INTEGRATE`. | `evidence/ui_r2/ui_integration.png` | Exact integral $\frac{x^4}{4} + \frac{2x^3}{3} - \frac{5x^2}{2} + 7x + C$. |
| **H. 2D Cartesian Graph** | 2D SVG graph plotting $x^2 - 4$ via `PLOT_2D`. | `evidence/ui_r2/ui_plot_2d.png` | Zero-dependency SVG Cartesian axes, grid, origin $(0,0)$, coordinate ticks, and curve. |
| **I. Domain Restrictions** | Removable singularity equation $\frac{x^2 - 4}{x - 2} = 4$. | `evidence/ui_r2/ui_domain_restriction.png` | Preserves exact domain restriction $x \neq 2$. |
| **J. Charcoal Dark Theme** | Live application rendered in charcoal dark theme. | `evidence/ui_r2/ui_dark_theme.png` | High-contrast mathematical palette, theme toggle verified. |

---

### 4. SHA-256 File Integrity Manifest

| SHA-256 Checksum | File Path |
| :--- | :--- |
| `e02b1536fc8880737f344a115a8248334599623ea52fd6ddf54545a112eae507` | `src/mke_product/cas/demo_server.py` |
| `c091e48419bbedb146c9961f79c734bb1c7895f0318f7e33a85bcc0cfbf20522` | `tests/test_cas_http_integration.py` |
| `a5d95599b5c6872739fb6b6c90b66bbb231c8c0ed0390b038097662e24c7d728` | `ui/ui00/index.html` |
| `dadd5f6c5d1adc82d5a0396f912b53fc026492b709797a45947e57fd72ef9225` | `ui/ui00/styles.css` |
| `5852abfc47deaffd13245bdda0de1c88bca9fe82fc37b3e6a23513d87e0e1216` | `ui/ui00/app.js` |
| `3121744279619e8804d05c628ebbaa26e866bbd44be7b1fcca21f37df0a1a728` | `ui/ui00/DESIGN_TOKENS.md` |
| `2c133fa83d3c60dafa1fcb9a95bea00ee2c8ff76afd91ad224c057e664a48ab0` | `ui/ui00/README.md` |
| `6104a8510128c99ee5eae603cc35de2f39321d71e3bd0addca9f6938b65424ad` | `scripts/run_and_log_ui_tests.py` |
| `568d28809a6dd9ec292e477f5918c5b4d4cb72073c414f1cd7f694fed1f096d6` | `evidence/ui_r2/ui_test_results.json` |
| `13d9be87444bbecd707a2fd9b01566955b6e35488f34d4fecd27403670f24d97` | `evidence/ui_r2/ui_test_suite_raw.log` |
| `33417aca78016435fd8d845ece767d0e9f1fab23a3c8c9b167dc97d6223abf8f` | `evidence/ui_r2/before_desktop_light.png` |
| `86570ebe72bfb3d8abebc32168cc3d1988f7e3804322e614253b36b5071152a6` | `evidence/ui_r2/before_desktop_dark.png` |
| `fca95ccebc030adbb21e53e2f6003e6f9466205efc652d628a44a78848d525f5` | `evidence/ui_r2/ui_home_screen.png` |
| `42b85014b59693b5b20f10f9795bc32e82e87e0e471b96d6e4f8a3a56007adc2` | `evidence/ui_r2/ui_solve_linear_native.png` |
| `3ad96bd1ea2706124e7565e1e8ebafc9bb0007035f4a453094f215dec2f08b40` | `evidence/ui_r2/ui_solve_quadratic.png` |
| `7cbd8eddd5a9be169148568d3131a91bc4eff2e1669889a32920d7c516a25db2` | `evidence/ui_r2/ui_differentiation.png` |
| `e296df8595a92507e78218de9066e6054b0025fddd808de1e755a14ec7848864` | `evidence/ui_r2/ui_integration.png` |
| `c35af0fe98053d38c8808df6f1cf98fa802aa7e667446204e982796db43f6a5a` | `evidence/ui_r2/ui_plot_2d.png` |
| `8b4d03e703e3dacec91dfe2d007b3b4b1f179439a1490b676d7f0c2341ca9737` | `evidence/ui_r2/ui_domain_restriction.png` |
| `d41968ec3ec4498ac6e87c76f340627ea3efdc1771362182f43346d22c10805f` | `evidence/ui_r2/ui_dark_theme.png` |
| `d9fdfcb1f1c798782bb5d40cb925000570b68a6fcf7c7f7bc8d7b38d4a9ea2ff` | `PRODUCT_UI_INTEGRATION_REPORT.md` |
| `[PENDING COMMIT]` | `PRODUCT_UI_INTEGRATION_EVIDENCE.md` |

---

### 5. Final Audit Verdict

- **Automated Regression Suite:** PASS (369/369, 100%)
- **Subtests:** PASS (18/18, 100%)
- **Visual Interface Preservation:** PASS (100%)
- **Status:** **`PENDING INDEPENDENT UI INTEGRATION AUDIT`**
