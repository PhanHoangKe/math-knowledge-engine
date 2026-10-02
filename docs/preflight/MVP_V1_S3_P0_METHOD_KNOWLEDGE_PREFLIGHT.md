# MKE PRODUCT — S3-P0 METHOD KNOWLEDGE & GRAPH SURFACES PREFLIGHT REPORT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-02  
**Target Milestone:** S3-P0 Method Knowledge & Graph Surfaces Preflight  
**Branch:** `product/mvp-v1-s3-p0-method-knowledge-preflight`  
**Baseline Acceptance Tag:** `mvp-v1-algebra-slice-accepted`  
**Baseline Commit SHA:** `e620c96470514f8bd7563efba25427c7a4764488`  
**Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (100% Untouched)  
**Preflight Status:** `PENDING INDEPENDENT S3-P0 AUDIT`

---

## 1. Executive Summary & Authorization Scope

This preflight document establishes the architectural foundation, schema designs, repository inventory, graph models, and staged implementation roadmap for **Milestone S3: Method Knowledge & Graph Surfaces**.

### 1.1 Authorization & Non-Goals
- **AUTHORIZED:** Preflight analysis, repository knowledge inventory, schema contracts design, graph distinction architecture, API exposure alternatives, and implementation staging.
- **STRICTLY NOT AUTHORIZED (ZERO RUNTIME MUTATION):**
  - No production backend or frontend code changes.
  - No modification to accepted S1 mathematical engine (`src/mke_product/domain/**`, `application/**`, `parser/**`).
  - No modification to accepted S2 transport layer (`src/mke_product/transport/**`).
  - No modification to accepted React workspace (`src/frontend/src/**`).
  - No database migration, No LLM / RAG integration, No merge of research tracks.

---

## 2. S3 Product Objective & Core Principles

The S3 layer enriches the First Algebra Workspace with structured pedagogical knowledge and relational graph surfaces to answer critical learner and educator questions:
1. **Why is this method applicable?** (Formal mathematical criteria vs. specific problem invariants).
2. **Why is another method not applicable?** (Missing structural conditions, e.g. non-zero discriminant, non-integer roots).
3. **What prerequisites are required?** (Fundamental concepts, prior skills, radical arithmetic).
4. **Which formulas and theorems support this method?** (Canonical mathematical statements and LaTeX proofs).
5. **How does editing a coefficient affect downstream knowledge?** (Instant dynamic invalidation of problem assessments vs. invariant static concept definitions).
6. **What related concepts should the learner study?** (Curriculum-aligned concept networks).

### 2.1 The Golden Invariant of S3
> **S3 ENRICHES MATHEMATICAL TRUTH; IT NEVER BECOMES A SECOND SOLVER.**  
> All mathematical evaluations, root calculations, discriminant analyses, and execution availability remain strictly governed by the S1 Symbolic Core. S3 provides structured pedagogical context and relational graphs around S1 execution truth.

---

## 3. Repository Knowledge Asset Inventory

A repository-wide inventory across `src/mke_product/**`, `src/mke/**`, `docs/**`, and historical DEV-02A commits classifies all existing knowledge artifacts:

| Category | Location | Content / Artifact | Production Reusability |
| :--- | :--- | :--- | :--- |
| **Production Safe** | `src/mke_product/domain/models.py` | `MethodDefinition`, `MethodAssessment`, `PrerequisiteStatus`, `DependencyNode` | **REUSE & EXTEND** (Strong Pydantic v2 foundation). |
| **Production Safe** | `src/mke_product/domain/registry.py` | `MethodRegistry` with 9 frozen `MethodId`s and orthogonal capability matrix | **AUTHORITY BASELINE** (Stable foreign keys). |
| **Production Safe** | `src/mke_product/domain/dag.py` | `DependencyGraph` (DAG engine, topological invalidation, cycle detection) | **REUSE AS REACTIVE DAG** (Preserve for parameter dependencies). |
| **Production Safe** | `src/mke_product/application/traces/*` | Structured solution step traces with `rule_or_theorem_used`, `why_this_step_vi` | **INTEGRATE** (Link step rules to S3 Theorem/Formula IDs). |
| **Research-Only** | `src/mke/g4p1/**` | Multi-CAS trust verification, Merkle batch manifests, relation judges | **RESEARCH ONLY** (Do not merge into S3 product). |
| **Research-Only** | Commit `753382a` (`src/mke/knowledge/*`) | SQLite indexer, Dev01 adapter, research metadata schemas | **RESEARCH ONLY** (Extract schema ideas; do not import). |
| **Legacy / Inactive** | `src/mke_product/ui/ui00/**` | Legacy monolithic HTML UI | **LEAVE UNTOUCHED** (Frozen historical baseline). |
| **Historical Evidence**| `evidence/p03b/**` | Milestone evidence screenshots and logs | **IMMUTABLE** (Never touch or modify). |

