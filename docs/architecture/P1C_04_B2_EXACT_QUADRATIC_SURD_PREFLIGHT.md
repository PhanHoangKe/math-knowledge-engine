# MKE Product 03C-P1C-04-B2 Preflight: Exact Quadratic Surd Roots Architecture (R1 Revision)

- **Milestone:** MKE Product 03C-P1C-04-B2
- **Document Version:** 1.1.0 (R1 Preflight Specification)
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Predecessor Baseline:** P1C-04-B1-R2 Accepted Limited (`0da7ac5157e3f92b7934535b45d38d64a6f0b625`)
- **Parent Preflight Commit:** `65f66a5ef725afde3197f69d11d096d726151069`
- **Status:** PREFLIGHT SPECIFICATION — PENDING AUDITOR GO/NO-GO REVIEW
- **Date:** 2026-09-30

---

## 1. Executive Decision & Recommendation

### 1.1 Recommendation: GO BOUNDED
We recommend **GO BOUNDED** for P1C-04-B2 implementation under a rigorous, mathematically certified architecture:

1. **Exact Symbolic Surd Representation:** Exact quadratic irrational roots are represented strictly in the quadratic extension field $\mathbb{Q}(\sqrt{d})$ as $a \pm b\sqrt{d}$ with $a \in \mathbb{Q}$, $b \in \mathbb{Q}^+$, and squarefree integer $d \in \mathbb{Z}^+ (2 \le d < 2^{32})$.
2. **Zero Floating-Point & Zero SymPy:** Authoritative reduction, solving, transport, and independent verification remain $100\%$ pure-Python integer and rational arithmetic. No floating-point or numerical approximations are permitted anywhere in the pipeline.
3. **Dedicated Protocol Version `mke.p02a.v3`:** To protect frozen B1 `mke.p02a.v2` rational-quadratic contracts from field-set mutation or type ambiguity, surd solving is introduced via dedicated schema `mke.p02a.v3` and operation `SOLVE_QUADRATIC_SURD`.
4. **Certified Squarefree Normalization ($R < 2^{32}$ via $P \le 65536$ Prime Trial Division):** Factoring arbitrary large integers is computationally difficult classically and no deterministic polynomial-time classical algorithm is known; arbitrary large-integer factorization is therefore unsuitable for bounded-latency containment. B2 enforces a deterministic squarefree certification contract:
   - Full trial division extraction of prime squares $p_i^2$ for all primes $p_i \le 65536$ ($2^{16}$).
   - Strict 32-bit ceiling on the final unfactored remainder: $R < 2^{32}$ ($R.\text{bit\_length}() \le 32$).
   - Any remainder $R$ exceeding 32 bits after small prime square extraction fails closed pre-dispatch with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT` (zero worker processes spawned).
5. **Complete Independent Host Proof:** Host verification does not trust worker calculations, worker residuals, or worker squarefree decomposition. Host independently extracts coefficients, computes discriminant, certifies squarefree decomposition, verifies Vieta identities, and evaluates exact polynomial residual identities over $\mathbb{Q}(\sqrt{d})$.
6. **Worker Entrypoint Frozen:** `src/mke_product/worker/entrypoint.py` remains 100% frozen; protocol dispatch is handled entirely in `protocol/dispatcher.py`.

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

B2 specifically replaces this pre-dispatch block with certified squarefree normalization and controlled dispatch to the surd solving and independent verification pipeline.

---

## 3. Exact B2 Mathematical Scope

### 3.1 Authorized Domain
- **Equation Form:** $A x^2 + B x + C = 0$
- **Variable:** Single target variable $x \in \mathbb{R}$.
- **Coefficients:** Exact rational numbers $A, B, C \in \mathbb{Q}$ with $A \neq 0$.
- **Discriminant Condition:** $\Delta = B^2 - 4AC > 0$, where $\Delta$ is **NOT** a rational square ($\Delta \notin \mathbb{Q}^2$).
- **Squarefree Remainder Condition:** Normalization of $\Delta$ yields a certified squarefree radicand $d$ with $d < 2^{32}$.
- **Output:** Exactly two distinct real irrational roots in the quadratic extension field $\mathbb{Q}(\sqrt{d})$.

### 3.2 Explicit Exclusions (Fail Closed)
- **No Numerical Root Approximations:** Floating-point representations (`1.4142...`) are strictly prohibited.
- **No Degree $\ge 3$ Polynomials:** $x^3 - 2 = 0$ rejected with `REJECTED_SCOPE / ERR_OUT_OF_SCOPE`.
- **No Complex Roots in B2:** $\Delta < 0$ continues through B1 `NO_REAL_ROOT` path.
- **No Radical Inputs in Grammar:** $x - \sqrt{2} = 0$ is rejected by the AST parser/intake.
- **No Variable Denominators:** $1/(x^2 - 2) = 0$ rejected with `REJECTED_SCOPE / ERR_OUT_OF_SCOPE`.
- **No Transcendental Functions:** $\sin(x) = 0, e^x = 2$ out of scope.
- **No Uncertified Large-Radicand Composites:** Discriminants whose unfactored remainder after prime table extraction exceeds 32 bits fail closed with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`.

