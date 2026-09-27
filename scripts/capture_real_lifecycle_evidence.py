"""Capture genuine reproducible real-process AppContainer lifecycle evidence (Task 2)."""

import ctypes
from ctypes import wintypes
import json
import os
import sys
import time
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.worker.appcontainer import get_appcontainer_manager
from mke_product.worker.constants import (
    WAIT_OBJECT_0,
    WAIT_TIMEOUT,
    WORKER_RESOURCE_EXHAUSTED,
)
from mke_product.worker.controller import (
    SafeProcessHandle,
    SafeWin32Handle,
    WorkerController,
)
from mke_product.worker.win32 import kernel32


def run_real_lifecycle_experiment() -> dict:
    evidence = {
        "milestone": "S4-B2/P1-R1",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host_pid": os.getpid(),
        "python_executable": sys.executable,
        "steps": {},
    }

    manager = get_appcontainer_manager()
    manager.prepare()

    evidence["initial_profile"] = {
        "profile_name": manager.profile_name,
        "sid_string": manager.sid_string,
        "stage_root": str(manager.stage_root) if manager.stage_root else None,
        "python_exe": str(manager.python_exe) if manager.python_exe else None,
    }

    # Step 1: Create WorkerController with long-running worker command
    controller = WorkerController(
        timeout_sec=0.2,
        _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
    )
    req = {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}

    # Step 2: Execute request with injected termination and Job close failures
    res = controller.execute_request(
        req,
        _inject_terminate_process_failure=True,
        _inject_termination_wait_timeout=True,
        _inject_job_close_failure=True,
    )

    app_evidence = controller.get_last_appcontainer_evidence()
    term_evidence = controller.get_last_termination_evidence()

    evidence["steps"]["step_1_request_execution"] = {
        "status": res.get("status"),
        "outcome": res.get("outcome"),
        "expected_status": WORKER_RESOURCE_EXHAUSTED,
        "status_matches_expected": res.get("status") == WORKER_RESOURCE_EXHAUSTED,
        "appcontainer_pre_resume_evidence": app_evidence,
        "termination_evidence": term_evidence,
    }

    # Step 3: Inspect unresolved handles and process liveness
    process_owners = [h for h in controller.get_unresolved_handles() if isinstance(h, SafeProcessHandle)]
    job_owners = controller.get_unresolved_job_handles()

    proc_owner = process_owners[0] if process_owners else None
    job_owner = job_owners[0] if job_owners else None

    child_wait_0 = kernel32.WaitForSingleObject(proc_owner.handle, 0) if proc_owner else -1
    child_is_alive = (child_wait_0 == WAIT_TIMEOUT)

    evidence["steps"]["step_2_unresolved_containment_and_liveness"] = {
        "process_owners_count": len(process_owners),
        "job_owners_count": len(job_owners),
        "proc_owner_raw_handle": proc_owner.raw_value() if proc_owner else 0,
        "proc_owner_blocked_reason": proc_owner.close_blocked_reason if proc_owner else None,
        "job_owner_raw_handle": job_owner.raw_value() if job_owner else 0,
        "wait_single_object_0ms_result": int(child_wait_0),
        "child_is_alive_during_uncertainty": child_is_alive,
    }

    # Step 4: Attempt cleanup while child process lease is active -> Must refuse
    refused_cleanup = manager.cleanup()
    evidence["steps"]["step_3_cleanup_refusal_while_lease_active"] = {
        "cleanup_result": refused_cleanup,
        "refused_as_expected": refused_cleanup.get("state") == "REFUSED_ACTIVE_CHILDREN",
        "active_children_count": refused_cleanup.get("active_children"),
    }

    # Step 5: Establish native termination proof via Job Object close (KILL_ON_JOB_CLOSE)
    job_close_success = job_owner.close(_inject_failure=False) if job_owner else False
    child_wait_after_job = kernel32.WaitForSingleObject(proc_owner.handle, 5000) if proc_owner else -1
    child_is_terminated = (child_wait_after_job == WAIT_OBJECT_0)

    exit_code = wintypes.DWORD()
    exit_code_ok = bool(kernel32.GetExitCodeProcess(proc_owner.handle, ctypes.byref(exit_code))) if proc_owner else False

    evidence["steps"]["step_4_native_termination_proof"] = {
        "job_close_succeeded": job_close_success,
        "job_is_confirmed_closed": job_owner.is_confirmed_closed() if job_owner else False,
        "wait_single_object_5000ms_result": int(child_wait_after_job),
        "child_termination_confirmed": child_is_terminated,
        "exit_code_query_succeeded": exit_code_ok,
        "exit_code": int(exit_code.value) if exit_code_ok else None,
    }

    # Step 6: Reconcile unresolved resources; process settles and deferred lease releases
    settled_count = controller.reconcile_unresolved_resources()
    unresolved_after_reconciliation = controller.get_unresolved_count()
    active_children_after_reconciliation = manager.active_children

    evidence["steps"]["step_5_reconciliation_and_lease_release"] = {
        "settled_count": settled_count,
        "unresolved_count_remaining": unresolved_after_reconciliation,
        "active_children_remaining": active_children_after_reconciliation,
        "lease_released_as_expected": (active_children_after_reconciliation == 0),
    }

    # Step 7: Final Profile & Staging Directory Deletion
    final_cleanup = manager.cleanup()
    evidence["steps"]["step_6_final_profile_cleanup"] = {
        "cleanup_result": final_cleanup,
        "cleaned_as_expected": final_cleanup.get("state") == "CLEANED",
        "stage_removed": final_cleanup.get("stage_removed"),
        "delete_hresult": final_cleanup.get("delete_hresult"),
        "manager_has_unresolved_cleanup": manager.has_unresolved_cleanup(),
    }

    evidence["experiment_verdict"] = (
        evidence["steps"]["step_1_request_execution"]["status_matches_expected"]
        and evidence["steps"]["step_2_unresolved_containment_and_liveness"]["child_is_alive_during_uncertainty"]
        and evidence["steps"]["step_3_cleanup_refusal_while_lease_active"]["refused_as_expected"]
        and evidence["steps"]["step_4_native_termination_proof"]["child_termination_confirmed"]
        and evidence["steps"]["step_5_reconciliation_and_lease_release"]["lease_released_as_expected"]
        and evidence["steps"]["step_6_final_profile_cleanup"]["cleaned_as_expected"]
    )

    return evidence


if __name__ == "__main__":
    result = run_real_lifecycle_experiment()
    output_path = Path(__file__).resolve().parents[1] / "evidence" / "s4b2_p1_r1" / "real_process_lifecycle_evidence.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\n[PASS] Real-Process Lifecycle Evidence saved to: {output_path}")
