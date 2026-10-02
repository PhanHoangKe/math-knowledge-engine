# MKE PRODUCT — S3-P0-R2 FINAL SOURCE-TRUTH ALIGNMENT CLOSEOUT REPORT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-02  
**Target Milestone:** S3-P0-R2 Final Source-Truth Alignment Closeout  
**Branch:** `product/mvp-v1-s3-p0-method-knowledge-preflight`  
**Parent Baseline Commit:** `77de61d3f3498dc9c5b12719814ecd108017cf79` (Audited S3-P0-R1 Head)  
**Accepted Algebra Baseline:** `e620c96470514f8bd7563efba25427c7a4764488`  
**Baseline Acceptance Tag:** `mvp-v1-algebra-slice-accepted`  
**Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (100% Untouched)  
**Preflight Status:** `PENDING INDEPENDENT S3-P0-R2 FINAL AUDIT`

---

## 1. Executive Summary & Authorization Scope

This preflight document establishes the final reconciled architectural blueprint, schema models, repository inventory, graph models, and staged implementation roadmap for **Milestone S3: Method Knowledge & Graph Surfaces**.

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
1. **Why is this method applicable?** (Theoretical applicability conditions vs. specific problem invariants).
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
| **Production Safe** | `src/mke_product/domain/models.py` | `MethodDefinition`, `MethodAssessment`, `PrerequisiteStatus`, `DependencyNode` | **REUSE & EXTEND** (Strict Pydantic v2 foundation). |
| **Production Safe** | `src/mke_product/domain/registry.py` | `MethodRegistry` with 9 canonical string method IDs and orthogonal capability matrix | **AUTHORITY BASELINE** (Stable foreign keys). |
| **Production Safe** | `src/mke_product/domain/dag.py` | `DependencyGraph` (DAG engine, topological invalidation, cycle detection) | **REUSE AS REACTIVE DAG** (Preserve for parameter dependencies). |
| **Production Safe** | `src/mke_product/application/traces/*` | Structured solution step traces with `rule_or_theorem_used`, `why_this_step_vi` | **INTEGRATE** (Link step rules to S3 Theorem/Formula IDs). |
| **Research-Only** | `src/mke/g4p1/**` | Multi-CAS trust verification, Merkle batch manifests, relation judges | **RESEARCH ONLY** (Do not merge into S3 product). |
| **Research-Only** | Commit `753382a` (`src/mke/knowledge/*`) | Research models (`MethodTemplate`, `MethodInstance`, etc.), SQLite indexer, Dev01 adapter | **RESEARCH ONLY** (Extract schema ideas; do not import). |
| **Legacy / Inactive** | `src/mke_product/ui/ui00/**` | Legacy monolithic HTML UI | **LEAVE UNTOUCHED** (Frozen historical baseline). |
| **Historical Evidence**| `evidence/p03b/**` | Milestone evidence screenshots and logs | **IMMUTABLE** (Never touch or modify). |

---

## 4. DEV-02A Research Input Evaluation

Historical DEV-02A (`753382a023835dbdbe6b074ca6101a3292d3474c`) provided an initial research exploration of knowledge schemas.

### 4.1 Factual Schema Evaluation
DEV-02A used typed Pydantic research schemas (`MethodTemplate`, `MethodInstance`, `FamilyRecord`, `ProblemRecord`, `MethodAnnotation`, `TransferPairRecord`, `DatasetManifest`), but they were substantially more permissive than the production S3 target:
- Lacked `strict=True` and `extra="forbid"`.
- Relied heavily on untyped `Dict[str, Any]` and dynamic payload dictionaries.
- Used a research-oriented M1–M5 method taxonomy that is incompatible with the product's 9 canonical string `method_id` values.
- Not suitable as production Single Source of Truth (SSOT) without clean adaptation.

### 4.2 Concept Classification

