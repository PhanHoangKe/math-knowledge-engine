# MKE Product 03C-P1C-04-B3 Preflight: Exact Quadratic Complex Roots Architecture

- **Milestone:** MKE Product 03C-P1C-04-B3
- **Document Version:** 1.0.0 (B3 Technical Preflight Specification)
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/p03c-p1c-04-b3-exact-complex-preflight`
- **Predecessor Baseline:** P1C-04-B2 Accepted / Closed (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
- **Status:** PREFLIGHT SPECIFICATION — PENDING AUDITOR GO/NO-GO REVIEW
- **Date:** 2026-10-01

---

## 1. Executive Summary & Recommendation

### 1.1 Recommendation: GO BOUNDED
We recommend **GO BOUNDED** for the implementation of milestone **PRODUCT-03C-P1C-04-B3** under the following mathematical, architectural, and security invariants:

1. **Exact Symbolic Complex Representation:** Exact quadratic complex roots are represented in the field $\mathbb{Q}(i\sqrt{d})$ as $a \pm c \cdot i\sqrt{d}$, where $a \in \mathbb{Q}$ is the exact rational real part, $c \in \mathbb{Q}^+$ is the exact positive rational imaginary magnitude, and $d \in \mathbb{Z}^+$ is a certified squarefree integer ($d = 1$ for purely rational imaginary roots, $2 \le d < 2^{32}$ for imaginary surd roots).
2. **Zero Floating-Point & Zero Native Python `complex`:** All solving, reduction, protocol serialization, and independent host verification are performed exclusively using exact integer and rational arithmetic (`Rational`). No floating-point approximations, `complex` primitives, or third-party CAS engines (e.g., SymPy) are permitted anywhere in the pipeline.
3. **Dedicated Protocol Version `mke.p02a.v4`:** To preserve the frozen contracts of `mke.p02a.v1` (affine / B0), `mke.p02a.v2` (rational quadratic / B1), and `mke.p02a.v3` (quadratic surd / B2), complex solving is introduced via dedicated schema `mke.p02a.v4` and operation `SOLVE_QUADRATIC_COMPLEX`.
4. **Certified Squarefree Normalization of $|\Delta|$ ($-\Delta$):** Deterministic extraction of small prime squares ($p_i \le 65536$) with a strict 32-bit ceiling on the unfactored remainder ($R < 2^{32}$). If $R \ge 2^{32}$, execution fails closed pre-dispatch with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT` without spawning worker processes.
5. **Independent Host Verification over $\mathbb{Q}(i\sqrt{d})$:** Host independently derives expected canonical roots and verifies worker candidates using exact rational algebraic identities:
   - Vieta sum: $2Aa + B = 0$
   - Vieta product: $A(a^2 + c^2 d) - C = 0$
   - Real polynomial residual: $A(a^2 - c^2 d) + Ba + C = 0$
   - Imaginary polynomial residual: $c(2Aa + B) = 0$
6. **Strict Operation Separation (Preserving B1 Real-Domain Semantics):** Legacy operations (`SOLVE`, `SOLVE_QUADRATIC`) continue to return `NO_REAL_ROOT` (`solution_type="EMPTY_SET"`) when $\Delta < 0$ in the real domain, preserving GDPT 2018 Grade 9-10 real algebra compatibility. Complex roots are dispatched strictly when requested via the v4 complex path.
7. **Containment Preservation:** Win32 Job Object and Windows AppContainer containment remain 100% active, with worker entrypoint and baseline files completely frozen.

---

## 2. Frozen Baseline & Provenance Lineage

| Milestone | Tested Source SHA | Evidence / Release Commit SHA | Status |
| :--- | :--- | :--- | :--- |
| **B0 Baseline (Affine)** | `bba90b868272ef93769b2b0c0ad2a8d8d4e2c9bf` | `147f561a883c6d5ea75febe7857e00291107b6da` | ACCEPTED / FROZEN |
| **B1 Baseline (Rational Quadratic)** | `56d4eb5a09e751304182492d38087c5a468beff6` | `0da7ac5157e3f92b7934535b45d38d64a6f0b625` | ACCEPTED / FROZEN |
| **B2 Baseline (Quadratic Surd)** | `e7265539634919bdbc7c276553033b8e9fda2659` | `dfa6d6626fdaf99e9d51b6f7321ed0342860355a` | ACCEPTED / FROZEN (Tag: `p03c-p1c-04-b2-accepted`) |
| **B3 Preflight (Exact Complex)** | N/A (Docs only) | *Pending Preflight Commit* | UNDER AUDIT |

All historical source, tests, protocol semantics, containment bounds, and evidence records remain strictly immutable.