---

## 4. DEV-02A Research Input Evaluation

Historical DEV-02A (`753382a023835dbdbe6b074ca6101a3292d3474c`) provided an initial research exploration of knowledge schemas. We evaluate its concepts for S3 product adaptation:

| DEV-02A Concept | DEV-02A Implementation | S3 Product Classification | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Method Taxonomy** | Methods M1–M5 (Linear, Quadratic, Factoring, Rational, Biquadratic) | `REIMPLEMENT_CLEANLY` | Product baseline strictly uses 9 frozen quadratic method IDs (`QUAD_*`). |
| **Concept Entities** | Freeform dictionary structures | `ADAPT` | Formalize into strict Pydantic v2 `ConceptKnowledge` models with bilingual fields. |
| **Prerequisite Links** | Ad-hoc string lists | `ADAPT` | Formalize as strictly validated typed edges with referential integrity. |
| **Dev01 Adapter & Dispatcher** | Heuristic AST pattern matcher | `REJECT` | Violates S1 exact polynomial normalizer and orthogonal assessment engine. |
| **SQLite Indexer** | Dynamic SQLite database file | `REJECT` (for MVP S3) | Static JSON/YAML files in Git provide superior determinism, auditability, zero-dependency deployment, and diffability. |
| **Transfer Near-Miss Pairs** | Heuristic pedagogical discrepancies | `RESEARCH_ONLY` | Keep in research track; do not introduce pedagogical approximations into S3 product. |

---

## 5. Current Product 9-Method Model Inventory

Current product truth registered in `src/mke_product/domain/registry.py`:

| Method ID | Title (VI) | Support Status | Execution Availability | Default Recommendation | Verification Capability | Prerequisites | Trace Available |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORMULA_STANDARD` | Công thức nghiệm tổng quát | `SUPPORTED` | `AVAILABLE` | `RECOMMENDED` (Neutral if Vieta applies) | `HOST_VERIFIABLE` | `PREREQ_RADICALS`, `PREREQ_POLYNOMIAL_COEFF` | **YES** |
| `QUAD_FORMULA_REDUCED` | Công thức nghiệm thu gọn | `SUPPORTED` | `AVAILABLE` | `RECOMMENDED` (if $b$ is even) | `HOST_VERIFIABLE` | `PREREQ_RADICALS` | **YES** |
| `QUAD_FACTORIZATION_Q` | Phân tích nhân tử trên $\mathbb{Q}$ | `SUPPORTED` | `UNAVAILABLE` | `NEUTRAL` (or `RECOMMENDED` if split exists) | `HOST_VERIFIABLE` | `PREREQ_FACTORING_ALGEBRA` | NO (`ANALYZED_NO_EXECUTION`) |
| `QUAD_FACTORIZATION_R` | Phân tích nhân tử trên $\mathbb{R}$ | `SUPPORTED` | `UNAVAILABLE` | `DISCOURAGED` | `HOST_VERIFIABLE` | `PREREQ_REAL_SURDS` | NO (`ANALYZED_NO_EXECUTION`) |
| `QUAD_COMPLETE_SQUARE` | Biến đổi tách bình phương | `SUPPORTED` | `UNAVAILABLE` | `NEUTRAL` / `DISCOURAGED` | `HOST_VERIFIABLE` | `PREREQ_PERFECT_SQUARE_IDENTITY` | NO (`ANALYZED_NO_EXECUTION`) |
| `QUAD_VIETE_SPECIAL_SUM` | Nhẩm nghiệm $a+b+c=0$ | `SUPPORTED` | `AVAILABLE` | `RECOMMENDED` (if $a+b+c=0$) | `HOST_VERIFIABLE` | `PREREQ_VIETE_THEOREM` | **YES** |
| `QUAD_VIETE_SPECIAL_DIF` | Nhẩm nghiệm $a-b+c=0$ | `SUPPORTED` | `AVAILABLE` | `RECOMMENDED` (if $a-b+c=0$) | `HOST_VERIFIABLE` | `PREREQ_VIETE_THEOREM` | **YES** |
| `QUAD_VIETE_SUM_PRODUCT` | Tìm hai số theo Tổng & Tích | `SUPPORTED` | `UNAVAILABLE` | `NEUTRAL` | `HOST_VERIFIABLE` | `PREREQ_VIETE_THEOREM` | NO (`ANALYZED_NO_EXECUTION`) |
| `QUAD_GRAPHICAL_ANALYSIS` | Khảo sát đồ thị Parabol | `SUPPORTED` | `UNAVAILABLE` | `NEUTRAL` | `NOT_APPLICABLE` | `PREREQ_PARABOLA_GRAPH` | NO (`ANALYZED_NO_EXECUTION`) |

---

## 6. Proposed Knowledge Entity Schemas

### 6.1 `MethodKnowledge` Schema (Minimum Coherent Contract)
```python
class MethodKnowledge(BaseModel):
    """Static epistemological and pedagogical definition of a solution method."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str = Field(..., description="Foreign key matching MethodId in domain registry")
    title_vi: str
    title_en: str
    summary_vi: str
    summary_en: str
    learning_objective_vi: str
    learning_objective_en: str
    formal_description_vi: str
    formal_description_en: str
    applicability_criteria_vi: List[str]
    non_applicability_criteria_vi: List[str]
    prerequisite_concept_ids: List[str]
    formula_refs: List[str]
    theorem_refs: List[str]
    common_mistakes_vi: List[str]
    diagnostic_tips_vi: List[str]
    related_method_ids: List[str]
    curriculum_alignment: CurriculumRef
    provenance: SourceProvenance
    version: str = Field(default="1.0.0")
```

### 6.2 `ConceptKnowledge` Schema
```python
class ConceptKnowledge(BaseModel):
    """Mathematical concept definition across algebra, geometry, and calculus."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    concept_id: str = Field(..., description="Unique snake_case concept ID, e.g. 'concept_discriminant'")
    title_vi: str
    title_en: str
    definition_vi: str
    definition_en: str
    prerequisite_concept_ids: List[str] = Field(default_factory=list)
    related_concept_ids: List[str] = Field(default_factory=list)
    formula_refs: List[str] = Field(default_factory=list)
    method_refs: List[str] = Field(default_factory=list)
    curriculum_refs: List[CurriculumRef] = Field(default_factory=list)
    provenance: SourceProvenance
    version: str = Field(default="1.0.0")
