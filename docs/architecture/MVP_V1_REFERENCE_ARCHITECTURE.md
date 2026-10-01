# MKE MVP V1 — Reference Architecture & System Topology

- **Document Identifier:** `docs/architecture/MVP_V1_REFERENCE_ARCHITECTURE.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.0.0 (Technical Reference Architecture)
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/mvp-v1-product-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
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
│  • React / Next.js + TypeScript + Tailwind CSS                                                   │
│  • Math Renderer: KaTeX (SSR + Client Fast Math Display)                                        │
│  • Interactive Geometry Canvas: JSXGraph (Semantic Construction Binding)                         │
│  • Interactive Formula Input: MathLive / LaTeX Visual Editor                                     │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                  ▲  REST API / JSON / WebSocket Streams                          │
│                                  ▼                                                               │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  API & WORKSPACE ORCHESTRATION LAYER (FastAPI Backend)                                           │
│  • Problem Workspace Session Manager (Stateful In-Memory / SQLite Session Cache)                  │
│  • Dependency Recomputation Graph Engine (DAG Invalidation & Reactive Cascade)                   │
│  • Intake Validator & Multi-Modal Parser Dispatcher                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  DOMAIN LAYER: KNOWLEDGE, METHOD & TRACE ENGINES                                                 │
│  • Method Registry Engine (Predicate Evaluation, Method Catalog, Curriculum Metadata)            │
│  • Proof / Solution Trace Generator (Canonical Deduction Step Trees)                             │
│  • Vietnamese Pedagogical Renderer (Templates + Constrained AI Paraphrase)                       │
│  • Curriculum & Knowledge Graph (GDPT 2018 Ontology & Prerequisites)                             │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  EXECUTION & SOLVER ADAPTER LAYER (Isolated & Sandboxed)                                         │
│  • Native Pure-Python Exact Solver Kernel (Algebraic Simplification, Factoring, Surds)            │
│  • External CAS Adapter (SymPy Worker - Process Contained / Untrusted Candidate Generator)       │
│  • Synthetic Geometry Deduction Engine (Forward-Chaining Rule Inference)                         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  INDEPENDENT VERIFICATION & CERTIFICATE GATEWAY                                                  │
│  • Host Algebraic Verifier (Exact Rational Vieta, Polynomial Residuals, Domain Safety)           │
│  • Host Geometry Verifier (Synthetic Proof Step Validator + Coordinate Counterexample Check)     │
│  • Cryptographic / Structural Certificate Builder (Deterministic Proof Signatures)               │
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
       ├── 2. Verify algebraic identities over Q independently (Zero SymPy in proof loop)
       ├── 3. Evaluate polynomial residuals & Vieta relations
       └── 4. Check domain constraints & edge cases
       │
       ├─► [MATCH & VERIFIED] ──► Issue VerificationCertificate(status=VERIFIED)
       └─► [MISMATCH / CORRUPT] ──► Issue VerificationCertificate(status=VERIFICATION_FAILED)
```

### 2.2 Reusable Baseline Components vs. Frozen Historical Protocols

| Component | Repository Path | B1/B2 Status | MVP V1 Role & Reuse Strategy |
| :--- | :--- | :--- | :--- |
| **Exact Rational Arithmetic** | `src/mke_product/core/rational.py` | Active / Frozen | **Reused Core:** Authoritative rational arithmetic engine over $\mathbb{Q}$. |
| **AST Parser & Data Structures** | `src/mke_product/parser/` | Active / Frozen | **Reused Core:** Deterministic mathematical expression AST parser. |
| **MKE-IR Validator** | `src/mke_product/ai/` | Active / Frozen | **Reused Core:** Pre-dispatch intake syntax and provenance validator. |
| **Win32 Job Object Containment** | `src/mke_product/worker/controller.py` | Active / Frozen | **Reused Infrastructure:** Process memory, timeout, and handle isolation. |
| **B0/B1/B2 IPC Protocols** | `src/mke_product/protocol/` (`v1`, `v2`, `v3`) | Active / Frozen | **Historical Infrastructure:** Preserved for backward-compatible solver tests. |
| **B3 Complex Solver** | `product/p03c-p1c-04-b3-exact-complex-preflight` | Parked | **PARKED:** Intentionally suspended to prioritize MVP Product Engine. |

---

## 3. Geometry Architecture: Semantic Geometry vs. Visualization State

A critical flaw in naive geometry software is treating Cartesian coordinates as mathematical truth. MKE strictly bifurcates semantic geometry from rendering state:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GEOMETRY ARCHITECTURE BIFURCATION                                   │
├──────────────────────────────────────────────────┬───────────────────────────────────────────────┤
│ SEMANTIC GEOMETRY (Mathematical Truth)           │ VISUALIZATION STATE (Rendering Realization)   │
├──────────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • Primitives: Point, Line, Segment, Circle       │ • Viewport: Bounds [-10, 10, -10, 10], Zoom   │
│ • Defined Relations:                             │ • Cartesian Coordinates: (x, y) per Point     │
│   - Incidence: OnLine(P, L), OnCircle(P, C)      │ • Style: StrokeColor, FillColor, DashPattern  │
│   - Angle Relations: Perpendicular(L1, L2)       │ • Drag State: IsDraggable, DragConstraints    │
│   - Length Relations: EqualLength(AB, CD)        │ • Selection: HighlightedObjects, Tooltips     │
│ • Givens & Hypotheses (Theorem Assumptions)      │                                               │
│ • Goal Proposition (Theorem to prove)            │ Coordinate values are derived to satisfy      │
│ • Proof Trace DAG (Axioms & Inference Rules)     │ semantic constraints for on-screen display.   │
└──────────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

### 3.1 The Geometry Deduction Engine
- **Inference Strategy:** Forward-chaining rule-based synthetic deduction engine.
- **Rule Base:** Standard Euclidean geometry axioms (congruence criteria $c-c-c, c-g-c, g-c-g$, parallel lines, angle bisectors, medians).
- **Coordinate-Based Counterexample Guard:** When evaluating candidate geometric propositions, the engine checks whether the property holds numerically across random perturbations of non-degenerate coordinates before generating a synthetic proof search.

---

## 4. Multi-Modal Intake & AI / OCR Boundary

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

## 5. Vietnamese Pedagogical Renderer Architecture

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

## 6. Frontend Reference Architecture & UI State Engine

### 6.1 Recommended Single-PC Web Technology Stack
- **Frontend Framework:** Next.js (App Router) + React 19 + TypeScript.
- **Styling & Design System:** Tailwind CSS + Radix UI / Lucide Icons.
- **Math Display:** KaTeX (Instant, high-performance LaTeX rendering without layout shift).
- **Interactive Geometry Canvas:** JSXGraph (Lightweight, open-source dynamic geometry engine).
- **Interactive Math Input:** MathLive (Accessible, mobile-friendly virtual math keyboard).
- **Backend API:** FastAPI (Python 3.10+) with Uvicorn, AnyIO, and Pydantic v2.

### 6.2 Workspace State Engine & Reactive DAG
The web client maintains a unidirectional reactive state model synchronized via WebSocket / HTTP REST:

```
[Workspace UI State]
  ├── Problem Input State (Raw query, Active parameters)
  ├── Presentation Mode State (`Học nhanh`, `Học hiểu`, `So sánh`, `Khám phá`, `Giáo viên`)
  ├── Recomputed Solution Artifacts (Roots, Traces, Graph Data, Verification Badges)
  └── Geometry Canvas State (JSXGraph Board instance, Bound points)
```
