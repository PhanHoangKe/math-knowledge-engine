"""
MKE THPT 40-Problem Pilot Diagnostic Benchmark Runner.
Executes the frozen Product 03B engine across all 40 authentic pilot benchmark problems,
applies normalized mathematical scoring, detects extraneous root leaks, and generates
transparent, machine-readable evidence.
"""

import json
import re
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

BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "thpt_pilot_benchmark_v1.json"
EVIDENCE_DIR = REPO_ROOT / "evidence" / "benchmark"
RESULTS_FILE = EVIDENCE_DIR / "thpt_pilot_benchmark_results.json"

def determine_pilot_operation(problem: dict) -> tuple[OperationType, str]:
    """
    Deterministically map benchmark problem to CAS OperationType and cleaned expression.
    Ensures derivative questions dispatch to DIFFERENTIATE rather than SOLVE.
    """
    arch = problem.get("archetype_id", "")
    strand = problem.get("strand", "")
    raw_expr = problem.get("problem_latex") or ""
    
    # 1. Calculus: Derivatives
    if arch.startswith("ARCH-11.5") or "đạo hàm" in problem.get("problem_text_vi", "").lower():
        clean_expr = raw_expr
        if clean_expr.startswith("y = ") or clean_expr.startswith("f(x) = "):
            clean_expr = clean_expr.split("=", 1)[1].strip()
        return OperationType.DIFFERENTIATE, clean_expr

    # 2. Calculus: Integrals
    if arch.startswith("ARCH-12.2") or "nguyên hàm" in problem.get("problem_text_vi", "").lower() or "tích phân" in problem.get("problem_text_vi", "").lower():
        clean_expr = raw_expr
        if clean_expr.startswith("integrate(") or clean_expr.startswith("int_"):
            pass
        return OperationType.INTEGRATE, clean_expr

    # 3. Inequalities
    if any(op in raw_expr for op in [">=", "<=", ">", "<"]):
        return OperationType.SOLVE_INEQUALITY, raw_expr

    # 4. Systems of Equations
    if is_top_level_system(raw_expr):
        return OperationType.SOLVE_SYSTEM, raw_expr

    # 5. Equations
    if "=" in raw_expr:
        return OperationType.SOLVE, raw_expr

    # 6. Default Simplify
    return OperationType.SIMPLIFY, raw_expr

