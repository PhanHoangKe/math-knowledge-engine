# MKE MVP V1 — Reference Architecture & System Topology

- **Document Identifier:** `docs/architecture/MVP_V1_REFERENCE_ARCHITECTURE.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.1.0 (Remediated Technical Reference Architecture)
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

## 1. Architectural Principles & System Overview

MKE is designed as a **modular monolith** optimized for robust single-PC local development, reproducible academic evaluation, and frictionless deployment as an interactive web demo.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MKE SYSTEM TOPOLOGY (MODULAR MONOLITH)                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  PRESENTATION LAYER (Web Client)                                                                 │
│  • React 19 / Next.js (App Router) + TypeScript + Tailwind CSS                                   │
│  • Math Renderer: KaTeX (SSR + Client Fast Math Display, MIT)                                    │
│  • Interactive Geometry Canvas: JSXGraph (Semantic Construction Binding, LGPLv3 / MIT)            │
│  • Interactive Formula Input: MathLive (Accessible Math Keyboard, MIT)                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                  ▲  REST API / JSON / WebSocket Streams                          │
│                                  ▼  (Generated TypeScript Client from OpenAPI / JSON Schema)     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  API & WORKSPACE ORCHESTRATION LAYER (FastAPI Backend)                                           │
│  • Problem Workspace Session Manager (Stateful In-Memory / SQLite Session Cache)                  │
│  • Dependency Recomputation Graph Engine (DAG Invalidation & Semantic Hash Gating)               │
│  • Intake Validator & Multi-Modal Parser Dispatcher (Strict syntax & provenance checks)          │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  DOMAIN LAYER: KNOWLEDGE, METHOD & TRACE ENGINES (Canonical Python SSOT)                         │
│  • Method Registry Engine (Orthogonal Multi-Dimensional Applicability & GDPT 2018 Metadata)      │
│  • Proof / Solution Trace Generator (Canonical Deduction Step Trees)                             │
│  • Vietnamese Pedagogical Renderer (Deterministic GDPT 2018 Templates + Constrained AI)          │
│  • Curriculum & Knowledge Graph (MoET Secondary Mathematics Ontology & Prerequisites)            │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  EXECUTION & SOLVER ADAPTER LAYER (Isolated & Sandboxed)                                         │
│  • Native Pure-Python Exact Solver Kernel (Algebraic Simplification, Factoring, Real Surds)      │
│  • Untrusted CAS Adapter (SymPy Worker - Process Contained / Candidate Generator Only)           │
│  • Synthetic Geometry Deduction Engine (Forward-Chaining Rule Inference with Counterexample Gate)│
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  INDEPENDENT HOST VERIFICATION & CERTIFICATE GATEWAY                                             │
│  • Host Algebraic Verifier (Exact Rational Vieta, Polynomial Residuals, Domain Safety)           │
│  • Host Geometry Verifier (Synthetic Proof Step Axiom Validator + Coordinate Falsification)      │
│  • Cryptographic / Structural Certificate Builder (Deterministic SHA-256 Proof Signatures)       │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Solver & Verifier Strategy: Untrusted CAS Adapter Pattern

### 2.1 The Untrusted Adapter Invariant
Historically, CAS systems (such as SymPy, Mathematica, or Maxima) are complex codebases that may have subtle edge cases, branch-cut conventions, or uncertified simplifications. MKE strictly treats any external CAS as an **untrusted candidate generator**:

```
[Math Problem AST]
       │
       ▼
[SymPy CAS Adapter] ──(Sandboxed Execution)──► Returns Raw Candidate Solution (Roots / Factors)
       │
       ▼
[Host Verification Gateway]
       ├── 1. Parse into strict Rational / GeometryIR models
       ├── 2. Verify algebraic identities over ℚ independently (Zero SymPy in proof loop)
       ├── 3. Evaluate polynomial residuals & Viète relations
       └── 4. Check domain constraints & edge cases (e.g. a ≠ 0, discriminant sign)
       │
       ├─► [MATCH & VERIFIED] ──► Issue VerificationCertificate(outcome=VERIFIED_COMPLETE)
       └─► [MISMATCH / CORRUPT] ──► Issue VerificationCertificate(outcome=VERIFICATION_FAILED)
