# MKE Product 03C-P1C-04-B3 Preflight: Exact Quadratic Complex Roots Architecture (R1 Revision)

- **Milestone:** MKE Product 03C-P1C-04-B3
- **Document Version:** 1.1.0 (B3 Technical Preflight Specification — R1 Remediation)
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Active Branch:** `product/p03c-p1c-04-b3-exact-complex-preflight`
- **Parent Preflight Commit:** `3749fe499aa8059a3cc747295214cf76d492fd70`
- **Predecessor Baseline:** P1C-04-B2 Accepted / Closed (`dfa6d6626fdaf99e9d51b6f7321ed0342860355a`, Tag: `p03c-p1c-04-b2-accepted`)
- **Status:** PREFLIGHT SPECIFICATION R1 — PENDING AUDITOR GO/NO-GO REVIEW
- **Date:** 2026-10-01

---

## 1. Executive Summary & Recommendation

### 1.1 Recommendation: GO BOUNDED
We recommend **GO BOUNDED** for the implementation of milestone **PRODUCT-03C-P1C-04-B3** under the following mathematical, architectural, and security invariants:

1. **Exact Symbolic Complex Representation (Option B):** Exact quadratic complex roots are represented in the field $\mathbb{Q}(i\sqrt{d})$ as $a \pm c \cdot i\sqrt{d}$, where $a \in \mathbb{Q}$ is the exact rational real part, $c \in \mathbb{Q}^+$ is the unique positive rational imaginary magnitude, and $d \in \mathbb{Z}^+$ is a certified squarefree integer ($d = 1$ for purely rational imaginary roots, $2 \le d < 2^{32}$ for imaginary surd roots).
2. **Explicit Product-Level Complex Entry Path (`dispatch_complex`):** To preserve the locked signature and real-domain semantics of `ControlledDispatchBridge.dispatch(raw_query, ir_payload)`, complex solving is invoked via a dedicated new bridge entry point: `ControlledDispatchBridge.dispatch_complex(raw_query, ir_payload)`. Legacy `dispatch()` continues to return `solution_type="NO_REAL_ROOT"` for $\Delta < 0$.
3. **Exact C1 Perfect-Square Fast Path:** For $D = -\Delta = p/q > 0$, host and worker independently perform exact integer square-root checks ($s_p^2 == p$ and $s_q^2 == q$). If both numerator and denominator are perfect squares, the root is classified as Case C1 ($d = 1$) and solved immediately in $\mathbb{Q}(i)$ without running the bounded small-prime factorization loop (e.g. supporting $D = 65537^2$ and large rational squares).
4. **Bounded C2 Squarefree Normalization ($R < 2^{32}$ via $P \le 65536$ Prime Trial Division):** For non-square $-\Delta$, trial division extracts small prime squares ($p_i \le 65536$). The engine certifies squarefreeness if and only if the unfactored remainder $R < 2^{32}$. If $R \ge 2^{32}$, execution fails closed with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`.
5. **Zero Floating-Point & Zero Native Python `complex`:** All solving, reduction, protocol serialization, and independent host verification are performed exclusively using exact integer and rational arithmetic (`Rational`). No floating-point approximations, `complex` primitives, or third-party CAS engines (e.g., SymPy) are permitted anywhere in the pipeline.
6. **Dedicated Protocol Version `mke.p02a.v4`:** Complex solving is introduced via dedicated schema `mke.p02a.v4` and operation `SOLVE_QUADRATIC_COMPLEX`.
7. **Independent Host Verification over $\mathbb{Q}(i\sqrt{d})$:** Host independently derives expected canonical roots and verifies worker candidates using exact rational algebraic identities (Vieta sum, Vieta product, and real/imaginary polynomial residuals).
8. **Containment Preservation & Surface Inventory:** Win32 Job Object and Windows AppContainer containment remain 100% active. `entrypoint.py` remains frozen, while `worker/controller.py` is updated to include `SOLVE_QUADRATIC_COMPLEX` in `ALLOWED_OPERATIONS`.

---

## 2. Frozen Baseline & Provenance Lineage

| Milestone | Tested Source SHA | Evidence / Release Commit SHA | Status |
| :--- | :--- | :--- | :--- |
| **B0 Baseline (Affine)** | `bba90b868272ef93769b2b0c0ad2a8d8d4e2c9bf` | `147f561a883c6d5ea75febe7857e00291107b6da` | ACCEPTED / FROZEN |
| **B1 Baseline (Rational Quadratic)** | `56d4eb5a09e751304182492d38087c5a468beff6` | `0da7ac5157e3f92b7934535b45d38d64a6f0b625` | ACCEPTED / FROZEN |
| **B2 Baseline (Quadratic Surd)** | `e7265539634919bdbc7c276553033b8e9fda2659` | `dfa6d6626fdaf99e9d51b6f7321ed0342860355a` | ACCEPTED / FROZEN (Tag: `p03c-p1c-04-b2-accepted`) |
| **B3 Preflight R1 (Exact Complex)** | N/A (Docs only) | *Pending R1 Commit* | UNDER AUDIT |

All historical source, tests, protocol semantics, containment bounds, and evidence records remain strictly immutable.

---

## 3. Product-Level Entry Path & Routing Architecture

### 3.1 Dual-Routing Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              STUDENT / CALLER INTAKE                                   │
└───────────────────┬────────────────────────────────────────────────┬───────────────────┘
                    │                                                │
       [Legacy Real-Domain Intent]                      [Explicit Complex-Domain Intent]
                    │                                                │
                    ▼                                                ▼
     ControlledDispatchBridge.dispatch()             ControlledDispatchBridge.dispatch_complex()
                    │                                                │
                    ▼                                                ▼
        [MKEIntakeValidator.validate()]                  [MKEIntakeValidator.validate()]
                    │                                                │
                    ▼                                                ▼
         [Host Quadratic Reduction]                       [Host Quadratic Reduction]
        Extracts (A, B, C) over Q                        Extracts (A, B, C) over Q
                    │                                                │
                    ▼                                                ▼
        Δ = B^2 - 4*A*C                                  Δ = B^2 - 4*A*C
                    │                                                │
        ┌───────────┴───────────┐                        ┌───────────┴───────────┐
        │ (Legacy Real Domain)  │                        │   (Complex Domain)    │
        ▼                       ▼                        ▼                       ▼
     If Δ >= 0:              If Δ < 0:                If Δ >= 0:              If Δ < 0:
  Route v1/v2/v3         Route v2 (mke.p02a.v2)   REJECT_SCOPE             Route v4 (mke.p02a.v4)
  SOLVE / QUADRATIC      SOLVE_QUADRATIC          Fail Closed              SOLVE_QUADRATIC_COMPLEX
  Returns real roots     Returns:                 ERR_QUADRATIC_COMPLEX_   Host Verifies & Returns:
                         solution_type=           EXPECTED_NEGATIVE_DISC   TWO_COMPLEX_CONJUGATE_ROOTS
                         "NO_REAL_ROOT"           (NOT_DISPATCHED)         in Q(i√d)
                         verified_roots=[]
```