| DEV-02A Concept | DEV-02A Implementation | S3 Product Classification | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Mathematical Concepts** | Freeform research dictionaries | `ADAPT` | Formalize into strict Pydantic v2 `ConceptKnowledge` models with symmetric bilingual fields. |
| **Prerequisite Links** | Ad-hoc string lists | `ADAPT` | Formalize as strictly validated typed edges with referential integrity. |
| **Method Taxonomy** | Methods M1–M5 | `REIMPLEMENT_CLEANLY` | Product baseline strictly uses the 9 canonical string method IDs (`QUAD_*`). |
| **Dev01 Adapter & Dispatcher** | Heuristic AST pattern matcher | `REJECT` | Violates S1 exact polynomial normalizer and orthogonal assessment engine. |
| **SQLite Indexer** | Dynamic SQLite database file | `REJECT` (for MVP S3) | Structured JSON files in Git provide superior determinism, auditability, zero-dependency deployment, and diffability. |
| **Transfer Near-Miss Pairs** | Heuristic pedagogical discrepancies | `RESEARCH_ONLY` | Keep in research track; do not introduce pedagogical approximations into S3 product. |

---

## 5. Current Product 9-Method Model Inventory & Assessment Truth

We strictly separate the **Static `MethodDefinition`** fields from the **Dynamic `MethodAssessment`** rules implemented in `src/mke_product/domain/registry.py`:

### 5.1 Static `MethodDefinition` Catalog (Invariant across all equations)

| Canonical `method_id` (`str`) | Vietnamese Title | Problem Family | Relative Complexity | Prerequisite IDs | Verification Capability |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `QUAD_FORMULA_STANDARD` | Công thức nghiệm tổng quát | `ALGEBRA_QUADRATIC` | 1 | `PREREQ_RADICALS`, `PREREQ_POLYNOMIAL_COEFF` | `HOST_VERIFIABLE` |
| `QUAD_FORMULA_REDUCED` | Công thức nghiệm thu gọn | `ALGEBRA_QUADRATIC` | 1 | `PREREQ_RADICALS` | `HOST_VERIFIABLE` |
| `QUAD_FACTORIZATION_Q` | Phân tích nhân tử trên $\mathbb{Q}$ | `ALGEBRA_QUADRATIC` | 2 | `PREREQ_FACTORING_ALGEBRA` | `HOST_VERIFIABLE` |
| `QUAD_FACTORIZATION_R` | Phân tích nhân tử trên $\mathbb{R}$ | `ALGEBRA_QUADRATIC` | 3 | `PREREQ_REAL_SURDS` | `HOST_VERIFIABLE` |
| `QUAD_COMPLETE_SQUARE` | Biến đổi tách bình phương | `ALGEBRA_QUADRATIC` | 3 | `PREREQ_PERFECT_SQUARE_IDENTITY` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SPECIAL_SUM` | Nhẩm nghiệm $a+b+c=0$ | `ALGEBRA_QUADRATIC` | 1 | `PREREQ_VIETE_THEOREM` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SPECIAL_DIF` | Nhẩm nghiệm $a-b+c=0$ | `ALGEBRA_QUADRATIC` | 1 | `PREREQ_VIETE_THEOREM` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SUM_PRODUCT` | Tìm hai số theo Tổng & Tích | `ALGEBRA_QUADRATIC` | 2 | `PREREQ_VIETE_THEOREM` | `HOST_VERIFIABLE` |
| `QUAD_GRAPHICAL_ANALYSIS` | Khảo sát đồ thị Parabol | `ALGEBRA_QUADRATIC` | 2 | `PREREQ_PARABOLA_GRAPH` | `NOT_APPLICABLE` |

### 5.2 Dynamic `MethodAssessment` Rules (Evaluated per equation instance on backend)

| Canonical `method_id` (`str`) | Mathematical Applicability Rule | Execution Availability | Dynamic Recommendation Rule | Pedagogical Priority Rule |
| :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORMULA_STANDARD` | **APPLICABLE** always ($a \neq 0$) | `AVAILABLE` | `RECOMMENDED` if not Vieta special; `NEUTRAL` if $a+b+c=0$ or $a-b+c=0$ | 1 (or 2 if Vieta special applies) |
| `QUAD_FORMULA_REDUCED` | **APPLICABLE** always ($a \neq 0, b \in \mathbb{Q}$) | `AVAILABLE` | `RECOMMENDED` if $b \in \mathbb{Z}$ and $b \pmod 2 == 0$; `NEUTRAL` otherwise | 1 if $b$ is even integer; 4 otherwise |
| `QUAD_FACTORIZATION_Q` | **APPLICABLE** if $\Delta$ is rational square ($\ge 0$); **NOT_APPLICABLE** otherwise | `UNAVAILABLE` | `RECOMMENDED` if applicable; `DISCOURAGED` otherwise | 1 if applicable and no Vieta special; 3 otherwise |
| `QUAD_FACTORIZATION_R` | **APPLICABLE** if $\Delta \ge 0$; **NOT_APPLICABLE** if $\Delta < 0$ | `UNAVAILABLE` | `RECOMMENDED` if $\Delta$ rational square; `NEUTRAL` if $\Delta > 0$ surd; `DISCOURAGED` if $\Delta < 0$ | 3 |
| `QUAD_COMPLETE_SQUARE` | **APPLICABLE** always ($a \neq 0$) | `UNAVAILABLE` | `NEUTRAL` always | 5 |
| `QUAD_VIETE_SPECIAL_SUM` | **APPLICABLE** if $a+b+c=0$; **NOT_APPLICABLE** if $a+b+c \neq 0$ | `AVAILABLE` | `RECOMMENDED` if $a+b+c=0$; `DISCOURAGED` if $a+b+c \neq 0$ | 1 if $a+b+c=0$; 9 otherwise |
| `QUAD_VIETE_SPECIAL_DIF` | **APPLICABLE** if $a-b+c=0$; **NOT_APPLICABLE** if $a-b+c \neq 0$ | `AVAILABLE` | `RECOMMENDED` if $a-b+c=0$; `DISCOURAGED` if $a-b+c \neq 0$ | 1 if $a-b+c=0$; 9 otherwise |
| `QUAD_VIETE_SUM_PRODUCT` | **APPLICABLE** if $\Delta$ is rational square; **NOT_APPLICABLE** otherwise | `UNAVAILABLE` | `RECOMMENDED` if applicable and $a=1$; `NEUTRAL` otherwise | 2 if applicable; 8 otherwise |
| `QUAD_GRAPHICAL_ANALYSIS` | **APPLICABLE** always ($a \neq 0$) | `UNAVAILABLE` | `RECOMMENDED` always | **6** |

