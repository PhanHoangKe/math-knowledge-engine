# MKE PRODUCT-02A-S4-B2 Preflight Architecture & Isolation Proposal

**Milestone:** Windows Filesystem Confinement & Outbound Network Denial (S4-B2 Preflight Design)  
**Status:** Read-Only Architectural Proposal (No implementation code changed)  
**Target Milestone:** S4-B2  
**Target Platform:** Windows 10 / 11 (64-bit AMD64)  
**Author:** Anty (Antigravity)  
**Chief Architect & Auditor:** ChatGPT  
**Approval Authority:** Project Owner (Kế Phan Hoàng)  

---

## 1. Executive Summary & Design Goals

The objective of milestone **PRODUCT-02A-S4-B2** is to establish defense-in-depth isolation around disposable Windows worker processes created by `WorkerController`:
1. **Filesystem Confinement:** Restrict the worker's filesystem access so it cannot write to repository files, system directories, user profiles, or arbitrary disks, restricting write operations exclusively to an ephemeral per-request scratch directory.
2. **Outbound Network Denial:** Completely deny worker processes the ability to establish TCP/UDP connections, bind local listening sockets, or communicate over loopback/LAN/WAN.
3. **Non-Administrative Feasibility:** Implement isolation mechanisms that function under a standard, non-elevated user token (avoiding `SeDebugPrivilege` or Administrator rights).

---

## 2. OS Security Enforcement Mechanisms

Three Windows containment architectures were evaluated for non-administrative feasibility and isolation strength:

| Mechanism | Description | Non-Admin Viable? | Filesystem Strength | Network Denial Strength | Worker Compatibility |
|---|---|:---:|:---:|:---:|:---:|
| **Option 1: Windows AppContainer (`SECURITY_APP_CONTAINER`)** | Low-privilege sandbox profile with explicit capability grants via `CreateAppContainerProfile` and `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES`. | **Yes** (Standard User can create ephemeral AppContainers) | **High** (Default deny for all files except AppContainer profile directory and explicit package grants) | **High** (Zero network capabilities granted $\to$ complete network denial at TCP/IP stack level) | **High** (Runs standard Python CPython runtime with read grants on Python DLLs) |
| **Option 2: Restricted Token (`CreateRestrictedToken`)** | Strips privileges and groups (e.g. `LUA_TOKEN`, `DISABLE_MAX_PRIVILEGE`, Restricted SIDs). | **Yes** | **Medium** (Relies on DACLs; access granted to `Everyone` remains readable) | **Low** (Cannot block Winsock TCP connect without filtering drivers) | **High** |
| **Option 3: Windows Filtering Platform (WFP) Callouts** | Kernel driver filtering TCP/UDP packets by Process ID. | **No** (Requires Administrator & Kernel Driver Signature) | N/A | **High** | **Medium** |

### Selected Architecture: Windows AppContainer Profile
**AppContainer** is selected as the primary S4-B2 containment mechanism because:
- It requires **no administrator privileges** to create and manage ephemeral user profiles.
- By default, an AppContainer process has **zero network access** (omitting `internetClient`, `internetClientServer`, and `privateNetworkClientServer` capabilities causes the Windows kernel to reject all socket connections at the transport layer).
- By default, an AppContainer process has **zero write access** to the filesystem outside its registered per-request package folder.

---

## 3. Required Permissions & Token Construction

1. **Token Hierarchy:**
   - The parent process (`WorkerController`) runs under the standard non-elevated user token.
   - For each request, the controller generates a unique ephemeral AppContainer profile:
     ```python
     app_container_name = f"MKE.Worker.S4B2.{request_id}"
     # CreateAppContainerProfile(app_container_name, displayName, description, capabilities, 0, byref(sid))
     ```
2. **Capability Set:**
   - `dwCapabilityCount = 0` (Strictly empty capability array).
   - Omitting all network capabilities (`internetClient`, etc.) guarantees hard OS-level blocking of Winsock `socket()`, `connect()`, and `bind()`.
3. **Process Attribute Integration:**
   - In `STARTUPINFOEXW`, `UpdateProcThreadAttribute` is configured with `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES` pointing to a `SECURITY_CAPABILITIES` structure holding the AppContainer SID.

---

## 4. Filesystem Access Boundaries

### 4.1 Access Control Matrix

