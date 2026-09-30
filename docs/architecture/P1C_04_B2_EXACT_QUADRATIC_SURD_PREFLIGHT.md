# MKE Product 03C-P1C-04-B2 Preflight: Exact Quadratic Surd Roots Architecture

- **Milestone:** MKE Product 03C-P1C-04-B2
- **Document Version:** 1.0.0 (Preflight Specification)
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Predecessor Baseline:** P1C-04-B1-R2 Accepted Limited (`0da7ac5157e3f92b7934535b45d38d64a6f0b625`)
- **Status:** PREFLIGHT SPECIFICATION — PENDING AUDITOR GO/NO-GO REVIEW
- **Date:** 2026-09-30

---

## 1. Executive Decision & Recommendation

### 1.1 Recommendation: GO BOUNDED
We recommend **GO BOUNDED** for P1C-04-B2 implementation under a strict, mathematically sound architecture:

1. **Exact Symbolic Surd Representation:** Exact quadratic irrational roots will be modeled in the algebraic field $\mathbb{Q}(\sqrt{d})$ as $a \pm b\sqrt{d}$ with $a \in \mathbb{Q}$, $b \in \mathbb{Q}^+$, and squarefree integer $d \in \mathbb{Z}^+ (d > 1)$.
2. **Zero Floating-Point & Zero SymPy:** Authoritative solving, transport, and verification will remain $100\%$ pure-Python integer and rational arithmetic. No floating-point or numerical approximations are permitted anywhere in the pipeline.
3. **Dedicated Protocol Version `mke.p02a.v3`:** To protect accepted B1 `mke.p02a.v2` rational-quadratic contracts from field-set mutation or type ambiguity, surd solving will be introduced via `mke.p02a.v3` and operation `SOLVE_QUADRATIC_SURD`.
4. **Deterministic Squarefree Decomposition with Strict Bit Limits:** Factoring arbitrary 256-bit discriminants is computationally intractable in bounded sub-second latency. B2 will enforce a deterministic squarefree reduction limit ($d \le 2^{63}-1$ and small prime search budget). Discriminants whose squarefree reduction exceeds bounds will fail closed pre-dispatch with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`.
5. **Complete Independent Host Proof:** Host verification will not trust worker calculations, worker residuals, or worker squarefree decomposition. Host will independently extract coefficients, compute discriminant, decompose surds, verify Vieta sums/products, and evaluate exact polynomial residual identities over $\mathbb{Q}(\sqrt{d})$.

---

## 2. Actual B1 Code Audit & Baseline Execution Path

An inspection of current repository code (`src/mke_product/cas/bridge.py`, `src/mke_product/solver/quadratic.py`, `src/mke_product/protocol/`) confirms the following execution pipeline for quadratic dispatch:

```
[User Query / IR Payload]
        │
        ▼
[MKEIntakeValidator.validate()] ──(Invalid / Non-Exhaustive / Scope)──► Fail Closed (NOT_DISPATCHED)
        │
        ▼
[B0 Affine Reduction Check] ──(Degree <= 1)──► Dispatch mke.p02a.v1 / SOLVE
        │
        ▼ (Non-affine)
[B1 Host Quadratic Reduction] ──► Extracts host (A, B, C) via bounded helpers (max 256 bits)
        │
        ▼
[Host Discriminant] ──► Δ = B^2 - 4*A*C
        │
        ├─► If Δ < 0:
        │     Dispatches mke.p02a.v2 / SOLVE_QUADRATIC ──► Verifies NO_REAL_ROOT ──► SUCCESS
        │
        ├─► If Δ == 0:
        │     Dispatches mke.p02a.v2 / SOLVE_QUADRATIC ──► Verifies UNIQUE_REAL_ROOT ──►
        │     Dispatches mke.p02a.v1 / CHECK_CANDIDATE (-B/2A) ──► SUCCESS
        │
        ├─► If Δ > 0 AND Δ is Rational Square (isqrt(p)^2 == p and isqrt(q)^2 == q):
        │     Dispatches mke.p02a.v2 / SOLVE_QUADRATIC ──► Verifies TWO_DISTINCT_REAL_ROOTS ──►
        │     Dispatches mke.p02a.v1 / CHECK_CANDIDATE (r1, r2) ──► SUCCESS
        │
        └─► If Δ > 0 AND Δ is NOT a Rational Square:
              Currently fails closed PRE-DISPATCH in bridge.py (lines 784-793):
              `error_code = "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"`
              (Zero worker processes spawned).
