# THPT MATHEMATICS BENCHMARK SPECIFICATION
## Comprehensive Diagnostic & 1,000+ Problem Evaluation Framework (GDPT 2018)

**Author:** Antigravity (Implementation Engineer)  
**Standard:** GDPT 2018 Secondary Mathematics Curriculum & Official MOET Exam Format (Cấu trúc định dạng đề thi tốt nghiệp THPT từ năm 2025)  
**Target:** 300 Diagnostic Problems (Initial) $\longrightarrow$ 1,000+ Benchmark Suite (Full Scale)  
**Version:** 1.0.0 (Design Specification)  

---

## 1. Benchmark Architecture & Objectives

The **MKE THPT Benchmark Suite** is a standardized, reproducible, and verifiable evaluation harness designed to:
1. Objectively quantify mathematical problem-solving accuracy across Grades 10–12.
2. Verify exact algebraic domain restrictions, extraneous root rejection, and boundary safety.
3. Test compatibility with the official 2025+ Vietnamese National High School Exam question formats.
4. Prevent data contamination and overfitting through strict partition controls.

---

## 2. Multi-Dimensional Stratification Framework

### A. Grade Stratification
- **Grade 10:** 35% of total benchmark (Foundation algebra, 2D geometry, combinatorics, ungrouped statistics).
- **Grade 11:** 35% of total benchmark (Trigonometry, sequences, limits, logs/exponents, basic calculus, 3D spatial geometry, grouped statistics).
- **Grade 12:** 30% of total benchmark (Advanced calculus, 3D Oxyz coordinate geometry, advanced probability with Bayes, grouped dispersion).

### B. Question Format Stratification (Aligned with MOET 2025 Format)
- **Format I (Multiple Choice 4 Options - Trắc nghiệm 4 lựa chọn):** 40% of items. Exactly one correct choice ($A, B, C, D$).
- **Format II (Grouped True/False - Trắc nghiệm Đúng/Sai 4 ý):** 30% of items. One central problem context with 4 independent statements ($a, b, c, d$), scored based on $1/4, 2/4, 3/4, 4/4$ correct matching.
- **Format III (Short Answer - Trắc nghiệm trả lời ngắn):** 20% of items. Numeric, exact rational fraction, or closed-form answer entered into a designated field.
- **Format IV (Structured Multi-Step Written Solution - Tự luận phân bước):** 10% of items. Evaluates intermediate algebraic derivation steps, domain justifications, and final solution set.

### C. Cognitive Difficulty Stratification (Ma trận cấp độ nhận thức)
1. **Nhận biết (Recognition - Level 1):** 40% — Direct formula application, reading values from graphs/tables, basic definition checks.
2. **Thông hiểu (Comprehension - Level 2):** 30% — Single-transformation problems, standard equation/inequality solving, direct geometric calculations.
3. **Vận dụng (Application - Level 3):** 20% — Multi-step algebraic reduction, domain intersection, parameter $m$ conditions, basic word problems.
4. **Vận dụng cao (Advanced Application - Level 4):** 10% — Realistic applied optimization, geometric synthesis, multi-stage probabilistic modeling.

### D. Input Modality Stratification
- **Modality 1: Typed Symbolic Expressions / Equations** (60%): Clean mathematical notation in LaTeX or standard ASCII CAS input.
- **Modality 2: Vietnamese Natural-Language Word Problems** (30%): Contextual text in Vietnamese describing real-world physics, finance, geometry, or biological growth.
- **Modality 3: Diagram / Table-Dependent Questions** (10%): Questions referencing explicit coordinate drawings, function graphs, variation tables (bảng biến thiên), or grouped data frequency tables.

---

## 3. Data Split & Anti-Contamination Protocol

To ensure verifiable generalization without prompt or test leakage:

| Dataset Partition | Percentage | Initial Size (Diagnostic) | Full Scale Size | Purpose & Access Control |
| :--- | :---: | :---: | :---: | :--- |
| **`DEV` (Development)** | 50% | 150 items | 500 items | Public to engineers during active test-driven development. |
| **`VAL` (Validation)** | 25% | 75 items | 250 items | Used for release candidate qualification and parameter tuning. |
| **`HOLDOUT` (Hidden Test)** | 25% | 75 items | 250 items | **Strictly sealed & encrypted**. Evaluated only by independent automated auditor during release freeze. |

---