---

## 4. Canonical Quadratic-Surd Representation

### 4.1 Algebraic Model
Every root of $A x^2 + B x + C = 0$ over $\mathbb{Q}$ with $\Delta > 0$ can be uniquely expressed as:
$$r = a + b\sqrt{d}$$
where:
1. $a \in \mathbb{Q}$ (Rational part: $a = -B / (2A)$).
2. $b \in \mathbb{Q}$ (Surd coefficient: $b = \pm \frac{s}{2|A|}$ for rational $s > 0$).
3. $d \in \mathbb{Z}^+$ (Radicand: squarefree positive integer, $2 \le d < 2^{32}$).

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
| `radicand` | `str` (decimal) | Positive integer string $d \ge 2, d < 2^{32}$, containing no square factor ($k^2 \nmid d$ for all $k \ge 2$). |

### Canonical Root Ordering & Symmetry Invariants
For any quadratic equation returning two real irrational roots $[r_1, r_2]$:
1. $r_1.\text{rational\_part} == r_2.\text{rational\_part} == a$.
2. $r_1.\text{radicand} == r_2.\text{radicand} == d$.
3. $r_1.\text{sqrt\_coefficient} == -b_0$ and $r_2.\text{sqrt\_coefficient} == +b_0$ where $b_0 = |b| > 0$.
4. Strict ascending order: $r_1 < r_2$ is algebraically equivalent to $-b_0 < +b_0$.

### Exact Canonical Reduction Examples
- $\sqrt{8} \longrightarrow 0 + 2\sqrt{2}$
- $\frac{\sqrt{18}}{3} \longrightarrow 0 + 1\sqrt{2}$
- $\sqrt{1/2} \longrightarrow 0 + \frac{1}{2}\sqrt{2}$
- $2 + \sqrt{8} \longrightarrow 2 + 2\sqrt{2}$
- $\frac{-1 \pm \sqrt{20}}{2} \longrightarrow -\frac{1}{2} \pm 1\sqrt{5}$
- $\frac{-6 \pm \sqrt{24}}{6} \longrightarrow -1 \pm \frac{1}{3}\sqrt{6}$

---

## 6. Deterministic Squarefree Decomposition & Certification Proof

### 6.1 Mathematical Certification Proof
**Theorem:** Let $M \in \mathbb{Z}^+$ be an integer. Let $\mathcal{P}_{65536} = \{p \in \text{Primes} \mid p \le 65536\}$. Suppose $M$ is divided by $p^2$ for every $p \in \mathcal{P}_{65536}$ until no $p^2 \mid M$. Let the remaining integer be $R$. If $R < 2^{32}$, then $R$ is certified squarefree.

**Proof:**
1. Suppose for contradiction that $R < 2^{32}$ is not squarefree.
2. Then there exists at least one prime $q$ such that $q^2 \mid R$.
3. Since $q^2 \le R$ and $R < 2^{32}$, we have:
   $$q \le \sqrt{R} < \sqrt{2^{32}} = 2^{16} = 65536.$$
4. Therefore, $q \le 65536$, which means $q \in \mathcal{P}_{65536}$.
5. But the algorithm exhaustively removed all factors of $p^2$ for all $p \in \mathcal{P}_{65536}$.
6. Hence $q^2 \nmid R$, yielding a direct contradiction.
7. Thus, no such prime $q$ exists, and $R$ is mathematically certified to be squarefree. $\blacksquare$

### 6.2 Deterministic Normalization Algorithm