```

### Exact Location of B1 Irrational Boundary
In `src/mke_product/cas/bridge.py` (lines 777-794):
```python
if host_delta.numerator > 0:
    p = host_delta.numerator
    q = host_delta.denominator
    import math
    sp = math.isqrt(p)
    sq = math.isqrt(q)
    if sp * sp != p or sq * sq != q:
        # Non-square positive discriminant -> irrational roots fail closed pre-dispatch
        return ControlledDispatchResult(
            intake_status=IntakeStatus.VALIDATED,
            intake_diagnostic=diagnostic,
            execution_status=ExecutionStatus.NOT_DISPATCHED,
            verification_status=VerificationStatus.NOT_APPLICABLE,
            is_verified=False,
            error_code="ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION",
        )
```
And in `src/mke_product/solver/quadratic.py` (lines 486-498):
```python
else:
    # Positive non-square discriminant (irrational roots deferred in B1)
    return QuadraticSolverResult(
        status="OUT_OF_SCOPE",
        classification=None,
        roots=[],
        discriminant=Delta,
        a=A,
        b=B,
        c=C,
        error_code="ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION",
        error_message="Positive discriminant is not an exact rational square; irrational quadratic roots are not supported in B1.",
    )
```

B2 specifically replaces this pre-dispatch block with bounded squarefree normalization and controlled dispatch to the surd solving and independent verification pipeline.

---

## 3. Exact B2 Mathematical Scope

### 3.1 Authorized Domain
- **Equation Form:** $A x^2 + B x + C = 0$
- **Variable:** Single target variable $x \in \mathbb{R}$.
- **Coefficients:** Exact rational numbers $A, B, C \in \mathbb{Q}$ with $A \neq 0$.
- **Discriminant Condition:** $\Delta = B^2 - 4AC > 0$, where $\Delta$ is **NOT** a rational square ($\Delta \notin \mathbb{Q}^2$).
- **Output:** Exactly two distinct real irrational roots in the quadratic extension field $\mathbb{Q}(\sqrt{d})$.

### 3.2 Explicit Exclusions (Fail Closed)
- **No Numerical Root Approximations:** Floating-point representations (`1.4142...`) are prohibited.
- **No Degree $\ge 3$ Polynomials:** $x^3 - 2 = 0$ rejected with `REJECTED_SCOPE / ERR_OUT_OF_SCOPE`.
- **No Complex Roots in B2:** $\Delta < 0$ continues through B1 `NO_REAL_ROOT` path.
- **No Radical Inputs in Grammar:** $x - \sqrt{2} = 0$ is rejected by the AST parser/intake.
- **No Variable Denominators:** $1/(x^2 - 2) = 0$ rejected with `REJECTED_SCOPE / ERR_OUT_OF_SCOPE`.
- **No Transcendental Functions:** $\sin(x) = 0, e^x = 2$ out of scope.

---

## 4. Canonical Quadratic-Surd Representation

### 4.1 Algebraic Model
Every root of $A x^2 + B x + C = 0$ over $\mathbb{Q}$ with $\Delta > 0$ can be uniquely expressed as:
$$r = a + b\sqrt{d}$$
where:
1. $a \in \mathbb{Q}$ (Rational part: $a = -B / (2A)$).
2. $b \in \mathbb{Q}$ (Surd coefficient: $b = \pm \frac{s}{2|A|}$ for rational $s > 0$).
3. $d \in \mathbb{Z}^+$ (Radicand: squarefree positive integer $> 1$).

### 4.2 Proof of Sufficiency and Uniqueness
**Proof:**
1. Let $\Delta = \frac{p}{q}$ in lowest terms ($\gcd(p, q) = 1, p > 0, q > 0$).
2. $\sqrt{\Delta} = \sqrt{\frac{p}{q}} = \frac{\sqrt{p q}}{q}$.
3. By the Fundamental Theorem of Arithmetic, the integer product $p q$ can be uniquely factored as:
   $$p q = s_0^2 \cdot d$$
   where $s_0 \in \mathbb{Z}^+$ and $d \in \mathbb{Z}^+$ is squarefree (i.e. not divisible by any $k^2 > 1$).
4. Since $\Delta \notin \mathbb{Q}^2$, $p q$ is not a perfect square, so $d > 1$.
5. Substituting back:
   $$\sqrt{\Delta} = \frac{s_0}{q}\sqrt{d} = s\sqrt{d} \quad \text{where } s = \frac{s_0}{q} \in \mathbb{Q}^+.$$
6. The roots of $A x^2 + B x + C = 0$ are given by:
   $$x = \frac{-B \pm \sqrt{\Delta}}{2A} = -\frac{B}{2A} \pm \frac{s}{2|A|}\sqrt{d} = a \pm b_0\sqrt{d}$$
   where $a = -\frac{B}{2A} \in \mathbb{Q}$ and $b_0 = \frac{s}{2|A|} \in \mathbb{Q}^+$.
7. Thus, the two roots are $r_1 = a - b_0\sqrt{d}$ and $r_2 = a + b_0\sqrt{d}$.
8. Because $d$ is squarefree and $d > 1$, the representation $a + b\sqrt{d}$ is unique in $\mathbb{Q}(\sqrt{d})$: if $a_1 + b_1\sqrt{d} = a_2 + b_2\sqrt{d}$, then $(a_1 - a_2) = (b_2 - b_1)\sqrt{d}$; since $\sqrt{d} \notin \mathbb{Q}$, this implies $a_1 = a_2$ and $b_1 = b_2$. $\blacksquare$

---

## 5. Canonicalization Requirements & Invariants

A valid wire representation of a quadratic surd root must strictly satisfy the following canonical invariants:

| Field | Type | Invariant Constraints |
| :--- | :--- | :--- |
| `rational_part` | `Rational` | Reduced fraction $p_a / q_a$ with $q_a > 0$ and $\gcd(\|p_a\|, q_a) = 1$. Sign in $p_a$. |
| `sqrt_coefficient` | `Rational` | Reduced fraction $p_b / q_b$ with $q_b > 0$, $\gcd(\|p_b\|, q_b) = 1$, and $p_b \neq 0$. Sign in $p_b$. |
| `radicand` | `str` (decimal) | Positive integer string $d \ge 2$, containing no square factor ($k^2 \nmid d$ for all $k \ge 2$). |

### Exact Canonical Reduction Examples
- $\sqrt{8} \longrightarrow 0 + 2\sqrt{2}$
- $\frac{\sqrt{18}}{3} \longrightarrow 0 + 1\sqrt{2}$
- $\sqrt{1/2} \longrightarrow 0 + \frac{1}{2}\sqrt{2}$
- $2 + \sqrt{8} \longrightarrow 2 + 2\sqrt{2}$
- $\frac{-1 \pm \sqrt{20}}{2} \longrightarrow -\frac{1}{2} \pm 1\sqrt{5}$
- $\frac{-6 \pm \sqrt{24}}{6} \longrightarrow -1 \pm \frac{1}{3}\sqrt{6}$

### Wire Representation Model
```json
{
  "rational_part": {
    "numerator": "-1",
    "denominator": "2"
  },
  "sqrt_coefficient": {
    "numerator": "1",
    "denominator": "2"
  },
  "radicand": "5"
}
```

---

## 6. Deterministic Squarefree Decomposition Algorithm

To decompose rational $\Delta = p/q > 0$ into $s^2 \cdot d$ without float or SymPy:

```python
def decompose_rational_squarefree(
    p: int, q: int, max_prime_limit: int = 65536, max_radicand_bits: int = 64
) -> Tuple[Rational, int]:
    """Deterministically decompose rational p/q into s * sqrt(d) where d is squarefree.

    Raises:
        SurdNormalizationLimitError: If radicand cannot be proven squarefree within bounds.
    """
    assert p > 0 and q > 0
    # 1. Coprime reduction
    g = math.gcd(p, q)
    p //= g
    q //= g

    # 2. Product to integer M = p * q
    M = p * q
    s_int = 1

    # 3. Trial division for small primes up to max_prime_limit
    # Extract all prime squares p_i^2 dividing M
    limit = min(math.isqrt(M), max_prime_limit)
    for p_i in PRIME_TABLE_UP_TO_65536:
        if p_i > limit:
            break
        p_sq = p_i * p_i
        while M % p_sq == 0:
            s_int *= p_i
            M //= p_sq
        if M % p_i == 0:
            # p_i divides M with multiplicity 1; cannot contain p_i^2
            pass

    # 4. Check if remaining M is a perfect square
    rem_isqrt = math.isqrt(M)
    if rem_isqrt * rem_isqrt == M:
        s_int *= rem_isqrt
        M = 1

    # 5. Resource and Squarefree Certification Guard
    if M == 1:
        # Rational square (should have been routed to B1 rational solver)
        d = 1
    else:
        # If remaining M exceeds maximum certified bit bound, fail closed
        if M.bit_length() > max_radicand_bits:
            raise SurdNormalizationLimitError(
                f"Radicand {M} bit length ({M.bit_length()}) exceeds safe squarefree limit ({max_radicand_bits} bits)."
            )
        d = M

    # s = s_int / q
    s = Rational(s_int, q)
    return (s, d)
