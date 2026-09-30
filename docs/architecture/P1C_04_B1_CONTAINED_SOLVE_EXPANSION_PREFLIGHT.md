# P1C-04-B1 CONTAINED SOLVE CAPABILITY EXPANSION PREFLIGHT

- **Document:** `docs/architecture/P1C_04_B1_CONTAINED_SOLVE_EXPANSION_PREFLIGHT.md`
- **Milestone:** `PRODUCT-03C-P1C-04-B1-PREFLIGHT`
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Branch:** `product/p03c-p1c-04-b1-contained-solve-preflight`
- **Base Baseline Commit:** `147f561a883c6d5ea75febe7857e00291107b6da` (P1C-04-B0-R3 Accepted & Locked)
- **Status:** `PREFLIGHT SPECIFICATION — PENDING INDEPENDENT AUDIT`
- **Date:** 2026-09-30

---

## 1. Executive Decision

The Math Knowledge Engine (MKE) has successfully established and locked the P1C-04-B0 baseline (`147f561a883c6d5ea75febe7857e00291107b6da`), providing safe, deterministic, Windows-contained execution and independent verification for **single-variable affine linear equations** ($Ax + B = 0$ over $\mathbb{Q}$).

### Core Finding
Expanding contained execution to **Real Quadratic Equations in One Variable $x$ with Exact Rational Coefficients** ($Ax^2 + Bx + C = 0$, $A \ne 0$, $A, B, C \in \mathbb{Q}$) is **FEASIBLE AND SAFE** under a strictly bounded implementation contract. However, general unconstrained polynomial solving (degree $\ge 3$), rational equations with variable denominators, radical equations, and transcendental equations **MUST REMAIN EXPLICITLY OUT OF SCOPE AND DEFERRED**.

### Non-Negotiable Preflight Principles
1. **Mathematical Capability $\ne$ Containment Authorization:** The presence of SymPy or broad solving logic in legacy/experimental modules (P1B) does NOT authorize unverified or uncontained exposure.
2. **Deterministic Independent Verification Gate:** No worker response may self-certify. A result achieves `VERIFIED_COMPLETE` if and only if the host performs an independent AST reduction, discriminant analysis ($\Delta = B^2 - 4AC$), and independent candidate membership verification.
3. **Fail-Closed Domain Safety:** Equations with variable-dependent exponents, undefined constant forms ($0^0$, division by zero), variable denominators, or radicals must fail closed before dispatch.
4. **Preservation of Accepted Baseline:** All accepted B0 affine behaviors and tests must remain 100% intact with zero regression.

---

## 2. Actual-Code Inventory

The current execution and containment architecture relies on the following codebase inventory:

| Module / File Path | Architectural Role | Current Status in B0-R3 |
| :--- | :--- | :--- |
| `src/mke_product/cas/bridge.py` | Controlled dispatch bridge, intake taxonomy mapping, AST affine extraction, proof checker | **LOCKED & VERIFIED** (Affine $Ax+B=0$ only) |
| `src/mke_product/worker/controller.py` | Win32 Job Object manager (256MB process, 512MB job, 5s timeout, restricted tokens) | **FROZEN & VERIFIED** |
| `src/mke_product/worker/entrypoint.py` | Disposable worker stdin/stdout length-prefixed IPC entrypoint | **FROZEN & VERIFIED** |
| `src/mke_product/protocol/schema.py` | Protocol definitions, wire rational serializer, length bounds (`mke.p02a.v1`) | **FROZEN** (Single `root` field) |
| `src/mke_product/protocol/dispatcher.py` | In-worker request validator, AST parser invocation, solver/evaluator dispatch | **FROZEN** |
| `src/mke_product/solver/solver.py` | In-worker pure-rational affine solver kernel ($Ax+B=0$) | **FROZEN** (Affine linear only) |
| `src/mke_product/solver/scope.py` | Pre-simplification linearity and scope checker | **FROZEN** (Rejects power $\ge 2$) |
| `src/mke_product/evaluator/evaluator.py` | S2 Candidate verification engine (`CHECK_CANDIDATE`) | **FROZEN** (Evaluates rational candidate) |
| `src/mke_product/cas/router.py` | In-process uncontained routing (legacy/demo) | **PROHIBITED** from worker bridge |
| `src/mke_product/cas/sympy_adapter.py` | SymPy-based solver adapter (P1B transcendental/system) | **UNCONTAINED** (Requires isolation) |

