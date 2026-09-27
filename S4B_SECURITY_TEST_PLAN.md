# MKE PRODUCT-02A-S4-B Security Test Plan & Verification Specification

**Milestone:** Windows Job Object & Worker Lifecycle (S4-B1)  
**Branch:** `product/p02a-foundation`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
**Status:** ACTIVE (S4-B1 Verified; S4-B2 / S4-B3 Planned / Unverified)  

---

## 1. Scope & Objective

Milestone S4-B1 establishes the Windows process-containment foundation for MKE Product without claiming full sandbox security.
This document defines the verification strategy, security test cases, observed kernel behaviors, and boundaries separating verified Job Object containment from future filesystem and network isolation milestones.

### Authorized Scope (S4-B1)
- Windows Job Object creation and extended limit configuration via Python standard library `ctypes`.
- Suspended worker process launch (`CREATE_SUSPENDED`) and pre-execution Job Object assignment verification.
- Explicit handle inheritance via `STARTUPINFOEXW` and `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`.
- Anonymous-pipe local IPC with 4-byte length prefix framing.
- Windows kernel containment enforcement: 256 MiB per-process memory limit, 512 MiB job memory limit, breakaway rejection (`CREATE_BREAKAWAY_FROM_JOB`), and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- Deterministic error taxonomy and fail-closed termination.

### Explicitly Excluded (Unauthorized in S4-B1)
- Restricted filesystem tokens and ACL confinement (deferred to S4-B2).
- OS-enforced outbound network blocking (WFP / AppContainer) (deferred to S4-B2).
- Adversarial sandbox penetration certification (deferred to S4-B3).
- HTTP API exposure, UI integration, or holdout execution.

---

## 2. Test Architecture & Environment

### 2.1 Test Platform
- **Operating System:** Windows 11 / Windows 10 Pro (Build 10.0.26200 AMD64)
- **Architecture:** AMD64 (64-bit)
- **Python Runtime:** Python 3.10.11 (64-bit standard library)
- **Privilege Level:** Unprivileged user mode (no Administrator privileges required or requested)
- **Nested Job Object Support:** Verified active on the host platform.

### 2.2 Test Isolation Strategy
- All stress tests, memory allocation checks, and kill tests execute strictly inside disposable worker processes.
- The controller main process, test runner, and repository workspace never allocate stress buffers or execute untrusted code.
- Every test deterministically reclaims all Windows handles in `finally` blocks.

---

## 3. Security Demonstration Matrix (Requirements A–G)

### Requirement A: Suspended Startup & Pre-Execution Assignment
- **Test:** `TestWindowsSuspendedStartup.test_worker_assigned_to_job_before_thread_resumed`
- **Objective:** Prove worker is assigned to configured Job Object before its primary thread executes any instructions.
- **Mechanism:**
  1. `CreateJobObjectW` and configure limits.
  2. `CreateProcessW` with `CREATE_SUSPENDED`.
  3. `AssignProcessToJobObject` while thread is suspended.
  4. Call `IsProcessInJob(pi.hProcess, hJob)` $\implies$ returns `True`.
  5. Call `QueryInformationJobObject` (`JobObjectBasicProcessIdList`) $\implies$ proves `pi.dwProcessId` is present in Job.
  6. Call `ResumeThread(pi.hThread)` $\implies$ returns previous suspend count `1`.
- **Expected Kernel Behavior:** Thread is un-suspended only after verified membership in the Job Object.
- **Status:** PASS (Verified).

### Requirement B: Per-Process Memory Limit (256 MiB)
- **Test:** `TestWindowsProcessMemoryLimit.test_process_memory_limit_exceeded_disposable_worker`
- **Objective:** Verify observed kernel behavior when a single process attempts to commit memory exceeding 256 MiB (`268,435,456` bytes).
- **Mechanism:** Disposable worker attempts to commit a 300 MiB bytearray.
- **Observed Kernel Behavior:** Windows denies commitment quota (`ERROR_COMMITMENT_LIMIT`). The CRT allocation fails, Python raises `MemoryError`, and the worker exits with controlled exit code 42. The controller queries `JobObjectExtendedLimitInformation`, detects peak memory, and returns `WORKER_RESOURCE_EXHAUSTED`.
- **Status:** PASS (Verified).

### Requirement C: Aggregate Job Memory Limit (512 MiB / 100 MiB Test Ceiling)
- **Test:** `TestWindowsJobMemoryLimit.test_job_memory_limit_exceeded_aggregate`
- **Objective:** Verify that multiple concurrent processes in the same Job Object cannot exceed the aggregate Job memory limit, even when each process stays within its individual per-process ceiling.
- **Mechanism:**
  1. Configure Job Object with 100 MiB Job limit and 80 MiB Process limit.
  2. Worker 1 commits 55 MiB ($< 80$ MiB, $< 100$ MiB) and sleeps.
  3. Worker 2 requests 55 MiB ($< 80$ MiB per-process limit). Aggregate commit would be 110 MiB ($> 100$ MiB).
