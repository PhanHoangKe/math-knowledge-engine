# P1C-04-B1 CONTAINED SOLVE CAPABILITY EXPANSION PREFLIGHT (REVISED R1)

- **Document:** `docs/architecture/P1C_04_B1_CONTAINED_SOLVE_EXPANSION_PREFLIGHT.md`
- **Milestone:** `PRODUCT-03C-P1C-04-B1-PREFLIGHT-R1`
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Branch:** `product/p03c-p1c-04-b1-contained-solve-preflight`
- **Base Baseline Commit:** `147f561a883c6d5ea75febe7857e00291107b6da` (P1C-04-B0-R3 Accepted & Locked)
- **Status:** `PREFLIGHT SPECIFICATION R1 — PENDING INDEPENDENT AUDIT`
- **Date:** 2026-09-30

---

## 1. Executive Decision

The Math Knowledge Engine (MKE) has established and locked the P1C-04-B0 baseline (`147f561a883c6d5ea75febe7857e00291107b6da`), providing safe, deterministic, Windows-contained execution and independent verification for **single-variable affine linear equations** ($Ax + B = 0$ over $\mathbb{Q}$).

### Core Finding & Bounded Scope
Expanding contained execution to **Exact Real Quadratic Equations in One Variable $x$ with Rational Coefficients** is **FEASIBLE AND SAFE** under a strictly bounded, non-symbolic implementation contract.

To guarantee absolute mathematical soundness, the B1 scope is strictly confined to cases where the solution set over $\mathbb{R}$ is fully representable in exact rationals $\mathbb{Q}$:
1. **$\Delta < 0$**: Provably no real roots ($\emptyset / \text{EMPTY\_SET}$).
2. **$\Delta = 0$**: Provably one unique rational root ($x = -B / (2A) \in \mathbb{Q}$).
3. **$\Delta > 0$ and $\Delta$ is an exact rational square**: Provably two distinct rational roots ($x_1, x_2 \in \mathbb{Q}$).

### Explicit Preflight Exclusions
- **Irrational Quadratic Roots ($\Delta > 0$ not a rational square, e.g., $x^2 - 2 = 0$):** Explicitly **DEFERRED** in B1. Fails closed with `UNSUPPORTED_EXACT_ROOT_REPRESENTATION`. Zero floating-point approximations, zero fabricated radical wire transports.
- **Polynomials of Degree $\ge 3$, Rational Equations, Radicals, and Transcendentals:** Explicitly **OUT OF SCOPE AND DEFERRED**.
- **SymPy in Contained Kernel:** Prohibited. B1 implements pure-Python integer/rational quadratic arithmetic to eliminate symbolic attack surfaces.

---

## 2. Actual-Code Inventory

The current execution, containment, and protocol architecture relies on the following codebase inventory:

| Module / File Path | Architectural Role | Current Status in B0-R3 |
| :--- | :--- | :--- |
| `src/mke_product/cas/bridge.py` | Controlled dispatch bridge, intake taxonomy mapping, AST affine extraction, independent proof checker | **LOCKED & VERIFIED** (Affine $Ax+B=0$ only; 5.0s cumulative deadline) |
| `src/mke_product/worker/controller.py` | Win32 Job Object manager (256MB process, 512MB job, 10.0s default timeout, restricted tokens) | **FROZEN & VERIFIED** (`DEFAULT_WORKER_TIMEOUT_SEC = 10.0`) |
| `src/mke_product/worker/entrypoint.py` | Disposable worker stdin/stdout length-prefixed IPC entrypoint | **FROZEN & VERIFIED** (Locked to `mke.p02a.v1` envelope) |
| `src/mke_product/protocol/schema.py` | Protocol definitions, wire rational serializer, length bounds | **FROZEN** (`SCHEMA_VERSION = "mke.p02a.v1"`, single `root` field) |
| `src/mke_product/protocol/validator.py` | In-worker request framing and version validator | **FROZEN** (Validates `mke.p02a.v1` and operations `SOLVE`, `CHECK_CANDIDATE`) |
| `src/mke_product/protocol/dispatcher.py` | Mathematical request dispatcher | **FROZEN** (Dispatches `mke.p02a.v1` to `solve_equation` or `check_candidate`) |
| `src/mke_product/parser/parser.py` | Contained-worker deterministic AST parser | **FROZEN** (P02A grammar: literals, $x$, $+,-,*,/$, $( )$, exponents $0,1,2$, $=$) |
| `src/mke_product/solver/solver.py` | In-worker pure-rational affine solver kernel ($Ax+B=0$) | **FROZEN** (Affine linear only) |
| `src/mke_product/solver/affine.py` | In-worker affine AST coefficient extractor over $\mathbb{Q}$ | **FROZEN** (Belongs to accepted affine kernel — DO NOT MODIFY FOR B1) |
| `src/mke_product/solver/scope.py` | Pre-simplification linearity and scope checker | **FROZEN** (Rejects power $\ge 2$ in affine kernel) |
| `src/mke_product/evaluator/evaluator.py` | S2 Candidate verification engine (`CHECK_CANDIDATE`) | **FROZEN** (Evaluates exact rational candidates) |
| `src/mke_product/cas/router.py` | In-process uncontained routing (legacy/demo) | **PROHIBITED** from worker bridge |
| `src/mke_product/cas/sympy_adapter.py` | SymPy-based solver adapter (P1B transcendental/system) | **UNCONTAINED** (Prohibited in worker kernel) |