---

## 3. Existing Execution Path Analysis

The end-to-end execution flow from user query to verified outcome traces through the following deterministic sequence:

```
[Raw User Query + MKE-IR Payload]
               │
               ▼
   [1. MKEIntakeValidator] ──(Invalid / Non-Exhaustive)──► [Immediate Rejection (Zero Worker Spawn)]
               │
          (Validated)
               ▼
 [2. ControlledDispatchBridge]
   - Scope Guard (single var 'x', no parameters, no constraints)
   - Protocol Bounds Check (ASCII, length <= 256)
   - Host AST Parsing (`parse_equation`)
   - Host Reduction Check (`extract_affine_coefficients`) ──(Non-Affine)──► [Reject `ERR_OUT_OF_SCOPE`]
               │
          (Affine OK)
               ▼
 [3. WorkerController & Win32 Job Object]
   - Spawns `python -m mke_product.worker.entrypoint`
   - Applies Win32 Job Object Limits (256 MiB Process, 512 MiB Job, Kill-on-Close, No Breakaway)
   - Enforces Monotonic 5.0s Wall-Clock Deadline Budget
               │
               ▼
 [4. Worker Process: `entrypoint.py`]
   - Reads 4-byte big-endian length prefix + JSON payload from stdin
   - Passes to `protocol.dispatcher.dispatch_request`
               │
               ▼
 [5. Protocol Dispatcher & Mathematical Solver]
   - Parses AST via `mke_product.parser.parser.parse_equation`
   - Dispatches to `solve_equation(eq_ast, budget)`
   - Computes canonical reduction, unique root $x = -B/A$, runs internal S2 `check_candidate`
   - Formats JSON response (`mke.p02a.v1`, `outcome: "SUCCESS"`, `root: {"numerator": "...", "denominator": "..."}`)
               │
               ▼
 [6. Worker Response Transport]
   - Length-prefixed framing written to stdout (max 16 KiB)
   - WorkerController reads stdout, terminates disposable worker
               │
               ▼
 [7. Host Independent Verification Gate]
   - Validates response envelope, schema version, operation echo, outcome, definedness
   - Matches worker root against independently derived host root ($-host_B / host_A$)
   - Dispatches secondary `CHECK_CANDIDATE` request to verify residual evaluates to exact 0
   - Projects authoritative `ControlledDispatchResult(is_verified=True, verification_status=VERIFIED_COMPLETE)`
```

---

## 4. Comprehensive Capability Matrix