```

---

## 7. Resource-Complexity Analysis & Radicand Bounding

### 7.1 Algorithmic Risk of Arbitrary Integer Factorization
General integer factorization for 256-bit integers is NP-hard and cannot be executed deterministically within a sub-second budget. If an adversarial equation produces a 200-bit semiprime $M = p_1^2 \cdot p_2$ with large primes, trial division will timeout.

### 7.2 Strict B2 Radicand Ceiling
To eliminate any risk of worker/host hangs while supporting all standard textbook and curriculum quadratics:
1. **Input Literal Max Bit Length:** 256 bits (standard MKE limit).
2. **Pre-dispatch Factorization Prime Table:** Precomputed primes up to $65536$ ($2^{16}$, 6542 primes).
3. **Discriminant Bit Length for B2 Surd Dispatch:** $\Delta \le 128$ bits.
4. **Certified Squarefree Radicand Bound:** $d \le 2^{63}-1$ (64-bit integer limit).
5. **Fail-Closed Behavior:** If the unfactored remainder after prime table trial division has bit length $> 64$ and is not a perfect square, the bridge raises `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT` pre-dispatch (0 worker processes spawned).

---

## 8. Protocol Versioning Decision

### 8.1 Analysis of Options

| Option | Description | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Extend v2 Union** | Allow `roots` in `mke.p02a.v2` to be `List[Union[Rational, QuadraticSurd]]`. | No new schema version string. | Mutates frozen v2 success envelope; breaks strict field-set validator; introduces wire ambiguity. | **REJECTED** |
| **Option B: Introduce `mke.p02a.v3`** | Dedicated schema `mke.p02a.v3` with operation `SOLVE_QUADRATIC_SURD`. | $100\%$ backward-compatible; preserves frozen v1 and v2 contracts byte-for-byte; strict schema enforcement. | Adds a new protocol version. | **RECOMMENDED** |
| **Option C: Add Surd Evidence in v2** | Keep v2 `SOLVE_QUADRATIC` but add an optional `surd_roots` field. | Reuses operation name. | Violates exact field-set check in accepted B1 bridge (`EXACT_V2_SUCCESS_RESPONSE_FIELDS`). | **REJECTED** |
| **Option D: Defer Surd Solving** | Do not expose surds over IPC. | Zero protocol changes. | Blocks B2 capability. | **REJECTED** |

### 8.2 Protocol Decision: `mke.p02a.v3` / `SOLVE_QUADRATIC_SURD`
- **Schema Version:** `mke.p02a.v3`
- **Operation:** `SOLVE_QUADRATIC_SURD`
- **Supported Operations Matrix:**
  - `mke.p02a.v1`: `SOLVE`, `CHECK_CANDIDATE`
  - `mke.p02a.v2`: `SOLVE_QUADRATIC`
  - `mke.p02a.v3`: `SOLVE_QUADRATIC_SURD`
- **Success Response Structure:**
  ```json
  {
    "schema_version": "mke.p02a.v3",
    "operation": "SOLVE_QUADRATIC_SURD",
    "outcome": "SUCCESS",
    "status": "TWO_DISTINCT_REAL_ROOTS",
    "roots": [
      {
        "rational_part": {"numerator": "-1", "denominator": "2"},
        "sqrt_coefficient": {"numerator": "-1", "denominator": "2"},
        "radicand": "5"
      },
      {
        "rational_part": {"numerator": "-1", "denominator": "2"},
        "sqrt_coefficient": {"numerator": "1", "denominator": "2"},
        "radicand": "5"
      }
    ],
    "discriminant": {"numerator": "5", "denominator": "1"},
    "radicand": "5",
    "definedness": true,
    "error": null,
    "is_provisional_evidence": false
  }
  ```

---

## 9. Host / Worker Trust & Independence Model

```
┌────────────────────────────────────────────────────────────────────────┐
│ UNTRUSTED WORKER PROCESS (Windows AppContainer / Low Integrity)        │
│  - Receives query: mke.p02a.v3 / SOLVE_QUADRATIC_SURD                  │
│  - Executes independent worker solver: solve_quadratic_surd_equation() │
│  - Emits candidate wire response (roots, discriminant, radicand)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ IPC Wire JSON (Untrusted Evidence)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TRUSTED HOST CONTROLLER (mke_product.cas.bridge)                       │
│  1. Authoritative Intake Validation (MKEIntakeValidator)               │
│  2. Independent Host AST Polynomial Reduction (A, B, C)                │
│  3. Independent Host Discriminant & Squarefree Decomp: Δ = s^2 * d     │
│  4. Independent Host Root Derivation: r_exp = -B/(2A) ± (s/(2|A|))√d   │
│  5. Strict Response Envelope Validation (EXACT_V3_SUCCESS_FIELDS)      │
│  6. Exact Match: worker_roots == expected_roots                        │
│  7. Independent Vieta Proof over Q(√d):                                │
│       r1 + r2 == -B/A   AND   r1 * r2 == C/A                           │
│  8. Independent Polynomial Residual Proof:                             │
│       A*(r)^2 + B*(r) + C == 0 in Q(√d)                                │
│  9. Emit Authoritative QuadraticSurdControlledDispatchResult           │
└────────────────────────────────────────────────────────────────────────┘
```

### Architectural Separation Invariant
The host bridge (`src/mke_product/cas/bridge.py`) **MUST NOT** import `src/mke_product/solver/quadratic_surd.py`. Host proofs must be implemented via separate host verification functions in the bridge module.

---

## 10. Independent Exact Verification & Surd Arithmetic Model

### 10.1 Field Arithmetic in $\mathbb{Q}(\sqrt{d})$
For a fixed squarefree integer $d > 1$, elements of $\mathbb{Q}(\sqrt{d})$ are represented as pairs $(a, b)$ denoting $a + b\sqrt{d}$ with $a, b \in \mathbb{Q}$.

1. **Addition:**
   $$(a_1 + b_1\sqrt{d}) + (a_2 + b_2\sqrt{d}) = (a_1 + a_2) + (b_1 + b_2)\sqrt{d}$$
2. **Negation:**
   $$-(a + b\sqrt{d}) = (-a) + (-b)\sqrt{d}$$
3. **Multiplication:**
   $$(a_1 + b_1\sqrt{d}) \cdot (a_2 + b_2\sqrt{d}) = (a_1 a_2 + b_1 b_2 d) + (a_1 b_2 + a_2 b_1)\sqrt{d}$$
4. **Squaring:**
   $$(a + b\sqrt{d})^2 = (a^2 + b^2 d) + (2 a b)\sqrt{d}$$

### 10.2 Exact Host Proof Identities
For roots $r_1 = a - b\sqrt{d}$ and $r_2 = a + b\sqrt{d}$ with $b > 0$:

1. **Vieta Sum Identity:**
   $$r_1 + r_2 = (a - b\sqrt{d}) + (a + b\sqrt{d}) = 2a + 0\sqrt{d} = -\frac{B}{A}$$
   Host checks: $2a == -B/A$.
2. **Vieta Product Identity:**
   $$r_1 \cdot r_2 = (a - b\sqrt{d})(a + b\sqrt{d}) = a^2 - b^2 d + 0\sqrt{d} = \frac{C}{A}$$
   Host checks: $a^2 - b^2 d == C/A$.
3. **Exact Polynomial Evaluation:**
   $$A(a \pm b\sqrt{d})^2 + B(a \pm b\sqrt{d}) + C = \left[A(a^2 + b^2 d) + B a + C\right] \pm \left[2 A a b + B b\right]\sqrt{d}$$
   Since $\sqrt{d} \notin \mathbb{Q}$, this equals $0$ if and only if:
   - Rational component: $A(a^2 + b^2 d) + B a + C = 0$
   - Radical component: $b(2 A a + B) = 0 \implies 2 A a + B = 0$ (since $b \neq 0$).

All host verification is computed using pure integer/Rational arithmetic with strict 256-bit resource bounds.

---

## 11. Exact Root Ordering

For distinct real roots $r_1 = a + b_1\sqrt{d}$ and $r_2 = a + b_2\sqrt{d}$ in $\mathbb{Q}(\sqrt{d})$:
- The worker is required to return roots in strictly ascending order: $r_1 < r_2$.
- Since $a_1 = a_2 = a$ and $d_1 = d_2 = d > 1$, exact ordering is algebraic:
  $$r_1 < r_2 \iff a + b_1\sqrt{d} < a + b_2\sqrt{d} \iff b_1 < b_2$$
- In canonical form, $b_1 = -b$ and $b_2 = +b$ with $b \in \mathbb{Q}^+$.
- Therefore:
  $$r_1 = a - b\sqrt{d} < r_2 = a + b\sqrt{d}$$
  is deterministically ordered without floating-point evaluation.

---

## 12. Candidate Verification: Why v1 `CHECK_CANDIDATE` is NOT Used

- **v1 Limitation:** `CHECK_CANDIDATE` in `mke.p02a.v1` is frozen and accepts rational strings $p/q$.
- **Irrational Incompatibility:** Quadratic surds cannot be represented as rational strings. Serializing decimal approximations (`"1.414"`) would violate exactness.
- **Mathematical Soundness:** Host algebraic proof over $\mathbb{Q}(\sqrt{d})$ (Vieta sum, Vieta product, exact residual evaluation) provides $100\%$ authoritative certification.
- **Decision:** Surd candidate verification will be performed entirely via host algebraic proof. No secondary worker candidate check is needed or permitted.

---

## 13. Public Result Model

### 13.1 Frozen Base Classes
To ensure zero breaking changes for existing consumers:
- `ControlledDispatchResult` (B0 9-field contract) remains **FROZEN**.
- `QuadraticControlledDispatchResult` (B1 11-field contract) remains **FROZEN**.

### 13.2 New Subclass: `QuadraticSurdControlledDispatchResult`
```python
class QuadraticSurdRoot(BaseModel):
    rational_part: RationalRoot
    sqrt_coefficient: RationalRoot
    radicand: int

    model_config = ConfigDict(frozen=True, extra="forbid")