---

## 6. Static Knowledge vs. Dynamic Assessment Separation

We freeze a strict boundary between static knowledge and dynamic runtime evaluation:

```text
┌─────────────────────────────────────────────────────────┐
│              STATIC METHOD KNOWLEDGE (S3)               │
│  - What is Completing the Square?                       │
│  - What prerequisite concepts does it have?             │
│  - Which formulas/theorems support it?                  │
│  - What are common learner mistakes & diagnostic tips?  │
│  - Invariant under coefficient edits (a, b, c)          │
└────────────────────────────┬────────────────────────────┘
                             │ Linked via method_id string foreign key
                             ▼
┌─────────────────────────────────────────────────────────┐
│             DYNAMIC PROBLEM ASSESSMENT (S1)             │
│  - Is method applicable to 2x^2 + 3x + 7 = 0? (YES)     │
│  - Is it executable in current build? (AVAILABLE)       │
│  - Dynamic recommendation: NEUTRAL (b=3 is odd)         │
│  - Exact discriminant Δ = -47 < 0 -> NO_REAL_ROOTS      │
│  - Recomputed on every 350ms coefficient edit           │
└─────────────────────────────────────────────────────────┘
```

### 6.1 Static vs. Dynamic Ownership Table

| Field / Capability | Authority Layer | Dynamic Reactivity | Storage / Origin | Type Contract |
| :--- | :--- | :--- | :--- | :--- |
| `method_id` | Shared Contract | Static FK | `MethodRegistry` | `str` |
| `title`, `summary`, `learning_objective` | S3 Static Knowledge | Static | `MethodKnowledge` JSON | `LocalizedText` |
| `formal_description`, `common_mistakes` | S3 Static Knowledge | Static | `MethodKnowledge` JSON | `LocalizedText` / `List[LocalizedText]` |
| `prerequisite_concept_ids`, `formula_refs` | S3 Static Knowledge | Static | `MethodKnowledge` JSON | `List[str]` |
| `mathematical_applicability` | **S1 Symbolic Engine** | **Dynamic (per equation)** | `MethodAssessment` (Runtime) | `MathematicalApplicability` |
| `execution_availability` | **S1 Domain Matrix** | Static / Build Feature | `MethodAssessment` (Runtime) | `ExecutionAvailability` |
| `pedagogical_recommendation` | **S1 Domain Registry** | **Dynamic (per equation)** | `MethodAssessment` (Runtime) | `PedagogicalRecommendation` |
| `reasons` (equation-specific) | **S1 Domain Registry** | **Dynamic (per equation)** | `MethodAssessment` (Runtime) | `List[str]` |
| `prerequisite_status.is_satisfied` | **S1 Domain Registry** | **Dynamic (per equation)** | `MethodAssessment` (Runtime) | `bool` |
| `pedagogical_priority` | **S1 Domain Registry** | **Dynamic (per equation)** | `MethodAssessment` (Runtime) | `int` |

