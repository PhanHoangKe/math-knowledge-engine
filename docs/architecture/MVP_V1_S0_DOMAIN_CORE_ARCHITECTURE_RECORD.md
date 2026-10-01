# MKE MVP V1 — S0 Domain Core Architecture & Implementation Record

- **Document Identifier:** `docs/architecture/MVP_V1_S0_DOMAIN_CORE_ARCHITECTURE_RECORD.md`
- **Milestone:** MVP-V1-S0 (Contracts & Executable Domain Core)
- **Document Version:** 1.0.0
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Branch:** `product/mvp-v1-s0-domain-core`
- **Predecessor Baseline:** Accepted MVP Preflight Remediation (`66c2c45fef74bb665de3437bb500d9d4a5df40f2`)
- **Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (`product/p03c-p1c-04-b3-exact-complex-preflight`)
- **Status:** `PENDING INDEPENDENT S0 AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Summary

Milestone `MVP-V1-S0` establishes the typed, deterministic, pure-Python domain core for the Math Knowledge Engine (MKE) MVP V1. It implements the Single Source of Truth (SSOT) data models, exact rational and real quadratic-surd arithmetic kernel, orthogonal Method Assessment engine, Method Registry, Host Independent Verifier, reactive dependency DAG, and deterministic JSON Schema generation.

---

## 2. Implemented Module Boundaries

The domain core is implemented under `src/mke_product/domain/`:

```
src/mke_product/domain/
├── __init__.py         # Clean public exports for domain contracts and engines
├── models.py           # Pydantic v2 strict models (ProblemIR, QuadraticProblemIR, GeometryProblemIR, MethodAssessment)
├── exact.py            # Exact rational and real quadratic surd arithmetic & decomposition
├── registry.py         # MethodRegistry & orthogonal assessment evaluator
├── verifier.py         # HostIndependentVerifier & VerificationCertificate generator
├── dag.py              # Reactive DependencyGraph with cycle rejection and invalidation
├── identity.py         # Semantic problem identity & computation cache identity hashing
└── schema.py           # Deterministic JSON Schema exporter
```

---

## 3. Core Architectural Contracts

### 3.1 Python Single Source of Truth (SSOT)
- All domain entities are defined in `src/mke_product/domain/models.py` using **Pydantic v2** (`BaseModel`, `ConfigDict(extra="forbid", strict=True, frozen=True)`).
- Unknown or extra fields raise `ValidationError` to prevent silent distortion of mathematical semantics.
- Export pipeline: Pydantic v2 SSOT $\longrightarrow$ `export_mvp_v1_json_schema()` $\longrightarrow$ JSON Schema Draft 2020-12 $\longrightarrow$ future TypeScript client bindings.

### 3.2 Exact Arithmetic Boundary
- **Zero Floating Point Authority:** Float arithmetic is strictly prohibited as a mathematical authority for exact algebra.
- **Coefficient Domain:** $\mathbb{Q}$ (exact rational fractions $p/q$ with $q > 0, \gcd(|p|, q) = 1$).
- **Solution Domain:** $\mathbb{R}$ (real numbers).
- **Squarefree Kernel Extraction:** For $\Delta = p/q > 0$, decomposes $p \cdot q = k^2 \cdot d$ with squarefree $d \ge 1$ and rational factor $s = k/q \in \mathbb{Q}$, yielding $\sqrt{\Delta} = s\sqrt{d}$ in closed form.
- **Negative Discriminant ($\Delta < 0$):** Produces mathematically valid `NO_REAL_ROOTS` ($S = \emptyset$) in $\mathbb{R}$ without invoking complex solver (B3).

### 3.3 Equation Classification & Routing
- `a != 0` $\longrightarrow$ `QUADRATIC`
- `a == 0, b != 0` $\longrightarrow$ `LINEAR` (exact root $-c/b$)
- `a == 0, b == 0, c == 0` $\longrightarrow$ `IDENTITY` (infinitely many real solutions)
- `a == 0, b == 0, c != 0` $\longrightarrow$ `CONTRADICTION` (no solution)

### 3.4 Orthogonal Method Assessment Model
Method evaluation is decoupled across 5 independent dimensions:
1. `mathematical_applicability`: `APPLICABLE`, `NOT_APPLICABLE`, `UNKNOWN`
2. `support_status`: `SUPPORTED`, `UNSUPPORTED`
3. `execution_availability`: `AVAILABLE`, `UNAVAILABLE`
4. `pedagogical_recommendation`: `RECOMMENDED`, `NEUTRAL`, `DISCOURAGED`
5. `verification_capability`: `HOST_VERIFIABLE`, `UNVERIFIED`, `NOT_APPLICABLE`

### 3.5 Registered MVP Quadratic Methods
1. `QUAD_FORMULA_STANDARD` (Công thức nghiệm tổng quát)
2. `QUAD_FORMULA_REDUCED` (Công thức nghiệm thu gọn)
3. `QUAD_FACTORIZATION_Q` (Phân tích nhân tử trên $\mathbb{Q}$)
4. `QUAD_FACTORIZATION_R` (Phân tích nhân tử trên $\mathbb{R}$)
5. `QUAD_COMPLETE_SQUARE` (Biến đổi tách bình phương)
6. `QUAD_VIETE_SPECIAL_SUM` (Nhẩm nghiệm $a + b + c = 0$)
7. `QUAD_VIETE_SPECIAL_DIF` (Nhẩm nghiệm $a - b + c = 0$)
8. `QUAD_VIETE_SUM_PRODUCT` (Tìm hai số theo Tổng và Tích)
9. `QUAD_GRAPHICAL_ANALYSIS` (Khảo sát đồ thị Parabol — `verification_capability = NOT_APPLICABLE`)

### 3.6 Host Independent Verifier Gateway
- **Zero CAS/AI Authority:** Verification is performed independently on the host by checking:
  - Exact polynomial residuals ($f(r) == 0$).
  - Exact surd polynomial residuals in $\mathbb{Q}(\sqrt{d})$ ($P_{\text{const}} == 0 \land P_{\text{surd}} == 0$).
  - Viète relations ($r_1 + r_2 == -b/a \land r_1 r_2 == c/a$).
  - Derivative multiplicity ($f'(r) == 0$ when $\Delta == 0$).
  - Canonical sign stability identity ($4a(ax^2+bx+c) = (2ax+b)^2 - \Delta > 0$ when $\Delta < 0$).
- Issues tamper-evident `VerificationCertificate` with SHA-256 signature.

### 3.7 Dependency DAG & Invalidation
- Directed Acyclic Graph (`DependencyGraph`) with cycle rejection (`CycleDetectedError`).
- Invalidation cascade: invalidating any node (e.g. `coefficients`) invalidates all transitive downstream nodes in topological order while leaving independent branches unaffected.

### 3.8 Cryptographic Identities
- **Semantic Problem Identity:** SHA-256 over canonical mathematical truth inputs (excludes theme, mode, viewport, timestamps).
- **Engine Config Identity:** SHA-256 over engine, registry, and verifier versions.
- **Computation Cache Identity:** Composite SHA-256 key (`cache:<semantic_id>:<engine_id>`).

---

## 4. B2 Codebase Reuse Observations

| Component | Repository Path | Observed Coupling | Final Reuse Decision |
| :--- | :--- | :--- | :--- |
| **Exact `Rational`** | `src/mke_product/core/rational.py` | Zero external coupling, pure arithmetic | `REUSE_DIRECT` |
| **AST Parser & Data Structures** | `src/mke_product/parser/` | Mathematical expression AST | `REUSE_DIRECT` |
| **MKE-IR Validator** | `src/mke_product/ai/validator.py` | Intake syntax and AST checks | `REUSE_VIA_ADAPTER` |
| **Win32 Job Object Controller** | `src/mke_product/worker/controller.py` | Process isolation, Win32 handle management | `REUSE_VIA_ADAPTER` (Deferred to execution sandbox) |
| **Historical IPC Protocols** | `src/mke_product/protocol/` (`v1`, `v2`, `v3`) | Historical worker protocols | `REGRESSION_ONLY` (Preserved intact) |
| **Parked B3 Complex Solver** | `product/p03c-p1c-04-b3-exact-complex-preflight` | Complex quadratic solver preflight | `PARKED` (Untouched at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`) |

---

## 5. Explicit S0 Exclusions

- No web application scaffold, Next.js, React UI, or JSXGraph.
- No FastAPI REST endpoints.
- No SymPy / CAS worker integration.
- No OCR, image parsing, or LLM paraphrasing.
- No geometry prover implementation.
- No complex quadratic roots (B3).