```python
PRIME_TRIAL_LIMIT = 65536  # Primes up to 2^16 (6542 primes)
CERTIFIED_REMAINDER_MAX = (1 << 32) - 1  # R < 2^32, i.e., R.bit_length() <= 32


def normalize_discriminant_squarefree(
    p: int,
    q: int,
    prime_table: List[int],
) -> Tuple[Rational, int]:
    """Deterministically normalize rational Delta = p/q into s * sqrt(d) with certified squarefree d.

    Guarantees:
    - Pure integer arithmetic (zero floats, zero SymPy).
    - If Delta is a rational square, returns d = 1 (belongs to B1 rational path).
    - If remaining R < 2^32, d = R is certified squarefree by Theorem 6.1.
    - If remaining R >= 2^32, raises SurdNormalizationResourceLimitError (fail closed).
    """
    assert p > 0 and q > 0
    # 1. Reduce fraction
    g = math.gcd(p, q)
    p //= g
    q //= g

    # 2. Integer product M = p * q
    M = p * q
    square_factor = 1
    R = M

    # 3. Exhaustive prime square trial division for all p_i <= 65536
    for p_i in prime_table:
        if p_i > 65536:
            break
        p_sq = p_i * p_i
        if p_sq > R:
            break
        while R % p_sq == 0:
            R //= p_sq
            square_factor *= p_i

    # 4. Check rational square
    if R == 1:
        # Delta is an exact rational square (routed to B1 rational path)
        return (Rational(square_factor, q), 1)

    # 5. Certification Boundary Guard
    if R.bit_length() > 32:
        raise SurdNormalizationResourceLimitError(
            f"Unfactored radicand remainder ({R.bit_length()} bits) exceeds 32-bit certification bound."
        )

    # 6. Certified squarefree radicand
    d = R
    s = Rational(square_factor, q)
    return (s, d)
```

---

## 7. Resource-Complexity & Work-Budget Analysis

### 7.1 Complexity Characterization
General integer factorization is computationally difficult classically and no deterministic polynomial-time classical algorithm is known; arbitrary large-integer factorization is therefore unsuitable for this bounded latency and security contract.

### 7.2 Statically Bounded Work Budget
To ensure complete determinism and sub-millisecond execution:
1. **Fixed Prime Table:** Precomputed list of 6,542 primes $\le 65536$ (static memory $\approx 26\text{ KiB}$).
2. **Fixed Maximum Divisions:** At most 6,542 prime division steps per normalization.
3. **Fixed Square-Extraction Steps:** Each prime division loop executes at most $\lfloor \log_2(M) / 2 \rfloor \le 128$ times.
4. **No Adaptive Factoring:** No Pollard-rho, no quadratic sieve, no unbounded search loops.
5. **Cumulative Time Budget:** Shared monotonic 5.0-second timeout across the bridge pipeline.

### 7.3 Large Input Compatibility
The input equation and discriminant may have large coefficients within the existing 256-bit Rational policy. If an equation has a huge square factor that reduces during trial division to a certified squarefree remainder $R < 2^{32}$, it succeeds. If the unfactored remainder $R \ge 2^{32}$, it fails closed immediately with zero worker calls.

---

## 8. Protocol Versioning Decision

### 8.1 Dedicated Protocol: `mke.p02a.v3`
- **Schema Version:** `mke.p02a.v3`
- **Operation:** `SOLVE_QUADRATIC_SURD`
- **Rationale:** Preserves frozen `mke.p02a.v1` (`SOLVE`, `CHECK_CANDIDATE`) and `mke.p02a.v2` (`SOLVE_QUADRATIC`) byte-for-byte without schema mutation or union ambiguity.

### 8.2 Version-Operation Matrix
| Schema Version | Allowed Operations | Notes |
| :--- | :--- | :--- |
| `mke.p02a.v1` | `SOLVE`, `CHECK_CANDIDATE` | Frozen B0 linear solver & rational candidate verifier |
| `mke.p02a.v2` | `SOLVE_QUADRATIC` | Frozen B1 rational quadratic solver |
| `mke.p02a.v3` | `SOLVE_QUADRATIC_SURD` | B2 exact quadratic surd solver |

### 8.3 Strict v3 Success Response Envelope
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
  "is_provisional_evidence": true
}
```

---

## 9. Host / Worker Trust & Independence Model

```
┌────────────────────────────────────────────────────────────────────────┐
│ UNTRUSTED WORKER PROCESS (Windows AppContainer / Low Integrity)        │
│  - Receives query: mke.p02a.v3 / SOLVE_QUADRATIC_SURD                  │
│  - Executes independent worker solver: solve_quadratic_surd_equation() │
│  - Emits candidate wire response with is_provisional_evidence: true    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ IPC Wire JSON (Untrusted Evidence)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TRUSTED HOST CONTROLLER (mke_product.cas.bridge)                       │
│  1. Authoritative Intake Validation (MKEIntakeValidator)               │
│  2. Independent Host AST Polynomial Reduction (A, B, C)                │
│  3. Independent Host Squarefree Normalization: Δ = s^2 * d (d < 2^32)  │
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
The host bridge (`src/mke_product/cas/bridge.py`) **MUST NOT** import `src/mke_product/solver/quadratic_surd.py` or share a normalization function with the worker. Host and worker must each contain an independent implementation of squarefree decomposition and surd derivation.