---

## 3. Existing B0/B1/B2 Behavior & The Routing Conflict

### 3.1 Current B0/B1/B2 Execution Architecture

```
[User Query / IR Payload]
        │
        ▼
[MKEIntakeValidator.validate()] ──(Invalid / Non-Exhaustive / Scope)──► Fail Closed (NOT_DISPATCHED)
        │
        ▼
[B0 Affine Reduction Check] ──(Degree <= 1)──► Dispatch mke.p02a.v1 / SOLVE
        │
        ▼ (Degree == 2)
[Host Quadratic Reduction] ──► Extracts host (A, B, C) via bounded helpers (max 256 bits)
        │
        ▼
[Host Discriminant] ──► Δ = B^2 - 4*A*C
        │
        ├─► If Δ > 0 AND Δ is Rational Square:
        │     Dispatch mke.p02a.v2 / SOLVE_QUADRATIC ──► Host Verifies TWO_DISTINCT_REAL_ROOTS (Q)
        │
        ├─► If Δ == 0:
        │     Dispatch mke.p02a.v2 / SOLVE_QUADRATIC ──► Host Verifies UNIQUE_REAL_ROOT (Q)
        │
        ├─► If Δ > 0 AND Δ is NOT a Rational Square:
        │     Dispatch mke.p02a.v3 / SOLVE_QUADRATIC_SURD ──► Host Verifies TWO_DISTINCT_REAL_ROOTS (Q(√d))
        │
        └─► If Δ < 0:
              Current B1 Behavior (mke.p02a.v2 / SOLVE_QUADRATIC):
              ──► Verifies NO_REAL_ROOT ──► Returns solution_type="EMPTY_SET", is_verified=True
```

### 3.2 The Semantic Routing Conflict & Resolution

#### Conflict Analysis
In high-school mathematics (GDPT 2018):
- **Grade 9 & 10 (Real Domain $\mathbb{R}$):** The equation $x^2 + 1 = 0$ has **no real solution** ($S = \emptyset$). Returning complex roots for a standard Grade 9 real equation would constitute a pedagogical and semantic regression.
- **Grade 12 & Advanced Algebra (Complex Domain $\mathbb{C}$):** The equation $x^2 + 1 = 0$ has **two complex conjugate roots** $x = \pm i$.

#### Resolution Strategy: Explicit Protocol & Intake Separation
1. **Legacy Real Routing Preserved:** When requests target standard real-domain solving (e.g. `SOLVE` or `SOLVE_QUADRATIC`), $\Delta < 0$ continues to return `solution_type="EMPTY_SET"` with `is_verified=True` and `verified_roots=[]`.
2. **Dedicated Complex Operation:** Complex quadratic solving is explicitly bound to `OPERATION_SOLVE_QUADRATIC_COMPLEX` (`"SOLVE_QUADRATIC_COMPLEX"`) under protocol version `SCHEMA_VERSION_V4` (`"mke.p02a.v4"`).
3. **No Silent Mutation:** Zero legacy tests or existing API consumers will observe changed semantics for $\Delta < 0$ on v1/v2/v3 endpoints.

---

## 4. B3 Target Mathematical Scope

### 4.1 Authorized Problem Class
- **Equation:** $A x^2 + B x + C = 0$
- **Target Variable:** Single variable $x \in \mathbb{C}$
- **Coefficients:** Exact rational numbers $A, B, C \in \mathbb{Q}$ with $A \neq 0$
- **Discriminant Condition:** $\Delta = B^2 - 4AC < 0$ (strictly negative)
- **Positive Absolute Discriminant:** $|\Delta| = -\Delta = 4AC - B^2 > 0$
- **Squarefree Remainder Condition:** Normalization of $|\Delta| = s^2 \cdot d$ yields squarefree $d$ with $d < 2^{32}$.

### 4.2 Mathematical Subcases

#### Case C1 — Rational Imaginary Magnitude ($d = 1$)
If $-\Delta$ is an exact rational square ($-\Delta \in \mathbb{Q}^2$):
$$x = a \pm b \cdot i$$
where:
- $a = \frac{-B}{2A} \in \mathbb{Q}$ (real part)
- $b = \frac{\sqrt{-\Delta}}{2|A|} \in \mathbb{Q}^+$ (positive rational imaginary coefficient)
- $d = 1$

*Example:* $x^2 + 1 = 0 \implies \Delta = -4 \implies -\Delta = 4 = 2^2 \implies x = 0 \pm 1 \cdot i$.

