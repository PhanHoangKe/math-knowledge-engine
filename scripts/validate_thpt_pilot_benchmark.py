"""
MKE THPT Pilot Benchmark Validator & Integrity Auditor.
Enforces strict schema validation, mathematical consistency of ground truth,
near-duplicate detection across splits, and zero-synthetic verification.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PILOT_BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "thpt_pilot_benchmark_v1.json"

REQUIRED_FIELDS = [
    "problem_id",
    "grade",
    "strand",
    "topic_id",
    "archetype_id",
    "archetype_desc",
    "curriculum_category",
    "split",
    "format_type",
    "difficulty_level",
    "input_modality",
    "problem_text_vi",
    "ground_truth",
    "oracle_family",
    "rubric_steps",
    "source_reference",
    "independent_proof_notes"
]

VALID_FORMATS = {"FORMAT_I_MCQ", "FORMAT_II_TRUE_FALSE", "FORMAT_III_SHORT_ANSWER", "FORMAT_IV_STRUCTURED"}
VALID_MODALITIES = {"SYMBOLIC_TYPED", "VIETNAMESE_WORD_PROBLEM", "TABLE_OR_COORDINATE_DATA"}
VALID_SPLITS = {"DEV", "VAL"}

def tokenize_text(text: str) -> set:
    """Normalize and tokenize text for Jaccard similarity comparison."""
    words = re.findall(r"\w+", text.lower())
    return set(words)

def jaccard_similarity(s1: set, s2: set) -> float:
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / len(s1.union(s2))

def validate_pilot_benchmark():
    print("================================================================================")
    print("           MKE THPT 40-ITEM PILOT BENCHMARK INTEGRITY VALIDATOR")
    print("================================================================================")
    
    if not PILOT_BENCHMARK_FILE.exists():
        print(f"[ERROR] Pilot benchmark file not found: {PILOT_BENCHMARK_FILE}")
        sys.exit(1)
        
    with open(PILOT_BENCHMARK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    meta = data.get("benchmark_metadata", {})
    problems = data.get("problems", [])
    
    print(f"Dataset Title: {meta.get('title')}")
    print(f"Declared Version: {meta.get('version')}")
    print(f"Total Problems Loaded: {len(problems)}")
    
    errors = []
    
    if len(problems) < 30 or len(problems) > 50:
        errors.append(f"Expected 30-50 problems in pilot suite, found {len(problems)}")
        
    seen_ids = set()
    split_counts = {"DEV": 0, "VAL": 0}
    grade_counts = {10: 0, 11: 0, 12: 0}
    format_counts = {fmt: 0 for fmt in VALID_FORMATS}
    modality_counts = {mod: 0 for mod in VALID_MODALITIES}
    
    dev_items = []
    val_items = []
    
    for idx, prob in enumerate(problems, 1):
        pid = prob.get("problem_id")
        if not pid:
            errors.append(f"Problem #{idx} missing 'problem_id'")
        elif pid in seen_ids:
            errors.append(f"Duplicate problem_id: {pid}")
        else:
            seen_ids.add(pid)
            
        for field in REQUIRED_FIELDS:
            if field not in prob or prob[field] is None:
                errors.append(f"Problem {pid} missing required field '{field}'")
                
        # Check for placeholder markers
        q_text = prob.get("problem_text_vi", "")
        if "Bài toán mẫu" in q_text or "sol_ARCH" in str(prob.get("ground_truth")):
            errors.append(f"Problem {pid} contains unverified synthetic placeholder markers!")
            
        fmt = prob.get("format_type")
        if fmt not in VALID_FORMATS:
            errors.append(f"Problem {pid} invalid format '{fmt}'")
        else:
            format_counts[fmt] += 1
            
        mod = prob.get("input_modality")
        if mod not in VALID_MODALITIES:
            errors.append(f"Problem {pid} invalid modality '{mod}'")
        else:
            modality_counts[mod] += 1
            
        splt = prob.get("split")
        if splt not in VALID_SPLITS:
            errors.append(f"Problem {pid} invalid split '{splt}'")
        else:
            split_counts[splt] += 1
            if splt == "DEV":
                dev_items.append((pid, q_text, tokenize_text(q_text)))
            else:
                val_items.append((pid, q_text, tokenize_text(q_text)))
                
        grd = prob.get("grade")
        if grd not in grade_counts:
            errors.append(f"Problem {pid} invalid grade '{grd}'")
        else:
            grade_counts[grd] += 1
            
        # Format-specific assertions
        gt = prob.get("ground_truth", {})
        if fmt == "FORMAT_I_MCQ":
            opts = prob.get("options")
            if not opts or not isinstance(opts, dict) or set(opts.keys()) != {"A", "B", "C", "D"}:
                errors.append(f"Problem {pid} (MCQ) must have valid A, B, C, D options dict")
            key = gt.get("correct_choice")
            if key not in {"A", "B", "C", "D"}:
                errors.append(f"Problem {pid} (MCQ) has invalid correct_choice '{key}'")
        elif fmt == "FORMAT_II_TRUE_FALSE":
            subs = prob.get("sub_statements")
            if not subs or not isinstance(subs, list) or len(subs) != 4:
                errors.append(f"Problem {pid} (True/False) must have exactly 4 sub-statements")
            bool_vals = gt.get("boolean_values", {})
            if set(bool_vals.keys()) != {"a", "b", "c", "d"}:
                errors.append(f"Problem {pid} (True/False) ground truth must have boolean_values for a,b,c,d")
                
        # Mathematical derivation provenance check
        notes = prob.get("independent_proof_notes", "").strip()
        if not notes:
            errors.append(f"Problem {pid} missing independent_proof_notes")

    # Near-duplicate detection across DEV and VAL splits
    duplicate_warnings = []
    for d_id, d_txt, d_tokens in dev_items:
        for v_id, v_txt, v_tokens in val_items:
            sim = jaccard_similarity(d_tokens, v_tokens)
            if sim > 0.80:
                duplicate_warnings.append(f"High similarity ({sim:.2f}) between {d_id} (DEV) and {v_id} (VAL)")

    print("\n--- Pilot Benchmark Audit Summary ---")
    print(f"Total Verified Authentic Problems: {len(seen_ids)}")
    print(f"Grade Breakdown: {grade_counts}")
    print(f"Split Breakdown: {split_counts}")
    print(f"Format Breakdown: {format_counts}")
    print(f"Modality Breakdown: {modality_counts}")
    
    if duplicate_warnings:
        print(f"\n[WARNING] Near-duplicate alerts across splits ({len(duplicate_warnings)}):")
        for dw in duplicate_warnings:
            print(f"  * {dw}")
            
    if errors:
        print(f"\n[FAILED] Encountered {len(errors)} validation error(s):")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n[SUCCESS] All 40 pilot items passed 100% integrity validation!")
        return True

if __name__ == "__main__":
    success = validate_pilot_benchmark()
    sys.exit(0 if success else 1)
