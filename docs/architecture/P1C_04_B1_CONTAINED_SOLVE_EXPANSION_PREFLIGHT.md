# P1C-04-B1 CONTAINED SOLVE CAPABILITY EXPANSION PREFLIGHT (FINAL R2)

- **Document:** `docs/architecture/P1C_04_B1_CONTAINED_SOLVE_EXPANSION_PREFLIGHT.md`
- **Milestone:** `PRODUCT-03C-P1C-04-B1-PREFLIGHT-R2`
- **Implementer:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Branch:** `product/p03c-p1c-04-b1-contained-solve-preflight`
- **Parent R1 Commit:** `97a653f23dbd56b96fcf1d9889925025e289d126`
- **Base Baseline Commit:** `147f561a883c6d5ea75febe7857e00291107b6da` (P1C-04-B0-R3 Accepted & Locked)
- **Status:** `FINAL PREFLIGHT SPECIFICATION R2 — PENDING INDEPENDENT AUDIT`
- **Date:** 2026-09-30

---

## 1. Executive Decision

The Math Knowledge Engine (MKE) has established and locked the P1C-04-B0 baseline (`147f561a883c6d5ea75febe7857e00291107b6da`), providing safe, deterministic, Windows-contained execution and independent verification for **single-variable affine linear equations** ($Ax + B = 0$ over $\mathbb{Q}$).

### Core Finding & Bounded B1 Scope
Expanding contained execution to **Exact Real Quadratic Equations in One Variable $x$ with Rational Coefficients** is **FEASIBLE AND SAFE** under a strictly bounded, non-symbolic implementation contract.

To guarantee absolute mathematical soundness, the B1 scope is strictly confined to cases where the solution set over $\mathbb{R}$ is fully representable in exact rationals $\mathbb{Q}$:
1. **$\Delta < 0$**: Provably no real roots ($\emptyset / \text{NO\_REAL\_ROOT}$).
2. **$\Delta = 0$**: Provably one unique rational root ($x = -B / (2A) \in \mathbb{Q}$).
3. **$\Delta > 0$ and $\Delta$ is an exact rational square**: Provably two distinct rational roots ($x_1, x_2 \in \mathbb{Q}$).

### Explicit Preflight Exclusions
- **Irrational Quadratic Roots ($\Delta > 0$ not a rational square, e.g., $x^2 - 2 = 0$):** Fails closed **BEFORE WORKER DISPATCH** as `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` (`execution_status=NOT_DISPATCHED`, `verification_status=NOT_APPLICABLE`, `is_verified=False`). Zero floating-point approximations, zero fabricated radical wire transports.
- **Polynomials of Degree $\ge 3$, Rational Equations, Radicals, and Transcendentals:** Explicitly **OUT OF SCOPE AND DEFERRED**.
- **SymPy in Contained Kernel:** Strictly prohibited. B1 implements pure-Python integer/rational quadratic arithmetic to eliminate symbolic attack surfaces.

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

## 3. Existing Execution Path & Worker Timeout Architecture

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
   - Host Polynomial Quadratic Reduction & Degree Check:
       * Degree <= 1 ──► Delegate to accepted B0 affine path (`mke.p02a.v1` SOLVE)
       * Degree == 2 ──► Host Computes A, B, C and Δ = B^2 - 4AC:
           - If Δ > 0 and Δ NOT a rational square ──► Fail closed immediately (`ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION`, zero worker spawn)
           - If Δ <= 0 OR Δ is an exact rational square ──► Proceed to B1 quadratic dispatch (`mke.p02a.v2` SOLVE_QUADRATIC)
       * Degree > 2  ──► Reject `ERR_OUT_OF_SCOPE`
             │
        (Degree == 2 and Rational Roots / No Real Roots)
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
   - Validates envelope, schema version (`mke.p02a.v2`), operation echo (`SOLVE_QUADRATIC`), outcome, definedness
   - Host Matches Worker Roots against Independently Derived Host Roots (sorted canonically)
   - Dispatches defense-in-depth `mke.p02a.v1` `CHECK_CANDIDATE` for each rational root with remaining budget
   - Projects authoritative `ControlledDispatchResult(is_verified=True, verification_status=VERIFIED_COMPLETE)`