---

## 3. Existing Execution Path & Worker Timeout Model

### End-to-End Execution Flow
```
[Raw Query + MKE-IR Payload]
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
   - Host Polynomial Degree Check:
       * Degree <= 1 ──► Delegate to accepted B0 affine path (`mke.p02a.v1` SOLVE)
       * Degree == 2 ──► Proceed to B1 quadratic path (`mke.p02a.v2` SOLVE_QUADRATIC)
       * Degree > 2  ──► Reject `ERR_OUT_OF_SCOPE`
             │
        (Degree == 2)
             ▼
 [3. WorkerController & Win32 Job Object]
   - Spawns `python -m mke_product.worker.entrypoint`
   - Win32 Job Object Limits: 256 MiB Process, 512 MiB Job, Kill-on-Close, No Breakaway
   - Bridge Policy Deadline Budget: Shared monotonic 5.0s cumulative wall-clock budget
   - Passes `timeout_sec = remaining_budget` to WorkerController
             │
             ▼
 [4. Worker Process: `entrypoint.py`]
   - Reads length prefix + JSON payload from stdin
   - Passes to `protocol.dispatcher.dispatch_request`
             │
             ▼
 [5. Protocol Dispatcher & Quadratic Solver Kernel]
   - Validates version (`mke.p02a.v2`) and operation (`SOLVE_QUADRATIC`)
   - Parses AST via contained parser
   - Dispatches to pure-Python quadratic solver (`mke_product.solver.quadratic`)
   - Formats JSON response (`mke.p02a.v2`, `outcome: "SUCCESS"`, `status: "..."`, `roots: [...]`, `discriminant: {...}`)
             │
             ▼
 [6. Worker Response Transport]
   - Length-prefixed framing written to stdout (max 16 KiB)
   - WorkerController reads stdout, terminates disposable worker
             │
             ▼
 [7. Host Independent Verification Gate]
   - Validates envelope, schema version, operation echo, outcome, definedness
   - Host Independently Computes: $A, B, C$, $\Delta = B^2 - 4AC$, rational square test, expected roots
   - Matches worker roots against host expected roots (sorted canonically)
   - Dispatches defense-in-depth `CHECK_CANDIDATE` for each rational root with remaining budget
   - Projects authoritative `ControlledDispatchResult(is_verified=True, verification_status=VERIFIED_COMPLETE)`
```

### Worker Timeout Architecture Contract
- **WorkerController Default:** `DEFAULT_WORKER_TIMEOUT_SEC = 10.0` seconds (defined in `constants.py`).
- **Bridge Policy Cumulative Budget:** The accepted B0 bridge and future B1 bridge enforce a **shared 5.0-second monotonic wall-clock budget**.
- **Deadline Inheritance:** The bridge calculates `remaining_budget = max(0.0, 5.0 - elapsed)` and passes it explicitly as `timeout_sec=remaining_budget` to `WorkerController.execute_request()`.
- **Invariance:** The WorkerController's 10.0-second fallback default **MUST NOT** be used to expand or weaken the public 5.0-second B1 deadline contract.

---

## 4. Capability Matrix: Contained Worker vs. Broader CAS