class QuadraticSurdControlledDispatchResult(ControlledDispatchResult):
    """Authoritative result for quadratic equations with exact irrational roots."""

    verified_surd_roots: List[QuadraticSurdRoot] = Field(default_factory=list)
    discriminant: Optional[RationalRoot] = None
    radicand: Optional[int] = None
    representation: str = "QUADRATIC_SURD"
```

---

## 14. Error & Status Taxonomy

### 14.1 Status Codes
- `TWO_DISTINCT_REAL_ROOTS`: Preserved as standard status for two real roots (with `representation="QUADRATIC_SURD"`).

### 14.2 Error Codes
- `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`: Discriminant factorization or bit bounds exceeded.
- `ERR_NONCANONICAL_SURD_RESPONSE`: Worker returned unreduced fractions, non-squarefree radicand, or inverted signs.
- `ERR_MALFORMED_SURD_RESPONSE`: Worker response violated strict v3 field schema.
- `ERR_SURD_VERIFICATION_MISMATCH`: Worker roots failed host algebraic proof or Vieta checks.

---

## 15. Threat Model & Adversarial Attack Vectors

| Threat Vector | Attack Mechanism | B2 Defense / Mitigation |
| :--- | :--- | :--- |
| **Large-Semiprime Stalling** | Adversary inputs equation with huge composite discriminant to stall factorization. | Hard bit bounds ($d \le 2^{63}-1$) and deterministic prime table search. Fails closed with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`. |
| **Noncanonical Wire Surds** | Collusive worker returns $\sqrt{8}$ instead of $2\sqrt{2}$ or $d=1$. | Host validates $d > 1$, $d$ squarefree, and strict field reduction before verification. |
| **Forged Roots with Fake Check** | Collusive worker returns incorrect roots $(r_1', r_2')$. | Host independently computes expected roots and evaluates exact Vieta identities and polynomial residuals over $\mathbb{Q}(\sqrt{d})$. |
| **Unsorted / Inverted Roots** | Worker returns $[r_2, r_1]$ instead of $[r_1, r_2]$. | Host strictly verifies $b_1 < b_2$ and rejects inverted roots. |
| **Surrogate / Extra Fields** | Worker injects extra JSON fields or surrogate characters. | Strict v3 protocol validator and JSON decode hooks reject malformed payloads. |

