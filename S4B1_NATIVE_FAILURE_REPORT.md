# S4-B1 Native Failure Final Gate Report

**Milestone:** PRODUCT-02A-S4-B1

**Branch baseline:** `product/p02a-foundation` at `549054072b397a63db25082e33bf08a13412742c`

**Implementation status:** **PASS — PENDING INDEPENDENT AUDIT**

**Scope:** Native Windows close-failure policy and process-termination evidence only

## Outcome

Both remaining native failure-handling findings are implemented and demonstrated on real Windows handles. The worker architecture, mathematical semantics, protocol behavior, Job Object containment, late-duplication behavior, and S4-B1 fail-closed contract are preserved. S4-B2 work was not started.

## Finding 1 — Native Close Failure Policy

**Disposition: RESOLVED, pending independent audit.**

`SafeWin32Handle` now records independent close evidence rather than inferring ownership from a retained integer:

| Condition | Evidence | Automatic policy |
|---|---|---|
| Injected before `CloseHandle` | `INJECTED_BEFORE_CLOSE`, `native_close_attempted=False` | Retry is allowed during ledger reconciliation because the native API was never called. |
| Genuine native `CloseHandle` failure | `NATIVE_CLOSE_FAILURE`, before/after validity and Win32 error retained | No implicit retry. Owner remains unresolved and the controller fails closed. |
| Invalid or stale handle | `INVALID_OR_STALE_HANDLE`, `GetHandleInformation=ERROR_INVALID_HANDLE` | Not considered closed and never retried implicitly. Diagnostic ownership record remains. |
| Successful native close | `CONFIRMED_SUCCESSFUL_CLOSURE`, successful `CloseHandle` | Wrapper transitions to `CONFIRMED_CLOSED`. |

The explicit recovery method `recover_native_close()` is the only path that permits a second native close after a genuine ambiguous failure. It is intended for a caller that has first corrected the external native condition. `reconcile_unresolved_resources()` and `settle_quarantine()` cannot accidentally override this policy because subsequent ordinary `close()` calls are non-operative for native/invalid failure evidence.

The real-native test applies `HANDLE_FLAG_PROTECT_FROM_CLOSE` to a real event handle. `CloseHandle` fails, `GetHandleInformation` proves the handle remains valid and protected, ledger reconciliation leaves the native attempt count unchanged, removal of the flag permits explicit recovery, and a final `GetHandleInformation` returns `ERROR_INVALID_HANDLE`. A separate stale-handle test proves that a closed numeric value is not accepted as ownership or successful cleanup.

## Finding 2 — Process Termination Evidence

**Disposition: RESOLVED, pending independent audit.**

Teardown now centralizes process termination and records two independent dimensions:

- request state: already terminated/not required, requested successfully, or request failed;
- confirmation state: confirmed, or uncertain/failed.

Confirmation requires both `WaitForSingleObject == WAIT_OBJECT_0` and a successful `GetExitCodeProcess` result other than `STILL_ACTIVE`. `WAIT_TIMEOUT`, `WAIT_FAILED`, and exit-code query failure never count as confirmation.

When confirmation is absent, the process handle is marked close-blocked, retained in the persistent unresolved-handle ledger, and never closed speculatively. Job Object ownership is retained if its close also fails. New requests fail closed until containment-backed recovery confirms process termination. If Job Object closure succeeds, `KILL_ON_JOB_CLOSE` supplies a second containment-backed opportunity to wait for and confirm termination before the process handle is released.

The required combined-failure test demonstrates:

1. `TerminateProcess` was requested successfully but an injected wait timeout prevented confirmation.
2. Job Object closure failed before the native close call.
3. The returned response was `WORKER_RESOURCE_EXHAUSTED` with `safe_cleanup=False` and raw termination evidence.
4. Both real native owners remained valid and recorded.
5. The real termination request completed; explicit reconciliation closed the retained Job and process handles safely.

Additional tests cover `WAIT_FAILED` and a failed termination request. In the latter case the live child remains inside the still-owned Job Object; recovering the injected Job close activates `KILL_ON_JOB_CLOSE`, after which termination is observed and the process handle is released. No unmanaged child is intentionally left behind.

## Regression Result

- Complete unittest discovery: **309 / 309 PASS**.
- Baseline mathematical and protocol tests: **246 / 246 preserved**.
- Windows containment/ownership tests: **63 / 63 PASS** (58 existing plus 5 targeted native-failure tests).
- Forensic matrix: **16 / 16 PASS**, exact handle delta `0` for all scenarios and iteration counts.
- Active quarantine after every forensic case: `0`.

Raw results and integrity evidence are listed in `S4B1_NATIVE_FAILURE_EVIDENCE.md`.

## Limitations and Residual Risk

- Windows exposes no generation number for a `HANDLE`. `GetHandleInformation` is point-in-time validity evidence, not proof that an externally closed-and-reused numeric value still denotes the original object. Safety therefore also depends on the controller's exclusive-ownership invariant. No policy in this change treats the integer alone as proof.
- A genuine native close failure intentionally poisons automatic recovery. If an operator cannot correct the native condition and call explicit recovery, the controller remains fail closed and retains the diagnostic owner.
- Wait-result injections simulate timeout/failure observations, while the protected-handle test uses a genuine native `CloseHandle` failure. The raw logs distinguish these evidence types.
- The historical workspace was observed as already dirty and on an unrelated branch; it was not modified. Its Git tree identity and selected direct working-file hashes are separate evidence and must not be interpreted as verification of every working-file byte.
- This implementation does not claim independent approval and does not authorize S4-B2.

## Gate Status

**PASS — PENDING INDEPENDENT AUDIT**
