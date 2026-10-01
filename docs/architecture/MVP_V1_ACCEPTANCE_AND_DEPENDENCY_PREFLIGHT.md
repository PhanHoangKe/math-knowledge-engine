# MKE MVP V1 — Acceptance Benchmark & Dependency Audit Preflight

- **Document Identifier:** `docs/architecture/MVP_V1_ACCEPTANCE_AND_DEPENDENCY_PREFLIGHT.md`
- **Milestone:** MKE MVP V1 (Math Knowledge Engine — Core Product Experience)
- **Document Version:** 1.0.0 (Acceptance Plan & Dependency Audit)
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/mvp-v1-product-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
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
│ **SageMath**      │ Python / CAS │ GPLv3+        │ sagemath.org         │ **REJECTED (Heavyweight│
└───────────────────┴──────────────┴───────────────┴──────────────────────┴────────────────────────┘
```

### 1.1 Detailed Dependency Evaluations

#### 1. SymPy (Recommended for Untrusted CAS Adapter)
- **Official Source:** [github.com/sympy/sympy](https://github.com/sympy/sympy)
- **Current License:** BSD 3-Clause (Permissive, commercial-friendly).
- **Role in MKE:** Backend untrusted candidate transformation engine (expansion, factorization, symbolic manipulation).
- **Build vs. Reuse:** **REUSE.** SymPy is mature and pure-Python. It will run in an isolated worker process whose output is verified by host rational proof checkers before inclusion in any trace.
- **Risk:** Zero algorithmic risk because output is NEVER authoritative without independent host proof.

#### 2. JSXGraph (Recommended for Dynamic Geometry Visualization)
- **Official Source:** [jsxgraph.uni-bayreuth.de](https://jsxgraph.uni-bayreuth.de) / [github.com/jsxgraph/jsxgraph](https://github.com/jsxgraph/jsxgraph)
- **Current License:** Dual-licensed LGPLv3 and MIT / Apache.
- **Role in MKE:** Renders interactive geometric constructions (triangles, special lines, vertices, points) and binds draggable coordinate events to the geometry engine.
- **Build vs. Reuse:** **REUSE.** Excellent performance, active maintenance, lightweight browser footprint, cleanly decoupled from theorem prover logic.

#### 3. GeoGebra (REJECTED for Core Engine)
- **License Evaluation:** GeoGebra's non-commercial license (CC-BY-NC-SA 3.0 with strict proprietary additions) prohibits commercial deployment and imposes restrictive redistribution constraints.
- **Decision:** **REJECTED.** MKE adopts JSXGraph for visualization and builds its own synthetic prover to maintain full open IP freedom.

#### 4. SageMath (REJECTED for MVP Monolith)
- **License & Footprint:** GPLv3+, multi-gigabyte distribution requiring complex container orchestration.
- **Decision:** **REJECTED for MVP.** Pure-Python SymPy + native MKE rational kernel is vastly superior for single-PC local development.

---

## 2. Acceptance Benchmark & Gold Test Set

The acceptance of MKE MVP V1 is governed by a deterministic, reproducible Gold Test Benchmark covering core mathematical correctness, edge cases, and adversarial tamper-resistance.

### 2.1 Algebra Gold Benchmark (Quadratic Equation Workbench)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 ALGEBRA GOLD ACCEPTANCE BENCHMARK                                │
├────┬────────────────────────┬─────────────────────┬────────────────────────┬─────────────────────┤
│ ID │ Equation / Scenario    │ Expected Roots (R)  │ Applicable Methods     │ Key Verification    │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A1 │ x² - 5x + 6 = 0        │ x₁ = 2, x₂ = 3      │ Standard Δ, Factoring, │ Verified Complete   │
│    │ (Distinct Rational)    │ (Two real roots)    │ Viète, Parabola Cut    │ Viète: S=5, P=6     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A2 │ x² - 6x + 9 = 0        │ x₁ = x₂ = 3         │ Standard Δ (Δ=0),      │ Verified Complete   │
│    │ (Repeated Real Root)   │ (Kép / Multiplicity)│ Perfect Square, Viète  │ Vertex touches Ox   │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A3 │ x² - 2 = 0             │ x = ±√2             │ Standard Δ, Squarefree │ Verified Complete   │
│    │ (Irrational Surd Root) │ (Exact surds)       │ Surd, Parabola Cut     │ Host d=2 Certified  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A4 │ x² + 1 = 0             │ S = ∅               │ Standard Δ (Δ = -4 < 0)│ Verified Complete   │
│    │ (No Real Root)         │ (NO_REAL_ROOT)      │ Parabola Above Ox      │ solution_type=      │
│    │                        │                     │                        │ "NO_REAL_ROOT"      │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A5 │ 2x² + 5x + 3 = 0       │ x₁ = -1, x₂ = -3/2  │ Special a - b + c = 0, │ Verified Complete   │
│    │ (Non-monic a ≠ 1)      │ (Rational fractions)│ Factoring ac, Standard │ Viète Special Test  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A6 │ Parameter Mutation:    │ x = 2, 3 ──► S = ∅  │ Recomputes DAG:        │ Reactive Cache      │
│    │ x² - 5x + 6 → + 7 = 0  │ (Valid Transition)  │ Factoring disabled     │ Invalidation Valid  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A7 │ Degenerate a = 0:      │ Rejected Pre-intake │ Intake Error Emitted   │ Fail-Closed Guard   │
│    │ 0*x² + 2x + 1 = 0      │ (Degree != 2)       │ REJECTED_SYNTAX        │ Zero worker spawned │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ A8 │ Adversarial Fake Root: │ Injected False Root │ Host Vieta & Residual  │ Proof Gateway       │
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
│ G1 │ Isosceles Median       │ Triangle(A, B, C)   │ Perpendicular(AM, BC)  │ Dragging A preserves│
│    │ is Altitude            │ EqualLength(AB, AC) │ (Via ΔABM = ΔACM c-c-c)│ AM ⊥ BC dynamically │
│    │                        │ Midpoint(M, BC)     │                        │                     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G2 │ Midpoint Parallelism   │ Triangle(A, B, C)   │ Parallel(MN, BC) &     │ Dragging B or C     │
│    │ (Đường trung bình)     │ Midpoint(M, AB)     │ Length(MN) = 0.5*BC    │ preserves MN // BC  │
│    │                        │ Midpoint(N, AC)     │ (Midpoint Theorem)     │                     │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G3 │ False Theorem Test     │ Scalene Triangle    │ Assert Equal(AB, AC)   │ Synthetic Prover    │
│    │ (Rejection Guard)      │ (Random A, B, C)    │ (Injected False Claim) │ Emits REFUTED       │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G4 │ Degenerate Collinear   │ Point A, B, C       │ Collinear(A, B, C)     │ Canvas displays     │
│    │ (Degeneracy Guard)     │ on same Line L      │ (Tam giác suy biến)    │ DEGENERATE_WARNING  │
├────┼────────────────────────┼─────────────────────┼────────────────────────┼─────────────────────┤
│ G5 │ Adversarial Proof Step │ Valid Triangle      │ Injected invalid step  │ Host Proof Verifier │
│    │ Injection Attack       │ Isosceles Theorem   │ with mismatched premise│ Rejects Proof DAG   │
└────┴────────────────────────┴─────────────────────┴────────────────────────┴─────────────────────┘
```

---

## 3. Required Preflight Architectural Decisions (A through L)

| # | Topic | Recommendation | Detailed Rationale & Guardrail |
| :--- | :--- | :--- | :--- |
| **A** | **Exact Algebra V1 Cut Line** | **Quadratic Equations over $\mathbb{Q}$ ($ax^2+bx+c=0, a \neq 0$)** | Covers rational roots, repeated roots, real surd roots, and no-real-root states with 4 solution methods, Viète relations, and dynamic parabola graphing. |
| **B** | **Linear Systems Placement** | **MVP V1B (Scheduled immediately post-V1)** | Keeps V1 focused on proving the multi-domain knowledge engine across 1D Algebra and 2D Geometry without expanding solver surface. |
| **C** | **Exact Geometry V1 Cut Line** | **Triangle Geometry with 3 Special Lines & Congruence Deductions** | Triangle properties, medians, altitudes, angle bisectors, and congruence criteria ($c-c-c, c-g-c, g-c-g$). |
| **D** | **Circumcircle Placement** | **Deferred to MVP V1B** | Circle theorems, inscribed angles, and cyclic quadrilaterals will form a dedicated geometry expansion slice. |
| **E** | **Free Auxiliary Construction** | **Template-Guided in V1; Free in V2** | Free auxiliary-line construction creates an infinite proof search space; V1 supports canonical problem-guided auxiliary lines. |
| **F** | **SymPy Reuse Boundary** | **Untrusted Candidate Generator Only** | SymPy runs in isolated sandboxes; zero SymPy code in host independent verification gates. |
| **G** | **Geometry Visualization Engine** | **JSXGraph** | Open-source (LGPLv3/MIT), lightweight, battle-tested, cleanly separable from semantic proof logic. Avoids GeoGebra licensing traps. |
| **H** | **Geometry Proof Verification** | **Synthetic Forward-Chaining Deduction Engine** | Axiomatic rule-based inference combined with coordinate-based counterexample check. |
| **I** | **Frontend / Backend Stack** | **Next.js + TypeScript + Tailwind + KaTeX / FastAPI (Python 3.10+)** | Single-PC developer-friendly modular monolith, blazing-fast local iterations, seamless web demo deployment. |
| **J** | **Reused vs. Frozen B2 Parts** | **Reused:** `Rational`, AST parser, Intake validator, Job Object controller.<br>**Frozen:** B0/B1/B2 IPC protocols. | Preserves all verified historical containment and arithmetic infrastructure. |
| **K** | **B3 Status** | **PARKED at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`** | Complex quadratic roots preflight is preserved on its branch and suspended to prioritize product engine completion. |
| **L** | **First Implementation Milestone** | **`MVP-V1-S1`: Core Domain & Knowledge Scaffold** | Scaffolds unified FastAPI / Next.js monolith, registers Quadratic ProblemIR and Method Registry, implements reactive dependency engine. |

---

## 4. Preflight Review Checklist & Status

- [x] Product contract defined with 19-point workspace anatomy and 5 learner presentation modes.
- [x] Pedagogical distinction established for Viète theorem vs. root-finding methods.
- [x] Factorization confirmed for non-monic $a \neq 1$ cases.
- [x] Semantic geometry strictly decoupled from Cartesian rendering coordinates.
- [x] Third-party dependency licenses audited with GeoGebra rejected and SymPy / JSXGraph accepted.
- [x] Concrete acceptance benchmarks established for both Algebra and Geometry.
- [x] All 12 required architectural decisions (A through L) explicitly documented.

**STATUS:** `STATUS: PENDING INDEPENDENT MVP PREFLIGHT AUDIT`
