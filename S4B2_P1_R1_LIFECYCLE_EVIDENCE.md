# MKE PRODUCT — S4-B2/P1-R1 EVIDENCE DOCUMENTATION
## Verified AppContainer Profile Lifecycle & Handle Containment Evidence

- **Milestone:** MKE PRODUCT-02A-S4-B2 / Phase 1 — Revision 1 (S4-B2/P1-R1)
- **Branch:** `product/s4b2-p1-r1-antigravity`
- **Baseline Commit:** `ea2f91c40cb0b751962467239f7bc89b66c60573`
- **Verification Environment:** Windows 11 (win32), Python 3.10
- **Status:** `PENDING INDEPENDENT AUDIT`

---

## 1. Test Suite Execution Output (322 / 322 PASS)

```text
test_check_candidate_domain_error (test_dispatcher.TestDispatcher) ... ok
test_check_candidate_invalid (test_dispatcher.TestDispatcher) ... ok
test_check_candidate_valid (test_dispatcher.TestDispatcher) ... ok
test_empty_equation (test_dispatcher.TestDispatcher) ... ok
test_equation_empty_set (test_dispatcher.TestDispatcher) ... ok
test_equation_identity (test_dispatcher.TestDispatcher) ... ok
test_equation_linear_one_variable (test_dispatcher.TestDispatcher) ... ok
test_equation_two_variables_rejected (test_dispatcher.TestDispatcher) ... ok
test_evaluate_expression_constant (test_dispatcher.TestDispatcher) ... ok
test_invalid_operation_type (test_dispatcher.TestDispatcher) ... ok
test_missing_equation_for_solve (test_dispatcher.TestDispatcher) ... ok
test_missing_operation (test_dispatcher.TestDispatcher) ... ok
test_missing_schema_version (test_dispatcher.TestDispatcher) ... ok
test_non_dict_request (test_dispatcher.TestDispatcher) ... ok
test_out_of_scope_multiplication (test_dispatcher.TestDispatcher) ... ok
test_unsupported_operation (test_dispatcher.TestDispatcher) ... ok
test_unsupported_schema_version (test_dispatcher.TestDispatcher) ... ok
...
test_cleanup_idempotent_when_already_cleaned (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_partial_preparation_failure_cleans_up_or_preserves_diagnostics (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_profile_cleanup_refuses_active_child_lease_then_recovers (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_profile_deletion_failure_preserves_sid_and_recovers (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_profile_sid_mismatch_is_rejected_while_suspended (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_real_appcontainer_process_lease_gating_and_termination_recovery (test_worker_windows.TestWindowsAppContainerIntegration)
Phase 2: Genuine AppContainer child process under Job containment with controlled termination uncertainty. ... ok
test_real_solve_worker_is_verified_before_resume (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_repeated_appcontainer_workers_do_not_accumulate_handles (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_security_capabilities_attribute_failure_is_fail_closed (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_staging_directory_deletion_failure_preserves_state_and_recovers (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_token_identity_mismatch_is_rejected_while_suspended (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
test_unresolved_cleanup_prevents_unsafe_profile_reuse (test_worker_windows.TestWindowsAppContainerIntegration) ... ok
...
test_no_double_close_on_pipe_handle (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_normal_execution_pipe_close_failure_quarantines_and_fails_closed (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_normal_write_completion_guards_active_writer (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_persistent_job_ledger_tracks_multiple_unresolved_handles (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_process_and_thread_handle_close_failure_fails_closed_and_preserves_ownership (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_quarantine_capacity_limit_rejects_requests (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_quarantined_handle_released_after_delayed_writer_eventual_exit (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_recovery_following_cleanup_failure (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_repeated_write_timeouts_no_kernel_handle_leak (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_safe_win32_handle_four_state_lifecycle (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_safe_win32_handle_native_handle_verification (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_single_request_contract_concurrent_execution_rejected (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_stdout_pipe_close_failure_fails_closed_and_preserves_ownership (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_writer_setup_hang_quarantines_handle (test_worker_windows.TestWindowsCancellationAndHandleOwnership) ... ok
test_unallowlisted_handle_not_inherited (test_worker_windows.TestWindowsHandleConfinement) ... ok
test_job_memory_limit_exceeded_aggregate (test_worker_windows.TestWindowsJobMemoryLimit) ... ok
test_job_memory_limit_isolated_control_succeeds (test_worker_windows.TestWindowsJobMemoryLimit) ... ok
test_kill_on_job_close_terminates_worker (test_worker_windows.TestWindowsKillOnJobClose) ... ok
test_check_candidate_domain_error (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_check_candidate_invalid (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_check_candidate_valid (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_contradiction_empty_set (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_domain_error_div_zero (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_identity_all_reals (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_linear_fractional_coefficients (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_linear_unique_root (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_solve_out_of_scope_nonlinear (test_worker_windows.TestWindowsMathematicalRegression) ... ok
test_process_memory_limit_exceeded_disposable_worker (test_worker_windows.TestWindowsProcessMemoryLimit) ... ok
test_process_memory_within_limit_succeeds (test_worker_windows.TestWindowsProcessMemoryLimit) ... ok
test_strict_utf8_payload_rejection (test_worker_windows.TestWindowsStrictUtf8Ipc) ... ok
test_worker_assigned_to_job_before_thread_resumed (test_worker_windows.TestWindowsSuspendedStartup) ... ok
test_worker_payload_too_large (test_worker_windows.TestWindowsTimeoutAndFraming) ... ok
test_worker_timeout_during_ipc_write_non_reading_worker (test_worker_windows.TestWindowsTimeoutAndFraming) ... ok
test_worker_timeout_fails_closed (test_worker_windows.TestWindowsTimeoutAndFraming) ... ok

----------------------------------------------------------------------
Ran 322 tests in 31.154s

OK
```