---

## 7. Proposed Knowledge Entity Schemas

### 7.1 Shared Localized Text Value Object
```python
class LocalizedText(BaseModel):
    """Symmetric bilingual text container."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    vi: str = Field(..., description="Vietnamese text content")
    en: str = Field(..., description="English text content")
```

### 7.2 `MethodKnowledge` Schema
```python
class MethodKnowledge(BaseModel):
    """Static epistemological and pedagogical definition of a solution method."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str = Field(..., description="Foreign key matching canonical string method_id in MethodRegistry")
    title: LocalizedText
    summary: LocalizedText
    learning_objective: LocalizedText
    formal_description: LocalizedText
    applicability_guidance: List[LocalizedText] = Field(default_factory=list)
    non_applicability_guidance: List[LocalizedText] = Field(default_factory=list)
    prerequisite_concept_ids: List[str] = Field(default_factory=list)
    formula_refs: List[str] = Field(default_factory=list)
    theorem_refs: List[str] = Field(default_factory=list)
    common_mistakes: List[LocalizedText] = Field(default_factory=list)
    diagnostic_tips: List[LocalizedText] = Field(default_factory=list)
    related_method_ids: List[str] = Field(default_factory=list)
    curriculum_refs: List[CurriculumRef] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
```

### 7.3 `ConceptKnowledge` Schema
```python
class ConceptKnowledge(BaseModel):
    """Mathematical concept definition across algebra, geometry, and calculus."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    concept_id: str = Field(..., description="Unique snake_case concept ID, e.g. 'concept_discriminant'")
    title: LocalizedText
    definition: LocalizedText
    prerequisite_concept_ids: List[str] = Field(default_factory=list)
    related_concept_ids: List[str] = Field(default_factory=list)
    formula_refs: List[str] = Field(default_factory=list)
    method_refs: List[str] = Field(default_factory=list)
    curriculum_refs: List[CurriculumRef] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
```

### 7.4 `FormulaKnowledge` & `TheoremKnowledge` Schemas
```python
class FormulaKnowledge(BaseModel):
    """Canonical mathematical formula entity with exact LaTeX representation."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    formula_id: str = Field(..., description="e.g. 'FORMULA_QUADRATIC_STANDARD'")
    title: LocalizedText
    latex_template: str
    variables_description: Dict[str, LocalizedText]
    domain_conditions: LocalizedText
    related_concept_ids: List[str] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")


class TheoremKnowledge(BaseModel):
    """Mathematical theorem with formal premises and conclusions."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    theorem_id: str = Field(..., description="e.g. 'THEOREM_VIETA_RELATIONS'")
    title: LocalizedText
    statement: LocalizedText
    formal_statement_latex: str
    hypotheses: List[LocalizedText] = Field(default_factory=list)
    conclusions: List[LocalizedText] = Field(default_factory=list)
    related_concept_ids: List[str] = Field(default_factory=list)
    provenance_refs: List[str] = Field(default_factory=list)
    version: str = Field(default="1.0.0")
```

### 7.5 `CurriculumRef` Schema
```python
class CurriculumMappingStatus(str, Enum):
    VERIFIED_MAPPING = "VERIFIED_MAPPING"
    PROVISIONAL_MAPPING = "PROVISIONAL_MAPPING"


class CurriculumRef(BaseModel):
    """Authoritative curriculum standard reference."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    framework: str = Field(..., description="e.g. 'GDPT_2018', 'CCSS', 'IB'")
    subject: str = Field(..., description="e.g. 'TOAN'")
    grade_band: str = Field(..., description="e.g. 'GRADE_9'")
    topic: str = Field(..., description="e.g. 'PHUONG_TRINH_BAC_HAI_MOT_AN'")
    competency_ref: Optional[str] = Field(default=None, description="Explicit MoET standard code if verified")
    source_document: str = Field(..., description="Official circular / textbook title")
    source_locator: str = Field(..., description="Chapter / section locator")
    status: CurriculumMappingStatus = Field(..., description="Explicit mapping verification status")
```

