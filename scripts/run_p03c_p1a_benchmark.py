"""Runner script for P03C-P1A Elementary Algebra Benchmark."""

import json
import os
import sys
import time

# Ensure src/ and root are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mke_product.cas.contracts import ExecutionRequest, OperationType
from mke_product.cas.router import CASRouter
from scripts.benchmark_scoring import evaluate_benchmark_response, BenchmarkOutcome


def run_benchmark():
    benchmark_path = os.path.join(os.path.dirname(__file__), "..", "tests", "benchmarks", "p03c_p1a_algebra_benchmark.json")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    router = CASRouter()
    items = bench_data["items"]
    results = []
    total_score = 0.0
    passed_count = 0

    print(f"Running P03C-P1A Benchmark: {len(items)} items...")

    for item in items:
        input_text = item["input_text"]
        # Format problem for evaluate_benchmark_response
        problem_spec = {
            "id": item["id"],
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": item["ground_truth"]["solution_set"],
                "extraneous_roots": item["ground_truth"].get("extraneous_roots", []),
            }
        }

        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression=input_text,
            options={"in_process": True},
        )
        t0 = time.monotonic()
        res = router.execute(req)
        dur = time.monotonic() - t0

        engine_response = res.to_dict()
        eval_result = evaluate_benchmark_response(problem_spec, res.status.value, engine_response)

        is_correct = eval_result["matched_ground_truth"]
        score = 1.0 if is_correct else 0.0
        total_score += score
        if is_correct:
            passed_count += 1

        print(f"[{item['id']}] Status: {res.status.value} | Outcome: {eval_result['outcome'].value if hasattr(eval_result['outcome'], 'value') else eval_result['outcome']} | Correct: {is_correct} | Res: {res.symbolic_result} | Details: {eval_result['details']}")

        results.append({
            "item_id": item["id"],
            "archetype_id": item["archetype_id"],
            "input_text": input_text,
            "engine_status": res.status.value,
            "symbolic_result": res.symbolic_result,
            "solution_set": res.solution_set,
            "extraneous_roots_eliminated": res.verification_evidence.get("extraneous_roots", []) if res.verification_evidence else [],
            "ground_truth": item["ground_truth"],
            "eval_result": {
                "outcome": eval_result["outcome"].value if hasattr(eval_result["outcome"], "value") else str(eval_result["outcome"]),
                "matched_ground_truth": eval_result["matched_ground_truth"],
                "details": eval_result["details"],
                "telemetry": eval_result.get("telemetry", {}),
            },
            "duration_sec": round(dur, 4),
        })

    summary = {
        "benchmark_name": bench_data["benchmark_name"],
        "total_items": len(items),
        "passed_items": passed_count,
        "total_score": round(total_score, 4),
        "max_score": float(len(items)),
        "accuracy_pct": round((total_score / len(items)) * 100, 2),
        "extraneous_root_leaks": sum(1 for r in results if r["eval_result"]["outcome"] == "EXTRANEOUS_ROOT_LEAK"),
        "results": results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "evidence", "benchmark")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "p03c_p1a_algebra_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n==================================================")
    print(f"P03C-P1A Benchmark Completed!")
    print(f"Passed: {passed_count}/{len(items)} ({summary['accuracy_pct']}%)")
    print(f"Extraneous Root Leaks: {summary['extraneous_root_leaks']}")
    print(f"Evidence written to: {out_file}")
    print(f"==================================================")

    return summary


if __name__ == "__main__":
    run_benchmark()
