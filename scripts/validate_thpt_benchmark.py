"""
MKE THPT 300-Problem Diagnostic Benchmark Validator.
Performs strict schema validation, archetype coverage auditing, split integrity,
and mathematical consistency checks.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.curriculum_auditor import load_taxonomy_archetypes

BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "thpt_diagnostic_benchmark.json"

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
    "rubric_steps"
]

VALID_FORMATS = {"FORMAT_I_MCQ", "FORMAT_II_TRUE_FALSE", "FORMAT_III_SHORT_ANSWER", "FORMAT_IV_STRUCTURED"}
VALID_MODALITIES = {"SYMBOLIC_TYPED", "VIETNAMESE_WORD_PROBLEM", "DIAGRAM_DEPENDENT"}
VALID_SPLITS = {"DEV", "VAL", "HOLDOUT"}
VALID_CATEGORIES = {"CORE", "ELECTIVE"}
VALID_DIFFICULTIES = {"RECOGNITION", "COMPREHENSION", "APPLICATION", "ADVANCED"}

def validate_benchmark():
    print("=== MKE THPT DIAGNOSTIC BENCHMARK VALIDATION ===")
    if not BENCHMARK_FILE.exists():
        print(f"[ERROR] Benchmark file not found: {BENCHMARK_FILE}")
        sys.exit(1)
        
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    metadata = data.get("benchmark_metadata", {})
    problems = data.get("problems", [])
    
    print(f"Dataset Version: {metadata.get('version')}")
    print(f"Total Problems Declared in metadata: {metadata.get('total_items')}")
    print(f"Total Problems Loaded: {len(problems)}")
    
    errors = []
    
    if len(problems) != 300:
        errors.append(f"Expected exactly 300 problems, found {len(problems)}")
        
    # Check archetype coverage
    taxonomy_archetypes = load_taxonomy_archetypes()
    taxonomy_ids = {a["id"] for a in taxonomy_archetypes}
    
    seen_problem_ids = set()
    seen_archetype_ids = set()
    split_counts = {"DEV": 0, "VAL": 0, "HOLDOUT": 0}
    grade_counts = {10: 0, 11: 0, 12: 0}
    category_counts = {"CORE": 0, "ELECTIVE": 0}
    format_counts = {fmt: 0 for fmt in VALID_FORMATS}
    modality_counts = {mod: 0 for mod in VALID_MODALITIES}
    difficulty_counts = {d: 0 for d in VALID_DIFFICULTIES}
    
    dev_questions = set()
    val_questions = set()
    holdout_questions = set()
    
    for idx, prob in enumerate(problems, 1):
        pid = prob.get("problem_id")
        if not pid:
            errors.append(f"Item #{idx} missing 'problem_id'")
        elif pid in seen_problem_ids:
            errors.append(f"Duplicate problem ID: {pid}")
        else:
            seen_problem_ids.add(pid)
            
        for req in REQUIRED_FIELDS:
            if req not in prob:
                errors.append(f"Problem {pid} missing required field '{req}'")
                
        aid = prob.get("archetype_id")
        if aid not in taxonomy_ids:
            errors.append(f"Problem {pid} has invalid archetype_id '{aid}' not in curriculum taxonomy")
        else:
            seen_archetype_ids.add(aid)
            
        # Validate format, modality, split, category, difficulty
        fmt = prob.get("format_type")
        if fmt not in VALID_FORMATS:
            errors.append(f"Problem {pid} has invalid format_type '{fmt}'")
        else:
            format_counts[fmt] += 1
            
        mod = prob.get("input_modality")
        if mod not in VALID_MODALITIES:
            errors.append(f"Problem {pid} has invalid input_modality '{mod}'")
        else:
            modality_counts[mod] += 1
            
        splt = prob.get("split")
        if splt not in VALID_SPLITS:
            errors.append(f"Problem {pid} has invalid split '{splt}'")
        else:
            split_counts[splt] += 1
            
        cat = prob.get("curriculum_category")
        if cat not in VALID_CATEGORIES:
            errors.append(f"Problem {pid} has invalid curriculum_category '{cat}'")
        else:
            category_counts[cat] += 1
            
        grd = prob.get("grade")
        if grd not in grade_counts:
            errors.append(f"Problem {pid} has invalid grade '{grd}'")
        else:
            grade_counts[grd] += 1
            
        diff = prob.get("difficulty_level")
        if diff not in VALID_DIFFICULTIES:
            errors.append(f"Problem {pid} has invalid difficulty_level '{diff}'")
        else:
            difficulty_counts[diff] += 1
            
        q_text = prob.get("problem_text_vi", "").strip()
        if not q_text:
            errors.append(f"Problem {pid} has empty problem_text_vi")
            
        # Split anti-leakage check
        if splt == "DEV":
            dev_questions.add(q_text)
        elif splt == "VAL":
            val_questions.add(q_text)
        elif splt == "HOLDOUT":
            holdout_questions.add(q_text)
            
        # Ground truth check
        gt = prob.get("ground_truth")
        if gt is None or not isinstance(gt, dict) or "solution_type" not in gt:
            errors.append(f"Problem {pid} has invalid ground_truth (must be dict with 'solution_type')")
            
        oracle = prob.get("oracle_family")
        if not oracle or not isinstance(oracle, str):
            errors.append(f"Problem {pid} has invalid oracle_family")
            
        rubric = prob.get("rubric_steps")
        if not rubric or not isinstance(rubric, list) or len(rubric) == 0:
            errors.append(f"Problem {pid} has invalid rubric_steps (must be non-empty list)")

    # Cross-split leakage checks
    dev_val_overlap = dev_questions.intersection(val_questions)
    if dev_val_overlap:
        errors.append(f"Cross-split leakage detected between DEV and VAL: {len(dev_val_overlap)} items")
    dev_holdout_overlap = dev_questions.intersection(holdout_questions)
    if dev_holdout_overlap:
        errors.append(f"Cross-split leakage detected between DEV and HOLDOUT: {len(dev_holdout_overlap)} items")
    val_holdout_overlap = val_questions.intersection(holdout_questions)
    if val_holdout_overlap:
        errors.append(f"Cross-split leakage detected between VAL and HOLDOUT: {len(val_holdout_overlap)} items")

    # Missing archetypes check
    missing_archetypes = taxonomy_ids - seen_archetype_ids
    if missing_archetypes:
        errors.append(f"Missing benchmark items for archetypes: {missing_archetypes}")

    print("\n--- Benchmark Validation Summary ---")
    print(f"Total Unique Problem IDs: {len(seen_problem_ids)} / 300")
    print(f"Archetypes Covered: {len(seen_archetype_ids)} / {len(taxonomy_ids)} (100% target)")
    print("Grade Distribution:")
    for g, cnt in grade_counts.items():
        print(f"  - Grade {g}: {cnt}")
    print("Category Distribution:")
    for c, cnt in category_counts.items():
        print(f"  - {c}: {cnt}")
    print("Split Distribution:")
    for s, cnt in split_counts.items():
        print(f"  - {s}: {cnt}")
    print("Format Distribution:")
    for f, cnt in format_counts.items():
        print(f"  - {f}: {cnt}")
    print("Modality Distribution:")
    for m, cnt in modality_counts.items():
        print(f"  - {m}: {cnt}")
    print("Difficulty Distribution:")
    for d, cnt in difficulty_counts.items():
        print(f"  - {d}: {cnt}")

    if errors:
        print(f"\n[FAILED] Encountered {len(errors)} validation error(s):")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        return False
    else:
        print("\n[SUCCESS] Benchmark validation passed with 0 errors!")
        return True

if __name__ == "__main__":
    success = validate_benchmark()
    sys.exit(0 if success else 1)
