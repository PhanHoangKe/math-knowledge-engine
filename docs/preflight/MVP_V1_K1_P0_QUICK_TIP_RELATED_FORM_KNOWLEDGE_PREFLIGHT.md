# MKE PRODUCT — K1-P0-R1 QUICK TIP & RELATED PROBLEM FORM KNOWLEDGE AUTHORITY PREFLIGHT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-03  
**Target Milestone:** K1-P0-R1 Knowledge Preflight Remediation  
**Branch:** `product/mvp-v1-k1-p0-r1-preflight-remediation`  
**Accepted Owner UI Baseline SHA:** `0a6ba07ddb1995891796d5b826424a2a1ff3531a`  
**Frozen S3 Knowledge Dataset SHA:** `e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`  
**Preflight Status:** `READY FOR INDEPENDENT K1-P0-R1 PREFLIGHT AUDIT`  

---

## 1. Executive Summary & Strict UI Freeze Statement

### 1.1 UI Status Statement
> **UI STATUS: FROZEN — NO FRONTEND CHANGES AUTHORIZED**  
> The current MKE frontend and user interface layout is formally considered **ACCEPTED** by the Project Owner.  
> ZERO modifications are authorized under `src/frontend/**`.  
> No JSX, CSS, TypeScript, i18n, or frontend tests are modified in this milestone.  
> All K1 preflight work is performed in an isolated Git worktree to guarantee the primary working tree and its running Vite server remain 100% untouched.

### 1.2 Purpose of Milestone K1
MKE will enrich its deterministic knowledge graph by introducing two new authoritative mathematical and pedagogical entities:
1. **Quick Solving Tips / Shortcuts (`QuickTipKnowledge`)**: Deterministic and heuristic-bounded pedagogical shortcuts (e.g., $a+b+c=0 \implies x_1=1, x_2=c/a$, even linear coefficient reduced discriminant $\Delta'$, Viète integer factoring).
2. **Related Problem Forms (`RelatedProblemFormKnowledge`)**: Canonical structures and classifications of mathematical problems that share solution strategies, prerequisites, and tips.

### 1.3 Scope of K1-P0-R1 Remediation
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

## 3. Strict Reuse of S3 Foundation Contracts

K1 strictly reuses the exact Pydantic v2 types validated and production-locked in Milestone S3 (`src/mke_product/knowledge/schemas.py`):

- **`LocalizedText`**: Symmetric bilingual container (`vi: str`, `en: str`).
- **`CurriculumRef`**: National curriculum alignment (`framework: str`, `grade_band: str`, `topic: str`, `status: CurriculumMappingStatus`, `source_document: str`, `lesson_locator: Optional[str]`).
- **`SourceProvenance`**: Centralized source provenance records in `provenance.json` (`source_id: str`, `source_type: ProvenanceSourceType`, `title: str`, `author_or_institution: str`, `publication_year: Optional[int]`, `locator: str`, `verification_status: ProvenanceVerificationStatus`).
- **Foreign Key Convention:** Entities use `provenance_refs: List[str]` referencing centralized `source_id` keys, and `curriculum_refs: List[CurriculumRef]`.

---

## 4. Closed Condition DSL & Predicate Definitions

To ensure 100% deterministic mathematical evaluation, conditions are expressed via a closed, typed expression model over atomic predicates.

### 4.1 Predicate ID Enumeration
```python
from enum import Enum

class PredicateId(str, Enum):
    A_NONZERO = "A_NONZERO"
    A_EQ_ONE = "A_EQ_ONE"
    B_EVEN_INTEGER = "B_EVEN_INTEGER"
    DISCRIMINANT_NONNEGATIVE = "DISCRIMINANT_NONNEGATIVE"
    DISCRIMINANT_RATIONAL_SQUARE = "DISCRIMINANT_RATIONAL_SQUARE"
    A_PLUS_B_PLUS_C_ZERO = "A_PLUS_B_PLUS_C_ZERO"
    A_MINUS_B_PLUS_C_ZERO = "A_MINUS_B_PLUS_C_ZERO"
    B_ZERO = "B_ZERO"
    C_ZERO = "C_ZERO"
    ROOTS_ARE_INTEGERS = "ROOTS_ARE_INTEGERS"
```

### 4.2 Exact Rational Semantics of All Predicates
Every predicate is formally defined over exact rational polynomial coefficients $a, b, c \in \mathbb{Q}$ ($a = \frac{n_a}{d_a}, b = \frac{n_b}{d_b}, c = \frac{n_c}{d_c}$ with $d_i \ge 1$):

| Predicate ID | Mathematical Definition | Exact Backend Implementation Rule |
| :--- | :--- | :--- |
| `A_NONZERO` | $a \neq 0$ | `a != 0` |
| `A_EQ_ONE` | $a = 1$ | `a == 1` (`n_a == 1 and d_a == 1`) |
| `B_EVEN_INTEGER` | $b \in \mathbb{Z} \land b \equiv 0 \pmod 2$ | `d_b == 1 and (n_b % 2 == 0)` |
| `DISCRIMINANT_NONNEGATIVE` | $\Delta = b^2 - 4ac \ge 0$ | `(b * b - 4 * a * c) >= 0` |
| `DISCRIMINANT_RATIONAL_SQUARE` | $\exists q \in \mathbb{Q}_{\ge 0}: q^2 = \Delta$ | `delta >= 0 and is_square(delta.num) and is_square(delta.den)` |
| `A_PLUS_B_PLUS_C_ZERO` | $a + b + c = 0$ | `(a + b + c) == 0` |
| `A_MINUS_B_PLUS_C_ZERO` | $a - b + c = 0$ | `(a - b + c) == 0` |
| `B_ZERO` | $b = 0$ | `b == 0` (`n_b == 0`) |
| `C_ZERO` | $c = 0$ | `c == 0` (`n_c == 0`) |
| `ROOTS_ARE_INTEGERS` | $\Delta = q^2 (q \in \mathbb{Q}) \land \frac{-b \pm q}{2a} \in \mathbb{Z}$ | `DISCRIMINANT_RATIONAL_SQUARE and ((-b - q)/(2*a)).is_integer() and ((-b + q)/(2*a)).is_integer()` |

### 4.3 Condition Expression Model (`ConditionExpr`)
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
        description="At least one predicate in this list must evaluate to TRUE (if non-empty)"
    )
    none_of: List[PredicateId] = Field(
        default_factory=list,
        description="All predicates in this list must evaluate to FALSE (if non-empty)"
    )