### 3.2 Product-Level Bridge Entry Contracts

1. **`ControlledDispatchBridge.dispatch(raw_query, ir_payload)` (Legacy Real Domain):**
   - Signature remains strictly locked: accepts only `raw_query` and `ir_payload`.
   - Preserves 100% backward compatibility for all GDPT 2018 Grade 9-10 real equations.
   - When $\Delta < 0$, executes `mke.p02a.v2 / SOLVE_QUADRATIC` and returns `ControlledDispatchResult` (or `QuadraticControlledDispatchResult`) with:
     - `solution_type = "NO_REAL_ROOT"`
     - `verified_roots = []`
     - `is_verified = True`
     - `verification_status = VERIFIED_COMPLETE`
2. **`ControlledDispatchBridge.dispatch_complex(raw_query, ir_payload)` (New Complex Domain):**
   - Explicit domain-intent entry point for Grade 12 / advanced complex quadratic solving.
   - Prohibits inferring complex intent merely because $\Delta < 0$ in `dispatch()`.
   - Prohibits heuristic string parsing (such as searching for "over C" or "phức") in B3.
   - Requires:
     - Input parses cleanly as a single quadratic equation in variable $x$.
     - Leading coefficient $A \neq 0$.
     - Discriminant $\Delta = B^2 - 4AC < 0$.
   - If $\Delta \ge 0$: fails closed pre-dispatch with:
     - `intake_status = IntakeStatus.REJECTED_SCOPE`
     - `execution_status = ExecutionStatus.NOT_DISPATCHED`
     - `verification_status = VerificationStatus.NOT_APPLICABLE`
     - `is_verified = False`
     - `error_code = "ERR_QUADRATIC_COMPLEX_EXPECTED_NEGATIVE_DISCRIMINANT"`