The matrix explicitly distinguishes **Current Contained-Worker Parser & Kernel Capability** (`src/mke_product/parser/parser.py`) from **Broader CAS / P1B Experimental Capability**:

| # | Mathematical Capability | Contained-Worker Parser Support | Broader CAS / P1B Parser Support | Contained-Worker Solver Kernel | Contained-Worker Protocol (`mke.p02a.v1`) | Containment Status | Independent Verification Authority | Contained Domain Certainty | Resource Bound Safety | Preflight Disposition |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Affine Equation** ($Ax+B=0$) | **Yes** | Yes | Yes (Pure $\mathbb{Q}$) | **Supported** (`root`) | Contained | Host Reduction + Vieta + S2 | Everywhere defined on $\mathbb{R}$ | Safe (Bounded bits) | `SUPPORTED_NOW` |
| 2 | **Quadratic: Rational Roots** ($\Delta = k^2$) | **Yes** (Exponent 2 supported) | Yes | Proposed (`solver/quadratic.py`) | Requires v2 (`roots`) | Contained | Host Discriminant + Rational Square + Vieta + S2 | Everywhere defined on $\mathbb{R}$ | Safe (Bounded intermediates) | `SAFE_TO_ADD_WITH_BOUNDED_CHANGE` |
| 3 | **Quadratic: No Real Roots** ($\Delta < 0$) | **Yes** | Yes | Proposed (`solver/quadratic.py`) | Requires v2 (`roots: []`) | Contained | Host Discriminant Proof ($\Delta < 0$) | Everywhere defined on $\mathbb{R}$ | Safe | `SAFE_TO_ADD_WITH_BOUNDED_CHANGE` |
| 4 | **Quadratic: Irrational Roots** ($\Delta > 0, \sqrt{\Delta} \notin \mathbb{Q}$) | **Yes** | Yes | Deferred in B1 | Unsupported in v1/v2 | Contained | Requires Exact Radical Engine | Everywhere defined on $\mathbb{R}$ | Safe | `DEFER` (`UNSUPPORTED_EXACT_ROOT_REPRESENTATION`) |
| 5 | **Polynomial Degree 3–4** (Cubic/Quartic) | **No** (Exponent > 2 rejected) | Yes | P1B only (SymPy) | Unsupported | Contained | Complex (Sturm / Isolating intervals) | Everywhere defined on $\mathbb{R}$ | Medium | `DEFER` |
| 6 | **Polynomial Degree $\ge 5$** | **No** | Yes | P1B only (SymPy) | Unsupported | Contained | Algebraic number isolation | Everywhere defined on $\mathbb{R}$ | High Risk | `DEFER` |
| 7 | **Rational Equation** ($\frac{P(x)}{Q(x)}=0$) | **No** (Var denominator rejected) | Yes | P1B only (SymPy) | Unsupported | Contained | Requires pole/singularity tracking | Singular at $Q(x)=0$ | Medium | `REQUIRES_NEW_VERIFIER` |
| 8 | **Algebraic Radical Equation** | **No** (No `sqrt` token) | Yes | P1B only (SymPy) | Unsupported | Contained | Requires branch check | Restricted ($P(x) \ge 0$) | High Risk | `REQUIRES_NEW_VERIFIER` |
| 9 | **Exponential Equation** ($a^x=b$) | **No** (No `exp` token) | Yes | P1B only (SymPy) | Unsupported | Contained | Requires transcendental CAS | Restricted | High Risk | `DEFER` |
| 10 | **Logarithmic Equation** ($\log_a x=b$) | **No** (No `log`/`ln` token) | Yes | P1B only (SymPy) | Unsupported | Contained | Requires branch/cut verifier | Restricted ($x>0, a>0, a\ne 1$) | High Risk | `DEFER` |
| 11 | **Trigonometric Equation** ($\sin x=a$) | **No** (No `sin`/`cos`/`tan` token) | Yes | P1B only (SymPy) | Unsupported | Contained | Requires periodic family verifier | Periodic | High Risk | `DEFER` |
| 12 | **System of Equations** | **No** (No system grammar) | Yes | P1B only (LinearSystem) | Unsupported | Contained | Requires matrix/elimination proof | Multivariable | High Risk | `DEFER` |
| 13 | **Inequality** ($P(x)>0$) | **No** (No inequality tokens) | Yes | P1B only (Inequality) | Unsupported | Contained | Requires sign chart verifier | Everywhere defined | High Risk | `DEFER` |
| 14 | **CHECK_CANDIDATE (Rational)** | **Yes** | Yes | Yes (S2 Evaluator) | **Supported** | Contained | S2 AST Residual == 0 | Exact | Safe | `SUPPORTED_NOW` |

