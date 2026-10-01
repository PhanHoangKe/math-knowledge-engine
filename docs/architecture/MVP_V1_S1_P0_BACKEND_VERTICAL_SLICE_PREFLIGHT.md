# MKE MVP V1 — S1-P0 Backend Vertical Slice Architecture & Implementation Preflight

- **Document Identifier:** `docs/architecture/MVP_V1_S1_P0_BACKEND_VERTICAL_SLICE_PREFLIGHT.md`
- **Milestone:** MVP-V1-S1-P0 (Backend Vertical Slice Preflight)
- **Document Version:** 1.0.0
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Working Branch:** `product/mvp-v1-s1-p0-backend-preflight`
- **Accepted S0 Baseline SHA:** `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`
- **Parked B3 Baseline SHA:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (`product/p03c-p1c-04-b3-exact-complex-preflight`)
- **Status:** `PENDING INDEPENDENT S1-P0 AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Summary & Objective

The objective of `MVP-V1-S1-P0` is to design the complete, deterministic backend vertical slice for the Math Knowledge Engine (MKE) MVP V1 algebra experience.

The vertical slice connects the intake of raw user queries through deterministic parsing, exact rational AST normalization, canonical Domain IR routing, orthogonal method assessment, step-by-step trace generation, independent host verification, and structured response construction suitable for a reactive frontend.

```
+------------------+     +-------------------+     +---------------------+
|  Raw User Query  | --> | Tokenizer & Parser| --> | Immutable AST Tree  |
+------------------+     +-------------------+     +---------------------+
                                                              |
                                                              v
+------------------+     +-------------------+     +---------------------+
| Domain Model IR  | <-- | Degree / Category | <-- | Exact Normalizer    |
| (Q / R Invariants) |   | Routing (Q/Linear)|     | (Pure Rational Q[x])|
+------------------+     +-------------------+     +---------------------+
         |
         v
+------------------+     +-------------------+     +---------------------+
| Method Registry  | --> | Trace Generator   | --> | Host Independent    |
| (5D Assessment)  |     | (S1 Executable)   |     | Verifier & Cert     |
+------------------+     +-------------------+     +---------------------+
                                                              |
                                                              v
                                                   +---------------------+
                                                   | SolveResponse (DTO) |
                                                   | (Reactive Ready)    |
                                                   +---------------------+