---

## 2. 16-Case Forensic Matrix Results (`handle_forensics.py`)

```text
======================================================================
MKE S4-B2/P1: COMPLETE 16-CASE WINDOWS HANDLE FORENSICS MATRIX
======================================================================
Stabilizing one-time AppContainer profile/runtime initialization...

--- Running Scenario A (Normal Control) ---
  N= 5 | Baseline: 182 | Final: 182 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 2.12s
  N=10 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 3.61s
  N=20 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 6.45s
  N=40 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 12.61s

--- Running Scenario B (Write Timeouts & Quarantine) ---
  N= 5 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 1.69s
  N=10 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 2.55s
  N=20 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 4.36s
  N=40 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 7.97s

--- Running Scenario C (Setup Timeouts & Hangs) ---
  N= 5 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 1.03s
  N=10 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 1.22s
  N=20 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 1.69s
  N=40 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 2.66s

--- Running Scenario D (Late Duplication) ---
  N= 5 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 0.62s
  N=10 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 0.67s
  N=20 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 0.74s
  N=40 | Baseline: 181 | Final: 181 | Delta: +0 [PASS] | ActiveQ: 0 | Elapsed: 0.81s

======================================================================
ALL 16 / 16 FORENSIC SCENARIOS PASSED WITH STRICT ZERO HANDLE DELTA.
======================================================================
```

---

## 3. AppContainer Worker Native Evidence Output

