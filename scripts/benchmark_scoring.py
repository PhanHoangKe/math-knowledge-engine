"""
MKE Mathematical Benchmark Scoring & Response Normalizer.
Provides rigorous mathematical normalization, equivalence checking,
extraneous root detection, and error taxonomy classification.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

class BenchmarkOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    GENUINE_WRONG_ANSWER = "GENUINE_WRONG_ANSWER"
    EXTRANEOUS_ROOT_LEAK = "EXTRANEOUS_ROOT_LEAK"
    UNSUPPORTED_GRAMMAR = "UNSUPPORTED_GRAMMAR"
    UNSUPPORTED_MODALITY = "UNSUPPORTED_MODALITY"
    DOMAIN_REJECTED = "DOMAIN_REJECTED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def normalize_solution_token(token: str) -> str:
    """Normalize algebraic tokens (remove whitespace, standard notation)."""
    t = str(token).strip().replace(" ", "")
    # Normalize fractions, e.g. 5/2, -1
    t = t.replace("\\frac{", "(").replace("}{", "/").replace("}", ")")
    t = t.replace("\\sqrt{", "sqrt(").replace("}", ")")
    return t

def normalize_solution_set(solutions: List[str] | Set[str]) -> Set[str]:
    """Normalize a set of solution string tokens."""
    norm_set = set()
    for s in solutions:
        # If solution is in form "x = 2", extract "2"
        s_clean = s.strip()
        if s_clean.startswith("x = ") or s_clean.startswith("x="):
            s_clean = s_clean.split("=", 1)[1].strip()
        norm_set.add(normalize_solution_token(s_clean))
    return norm_set

def check_extraneous_root_leak(
    produced_solutions: Set[str],
    known_extraneous_roots: List[str]
) -> Tuple[bool, List[str]]:
    """Check if any known extraneous root leaked into the engine's solution set."""
    if not known_extraneous_roots or not produced_solutions:
        return False, []
    
    leaked = []
    norm_extraneous = {normalize_solution_token(r) for r in known_extraneous_roots}
    
    for sol in produced_solutions:
        if sol in norm_extraneous:
            leaked.append(sol)
            
    return len(leaked) > 0, leaked