---

## 10. Independent Exact Verification & Surd Arithmetic Model

### 10.1 Field Arithmetic in $\mathbb{Q}(\sqrt{d})$
For a certified squarefree integer $d \ge 2$, arithmetic operations in $\mathbb{Q}(\sqrt{d})$ on elements $(a, b) \equiv a + b\sqrt{d}$ are evaluated symbolically in $\mathbb{Q}$:

1. **Addition:**
   $$(a_1 + b_1\sqrt{d}) + (a_2 + b_2\sqrt{d}) = (a_1 + a_2) + (b_1 + b_2)\sqrt{d}$$
2. **Negation:**
   $$-(a + b\sqrt{d}) = (-a) + (-b)\sqrt{d}$$
3. **Multiplication:**
   $$(a_1 + b_1\sqrt{d}) \cdot (a_2 + b_2\sqrt{d}) = (a_1 a_2 + b_1 b_2 d) + (a_1 b_2 + a_2 b_1)\sqrt{d}$$
4. **Squaring:**
   $$(a + b\sqrt{d})^2 = (a^2 + b^2 d) + (2 a b)\sqrt{d}$$

### 10.2 Host Proof Algebraic Identities
For roots $r_1 = a - b_0\sqrt{d}$ and $r_2 = a + b_0\sqrt{d}$ with $b_0 > 0$:

1. **Vieta Sum Identity:**
   $$r_1 + r_2 = (a - b_0\sqrt{d}) + (a + b_0\sqrt{d}) = 2a + 0\sqrt{d} = -\frac{B}{A}$$
   Host checks: $2A a + B == 0$.
2. **Vieta Product Identity:**
   $$r_1 \cdot r_2 = (a - b_0\sqrt{d})(a + b_0\sqrt{d}) = a^2 - b_0^2 d + 0\sqrt{d} = \frac{C}{A}$$
   Host checks: $A(a^2 - b_0^2 d) - C == 0$.
3. **Exact Polynomial Evaluation:**
   $$A(a \pm b_0\sqrt{d})^2 + B(a \pm b_0\sqrt{d}) + C = \left[A(a^2 + b_0^2 d) + B a + C\right] \pm \left[b_0(2 A a + B)\right]\sqrt{d}$$
   Since $d > 1$ is squarefree, $\sqrt{d}$ is irrational, so this equals $0$ if and only if:
   - Rational component: $A(a^2 + b_0^2 d) + B a + C = 0$.
   - Radical component: $b_0(2 A a + B) = 0 \implies 2 A a + B = 0$.

All host verification is computed using bounded pure integer/Rational helpers with strict 256-bit resource bounds.

---

## 11. Exact Root Ordering

For roots $r_1 = a + b_1\sqrt{d}$ and $r_2 = a + b_2\sqrt{d}$ in $\mathbb{Q}(\sqrt{d})$:
- The worker must return roots in strictly ascending order: $r_1 < r_2$.
- Since $a_1 = a_2 = a$ and $d_1 = d_2 = d > 1$, exact ordering is algebraic:
  $$r_1 < r_2 \iff b_1 < b_2$$
- In canonical form, $b_1 = -b_0$ and $b_2 = +b_0$ with $b_0 \in \mathbb{Q}^+$.
- Therefore:
  $$r_1 = a - b_0\sqrt{d} < r_2 = a + b_0\sqrt{d}$$
  is deterministically ordered without floating-point evaluation.

---

## 12. Candidate Verification: Why v1 `CHECK_CANDIDATE` is NOT Used

- **v1 Frozen Limitation:** `CHECK_CANDIDATE` in `mke.p02a.v1` is frozen and accepts rational strings $p/q$.
- **Irrational Incompatibility:** Quadratic surds cannot be represented as rational strings. Serializing decimal approximations (`"1.414"`) would violate exactness.
- **Mathematical Soundness:** Host algebraic proof over $\mathbb{Q}(\sqrt{d})$ (Vieta sum, Vieta product, exact residual evaluation) provides $100\%$ authoritative certification.
- **Decision:** Surd candidate verification is performed entirely via host algebraic proof. No secondary worker candidate check is needed or permitted.

