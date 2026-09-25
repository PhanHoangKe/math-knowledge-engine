# DEV-02A Final Acceptance Evidence

Repository: `PhanHoangKe/math-knowledge-engine`  
PR: `#1`  
Target: `ef0276a6e161b48b2d7ee069f1e646bd965d0c58`  
Comparison: `dev01-accepted` (`c9199abf3148b4983d3f29cd214e164cef0aad9e`) → `dev02a-method-knowledge-base`

## Mission A — reproducible execution

The repository declares Python `>=3.10` and pins its runtime dependencies in `pyproject.toml:8-39`: `sympy==1.14.0`, `pydantic==2.13.5`, `typer==0.25.1`, `rich==13.9.4`, with `pytest==9.1.1` under the `dev` extra. A clean `.audit-venv` was created with Python **3.12.14** and installed from `.[dev]`; the exact resolved environment is preserved in [`audit_logs/pip-freeze.txt`](D:/Math%20Knowledge%20Engine/audit_logs/pip-freeze.txt).

The complete suite ran from the target checkout:

```
166 collected, 166 passed in 5.63s
```

The raw output is [`audit_logs/pytest-v.log`](D:/Math%20Knowledge%20Engine/audit_logs/pytest-v.log). The existing independent suites also passed: DEV-01 R2 gates **7/7**, R2 recheck **6/6**, DEV-02A dependency-free gates **10/10**. Their unmodified logs are in `audit_logs/`.

CLI execution passed:

* `kb validate`: `VALID`, errors 0, warnings 0; 5 methods, 15 families, 41 problems, 43 annotations, 4 transfer pairs.
* `kb run-dev-validation`: 41 normalized, 39 method verified, 39 solution verified, 37 ground-truth matches, 7 discrepancies.
* `kb list-methods`: 5 method templates listed.

Raw CLI output is in [`audit_logs/cli-kb-validate.log`](D:/Math%20Knowledge%20Engine/audit_logs/cli-kb-validate.log), [`audit_logs/cli-kb-run-dev-validation.log`](D:/Math%20Knowledge%20Engine/audit_logs/cli-kb-run-dev-validation.log), and [`audit_logs/cli-kb-list-methods.log`](D:/Math%20Knowledge%20Engine/audit_logs/cli-kb-list-methods.log). No production source or research data was edited.

## Mission B — seven-record adjudication

The source records are [`reports/DEV02A_DISCREPANCIES.json`](D:/Math%20Knowledge%20Engine/reports/DEV02A_DISCREPANCIES.json). All source problems have `domain_str=R` and no excluded points unless stated; method-instance IDs and guards are retained in `data/dev_pilot/annotations.jsonl`.