#### Case C2 — Irrational Imaginary Magnitude ($d \ge 2$)
If $-\Delta$ is not an exact rational square ($-\Delta \notin \mathbb{Q}^2$):
$$x = a \pm b \cdot i\sqrt{d}$$
where:
- $a = \frac{-B}{2A} \in \mathbb{Q}$ (real part)
- $b = \frac{s}{2|A|} \in \mathbb{Q}^+$ (positive rational imaginary coefficient multiplier)
- $d \in \mathbb{Z}^+$ is certified squarefree with $2 \le d < 2^{32}$ ($-\Delta = s^2 \cdot d$).

*Example:* $x^2 + 2 = 0 \implies \Delta = -8 \implies -\Delta = 8 = 2^2 \cdot 2 \implies x = 0 \pm 1 \cdot i\sqrt{2}$.

---

## 5. Canonical Exact Complex Representation

### 5.1 Representation Options Analysis

| Option | Schema Structure | Uniqueness | Complexity | Decision |
| :--- | :--- | :--- | :--- | :--- |
| **Option A (Disjoint Models)** | Two separate models: `ComplexRationalRoot(a, b)` and `ComplexSurdRoot(a, b, d)` | High, but creates polymorphic return types | Callers must handle union types `Union[ComplexRationalRoot, ComplexSurdRoot]` | Rejected |
| **Option B (Unified Canonical Surd Model)** | Single model: `ComplexQuadraticRoot(real_part, imaginary_coefficient, radicand)` with canonical $d=1$ convention | **Proven Unique** | Uniform, clean, zero polymorphism, directly extends B2 patterns | **SELECTED** |
| **Option C (Free-Form Symbolic AST)** | Arbitrary AST expressions | Low (multiple equivalent AST trees) | High verification and parsing overhead | Rejected |

### 5.2 Selected Canonical Representation: Option B
Every exact quadratic complex root $z \in \mathbb{C}$ is uniquely represented by the tuple:
$$\text{Root}(a, c, d) \iff a + c \cdot i\sqrt{d}$$
where:
1. `real_part` ($a \in \mathbb{Q}$): Exact integer rational $p_a / q_a$ in lowest terms ($q_a > 0, \gcd(|p_a|, q_a) = 1$). If $p_a = 0$, $q_a = 1$.
2. `imaginary_coefficient` ($c \in \mathbb{Q}$): Exact non-zero integer rational $p_c / q_c$ in lowest terms ($q_c > 0, \gcd(|p_c|, q_c) = 1, p_c \neq 0$).
3. `radicand` ($d \in \mathbb{Z}^+$): Exact positive integer strictly bounded by $1 \le d < 2^{32}$ and certified squarefree.
   - When $d = 1$: Represents rational imaginary magnitude $c \cdot i\sqrt{1} = c \cdot i$.
   - When $d \ge 2$: Represents irrational imaginary magnitude $c \cdot i\sqrt{d}$.

### 5.3 Ambiguity Elimination Proofs

| Prohibited Ambiguity | Canonical Enforcement Mechanism |
| :--- | :--- |
| $i$ vs $1 \cdot i$ vs $i\sqrt{1}$ | All rational imaginary roots enforce $c = 1/1, d = 1$. |
| $\sqrt{-2}$ vs $i\sqrt{2}$ | Negative radicands are strictly forbidden ($d \ge 1$); imaginary unit $i$ is factored out. |
| $2i\sqrt{2}$ vs $i\sqrt{8}$ | Radicand $d$ must be squarefree. $\sqrt{8}$ factors into $s=2, d=2$, forcing $c = \pm 2, d = 2$. |
| $a + 0 \cdot i$ (Real degenerate root) | $c.numerator \neq 0$ is strictly required on `ComplexQuadraticRoot`. Real roots cannot be represented in B3 complex models. |
| Unreduced fractions $2/4 \cdot i$ | Rational components enforce $\gcd(|p|, q) = 1$. |

---

## 6. Proof of Representation Completeness & Canonical Uniqueness

### 6.1 Theorem: Completeness of Representation
**Statement:** Let $P(x) = Ax^2 + Bx + C = 0$ with $A, B, C \in \mathbb{Q}$, $A \neq 0$, and $\Delta = B^2 - 4AC < 0$. Then both roots of $P(x)$ in $\mathbb{C}$ are expressible in the form $a \pm b \cdot i\sqrt{d}$ with $a \in \mathbb{Q}, b \in \mathbb{Q}^+, d \in \mathbb{Z}^+_{\text{sqf}}$.