```

### Worker Timeout Architecture Contract
- **WorkerController Default:** `DEFAULT_WORKER_TIMEOUT_SEC = 10.0` seconds (defined in `constants.py`).
- **Bridge Policy Cumulative Budget:** The accepted B0 bridge and future B1 bridge enforce a **shared 5.0-second monotonic wall-clock budget**.
- **Deadline Inheritance:** The bridge calculates `remaining_budget = max(0.0, 5.0 - elapsed)` and passes it explicitly as `timeout_sec=remaining_budget` to `WorkerController.execute_request()`.
- **Invariance:** The WorkerController's 10.0-second fallback default **MUST NOT** be used to expand or weaken the public 5.0-second B1 deadline contract.

---

## 4. Multi-Layer Capability Matrix: Parser Syntax vs. Scope vs. Solver

The matrix strictly distinguishes **Contained Parser Syntactic Support**, **AST Representability**, **B1 Scope Acceptance**, **Contained Solver Kernel Support**, and **Protocol Capability**:

| # | Mathematical Capability | Contained Parser Syntax | AST Representability | B1 Scope Acceptance | Contained Solver Kernel | Contained Protocol | Preflight Disposition |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Affine Equation** ($Ax+B=0$) | **Yes** | Full | **In Scope** | Supported (`solver/solver.py`) | Supported (`mke.p02a.v1` SOLVE) | `SUPPORTED_NOW` |
| 2 | **Quadratic: Rational Roots** ($\Delta = k^2$) | **Yes** ($x^2$ syntax) | Full | **In Scope** | Proposed (`solver/quadratic.py`) | Supported in v2 (`SOLVE_QUADRATIC`) | `SAFE_TO_ADD_WITH_BOUNDED_CHANGE` |
| 3 | **Quadratic: No Real Roots** ($\Delta < 0$) | **Yes** ($x^2$ syntax) | Full | **In Scope** | Proposed (`solver/quadratic.py`) | Supported in v2 (`roots: []`) | `SAFE_TO_ADD_WITH_BOUNDED_CHANGE` |
| 4 | **Quadratic: Irrational Roots** ($\Delta > 0, \sqrt{\Delta} \notin \mathbb{Q}$) | **Yes** ($x^2$ syntax) | Full | **Rejected** (Deferred) | Deferred in B1 | Unsupported in v1/v2 | `DEFER` (`UNSUPPORTED_EXACT_ROOT_REPRESENTATION`) |
| 5 | **Polynomial Degree $\ge 3$** (e.g. $x*x*x = 1$) | **Partial** (via `$*$`; `^3` rejected) | Full (via `$*$`) | **Rejected** (Degree > 2) | Unsupported | Unsupported | `DEFER` |
| 6 | **Rational Equation** (e.g. $\frac{1}{x-1} = 0$) | **Yes** (`/` syntax supported) | Full | **Rejected** (Var denominator) | Unsupported | Unsupported | `REQUIRES_NEW_VERIFIER` |
| 7 | **Algebraic Radical Equation** ($\sqrt{x} = 1$) | **No** (No `sqrt` token) | No | **Rejected** | Unsupported | Unsupported | `REQUIRES_NEW_VERIFIER` |
| 8 | **Exponential Equation** ($2^x = 8$) | **No** (No `exp` token) | No | **Rejected** | Unsupported | Unsupported | `DEFER` |
| 9 | **Logarithmic Equation** ($\log_2 x = 3$) | **No** (No `log` token) | No | **Rejected** | Unsupported | Unsupported | `DEFER` |
| 10 | **Trigonometric Equation** ($\sin x = 0$) | **No** (No `sin` token) | No | **Rejected** | Unsupported | Unsupported | `DEFER` |
| 11 | **System of Equations** | **No** (No system syntax) | No | **Rejected** | Unsupported | Unsupported | `DEFER` |
| 12 | **Inequality** ($x^2 - 4 > 0$) | **No** (No inequality tokens) | No | **Rejected** | Unsupported | Unsupported | `DEFER` |
| 13 | **CHECK_CANDIDATE (Rational)** | **Yes** | Full | **In Scope** | Supported (`evaluator.py`) | Supported (`mke.p02a.v1`) | `SUPPORTED_NOW` |

---

## 5. Protocol Architecture: Minimizing Surface via Single-Operation v2

### Dual-Version Protocol Boundary
To completely protect the accepted B0 affine baseline from protocol pollution, B1 restricts protocol versioning to the absolute minimum:

```
┌────────────────────────────────────────────────────────────────────────┐
│ mke.p02a.v1 PROTOCOL CONTRACT (FROZEN — 100% UNCHANGED)                │
│ - Operations: "SOLVE" (Affine only), "CHECK_CANDIDATE" (Rational check)│
│ - Request: {"schema_version": "mke.p02a.v1", "operation": "SOLVE", ...}│
│ - Response: {"root": {"numerator": "...", "denominator": "..."}}      │
│ - Used for: All B0 Affine solving + B1 Defense-in-Depth Candidate Checks│
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ mke.p02a.v2 PROTOCOL CONTRACT (NEW — DEDICATED TO QUADRATICS)          │
│ - Operations: "SOLVE_QUADRATIC" ONLY                                   │
│ - Request: {"schema_version": "mke.p02a.v2", "operation": "SOLVE_QUADRATIC", "equation": "<str>"}│
│ - Response: {"roots": [...], "discriminant": {...}, "status": "..."}   │
│ - Used for: Contained Quadratic Solving ONLY                           │
└────────────────────────────────────────────────────────────────────────┘
```

### Defense-in-Depth Candidate Check Uses v1 Protocol
After a successful v2 `SOLVE_QUADRATIC` response, the bridge executes candidate verification using the **existing accepted `mke.p02a.v1` `CHECK_CANDIDATE` operation**.
- No `CHECK_CANDIDATE_V2` is created.
- Candidate checks for $r_1$ and $r_2$ use the exact frozen v1 candidate evaluator.
- Execution sequence:
  $$\text{v2 SOLVE\_QUADRATIC} \longrightarrow \text{Host Proof Check} \longrightarrow \text{v1 CHECK\_CANDIDATE}(r_1) \longrightarrow \text{v1 CHECK\_CANDIDATE}(r_2)$$
  All operations execute sequentially under the single shared 5.0-second cumulative deadline.

---

## 6. Infrastructure/Transport Failures vs. Mathematical Responses

The architecture strictly separates **Infrastructure / Transport Failures** from **Mathematical Protocol Responses**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ LAYER A: INFRASTRUCTURE / TRANSPORT FAILURE BOUNDARY                   │
│ - Emitted by: WorkerController, IPC framing, process startup, Win32 Job│
│ - Triggered on: Pipe break, incomplete frame, payload overflow, memory │
│   quota exhaustion (256/512MB), deadline timeout, abnormal exit.       │
│ - Statuses: WORKER_TIMEOUT, WORKER_RESOURCE_EXHAUSTED, WORKER_EXIT_FAILURE,│
│   ERR_PAYLOAD_TOO_LARGE, ERR_RESPONSE_LIMIT_EXCEEDED.                  │
│ - Handling: The Bridge recognizes allowlisted WORKER_* error statuses  │
│   BEFORE validating mathematical response schemas. These are treated as│
│   infrastructure errors and NEVER reflected as valid mathematical v2.  │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ LAYER B: MATHEMATICAL PROTOCOL RESPONSE BOUNDARY                       │
│ - Emitted by: Mathematical Dispatcher inside worker process.           │
│ - Requires: Successful framing, valid schema_version, valid operation. │
│ - Validation: For a v2 SOLVE_QUADRATIC request, the response MUST have:│
│   schema_version == "mke.p02a.v2" AND operation == "SOLVE_QUADRATIC"   │
│ - Any schema discrepancy or unparseable envelope fails closed as       │
│   ERR_MALFORMED_WORKER_RESPONSE.                                       │
└────────────────────────────────────────────────────────────────────────┘
```