| # | Mathematical Capability | Parser Support | Typed AST Support | Mathematical Solver | Exactness / Completeness | Current Worker Support | Protocol Support (`mke.p02a.v1`) | Containment Status | Independent Verification Gate | Domain Certainty | Resource Bound Safety | Preflight Disposition |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Affine Equation** ($Ax+B=0$) | Yes | Yes | Yes (Pure $\mathbb{Q}$) | Exact $\mathbb{Q}$, Complete | **Supported** | Supported (`root`) | Contained | Host Reduction + S2 Check | Everywhere defined on $\mathbb{R}$ | Safe (Bounded bits) | `SUPPORTED_NOW` |
| 2 | **Quadratic Equation** ($Ax^2+Bx+C=0$) | Yes | Yes | P1B only (SymPy) | Exact $\mathbb{Q}$ / Quadratic Radicals | **Rejected** (Scope check) | Insufficient (Needs multi-root) | Contained | Host Discriminant + Vieta + S2 | Everywhere defined on $\mathbb{R}$ | Safe (Degree $\le 2$) | `SAFE_TO_ADD_WITH_BOUNDED_CHANGE` |
| 3 | **Polynomial Degree 3–4** (Cubic/Quartic) | Yes | Yes | P1B (SymPy) | Nested Radicals / Casus Irreducibilis | **Rejected** | Insufficient | Contained | Complex (Sturm chains needed) | Everywhere defined on $\mathbb{R}$ | Medium | `DEFER` |
| 4 | **Higher Polynomial** (Degree $\ge 5$) | Yes | Yes | P1B (SymPy roots) | Non-radical / Approx only | **Rejected** | Insufficient | Contained | Infeasible without float approx | Everywhere defined on $\mathbb{R}$ | High Risk | `DEFER` |
| 5 | **Rational Equation** ($\frac{P(x)}{Q(x)}=0$) | Yes | Yes | P1B (SymPy) | Exact $\mathbb{Q}$ with exclusions | **Rejected** | Insufficient | Contained | Requires pole tracking | Singular at $Q(x)=0$ | Medium | `REQUIRES_NEW_VERIFIER` |
| 6 | **Algebraic Radical Equation** | Yes | Yes | P1B (SymPy) | Extraneous root elimination | **Rejected** | Insufficient | Contained | Requires branch check | Restricted ($P(x) \ge 0$) | High Risk | `REQUIRES_NEW_VERIFIER` |
| 7 | **Exponential Equation** ($a^x=b$) | Yes | Yes | P1B (SymPy) | Transcendental / Logarithmic | **Rejected** | Insufficient | Contained | Requires transcendental CAS | Restricted | High Risk | `DEFER` |
| 8 | **Logarithmic Equation** ($\log_a x=b$) | Yes | Yes | P1B (SymPy) | Exact with domain cuts | **Rejected** | Insufficient | Contained | Requires domain verifier | Restricted ($x>0, a>0, a\ne 1$) | High Risk | `DEFER` |
| 9 | **Trigonometric Equation** ($\sin x=a$) | Yes | Yes | P1B (SymPy) | Infinite periodic families | **Rejected** | Insufficient | Contained | Requires family verifier | Periodic | High Risk | `DEFER` |
| 10 | **System of Equations** | Yes | Yes | P1B (LinearSystem) | Multi-variable solution sets | **Rejected** | Insufficient | Contained | Requires matrix proof | Multivariable | High Risk | `DEFER` |
| 11 | **Inequality** ($P(x)>0$) | Yes | Yes | P1B (Inequality) | Union of Intervals | **Rejected** | Insufficient | Contained | Requires sign chart verifier | Everywhere defined | High Risk | `DEFER` |
| 12 | **CHECK_CANDIDATE (Rational)** | Yes | Yes | Yes (S2 Evaluator) | Exact $\mathbb{Q}$ Residual | **Supported** | Supported | Contained | Exact Residual == 0 | Exact | Safe | `SUPPORTED_NOW` |

---

## 5. Audit of P1B Functionality Reuse Inside Worker Boundary

P1B contains extensive mathematical functionality (`src/mke_product/cas/sympy_adapter.py`, `ast_bridge.py`, `safety.py`). We evaluate the feasibility, risks, and boundaries of reusing P1B components inside the worker:

1. **Exact Modules Evaluated for Reuse:**
   - `mke_product.cas.safety.is_polynomial_ast`: AST property inspection.
   - `mke_product.cas.ast_bridge.ast_to_sympy`: Safe conversion of MKE AST to SymPy expressions.
   - `mke_product.cas.sympy_adapter.execute_sympy_direct`: Invocation of SymPy solvers.
2. **SymPy Invocation Analysis:**
   - P1B directly invokes `sympy.solve`, `sympy.solveset`, `sympy.roots`, and `sympy.simplify`.
3. **Resource Boundedness Inside Worker:**
   - The OS-level Win32 Job Object enforces a hard 256 MiB process limit and 512 MiB job limit from process start (`CREATE_SUSPENDED`).
   - SymPy initialization consumes ~50 MiB and ~150–200 ms of CPU time.
   - For quadratic equations with small coefficients, SymPy executes in $<10$ ms. However, unconstrained SymPy calls on complex expressions can trigger recursive Groebner bases, polynomial factorization blowup, or memory spikes.
4. **Determinism Assessment:**
   - SymPy's output sets (`FiniteSet`, `EmptySet`) are generally deterministic for univariate polynomials, but internal dictionary ordering can exhibit subtle differences across Python patch versions unless explicitly sorted.
