# MKE MVP V1 — Domain Models & IR Specifications

- **Document Identifier:** `docs/architecture/MVP_V1_DOMAIN_AND_IR_CONTRACTS.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.0.0 (Domain Schema & IR Contracts)
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/mvp-v1-product-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
- **Status:** `STATUS: PENDING INDEPENDENT MVP PREFLIGHT AUDIT`
- **Date:** 2026-10-01

---

## 1. Domain Object Model Overview

MKE domain entities are modeled as immutable, strictly validated data contracts (specified in Pydantic v2 / TypeScript). Every entity has clear provenance, verification status, and cache invalidation characteristics.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MKE DOMAIN OBJECT GRAPH                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                         ┌───────────────────────┐                                      │
│                         │       ProblemIR       │                                      │
│                         └───────────┬───────────┘                                      │
│                                     │                                                  │
│             ┌───────────────────────┴───────────────────────┐                          │
│             ▼                                               ▼                          │
│  ┌──────────────────────┐                       ┌──────────────────────┐               │
│  │   AlgebraProblemIR   │                       │  GeometryProblemIR   │               │
│  └──────────┬───────────┘                       └──────────┬───────────┘               │
│             │                                              │                           │
│             ▼                                              ▼                           │
│  ┌──────────────────────┐                       ┌──────────────────────┐               │
│  │   MethodRegistry     │                       │  ConstructionGraph   │               │
│  └──────────┬───────────┘                       └──────────┬───────────┘               │
│             │                                              │                           │
│             ▼                                              ▼                           │
│  ┌──────────────────────┐                       ┌──────────────────────┐               │
│  │    SolutionTrace     │                       │      ProofTrace      │               │
│  └──────────┬───────────┘                       └──────────┬───────────┘               │
│             │                                              │                           │
│             ▼                                              ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐               │
│  │                     VerificationCertificate                         │               │
│  └─────────────────────────────────────────────────────────────────────┘               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Domain Object Contracts

### 2.1 `ProblemIR` (Base Problem Representation)
- **Responsibility:** Top-level container representing an ingested mathematical problem.
- **Authoritative Fields:** `problem_id: str`, `raw_query: str`, `category: ProblemCategory`, `assumptions: List[Assumption]`, `created_at: datetime`.
- **Derived Fields:** `canonical_latex: str`, `normalized_signature: str`.
- **Provenance:** Populated by Intake Validator from user text, LaTeX, or OCR ingestion.
- **Invalidation Behavior:** Root of the dependency graph; modifying `ProblemIR` clears all cached downstream artifacts.

```python
class ProblemCategory(str, Enum):
    ALGEBRA_QUADRATIC = "ALGEBRA_QUADRATIC"
    ALGEBRA_LINEAR_SYSTEM = "ALGEBRA_LINEAR_SYSTEM"
    GEOMETRY_TRIANGLE = "GEOMETRY_TRIANGLE"
    UNSUPPORTED = "UNSUPPORTED"