def run_pilot_benchmark():
    print("================================================================================")
    print("           MKE THPT 40-PROBLEM PILOT BENCHMARK BASELINE RUNNER")
    print("================================================================================")
    
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    if not BENCHMARK_FILE.exists():
        print(f"[ERROR] Pilot benchmark file not found: {BENCHMARK_FILE}")
        sys.exit(1)
        
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    problems = dataset.get("problems", [])
    print(f"Loaded {len(problems)} genuine pilot problems from {BENCHMARK_FILE.name}")
    
    router = EngineRouter()
    
    results = []
    
    stats = {
        "total_problems": len(problems),
        "attempted_symbolic": 0,
        "unsupported_modality": 0,
        "outcomes": {
            "SUCCESS": 0,
            "GENUINE_WRONG_ANSWER": 0,
            "EXTRANEOUS_ROOT_LEAK": 0,
            "UNSUPPORTED_GRAMMAR": 0,
            "UNSUPPORTED_MODALITY": 0,
            "DOMAIN_REJECTED": 0,
            "TIMEOUT": 0,
            "INTERNAL_ERROR": 0,
        },
        "extraneous_roots_telemetry": {
            "problems_with_extraneous_roots": 0,
            "total_extraneous_candidates_tested": 0,
            "extraneous_roots_leaked_count": 0,
        },
        "by_grade": {
            "10": {"total": 0, "attempted": 0, "success": 0},
            "11": {"total": 0, "attempted": 0, "success": 0},
            "12": {"total": 0, "attempted": 0, "success": 0},
        },
        "by_format": {
            "FORMAT_I_MCQ": {"total": 0, "success": 0},
            "FORMAT_II_TRUE_FALSE": {"total": 0, "success": 0},
            "FORMAT_III_SHORT_ANSWER": {"total": 0, "success": 0},
            "FORMAT_IV_STRUCTURED": {"total": 0, "success": 0},
        },
        "by_modality": {
            "SYMBOLIC_TYPED": {"total": 0, "attempted": 0, "success": 0},
            "VIETNAMESE_WORD_PROBLEM": {"total": 0, "attempted": 0, "success": 0},
            "TABLE_OR_COORDINATE_DATA": {"total": 0, "attempted": 0, "success": 0},
        }
    }
    
    start_time = time.monotonic()
    
    for idx, prob in enumerate(problems, 1):
        pid = prob["problem_id"]
        grade = str(prob["grade"])
        fmt = prob["format_type"]
        mod = prob["input_modality"]
        gt = prob.get("ground_truth", {})
        extraneous_declared = gt.get("extraneous_roots", [])
        
        if extraneous_declared:
            stats["extraneous_roots_telemetry"]["problems_with_extraneous_roots"] += 1
            stats["extraneous_roots_telemetry"]["total_extraneous_candidates_tested"] += len(extraneous_declared)
            
        stats["by_grade"][grade]["total"] += 1
        stats["by_format"][fmt]["total"] += 1
        stats["by_modality"][mod]["total"] += 1
        
        # 1. Check Modality Support
        if mod in ["VIETNAMESE_WORD_PROBLEM", "TABLE_OR_COORDINATE_DATA"]:
            stats["unsupported_modality"] += 1
            stats["outcomes"]["UNSUPPORTED_MODALITY"] += 1
            
            res_item = {
                "problem_id": pid,
                "grade": int(grade),
                "archetype_id": prob["archetype_id"],
                "format_type": fmt,
                "input_modality": mod,
                "outcome": BenchmarkOutcome.UNSUPPORTED_MODALITY.value,
                "attempted": False,
                "matched_ground_truth": False,
                "details": f"Input modality '{mod}' requires external NLP / table extraction pipeline."
            }
            results.append(res_item)
            continue
            
        # 2. Symbolic Attempt
        stats["attempted_symbolic"] += 1
        stats["by_grade"][grade]["attempted"] += 1
        stats["by_modality"][mod]["attempted"] += 1
        
        op, expr_to_execute = determine_pilot_operation(prob)
        
        req = ExecutionRequest(
            operation=op,
            raw_input=expr_to_execute,
            expression=expr_to_execute,
            variable="x"
        )
        
        try:
            resp: ExecutionResponse = router.route_and_execute(req)
            engine_status_val = resp.mathematical_status.value if isinstance(resp.mathematical_status, EngineStatus) else str(resp.mathematical_status)
            
            raw_resp_dict = resp.to_dict()
            raw_resp_dict["solution_set"] = resp.solution_set
            
            score_res = evaluate_benchmark_response(prob, engine_status_val, raw_resp_dict)
            outcome = score_res["outcome"]
            
            stats["outcomes"][outcome.value] += 1
            if outcome == BenchmarkOutcome.SUCCESS:
                stats["by_grade"][grade]["success"] += 1
                stats["by_format"][fmt]["success"] += 1
                stats["by_modality"][mod]["success"] += 1
                
            if outcome == BenchmarkOutcome.EXTRANEOUS_ROOT_LEAK:
                stats["extraneous_roots_telemetry"]["extraneous_roots_leaked_count"] += score_res.get("extraneous_roots_leaked", 0)
                
            res_item = {
                "problem_id": pid,
                "grade": int(grade),
                "archetype_id": prob["archetype_id"],
                "format_type": fmt,
                "input_modality": mod,
                "operation_dispatched": op.value,
                "expression_dispatched": expr_to_execute,
                "outcome": outcome.value,
                "attempted": True,
                "matched_ground_truth": score_res["matched_ground_truth"],
                "selected_engine": resp.selected_engine,
                "engine_status": engine_status_val,
                "scoring_details": score_res["details"],
                "engine_result": resp.symbolic_result,
                "engine_solution_set": resp.solution_set,
            }
        except Exception as ex:
            stats["outcomes"]["INTERNAL_ERROR"] += 1
            res_item = {
                "problem_id": pid,
                "grade": int(grade),
                "archetype_id": prob["archetype_id"],
                "format_type": fmt,
                "input_modality": mod,
                "outcome": BenchmarkOutcome.INTERNAL_ERROR.value,
                "attempted": True,
                "matched_ground_truth": False,
                "exception": str(ex)
            }
            
        results.append(res_item)

    total_duration = time.monotonic() - start_time
    total_problems = stats["total_problems"]
    attempted = stats["attempted_symbolic"]
    successes = stats["outcomes"]["SUCCESS"]
    
    full_accuracy = (successes / total_problems) * 100.0 if total_problems > 0 else 0.0
    symbolic_accuracy = (successes / attempted) * 100.0 if attempted > 0 else 0.0

    output_payload = {
        "benchmark_metadata": dataset.get("benchmark_metadata"),
        "pilot_execution_metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine_version": "v0.3.0-p03b-accepted",
            "duration_seconds": round(total_duration, 3),
            "summary_metrics": {
                "total_pilot_problems": total_problems,
                "attempted_symbolic": attempted,
                "unsupported_modality": stats["unsupported_modality"],
                "success": successes,
                "genuine_wrong_answer": stats["outcomes"]["GENUINE_WRONG_ANSWER"],
                "extraneous_root_leak": stats["outcomes"]["EXTRANEOUS_ROOT_LEAK"],
                "unsupported_grammar": stats["outcomes"]["UNSUPPORTED_GRAMMAR"],
                "domain_rejected": stats["outcomes"]["DOMAIN_REJECTED"],
                "timeout": stats["outcomes"]["TIMEOUT"],
                "internal_error": stats["outcomes"]["INTERNAL_ERROR"],
                "full_pilot_accuracy_pct": round(full_accuracy, 2),
                "symbolic_attempted_accuracy_pct": round(symbolic_accuracy, 2),
            },
            "extraneous_roots_telemetry": stats["extraneous_roots_telemetry"],
            "stratified_breakdown": {
                "by_grade": stats["by_grade"],
                "by_format": stats["by_format"],
                "by_modality": stats["by_modality"],
            }
        },
        "item_results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print("\n--------------------------------------------------------------------------------")
    print("                    PILOT BENCHMARK EXECUTION RESULTS SUMMARY                   ")
    print("--------------------------------------------------------------------------------")
    print(f"Total Authentic Pilot Items:           {total_problems}")
    print(f"Attempted Symbolic Expressions:        {attempted} ({attempted/total_problems*100:.1f}%)")
    print(f"Unsupported Modality (NLP/Data):       {stats['unsupported_modality']} ({stats['unsupported_modality']/total_problems*100:.1f}%)")
    print(f"Mathematical Successes:                {successes}")
    print(f"Genuine Wrong Answers:                 {stats['outcomes']['GENUINE_WRONG_ANSWER']}")
    print(f"Extraneous Root Leaks:                 {stats['outcomes']['EXTRANEOUS_ROOT_LEAK']}")
    print(f"Unsupported Grammar / Out of Scope:    {stats['outcomes']['UNSUPPORTED_GRAMMAR']}")
    print(f"Domain Rejected / Safety Blocked:      {stats['outcomes']['DOMAIN_REJECTED']}")
    print(f"Engine Timeouts:                       {stats['outcomes']['TIMEOUT']}")
    print(f"\n-> Full 40-Item Pilot Accuracy:        {full_accuracy:.2f}% ({successes}/{total_problems})")
    print(f"-> Attempted Symbolic Subset Accuracy: {symbolic_accuracy:.2f}% ({successes}/{attempted})")
    print("--------------------------------------------------------------------------------")
    print("Extraneous Roots Telemetry:")
    print(f"  - Problems with Defined Extraneous Roots: {stats['extraneous_roots_telemetry']['problems_with_extraneous_roots']}")
    print(f"  - Total Extraneous Candidates Tested:     {stats['extraneous_roots_telemetry']['total_extraneous_candidates_tested']}")
    print(f"  - Extraneous Roots Leaked Count:          {stats['extraneous_roots_telemetry']['extraneous_roots_leaked_count']}")
    print("--------------------------------------------------------------------------------")
    print("Stratified Grade Breakdown:")
    for gr in ["10", "11", "12"]:
        g_st = stats["by_grade"][gr]
        print(f"  - Grade {gr}: Total={g_st['total']}, Attempted={g_st['attempted']}, Solved={g_st['success']}")
    print("--------------------------------------------------------------------------------")
    print(f"Detailed machine-readable evidence saved to: {RESULTS_FILE}")
    print("================================================================================")

if __name__ == "__main__":
    run_pilot_benchmark()