5. **Typed Representation for Verification:**
   - Raw SymPy outputs are symbolic objects (`sympy.Rational`, `sympy.Add`, `sympy.Mul`, `sympy.Pow`). They cannot be directly transported across the IPC boundary without structured serialization into canonical JSON dictionaries.
6. **Independence of Proof Claims:**
   - SymPy-generated solutions are **same-engine evidence**. Trusting SymPy's claims of root completeness or no-real-root status without an independent host verification gate would violate MKE soundness principles.
7. **Alternative: Pure-Python Deterministic Polynomial Solver:**
   - Instead of importing heavy SymPy into the worker kernel, quadratic equation reduction ($Ax^2 + Bx + C = 0$), discriminant evaluation ($\Delta = B^2 - 4AC$), and quadratic formula derivation can be implemented in a **lightweight, pure-Python deterministic solver module** (`mke_product.solver.quadratic`) using the existing `Rational` class.
   - **Recommendation:** Implement a pure-Python quadratic solver within the worker kernel, avoiding SymPy entirely for bounded B1 quadratic scope.

---

## 6. Protocol Versioning Analysis

The current protocol `mke.p02a.v1` is locked to single-variable affine equations with a single `root: Optional[Dict[str, str]]` field.

### Comparison of Protocol Options

| Criterion | Option A: In-Place `mke.p02a.v1` Extension | Option B: Versioned `mke.p02a.v2` Protocol | Option C: Unchanged Protocol (No Expansion) |
| :--- | :--- | :--- | :--- |
| **Backward Compatibility** | High (Additive fields) | Full (Dual schema support via dispatcher) | Complete (Blocks progress) |
| **Accepted Worker Tests** | Requires updating validator allowlist | 100% Frozen & Isolated (`mke.p02a.v1` tests untouched) | Untouched |
| **Response Ambiguity** | Moderate (Conflict between `root` and `roots`) | Zero (Strict typed schema per version) | None |
| **Multi-Root Representation** | Clunky | Clean (`roots: List[RationalRoot]`, `discriminant: Rational`) | None |
| **Migration Risk** | Low-Medium | Very Low | None |
| **Auditor Verification Burden** | Higher (Schema drift) | Clean, explicit, segregated | Minimal |

### Recommended Decision: **OPTION B (`mke.p02a.v2`)**
- Introduce `SCHEMA_VERSION_V2 = "mke.p02a.v2"`.
- The worker dispatcher routes `mke.p02a.v1` requests to the frozen affine solver and `mke.p02a.v2` requests to the expanded polynomial solver.
- Wire response schema for `mke.p02a.v2` supports:
  - `status`: `"UNIQUE_REAL_ROOT"`, `"TWO_DISTINCT_REAL_ROOTS"`, `"NO_REAL_ROOT"`, `"DomainSet(R)"`, `"EmptySet"`.
  - `roots`: List of canonical rational wire dicts `[{"numerator": "...", "denominator": "..."}]`.
  - `discriminant`: Wire rational dict for $\Delta$.

---

## 7. Mathematical Verification Contract for Quadratic Scope

To achieve `VerificationStatus.VERIFIED_COMPLETE`, a quadratic equation $Ax^2 + Bx + C = 0$ ($A \ne 0$, $A, B, C \in \mathbb{Q}$) must satisfy the following independent proof checks:

```
                  [Host AST Reduction]
           Derive A, B, C in Q deterministically
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
        [Case: A == 0]              [Case: A != 0]
      (Degenerate Linear)           (True Quadratic)
             │                           │
    Delegate to B0 Gate                  ▼
                              [Compute Discriminant]
                              Δ = B^2 - 4*A*C in Q
                                         │
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
       [Case 1: Δ < 0]             [Case 2: Δ == 0]            [Case 3: Δ > 0]
      (No Real Roots)              (Unique Real Root)        (Two Distinct Roots)
             │                           │                           │
  - Verify Worker Claims:     - Expected Root:            - If Δ = k^2 (k in Q):
    status == "NO_REAL_ROOT"    r = -B / (2*A) in Q         Expected roots:
  - Proof: Δ < 0 strictly     - Verify Worker Claims:       r1 = (-B - k)/(2*A)
  - Result: EMPTY_SET           status == "UNIQUE_ROOT"     r2 = (-B + k)/(2*A)
  - Completeness: PROVEN        roots == [r]              - Verify Worker Claims:
                              - Vieta Check:                roots == [r1, r2]
                                2*r == -B/A               - Vieta Check:
                                r^2 == C/A                  r1 + r2 == -B/A
                              - S2 Residual:                r1 * r2 == C/A
                                CHECK_CANDIDATE(r) == 0   - S2 Residuals:
                              - Result: UNIQUE_ROOT         CHECK_CANDIDATE(r1) == 0
                              - Completeness: PROVEN        CHECK_CANDIDATE(r2) == 0
                                                          - Result: TWO_DISTINCT_ROOTS
                                                          - Completeness: PROVEN
```