```

---

## 5. `QuickTipKnowledge` Schema Design

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from mke_product.knowledge.schemas import (
    LocalizedText,
    CurriculumRef,
    EntityStatus,
)

class TipCategory(str, Enum):
    COEFFICIENT_RELATION = "COEFFICIENT_RELATION"      # e.g., a+b+c=0, a-b+c=0
    REDUCED_ARITHMETIC = "REDUCED_ARITHMETIC"          # e.g., even b -> Delta'
    ROOT_PRODUCT_SUM = "ROOT_PRODUCT_SUM"              # e.g., Viète integer factoring
    SPECIAL_STRUCTURE = "SPECIAL_STRUCTURE"            # e.g., missing b (b=0), missing c (c=0)
    TRANSFORMATION = "TRANSFORMATION"                  # e.g., completing square shortcut

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
        description="National curriculum standards mapping"
    )
    provenance_refs: List[str] = Field(
        ...,
        min_length=1,
        description="List of authoritative source provenance IDs in provenance.json"
    )

    status: EntityStatus = Field(
        default=EntityStatus.VERIFIED,
        description="Entity governance status"
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
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from mke_product.knowledge.schemas import (
    LocalizedText,
    CurriculumRef,
    EntityStatus,
)

class DifficultyLevel(str, Enum):
    BASIC = "BASIC"                  # Standard textbook introductory exercises
    INTERMEDIATE = "INTERMEDIATE"    # Standard examination problems requiring transformation
    ADVANCED = "ADVANCED"            # Multi-step reasoning / competition problems

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

    # Curated Examples (Foreign Keys to Example Problem Registry)
    worked_example_ids: List[str] = Field(
        default_factory=list,
        description="Stable IDs to curated, verified worked examples"
    )
    practice_example_ids: List[str] = Field(
        default_factory=list,
        description="Stable IDs to curated practice problems"
    )

    # Curriculum & Governance
    curriculum_refs: List[CurriculumRef] = Field(
        default_factory=list,
        description="Curriculum standards references"
    )
    provenance_refs: List[str] = Field(
        ...,
        min_length=1,
        description="Authoritative source provenance IDs"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.BASIC,
        description="Relative pedagogical difficulty"
    )
    status: EntityStatus = Field(
        default=EntityStatus.VERIFIED,
        description="Entity governance status"
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version"
    )
```