- **Observed Kernel Behavior:** Worker 2's allocation fails with `MemoryError` (exit code 42) strictly due to Job memory limit exhaustion.
- **Status:** PASS (Verified).

### Requirement D: Breakaway Prevention
- **Test:** `TestWindowsBreakawayRejection.test_breakaway_from_job_rejected`
- **Objective:** Prove that a worker process inside the Job cannot escape by spawning a child process with `CREATE_BREAKAWAY_FROM_JOB`.
- **Mechanism:** Worker inside Job calls `CreateProcessW` with `dwCreationFlags = CREATE_BREAKAWAY_FROM_JOB` (0x01000000).
- **Observed Kernel Behavior:** Windows kernel immediately blocks process creation and returns `ERROR_ACCESS_DENIED` (error code 5). Exit code 55 confirms rejection.
- **Status:** PASS (Verified).

### Requirement E: Kill on Job Close
- **Test:** `TestWindowsKillOnJobClose.test_kill_on_job_close_terminates_worker`
- **Objective:** Prove that closing the last Job Object handle immediately terminates all associated disposable worker processes.
- **Mechanism:**
  1. Worker launched with 60-second sleep.
  2. Confirmed actively running with `WaitForSingleObject` returning `WAIT_TIMEOUT`.
  3. Controller closes the single Job Object handle (`CloseHandle(hJob)`).
- **Observed Kernel Behavior:** Windows kernel terminates the worker immediately (`WaitForSingleObject` returns `WAIT_OBJECT_0` within 100ms).
- **Status:** PASS (Verified).

### Requirement F: Fail-Closed Failure Paths
- **Test:** `TestWindowsFailurePaths` (5 tests)
- **Objective:** Verify deterministic error mapping and complete resource cleanup across all injected lifecycle failures.
- **Injected Stages:**
  1. Job Object creation failure $\implies$ `WORKER_STARTUP_FAILURE`.
  2. Job Object configuration failure $\implies$ `WORKER_STARTUP_FAILURE`.
  3. Process creation failure $\implies$ `WORKER_STARTUP_FAILURE`.
  4. Assignment failure $\implies$ `WORKER_ASSIGNMENT_FAILURE` (suspended process terminated immediately).
  5. Thread resume failure $\implies$ `WORKER_STARTUP_FAILURE` (suspended process terminated).
- **Expected Outcome:** Fail closed with `outcome: PROTOCOL_ERROR`, `definedness: null`, zero orphaned processes, and zero handle leaks.
- **Status:** PASS (Verified).

### Requirement G: Mathematical Parity & Non-Fallback Rule
- **Test:** `TestWindowsMathematicalRegression` (9 tests)
- **Objective:** Prove exact equivalence between worker-routed execution and direct S4-A dispatch across all mathematical categories (`UNIQUE_ROOT`, `DomainSet(R)`, `EmptySet`, `OUT_OF_SCOPE`, `DOMAIN_ERROR`, `VALID`, `INVALID`).
- **Critical Policy:** Controller performs ZERO fallback math when worker execution fails.
- **Status:** PASS (Verified).

---

## 4. Security Control Status (S4-B1 Closure)

| Security Control | Implementation Mechanism | Status |
| :--- | :--- | :--- |
| **Job Object Memory Quota (256 MiB/512 MiB)** | Win32 `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` | **VERIFIED** (Pass) |
| **Suspended Startup Assignment** | `CREATE_SUSPENDED` + `IsProcessInJob` | **VERIFIED** (Pass) |
| **Restricted Handle Inheritance** | `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` | **VERIFIED** (Pass) |
| **Breakaway Prevention** | Disabled `JOB_OBJECT_LIMIT_BREAKAWAY_OK` | **VERIFIED** (Pass) |
| **Kill On Job Close** | `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` | **VERIFIED** (Pass) |
| **Fail-Closed Result Taxonomy** | S4 Protocol Error Mapping | **VERIFIED** (Pass) |
| **Mathematical Non-Fallback Invariant** | Controller Decoupling | **VERIFIED** (Pass) |
| **Restricted Filesystem ACL / Token** | Planned for S4-B2 | **PLANNED / UNVERIFIED** |
| **Outbound Network Blocking (WFP)** | Planned for S4-B2 | **PLANNED / UNVERIFIED** |
| **Adversarial Penetration Certification** | Planned for S4-B3 | **PLANNED / UNVERIFIED** |
| **Overall Sandbox Security Certification** | Post S4-B3 Full Audit | **PLANNED / UNVERIFIED** |