def evaluate_benchmark_response(
    problem: Dict[str, Any],
    engine_status: str,
    raw_response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Score a single benchmark problem against an engine execution response.
    Returns structured scoring metadata.
    """
    gt = problem.get("ground_truth", {})
    sol_type = gt.get("solution_type", "EXACT_SET")
    extraneous_declared = gt.get("extraneous_roots", [])
    
    # 1. Check pre-dispatch / non-symbolic modality
    modality = problem.get("input_modality", "SYMBOLIC_TYPED")
    if modality in ["VIETNAMESE_WORD_PROBLEM", "TABLE_OR_COORDINATE_DATA"]:
        return {
            "outcome": BenchmarkOutcome.UNSUPPORTED_MODALITY,
            "matched_ground_truth": False,
            "extraneous_roots_tested": 0,
            "extraneous_roots_leaked": 0,
            "details": f"Modality '{modality}' requires external NLP / multimodal pipeline."
        }
        
    # 2. Check engine status
    if engine_status in ["OUT_OF_SCOPE", "UNSUPPORTED_EXPRESSION"]:
        return {
            "outcome": BenchmarkOutcome.UNSUPPORTED_GRAMMAR,
            "matched_ground_truth": False,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": raw_response.get("error_message") or "Engine reported OUT_OF_SCOPE."
        }
        
    if engine_status in ["TIMEOUT", "RESOURCE_EXHAUSTED"]:
        return {
            "outcome": BenchmarkOutcome.TIMEOUT,
            "matched_ground_truth": False,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": raw_response.get("error_message") or "Resource / time limit exceeded."
        }
        
    if engine_status in ["DOMAIN_ERROR", "INVALID_INPUT"]:
        # If the problem was expected to be empty or domain error, check if intentional
        if sol_type == "EXACT_SET" and len(gt.get("exact_solution_set", [])) == 0 and not extraneous_declared:
            return {
                "outcome": BenchmarkOutcome.SUCCESS,
                "matched_ground_truth": True,
                "extraneous_roots_tested": 0,
                "extraneous_roots_leaked": 0,
                "details": "Engine correctly identified empty domain / invalid input."
            }
        return {
            "outcome": BenchmarkOutcome.DOMAIN_REJECTED,
            "matched_ground_truth": False,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": raw_response.get("error_message") or "Input rejected by domain guard."
        }

    if engine_status != "SUCCESS":
        return {
            "outcome": BenchmarkOutcome.INTERNAL_ERROR,
            "matched_ground_truth": False,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": raw_response.get("error_message") or f"Engine status: {engine_status}"
        }

    # 3. Process SUCCESS status from engine
    produced_sol_set = set()
    if raw_response.get("solution_set"):
        produced_sol_set = normalize_solution_set(raw_response["solution_set"])
    elif raw_response.get("symbolic_result"):
        res_str = raw_response["symbolic_result"].strip()
        if res_str.startswith("{") and res_str.endswith("}"):
            inner = res_str[1:-1].strip()
            if inner:
                produced_sol_set = {normalize_solution_token(item) for item in inner.split(",") if item.strip()}
        else:
            produced_sol_set = {normalize_solution_token(res_str)}

    # 4. Check Extraneous Root Leakage
    leaked, leak_list = check_extraneous_root_leak(produced_sol_set, extraneous_declared)
    if leaked:
        return {
            "outcome": BenchmarkOutcome.EXTRANEOUS_ROOT_LEAK,
            "matched_ground_truth": False,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": len(leak_list),
            "leaked_roots": leak_list,
            "details": f"Engine admitted extraneous root(s): {leak_list}"
        }

    # 5. Check Ground Truth Match
    expected_set = normalize_solution_set(gt.get("exact_solution_set", []))
    
    # Check if empty solution set expected
    if not expected_set and not produced_sol_set:
        return {
            "outcome": BenchmarkOutcome.SUCCESS,
            "matched_ground_truth": True,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": "Correctly matched empty solution set."
        }

    # Compare non-empty sets
    if expected_set and produced_sol_set == expected_set:
        return {
            "outcome": BenchmarkOutcome.SUCCESS,
            "matched_ground_truth": True,
            "extraneous_roots_tested": len(extraneous_declared),
            "extraneous_roots_leaked": 0,
            "details": f"Exact solution set matched: {produced_sol_set}"
        }
        
    # Check numeric value float equivalence if declared
    if "numeric_value" in gt and raw_response.get("symbolic_result"):
        try:
            num_val = float(raw_response["symbolic_result"])
            exp_val = float(gt["numeric_value"])
            tol = gt.get("numeric_tolerance", 0.001)
            if abs(num_val - exp_val) <= tol:
                return {
                    "outcome": BenchmarkOutcome.SUCCESS,
                    "matched_ground_truth": True,
                    "extraneous_roots_tested": len(extraneous_declared),
                    "extraneous_roots_leaked": 0,
                    "details": f"Numeric float matched within tolerance: {num_val} ~= {exp_val}"
                }
        except (ValueError, TypeError):
            pass

    # Derivative / Simplified Expression equivalence check
    sym_res = raw_response.get("symbolic_result", "")
    if sym_res:
        norm_sym = normalize_solution_token(sym_res)
        for exp_sol in expected_set:
            if norm_sym == exp_sol or norm_sym == exp_sol.replace(" ", ""):
                return {
                    "outcome": BenchmarkOutcome.SUCCESS,
                    "matched_ground_truth": True,
                    "extraneous_roots_tested": len(extraneous_declared),
                    "extraneous_roots_leaked": 0,
                    "details": f"Expression matched expected form: {norm_sym}"
                }

    # Otherwise Genuine Wrong Answer
    return {
        "outcome": BenchmarkOutcome.GENUINE_WRONG_ANSWER,
        "matched_ground_truth": False,
        "extraneous_roots_tested": len(extraneous_declared),
        "extraneous_roots_leaked": 0,
        "details": f"Produced {produced_sol_set} does not match expected {expected_set}."
    }
