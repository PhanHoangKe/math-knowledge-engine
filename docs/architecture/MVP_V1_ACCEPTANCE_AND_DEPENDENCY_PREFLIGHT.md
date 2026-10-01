# MKE MVP V1 — Acceptance Benchmark & Dependency Audit Preflight

- **Document Identifier:** `docs/architecture/MVP_V1_ACCEPTANCE_AND_DEPENDENCY_PREFLIGHT.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.1.0 (Remediated Acceptance Plan & Dependency Audit)
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

## 1. Third-Party Dependency, License & Build-vs-Reuse Audit

Every candidate dependency has been researched against official repository metadata and license texts to evaluate legal, operational, and architectural suitability.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               THIRD-PARTY DEPENDENCY AUDIT MATRIX                                │
├───────────────────┬──────────────┬───────────────┬──────────────────────┬────────────────────────┤
│ Technology        │ Ecosystem    │ License       │ Official Source      │ Architectural Role     │
├───────────────────┼──────────────┼───────────────┼──────────────────────┼────────────────────────┤
│ **SymPy**         │ Python / CAS │ BSD 3-Clause  │ github.com/sympy     │ Untrusted CAS Adapter  │
│ **JSXGraph**      │ Browser JS   │ LGPLv3 / MIT  │ jsxgraph.uni-bayr... │ Dynamic Geometry Board │
│ **KaTeX**         │ Browser JS   │ MIT License   │ katex.org            │ Ultra-fast Math Display│
│ **MathLive**      │ Browser JS   │ MIT License   │ cortexjs.net/mathlive│ Visual Math LaTeX Input│
│ **FastAPI**       │ Python API   │ MIT License   │ fastapi.tiangolo.com │ Backend Web Framework  │
│ **Next.js / React**│ Frontend TS  │ MIT License   │ nextjs.org           │ Modular Web Client App │
│ **Tailwind CSS**  │ Styling      │ MIT License   │ tailwindcss.com      │ Responsive Design Sys  │
│ **GeoGebra**      │ Geometry     │ Non-Comm / Pro│ geogebra.org/license │ **REJECTED (Licensing)│
│ **SageMath**      │ Python / CAS │ GPLv3+        │ sagemath.org         │ **REJECTED (Footprint)│
└───────────────────┴──────────────┴───────────────┴──────────────────────┴────────────────────────┘
```

### 1.1 Detailed Dependency Evaluations

