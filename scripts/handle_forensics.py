"""Windows Handle Forensics and Resource Ownership Verification Tool.

Runs isolated failure scenarios for N = 5, 10, 20, 40 iterations and records
deterministic Win32 handle metrics, quarantine settlement states, and handle deltas.
"""

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mke_product.worker.controller import WorkerController
from mke_product.worker.win32 import get_current_process_handle_count

SCHEMA_VERSION = "mke.p02a.v1"


def run_scenario_a_normal(n: int) -> Dict[str, Any]:
    """Scenario A: N normal requests (control baseline)."""
    controller = WorkerController(timeout_sec=2.0)
    # Warmup
    controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
    time.sleep(0.1)
    controller.settle_quarantine(timeout=0.2)
    gc.collect()

    h_baseline = get_current_process_handle_count()

    for _ in range(n):
        res = controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
        assert res["outcome"] == "SUCCESS", f"Expected SUCCESS, got {res}"

    time.sleep(0.1)
    controller.settle_quarantine(timeout=0.2)
    gc.collect()

    h_final = get_current_process_handle_count()
    delta = h_final - h_baseline
    recs = controller.get_quarantine_records()
    active_q = controller.get_active_quarantine_count()

    return {
        "scenario": "Scenario A: Normal Requests (Control)",
        "iterations": n,
        "baseline_handles": h_baseline,
        "final_handles": h_final,
        "net_delta": delta,
        "active_quarantine_count": active_q,
        "total_quarantine_records": len(recs),
        "all_records_settled": all(r["settled"] for r in recs) if recs else True,
    }


def run_scenario_b_write_timeout_quarantine(n: int) -> Dict[str, Any]:
    """Scenario B: N write timeouts with cancellation and quarantine."""
    controller = WorkerController(
        timeout_sec=0.15,
        _stdin_pipe_buffer_size=1024,
    )
    # Warmup
    controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
    time.sleep(0.1)
    controller.settle_quarantine(timeout=0.2)
    gc.collect()

    h_baseline = get_current_process_handle_count()

    for _ in range(n):
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _inject_writer_join_timeout=True,
        )
        assert res["status"] == "WORKER_TIMEOUT", f"Expected WORKER_TIMEOUT, got {res}"

    # Allow all writer threads to complete their injected sleep(0.3)
    time.sleep(0.5)
    settled_count = controller.settle_quarantine(timeout=0.5)
    gc.collect()

    h_final = get_current_process_handle_count()
    delta = h_final - h_baseline
    recs = controller.get_quarantine_records()
    active_q = controller.get_active_quarantine_count()

    return {
        "scenario": "Scenario B: Write Timeouts & Quarantine",
        "iterations": n,
        "baseline_handles": h_baseline,
        "final_handles": h_final,
        "net_delta": delta,
        "settled_count": settled_count,
        "active_quarantine_count": active_q,
        "total_quarantine_records": len(recs),
        "all_records_settled": all(r["settled"] for r in recs),
        "all_handles_confirmed_closed": all(r["handle_closed"] and r["thread_handle_closed"] for r in recs),
    }


def run_scenario_c_setup_timeout_hang(n: int) -> Dict[str, Any]:
    """Scenario C: N setup timeouts / hangs."""
    controller = WorkerController(timeout_sec=1.0)
    # Warmup
    controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
    time.sleep(0.1)
    controller.settle_quarantine(timeout=0.2)
    gc.collect()

    h_baseline = get_current_process_handle_count()

    for _ in range(n):
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"},
            _inject_writer_setup_hang=True,
        )
        assert res["status"] == "WORKER_STARTUP_FAILURE", f"Expected WORKER_STARTUP_FAILURE, got {res}"

    # Allow setup hang threads (sleep 2.0) to complete
    time.sleep(2.2)
    settled_count = controller.settle_quarantine(timeout=0.5)
    gc.collect()

    h_final = get_current_process_handle_count()
    delta = h_final - h_baseline
    recs = controller.get_quarantine_records()
    active_q = controller.get_active_quarantine_count()

    return {
        "scenario": "Scenario C: Setup Timeouts / Hangs",
        "iterations": n,
        "baseline_handles": h_baseline,
        "final_handles": h_final,
        "net_delta": delta,
        "settled_count": settled_count,
        "active_quarantine_count": active_q,
        "total_quarantine_records": len(recs),
        "all_records_settled": all(r["settled"] for r in recs),
        "all_handles_confirmed_closed": all(r["handle_closed"] and r["thread_handle_closed"] for r in recs),
    }