### Prohibition of Arbitrary Schema Reflection
No controller, entrypoint, or dispatcher component may echo an arbitrary caller-supplied `schema_version` (such as `"mke.p99.v1"`, `"AAAA..."`, or Unicode garbage).
- All recognized schemas are matched against a static allowlist: `{"mke.p02a.v1", "mke.p02a.v2"}`.
- Unrecognized or malformed schemas immediately trigger static transport failure envelopes.

---

## 7. Strict v2 Request & Response Contracts

### Strict v2 Request Contract
```json
{
  "schema_version": "mke.p02a.v2",
  "operation": "SOLVE_QUADRATIC",
  "equation": "3*x^2 - 5*x + 2 = 0"
}
```
- **Allowlisted Request Fields EXACTLY:** `{"schema_version", "operation", "equation"}`.
- **Prohibited Fields:** No options, hints, timeouts, degree overrides, caller-supplied coefficients, or root counts.
- **Payload Bounds:** ASCII only, $\le 256$ equation characters, $\le 4096$ total bytes.

### Strict v2 Response Contract
```json
{
  "schema_version": "mke.p02a.v2",
  "operation": "SOLVE_QUADRATIC",
  "outcome": "SUCCESS",
  "status": "TWO_DISTINCT_REAL_ROOTS",
  "roots": [
    {"numerator": "2", "denominator": "3"},
    {"numerator": "1", "denominator": "1"}
  ],
  "discriminant": {
    "numerator": "1",
    "denominator": "1"
  },
  "definedness": true,
  "error": null,
  "is_provisional_evidence": false
}
```
- **Allowed Successful Statuses ONLY:**
  1. `"NO_REAL_ROOT"` (with canonical `roots: []`).
  2. `"UNIQUE_REAL_ROOT"` (with canonical `roots: [r]`).
  3. `"TWO_DISTINCT_REAL_ROOTS"` (with canonical `roots: [r_low, r_high]` where $r_{\text{low}} < r_{\text{high}}$).