#### 1. SymPy (Recommended for Untrusted CAS Adapter)
- **Official Source:** [github.com/sympy/sympy](https://github.com/sympy/sympy)
- **License:** BSD 3-Clause (Permissive, commercial-friendly).
- **Role in MKE:** Backend untrusted candidate transformation engine (expansion, factorization, symbolic manipulation).
- **Build vs. Reuse:** **REUSE.** SymPy runs in an isolated worker process whose output is strictly verified by host rational proof checkers before inclusion in any trace.
- **Risk:** Zero algorithmic risk because output is NEVER authoritative without independent host proof.

#### 2. JSXGraph (Recommended for Dynamic Geometry Visualization)
- **Official Source:** [jsxgraph.uni-bayreuth.de](https://jsxgraph.uni-bayreuth.de) / [github.com/jsxgraph/jsxgraph](https://github.com/jsxgraph/jsxgraph)
- **License:** Dual-licensed under LGPLv3 and MIT License.
- **Role in MKE:** Renders interactive geometric constructions (triangles, special lines, vertices, points) and binds draggable coordinate events to the geometry engine.
- **Build vs. Reuse:** **REUSE.** Excellent performance, active maintenance, lightweight browser footprint, cleanly decoupled from theorem prover logic.

#### 3. GeoGebra (REJECTED for Core Engine)
- **License Evaluation:** GeoGebra's non-commercial license (CC-BY-NC-SA 3.0 with proprietary additions and trademark terms) prohibits commercial deployment and imposes restrictive redistribution constraints.
- **Decision:** **REJECTED.** MKE adopts JSXGraph for visualization and builds its own synthetic prover to maintain full open IP freedom.

#### 4. SageMath (REJECTED for MVP Monolith)
- **License & Footprint:** GPLv3+, multi-gigabyte distribution requiring complex container orchestration and heavy C/C++ dependencies.
- **Decision:** **REJECTED for MVP.** Pure-Python SymPy + native MKE rational kernel is vastly superior for single-PC local development.

---

## 2. Acceptance Benchmark & Gold Test Set

The acceptance of MKE MVP V1 is governed by a deterministic, reproducible Gold Test Benchmark covering core mathematical correctness, edge cases, and adversarial tamper-resistance.

### 2.1 Algebra Gold Benchmark (Quadratic Equation Workbench)

All equations have $a, b, c \in \mathbb{Q}$ and are evaluated in $\text{solution\_domain} = \mathbb{R}$.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 ALGEBRA GOLD ACCEPTANCE BENCHMARK                                │
├────┬────────────────────────┬─────────────────────┬────────────────────────┬─────────────────────┤
│ ID │ Equation / Scenario    │ Expected Roots (ℝ)  │ Applicable Methods     │ Key Verification    │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q1 │ x² - 5x + 6 = 0        │ x₁ = 2, x₂ = 3      │ Standard Δ (Δ=1),      │ Verified Complete   │
│    │ (Distinct Rational)    │ (Two real roots)    │ Factoring ℚ, Viète,    │ Viète: S=5, P=6     │
│    │                        │                     │ Completing Square      │ Residual Check = 0  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q2 │ x² - 2 = 0             │ x = ±√2             │ Standard Δ (Δ=8),      │ Verified Complete   │
│    │ (Exact Real Surd Roots)│ (Exact surds in ℝ)  │ Completing Square,     │ Host d=2 Certified  │
│    │                        │                     │ Factoring over ℝ       │ Factoring ℚ = N/A   │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q3 │ x² - 2x + 1 = 0        │ x₁ = x₂ = 1         │ Standard Δ (Δ=0),      │ Verified Complete   │
│    │ (Repeated Real Root)   │ (Kép / Multiplicity)│ Reduced Δ', Factoring, │ Parabola Tangent Ox │
│    │                        │                     │ Completing Square      │ Vertex at (1, 0)    │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q4 │ x² + 1 = 0             │ S = ∅               │ Standard Δ (Δ = -4 < 0)│ Verified Complete   │
│    │ (No Real Root in ℝ)    │ (NO_REAL_ROOT)      │ Completing Square      │ solution_type =     │
│    │                        │ (Valid ℝ result)    │ Parabola Above Ox      │ "NO_REAL_ROOT"      │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q5 │ 2x² - 4x + 2 = 0       │ x₁ = x₂ = 1         │ Reduced Δ' (Δ'=0),     │ Verified Complete   │
│    │ (Non-monic Repeated)   │ (Kép / Multiplicity)│ Standard Δ, Factoring  │ Leading a=2 Checked │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ Q6 │ -x² + 6x + 9 = 0       │ x = 3 ± 3√2         │ Standard Δ (Δ=72),     │ Verified Complete   │
│    │ (Negative a & Surds)   │ (Exact surds in ℝ)  │ Reduced Δ' (Δ'=18),    │ Parabola Opens Down │
│    │                        │                     │ Completing Square      │ Vertex I(3, 18)     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ D1 │ Degenerate Linear:     │ Rejected from       │ Reclassify to Linear   │ Intake Error        │
│    │ 0*x² + 2x - 4 = 0      │ QuadraticProblemIR  │ or Intake Error        │ `NOT_QUADRATIC_     │
│    │                        │ (a = 0, b ≠ 0)      │                        │  DEGENERATE_LINEAR` │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ D2 │ Degenerate Identity:   │ Rejected from       │ Degenerate Infinite    │ Intake Error        │
│    │ 0*x² + 0*x + 0 = 0     │ QuadraticProblemIR  │ Solution State         │ `DEGENERATE_IDENTITY│
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ D3 │ Degenerate Contradict: │ Rejected from       │ Degenerate No Solution │ Intake Error        │
│    │ 0*x² + 0*x + 1 = 0     │ QuadraticProblemIR  │ State                  │ `DEGENERATE_CONTRAD`│
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ M1 │ Parameter Mutation:    │ x = 2, 3 ──► S = ∅  │ Recomputes DAG:        │ Reactive Cache      │
│    │ x² - 5x + 6 → + 7 = 0  │ (Valid Transition)  │ Factoring_Q disabled   │ Invalidation Valid  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ T1 │ Adversarial Fake Root: │ Injected False Root │ Host Vieta & Residual  │ Proof Gateway       │
│    │ x² - 5x + 6 = 0, x=4   │ (Tampered Worker)   │ Identity Fails Closed  │ VERIFICATION_FAILED │
└────┴────────────────────────┴─────────────────────┴────────────────────────┴─────────────────────┘
```

