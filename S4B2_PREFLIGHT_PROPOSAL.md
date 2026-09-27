# MKE PRODUCT-02A-S4-B2 Preflight Architecture & Isolation Proposal

**Milestone:** Windows Filesystem Confinement & Outbound Network Denial (S4-B2 Preflight Design)  
**Status:** Read-Only Architectural Proposal (Zero Implementation Code Changed)  
**Target Milestone:** S4-B2  
**Target Platform:** Windows 10 / 11 (64-bit AMD64)  
**Author:** Anty (Antigravity)  
**Chief Architect & Auditor:** ChatGPT  
**Approval Authority:** Project Owner (Kế Phan Hoàng)  

---

## 1. Executive Summary & Design Goals

The objective of milestone **PRODUCT-02A-S4-B2** is to establish defense-in-depth OS isolation around disposable Windows worker processes created by `WorkerController`:
1. **Filesystem Confinement:** Restrict the worker's filesystem access so it cannot write to repository files, system directories, user profiles, or arbitrary disks, restricting write operations exclusively to an ephemeral per-request scratch directory.
2. **Outbound Network Denial:** Completely deny worker processes the ability to establish TCP/UDP connections, bind local listening sockets, or communicate over loopback/LAN/WAN.
3. **Non-Administrative Feasibility:** Implement isolation mechanisms that function strictly under a standard, non-elevated user token (avoiding `SeDebugPrivilege` or Administrator rights).

---

## 2. 10-Point Technical Evaluation Matrix

### Point 1: Standard-User AppContainer Profile Creation
- **API:** `CreateAppContainerProfile` from `Userenv.dll`.
- **Function Signature:**
  ```c
  HRESULT CreateAppContainerProfile(
      PCWSTR pszAppContainerName,
      PCWSTR pszDisplayName,
      PCWSTR pszDescription,
      PSID_AND_ATTRIBUTES pCapabilities,
      DWORD dwCapabilityCount,
      PSID* ppSidAppContainerSid
  );
  ```
- **Feasibility:** Fully supported for standard, non-elevated user tokens. Windows manages AppContainer profiles in the calling user's registry hive (`HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Mappings`).
- **Execution Pattern:** For each request, `WorkerController` creates an ephemeral profile `f"MKE.Worker.S4B2.{request_id}"` with `dwCapabilityCount = 0`.

### Point 2: Profile Deletion & Lifecycle Cleanup
- **API:** `DeleteAppContainerProfile` from `Userenv.dll`.
- **Function Signature:**
  ```c
  HRESULT DeleteAppContainerProfile(
      PCWSTR pszAppContainerName
  );
  ```
- **Feasibility:** Standard user tokens can delete AppContainer profiles created under their own security context.
- **Teardown Guarantee:** In the controller's `finally:` block, `DeleteAppContainerProfile` is invoked synchronously after worker process termination, guaranteeing zero persistent registry or profile residue.

### Point 3: SID Lifecycle Management & Memory Freeing
- **API:** `DeriveAppContainerSidFromAppContainerName` and `FreeSid` from `Advapi32.dll`.
- **Lifecycle Invariants:**
  1. The allocated SID buffer returned by `CreateAppContainerProfile` (or `DeriveAppContainerSidFromAppContainerName`) is wrapped in a Python RAII context.
  2. `kernel32.FreeSid(psid)` is guaranteed in the cleanup handler.
  3. No SID memory or security descriptor handles leak across requests.

### Point 4: Job Object Compatibility
- **Evaluation:** Can an AppContainer process run inside a Windows Job Object?
- **Finding:** **Yes, 100% compatible.**
- **Integration Mechanism:**
  1. `CreateProcessW` is invoked with `EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED`.
  2. `STARTUPINFOEXW` contains both `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` (pipes) and `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES` (AppContainer SID).
  3. While suspended, `assign_and_verify_process_in_job(h_job, pi.hProcess)` attaches the AppContainer worker to the existing S4-B1 Job Object.
  4. Memory quotas (`JOB_OBJECT_LIMIT_PROCESS_MEMORY`, `JOB_OBJECT_LIMIT_JOB_MEMORY`) and `KILL_ON_JOB_CLOSE` enforce process limits without interfering with AppContainer token isolation.

### Point 5: Inherited Anonymous Stdio Pipes Across Boundary
- **Evaluation:** Can standard anonymous pipes created by the controller cross the AppContainer isolation boundary?
- **Finding:** **Yes, via `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`.**
- **Mechanism:**
  - Anonymous pipes created with `bInheritHandle = True` in the controller are explicitly included in `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`.
  - Windows bypasses DACL checks for handles explicitly inherited via `STARTUPINFOEXW`, ensuring high-speed IPC communication without requiring custom named pipe ACLs or network sockets.