---

## 5. Audit of P1B Functionality Reuse Inside Worker Boundary

### Architectural Analysis
P1B contains extensive symbolic solving functionality based on SymPy (`src/mke_product/cas/sympy_adapter.py`).

### Decision: Reject SymPy in Contained Worker Kernel for B1
1. **Attack Surface & Boundedness:** SymPy is an unconstrained symbolic computer algebra system with millions of lines of code. Invoking SymPy introduces broad memory allocation patterns, potential recursion depth issues, and unpredictable internal algorithmic branches (e.g., Groebner bases, polynomial factorization heuristics).
2. **Determinism & Simplicity:** Univariate quadratic equations with rational coefficients require only basic arithmetic operations ($+,-,*,/$ and integer square root `math.isqrt`). Implementing a pure-Python deterministic solver using the existing `Rational` class is straightforward, self-contained, and completely bounded.
3. **Verification Independence:** Host independent verification relies on pure arithmetic proofs. A lightweight in-worker solver aligns perfectly with the host proof checker.

---

## 6. Protocol Versioning & Dual-Version Architecture

### Identification of Current Stack v1 Dependencies
The current repository contains hardcoded v1 assumptions across multiple layers:
1. `src/mke_product/protocol/schema.py`: Hardcoded `SCHEMA_VERSION = "mke.p02a.v1"`, single `root` field serializer.
2. `src/mke_product/protocol/validator.py`: Asserts `schema_version == "mke.p02a.v1"`, allowlists only `{"SOLVE", "CHECK_CANDIDATE"}`.
3. `src/mke_product/worker/controller.py`: Imports `SCHEMA_VERSION = "mke.p02a.v1"`, enforces `ALLOWED_OPERATIONS = {"SOLVE", "CHECK_CANDIDATE"}`, generates v1-formatted controller error envelopes.
4. `src/mke_product/worker/entrypoint.py`: Imports `SCHEMA_VERSION = "mke.p02a.v1"`, emits v1 protocol failure envelopes on IPC framing errors.

### B1 Dual-Version Protocol Design (`mke.p02a.v2`)
To avoid breaking accepted B0 tests while supporting quadratic multi-root results:

1. **Protocol Declarations:**
   - `SCHEMA_VERSION_V1 = "mke.p02a.v1"` (Frozen)
   - `SCHEMA_VERSION_V2 = "mke.p02a.v2"` (New)
   - `SUPPORTED_SCHEMA_VERSIONS = (SCHEMA_VERSION_V1, SCHEMA_VERSION_V2)`
2. **Operation Specialization:**
   - `OPERATION_SOLVE = "SOLVE"` (v1 only: Affine linear equation)
   - `OPERATION_CHECK_CANDIDATE = "CHECK_CANDIDATE"` (v1 & v2: Rational candidate check)
   - `OPERATION_SOLVE_QUADRATIC = "SOLVE_QUADRATIC"` (v2 only: Quadratic equation)
3. **WorkerController & Entrypoint Version Awareness:**
   - `WorkerController` allowlist updated to: `ALLOWED_OPERATIONS = {"SOLVE", "CHECK_CANDIDATE", "SOLVE_QUADRATIC"}`.
   - Controller-side and Entrypoint error envelopes inherit the requested `schema_version` from the request payload, falling back to `mke.p02a.v1` only if unparseable.
4. **Dispatcher Version Routing:**
   - If `schema_version == "mke.p02a.v1"` and `operation == "SOLVE"`: routes to `solve_equation()` (frozen affine solver).
   - If `schema_version == "mke.p02a.v2"` and `operation == "SOLVE_QUADRATIC"`: routes to `solve_quadratic_equation()` (new pure-Python quadratic solver).
5. **v2 Wire Response Schema (`SOLVE_QUADRATIC`):**
```json
{
  "schema_version": "mke.p02a.v2",
  "operation": "SOLVE_QUADRATIC",
  "outcome": "SUCCESS",
  "status": "TWO_DISTINCT_REAL_ROOTS",
  "roots": [
    {"numerator": "-2", "denominator": "1"},
    {"numerator": "2", "denominator": "1"}
  ],
  "discriminant": {"numerator": "16", "denominator": "1"},
  "definedness": true,
  "error": null,
  "is_provisional_evidence": false
}
```

