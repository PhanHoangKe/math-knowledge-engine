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
### Requirement C: Aggregate Job Memory Limit (Causal Control & 100 MiB Restricted Ceiling)
- **Test:** `TestWindowsJobMemoryLimit` (2 tests)
  - `test_job_memory_limit_isolated_control_succeeds`: Proves identical Worker 2 55 MiB allocation succeeds (exit code 0) under 80 MiB per-process limit when Job limit is generous (200 MiB), establishing the isolated control baseline.
  - `test_job_memory_limit_exceeded_aggregate`: Proves identical Worker 2 55 MiB allocation fails with `MemoryError` (exit code 42) strictly when concurrent Worker 1 holds 55 MiB under restricted 100 MiB Job limit. Bounded handshake polling ensures deterministic execution.
- **Status:** PASS (Verified).

### Requirement D: Breakaway Prevention
- **Test:** `TestWindowsBreakawayRejection.test_breakaway_from_job_rejected`
- **Objective:** Prove that a worker process inside the Job cannot escape by spawning a child process with `CREATE_BREAKAWAY_FROM_JOB`.
- **Mechanism:** Worker inside Job calls `CreateProcessW` with `dwCreationFlags = CREATE_BREAKAWAY_FROM_JOB` (0x01000000) using full 104-byte `STARTUPINFOW`.
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

### Requirement H: Deterministic Full-Lifecycle Timeout & Safe IPC Write Cancellation
- **Test:** `TestWindowsTimeoutAndFraming` (3 tests)
  - `test_worker_payload_too_large`: Verifies oversized payload (> 4096 bytes) is rejected as `ERR_PAYLOAD_TOO_LARGE`.
  - `test_worker_timeout_fails_closed`: Uses dedicated blocking fixture (5.0s sleep with 0.2s timeout), proving strict `outcome: RESOURCE_EXHAUSTED` and `status: WORKER_TIMEOUT` without timing races, duration $< 1.5$s, reporting `details.timeout_phase: "READ"` and immediate process cleanup.
  - `test_worker_timeout_during_ipc_write_non_reading_worker`: Proves single effective deadline covers IPC writing to a non-reading worker with near-maximum payload (4000+ bytes) over 1024-byte pipe buffer. Verified kernel instrumentation:
    * Writer thread pseudo-handle duplicated to real handle via `DuplicateHandle(..., GetCurrentThread(), ...)`
    * Kernel cancellation executed via `kernel32.CancelSynchronousIo(hWriterThread)`
    * Writer thread verified alive before cancel, joined, and confirmed terminated (`writer_thread_alive_after_join: False`) BEFORE pipe handle is closed
    * Factual kernel evidence recorded in `_last_write_info`: `write_entered: True`, `write_blocked_at_deadline: True`, `cancel_synchronous_io_called: True`, `writer_thread_alive_before_cancel: True`, `writer_thread_alive_after_join: False`
    * Reports exact timeout phase: `details.timeout_phase: "WRITE"`.
- **Status:** PASS (Verified).

### Requirement I: Controller Input Boundary Pre-Validation & Bounded Error Envelopes
- **Test:** `TestWindowsControllerInputBoundary` (10 tests)
  - `test_controller_rejects_cyclic_dictionary`: Cyclic structure rejected before serialization as `ERR_PAYLOAD_TOO_LARGE` / `ERR_PROTOCOL_MALFORMED_STRUCTURE`.
  - `test_controller_rejects_non_string_keys`: Non-string keys rejected as `ERR_PROTOCOL_INVALID_TYPE`.
  - `test_controller_rejects_unsupported_types`: Sets / complex types rejected as `ERR_PROTOCOL_INVALID_TYPE`.
  - `test_controller_rejects_oversized_payload`: Oversized dict rejected as `ERR_PAYLOAD_TOO_LARGE`.
  - `test_controller_rejects_isolated_surrogates`: Isolated surrogates rejected as `ERR_PROTOCOL_JSON_DECODE`.
  - `test_controller_rejects_chinese_chars_exceeding_byte_limit_before_job_creation`: 1400 Chinese characters (4200 bytes) rejected as `ERR_PAYLOAD_TOO_LARGE` before Job Object creation (`_inject_job_creation_failure=True` not reached).
  - `test_controller_accepts_chinese_chars_within_byte_limit_before_worker`: 700 Chinese characters (2100 bytes) serialize safely under `ensure_ascii=False` within bounds and advance to Job Object creation.
  - `test_controller_rejects_oversized_operation_and_bounds_error_envelope`: Proves 50,000-char operation string is normalized to `"UNKNOWN"`, not reflected in output, rejected as `ERR_PAYLOAD_TOO_LARGE`, and serialized error response is bounded $\le 16384$ bytes.
  - `test_controller_rejects_raw_string_oversized_operation_bounded`: Proves oversized raw JSON string request with 20,000-char operation is rejected, normalized, and bounded.
  - `test_controller_bounds_error_envelope_under_huge_details`: Proves controller error builder strictly enforces `IPC_MAX_RESPONSE_BYTES` ceiling even under oversized messages/details.