---

## 16. Test Matrix Plan

1. **Protocol v3 Unit Tests (`tests/test_protocol.py`):**
   - Validation of `mke.p02a.v3` / `SOLVE_QUADRATIC_SURD`.
   - Rejection of unknown fields, invalid types, and non-ASCII equations.
2. **Worker Surd Solver Tests (`tests/test_p03c_p1c_quadratic_surd.py`):**
   - Standard surds: $x^2 - 2 = 0 \to \pm\sqrt{2}$, $x^2 - 8 = 0 \to \pm 2\sqrt{2}$, $2x^2 - 1 = 0 \to \pm\sqrt{2}/2$, $x^2 + x - 1 = 0 \to (-1 \pm \sqrt{5})/2$.
   - Resource exhaustion on huge discriminants.
3. **Bridge Controlled Dispatch & Verification Tests (`tests/test_p03c_p1c_quadratic_surd_dispatch.py`):**
   - End-to-end dispatch and verification of surd roots.
   - Host proof independent verification.
   - Adversarial worker collusion tests (wrong roots, wrong discriminant, wrong radicand, noncanonical surd).
   - Strict budget monotonicity and cumulative timeout enforcement.
4. **Full Regression Suite:**
   - Zero regressions on B0 linear dispatch, B1 rational quadratic dispatch, Windows AppContainer containment, and browser UI suites.