### 7.6 Centralized `SourceProvenance` Registry Schema
```python
class ProvenanceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class SourceProvenance(BaseModel):
    """Traceable academic or curriculum citation in centralized registry."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source_id: str = Field(..., description="e.g. 'SRC_SGK_TOAN_9_TAP_2'")
    source_type: str = Field(..., description="TEXTBOOK, OFFICIAL_CURRICULUM, MONOGRAPH")
    title: str
    author_or_institution: str
    publication_year: Optional[int] = None
    locator: str = Field(..., description="Page, chapter, section, or circular article")
    verification_status: ProvenanceStatus = Field(..., description="Explicit verification status")
```

---

## 8. Graph Kinds, Cycle Policies & Symmetric Edge Serialization

### 8.1 Graph Kinds and Cycle Policies

| Graph Kind | Entities / Nodes | Edges Included | Cycle Policy | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`KNOWLEDGE_GRAPH`** | Concepts, Methods, Formulas, Theorems | All accepted edge types (`REQUIRES`, `USES_FORMULA`, `USES_THEOREM`, `ALTERNATIVE_TO`, `SPECIAL_CASE_OF`, `RELATED_TO`, `LEARN_BEFORE`) | **CYCLES PERMITTED** | Represents the rich associative network of pedagogical knowledge, including bidirectional relationships. |
| **`PREREQUISITE_DAG`** | Concepts | Subgraph of `REQUIRES` and `LEARN_BEFORE` edges only | **CYCLES STRICTLY FORBIDDEN** | Represents strict learning pathways; acyclicity enforced via DFS during knowledge bundle build. |
| **`REACTIVE_DEPENDENCY_DAG`** | Workspace parameters, $\Delta$, roots, traces, certificates | Computational dependency dataflow edges | **CYCLES STRICTLY FORBIDDEN** | Represents reactive computational evaluation pipeline for active problem instance. |

### 8.2 Symmetric Edge Serialization Rule
- For symmetric relations (`ALTERNATIVE_TO`, `RELATED_TO`):
  - In static JSON storage, store exactly **one canonical edge** ordered deterministically by stable node IDs (`source < target`) with flag `"is_symmetric": true`.
  - Do NOT store duplicate inverse edges (`A -> B` and `B -> A`) in the JSON files.
  - The API graph service and frontend graph loader expand symmetric edges bidirectionally at load time.
  - Eliminates redundant storage and artificial 2-cycles in the data source.

### 8.3 Graph Model Contracts
```python
class GraphNodeType(str, Enum):
    CONCEPT = "CONCEPT"
    METHOD = "METHOD"
    FORMULA = "FORMULA"
    THEOREM = "THEOREM"
    PARAMETER = "PARAMETER"
    COMPUTATION = "COMPUTATION"


class GraphEdgeType(str, Enum):
    REQUIRES = "REQUIRES"
    USES_FORMULA = "USES_FORMULA"
    USES_THEOREM = "USES_THEOREM"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    SPECIAL_CASE_OF = "SPECIAL_CASE_OF"
    RELATED_TO = "RELATED_TO"
    LEARN_BEFORE = "LEARN_BEFORE"
    COMPUTATIONAL_DEPENDENCY = "COMPUTATIONAL_DEPENDENCY"


class GraphKind(str, Enum):
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    PREREQUISITE_DAG = "PREREQUISITE_DAG"
    REACTIVE_DEPENDENCY_DAG = "REACTIVE_DEPENDENCY_DAG"


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    node_id: str
    node_type: GraphNodeType
    label: LocalizedText
    subtitle: Optional[LocalizedText] = None
    status: Optional[str] = None
    knowledge_ref: Optional[str] = None
    dependency_ref: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    source: str
    target: str
    relation_type: GraphEdgeType
    label: Optional[LocalizedText] = None
    is_directed: bool = True
    is_symmetric: bool = False


class GraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    graph_id: str
    graph_kind: GraphKind
    title: LocalizedText
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    is_acyclic: bool
    version: str = Field(default="1.0.0")
```

