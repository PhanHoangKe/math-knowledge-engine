# MKE P03C-P1B-R1 Transcendental Solver & Adversarial Soundness Benchmark Report

- **Benchmark ID:** `P03C_P1B_TRANSCENDENTAL_BENCHMARK_R1`
- **Tested Source Commit:** `2dc9fdd30e7dd3099a6f8c0f724665041fb92e1d`
- **Worktree Status:** `Clean`
- **Dataset File:** `p03c_p1b_transcendental_benchmark.json`
- **Dataset Canonical LF SHA-256 (Platform Independent):** `64f5eb610843295d0f0ebdd284c7b673a65aa139243dc3fd317bde3776821750`
- **Dataset On-Disk SHA-256:** `76edfc7aa5b19323746121adcee75c4647c6a60f95f62e3ad74d61d56e8d6c4f`
- **Build Version:** `v0.3.2-p03c-p1b-r1`
- **Environment:** Python `3.10.11` on `Windows-10-10.0.26200-SP0`
- **Timestamp:** `2026-09-29T04:57:34Z`
- **Execution Duration:** `44.66s`

## Executive Summary

| Suite Category | Total Problems | Passed | Failed | Accuracy Rate |
|:---|:---:|:---:|:---:|:---:|
| **Original P1B Suite** | 32 | 32 | 0 | **100.0%** |
| **Adversarial Soundness Suite** | 15 | 15 | 0 | **100.0%** |
| **Combined P1B-R1 Benchmark** | **47** | **47** | **0** | **100.0%** |

### Stratified Item Categorization Breakdown

To ensure strict data honesty and prevent overclaiming, the 47 benchmark items are explicitly categorized into three distinct operational buckets:
1. **Mathematically Solved Answers (41/47):** Authentic high-school calculus, exponential, logarithmic, and trigonometric equations/derivatives solved to canonical symbolic truth.
2. **Proven Mathematical Domain Rejections (5/47):** Adversarial items with impossible or undefined domains (e.g. `P1B-ADV-005` to `P1B-ADV-009`) correctly rejected with `DOMAIN_ERROR` / `NOT_APPLICABLE`.
3. **Supported Out-of-Scope Soundness Rejections (1/47):** Adversarial non-elementary mixed equations (e.g. `P1B-ADV-015` $\sin(x) + \cos(x) = x$) correctly failed closed with `OUT_OF_SCOPE` / `NOT_FULLY_DETERMINED`.

## Curriculum Archetype Taxonomy Crosswalk

All benchmark items are strictly reconciled against the official GDPT 2018 curriculum taxonomy:

| Archetype ID | Official GDPT 2018 Description | Benchmark Category | Items | Passed | Accuracy |
|:---|:---|:---|:---:|:---:|:---:|
| `ARCH-11.1.1` | Biến đổi lượng giác cơ bản và công thức lượng giác (Trig Simplification) | Standard / Adversarial | 7 | 7 | **100.0%** |
| `ARCH-11.1.3` | Phương trình lượng giác cơ bản (Periodic Trigonometric Equations) | Standard / Adversarial | 7 | 7 | **100.0%** |
| `ARCH-11.4.1` | Khái niệm và tính chất logarit, biến đổi logarit (Log Evaluation) | Standard / Adversarial | 12 | 12 | **100.0%** |
| `ARCH-11.4.3` | Phương trình, bất phương trình mũ và logarit cơ bản (Exp/Log Equations & Identities) | Standard / Adversarial | 13 | 13 | **100.0%** |
| `ARCH-11.5.1` | Đạo hàm của hàm số lượng giác, mũ và logarit (Transcendental Differentiation) | Standard / Adversarial | 8 | 8 | **100.0%** |

## Longitudinal Pilot Benchmark Provenance

In the 40-problem THPT pilot diagnostic benchmark (`tests/benchmarks/thpt_pilot_benchmark_v1.json`), P1B accurately unlocked 3 genuine new problems:
- `PILOT-11-0005` (`ARCH-11.1.1`): $\sin(x + \pi/4) - \cos(x - \pi/4) = 0$ -> **PASS** (simplification to 0)
- `PILOT-11-0007` (`ARCH-11.4.1`): $\log_2(12) - \log_2(3) = 2$ -> **PASS** (exact log quotient reduction)
- `PILOT-11-0008` (`ARCH-11.4.3`): $\log_2(x-1) + \log_2(x+1) = 3 \implies S = \{3\}$ -> **PASS** (extraneous root $-3$ rejected via domain gating)