def run_scenario_d_late_duplication(n: int) -> Dict[str, Any]:
    """Scenario D: N late duplication completions after timeout."""
    controller = WorkerController(
        timeout_sec=0.15,
        _stdin_pipe_buffer_size=1024,
    )
    # Warmup
    controller.execute_request({"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"})
    time.sleep(0.1)
    controller.settle_quarantine(timeout=0.2)
    gc.collect()

    h_baseline = get_current_process_handle_count()

    for _ in range(n):
        res = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=" + "1" * 4000},
            _worker_cmd=f'"{sys.executable}" -c "import time; time.sleep(5)"',
            _inject_late_duplicate_handle=True,
        )
        assert res["status"] == "WORKER_TIMEOUT", f"Expected WORKER_TIMEOUT, got {res}"

    time.sleep(0.5)
    settled_count = controller.settle_quarantine(timeout=0.5)
    gc.collect()

    h_final = get_current_process_handle_count()
    delta = h_final - h_baseline
    recs = controller.get_quarantine_records()
    active_q = controller.get_active_quarantine_count()

    return {
        "scenario": "Scenario D: Late Duplication Completions",
        "iterations": n,
        "baseline_handles": h_baseline,
        "final_handles": h_final,
        "net_delta": delta,
        "settled_count": settled_count,
        "active_quarantine_count": active_q,
        "total_quarantine_records": len(recs),
        "all_records_settled": all(r["settled"] for r in recs) if recs else True,
        "all_handles_confirmed_closed": all(r["handle_closed"] and r["thread_handle_closed"] for r in recs) if recs else True,
    }


def main():
    print("=" * 70)
    print("MKE S4-B1-R7: WINDOWS HANDLE FORENSICS & RESOURCE OWNERSHIP")
    print("=" * 70)

    test_matrix = [
        ("Scenario A (Normal Control)", run_scenario_a_normal, [5, 10, 20, 40]),
        ("Scenario B (Write Timeouts & Quarantine)", run_scenario_b_write_timeout_quarantine, [5, 10, 20, 40]),
        ("Scenario C (Setup Timeouts & Hangs)", run_scenario_c_setup_timeout_hang, [5, 10]),
        ("Scenario D (Late Duplication)", run_scenario_d_late_duplication, [5, 10, 20]),
    ]

    all_results: List[Dict[str, Any]] = []

    for name, runner, n_list in test_matrix:
        print(f"\n--- Running {name} ---")
        for n in n_list:
            t0 = time.monotonic()
            result = runner(n)
            elapsed = time.monotonic() - t0
            result["elapsed_sec"] = round(elapsed, 3)
            all_results.append(result)
            print(
                f"  N={n:2d} | Baseline: {result['baseline_handles']:3d} | "
                f"Final: {result['final_handles']:3d} | Delta: {result['net_delta']:+2d} | "
                f"ActiveQ: {result['active_quarantine_count']} | Elapsed: {elapsed:.2f}s"
            )

    print("\n" + "=" * 70)
    print("RAW JSON TELEMETRY OUTPUT:")
    print("=" * 70)
    print(json.dumps(all_results, indent=2))

    # Save to forensics output file
    output_path = Path(__file__).resolve().parents[1] / "handle_forensics_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved forensics results to {output_path}")


if __name__ == "__main__":
    main()