**Proof:**
1. Since $A, B, C \in \mathbb{Q}$, $\Delta = B^2 - 4AC \in \mathbb{Q}$.
2. Since $\Delta < 0$, $-\Delta > 0$ is a strictly positive rational number $p/q$ ($p, q \in \mathbb{Z}^+, \gcd(p, q) = 1$).
3. The product $M = p \cdot q \in \mathbb{Z}^+$ has a unique prime factorization $M = \prod_{k} p_k^{e_k}$.
4. Let $s_0 = \prod_k p_k^{\lfloor e_k/2 \rfloor}$ and $d = \prod_{k, e_k \text{ odd}} p_k$. Then $M = s_0^2 \cdot d$, where $d$ is squarefree and $d \ge 1$.
5. Then $-\Delta = \frac{p}{q} = \frac{p q}{q^2} = \frac{M}{q^2} = \left(\frac{s_0}{q}\right)^2 \cdot d = s^2 \cdot d$, where $s = s_0/q \in \mathbb{Q}^+$.
6. By the quadratic formula, the roots are:
   $$x = \frac{-B \pm \sqrt{\Delta}}{2A} = \frac{-B \pm i\sqrt{-\Delta}}{2A} = \frac{-B}{2A} \pm \frac{s\sqrt{d}}{2|A|} i = a \pm b \cdot i\sqrt{d}$$
   where $a = \frac{-B}{2A} \in \mathbb{Q}$ and $b = \frac{s}{2|A|} \in \mathbb{Q}^+$.
7. Therefore, every quadratic equation over $\mathbb{Q}$ with $\Delta < 0$ has roots covered by the representation $(a, -b, d)$ and $(a, +b, d)$, subject only to the computational 32-bit certification bound on $d$. $\blacksquare$

### 6.2 Theorem: Uniqueness of Canonical Representation
**Statement:** For any given quadratic equation $Ax^2 + Bx + C = 0$ ($\Delta < 0$), the representation of the ordered root pair $[(a, -b, d), (a, +b, d)]$ is unique.

**Proof:**
1. The real part $a = -B/(2A)$ is uniquely determined as the quotient of two rationals in $\mathbb{Q}$.
2. By the Fundamental Theorem of Arithmetic, the squarefree decomposition of $-\Delta = s^2 d$ with $s \in \mathbb{Q}^+$ and squarefree integer $d \ge 1$ is unique.
3. The imaginary magnitude $b = s/(2|A|)$ is uniquely determined in $\mathbb{Q}^+$.
4. Lowest-terms reduction of $a = p_a/q_a$ and $b = p_b/q_b$ with $q_a, q_b > 0$ and $\gcd(|p_a|, q_a) = \gcd(p_b, q_b) = 1$ is unique.
5. The ordering constraint requiring negative imaginary coefficient first ($c_1 = -b < 0$) and positive second ($c_2 = +b > 0$) induces a strict, unique bijection between the unordered root set $\{z_1, z_2\}$ and the ordered sequence $[(a, -b, d), (a, +b, d)]$. $\blacksquare$

---

## 7. Deterministic Root Serialization Ordering

To ensure $100\%$ deterministic transport and avoid floating-point / complex sorting issues:

1. **Conjugate Pair Structure:** Every complex quadratic solution set contains exactly two distinct conjugate roots:
   - Root 1: $z_1 = a - b \cdot i\sqrt{d}$ (negative imaginary coefficient $c_1 = -b < 0$)
   - Root 2: $z_2 = a + b \cdot i\sqrt{d}$ (positive imaginary coefficient $c_2 = +b > 0$)
2. **Canonical List Order:**
   $$\text{verified\_complex\_roots} = [z_1, z_2]$$
3. **Ordering Invariants:**
   - $z_1.\text{real\_part} == z_2.\text{real\_part} == a$
   - $z_1.\text{radicand} == z_2.\text{radicand} == d$
   - $z_1.\text{imaginary\_coefficient.numerator} < 0$
   - $z_2.\text{imaginary\_coefficient.numerator} > 0$
   - $|z_1.\text{imaginary\_coefficient}| == z_2.\text{imaginary\_coefficient} == b$
4. Any response with positive imaginary first, missing root, extra root, or unequal magnitudes is strictly rejected as malformed.

---

## 8. Squarefree Certification for $|\Delta|$