```

### 6.3 `FormulaKnowledge` & `TheoremKnowledge` Schemas
```python
class FormulaKnowledge(BaseModel):
    """Canonical mathematical formula entity with exact LaTeX representation."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    formula_id: str = Field(..., description="e.g. 'FORMULA_QUADRATIC_STANDARD'")
    title_vi: str
    title_en: str
    latex_template: str
    variables_description_vi: Dict[str, str]
    domain_conditions_vi: str
    related_concept_ids: List[str]
    provenance: SourceProvenance
    version: str = Field(default="1.0.0")


class TheoremKnowledge(BaseModel):
    """Mathematical theorem with formal premises and conclusions."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    theorem_id: str = Field(..., description="e.g. 'THEOREM_VIETA_RELATIONS'")
    title_vi: str
    title_en: str
    statement_vi: str
    statement_en: str
    formal_statement_latex: str
    hypotheses_vi: List[str]
    conclusions_vi: List[str]
    related_concept_ids: List[str]
    provenance: SourceProvenance
    version: str = Field(default="1.0.0")
```

---

## 7. Static Knowledge vs. Dynamic Assessment Separation

We freeze a strict boundary between static knowledge and dynamic runtime evaluation:

```text
┌─────────────────────────────────────────────────────────┐
│              STATIC METHOD KNOWLEDGE (S3)               │
│  - What is Completing the Square?                       │
│  - What prerequisites does it have?                     │
│  - Which formulas/theorems support it?                  │
│  - What are common learner mistakes?                    │
│  - Curriculum mapping (Grade 9, Topic 3)                │
│  Invariant under coefficient edits (a, b, c)            │
└────────────────────────────┬────────────────────────────┘
                             │ Linked via method_id foreign key
                             ▼
┌─────────────────────────────────────────────────────────┐
│             DYNAMIC PROBLEM ASSESSMENT (S1)             │
│  - Is method applicable to 2x^2 - 5x + 3 = 0? (YES)     │
│  - Is it executable in current build? (UNAVAILABLE)     │
│  - Why? (ANALYZED_NO_EXECUTION)                         │
│  - Exact discriminant Δ = 1 > 0                         │
│  - Recomputed on every 350ms coefficient edit           │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Formula & Theorem Architecture

### Architectural Decision: Separate First-Class Entities (Option A)
- **Decision:** Model Formulas and Theorems as **separate first-class entities** rather than embedding raw text strings inside `MethodKnowledge`.
- **Concrete Example:**
  - `THEOREM_VIETA_RELATIONS` is shared across 3 distinct methods: `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`, and `QUAD_VIETE_SUM_PRODUCT`.
  - `FORMULA_QUADRATIC_STANDARD` is linked to both `concept_discriminant` and `QUAD_FORMULA_STANDARD`.
