# MKE MVP V1 — Domain Models & IR Specifications

- **Document Identifier:** `docs/architecture/MVP_V1_DOMAIN_AND_IR_CONTRACTS.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.1.0 (Remediated Domain Schema & IR Contracts)
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/mvp-v1-product-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
- **Parked B3 Baseline:** Parked on `product/p03c-p1c-04-b3-exact-complex-preflight` (`cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`)
- **Status:** `STATUS: PENDING INDEPENDENT MVP PREFLIGHT AUDIT`
- **Date:** 2026-10-01

---

## 1. Domain Object Model Overview

MKE domain entities are modeled as immutable, strictly validated data contracts (specified in Pydantic v2 as the Single Source of Truth). Every entity provides deterministic serialization for automated TypeScript code generation, tamper-evident verification tokens, and reactive cache invalidation keys.

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
│  │  QuadraticProblemIR  │                       │  GeometryProblemIR   │               │
│  └──────────┬───────────┘                       └──────────┬───────────┘               │
│             │                                              │                           │
│             ▼                                              ▼                           │
│  ┌──────────────────────┐                       ┌──────────────────────┐               │
│  │   MethodAssessment   │                       │  SyntheticDeduction  │               │
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
- **Responsibility:** Root polymorphic container representing an ingested mathematical problem.
- **Authoritative Fields:** `problem_id: str`, `raw_query: str`, `category: ProblemCategory`, `assumptions: List[Assumption]`, `created_at: datetime`.
- **Derived Fields:** `canonical_latex: str`, `semantic_revision_hash: str`.
- **Provenance:** Populated by Intake Validator from user text, LaTeX, or OCR ingestion.
- **Invalidation Behavior:** Root of the dependency DAG; modifying `ProblemIR` invalidates all cached downstream artifacts.

```python
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

class ProblemCategory(str, Enum):
    ALGEBRA_QUADRATIC = "ALGEBRA_QUADRATIC"
    ALGEBRA_LINEAR_SYSTEM = "ALGEBRA_LINEAR_SYSTEM"
    GEOMETRY_TRIANGLE = "GEOMETRY_TRIANGLE"
    UNSUPPORTED = "UNSUPPORTED"

class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    symbol: str
    domain: str = Field(default="REAL", description="Declared domain: REAL, POSITIVE_REAL, NON_ZERO")
    description_vi: Optional[str] = None