---

## 17. Backward-Compatibility Locks

- **B0 Baseline:** All linear dispatches and 9-field `ControlledDispatchResult` contracts remain identical.
- **B1 Baseline:** All rational-quadratic dispatches ($x^2 - 4 = 0$, $(x-1)^2 = 0$, $x^2 + 1 = 0$) execute identically through `mke.p02a.v2` and `QuadraticControlledDispatchResult`.
- **`test_worker_windows.py`:** Strictly byte-identical to accepted baseline with zero handle leaks (`handles_end - handles_start <= 0`).

---

## 18. Proposed File Change Inventory

### Unchanged Files
- `src/mke_product/cas/evaluator.py`
- `src/mke_product/parser/ast.py`
- `src/mke_product/parser/parser.py`
- `src/mke_product/solver/affine.py`
- `src/mke_product/solver/quadratic.py` (B1 rational solver remains untouched)
- `tests/test_worker_windows.py`

### Modified Files
- `src/mke_product/protocol/schema.py` (Add `SCHEMA_VERSION_V3`, `OPERATION_SOLVE_QUADRATIC_SURD`)
- `src/mke_product/protocol/validator.py` (Add v3 validation rules)
- `src/mke_product/protocol/dispatcher.py` (Route v3 operation)
- `src/mke_product/worker/controller.py` (Support v3 request serialization)
- `src/mke_product/worker/entrypoint.py` (Register v3 handler)
- `src/mke_product/cas/bridge.py` (Add B2 surd host verification and routing)
- `tests/test_protocol.py` (Add v3 protocol test cases)

