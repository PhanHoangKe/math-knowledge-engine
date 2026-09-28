# MKE PRODUCT-03C-P1A-R1: Mathematical Soundness and Benchmark Closure Record

## 1. Overview & Mandate
- **Mandate:** `MKE PRODUCT-03C-P1A-R1 — MATHEMATICAL SOUNDNESS AND BENCHMARK CLOSURE`
- **Branch:** `product/p03c-p1a-r1-soundness`
- **Baseline Source Commit:** `7cf0246a26ec825466a4415bd94dcf04d4df6830`
- **Baseline Evidence Commit:** `7baec0059992c29104022e6d1e8b1b24e1480fc8`
- **Role:** Antigravity — Implementation Engineer
- **Project Owner:** Kế Phan Hoàng
- **Independent Auditor:** ChatGPT

---

## 2. Remediation Summary & Mathematical Soundness

### Task 1: Exact Symbolic Root Validation
- **Problem:** `_validate_root_in_ast()` previously used floating-point epsilon comparison `abs(float(diff.evalf())) > 1e-9`. When presented with counterexample `sqrt(x^2) = x - 1/1000000000000`, algebraic squaring produced candidate root $x = 1/2000000000000$. The difference evaluated to $10^{-12} < 10^{-9}$, allowing this false candidate to leak into the solution set as a valid root.
- **Fix:** Removed all floating-point epsilon checks in `_validate_root_in_ast()`. Implemented exact symbolic equality verification using `diff = sympy.simplify(lhs_val - rhs_val)`. If `diff == 0` or `diff.is_zero is True`, the candidate is accepted. If `diff.is_zero is False` or `diff.is_number and diff != 0`, it is rejected as an extraneous candidate. If equality/inequality is undecidable, it fails closed with `False, "undecidable_equality"`.
- **Validation:** Tested counterexample `sqrt(x^2) = x - 1/1000000000000` -> Result: `{}` ($\emptyset$), candidate $x = 1/2000000000000$ recorded in `extraneous_roots`. Positive controls confirmed for valid roots.

### Task 2: Domain-Preserving Identities
- **Problem:** When solving identity equations ($LHS - RHS \equiv 0$), `_execute_solve()` previously assumed all domain restrictions were isolated point exclusions ($x \neq a$), outputting incorrect text such as `"All real numbers except x >= 0"` for `sqrt(x) = sqrt(x)`.
- **Fix:** Restructured identity equation handling to compute the exact real domain:
  - Radicands $R(x)$ intersect domain with `sympy.solveset(R >= 0, x, domain=sympy.S.Reals)`.
  - Rational denominators $D(x)$ exclude zeros `domain - sympy.solveset(Eq(D, 0), x, domain=sympy.S.Reals)`.
  - Zero-exponent bases $B(x)^0$ exclude zeros `domain - sympy.solveset(Eq(B, 0), x, domain=sympy.S.Reals)`.
  - Non-trivial interval domains are formatted using `format_interval_symbolic()` and `format_interval_latex()`.
- **Validation:** `sqrt(x) = sqrt(x)` -> `[0, oo)` / $\left[0, \infty\right)$. `sqrt(x - 2)/(x - 5) = sqrt(x - 2)/(x - 5)` -> `[2, 5) U (5, oo)`.

### Task 3: Benchmark Metadata & Telemetry Reconciliation
- **Problem:** `tests/benchmarks/p03c_p1a_algebra_benchmark.json` contained invalid archetype ID `ARCH-10.3.4` not present in `docs/curriculum/GDPT2018_THPT_MATH_TAXONOMY.md`. Item `P1A-ALG-015` (`sqrt(x^2 - 3*x + 2) = x - 1`) declared $x = 2$ as an extraneous root, whereas algebraic squaring produces only candidate $x = 1$.
- **Fix:**
  - Reconciled all archetype IDs with official Topic 10.5 taxonomy: `ARCH-10.5.1` (Dual radical), `ARCH-10.5.2` (Single radical), `ARCH-10.5.3` (Absolute value).
  - Corrected `P1A-ALG-015` ground truth: `solution_set: ["1"]`, `extraneous_roots: []`.

### Task 4: Scoring Engine Hardening
- **Fix:** Enhanced `scripts/benchmark_scoring.py`:
  - Added exact symbolic mathematical equivalence `is_mathematically_equivalent()` supporting radical simplifications ($2\sqrt{3} \equiv \sqrt{12}$) and algebraic identities.
  - Added robust multi-variable linear system parsing and equivalence `are_systems_equivalent()`.
  - Added empty-set MCQ evaluation and separate tracking of `choice_matched` vs `math_matched`.
  - Added mutation unit test suite in `tests/test_benchmark_scoring.py` with deliberately corrupted responses (wrong signs, partial subsets, supersets with bogus roots, inequivalent radicals, empty vs zero) verifying zero false positives.

---

## 3. Benchmark Execution Results

### A. P03C-P1A Elementary Algebra Benchmark (15 Items)
- **Total Items:** 15
- **Passed Items:** 15 / 15 (100.0%)
- **Extraneous Root Leaks:** 0
- **Evidence File:** `evidence/benchmark/p03c_p1a_algebra_benchmark_results.json`

### B. THPT 40-Problem Pilot Diagnostic Benchmark
- **Total Items:** 40
- **Attempted Symbolic Subset:** 34 / 40 (85.0%)
- **Unsupported Modality:** 6 / 40 (15.0%)
- **Mathematical Successes:** 12
- **Genuine Wrong Answers:** 5
- **Domain Rejected / Safety Blocked:** 17
- **Extraneous Root Leaks:** 0
- **Overall Accuracy:** 30.00% (12/40)
- **Attempted Subset Accuracy:** 35.29% (12/34)
- **Evidence File:** `evidence/benchmark/thpt_pilot_benchmark_results.json`

---

## 4. Test Suite Summary
- **Targeted Unit & Mutation Tests:** 33 passed in 1.88s (`tests/test_p03c_p1a_algebra_solver.py`, `tests/test_benchmark_scoring.py`).
- **Windows Worker Isolation Suite:** 80 passed in 39.83s (`tests/test_worker_windows.py`).
- **Full Pytest Suite:** 526 passed.