| Record | Mathematical/domain check | Method/guard evidence | Classification | Conclusion |
|---|---|---|---|---|
| `PROB_FAM02_V03` — `5*x=0`, expected `{0}`, verifier `{}` / `UNDETERMINED` | Over `R`, `5x=0` has exactly `{0}`; domain is all real numbers. | Annotation `INST_PROB_FAM02_V03_M1` says M1 applicable. Independent engine run chose M3 and rejected it because degree is 1. Direct M1 run returns candidate `[0]` and all obligations PASS. Dispatch heuristic in `src/mke/verification/engine.py:384-391` treats any `left '*'` with RHS zero as factorization, while M3 requires degree ≥2 (`src/mke/methods/m3_factorization.py:29-39`). | **IMPLEMENTATION_BUG** | Real dispatcher bug causing a false unresolved result; annotation is mathematically correct. Proposed patch: require polynomial degree ≥2 before the M3 raw-product dispatch, then add a regression test for `5*x=0`. |
| `PROB_FAM03_V01` — `(1/2)x+3/4=0`, expected `{-3/2}`, verifier root correct but M1 `NOT_APPLICABLE` | Constant denominators do not exclude any real x; root is `-3/2`. | Annotation `INST_PROB_FAM03_V01_M1` and M1 applicable. M1 guard `STRUCTURAL_NON_RATIONAL` rejects `norm_eq.is_rational` (`src/mke/methods/m1_linear.py:24-34,65-67`) even though denominators are numeric constants. | **VERIFIER_LIMITATION** | The mathematics and root are correct; the verifier’s structural scope is narrower than the DEV-02A FAM-03 family. Keep annotation provisional; broaden M1 only through an explicitly scoped patch and tests for constant rational coefficients. |
| `PROB_FAM03_V02` — `(2/3)x-4/5=0`, expected `{6/5}`, same mismatch | Domain `R`; exact root `6/5`. | Same M1 non-rational guard and same annotation binding as V01. | **VERIFIER_LIMITATION** | Same root cause and proposed patch scope as V01. |
| `PROB_FAM03_V03` — `(1/2)x+3/4=1/4`, expected `{-1}`, same mismatch | Domain `R`; subtracting RHS gives `x+1=0`, root `-1`. | Same M1 guard limitation; record is tagged `TRANSFER_NEAR_MISS`, but no domain exclusion exists. | **VERIFIER_LIMITATION** | The transfer tag does not make the direct M1 scope mismatch disappear. Keep provisional and adjudicate after a scoped constant-denominator capability decision. |
| `PROB_FAM07_V03` — `x(x-3)=4`, expected `{-1,4}`, verifier agrees and says M3 applicable while annotation says not | Domain `R`; equivalent polynomial is `x²-3x-4=(x-4)(x+1)`, so both roots are valid. | Annotation `INST_PROB_FAM07_V03_M3` sets `NOT_APPLICABLE` with failed degree/form guard. The engine normalizes and factors the target successfully; direct run returns `[-1,4]`. | **PROVISIONAL_LABEL_ERROR** | The annotation’s negative method label conflicts with the target’s actual factorability. The related transfer near-miss is valid only for copying the source product without expansion; it does not justify a negative label for solving the target directly. |
| `PROB_FAM08_V03` — `x²+9=0`, expected `{}`, verifier proves empty and says M3 not applicable | Domain `R`; no real roots because discriminant is `-36`. | M3 requires nontrivial rational factorization (`src/mke/methods/m3_factorization.py:29-39,65-76`); `x²+9` is irreducible over `Q`. Annotation says M3 applicable despite its failed guard. | **PROVISIONAL_LABEL_ERROR** | Empty solution is correct, but M3 applicability is not. The record should remain provisional and be relabeled or explicitly documented as a boundary near-miss; no data was changed. |
| `PAIR_FAM09_V01_V03` — source roots `{-2,1}` transferred to `(x-1)(x+2)=4` | Target has domain `R`; source roots do not satisfy target equation (residue `-4` for both). Solving target independently gives `{-3,2}`. | Transfer auditor returns `UNSAFE_COPY` and rejects both candidates; pair proposes `INAPPLICABLE_INSTANCE`. Evidence and guard obligations are in `data/dev_pilot/transfer_pairs.jsonl` and `src/mke/knowledge/dev01_adapter.py:143-174`. | **INTENDED_NEAR_MISS** | Direct copying is unsafe, exactly as the guard intends. The enum mismatch is a vocabulary distinction between “instance cannot transfer” and “candidate copy is unsafe,” not evidence that either candidate is valid. |

## Blockers and acceptance status

The seven discrepancies are not all traps. One is a confirmed implementation bug (`PROB_FAM02_V03`), three expose a verifier scope limitation for constant rational coefficients, two are provisional annotation errors, and one is an intended transfer near-miss. The acceptance blocker is therefore the unresolved production dispatch bug and the need to adjudicate/patch the FAM-03 scope before promoting those labels. All labels remain provisional; no gold promotion, merge, or DEV-02B deployment is authorized by this evidence.