- **Canonical Rational Wire Format:** Reduced rational string dict `{"numerator": "<int>", "denominator": "<pos_int>"}`.

---

## 8. Host/Worker Verification Independence Architecture

### Mandatory Non-Shared Implementation Contract
To prevent common-mode verification failure, the **Host Proof Checker** and **Worker Quadratic Solver** **MUST NOT SHARE** the polynomial reduction or solving implementation:

```
┌────────────────────────────────────────────────────────────────────────┐
│ HOST PROCESS (Bridge Gate)                                             │
│ - Implementation: `ControlledDispatchBridge._reduce_quadratic_host()`   │
│ - Derives: host_A, host_B, host_C, host_Δ, host_isqrt_square, expected │
│   roots [r_low, r_high] independently from AST.                        │
│ - NEVER imports or calls `mke_product.solver.quadratic`.               │
└────────────────────────────────────────────────────────────────────────┘
                                    ≠ (NO SHARED REDUCER CODE)
┌────────────────────────────────────────────────────────────────────────┐
│ WORKER PROCESS (Contained Sandbox)                                     │
│ - Implementation: `mke_product.solver.quadratic.solve_quadratic()`     │
│ - Derives: worker_A, worker_B, worker_C, worker_Δ, worker roots        │
│   independently from AST.                                              │
│ - Dispatched strictly across length-prefixed IPC boundary.             │
└────────────────────────────────────────────────────────────────────────┘
```
- **Shared Primitives Allowed:** Foundational immutable structures (`Rational`, AST node dataclasses, `parse_equation`).
- **Shared Solver Code Prohibited:** Host must never call worker solver routines to verify worker outputs.

---

## 9. Quadratic Host Reducer & Exact Degree Routing Contract