---

## 4. Mathematical Scope & Exact Subcases

### 4.1 Input Scope
- **Equation:** $A x^2 + B x + C = 0$
- **Target Variable:** Single variable $x \in \mathbb{C}$
- **Coefficients:** Exact rational numbers $A, B, C \in \mathbb{Q}$ with $A \neq 0$
- **Discriminant Condition:** $\Delta = B^2 - 4AC < 0$
- **Positive Absolute Discriminant:** $D = -\Delta = |\Delta| = 4AC - B^2 > 0$

### 4.2 Exact Subcases: Case C1 vs Case C2

#### Case C1 — Rational Imaginary Magnitude ($d = 1$)
Occurs when $D = -\Delta = p/q$ is an exact rational square ($\text{isqrt}(p)^2 == p$ and $\text{isqrt}(q)^2 == q$).
$$x = a \pm b \cdot i$$
where:
- $a = \frac{-B}{2A} \in \mathbb{Q}$ (real part)
- $b = \frac{\sqrt{-\Delta}}{2|A|} \in \mathbb{Q}^+$ (positive rational imaginary magnitude)
- $d = 1$ (fixed canonical radicand)

*Canonical Examples:*
- $x^2 + 1 = 0 \implies \Delta = -4, -\Delta = 4 = 2^2 \implies \text{roots } [ -1i, +1i ] \implies (0, -1, 1), (0, +1, 1)$.
- $x^2 + 4 = 0 \implies \Delta = -16, -\Delta = 16 = 4^2 \implies \text{roots } [ -2i, +2i ] \implies (0, -2, 1), (0, +2, 1)$.
- $25x^2 + 9 = 0 \implies \Delta = -900, -\Delta = 900 = 30^2 \implies \text{roots } [ -(3/5)i, +(3/5)i ] \implies (0, -3/5, 1), (0, +3/5, 1)$.
- $x^2 + 65537^2 = 0 \implies -\Delta = (2 \cdot 65537)^2 \implies \text{roots } [ -65537i, +65537i ]$ (supported via exact C1 integer-square fast path).

#### Case C2 — Irrational Imaginary Magnitude ($d \ge 2$)
Occurs when $D = -\Delta$ is not an exact rational square.
$$x = a \pm b \cdot i\sqrt{d}$$
where:
- $a = \frac{-B}{2A} \in \mathbb{Q}$ (real part)
- $b = \frac{s}{2|A|} \in \mathbb{Q}^+$ (positive rational imaginary coefficient multiplier)
- $d \in \mathbb{Z}^+$ is certified squarefree with $2 \le d < 2^{32}$ ($-\Delta = s^2 \cdot d$).

*Canonical Examples:*
- $x^2 + 2 = 0 \implies \Delta = -8, -\Delta = 8 = 2^2 \cdot 2 \implies \text{roots } [ -1i\sqrt{2}, +1i\sqrt{2} ] \implies (0, -1, 2), (0, +1, 2)$.
- $x^2 + 2x + 3 = 0 \implies \Delta = -8, -\Delta = 8 = 2^2 \cdot 2 \implies \text{roots } [ -1 - 1i\sqrt{2}, -1 + 1i\sqrt{2} ]$.

---

## 5. Canonical Exact Complex Representation