### 8.1 The Factoring Challenge & Bounded Contract
For $-\Delta = p/q \in \mathbb{Q}^+$, let $M = p \cdot q$. To compute $-\Delta = s^2 d$:
1. **Prime Sieve & Trial Division:** The engine checks all prime squares $p_i^2$ for $p_i \le 65536$ ($2^{16}$, total 6,542 primes).
2. **Certification Ceiling:** After trial division, $M = s_0^2 \cdot R$.
   - If $R = 1$: Fully factored rational square ($d = 1$).
   - If $R < 2^{32}$: $R$ is mathematically certified squarefree.
     *Proof:* If $R$ contained a composite square factor $q^2 > 1$, then prime factor $q \ge 65537 > 2^{16} \implies q^2 > (2^{16})^2 = 2^{32} > R$, which contradicts $q^2 \mid R$. Thus, $R$ cannot contain any square factor $> 1$ and is certified squarefree ($d = R$).
   - If $R \ge 2^{32}$: Squarefreeness cannot be certified in $O(1)$ small-prime bounds. The engine **fails closed** with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`.

---

## 9. Resource Bounds & Containment Philosophy

| Resource Dimension | Bound / Ceiling | Enforcement Point | Fail-Closed Action |
| :--- | :--- | :--- | :--- |
| **Rational Component Bit Length** | 256 bits ($p, q < 2^{256}$) | Host & Worker AST / Rational checks | `ERR_RESOURCE_EXHAUSTED` |
| **Normalization Product $M = p \cdot q$** | 512 bits ($M < 2^{512}$) | Host & Worker Normalizer | `ERR_RESOURCE_EXHAUSTED` |
| **Squarefree Trial Primes** | $p_i \le 65536$ (6,542 primes) | Host & Worker Factorization Loop | Strict loop bound |
| **Squarefree Remainder Bound** | $R < 2^{32}$ (32 bits) | Host & Worker Post-Factorization | `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT` |
| **AST Node Budget** | Max 100 nodes | Host AST Coefficient Extractor | `ERR_AST_TOO_COMPLEX` |
| **AST Depth Budget** | Max 20 recursive depth | Host AST Coefficient Extractor | `ERR_AST_TOO_DEEP` |
| **Wall-Clock Budget** | 5.0 seconds aggregate | Host Monotonic Timer | `ERR_TIMEOUT` |
| **Process Memory** | 256 MB per worker | Win32 Job Object | `ERR_RESOURCE_EXHAUSTED` |
| **Job Memory** | 512 MB job limit | Win32 Job Object | `ERR_RESOURCE_EXHAUSTED` |
| **Breakaway Processes** | Denied (`JOB_OBJECT_LIMIT_BREAKAWAY_OK` omitted) | Win32 Job Object | Process termination |

---

## 10. Dedicated Protocol Version 4 (`mke.p02a.v4`)

### 10.1 Request Envelope
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "equation": "x^2 + 2*x + 5 = 0"
}
```