### Host Reducer Specification
The host reducer recursively converts grammar-compatible AST expressions to canonical polynomial form:
$$c_2 x^2 + c_1 x + c_0 \quad (c_2, c_1, c_0 \in \mathbb{Q})$$
- **Supported AST Nodes:** `IntegerLiteral`, `Variable("x")`, `UnaryOp(+,-)`, `Group`, `BinaryOp(+,-,*,/)`, `Power(base, exponent=0,1,2)`.
- **Multiplication Rule:** $(p_2 x^2 + p_1 x + p_0) \cdot (q_2 x^2 + q_1 x + q_0)$ is allowed **if and only if** resulting degree $\le 2$. (e.g. $(x+1)*(x-1)$ succeeds with degree 2; $x*x*x$ rejects with degree 3).
- **Division Rule:** Allowed only when denominator is a **provably non-zero constant rational expression**. Division by any variable-dependent expression immediately aborts.
- **Domain Safety Rules:** Fail closed on variable-dependent base with exponent 0, $0^0$, or constant division by zero.

### Exact Degree Routing
After reducing `Equation(LHS, RHS)` to $A x^2 + B x + C = 0$:
1. **If $A == 0$ (Degree $\le 1$):**
   - The equation is affine linear ($Bx + C = 0$).
   - The bridge **DELEGATES DIRECTLY** to the existing, accepted B0 affine execution path (`mke.p02a.v1` `SOLVE`).
   - Equations such as `x = 1`, `x = x`, `x = x + 1`, `0*x^2 + x = 1` bypass v2 quadratic execution entirely.
2. **If $A \ne 0$ (Degree == 2):**
   - The equation is true quadratic.
   - Host computes $\Delta = B^2 - 4AC$.
   - If $\Delta > 0$ and $\Delta$ is NOT a rational square: abort immediately before dispatch with `UNSUPPORTED_EXACT_ROOT_REPRESENTATION`.
   - If $\Delta \le 0$ or $\Delta$ is an exact rational square: dispatch via `mke.p02a.v2` `SOLVE_QUADRATIC`.

---

## 10. Mathematical Proof & Defense-in-Depth Verification Model

### Trust Hierarchy
1. **Host Discriminant Sign Proof ($\Delta = B^2 - 4AC$):** Authoritative proof of real root cardinality (0, 1, or 2).
2. **Host Rational Square Test:**
   $$\Delta = \frac{p}{q} \text{ is a square} \iff \text{math.isqrt}(p)^2 == p \;\land\; \text{math.isqrt}(q)^2 == q$$
3. **Host Root Derivation & Vieta Checks:**
   - For $\Delta = 0$: $2 \cdot r == -B/A$ and $r^2 == C/A$.
   - For $\Delta = k^2$: $r_1 + r_2 == -B/A$ and $r_1 \cdot r_2 == C/A$.
4. **Defense-in-Depth S2 Candidate Evaluation:**
   - Worker evaluates `mke.p02a.v1` `CHECK_CANDIDATE` for each root against original unreduced AST.
   - Residual must be exact 0, definedness True, exact equality True.
5. **Worker Discriminant:** Diagnostic consistency check only ($worker\_\Delta == host\_\Delta$). A forged worker discriminant cannot influence host proof.

---

## 11. Layered Resource & Containment Failure Taxonomy

```
┌────────────────────────────────────────────────────────────────────────┐
│ LAYERED RESOURCE FAILURE CLASSIFICATION                                │
├────────────────────────────┬──────────────────┬────────────────────────┤
│ Failure Condition          │ ExecutionStatus  │ Standardized Error Code│
├────────────────────────────┼──────────────────┼────────────────────────┤
│ 5.0s Cumulative Deadline   │ TIMEOUT          │ ERR_TIMEOUT            │
│ Memory Commit Limit (256MB)│ ENGINE_ERROR     │ ERR_RESOURCE_EXHAUSTED │
│ Response Overflow (>16 KiB)│ ENGINE_ERROR     │ ERR_RESPONSE_LIMIT_EXC │
│ Abnormal Process Exit      │ ENGINE_ERROR     │ ERR_WORKER_EXIT_FAILURE│
│ Intermediate Bit Overflow  │ NOT_DISPATCHED   │ ERR_OUT_OF_SCOPE       │
│ Irrational Root Quadratic  │ NOT_DISPATCHED   │ ERR_UNSUPPORTED_EXACT_ │
│                            │                  │ ROOT_REPRESENTATION    │
└────────────────────────────┴──────────────────┴────────────────────────┘
```