- **Benefits:**
  - Eliminates duplication of LaTeX strings and explanations across methods and concepts.
  - Enables direct graph edges (`Method -[USES_THEOREM]-> Theorem <-[EXPLAINS]- Concept`).
  - Supports standalone Formula Reference cards in UI.

---

## 9. Typed Knowledge Edge Vocabulary

To prevent graph bloat while supporting rich educational navigation, S3 accepts a small, strictly-typed vocabulary of 7 edge relations:

| Edge Relation | Source Type | Target Type | Direction | Symmetry | Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `REQUIRES` | Method / Concept | Concept | Directed ($\to$) | Asymmetric | Source cannot be understood or applied without target concept. |
| `USES_FORMULA` | Method | Formula | Directed ($\to$) | Asymmetric | Method execution relies on evaluating this formula. |
| `USES_THEOREM` | Method | Theorem | Directed ($\to$) | Asymmetric | Method correctness is mathematically proven by this theorem. |
| `ALTERNATIVE_TO` | Method | Method | Bidirectional ($\leftrightarrow$) | Symmetric | Solves the same mathematical problem class via different technique. |
| `SPECIAL_CASE_OF`| Method | Method | Directed ($\to$) | Asymmetric | Source is an optimized short-cut of general method under specific invariants. |
| `RELATED_TO` | Concept / Method | Concept | Bidirectional ($\leftrightarrow$) | Symmetric | Pedagogically related conceptual connection. |
| `LEARN_BEFORE` | Concept | Concept | Directed ($\to$) | Asymmetric | Curriculum learning pathway prerequisite ordering. |

---

## 10. Graph Distinction: Knowledge Graph vs. Reactive Dependency DAG

S3 models and exposes two fundamentally distinct graphs with zero semantic conflation:

```text
========================================================================================
GRAPH A: STATIC KNOWLEDGE GRAPH
========================================================================================
Nodes: Concepts, Methods, Formulas, Theorems
Edges: REQUIRES, USES_FORMULA, USES_THEOREM, ALTERNATIVE_TO, SPECIAL_CASE_OF, LEARN_BEFORE
Semantics: Epistemological relationship network (Pedagogical Textbook View)
Reactivity: Static, invariant, heavily cacheable

       [Concept: Real Numbers] ──▶ [Concept: Radicals] ──▶ [Formula: Quadratic Formula]
                                                                 ▲
                                                                 │ USES_FORMULA
                                                     [Method: QUAD_FORMULA_STANDARD]
                                                                 │ ALTERNATIVE_TO
                                                     [Method: QUAD_COMPLETE_SQUARE]

========================================================================================
GRAPH B: REACTIVE PARAMETER DEPENDENCY DAG
========================================================================================
Nodes: Parameter instances (a,b,c), discriminant (Δ), classification, roots, trace, cert
Edges: COMPUTATIONAL_DEPENDENCY (Dataflow / Invalidation)
Semantics: Dynamic computational pipeline for active problem (Interactive Execution View)
Reactivity: Dynamically invalidated and recomputed on every coefficient change

       (Coefficients a,b,c) ──▶ (Discriminant Δ) ──▶ (Root Classification) ──▶ (Roots)
                                      │                                          │
                                      ▼                                          ▼
                         (Method Assessments)                           (Solution Traces)
                                      │                                          │
                                      └──────────────────┬───────────────────────┘
                                                         ▼
                                           (Verification Certificate)
========================================================================================
```

---

## 11. Existing Reactive DAG Inventory & Status

Inspection of `src/mke_product/domain/dag.py`:
- **Existing Nodes in `build_quadratic_workspace_dag()`:**
  1. `coefficients`: `INPUT`
  2. `discriminant`: `COMPUTED`
  3. `root_classification`: `COMPUTED`
  4. `roots`: `COMPUTED`
  5. `method_assessments`: `COMPUTED`
  6. `solution_traces`: `COMPUTED`
  7. `verification_certificate`: `COMPUTED`
  8. `graph_visualization`: `COMPUTED`
  9. `pedagogical_view`: `PRESENTATION`
- **Current Runtime Status:**
  - The DAG data structure and invalidation algorithms (`invalidate()`, `_is_reachable()`, `dfs_topo()`) are fully implemented and unit-tested in `domain/dag.py`.
  - The orchestrator currently executes these computations in direct linear pipeline.
  - S3 will expose this DAG structure cleanly for UI visualization without altering S1 execution order.

