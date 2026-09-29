# MKE PRODUCT-03C-P1B ACCEPTED LIMITED RELEASE RECORD

- **Release Name:** MKE Product 03C-P1B (Transcendental Solver & Completeness Certification Release)
- **Release Tag:** `v0.3.2-p03c-p1b-accepted-limited`
- **Stable Branch:** `product/stable-p03c-p1b`
- **Owner Acceptance Decision:** `P1B ACCEPTED LIMITED — APPROVED`
- **Owner:** Kế Phan Hoàng
- **Independent Auditor:** ChatGPT
- **Implementation Engineer:** Antigravity
- **Date:** 2026-09-29

---

## 1. Commit Ancestry & Canonical Identifiers

| Object | Git Reference / SHA | Description |
| :--- | :--- | :--- |
| **Accepted Limited Source** | `f5e3a360a70fa99c7f76bd55500e83a8232495b8` | Pure CAS source code & unit test modifications. |
| **Accepted Release Evidence** | `73c54f7d22fad87dc8c323c7281a18636a1d8908` | Release benchmark artifacts, execution manifests, and raw process logs. |
| **Parent Relationship** | `73c54f7d22fad87dc8c323c7281a18636a1d8908` $\to$ `f5e3a360a70fa99c7f76bd55500e83a8232495b8` | Direct single-commit evidence child on top of source. |
| **Stable Branch Ref** | `product/stable-p03c-p1b` | Pinned directly to `73c54f7d22fad87dc8c323c7281a18636a1d8908`. |
| **Annotated Tag Ref** | `v0.3.2-p03c-p1b-accepted-limited` | Pinned directly to `73c54f7d22fad87dc8c323c7281a18636a1d8908`. |

---

## 2. Test & Verification Summary

All verification suites were executed from a verified clean worktree (`git status --porcelain` empty at `f5e3a36`) on Python `3.10.11` (Windows 10/11 x64):

1. **Full Repository Pytest Suite:** **577 / 577 PASSED** (100.0%, duration 185.7s, log: `evidence/benchmark/raw_logs/04_full_repository_pytest.log`).
2. **Targeted Transcendental Solver Suite:** **44 / 44 PASSED** (100.0%, duration 46.2s, log: `evidence/benchmark/raw_logs/01_targeted_p1b_regression.log`).
3. **Windows Confinement & Worker Isolation:** **80 / 80 PASSED** (100.0%, duration 37.8s, log: `evidence/benchmark/raw_logs/02_windows_containment.log`).
4. **Canonical Browser UI Suite:** **21 / 21 PASSED** (100.0%, duration 44.3s, log: `evidence/benchmark/raw_logs/03_browser_ui_regression.log`).
5. **Dedicated P1B Transcendental Benchmark:** **47 / 47 PASSED** (100.0%, duration 48.0s, log: `evidence/benchmark/raw_logs/05_p1b_benchmark_runner.log`).
6. **Longitudinal THPT Pilot Benchmark:** **17 / 40 SOLVED** (42.5%, duration 26.5s, 0 extraneous root leaks, log: `evidence/benchmark/raw_logs/06_thpt_pilot_benchmark_runner.log`).

---

## 3. Dedicated P1B Benchmark Item Categorization

To maintain strict scientific honesty and prevent overclaiming, the 47 benchmark items are explicitly categorized into three distinct operational buckets:

- **1. Mathematically Solved Answers (41/47):**
  - Elementary Trigonometric Simplifications (`ARCH-11.1.1`): 6 items (`P1B-TRIG-001` to `006`).
  - Exact Logarithmic Reductions & Properties (`ARCH-11.4.1`): 8 items (`P1B-LOG-001` to `008`).
  - Transcendental Differentiation (`ARCH-11.5.1`): 8 items (`P1B-DIFF-001` to `008`).
  - Logarithmic & Exponential Equations (`ARCH-11.4.3`): 10 items (`P1B-EQ-001` to `010`).
  - Domain-Preserving Transcendental Identities (`ARCH-11.4.3`, `ARCH-11.1.3`): 4 items (`P1B-ADV-001` to `004`).
  - Elementary Periodic Trigonometric Equations (`ARCH-11.1.3`): 5 items (`P1B-ADV-010` to `014`).