### Hardened 256-Bit Intermediate Bounds
Every arithmetic intermediate is checked against a 256-bit integer ceiling:
- $A, B, C$, $B^2$, $4AC$, $\Delta$, $2A$, $\text{isqrt}(p)$, $\text{isqrt}(q)$, $-B \pm k$, final roots, Vieta sums and products.
- Any overflow aborts safely without uncontained memory expansion.

---

## 12. Final Implementation File Inventory

### Files Expected to Remain 100% UNCHANGED
- `src/mke_product/solver/affine.py` (Accepted B0 affine extractor)
- `src/mke_product/solver/solver.py` (Accepted B0 affine solver kernel)
- All existing B0 test suites and evidence records.

### Files to Create
- `src/mke_product/solver/quadratic.py` (Pure-Python deterministic quadratic solver kernel over $\mathbb{Q}$)
- `tests/test_p03c_p1c_quadratic_dispatch.py` (Quadratic unit, integration, and adversarial test suite)

### Files Expected to Require Narrow B1 Changes
- `src/mke_product/protocol/schema.py` (Declare `mke.p02a.v2`, `OPERATION_SOLVE_QUADRATIC`, v2 serializers)
- `src/mke_product/protocol/validator.py` (Validate v2 request schema and `SOLVE_QUADRATIC` fields)
- `src/mke_product/protocol/dispatcher.py` (Route v2 `SOLVE_QUADRATIC` to `solve_quadratic_equation`)
- `src/mke_product/worker/controller.py` (Allow `SOLVE_QUADRATIC` in `ALLOWED_OPERATIONS`)
- `src/mke_product/cas/bridge.py` (Host quadratic reduction, rational square test, Vieta checks, degree routing)

---

## 13. Comprehensive Adversarial Test Plan