```

This preflight freezes all architectural boundaries, mathematical normalization rules, solution trace generation algorithms, DTO schemas, and acceptance criteria prior to any production code implementation.

---

## 2. Component Reuse Classification Matrix (Accepted S0 Baseline)

Audited at baseline `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`:

| Component / Subsystem | Repository Path | Observed Constraints & Capabilities | Classification | Usage in S1 Vertical Slice |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Rational Arithmetic** | `src/mke_product/core/rational.py` | Pure $\mathbb{Q}$ arithmetic ($p/q, \gcd(|p|, q)=1, q>0$), zero float authority. | `REUSE_DIRECT` | Foundational arithmetic authority for normalization and solvers. |
| **P02A Lexer & Parser** | `src/mke_product/parser/` | Bounded recursive descent grammar ($x$, exponents $\in \{0,1,2\}$, nesting $\le 16$). | `REUSE_VIA_ADAPTER` | Parses raw input string into raw `Equation` AST. Must be normalized by Application layer. |
| **Domain Models & Invariants** | `src/mke_product/domain/models.py` | Pydantic v2 strict models with runtime semantic invariants (`QuadraticProblemIR`, `DegenerateEquationIR`, etc.). | `REUSE_DIRECT` | Immutable domain representations of mathematical truth. |
| **Exact Algebraic Kernel** | `src/mke_product/domain/exact.py` | Squarefree kernel decomposition, discriminant computation, exact real quadratic solving. | `REUSE_DIRECT` | Computes canonical discriminants and closed-form real roots in $\mathbb{Q}(\sqrt{d})$. |
| **Method Registry & Evaluator** | `src/mke_product/domain/registry.py` | Catalog of 9 quadratic methods with 5D orthogonal assessment. | `REUSE_DIRECT` | Assesses problem-level mathematical applicability and capability states. |
| **Host Independent Verifier** | `src/mke_product/domain/verifier.py` | Zero-CAS residual checks, Viète relations, sign stability, SHA-256 integrity fingerprinting. | `REUSE_DIRECT` | Issues tamper-evident `VerificationCertificate`. |
| **Workspace Dependency DAG** | `src/mke_product/domain/dag.py` | Directed acyclic graph with cycle detection and topological invalidation cascade. | `REUSE_DIRECT` | Coordinates reactive node invalidation for interactive frontend. |
| **Cryptographic Identity** | `src/mke_product/domain/identity.py` | Deterministic SHA-256 semantic problem identity and cache keys with canonical assumption sorting. | `REUSE_DIRECT` | Generates stable memoization and reactive revision hashes. |
| **JSON Schema Exporter** | `src/mke_product/domain/schema.py` | Deterministic JSON Schema Draft 2020-12 generator. | `REUSE_DIRECT` | Contract synchronization with frontend clients. |
| **Historical AI Validator** | `src/mke_product/ai/validator.py` | Coupled to legacy CAS parser contracts and `OperationType`. | `DO_NOT_USE` | Excluded from S1 vertical slice. |
| **Win32 Job Object Controller** | `src/mke_product/worker/controller.py` | Windows OS process containment infrastructure. | `DO_NOT_USE` | Excluded from S1 pure-Python application vertical slice. |
| **Historical IPC Protocols** | `src/mke_product/protocol/` (`v1, v2, v3`) | Historical worker IPC protocol schemas. | `REGRESSION_ONLY` | Preserved intact for historical regression test suite. |
| **Parked B3 Complex Solver** | `product/p03c-p1c-04-b3-exact-complex-preflight` | Complex quadratic solver preflight. | `PARKED` | Untouched at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`. |

---

## 3. Proposed Package Architecture: `src/mke_product/application/`

To maintain strict boundary separation between parsing, normalization, domain modeling, and presentation DTOs, a new pure-Python package `src/mke_product/application/` will be established:

```
src/mke_product/application/
├── __init__.py              # Clean public exports for application orchestration
├── errors.py                # Application-level error taxonomy and exceptions
├── dto.py                   # Pydantic v2 DTO request/response models for client/API
├── normalizer.py            # Exact AST -> Canonical Polynomial Q[x] normalizer
├── orchestrator.py          # End-to-end Application Service pipeline coordinator
└── traces/                  # Deterministic step-by-step solution trace engines
    ├── __init__.py          # Registry of trace generators
    ├── base.py              # BaseTraceGenerator abstract protocol
    ├── formula_standard.py  # QUAD_FORMULA_STANDARD step generator
    ├── formula_reduced.py   # QUAD_FORMULA_REDUCED step generator
    ├── viete_sum.py         # QUAD_VIETE_SPECIAL_SUM step generator
    └── viete_dif.py         # QUAD_VIETE_SPECIAL_DIF step generator
```

### Module Responsibilities:
1. **`normalizer.py`:** Takes an `ast.Equation` or `ast.ASTNode`, algebraically expands, multiplies, cancels, and collects like terms over $\mathbb{Q}[x]/\langle x^3 \rangle$, and yields exact coefficients $(c_2, c_1, c_0) \in \mathbb{Q}^3$ or raises structured normalization errors.
2. **`orchestrator.py`:** Pure orchestration service that coordinates parsing $\to$ normalization $\to$ domain classification $\to$ method assessment $\to$ trace execution $\to$ independent verification $\to$ DTO synthesis.
3. **`traces/`:** Implements pedagogical step generation with clean LaTeX and Vietnamese explanations for methods whose execution availability is `AVAILABLE` in S1.
4. **`dto.py`:** Frontend-agnostic, immutable data transfer contracts representing the complete state of a solved/analyzed equation.

