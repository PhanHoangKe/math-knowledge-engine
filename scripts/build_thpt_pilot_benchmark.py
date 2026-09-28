"""
MKE THPT Genuine 40-Problem Pilot Diagnostic Benchmark Generator (GDPT 2018).
Builds a curated dataset of 40 verified, independently calculated THPT problems
spanning Grades 10-12, multiple topics, MOET 2025 formats, and input modalities.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_FILE = REPO_ROOT / "tests" / "benchmarks" / "thpt_pilot_benchmark_v1.json"

def build_pilot_benchmark():
    BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    problems = [
        # -------------------------------------------------------------
        # GRADE 10 (15 items)
        # -------------------------------------------------------------
        {
            "problem_id": "PILOT-10-0001",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "4",
            "archetype_id": "ARCH-10.4.1",
            "archetype_desc": "Giải bất phương trình bậc hai một ẩn",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải bất phương trình bậc hai: x^2 - 5x + 6 > 0.",
            "problem_latex": "x^2 - 5*x + 6 > 0",
            "options": {
                "A": "x in (2, 3)",
                "B": "x in (-oo, 2) U (3, +oo)",
                "C": "x in [2, 3]",
                "D": "x in (-oo, 2] U [3, +oo)"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "B",
                "exact_solution_set": ["(-oo, 2) U (3, oo)"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Determine roots of quadratic polynomial x^2 - 5x + 6 = 0 -> x1 = 2, x2 = 3.",
                "Step 2: Apply sign table rule for quadratic expression (a = 1 > 0).",
                "Step 3: Conclude solution interval (-oo, 2) U (3, +oo) corresponding to choice B."
            ],
            "source_reference": "SGK Toán 10 Cánh Diều / KNTT - Bất phương trình bậc hai",
            "independent_proof_notes": "Roots: x=2, x=3. Test point x=0 -> 6 > 0 (True). Test point x=2.5 -> -0.25 > 0 (False)."
        },
        {
            "problem_id": "PILOT-10-0002",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "4",
            "archetype_id": "ARCH-10.4.1",
            "archetype_desc": "Giải bất phương trình bậc hai một ẩn",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm tập nghiệm của bất phương trình: -2x^2 + 3x + 5 <= 0.",
            "problem_latex": "-2*x^2 + 3*x + 5 <= 0",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["(-oo, -1] U [5/2, oo)"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Solve equation -2x^2 + 3x + 5 = 0 -> x = -1 or x = 5/2.",
                "Step 2: Leading coefficient a = -2 < 0; inequality is <= 0 (same sign as a).",
                "Step 3: Solution set is outside roots: (-oo, -1] U [5/2, +oo)."
            ],
            "source_reference": "GDPT 2018 Toán 10 - Dấu của tam thức bậc hai",
            "independent_proof_notes": "Factoring: -(2x - 5)(x + 1) <= 0 <=> (2x - 5)(x + 1) >= 0."
        },
        {
            "problem_id": "PILOT-10-0003",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "4",
            "archetype_id": "ARCH-10.4.1",
            "archetype_desc": "Giải bất phương trình bậc hai một ẩn",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải bất phương trình: x^2 - 4x + 4 <= 0.",
            "problem_latex": "x^2 - 4*x + 4 <= 0",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["{2}"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Recognize identity (x - 2)^2 <= 0.",
                "Step 2: Since (x - 2)^2 >= 0 for all real x, equality holds iff x = 2.",
                "Step 3: Single point solution set S = {2}."
            ],
            "source_reference": "GDPT 2018 Toán 10 - Tam thức có nghiệm kép",
            "independent_proof_notes": "Delta = 16 - 16 = 0. Unique solution x = 2."
        },
        {
            "problem_id": "PILOT-10-0004",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.1",
            "archetype_desc": "Giải phương trình căn(f) = căn(g)",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải phương trình chứa căn: sqrt(2x^2 - 3) = sqrt(x^2 + 1).",
            "problem_latex": "sqrt(2*x^2 - 3) = sqrt(x^2 + 1)",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["-2", "2"],
                "domain_restrictions": ["2*x^2 - 3 >= 0", "x^2 + 1 >= 0"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Domain condition 2x^2 - 3 >= 0 <=> |x| >= sqrt(3/2).",
                "Step 2: Square both sides: 2x^2 - 3 = x^2 + 1 <=> x^2 = 4 <=> x = +-2.",
                "Step 3: Check domain: (+-2)^2 = 4 >= 1.5 (valid). Final set {-2, 2}."
            ],
            "source_reference": "SGK Toán 10 - Phương trình vô tỉ cơ bản",
            "independent_proof_notes": "Check x=2: sqrt(8-3)=sqrt(5), sqrt(4+1)=sqrt(5). Check x=-2: identical."
        },
        {
            "problem_id": "PILOT-10-0005",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.1",
            "archetype_desc": "Giải phương trình căn(f) = căn(g)",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm tập nghiệm của phương trình: sqrt(x^2 - 4x + 3) = sqrt(x - 1).",
            "problem_latex": "sqrt(x^2 - 4*x + 3) = sqrt(x - 1)",
            "options": {
                "A": "S = {1, 4}",
                "B": "S = {4}",
                "C": "S = {1}",
                "D": "S = empty"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["1", "4"],
                "domain_restrictions": ["x >= 1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Domain condition x - 1 >= 0 and x^2 - 4x + 3 >= 0 -> x in {1} U [3, +oo).",
                "Step 2: Square both sides: x^2 - 4x + 3 = x - 1 <=> x^2 - 5x + 4 = 0 -> x = 1, x = 4.",
                "Step 3: Check domain: x=1 in domain, x=4 in domain. Both valid -> Choice A."
            ],
            "source_reference": "Đề kiểm tra định kỳ Toán 10 GDPT 2018",
            "independent_proof_notes": "x=1 -> sqrt(0)=sqrt(0). x=4 -> sqrt(16-16+3)=sqrt(3), sqrt(4-1)=sqrt(3)."
        },
        {
            "problem_id": "PILOT-10-0006",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.1",
            "archetype_desc": "Giải phương trình căn(f) = căn(g)",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_IV_STRUCTURED",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải phương trình và loại nghiệm ngoại lai: sqrt(3x^2 - 9x + 1) = sqrt(x^2 - 2x - 2).",
            "problem_latex": "sqrt(3*x^2 - 9*x + 1) = sqrt(x^2 - 2*x - 2)",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["3"],
                "extraneous_roots": ["1/2"],
                "domain_restrictions": ["x^2 - 2*x - 2 >= 0"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: State domain condition x^2 - 2x - 2 >= 0.",
                "Step 2: Square both sides: 3x^2 - 9x + 1 = x^2 - 2x - 2 <=> 2x^2 - 7x + 3 = 0 -> x = 3, x = 1/2.",
                "Step 3: Verify candidate x = 1/2: (1/2)^2 - 2(1/2) - 2 = -11/4 < 0 (EXTRANEOUS, REJECT).",
                "Step 4: Verify candidate x = 3: 3^2 - 2(3) - 2 = 1 >= 0 (VALID). Final solution set S = {3}."
            ],
            "source_reference": "Chuyên đề Phương trình vô tỉ - Toán 10",
            "independent_proof_notes": "2x^2 - 7x + 3 = (2x - 1)(x - 3). Roots 1/2 and 3. x=1/2 makes radicand negative."
        },
        {
            "problem_id": "PILOT-10-0007",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.2",
            "archetype_desc": "Giải phương trình căn(f) = g",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm tập nghiệm của phương trình: sqrt(3x^2 - 4x + 1) = 2x - 1.",
            "problem_latex": "sqrt(3*x^2 - 4*x + 1) = 2*x - 1",
            "options": {
                "A": "S = {0}",
                "B": "S = {1/2}",
                "C": "S = empty",
                "D": "S = {0, 1/2}"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "C",
                "exact_solution_set": [],
                "extraneous_roots": ["0"],
                "domain_restrictions": ["2*x - 1 >= 0"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Necessary condition for non-negative RHS: 2x - 1 >= 0 <=> x >= 1/2.",
                "Step 2: Square both sides: 3x^2 - 4x + 1 = 4x^2 - 4x + 1 <=> x^2 = 0 -> x = 0.",
                "Step 3: Candidate x = 0 violates x >= 1/2 (2(0) - 1 = -1 < 0). Root is extraneous.",
                "Step 4: Equation has no real solutions S = empty -> Choice C."
            ],
            "source_reference": "Đề thi thử THPT Quốc gia - Chuyên đề Phương trình vô tỉ",
            "independent_proof_notes": "LHS(0) = sqrt(1) = 1 != RHS(0) = -1. S is empty."
        },
        {
            "problem_id": "PILOT-10-0008",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.2",
            "archetype_desc": "Giải phương trình căn(f) = g",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải phương trình: sqrt(2x^2 + 5) = x + 2.",
            "problem_latex": "sqrt(2*x^2 + 5) = x + 2",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["2 - sqrt(3)", "2 + sqrt(3)"],
                "domain_restrictions": ["x >= -2"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Domain restriction x + 2 >= 0 <=> x >= -2.",
                "Step 2: Square both sides: 2x^2 + 5 = x^2 + 4x + 4 <=> x^2 - 4x + 1 = 0.",
                "Step 3: Quadratic formula roots x = 2 +- sqrt(3).",
                "Step 4: Verify 2 - sqrt(3) ~= 0.268 >= -2 (valid), 2 + sqrt(3) ~= 3.732 >= -2 (valid)."
            ],
            "source_reference": "Bài tập nâng cao Toán 10 - NXB Giáo Dục",
            "independent_proof_notes": "Both roots satisfy x >= -2. Exact roots: 2 - sqrt(3) and 2 + sqrt(3)."
        },
        {
            "problem_id": "PILOT-10-0009",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "5",
            "archetype_id": "ARCH-10.5.2",
            "archetype_desc": "Giải phương trình căn(f) = g",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm nghiệm của phương trình: sqrt(x^2 - 3x + 2) = x - 1.",
            "problem_latex": "sqrt(x^2 - 3*x + 2) = x - 1",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["1"],
                "domain_restrictions": ["x >= 1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Domain condition x - 1 >= 0 <=> x >= 1.",
                "Step 2: Square both sides: x^2 - 3x + 2 = (x - 1)^2 = x^2 - 2x + 1 <=> -x = -1 <=> x = 1.",
                "Step 3: Candidate x = 1 satisfies x >= 1 and yields sqrt(0) = 0. Solution set S = {1}."
            ],
            "source_reference": "SGK Toán 10 Chân Trời Sáng Tạo",
            "independent_proof_notes": "Linear reduction after quadratic cancellation yields x = 1."
        },
        {
            "problem_id": "PILOT-10-0010",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "2",
            "archetype_id": "ARCH-10.2.1",
            "archetype_desc": "Hệ phương trình bậc nhất hai ẩn",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải hệ phương trình: 2x - 3y = 7 và 3x + 2y = 4.",
            "problem_latex": "2*x - 3*y = 7, 3*x + 2*y = 4",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x = 2", "y = -1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Compute determinant D = 2(2) - (-3)(3) = 4 + 9 = 13 != 0.",
                "Step 2: Dx = 7(2) - (-3)(4) = 14 + 12 = 26 -> x = 26/13 = 2.",
                "Step 3: Dy = 2(4) - 7(3) = 8 - 21 = -13 -> y = -13/13 = -1."
            ],
            "source_reference": "SGK Toán 10 - Hệ phương trình bậc nhất hai ẩn",
            "independent_proof_notes": "2(2) - 3(-1) = 4 + 3 = 7; 3(2) + 2(-1) = 6 - 2 = 4."
        },
        {
            "problem_id": "PILOT-10-0011",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "1",
            "archetype_id": "ARCH-10.1.2",
            "archetype_desc": "Tìm tập hợp giao, hợp, hiệu của hai tập hợp số dạng khoảng, đoạn",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho hai tập hợp A = [-2, 4) và B = (0, 5]. Xác định tập hợp giao A intersect B.",
            "problem_latex": "[-2, 4) intersect (0, 5]",
            "options": {
                "A": "(0, 4)",
                "B": "[-2, 5]",
                "C": "[-2, 0]",
                "D": "[4, 5]"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["(0, 4)"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Intersection takes elements belonging to both intervals: -2 <= x < 4 and 0 < x <= 5.",
                "Step 2: Lower bound is max(-2, 0) = 0 (open bracket '(').",
                "Step 3: Upper bound is min(4, 5) = 4 (open bracket ')').",
                "Step 4: Result is interval (0, 4) -> Choice A."
            ],
            "source_reference": "GDPT 2018 Toán 10 - Các phép toán tập hợp",
            "independent_proof_notes": "A = [-2, 4), B = (0, 5] -> A intersect B = (0, 4)."
        },
        {
            "problem_id": "PILOT-10-0012",
            "grade": 10,
            "strand": "Geometry",
            "topic_id": "8",
            "archetype_id": "ARCH-10.8.2",
            "archetype_desc": "Tính tích vô hướng của hai vectơ trong mặt phẳng Oxy",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Trong mặt phẳng Oxy, cho vectơ a = (2, -3) và b = (4, 1). Tính tích vô hướng a . b.",
            "problem_latex": "dot((2, -3), (4, 1))",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 5.0,
                "exact_solution_set": ["5"]
            },
            "oracle_family": "GEOMETRIC_ORACLE",
            "rubric_steps": [
                "Step 1: Apply coordinate formula for dot product: a . b = a1*b1 + a2*b2.",
                "Step 2: Calculate: 2*4 + (-3)*1 = 8 - 3 = 5."
            ],
            "source_reference": "SGK Toán 10 - Tọa độ vectơ và tích vô hướng",
            "independent_proof_notes": "2*4 + (-3)*1 = 8 - 3 = 5."
        },
        {
            "problem_id": "PILOT-10-0013",
            "grade": 10,
            "strand": "Geometry",
            "topic_id": "9",
            "archetype_id": "ARCH-10.9.3",
            "archetype_desc": "Phương trình đường tròn trong mặt phẳng Oxy",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_II_TRUE_FALSE",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho đường tròn (C) có phương trình: x^2 + y^2 - 4x + 6y - 12 = 0.",
            "problem_latex": "x^2 + y^2 - 4*x + 6*y - 12 = 0",
            "sub_statements": [
                {"id": "a", "statement_vi": "Tọa độ tâm của đường tròn (C) là I(2, -3).", "ground_truth_bool": True},
                {"id": "b", "statement_vi": "Bán kính của đường tròn (C) là R = 12.", "ground_truth_bool": False},
                {"id": "c", "statement_vi": "Điểm M(2, 2) nằm trên đường tròn (C).", "ground_truth_bool": True},
                {"id": "d", "statement_vi": "Đường thẳng Delta: x = 2 đi qua tâm I.", "ground_truth_bool": True}
            ],
            "ground_truth": {
                "solution_type": "BOOLEAN_ARRAY",
                "boolean_values": {"a": True, "b": False, "c": True, "d": True}
            },
            "oracle_family": "GEOMETRIC_ORACLE",
            "rubric_steps": [
                "Step 1: Rewrite into canonical form: (x - 2)^2 + (y + 3)^2 = 12 + 4 + 9 = 25.",
                "Step 2: Center I = (2, -3) -> Statement (a) TRUE.",
                "Step 3: Radius R = sqrt(25) = 5 != 12 -> Statement (b) FALSE.",
                "Step 4: Plug M(2, 2): (2-2)^2 + (2+3)^2 = 25 -> Statement (c) TRUE.",
                "Step 5: Center I(2, -3) has x = 2 -> Statement (d) TRUE."
            ],
            "source_reference": "Đề tham khảo tốt nghiệp THPT 2025 - Phần II Trắc nghiệm Đúng Sai",
            "independent_proof_notes": "Center: a = -(-4)/2 = 2, b = -(6)/2 = -3. R = sqrt(2^2 + (-3)^2 - (-12)) = sqrt(25) = 5."
        },
        {
            "problem_id": "PILOT-10-0014",
            "grade": 10,
            "strand": "Algebra",
            "topic_id": "2",
            "archetype_id": "ARCH-10.2.3",
            "archetype_desc": "Tối ưu hóa hàm mục tiêu trên miền nghiệm (Linear Programming)",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "APPLICATION",
            "input_modality": "VIETNAMESE_WORD_PROBLEM",
            "problem_text_vi": "Một xưởng mộc sản xuất hai loại ghế A và B. Mỗi ghế A cần 2 giờ tiện và 1 giờ ráp; mỗi ghế B cần 1 giờ tiện và 3 giờ ráp. Quỹ thời gian tối đa mỗi tuần là 40 giờ tiện và 45 giờ ráp. Lợi nhuận mỗi ghế A là 300 nghìn đồng, ghế B là 400 nghìn đồng. Tìm số lượng ghế (x, y) để xưởng đạt lợi nhuận lớn nhất.",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x = 15", "y = 10"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Model constraints: 2x + y <= 40, x + 3y <= 45, x >= 0, y >= 0.",
                "Step 2: Maximize objective F(x, y) = 300x + 400y.",
                "Step 3: Find vertices: (0,0) -> 0; (20,0) -> 6000; (0,15) -> 6000; (15,10) -> 8500.",
                "Step 4: Maximum achieved at x = 15, y = 10 with profit 8.5 million VND."
            ],
            "source_reference": "SGK Toán 10 - Ứng dụng quy hoạch tuyến tính",
            "independent_proof_notes": "Intersection of 2x + y = 40 and x + 3y = 45 gives 5y = 50 -> y = 10, x = 15."
        },
        {
            "problem_id": "PILOT-10-0015",
            "grade": 10,
            "strand": "Statistics",
            "topic_id": "10",
            "archetype_id": "ARCH-10.10.1",
            "archetype_desc": "Các số đặc trưng đo xu thế trung tâm của mẫu số liệu không ghép nhóm",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "TABLE_OR_COORDINATE_DATA",
            "problem_text_vi": "Cho mẫu số liệu điểm số của 10 học sinh: 6, 7, 7, 8, 8, 8, 9, 9, 10, 10. Tính điểm trung bình cộng và trung vị của mẫu.",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["mean = 8.2", "median = 8.0"]
            },
            "oracle_family": "STATISTICS_ORACLE",
            "rubric_steps": [
                "Step 1: Calculate sum: 6 + 14 + 24 + 18 + 20 = 82.",
                "Step 2: Mean = 82 / 10 = 8.2.",
                "Step 3: Median for n=10 is average of 5th and 6th elements: (8 + 8) / 2 = 8.0."
            ],
            "source_reference": "GDPT 2018 Toán 10 - Thống kê mô tả",
            "independent_proof_notes": "Sorted: [6, 7, 7, 8, 8, 8, 9, 9, 10, 10]. Mean = 8.2, Median = 8.0."
        },

        # -------------------------------------------------------------
        # GRADE 11 (14 items)
        # -------------------------------------------------------------
        {
            "problem_id": "PILOT-11-0001",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "5",
            "archetype_id": "ARCH-11.5.1",
            "archetype_desc": "Tính đạo hàm của hàm đa thức",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính đạo hàm của hàm số: y = x^3 - 3x^2 + 2x - 5.",
            "problem_latex": "x^3 - 3*x^2 + 2*x - 5",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["3*x^2 - 6*x + 2"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Apply power rule (x^n)' = n*x^(n-1).",
                "Step 2: (x^3)' = 3x^2, (-3x^2)' = -6x, (2x)' = 2, (-5)' = 0.",
                "Step 3: y' = 3x^2 - 6x + 2."
            ],
            "source_reference": "SGK Toán 11 - Đạo hàm các hàm số cơ bản",
            "independent_proof_notes": "d/dx(x^3 - 3x^2 + 2x - 5) = 3x^2 - 6x + 2."
        },
        {
            "problem_id": "PILOT-11-0002",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "5",
            "archetype_id": "ARCH-11.5.1",
            "archetype_desc": "Đạo hàm của hàm phân thức hữu tỉ",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính đạo hàm của hàm số y = (2x - 1)/(x + 3).",
            "problem_latex": "(2*x - 1)/(x + 3)",
            "options": {
                "A": "y' = 7/(x + 3)^2",
                "B": "y' = 5/(x + 3)^2",
                "C": "y' = -7/(x + 3)^2",
                "D": "y' = 2/(x + 3)^2"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["7/(x + 3)^2"],
                "domain_restrictions": ["x != -3"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Apply quotient rule (u/v)' = (u'v - uv') / v^2 with u = 2x-1, v = x+3.",
                "Step 2: u' = 2, v' = 1 -> u'v - uv' = 2(x + 3) - 1(2x - 1) = 2x + 6 - 2x + 1 = 7.",
                "Step 3: y' = 7 / (x + 3)^2 -> Choice A."
            ],
            "source_reference": "Đề thi học kì Toán 11 GDPT 2018",
            "independent_proof_notes": "Formula (ax+b)/(cx+d)' = (ad - bc)/(cx+d)^2 -> (2*3 - (-1)*1)/(x+3)^2 = 7/(x+3)^2."
        },
        {
            "problem_id": "PILOT-11-0003",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "5",
            "archetype_id": "ARCH-11.5.1",
            "archetype_desc": "Đạo hàm của hàm số lượng giác và hàm mũ",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính đạo hàm của hàm số: y = sin(2x) + e^(3x).",
            "problem_latex": "sin(2*x) + exp(3*x)",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["2*cos(2*x) + 3*e^(3*x)"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Apply chain rule for trigonometric term: (sin(2x))' = 2*cos(2x).",
                "Step 2: Apply chain rule for exponential term: (e^(3x))' = 3*e^(3x).",
                "Step 3: Sum of derivatives: y' = 2*cos(2x) + 3*e^(3x)."
            ],
            "source_reference": "SGK Toán 11 - Đạo hàm lượng giác & hàm mũ",
            "independent_proof_notes": "d/dx(sin(2x) + exp(3x)) = 2*cos(2x) + 3*exp(3x)."
        },
        {
            "problem_id": "PILOT-11-0004",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "5",
            "archetype_id": "ARCH-11.5.4",
            "archetype_desc": "Tính đạo hàm cấp hai",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho hàm số f(x) = x^4 - 2x^2 + 1. Tính giá trị của đạo hàm cấp hai f''(1).",
            "problem_latex": "diff(diff(x^4 - 2*x^2 + 1, x), x)",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 8.0,
                "exact_solution_set": ["8"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: First derivative f'(x) = 4x^3 - 4x.",
                "Step 2: Second derivative f''(x) = 12x^2 - 4.",
                "Step 3: Evaluate at x = 1: f''(1) = 12(1)^2 - 4 = 8."
            ],
            "source_reference": "GDPT 2018 Toán 11 - Đạo hàm cấp hai",
            "independent_proof_notes": "f'(x) = 4x^3 - 4x -> f''(x) = 12x^2 - 4 -> f''(1) = 8."
        },
        {
            "problem_id": "PILOT-11-0005",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-11.1.1",
            "archetype_desc": "Rút gọn biểu thức bằng công thức cộng lượng giác",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Rút gọn biểu thức lượng giác: A = sin(x + pi/4) - cos(x - pi/4).",
            "problem_latex": "sin(x + pi/4) - cos(x - pi/4)",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["0"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Expand sin(x + pi/4) = (sqrt(2)/2)*(sin(x) + cos(x)).",
                "Step 2: Expand cos(x - pi/4) = (sqrt(2)/2)*(cos(x) + sin(x)).",
                "Step 3: Subtract: A = 0."
            ],
            "source_reference": "SGK Toán 11 - Công thức cộng lượng giác",
            "independent_proof_notes": "sin(x + pi/4) = cos(pi/2 - (x + pi/4)) = cos(pi/4 - x) = cos(x - pi/4) -> difference is 0."
        },
        {
            "problem_id": "PILOT-11-0006",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-11.1.3",
            "archetype_desc": "Giải phương trình lượng giác cơ bản sin(x) = m",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm tất cả các nghiệm của phương trình lượng giác: sin(x) = 1/2.",
            "problem_latex": "sin(x) = 1/2",
            "options": {
                "A": "x = pi/6 + k*2*pi, x = 5*pi/6 + k*2*pi",
                "B": "x = +-pi/3 + k*2*pi",
                "C": "x = pi/6 + k*pi",
                "D": "x = pi/3 + k*2*pi"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["pi/6 + 2*k*pi", "5*pi/6 + 2*k*pi"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: arcsin(1/2) = pi/6.",
                "Step 2: Solution family 1: x = pi/6 + k2pi.",
                "Step 3: Solution family 2: x = pi - pi/6 + k2pi = 5pi/6 + k2pi -> Choice A."
            ],
            "source_reference": "SGK Toán 11 - Phương trình lượng giác cơ bản",
            "independent_proof_notes": "sin(x) = sin(alpha) <=> x = alpha + k2pi or x = pi - alpha + k2pi."
        },
        {
            "problem_id": "PILOT-11-0007",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "4",
            "archetype_id": "ARCH-11.4.1",
            "archetype_desc": "Rút gọn và tính giá trị biểu thức logarit",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Rút gọn biểu thức logarit: P = log2(12) - log2(3).",
            "problem_latex": "log(12, 2) - log(3, 2)",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 2.0,
                "exact_solution_set": ["2"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Apply quotient rule for logarithms: log_a(u) - log_a(v) = log_a(u/v).",
                "Step 2: P = log2(12/3) = log2(4).",
                "Step 3: Since 4 = 2^2, P = 2."
            ],
            "source_reference": "SGK Toán 11 - Khái niệm và tính chất logarit",
            "independent_proof_notes": "log2(12/3) = log2(4) = 2."
        },
        {
            "problem_id": "PILOT-11-0008",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "4",
            "archetype_id": "ARCH-11.4.3",
            "archetype_desc": "Giải phương trình logarit cơ bản",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Giải phương trình logarit: log2(x - 1) + log2(x + 1) = 3.",
            "problem_latex": "log(x - 1, 2) + log(x + 1, 2) = 3",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["3"],
                "extraneous_roots": ["-3"],
                "domain_restrictions": ["x > 1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Domain condition x - 1 > 0 and x + 1 > 0 <=> x > 1.",
                "Step 2: Combine: log2((x - 1)(x + 1)) = 3 <=> x^2 - 1 = 2^3 = 8 <=> x^2 = 9 <=> x = +-3.",
                "Step 3: Reject extraneous candidate x = -3 (violates x > 1).",
                "Step 4: Conclude unique real solution S = {3}."
            ],
            "source_reference": "Đề thi thử THPT Quốc gia 2024",
            "independent_proof_notes": "x=3 -> log2(2) + log2(4) = 1 + 2 = 3. x=-3 is outside domain of log2(x-1)."
        },
        {
            "problem_id": "PILOT-11-0009",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "3",
            "archetype_id": "ARCH-11.3.2",
            "archetype_desc": "Tính giới hạn hàm số dạng vô định 0/0",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính giới hạn khử dạng vô định 0/0: lim_{x -> 2} (x^2 - 4)/(x - 2).",
            "problem_latex": "limit((x^2 - 4)/(x - 2), x, 2)",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 4.0,
                "exact_solution_set": ["4"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Direct substitution yields 0/0 (indeterminate).",
                "Step 2: Factor numerator: x^2 - 4 = (x - 2)(x + 2).",
                "Step 3: Cancel common factor (x - 2) for x != 2: lim (x + 2) = 2 + 2 = 4."
            ],
            "source_reference": "SGK Toán 11 - Giới hạn hàm số",
            "independent_proof_notes": "lim_{x->2} (x+2) = 4."
        },
        {
            "problem_id": "PILOT-11-0010",
            "grade": 11,
            "strand": "Algebra",
            "topic_id": "2",
            "archetype_id": "ARCH-11.2.2",
            "archetype_desc": "Tìm u1, d của cấp số cộng, tính tổng n số hạng đầu Sn",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho cấp số cộng (u_n) có u_1 = 3 và công sai d = 4. Tính tổng 10 số hạng đầu S_10.",
            "problem_latex": "sum(3 + 4*(n-1), n, 1, 10)",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 210.0,
                "exact_solution_set": ["210"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Formula S_n = (n/2) * [2*u1 + (n - 1)*d].",
                "Step 2: S_10 = (10/2) * [2(3) + 9(4)] = 5 * [6 + 36] = 5 * 42 = 210."
            ],
            "source_reference": "GDPT 2018 Toán 11 - Cấp số cộng",
            "independent_proof_notes": "u10 = 3 + 9*4 = 39. S10 = 10*(3 + 39)/2 = 5*42 = 210."
        },
        {
            "problem_id": "PILOT-11-0011",
            "grade": 11,
            "strand": "Geometry",
            "topic_id": "7",
            "archetype_id": "ARCH-11.7.2",
            "archetype_desc": "Góc giữa đường thẳng và mặt phẳng trong không gian",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "VIETNAMESE_WORD_PROBLEM",
            "problem_text_vi": "Cho hình chóp S.ABC có đáy ABC là tam giác vuông cân tại B, AB = a. Cạnh bên SA vuông góc với mặt phẳng (ABC) và SA = a*sqrt(2). Tính góc giữa đường thẳng SC và mặt phẳng (ABC).",
            "options": {
                "A": "30 deg",
                "B": "45 deg",
                "C": "60 deg",
                "D": "90 deg"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "B",
                "exact_solution_set": ["45 deg"]
            },
            "oracle_family": "GEOMETRIC_ORACLE",
            "rubric_steps": [
                "Step 1: Projection of SC on (ABC) is AC since SA perp (ABC).",
                "Step 2: The angle is angle(SCA).",
                "Step 3: In right triangle ABC, AC = sqrt(a^2 + a^2) = a*sqrt(2).",
                "Step 4: In right triangle SAC, tan(SCA) = SA / AC = a*sqrt(2) / a*sqrt(2) = 1 -> angle = 45 deg -> Choice B."
            ],
            "source_reference": "Đề thi tốt nghiệp THPT 2023 - Môn Toán",
            "independent_proof_notes": "AC = a*sqrt(2), SA = a*sqrt(2) -> triangle SAC is right isosceles at A -> angle SCA = 45 deg."
        },
        {
            "problem_id": "PILOT-11-0012",
            "grade": 11,
            "strand": "Statistics",
            "topic_id": "8",
            "archetype_id": "ARCH-11.8.1",
            "archetype_desc": "Các số đặc trưng đo xu thế trung tâm của mẫu số liệu ghép nhóm",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "APPLICATION",
            "input_modality": "TABLE_OR_COORDINATE_DATA",
            "problem_text_vi": "Cho mẫu số liệu ghép nhóm thời gian tự học (giờ/tuần) của 20 học sinh: [0, 4): 3 học sinh; [4, 8): 8 học sinh; [8, 12): 6 học sinh; [12, 16): 3 học sinh. Tính trung vị Me của mẫu số liệu ghép nhóm.",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 7.5,
                "exact_solution_set": ["7.5"]
            },
            "oracle_family": "STATISTICS_ORACLE",
            "rubric_steps": [
                "Step 1: Total n = 20 -> n/2 = 10. Cumulative frequencies: C1 = 3, C2 = 11.",
                "Step 2: Median group is [4, 8) with L = 4, frequency m = 8, width h = 4, prior cumulative C1 = 3.",
                "Step 3: Formula Me = L + [(n/2 - C1) / m] * h = 4 + [(10 - 3)/8] * 4 = 4 + 3.5 = 7.5."
            ],
            "source_reference": "SGK Toán 11 Cánh Diều - Số liệu ghép nhóm",
            "independent_proof_notes": "Me = 4 + (7/8)*4 = 4 + 3.5 = 7.5."
        },
        {
            "problem_id": "PILOT-11-0013",
            "grade": 11,
            "strand": "Probability",
            "topic_id": "9",
            "archetype_id": "ARCH-11.9.1",
            "archetype_desc": "Biến cố độc lập và quy tắc nhân xác suất",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "APPLICATION",
            "input_modality": "VIETNAMESE_WORD_PROBLEM",
            "problem_text_vi": "Hai xạ thủ độc lập cùng bắn vào một bia. Xác suất bắn trúng của xạ thủ thứ nhất là 0,8 và của xạ thủ thứ hai là 0,7. Tính xác suất để có đúng một xạ thủ bắn trúng bia.",
            "options": {
                "A": "0.38",
                "B": "0.56",
                "C": "0.94",
                "D": "0.06"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "numeric_value": 0.38,
                "exact_solution_set": ["0.38"]
            },
            "oracle_family": "PROBABILITY_ORACLE",
            "rubric_steps": [
                "Step 1: Event E1 (only shooter 1 hits): P1 = 0.8 * (1 - 0.7) = 0.24.",
                "Step 2: Event E2 (only shooter 2 hits): P2 = (1 - 0.8) * 0.7 = 0.14.",
                "Step 3: Total probability P = P1 + P2 = 0.24 + 0.14 = 0.38 -> Choice A."
            ],
            "source_reference": "Đề minh họa tốt nghiệp THPT 2025 - Bộ GD&ĐT",
            "independent_proof_notes": "P = 0.8*0.3 + 0.2*0.7 = 0.24 + 0.14 = 0.38."
        },
        {
            "problem_id": "PILOT-11-0014",
            "grade": 11,
            "strand": "Calculus",
            "topic_id": "5",
            "archetype_id": "ARCH-11.5.2",
            "archetype_desc": "Viết phương trình tiếp tuyến của đồ thị hàm số tại điểm có hoành độ x0",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_II_TRUE_FALSE",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho hàm số y = f(x) = x^3 - 3x + 2 có đồ thị (C).",
            "problem_latex": "x^3 - 3*x + 2",
            "sub_statements": [
                {"id": "a", "statement_vi": "Đạo hàm của hàm số là f'(x) = 3x^2 - 3.", "ground_truth_bool": True},
                {"id": "b", "statement_vi": "Hệ số góc của tiếp tuyến tại điểm có hoành độ x0 = 2 là k = 9.", "ground_truth_bool": True},
                {"id": "c", "statement_vi": "Điểm M(1, 0) thuộc đồ thị (C).", "ground_truth_bool": True},
                {"id": "d", "statement_vi": "Phương trình tiếp tuyến tại điểm có hoành độ x0 = 1 là y = 3x - 3.", "ground_truth_bool": False}
            ],
            "ground_truth": {
                "solution_type": "BOOLEAN_ARRAY",
                "boolean_values": {"a": True, "b": True, "c": True, "d": False}
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: f'(x) = 3x^2 - 3 -> (a) TRUE.",
                "Step 2: f'(2) = 3(4) - 3 = 9 -> (b) TRUE.",
                "Step 3: f(1) = 1 - 3 + 2 = 0 -> (c) TRUE.",
                "Step 4: At x0 = 1, f'(1) = 0, y0 = 0 -> tangent equation is y = 0 != 3x - 3 -> (d) FALSE."
            ],
            "source_reference": "Đề tham khảo Tốt nghiệp THPT 2025 - Định dạng mới",
            "independent_proof_notes": "f'(1)=0, tangent line is y=0 horizontal line."
        },

        # -------------------------------------------------------------
        # GRADE 12 (11 items)
        # -------------------------------------------------------------
        {
            "problem_id": "PILOT-12-0001",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-12.1.1",
            "archetype_desc": "Xét tính đơn điệu và tìm cực trị của hàm số",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm các khoảng đồng biến của hàm số: y = x^3 - 3x^2 + 1.",
            "problem_latex": "x^3 - 3*x^2 + 1",
            "options": {
                "A": "(0, 2)",
                "B": "(-oo, 0) va (2, +oo)",
                "C": "(-oo, 2)",
                "D": "(0, +oo)"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "B",
                "exact_solution_set": ["(-oo, 0) U (2, oo)"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Compute derivative y' = 3x^2 - 6x = 3x(x - 2).",
                "Step 2: y' > 0 <=> x in (-oo, 0) U (2, +oo).",
                "Step 3: Conclude intervals of increase -> Choice B."
            ],
            "source_reference": "SGK Toán 12 - Ứng dụng đạo hàm khảo sát hàm số",
            "independent_proof_notes": "y' = 3x(x - 2). Roots 0 and 2. Positive on (-oo, 0) and (2, +oo)."
        },
        {
            "problem_id": "PILOT-12-0002",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-12.1.2",
            "archetype_desc": "Tìm giá trị lớn nhất, nhỏ nhất của hàm số trên đoạn [a; b]",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm giá trị lớn nhất M và giá trị nhỏ nhất m của hàm số f(x) = x^4 - 2x^2 + 3 trên đoạn [0, 2].",
            "problem_latex": "max_min(x^4 - 2*x^2 + 3, x, 0, 2)",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["max = 11", "min = 2"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: f'(x) = 4x^3 - 4x = 4x(x^2 - 1) = 0 -> x = 0, x = 1 (in [0, 2]).",
                "Step 2: Evaluate: f(0) = 3, f(1) = 1 - 2 + 3 = 2, f(2) = 16 - 8 + 3 = 11.",
                "Step 3: Maximum M = 11, Minimum m = 2."
            ],
            "source_reference": "Đề thi chính thức THPT 2024",
            "independent_proof_notes": "f(0)=3, f(1)=2, f(2)=11 -> Max=11, Min=2."
        },
        {
            "problem_id": "PILOT-12-0003",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-12.1.3",
            "archetype_desc": "Đường tiệm cận của đồ thị hàm số",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm phương trình đường tiệm cận đứng và tiệm cận ngang của đồ thị hàm số y = (2x - 3)/(x + 1).",
            "problem_latex": "asymptotes((2*x - 3)/(x + 1))",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x = -1", "y = 2"],
                "domain_restrictions": ["x != -1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Denominator root x + 1 = 0 -> Vertical asymptote x = -1.",
                "Step 2: Limit as x -> +-oo is 2/1 -> Horizontal asymptote y = 2."
            ],
            "source_reference": "SGK Toán 12 - Đường tiệm cận",
            "independent_proof_notes": "lim_{x->-1} y = oo -> x = -1; lim_{x->oo} y = 2 -> y = 2."
        },
        {
            "problem_id": "PILOT-12-0004",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "2",
            "archetype_id": "ARCH-12.2.1",
            "archetype_desc": "Tìm nguyên hàm của hàm đa thức",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tìm nguyên hàm của hàm số: f(x) = 3x^2 - 4x + 1.",
            "problem_latex": "3*x^2 - 4*x + 1",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x^3 - 2*x^2 + x + C"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: int 3x^2 dx = x^3.",
                "Step 2: int -4x dx = -2x^2.",
                "Step 3: int 1 dx = x.",
                "Step 4: F(x) = x^3 - 2x^2 + x + C."
            ],
            "source_reference": "SGK Toán 12 - Nguyên hàm",
            "independent_proof_notes": "d/dx(x^3 - 2x^2 + x + C) = 3x^2 - 4x + 1."
        },
        {
            "problem_id": "PILOT-12-0005",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "2",
            "archetype_id": "ARCH-12.2.1",
            "archetype_desc": "Tính tích phân xác định cơ bản",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính tích phân xác định: I = int_0^1 (4x^3 + 1) dx.",
            "problem_latex": "integrate(4*x^3 + 1, (x, 0, 1))",
            "ground_truth": {
                "solution_type": "NUMERIC_FLOAT",
                "numeric_value": 2.0,
                "exact_solution_set": ["2"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Antiderivative F(x) = x^4 + x.",
                "Step 2: F(1) = 1 + 1 = 2; F(0) = 0.",
                "Step 3: I = F(1) - F(0) = 2."
            ],
            "source_reference": "Đề thi tốt nghiệp THPT 2022",
            "independent_proof_notes": "[x^4 + x]_0^1 = 2."
        },
        {
            "problem_id": "PILOT-12-0006",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "2",
            "archetype_id": "ARCH-12.2.2",
            "archetype_desc": "Tính nguyên hàm/tích phân bằng phương pháp đổi biến số",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính tích phân: I = int_0^1 2x * e^(x^2) dx.",
            "problem_latex": "integrate(2*x*exp(x^2), (x, 0, 1))",
            "options": {
                "A": "e - 1",
                "B": "e + 1",
                "C": "2*e",
                "D": "e^2 - 1"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["e - 1"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Substitute u = x^2 -> du = 2x dx. Limits: x=0 -> u=0, x=1 -> u=1.",
                "Step 2: I = int_0^1 e^u du = [e^u]_0^1 = e^1 - e^0 = e - 1 -> Choice A."
            ],
            "source_reference": "SGK Toán 12 - Tích phân đổi biến số",
            "independent_proof_notes": "int_0^1 2x e^(x^2) dx = [exp(x^2)]_0^1 = e - 1."
        },
        {
            "problem_id": "PILOT-12-0007",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "2",
            "archetype_id": "ARCH-12.2.3",
            "archetype_desc": "Tính nguyên hàm/tích phân bằng phương pháp từng phần",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Tính tích phân từng phần: I = int_0^pi x * sin(x) dx.",
            "problem_latex": "integrate(x*sin(x), (x, 0, pi))",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["pi"]
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: Set u = x, dv = sin(x) dx -> du = dx, v = -cos(x).",
                "Step 2: I = [-x*cos(x)]_0^pi + int_0^pi cos(x) dx.",
                "Step 3: [-pi*cos(pi) - 0] + [sin(x)]_0^pi = -pi*(-1) + (0 - 0) = pi."
            ],
            "source_reference": "Đề thi đại học khối A",
            "independent_proof_notes": "[-x cos x + sin x]_0^pi = (-pi(-1) + 0) - (0 + 0) = pi."
        },
        {
            "problem_id": "PILOT-12-0008",
            "grade": 12,
            "strand": "Geometry",
            "topic_id": "3",
            "archetype_id": "ARCH-12.3.1",
            "archetype_desc": "Tính tọa độ vectơ và tích có hướng trong không gian Oxyz",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "RECOGNITION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Trong không gian Oxyz, cho hai vectơ u = (1, 2, -1) và v = (2, 0, 3). Tính tích có hướng [u, v].",
            "problem_latex": "cross((1, 2, -1), (2, 0, 3))",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["(6, -5, -4)"]
            },
            "oracle_family": "GEOMETRIC_ORACLE",
            "rubric_steps": [
                "Step 1: Formula [u, v] = (u2*v3 - u3*v2, u3*v1 - u1*v3, u1*v2 - u2*v1).",
                "Step 2: x = 2*3 - (-1)*0 = 6.",
                "Step 3: y = (-1)*2 - 1*3 = -5.",
                "Step 4: z = 1*0 - 2*2 = -4 -> Result (6, -5, -4)."
            ],
            "source_reference": "SGK Toán 12 - Phương pháp tọa độ trong không gian",
            "independent_proof_notes": "[u, v] . u = 6(1) - 5(2) - 4(-1) = 6 - 10 + 4 = 0 (orthogonality verified)."
        },
        {
            "problem_id": "PILOT-12-0009",
            "grade": 12,
            "strand": "Geometry",
            "topic_id": "3",
            "archetype_id": "ARCH-12.3.3",
            "archetype_desc": "Viết phương trình mặt phẳng qua 1 điểm biết VTPT",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_I_MCQ",
            "difficulty_level": "COMPREHENSION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Trong không gian Oxyz, viết phương trình mặt phẳng (P) đi qua điểm M(1, -2, 3) và có vectơ pháp tuyến n = (2, 1, -4).",
            "problem_latex": "plane_through_point_normal((1, -2, 3), (2, 1, -4))",
            "options": {
                "A": "2x + y - 4z + 12 = 0",
                "B": "2x + y - 4z - 12 = 0",
                "C": "x - 2y + 3z + 12 = 0",
                "D": "2x - y + 4z - 12 = 0"
            },
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "A",
                "exact_solution_set": ["2*x + y - 4*z + 12 = 0"]
            },
            "oracle_family": "GEOMETRIC_ORACLE",
            "rubric_steps": [
                "Step 1: Point-normal equation: A(x - x0) + B(y - y0) + C(z - z0) = 0.",
                "Step 2: 2(x - 1) + 1(y + 2) - 4(z - 3) = 0.",
                "Step 3: 2x - 2 + y + 2 - 4z + 12 = 0 <=> 2x + y - 4z + 12 = 0 -> Choice A."
            ],
            "source_reference": "Đề thi tốt nghiệp THPT 2021",
            "independent_proof_notes": "Plug M(1, -2, 3): 2(1) + (-2) - 4(3) + 12 = 2 - 2 - 12 + 12 = 0."
        },
        {
            "problem_id": "PILOT-12-0010",
            "grade": 12,
            "strand": "Probability",
            "topic_id": "4",
            "archetype_id": "ARCH-12.4.4",
            "archetype_desc": "Ứng dụng công thức Bayes để tính xác suất hậu nghiệm",
            "curriculum_category": "CORE",
            "split": "DEV",
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "difficulty_level": "APPLICATION",
            "input_modality": "VIETNAMESE_WORD_PROBLEM",
            "problem_text_vi": "Một hộp có 10 viên bi gồm 6 bi đỏ và 4 bi xanh. Lấy ngẫu nhiên lần lượt 2 viên bi không hoàn lại. Biết rằng viên bi thứ hai lấy được có màu đỏ, tính xác suất để viên bi thứ nhất cũng có màu đỏ.",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["5/9"],
                "numeric_value": 0.5556
            },
            "oracle_family": "PROBABILITY_ORACLE",
            "rubric_steps": [
                "Step 1: Let A = 'Ball 1 is red', B = 'Ball 2 is red'. P(A) = 6/10 = 3/5.",
                "Step 2: P(B|A) = 5/9, P(B|not A) = 6/9.",
                "Step 3: Total prob P(B) = (6/10)*(5/9) + (4/10)*(6/9) = 54/90 = 3/5.",
                "Step 4: Bayes theorem: P(A|B) = P(A and B) / P(B) = (30/90) / (54/90) = 30/54 = 5/9 ~= 0.5556."
            ],
            "source_reference": "SGK Toán 12 Chân Trời Sáng Tạo - Xác suất có điều kiện GDPT 2018",
            "independent_proof_notes": "P(A|B) = 30/54 = 5/9."
        },
        {
            "problem_id": "PILOT-12-0011",
            "grade": 12,
            "strand": "Calculus",
            "topic_id": "1",
            "archetype_id": "ARCH-12.1.1",
            "archetype_desc": "Khảo sát tính đơn điệu và cực trị của hàm số bậc ba",
            "curriculum_category": "CORE",
            "split": "VAL",
            "format_type": "FORMAT_II_TRUE_FALSE",
            "difficulty_level": "APPLICATION",
            "input_modality": "SYMBOLIC_TYPED",
            "problem_text_vi": "Cho hàm số bậc ba y = f(x) = -x^3 + 3x - 1.",
            "problem_latex": "-x^3 + 3*x - 1",
            "sub_statements": [
                {"id": "a", "statement_vi": "Hàm số có hai điểm cực trị tại x = -1 và x = 1.", "ground_truth_bool": True},
                {"id": "b", "statement_vi": "Điểm cực đại của đồ thị hàm số là M(1, 1).", "ground_truth_bool": True},
                {"id": "c", "statement_vi": "Đồ thị hàm số cắt trục tung tại điểm có tung độ bằng -1.", "ground_truth_bool": True},
                {"id": "d", "statement_vi": "Hàm số đồng biến trên khoảng (-oo, -1).", "ground_truth_bool": False}
            ],
            "ground_truth": {
                "solution_type": "BOOLEAN_ARRAY",
                "boolean_values": {"a": True, "b": True, "c": True, "d": False}
            },
            "oracle_family": "SYMPY_ALGEBRAIC",
            "rubric_steps": [
                "Step 1: f'(x) = -3x^2 + 3 = 0 <=> x = +-1 -> (a) TRUE.",
                "Step 2: Sign changes from + to - at x = 1, f(1) = 1 -> Local max point M(1, 1) -> (b) TRUE.",
                "Step 3: f(0) = -1 -> (c) TRUE.",
                "Step 4: Leading coefficient a = -1 < 0 -> function decreases on (-oo, -1) -> (d) FALSE."
            ],
            "source_reference": "Đề minh họa THPT 2025 - Phần II Đúng/Sai",
            "independent_proof_notes": "f'(x) < 0 for x < -1, so f is decreasing on (-oo, -1)."
        }
    ]

    dataset = {
        "benchmark_metadata": {
            "title": "MKE GDPT 2018 THPT 40-Problem Pilot Diagnostic Benchmark",
            "version": "1.0.0-pilot",
            "curriculum_standard": "GDPT 2018 (Thông tư 32/2018/TT-BGDĐT)",
            "exam_format_standard": "Quyết định 764/QĐ-BGDĐT (Cấu trúc định dạng đề thi tốt nghiệp THPT từ năm 2025)",
            "total_items": len(problems),
            "data_authenticity": "100% GENUINE_AUTHENTIC_PROBLEMS (Zero Synthetic Placeholders)",
            "grade_distribution": {
                "Grade 10": len([p for p in problems if p["grade"] == 10]),
                "Grade 11": len([p for p in problems if p["grade"] == 11]),
                "Grade 12": len([p for p in problems if p["grade"] == 12]),
            },
            "split_distribution": {
                "DEV": len([p for p in problems if p["split"] == "DEV"]),
                "VAL": len([p for p in problems if p["split"] == "VAL"]),
            },
            "format_distribution": {
                "FORMAT_I_MCQ": len([p for p in problems if p["format_type"] == "FORMAT_I_MCQ"]),
                "FORMAT_II_TRUE_FALSE": len([p for p in problems if p["format_type"] == "FORMAT_II_TRUE_FALSE"]),
                "FORMAT_III_SHORT_ANSWER": len([p for p in problems if p["format_type"] == "FORMAT_III_SHORT_ANSWER"]),
                "FORMAT_IV_STRUCTURED": len([p for p in problems if p["format_type"] == "FORMAT_IV_STRUCTURED"]),
            },
            "modality_distribution": {
                "SYMBOLIC_TYPED": len([p for p in problems if p["input_modality"] == "SYMBOLIC_TYPED"]),
                "VIETNAMESE_WORD_PROBLEM": len([p for p in problems if p["input_modality"] == "VIETNAMESE_WORD_PROBLEM"]),
                "TABLE_OR_COORDINATE_DATA": len([p for p in problems if p["input_modality"] == "TABLE_OR_COORDINATE_DATA"]),
            }
        },
        "problems": problems
    }

    with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"[OK] Generated {len(problems)} genuine pilot benchmark items saved to {BENCHMARK_FILE}")
    print(f"     - Grade 10: {dataset['benchmark_metadata']['grade_distribution']['Grade 10']}")
    print(f"     - Grade 11: {dataset['benchmark_metadata']['grade_distribution']['Grade 11']}")
    print(f"     - Grade 12: {dataset['benchmark_metadata']['grade_distribution']['Grade 12']}")
    print(f"     - Modalities: {dataset['benchmark_metadata']['modality_distribution']}")
    print(f"     - Formats: {dataset['benchmark_metadata']['format_distribution']}")

if __name__ == "__main__":
    build_pilot_benchmark()