| Test ID | Input Scenario | Expected Outcome | Public Status | Verification Status | Verification Rule Tested |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ADV-01` | `x^2 - 4 = 0` | SUCCESS | `TWO_DISTINCT_REAL_ROOTS` | `VERIFIED_COMPLETE` | Distinct rational roots `[-2, 2]`, $\Delta = 16$. |
| `ADV-02` | `(x - 1)^2 = 0` | SUCCESS | `UNIQUE_REAL_ROOT` | `VERIFIED_COMPLETE` | Repeated rational root `[1]`, $\Delta = 0$. |
| `ADV-03` | `x^2 + 1 = 0` | SUCCESS | `NO_REAL_ROOT` | `VERIFIED_COMPLETE` | Negative discriminant $\Delta = -4 < 0$, roots `[]`. |
| `ADV-04` | `x^2 - 2 = 0` | NOT_DISPATCHED | `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` | `NOT_APPLICABLE` | $\Delta = 8$ (non-square); zero worker spawn. |
| `ADV-05` | Positive non-square $\Delta = 1/2$ | NOT_DISPATCHED | `UNSUPPORTED_EXACT_ROOT_REPRESENTATION` | `NOT_APPLICABLE` | $\text{isqrt}(2)^2 \ne 2$; zero worker spawn. |
| `ADV-06` | `x*x*x = 1` | REJECTED_SCOPE | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Parser parses `$*$`, host reducer rejects degree 3. |
| `ADV-07` | `1/(x - 1) = 0` | REJECTED_SCOPE | `REJECTED_SCOPE` | `NOT_APPLICABLE` | Parser parses `/`, host reducer rejects var denominator. |
| `ADV-08` | Forged worker roots for `x^2 - 4` (claims `[2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host expected cardinality mismatch ($1 \ne 2$). |
| `ADV-09` | Forged extra root for `x^2 - 4` (claims `[-2, 2, 0]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host expected cardinality mismatch ($3 \ne 2$). |
| `ADV-10` | Unsorted worker roots (claims `[2, -2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Strict ordering check $r_{\text{low}} < r_{\text{high}}$ fails. |
| `ADV-11` | Forged duplicate roots (claims `[2, 2]`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Vieta product check fails ($2 \cdot 2 = 4 \ne -4$). |
| `ADV-12` | Forged worker discriminant value | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Host independent $\Delta$ derivation refutes worker. |
| `ADV-13` | Consistent forgery (worker root + $\Delta$ forged) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Independent host AST derivation refutes both. |
| `ADV-14` | v1 response returned to v2 request | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Schema mismatch rejected by bridge. |
| `ADV-15` | Malformed framing before JSON decoded | FAIL CLOSED | `ENGINE_ERROR` | `NOT_APPLICABLE` | Transport error handled as infrastructure failure. |
| `ADV-16` | Oversized frame (> 4096 bytes) | FAIL CLOSED | `ENGINE_ERROR` | `NOT_APPLICABLE` | Transport ceiling rejects request safely. |
| `ADV-17` | Arbitrary schema version (`mke.p99.v1`) | FAIL CLOSED | `ENGINE_ERROR` | `VERIFICATION_FAILED` | Static schema allowlist rejects without reflection. |
| `ADV-18` | Worker timeout during v2 solve (> 5.0s) | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Cumulative 5.0s budget terminates worker. |
| `ADV-19` | Worker timeout during S2 check | TIMEOUT | `TIMEOUT` | `NOT_APPLICABLE` | Remaining budget terminates worker. |
| `ADV-20` | Degenerate $A=0$ (`0*x^2 + x = 1`) | SUCCESS | `UNIQUE_ROOT` | `VERIFIED_COMPLETE` | Host routes to B0 v1 path, exact B0 behavior. |
| `ADV-21` | Affine identity regression (`x = x`) | SUCCESS | `ALL_REALS` | `VERIFIED_COMPLETE` | Routed to B0 v1 path, exact B0 behavior. |
| `ADV-22` | Affine contradiction regression (`x = x + 1`)| SUCCESS | `EMPTY_SET` | `VERIFIED_COMPLETE` | Routed to B0 v1 path, exact B0 behavior. |
| `ADV-23` | B0 Full Regression Suite (41 tests) | PASS | - | - | 100% pass on `test_p03c_p1c_controlled_dispatch.py`. |
| `ADV-24` | Windows Containment Full Regression (80 tests) | PASS | - | - | 100% pass on `test_worker_windows.py`. |

---

## 14. Final R2 Recommendation & Implementation Authorization Boundary

### Final Recommendation
**GO FOR BOUNDED P1C-04-B1 IMPLEMENTATION CANDIDATE:**
- Exact univariate real quadratic equations with rational coefficients ($Ax^2 + Bx + C = 0, A \ne 0, A, B, C \in \mathbb{Q}$).
- Supported outcomes:
  - $\Delta < 0 \implies \text{NO\_REAL\_ROOT}$ ($\emptyset$).
  - $\Delta = 0 \implies \text{UNIQUE\_REAL\_ROOT}$ ($x \in \mathbb{Q}$).
  - $\Delta > 0 \land \Delta \text{ is a rational square} \implies \text{TWO\_DISTINCT\_REAL\_ROOTS}$ ($x_1, x_2 \in \mathbb{Q}$).
- All non-square $\Delta > 0$, polynomials of degree $\ge 3$, rational equations, radicals, and transcendentals fail closed before worker dispatch.
- Pure Python integer/rational arithmetic only; zero SymPy, zero floating point.
- Dual-version protocol: `mke.p02a.v2` for `SOLVE_QUADRATIC` only; existing `mke.p02a.v1` for `SOLVE` and `CHECK_CANDIDATE`.
- Separate host and worker reduction/solving implementations ensuring complete mathematical proof independence.
