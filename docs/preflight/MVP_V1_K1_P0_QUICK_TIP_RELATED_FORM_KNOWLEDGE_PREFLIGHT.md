# MKE PRODUCT — K1-P0-R2 QUICK TIP & RELATED PROBLEM FORM KNOWLEDGE AUTHORITY PREFLIGHT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-03  
**Target Milestone:** K1-P0-R2 Exact Contract & Versioning Closeout  
**Branch:** `product/mvp-v1-k1-p0-r2-exact-contract-closeout`  
**Parent Baseline Commit:** `63090c7f652312060d9e0f655b2198c4fa7dec41` (Audited K1-P0-R1 Head)  
**Accepted Owner UI Baseline SHA:** `0a6ba07ddb1995891796d5b826424a2a1ff3531a`  
**Frozen S3 Knowledge Dataset SHA:** `e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`  
**Preflight Status:** `READY FOR FINAL INDEPENDENT K1-P0-R2 AUDIT`  

---

## 1. Executive Summary & Strict UI Freeze Statement

### 1.1 UI Status Statement
> **UI STATUS: FROZEN — NO FRONTEND CHANGES AUTHORIZED**  
> The current MKE frontend and user interface layout is formally considered **ACCEPTED** by the Project Owner.  
> ZERO modifications are authorized under `src/frontend/**`.  
> No JSX, CSS, TypeScript, i18n, or frontend tests are modified in this milestone.  
> All K1 preflight work is performed in an isolated Git worktree (`D:/mke_k1_worktree`) to guarantee the primary working tree and its running Vite server remain 100% untouched.