- **Status:** PASS (Verified).

### Requirement J: Strict UTF-8 IPC Transport
- **Test:** `TestWindowsStrictUtf8Ipc` (1 test)
  - `test_strict_utf8_payload_rejection`: Raw invalid UTF-8 byte (`b'x=\xff'`) sent over IPC pipe is rejected strictly as `ERR_PROTOCOL_JSON_DECODE` without character replacement (`errors="replace"` eliminated).
- **Status:** PASS (Verified).

### Requirement K: Restricted Handle Confinement
- **Test:** `TestWindowsHandleConfinement` (1 test)
  - `test_unallowlisted_handle_not_inherited`: An inheritable handle (`bInheritHandle=True`) not present in `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` is proven inaccessible in the worker (`msvcrt.open_osfhandle` fails with `OSError`, exit code 77).
- **Status:** PASS (Verified).

---

## 4. Security Control Status (S4-B1-R2 Verification Matrix)

| Security Control | Implementation Mechanism | Status |
| :--- | :--- | :--- |
| **Job Object Memory Quota (256 MiB/512 MiB)** | Win32 `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` | **RUNTIME VERIFIED** (Pass) |
| **Suspended Startup Assignment** | `CREATE_SUSPENDED` + `IsProcessInJob` | **RUNTIME VERIFIED** (Pass) |
| **Restricted Handle Inheritance** | `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` + `msvcrt` verification | **RUNTIME VERIFIED** (Pass) |
| **Breakaway Prevention** | Disabled breakaway flags + `ERROR_ACCESS_DENIED` test | **RUNTIME VERIFIED** (Pass) |
| **Kill On Job Close** | `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` | **RUNTIME VERIFIED** (Pass) |
| **Full-Lifecycle Timeout** | Single deadline across IPC write & read phases | **RUNTIME VERIFIED** (Pass) |
| **Input Boundary Pre-Validation & Size Check** | Bounded `_measure_dict_bytes` + post-serialization check | **RUNTIME VERIFIED** (Pass) |
| **Strict UTF-8 Transport** | Zero lossy replacement on IPC pipes | **RUNTIME VERIFIED** (Pass) |
| **Fail-Closed Result Taxonomy** | S4 Protocol Error Mapping & Stderr Sanitization | **RUNTIME VERIFIED** (Pass) |
| **Mathematical Non-Fallback Invariant** | Controller Decoupling | **RUNTIME VERIFIED** (Pass) |
| **Restricted Filesystem ACL / Token** | Planned for S4-B2 | **UNVERIFIED / BLOCKED** (Unauthorized in S4-B1) |
| **Outbound Network Blocking (WFP)** | Planned for S4-B2 | **UNVERIFIED / BLOCKED** (Unauthorized in S4-B1) |
| **Adversarial Penetration Certification** | Planned for S4-B3 | **UNVERIFIED / BLOCKED** (Unauthorized in S4-B1) |
| **Overall Sandbox Security Certification** | Post S4-B3 Full Audit | **UNVERIFIED / BLOCKED** (Unauthorized in S4-B1) |