### 5.1 Representation Model (Option B)
Every exact quadratic complex root $z \in \mathbb{C}$ is uniquely represented by the tuple:
$$\text{Root}(a, c, d) \iff a + c \cdot i\sqrt{d}$$
where:
1. `real_part` ($a \in \mathbb{Q}$): Exact integer rational $p_a / q_a$ in lowest terms ($q_a > 0, \gcd(|p_a|, q_a) = 1$). If $p_a = 0$, $q_a = 1$.
2. `imaginary_coefficient` ($c \in \mathbb{Q}$): Exact non-zero integer rational $p_c / q_c$ in lowest terms ($q_c > 0, \gcd(|p_c|, q_c) = 1, p_c \neq 0$).
3. `radicand` ($d \in \mathbb{Z}^+$): Exact positive integer strictly bounded by $1 \le d < 2^{32}$ and certified squarefree.
   - When $d = 1$: Represents rational imaginary magnitude $c \cdot i\sqrt{1} = c \cdot i$.
   - When $d \ge 2$: Represents irrational imaginary magnitude $c \cdot i\sqrt{d}$.

### 5.2 Canonical Uniqueness Invariants
- **Squarefree Radicand:** No square factors $> 1$ permitted in $d$. For rational imaginary roots, $d$ is strictly $1$. For surd roots, $d \ge 2$ is squarefree.
- **Non-Zero Imaginary Part:** $c.numerator \neq 0$ is strictly required. Real degenerate roots ($c = 0$) are rejected.
- **Sign Invariant for Negative Leading Coefficient ($A < 0$):** Since $b = s / (2|A|) > 0$, the unordered set of roots $\{ \frac{-B}{2A} - b \cdot i\sqrt{d}, \frac{-B}{2A} + b \cdot i\sqrt{d} \}$ is invariant under the sign of $A$. Canonical serialization always places the root with negative imaginary coefficient first.

---

## 6. Mathematical Representability vs. Bounded Engine Coverage

To ensure mathematical precision, B3 distinguishes between theoretical mathematical completeness and deterministic bounded execution coverage.

### 6.1 Definition A: Mathematical Representability
**Theorem:** Every quadratic equation $Ax^2 + Bx + C = 0$ with $A, B, C \in \mathbb{Q}$, $A \neq 0$, and $\Delta = B^2 - 4AC < 0$ has two roots in $\mathbb{C}$ that admit an exact mathematical representation $a \pm b \cdot i\sqrt{d}$ with $a \in \mathbb{Q}, b \in \mathbb{Q}^+$, and squarefree integer $d \ge 1$.

### 6.2 Definition B: Bounded Engine Executable Coverage
The B3 engine can deterministically solve and certify exact roots if and only if:
1. **C1 Path:** $-\Delta$ is an exact rational square ($d = 1$ certified via integer square root, regardless of prime magnitude, provided component bit lengths $\le 256$).
2. **C2 Path:** $-\Delta$ is not an exact rational square, and after stripping all prime-square factors $p_i^2$ for primes $p_i \le 65536$, the remaining unfactored integer $R$ satisfies $R < 2^{32}$.

### 6.3 Canonical Counterexample: $-\Delta = 2 \cdot 65537^2$
- **Mathematical Reality:** $-\Delta = 2 \cdot 65537^2 \implies s = 65537, d = 2$.
- **Bounded Engine Execution:** Since $65537 > 65536$, the prime trial division loop cannot extract $65537^2$. The remainder $R = 2 \cdot 65537^2 = 8,590,196,738 \approx 2^{32.9999} \ge 2^{32}$.
- **Engine Behavior:** Fails closed pre-dispatch with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`.
- **Integrity Rule:** The engine NEVER claims completeness outside its bounded certification contract.

---

## 7. Exact C1 Perfect-Square Fast Path

To ensure large rational squares (such as $D = 65537^2$ or fractional squares) do not fail due to the small-prime factorization bound, host and worker implement an independent C1 fast path:

```python
# Host / Worker Independent C1 Check
p = D.numerator
q = D.denominator
sp = math.isqrt(p)
sq = math.isqrt(q)

if sp * sp == p and sq * sq == q:
    # Exact C1 Rational Imaginary Root
    s = Rational(sp, sq)
    d = 1
    # Solves immediately in Q(i) without small-prime sieve loop