---

## 12. Recommended API Architecture: Option C (Hybrid)

We evaluated three API exposure strategies:

| Metric | Option A: Monolithic Solve Payload | Option B: Pure Separate Endpoints | Option C: Hybrid Architecture (RECOMMENDED) |
| :--- | :--- | :--- | :--- |
| **Payload Size** | Large (50+ KB per debounce tick with repeated textbook text) | Minimal solve payload (~2 KB) | Minimal solve payload (~2 KB); static knowledge fetched once (~15 KB) |
| **Debounce Performance** | High CPU & network overhead on 350ms edit | Excellent solve latency | **Optimal solve latency** (only dynamic assessment transmitted) |
| **Cacheability** | Zero (dynamic solve is uncacheable) | High cacheability | **Maximum cacheability** (`Cache-Control: public, max-age=3600` on static knowledge) |
| **Offline Capability** | Bundled inside solve | Multiple HTTP roundtrips | **Frontend can pre-bundle or pre-fetch static knowledge JSON** |
| **Coupling** | High (backend math tightly coupled with textbook prose) | Clean separation | **Clean separation via stable Foreign Keys (`method_id`, `concept_id`)** |

### Proposed Endpoints for S3:
1. `POST /api/v1/algebra/solve` (Existing S2): Returns dynamic result + stable knowledge reference IDs.
2. `GET /api/v1/knowledge/methods/{method_id}`: Returns static `MethodKnowledge`.
3. `GET /api/v1/knowledge/concepts/{concept_id}`: Returns static `ConceptKnowledge`.
4. `GET /api/v1/knowledge/graph`: Returns full static Knowledge Graph export.

---

## 13. Reactive Knowledge Ownership Rules

| Parameter / Field | Owner Layer | Reactivity Behavior |
| :--- | :--- | :--- |
| **$a, b, c$ Coefficients** | User Input / Client State | Triggers 350ms debounce solve request. |
| **$\Delta$, Root Classification, Roots** | S1 Symbolic Core | Dynamically recomputed on backend. |
| **Method Applicability & Reasons** | S1 Method Registry | Dynamically assessed based on $a,b,c$ and $\Delta$. |
| **Solution Trace & Step LaTeX** | S1 Trace Generators | Dynamically generated from exact algebraic values. |
| **Verification Certificate** | S1 Host Verifier | Dynamically signed with unkeyed SHA-256 fingerprint. |
| **Method Definition, Formulas, Theorems**| S3 Static Knowledge Repository | **100% Invariant** across coefficient edits. |
| **Concept Definitions & Prereqs** | S3 Static Knowledge Repository | **100% Invariant** across coefficient edits. |
| **Frontend Presentation** | React S3 Components | Combines dynamic status with cached static knowledge without fabricating math. |

---

## 14. Frontend S3 Surface Proposal

Future S3 workspace surfaces to be implemented in React:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ MKE Live Algebra Workspace                                          [EN | VI] [🌙 / ☀️]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Equation Input: [ 2*x^2 - 5*x + 3 = 0 ]                                [ Compute ]     │
├──────────────────────────────────────┬─────────────────────────────────────────────────┤
│ Active Method: nhẩm a+b+c=0 (SOLVED) │  📚 PEDAGOGICAL KNOWLEDGE SURFACE (S3)          │
│                                      ├─────────────────────────────────────────────────┤
│ [ Step-by-Step Solution Trace ]      │  ▼ 1. "Why this method?"                        │
│ Step 1: Xác định hệ số a=2, b=-5, c=3│     Tổng hệ số 2 + (-5) + 3 = 0.                │
│ Step 2: a + b + c = 0 -> x1=1, x2=3/2│     Áp dụng hệ quả định lý Viète nhẩm nghiệm.   │
│                                      ├─────────────────────────────────────────────────┤
│ [ Verification Certificate ]         │  ▼ 2. Prerequisites & Concepts                  │
│ ✅ Verified Complete (SHA-256: e620) │     • Định lý Viète [concept_vieta_relations]   │
│                                      │     • Hệ số đa thức [concept_polynomial_coeff]  │
│ [ 9-Method Catalog ]                 ├─────────────────────────────────────────────────┤
│ • Công thức tổng quát (Khả thi)      │  ▼ 3. Formulas & Theorems                       │
│ • Công thức thu gọn (Khả thi)        │     Định lý Viète: x1 + x2 = -b/a, x1*x2 = c/a  │
│ • Nhẩm a+b+c=0 (ĐANG CHỌN - Tối ưu)  ├─────────────────────────────────────────────────┤
│ • Tách nhân tử (Chưa hỗ trợ giải)    │  ▼ 4. Interactive Knowledge Connections         │
│ • Tách bình phương (Chưa hỗ trợ giải)│     [ View Knowledge Graph ] [ View Reactive DAG]
└──────────────────────────────────────┴─────────────────────────────────────────────────┘
```

---

## 15. GraphModel & Serialization Design

```python
class GraphNodeType(str, Enum):
    CONCEPT = "CONCEPT"
    METHOD = "METHOD"
    FORMULA = "FORMULA"
    THEOREM = "THEOREM"
    PARAMETER = "PARAMETER"
    COMPUTATION = "COMPUTATION"


