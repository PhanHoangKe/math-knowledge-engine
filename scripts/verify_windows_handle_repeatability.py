"""Dedicated Windows Handle Telemetry & Repeatability Verification Script."""

import gc
import json
import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mke_product.protocol.schema import SCHEMA_VERSION
from mke_product.worker.constants import WORKER_TIMEOUT
from mke_product.worker.controller import WorkerController
from mke_product.worker.win32 import get_current_process_handle_count

def run_repeatability_verification(iterations: int = 20):
    print(f"[*] Starting Windows Handle Telemetry & Repeatability Verification ({iterations} iterations)...")
    controller = WorkerController(timeout_sec=0.2, _stdin_pipe_buffer_size=1024)
    
    # Warmup
    controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
    time.sleep(0.5)
    controller.settle_quarantine(timeout=0.5)
    gc.collect()

    initial_handles = get_current_process_handle_count()
    print(f"[*] Initial baseline process handle count: {initial_handles}")

    telemetry = []
    all_passed = True

    for i in range(1, iterations + 1):
        h_start = get_current_process_handle_count()

        # Req 1: timeout with quarantined handle
        res1 = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _inject_writer_join_timeout=True,
        )
        assert res1["status"] == WORKER_TIMEOUT, f"Req 1 failed status: {res1['status']}"
        assert controller._last_write_info["handle_quarantined"] is True

        # Allow writer thread to finish sleeping
        time.sleep(0.4)

        # Req 2: normal solve on same controller instance
        res2 = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"},
            timeout_sec=2.0,
        )
        assert res2["outcome"] == "SUCCESS", f"Req 2 failed outcome: {res2.get('outcome')}"
        assert controller._last_write_info["handle_quarantined"] is False

        # Settle quarantine and collect garbage
        time.sleep(0.5)
        controller.settle_quarantine(timeout=0.5)
        gc.collect()

        h_end = get_current_process_handle_count()
        delta = h_end - h_start
        active_q = controller.get_active_quarantine_count()
        unresolved = controller.get_unresolved_count()

        passed = (delta <= 0) and (active_q == 0) and (unresolved == 0)
        if not passed:
            all_passed = False

        record = {
            "iteration": i,
            "handles_start": h_start,
            "handles_end": h_end,
            "delta": delta,
            "active_quarantine": active_q,
            "unresolved_count": unresolved,
            "passed": passed,
        }
        telemetry.append(record)
        print(f"  Iteration {i:02d}: start={h_start}, end={h_end}, delta={delta:+d}, active_q={active_q}, unresolved={unresolved} -> {'PASS' if passed else 'FAIL'}")

    final_handles = get_current_process_handle_count()
    net_delta = final_handles - initial_handles
    print(f"[*] Final process handle count: {final_handles} (Net Delta across {iterations} iterations: {net_delta:+d})")
    print(f"[*] Overall Repeatability Result: {'PASS' if all_passed and net_delta <= 0 else 'FAIL'}")

    # Output JSON summary
    summary = {
        "milestone": "PRODUCT-03B-FINAL-RECONCILIATION",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "iterations": iterations,
        "initial_handles": initial_handles,
        "final_handles": final_handles,
        "net_delta": net_delta,
        "all_passed": all_passed and (net_delta <= 0),
        "telemetry": telemetry,
    }
    
    out_dir = Path(__file__).resolve().parent.parent / "evidence" / "p03b_final"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "windows_handle_repeatability_telemetry.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[*] Telemetry saved to {out_file}")

    return 0 if (all_passed and net_delta <= 0) else 1


if __name__ == "__main__":
    sys.exit(run_repeatability_verification(20))