else:
    # C2 Path: Proceed to small-prime squarefree factorization
    s, d = _host_normalize_complex_discriminant_squarefree(D)
```

### Mandatory Adversarial Distinction:
1. $D = 65537^2 \implies C1$ success, $d = 1$, root pair $[ -65537i, +65537i ]$.
2. $D = (65537/65539)^2 \implies C1$ success, $d = 1$, root pair $[ -(65537/65539)i, +(65537/65539)i ]$.
3. $D = 2 \cdot 65537^2 \implies C2$ bounded certification failure, `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`.

---

## 8. Independent Host Verification over $\mathbb{Q}(i\sqrt{d})$

The trusted host verifier never trusts worker calculations. It independently validates candidate roots $z_1 = a - b \cdot i\sqrt{d}$ and $z_2 = a + b \cdot i\sqrt{d}$ using exact rational arithmetic (`Rational`):

### 8.1 Proof Identities
1. **Vieta Sum:**
   $$z_1 + z_2 = 2a == -\frac{B}{A} \iff 2Aa + B == 0 \text{ in } \mathbb{Q}$$
2. **Vieta Product:**
   $$z_1 \cdot z_2 = a^2 + b^2 d == \frac{C}{A} \iff A(a^2 + b^2 d) - C == 0 \text{ in } \mathbb{Q}$$
3. **Exact Polynomial Residual Real Component:**
   $$\text{Re}(P(z)) = A(a^2 - b^2 d) + Ba + C == 0 \text{ in } \mathbb{Q}$$
4. **Exact Polynomial Residual Imaginary Component:**
   $$\text{Im}(P(z)) = b(2Aa + B) == 0 \text{ in } \mathbb{Q}$$

Host evaluates all four identities strictly in $\mathbb{Q}$. Zero floating-point and zero `complex` numbers are used.

---

## 9. Protocol Version 4 (`mke.p02a.v4`) Envelopes

### 9.1 Request Envelope
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "equation": "x^2 + 2*x + 5 = 0"
}
```

### 9.2 Success Response Envelope (Exact Key Set)
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "outcome": "SUCCESS",
  "status": "TWO_COMPLEX_CONJUGATE_ROOTS",
  "roots": [
    {
      "real_part": {"numerator": "-1", "denominator": "1"},
      "imaginary_coefficient": {"numerator": "-2", "denominator": "1"},
      "radicand": "1"
    },
    {
      "real_part": {"numerator": "-1", "denominator": "1"},
      "imaginary_coefficient": {"numerator": "2", "denominator": "1"},
      "radicand": "1"
    }
  ],
  "discriminant": {"numerator": "-16", "denominator": "1"},
  "radicand": "1",
  "definedness": true,
  "error": null,
  "is_provisional_evidence": true
}
```

### 9.3 Out-Of-Scope Response Envelope ($\Delta \ge 0$)
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "outcome": "OUT_OF_SCOPE",
  "status": "OUT_OF_SCOPE",
  "roots": [],
  "discriminant": {"numerator": "0", "denominator": "1"},
  "radicand": null,
  "definedness": true,
  "error": {
    "code": "ERR_QUADRATIC_COMPLEX_EXPECTED_NEGATIVE_DISCRIMINANT",
    "message": "Discriminant is non-negative; complex solver requires strictly negative discriminant."
  },
  "is_provisional_evidence": false
}
```

### 9.4 Resource-Exhausted Response Envelope
```json
{
  "schema_version": "mke.p02a.v4",
  "operation": "SOLVE_QUADRATIC_COMPLEX",
  "outcome": "RESOURCE_EXHAUSTED",
  "status": "RESOURCE_EXHAUSTED",
  "roots": [],
  "discriminant": null,
  "radicand": null,
  "definedness": true,
  "error": {
    "code": "ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT",
    "message": "Unfactored discriminant remainder exceeds 32-bit certification bound."
  },
  "is_provisional_evidence": false
}
```

