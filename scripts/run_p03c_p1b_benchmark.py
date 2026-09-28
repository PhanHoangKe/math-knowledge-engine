"""
P03C-P1B Transcendental Functions, Calculus & Equations Benchmark Runner.
Executes the product engine across all 32 authentic Grade 11-12 transcendental problems,
evaluates exact mathematical equivalence, detects extraneous roots, and outputs evidence.
"""

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from mke_product.cas.cas_parser import is_top_level_system
from mke_product.cas.contracts import (
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    OperationType,
)
from mke_product.cas.router import EngineRouter
from scripts.benchmark_scoring import (
    BenchmarkOutcome,
    evaluate_benchmark_response,
)

BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "p03c_p1b_transcendental_benchmark.json"
EVIDENCE_DIR = REPO_ROOT / "evidence" / "benchmark"
RESULTS_FILE = EVIDENCE_DIR / "p03c_p1b_benchmark_results.json"
REPORT_FILE = EVIDENCE_DIR / "P03C_P1B_BENCHMARK_REPORT.md"


def determine_p1b_operation(problem: dict) -> tuple[OperationType, str]:
    """Deterministically map benchmark problem to OperationType."""
    arch = problem.get("archetype_id", "")
    raw_expr = problem.get("problem_latex") or ""

    if arch.startswith("ARCH-11.5") or "đạo hàm" in problem.get("problem_text_vi", "").lower():
        clean_expr = raw_expr
        if clean_expr.startswith("y = ") or clean_expr.startswith("f(x) = "):
            clean_expr = clean_expr.split("=", 1)[1].strip()
        return OperationType.DIFFERENTIATE, clean_expr

    if "=" in raw_expr:
        return OperationType.SOLVE, raw_expr

    return OperationType.SIMPLIFY, raw_expr


def run_p1b_benchmark():
    print("================================================================================")
    print("        MKE P03C-P1B TRANSCENDENTAL FUNCTIONS & CALCULUS BENCHMARK")
    print("================================================================================")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    if not BENCHMARK_FILE.exists():
        print(f"[ERROR] Benchmark file not found: {BENCHMARK_FILE}")
        sys.exit(1)

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    problems = dataset.get("problems", [])
    print(f"Loaded {len(problems)} genuine transcendental problems from {BENCHMARK_FILE.name}")

    router = EngineRouter()
    results = []

    stats = {
        "total_problems": len(problems),
        "passed": 0,
        "failed": 0,
        "by_archetype": {},
    }

    start_time = time.monotonic()

    for idx, prob in enumerate(problems, 1):
        pid = prob["problem_id"]
        arch = prob.get("archetype_id", "UNKNOWN")
        gt = prob.get("ground_truth", {})

        if arch not in stats["by_archetype"]:
            stats["by_archetype"][arch] = {"total": 0, "passed": 0}
        stats["by_archetype"][arch]["total"] += 1

        op, clean_expr = determine_p1b_operation(prob)

        req = ExecutionRequest(
            operation=op,
            raw_input=clean_expr,
            variable="x",
        )

        resp = router.route_and_execute(req)
        engine_status_str = resp.mathematical_status.value if hasattr(resp.mathematical_status, "value") else str(resp.mathematical_status)
        raw_resp_dict = resp.to_dict() if hasattr(resp, "to_dict") else {
            "symbolic_result": resp.symbolic_result,
            "latex_output": resp.latex_output,
            "verification_evidence": resp.verification_evidence,
            "error_message": resp.error_message,
        }
        eval_res = evaluate_benchmark_response(prob, engine_status_str, raw_resp_dict)

        outcome_val = eval_res.get("outcome")
        is_passed = (outcome_val == BenchmarkOutcome.SUCCESS or outcome_val == "SUCCESS")
        if is_passed:
            stats["passed"] += 1
            stats["by_archetype"][arch]["passed"] += 1
        else:
            stats["failed"] += 1

        outcome_name = outcome_val.value if hasattr(outcome_val, "value") else str(outcome_val)
        status_str = "[PASS]" if is_passed else f"[{outcome_name}]"
        print(f"[{idx:02d}/{len(problems):02d}] {pid} ({arch}): {status_str} -> Got: {resp.symbolic_result} (Expected: {gt.get('symbolic_canonical')})")

        results.append({
            "problem_id": pid,
            "archetype_id": arch,
            "operation": op.value,
            "input_latex": prob.get("problem_latex"),
            "ground_truth": gt,
            "engine_status": engine_status_str,
            "symbolic_result": resp.symbolic_result,
            "outcome": outcome_name,
            "detail": eval_res.get("details", ""),
            "duration_sec": resp.execution_duration_sec,
            "verification_evidence": resp.verification_evidence,
        })

    duration_total = time.monotonic() - start_time
    accuracy = (stats["passed"] / stats["total_problems"]) * 100.0 if stats["total_problems"] > 0 else 0.0

    print("================================================================================")
    print(f"BENCHMARK COMPLETE: {stats['passed']}/{stats['total_problems']} Passed ({accuracy:.1f}%) in {duration_total:.2f}s")
    print("================================================================================")

    # Save JSON results
    output_data = {
        "benchmark_id": "P03C_P1B_TRANSCENDENTAL_BENCHMARK",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_problems": stats["total_problems"],
        "passed": stats["passed"],
        "failed": stats["failed"],
        "accuracy_pct": accuracy,
        "duration_sec": duration_total,
        "by_archetype": stats["by_archetype"],
        "results": results,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {RESULTS_FILE}")

    # Generate Markdown report
    md_lines = [
        "# MKE P03C-P1B Transcendental Solver Benchmark Report",
        "",
        f"- **Benchmark ID:** `P03C_P1B_TRANSCENDENTAL_BENCHMARK`",
        f"- **Timestamp:** {output_data['timestamp_utc']}",
        f"- **Total Problems:** {stats['total_problems']}",
        f"- **Passed:** {stats['passed']} ({accuracy:.1f}%)",
        f"- **Failed:** {stats['failed']}",
        f"- **Duration:** {duration_total:.2f}s",
        "",
        "## Summary by Archetype",
        "",
        "| Archetype ID | Category | Total | Passed | Accuracy |",
        "|:---|:---|:---:|:---:|:---:|",
    ]

    for arch, a_stats in sorted(stats["by_archetype"].items()):
        a_acc = (a_stats["passed"] / a_stats["total"]) * 100.0 if a_stats["total"] > 0 else 0.0
        md_lines.append(f"| `{arch}` | {arch.split('-')[1] if '-' in arch else 'General'} | {a_stats['total']} | {a_stats['passed']} | {a_acc:.1f}% |")

    md_lines.extend([
        "",
        "## Problem Execution Details",
        "",
        "| ID | Archetype | Operation | Input LaTeX | Engine Result | Expected | Outcome |",
        "|:---|:---|:---|:---|:---|:---|:---|",
    ])

    for r in results:
        res_disp = str(r["symbolic_result"]).replace("|", "\\|")
        exp_disp = str(r["ground_truth"].get("symbolic_canonical")).replace("|", "\\|")
        inp_disp = f"`{r['input_latex']}`"
        md_lines.append(f"| `{r['problem_id']}` | `{r['archetype_id']}` | `{r['operation']}` | {inp_disp} | `{res_disp}` | `{exp_disp}` | **{r['outcome']}** |")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved report to {REPORT_FILE}")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(run_p1b_benchmark())