Longitudinal Pilot Progression:
- **Accepted P1A Baseline:** 13 / 40 (32.5%)
- **Initial P1B Milestone:** 16 / 40 (40.0%)
- **P03C-P1B-R1 Gate Hotfix:** **17 / 40 (42.5%)** (+10.0% net progression over accepted P1A, 0 extraneous root leaks)

## Mathematical Scope & Completeness Guarantees (Task 4)

1. **Exhaustive Real-Root Completeness Boundary:**
   - General candidate collection through SymPy `solve` does **not** itself establish exhaustive real-root completeness for general transcendental equations.
   - Formal complete-solution set claims are **strictly restricted** to justified, certified problem classes:
     - Elementary affine single-function periodic trigonometric equations: $\sin(ax+b)=m, \cos(ax+b)=m, \tan(ax+b)=m$ (with complete $k \in \mathbb{Z}$ parameterization).
     - Identity equations with certified domain extraction ($f(x)=f(x)$ over verified continuous/periodic domain subsets).
     - Quadratic, linear, and single/dual radical equations with certified extraneous root elimination.
2. **Fail-Closed Unclassified Transcendental Scope:**
   - Unsupported general exponential, logarithmic, and mixed transcendental equations (e.g. $\sin(x) + \cos(x) = x$, $\ln(x) + x = 0$, $2^x = x^2$) fail closed with `OUT_OF_SCOPE` or `UNRESOLVED` and domain certainty `NOT_FULLY_DETERMINED`.
   - The engine **never** returns partial principal roots as complete solution sets for unclassified periodic equations.

## Mathematical Soundness Demonstrations

### 1. Domain-Preserving Transcendental Identities
- `\ln(x) = \ln(x)` -> `(0, oo)` (`PROVEN_REALS`)
- `\log(x-1, 2) = \log(x-1, 2)` -> `(1, oo)` (`PROVEN_REALS`)
- `\tan(x) = \tan(x)` -> `All real numbers except pi/2 + k*pi (k integer)` (`EXPLICIT_EXCLUSIONS`)
- Injected domain failure returns `UNRESOLVED` with `NOT_FULLY_DETERMINED` (fail-closed, never false real reals).

### 2. Periodic Trigonometric Equations
- $\sin(x) = 1/2 \implies x = \pi/6 + 2k\pi \lor x = 5\pi/6 + 2k\pi \quad (k \in \mathbb{Z})$ (complete two-family representation)
- $\cos(x) = 0 \implies x = \pi/2 + k\pi \quad (k \in \mathbb{Z})$
- $\tan(x) = 1 \implies x = \pi/4 + k\pi \quad (k \in \mathbb{Z})$
- $\sin(2x - \pi/6) = 1/2 \implies x = \pi/6 + k\pi \lor x = \pi/2 + k\pi \quad (k \in \mathbb{Z})$
- $\sin(3x) = 0 \implies x = k\pi/3 \quad (k \in \mathbb{Z})$
- $\cos(2x) = 1 \implies x = k\pi \quad (k \in \mathbb{Z})$
- $\tan(2x) = 1 \implies x = \pi/8 + k\pi/2 \quad (k \in \mathbb{Z})$
- $\sin(-2x + \pi/3) = 1/2 \implies x = \pi/12 + k\pi \lor x = -\pi/4 + k\pi \quad (k \in \mathbb{Z})$ (negative coefficient handling)
- $\sin(x) = 2 \implies \emptyset$ (empty set)
- Non-elementary periodic equation $\sin(x) + \cos(x) = x \implies \text{OUT\_OF\_SCOPE}$ / `UNRESOLVED` (fail-closed).

## Remaining Limitations & Honest Boundaries

1. **Non-elementary Trigonometric Equations:** High-degree trigonometric polynomials and mixed transcendental equations without affine arguments remain explicitly `OUT_OF_SCOPE`.
2. **Logarithmic Inequalities:** Logarithmic inequalities ($\log_a(x) > b$) are scheduled for subsequent milestone P1C.
3. **Word Problems / Geometry:** Geometry and Vietnamese word problem modalities require separate multimodal/NLP frontend pipelines.

## Non-Overclaiming Disclaimer