---

## 9. API Architecture & Stable Foreign Key Strategy

### 9.1 Foreign Key Alignment with Accepted S2 Baseline
- In the accepted S2 production contract (`POST /api/v1/algebra/solve`):
  - `SolvedResponse` and `AnalyzedNoExecutionResponse` expose `available_methods: List[MethodOptionView]`.
  - Each item in `available_methods` contains `method_id: str` (e.g. `"QUAD_FORMULA_STANDARD"`).
  - This existing `method_id` string serves as the **immutable primary foreign key** to static `MethodKnowledge.method_id`.
  - **Zero SolveResponse DTO mutation:** S3 does NOT add a redundant `knowledge_method_id` field to `SolveResponse`.

### 9.2 Exact 1:1 Foreign-Key Test Contract (for Stage S3-01)
- The S3-01 test suite will enforce exact set equality between the method IDs registered in backend `MethodRegistry` and the entities defined in static `methods.json`:
  ```python
  registry_method_ids = {m.method_id for m in MethodRegistry().list_all()}
  knowledge_method_ids = {m.method_id for m in load_method_knowledge()}

  assert len(registry_method_ids) == 9
  assert len(knowledge_method_ids) == 9
  assert knowledge_method_ids == registry_method_ids
  ```
  - Zero missing IDs.
  - Zero extraneous IDs.
  - Zero duplicate `MethodKnowledge.method_id` values.
  - No `MethodId` enum introduced in S1 or S3.

### 9.3 Proposed Read-Only Knowledge Endpoints (Targeted for S3-03)
1. `GET /api/v1/knowledge/methods/{method_id}`: Returns static `MethodKnowledge`.
2. `GET /api/v1/knowledge/concepts/{concept_id}`: Returns static `ConceptKnowledge`.
3. `GET /api/v1/knowledge/formulas/{formula_id}`: Returns static `FormulaKnowledge`.
4. `GET /api/v1/knowledge/theorems/{theorem_id}`: Returns static `TheoremKnowledge`.
5. `GET /api/v1/knowledge/graph`: Returns full `GraphModel` for client visualization.

*Note: S3-P0 defines the endpoint design; runtime implementation and dedicated structured error contracts will be authorized and executed in Stage S3-03.*

---

## 10. Deterministic JSON Storage & Unkeyed Content Hash

### 10.1 Structured JSON Canonical Storage
- Static knowledge entities are stored in **structured JSON files** under `src/mke_product/knowledge/data/`:
  - `methods.json`
  - `concepts.json`
  - `formulas.json`
  - `theorems.json`
  - `provenance.json`
- **Rationale:** Standard library parsing (`json`), zero third-party YAML dependencies, deterministic canonical formatting, 100% offline-first execution, and clean Git auditability.

### 10.2 Content Hash Semantics
- When computing a `content_hash` over knowledge bundles:
  - Canonical JSON string serialization with sorted keys (`json.dumps(obj, sort_keys=True, separators=(',', ':'))`).
  - Compute unkeyed SHA-256 digest.
  - **Strict Semantic Boundary:** The `content_hash` serves strictly as **deterministic unkeyed content identity and bundle integrity metadata** for client caching and tamper detection. It is NOT a cryptographic digital signature and NOT proof of mathematical truth.

---

## 11. Acceptance Dataset Design (9 Methods & 4 Canonical Equations)

### 11.1 Static Knowledge Fixture (All 9 Methods)
The acceptance dataset provides verified static metadata for all 9 registered methods with complete bilingual text, prerequisite concepts, formulas, and theorems:
1. `QUAD_FORMULA_STANDARD` $\to$ `FORMULA_QUADRATIC_STANDARD`, `concept_discriminant`, `concept_quadratic_equation`
2. `QUAD_FORMULA_REDUCED` $\to$ `FORMULA_QUADRATIC_REDUCED`, `concept_reduced_discriminant`
3. `QUAD_FACTORIZATION_Q` $\to$ `concept_factoring_rational`, `concept_rational_root`
4. `QUAD_FACTORIZATION_R` $\to$ `concept_factoring_real`, `concept_real_surd`
5. `QUAD_COMPLETE_SQUARE` $\to$ `FORMULA_PERFECT_SQUARE`, `concept_completing_square`
6. `QUAD_VIETE_SPECIAL_SUM` $\to$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_special_sum`
7. `QUAD_VIETE_SPECIAL_DIF` $\to$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_special_dif`
8. `QUAD_VIETE_SUM_PRODUCT` $\to$ `THEOREM_VIETA_RELATIONS`, `concept_vieta_sum_product`
9. `QUAD_GRAPHICAL_ANALYSIS` $\to$ `concept_parabola_vertex`, `concept_axis_symmetry`