---

## 7. Mathematical Verification Contract & Independence Trust Model

### Independence Trust Domain Segregation
```
┌────────────────────────────────────────────────────────────────────────┐
│ UNTRUSTED / SAME-CONTAINED-BOUNDARY EVIDENCE (Worker Process)          │
│ - Worker status string ("TWO_DISTINCT_REAL_ROOTS")                     │
│ - Worker discriminant object                                           │
│ - Worker roots list                                                    │
│ - Worker internal execution state                                      │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ (Submitted via IPC)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ DEFENSE-IN-DEPTH CONTAINED PASS (Worker Process)                       │
│ - CHECK_CANDIDATE evaluates LHS(r) - RHS(r) == 0 on unreduced AST      │
│ - Evaluated in worker sandbox, subject to deadline budget              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ (Submitted via IPC)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ AUTHORITATIVE TRUSTED INDEPENDENT PROOF (Host Process)                 │
│ 1. Host AST Quadratic Reduction -> Deterministic A, B, C in Q          │
│ 2. Degree Proof -> Verify A != 0                                       │
│ 3. Host Discriminant Evaluation -> Δ = B^2 - 4*A*C in Q                │
│ 4. Host Exact Rational-Square Test -> Deterministic integer isqrt check│
│ 5. Host Closed-Form Root Derivation -> r = (-B +/- isqrt(Δ)) / (2*A)   │
│ 6. Expected Cardinality & Sorting Check -> Canonical root-set matching│
│ 7. Vieta Invariant Checks -> r1 + r2 == -B/A and r1 * r2 == C/A        │
│ 8. Defense-in-Depth S2 Confirmation -> All worker residuals == 0       │
└────────────────────────────────────────────────────────────────────────┘
```

### Deterministic Exact Rational-Square Check
For a reduced rational discriminant $\Delta = \frac{p}{q}$ with $p > 0, q > 0, \gcd(p, q) = 1$:
$\Delta$ is an exact rational square if and only if:
$$\text{math.isqrt}(p)^2 == p \quad \land \quad \text{math.isqrt}(q)^2 == q$$
- **Implementation Rules:** Pure Python integer arithmetic only. Zero floating-point `math.sqrt`. Zero SymPy.
- **Independence:** The host executes this test independently without relying on worker claims.

### Canonical Root-Set Contract
For quadratic equation $Ax^2 + Bx + C = 0$ ($A \ne 0$):
- **Case 1: $\Delta < 0$ (No Real Roots)**
  - Public status: `NO_REAL_ROOT` (Solution set $\emptyset$).
  - Canonical wire `roots`: `[]` (Empty list).
- **Case 2: $\Delta = 0$ (Unique Real Root of Multiplicity 2)**
  - Public status: `UNIQUE_REAL_ROOT`.
  - Canonical wire `roots`: `[r]` where $r = \frac{-B}{2A} \in \mathbb{Q}$ (Reduced Rational).
  - Solution set cardinality is exactly 1.
- **Case 3: $\Delta > 0$ and $\Delta$ is an Exact Rational Square (Two Distinct Roots)**
  - Public status: `TWO_DISTINCT_REAL_ROOTS`.
  - Canonical wire `roots`: `[r_low, r_high]` strictly sorted such that $r_{\text{low}} < r_{\text{high}}$.
- **Rejection Rules:** The host verification gate immediately refutes and fails closed on:
  - Duplicate roots in two-root cases.
  - Unsorted root lists.
  - Root lists with cardinality $\ne$ expected cardinality.
  - Any root $r$ where $r \ne r_{\text{host}}$.
  - Any root with non-zero S2 residual.

---

## 8. Domain-Safety Audit & Counterexamples