### Verification Method Authority Matrix

| Verification Method | Trust Level | Description |
| :--- | :--- | :--- |
| **Host AST Reduction** ($Ax^2+Bx+C=0$) | `TRUSTED INDEPENDENT CHECK` | Pure host reduction over $\mathbb{Q}$ without symbolic solver. |
| **Discriminant Sign Proof** ($\Delta = B^2-4AC$) | `TRUSTED INDEPENDENT CHECK` | Exact sign determination in $\mathbb{Q}$. |
| **Rational Root Formula Derivation** | `TRUSTED INDEPENDENT CHECK` | Closed-form formula $r = \frac{-B \pm \sqrt{\Delta}}{2A}$ computed on host. |
| **Vieta Sum & Product Invariants** | `TRUSTED INDEPENDENT CHECK` | $r_1+r_2 = -B/A$ and $r_1 \cdot r_2 = C/A$ checked in exact rationals. |
| **S2 Exact Residual Check** | `TRUSTED INDEPENDENT CHECK` | In-worker $LHS(r_i) - RHS(r_i) \equiv 0$ evaluated over original unreduced AST. |
| **Raw Solver Output / Status String** | `SAME-ENGINE EVIDENCE ONLY` | Untrusted for certification without host verification. |
| **Floating-Point Evaluation** | `INSUFFICIENT` | Prohibited in MKE verification gate. |

---

## 8. Domain-Safety Audit & Counterexamples

| Counterexample Query | Mathematical Nature | Expected Intake / Bridge Behavior | Expected Public Status | Verification Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `x^2 - 4 = 0` | Standard quadratic, $\Delta = 16 = 4^2 > 0$ | In scope, valid AST | `TWO_DISTINCT_REAL_ROOTS` | `VERIFIED_COMPLETE` (roots: $\{-2, 2\}$) |
| `(x - 1)^2 = 0` | Repeated root, $\Delta = 0$ | In scope, expanded to $x^2 - 2x + 1 = 0$ | `UNIQUE_REAL_ROOT` | `VERIFIED_COMPLETE` (root: $1$, mult 2) |
| `x^2 + 1 = 0` | Definite positive, $\Delta = -4 < 0$ | In scope, valid AST | `NO_REAL_ROOT` | `VERIFIED_COMPLETE` (empty set $\emptyset$) |
| `x^4 - 5*x^2 + 4 = 0` | Biquadratic (Degree 4) | Rejected by quadratic scope guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `(x - 1)/(x - 1) = 1` | Rational with removable singularity at $x=1$ | Rejected (Variable denominator) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `sqrt(x) = -1` | Algebraic radical equation | Rejected (Radical AST node) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `sqrt(x^2) = x` | Identity on $[0, \infty)$, false on $(-\infty, 0)$ | Rejected (Radical AST node) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `1/(x - 1) = 0` | Rational contradiction | Rejected (Variable denominator) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `2^x = 8` | Exponential equation | Rejected (Nonlinear power / function) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `sin(x) = 0` | Trigonometric (Infinite family $k\pi$) | Rejected (FunctionCall node) | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `x^0 = 1` | Undefined at $x=0$ ($0^0$) | Rejected by domain-safety guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `0^0 = 1` | Undefined constant expression | Rejected by AST domain evaluator | `REJECTED_SCOPE` (`ERR_DOMAIN_ERROR`) | `NOT_APPLICABLE` (Fail Closed) |

---

## 9. Resource & Containment Threat Model

### Symbolic Execution Threats & Mitigations