### 11.2 Canonical Test Equations Matrix

| Equation | Mathematical Properties | S1 Dynamic Method Assessment Truth | Static Knowledge Verification |
| :--- | :--- | :--- | :--- |
| **$x^2 - 5x + 6 = 0$** | $\Delta = 1 > 0$, rational roots ($x_1=2, x_2=3$), $b=-5$ (odd). | `QUAD_FORMULA_STANDARD`: APPLICABLE, RECOMMENDED.<br>`QUAD_FORMULA_REDUCED`: **APPLICABLE**, **NEUTRAL** ($b$ is odd).<br>`QUAD_FACTORIZATION_Q`: APPLICABLE, RECOMMENDED.<br>`QUAD_VIETE_SPECIAL_SUM`: NOT_APPLICABLE, DISCOURAGED. | Verify `MethodKnowledge` for standard formula, Vieta relations, and factoring concepts. |
| **$x^2 + 2x + 1 = 0$** | $\Delta = 0$, double root ($x=-1$), $a-b+c=0$, $b=2$ (even). | `QUAD_FORMULA_STANDARD`: APPLICABLE, NEUTRAL (Vieta applies).<br>`QUAD_FORMULA_REDUCED`: APPLICABLE, RECOMMENDED ($b$ even).<br>`QUAD_VIETE_SPECIAL_DIF`: **APPLICABLE**, **RECOMMENDED** ($a-b+c=0$).<br>`QUAD_COMPLETE_SQUARE`: APPLICABLE, NEUTRAL. | Verify `TheoremKnowledge` for Vieta special difference and `FormulaKnowledge` for perfect square. |
| **$x^2 + 1 = 0$** | $\Delta = -4 < 0$, no real roots, $b=0$ (even). | `QUAD_FORMULA_STANDARD`: APPLICABLE, RECOMMENDED.<br>`QUAD_FACTORIZATION_Q`: **NOT_APPLICABLE**, DISCOURAGED.<br>`QUAD_FACTORIZATION_R`: **NOT_APPLICABLE**, DISCOURAGED.<br>`QUAD_GRAPHICAL_ANALYSIS`: APPLICABLE, RECOMMENDED. | Verify non-applicability guidance for negative discriminant in factoring concepts. |
| **$2x^2 + 3x + 7 = 0$** | $\Delta = -47 < 0$, no real roots, $b=3$ (odd integer). | `QUAD_FORMULA_STANDARD`: APPLICABLE, RECOMMENDED.<br>`QUAD_FORMULA_REDUCED`: **APPLICABLE**, **NEUTRAL** ($b=3$ is not even integer).<br>`QUAD_FACTORIZATION_Q`: NOT_APPLICABLE, DISCOURAGED. | **Crucial Invariant:** Reduced formula is mathematically **APPLICABLE**; odd $b$ results in **NEUTRAL** pedagogical recommendation (not non-applicability). |

---

## 12. Curriculum & Provenance Evidence Policy

### 12.1 S3-01 Initial Curriculum Policy
- For the initial S3-01 production acceptance dataset, **only independently verified curriculum mappings** with authoritative source and exact locator citations will be populated.
- If an official mapping is not yet verified for an entity, `curriculum_refs = []`.
- Zero manufactured competency codes permitted.
- `PROVISIONAL_MAPPING` records will not be added merely to make dataset fields look populated.

### 12.2 Provenance Granularity Policy
- Centralized `SourceProvenance` registry stored in `provenance.json`.
- Entities link to sources via `provenance_refs: List[str]`.
- Avoids duplicated full bibliographic text across individual concept and method records.

---

## 13. Integration Risk Matrix