class GraphNode(BaseModel):
    """Generic serializable graph node for visualization."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    node_id: str
    node_type: GraphNodeType
    label: str
    subtitle: Optional[str] = None
    status: Optional[str] = None
    knowledge_ref: Optional[str] = None
    dependency_ref: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Generic serializable graph edge."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source: str
    target: str
    relation_type: str
    label: Optional[str] = None
    is_directed: bool = True


class GraphModel(BaseModel):
    """Deterministic export model for graph visualizations."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    graph_id: str
    title: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    is_acyclic: bool = True
    version: str = Field(default="1.0.0")
```

---

## 16. Vietnamese Education Alignment & Provenance Design

### 16.1 Curriculum Reference Schema
```python
class CurriculumMappingStatus(str, Enum):
    VERIFIED_MAPPING = "VERIFIED_MAPPING"
    PROVISIONAL_MAPPING = "PROVISIONAL_MAPPING"


class CurriculumRef(BaseModel):
    """Authoritative curriculum standard reference."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    framework: str = Field(default="GDPT_2018", description="e.g. GDPT_2018, CCSS, IB")
    subject: str = Field(default="TOAN")
    grade_band: str = Field(default="GRADE_9", description="GRADE_8, GRADE_9, GRADE_10")
    topic: str = Field(..., description="e.g. 'PHUONG_TRINH_BAC_HAI_MOT_AN'")
    competency_ref: str = Field(..., description="Specific MoET learning standard code")
    source_document: str = Field(..., description="Official MoET circular / textbook name")
    source_locator: str = Field(..., description="Chapter / section reference")
    status: CurriculumMappingStatus = Field(default=CurriculumMappingStatus.VERIFIED_MAPPING)
```

### 16.2 Source Provenance Schema
```python
class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class SourceProvenance(BaseModel):
    """Traceable academic or curriculum citation."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source_id: str
    source_type: str = Field(default="TEXTBOOK", description="TEXTBOOK, OFFICIAL_CURRICULUM, MONOGRAPH")
    title: str
    author_or_institution: str
    publication_year: Optional[int] = None
    locator: str = Field(..., description="Page, section, or circular article locator")
    verification_status: ProvenanceStatus = Field(default=ProvenanceStatus.VERIFIED)
```

---

## 17. Determinism, Storage & No-RAG Policy

### 17.1 Deterministic Storage Architecture
- **Decision:** Static knowledge entities stored in **structured JSON files** (`src/mke_product/knowledge/data/`) bundled with the application repository.
- **Benefits:**
  - 100% offline-first execution with zero external database dependencies.
  - Seamless Git diffability and peer-reviewable knowledge updates.
  - In-memory startup index provides sub-millisecond lookup latency.
  - Deterministic serialization with canonical key ordering and SHA-256 `content_hash` for bundle cache integrity.

### 17.2 Strict No-RAG Policy in S3 Core
> **S3 CORE KNOWLEDGE OPERATES WITH ZERO AI / EMBEDDING / VECTOR DB DEPENDENCIES.**  
> All explanations, prerequisites, diagnostic tips, and curriculum alignments are deterministically authored and verified. Any future AI / RAG capabilities will consume S3 structured knowledge as ground truth, never generate unverified mathematical knowledge.

---

## 18. Acceptance Dataset Design (9 Methods & Canonical Test Equations)

### 18.1 Static Knowledge Fixture (All 9 Methods)
The S3 acceptance dataset will provide complete static `MethodKnowledge`, `ConceptKnowledge`, `FormulaKnowledge`, and `TheoremKnowledge` for all 9 registered methods:
1. `QUAD_FORMULA_STANDARD` $\leftrightarrow$ `FORMULA_QUADRATIC_STANDARD`, `concept_discriminant`, `concept_quadratic_equation`
2. `QUAD_FORMULA_REDUCED` $\leftrightarrow$ `FORMULA_QUADRATIC_REDUCED`, `concept_reduced_discriminant`
3. `QUAD_FACTORIZATION_Q` $\leftrightarrow$ `concept_factoring_rational`, `concept_rational_root`
4. `QUAD_FACTORIZATION_R` $\leftrightarrow$ `concept_factoring_real`, `concept_real_surd`
5. `QUAD_COMPLETE_SQUARE` $\leftrightarrow$ `FORMULA_PERFECT_SQUARE`, `concept_completing_square`
6. `QUAD_VIETE_SPECIAL_SUM` $\leftrightarrow$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_special_sum`
7. `QUAD_VIETE_SPECIAL_DIF` $\leftrightarrow$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_special_dif`
8. `QUAD_VIETE_SUM_PRODUCT` $\leftrightarrow$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_sum_product`
9. `QUAD_GRAPHICAL_ANALYSIS` $\leftrightarrow$ `concept_parabola_vertex`, `concept_axis_symmetry`