---

## 13. Public Result Model

### 13.1 Frozen Base Classes
To ensure zero breaking changes for existing consumers:
- `ControlledDispatchResult` (B0 9-field contract) remains **FROZEN**.
- `QuadraticControlledDispatchResult` (B1 11-field contract) remains **FROZEN**.

### 13.2 Subclass: `QuadraticSurdControlledDispatchResult`
```python
class WireRational(BaseModel):
    numerator: str
    denominator: str

    model_config = ConfigDict(frozen=True, extra="forbid")


class QuadraticSurdRoot(BaseModel):
    rational_part: WireRational
    sqrt_coefficient: WireRational
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
- `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`: Discriminant factorization remainder exceeds 32-bit certification ceiling ($R \ge 2^{32}$) or bit bounds exceeded.
- `ERR_NONCANONICAL_SURD_RESPONSE`: Worker returned unreduced fractions, non-squarefree radicand, or inverted signs.
- `ERR_MALFORMED_SURD_RESPONSE`: Worker response violated strict v3 field schema.
- `ERR_SURD_VERIFICATION_MISMATCH`: Worker roots failed host algebraic proof or Vieta checks.

### 14.3 Transport Error Handling
Infrastructure failures (`WORKER_TIMEOUT`, `WORKER_RESOURCE_EXHAUSTED`, `WORKER_STARTUP_FAILURE`, `WORKER_ASSIGNMENT_FAILURE`, `WORKER_EXIT_FAILURE`, `WORKER_PROTOCOL_FAILURE`, `ERR_PAYLOAD_TOO_LARGE`, `ERR_RESPONSE_LIMIT_EXCEEDED`, `PROTOCOL_ERROR`) are mapped systematically before response envelope inspection and do not require valid v3 fields.

---

## 15. Threat Model & Adversarial Attack Vectors

| Threat Vector | Attack Mechanism | B2 Defense / Mitigation |
| :--- | :--- | :--- |
| **Large Prime Square Divisor (Counterexample)** | Adversary inputs equation with $\Delta = 2 \cdot 65537^2$. Untested prime $65537 > 65536$. | $R = 2 \cdot 65537^2 \approx 8.59 \times 10^9$ has $R.\text{bit\_length}() = 34 > 32$. Bridge fails closed pre-dispatch with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`. |
| **Large-Semiprime Stalling** | Adversary inputs equation with huge composite discriminant to stall factorization. | Fixed prime table search up to 65536. If $R.\text{bit\_length}() > 32$, fails closed immediately (0 worker calls). |
| **Noncanonical Wire Surds** | Collusive worker returns $\sqrt{8}$ instead of $2\sqrt{2}$ or $d=1$. | Host validates $d \ge 2, d < 2^{32}$, $d$ squarefree, and strict field reduction before verification. |
| **Forged Roots with Fake Check** | Collusive worker returns incorrect roots $(r_1', r_2')$. | Host independently computes expected roots and evaluates exact Vieta identities and polynomial residuals over $\mathbb{Q}(\sqrt{d})$. |
| **Unsorted / Inverted Roots** | Worker returns $[r_2, r_1]$ instead of $[r_1, r_2]$. | Host strictly verifies $b_1 < b_2$ and rejects inverted roots. |
| **Surrogate / Extra Fields** | Worker injects extra JSON fields or surrogate characters. | Strict v3 protocol validator and JSON decode hooks reject malformed payloads. |

---

## 16. Test Matrix Plan

1. **Protocol v3 Unit Tests (`tests/test_protocol.py`):**
   - Validation of `mke.p02a.v3` / `SOLVE_QUADRATIC_SURD`.
   - Rejection of unknown fields, invalid types, and non-ASCII equations.
2. **Worker Surd Solver Tests (`tests/test_p03c_p1c_quadratic_surd.py`):**
   - Standard surds: $x^2 - 2 = 0 \to \pm\sqrt{2}$, $x^2 - 8 = 0 \to \pm 2\sqrt{2}$, $x^2 - 18 = 0 \to \pm 3\sqrt{2}$, $2x^2 - 1 = 0 \to \pm\sqrt{2}/2$, $x^2 + x - 1 = 0 \to (-1 \pm \sqrt{5})/2$, $3x^2 + 6x + 1 = 0 \to -1 \pm \sqrt{6}/3$, $(x-1)^2 = 2 \to 1 \pm \sqrt{2}$, $x^2 - 50 = 0 \to \pm 5\sqrt{2}$.