### 2.2 Geometry Gold Benchmark (Triangle Geometry Workbench)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                GEOMETRY GOLD ACCEPTANCE BENCHMARK                                │
├────┬────────────────────────┬─────────────────────┬────────────────────────┬─────────────────────┤
│ ID │ Geometric Theorem      │ Semantic Givens     │ Verified Proof Goal    │ Visualization Check │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G1 │ Isosceles Median       │ NonDegenerateTriangle│ Perpendicular(AM, BC)  │ Dragging A preserves│
│    │ is Altitude            │ EqualLength(AB, AC) │ (Via ΔABM = ΔACM       │ AM ⊥ BC dynamically │
│    │                        │ Midpoint(M, BC)     │  RULE_CONGRUENCE_SSS)  │                     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G2 │ Midpoint Parallelism   │ NonDegenerateTriangle│ Parallel(MN, BC) &     │ Dragging B or C     │
│    │ (Đường trung bình)     │ Midpoint(M, AB)     │ Length(MN) = 0.5*BC    │ preserves MN // BC  │
│    │                        │ Midpoint(N, AC)     │ (RULE_MIDPOINT_THEOREM)│                     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G3 │ Isosceles Bisector is  │ NonDegenerateTriangle│ Perpendicular(AD, BC) &│ Dragging A preserves│
│    │ Median & Altitude      │ EqualLength(AB, AC) │ Midpoint(D, BC)        │ bisector alignment  │
│    │                        │ AngleBisector(AD, A)│ (RULE_CONGRUENCE_SAS)  │                     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G4 │ False Theorem Test     │ Scalene Triangle    │ Assert Equal(AB, AC)   │ Counterexample check│
│    │ (Rejection Guard)      │ (Random A, B, C)    │ (Injected False Claim) │ Emits REFUTED       │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G5 │ Degenerate Collinear   │ Point A, B, C       │ Collinear(A, B, C)     │ Canvas displays     │
│    │ (Degeneracy Guard)     │ on same Line L      │ (Tam giác suy biến)    │ DEGENERATE_STATE    │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G6 │ Adversarial Proof Step │ Valid Triangle      │ Injected invalid step  │ Host Proof Verifier │
│    │ Injection Attack       │ Isosceles Theorem   │ with mismatched premise│ Rejects Proof DAG   │
└────┴────────────────────────┴─────────────────────┴────────────────────────┴─────────────────────┘
```

---

## 3. Required Preflight Architectural Decisions (A through L)

| # | Topic | Recommendation | Detailed Rationale & Guardrail |
| :--- | :--- | :--- | :--- |
| **A** | **Exact Algebra V1 Cut Line** | **Quadratic Equations over $\mathbb{Q}$ ($ax^2+bx+c=0, a \neq 0$)** | Covers rational roots, repeated roots, real surd roots, and no-real-root states with 5 solution methods, Viète relations, and dynamic parabola graphing. |
| **B** | **Linear Systems Placement** | **MVP V1B (Scheduled immediately post-V1)** | Keeps V1 focused on proving the multi-domain knowledge engine across 1D Algebra and 2D Geometry without expanding solver surface. |
| **C** | **Exact Geometry V1 Cut Line** | **Triangle Geometry with 3 Special Lines & Congruence Deductions** | Non-degenerate triangles, medians, altitudes, angle bisectors, and canonical congruence rules ($c-c-c, c-g-c, g-c-g$). |
| **D** | **Circumcircle Placement** | **Deferred to MVP V1B** | Circle theorems, inscribed angles, and cyclic quadrilaterals will form a dedicated geometry expansion slice. |
| **E** | **Free Auxiliary Construction** | **Template-Guided in V1; Free in V2** | Free auxiliary-line construction creates an infinite proof search space; V1 supports canonical problem-guided auxiliary lines. |
| **F** | **SymPy Reuse Boundary** | **Untrusted Candidate Generator Only** | SymPy runs in isolated sandboxes; zero SymPy code in host independent verification gates. |
| **G** | **Geometry Visualization Engine** | **JSXGraph** | Dual-licensed (LGPLv3/MIT), lightweight, battle-tested, cleanly separable from semantic proof logic. Avoids GeoGebra licensing traps. |
| **H** | **Geometry Proof Verification** | **Synthetic Forward-Chaining Deduction Engine** | Axiomatic rule-based inference combined with coordinate-based counterexample check. Incomplete search yields `NO_PROOF_FOUND_WITHIN_SUPPORTED_SYSTEM`. |
| **I** | **Frontend / Backend Stack** | **Next.js + TypeScript + Tailwind + KaTeX / FastAPI (Python 3.10+)** | Single-PC developer-friendly modular monolith, blazing-fast local iterations, seamless web demo deployment. |
| **J** | **Reused vs. Frozen B2 Parts** | **Reused:** `Rational`, AST parser, Intake validator, Job Object controller.<br>**Frozen:** B0/B1/B2 IPC protocols. | Preserves all verified historical containment and arithmetic infrastructure. |
| **K** | **B3 Status** | **PARKED at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`** | Complex quadratic roots preflight is preserved on its branch and suspended to prioritize product engine completion. |
| **L** | **Implementation Milestone Sequence** | **S0 $\to$ S1 $\to$ S2 $\to$ S3 $\to$ S4 Sequence** | S0 (Contracts & Executable Domain Core) $\to$ S1 (Quadratic Backend Slice) $\to$ S2 (API & Renderer) $\to$ S3 (Frontend Workbench) $\to$ S4 (Geometry Slice). |

