# MKE S4-B2/P1 AppContainer Worker Integration Report

## Disposition

**PASS — pending independent technical audit and Project Owner approval.**

A genuine staged MKE Python worker now runs inside a native Windows
AppContainer and the existing Job Object.  The child is created suspended and
is resumed only after Job membership, AppContainer token identity, exact
profile SID, and non-elevation are verified.

This report describes implementation commit
`deb357dad6f308783d39eb7ada31ae6606c37f67`.  The accepted S4-B1 baseline
`16162ab56028c6f83d70579cab6001f6b3b4c4aa` and audited P0-R1 commit
`2e3ddc61228ecb2561dd7b6a182e02aed95a46da` are both ancestors of that commit.

## Repository safety

- Integration branch: `product/s4b2-p1-integration`.
- Branch point: exact audited P0-R1 commit `2e3ddc61228ecb2561dd7b6a182e02aed95a46da`.
- The accepted product branch was not changed.
- The historical working tree at `D:\Math Knowledge Engine` was not modified.
- No merge, rebase, amend, force-push, or push was performed.

## Integrated startup gate

The controller allocates a two-entry `STARTUPINFOEXW` attribute list and sets
both mandatory attributes:

1. `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` containing only worker stdin, stdout,
   and stderr pipe ends.
2. `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES` containing the intended
   AppContainer SID and zero optional capabilities.

The process starts with
`CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT`.
Before `ResumeThread`, the controller:

1. assigns and verifies the child in the configured Job Object;
2. opens the child token;
3. verifies `TokenIsAppContainer`;
4. reads `TokenAppContainerSid` and compares it with `EqualSid`;
5. verifies `TokenElevation == false`;
6. terminates the still-suspended child on any mismatch.

The accepted Job controls remain unchanged: 256 MiB per-process memory,
512 MiB job-wide memory, `KILL_ON_JOB_CLOSE`, and no breakaway permission.

## Staged Python worker

The process-local manager stages a disposable runtime under the current
temporary directory.  The staged tree contains:

- the current `python.exe`, `python*.dll`, and `vcruntime*.dll` files;
- the standard-library `DLLs` and `Lib` trees, excluding development, GUI,
  test, package-installation, virtual-environment, cache, and site-package
  directories;
- only `src/mke_product/**/*.py` from the product source;
- one fixed bootstrap file for `mke_product.worker.entrypoint`.

The intended AppContainer SID receives only inherited read/execute access
`(OI)(CI)RX` to this tree.  The worker runs with `-I -S -B` and an explicit
environment allowlist.  No product repository, historical workspace, user
home, or system-directory write grant is added.

The captured manifest contains 673 files totaling 36,388,444 bytes.  Its
path-and-content aggregate SHA-256 is
`9B8915A38FF6890F6A6C315DCF6177AE03C9C12B107B77E6022395D185BB921B`.

## IPC and handle security

The existing length-prefixed stdin/stdout protocol is unchanged.  A real
`SOLVE x=1` request returned `SUCCESS`, `UNIQUE_ROOT`, numerator `1`, and
denominator `1`.

The decoy test uses an inheritable Event not present in the handle list.  The
child performs an object-type-aware probe, so reuse of the same numeric handle
for an allowlisted pipe cannot cause a false positive.  The Event is not
accessible.  Existing cancellation, timeout, quarantine, ownership,
double-close, native-close-failure, and recovery tests all continue to pass.

## Profile lifecycle

- A unique zero-capability profile is created lazily per controller host
  process and reused by that process.
- A lease is acquired before process creation.
- The lease is released only after native termination confirmation.
- If termination is uncertain, the lease follows the unresolved process owner
  and is released during evidence-backed reconciliation.
- Profile deletion is refused while any lease is active.
- Preparation failures remove staged resources and delete the created profile.
- Normal cleanup deletes the stage and profile only at zero active leases.
- Cleanup failures retain an explicit diagnostic state; no unrestricted
  fallback exists.

Captured lifecycle evidence shows `REFUSED_ACTIVE_CHILDREN` with one lease,
then `CLEANED`, stage removed, and `DeleteAppContainerProfile` HRESULT zero
after release.

## Verification results

- Complete unit/integration discovery: **316 passed, 0 failed, 0 skipped** in
  34.369 seconds.
- New AppContainer integration class: **6 passed**.
- Handle forensics: **16/16 passed**, strict zero handle delta in every case,
  zero active quarantine records, and all recorded handles confirmed closed.
- Real token evidence: AppContainer true, actual SID equals intended SID,
  elevated false, Job verified, and resume occurred only after verification.

The forensics tool performs a separate 20-worker burn-in before taking any
baseline.  This retires two one-time Windows/CPython initialization handles;
the historical per-case `net_delta == 0` assertion remains unchanged.

## Changed implementation inventory

- `src/mke_product/worker/appcontainer.py`
- `src/mke_product/worker/constants.py`
- `src/mke_product/worker/controller.py`
- `tests/test_worker_windows.py`
- `scripts/handle_forensics.py`
- `scripts/appcontainer_worker_evidence.py`
- `handle_forensics_results.json`
- `evidence/s4b2_p1/*`

## Remaining scope and risks

P1 establishes the real worker's AppContainer identity, verified suspended
startup, staged runtime read access, strict inherited handles, Job containment,
and lifecycle safety.  It does **not** establish complete filesystem isolation
or outbound/loopback network isolation.  Dedicated positive and negative
filesystem and TCP/UDP experiments remain required before either guarantee can
be claimed.  S4-B2 is not declared complete, and no P2 work was started.