### Point 6: Python DLL and C-Runtime Accessibility
- **Evaluation:** Can the AppContainer worker access CPython binaries and standard library DLLs?
- **Finding:** **Yes, using `ALL_APPLICATION_PACKAGES` (SID `S-1-15-2-1`).**
- **Implementation:**
  - Standard Windows system directories (`C:\Windows\System32`, `ucrtbase.dll`, `vcruntime140.dll`) have default Read/Execute grants for `ALL_APPLICATION_PACKAGES`.
  - The Python runtime directory (`sys.executable`) and MKE source tree (`src/mke_product`) are verified for Read & Execute access by `ALL_APPLICATION_PACKAGES`.

### Point 7: Filesystem Write Containment & Ephemeral Scratch Directory
- **Access Control Matrix:**
  | Directory / Path | Access Mode | Enforcement Mechanism |
  |---|---|---|
  | **Python Runtime / System DLLs** | Read & Execute | `ALL_APPLICATION_PACKAGES` Read/Execute DACL |
  | **MKE Source Tree (`src/`)** | Read Only | `ALL_APPLICATION_PACKAGES` Read DACL |
  | **Ephemeral Request Scratch Dir** | Read & Write | Container SID explicit Full Control DACL (`GENERIC_ALL`) |
  | **Repository Root (`.git/`, tests)** | Access Denied | Default AppContainer boundary (no package grant) |
  | **User Profile (`C:\Users\...`)** | Access Denied | Default AppContainer boundary |
- **Scratch Directory Lifecycle:**
  1. Controller creates temporary directory `d:\mke-product\.tmp\scratch_<req_id>`.
  2. Sets explicit DACL granting `GENERIC_ALL` to the worker's AppContainer SID.
  3. Worker executes with `TMP`, `TEMP`, and `PYTHONPYCACHEPREFIX` set to the scratch directory.
  4. Controller recursively purges the directory in `finally:`.

### Point 8: Outbound TCP/UDP Network Denial at Kernel Layer
- **Enforcement Mechanism:**
  - `dwCapabilityCount = 0` in `SECURITY_CAPABILITIES`.
  - Omitting `internetClient` (`S-1-15-3-1`), `internetClientServer` (`S-1-15-3-2`), and `privateNetworkClientServer` (`S-1-15-3-3`).
  - The Windows kernel network drivers (`tcpip.sys` and `afd.sys`) enforce capability checks directly at the transport layer.
  - Any worker attempt to call `socket()`, `connect()`, or `bind()` fails deterministically with `WSAEACCES` (Win32 error `10013` / *Permission Denied*) or `WSAENETUNREACH`.

### Point 9: Non-Administrative Execution Feasibility
- **Privilege Requirements:**
  - `CreateAppContainerProfile` $\to$ Standard user.
  - `DeleteAppContainerProfile` $\to$ Standard user.
  - `CreateJobObjectW` / `AssignProcessToJobObject` $\to$ Standard user.
  - `SetNamedSecurityInfoW` on scratch directory $\to$ Standard user (file owner).
- **Result:** Complete S4-B2 isolation functions without elevation or administrative privileges.

### Point 10: Fallback & Error Handling Strategy
- **Failure Modes:**
  1. If `CreateAppContainerProfile` fails (e.g. registry quota error or unsupported Windows edition):
     - Fail closed immediately with `WORKER_STARTUP_FAILURE`.
     - Log diagnostic Win32 error code.
     - Never fall back to uncontained execution.
  2. If scratch directory DACL assignment fails:
     - Terminate worker creation and return `WORKER_STARTUP_FAILURE`.
  3. If profile deletion fails:
     - Log diagnostic warning and track in controller quarantine ledger for subsequent cleanup.

---

## 3. Independent Verification Strategy for S4-B2

The S4-B2 test suite will execute adversarial containment probes directly inside the sandboxed worker:

1. **Network Denial Probes:**
   - Probe 1: TCP connect to external DNS (`8.8.8.8:53`) $\to$ must fail with `PermissionError` / `WSAEACCES`.
   - Probe 2: TCP connect to local loopback (`127.0.0.1:8080`) $\to$ must fail with `PermissionError` / `WSAEACCES`.
   - Probe 3: Socket bind (`socket.bind(('0.0.0.0', 0))`) $\to$ must fail with `PermissionError`.
2. **Filesystem Confinement Probes:**
   - Probe 4: Attempt file creation in repository root $\to$ must fail with `PermissionError`.
   - Probe 5: Attempt file modification in `C:\Windows` or User profile $\to$ must fail with `PermissionError`.
   - Probe 6: File write in designated scratch directory $\to$ must succeed, with scratch directory cleaned upon exit.
3. **Mathematical Soundness Probe:**
   - Re-run all 246 baseline mathematical tests through the AppContainer-confined worker to prove 100% parity with direct evaluation.