### 9.5 Protocol & Infrastructure Error Envelopes
- Protocol syntax errors emit `outcome="PROTOCOL_ERROR"`, `status="PROTOCOL_ERROR"`, `error={"code": "ERR_PROTOCOL_ERROR", ...}`.
- Worker timeout emits `outcome="TIMEOUT"`, `status="WORKER_TIMEOUT"`, `error={"code": "ERR_TIMEOUT", ...}`.
- AppContainer startup failure emits `outcome="ENGINE_ERROR"`, `status="WORKER_STARTUP_FAILURE"`.

---

## 10. Strict B3 Public Models Contract

### 10.1 `ComplexQuadraticRoot`
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

### 10.2 `ComplexControlledDispatchResult`
```python
class ComplexControlledDispatchResult(ControlledDispatchResult):
    """B3-specific outcome model carrying exact complex conjugate roots and strict discriminant."""
    model_config = ConfigDict(extra="forbid")

    verified_complex_roots: List[ComplexQuadraticRoot] = Field(..., description="Exact complex conjugate roots pair [z_minus, z_plus]")
    discriminant: SurdRationalComponent = Field(..., strict=True, description="Strict negative rational discriminant")
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

## 11. Resource Bounds & Product Constants Reconciled

The B3 implementation reuses accepted repository constants unchanged from B2:

| Constant Name | Value | Purpose / Reused From |
| :--- | :--- | :--- |
| `MAX_PAYLOAD_BYTES` | `65536` (64 KB) | Framing limit (reused from B0/B1/B2) |
| `MAX_RESPONSE_BYTES` | `65536` (64 KB) | Framing limit (reused from B0/B1/B2) |
| `MAX_PROTOCOL_CHARS` | `256` | Wire string bounds (reused from B0/B1/B2) |
| `MAX_JSON_DEPTH` | `10` | JSON framing recursion limit |
| `MAX_RATIONAL_BITS` | `256` | Rational numerator / denominator bound |
| `MAX_NORMALIZATION_BITS` | `512` | Working product $M = p \cdot q$ ceiling |
| `MAX_SQUAREFREE_CERTIFICATION_BITS` | `32` ($R < 2^{32}$) | Squarefree certification ceiling |
| `MAX_AST_NODES` | `100` | AST coefficient reduction budget |
| `MAX_AST_DEPTH` | `20` | AST recursion limit |
| `BRIDGE_TOTAL_BUDGET_SEC` | `5.0` s | Aggregate monotonic wall-clock budget |
| `DEFAULT_WORKER_TIMEOUT_SEC` | `10.0` s | WorkerController default timeout |
| `JOB_OBJECT_MAX_PROCESS_MEMORY` | `268,435,456` (256 MB) | Process Job Object limit |
| `JOB_OBJECT_MAX_JOB_MEMORY` | `536,870,912` (512 MB) | Job Object memory limit |

---

## 12. Full Mandatory Adversarial Test Matrix

| # | Test Case Description | Injected Attack / Condition | Expected Result | Layer |
|---|---|---|---|---|
| 1 | Zero roots list | `"roots": []` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 2 | Single root returned | `"roots": [z1]` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 3 | Three roots returned | `"roots": [z1, z2, z2]` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 4 | Duplicate roots | `"roots": [z1, z1]` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 5 | Reversed root order | Positive imaginary first, negative second | Fail Closed (`ERR_SURD_VERIFICATION_MISMATCH` / `ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 6 | Both imaginary positive | $c_1 > 0, c_2 > 0$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 7 | Both imaginary negative | $c_1 < 0, c_2 < 0$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 8 | Mismatched real parts | $a_1 \neq a_2$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 9 | Mismatched imaginary magnitudes | $\|c_1\| \neq c_2$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 10 | Wrong discriminant | Discriminant wire value $\neq \Delta_{\text{host}}$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 11 | Wrong top-level radicand | Top-level radicand $\neq d_{\text{host}}$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 12 | Root vs top-level radicand mismatch | Root $d \neq$ top-level $d$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 13 | Radicand $d = 0$ | `"radicand": "0"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 14 | Negative radicand | `"radicand": "-1"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 15 | Radicand $d \ge 2^{32}$ | `"radicand": str(1 << 32)` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 16 | Non-squarefree radicand ($d=4,8,12$) | Radical with square factors | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 17 | C1 canonical $d=1$ case | $x^2 + 1 = 0 \implies d=1, c=\pm 1$ | Pass (`SUCCESS`, `VERIFIED_COMPLETE`) | End-to-End |
| 18 | Misuse of $d=1$ for C2 equation | Injected $d=1$ for $x^2 + 2 = 0$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 19 | Unreduced rational wire value | `"numerator": "2", "denominator": "4"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 20 | Noncanonical zero | `"numerator": "0", "denominator": "2"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 21 | Denominator $\le 0$ | `"denominator": "-1"` or `"0"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 22 | Leading plus sign | `"numerator": "+1"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 23 | Redundant leading zero | `"numerator": "01"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 24 | 257-bit wire integer | $2^{256}$ in numerator/denominator | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Host Verification |
| 25 | Boolean input in public model | `radicand=True`, `numerator=True` | `ValidationError` raised | Public Model |
| 26 | Float input in public model | `radicand=1.0`, `numerator=1.5` | `ValidationError` raised | Public Model |
| 27 | Missing success field | Omitted `"radicand"` key | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 28 | Extra success field | Injected `"extra": 123` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 29 | Malformed error envelope | Error missing `"code"` | Fail Closed (`ERR_MALFORMED_WORKER_RESPONSE`) | Protocol / Host |
| 30 | Wrong schema version | `"schema_version": "mke.p02a.v99"` | `ProtocolUnsupportedVersionError` | Protocol |
| 31 | Wrong operation string | `"operation": "UNKNOWN"` | `ProtocolUnknownOperationError` | Protocol |
| 32 | v4 operation under v1/v2/v3 | `SOLVE_QUADRATIC_COMPLEX` on v2 | `ProtocolUnknownOperationError` | Protocol |
| 33 | Legacy operation under v4 | `SOLVE` on v4 | `ProtocolUnknownOperationError` | Protocol |
| 34 | Plausible but incorrect pair | Symmetrical pair with wrong values | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 35 | Fake worker success | Worker returns `SUCCESS` for $\Delta > 0$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 36 | Discriminant disagreement | Worker $\Delta \neq$ Host $\Delta$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 37 | Root value disagreement | Worker $z \neq$ Host $z$ | Fail Closed (`ERR_COMPLEX_VERIFICATION_MISMATCH`) | Host Verification |
| 38 | $D = 65537^2$ C1 success | Large rational square root | Pass (`SUCCESS`, $d=1$) | C1 Fast Path |
| 39 | $D = 2 \cdot 65537^2$ bounded failure | Remainder $R \ge 2^{32}$ | Fail Closed (`ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`) | Bounded Normalizer |
| 40 | True 512-bit working product | $p = 2^{256}-1, q = 2^{256}-3$ | Pass 512-bit check, fails on 32-bit $R$ | Normalizer Bound |
| 41 | 257-bit component rejection | $p = 2^{256}$ | Fail Closed (`HostQuadraticSurdResourceLimitError`) | Host Normalizer |
| 42 | Worker hang / timeout | Worker sleeps $> 5.0$s | Fail Closed (`ERR_TIMEOUT`) | Containment |
| 43 | Oversized worker response | Worker emits $> 64$ KB | Fail Closed (`ERR_RESPONSE_LIMIT_EXCEEDED`) | Containment |
| 44 | Windows handle leak check | Repeated worker executions | Zero handle leaks (`handles_end <= handles_start`) | Windows Job Object |

---

## 13. Implementation Staging & Surface Inventory

### 13.1 Staging Plan

```
dfa6d662 (B2-R2 Accepted Closeout)
   │
   ▼
