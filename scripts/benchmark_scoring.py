"""
MKE Mathematical Benchmark Scoring & Response Normalizer (P03C-P1A-R1).
Provides domain-aware mathematical equivalence checking, multi-format evaluation (MCQ, True/False,
Short Answer, Structured), extraneous root telemetry, and strict error categorization.
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


def normalize_math_string(s: str) -> str:
    """Normalize mathematical expression strings for robust equivalence comparison."""
    if s is None:
        return ""
    t = str(s).strip().replace(" ", "").lower()
    # Normalize LaTeX symbols
    t = t.replace("\\frac{", "(").replace("}{", "/").replace("}", ")")
    t = t.replace("\\sqrt{", "sqrt(").replace("}", ")")
    t = t.replace("\\sin", "sin").replace("\\cos", "cos").replace("\\tan", "tan")
    t = t.replace("\\log", "log").replace("\\ln", "ln").replace("\\exp", "exp")
    t = t.replace("\\int", "integrate").replace("\\cup", "u").replace("cup", "u")
    t = t.replace("\\infty", "oo").replace("+oo", "oo").replace("+\\infty", "oo")
    t = t.replace("\\emptyset", "{}").replace("emptyset", "{}")
    t = t.replace(";", ",")
    # Remove redundant outer braces
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    return t


def is_mathematically_equivalent(s1: str, s2: str) -> bool:
    """Check mathematical equivalence using normalization and SymPy simplification."""
    norm1 = normalize_math_string(s1)
    norm2 = normalize_math_string(s2)
    if norm1 == norm2:
        return True
    if not norm1 and not norm2:
        return True
    if not norm1 or not norm2:
        return False

    # Try exact SymPy algebraic comparison
    try:
        import sympy
        # Replace ^ with ** for SymPy
        sym1 = sympy.sympify(norm1.replace("^", "**"))
        sym2 = sympy.sympify(norm2.replace("^", "**"))
        diff = sympy.simplify(sym1 - sym2)
        if diff == 0 or diff.is_zero is True:
            return True
    except Exception:
        pass
    return False


def are_solution_sets_equivalent(prod_set: Set[str], exp_set: Set[str]) -> bool:
    """Check if two solution sets are mathematically equivalent."""
    if len(prod_set) != len(exp_set):
        return False
    if prod_set == exp_set:
        return True

    # Match each expected item with a unique produced item
    unmatched_prod = list(prod_set)
    for exp in exp_set:
        found = False
        for i, prod in enumerate(unmatched_prod):
            if is_mathematically_equivalent(exp, prod):
                unmatched_prod.pop(i)
                found = True
                break
        if not found:
            return False
    return len(unmatched_prod) == 0


def parse_interval_tokens(interval_str: str) -> Set[str]:
    """Parse union of intervals into normalized component strings."""
    norm = normalize_math_string(interval_str)
    parts = re.split(r"u|union|v|hoặc", norm)
    return {p.strip() for p in parts if p.strip()}


def parse_system_solution(sol_input: Any) -> Dict[str, str]:
    """Parse system solution into variable-value dictionary."""
    out: Dict[str, str] = {}
    if sol_input is None:
        return out
    if isinstance(sol_input, dict):
        for k, v in sol_input.items():
            out[str(k).strip().lower()] = normalize_math_string(str(v))
        return out

    raw_items: List[str] = []
    if isinstance(sol_input, (list, tuple, set)):
        raw_items = [str(x) for x in sol_input]
    elif isinstance(sol_input, str):
        raw_items = [sol_input]

    subparts: List[str] = []
    for raw in raw_items:
        s = raw.strip()
        parts = re.split(r"[,;]", s)
        for p in parts:
            if p.strip():
                subparts.append(p.strip())

    for item in subparts:
        if "=" in item:
            var, val = item.split("=", 1)
            out[var.strip().lower()] = normalize_math_string(val)
        elif ":" in item:
            var, val = item.split(":", 1)
            out[var.strip().lower()] = normalize_math_string(val)
    return out


def are_systems_equivalent(prod_sys: Dict[str, str], exp_sys: Dict[str, str]) -> bool:
    """Check if two parsed system solutions are mathematically equivalent."""
    if not prod_sys or not exp_sys:
        return False
    if set(prod_sys.keys()) != set(exp_sys.keys()):
        return False
    for var, exp_val in exp_sys.items():
        prod_val = prod_sys[var]
        if not is_mathematically_equivalent(prod_val, exp_val):
            return False
    return True


def check_extraneous_root_leak(
    produced_solutions: Set[str],
    known_extraneous_roots: List[str]
) -> Tuple[bool, List[str]]:
    """Check if any known extraneous candidate root leaked into the engine's solution set."""
    if not known_extraneous_roots or not produced_solutions:
        return False, []

    leaked = []
    norm_extraneous = {normalize_math_string(r) for r in known_extraneous_roots}

    for sol in produced_solutions:
        norm_sol = normalize_math_string(sol)
        if norm_sol in norm_extraneous:
            leaked.append(sol)
        else:
            for ext in norm_extraneous:
                if is_mathematically_equivalent(norm_sol, ext):
                    leaked.append(sol)
                    break

    return len(leaked) > 0, leaked