---

## 4. Implementation Milestone Breakdown

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MKE MVP V1 IMPLEMENTATION ROADMAP                                │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MVP-V1-S0: Contracts & Executable Domain Core                                                    │
│ • Define Pydantic v2 domain schemas (ProblemIR, QuadraticProblemIR, GeometryProblemIR)           │
│ • Implement Orthogonal MethodAssessment model & Method Registry catalog                          │
│ • Implement Pure-Python Exact Quadratic Primitives (over ℚ and ℝ)                                │
│ • Implement Reactive Dependency DAG Engine & Semantic Hash Invalidation                          │
│ • Build Golden Acceptance Test Fixtures (Algebra Q1–Q6, D1–D3; Geometry G1–G6)                   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MVP-V1-S1: Quadratic Backend Vertical Slice                                                      │
│ • Pure-Python Quadratic Solver (Standard formula, reduced formula, factoring ℚ/ℝ, square-comp)   │
│ • Untrusted SymPy Adapter (Process sandboxing, candidate generator)                              │
│ • Host Independent Algebraic Verifier & VerificationCertificate Builder                          │
│ • SolutionTrace generator with rule justifications                                               │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MVP-V1-S2: API & Vietnamese Pedagogical Renderer                                                 │
│ • FastAPI Workspace Session Endpoints (Create, Mutate, Recompute, FetchTrace)                    │
│ • Deterministic GDPT 2018 Vietnamese Renderer Templates                                          │
│ • 5 Presentation Modes implementation (Học nhanh, Học hiểu, So sánh, Khám phá, Giáo viên)        │
│ • OpenAPI / JSON Schema generation & automated TypeScript client bindings export                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MVP-V1-S3: Frontend Quadratic Workbench & Synchronized Parabola Graph                            │
│ • Next.js + React 19 Workspace Workbench UI                                                      │
│ • KaTeX math rendering + MathLive visual equation editor                                         │
│ • Interactive Parameter Sliders & dynamic recomputation trigger                                  │
│ • Synchronized Parabola Graph (vertex, roots, axes, tangent/lift state)                          │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MVP-V1-S4: Geometry Semantic, Construction & Proof Vertical Slice                                │
│ • GeometryProblemIR parser & semantic validator                                                  │
│ • Forward-chaining synthetic proof engine with numerical counterexample filter                   │
│ • JSXGraph interactive canvas with constraint-preserving drag handlers                           │
│ • ProofTrace DAG visualizer & step-by-step Vietnamese proof explanation                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Preflight Review Checklist & Status

- [x] Product contract defined with 19-point workspace anatomy and 5 learner presentation modes.
- [x] Orthogonal multi-dimensional `MethodAssessment` model defined.
- [x] Quadratic domain semantics explicitly defined ($\text{coeff} \in \mathbb{Q}, \text{roots} \in \mathbb{R}$, $\Delta < 0 \implies \text{NO\_REAL\_ROOT}$).
- [x] Precise distinction between rational factoring ($\Delta = s^2$) and real surd factoring.
- [x] Full Algebra gold acceptance matrix audited with Q1–Q6, degenerate cases D1–D3, and mutations.
- [x] Semantic geometry strictly decoupled from Cartesian rendering coordinates.
- [x] Soundness (100% within rule set) and Incompleteness (`NO_PROOF_FOUND`) policies defined.
- [x] Third-party dependency licenses audited with GeoGebra & SageMath rejected, SymPy & JSXGraph approved.
- [x] B2 assets classified into `REUSE_DIRECT`, `REUSE_VIA_ADAPTER`, `REGRESSION_ONLY`, and `DO_NOT_REUSE`.
- [x] Implementation roadmap sequenced starting with `MVP-V1-S0 — Contracts & Executable Domain Core`.

**STATUS:** `STATUS: PENDING INDEPENDENT MVP PREFLIGHT AUDIT`