```
Threat: Expression Expansion Explosion (e.g. (x+1)^100)
Mitigation: Max raw query length 256 chars, max AST nodes 100, max constant exponent 2.

Threat: Coefficient Bit-Length Growth
Mitigation: 256-bit maximum per integer numerator/denominator; fail closed on bit overflow.

Threat: Factorization / Symbolic Hang
Mitigation: Deterministic closed-form quadratic formula (O(1) arithmetic ops over Q). Zero Groebner basis.

Threat: Large Output Buffer Overflow
Mitigation: Hard 16 KiB serialized JSON ceiling; responses exceeding buffer fail closed.

Threat: Process Hang / Infinite Loops
Mitigation: Shared 5.0s wall-clock deadline budget enforced by Win32 Job Object and host timers.

Threat: Memory Bomb / Heap Exhaustion
Mitigation: Hard OS-enforced 256 MiB per-process / 512 MiB per-job commit limit via Win32 Job Object.

Threat: Forged / Incomplete Solver Response
Mitigation: Independent host reduction, discriminant check, Vieta check, and S2 residual validation.
```

### Mandatory Hard Bounds Table

| Parameter / Bound | Maximum Limit | Enforcement Layer | Failure Action |
| :--- | :--- | :--- | :--- |
| Raw Query Length | 256 ASCII characters | Intake & Bridge | `ERR_INTAKE_SYNTAX_INVALID` |
| AST Node Budget | 100 nodes | Host AST Reducer & Worker | `ERR_OUT_OF_SCOPE` |
| AST Recursion Depth | 20 levels | Host AST Reducer & Worker | `ERR_OUT_OF_SCOPE` |
| Maximum Polynomial Degree | 2 (Quadratic) | Host AST Reducer & Worker | `ERR_OUT_OF_SCOPE` |
| Maximum Exponent Value | 2 (Variable), 10 (Constant) | Host AST Reducer & Worker | `ERR_OUT_OF_SCOPE` |
| Integer Coefficient Size | 256 bits | Rational Arithmetic Engine | `ERR_OUT_OF_SCOPE` / `RESOURCE_EXHAUSTED` |
| Maximum Roots Returned | 2 roots | Protocol Dispatcher & Bridge | `ERR_MALFORMED_WORKER_RESPONSE` |
| Maximum Response Size | 16,384 bytes (16 KiB) | Worker IPC & Controller | `ERR_RESPONSE_LIMIT_EXCEEDED` |
| Total Execution Deadline | 5.0 seconds (wall clock) | Bridge & WorkerController | `ERR_TIMEOUT` |
| Worker Process Memory | 256 MiB | Win32 Job Object (`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`) | Process Terminated / `ERR_TIMEOUT` |
| Worker Job Memory | 512 MiB | Win32 Job Object | Job Terminated / `ERR_TIMEOUT` |

---

## 10. Selected Bounded B1 Implementation Candidate

### Scope Definition
**Real Quadratic Equations in One Variable $x$ with Exact Rational Coefficients.**
Canonical form:
$$A x^2 + B x + C = 0 \quad (A, B, C \in \mathbb{Q}, A \ne 0)$$
where the equation AST contains only integer literals, variable $x$, binary $+,-,*$, unary $+,-$, groups $()$, and powers $x^2$ or $x^1$.

### Sub-Scope 1: Rational Roots ($\Delta = k^2, k \in \mathbb{Q}$)
- Supported for direct exact rational representation.
- Full independent verification via Vieta formulas and S2 candidate checks.
- Public status: `TWO_DISTINCT_REAL_ROOTS` or `UNIQUE_REAL_ROOT`.

### Sub-Scope 2: No Real Roots ($\Delta < 0$)
- Supported for empty set determination over $\mathbb{R}$.
- Full independent verification via host discriminant evaluation ($\Delta < 0$).
- Public status: `NO_REAL_ROOT` (solution set $\emptyset$).