[Stage 1: Protocol v4, Controller Update & Worker Kernel]
   ├── src/mke_product/protocol/schema.py (Defines SCHEMA_VERSION_V4, OPERATION_SOLVE_QUADRATIC_COMPLEX)
   ├── src/mke_product/protocol/validator.py (v4 schema validation)
   ├── src/mke_product/protocol/dispatcher.py (v4 operation routing)
   ├── src/mke_product/protocol/__init__.py
   ├── src/mke_product/worker/controller.py (Add SOLVE_QUADRATIC_COMPLEX to ALLOWED_OPERATIONS)
   ├── src/mke_product/solver/quadratic_complex.py (Pure-Python worker complex solver kernel)
   ├── tests/test_protocol.py (v4 schema matrix)
   └── tests/test_p03c_p1c_quadratic_complex_solver.py (Worker unit tests)
   │
   ▼
[Stage 2: Host Bridge Verification Gate, Public Models & Adversarial Matrix]
   ├── src/mke_product/cas/bridge.py (dispatch_complex, C1 fast path, host proof, ComplexControlledDispatchResult)
   └── tests/test_p03c_p1c_quadratic_complex_dispatch.py (Full 44-test adversarial suite & AppContainer integration)
```

### 13.2 Frozen File Invariants
The following files remain 100% frozen and byte-identical to `0da7ac5157e3f92b7934535b45d38d64a6f0b625`:
- `src/mke_product/worker/entrypoint.py` (Unchanged: routes framed payloads via `protocol/dispatcher.py`)
- `src/mke_product/solver/quadratic.py`
- `src/mke_product/solver/affine.py`
- `src/mke_product/solver/solver.py`
- `src/mke_product/evaluator/evaluator.py`
- `src/mke_product/parser/parser.py`
- `src/mke_product/parser/ast.py`
- `tests/test_worker_windows.py`

---

## 14. Preflight Acceptance Gates Evaluation

| Gate | Criterion | Status | Evaluation |
| :--- | :--- | :--- | :--- |
| **Gate A** | Exact canonical representation | **PASS** | Option B provides proven unique tuple $(a, \pm c, d)$ with $d \ge 1$ squarefree. |
| **Gate B** | No authoritative floats | **PASS** | 100% exact rational arithmetic (`Rational`). |
| **Gate C** | No Python `complex` for proof | **PASS** | Proof decomposed into pure-rational real and imaginary identities over $\mathbb{Q}$. |
| **Gate D** | Deterministic bounded arithmetic | **PASS** | 256-bit component and 512-bit product bounds enforced. |
| **Gate E** | Host verification independent of worker | **PASS** | Host independently derives roots and evaluates Vieta + polynomial residual identities. |
| **Gate F** | No mutation of v1/v2/v3 contracts | **PASS** | Dedicated schema `mke.p02a.v4` and operation `SOLVE_QUADRATIC_COMPLEX`. |
| **Gate G** | No silent change to legacy B1 semantics | **PASS** | `dispatch()` continues to return `solution_type="NO_REAL_ROOT"` for $\Delta < 0$. |
| **Gate H** | Exact conjugate root verification | **PASS** | Symmetry and sign invariants strictly validated by host and Pydantic models. |
| **Gate I** | Resource limits remain fail-closed | **PASS** | Remainder $R \ge 2^{32}$ fails closed with `ERR_COMPLEX_NORMALIZATION_RESOURCE_LIMIT`. |
| **Gate J** | Windows containment unaffected | **PASS** | AppContainer and Job Object containment 100% active. |
| **Gate K** | Adversarial matrix is explicit | **PASS** | 44-row comprehensive attack matrix specified. |
| **Gate L** | Staged, auditable implementation plan | **PASS** | Exactly two auditable implementation commits defined. |

---

## 15. Explicit Deferred Capabilities

The following capabilities remain explicitly **OUT OF SCOPE** for B3:
- Cubic, quartic, or general polynomial solving.
- Nested radicals.
- Arbitrary degree algebraic extension fields.
- Transcendental complex equations ($e^{iz} = 1$, $\sin(z) = 0$).
- Arbitrary large integer prime factorization.
- Approximate or numerical complex solving.
- Branch-cut dependent complex functions.

---

## 16. Final Recommendation

**RECOMMENDATION:** **`GO BOUNDED`**

The remediated technical specification for PRODUCT-03C-P1C-04-B3 is complete, mathematically sound, strictly backward-compatible, and ready for Coordinator / Independent Auditor review.