- **2. Proven Mathematical Domain Rejections (5/47):**
  - Undefined/negative log argument: `P1B-ADV-005` ($\log_2(-4)$), `P1B-ADV-008` ($\ln(0)$).
  - Invalid log base: `P1B-ADV-006` ($\log_1(5)$), `P1B-ADV-007` ($\log_{-2}(8)$).
  - Trigonometric pole: `P1B-ADV-009` ($\tan(\pi/2)$).
  - All return `DOMAIN_ERROR` with verified `NOT_APPLICABLE` certainty.
- **3. Supported Out-of-Scope Soundness Rejections (1/47):**
  - Non-elementary mixed equation: `P1B-ADV-015` ($\sin(x) + \cos(x) = x$) $\to$ fails closed with `OUT_OF_SCOPE` and `NOT_FULLY_DETERMINED`.

---

## 4. Longitudinal THPT Pilot Benchmark Comparison

In the 40-problem authentic Vietnamese National High School Exam pilot dataset (`tests/benchmarks/thpt_pilot_benchmark_v1.json`), P1B unlocked 4 genuine problems over the accepted P1A baseline without introducing a single extraneous root leak:

- **Accepted P1A Baseline:** 13 / 40 (32.5%)
- **P03C-P1B Release:** **17 / 40 (42.5%)** (+10.0% net progression)
- **The 4 Newly Unlocked Items:**
  1. `PILOT-11-0005` (`ARCH-11.1.1`): $\sin(x + \pi/4) - \cos(x - \pi/4) = 0$ $\to$ **PASS** (trigonometric simplification to 0).
  2. `PILOT-11-0006` (`ARCH-11.1.3`): $\sin(x) = 1/2 \implies x = \pi/6 + 2k\pi \lor x = 5\pi/6 + 2k\pi$ $\to$ **PASS** (elementary periodic trig families).
  3. `PILOT-11-0007` (`ARCH-11.4.1`): $\log_2(12) - \log_2(3) = 2$ $\to$ **PASS** (exact log quotient reduction).
  4. `PILOT-11-0008` (`ARCH-11.4.3`): $\log_2(x-1) + \log_2(x+1) = 3 \implies S = \{3\}$ $\to$ **PASS** (extraneous root $-3$ rejected via domain gating).

---

## 5. Explicit Limitations & Boundaries

1. **Pure Exponential Equality Restriction:**
   Exponential equality certification ($b^{f(x)} = b^{g(x)}$) is strictly restricted to expressions where both entire sides are isolated pure exponential terms. Additive or mixed exponential equations (e.g. $2^x + 1 = 2^{x+1}$) route to the substitution pipeline $u = b_0^x$.
2. **Polynomial Multiplicity Certification:**
   Polynomial certification compares deduplicated mathematical sets of distinct roots against Sturm real-root isolation. Incomplete candidate subsets remain strictly rejected.
3. **Fail-Closed Completeness Gate:**
   SymPy candidate generation is not treated as a completeness proof. Unsupported or mixed transcendental equations (e.g. $2^x + 3^x = 7$, $\ln(x) + x = 0$, $2^x = x^2$) fail closed with `OUT_OF_SCOPE` or `UNRESOLVED` and domain certainty `NOT_FULLY_DETERMINED`.
4. **Benchmark Generalization:**
   The 47-item benchmark and 40-item THPT pilot measure deterministic capability against curated Grade 11-12 curriculum archetypes. They do not constitute a claim of universal mathematical completeness on arbitrary mathematical expressions.
5. **Git Clean-State & Extraneous-Root Telemetry Scope:**
   Clean-state guarantees apply to the isolated source commit `f5e3a360a70fa99c7f76bd55500e83a8232495b8`. Extraneous root telemetry specifically evaluates tested candidate sets against exact domain restrictions.
6. **Unsupported Modalities:**
   Vietnamese word problems, geometric figure reasoning, and non-symbolic question formats remain out of scope for the pure CAS engine and are delegated to the upcoming P1C AI intake pipeline.
7. **Research Freeze:**
   Research G4 remains frozen and unexecuted.

---

## 6. Predecessor Release Immutability Confirmation

All predecessor releases remain untouched and verified:
- `v0.3.0-p03b-accepted`: `e207efcfd4d1af31e4e94202174f5d98e0bb5692`
- `v0.3.1-p03c-p1a-accepted-limited`: `1c2b0907b94986d8bda97008ab84492b019d0e4d`
- `product/stable-p03c-p1a`: `1c2b0907b94986d8bda97008ab84492b019d0e4d`
- No merge into `main` was performed.