---

## 7. Dynamic Assessment Contracts (`QuickTipAssessmentView` & `ProblemFormAssessmentView`)

To maintain the absolute boundary between static knowledge and dynamic equation evaluation, MKE formalizes the runtime assessment DTOs:

### 7.1 `QuickTipAssessmentView`
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
    """Runtime assessment of a tip against a specific normalized equation."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tip_id: str = Field(..., description="Target tip identifier")
    mathematical_applicability: TipApplicability = Field(..., description="Objective applicability state")
    pedagogical_recommendation: TipRecommendation = Field(..., description="Pedagogical preference state")
    execution_availability: TipExecutionAvailability = Field(..., description="Backend execution availability")
    matched_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to TRUE")
    failed_predicates: List[PredicateId] = Field(default_factory=list, description="Predicates that evaluated to FALSE")
    reason_codes: List[str] = Field(default_factory=list, description="Canonical deterministic reason codes")
```

### 7.2 `ProblemFormAssessmentView`
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
    matched_predicates: List[PredicateId] = Field(default_factory=list)
    failed_predicates: List[PredicateId] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
```

---

## 8. Mathematical Analysis of Canonical Shortcuts & Soundness

### 8.1 Special Case $a + b + c = 0$
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

### 8.2 Special Case $a - b + c = 0$
- **Mathematical Basis:**
  Evaluating $P(x) = ax^2 + bx + c$ at $x = -1$:  
  $$P(-1) = a(-1)^2 + b(-1) + c = a - b + c$$
  If $a - b + c = 0$, then $P(-1) = 0 \implies x_1 = -1$ is an exact root.  
  By Viète's Theorem ($x_1 \cdot x_2 = \frac{c}{a}$):  
  $$(-1) \cdot x_2 = \frac{c}{a} \implies x_2 = -\frac{c}{a}$$
- **Applicability Condition:** `ConditionExpr(all_of=[PredicateId.A_NONZERO, PredicateId.A_MINUS_B_PLUS_C_ZERO])`

---

### 8.3 Reduced Discriminant $\Delta'$ ($b = 2b'$) — Method vs. Tip Boundary
- **Method `QUAD_FORMULA_REDUCED`:** Broad algorithmic procedure mathematically valid for any $a \neq 0, b \in \mathbb{Q}$.
- **Tip `QUAD_TIP_REDUCED_FORMULA_EVEN_B`:** Pedagogical shortcut for convenient mental/pencil arithmetic. Requires `B_EVEN_INTEGER` ($b \in 2\mathbb{Z}$) because the shortcut is specifically intended to eliminate fraction arithmetic inside $\Delta'$.

---

### 8.4 Sound Viète Integer Factoring & Heuristic Policy
- **Sound Mathematical Condition:**
  Having $\Delta$ be a rational square is **NOT** sufficient to guarantee integer roots (e.g. $2x^2 - 3x + 1 = 0 \implies \Delta=1$, roots are $1$ and $1/2 \notin \mathbb{Z}$).  
  Therefore, the tip `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` requires the exact predicate `ROOTS_ARE_INTEGERS`:
  $$\exists q \in \mathbb{Q}_{\ge 0}: q^2 = \Delta \land \frac{-b - q}{2a} \in \mathbb{Z} \land \frac{-b + q}{2a} \in \mathbb{Z}$$
- **Versioned Heuristic Policy `HEURISTIC_SMALL_INTEGER_ROOTS_V1`:**
  - **Threshold:** $|x_1| \le 12 \land |x_2| \le 12$.
  - **Rationale:** Factoring integers mentally is effective for multiplication table products up to $144$.
  - **Scope:** Used **ONLY** to set `pedagogical_recommendation` (`RECOMMENDED` if within threshold, `NEUTRAL` if larger integers). It **NEVER** alters `mathematical_applicability`.

---

## 9. Candidate Quadratic Quick Tips & Problem Forms Matrix

### 9.1 Candidate Quick Tips Matrix
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

### 9.2 Candidate Problem Forms Matrix
| Form ID | Title (VI) | Recognition Condition | Guaranteed Methods | Guaranteed Tips | Related Tips | Difficulty | Disposition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORM_GENERAL_STANDARD` | Phương trình bậc hai đầy đủ tổng quát | `all_of: [A_NONZERO]` | `QUAD_FORMULA_STANDARD` | *(None)* | `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_SPECIAL_SUM_ZERO` | Phương trình bậc hai có $a+b+c=0$ | `all_of: [A_NONZERO, A_PLUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_SUM` | `QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_SPECIAL_DIF_ZERO` | Phương trình bậc hai có $a-b+c=0$ | `all_of: [A_NONZERO, A_MINUS_B_PLUS_C_ZERO]` | `QUAD_VIETE_SPECIAL_DIF` | `QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_INCOMPLETE_B_ZERO` | Phương trình bậc hai khuyết $b=0$ | `all_of: [A_NONZERO, B_ZERO]` | `QUAD_FORMULA_STANDARD` | `QUAD_TIP_INCOMPLETE_B_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_INCOMPLETE_C_ZERO` | Phương trình bậc hai khuyết $c=0$ | `all_of: [A_NONZERO, C_ZERO]` | `QUAD_FACTORIZATION_Q` | `QUAD_TIP_INCOMPLETE_C_ZERO` | *(None)* | `BASIC` | `READY_AFTER_PROVENANCE_VERIFICATION` |
| `QUAD_FORM_MONIC_INTEGER_FACTORABLE`| Phương trình bậc hai monic nhẩm nghiệm nguyên | `all_of: [A_EQ_ONE, ROOTS_ARE_INTEGERS]` | `QUAD_VIETE_SUM_PRODUCT` | `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` | *(None)* | `INTERMEDIATE` | `READY_AFTER_PROVENANCE_VERIFICATION` |

---

## 10. Relational Knowledge Graph Topology Expansion & Evolution Policy

### 10.1 Graph Evolution Policy
Adding `QUICK_TIP` and `PROBLEM_FORM` to `GraphNodeType` and new edge types to `GraphEdgeType` is an additive schema evolution. To protect strict external clients:
1. The Knowledge Graph API will maintain semantic versioning (`/api/v1/knowledge/graph`).
2. An additive enum compatibility policy is formally declared in OpenAPI documentation.

```
                    +-----------------------------+
                    |    RelatedProblemForm       |
                    |   (RelatedProblemFormNode)  |
                    +-----------------------------+
                       /          |            \
       VALID_FOR_FORM /           |             \ USES_TIP
                     v            |              v
+------------------------+        |       +------------------------+
|    MethodDefinition    |        |       |    QuickTipKnowledge   |
|      (MethodNode)      |<-------+-------|     (QuickTipNode)     |
+------------------------+ APPLIES_METHOD +------------------------+
         |            \                               /         |
         | USES_FORMULA\                             / USES_THM |
         v              \                           v           v
+-----------------+   +-------------------+   +--------------------+
| FormulaKnowledge|   | ConceptKnowledge  |   |  TheoremKnowledge  |
|  (FormulaNode)  |   |   (ConceptNode)   |   |   (TheoremNode)    |
+-----------------+   +-------------------+   +--------------------+
```

---

## 11. Read-Only Knowledge API & Assessment Endpoints Design

### 11.1 Static Read-Only Endpoints
- `GET /api/v1/knowledge/tips/{tip_id}`: Returns `QuickTipKnowledgeView`.
- `GET /api/v1/knowledge/tips`: Returns list of all verified quick tips.
- `GET /api/v1/knowledge/problem-forms/{form_id}`: Returns `RelatedProblemFormKnowledgeView`.
- `GET /api/v1/knowledge/problem-forms`: Returns list of all verified problem forms.
- `GET /api/v1/knowledge/methods/{method_id}/tips`: Returns tips associated with a method.
- `GET /api/v1/knowledge/methods/{method_id}/problem-forms`: Returns problem forms solved by a method.

### 11.2 Frozen Solve Endpoint & Separate Assessment API Boundary
- **`POST /api/v1/algebra/solve`:** Remains 100% frozen with existing `SolveResponse` contract.
- **Dynamic Assessment API:** Proposed as a dedicated endpoint in Milestone K1-05:
  - `POST /api/v1/algebra/quick-tip-assessments` taking canonical problem parameters and returning `List[QuickTipAssessmentView]`.

---

## 12. Provenance & Non-Fabrication Invariants

1. **Zero Frontend Fabrication:** The frontend MUST NEVER invent, guess, generate, or calculate quick tips or problem forms.
2. **Zero LLM Authority:** Large language model outputs are never used as source truth for mathematical rules, tips, or assessments.
3. **Static/Dynamic Non-Conflation:** Static knowledge files NEVER claim that a tip applies to a specific problem instance without backend evaluation.
4. **Authoritative Provenance Required:** Every `QuickTipKnowledge` and `RelatedProblemFormKnowledge` entry must cite verifiable source IDs in `provenance.json`.
5. **Deterministic Condition Verification:** Tip applicability is evaluated solely via exact rational arithmetic over AST/canonical problem invariants.
6. **Immutable SHA-256 Dataset Hashing:** All static datasets are serialized to sorted JSON and hashed with SHA-256 upon repository startup.
7. **Curated Examples Only:** Worked and practice examples are static, validated problem instances with exact proofs.

---

## 13. Implementation Roadmap (Post-P0)

```
+-------------------------------------------------------------------------+
| Milestone K1 Implementation Roadmap                                     |
|                                                                         |
|  [K1-P0-R1] Remediated Preflight Blueprint & Contracts (CURRENT)       |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-01] Pydantic v2 Knowledge Schemas (QuickTip & ProblemForm)         |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-02] Curated Static JSON Dataset with Verified GDPT 2018 Provenance |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-03] Knowledge Repository Extension & Relational Graph Indices      |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-04] Read-Only FastAPI Knowledge Endpoints & Contract Tests         |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-05] Deterministic Backend Evaluator for QuickTipAssessmentView     |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-06] React Workspace Integration into FROZEN Pedagogical Sections   |
|     │    (Populate existing slots; ZERO UI redesign or restyling)       |
|     ▼                                                                   |
|  [K1-07] End-to-End Real Browser Acceptance & Final Closeout            |
+-------------------------------------------------------------------------+
```

---

## 14. Acceptance Criteria for K1-P0-R1

- [x] Primary UI working tree preserved on `product/mvp-v1-ux-p1-math-input-result-pods` (`0a6ba07ddb1995891796d5b826424a2a1ff3531a`) with Vite untouched.
- [x] Remote UI branch pushed and verified matching `OWNER_UI_BASE_SHA`.
- [x] K1 remediation conducted in dedicated isolated worktree `D:/mke_k1_worktree`.
- [x] Preflight document remediated at `docs/preflight/MVP_V1_K1_P0_QUICK_TIP_RELATED_FORM_KNOWLEDGE_PREFLIGHT.md`.
- [x] S3 type names reused exactly (`LocalizedText`, `CurriculumRef`, `provenance_refs: List[str]`).
- [x] Closed condition DSL (`ConditionExpr`, `PredicateId`) fully defined with exact rational semantics.
- [x] Sound Viète integer condition `ROOTS_ARE_INTEGERS` and named versioned heuristic policy `HEURISTIC_SMALL_INTEGER_ROOTS_V1` formalized.
- [x] Reduced formula method vs. tip boundary and problem form relation semantics clarified.
- [x] `QuickTipAssessmentView` and `ProblemFormAssessmentView` contracts formally frozen.
- [x] Existing `SolveResponse` contract frozen; assessment API separated.
- [x] Candidate matrix updated to `READY_AFTER_PROVENANCE_VERIFICATION`.
- [x] ZERO production code modified (`src/mke_product/**`, `src/frontend/**`, `tests/**`).
- [x] S3 dataset SHA (`e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`) untouched.