| Risk ID | Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-01** | DEV-02A research schema mismatch contaminating production models. | **HIGH** | Strict boundary: zero code imported from DEV-02A; clean Pydantic v2 implementation. |
| **R-02** | Knowledge IDs drifting from product string `method_id`. | **HIGH** | Static CI test asserting exact 1:1 foreign key set equality between `MethodRegistry` and `MethodKnowledge`. |
| **R-03** | Conflating static Knowledge Graph with dynamic Parameter DAG. | **MEDIUM** | Distinct `GraphKind` taxonomy (`KNOWLEDGE_GRAPH` vs `REACTIVE_DEPENDENCY_DAG`) and separate UI views. |
| **R-04** | Large static knowledge payload bloating 350ms solve debounce. | **MEDIUM** | Option C Hybrid API architecture: solve returns existing `method_id`; static knowledge cached separately. |
| **R-05** | Circular prerequisite definitions in concept graph. | **MEDIUM** | Automated DFS cycle detection test executed on `PREREQUISITE_DAG` during bundle build. |
| **R-06** | Hardcoded Vietnamese-only content blocking bilingual parity. | **MEDIUM** | Strict model requirement for `LocalizedText` (symmetric `.vi` and `.en`) on all text fields. |
| **R-07** | Inaccurate or unverified curriculum mapping claims. | **LOW** | `CurriculumRef` requires explicit `status` and locator; defaults to empty list in S3-01 initial dataset. |
| **R-08** | Incompatibility with future geometry/calculus expansion. | **LOW** | Domain-neutral `ConceptKnowledge`, `FormulaKnowledge`, and `TheoremKnowledge` schemas. |

---

## 14. Proposed S3 Implementation Stages

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-01: KNOWLEDGE SCHEMAS & STATIC ACCEPTANCE DATASET                             │
│ - Implement Pydantic v2 schemas: LocalizedText, MethodKnowledge, ConceptKnowledge, etc.│
│ - Author verified JSON dataset for all 9 quadratic methods and core algebra concepts.  │
│ - Tests: Strict schema validation, symmetric bilingual tests, 1:1 FK set equality.     │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-02: IN-MEMORY KNOWLEDGE REPOSITORY & GRAPH SERVICE                            │
│ - Implement KnowledgeRepository with indexed lookups and topological DAG traversal.   │
│ - Implement GraphModel exporter for Knowledge Graph, Prerequisite DAG, and Reactive DAG│
│ - Tests: Lookup performance, DAG acyclicity validation, canonical edge serialization.  │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE S3-03: FASTAPI STATIC KNOWLEDGE API ENDPOINTS                                    │
│ - Implement GET /api/v1/knowledge/methods/{id}, concepts/{id}, formulas/{id}, etc.     │
│ - Configure HTTP caching headers (Cache-Control: public, max-age=3600).                │
│ - Tests: FastAPI TestClient integration tests and OpenAPI schema synchronization.      │
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

## 15. Preflight GO / NO-GO Verdict

| Criterion | Evaluation Result | Evidence |
| :--- | :--- | :--- |
| **A. Stable Foreign Keys** | **PASS** | `MethodRegistry.list_all()` exposes 9 canonical stable string method IDs suitable as S3 foreign keys. |
| **B. Knowledge / Solver Separation** | **PASS** | Strict architectural boundary: S3 enriches S1; S1 remains sole execution authority. |
| **C. Deterministic Offline Storage** | **PASS** | Repository-bundled structured JSON files provide 100% offline, zero-database execution. |
| **D. DEV-02A Selective Adaptation** | **PASS** | DEV-02A evaluated as research input only; clean Pydantic v2 schemas defined without importing research code. |
| **E. Two-Graph Distinction** | **PASS** | Knowledge Graph (associative, cycles allowed) and Reactive DAG / Prerequisite DAG (acyclic) formalized as distinct models. |

### Final Preflight Verdict: **`GO FOR S3 IMPLEMENTATION SEQUENCE`**

---

## 16. Scope & Immutability Verification

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

## 17. Audit Conclusion & Handoff

Milestone **S3-P0-R2** delivers the finalized, source-truth aligned, and verified preflight architectural blueprint for S3 Method Knowledge & Graph Surfaces.

**Formal Preflight Status:** `PENDING INDEPENDENT S3-P0-R2 FINAL AUDIT`