### Sub-Scope 3: Quadratic Irrationals ($\Delta > 0, \sqrt{\Delta} \notin \mathbb{Q}$)
- **Preflight Boundary Decision:** If irrational square roots $\sqrt{\Delta}$ are encountered:
  - Worker returns exact radical representation `{"type": "QUADRATIC_RADICAL", "p": Rational, "q": Rational, "d": Rational}`.
  - If exact radical verification arithmetic is implemented in B1 host: status `TWO_DISTINCT_REAL_ROOTS` with exact radical representation.
  - If radical arithmetic is deferred: status `UNVERIFIED_CLAIM` or `REJECTED_SCOPE`.
  - **Recommended B1 Staging:** Support rational roots and no-real-root cases in Stage 1; support irrational quadratic radicals in Stage 2.

---

## 11. Proposed B1 Implementation Contract

### 1. Files to Add / Modify

| File | Change Type | Purpose |
| :--- | :--- | :--- |
| `src/mke_product/protocol/schema.py` | Modify | Define `SCHEMA_VERSION_V2 = "mke.p02a.v2"`, multi-root wire schemas. |
| `src/mke_product/solver/quadratic.py` | **Create** | Pure-Python deterministic quadratic solver kernel over $\mathbb{Q}$. |
| `src/mke_product/solver/affine.py` | Modify / Refactor | Generalize AST polynomial coefficient extraction to degree 2. |
| `src/mke_product/protocol/dispatcher.py` | Modify | Route `mke.p02a.v2` requests to quadratic solver. |
| `src/mke_product/cas/bridge.py` | Modify | Implement `extract_quadratic_coefficients`, quadratic verification gate, Vieta checks. |
| `tests/test_p03c_p1c_quadratic_dispatch.py` | **Create** | Comprehensive unit, integration, and adversarial test suite. |

### 2. Public Result Schema (`ControlledDispatchResult`)
```python
class ControlledDispatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intake_status: IntakeStatus
    intake_diagnostic: PublicValidationDiagnostic
    execution_status: ExecutionStatus
    verification_status: VerificationStatus
    is_verified: bool
    solution_type: Optional[str] = None  # "UNIQUE_ROOT", "TWO_DISTINCT_ROOTS", "NO_REAL_ROOT", "ALL_REALS", "EMPTY_SET"
    verified_roots: Optional[List[RationalRoot]] = None
    discriminant: Optional[RationalRoot] = None
    completeness_proven: bool = False
    error_code: Optional[str] = None
```

---

## 12. Required Adversarial Test Matrix