class ProblemIR(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    problem_id: str = Field(..., description="Deterministic UUID/Hash")
    raw_query: str = Field(..., description="Original student query string")
    category: ProblemCategory = Field(..., description="Classified problem category")
    assumptions: List[Assumption] = Field(default_factory=list)
    raw_query_provenance: str = Field(default="USER_TEXT", description="USER_TEXT, OCR, DEMO")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    semantic_revision_hash: str = Field(..., description="SHA-256 over semantic fields only")
```

---

### 2.2 `QuadraticProblemIR` (Quadratic Equation Specialization)
- **Responsibility:** Explicitly models univariate quadratic equations $ax^2 + bx + c = 0$.
- **Authoritative Fields:** `a: RationalFraction`, `b: RationalFraction`, `c: RationalFraction`, `target_variable: str`.
- **Domain Invariants:**
  - `coefficient_domain = "Q"` (Exact rationals $\mathbb{Q}$).
  - `solution_domain = "R"` (Real numbers $\mathbb{R}$).
  - $a \neq 0$ ($a = 0$ is rejected at intake with `NOT_QUADRATIC_DEGENERATE_LINEAR`).

```python
class RationalFraction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    numerator: int
    denominator: int = Field(default=1, gt=0)

class QuadraticDiscriminant(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: RationalFraction
    is_positive: bool
    is_zero: bool
    is_negative: bool
    is_rational_square: bool
    square_root_rational: Optional[RationalFraction] = None
    squarefree_kernel: Optional[int] = None
    extracted_factor: Optional[int] = None

class QuadraticProblemIR(ProblemIR):
    target_variable: str = Field(default="x", min_length=1, max_length=10)
    a: RationalFraction = Field(..., description="Leading coefficient a != 0")
    b: RationalFraction = Field(..., description="Linear coefficient b")
    c: RationalFraction = Field(..., description="Constant term c")
    equation_string: str = Field(..., description="Normalized string e.g. x^2 - 5*x + 6 = 0")
    discriminant: QuadraticDiscriminant
```

---

### 2.3 Orthogonal `MethodAssessment` Model

To eliminate ambiguities from flat status enums, MKE implements an orthogonal multi-dimensional method assessment:

```python
class MathematicalApplicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"

class SupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"

class ExecutionAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"

class PedagogicalRecommendation(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    NEUTRAL = "NEUTRAL"
    DISCOURAGED = "DISCOURAGED"

class VerificationCapability(str, Enum):
    HOST_VERIFIABLE = "HOST_VERIFIABLE"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class PrerequisiteStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    prerequisite_id: str
    is_satisfied: bool
    description_vi: str

class MethodAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method_id: str
    mathematical_applicability: MathematicalApplicability
    support_status: SupportStatus
    execution_availability: ExecutionAvailability
    pedagogical_recommendation: PedagogicalRecommendation
    verification_capability: VerificationCapability
    reasons: List[str] = Field(default_factory=list, description="Explanations for status or recommendation")
    prerequisite_status: List[PrerequisiteStatus] = Field(default_factory=list)
    pedagogical_priority: int = Field(default=1, description="Sort order in UI")
```

---

### 2.4 `SolutionTrace` & Root Models

```python
class SolutionRootType(str, Enum):
    RATIONAL = "RATIONAL"
    REAL_SURD = "REAL_SURD"
    NO_REAL_ROOT = "NO_REAL_ROOT"

class RealRootValue(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    root_type: SolutionRootType
    rational_value: Optional[RationalFraction] = None
    surd_base: Optional[RationalFraction] = None
    surd_factor: Optional[RationalFraction] = None
    radicand: Optional[int] = None
    approximate_float: Optional[float] = None
    latex_str: str

class SolutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    step_number: int = Field(..., ge=1)
    latex_expression: str
    explanation_vi: str
    rule_or_theorem_used: Optional[str] = None
    why_this_step_vi: Optional[str] = None
    sub_steps: List["SolutionStep"] = Field(default_factory=list)

class SolutionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    method_id: str
    solution_outcome: str = Field(..., description="TWO_DISTINCT_REAL_ROOTS, ONE_REPEATED_REAL_ROOT, NO_REAL_ROOT")
    roots: List[RealRootValue] = Field(default_factory=list)
    steps: List[SolutionStep]
    final_answer_latex: str
    is_complete: bool = True
```

---

### 2.5 `GeometryProblemIR` & Semantic Entities

```python
class PrimitiveType(str, Enum):
    POINT = "POINT"
    LINE = "LINE"
    SEGMENT = "SEGMENT"
    TRIANGLE = "TRIANGLE"

class GeometricPrimitive(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(..., description="e.g. 'A', 'B', 'C', 'M', 'BC', 'triangle_ABC'")
    type: PrimitiveType
    parent_ids: List[str] = Field(default_factory=list)

class GeometricPredicate(str, Enum):
    NON_DEGENERATE_TRIANGLE = "NON_DEGENERATE_TRIANGLE"
    EQUAL_LENGTH = "EQUAL_LENGTH"
    EQUAL_ANGLE = "EQUAL_ANGLE"
    PERPENDICULAR = "PERPENDICULAR"
    PARALLEL = "PARALLEL"
    MIDPOINT = "MIDPOINT"
    MEDIAN = "MEDIAN"
    ALTITUDE = "ALTITUDE"
    ANGLE_BISECTOR = "ANGLE_BISECTOR"
    PERPENDICULAR_BISECTOR = "PERPENDICULAR_BISECTOR"
    CONGRUENT_TRIANGLES = "CONGRUENT_TRIANGLES"

class GeometricRelation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    predicate: GeometricPredicate
    target_ids: List[str] = Field(..., description="Primitives referenced e.g. ['AM', 'BC']")
    parameters: Dict[str, str] = Field(default_factory=dict)

class GeometryProblemIR(ProblemIR):
    primitives: List[GeometricPrimitive]
    givens: List[GeometricRelation]
    goals: List[GeometricRelation]
```

---

### 2.6 `ProofTrace` (Geometric Deductive DAG)

```python
class ProofStep(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    step_id: str
    canonical_rule_id: str = Field(..., description="e.g. 'RULE_TRIANGLE_CONGRUENCE_SSS'")
    statement_vi: str = Field(..., description="Vietnamese statement e.g. 'Xét tam giác ABM và tam giác ACM'")
    deduction_latex: str = Field(..., description="\\Delta ABM = \\Delta ACM")
    premise_step_ids: List[str] = Field(default_factory=list)

class ProofOutcome(str, Enum):
    VERIFIED_PROOF = "VERIFIED_PROOF"
    NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM = "NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM"
    REFUTED_BY_COUNTEREXAMPLE = "REFUTED_BY_COUNTEREXAMPLE"
    INVALID_DEGENERATE_INPUT = "INVALID_DEGENERATE_INPUT"

class ProofTrace(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    proof_method_id: str
    outcome: ProofOutcome
    steps: List[ProofStep] = Field(default_factory=list)
    qed_conclusion_vi: Optional[str] = None
    is_valid_dag: bool = True
```

---

### 2.7 `VerificationCertificate` (Tamper-Evident Proof Token)

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
    verified_at_utc: datetime = Field(default_factory=datetime.utcnow)
    algebraic_identities_passed: List[str] = Field(default_factory=list)
    geometric_axioms_checked: List[str] = Field(default_factory=list)
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
│        │          └──► Invalidate: [MethodAssessmentNodes]                             │
│        │                     ├── Factorization_Q: NOT_APPLICABLE                       │
│        │                     └── GeneralFormula: APPLICABLE (No real root trace)       │
│        │                                                                               │
│        ├──► Invalidate: [SolutionTraces] (Re-generate Step DAGs)                       │
│        ├──► Invalidate: [ParabolaVisualizationState] (Shift vertex above Ox)           │
│        └──► Invalidate: [PedagogicalRendererCache] (Emit updated Vietnamese text)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
