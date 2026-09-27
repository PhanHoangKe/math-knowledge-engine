# MKE S4-B2/P0 Feasibility Report

## Decision

**REVISE** — the tracked S4-B1 cleanup exception is closed and the complete
regression remains green, but this host did not create an AppContainer process.
The P1 architecture must therefore be revised and validated with a native
reference launcher before any isolation claim or full S4-B2 implementation.

This report is an implementation/preflight handoff, not independent audit
approval.

## Scope and repository state

- Baseline commit: `16162ab56028c6f83d70579cab6001f6b3b4c4aa`
- Baseline remote: `origin/product/p02a-foundation` at the same commit
- Isolated implementation branch: `product/s4b2-preflight`
- Worktree: managed S4-B1 worktree; the historical workspace was not modified
- Host: Windows 11 build `26200`
- AppContainer probe account: `phanhoangke\kedep`
- Probe token: standard, non-administrator, non-elevated

## Phase 1 — tracked S4-B1 exception

**PASS.** `create_configured_job_object()` still returns its original public
two-tuple. When Job configuration fails, it now preserves the configuration
error and checks the native `CloseHandle` result. A failed cleanup produces a
persistent ownership record containing the real handle, configuration error,
cleanup error, validity observation, and failure id.

The controller claims that record immediately, adopts it into the existing
`SafeWin32Handle` ledger without a blind second close, fails closed, and returns
actionable diagnostics. Explicit recovery remains separate from ordinary ledger
reconciliation.

The new Windows test creates a genuine combined failure:

- zero Job memory limits make `SetInformationJobObject` fail with Win32 error
  `87` (`ERROR_INVALID_PARAMETER`);
- `HANDLE_FLAG_PROTECT_FROM_CLOSE` makes the following native `CloseHandle`
  fail (observed Win32 error `6` on this host);
- the real still-valid handle is transferred to the controller ledger;
- reconciliation does not retry the ambiguous native close;
- after the test removes the protection flag, explicit recovery closes it and
  the unresolved count returns to zero.

## Phase 2 — AppContainer probes

| Probe | Result | Direct observation |
|---|---|---|
| A. Standard-user profile lifecycle | **PASS** | `CreateAppContainerProfile`, SID derivation, SID validation/equality, and deletion all succeeded under a non-elevated standard token. |
| B. Process creation and handle-list coexistence | **FAIL** | Both security-capability and handle-list attribute updates succeeded, but `CreateProcessW` returned error `87` for security-only staged CPython, combined CPython + handle list, and a clean native `whoami.exe` control. |
| C. Minimal Python runtime | **INCONCLUSIVE** | A 36,084,323-byte runtime was staged and granted profile-SID RX, but no child process started. Runtime sufficiency was not demonstrated. |
| D. TCP/UDP loopback denial | **INCONCLUSIVE** | The child never started, so neither protocol reached its fixture. Socket-close markers are fixture cleanup, not security-policy evidence. No network-isolation claim is made. |
| E. Assigned-directory write / outside denial | **INCONCLUSIVE** | Profile-SID RX/M ACL grants succeeded, but no child ran; neither the allowed write nor the denied write was exercised. No filesystem-isolation claim is made. |

The successful dual attribute-list updates show that the two documented
attributes can be constructed together in this harness. They do **not** prove
that a process can be launched with that combination. The same error from the
security-only native control makes the observed failure broader than the staged
Python runtime or its ACL, but does not by itself establish the root cause.

## Phase 3 — recommendation

**REVISE** is the only evidence-supported gate result:

- not **GO**, because process launch and probes C–E were not demonstrated;
- not **STOP**, because the standard-user profile/SID lifecycle and attribute
  construction succeeded, leaving a credible path for a corrected P1 design.

### P1 implementation plan

1. Build and run a tiny native C/C++ launcher derived from Microsoft's
   AppContainer reference on a supported stable Windows host; isolate the source
   of `CreateProcessW` error `87` before changing product code.
2. Choose explicitly between the existing `STARTUPINFOEX` design and
   `Experimental_CreateProcessInSandbox`. The latter rejects inherited handles,
   so adopting it would require a separately reviewed IPC redesign rather than
   a silent substitution.
3. Once a native child launches, rerun the staged-CPython dependency and ACL
   matrix until the minimal runtime is proven rather than assumed.
4. Run controlled capability-free TCP and UDP loopback probes and record exact
   child-side WinSock results.
5. Run positive assigned-directory and negative outside-directory write probes
   and retain the resulting ACL and filesystem evidence.
6. Only then design integration with the existing Job containment, strict
   inherited-handle allowlist, fail-closed behavior, and no-isolation-fallback
   rule.

## Phase 4 — regression

- Full unittest discovery: **310/310 passed** (`Ran 310 tests ... OK`)
- Strict handle forensics: **16/16 passed**, every case net handle delta `0`
- Final active quarantine count: `0`; all recorded handles confirmed closed

The final code state was rerun after the ownership-ledger hardening. Raw logs
and structured probe output are listed in `S4B2_P0_EXPERIMENT_EVIDENCE.md`.

## Microsoft references

- [CreateAppContainerProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-createappcontainerprofile)
- [DeleteAppContainerProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deleteappcontainerprofile)
- [DeriveAppContainerSidFromAppContainerName](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-deriveappcontainersidfromappcontainername)
- [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
- [Implementing an AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer)
- [AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)
- [App-service IPC and loopback](https://learn.microsoft.com/en-us/windows/apps/develop/communication/interprocess-communication)
- [Sockets for UWP/AppContainer applications](https://learn.microsoft.com/en-us/windows/uwp/networking/sockets)
- [Windows Firewall AppContainer troubleshooting](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/troubleshooting-uwp-firewall)
- [Experimental_CreateProcessInSandbox](https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox)
- [Microsoft SandboxSecurityTools reference launcher](https://github.com/microsoft/SandboxSecurityTools/blob/main/LaunchAppContainer/LaunchAppContainer/LaunchAppContainer.cpp)