| Counterexample Query | Mathematical Nature | Expected Host / Bridge Action | Expected Public Status | Verification Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `x^2 - 4 = 0` | Rational square discriminant ($\Delta = 16 = 4^2$) | In-scope quadratic ($A=1, B=0, C=-4$) | `TWO_DISTINCT_REAL_ROOTS` | `VERIFIED_COMPLETE` (roots: `[-2, 2]`) |
| `(x - 1)^2 = 0` | Zero discriminant ($\Delta = 0$) | In-scope quadratic ($A=1, B=-2, C=1$) | `UNIQUE_REAL_ROOT` | `VERIFIED_COMPLETE` (root: `[1]`) |
| `x^2 + 1 = 0` | Negative discriminant ($\Delta = -4 < 0$) | In-scope quadratic ($A=1, B=0, C=1$) | `NO_REAL_ROOT` | `VERIFIED_COMPLETE` (roots: `[]`) |
| `x^2 - 2 = 0` | Positive non-square discriminant ($\Delta = 8$) | In-scope quadratic AST, but irrational roots | `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` | `NOT_APPLICABLE` (Fail Closed) |
| `x^4 - 5*x^2 + 4 = 0` | Degree 4 (Biquadratic) | Rejected by quadratic degree guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `(x - 1)/(x - 1) = 1` | Variable in denominator | Rejected by parser/bridge scope guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `sqrt(x) = -1` | Radical equation | Rejected by parser (no radical token) | `REJECTED_SYNTAX` (`ERR_SYNTAX_ERROR`) | `NOT_APPLICABLE` (Fail Closed) |
| `sqrt(x^2) = x` | Radical equation | Rejected by parser (no radical token) | `REJECTED_SYNTAX` (`ERR_SYNTAX_ERROR`) | `NOT_APPLICABLE` (Fail Closed) |
| `1/(x - 1) = 0` | Variable in denominator | Rejected by parser/bridge scope guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `2^x = 8` | Variable in exponent | Rejected by parser/bridge scope guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `sin(x) = 0` | Function call | Rejected by parser (no function token) | `REJECTED_SYNTAX` (`ERR_SYNTAX_ERROR`) | `NOT_APPLICABLE` (Fail Closed) |
| `x^0 = 1` | Variable-dependent exponent zero | Rejected by domain safety guard | `REJECTED_SCOPE` (`ERR_OUT_OF_SCOPE`) | `NOT_APPLICABLE` (Fail Closed) |
| `0^0 = 1` | Undefined constant expression | Rejected by constant domain evaluator | `REJECTED_SCOPE` (`ERR_DOMAIN_ERROR`) | `NOT_APPLICABLE` (Fail Closed) |

### Note on General Degree $\ge 5$ Polynomials
General polynomials of degree $\ge 5$ do not admit a general algebraic solution in radicals (Abel-Ruffini theorem). However, exact algebraic-number representations, root isolation intervals, and exact root-counting methods (e.g., Sturm sequences) can mathematically exist. Higher-degree polynomials remain **DEFERRED** in B1 because their exact algebraic representations, protocol schemas, and isolation verifiers are outside B1 scope, not because exact mathematical treatment is impossible.

---

## 9. Resource & Containment Failure Taxonomy

The containment failure handling strictly distinguishes separate failure paths:

```
┌────────────────────────────────────────────────────────────────────────┐
│ CONTAINMENT FAILURE TAXONOMY                                           │
├────────────────────────────┬───────────────────────────────────────────┤
│ Failure Cause              │ Classification & Mapping                  │
├────────────────────────────┼───────────────────────────────────────────┤
│ 5.0s Cumulative Deadline   │ ExecutionStatus.TIMEOUT                   │
│ Exceeded                   │ (Error code: "ERR_TIMEOUT")               │
├────────────────────────────┼───────────────────────────────────────────┤
│ Process / Job Commit Memory│ ExecutionStatus.ENGINE_ERROR              │
│ Quota Exceeded (256/512MB) │ (Mapped from WORKER_RESOURCE_EXHAUSTED    │
│                            │  Error code: "ERR_RESOURCE_EXHAUSTED")    │
├────────────────────────────┼───────────────────────────────────────────┤
│ Serialized Response Exceeds│ ExecutionStatus.ENGINE_ERROR              │
│ 16 KiB Ceiling             │ (Mapped from ERR_RESPONSE_LIMIT_EXCEEDED) │
├────────────────────────────┼───────────────────────────────────────────┤
│ Abnormal Worker Process    │ ExecutionStatus.ENGINE_ERROR              │
│ Termination (Crash / SEH)  │ (Mapped from WORKER_EXIT_FAILURE)         │
└────────────────────────────┴───────────────────────────────────────────┘
```

