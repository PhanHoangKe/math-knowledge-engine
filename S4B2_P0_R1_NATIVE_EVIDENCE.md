# MKE S4-B2/P0-R1 Native Evidence

## Evidence inventory

| Artifact | Content |
|---|---|
| `scripts/appcontainer_native_diagnosis.cpp` | Independent native C++ launcher |
| `scripts/appcontainer_ctypes_diagnosis.py` | Corrected standalone ctypes launcher |
| `scripts/appcontainer_preflight.py` | P0 probe with the identified ABI omission corrected |
| `S4B2_P0_R1_NATIVE_VS_CTYPES_MATRIX.md` | Native-versus-ctypes matrix |
| `evidence/s4b2_p0_r1/native_build.log` | Compiler identity and build command |
| `evidence/s4b2_p0_r1/native_execution.jsonl` | Raw native A-D results |
| `evidence/s4b2_p0_r1/ctypes_execution_broken_layout.jsonl` | Error-87 reproduction with 96/104-byte layout |
| `evidence/s4b2_p0_r1/ctypes_execution_corrected.jsonl` | Corrected ctypes A-E results |
| `evidence/s4b2_p0_r1/repository_environment.txt` | Repository/host preflight |
| `evidence/s4b2_p0_r1/unittest_full.log` | Full regression log |
| `evidence/s4b2_p0_r1/SHA256SUMS.txt` | Integrity hashes |

## Reproduction

The host had no C++ compiler in `PATH`. Zig 0.16.0 was downloaded from the
official release page without system installation. Expected archive SHA-256:
`68659eb5f1e4eb1437a722f1dd889c5a322c9954607f5edcf337bc3684a75a7e`.

```powershell
Invoke-WebRequest https://ziglang.org/download/0.16.0/zig-x86_64-windows-0.16.0.zip -OutFile $env:TEMP\zig-x86_64-windows-0.16.0.zip
Get-FileHash -Algorithm SHA256 $env:TEMP\zig-x86_64-windows-0.16.0.zip

zig c++ scripts/appcontainer_native_diagnosis.cpp -std=c++17 -O2 -municode -Wno-nullability-completeness -luserenv -ladvapi32 -o $env:TEMP\mke-s4b2-p0-r1-native.exe
& $env:TEMP\mke-s4b2-p0-r1-native.exe

python scripts/appcontainer_ctypes_diagnosis.py
```

## Exact ABI evidence

The retained pre-fix ctypes log reports `STARTUPINFOW=96` and
`STARTUPINFOEXW=104`. A succeeds; every extended case returns error `87`.

Native and corrected ctypes both report:

```text
pointer/HANDLE size             8
STARTUPINFOW size/alignment   104 / 8
STARTUPINFOEXW size/alignment 112 / 8
SECURITY_CAPABILITIES          24 / 8
dwXCountChars offset           48
dwYCountChars offset           52
dwFillAttribute offset         56
lpAttributeList offset        104
attribute-list bytes       48 / 72
```

Native pointer types were `LPPROC_THREAD_ATTRIBUTE_LIST`,
`SECURITY_CAPABILITIES*`, `PSID`, `PSID_AND_ATTRIBUTES` and `HANDLE[1]`.
ctypes used `c_void_p` attribute storage,
`POINTER(SECURITY_CAPABILITIES)`, `c_void_p` SID,
`POINTER(SID_AND_ATTRIBUTES)` and `wintypes.HANDLE * 1`. Every corrected ctypes
attribute buffer recorded `address % 8 == 0`.

## API results

Each successful extended case recorded:

- sizing `InitializeProcThreadAttributeList`: `FALSE`, immediate error `122`;
- initialized attribute list: `TRUE`, error `0`;
- requested attribute updates: `TRUE`, error `0`;
- `CreateProcessW`: `TRUE`, error `0`.

Native and corrected ctypes B/D recorded AppContainer tokens, matching token and
profile SIDs, and no elevation. C/D recorded the allowed handle present and the
equally inheritable decoy absent. Corrected null-application-name and
explicit-current-directory controls also passed.

The launchers used `CreateAppContainerProfile`,
`InitializeProcThreadAttributeList`, `UpdateProcThreadAttribute`,
`CreateProcessW`, `OpenProcessToken`, `GetTokenInformation` and
`DuplicateHandle` directly.

## Cleanup and regression

Every temporary profile deletion returned HRESULT `0`. Children stayed
suspended, were terminated and waited, and all tracked handles and attribute
lists were released. No `whoami.exe` child remained.

No production worker code changed. The complete unittest suite was nevertheless
run as a safety check: `310/310` passed in `17.562s`. The exact output is
retained in `unittest_full.log`.

This evidence supports the P1 gate only. It does not establish full runtime,
filesystem, or network isolation.