> [!IMPORTANT]
> This benchmark measures deterministic accuracy on 47 curated Grade 11-12 curriculum problems and 40 pilot diagnostic items. It does not constitute a claim of universal mathematical completeness or performance on uncurated hidden-holdout distributions.

## Problem-by-Problem Execution Details

| ID | Archetype | Category | Input LaTeX | Engine Result | Expected | Outcome |
|:---|:---|:---|:---|:---|:---|:---:|
| `P1B-TRIG-001` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\sin(x + \pi/4) - \cos(x - \pi/4)` | `0` | `0` | **SUCCESS** |
| `P1B-TRIG-002` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\sin^2(x) + \cos^2(x)` | `1` | `1` | **SUCCESS** |
| `P1B-TRIG-003` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\sin(\pi/6) + \cos(\pi/3)` | `1` | `1` | **SUCCESS** |
| `P1B-TRIG-004` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\cos(0) + \sin(\pi/2)` | `2` | `2` | **SUCCESS** |
| `P1B-TRIG-005` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\cos(x + \pi/2) + \sin(x)` | `0` | `0` | **SUCCESS** |
| `P1B-TRIG-006` | `ARCH-11.1.1` | TRIG_SIMPLIFICATION | `\sin(\pi - x) - \sin(x)` | `0` | `0` | **SUCCESS** |
| `P1B-LOG-001` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(12, 2) - \log(3, 2)` | `2` | `2` | **SUCCESS** |
| `P1B-LOG-002` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(25, 5) + \log(4, 2)` | `4` | `4` | **SUCCESS** |
| `P1B-LOG-003` | `ARCH-11.4.1` | LOG_EVALUATION | `\ln(e^5) - \ln(e^2)` | `3` | `3` | **SUCCESS** |
| `P1B-LOG-004` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(1000, 10)` | `3` | `3` | **SUCCESS** |
| `P1B-LOG-005` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(8, 2) * \log(9, 3)` | `6` | `6` | **SUCCESS** |
| `P1B-LOG-006` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(1/16, 2)` | `-4` | `-4` | **SUCCESS** |
| `P1B-LOG-007` | `ARCH-11.4.1` | LOG_EVALUATION | `\log(81, 3) - \log(27, 3)` | `1` | `1` | **SUCCESS** |
| `P1B-LOG-008` | `ARCH-11.4.1` | LOG_EVALUATION | `\ln(e)` | `1` | `1` | **SUCCESS** |
| `P1B-DIFF-001` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\sin(2*x) + \exp(3*x)` | `3*exp(3*x) + 2*cos(2*x)` | `2*cos(2*x) + 3*exp(3*x)` | **SUCCESS** |
| `P1B-DIFF-002` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\cos(5*x)` | `-5*sin(5*x)` | `-5*sin(5*x)` | **SUCCESS** |
| `P1B-DIFF-003` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\exp(-2*x)` | `-2*exp(-2*x)` | `-2*exp(-2*x)` | **SUCCESS** |
| `P1B-DIFF-004` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\ln(x)` | `1/x` | `1/x` | **SUCCESS** |
| `P1B-DIFF-005` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\log(x, 2)` | `1/(x*log(2))` | `1/(x*log(2))` | **SUCCESS** |
| `P1B-DIFF-006` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\sin(x) + \cos(x)` | `-sin(x) + cos(x)` | `cos(x) - sin(x)` | **SUCCESS** |
| `P1B-DIFF-007` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `\tan(x)` | `tan(x)^2 + 1` | `tan(x)**2 + 1` | **SUCCESS** |
| `P1B-DIFF-008` | `ARCH-11.5.1` | TRANSCENDENTAL_DIFF | `x*\exp(x)` | `x*exp(x) + exp(x)` | `x*exp(x) + exp(x)` | **SUCCESS** |
| `P1B-EQ-001` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\log(x-1, 2) + \log(x+1, 2) = 3` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-002` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\log(x^2 - 3, 2) = \log(2*x, 2)` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-003` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\log(x-2, 3) = 2` | `{11}` | `{11}` | **SUCCESS** |
| `P1B-EQ-004` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `2^(x+1) = 8` | `{2}` | `{2}` | **SUCCESS** |
| `P1B-EQ-005` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `3^(2*x - 1) = 27` | `{2}` | `{2}` | **SUCCESS** |
| `P1B-EQ-006` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\exp(2*x) - 3*\exp(x) + 2 = 0` | `{0, log(2)}` | `{0, log(2)}` | **SUCCESS** |
| `P1B-EQ-007` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\log(x+2, 5) + \log(x-2, 5) = 1` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-008` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `4^x - 5*2^x + 4 = 0` | `{0, 2}` | `{0, 2}` | **SUCCESS** |
| `P1B-EQ-009` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\ln(2*x - 1) = 0` | `{1}` | `{1}` | **SUCCESS** |
| `P1B-EQ-010` | `ARCH-11.4.3` | EXP_LOG_EQUATION | `\log(x, 2) = 5` | `{32}` | `{32}` | **SUCCESS** |
| `P1B-ADV-001` | `ARCH-11.4.3` | DOMAIN_IDENTITY | `\ln(x) = \ln(x)` | `(0, oo)` | `(0, oo)` | **SUCCESS** |
| `P1B-ADV-002` | `ARCH-11.4.3` | DOMAIN_IDENTITY | `\log(x-1, 2) = \log(x-1, 2)` | `(1, oo)` | `(1, oo)` | **SUCCESS** |
| `P1B-ADV-003` | `ARCH-11.1.3` | DOMAIN_IDENTITY | `\tan(x) = \tan(x)` | `All real numbers except pi/2 + k*pi (k integer)` | `All real numbers except pi/2 + k*pi (k integer)` | **SUCCESS** |
| `P1B-ADV-004` | `ARCH-11.4.3` | DOMAIN_IDENTITY | `\log(x, 2) / \log(x, 2) = 1` | `(0, 1) U (1, oo)` | `(0, 1) U (1, oo)` | **SUCCESS** |
| `P1B-ADV-005` | `ARCH-11.4.1` | INVALID_DOMAIN_ARGUMENT | `\log(-4, 2)` | `None` | `DOMAIN_ERROR` | **SUCCESS** |
| `P1B-ADV-006` | `ARCH-11.4.1` | INVALID_DOMAIN_BASE | `\log(5, 1)` | `None` | `DOMAIN_ERROR` | **SUCCESS** |
| `P1B-ADV-007` | `ARCH-11.4.1` | INVALID_DOMAIN_BASE | `\log(8, -2)` | `None` | `DOMAIN_ERROR` | **SUCCESS** |
| `P1B-ADV-008` | `ARCH-11.4.1` | INVALID_DOMAIN_ARGUMENT | `\ln(0)` | `None` | `DOMAIN_ERROR` | **SUCCESS** |
| `P1B-ADV-009` | `ARCH-11.1.1` | INVALID_DOMAIN_POLE | `\tan(\pi/2)` | `None` | `DOMAIN_ERROR` | **SUCCESS** |
| `P1B-ADV-010` | `ARCH-11.1.3` | PERIODIC_TRIG_EQUATION | `\sin(x) = 1/2` | `x = pi/6 + 2*k*pi, x = 5*pi/6 + 2*k*pi (k in Z)` | `x = pi/6 + 2*k*pi, x = 5*pi/6 + 2*k*pi (k in Z)` | **SUCCESS** |
| `P1B-ADV-011` | `ARCH-11.1.3` | PERIODIC_TRIG_EQUATION | `\cos(x) = 0` | `x = pi/2 + k*pi (k in Z)` | `x = pi/2 + k*pi (k in Z)` | **SUCCESS** |
| `P1B-ADV-012` | `ARCH-11.1.3` | PERIODIC_TRIG_EQUATION | `\tan(x) = 1` | `x = pi/4 + k*pi (k in Z)` | `x = pi/4 + k*pi (k in Z)` | **SUCCESS** |
| `P1B-ADV-013` | `ARCH-11.1.3` | PERIODIC_TRIG_EQUATION | `\sin(2*x - \pi/6) = 1/2` | `x = pi/6 + k*pi, x = pi/2 + k*pi (k in Z)` | `x = pi/6 + k*pi, x = pi/2 + k*pi (k in Z)` | **SUCCESS** |
| `P1B-ADV-014` | `ARCH-11.1.3` | PERIODIC_TRIG_EQUATION | `\sin(x) = 2` | `{}` | `{}` | **SUCCESS** |
| `P1B-ADV-015` | `ARCH-11.1.3` | UNSUPPORTED_NONLINEAR | `\sin(x) + \cos(x) = x` | `None` | `OUT_OF_SCOPE` | **SUCCESS** |