| Path / Directory | Access Mode | Enforcement Mechanism |
|---|---|---|
| **Python Runtime (`sys.executable` directory)** | **Read & Execute Only** | `ALL_APPLICATION_PACKAGES` read DACL |
| **MKE Source Tree (`src/mke_product`)** | **Read Only** | `ALL_APPLICATION_PACKAGES` read DACL |
| **Ephemeral Request Scratch Dir (`tmp/worker_<req_id>`)** | **Read & Write** | AppContainer SID explicit Full Control DACL |
| **Repository Root (`.git/`, tests, specs)** | **No Access / Deny** | Default AppContainer boundary (no package grant) |
| **User Profile (`C:\Users\...`)** | **No Access / Deny** | Default AppContainer boundary |
| **System Drives (`C:\Windows`, etc.)** | **Read Only (OS DLLs)** | Default AppContainer `ALL_APPLICATION_PACKAGES` read |

### 4.2 Ephemeral Scratch Directory Lifecycle
1. Controller creates temporary directory `d:\mke-product\.tmp\scratch_<req_id>`.
2. Controller assigns explicit `GENERIC_ALL` DACL to the worker's AppContainer SID.
3. Worker sets `TMP`, `TEMP`, and `PYTHONPYCACHEPREFIX` environment variables to this directory.
4. Upon request completion, controller destroys the scratch directory and revokes the AppContainer profile via `DeleteAppContainerProfile`.

---

## 5. Network Denial Strategy

1. **Zero-Capability AppContainer Enforcement:**
   - The Windows networking subsystem enforces AppContainer capability checks in `afd.sys` and `tcpip.sys`.
   - Any attempt by Python worker code to execute `urllib.request.urlopen()`, `socket.create_connection()`, or `socket.bind()` fails with `WSAEACCES` (Win32 Error `10013` / *Permission Denied*) or `WSAENETUNREACH`.
2. **Loopback & Named Pipe Protection:**
   - Loopback network access (`127.0.0.1`, `::1`) is denied by default in AppContainers.
   - Named pipes created outside the AppContainer are inaccessible unless explicitly granted to `ALL_APPLICATION_PACKAGES` or the specific container SID. The controller's anonymous stdio pipes remain accessible via `PROC_THREAD_ATTRIBUTE_HANDLE_LIST`.

---

## 6. Worker Compatibility & Runtime Requirements

1. **Standard Python CPython 3.10+ Compatibility:**
   - CPython loads required C runtime DLLs (`ucrtbase.dll`, `vcruntime140.dll`, `python310.dll`) directly from system and Python install directories.
   - Standard library modules used by MKE mathematical kernel (`json`, `sys`, `struct`, `re`, `pathlib`) require zero network and zero persistent disk writes.
2. **Stdio IPC Continuity:**
   - Anonymous pipes inherited via `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` operate identically under AppContainer processes, preserving the exact S4-B1 length-prefixed protocol.

---

## 7. Security Limitations & Threat Model

1. **Non-Administrative Boundary:**
   - AppContainer is a strong user-mode sandbox (used by Chromium and Windows Sandbox). However, kernel-level local privilege escalation (LPE) vulnerabilities in Windows could theoretically allow sandbox escape. MKE mitigates this by restricting worker code exclusively to trusted deterministic math evaluation.
2. **Local Denial of Service:**
   - CPU and memory exhaustion remain constrained by the S4-B1 Windows Job Object limits (`JOB_OBJECT_LIMIT_PROCESS_MEMORY`, `JOB_OBJECT_LIMIT_JOB_MEMORY`).

---

## 8. Independent Verification Strategy for S4-B2

The S4-B2 test suite will include deterministic adversarial probes executing inside the sandboxed worker:

1. **Network Denial Probes:**
   - Probe 1: TCP connect to external IP (`8.8.8.8:53`) $\to$ must fail with `PermissionError` / `WSAEACCES`.
   - Probe 2: TCP connect to local loopback (`127.0.0.1:8080`) $\to$ must fail with `PermissionError` / `WSAEACCES`.
   - Probe 3: Socket bind (`socket.bind(('0.0.0.0', 0))`) $\to$ must fail with `PermissionError`.
2. **Filesystem Confinement Probes:**
   - Probe 4: Attempt file creation in repository root $\to$ must fail with `PermissionError`.
   - Probe 5: Attempt file modification in `C:\Windows` or User profile $\to$ must fail with `PermissionError`.
   - Probe 6: File write in designated scratch directory $\to$ must succeed, with scratch directory cleaned upon exit.
3. **Mathematical Soundness Probe:**
   - Re-run all 246 baseline mathematical tests through the AppContainer-confined worker to prove 100% parity with direct evaluation.
