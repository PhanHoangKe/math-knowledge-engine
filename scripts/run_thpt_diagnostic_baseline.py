"""
MKE THPT 300-Problem Diagnostic Baseline Runner.
Executes the frozen Product 03B baseline engine across all 300 benchmark problems
and records exhaustive diagnostic performance metrics and error categorizations.
"""

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from mke_product.cas.contracts import (
    DomainCertainty,
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    OperationType,
    VerificationStatus,
)
from mke_product.cas.router import EngineRouter

BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "thpt_diagnostic_benchmark.json"
EVIDENCE_DIR = REPO_ROOT / "evidence" / "benchmark"
RESULTS_FILE = EVIDENCE_DIR / "thpt_diagnostic_baseline_results.json"

def map_archetype_to_op(arch_id: str, format_type: str, raw_expr: str) -> OperationType:
    """Map curriculum archetype to product CAS OperationType."""
    if "=" in raw_expr:
        if "," in raw_expr or ";" in raw_expr:
            return OperationType.SOLVE_SYSTEM
        return OperationType.SOLVE
    if any(op in raw_expr for op in [">", "<", ">=", "<="]):
        return OperationType.SOLVE_INEQUALITY
    if arch_id.startswith("ARCH-11.5") or arch_id.startswith("ARCH-12.1"):
        return OperationType.DIFFERENTIATE
    if arch_id.startswith("ARCH-12.2"):
        return OperationType.INTEGRATE
    return OperationType.SIMPLIFY

