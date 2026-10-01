# MKE MVP V1 — S0 Domain Core Architecture & Implementation Record

- **Document Identifier:** `docs/architecture/MVP_V1_S0_DOMAIN_CORE_ARCHITECTURE_RECORD.md`
- **Milestone:** MVP-V1-S0-R2 (Contract Hardening & Domain Core Closeout)
- **Document Version:** 1.2.0
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Branch:** `product/mvp-v1-s0-r2-contract-hardening`
- **Parent SHA:** `ac5e749beced8ce07cfefd4cf5974cf558ee4f86`
- **Predecessor Baseline:** S0-R1 Remediation (`ac5e749beced8ce07cfefd4cf5974cf558ee4f86`)
- **Parked B3 Baseline:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (`product/p03c-p1c-04-b3-exact-complex-preflight`)
- **Status:** `PENDING INDEPENDENT S0-R2 AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Summary

Milestone `MVP-V1-S0-R2` finalizes the contract hardening and semantic verification of the Math Knowledge Engine (MKE) MVP V1 executable domain core. It hardens Pydantic model boundaries against self-contradictory states, canonicalizes exact rational value objects, cleanses the reduced quadratic formula from false prerequisites, aligns method registry execution availability with S0 milestone implementation reality, replaces unverified curriculum claims with neutral metadata, clarifies certificate integrity fingerprinting, and enforces deterministic assumption sorting in semantic problem identity hashing.

---

## 2. Implemented Module Boundaries

The domain core is implemented under `src/mke_product/domain/`:

```
src/mke_product/domain/
├── __init__.py         # Clean public exports for domain contracts and engines
├── models.py           # Pydantic v2 strict models with semantic mathematical invariant validators
├── exact.py            # Exact rational and real quadratic surd arithmetic & decomposition
├── registry.py         # MethodRegistry & truthful orthogonal capability evaluator
├── verifier.py         # HostIndependentVerifier & VerificationCertificate generator
├── dag.py              # Reactive DependencyGraph with cycle rejection and invalidation
├── identity.py         # Deterministic semantic problem & computation cache identity hashing
└── schema.py           # Deterministic JSON Schema exporter
```

---

## 3. Core Architectural Contracts & Semantic Invariants

### 3.1 Python Single Source of Truth (SSOT) & Model Invariant Enforcement
- All domain entities are defined in `src/mke_product/domain/models.py` using **Pydantic v2** (`BaseModel`, `ConfigDict(extra="forbid", strict=True, frozen=True)`).
- **`RationalFraction` Invariants:**
  - Enforces deterministic canonicalization: `denominator > 0`, `gcd(abs(numerator), denominator) == 1`.
  - Zero is canonicalized strictly to `0/1` (preventing dual representations like `0/7` vs `0/1` or `2/4` vs `1/2`).
  - Denominator zero is rejected with `ValidationError`.
- **`QuadraticProblemIR` Invariants:**
  - `a.numerator != 0` strictly enforced (leading coefficient cannot be zero).
  - `category == ProblemCategory.ALGEBRA_QUADRATIC` and `classification == EquationClassificationType.QUADRATIC`.
  - `coefficient_domain == "Q"` and `solution_domain == "R"` strictly required.
  - Caller cannot inject or forge inconsistent discriminant values: `discriminant` is validated against exact $b^2 - 4ac$ computation.
- **`DegenerateEquationIR` Invariants:**
  - `a.numerator == 0` strictly enforced.
  - For $b \neq 0$: classification must be `LINEAR` with `linear_root == -c/b`.
  - For $b = 0, c = 0$: classification must be `IDENTITY` with `linear_root is None`.
  - For $b = 0, c \neq 0$: classification must be `CONTRADICTION` with `linear_root is None`.

### 3.2 Exact Arithmetic Boundary
- **Zero Floating Point Authority:** Float arithmetic is strictly prohibited as a mathematical authority for exact algebra.
- **Coefficient Domain:** $\mathbb{Q}$ (exact rational fractions $p/q$ with $q > 0, \gcd(|p|, q) = 1$).
- **Solution Domain:** $\mathbb{R}$ (real numbers).
- **Squarefree Kernel Extraction:** For $\Delta = p/q > 0$, decomposes $p \cdot q = k^2 \cdot d$ with squarefree $d \ge 1$ and rational factor $s = k/q \in \mathbb{Q}$, yielding $\sqrt{\Delta} = s\sqrt{d}$ in closed form.
- **Negative Discriminant ($\Delta < 0$):** Produces mathematically valid `NO_REAL_ROOTS` ($S = \emptyset$) in $\mathbb{R}$ without invoking complex solver (B3).

### 3.3 Truthful Orthogonal Method Assessment Model
Method evaluation is decoupled across 5 independent dimensions:
1. `mathematical_applicability`: `APPLICABLE`, `NOT_APPLICABLE`, `UNKNOWN`
2. `support_status`: `SUPPORTED`, `UNSUPPORTED`
3. `execution_availability`: `AVAILABLE`, `UNAVAILABLE`
4. `pedagogical_recommendation`: `RECOMMENDED`, `NEUTRAL`, `DISCOURAGED`
5. `verification_capability`: `HOST_VERIFIABLE`, `UNVERIFIED`, `NOT_APPLICABLE`

#### Key Invariant: Coexistence of `APPLICABLE` and `UNAVAILABLE`
In S0 (domain core), mathematical applicability is assessed accurately regardless of whether a full execution trace engine is implemented in the current milestone:
- Methods with executable algebraic solvers in S0 (`QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`) report `execution_availability = AVAILABLE`.
- Methods whose full step-by-step trace engines are deferred to future milestones (`QUAD_FACTORIZATION_Q`, `QUAD_FACTORIZATION_R`, `QUAD_COMPLETE_SQUARE`, `QUAD_VIETE_SUM_PRODUCT`, `QUAD_GRAPHICAL_ANALYSIS`) report `support_status = SUPPORTED` (metadata & assessment supported) but `execution_availability = UNAVAILABLE`.

#### Reduced Quadratic Formula Prerequisite Correction:
- For `QUAD_FORMULA_REDUCED` ($x = \frac{-b' \pm \sqrt{\Delta'}}{a}$ where $b' = b/2, \Delta' = b'^2 - ac$):
  - **Mathematical Applicability:** Always `APPLICABLE` for all $a \neq 0$ (including odd integer $b$ and fractional $b$).
  - **Prerequisites:** Contains only `PREREQ_RADICALS`. False prerequisite `PREREQ_EVEN_COEFF` is removed.
  - **Pedagogical Recommendation:** `RECOMMENDED` if $b$ is an even integer ($b \in \mathbb{Z} \land b \equiv 0 \pmod 2$), else `NEUTRAL`.

### 3.4 Neutral Curriculum Metadata
All registered methods in `MethodRegistry` use the neutral curriculum reference tag:
`curriculum_level = "VIETNAM_SECONDARY_TO_BE_VERIFIED"`
preventing unverified grade/semester claims in the executable domain core prior to authoritative MoET mapping.

### 3.5 Host Independent Verifier & Integrity Fingerprint
- **Zero CAS/AI Authority:** Verification is performed independently on the host by checking:
  - Exact polynomial residuals ($f(r) == 0$).
  - Exact surd polynomial residuals in $\mathbb{Q}(\sqrt{d})$ ($P_{\text{const}} == 0 \land P_{\text{surd}} == 0$).
  - Viète relations ($r_1 + r_2 == -b/a \land r_1 r_2 == c/a$).
  - Derivative multiplicity ($f'(r) == 0$ when $\Delta == 0$).
  - Canonical sign stability identity ($4a(ax^2+bx+c) = (2ax+b)^2 - \Delta > 0$ when $\Delta < 0$).
- Issues tamper-evident `VerificationCertificate` with unkeyed SHA-256 `integrity_fingerprint` (reproducible digest computed over canonical certificate payload; content identifier, not a digital signature).

### 3.6 Deterministic Identity Hashing
- **Semantic Problem Identity:** Unkeyed SHA-256 over canonical mathematical truth inputs. Assumptions are deterministically sorted by `(symbol, domain)`, ensuring list order invariance while remaining sensitive to truth-affecting changes.
- **Engine Config Identity:** Unkeyed SHA-256 over engine, registry, and verifier versions.
- **Computation Cache Identity:** Composite key (`cache:<semantic_id>:<engine_id>`).

---

## 4. Historical Codebase Reuse Classification & Runtime Import Boundary

### 4.1 Component Reuse Classification Matrix

| Component | Repository Path | Observed Coupling & Constraints | Final Reuse Decision |
| :--- | :--- | :--- | :--- |
| **Exact `Rational`** | `src/mke_product/core/rational.py` | Pure $\mathbb{Q}$ arithmetic, zero external dependencies | `REUSE_DIRECT` |
| **AST Parser & Structures** | `src/mke_product/parser/` | Bounded P02A grammar (variable $x$, exponent $\le 2$, nesting $\le 16$); not generic AST | `REUSE_VIA_ADAPTER` |
| **MKE-IR AI Validator** | `src/mke_product/ai/validator.py` | Coupled to historical CAS parser contracts and `OperationType` | `REUSE_VIA_ADAPTER` |
| **Win32 Job Object Controller** | `src/mke_product/worker/controller.py` | Windows-specific process containment & handle lifecycle | `REUSE_VIA_ADAPTER` (Deferred to execution sandbox) |
| **Historical IPC Protocols** | `src/mke_product/protocol/` (`v1`, `v2`, `v3`) | Historical worker IPC protocol schemas | `REGRESSION_ONLY` (Preserved intact for test suite) |
| **Parked B3 Complex Solver** | `product/p03c-p1c-04-b3-exact-complex-preflight` | Complex quadratic solver preflight | `PARKED` (Untouched at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`) |