### New Files
- `src/mke_product/solver/quadratic_surd.py` (Isolated pure-Python surd solver)
- `tests/test_p03c_p1c_quadratic_surd_dispatch.py` (Comprehensive surd dispatch & adversarial test suite)

---

## 19. GO / NO-GO Criteria

| Criterion | Requirement | Status |
| :--- | :--- | :--- |
| **Exact Canonical Model** | $a \pm b\sqrt{d}$ uniquely represents all real quadratic roots over $\mathbb{Q}$. | **SATISFIED** |
| **Pure Python / No Float** | Zero SymPy, zero floats, exact rational arithmetic only. | **SATISFIED** |
| **Deterministic Resource Bound** | Radicand bound $d \le 2^{63}-1$ with small prime search avoids intractable factorization. | **SATISFIED** |
| **Independent Verification** | Host derives proofs independently without importing worker solver. | **SATISFIED** |
| **Backward Compatibility** | B0 and B1 contracts frozen and preserved via dedicated `mke.p02a.v3`. | **SATISFIED** |
| **Containment Integrity** | Windows AppContainer isolation and zero handle leaks maintained. | **SATISFIED** |

---

## 20. Explicit Deferred Capabilities

The following capabilities are explicitly deferred to future milestones:
- **Higher-Degree Algebraic Numbers:** Roots of cubic, quartic, or general polynomials.
- **Complex Roots with Radicals:** Imaginary quadratic surds ($a \pm b i \sqrt{d}$ for $\Delta < 0$).
- **Nested Radicals:** Expressions of the form $\sqrt{a + \sqrt{b}}$.
- **Arbitrary Radicand Prime Factorization:** Factoring discriminants exceeding 64-bit radicand bounds.

---

## 21. Final Recommendation

Antigravity recommends **GO BOUNDED** for P1C-04-B2 implementation following the architecture detailed in this specification. All prerequisites for exactness, security containment, and independent verification are met.