```

### 2.2 Reusable Baseline Components vs. Frozen Historical Protocols

MKE classifies prior codebase assets into four explicit reuse categories:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               HISTORICAL CODEBASE REUSE CLASSIFICATION                           │
├───────────────────┬──────────────────────────────────────────┬─────────────────┬─────────────────┤
│ Category          │ Component & File Path                    │ Origin Baseline │ Reuse Strategy  │
├───────────────────┼──────────────────────────────────────────┼─────────────────┼─────────────────┤
│ `REUSE_DIRECT`    │ Exact `Rational` arithmetic              │ B0/B1/B2 Core   │ Direct import   │
│                   │ `src/mke_product/core/rational.py`       │                 │ for exact math  │
│                   │ AST Parser & Data Structures             │ B0/B1 Core      │ Direct import   │
│                   │ `src/mke_product/parser/ast.py`, `parser`│                 │ for formula AST │
├───────────────────┼──────────────────────────────────────────┼─────────────────┼─────────────────┤
│ `REUSE_VIA_       │ Intake Validator                         │ B0/B1 Intake    │ Wrap behind API │
│  ADAPTER`         │ `src/mke_product/ai/validator.py`        │                 │ intake schema   │
│                   │ Win32 Job Object Controller              │ B0/B1 Worker    │ Wrap behind sand│
│                   │ `src/mke_product/worker/controller.py`   │                 │ box adapter     │
├───────────────────┼──────────────────────────────────────────┼─────────────────┼─────────────────┤
│ `REGRESSION_      │ B0/B1/B2 IPC Protocols (`v1`, `v2`, `v3`)│ B0/B1/B2 IPC    │ Preserved for   │
│  ONLY`            │ `src/mke_product/protocol/`              │                 │ historical test │
│                   │ Historical Worker Dispatch Tests         │ B0/B1/B2 Tests  │ suites; do not  │
│                   │ `tests/test_p03c_p1c_quadratic_surd_*.py`│                 │ alter           │
├───────────────────┼──────────────────────────────────────────┼─────────────────┼─────────────────┤
│ `DO_NOT_REUSE`    │ Monolithic CLI worker process model      │ B0 Worker CLI   │ Replace with Web│
│                   │ for general web API endpoints            │                 │ API orchestrator│
└───────────────────┴──────────────────────────────────────────┴─────────────────┴─────────────────┘
```

- **Parked B3 Baseline:** Complex quadratic roots preflight remains PARKED at commit `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` on branch `product/p03c-p1c-04-b3-exact-complex-preflight`. It is intentionally not merged into MVP V1.

---

## 3. Geometry Architecture: Semantic Geometry vs. Visualization State

A critical flaw in naive geometry software is treating Cartesian coordinates as mathematical truth. MKE strictly bifurcates semantic geometry from rendering state:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GEOMETRY ARCHITECTURE BIFURCATION                                   │
├──────────────────────────────────────────────────┬───────────────────────────────────────────────┤
│ SEMANTIC GEOMETRY (Mathematical Truth)           │ VISUALIZATION STATE (Rendering Realization)   │
├──────────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • Primitives: Point, Line, Segment, Triangle     │ • Viewport: Bounds [-10, 10, -10, 10], Zoom   │
│ • Defined Relations:                             │ • Cartesian Coordinates: (x, y) per Point     │
│   - Incidence: OnLine(P, L), OnSegment(P, AB)    │ • Style: StrokeColor, FillColor, DashPattern  │
│   - Angle Relations: Perpendicular(L1, L2)       │ • Drag State: IsDraggable, DragConstraints    │
│   - Length Relations: EqualLength(AB, CD)        │ • Selection: HighlightedObjects, Tooltips     │
│   - Midpoint / Median / Altitude / Bisector      │ • Degeneracy Warning: Collinear Alert Badge   │
│ • Givens & Hypotheses (Theorem Assumptions)      │                                               │
│ • Goal Proposition (Theorem to prove)            │ Coordinate values are derived to satisfy      │
│ • Proof Trace DAG (Axioms & Inference Rules)     │ semantic constraints for on-screen display.   │
└──────────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

### 3.1 The Geometry Deduction Engine: Soundness, Completeness & Counterexamples
- **Inference Strategy:** Forward-chaining rule-based synthetic deduction engine.
- **Rule Base:** Standard Euclidean geometry axioms (triangle congruence criteria $c-c-c, c-g-c, g-c-g$, parallel lines, angle bisectors, medians, altitudes).
- **Soundness Invariant:** Target 100% soundness within the bounded registered rule system. Every deduction step must reference a canonical rule ID and verified premises.
- **Completeness Policy:** Incomplete by design (finite rule depth). When the engine exhausts search depth without reaching the goal, it outputs `NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM` rather than asserting the conjecture is false.
- **Coordinate-Based Counterexample Guard:** When evaluating candidate geometric propositions, the engine tests whether the property holds numerically across random perturbations of non-degenerate coordinates. If a property fails numerically, it is discarded immediately as falsified. Numerical agreement is **NEVER treated as a proof certificate**.

---

## 4. Single Source of Truth (SSOT) & Schema Pipeline