### 4.2 Runtime Import Isolation Evidence
The S0 domain core code under `src/mke_product/domain/` does **NOT** import or depend upon `src/mke_product/parser/`, `src/mke_product/ai/`, `src/mke_product/worker/`, or `src/mke_product/protocol/` at runtime.

Explicit import verification:
- `src/mke_product/domain/models.py`: imports `pydantic`, `enum`, `typing`, `mke_product.core.rational.Rational`
- `src/mke_product/domain/exact.py`: imports `math`, `typing`, `mke_product.core.rational.Rational`, `mke_product.domain.models`
- `src/mke_product/domain/registry.py`: imports `typing`, `mke_product.core.rational.Rational`, `mke_product.domain.models`
- `src/mke_product/domain/verifier.py`: imports `hashlib`, `json`, `typing`, `mke_product.core.rational.Rational`, `mke_product.domain.models`
- `src/mke_product/domain/dag.py`: imports `typing`, `collections`
- `src/mke_product/domain/identity.py`: imports `hashlib`, `json`, `typing`, `mke_product.domain.models`
- `src/mke_product/domain/schema.py`: imports `json`, `typing`, `pydantic`, `mke_product.domain.models`

Total external runtime domain imports: `pydantic` and `mke_product.core.rational.Rational`. Zero coupling to parser, AI, worker, or legacy protocols.

---

## 5. Explicit S0 Exclusions

- No web application scaffold, Next.js, React UI, or JSXGraph.
- No FastAPI REST endpoints.
- No SymPy / CAS worker integration in S0 domain core.
- No OCR, image parsing, or LLM paraphrasing.
- No geometry prover implementation.
- No complex quadratic roots (B3).
