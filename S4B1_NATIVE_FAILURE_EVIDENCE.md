# S4-B1 Native Failure Final Gate Evidence

**Evidence date:** 2026-09-27 (Asia/Saigon)

**Baseline commit:** `549054072b397a63db25082e33bf08a13412742c`

**Baseline committed-tree digest:** `9971b6f86f7f53cb1f73123c4d36932392f245af`

**Milestone status:** **PENDING INDEPENDENT AUDIT**

## Raw Evidence Inventory

| Artifact | Purpose | SHA-256 |
|---|---|---|
| `evidence/s4b1_native_failure/unittest_full.log` | Complete verbose unittest execution | `147CED5080C290B7B5744537FA2039142259B35D39509E3E3D277E83D8CF16EE` |
| `evidence/s4b1_native_failure/handle_forensics.log` | Complete 16-case forensic console output | `CD9294A360FCFA9C2D4F1AB722FEAFEECDF5ACC0D1E09D851DA0EFEFCA3BBEE2` |
| `handle_forensics_results.json` | Structured 16-case result data | `789B85DB96E64A5C9050BF343CCAA0335B43A9C53424C758FE3195525F0A309F` |
| `evidence/s4b1_native_failure/historical_integrity.log` | Read-only historical Git and direct file evidence | `C5FBA5E17DB3C1AD9CE93FDD47481D9863DFB116A82ABB27485BB0DBF5AD9E48` |

## Complete Unittest Execution

Command requested by the gate (executed with the app-bundled Python executable because `python` was not on shell `PATH`):

```text
python -m unittest discover -s tests -p "test_*.py"
```

Final raw summary:

```text
Ran 309 tests in 17.398s

OK
```

Composition:

- 246 mathematical and protocol tests: preserved and passing.
- 58 pre-existing Windows containment/ownership tests: preserved and passing.
- 5 new targeted tests: passing.
- Total: 309.

New targeted tests:

1. `test_genuine_native_close_failure_is_not_blindly_retried`
2. `test_invalid_stale_handle_is_recorded_not_closed_or_retried`
3. `test_combined_uncertain_termination_and_job_close_failure_fails_closed`
4. `test_failed_termination_wait_is_not_confirmation`
5. `test_failed_termination_request_retains_job_containment`

## Complete 16-Case Forensic Matrix

Command requested by the gate:

```text
python scripts/handle_forensics.py
```

Result:

```text
ALL 16 / 16 FORENSIC SCENARIOS PASSED WITH STRICT ZERO HANDLE DELTA.
```

| Scenario | Iterations | Baseline | Final | Delta | Active quarantine |
|---|---:|---:|---:|---:|---:|
| Normal control | 5 | 165 | 165 | 0 | 0 |
| Normal control | 10 | 165 | 165 | 0 | 0 |
| Normal control | 20 | 165 | 165 | 0 | 0 |
| Normal control | 40 | 165 | 165 | 0 | 0 |
| Write timeout/quarantine | 5 | 165 | 165 | 0 | 0 |
| Write timeout/quarantine | 10 | 165 | 165 | 0 | 0 |
| Write timeout/quarantine | 20 | 165 | 165 | 0 | 0 |
| Write timeout/quarantine | 40 | 165 | 165 | 0 | 0 |
| Setup timeout/hang | 5 | 165 | 165 | 0 | 0 |
| Setup timeout/hang | 10 | 165 | 165 | 0 | 0 |
| Setup timeout/hang | 20 | 165 | 165 | 0 | 0 |
| Setup timeout/hang | 40 | 165 | 165 | 0 | 0 |
| Late duplication | 5 | 165 | 165 | 0 | 0 |
| Late duplication | 10 | 165 | 165 | 0 | 0 |
| Late duplication | 20 | 165 | 165 | 0 | 0 |
| Late duplication | 40 | 165 | 165 | 0 | 0 |

## Native Evidence Assertions

### Close policy

- Protected real event handle: first native `CloseHandle` failed; before/after `GetHandleInformation` state was `VALID`.
- Persistent-ledger reconciliation: native close attempt count did not increase.
- Protection removal: explicit `recover_native_close()` succeeded.
- Post-recovery: `GetHandleInformation` failed with `ERROR_INVALID_HANDLE (6)`.
- Stale real event value: classified `INVALID_OR_STALE_HANDLE`, no native close call issued, no implicit retry issued, and not falsely marked confirmed closed.

### Termination policy

- Successful request plus injected wait timeout: request state `REQUESTED_SUCCESSFULLY`; confirmation state `UNCERTAIN_OR_FAILED`.
- Injected `WAIT_FAILED`: confirmation remained `UNCERTAIN_OR_FAILED`.
- Injected `TerminateProcess` failure: request state `REQUEST_FAILED`; the live process and Job remained owned; recovered Job closure killed the contained process and subsequent observation confirmed termination.
- Combined failure responses: `WORKER_RESOURCE_EXHAUSTED`, `safe_cleanup=False`, process and Job errors retained, unresolved owners non-zero until recovery.

## Historical Integrity Evidence

The historical workspace `D:\Math Knowledge Engine` was read only. It was not pristine at capture time; the raw status is preserved verbatim in `historical_integrity.log`.

- Historical HEAD: `753382a023835dbdbe6b074ca6101a3292d3474c`
- Historical committed-tree digest: `43d1439ef011e7883b97dc632b97b4ff3d7a231c`
- Requested product baseline object present after fetch: `True`
- Before the fetch, resolving the requested commit from the historical checkout failed with `bad object`; the fetched branch was then verified in an isolated managed worktree.

Direct working-file SHA-256 measurements (not a claim about every workspace byte):

| Historical working file | Bytes | SHA-256 |
|---|---:|---|
| `G4P0_FREEZE_RECORD.md` | 3513 | `C1AA4645AD17490D1149DD00A11A6CA86F0AB0E4335DFB76066F0F8BC30B3EBB` |
| `G4P0_MATHEMATICAL_SPECIFICATION.md` | 26251 | `CA4FB5FB115C36E3E401CA49EB78C3153CF3220BA4414EADA493C4AEEC86CA02` |
| `G4P0_MATHEMATICAL_SPECIFICATION_R1.md` | 39489 | `468FD52C7879609A4C22E6AD5D1F9F9BAEEDDDB0C62B3A5FF1C8B919ED5966ED` |
| `G4P0_TWELVE_PAPER_PROBES.md` | 47561 | `61E4F5751ECEDBE46A3C127F9514790387CDAB5C919BDA1254CBEB951860E8C9` |
| `G4P0_TWELVE_PAPER_PROBES_R1.md` | 85250 | `C747EAFF3DD7E3D7E642DDC84520247B8EE114680922C2379419034F1DF9D754` |

The Git tree digest identifies committed content only. The direct SHA-256 measurements identify only the listed working files. Neither is conflated with a byte-for-byte proof of the entire dirty historical workspace.

## Changed-File Inventory

- `src/mke_product/worker/constants.py`
- `src/mke_product/worker/win32.py`
- `src/mke_product/worker/controller.py`
- `tests/test_worker_windows.py`
- `handle_forensics_results.json`
- `evidence/s4b1_native_failure/unittest_full.log`
- `evidence/s4b1_native_failure/handle_forensics.log`
- `evidence/s4b1_native_failure/historical_integrity.log`
- `S4B1_NATIVE_FAILURE_REPORT.md`
- `S4B1_NATIVE_FAILURE_EVIDENCE.md`
- `S4B1_ACCEPTANCE_REPORT.md`

The exact final commit SHA is supplied in the final handoff because a commit cannot contain its own SHA.