### 18.2 Canonical Test Equations for Integration Verification
1. **$x^2 - 5x + 6 = 0$**: Two distinct rational roots ($x_1=2, x_2=3$), tests standard/reduced formula, Vieta relations, rational factorization.
2. **$x^2 + 2x + 1 = 0$**: One repeated root ($x=-1$), tests double root classification, perfect square identity.
3. **$x^2 + 1 = 0$**: No real roots ($\Delta = -4 < 0$), tests non-applicability criteria, graphical parabola lack of real intercepts.
4. **$2x^2 + 3x + 7 = 0$**: Odd linear coefficient with negative discriminant, tests reduced formula non-applicability diagnostic tips.

---

## 19. S3 Implementation Test Plan

A comprehensive 5-layer test strategy is designed for S3 implementation:
1. **Schema & Contract Tests (`tests/test_knowledge_schemas.py`):**
   - Strict Pydantic v2 validation, rejection of unwhitelisted fields, immutability (`frozen=True`).
2. **Referential Integrity & Graph Tests (`tests/test_knowledge_graph.py`):**
   - Zero dangling foreign keys (`prerequisite_concept_ids`, `formula_refs`, `theorem_refs`, `related_method_ids`).
   - Strict DAG cycle detection on `REQUIRES` and `LEARN_BEFORE` edges.
   - Deterministic topological sort verification.
3. **Service & Repository Tests (`tests/test_knowledge_repository.py`):**
   - Sub-millisecond lookup by ID, family filtering, multilingual fallback handling, deterministic SHA-256 bundle hash.
4. **FastAPI Route Contract Tests (`tests/test_knowledge_api.py`):**
   - GET `/api/v1/knowledge/methods/{method_id}` returns 200 with schema-valid JSON.
   - Unknown IDs return structured 404 `KNOWLEDGE_NOT_FOUND`.
   - `Cache-Control` header verification.
5. **Frontend UI & Browser E2E Tests (`src/frontend/src/test/**`, `tests/test_mvp_v1_react_e2e.py`):**
   - "Why this method?" panel renders correct dynamic reason + static criteria.
   - Formula card displays rendered KaTeX LaTeX.
   - Coefficient debounce ($6 \to 7$) instantly updates dynamic reason while preserving static concept definitions.

---

## 20. Integration Risk Matrix

| Risk ID | Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-01** | DEV-02A research schema mismatch contaminating production models. | **HIGH** | Strict boundary: zero code copied from DEV-02A without clean Pydantic v2 reimplementation. |
| **R-02** | Knowledge IDs drifting from product `MethodId`. | **HIGH** | Static CI test asserting bidirectional 1:1 foreign key match between `MethodRegistry` and `MethodKnowledge`. |
| **R-03** | Conflating static epistemological graph with dynamic parameter DAG. | **MEDIUM** | Separate Python modules (`knowledge_graph.py` vs `domain/dag.py`) and distinct UI views. |
| **R-04** | Large static knowledge payload bloating 350ms solve debounce. | **MEDIUM** | Option C Hybrid API architecture: solve returns only IDs; static knowledge fetched/cached separately. |
| **R-05** | Circular prerequisite definitions in concept graph. | **MEDIUM** | Automated DFS cycle detection test executed during knowledge bundle build. |
| **R-06** | Hardcoded Vietnamese-only content blocking bilingual parity. | **MEDIUM** | Strict model requirement for symmetric `_vi` and `_en` fields across all knowledge entities. |
| **R-07** | Inaccurate or unverified curriculum mapping claims. | **LOW** | `CurriculumRef` requires `status` distinction (`VERIFIED_MAPPING` vs `PROVISIONAL_MAPPING`) with citation locator. |
| **R-08** | Incompatibility with future geometry/calculus expansion. | **LOW** | Generic `ConceptKnowledge` and `FormulaKnowledge` models designed without algebra-specific hardcoding. |