### Hardened Intermediate Arithmetic Bounds
To prevent integer bit-explosion attacks, every arithmetic step is strictly bounded:
- **Maximum Bit Policy:** 256 bits per integer numerator/denominator.
- **Bounded Intermediates:**
  1. Input coefficients $A, B, C$.
  2. Multiplications: $B^2$, $4AC$, $2A$.
  3. Discriminant: $\Delta = B^2 - 4AC$.
  4. Integer square roots: $\text{isqrt}(p)$, $\text{isqrt}(q)$.
  5. Root numerators/denominators: $-B \pm \text{isqrt}(\Delta)$, $2A$.
  6. Vieta check products and sums: $r_1 + r_2$, $r_1 \cdot r_2$.
- **Action on Overflow:** Any intermediate exceeding 256 bits immediately aborts with `NonQuadraticExpressionError` / `RESOURCE_EXHAUSTED` and fails closed safely.

---

## 10. Implementation File Inventory & Isolation

### Isolation Strategy
- **DO NOT MODIFY ACCEPTED AFFINE FILES:**
  - `src/mke_product/solver/affine.py` remains **100% UNTOUCHED**.
  - `src/mke_product/solver/solver.py` affine solving remains **100% UNTOUCHED**.
  - Existing `mke.p02a.v1` protocol semantics and tests remain **100% UNTOUCHED**.
- **Affine Routing Preservation:**
  - If host AST reduction determines degree $\le 1$ ($A == 0$), the bridge routes directly to the existing accepted B0 affine path (`mke.p02a.v1` `SOLVE`).
  - Queries like `x = 1`, `x = x`, `x = x + 1` never enter the v2 quadratic execution path.

### Proposed File Inventory for B1 Implementation

| File Path | Expected Action | Role in B1 |
| :--- | :---: | :--- |
| `src/mke_product/solver/affine.py` | **NO CHANGE** | Frozen B0 affine extractor. |
| `src/mke_product/solver/solver.py` | **NO CHANGE** | Frozen B0 affine solver kernel. |
| `src/mke_product/solver/quadratic.py` | **CREATE** | Pure-Python deterministic quadratic solver kernel over $\mathbb{Q}$. |
| `src/mke_product/protocol/schema.py` | MODIFY | Declare `mke.p02a.v2`, `OPERATION_SOLVE_QUADRATIC`, v2 multi-root serializers. |
| `src/mke_product/protocol/validator.py` | MODIFY | Add v2 schema and `SOLVE_QUADRATIC` validation rules. |
| `src/mke_product/protocol/dispatcher.py` | MODIFY | Route v2 requests to `solve_quadratic_equation()`. |
| `src/mke_product/worker/controller.py` | MODIFY | Allow `SOLVE_QUADRATIC` in `ALLOWED_OPERATIONS`, version-aware error envelopes. |
| `src/mke_product/worker/entrypoint.py` | MODIFY | Version-aware IPC error envelopes. |
| `src/mke_product/cas/bridge.py` | MODIFY | Add host quadratic AST reduction, exact rational-square test, Vieta verification gate, degree routing. |
| `tests/test_p03c_p1c_quadratic_dispatch.py` | **CREATE** | Unit, integration, and adversarial tests for B1 quadratic dispatch. |

---

## 11. Required Adversarial Test Plan