3. **Normalization Boundary & Adversarial Cases:**
   - $M = 2 \cdot 65537^2$ (34 bits $\to$ fails closed with `ERR_SURD_NORMALIZATION_RESOURCE_LIMIT`).
   - $M = 3 \cdot 65537^2$ and $5 \cdot 65537^2$ ($\to$ fail closed pre-dispatch).
   - 33-64 bit composite remainders ($\to$ fail closed pre-dispatch).
   - Huge reducible square: $M = (2^{100})^2 \cdot 2$ (reduces to $R = 2 < 2^{32} \to$ succeeds).
4. **Bridge Controlled Dispatch & Verification Tests (`tests/test_p03c_p1c_quadratic_surd_dispatch.py`):**
   - End-to-end dispatch and verification of surd roots.
   - Host proof independent verification.
   - Adversarial worker collusion tests (wrong roots, wrong discriminant, wrong radicand, noncanonical surd).
   - Strict budget monotonicity and cumulative timeout enforcement.
5. **Full Regression Suite:**
   - Zero regressions on B0 linear dispatch, B1 rational quadratic dispatch ($x^2 - 4 = 0$, $(x-1)^2 = 0$, $x^2 + 1 = 0$), Windows AppContainer containment (`test_worker_windows.py`), and browser UI suites.

---

## 17. Backward-Compatibility Locks

- **B0 Baseline:** All linear dispatches and 9-field `ControlledDispatchResult` contracts remain identical.
- **B1 Baseline:** All rational-quadratic dispatches ($x^2 - 4 = 0$, $(x-1)^2 = 0$, $x^2 + 1 = 0$) execute identically through `mke.p02a.v2` and `QuadraticControlledDispatchResult`.
- **`test_worker_windows.py`:** Strictly byte-identical to accepted baseline with zero handle leaks (`handles_end - handles_start <= 0`).
- **`entrypoint.py`:** Strictly byte-identical and frozen.

---

## 18. Proposed File Change Inventory

### Unchanged Files (FROZEN)
- `src/mke_product/worker/entrypoint.py`
- `src/mke_product/solver/quadratic.py` (B1 rational solver remains untouched)
- `src/mke_product/solver/affine.py`
- `src/mke_product/solver/solver.py`
- `src/mke_product/evaluator/evaluator.py`
- `src/mke_product/parser/parser.py`
- `src/mke_product/parser/ast.py`
- `tests/test_worker_windows.py`

### Modified Files
- `src/mke_product/cas/bridge.py` (Add B2 surd host verification, squarefree normalization, and v3 routing)
- `src/mke_product/protocol/schema.py` (Add `SCHEMA_VERSION_V3`, `OPERATION_SOLVE_QUADRATIC_SURD`)
- `src/mke_product/protocol/validator.py` (Add v3 validation rules)
- `src/mke_product/protocol/dispatcher.py` (Route v3 operation and audit response schema allowlists)
- `src/mke_product/worker/controller.py` (Extend operation allowlist)
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
| **Mathematically Certified Bound** | Prime trial division up to 65536 with strict $R < 2^{32}$ remainder ceiling guarantees squarefree $d$. | **SATISFIED** |
| **Independent Verification** | Host derives proofs independently without importing worker solver. | **SATISFIED** |
| **Backward Compatibility** | B0 and B1 contracts frozen and preserved via dedicated `mke.p02a.v3`. | **SATISFIED** |
| **Containment Integrity** | Windows AppContainer isolation, zero handle leaks, and frozen `entrypoint.py`. | **SATISFIED** |

---

## 20. Explicit Deferred Capabilities

The following capabilities are explicitly deferred to future milestones:
- **Higher-Degree Algebraic Numbers:** Roots of cubic, quartic, or general polynomials.
- **Complex Roots with Radicals:** Imaginary quadratic surds ($a \pm b i \sqrt{d}$ for $\Delta < 0$).
- **Nested Radicals:** Expressions of the form $\sqrt{a + \sqrt{b}}$.
- **Arbitrary Radicand Prime Factorization:** Factoring discriminants whose unfactored remainder exceeds 32 bits ($R \ge 2^{32}$).

---

## 21. Final Recommendation

Antigravity recommends **GO BOUNDED** for P1C-04-B2 implementation following the architecture detailed in this R1 specification. All prerequisites for exactness, mathematical soundness, resource bounding, security containment, and independent verification are met.