---

## 21. Proposed S3 Implementation Stages

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-01: KNOWLEDGE SCHEMAS & STATIC ACCEPTANCE DATASET                             │
│ - Implement Pydantic v2 schemas: MethodKnowledge, ConceptKnowledge, Formula, Theorem. │
│ - Author verified JSON dataset for all 9 quadratic methods and core algebra concepts.  │
│ - Tests: Schema validation and referential integrity tests (100% green).              │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-02: IN-MEMORY KNOWLEDGE REPOSITORY & GRAPH SERVICE                            │
│ - Implement KnowledgeRepository with indexed lookups and topological traversal.        │
│ - Implement GraphModel exporter for Knowledge Graph and Reactive DAG.                  │
│ - Tests: Lookup performance, acyclicity validation, deterministic graph serialization.  │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-03: FASTAPI STATIC KNOWLEDGE API ENDPOINTS                                    │
│ - Implement GET /api/v1/knowledge/methods/{id}, concepts/{id}, /graph.                │
│ - Configure HTTP caching headers (Cache-Control: public, max-age=3600).                │
│ - Tests: FastAPI TestClient integration tests and OpenAPI schema sync.                 │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-04: FRONTEND METHOD KNOWLEDGE SURFACES & FORMULA CARDS                        │
│ - Implement TypeScript knowledge DTOs and API client methods.                          │
│ - Build "Why this method?" panel, Prerequisites list, and Formula/Theorem cards.       │
│ - Tests: Vitest component unit tests and bilingual rendering tests.                    │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-05: INTERACTIVE GRAPH VISUALIZATIONS                                          │
│ - Build React static Knowledge Graph modal and Reactive Parameter DAG view.           │
│ - Connect 350ms debounce coefficient edits to dynamic node invalidation.               │
│ - Tests: Interactive state transition tests and zero math fabrication assertions.      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-06: REAL BROWSER E2E, OFFLINE AUDIT & FINAL S3 CLOSEOUT                       │
│ - Selenium Headless Chrome E2E suite covering all knowledge surfaces.                  │
│ - Full repository test gate execution (1343+ tests).                                   │
│ - Final S3 acceptance report and baseline freeze tagging.                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 22. Preflight GO / NO-GO Verdict

| Criterion | Evaluation Result | Evidence |
| :--- | :--- | :--- |
| **A. Stable Foreign Keys** | **PASS** | `MethodRegistry.list_all()` defines 9 frozen `MethodId`s matching mathematical engine. |
| **B. Knowledge / Solver Separation** | **PASS** | Strict architectural boundary: S3 enriches S1; S1 remains sole execution authority. |
| **C. Deterministic Offline Storage** | **PASS** | Repository-bundled static JSON files provide 100% offline, zero-database execution. |
| **D. DEV-02A Selective Adaptation** | **PASS** | DEV-02A evaluated as research input only; clean Pydantic v2 schemas defined. |
| **E. Two-Graph Distinction** | **PASS** | Knowledge Graph (static) and Reactive DAG (dynamic dataflow) formalized as distinct models. |

### Final Preflight Verdict: **`GO FOR S3 IMPLEMENTATION SEQUENCE`**

---

## 23. Scope & Immutability Verification

- [x] Backend mathematical engine files (`src/mke_product/domain/**`, `application/**`, `parser/**`) remain 100% UNTOUCHED.
- [x] Backend transport layer (`src/mke_product/transport/**`) remains 100% UNTOUCHED.
- [x] Frontend source code (`src/frontend/src/**`) remains 100% UNTOUCHED.
- [x] Test suite files (`tests/**`) remain 100% UNTOUCHED.
- [x] Root `pytest.ini` remains 100% UNTOUCHED.
- [x] Legacy canonical UI files (`src/mke_product/ui/ui00/**`) remain 100% UNTOUCHED.
- [x] Historical evidence namespaces (`evidence/p03b/**`) remain 100% UNTOUCHED and pristine.
- [x] Parked milestone B3 (`cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`) remains 100% UNTOUCHED.
- [x] Official baseline tag `mvp-v1-algebra-slice-accepted` points to `e620c96470514f8bd7563efba25427c7a4764488`.

---

## 24. Audit Conclusion & Handoff

Milestone **S3-P0** delivers a complete, rigorous, and verified preflight architectural blueprint for S3 Method Knowledge & Graph Surfaces.

**Formal Preflight Status:** `PENDING INDEPENDENT S3-P0 AUDIT`
