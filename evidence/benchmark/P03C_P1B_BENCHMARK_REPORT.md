# MKE P03C-P1B Transcendental Solver Benchmark Report

- **Benchmark ID:** `P03C_P1B_TRANSCENDENTAL_BENCHMARK`
- **Timestamp:** 2026-09-28T16:18:58Z
- **Total Problems:** 32
- **Passed:** 32 (100.0%)
- **Failed:** 0
- **Duration:** 28.20s

## Summary by Archetype

| Archetype ID | Category | Total | Passed | Accuracy |
|:---|:---|:---:|:---:|:---:|
| `ARCH-11.1-TRIG-SIMP` | 11.1 | 6 | 6 | 100.0% |
| `ARCH-11.2-LOG-EVAL` | 11.2 | 8 | 8 | 100.0% |
| `ARCH-11.3-EXP-EQ` | 11.3 | 4 | 4 | 100.0% |
| `ARCH-11.3-LOG-EQ` | 11.3 | 6 | 6 | 100.0% |
| `ARCH-11.5-DIFF-TRANSCENDENTAL` | 11.5 | 8 | 8 | 100.0% |

## Problem Execution Details

| ID | Archetype | Operation | Input LaTeX | Engine Result | Expected | Outcome |
|:---|:---|:---|:---|:---|:---|:---|
| `P1B-TRIG-001` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\sin(x + \pi/4) - \cos(x - \pi/4)` | `0` | `0` | **SUCCESS** |
| `P1B-TRIG-002` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\sin^2(x) + \cos^2(x)` | `1` | `1` | **SUCCESS** |
| `P1B-TRIG-003` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\sin(\pi/6) + \cos(\pi/3)` | `1` | `1` | **SUCCESS** |
| `P1B-TRIG-004` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\cos(0) + \sin(\pi/2)` | `2` | `2` | **SUCCESS** |
| `P1B-TRIG-005` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\cos(x + \pi/2) + \sin(x)` | `0` | `0` | **SUCCESS** |
| `P1B-TRIG-006` | `ARCH-11.1-TRIG-SIMP` | `SIMPLIFY` | `\sin(\pi - x) - \sin(x)` | `0` | `0` | **SUCCESS** |
| `P1B-LOG-001` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(12, 2) - \log(3, 2)` | `2` | `2` | **SUCCESS** |
| `P1B-LOG-002` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(25, 5) + \log(4, 2)` | `4` | `4` | **SUCCESS** |
| `P1B-LOG-003` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\ln(e^5) - \ln(e^2)` | `3` | `3` | **SUCCESS** |
| `P1B-LOG-004` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(1000, 10)` | `3` | `3` | **SUCCESS** |
| `P1B-LOG-005` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(8, 2) * \log(9, 3)` | `6` | `6` | **SUCCESS** |
| `P1B-LOG-006` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(1/16, 2)` | `-4` | `-4` | **SUCCESS** |
| `P1B-LOG-007` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\log(81, 3) - \log(27, 3)` | `1` | `1` | **SUCCESS** |
| `P1B-LOG-008` | `ARCH-11.2-LOG-EVAL` | `SIMPLIFY` | `\ln(e)` | `1` | `1` | **SUCCESS** |
| `P1B-DIFF-001` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\sin(2*x) + \exp(3*x)` | `3*exp(3*x) + 2*cos(2*x)` | `2*cos(2*x) + 3*exp(3*x)` | **SUCCESS** |
| `P1B-DIFF-002` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\cos(5*x)` | `-5*sin(5*x)` | `-5*sin(5*x)` | **SUCCESS** |
| `P1B-DIFF-003` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\exp(-2*x)` | `-2*exp(-2*x)` | `-2*exp(-2*x)` | **SUCCESS** |
| `P1B-DIFF-004` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\ln(x)` | `1/x` | `1/x` | **SUCCESS** |
| `P1B-DIFF-005` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\log(x, 2)` | `1/(x*log(2))` | `1/(x*log(2))` | **SUCCESS** |
| `P1B-DIFF-006` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\sin(x) + \cos(x)` | `-sin(x) + cos(x)` | `cos(x) - sin(x)` | **SUCCESS** |
| `P1B-DIFF-007` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `\tan(x)` | `tan(x)^2 + 1` | `tan(x)**2 + 1` | **SUCCESS** |
| `P1B-DIFF-008` | `ARCH-11.5-DIFF-TRANSCENDENTAL` | `DIFFERENTIATE` | `x*\exp(x)` | `x*exp(x) + exp(x)` | `x*exp(x) + exp(x)` | **SUCCESS** |
| `P1B-EQ-001` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\log(x-1, 2) + \log(x+1, 2) = 3` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-002` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\log(x^2 - 3, 2) = \log(2*x, 2)` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-003` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\log(x-2, 3) = 2` | `{11}` | `{11}` | **SUCCESS** |
| `P1B-EQ-004` | `ARCH-11.3-EXP-EQ` | `SOLVE` | `2^(x+1) = 8` | `{2}` | `{2}` | **SUCCESS** |
| `P1B-EQ-005` | `ARCH-11.3-EXP-EQ` | `SOLVE` | `3^(2*x - 1) = 27` | `{2}` | `{2}` | **SUCCESS** |
| `P1B-EQ-006` | `ARCH-11.3-EXP-EQ` | `SOLVE` | `\exp(2*x) - 3*\exp(x) + 2 = 0` | `{0, log(2)}` | `{0, log(2)}` | **SUCCESS** |
| `P1B-EQ-007` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\log(x+2, 5) + \log(x-2, 5) = 1` | `{3}` | `{3}` | **SUCCESS** |
| `P1B-EQ-008` | `ARCH-11.3-EXP-EQ` | `SOLVE` | `4^x - 5*2^x + 4 = 0` | `{0, 2}` | `{0, 2}` | **SUCCESS** |
| `P1B-EQ-009` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\ln(2*x - 1) = 0` | `{1}` | `{1}` | **SUCCESS** |
| `P1B-EQ-010` | `ARCH-11.3-LOG-EQ` | `SOLVE` | `\log(x, 2) = 5` | `{32}` | `{32}` | **SUCCESS** |