### 10.2 Success Response Envelope
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "outcome": "SUCCESS",
  "status": "TWO_COMPLEX_CONJUGATE_ROOTS",
  "roots": [
    {
      "real_part": {
        "numerator": "-1",
        "denominator": "1"
      },
      "imaginary_coefficient": {
        "numerator": "-2",
        "denominator": "1"
      },
      "radicand": "1"
    },
    {
      "real_part": {
        "numerator": "-1",
        "denominator": "1"
      },
      "imaginary_coefficient": {
        "numerator": "2",
        "denominator": "1"
      },
      "radicand": "1"
    }
  ],
  "discriminant": {
    "numerator": "-16",
    "denominator": "1"
  },
  "radicand": "1",
  "definedness": true,
  "error": null,
  "is_provisional_evidence": true
}
```

### 10.3 Protocol Invariants & Rejection Rules
- Exact field set match: any unexpected or missing keys produce `ERR_PROTOCOL_ERROR`.
- `schema_version` must be strictly `"mke.p02a.v4"`.
- `operation` must be strictly `"SOLVE_QUADRATIC_COMPLEX"`.
- `roots` must be a 2-element list of exact wire dictionaries.
- `discriminant` must have negative numerator (`numerator < 0`).
- `radicand` must be a string decimal integer $1 \le d < 2^{32}$.
- Cross-version dispatch (e.g. sending `SOLVE` on v4 or `SOLVE_QUADRATIC_COMPLEX` on v1/v2/v3) is strictly rejected at the protocol layer.

---

## 11. Worker Solver Architecture

### 11.1 Pure-Python Isolated Kernel
Located in `src/mke_product/solver/quadratic_complex.py`:
- Extracts coefficients $A, B, C \in \mathbb{Q}$ from parsed AST.
- Computes $\Delta = B^2 - 4AC$.
- If $\Delta \ge 0$: returns `status="OUT_OF_SCOPE"`, `error_code="ERR_QUADRATIC_COMPLEX_EXPECTED_NEGATIVE_DISCRIMINANT"`.
- Computes $-\Delta = |\Delta|$.
- Normalizes $-\Delta = s^2 \cdot d$ using worker-local prime trial division.
- If $R \ge 2^{32}$: returns `status="RESOURCE_EXHAUSTED"`, `error_code="ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT"`.
- Computes:
  $$a = \frac{-B}{2A}, \quad b = \frac{s}{2|A|}$$
- Returns `QuadraticComplexSolverResult` with status `"TWO_COMPLEX_CONJUGATE_ROOTS"`, roots $[(a, -b, d), (a, +b, d)]$, `discriminant`, and `radicand`.

---

## 12. Independent Host Algebraic Verification Gate

### 12.1 Host Verification Invariant
The host verifier **never trusts worker output**. The worker output is treated strictly as provisional evidence (`is_provisional_evidence: true`).

### 12.2 Exact Algebraic Proof over $\mathbb{Q}(i\sqrt{d})$
The host independently:
1. Re-extracts $A, B, C \in \mathbb{Q}$ from the original validated AST.
2. Computes host discriminant $\Delta_{\text{host}} = B^2 - 4AC$.
3. Verifies $\Delta_{\text{host}} < 0$.
4. Independently normalizes $-\Delta_{\text{host}} = s_{\text{host}}^2 \cdot d_{\text{host}}$ using the host's independent prime sieve.
5. Proves the algebraic identities in $\mathbb{Q}$ using exact rational arithmetic:
   - **Identity 1 (Vieta Sum):**
     $$z_1 + z_2 = 2a \iff 2Aa + B = 0$$
   - **Identity 2 (Vieta Product):**
     $$z_1 \cdot z_2 = a^2 + b^2 d \iff A(a^2 + b^2 d) - C = 0$$
   - **Identity 3 (Real Polynomial Residual):**
     $$A(a^2 - b^2 d) + Ba + C = 0$$
   - **Identity 4 (Imaginary Polynomial Residual):**
     $$b(2Aa + B) = 0$$
6. Validates that wire response roots match $[(a, -b, d), (a, +b, d)]$ with exact canonical signs and lowest-terms rationals.

---

## 13. Public Pydantic Models Contract

### 13.1 Root Model: `ComplexQuadraticRoot`
```python
class ComplexQuadraticRoot(BaseModel):
    """Exact quadratic complex root in public result: real_part + imaginary_coefficient * i * sqrt(radicand)."""
    model_config = ConfigDict(extra="forbid", strict=True)

    real_part: SurdRationalComponent = Field(..., description="Exact rational real part a")
    imaginary_coefficient: SurdRationalComponent = Field(..., description="Exact non-zero rational imaginary coefficient c")
    radicand: int = Field(..., strict=True, description="Certified squarefree radicand d in [1, 2^32 - 1]")

    @model_validator(mode="after")
    def _validate_complex_root(self) -> ComplexQuadraticRoot:
        if type(self.radicand) is not int or type(self.radicand) is bool:
            raise ValueError("ComplexQuadraticRoot radicand must be a strict integer.")
        if not (1 <= self.radicand < (1 << 32)):
            raise ValueError("ComplexQuadraticRoot radicand must satisfy 1 <= radicand < 2^32.")
        if self.imaginary_coefficient.numerator == 0:
            raise ValueError("ComplexQuadraticRoot imaginary_coefficient must be non-zero.")
        return self
```

### 13.2 Result Model: `ComplexControlledDispatchResult`
```python
class ComplexControlledDispatchResult(ControlledDispatchResult):
    """B3-specific outcome model carrying exact complex conjugate roots and discriminant."""
    model_config = ConfigDict(extra="forbid")

    verified_complex_roots: List[ComplexQuadraticRoot] = Field(..., description="Exact complex conjugate roots pair [z_minus, z_plus]")
    discriminant: RationalRoot = Field(..., description="Exact negative rational discriminant")
    radicand: int = Field(..., strict=True, description="Certified squarefree radicand d in [1, 2^32 - 1]")
    representation: Literal["QUADRATIC_COMPLEX"] = Field(default="QUADRATIC_COMPLEX", description="Representation tag")

    @model_validator(mode="after")
    def _validate_complex_result(self) -> ComplexControlledDispatchResult:
        if type(self.radicand) is not int or type(self.radicand) is bool:
            raise ValueError("ComplexControlledDispatchResult radicand must be a strict integer.")
        if not (1 <= self.radicand < (1 << 32)):
            raise ValueError("ComplexControlledDispatchResult radicand must satisfy 1 <= radicand < 2^32.")
        if self.discriminant.numerator >= 0:
            raise ValueError("ComplexControlledDispatchResult discriminant must be strictly negative.")
        if not isinstance(self.verified_complex_roots, list) or len(self.verified_complex_roots) != 2:
            raise ValueError("ComplexControlledDispatchResult must contain exactly two roots.")
        r1, r2 = self.verified_complex_roots
        if r1.real_part != r2.real_part:
            raise ValueError("ComplexControlledDispatchResult roots must have identical real parts.")
        if r1.radicand != self.radicand or r2.radicand != self.radicand:
            raise ValueError("ComplexControlledDispatchResult roots must share the top-level radicand.")
        if r1.imaginary_coefficient.numerator >= 0 or r2.imaginary_coefficient.numerator <= 0:
            raise ValueError("ComplexControlledDispatchResult canonical order requires negative imaginary coeff first and positive second.")
        if abs(r1.imaginary_coefficient.numerator) != r2.imaginary_coefficient.numerator or r1.imaginary_coefficient.denominator != r2.imaginary_coefficient.denominator:
            raise ValueError("ComplexControlledDispatchResult imaginary coefficients must have equal magnitude and opposite signs.")
        return self
