# MKE PRODUCT-03C PILOT BENCHMARK FINDINGS & P1 IMPLEMENTATION GATE

**Author:** Antigravity (Implementation Engineer)  
**Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Dedicated Branch:** `product/p03c-p0-r2-benchmark-hotfix`  
**Dataset Version:** `v1.0.0-pilot` (`tests/benchmarks/thpt_pilot_benchmark_v1.json`)  
**Frozen Baseline:** `e207efcfd4d1af31e4e94202174f5d98e0bb5692` (`v0.3.0-p03b-accepted`)

---

## 1. Executive Summary & Data Honesty Audit

In accordance with the Independent Auditor's findings on R1 benchmark integrity, this document establishes full data honesty, repairs all identified mathematical errors, introduces a genuine 40-problem pilot evaluation dataset, and defines the quantitative **P03C-P1 Implementation Gate**.

### Audit Reconciliation on R1 Datasets:
1. **Preservation of Audit History:**
   - The R1 synthetic dataset has been preserved in [`tests/benchmarks/archive/thpt_diagnostic_benchmark_r1_synthetic.json`](file:///D:/mke-product-ui-r4/tests/benchmarks/archive/thpt_diagnostic_benchmark_r1_synthetic.json).
   - All 285 placeholder records in the diagnostic benchmark are explicitly tagged:
     `"item_status": "NOT_REAL_PROBLEM_SYNTHETIC_TEMPLATE"`, `"is_real_problem": false`, `"review_status": "UNVERIFIED_PLACEHOLDER"`.
   - **Zero placeholder records are presented or counted as validated mathematics problems.**
2. **Correction of Identified Radical Errors:**
   - **ARCH-10.5.1 (Item 3):** $\sqrt{3x^2 - 9x + 1} = \sqrt{x^2 - 2x - 2}$. Squaring yields $2x^2 - 7x + 3 = 0 \implies x \in \{1/2, 3\}$. The root $x = 1/2 = +0.5$ makes $x^2 - 2x - 2 = -11/4 < 0$ and is extraneous. Corrected extraneous root declaration from `-1/2` to `+1/2`.
   - **ARCH-10.5.2 (Item 1):** $\sqrt{2x^2 + 5} = x + 2$. Condition $x \ge -2$. Squaring yields $x^2 - 4x + 1 = 0 \implies x = 2 \pm \sqrt{3}$. Both satisfy $x \ge -2$. Corrected ground truth from invalid `["-1", "1"]` to `["2 - sqrt(3)", "2 + sqrt(3)"]`.
   - **ARCH-10.5.2 (Item 2):** $\sqrt{3x^2 - 4x + 1} = 2x - 1$. Condition $x \ge 1/2$. Squaring yields $x^2 = 0 \implies x = 0$. Since $0 < 1/2$, $x = 0$ is extraneous. Corrected ground truth from hallucinated `["4"]` to empty set $\mathcal{S} = \emptyset$ with `"extraneous_roots": ["0"]`.
   - **ARCH-10.5.2 (Item 3):** $\sqrt{x^2 - 3x + 2} = x - 1$. Reconciled question wording from ambiguous "Tìm số nghiệm" to "Giải phương trình" with exact solution set `["1"]`.

---

## 2. The 40-Item Pilot Benchmark (`thpt_pilot_benchmark_v1.json`)

The Pilot Benchmark contains **40 fully authored, dual-verified authentic problems** based on the official GDPT 2018 curriculum (Thông tư 32/2018/TT-BGDĐT) and the official MOET 2025/2026 exam format standard (Quyết định 764/QĐ-BGDĐT).

### A. Pilot Stratification Breakdown
| Dimension | Category | Count | Percentage |
| :--- | :--- | :---: | :---: |
| **Grade Level** | Grade 10 | 15 | 37.5% |
| | Grade 11 | 14 | 35.0% |
| | Grade 12 | 11 | 27.5% |
| **Exam Format** | Format I (MCQ 4 Choices A, B, C, D) | 11 | 27.5% |
| | Format II (Grouped True/False 4 Statements) | 3 | 7.5% |
| | Format III (Short Answer - Rational / Float) | 25 | 62.5% |
| | Format IV (Structured Multi-Step Derivation) | 1 | 2.5% |
| **Input Modality** | `SYMBOLIC_TYPED` (Executable CAS AST) | 34 | 85.0% |
| | `VIETNAMESE_WORD_PROBLEM` (Contextual NLP) | 4 | 10.0% |
| | `TABLE_OR_COORDINATE_DATA` (Text Tables) | 2 | 5.0% |
| **Dataset Split** | `DEV` (Engineering iteration) | 27 | 67.5% |
| | `VAL` (Candidate release qualification) | 13 | 32.5% |

### B. Dual-Verification Provenance
Every single problem in the pilot dataset includes:
1. Step-by-step mathematical derivation in `rubric_steps`.
2. Exact independent proof notes (`independent_proof_notes`) cross-checked with SymPy and manual analytical calculation.
3. Official curriculum and textbook provenance (`source_reference`).

---

## 3. Pilot Execution Results Against Frozen Product 03B

Executed via [`scripts/run_thpt_pilot_benchmark.py`](file:///D:/mke-product-ui-r4/scripts/run_thpt_pilot_benchmark.py) against the frozen engine:

```
================================================================================
           MKE THPT 40-PROBLEM PILOT BENCHMARK BASELINE RUNNER
================================================================================
Total Authentic Pilot Items:           40
Attempted Symbolic Expressions:        34 (85.0%)
Unsupported Modality (NLP/Data):        6 (15.0%)
Mathematical Successes:                 6
Genuine Wrong Answers:                  5
Extraneous Root Leaks:                  0
Unsupported Grammar / Out of Scope:     0
Domain Rejected / Safety Blocked:      23
Engine Timeouts:                        0

-> Full 40-Item Pilot Accuracy:        15.00% (6 / 40)
-> Attempted Symbolic Subset Accuracy: 17.65% (6 / 34)
================================================================================
```

### Breakdown of Current Capabilities & Failures:
1. **Successful Solves (6 items / 17.65%):**
   - Linear inequalities & quadratic inequalities (`PILOT-10-0001`, `PILOT-10-0002`, `PILOT-10-0003`).
   - $2 \times 2$ linear system of equations (`PILOT-10-0010`).
   - Polynomial derivative differentiation (`PILOT-11-0001`).
   - Indefinite polynomial integration (`PILOT-12-0004`).
2. **Domain-Blocked / Pre-Dispatch Rejections (23 items):**
   - Radical expressions ($\sqrt{2x^2-3}$, $\sqrt{x-1}$) are currently blocked by `inspect_ast_safety()` or `extract_domain_restrictions()` due to non-polynomial square root operations.
   - Trigonometric, logarithmic, and vector AST expressions are rejected by pre-dispatch safety rules.
3. **Genuine Wrong Answers (5 items):**
   - Composite operations where the engine returned an incomplete or alternate representation (e.g. definite integration limit format).
4. **Unsupported Modalities (6 items):**
   - Correctly pre-filtered without calling CAS router, preventing spurious parser crashes.

---

## 4. Extraneous Root Telemetry & Honest Reporting

- **Problems Testing Extraneous Roots:** Exactly 3 items in the pilot suite (`PILOT-10-0006`, `PILOT-10-0007`, `PILOT-11-0008`) explicitly test whether the solver rejects candidate roots ($x = 1/2$, $x = 0$, $x = -3$).
- **Telemetry Result:** 0 extraneous roots leaked because these radical/logarithmic expressions were safely rejected at the domain gate rather than admitting invalid roots.
- **Scoring Invariant:** Extraneous root tests are explicitly reported as **3 candidates tested / 0 leaked**, rather than an unverified global claim.

---

## 5. Benchmark Expansion & Partition Architecture

```
MKE THPT Evaluation Architecture
├── PILOT BENCHMARK (40 Items) [Current Baseline - 100% Authentic]
│   ├── DEV Split (27 items) -> Public to implementation engineer
│   └── VAL Split (13 items) -> Release candidate qualification
│
├── DIAGNOSTIC EXPANSION (300 Items) [P03C Gate]
│   ├── 100 Archetypes x 3 Authentic Items
│   └── 100% replacement of synthetic templates with dual-verified problems
│
└── FULL-SCALE BENCHMARK (1,000+ Items) [P03E Release Gate]
    ├── Public DEV (500 items)
    ├── Parameter VAL (250 items)
    └── Sealed HOLDOUT (250 items) [Encrypted / Independent Auditor Only]
```

### Anti-Contamination Protocol:
- Jaccard token similarity check is enforced across splits ($\text{Sim} < 0.80$).
- Future hidden `HOLDOUT` datasets will remain in an external repository or encrypted directory inaccessible to the implementation agent during solver development.

---

## 6. Proposed P03C-P1 Implementation Gate

Before opening Milestone P03C solver implementation, the following criteria must be met:

| Gate Dimension | Requirement | Status |
| :--- | :--- | :---: |
| **1. Ground Truth Integrity** | 100% of pilot items have independent mathematical derivation notes and 0 unverified placeholders. | **PASS (40/40)** |
| **2. Scorer Unit Testing** | `tests/test_benchmark_scoring.py` passes all unit tests for exact set matching, extraneous root leak detection, and error taxonomy. | **PASS (9/9 passed)** |
| **3. Dispatch Accuracy** | Calculus/derivative problems dispatch to `DIFFERENTIATE`, integrals to `INTEGRATE`, equations to `SOLVE`. | **PASS** |
| **4. Regression Integrity** | Full Product 03B regression suite passes with 0 failures. | **PASS (479 passed)** |
| **5. Working Tree Cleanliness** | Dedicated branch `product/p03c-p0-r2-benchmark-hotfix` pushed to origin. | **READY** |

### P03C-P1 Work Package Priorities:
1. **AST & Grammar Extension:** Support radical nodes `AST_RADICAL` ($\sqrt{A}$), rational denominators $P(x)/Q(x)$ with guard conditions $Q(x) \ne 0$, and absolute value $|A|$.
2. **Extraneous Root Elimination Engine:** Implement domain-guarded squaring transformations $\sqrt{f(x)} = g(x) \iff g(x) \ge 0 \land f(x) = g(x)^2$.
3. **Pilot Score Target:** Advance pilot benchmark accuracy from **15.0% (6/40)** to $\ge \mathbf{50.0\% (20/40)}$ in P03C-P1.
