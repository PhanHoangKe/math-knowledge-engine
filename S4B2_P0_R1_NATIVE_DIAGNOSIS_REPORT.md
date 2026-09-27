# MKE S4-B2/P0-R1 Native AppContainer Launch Diagnosis

## Decision

**GO for S4-B2/P1 design work using the existing Job Object plus explicit
inherited-handle architecture, subject to later isolation tests.**

This is not full S4-B2 acceptance and is not independent audit approval. No
production worker behavior was changed.

## Exact root cause

The error `CreateProcessW -> FALSE / GetLastError() == 87` was caused by an
incorrect Python ctypes ABI definition of `STARTUPINFOW`. The P0 definition
omitted:

```python
("dwYCountChars", wintypes.DWORD)
```

That missing `DWORD` shifted every subsequent field:

| Layout | `STARTUPINFOW` | `STARTUPINFOEXW` | `lpAttributeList` offset |
|---|---:|---:|---:|
| Native Windows headers | 104 | 112 | 104 |
| Broken P0 ctypes | 96 | 104 | 96 |
| Corrected ctypes | 104 | 112 | 104 |

The broken launcher set `StartupInfo.cb` to `104`, the size of its malformed
`STARTUPINFOEXW`. Windows expects `112` and `lpAttributeList` at offset `104`.
Normal creation succeeded because it did not use the extended tail. Every case
with `EXTENDED_STARTUPINFO_PRESENT` failed with error `87`. Restoring
`dwYCountChars` made the same calls succeed.

This reproducibly excludes the alternatives tested:

- native and corrected ctypes use pointer size/alignment `8`;
- `SECURITY_CAPABILITIES` is size `24`, alignment `8` in both;
- the profile SID was valid and alive through `CreateProcessW`;
- attribute sizing returned documented error `122`, then initialization passed;
- ctypes attribute storage was 8-byte aligned;
- `bInheritHandles=TRUE` was used only with the handle list;
- `CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT` succeeded;
- parent Job membership did not prevent launch;
- explicit/null application name and explicit/null current directory all
  succeeded after correcting the ABI.

## Repository and environment

- Accepted baseline: `16162ab56028c6f83d70579cab6001f6b3b4c4aa`
- Starting R1 commit: `415d0cf4ef09fcc1c4637e65f7cf5ff230466834`
- Branch: `product/s4b2-preflight`
- Managed worktree:
  `C:\Users\kedep\.codex\worktrees\s4b1-native-failure\Math Knowledge Engine`
- Windows 11 `10.0.26200.0`
- Python `3.12.14`, 64-bit AMD64, MSC v.1944
- Zig `0.16.0` / Clang `21.1.0` / `x86_64-unknown-windows-gnu`
- Compiler archive SHA-256:
  `68659eb5f1e4eb1437a722f1dd889c5a322c9954607f5edcf337bc3684a75a7e`
- Account `PHANHOANGKE\kedep`; administrator/elevated `false/false`
- Parent AppContainer `false`; parent Job membership `true`

The historical workspace at `D:\Math Knowledge Engine` was not modified.

## Controlled experiments

All tests used `C:\Windows\System32\whoami.exe`. Children were created
suspended, inspected via process-token and handle APIs, terminated, waited, and
closed.

| Test | Native C++ | Corrected ctypes | Security observation |
|---|---|---|---|
| A. Normal `CreateProcessW` | PASS | PASS | Non-AppContainer, non-elevated |
| B. AppContainer only | PASS | PASS | `TokenIsAppContainer=true`; SID match; non-elevated |
| C. Handle list only | PASS | PASS | Allowed event inherited; inheritable decoy excluded |
| D. Combined attributes | PASS | PASS | Genuine AppContainer; SID match; allowlist enforced |
| E. ctypes parity | N/A | PASS | ABI, attributes, token, and handle results match native |

For B/D, `OpenProcessToken` and `GetTokenInformation` verified
`TokenIsAppContainer`, `TokenAppContainerSid`, and `TokenElevation`. Process
creation alone was not treated as isolation proof.

For C/D, the parent created two inheritable events but put only one in
`PROC_THREAD_ATTRIBUTE_HANDLE_LIST`. `DuplicateHandle` from the suspended child
confirmed that the allowlisted handle existed and the decoy did not.

## Cleanup and scope

- Profile creation and deletion returned success in both launchers.
- Process, thread, token, event, duplicate, and attribute-list resources were
  released.
- No broad filesystem ACL grant was made.
- No MKE worker was used.
- No production source file changed.
- The earlier standalone P0 probe received only the same one-field ABI fix.
- Full safety regression: `310/310` tests passed in `17.562s`.
- Python-runtime, filesystem, and network isolation remain outside R1.

## Architectural recommendation

Proceed to P1 with the existing architecture:

1. Keep Job Object containment and strict handle ownership.
2. Add `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES` beside the explicit handle
   list.
3. Keep `bInheritHandles=TRUE` only with the allowlist and retain negative
   decoy-handle tests.
4. Verify the child token before resume and fail closed on mismatch.
5. Complete the deferred runtime, ACL, filesystem, TCP, and UDP tests before
   declaring S4-B2 complete.

`Experimental_CreateProcessInSandbox` is unnecessary for this failure. It
remains experimental, lacks a public header, and documents `inheritHandles` as
unsupported and required to be `FALSE`. It would require a separately approved
IPC redesign.

## Official references

- [Launch an AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer)
- [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
- [SECURITY_CAPABILITIES](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_capabilities)
- [STARTUPINFOEXW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-startupinfoexw)
- [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)
- [Experimental Create Process in Sandbox](https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox)