```

---

## 14. Backward Compatibility Matrix

| API / Endpoint | Target Domain | Input Equation | Pre-B3 Result | B3 Result | Compatibility Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `v1 / SOLVE` | Real $\mathbb{R}$ | `2*x + 4 = 0` | $x = -2$ | $x = -2$ | 100% Identical |
| `v2 / SOLVE_QUADRATIC` | Real $\mathbb{R}$ | `x^2 - 4 = 0` | $x = \pm 2$ | $x = \pm 2$ | 100% Identical |
| `v2 / SOLVE_QUADRATIC` | Real $\mathbb{R}$ | `x^2 + 1 = 0` | `NO_REAL_ROOT` (`EMPTY_SET`) | `NO_REAL_ROOT` (`EMPTY_SET`) | 100% Identical |
| `v3 / SOLVE_QUADRATIC_SURD` | Real $\mathbb{R}$ | `x^2 - 2 = 0` | $x = \pm \sqrt{2}$ | $x = \pm \sqrt{2}$ | 100% Identical |
| `v4 / SOLVE_QUADRATIC_COMPLEX` | Complex $\mathbb{C}$ | `x^2 + 1 = 0` | Unsupported (v4 didn't exist) | $x = \pm i$ | NEW Capability |
| `v4 / SOLVE_QUADRATIC_COMPLEX` | Complex $\mathbb{C}$ | `x^2 + 2 = 0` | Unsupported (v4 didn't exist) | $x = \pm i\sqrt{2}$ | NEW Capability |

---

## 15. Error Taxonomy & Standardized Codes

| Error Code | Layer | Trigger Condition |
| :--- | :--- | :--- |
| `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT` | Host / Worker | Discriminant remainder $R \ge 2^{32}$ |
| `ERR_QUADRATIC_COMPLEX_EXPECTED_NEGATIVE_DISCRIMINANT` | Worker | $\Delta \ge 0$ passed to complex solver |
| `ERR_COMPLEX_VERIFICATION_MISMATCH` | Host | Worker roots fail algebraic Vieta / residual proof |
| `ERR_MALFORMED_WORKER_RESPONSE` | Host | Non-conforming wire schema, unexpected fields, or invalid types |
| `ERR_UNSUPPORTED_VERSION` | Protocol | Unknown or mismatched schema version |
| `ERR_UNKNOWN_OPERATION` | Protocol | Unknown operation string |
| `ERR_TIMEOUT` | Host Bridge | Cumulative 5.0s monotonic deadline exceeded |
| `ERR_RESOURCE_EXHAUSTED` | Job Object / Host | Memory or integer bit length limits exceeded |

---

## 16. Adversarial Threat & Wire Matrix

The B3 test suite must explicitly assert fail-closed rejection for:
1. **Root Count Violations:** 0 roots, 1 root, 3 roots, empty root list.
2. **Conjugate Symmetry Violations:** Mismatched real parts ($a_1 \neq a_2$), unequal imaginary magnitudes ($|c_1| \neq c_2$), identical signs (both positive or both negative).
3. **Canonical Ordering Violations:** Positive imaginary root first, negative second.
4. **Radicand Edge Cases:** $d = 0$, negative $d$, non-squarefree $d$ ($d=4, 8, 12$), out-of-bounds $d \ge 2^{32}$, mismatched root and top-level radicands.
5. **Rational Wire Violations:** Denominator $\le 0$, unreduced fractions ($\gcd \neq 1$), noncanonical zero ($0/2$), leading plus signs (`"+1"`), redundant leading zeros (`"01"`), values exceeding 256 bits.
6. **Type & Coercion Violations:** String radicand (`radicand="1"`), float radicand (`radicand=1.0`), boolean radicand (`radicand=True`), float coefficients (`1.5`).
7. **Cross-Version Attacks:** Sending `SOLVE_QUADRATIC_COMPLEX` under `mke.p02a.v1`, `v2`, or `v3`; sending legacy operations under `v4`.
8. **Worker Spoofing:** Worker returning `outcome="SUCCESS"` with mathematically incorrect roots. Host proof fails closed with `ERR_COMPLEX_VERIFICATION_MISMATCH`.

---

## 17. Frozen Surface Inventory

The following files remain strictly frozen and byte-identical to `0da7ac5157e3f92b7934535b45d38d64a6f0b625`:
- `src/mke_product/worker/entrypoint.py`
- `src/mke_product/solver/quadratic.py`
- `src/mke_product/solver/affine.py`
- `src/mke_product/solver/solver.py`
- `src/mke_product/evaluator/evaluator.py`
- `src/mke_product/parser/parser.py`
- `src/mke_product/parser/ast.py`
- `tests/test_worker_windows.py`

---

## 18. Proposed Implementation Staging Plan

If GO is approved, implementation will proceed across two disciplined commits:

### Stage 1: Protocol v4 & Isolated Worker Kernel
- Files: `src/mke_product/protocol/schema.py`, `src/mke_product/protocol/validator.py`, `src/mke_product/protocol/dispatcher.py`, `src/mke_product/solver/quadratic_complex.py`, `tests/test_protocol.py`, `tests/test_p03c_p1c_quadratic_complex_solver.py`.
- Deliverables: Wire schema `mke.p02a.v4`, operation `SOLVE_QUADRATIC_COMPLEX`, pure-Python worker solver kernel, protocol matrix tests.

### Stage 2: Host Bridge Verification Gate & Adversarial Test Suite
- Files: `src/mke_product/cas/bridge.py`, `tests/test_p03c_p1c_quadratic_complex_dispatch.py`.
- Deliverables: Host independent verification over $\mathbb{Q}(i\sqrt{d})$, public Pydantic models (`ComplexQuadraticRoot`, `ComplexControlledDispatchResult`), end-to-end bridge tests, adversarial wire tests, Windows AppContainer live worker integration tests.

---

## 19. Preflight Acceptance Gates Evaluation

| Gate | Criterion | Status | Evaluation |
| :--- | :--- | :--- | :--- |
| **Gate A** | Exact canonical representation | **PASS** | Option B provides proven unique tuple $(a, \pm c, d)$ with $d \ge 1$ squarefree. |
| **Gate B** | No authoritative floats | **PASS** | 100% exact rational arithmetic (`Rational`). |
| **Gate C** | No Python `complex` for proof | **PASS** | Host proof decomposes into independent rational real and imaginary equations over $\mathbb{Q}$. |
| **Gate D** | Deterministic bounded arithmetic | **PASS** | 256-bit component and 512-bit product bounds enforced. |
| **Gate E** | Independent host verification | **PASS** | Host independently derives roots and evaluates Vieta + polynomial residual identities. |
| **Gate F** | No mutation of v1/v2/v3 contracts | **PASS** | Dedicated schema `mke.p02a.v4` and operation `SOLVE_QUADRATIC_COMPLEX`. |
| **Gate G** | No silent change to legacy B1 semantics | **PASS** | Real solving continues to return `NO_REAL_ROOT` (`EMPTY_SET`) for $\Delta < 0$. |
| **Gate H** | Exact conjugate root verification | **PASS** | Symmetry and sign invariants strictly validated by host and Pydantic models. |
| **Gate I** | Resource limits remain fail-closed | **PASS** | Remainder $R \ge 2^{32}$ fails closed with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`. |
| **Gate J** | Windows containment unaffected | **PASS** | AppContainer and Job Object limits remain 100% active. |
| **Gate K** | Adversarial matrix is explicit | **PASS** | Comprehensive wire, symmetry, and type attack matrix specified. |
| **Gate L** | Staged, auditable commits | **PASS** | Exactly 2 implementation commits specified. |

---

## 20. Explicit Deferred Capabilities

The following capabilities remain explicitly **OUT OF SCOPE** for B3:
- Cubic, quartic, or general polynomial solving.
- Arbitrary degree algebraic extension fields.
- Transcendental complex equations ($e^{iz} = 1$, $\sin(z) = 0$).
- Arbitrary large integer prime factorization.
- Approximate or numerical complex solving.

---

## 21. Final Recommendation

**RECOMMENDATION:** **`GO BOUNDED`**

The technical specification for PRODUCT-03C-P1C-04-B3 is complete, mathematically sound, backward-compatible, and ready for Coordinator / Independent Auditor review.