---

## 4. Exact Normalization Contract

### 4.1 Internal Representation: `PolynomialQ`
Algebraic normalization operates on exact univariate polynomials of degree $\le 2$ over the field of rational numbers $\mathbb{Q}$:
$$P(x) = c_2 x^2 + c_1 x + c_0, \quad c_i \in \mathbb{Q}$$
represented internally as a dataclass `PolynomialQ(c2: Rational, c1: Rational, c0: Rational)`.

### 4.2 AST Node Normalization Rules
For any AST node $N$, the recursive normalizer $\mathcal{N}(N) \to \text{PolynomialQ}$ evaluates as follows:

1. **`IntegerLiteral(v)`:**
   $$\mathcal{N}(\text{IntegerLiteral}(v)) = (0, 0, \text{Rational}(v, 1))$$

2. **`Variable("x")`:**
   $$\mathcal{N}(\text{Variable}("x")) = (0, \text{Rational}(1, 1), 0)$$
   *Constraint:* Any variable name other than `"x"` raises `UNSUPPORTED_VARIABLE`.

3. **`Group(inner)`:**
   $$\mathcal{N}(\text{Group}(\text{inner})) = \mathcal{N}(\text{inner})$$

4. **`UnaryOp(op, operand)`:**
   - If $\text{op} == "+"$ $\implies \mathcal{N}(\text{operand})$
   - If $\text{op} == "-"$ $\implies (-c_2, -c_1, -c_0)$ where $(c_2, c_1, c_0) = \mathcal{N}(\text{operand})$.

5. **`BinaryOp("+", left, right)`:**
   $$\mathcal{N}(\text{left}) + \mathcal{N}(\text{right}) = (c_{2,L} + c_{2,R}, c_{1,L} + c_{1,R}, c_{0,L} + c_{0,R})$$

6. **`BinaryOp("-", left, right)`:**
   $$\mathcal{N}(\text{left}) - \mathcal{N}(\text{right}) = (c_{2,L} - c_{2,R}, c_{1,L} - c_{1,R}, c_{0,L} - c_{0,R})$$