| Test ID | Input Scenario | Expected Outcome | Public Status | Verification Status | Verification Rule Checked |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ADV-01` | `x^2 - 4 = 0` | SUCCESS | `TWO_DISTINCT_REAL_ROOTS` | `VERIFIED_COMPLETE` | Distinct roots `[-2, 2]`, $\Delta = 16$. |
| `ADV-02` | `(x - 1)^2 = 0` | SUCCESS | `UNIQUE_REAL_ROOT` | `VERIFIED_COMPLETE` | Repeated root `[1]`, $\Delta = 0$. |
| `ADV-03` | `x^2 + 1 = 0` over $\mathbb{R}$ | SUCCESS | `NO_REAL_ROOT` | `VERIFIED_COMPLETE` | Negative discriminant $\Delta = -4 < 0$. |
| `ADV-04` | `x^2 - 2 = 0` (Irrational root) | FAIL CLOSED | `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` | `NOT_APPLICABLE` | $\Delta = 8$ is not a rational square; fails closed. |
| `ADV-05` | Forged rational roots for `x^2 - 2` | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host rational square check refutes worker claim. |
| `ADV-06` | Forged missing root for `x^2 - 4` (worker claims `[2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host cardinality mismatch ($1 \ne 2$). |
| `ADV-07` | Forged extra root for `x^2 - 4` (worker claims `[-2, 2, 0]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host cardinality mismatch ($3 \ne 2$). |
| `ADV-08` | Unsorted roots for `x^2 - 4` (worker claims `[2, -2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Strict sorting assertion $r_{\text{low}} < r_{\text{high}}$ fails. |
| `ADV-09` | Duplicate roots in two-root case (worker claims `[2, 2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Vieta product check fails ($2 \cdot 2 = 4 \ne -4$). |
| `ADV-10` | Forged discriminant value from worker | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host independent $\Delta$ derivation refutes worker. |
| `ADV-11` | Non-square rational $\Delta = 1/2$ | FAIL CLOSED | `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` | `NOT_APPLICABLE` | $\text{isqrt}(1)^2=1$ but $\text{isqrt}(2)^2 \ne 2$. |
| `ADV-12` | Huge coefficient causing $B^2$ bit overflow (> 256 bits) | FAIL CLOSED | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Intermediate bit bound aborts reduction. |
| `ADV-13` | Huge $4AC$ intermediate overflow (> 256 bits) | FAIL CLOSED | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Intermediate bit bound aborts reduction. |
| `ADV-14` | v1 response returned to v2 request | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Schema mismatch rejected. |
| `ADV-15` | Controller-level failure during v2 request | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Controller emits version-matching envelope. |
| `ADV-16` | S2 non-zero residual attack on quadratic root | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | S2 `CHECK_CANDIDATE` fails closed. |
| `ADV-17` | Worker timeout during solve (> 5.0s) | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Bridge 5.0s cumulative budget kills worker. |
| `ADV-18` | Worker timeout during S2 check | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Bridge remaining budget kills worker. |
| `ADV-19` | Degenerate $A=0$ equation (`2*x + 4 = 0`) | SUCCESS | `UNIQUE_ROOT` | `VERIFIED_COMPLETE` | Host routes to B0 v1 path, bypassing v2. |
| `ADV-20` | Affine identity regression (`x = x`) | SUCCESS | `ALL_REALS` | `VERIFIED_COMPLETE` | Routed to B0 v1 path, exact B0 behavior. |
| `ADV-21` | Affine contradiction regression (`x = x + 1`) | SUCCESS | `EMPTY_SET` | `VERIFIED_COMPLETE` | Routed to B0 v1 path, exact B0 behavior. |
| `ADV-22` | B0 Full Regression Suite (41 tests) | PASS | - | - | 100% pass on `test_p03c_p1c_controlled_dispatch.py`. |
| `ADV-23` | Windows Containment Full Regression (80 tests) | PASS | - | - | 100% pass on `test_worker_windows.py`. |

---

## 12. Final Preflight Decision & Recommendation

### P1C-04-B1 Implementation Candidate Recommendation
**AUTHORIZE ONLY:**
Exact univariate real quadratic equations with rational coefficients:
$$A x^2 + B x + C = 0 \quad (A \ne 0, A, B, C \in \mathbb{Q})$$
satisfying:
- $\Delta < 0 \implies \text{NO\_REAL\_ROOT}$ ($\emptyset$), OR
- $\Delta = 0 \implies \text{UNIQUE\_REAL\_ROOT}$ ($x \in \mathbb{Q}$), OR
- $\Delta > 0 \land \Delta$ is an exact rational square $\implies \text{TWO\_DISTINCT\_REAL\_ROOTS}$ ($x_1, x_2 \in \mathbb{Q}$).

### Strict Restrictions for B1 Implementation
1. **NO SymPy inside contained worker:** Pure-Python quadratic solver kernel only.
2. **NO floating-point approximations:** Exact rational arithmetic only.
3. **NO irrational root transport:** $\Delta > 0$ non-square fails closed with `UNSUPPORTED_EXACT_ROOT_REPRESENTATION`.
4. **NO modifications to `solver/affine.py`:** Accepted affine kernel remains locked.
5. **NO weakening of 5.0s deadline:** Cumulative bridge deadline strictly preserved.
6. **NO degree $\ge 3$, rational equations, radicals, or transcendentals:** All deferred.
