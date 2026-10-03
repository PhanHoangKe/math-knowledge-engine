# MKE PRODUCT — K1-P0 QUICK TIP & RELATED PROBLEM FORM KNOWLEDGE AUTHORITY PREFLIGHT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-03  
**Target Milestone:** K1-P0 Knowledge Preflight  
**Branch:** `product/mvp-v1-k1-p0-knowledge-preflight`  
**Accepted Product Baseline:** `1d0f654ad1077b478ec88f583afa7f41b8b4bbb4` (S3-04-R4 Final Semantic Closeout)  
**Frozen S3 Knowledge Dataset SHA:** `e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`  
**Preflight Status:** `READY FOR INDEPENDENT K1-P0 PREFLIGHT AUDIT`  

---

## 1. Executive Summary & Strict UI Freeze Statement

### 1.1 UI Status Statement
> **UI STATUS: FROZEN — NO FRONTEND CHANGES AUTHORIZED**  
> The current MKE frontend and user interface layout is formally considered **ACCEPTED** by the Project Owner.  
> ZERO modifications are authorized under `src/frontend/**`.  
> No JSX, CSS, TypeScript, i18n, or frontend tests are modified in this milestone.

### 1.2 Purpose of Milestone K1
MKE will enrich its deterministic knowledge graph by introducing two new authoritative mathematical and pedagogical entities:
1. **Quick Solving Tips / Shortcuts (`QuickTipKnowledge`)**: Deterministic and heuristic-bounded pedagogical shortcuts (e.g., $a+b+c=0 \implies x_1=1, x_2=c/a$, even linear coefficient reduced discriminant $\Delta'$, Viète mental factoring).
2. **Related Problem Forms (`RelatedProblemFormKnowledge`)**: Canonical structures and classifications of mathematical problems that share solution strategies, prerequisites, and tips.

### 1.3 Scope of K1-P0 Preflight
- **AUTHORIZED:** Complete architectural, schema, condition DSL, provenance, graph linkage, API contract, and candidate matrix preflight specification.
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

## 3. Reused S3 Foundation Contracts

K1 directly builds upon the validated, production-locked Pydantic v2 infrastructure delivered in Milestone S3:

- **`LocalizedText`**: Symmetric bilingual container (`vi: str`, `en: str`).
- **`EntityStatus`**: Strict lifecycle enum (`PROVISIONAL`, `VERIFIED`, `DEPRECATED`).
- **`CurriculumReference`**: National curriculum alignment (`framework`, `grade_band`, `topic`, `status`, `source_document`, `lesson_locator`).
- **`ProvenanceReference`**: Authoritative provenance citation (`source_type`, `citation_vi`, `citation_en`, `locator`, `verification_record`).
- **`FormulaKnowledge` & `TheoremKnowledge`**: Established referenced mathematical formulas and theorems.
- **`ConceptKnowledge`**: Foundational prerequisite concepts.
- **`MethodDefinition` & `MethodAssessment`**: The 9 canonical product methods and their runtime evaluation rules.

---

## 4. `QuickTipKnowledge` Schema Design

The `QuickTipKnowledge` model defines static pedagogical and mathematical metadata for a solving shortcut.

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from mke_product.domain.knowledge import (
    LocalizedText,
    EntityStatus,
    CurriculumReference,
    ProvenanceReference,
)

class TipCategory(str, Enum):
    COEFFICIENT_RELATION = "COEFFICIENT_RELATION"      # e.g., a+b+c=0, a-b+c=0
    REDUCED_ARITHMETIC = "REDUCED_ARITHMETIC"          # e.g., even b -> Delta'
    ROOT_PRODUCT_SUM = "ROOT_PRODUCT_SUM"              # e.g., mental Viete factoring
    SPECIAL_STRUCTURE = "SPECIAL_STRUCTURE"            # e.g., missing b (b=0), missing c (c=0)
    TRANSFORMATION = "TRANSFORMATION"                  # e.g., completing square shortcut

class QuickTipKnowledge(BaseModel):
    """
    Static pedagogical knowledge entity describing an authoritative solving shortcut.
    Immutable, source-backed, and bilingual.
    """
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tip_id: str = Field(
        ...,
        description="Unique canonical identifier (e.g. QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO)"
    )
    title: LocalizedText = Field(
        ...,
        description="Bilingual title of the quick tip"
    )
    summary: LocalizedText = Field(
        ...,
        description="Concise pedagogical summary of what the shortcut achieves"
    )
    category: TipCategory = Field(
        ...,
        description="Taxonomic classification of the shortcut"
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
        description="Problem forms where this shortcut is applicable"
    )

    # Provenance & Curriculum
    curriculum_refs: List[CurriculumReference] = Field(
        default_factory=list,
        description="National curriculum standards mapping"
    )
    provenance_refs: List[ProvenanceReference] = Field(
        ...,
        min_length=1,
        description="Authoritative source citations (textbooks, formal theorems)"
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

## 5. `RelatedProblemFormKnowledge` Schema Design

The `RelatedProblemFormKnowledge` model captures the structural archetype of a mathematical problem family, distinguishing between the abstract pattern and specific concrete examples.

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from mke_product.domain.knowledge import (
    LocalizedText,
    EntityStatus,
    CurriculumReference,
    ProvenanceReference,
)

class DifficultyLevel(str, Enum):
    BASIC = "BASIC"                  # Standard textbook introductory exercises
    INTERMEDIATE = "INTERMEDIATE"    # Standard examination problems requiring transformation
    ADVANCED = "ADVANCED"            # Multi-step reasoning / competition problems

class ExampleProblemReference(BaseModel):
    """Reference to a curated, verified concrete problem instance."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    equation_raw: str = Field(..., description="Canonical equation string (e.g. 'x^2 - 5*x + 6 = 0')")
    equation_latex: str = Field(..., description="Formatted LaTeX representation")
    brief_solution_vi: str = Field(..., description="Concise Vietnamese solution guide")
    brief_solution_en: str = Field(..., description="Concise English solution guide")
    provenance_note: Optional[str] = Field(None, description="Source citation of this example")

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
    recognition_guidance: LocalizedText = Field(
        ...,
        description="Pedagogical clues for students to recognize this form"
    )

    # Strategy & Tool Connections
    applicable_method_ids: List[str] = Field(
        default_factory=list,
        description="Methods suitable for solving this problem form"
    )
    applicable_tip_ids: List[str] = Field(
        default_factory=list,
        description="Quick tips applicable to this problem form"
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

    # Curated Examples (Strictly no dynamic frontend hallucination)
    worked_example_refs: List[ExampleProblemReference] = Field(
        default_factory=list,
        description="Curated worked examples with step summaries"
    )
    practice_example_refs: List[ExampleProblemReference] = Field(
        default_factory=list,
        description="Curated practice problems for self-study"
    )

    # Curriculum & Governance
    curriculum_refs: List[CurriculumReference] = Field(
        default_factory=list,
        description="Curriculum standards references"
    )
    provenance_refs: List[ProvenanceReference] = Field(
        ...,
        min_length=1,
        description="Authoritative source citations"
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

## 6. Static vs. Dynamic Truth Boundary

To prevent epistemic corruption and maintain 100% verifiability, MKE enforces a strict boundary between **Static Knowledge** and **Dynamic Runtime Assessment**:

```
+-------------------------------------------------------------------------+
|                       STATIC KNOWLEDGE (Pydantic / Git)                 |
|  - QuickTipKnowledge: What the shortcut is, its proof, general scope    |
|  - RelatedProblemFormKnowledge: Archetype structure, general methods    |
|  * Invariant across all problem instances                                |
|  * NEVER claims: "This tip applies to the user's current equation"      |
+-------------------------------------------------------------------------+
                                    |
                                    | (Evaluated by Backend Engine)
                                    v
+-------------------------------------------------------------------------+
|                  DYNAMIC RUNTIME ASSESSMENT (Evaluator DTO)             |
|  - QuickTipAssessmentView: Specific to equation ax^2 + bx + c = 0       |
|  - Evaluates atomic condition predicates (e.g., a+b+c == 0 -> TRUE)     |
|  - Outputs: mathematical_applicability, recommendation, matched_reasons |
|  * Ephemeral, computed per request, cryptographically verifiable        |
+-------------------------------------------------------------------------+
```

### 6.1 Dynamic Assessment Model (`QuickTipAssessmentView`)
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

class QuickTipAssessmentView(BaseModel):
    """Runtime assessment of a tip against a specific normalized equation."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tip_id: str
    tip_title_vi: str
    tip_title_en: str
    applicability: TipApplicability
    recommendation: TipRecommendation
    matched_conditions: List[str]
    failed_conditions: List[str]
    assessment_message_vi: str
    assessment_message_en: str
```

---

## 7. Condition Predicate Language & Heuristic Policy

MKE explicitly bans open-ended script execution, Python `eval()`, and LLM natural-language condition matching. All condition checks are strictly defined as bounded, deterministic atomic predicates.

### 7.1 Atomic Mathematical Predicates
These predicates are mathematically objective and evaluated over exact rational coefficients $a, b, c \in \mathbb{Q}$:

| Predicate Code | Mathematical Definition | Deterministic Evaluation Rule |
| :--- | :--- | :--- |
| `A_NONZERO` | $a \neq 0$ | `a != 0` |
| `B_EVEN_INTEGER` | $b \in \mathbb{Z} \land b \equiv 0 \pmod 2$ | `b.is_integer() and (b.numerator % 2 == 0) and (b.denominator == 1)` |
| `DISCRIMINANT_NONNEGATIVE` | $\Delta = b^2 - 4ac \ge 0$ | `delta >= 0` |
| `DISCRIMINANT_RATIONAL_SQUARE` | $\exists q \in \mathbb{Q}_{\ge 0}: q^2 = \Delta$ | `delta.is_rational_square()` |
| `A_PLUS_B_PLUS_C_ZERO` | $a + b + c = 0$ | `a + b + c == 0` |
| `A_MINUS_B_PLUS_C_ZERO` | $a - b + c = 0$ | `a - b + c == 0` |
| `B_ZERO` | $b = 0$ | `b == 0` (Incomplete quadratic $ax^2 + c = 0$) |
| `C_ZERO` | $c = 0$ | `c == 0` (Incomplete quadratic $ax^2 + bx = 0$) |

### 7.2 Pedagogical Heuristic vs. Mathematical Truth Policy
Certain pedagogical ideas commonly taught in Vietnamese schools (e.g., *"nhẩm nghiệm tổng tích số nhỏ"* / *"mental arithmetic for small roots"*) involve cognitive heuristics rather than formal algebraic boundaries.

**Policy Formulation:**
1. **Mathematical Applicability** depends **ONLY** on objective algebraic invariants (e.g., $\Delta$ is a rational square, $a, b, c \in \mathbb{Q}$).
2. **Pedagogical Recommendation** can incorporate bounded heuristics (e.g., if roots $x_1, x_2 \in \mathbb{Z} \land |x_1|, |x_2| \le 12$, recommendation is `RECOMMENDED`; if roots are large integers or non-integers, recommendation falls to `NEUTRAL` or `DISCOURAGED`).
3. Under no circumstances is a heuristic presented as a mathematical law.

---

## 8. Mathematical Analysis of Canonical Quadratic Shortcuts

### 8.1 Special Case $a + b + c = 0$
- **Mathematical Basis:**
  Let $P(x) = ax^2 + bx + c$.  
  Evaluating at $x = 1$:  
  $$P(1) = a(1)^2 + b(1) + c = a + b + c$$
  If $a + b + c = 0$, then $P(1) = 0$, proving that $x_1 = 1$ is an exact root.  
  By Viète's Theorem for quadratics with $a \neq 0$:  
  $$x_1 \cdot x_2 = \frac{c}{a} \implies 1 \cdot x_2 = \frac{c}{a} \implies x_2 = \frac{c}{a}$$
- **Valid Domain:** All quadratic equations $ax^2 + bx + c = 0$ with $a \neq 0$ and $a + b + c = 0$.
- **Pedagogical Significance:** Provides an instant $O(1)$ mental verification without computing $\Delta = b^2 - 4ac$.
- **Common Student Misconceptions & Pitfalls:**
  1. Applying when $a = 0$ (degenerate linear case).
  2. Forgetting that the second root is $\frac{c}{a}$, not $-\frac{c}{a}$ or $c$.
  3. Misidentifying signs when coefficients are negative (e.g., in $2x^2 - 3x + 1 = 0$, verifying $2 + (-3) + 1 = 0$).

---

### 8.2 Special Case $a - b + c = 0$
- **Mathematical Basis:**
  Evaluating polynomial $P(x) = ax^2 + bx + c$ at $x = -1$:  
  $$P(-1) = a(-1)^2 + b(-1) + c = a - b + c$$
  If $a - b + c = 0$, then $P(-1) = 0$, proving that $x_1 = -1$ is an exact root.  
  By Viète's Theorem:  
  $$x_1 \cdot x_2 = \frac{c}{a} \implies (-1) \cdot x_2 = \frac{c}{a} \implies x_2 = -\frac{c}{a}$$
- **Valid Domain:** All quadratic equations $ax^2 + bx + c = 0$ with $a \neq 0$ and $a - b + c = 0$.
- **Common Student Misconceptions & Pitfalls:**
  1. Confusing the second root sign (mistaking $-\frac{c}{a}$ for $\frac{c}{a}$).
  2. Mixing up $a - b + c = 0$ with $a + b - c = 0$.

---

### 8.3 Reduced Discriminant $\Delta'$ ($b = 2b'$)
- **Mathematical Basis:**
  Let $b = 2b'$ where $b' = \frac{b}{2}$.  
  $$\Delta = b^2 - 4ac = (2b')^2 - 4ac = 4(b'^2 - ac) = 4\Delta'$$
  Since $\Delta = 4\Delta'$, $\text{sgn}(\Delta) = \text{sgn}(\Delta')$, and $\sqrt{\Delta} = 2\sqrt{\Delta'}$.  
  The roots reduce to:  
  $$x = \frac{-2b' \pm 2\sqrt{\Delta'}}{2a} = \frac{-b' \pm \sqrt{\Delta'}}{a}$$
- **Vietnamese Curriculum Standard:** Standard Grade 9 curriculum topic (SGK Toán 9 Tập 2, Chương IV).
- **Modeling Decision:** Modeled both as an executable method (`QUAD_FORMULA_REDUCED`) and as a quick arithmetic tip (`QUAD_TIP_REDUCED_FORMULA_EVEN_B`) referencing that method to avoid redundant formula definitions.

---

### 8.4 Viète Sum and Product Mental Factoring
- **Mathematical Basis:**
  For $ax^2 + bx + c = 0$ ($a \neq 0$), roots satisfy:  
  $$S = x_1 + x_2 = -\frac{b}{a}, \quad P = x_1 \cdot x_2 = \frac{c}{a}$$
  For monic polynomials ($a = 1$) with integer coefficients, if $x_1, x_2 \in \mathbb{Z}$, then $x_1, x_2$ must be integer factors of $c$ whose sum is $-b$.
- **Pedagogical Bounding:** The tip explicitly explains that while Viète identities are universally exact, *mental inspection* is only reliable when $c$ has few integer factors and $|S|, |P|$ are small.

---

## 9. Candidate Quadratic Quick Tips & Problem Forms Matrix

### 9.1 Candidate Quick Tips Matrix
| Tip ID | Category | Mathematical Basis | Related Method ID | Deterministic Predicate | Heuristic Involved? | Provenance Status | Disposition |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO` | `COEFFICIENT_RELATION` | $P(1) = a+b+c = 0 \implies x_1=1, x_2=c/a$ | `QUAD_VIETE_SPECIAL_SUM` | `A_NONZERO` & `A_PLUS_B_PLUS_C_ZERO` | No | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO` | `COEFFICIENT_RELATION` | $P(-1) = a-b+c = 0 \implies x_1=-1, x_2=-c/a$ | `QUAD_VIETE_SPECIAL_DIF` | `A_NONZERO` & `A_MINUS_B_PLUS_C_ZERO` | No | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `REDUCED_ARITHMETIC` | $b=2b' \implies \Delta'=b'^2-ac, x=(-b'\pm\sqrt{\Delta'})/a$ | `QUAD_FORMULA_REDUCED` | `A_NONZERO` & `B_EVEN_INTEGER` | No | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` | `ROOT_PRODUCT_SUM` | $x_1+x_2=-b/a, x_1 x_2=c/a$ with $x_1, x_2 \in \mathbb{Z}$ | `QUAD_VIETE_SUM_PRODUCT` | `A_NONZERO` & `DISCRIMINANT_RATIONAL_SQUARE` | Yes (Bounded integer search) | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_INCOMPLETE_B_ZERO` | `SPECIAL_STRUCTURE` | $b=0 \implies ax^2+c=0 \implies x^2=-c/a$ | `QUAD_FORMULA_STANDARD` | `A_NONZERO` & `B_ZERO` | No | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_INCOMPLETE_C_ZERO` | `SPECIAL_STRUCTURE` | $c=0 \implies x(ax+b)=0 \implies x=0 \lor x=-b/a$ | `QUAD_FACTORIZATION_Q` | `A_NONZERO` & `C_ZERO` | No | SGK Toán 9 KNTT | `READY_FOR_DATASET` |
| `QUAD_TIP_COMPLETING_SQUARE_MONIC` | `TRANSFORMATION` | $x^2+bx = (x+b/2)^2 - (b/2)^2$ | `QUAD_COMPLETE_SQUARE` | `A_NONZERO` & `A_EQ_ONE` | No | SGK Toán 9 KNTT | `NEEDS_SOURCE_REVIEW` |

---

### 9.2 Candidate Problem Forms Matrix
| Form ID | Title (VI) | Canonical Structure LaTeX | Primary Method ID | Applicable Tip IDs | Difficulty | Disposition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORM_GENERAL_STANDARD` | Phương trình bậc hai đầy đủ tổng quát | $ax^2 + bx + c = 0 \quad (a \neq 0)$ | `QUAD_FORMULA_STANDARD` | `QUAD_TIP_REDUCED_FORMULA_EVEN_B` | `BASIC` | `READY_FOR_DATASET` |
| `QUAD_FORM_SPECIAL_SUM_ZERO` | Phương trình bậc hai có $a+b+c=0$ | $ax^2 + bx + c = 0 \quad (a+b+c=0)$ | `QUAD_VIETE_SPECIAL_SUM` | `QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO` | `BASIC` | `READY_FOR_DATASET` |
| `QUAD_FORM_SPECIAL_DIF_ZERO` | Phương trình bậc hai có $a-b+c=0$ | $ax^2 + bx + c = 0 \quad (a-b+c=0)$ | `QUAD_VIETE_SPECIAL_DIF` | `QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO` | `BASIC` | `READY_FOR_DATASET` |
| `QUAD_FORM_INCOMPLETE_B_ZERO` | Phương trình bậc hai khuyết hệ số bậc nhất ($b=0$) | $ax^2 + c = 0 \quad (a \neq 0)$ | `QUAD_FORMULA_STANDARD` | `QUAD_TIP_INCOMPLETE_B_ZERO` | `BASIC` | `READY_FOR_DATASET` |
| `QUAD_FORM_INCOMPLETE_C_ZERO` | Phương trình bậc hai khuyết hệ số tự do ($c=0$) | $ax^2 + bx = 0 \quad (a \neq 0)$ | `QUAD_FACTORIZATION_Q` | `QUAD_TIP_INCOMPLETE_C_ZERO` | `BASIC` | `READY_FOR_DATASET` |
| `QUAD_FORM_MONIC_INTEGER_FACTORABLE`| Phương trình bậc hai monic nhẩm được nghiệm nguyên | $x^2 + bx + c = 0 \quad (x_1, x_2 \in \mathbb{Z})$ | `QUAD_VIETE_SUM_PRODUCT` | `QUAD_TIP_VIETE_INTEGER_SUM_PRODUCT` | `INTERMEDIATE` | `READY_FOR_DATASET` |

---

## 10. Relational Knowledge Graph Topology Expansion

The introduction of `QuickTipKnowledge` and `RelatedProblemFormKnowledge` extends MKE's static knowledge graph without disrupting the existing 4 node types (`METHOD`, `CONCEPT`, `FORMULA`, `THEOREM`).

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

### 10.1 Planned Graph Node & Edge Extensions
- **New `GraphNodeType` values:**
  - `QUICK_TIP`
  - `PROBLEM_FORM`
- **New `GraphEdgeType` values:**
  - `APPLIES_METHOD`: (Tip/Form $\to$ Method)
  - `USES_TIP`: (Form $\to$ Tip)
  - `VALID_FOR_FORM`: (Method $\to$ Form)
  - `RELATED_FORM`: (Form $\to$ Form)

---

## 11. Read-Only Knowledge API & Assessment Endpoints Design

### 11.1 Static Knowledge Query Endpoints
- `GET /api/v1/knowledge/tips/{tip_id}`: Returns authoritative `QuickTipKnowledgeView`.
- `GET /api/v1/knowledge/tips`: Returns paginated list of all verified quick tips.
- `GET /api/v1/knowledge/problem-forms/{form_id}`: Returns authoritative `RelatedProblemFormKnowledgeView`.
- `GET /api/v1/knowledge/problem-forms`: Returns list of all verified problem forms.
- `GET /api/v1/knowledge/methods/{method_id}/tips`: Returns tips associated with a canonical method.
- `GET /api/v1/knowledge/methods/{method_id}/problem-forms`: Returns problem forms solved by a canonical method.

### 11.2 Dynamic Problem Assessment API Integration
In Milestone K1-05, the existing solve endpoint (`POST /api/v1/algebra/solve` and `SolveResponse`) will receive optional enriched assessment fields produced by the backend:
- `applicable_quick_tips: List[QuickTipAssessmentView]`
- `matched_problem_form_id: Optional[str]`

The frontend will consume this data directly without calculating or generating mathematical shortcuts.

---

## 12. Provenance & Non-Fabrication Invariants

To guarantee 100% mathematical integrity, K1 establishes these immutable invariants:

1. **Zero Frontend Fabrication:** The frontend MUST NEVER invent, guess, generate, or calculate quick tips or problem forms.
2. **Zero LLM Authority:** Large language model outputs are never used as source truth for mathematical rules, tips, or assessments.
3. **Static/Dynamic Non-Conflation:** Static knowledge files NEVER claim that a tip applies to a specific problem instance without backend evaluation.
4. **Authoritative Provenance Required:** Every `QuickTipKnowledge` and `RelatedProblemFormKnowledge` entry must cite verifiable textbook or curriculum sources.
5. **Deterministic Condition Verification:** Tip applicability is evaluated solely via exact rational arithmetic over AST/canonical problem invariants.
6. **Immutable SHA-256 Dataset Hashing:** All static datasets are serialized to sorted JSON and hashed with SHA-256 upon repository startup.
7. **Curated Examples Only:** Worked and practice examples are static, validated problem instances with exact proofs, not dynamically synthesized strings.

---

## 13. Risk Analysis & Mitigation Matrix

| Risk | Likelihood | Impact | Architectural Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Teaching shortcuts without conditions** | High | High | Strict Pydantic fields `valid_scope` and `invalid_scope` are mandatory on every tip. |
| **Confusing Method vs. Tip** | Medium | Medium | Clear semantic separation: Methods are general solving algorithms; Tips are specific algebraic arithmetic shortcuts. |
| **Overfitting Vietnamese exam tricks** | Medium | Low | Require formal theorem backing and standard curriculum references for all shortcuts. |
| **Subjective "easy numbers" heuristics** | High | Medium | Isolate cognitive heuristics to `recommendation` level only; `applicability` remains purely mathematical. |
| **Knowledge Drift / Duplication** | Low | Medium | Tips reference existing `FormulaKnowledge`, `TheoremKnowledge`, and `MethodDefinition` by stable ID rather than duplicating text. |
| **Static / Dynamic Truth Leakage** | Medium | Critical | Distinct schemas: `QuickTipKnowledge` (static) vs. `QuickTipAssessmentView` (dynamic runtime DTO). |

---

## 14. Implementation Roadmap (Post-P0)

```
+-------------------------------------------------------------------------+
| Milestone K1 Implementation Roadmap                                     |
|                                                                         |
|  [K1-P0] Preflight Blueprint & Architectural Contracts (CURRENT)        |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-01] Pydantic v2 Knowledge Schemas (QuickTip & ProblemForm)         |
|     │                                                                   |
|     ▼                                                                   |
|  [K1-02] Curated Static JSON Dataset with Verified Provenance           |
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

## 15. Acceptance Criteria for K1-P0

- [x] Preflight document created at `docs/preflight/MVP_V1_K1_P0_QUICK_TIP_RELATED_FORM_KNOWLEDGE_PREFLIGHT.md`.
- [x] Explicit UI freeze statement included (`UI STATUS: FROZEN — NO FRONTEND CHANGES AUTHORIZED`).
- [x] Strict Pydantic schemas designed for `QuickTipKnowledge` and `RelatedProblemFormKnowledge`.
- [x] Static vs. dynamic truth boundary formalized.
- [x] Deterministic condition predicate language and heuristic policy defined.
- [x] Candidate tips and problem forms matrix mapped with exact mathematical proofs.
- [x] ZERO production code modified (`src/mke_product/**`, `src/frontend/**`, `tests/**`).
- [x] S3 dataset SHA (`e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66`) untouched.
- [x] Single documentation commit created on dedicated preflight branch.
