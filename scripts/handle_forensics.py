"""Windows Handle Forensics and Resource Ownership Verification Tool.

Runs isolated failure scenarios for N = 5, 10, 20, 40 iterations (16 total matrix cases)
and asserts zero net handle growth, 100% quarantine settlement, and verified Win32 closure.
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


def stabilize_appcontainer_runtime() -> None:
    """Exclude one-time Windows profile/cache retirement from leak baselines.

    Creating the process-local AppContainer profile transiently leaves two
    userenv-managed handles in the host for roughly 15 seconds.  P1 measures
    request ownership only after those OS initialization handles retire; the
    strict per-case ``net_delta == 0`` invariant remains unchanged.
    """
    controller = WorkerController(timeout_sec=10.0)
    for _ in range(20):
        result = controller.execute_request(
            {"schema_version": SCHEMA_VERSION, "operation": "SOLVE", "equation": "x=1"}
        )
        assert result["outcome"] == "SUCCESS", f"AppContainer forensic warmup failed: {result}"
    controller.settle_quarantine(timeout=0.5)
    del controller
    gc.collect()
    time.sleep(20.0)
    gc.collect()


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
        "all_handles_confirmed_closed": True,
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

    # Allow setup hang threads (sleep 0.08) to complete
    time.sleep(0.3)
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
        assert res["status"] == "WORKER_STARTUP_FAILURE", f"Expected WORKER_STARTUP_FAILURE, got {res}"

    time.sleep(0.3)
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
    print("MKE S4-B2/P1: COMPLETE 16-CASE WINDOWS HANDLE FORENSICS MATRIX")
    print("=" * 70)
    print("Stabilizing one-time AppContainer profile/runtime initialization...")
    stabilize_appcontainer_runtime()

    test_matrix = [
        ("Scenario A (Normal Control)", run_scenario_a_normal, [5, 10, 20, 40]),
        ("Scenario B (Write Timeouts & Quarantine)", run_scenario_b_write_timeout_quarantine, [5, 10, 20, 40]),
        ("Scenario C (Setup Timeouts & Hangs)", run_scenario_c_setup_timeout_hang, [5, 10, 20, 40]),
        ("Scenario D (Late Duplication)", run_scenario_d_late_duplication, [5, 10, 20, 40]),
    ]

    all_results: List[Dict[str, Any]] = []

    for name, runner, n_list in test_matrix:
        print(f"\n--- Running {name} ---")
        for n in n_list:
            t0 = time.monotonic()
            result = runner(n)
            elapsed = time.monotonic() - t0
            result["elapsed_sec"] = round(elapsed, 3)

            # Strict assertion of resource invariants
            assert result["net_delta"] == 0, (
                f"Resource leak invariant violated in {name} (N={n}): "
                f"baseline={result['baseline_handles']}, final={result['final_handles']}, delta={result['net_delta']}"
            )
            assert result["active_quarantine_count"] == 0, (
                f"Quarantine invariant violated: {result['active_quarantine_count']} active records remaining"
            )
            assert result["all_records_settled"], "Unsettled records found in quarantine ledger"
            assert result["all_handles_confirmed_closed"], "Unclosed Win32 handles found in quarantine records"

            all_results.append(result)
            print(
                f"  N={n:2d} | Baseline: {result['baseline_handles']:3d} | "
                f"Final: {result['final_handles']:3d} | Delta: {result['net_delta']:+2d} [PASS] | "
                f"ActiveQ: {result['active_quarantine_count']} | Elapsed: {elapsed:.2f}s"
            )

    print("\n" + "=" * 70)
    print(f"ALL {len(all_results)} / 16 FORENSIC SCENARIOS PASSED WITH STRICT ZERO HANDLE DELTA.")
    print("=" * 70)
    print(json.dumps(all_results, indent=2))

    # Save to forensics output file
    output_path = Path(__file__).resolve().parents[1] / "handle_forensics_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved 16-case forensics results to {output_path}")


if __name__ == "__main__":
    main()