| Test ID | Input Equation / Scenario | Expected Outcome | Expected Status | Verification Status | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ADV-01` | `x^2 - 4 = 0` | SUCCESS | `TWO_DISTINCT_ROOTS` | `VERIFIED_COMPLETE` | Canonical distinct rational roots $\{-2, 2\}$. |
| `ADV-02` | `(x - 1)^2 = 0` | SUCCESS | `UNIQUE_ROOT` | `VERIFIED_COMPLETE` | Repeated root $x=1$ ($\Delta = 0$). |
| `ADV-03` | `x^2 + 1 = 0` over $\mathbb{R}$ | SUCCESS | `NO_REAL_ROOT` | `VERIFIED_COMPLETE` | Negative discriminant $\Delta = -4 < 0$. |
| `ADV-04` | `x^4 - 5*x^2 + 4 = 0` | OUT_OF_SCOPE | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Degree 4 exceeds quadratic bound. |
| `ADV-05` | Forged missing root (solver claims only $\{2\}$ for $x^2-4=0$) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host Vieta check fails ($2+0 \ne 0$). |
| `ADV-06` | Forged extra root (solver claims $\{-2, 2, 0\}$) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host root count and residual checks fail. |
| `ADV-07` | Wrong sign on root (solver claims $\{2, 2\}$ for $x^2-4=0$) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Vieta product check fails ($2 \cdot 2 = 4 \ne -4$). |
| `ADV-08` | Incomplete root list (solver claims $\emptyset$ for $x^2-4=0$) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host proves $\Delta = 16 > 0$, contradicts empty claim. |
| `ADV-09` | Solver claims SUCCESS but non-zero S2 residual | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | S2 `CHECK_CANDIDATE` fails closed. |
| `ADV-10` | Malformed wire rational (float/string corruption) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Strict wire regex and canonical check reject. |
| `ADV-11` | Worker timeout during solve (> 5.0s) | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Monotonic deadline kills worker cleanly. |
| `ADV-12` | Worker timeout during candidate check | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Remaining budget exhaustion triggers timeout. |
| `ADV-13` | Memory exhaustion (deep nested AST) | FAIL CLOSED | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Host node budget catches before worker spawn. |
| `ADV-14` | Response size overflow (> 16 KiB) | FAIL CLOSED | `ENGINE_ERROR` | `NOT_APPLICABLE` | `_build_bounded_response` enforces byte ceiling. |
| `ADV-15` | Protocol version mismatch (`mke.p99.v1`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Schema validation fails closed. |
| `ADV-16` | Forged classification (`TWO_DISTINCT_ROOTS` on $\Delta < 0$) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host discriminant proof refutes solver claim. |
| `ADV-17` | Transcendental input `sin(x) = 0` | OUT_OF_SCOPE | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Host parser / AST check rejects FunctionCall. |
| `ADV-18` | Affine regression `x = 1` | SUCCESS | `UNIQUE_ROOT` | `VERIFIED_COMPLETE` | Seamless B0 backward compatibility. |
| `ADV-19` | Affine identity `x = x` | SUCCESS | `ALL_REALS` | `VERIFIED_COMPLETE` | $A=0, B=0, C=0$ degenerate case. |
| `ADV-20` | Affine contradiction `x = x + 1` | SUCCESS | `EMPTY_SET` | `VERIFIED_COMPLETE` | $A=0, B=0, C=1$ degenerate case. |

---

## 13. Acceptance Criteria

For P1C-04-B1 implementation to be accepted by the independent auditor:
1. **Scope Precision:** Strictly confined to univariate real quadratics with rational coefficients.
2. **Zero In-Process Uncontained CAS:** No uncontained SymPy execution in the host process.
3. **Independent Mathematical Verification:** Every `VERIFIED_COMPLETE` result must have independent host reduction, discriminant calculation, Vieta validation, and S2 candidate verification.
4. **Clean Evidence Architecture:** Test evidence must be generated from a clean git working tree outside the repo worktree, with exact SHA256 checksums matching committed logs.
5. **Zero Baseline Regressions:** 100% pass rate across all existing B0 suites (692+ tests).

---

## 14. Rejection Criteria

The implementation MUST be rejected if any of the following occur:
1. SymPy or external symbolic libraries are invoked on the host side.
2. Degree $\ge 3$ polynomials, rational equations, radicals, or transcendentals are admitted to worker dispatch.
3. Solver outputs are accepted without host-derived discriminant and Vieta checks.
4. Existing B0 affine tests or protocol schemas are weakened or broken.
5. Non-Windows environments fail with unhandled exceptions instead of `ERR_PLATFORM_NOT_SUPPORTED`.

---

## 15. Deferred Capabilities

The following capabilities are explicitly deferred to subsequent milestones:
- Polynomial equations of degree $\ge 3$ (Cubic, Quartic, General Quintic+).
- Rational equations involving variable denominators ($\frac{P(x)}{Q(x)} = 0$).
- Equations involving algebraic radicals ($\sqrt{P(x)} = Q(x)$).
- Exponential, logarithmic, and trigonometric equations.
- Systems of simultaneous linear or nonlinear equations.
- Algebraic inequalities over $\mathbb{R}$.

---

## 16. Open Risks & Mitigations

1. **Risk:** Irrational quadratic roots (e.g. $x^2 - 2 = 0 \implies x = \pm \sqrt{2}$) cannot be represented as simple rationals.
   - **Mitigation:** In Stage 1, restrict `VERIFIED_COMPLETE` to rational roots ($\Delta = k^2$) and no-real-root ($\Delta < 0$). Irrational roots return `UNVERIFIED_CLAIM` until an exact quadratic radical wire type is established.
2. **Risk:** Host polynomial expansion complexity for deeply parenthesized expressions.
   - **Mitigation:** Strict 100-node AST budget and 256-bit coefficient limit prevent exponential coefficient growth.
3. **Risk:** Performance overhead of multiple S2 `CHECK_CANDIDATE` calls for two-root quadratics.
   - **Mitigation:** S2 evaluation takes $< 1$ ms per root; 5.0-second budget is more than sufficient for two sequential checks.