To ensure perfect synchronization between backend logic, API contracts, and frontend TypeScript components:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CANONICAL SCHEMA PIPELINE                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
  [Python Pydantic v2 Domain Models] (SSOT)
        │
        ├──► FastAPI Backend (Validation & Serialization)
        │
        ├──► Export JSON Schema / OpenAPI Spec (`mke-openapi.json`)
        │         │
        │         ▼
        │    [openapi-typescript-codegen / typegen]
        │         │
        │         ▼
        └──► [TypeScript Interface Contracts] (`src/types/mke-domain.ts`)
                  │
                  ▼
             Next.js Frontend React Components
```

### 4.1 Workspace Revision Hash Invariant
- **Revision Hash Calculation:** The deterministic workspace hash $H_{\text{rev}} = \text{SHA256}(\text{canonical\_payload})$ is calculated **STRICTLY over semantic mathematical inputs** (normalized coefficients $a, b, c$, problem category, declared assumptions).
- **Excluded Display Fields:** User interface state, selected presentation mode (`Học nhanh` vs `Học hiểu`), zoom/pan coordinates, theme (light/dark), and local timestamps are **explicitly excluded** from the revision hash.

---

## 5. Multi-Modal Intake & AI / OCR Boundary

MKE is designed to ingest student queries across multiple modalities while maintaining deterministic safety:

```
[Raw Student Input] ──► (Text / LaTeX / Mobile Camera Image / PDF)
       │
       ▼
[Multimodal Ingestion Adapter (Untrusted)]
       ├── Math OCR Engine (e.g. Nougat / Pix2Text / Vision LLM)
       └── Language Understanding LLM (Vietnamese Math Prompt)
       │
       ▼
[Proposed Candidate MathIR] (Carries field-level provenance & confidence scores)
       │
       ▼
[MKE Intake Semantic Validator (Deterministic)]
       ├── Check 1: AST Well-formedness & Syntax Validity
       ├── Check 2: Variable & Expression Length Bounds
       ├── Check 3: Semantic Integrity (Provenance fidelity with raw input)
       └── Check 4: Confidence Gating
             ├─► [High Confidence & Valid] ──► Automatic Workspace Population
             └─► [Ambiguous / Low Confidence] ──► UI Confirmation Modal ("MKE hiểu đề như thế này đúng chưa?")
```

---

## 6. Vietnamese Pedagogical Renderer Architecture

The renderer translates structured, verified solution DAGs into elegant, textbook-standard Vietnamese mathematical prose conforming to GDPT 2018 guidelines.

```
[Verified Solution / Proof Trace DAG]
       │
       ▼
[Pedagogical Renderer Engine]
       ├── Step Formatter: Renders LaTeX equations, justifications, and intermediate conclusions
       ├── "Tại sao làm bước này?" Generator: Associates step with foundational rules & theorems
       ├── Presentation Mode Filter: Filters detail level (Học nhanh vs Học hiểu vs Giáo viên)
       └── Common Pitfall Annotator: Injects warnings for common student errors
       │
       ▼
[Optional Constrained AI Paraphrase]
       • Input: STRICTLY the verified step contents and justifications
       • Prompt Constraint: "Do not add new mathematical claims; paraphrase for student clarity only."
       • Fallback: Deterministic textbook template is ALWAYS available and primary.
```

---

## 7. Frontend Reference Architecture & UI State Engine

### 7.1 Recommended Single-PC Web Technology Stack
- **Frontend Framework:** Next.js (App Router) + React 19 + TypeScript.
- **Styling & Design System:** Tailwind CSS + Radix UI / Lucide Icons.
- **Math Display:** KaTeX (Instant, high-performance LaTeX rendering without layout shift).
- **Interactive Geometry Canvas:** JSXGraph (Dual-licensed LGPLv3/MIT, lightweight, dynamic geometry engine).
- **Interactive Math Input:** MathLive (Accessible, mobile-friendly virtual math keyboard, MIT).
- **Backend API:** FastAPI (Python 3.10+) with Uvicorn, AnyIO, and Pydantic v2.

### 7.2 Workspace State Engine & Reactive DAG
The web client maintains a unidirectional reactive state model synchronized via WebSocket / HTTP REST:

```
[Workspace UI State]
  ├── Problem Input State (Raw query, Active parameters)
  ├── Presentation Mode State (`Học nhanh`, `Học hiểu`, `So sánh`, `Khám phá`, `Giáo viên`)
  ├── Recomputed Solution Artifacts (Roots, Traces, Graph Data, Verification Badges)
  └── Geometry Canvas State (JSXGraph Board instance, Bound points, Constraint handlers)
```