## 4. Benchmark Problem Schema (`thpt_problem_schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MKE_THPT_Benchmark_Item",
  "type": "object",
  "required": [
    "problem_id",
    "grade",
    "strand",
    "topic_id",
    "archetype_id",
    "format_type",
    "difficulty_level",
    "input_modality",
    "problem_text_vi",
    "ground_truth"
  ],
  "properties": {
    "problem_id": { "type": "string", "pattern": "^THPT-(10|11|12)-[0-9]{4}$" },
    "grade": { "type": "integer", "enum": [10, 11, 12] },
    "strand": { "type": "string" },
    "topic_id": { "type": "string" },
    "archetype_id": { "type": "string" },
    "format_type": { "type": "string", "enum": ["FORMAT_I_MCQ", "FORMAT_II_TRUE_FALSE", "FORMAT_III_SHORT_ANSWER", "FORMAT_IV_STRUCTURED"] },
    "difficulty_level": { "type": "string", "enum": ["RECOGNITION", "COMPREHENSION", "APPLICATION", "ADVANCED"] },
    "input_modality": { "type": "string", "enum": ["SYMBOLIC_TYPED", "VIETNAMESE_WORD_PROBLEM", "DIAGRAM_DEPENDENT"] },
    "problem_text_vi": { "type": "string" },
    "problem_latex": { "type": "string" },
    "options": {
      "type": "object",
      "properties": {
        "A": { "type": "string" },
        "B": { "type": "string" },
        "C": { "type": "string" },
        "D": { "type": "string" }
      }
    },
    "sub_statements": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "statement_vi": { "type": "string" },
          "ground_truth_bool": { "type": "boolean" }
        }
      }
    },
    "ground_truth": {
      "type": "object",
      "required": ["solution_type"],
      "properties": {
        "solution_type": { "type": "string", "enum": ["EXACT_SET", "NUMERIC_FLOAT", "CHOICE_KEY", "BOOLEAN_ARRAY", "STEP_SEQUENCE"] },
        "exact_solution_set": { "type": "array", "items": { "type": "string" } },
        "numeric_value": { "type": "number" },
        "numeric_tolerance": { "type": "number", "default": 0.0001 },
        "correct_choice": { "type": "string", "enum": ["A", "B", "C", "D"] },
        "domain_restrictions": { "type": "array", "items": { "type": "string" } },
        "extraneous_roots": { "type": "array", "items": { "type": "string" } },
        "key_steps": { "type": "array", "items": { "type": "string" } }
      }
    },
    "oracle_family": {
      "type": "string",
      "enum": ["EXACT_RATIONAL_SOLVER", "SYMPY_ALGEBRAIC", "INTERVAL_ARITHMETIC", "GEOMETRIC_ORACLE", "STATISTICS_ORACLE", "PROBABILITY_ORACLE"]
    },
    "source_reference": { "type": "string" }
  }
}
```

---

## 5. Domain-Specific Verification Oracles

| Mathematical Domain | Primary Solver Engine | Verification Oracle / Proof Method | Failure Handling & Tolerance |
| :--- | :--- | :--- | :--- |
| **Linear / Polynomial Equations** | `mke_native_v1` / `sympy_cas_v0` | Exact Rational Arithmetic & Root Back-Substitution ($f(r_i) \equiv 0$). | Exact rational comparison ($\frac{p}{q}$ irreducible). |
| **Rational Equations with Extraneous Roots** | Polynomial Reduction Engine | Original AST Denominator Evaluation ($D(r_i) \ne 0$) + Root Substitution. | Strict boolean exclusion ($D(r) = 0 \implies \text{EXTRANEOUS}$). |
| **Inequalities & Intervals** | Inequality Solver Engine | Critical Point Sign Test & Test Point Interval Evaluation. | Exact endpoint boundary inclusion ($[a, b)$ vs $(a, b]$). |
| **Calculus (Derivatives & Integrals)** | Calculus Rule Engine | SymPy Dual-Engine Symbolic Differentiation & Numerical Quad ($|I_{num} - I_{sym}| < 10^{-6}$). | Analytical antiderivative derivative check: $\frac{d}{dx} F(x) \equiv f(x)$. |
| **2D / 3D Coordinate Geometry** | Vector/Geometric Engine | Coordinate Vector Dot/Cross Products & Distance Invariants. | Exact radical/fractional coordinates. |
| **Statistics & Data Analysis** | Statistical Table Engine | Multi-Pass Accumulator for $\sum x_i, \sum x_i^2$, Exact Quartile Interpolation. | Float tolerance $\epsilon = 10^{-4}$ for irrational roots. |
| **Probability & Bayes** | Discrete Probability Engine | Tree Graph Verification ($\sum P(B_i) = 1$) & Exact Rational Fraction Math. | Probability bound check $0 \le P \le 1$. |

---

## 6. Initial 300-Item Diagnostic Distribution Matrix

```
Total Diagnostic Set: 300 Problems
├── Grade 10 (105 items)
│   ├── Algebra & Functions: 45 items
│   ├── 2D Geometry & Oxy: 35 items
│   └── Statistics & Probability: 25 items
├── Grade 11 (105 items)
│   ├── Trigonometry & Sequences: 35 items
│   ├── Limits, Log/Exp & Calculus: 40 items
│   ├── Spatial Geometry 3D: 20 items
│   └── Grouped Data & Prob: 10 items
└── Grade 12 (90 items)
    ├── Advanced Calculus & Curves: 45 items
    ├── 3D Coordinate Oxyz: 25 items
    └── Conditional Prob & Bayes: 20 items
```

---

## 7. Public Exam Provenance & Copyright Compliance

1. **Official Exam References:**
   - Đề tham khảo Kỳ thi Tốt nghiệp THPT 2025 môn Toán (Bộ Giáo dục và Đào tạo).
   - Đề thi chính thức Tốt nghiệp THPT 2020–2024.
   - Đề thi học sinh giỏi các tỉnh/thành phố và đề thi thử của các trường THPT Chuyên (preserve source metadata citation).
2. **Original Newly Authored Parallels:**
   - For items with restrictive third-party copyright, newly authored isomorphic problems (same mathematical archetype, varied coefficients and real-world contexts) are authored to guarantee open reproducibility.
