# MKE S4-B2/P0 Experiment Evidence

## Evidence inventory

| Artifact | Purpose |
|---|---|
| `scripts/appcontainer_preflight.py` | Reproducible disposable standard-user AppContainer probe |
| `evidence/s4b2_p0/appcontainer_preflight.json` | Complete structured AppContainer observations |
| `evidence/s4b2_p0/unittest_full.log` | Complete 310-test execution log |
| `evidence/s4b2_p0/handle_forensics.log` | Complete 16-scenario forensic execution log |
| `handle_forensics_results.json` | Structured final forensic results |
| `evidence/s4b2_p0/repository_preflight.txt` | Baseline, branch, worktree, and remote record |

SHA-256 values are recorded after the final rerun in
`evidence/s4b2_p0/SHA256SUMS.txt`.

## Reproduction

From the isolated worktree on Windows:

```powershell
python scripts/appcontainer_preflight.py `
  --python-root C:\path\to\portable-python `
  --output evidence/s4b2_p0/appcontainer_preflight.json

python -m unittest discover -s tests -p "test_*.py" -v
python scripts/handle_forensics.py
```

The AppContainer probe intentionally returns a nonzero exit status when profile
creation succeeds but the combined child launch does not.

## Tracked exception evidence

Test:
`TestWindowsFailurePaths.test_combined_real_job_config_and_native_cleanup_failure_retains_owner`

The test uses real Win32 operations, not a mocked `CloseHandle` result. It
asserts the preserved configuration error, nonzero native close error,
post-failure validity, controller ownership, no retry during reconciliation,
and explicit recovery to zero unresolved owners.

## AppContainer raw observations

- Account `phanhoangke\kedep`; `is_user_an_admin=false`;
  `token_is_elevated=false`.
- Profile create/derive/delete HRESULTs: `0x00000000`.
- Returned and derived SIDs were valid and equal.
- Runtime staging copied CPython and its standard library (36,084,323 bytes).
- `icacls` successfully granted the profile SID RX on the runtime and Modify on
  the assigned write directory.
- Attribute-list initialization behaved as documented: the sizing call failed
  with error `122`, then initialization succeeded.
- `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES` update succeeded in all three
  launch attempts.
- `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` update succeeded in the combined attempt.
- All three `CreateProcessW` attempts returned Win32 error `87`: staged CPython
  security-only, staged CPython combined with one inherited handle, and native
  `C:\Windows\System32\whoami.exe` security-only.
- No child result exists. TCP/UDP fixtures were closed without a connection or
  datagram because process creation had already failed. Those fixture markers
  are not evidence of an AppContainer network denial.
- No allowed or denied output file exists because the child never ran. This is
  not evidence of an AppContainer filesystem denial.
- The disposable profile and temporary root were removed successfully.

## Interpretation boundary

The evidence supports profile lifecycle feasibility under the actual standard
user and successful construction of both requested process attributes. It does
not support a claim that AppContainer process creation, Python compatibility,
network denial, or filesystem isolation works in the proposed architecture.
Those four points remain open for P1.

## Regression acceptance record

The full log ends with:

```text
Ran 310 tests in 16.512s

OK
```

The forensic run produced 16 result objects. Every object reports
`net_delta: 0`, `active_quarantine_count: 0`,
`all_records_settled: true`, and `all_handles_confirmed_closed: true`.

## Discrepancies and limitations

- Probe B is a measured failure, not an implementation success.
- Probes C, D, and E are inconclusive because the sandboxed child never began.
- Win32 error `87` is recorded, but this preflight does not claim a proven root
  cause.
- No S4-B2 product isolation code was implemented.
- No historical workspace was modified and no independent audit approval is
  declared.