```json
{
  "milestone": "S4-B2/P1",
  "request": {
    "schema_version": "mke.p02a.v1",
    "operation": "SOLVE",
    "equation": "x=1"
  },
  "response": {
    "schema_version": "mke.p02a.v1",
    "operation": "SOLVE",
    "outcome": "SUCCESS",
    "status": "UNIQUE_ROOT",
    "classification": "UNIQUE_ROOT",
    "root": {
      "numerator": "1",
      "denominator": "1"
    },
    "definedness": true,
    "error": null,
    "is_provisional_evidence": true,
    "evidence": {
      "equation_str": "Equation(Variable('x'), IntegerLiteral(1))",
      "left_affine": [
        {
          "numerator": 1,
          "denominator": 1
        },
        {
          "numerator": 0,
          "denominator": 1
        }
      ],
      "right_affine": [
        {
          "numerator": 0,
          "denominator": 1
        },
        {
          "numerator": 1,
          "denominator": 1
        }
      ],
      "normalized_a": {
        "numerator": 1,
        "denominator": 1
      },
      "normalized_b": {
        "numerator": -1,
        "denominator": 1
      },
      "classification": "UNIQUE_ROOT",
      "root": {
        "numerator": 1,
        "denominator": 1
      },
      "candidate_check": {
        "status": "VALID",
        "candidate": {
          "numerator": 1,
          "denominator": 1
        },
        "is_valid": true,
        "is_defined": true,
        "left_value": {
          "numerator": 1,
          "denominator": 1
        },
        "right_value": {
          "numerator": 1,
          "denominator": 1
        },
        "error_code": null,
        "error_message": null,
        "error_span": null,
        "diagnostics": {
          "exact_equality": "True",
          "residual": "0",
          "steps_left": "1",
          "steps_right": "1",
          "total_steps": "2"
        }
      },
      "step_trace": [
        [
          "STEP_01_SCOPE_PREFLIGHT",
          "PRE_SIMPLIFICATION_IN_SCOPE"
        ],
        [
          "STEP_02_AFFINE_EXTRACTION",
          "EXACT_AFFINE_CONVERSION"
        ],
        [
          "STEP_03_EQUATION_REDUCTION",
          "NORMALIZED_AX_PLUS_B_EQUALS_ZERO"
        ],
        [
          "STEP_04_ROOT_ISOLATION",
          "SOLVE_LINEAR_UNIQUE_ROOT"
        ],
        [
          "STEP_05_INDEPENDENT_VERIFICATION",
          "S2_CHECK_CANDIDATE_VALID"
        ]
      ],
      "diagnostics": {
        "root": "1",
        "steps": "11"
      }
    }
  },
  "token_and_job": {
    "query_ok": true,
    "is_appcontainer": true,
    "sid_matches_profile": true,
    "elevated": false,
    "verified_before_resume": true,
    "query_error": 0,
    "appcontainer_sid": "S-1-15-2-995832725-2294432519-719043668-3531832658-2427251326-3186074894-2825198323",
    "accepted": true,
    "profile_name": "mke.product.worker.p1.10872.431b4920bc4e",
    "expected_sid": "S-1-15-2-995832725-2294432519-719043668-3531832658-2427251326-3186074894-2825198323",
    "job_assignment_verified": true,
    "process_was_resumed": true
  },
  "profile": {
    "name": "mke.product.worker.p1.10872.431b4920bc4e",
    "active_children_after_request": 0,
    "cleanup_with_active_lease": {
      "state": "REFUSED_ACTIVE_CHILDREN",
      "active_children": 1,
      "profile_name": "mke.product.worker.p1.10872.431b4920bc4e"
    },
    "cleanup_after_release": {
      "state": "CLEANED",
      "stage_removed": true,
      "stage_error": null,
      "delete_hresult": 0,
      "active_children": 0,
      "profile_name": "mke.product.worker.p1.10872.431b4920bc4e"
    }
  },
  "acl": {
    "command": "icacls.exe <staged-root>",
    "returncode": 0,
    "stdout": "<staged-root> S-1-15-2-995832725-2294432519-719043668-3531832658-2427251326-3186074894-2825198323:(OI)(CI)(RX)\n                                                       phanhoangke\\CodexSandboxUsers:(I)(OI)(CI)(M)\n                                                       S-1-5-21-3061253661-1315290125-2520860270-4197145290:(I)(OI)(CI)(M)\n                                                       NT AUTHORITY\\SYSTEM:(I)(OI)(CI)(F)\n                                                       BUILTIN\\Administrators:(I)(OI)(CI)(F)\n                                                       PHANHOANGKE\\kedep:(I)(OI)(CI)(F)\n\nSuccessfully processed 1 files; Failed processing 0 files",
    "stderr": "",
    "intended_sid_rights": "(OI)(CI)RX"
  }
}
```