class ProblemIR(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    problem_id: str = Field(..., description="Unique deterministic UUID/Hash")
    raw_query: str = Field(..., description="Original student text or formula string")
    category: ProblemCategory = Field(..., description="Classified mathematical category")
    assumptions: List[Assumption] = Field(default_factory=list, description="Declared domain conditions")
    raw_query_provenance: str = Field(default="USER_TEXT", description="Source modality: USER_TEXT, OCR, DEMO")
```

### 2.2 `AlgebraProblemIR` (Algebraic Specialization)
- **Responsibility:** Represents single-variable polynomial and quadratic equations.
- **Authoritative Fields:** `equation_ast: ASTNode`, `target_variable: str`, `coefficients: Dict[str, Rational]`.
- **Derived Fields:** `discriminant: Rational`, `degree: int`, `is_monic: bool`.

```python
class AlgebraProblemIR(ProblemIR):
    target_variable: str = Field(default="x", min_length=1, max_length=10)
    equation_string: str = Field(..., description="Normalized equation text e.g. x^2 - 5*x + 6 = 0")
    coefficients: Dict[str, RationalRoot] = Field(..., description="Map of powers to exact rational coefficients: {'2': a, '1': b, '0': c}")
```

### 2.3 `GeometryProblemIR` (Semantic Geometric Representation)
- **Responsibility:** Encapsulates semantic geometric entities, relationships, givens, and target theorem goals without Cartesian coordinate bias.
- **Authoritative Fields:** `primitives: List[GeometricPrimitive]`, `givens: List[GeometricRelation]`, `goals: List[GeometricRelation]`.

```python
class PrimitiveType(str, Enum):
    POINT = "POINT"
    LINE = "LINE"
    SEGMENT = "SEGMENT"
    CIRCLE = "CIRCLE"
    TRIANGLE = "TRIANGLE"

class GeometricPrimitive(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(..., description="Identifier e.g. 'A', 'B', 'C', 'M'")
    type: PrimitiveType
    parent_ids: List[str] = Field(default_factory=list, description="Constituent points e.g. ['A', 'B'] for segment AB")

class GeometricRelationType(str, Enum):
    EQUAL_LENGTH = "EQUAL_LENGTH"
    EQUAL_ANGLE = "EQUAL_ANGLE"
    PERPENDICULAR = "PERPENDICULAR"
    PARALLEL = "PARALLEL"
    MIDPOINT = "MIDPOINT"
    ISOSCELES_TRIANGLE = "ISOSCELES_TRIANGLE"
    RIGHT_TRIANGLE = "RIGHT_TRIANGLE"

class GeometricRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    relation_type: GeometricRelationType
    target_ids: List[str] = Field(..., description="Involved primitives e.g. ['AM', 'BC'] for Perpendicular(AM, BC)")
    parameters: Dict[str, str] = Field(default_factory=dict)

class GeometryProblemIR(ProblemIR):
    primitives: List[GeometricPrimitive]
    givens: List[GeometricRelation]
    goals: List[GeometricRelation]
```

### 2.4 `MethodDefinition` & `MethodApplicability`
- **Responsibility:** First-class registry objects defining solution techniques, preconditions, complexity metrics, and evaluation outcomes.

```python
class MethodApplicabilityStatus(str, Enum):
    MATHEMATICALLY_APPLICABLE = "MATHEMATICALLY_APPLICABLE"
    SUPPORTED_BY_MKE = "SUPPORTED_BY_MKE"
    PEDAGOGICALLY_RECOMMENDED = "PEDAGOGICALLY_RECOMMENDED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"

class MethodDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method_id: str = Field(..., description="Unique slug e.g. 'QUAD_FACTORIZATION_AC'")
    problem_family: ProblemCategory
    title_vi: str = Field(..., description="Vietnamese title e.g. 'Phân tích đa thức thành nhân tử'")
    description_vi: str
    curriculum_level: str = Field(..., description="GDPT 2018 grade reference e.g. 'Lớp 8, Lớp 9'")
    relative_complexity: int = Field(default=1, ge=1, le=5, description="1=Direct, 5=Advanced")
    prerequisite_ids: List[str] = Field(default_factory=list)

class MethodApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method_id: str
    status: MethodApplicabilityStatus
    is_applicable: bool
    rejection_reason_vi: Optional[str] = None
    pedagogical_priority: int = Field(default=1, description="Sort order in UI")
```

### 2.5 `SolutionTrace` & `SolutionStep` (Algebraic Deducibility)
- **Responsibility:** Represents verified, linear or branching step-by-step solution derivations.

```python
class SolutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    step_number: int = Field(..., ge=1)
    latex_expression: str = Field(..., description="Mathematical transformation")
    explanation_vi: str = Field(..., description="Pedagogical justification in Vietnamese")
    rule_or_theorem_used: Optional[str] = None
    why_this_step_vi: Optional[str] = Field(None, description="Detailed pedagogical 'Tại sao làm bước này?'")
    sub_steps: List[SolutionStep] = Field(default_factory=list)

class SolutionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method_id: str
    steps: List[SolutionStep]
    final_answer_latex: str
    is_complete: bool = True
```

### 2.6 `ProofTrace` & `ProofStep` (Geometric Deductive DAG)
- **Responsibility:** Represents deductive geometric proof steps backed by axiomatic inferences.

```python
class ProofStep(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    step_id: str
    statement_vi: str = Field(..., description="e.g. 'Xét tam giác ABM và tam giác ACM'")
    deduction_latex: str = Field(..., description="e.g. '\\Delta ABM = \\Delta ACM'")
    justification_rule: str = Field(..., description="e.g. 'Trường hợp cạnh - cạnh - cạnh (c-c-c)'")
    premise_step_ids: List[str] = Field(default_factory=list, description="IDs of earlier steps used as premises")

class ProofTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proof_method_id: str
    steps: List[ProofStep]
    qed_conclusion_vi: str
    is_valid_dag: bool = True
```

### 2.7 `VerificationCertificate` (Deterministic Proof Token)
- **Responsibility:** Independent, tamper-evident cryptographic and algebraic certificate of correctness.

```python
class VerificationOutcome(str, Enum):
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class VerificationCertificate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    certificate_id: str
    problem_hash: str
    outcome: VerificationOutcome
    verifier_name: str = Field(default="MKE_HOST_INDEPENDENT_VERIFIER_V1")
    verified_at_utc: datetime
    algebraic_identities_passed: List[str] = Field(default_factory=list)
    certificate_signature: str = Field(..., description="SHA-256 integrity digest")
```

---

## 3. Dependency & Recomputation Graph Engine

The MKE Dependency Engine manages the reactive invalidation cascade when problem parameters are edited in real time.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              RECOMPUTATION DAG CASCADE                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [Source Node: Raw Coefficients a, b, c] ──(Mutated: c := 7)                           │
│        │                                                                               │
│        ├──► Invalidate: [DiscriminantNode] (Δ = -3)                                    │
│        │          │                                                                    │
│        │          ├──► Invalidate: [RootClassificationNode] (NO_REAL_ROOT)              │
│        │          │          │                                                         │
│        │          │          ├──► Invalidate: [RootsValueNode] ([])                    │
│        │          │          └──► Invalidate: [VerificationCertificate] (Re-certified) │
│        │          │                                                                    │
│        │          └──► Invalidate: [MethodApplicabilityNodes]                          │
│        │                     ├── Factorization: NOT_APPLICABLE                         │
│        │                     └── GeneralFormula: APPLICABLE (No real root trace)       │
│        │                                                                               │
│        ├──► Invalidate: [SolutionTraces] (Re-generate Step DAGs)                       │
│        ├──► Invalidate: [ParabolaVisualizationState] (Shift vertex above Ox)           │
│        └──► Invalidate: [PedagogicalRendererCache] (Emit updated Vietnamese text)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