### 1.2 Purpose of Milestone K1
MKE will enrich its deterministic knowledge graph by introducing two new authoritative mathematical and pedagogical entities:
1. **Quick Solving Tips / Shortcuts (`QuickTipKnowledge`)**: Deterministic and heuristic-bounded pedagogical shortcuts (e.g., $a+b+c=0 \implies x_1=1, x_2=c/a$, even linear coefficient reduced discriminant $\Delta'$, Viète integer factoring).
2. **Related Problem Forms (`RelatedProblemFormKnowledge`)**: Canonical structures and classifications of mathematical problems that share solution strategies, prerequisites, and tips.

### 1.3 Scope of K1-P0-R2 Closeout
- **AUTHORIZED:** Complete architectural, schema, closed condition DSL, provenance, graph linkage, API contract, and candidate matrix preflight specification.
- **NOT AUTHORIZED (ZERO RUNTIME MUTATION):**
  - No production backend code changes under `src/mke_product/**`.
  - No frontend code changes under `src/frontend/**`.
  - No dataset mutation to `src/mke_product/knowledge/data/**`.
  - No test changes under `tests/**`.
  - No S3-05 graph rendering / visualization implementation.

---

## 2. Primary Product Goals & Learner Inquiries

The K1 knowledge architecture enables MKE to answer authentic student and educator questions deterministically without frontend fabrication and without LLM hallucinations:

1. *"Có mẹo giải nhanh nào cho bài này?"* (Are there quick solving shortcuts for this equation?)
2. *"Khi nào dùng mẹo này?"* (Under what mathematical conditions is this shortcut valid?)
3. *"Vì sao mẹo này đúng?"* (What is the formal mathematical proof/basis of this shortcut?)
4. *"Mẹo này không được dùng khi nào?"* (When does this shortcut fail or cause fallacies?)
5. *"Phương pháp này áp dụng cho những dạng bài nào?"* (What problem forms can this method solve?)
6. *"Dạng bài nào tương tự để luyện tập?"* (What related problem forms and curated practice examples exist?)
7. *"Bài này thuộc dạng nào?"* (Which canonical problem form does this equation match?)
8. *"Mẹo/phương pháp này liên quan đến kiến thức nào?"* (Which prerequisite concepts, formulas, and theorems are connected?)

---

## 3. Exact S3 Type Reuse & New K1 Type Declarations

### 3.1 Actual Locked S3 Types (`src/mke_product/knowledge/schemas.py`)
K1 strictly reuses the exact Pydantic v2 types validated and production-locked in Milestone S3:

- **`LocalizedText`**: Symmetric bilingual text container (`vi: str`, `en: str`).
- **`CurriculumMappingStatus`**: Enum with values `VERIFIED_MAPPING`, `PROVISIONAL_MAPPING`.
- **`CurriculumRef`**: Exact S3 model with fields:
  - `framework: str`
  - `subject: str`
  - `grade_band: str`
  - `topic: str`
  - `competency_ref: Optional[str] = None`
  - `source_document: str`
  - `source_locator: str` *(Strictly `source_locator`, NOT `lesson_locator`)*
  - `status: CurriculumMappingStatus`
- **`ProvenanceStatus`**: Enum with values `VERIFIED`, `UNVERIFIED`.
- **`SourceProvenance`**: Model with fields:
  - `source_id: str`
  - `source_type: str`
  - `title: str`
  - `author_or_institution: str`
  - `publication_year: Optional[int] = None`
  - `locator: str`
  - `verification_status: ProvenanceStatus`
- **Entity Foreign Key Pattern:** Entities use `provenance_refs: List[str]` referencing centralized `SourceProvenance.source_id` keys in `provenance.json`, and `curriculum_refs: List[CurriculumRef]`.

### 3.2 New K1-Owned Types (Not in S3)
The following types are **NEW IN K1** and will be declared in K1-01:
- **`KnowledgeEntityStatus`**: Strict governance lifecycle enum:
  ```python
  class KnowledgeEntityStatus(str, Enum):
      PROVISIONAL = "PROVISIONAL"
      VERIFIED = "VERIFIED"
      DEPRECATED = "DEPRECATED"
  ```
- **`DifficultyLevel`**: Pedagogical difficulty enum for problem forms:
  ```python
  class DifficultyLevel(str, Enum):
      BASIC = "BASIC"
      INTERMEDIATE = "INTERMEDIATE"
      ADVANCED = "ADVANCED"
  ```
- **`TipCategory`**: Taxonomic categorization for shortcuts:
  ```python
  class TipCategory(str, Enum):
      COEFFICIENT_RELATION = "COEFFICIENT_RELATION"
      REDUCED_ARITHMETIC = "REDUCED_ARITHMETIC"
      ROOT_PRODUCT_SUM = "ROOT_PRODUCT_SUM"
      SPECIAL_STRUCTURE = "SPECIAL_STRUCTURE"
      TRANSFORMATION = "TRANSFORMATION"
  ```

---

## 4. Closed Condition DSL & Predicate Definitions

To guarantee 100% deterministic mathematical evaluation, conditions are expressed via a closed, typed expression model over atomic predicates.

### 4.1 Predicate ID Enumeration (`PredicateId`)
```python
from enum import Enum

class PredicateId(str, Enum):
    A_NONZERO = "A_NONZERO"
    A_EQ_ONE = "A_EQ_ONE"
    B_NONZERO = "B_NONZERO"
    C_NONZERO = "C_NONZERO"
    B_EVEN_INTEGER = "B_EVEN_INTEGER"
    DISCRIMINANT_NONNEGATIVE = "DISCRIMINANT_NONNEGATIVE"
    DISCRIMINANT_RATIONAL_SQUARE = "DISCRIMINANT_RATIONAL_SQUARE"
    A_PLUS_B_PLUS_C_ZERO = "A_PLUS_B_PLUS_C_ZERO"
    A_MINUS_B_PLUS_C_ZERO = "A_MINUS_B_PLUS_C_ZERO"
    B_ZERO = "B_ZERO"
    C_ZERO = "C_ZERO"
    ROOTS_ARE_INTEGERS = "ROOTS_ARE_INTEGERS"
```

### 4.2 Exact Rational Semantics of All Defined Predicates
Every predicate is formally defined over exact rational polynomial coefficients $a, b, c \in \mathbb{Q}$ ($a = \frac{n_a}{d_a}, b = \frac{n_b}{d_b}, c = \frac{n_c}{d_c}$ with $d_i \ge 1$):

| Predicate ID | Mathematical Definition | Exact Backend Implementation Rule |
| :--- | :--- | :--- |
| `A_NONZERO` | $a \neq 0$ | `a != 0` |
| `A_EQ_ONE` | $a = 1$ | `a == 1` (`n_a == 1 and d_a == 1`) |
| `B_NONZERO` | $b \neq 0$ | `b != 0` (`n_b != 0`) |
| `C_NONZERO` | $c \neq 0$ | `c != 0` (`n_c != 0`) |
| `B_EVEN_INTEGER` | $b \in \mathbb{Z} \land b \equiv 0 \pmod 2$ | `d_b == 1 and (n_b % 2 == 0)` |
| `DISCRIMINANT_NONNEGATIVE` | $\Delta = b^2 - 4ac \ge 0$ | `(b * b - 4 * a * c) >= 0` |
| `DISCRIMINANT_RATIONAL_SQUARE` | $\exists q \in \mathbb{Q}_{\ge 0}: q^2 = \Delta$ | `delta >= 0 and is_square(delta.num) and is_square(delta.den)` |
| `A_PLUS_B_PLUS_C_ZERO` | $a + b + c = 0$ | `(a + b + c) == 0` |
| `A_MINUS_B_PLUS_C_ZERO` | $a - b + c = 0$ | `(a - b + c) == 0` |
| `B_ZERO` | $b = 0$ | `b == 0` (`n_b == 0`) |
| `C_ZERO` | $c = 0$ | `c == 0` (`n_c == 0`) |
| `ROOTS_ARE_INTEGERS` | $\Delta = q^2 (q \in \mathbb{Q}) \land \frac{-b \pm q}{2a} \in \mathbb{Z}$ | `DISCRIMINANT_RATIONAL_SQUARE and ((-b - q)/(2*a)).is_integer() and ((-b + q)/(2*a)).is_integer()` |

### 4.3 `ConditionExpr` Model & Complete Evaluation Semantics
```python
from typing import List
from pydantic import BaseModel, ConfigDict, Field

class ConditionExpr(BaseModel):
    """
    Closed boolean predicate expression container.
    Evaluated with short-circuiting deterministic boolean logic.
    """
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    all_of: List[PredicateId] = Field(
        default_factory=list,
        description="All predicates in this list must evaluate to TRUE"
    )
    any_of: List[PredicateId] = Field(
        default_factory=list,
        description="If non-empty, at least one predicate in this list must evaluate to TRUE"
    )
    none_of: List[PredicateId] = Field(
        default_factory=list,
        description="All predicates in this list must evaluate to FALSE"
    )
```

**Evaluation Semantics Specification:**
1. **`all_of` clause:** Passes if every predicate in `all_of` is `TRUE`. (If empty, passes unconditionally).
2. **`any_of` clause:** If empty, imposes no requirement. If non-empty, passes if at least one predicate in `any_of` is `TRUE`.
3. **`none_of` clause:** Passes if every predicate in `none_of` is `FALSE`. (If empty, passes unconditionally).
4. **Overall Condition:** The expression evaluates to `TRUE` if and only if all three clauses (`all_of`, `any_of`, `none_of`) pass.
5. **UNKNOWN Propagation Policy:** Exact rational quadratic predicates evaluate deterministically to `TRUE` or `FALSE`. If a predicate cannot be evaluated (e.g. unsupported AST or missing coefficients), the predicate returns `UNKNOWN`. If any predicate in an active clause is `UNKNOWN` and determines the outcome, the overall expression evaluates to `UNKNOWN`. `UNKNOWN` is never silently coerced to `FALSE`.

---

## 5. `QuickTipKnowledge` Schema Design

```python
from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from mke_product.knowledge.schemas import LocalizedText, CurriculumRef

class QuickTipKnowledge(BaseModel):
    """
    Static pedagogical knowledge entity describing an authoritative solving shortcut.
    Immutable, source-backed, bilingual, and linked to machine-readable conditions.
    """
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tip_id: str = Field(
        ...,
        description="Canonical uppercase ID (e.g. QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO)"
    )
    title: LocalizedText = Field(
        ...,
        description="Bilingual title of the quick tip"
    )
    summary: LocalizedText = Field(
        ...,
        description="Concise pedagogical summary of the shortcut"
    )
    category: TipCategory = Field(
        ...,
        description="Taxonomic classification of the shortcut"
    )

    # Machine-Readable Condition Authority
    applicability_condition: ConditionExpr = Field(
        ...,
        description="Closed deterministic condition expression required for mathematical validity"
    )

    # Recognition & Mathematical Foundation
    recognition_guidance: LocalizedText = Field(
        ...,
        description="Static pedagogical explanation of how a student identifies when to consider this tip"
    )
    explanation: LocalizedText = Field(
        ...,
        description="Rigorous mathematical explanation and proof of why the shortcut is correct"
    )
    quick_steps: List[LocalizedText] = Field(
        ...,
        description="Ordered sequence of execution steps when applying this tip"
    )

    # Domain Boundaries & Safety
    valid_scope: LocalizedText = Field(
        ...,
        description="Explicit mathematical domain and conditions where this shortcut is strictly valid"
    )
    invalid_scope: LocalizedText = Field(
        ...,
        description="Explicit boundary cases, caveats, and common misconceptions where this tip is INVALID"
    )

    # Relational Graph Foreign Keys
    related_method_ids: List[str] = Field(
        default_factory=list,
        description="Canonical method IDs related to this shortcut (e.g. QUAD_VIETE_SPECIAL_SUM)"
    )
    related_concept_ids: List[str] = Field(
        default_factory=list,
        description="Prerequisite ConceptKnowledge IDs"
    )
    formula_refs: List[str] = Field(
        default_factory=list,
        description="Referenced FormulaKnowledge IDs"
    )
    theorem_refs: List[str] = Field(
        default_factory=list,
        description="Referenced TheoremKnowledge IDs"
    )
    related_problem_form_ids: List[str] = Field(
        default_factory=list,
        description="Problem forms where this shortcut is applicable or candidate"
    )

    # Provenance & Curriculum
    curriculum_refs: List[CurriculumRef] = Field(
        default_factory=list,
        description="National curriculum standards mapping with source_locator"
    )
    provenance_refs: List[str] = Field(
        ...,
        min_length=1,
        description="List of authoritative source IDs in centralized provenance.json"
    )

    status: KnowledgeEntityStatus = Field(
        default=KnowledgeEntityStatus.VERIFIED,
        description="K1 Entity governance status (NEW in K1)"
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version string of the entity"
    )
```

---

## 6. `RelatedProblemFormKnowledge` Schema Design

```python
from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from mke_product.knowledge.schemas import LocalizedText, CurriculumRef

class RelatedProblemFormKnowledge(BaseModel):
    """
    Static pedagogical entity defining a problem archetype / form (Dạng bài).
    """
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    form_id: str = Field(
        ...,
        description="Unique canonical form identifier (e.g. QUAD_FORM_SPECIAL_SUM_ZERO)"
    )
    title: LocalizedText = Field(
        ...,
        description="Bilingual title of the problem form"
    )
    summary: LocalizedText = Field(
        ...,
        description="Pedagogical description of the problem form"
    )
    canonical_structure_latex: str = Field(
        ...,
        description="Generalized LaTeX template (e.g. 'ax^2 + bx + c = 0 \\quad (a + b + c = 0)')"
    )
    recognition_condition: ConditionExpr = Field(
        ...,
        description="Closed deterministic condition expression for mathematical classification"
    )
    recognition_guidance: LocalizedText = Field(
        ...,
        description="Pedagogical clues for students to recognize this form"
    )

    # Strategy & Tool Connections (Distinct Semantics)
    related_method_ids: List[str] = Field(
        default_factory=list,
        description="Methods conceptually related or applicable to this form"
    )
    guaranteed_method_ids: List[str] = Field(
        default_factory=list,
        description="Methods mathematically guaranteed to solve all equations of this form"
    )
    related_tip_ids: List[str] = Field(
        default_factory=list,
        description="Candidate quick tips worth evaluating at runtime for instances of this form"
    )
    guaranteed_tip_ids: List[str] = Field(
        default_factory=list,
        description="Quick tips mathematically guaranteed by this form's recognition condition"
    )

    # Foundations
    prerequisite_concept_ids: List[str] = Field(
        default_factory=list,
        description="Prerequisite concept IDs"
    )
    formula_refs: List[str] = Field(
        default_factory=list,
        description="Formula IDs used when solving this form"
    )
    theorem_refs: List[str] = Field(
        default_factory=list,
        description="Theorem IDs supporting this form"
    )

    # Curated Example Reference Placeholders (Deferred Policy)
    worked_example_ids: List[str] = Field(
        default_factory=list,
        description="Stable IDs to curated worked examples (MUST be empty in K1-02 until Example Registry exists)"
    )
    practice_example_ids: List[str] = Field(
        default_factory=list,
        description="Stable IDs to curated practice problems (MUST be empty in K1-02 until Example Registry exists)"
    )

    # Curriculum & Governance
    curriculum_refs: List[CurriculumRef] = Field(
        default_factory=list,
        description="Curriculum standards references with source_locator"
    )
    provenance_refs: List[str] = Field(
        ...,
        min_length=1,
        description="Authoritative source provenance IDs in provenance.json"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.BASIC,
        description="Relative pedagogical difficulty (NEW in K1)"
    )
    status: KnowledgeEntityStatus = Field(
        default=KnowledgeEntityStatus.VERIFIED,
        description="K1 Entity governance status (NEW in K1)"
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version"
    )
```

---

## 7. Problem Form Overlap Policy & General Form Naming

### 7.1 Multi-Match Overlap Policy
Problem forms are **NOT** mutually exclusive. An equation may simultaneously match multiple structural archetypes.
For example, the equation:
$$x^2 - 5x + 6 = 0$$
simultaneously satisfies:
1. `QUAD_FORM_GENERAL_QUADRATIC` ($a \neq 0$)
2. `QUAD_FORM_COMPLETE_QUADRATIC` ($a \neq 0, b \neq 0, c \neq 0$)
3. `QUAD_FORM_MONIC_INTEGER_FACTORABLE` ($a = 1 \land \text{roots} \in \mathbb{Z}$)

The future `ProblemFormEvaluator` evaluates all registered forms independently and returns all matching forms. MKE does not force a single arbitrary winner.

### 7.2 Semantically Precise Problem Form Naming
- **`QUAD_FORM_GENERAL_QUADRATIC`:**
  - Title VI: *"Phương trình bậc hai tổng quát"*
  - Recognition: `all_of: [PredicateId.A_NONZERO]`
- **`QUAD_FORM_COMPLETE_QUADRATIC`:**
  - Title VI: *"Phương trình bậc hai đầy đủ"*
  - Recognition: `all_of: [PredicateId.A_NONZERO, PredicateId.B_NONZERO, PredicateId.C_NONZERO]`

---

## 8. Dynamic Assessment Contracts (`QuickTipAssessmentView` & `ProblemFormAssessmentView`)

### 8.1 `QuickTipAssessmentView`
```python
from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field

class TipApplicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"

class TipRecommendation(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    NEUTRAL = "NEUTRAL"
    DISCOURAGED = "DISCOURAGED"

class TipExecutionAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"

class QuickTipAssessmentView(BaseModel):
    """Runtime assessment of a quick tip against a specific normalized equation."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tip_id: str = Field(..., description="Target tip identifier")
    mathematical_applicability: TipApplicability = Field(..., description="Objective applicability state")
    pedagogical_recommendation: TipRecommendation = Field(..., description="Pedagogical preference state")
    execution_availability: TipExecutionAvailability = Field(..., description="Backend execution availability")
    matched_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to TRUE")
    failed_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to FALSE")
    unknown_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to UNKNOWN")
    reason_codes: List[str] = Field(default_factory=list, description="Canonical deterministic reason codes")
```

### 8.2 `ProblemFormAssessmentView`
```python
class FormMatchStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    UNKNOWN = "UNKNOWN"

class ProblemFormAssessmentView(BaseModel):
    """Runtime assessment of a problem archetype match against a specific equation."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    form_id: str = Field(..., description="Target form identifier")
    mathematical_match: FormMatchStatus = Field(..., description="Whether equation matches this form archetype")
    matched_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to TRUE")
    failed_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to FALSE")
    unknown_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to UNKNOWN")
    reason_codes: List[str] = Field(default_factory=list, description="Canonical deterministic reason codes")
```

---

## 9. Mathematical Analysis of Canonical Shortcuts & Soundness

### 9.1 Special Case $a + b + c = 0$
- **Mathematical Basis:**
  Let $P(x) = ax^2 + bx + c$.  
  Evaluating at $x = 1$:  
  $$P(1) = a(1)^2 + b(1) + c = a + b + c$$
  If $a + b + c = 0$, then $P(1) = 0 \implies x_1 = 1$ is an exact root.  
  By Viète's Theorem ($x_1 \cdot x_2 = \frac{c}{a}$):  
  $$1 \cdot x_2 = \frac{c}{a} \implies x_2 = \frac{c}{a}$$
- **Applicability Condition:** `ConditionExpr(all_of=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO])`
- **Valid Domain:** All quadratics $ax^2 + bx + c = 0$ ($a \neq 0$) where coefficients sum to zero.

---

### 9.2 Special Case $a - b + c = 0$
- **Mathematical Basis:**
  Evaluating $P(x) = ax^2 + bx + c$ at $x = -1$:  
  $$P(-1) = a(-1)^2 + b(-1) + c = a - b + c$$
  If $a - b + c = 0$, then $P(-1) = 0 \implies x_1 = -1$ is an exact root.  
  By Viète's Theorem ($x_1 \cdot x_2 = \frac{c}{a}$):  
  $$(-1) \cdot x_2 = \frac{c}{a} \implies x_2 = -\frac{c}{a}$$
- **Applicability Condition:** `ConditionExpr(all_of=[PredicateId.A_NONZERO, PredicateId.A_MINUS_B_PLUS_C_ZERO])`

---

### 9.3 Reduced Discriminant $\Delta'$ ($b = 2b'$) — Method vs. Tip Boundary
- **Method `QUAD_FORMULA_REDUCED`:** Broad algorithmic procedure mathematically valid for any $a \neq 0, b \in \mathbb{Q}$.
- **Tip `QUAD_TIP_REDUCED_FORMULA_EVEN_B`:** Pedagogical shortcut for convenient mental/pencil arithmetic. Requires `B_EVEN_INTEGER` ($b \in 2\mathbb{Z}$) because the shortcut is specifically intended to eliminate fractional intermediate arithmetic inside $\Delta'$.

---

### 9.4 Sound Viète Integer Factoring & Versioned Heuristic Policy
- **Sound Mathematical Condition:**
  Having $\Delta$ be a rational square is **NOT** sufficient to guarantee integer roots.  
  *Counterexample:* $2x^2 - 3x + 1 = 0 \implies \Delta = 1$, but roots are $x_1 = 1 \in \mathbb{Z}$ and $x_2 = 1/2 \notin \mathbb{Z}$.  
  Therefore, the tip `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` requires the exact predicate `ROOTS_ARE_INTEGERS`:
  $$\exists q \in \mathbb{Q}_{\ge 0}: q^2 = \Delta \land \frac{-b - q}{2a} \in \mathbb{Z} \land \frac{-b + q}{2a} \in \mathbb{Z}$$
- **Versioned Heuristic Policy `HEURISTIC_SMALL_INTEGER_ROOTS_V1`:**
  - **Threshold:** $|x_1| \le 12 \land |x_2| \le 12$.
  - **Rationale:** Factoring integers mentally is effective for single/double-digit multiplication products up to $144$.
  - **Scope:** Used **ONLY** to set `pedagogical_recommendation` (`RECOMMENDED` if within threshold, `NEUTRAL` if larger integers). It **NEVER** alters `mathematical_applicability`.

---

## 10. Candidate Quadratic Quick Tips & Problem Forms Matrix

### 10.1 Candidate Quick Tips Matrix
| Tip ID | Category | Applicability Condition (`ConditionExpr`) | Related Method | Exact Integrality Required? | Heuristic Involved? | Provenance Status | Disposition |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO` | `COEFFICIENT_RELATION` | `all_of: [A_NONZERO, A_PLUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_SUM` | No | No | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO` | `COEFFICIENT_RELATION` | `all_of: [A_NONZERO, A_MINUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_DIF` | No | No | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `REDUCED_ARITHMETIC` | `all_of: [A_NONZERO, B_EVEN_INTEGER]` | `QUAD_FORMULA_REDUCED` | No | No | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` | `ROOT_PRODUCT_SUM` | `all_of: [A_NONZERO, ROOTS_ARE_INTEGERS]` | `QUAD_VIETE_SUM_PRODUCT` | Yes | Yes (`HEURISTIC_SMALL_INTEGER_ROOTS_V1`) | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_INCOMPLETE_B_ZERO` | `SPECIAL_STRUCTURE` | `all_of: [A_NONZERO, B_ZERO]` | `QUAD_FORMULA_STANDARD` | No | No | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_INCOMPLETE_C_ZERO` | `SPECIAL_STRUCTURE` | `all_of: [A_NONZERO, C_ZERO]` | `QUAD_FACTORIZATION_Q` | No | No | SGK Toán 9 KNTT | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_TIP_COMPLETING_SQUARE_MONIC` | `TRANSFORMATION` | `all_of: [A_NONZERO, A_EQ_ONE]` | `QUAD_COMPLETE_SQUARE` | No | No | SGK Toán 9 KNTT | `NEEDS_SOURCE_REVIEW` |

---

### 10.2 Candidate Problem Forms Matrix
| Form ID | Title (VI) | Recognition Condition | Guaranteed Methods | Guaranteed Tips | Related Tips | Difficulty | Disposition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORM_GENERAL_QUADRATIC` | Phương trình bậc hai tổng quát | `all_of: [A_NONZERO]` | `QUAD_FORMULA_STANDARD` | *(None)* | `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_COMPLETE_QUADRATIC` | Phương trình bậc hai đầy đủ | `all_of: [A_NONZERO, B_NONZERO, C_NONZERO]` | `QUAD_FORMULA_STANDARD` | *(None)* | `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_SPECIAL_SUM_ZERO` | Phương trình bậc hai có $a+b+c=0$ | `all_of: [A_NONZERO, A_PLUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_SUM` | `QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_SPECIAL_DIF_ZERO` | Phương trình bậc hai có $a-b+c=0$ | `all_of: [A_NONZERO, A_MINUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_DIF` | `QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_INCOMPLETE_B_ZERO` | Phương trình bậc hai khuyết $b=0$ | `all_of: [A_NONZERO, B_ZERO]` | `QUAD_FORMULA_STANDARD` | `QUAD_TIP_INCOMPLETE_B_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_INCOMPLETE_C_ZERO` | Phương trình bậc hai khuyết $c=0$ | `all_of: [A_NONZERO, C_ZERO]` | `QUAD_FACTORIZATION_Q` | `QUAD_TIP_INCOMPLETE_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_MONIC_INTEGER_FACTORABLE`| Phương trình bậc hai monic nhẩm nghiệm nguyên | `all_of: [A_EQ_ONE, ROOTS_ARE_INTEGERS]` | `QUAD_VIETE_SUM_PRODUCT` | `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` | *(None)* | `INTERMEDIATE` | `READY_AFTER_PROVENANCE_VERIFICATION` |

---

## 11. Knowledge Graph Extension Policy (DEFERRED)

### 11.1 Graph Evolution Policy
Adding `QUICK_TIP` and `PROBLEM_FORM` to `GraphNodeType` and new edge types to `GraphEdgeType` is **DEFERRED** throughout Milestones K1-01 through K1-05.
- Existing S3 graph endpoint `/api/v1/knowledge/graph`, `GraphModel`, `GraphNodeType`, and `GraphEdgeType` remain **100% UNCHANGED**.
- When graph integration is scheduled in a future milestone, it will be introduced with an explicit graph schema version bump (`GraphModel v2`) or a separate endpoint (`/api/v2/knowledge/graph`) to protect strict external clients.

---

## 12. Read-Only Knowledge API & Separate Assessment Endpoints

### 12.1 Static Read-Only Endpoints (Milestone K1-04)
- `GET /api/v1/knowledge/tips/{tip_id}`: Returns `QuickTipKnowledgeView`.
- `GET /api/v1/knowledge/tips`: Returns list of all verified quick tips.
- `GET /api/v1/knowledge/problem-forms/{form_id}`: Returns `RelatedProblemFormKnowledgeView`.
- `GET /api/v1/knowledge/problem-forms`: Returns list of all verified problem forms.
- `GET /api/v1/knowledge/methods/{method_id}/tips`: Returns tips associated with a method.
- `GET /api/v1/knowledge/methods/{method_id}/problem-forms`: Returns problem forms solved by a method.

### 12.2 Frozen Solve Endpoint & Separate Assessment Boundaries (Milestone K1-05)
- **`POST /api/v1/algebra/solve`:** Remains 100% frozen with existing `SolveResponse` contract throughout K1-01 through K1-05.
- **Dedicated Assessment Endpoints (Milestone K1-05):**
  - `POST /api/v1/algebra/quick-tip-assessments`: Accepts canonical problem parameters and returns `List[QuickTipAssessmentView]`.
  - `POST /api/v1/algebra/problem-form-assessments`: Accepts canonical problem parameters and returns `List[ProblemFormAssessmentView]`.

---

## 13. Provenance & Non-Fabrication Invariants

1. **Zero Frontend Fabrication:** The frontend MUST NEVER invent, guess, generate, or calculate quick tips or problem forms.
2. **Zero LLM Authority:** Large language model outputs are never used as source truth for mathematical rules, tips, or assessments.
3. **Static/Dynamic Non-Conflation:** Static knowledge files NEVER claim that a tip applies to a specific problem instance without backend evaluation.
4. **Authoritative Provenance Gate:** Every `QuickTipKnowledge` and `RelatedProblemFormKnowledge` entry must cite verified source IDs in centralized `provenance.json` with exact chapter/page locators.
5. **Deterministic Condition Verification:** Tip applicability is evaluated solely via exact rational arithmetic over AST/canonical problem invariants.
6. **Immutable SHA-256 Dataset Hashing:** All static datasets are serialized to sorted JSON and hashed with SHA-256 upon repository startup.
7. **Curated Examples Only:** Worked and practice examples are deferred (`[]`) until an authoritative Example Problem Registry is established.

---

## 14. Implementation Roadmap (Post-P0)

```
+-------------------------------------------------------------------------+
| Milestone K1 Implementation Roadmap                                     |
|                                                                         |
|  [K1-P0-R2] Exact Contract & Versioning Closeout (CURRENT)              |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-01] Pydantic v2 Knowledge Schemas (QuickTip & ProblemForm)         |
|     │    (Contracts + ConditionExpr + PredicateId + validation tests)   |
|     ▼                                                                   |
|  [K1-02] Curated Static JSON Dataset with Verified GDPT 2018 Provenance |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-03] Knowledge Repository Extension & Static Relationship Queries   |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-04] Read-Only FastAPI Knowledge Endpoints & Contract Tests         |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-05] Deterministic Predicate Evaluator + QuickTipEvaluator +         |
|     │    ProblemFormEvaluator + Separate Assessment Endpoints           |
|     ▼                                                                   |
|  [K1-06] React Workspace Integration into FROZEN Pedagogical Sections   |
|     │    (Populate existing slots; ZERO UI redesign or restyling)       |
|     ▼                                                                   |
|  [K1-07] End-to-End Real Browser Acceptance & Final Closeout            |
+-------------------------------------------------------------------------+
```

---

## 15. Acceptance Criteria for K1-P0-R2

- [x] Preflight document updated at `docs/preflight/MVP_V1_K1_P0_QUICK_TIP_RELATED_FORM_KNOWLEDGE_PREFLIGHT.md`.
- [x] Exact S3 type reuse corrected (`LocalizedText`, `CurriculumRef` with `source_locator`, `SourceProvenance` with `source_type: str`, `verification_status: ProvenanceStatus`, `provenance_refs: List[str]`).
- [x] `KnowledgeEntityStatus`, `DifficultyLevel`, and `TipCategory` explicitly declared as NEW IN K1.
- [x] ConditionExpr evaluation semantics fully defined (`all_of`, `any_of`, `none_of`, and `UNKNOWN` propagation).
- [x] All 12 predicates defined with exact rational semantics (`A_NONZERO`, `A_EQ_ONE`, `B_NONZERO`, `C_NONZERO`, `B_EVEN_INTEGER`, `DISCRIMINANT_NONNEGATIVE`, `DISCRIMINANT_RATIONAL_SQUARE`, `A_PLUS_B_PLUS_C_ZERO`, `A_MINUS_B_PLUS_C_ZERO`, `B_ZERO`, `C_ZERO`, `ROOTS_ARE_INTEGERS`).
- [x] Counterexample ($2x^2 - 3x + 1 = 0$) and `ROOTS_ARE_INTEGERS` soundness preserved.
- [x] `worked_example_ids` and `practice_example_ids` marked explicitly as deferred (empty `[]` in K1-02).
- [x] Multi-match problem form overlap policy formalized.
- [x] General form naming corrected (`QUAD_FORM_GENERAL_QUADRATIC` and `QUAD_FORM_COMPLETE_QUADRATIC`).
- [x] Static relation semantics (`related_*` vs `guaranteed_*`) clarified.
- [x] `QuickTipAssessmentView` and `ProblemFormAssessmentView` contracts frozen with `unknown_predicates`.
- [x] Assessment API endpoints frozen (`POST /api/v1/algebra/quick-tip-assessments`, `POST /api/v1/algebra/problem-form-assessments`).
- [x] Existing `SolveResponse` contract frozen throughout K1-01 to K1-05.
- [x] Graph extension formally DEFERRED.
- [x] Candidate matrix updated with `READY_AFTER_PROVENANCE_VERIFICATION`.
- [x] ZERO production code modified (`src/mke_product/**`, `src/frontend/**`, `tests/**`).
- [x] S3 dataset SHA (`e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`) untouched.