7. **`BinaryOp("*", left, right)`:**
   Let $P_L = (c_{2,L}, c_{1,L}, c_{0,L})$ and $P_R = (c_{2,R}, c_{1,R}, c_{0,R})$.
   The expanded product is:
   $$\begin{aligned}
   P_{L} \cdot P_{R} &= (c_{2,L} c_{2,R}) x^4 + (c_{2,L} c_{1,R} + c_{1,L} c_{2,R}) x^3 \\
   &\quad + (c_{2,L} c_{0,R} + c_{1,L} c_{1,R} + c_{0,L} c_{2,R}) x^2 \\
   &\quad + (c_{1,L} c_{0,R} + c_{0,L} c_{1,R}) x + (c_{0,L} c_{0,R})
   \end{aligned}$$
   *Degree Bounds Rule:* If $(c_{2,L} \cdot c_{2,R} \neq 0) \lor (c_{2,L} c_{1,R} + c_{1,L} c_{2,R} \neq 0)$, the resulting polynomial has degree $> 2$. The normalizer must immediately fail closed and raise `DEGREE_OUT_OF_SCOPE`.
   Otherwise, returns $(c_2', c_1', c_0') \in \mathbb{Q}^3$.

8. **`BinaryOp("/", left, right)`:**
   Let $P_R = \mathcal{N}(\text{right})$.
   - If $P_R.c_2 \neq 0 \lor P_R.c_1 \neq 0$: The denominator contains variable $x$. Division by a polynomial in $x$ produces non-polynomial rational functions. Reject immediately with `NON_POLYNOMIAL_INPUT`.
   - If $P_R.c_0.is\_zero$: Reject with `DIVISION_BY_ZERO`.
   - If $P_R = (0, 0, k)$ with $k \neq 0 \in \mathbb{Q}$:
     $$\mathcal{N}(\text{left}) / k = \left(\frac{c_{2,L}}{k}, \frac{c_{1,L}}{k}, \frac{c_{0,L}}{k}\right)$$

9. **`Power(base, exponent)`:**
   - If exponent $== 0$:
     Evaluate $P_{\text{base}} = \mathcal{N}(\text{base})$. If $P_{\text{base}}$ is well-defined, $P^0 = (0, 0, \text{Rational}(1, 1))$.
   - If exponent $== 1$:
     $\mathcal{N}(\text{base})$
   - If exponent $== 2$:
     Let $P = \mathcal{N}(\text{base})$.
     - If $P.c_2 \neq 0$: degree of $P^2$ is 4 $\implies$ reject with `DEGREE_OUT_OF_SCOPE`.
     - If $P.c_2 == 0$: $P = c_1 x + c_0$. Then $P^2 = c_1^2 x^2 + 2 c_1 c_0 x + c_0^2$. Return $(c_1^2, 2 c_1 c_0, c_0^2)$.

10. **`Equation(left, right)`:**
    Subtracts right-hand side from left-hand side:
    $$P_{\text{eq}} = \mathcal{N}(\text{left}) - \mathcal{N}(\text{right})$$
    Yields canonical coefficients:
    $$a = P_{\text{eq}}.c_2, \quad b = P_{\text{eq}}.c_1, \quad c = P_{\text{eq}}.c_0$$

### 4.3 Fail-Closed Rejection Boundaries

| Rejection Trigger | Error Code | Error Rationale |
| :--- | :--- | :--- |
| Exponent $> 2$ or non-integer exponent | `DEGREE_OUT_OF_SCOPE` | Polynomial degree exceeds univariate quadratic boundary. |
| Polynomial product degree $> 2$ (e.g. $(x^2+1)(x+1)$) | `DEGREE_OUT_OF_SCOPE` | Multiplicative expansion exceeds degree 2. |
| Division by expression with $x$ (e.g. $1/(x-1)$) | `NON_POLYNOMIAL_INPUT` | Expression is not in polynomial ring $\mathbb{Q}[x]$. |
| Division by exact zero constant (e.g. $x/0$) | `DIVISION_BY_ZERO` | Undefined arithmetic operation. |
| Variable identifier $\neq "x"$ (e.g. $y, t$) | `UNSUPPORTED_VARIABLE` | Single-variable scope restriction in MVP V1. |
| Transcendental functions (sin, cos, exp, log) | `UNSUPPORTED_SYNTAX` | Non-algebraic functions excluded from polynomial slice. |
| Multiple equality signs ($x = y = 0$) | `SYNTAX_ERROR` | Malformed equation syntax. |
| Unbalanced parentheses, nesting depth $> 16$ | `INPUT_LIMIT_EXCEEDED` / `SYNTAX_ERROR` | Parser safety bounds violated. |

---

## 5. Application Request & Response Contracts (DTOs)

The DTO models in `src/mke_product/application/dto.py` provide a stable, serializable interface between the backend engine and any client (CLI, REST API, or React/Next.js frontend):

```python
class SolveRequest(BaseModel):
    """Client request to solve or analyze an algebraic equation."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    raw_query: str = Field(..., min_length=1, max_length=500, description="Raw input formula or equation string")
    target_variable: str = Field(default="x", min_length=1, max_length=10)
    selected_method_id: Optional[str] = Field(
        default=None, description="Optional method ID to execute specifically. If None, recommended method is chosen."
    )
    schema_version: str = Field(default="1.0.0")


class MethodOptionView(BaseModel):
    """View model representing the orthogonal assessment of a solution method."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    title_vi: str
    mathematical_applicability: MathematicalApplicability
    support_status: SupportStatus
    execution_availability: ExecutionAvailability
    pedagogical_recommendation: PedagogicalRecommendation
    verification_capability: VerificationCapability
    reasons: List[str]
    prerequisites: List[PrerequisiteStatus]
    has_trace_available: bool = Field(..., description="True if a step-by-step solution trace can be generated now")
    pedagogical_priority: int


class CanonicalProblemView(BaseModel):
    """Normalized, canonical view of the problem for display and reactive editing."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_id: str
    raw_query: str
    equation_latex: str = Field(..., description="Canonical equation LaTeX e.g. x^2 - 5x + 6 = 0")
    category: ProblemCategory
    classification: EquationClassificationType
    a: RationalFraction
    b: RationalFraction
    c: RationalFraction
    discriminant: QuadraticDiscriminant
    semantic_revision_hash: str


class VerifiedSolutionView(BaseModel):
    """Structured solution result with execution trace and verification certificate."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    outcome: SolutionOutcome
    roots: List[RealRootValue]
    final_answer_latex: str
    trace: Optional[SolutionTrace] = None
    certificate: VerificationCertificate


class ErrorResponse(BaseModel):
    """Structured, client-safe error response."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    code: str = Field(..., description="Machine-readable error code")
    message_vi: str = Field(..., description="User-friendly Vietnamese explanation")
    message_en: str = Field(..., description="Technical English error detail")
    span: Optional[Tuple[int, int]] = Field(None, description="Source character offset [start, end]")
    details: Dict[str, Any] = Field(default_factory=dict)


class SolveResponse(BaseModel):
    """Root vertical slice response returned to client."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    success: bool
    problem: Optional[CanonicalProblemView] = None
    available_methods: List[MethodOptionView] = Field(default_factory=list)
    selected_method_id: Optional[str] = None
    solution: Optional[VerifiedSolutionView] = None
    error: Optional[ErrorResponse] = None
```

---

## 6. Solution Trace Contract & Executable Methods

### 6.1 S1 Executable Methods Scope
In Milestone S1, exactly four methods will have fully executable, deterministic step-by-step trace generation engines implemented:

1. **`QUAD_FORMULA_STANDARD`** (Công thức nghiệm tổng quát):
   - **Step 1:** Identify coefficients $a, b, c$ and determine $a \neq 0$.
   - **Step 2:** Compute discriminant $\Delta = b^2 - 4ac$.
   - **Step 3:** Evaluate sign of $\Delta$:
     - If $\Delta > 0$: compute $\sqrt{\Delta} = s\sqrt{d}$, apply $x_{1,2} = \frac{-b \pm \sqrt{\Delta}}{2a}$.
     - If $\Delta = 0$: compute repeated root $x_0 = \frac{-b}{2a}$.
     - If $\Delta < 0$: conclude no real roots ($S = \emptyset$).
   - **Step 4:** Final solution set conclusion $S$.

2. **`QUAD_FORMULA_REDUCED`** (Công thức nghiệm thu gọn):
   - **Step 1:** Identify $b' = b/2 \in \mathbb{Q}$, compute $\Delta' = (b')^2 - ac$.
   - **Step 2:** Evaluate sign of $\Delta'$:
     - If $\Delta' > 0$: compute $\sqrt{\Delta'} = s'\sqrt{d}$, apply $x_{1,2} = \frac{-b' \pm \sqrt{\Delta'}}{a}$.
     - If $\Delta' = 0$: compute $x_0 = \frac{-b'}{a}$.
     - If $\Delta' < 0$: conclude no real roots.
   - **Step 3:** Final conclusion.

3. **`QUAD_VIETE_SPECIAL_SUM`** (Nhẩm nghiệm $a + b + c = 0$):
   - **Step 1:** Verify $a + b + c = 0$ explicitly with step calculation.
   - **Step 2:** Deduce immediate roots: $x_1 = 1$, $x_2 = c/a$.
   - **Step 3:** Final conclusion.

4. **`QUAD_VIETE_SPECIAL_DIF`** (Nhẩm nghiệm $a - b + c = 0$):
   - **Step 1:** Verify $a - b + c = 0$ explicitly with step calculation.
   - **Step 2:** Deduce immediate roots: $x_1 = -1$, $x_2 = -c/a$.
   - **Step 3:** Final conclusion.

### 6.2 Trace Engine Status Table

| Method ID | S1 Implementation Status | Trace Generator Strategy | Verification Strategy |
| :--- | :--- | :--- | :--- |
| `QUAD_FORMULA_STANDARD` | **EXECUTABLE (S1)** | Pure-Python deterministic template builder | `HostIndependentVerifier` |
| `QUAD_FORMULA_REDUCED` | **EXECUTABLE (S1)** | Pure-Python deterministic template builder | `HostIndependentVerifier` |
| `QUAD_VIETE_SPECIAL_SUM` | **EXECUTABLE (S1)** | Pure-Python deterministic template builder | `HostIndependentVerifier` |
| `QUAD_VIETE_SPECIAL_DIF` | **EXECUTABLE (S1)** | Pure-Python deterministic template builder | `HostIndependentVerifier` |
| `QUAD_FACTORIZATION_Q` | *UNAVAILABLE (Deferred to S2)* | Integer ac-splitting factoring algorithm | `HostIndependentVerifier` |
| `QUAD_FACTORIZATION_R` | *UNAVAILABLE (Deferred to S2)* | Real surd factoring expansion | `HostIndependentVerifier` |
| `QUAD_COMPLETE_SQUARE` | *UNAVAILABLE (Deferred to S2)* | Identity grouping transformer | `HostIndependentVerifier` |
| `QUAD_VIETE_SUM_PRODUCT` | *UNAVAILABLE (Deferred to S2)* | Integer sum-product factoring search | `HostIndependentVerifier` |
| `QUAD_GRAPHICAL_ANALYSIS` | *UNAVAILABLE (Deferred to S3)* | Parabola vertex & root surveyor | `NOT_APPLICABLE` |

---

## 7. Reactive Workspace Dependency Mapping

The S1 vertical slice maps directly to the reactive `DependencyGraph` defined in `src/mke_product/domain/dag.py`:

```
                 [raw_query]
                      |
                      v
             [ast_parsed_node]
                      |
                      v
            [coefficients (a,b,c)]
                 /          \
                v            v
        [classification]  [discriminant]
                \            /
                 v          v
              [exact_solution_set]
                /            \
               v              v
     [method_assessments]  [semantic_identity]
               |
               v
       [selected_method]
               |
               v
       [solution_trace]
               |
               v
   [verification_certificate]
               |
               v
        [solve_response]
```

### Invalidation Cascade Semantics:
- **Changing `raw_query`:** Invalidates all nodes downstream.
- **Directly editing coefficient `c` (via future parameter slider):** Invalidation starts at `coefficients`, immediately invalidating `discriminant`, `exact_solution_set`, `method_assessments`, `solution_trace`, `verification_certificate`, and `solve_response`, while leaving unrelated UI presentation settings (theme, zoom, language) completely intact.

---

## 8. Deterministic Acceptance Matrix

| Case ID | Input Expression | Expected Classification / (a,b,c) | Expected Outcome / Roots | Expected Applicable Methods | Executable in S1 | Verification Outcome | Expected Error / Rejection |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1** | `x^2 - 5*x + 6 = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_G | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q2** | `x^2 - 2 = 0` | `QUADRATIC` (1, 0, -2) | `TWO_DISTINCT_REAL_ROOTS` $\{-\sqrt{2}, \sqrt{2}\}$ | STANDARD, REDUCED, FACT_R, SQ | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q3** | `x^2 - 2*x + 1 = 0` | `QUADRATIC` (1, -2, 1) | `ONE_REPEATED_REAL_ROOT` $\{1\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_SUM | STANDARD, REDUCED, VIETE_SUM | `VERIFIED_COMPLETE` | None (Success) |
| **Q4** | `x^2 + 1 = 0` | `QUADRATIC` (1, 0, 1) | `NO_REAL_ROOTS` $\emptyset$ | STANDARD, REDUCED, SQ | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q5** | `2*x^2 - 5*x + 2 = 0` | `QUADRATIC` (2, -5, 2) | `TWO_DISTINCT_REAL_ROOTS` $\{1/2, 2\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q6** | `x^2 + 6 = 5*x` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_G | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q7** | `(x - 2)*(x - 3) = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_G | STANDARD, REDUCED | `VERIFIED_COMPLETE` | None (Success) |
| **Q8** | `(x + 1)^2 = 0` | `QUADRATIC` (1, 2, 1) | `ONE_REPEATED_REAL_ROOT` $\{-1\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_DIF | STANDARD, REDUCED, VIETE_DIF | `VERIFIED_COMPLETE` | None (Success) |
| **Q9** | `(1/2)*x^2 - (5/4)*x + 3/4 = 0` | `QUADRATIC` (1/2, -5/4, 3/4) | `TWO_DISTINCT_REAL_ROOTS` $\{1, 3/2\}$ | STANDARD, REDUCED, FACT_Q, FACT_R, SQ, VIETE_SUM | STANDARD, REDUCED, VIETE_SUM | `VERIFIED_COMPLETE` | None (Success) |
| **D1** | `2*x - 4 = 0` | `LINEAR` (0, 2, -4) | `ONE_REAL_LINEAR_ROOT` $\{2\}$ | N/A (Linear specialized) | N/A | `VERIFIED_COMPLETE` | None (Success) |
| **D2** | `0 = 0` | `IDENTITY` (0, 0, 0) | `INFINITE_REAL_SOLUTIONS` | N/A (Identity) | N/A | `VERIFIED_COMPLETE` | None (Success) |
| **D3** | `1 = 0` | `CONTRADICTION` (0, 0, 1) | `NO_REAL_SOLUTIONS_CONTRADICTION` | N/A (Contradiction) | N/A | `VERIFIED_COMPLETE` | None (Success) |
| **E1** | `x^2 + = 0` | N/A | N/A | N/A | N/A | N/A | `SYNTAX_ERROR` |
| **E2** | `x^3 - 2*x + 1 = 0` | N/A | N/A | N/A | N/A | N/A | `DEGREE_OUT_OF_SCOPE` |
| **E3** | `(x^2 + 1)*(x + 1) = 0` | N/A | N/A | N/A | N/A | N/A | `DEGREE_OUT_OF_SCOPE` |
| **E4** | `y^2 - 4 = 0` | N/A | N/A | N/A | N/A | N/A | `UNSUPPORTED_VARIABLE` |
| **E5** | `1/x = 0` | N/A | N/A | N/A | N/A | N/A | `NON_POLYNOMIAL_INPUT` |
| **E6** | `x^2 / 0 = 0` | N/A | N/A | N/A | N/A | N/A | `DIVISION_BY_ZERO` |
| **E7** | `sin(x) = 0` | N/A | N/A | N/A | N/A | N/A | `UNSUPPORTED_SYNTAX` |

---

## 9. Structured Error Taxonomy

All error states are mapped to deterministic, machine-readable error codes with localized messages:

```python
class ApplicationErrorCode(str, Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    INPUT_LIMIT_EXCEEDED = "INPUT_LIMIT_EXCEEDED"
    UNSUPPORTED_SYNTAX = "UNSUPPORTED_SYNTAX"
    UNSUPPORTED_VARIABLE = "UNSUPPORTED_VARIABLE"
    NON_POLYNOMIAL_INPUT = "NON_POLYNOMIAL_INPUT"
    DEGREE_OUT_OF_SCOPE = "DEGREE_OUT_OF_SCOPE"
    DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    DOMAIN_CONTRACT_ERROR = "DOMAIN_CONTRACT_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

### Safety Invariant:
When normalization or verification fails, the orchestrator **never** returns partial or unverified solution claims. `SolveResponse.success` is set to `False` and populated exclusively with `ErrorResponse`.

---

## 10. Future Frontend Capability Enablement

The proposed S1 response contract enables all future UI modules without structural schema revisions:

1. **Live Parameter Slider / Direct Coefficient Editing:** Frontend updates $a, b, c$ directly in `CanonicalProblemView`, calling orchestrator with exact rational coefficients.
2. **Interactive Method Switching:** User clicks any method in `available_methods`; frontend sends `selected_method_id` to receive updated `VerifiedSolutionView` without re-parsing.
3. **Pedagogical Recommendation & Rule Cards:** Populated directly from `MethodOptionView.reasons`, `prerequisites`, and `pedagogical_recommendation`.
4. **Interactive Parabola Graph Canvas:** Rendered deterministically on frontend using canonical roots, vertex $(-\frac{b}{2a}, -\frac{\Delta}{4a})$, and y-intercept $(0, c)$.
5. **Session Workspace State:** Frontend serializes `problem.semantic_revision_hash` and `selected_method_id` into client local storage or URL query parameters.

---

## 11. Security & Soundness Guarantees

1. **Zero Dynamic Execution:** No use of Python `eval()`, `exec()`, or dynamic `__import__()`.
2. **Zero CAS/AI Authority:** Mathematical truth originates entirely within deterministic rational arithmetic.
3. **Fail-Closed Boundary:** Any non-polynomial division, degree $> 2$, or invalid syntax is immediately rejected.
4. **Preserved B0/B1/B2 Lineage:** All existing parser bounds (`MAX_NESTING_DEPTH = 16`, bounded exponent grammar) remain strictly enforced.

---

## 12. Proposed Implementation Stages for S1

- **Stage S1-01: Application Normalizer (`src/mke_product/application/normalizer.py`)**
  - Implement `PolynomialQ` and recursive AST normalization.
  - Implement expansion, cancellation, and degree bounding.
- **Stage S1-02: Solution Trace Generators (`src/mke_product/application/traces/`)**
  - Implement deterministic trace engines for `QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`.
- **Stage S1-03: Application Orchestrator & DTOs (`src/mke_product/application/`)**
  - Implement `SolveRequest`, `SolveResponse`, and end-to-end `SolveOrchestrator`.
- **Stage S1-04: Full Vertical Slice Acceptance & Regression Testing**
  - Execute full acceptance matrix Q1–Q9, D1–D3, E1–E7.
  - Verify zero regressions across full repository test suite.

---

## 13. Risks and Unresolved Questions

1. **Risk:** Future client inputs with multiple variables or degree $> 2$ (e.g. cubic equations) attempting to use the quadratic slice.
   - *Mitigation:* Bounded at normalizer entry point with explicit `DEGREE_OUT_OF_SCOPE` and `UNSUPPORTED_VARIABLE` error codes.
2. **Unresolved Question:** Should S1 support automated fallback to `QUAD_FORMULA_STANDARD` if a user selects an unavailable method (e.g. `QUAD_COMPLETE_SQUARE`)?
   - *Recommendation:* Return `SolveResponse` containing the full `available_methods` assessment (marking `QUAD_COMPLETE_SQUARE` as `has_trace_available = False`), while automatically populating `selected_method_id` with the highest priority available method (or reporting structured error if user strictly requested an unavailable method).

---

## 14. Implementation Recommendation

**RECOMMENDATION: GO FOR S1 IMPLEMENTATION AUTHORIZATION**

The S1-P0 preflight establishes a complete, mathematically sound, bounded, and verified architecture for the backend vertical slice of the MKE MVP V1 algebra product.