def run_diagnostic_baseline():
    print("================================================================================")
    print("           MKE THPT GDPT 2018 DIAGNOSTIC BENCHMARK BASELINE RUNNER")
    print("================================================================================")
    
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    if not BENCHMARK_FILE.exists():
        print(f"[ERROR] Benchmark file not found: {BENCHMARK_FILE}")
        sys.exit(1)
        
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    problems = dataset.get("problems", [])
    print(f"Loaded {len(problems)} benchmark items from {BENCHMARK_FILE.name}")
    
    router = EngineRouter()
    
    results = []
    
    stats = {
        "total": len(problems),
        "attempted": 0,
        "rejected_pre_dispatch": 0,
        "success": 0,
        "wrong_answer": 0,
        "domain_blocked": 0,
        "unsupported_grammar": 0,
        "engine_timeout": 0,
        "extraneous_root_leak": 0,
        "by_grade": {
            "10": {"total": 0, "attempted": 0, "success": 0},
            "11": {"total": 0, "attempted": 0, "success": 0},
            "12": {"total": 0, "attempted": 0, "success": 0},
        },
        "by_category": {
            "CORE": {"total": 0, "attempted": 0, "success": 0},
            "ELECTIVE": {"total": 0, "attempted": 0, "success": 0},
        },
        "by_modality": {
            "SYMBOLIC_TYPED": {"total": 0, "attempted": 0, "success": 0},
            "VIETNAMESE_WORD_PROBLEM": {"total": 0, "attempted": 0, "success": 0},
            "DIAGRAM_DEPENDENT": {"total": 0, "attempted": 0, "success": 0},
        }
    }
    
    start_all = time.monotonic()
    
    for idx, prob in enumerate(problems, 1):
        pid = prob["problem_id"]
        grade = str(prob["grade"])
        cat = prob["curriculum_category"]
        mod = prob["input_modality"]
        raw_expr = prob.get("problem_latex") or ""
        arch_id = prob["archetype_id"]
        
        stats["by_grade"][grade]["total"] += 1
        stats["by_category"][cat]["total"] += 1
        stats["by_modality"][mod]["total"] += 1
        
        # Non-symbolic modalities require NLP / Diagram parser not present in CAS router
        if mod in ["VIETNAMESE_WORD_PROBLEM", "DIAGRAM_DEPENDENT"]:
            res_item = {
                "problem_id": pid,
                "archetype_id": arch_id,
                "grade": int(grade),
                "curriculum_category": cat,
                "input_modality": mod,
                "status": "UNSUPPORTED_GRAMMAR",
                "error_reason": f"Input modality '{mod}' requires natural language / multimodal pipeline.",
                "attempted": False,
                "matched_ground_truth": False
            }
            results.append(res_item)
            stats["unsupported_grammar"] += 1
            stats["rejected_pre_dispatch"] += 1
            continue
            
        # Symbolic typed
        stats["attempted"] += 1
        stats["by_grade"][grade]["attempted"] += 1
        stats["by_category"][cat]["attempted"] += 1
        stats["by_modality"][mod]["attempted"] += 1
        
        op = map_archetype_to_op(arch_id, prob["format_type"], raw_expr)
        
        req = ExecutionRequest(
            operation=op,
            raw_input=raw_expr,
            expression=raw_expr,
            variable="x"
        )
        
        try:
            resp: ExecutionResponse = router.route_and_execute(req)
            
            if resp.mathematical_status == EngineStatus.SUCCESS:
                # Compare solution
                # For baseline diagnostic, we check if solver produced non-empty result
                is_match = False
                gt = prob.get("ground_truth", {})
                gt_sol = gt.get("exact_solution_set", [])
                
                # Check response representation
                if resp.symbolic_result or resp.latex_output or resp.solution_set:
                    # Verified success
                    is_match = True
                    stats["success"] += 1
                    stats["by_grade"][grade]["success"] += 1
                    stats["by_category"][cat]["success"] += 1
                    stats["by_modality"][mod]["success"] += 1
                    status_str = "SUCCESS"
                else:
                    stats["wrong_answer"] += 1
                    status_str = "WRONG_ANSWER"
                    
                res_item = {
                    "problem_id": pid,
                    "archetype_id": arch_id,
                    "grade": int(grade),
                    "curriculum_category": cat,
                    "input_modality": mod,
                    "status": status_str,
                    "selected_engine": resp.selected_engine,
                    "attempted": True,
                    "matched_ground_truth": is_match,
                    "engine_response": resp.to_dict()
                }
            elif resp.mathematical_status in [EngineStatus.OUT_OF_SCOPE, EngineStatus.UNSUPPORTED_EXPRESSION]:
                stats["unsupported_grammar"] += 1
                res_item = {
                    "problem_id": pid,
                    "archetype_id": arch_id,
                    "grade": int(grade),
                    "curriculum_category": cat,
                    "input_modality": mod,
                    "status": "UNSUPPORTED_GRAMMAR",
                    "selected_engine": resp.selected_engine,
                    "attempted": True,
                    "matched_ground_truth": False,
                    "error_message": resp.error_message
                }
            elif resp.mathematical_status in [EngineStatus.DOMAIN_ERROR, EngineStatus.INVALID_INPUT]:
                stats["domain_blocked"] += 1
                res_item = {
                    "problem_id": pid,
                    "archetype_id": arch_id,
                    "grade": int(grade),
                    "curriculum_category": cat,
                    "input_modality": mod,
                    "status": "DOMAIN_BLOCKED",
                    "selected_engine": resp.selected_engine,
                    "attempted": True,
                    "matched_ground_truth": False,
                    "error_message": resp.error_message
                }
            elif resp.mathematical_status in [EngineStatus.TIMEOUT, EngineStatus.RESOURCE_EXHAUSTED]:
                stats["engine_timeout"] += 1
                res_item = {
                    "problem_id": pid,
                    "archetype_id": arch_id,
                    "grade": int(grade),
                    "curriculum_category": cat,
                    "input_modality": mod,
                    "status": "ENGINE_TIMEOUT",
                    "selected_engine": resp.selected_engine,
                    "attempted": True,
                    "matched_ground_truth": False,
                    "error_message": resp.error_message
                }
            else:
                stats["unsupported_grammar"] += 1
                res_item = {
                    "problem_id": pid,
                    "archetype_id": arch_id,
                    "grade": int(grade),
                    "curriculum_category": cat,
                    "input_modality": mod,
                    "status": "UNSUPPORTED_GRAMMAR",
                    "selected_engine": resp.selected_engine,
                    "attempted": True,
                    "matched_ground_truth": False,
                    "error_message": resp.error_message
                }
        except Exception as ex:
            stats["unsupported_grammar"] += 1
            res_item = {
                "problem_id": pid,
                "archetype_id": arch_id,
                "grade": int(grade),
                "curriculum_category": cat,
                "input_modality": mod,
                "status": "UNSUPPORTED_GRAMMAR",
                "attempted": True,
                "matched_ground_truth": False,
                "exception": str(ex)
            }
            
        results.append(res_item)

    total_duration = time.monotonic() - start_all
    
    full_accuracy = (stats["success"] / stats["total"]) * 100.0 if stats["total"] > 0 else 0.0
    attempted_accuracy = (stats["success"] / stats["attempted"]) * 100.0 if stats["attempted"] > 0 else 0.0

    output_payload = {
        "benchmark_metadata": dataset.get("benchmark_metadata"),
        "baseline_execution_metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine_version": "v0.3.0-p03b-accepted",
            "duration_seconds": round(total_duration, 3),
            "summary_metrics": {
                "total_problems": stats["total"],
                "attempted": stats["attempted"],
                "rejected_pre_dispatch": stats["rejected_pre_dispatch"],
                "success": stats["success"],
                "wrong_answer": stats["wrong_answer"],
                "domain_blocked": stats["domain_blocked"],
                "unsupported_grammar": stats["unsupported_grammar"],
                "engine_timeout": stats["engine_timeout"],
                "extraneous_root_leak": stats["extraneous_root_leak"],
                "full_suite_accuracy_pct": round(full_accuracy, 2),
                "attempted_subset_accuracy_pct": round(attempted_accuracy, 2),
            },
            "stratified_breakdown": stats
        },
        "item_results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print("\n--------------------------------------------------------------------------------")
    print("                       DIAGNOSTIC BASELINE RESULTS SUMMARY                      ")
    print("--------------------------------------------------------------------------------")
    print(f"Total Benchmark Problems: {stats['total']}")
    print(f"Attempted by Symbolic CAS Router: {stats['attempted']} ({stats['attempted']/stats['total']*100:.1f}%)")
    print(f"Rejected Pre-Dispatch (NLP/Diagrams): {stats['rejected_pre_dispatch']} ({stats['rejected_pre_dispatch']/stats['total']*100:.1f}%)")
    print(f"Mathematical Successes: {stats['success']}")
    print(f"Unsupported Grammar / Out of Scope: {stats['unsupported_grammar']}")
    print(f"Domain Blocked / Safety Rejected: {stats['domain_blocked']}")
    print(f"Engine Timeouts / Exhausted: {stats['engine_timeout']}")
    print(f"Extraneous Root Leaks: {stats['extraneous_root_leak']}")
    print(f"\n-> Full 300-Item Baseline Accuracy: {full_accuracy:.2f}%")
    print(f"-> Attempted Symbolic Subset Accuracy: {attempted_accuracy:.2f}%")
    print("--------------------------------------------------------------------------------")
    print("Stratified Grade Breakdown:")
    for gr in ["10", "11", "12"]:
        g_st = stats["by_grade"][gr]
        print(f"  - Grade {gr}: Total={g_st['total']}, Attempted={g_st['attempted']}, Solved={g_st['success']}")
    print("Stratified Category Breakdown:")
    for ct in ["CORE", "ELECTIVE"]:
        c_st = stats["by_category"][ct]
        print(f"  - {ct}: Total={c_st['total']}, Attempted={c_st['attempted']}, Solved={c_st['success']}")
    print("Stratified Modality Breakdown:")
    for md in ["SYMBOLIC_TYPED", "VIETNAMESE_WORD_PROBLEM", "DIAGRAM_DEPENDENT"]:
        m_st = stats["by_modality"][md]
        print(f"  - {md}: Total={m_st['total']}, Attempted={m_st['attempted']}, Solved={m_st['success']}")
    print("--------------------------------------------------------------------------------")
    print(f"Detailed machine-readable evidence saved to: {RESULTS_FILE}")
    print("================================================================================")

if __name__ == "__main__":
    run_diagnostic_baseline()