def evaluate_benchmark_response(
    problem: Dict[str, Any],
    engine_status: str,
    raw_response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Score a single benchmark problem against an engine execution response.
    Returns comprehensive scoring metadata, including sub-statement and choice keys.
    """
    gt = problem.get("ground_truth", {})
    sol_type = gt.get("solution_type", "EXACT_SET")
    extraneous_declared = gt.get("extraneous_roots", [])
    format_type = problem.get("format_type", "FORMAT_III_SHORT_ANSWER")
    modality = problem.get("input_modality", "SYMBOLIC_TYPED")

    base_telemetry = {
        "declared_candidates_count": len(extraneous_declared),
        "actually_processed_candidates_count": 0,
        "admitted_invalid_roots_count": 0,
        "rejected_at_domain_gate_count": 0,
        "genuinely_verified_excluded_roots_count": 0,
    }

    # 1. Non-symbolic modalities
    if modality in ["VIETNAMESE_WORD_PROBLEM", "TABLE_OR_COORDINATE_DATA"]:
        return {
            "outcome": BenchmarkOutcome.UNSUPPORTED_MODALITY,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "details": f"Input modality '{modality}' requires external NLP / multimodal pipeline."
        }

    expected_status = gt.get("expected_status")
    if expected_status:
        if (
            engine_status == expected_status
            or (expected_status in ["OUT_OF_SCOPE", "UNRESOLVED"] and engine_status in ["OUT_OF_SCOPE", "UNRESOLVED"])
            or (expected_status == "DOMAIN_ERROR" and engine_status in ["DOMAIN_ERROR", "INVALID_INPUT"])
        ):
            return {
                "outcome": BenchmarkOutcome.SUCCESS,
                "matched_ground_truth": True,
                "telemetry": base_telemetry,
                "details": f"Correctly produced expected status: {engine_status}."
            }

    # 2. Engine non-success statuses: separate syntax rejection from mathematical domain error
    if engine_status in ["OUT_OF_SCOPE", "UNRESOLVED", "UNSUPPORTED_EXPRESSION", "INVALID_INPUT"]:
        return {
            "outcome": BenchmarkOutcome.UNSUPPORTED_GRAMMAR,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "details": raw_response.get("error_message") or f"Engine syntax/grammar rejection: {engine_status}."
        }

    if engine_status == "DOMAIN_ERROR":
        base_telemetry["rejected_at_domain_gate_count"] = len(extraneous_declared)
        return {
            "outcome": BenchmarkOutcome.DOMAIN_REJECTED,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "details": raw_response.get("error_message") or "Mathematical domain error."
        }

    if engine_status in ["TIMEOUT", "RESOURCE_EXHAUSTED"]:
        return {
            "outcome": BenchmarkOutcome.TIMEOUT,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "details": raw_response.get("error_message") or "Execution timed out / resource exhausted."
        }

    if engine_status != "SUCCESS":
        return {
            "outcome": BenchmarkOutcome.INTERNAL_ERROR,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "details": raw_response.get("error_message") or f"Engine status: {engine_status}"
        }

    # 3. SUCCESS Status Processing
    base_telemetry["actually_processed_candidates_count"] = len(extraneous_declared)

    produced_sol_set: Set[str] = set()
    if raw_response.get("solution_set") is not None and isinstance(raw_response.get("solution_set"), (list, tuple, set)):
        produced_sol_set = {normalize_math_string(s) for s in raw_response["solution_set"] if normalize_math_string(s)}
    elif raw_response.get("symbolic_result"):
        res_str = raw_response["symbolic_result"].strip()
        if res_str in ["{}", "\\emptyset", "No real solution", "None"]:
            produced_sol_set = set()
        elif res_str.startswith("{") and res_str.endswith("}"):
            inner = res_str[1:-1].strip()
            if inner:
                produced_sol_set = {normalize_math_string(item) for item in inner.split(",") if normalize_math_string(item)}
            else:
                produced_sol_set = set()
        elif res_str:
            norm = normalize_math_string(res_str)
            if norm:
                produced_sol_set = {norm}

    # 4. Extraneous root check
    leaked, leak_list = check_extraneous_root_leak(produced_sol_set, extraneous_declared)
    if leaked:
        base_telemetry["admitted_invalid_roots_count"] = len(leak_list)
        return {
            "outcome": BenchmarkOutcome.EXTRANEOUS_ROOT_LEAK,
            "matched_ground_truth": False,
            "telemetry": base_telemetry,
            "leaked_roots": leak_list,
            "details": f"Engine admitted extraneous root(s): {leak_list}"
        }
    elif extraneous_declared:
        evidence = raw_response.get("verification_evidence") or {}
        worker_eliminated = evidence.get("extraneous_roots", [])
        if worker_eliminated:
            base_telemetry["genuinely_verified_excluded_roots_count"] = len(worker_eliminated)
        else:
            base_telemetry["genuinely_verified_excluded_roots_count"] = 0

    # 5. Format-Specific Scoring
    # FORMAT II: True / False (4 Sub-statements)
    if sol_type == "BOOLEAN_ARRAY" or format_type == "FORMAT_II_TRUE_FALSE":
        expected_bools = gt.get("boolean_values", {})
        produced_bools = raw_response.get("boolean_values") or raw_response.get("sub_statement_evaluations")

        if not produced_bools or not isinstance(produced_bools, dict):
            # An empty solution set or non-boolean response is a WRONG ANSWER
            return {
                "outcome": BenchmarkOutcome.GENUINE_WRONG_ANSWER,
                "matched_ground_truth": False,
                "telemetry": base_telemetry,
                "details": "Engine did not produce boolean sub-statement judgements for Format II."
            }

        sub_scores = {}
        for stmt_id, exp_bool in expected_bools.items():
            sub_scores[stmt_id] = (produced_bools.get(stmt_id) == exp_bool)

        all_correct = all(sub_scores.values()) and len(sub_scores) == 4
        correct_cnt = sum(1 for v in sub_scores.values() if v)

        return {
            "outcome": BenchmarkOutcome.SUCCESS if all_correct else BenchmarkOutcome.GENUINE_WRONG_ANSWER,
            "matched_ground_truth": all_correct,
            "sub_statement_scores": sub_scores,
            "correct_statements_count": correct_cnt,
            "telemetry": base_telemetry,
            "details": f"Format II score: {correct_cnt}/4 statements matched."
        }

    # FORMAT I: MCQ (Choice Key A, B, C, D)
    if format_type == "FORMAT_I_MCQ" or sol_type == "CHOICE_KEY":
        expected_key = gt.get("correct_choice")
        produced_key = raw_response.get("selected_choice")
        choice_matched = bool(produced_key and produced_key.strip().upper() == expected_key)

        expected_set = {normalize_math_string(s) for s in gt.get("exact_solution_set", []) if normalize_math_string(s)}
        math_matched = False

        # Fall back to mathematical solution set comparison for choice
        if not expected_set:
            # Expected empty set
            if not produced_sol_set:
                math_matched = True
        else:
            if are_solution_sets_equivalent(produced_sol_set, expected_set):
                math_matched = True
            elif any(is_mathematically_equivalent(raw_response.get("symbolic_result", ""), s) for s in expected_set):
                math_matched = True

        if choice_matched or math_matched:
            return {
                "outcome": BenchmarkOutcome.SUCCESS,
                "matched_ground_truth": True,
                "choice_matched": choice_matched,
                "math_matched": math_matched,
                "telemetry": base_telemetry,
                "details": f"MCQ matched (choice_matched={choice_matched}, math_matched={math_matched})"
            }

        return {
            "outcome": BenchmarkOutcome.GENUINE_WRONG_ANSWER,
            "matched_ground_truth": False,
            "choice_matched": choice_matched,
            "math_matched": math_matched,
            "telemetry": base_telemetry,
            "details": f"MCQ failed: expected choice {expected_key} / {expected_set}, got key '{produced_key}' / {produced_sol_set}"
        }

    # Multi-variable system of equations
    if any("=" in s and any(v in s for v in ["x", "y", "z"]) for s in gt.get("exact_solution_set", [])):
        exp_sys = parse_system_solution(gt.get("exact_solution_set", []))
        prod_sys = parse_system_solution(raw_response.get("solution_set") or raw_response.get("symbolic_result") or produced_sol_set)
        if exp_sys and are_systems_equivalent(prod_sys, exp_sys):
            return {
                "outcome": BenchmarkOutcome.SUCCESS,
                "matched_ground_truth": True,
                "telemetry": base_telemetry,
                "details": f"System solution matched: {exp_sys}"
            }

    # Standard Exact Set Matching
    expected_set = {normalize_math_string(s) for s in gt.get("exact_solution_set", []) if normalize_math_string(s)}
    if not expected_set and gt.get("symbolic_canonical"):
        expected_set.add(normalize_math_string(gt["symbolic_canonical"]))
        for alt in gt.get("alternate_forms", []):
            expected_set.add(normalize_math_string(alt))

    # Check if empty solution set expected
    if not expected_set and not produced_sol_set:
        return {
            "outcome": BenchmarkOutcome.SUCCESS,
            "matched_ground_truth": True,
            "telemetry": base_telemetry,
            "details": "Correctly matched empty solution set."
        }

    if expected_set and are_solution_sets_equivalent(produced_sol_set, expected_set):
        return {
            "outcome": BenchmarkOutcome.SUCCESS,
            "matched_ground_truth": True,
            "telemetry": base_telemetry,
            "details": f"Exact solution set matched: {produced_sol_set}"
        }

    # Numeric float tolerance check
    if "numeric_value" in gt and raw_response.get("symbolic_result"):
        try:
            num_val = float(raw_response["symbolic_result"])
            exp_val = float(gt["numeric_value"])
            tol = gt.get("numeric_tolerance", 0.001)
            if abs(num_val - exp_val) <= tol:
                return {
                    "outcome": BenchmarkOutcome.SUCCESS,
                    "matched_ground_truth": True,
                    "telemetry": base_telemetry,
                    "details": f"Numeric float matched: {num_val} ~= {exp_val} (tol={tol})"
                }
        except (ValueError, TypeError):
            pass

    # Interval representation matching (e.g. (-oo, 2) U (3, oo))
    for exp_str in expected_set:
        exp_intervals = parse_interval_tokens(exp_str)
        if exp_intervals and len(exp_intervals) > 1:
            prod_intervals = set()
            for ps in produced_sol_set:
                prod_intervals.update(parse_interval_tokens(ps))
            if prod_intervals == exp_intervals:
                return {
                    "outcome": BenchmarkOutcome.SUCCESS,
                    "matched_ground_truth": True,
                    "telemetry": base_telemetry,
                    "details": f"Interval set matched: {prod_intervals}"
                }

    # Expression equivalence check for symbolic derivatives / integrals
    sym_res = raw_response.get("symbolic_result", "")
    if sym_res:
        norm_sym = normalize_math_string(sym_res)
        for exp_expr in expected_set:
            if is_mathematically_equivalent(norm_sym, exp_expr):
                return {
                    "outcome": BenchmarkOutcome.SUCCESS,
                    "matched_ground_truth": True,
                    "telemetry": base_telemetry,
                    "details": f"Expression matched expected form: {norm_sym}"
                }

    # If no match occurred
    return {
        "outcome": BenchmarkOutcome.GENUINE_WRONG_ANSWER,
        "matched_ground_truth": False,
        "telemetry": base_telemetry,
        "details": f"Produced {produced_sol_set} did not match expected {expected_set}."
    }
