# MKE MVP V1 — S1-P0 Backend Vertical Slice Architecture & Implementation Preflight

- **Document Identifier:** `docs/architecture/MVP_V1_S1_P0_BACKEND_VERTICAL_SLICE_PREFLIGHT.md`
- **Milestone:** MVP-V1-S1-P0-R1 (Backend Vertical Slice Preflight Remediation)
- **Document Version:** 1.1.0
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Working Branch:** `product/mvp-v1-s1-p0-backend-preflight`
- **Accepted S0 Baseline SHA:** `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`
- **Parent Preflight SHA:** `37acd112e1ad21d8231b4c7de4962643cefb5a7f`
- **Parked B3 Baseline SHA:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (`product/p03c-p1c-04-b3-exact-complex-preflight`)
- **Status:** `PENDING INDEPENDENT S1-P0-R1 AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Summary & Objective

The objective of `MVP-V1-S1-P0-R1` is to freeze the complete, mathematically rigorous, fail-closed backend vertical slice architecture for the Math Knowledge Engine (MKE) MVP V1 algebra experience.

The vertical slice defines the pure-Python pipeline connecting:
1. **Intake Modes:** Raw equation string or direct canonical coefficient editing $[a, b, c]$.
2. **Deterministic Parsing & Lexical Mapping:** Bounded P02A parser (`MAX_INPUT_LENGTH = 256`, variable $x$).
3. **Exact Bounded Normalization:** Algebraic reduction in $\mathbb{Q}[x]$ for $\deg(P) \le 2$ via `PolynomialQDegree2`.
4. **Domain Classification & Discriminated IR Routing:**
   - $a \neq 0 \longrightarrow \text{QuadraticProblemIR}$ (with canonical $b^2 - 4ac$ discriminant).
   - $a = 0 \longrightarrow \text{DegenerateEquationIR}$ (LINEAR, IDENTITY, CONTRADICTION; zero discriminant invented).
5. **Orthogonal Method Assessment:** Multi-dimensional capability evaluation across all 9 canonical methods.
6. **Selected Method Semantics & Trace Generation:** Deterministic execution without silent fallback for S1 executable methods.
7. **Host Independent Verification:** Exact residual & invariant verification certifying final mathematical outcomes (`verification_scope = "FINAL_SOLUTION"`).
8. **Discriminated Response Union:** Strictly typed state machine (`SOLVED`, `ANALYZED_NO_EXECUTION`, `ERROR`).

```
+---------------------------------------------------------------------------------------------------+
|                                    APPLICATION INTAKE LAYER                                       |
|  [RawEquationInput: raw_query]                  [CanonicalCoefficientInput: (a,b,c)]              |
+---------------------------------------------------------------------------------------------------+
             | (Parser & Lexer)                                     | (Direct Path)
             v                                                      |
+------------------------------------+                              |
| Immutable AST Tree (Equation)      |                              |
+------------------------------------+                              |
             | (Exact Normalizer)                                   |
             v                                                      |
+-------------------------------------------------------------------+-------------------------------+
| Bounded Polynomial Reduction: P(x) = c2*x^2 + c1*x + c0  (PolynomialQDegree2 in Q[x], deg <= 2)  |
+---------------------------------------------------------------------------------------------------+
                                             |
                                             v
+---------------------------------------------------------------------------------------------------+
|                                  DOMAIN CLASSIFICATION ROUTING                                    |
|             [ a != 0 ]                                                  [ a == 0 ]                |
|                 |                                                           |                     |
|                 v                                                           v                     |
|      QuadraticProblemIR                                           DegenerateEquationIR            |
|   (Exact b^2 - 4ac Discriminant)                                (LINEAR | IDENTITY | CONTRAD.)    |
+---------------------------------------------------------------------------------------------------+
             |                                                                |
             v                                                                v
+------------------------------------+                       +------------------------------------+
| Method Registry (5D Assessment)    |                       | Degenerate Verifier                |
|  - 9 Canonical Quadratic Methods   |                       |  - Linear: b*r + c == 0            |
+------------------------------------+                       |  - Identity: 0 == 0                |
             |                                               |  - Contradiction: c != 0           |
             v                                               +------------------------------------+
+------------------------------------+                                        |
| Trace Generation (S1 Executable)   |                                        |
|  - QUAD_FORMULA_STANDARD           |                                        |
|  - QUAD_FORMULA_REDUCED            |                                        |
|  - QUAD_VIETE_SPECIAL_SUM/DIF      |                                        |
+------------------------------------+                                        |
             |                                                                |
             v                                                                |
+------------------------------------+                                        |
| Host Independent Verifier          |                                        |
|  - Residual == 0, Viète, Sign      |                                        |
|  - Certificate: FINAL_SOLUTION     |                                        |
+------------------------------------+                                        |
             |                                                                |
             +-------------------------------+--------------------------------+
                                             |
                                             v
+---------------------------------------------------------------------------------------------------+
|                                 APPLICATION RESPONSE DTO UNION                                    |
|   [ SOLVED ]               |       [ ANALYZED_NO_EXECUTION ]       |           [ ERROR ]              |
|   - CanonicalProblemUnion  |       - CanonicalProblemUnion         |           - Machine ErrorCode    |
|   - MethodOptionViews (9)  |       - MethodOptionViews (9)         |           - Localized message    |
|   - VerifiedSolutionView   |       - Selected Method State         |           - Error Source Span    |
|   - Final Certificate      |       - Analysis Message              |                                  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Component Reuse Classification Matrix (Accepted S0 Baseline)

Audited at baseline `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`:

| Component / Subsystem | Repository Path | Observed Constraints & Capabilities | Classification | Usage in S1 Vertical Slice |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Rational Arithmetic** | `src/mke_product/core/rational.py` | Pure $\mathbb{Q}$ arithmetic ($p/q, \gcd(|p|, q)=1, q>0$), zero float authority. | `REUSE_DIRECT` | Foundational arithmetic authority for normalization and solvers. |
| **P02A Lexer & Parser** | `src/mke_product/parser/` | Bounded recursive descent grammar ($x$, exponents $\in \{0,1,2\}$, nesting $\le 16$, `MAX_INPUT_LENGTH = 256`). | `REUSE_VIA_ADAPTER` | Parses raw input string into raw `Equation` AST. Must be normalized by Application layer. |
| **Domain Models & Invariants** | `src/mke_product/domain/models.py` | Pydantic v2 strict models with runtime semantic invariants (`QuadraticProblemIR`, `DegenerateEquationIR`, etc.). | `REUSE_DIRECT` | Immutable domain representations of mathematical truth. |
| **Exact Algebraic Kernel** | `src/mke_product/domain/exact.py` | Squarefree kernel decomposition, discriminant computation, exact real quadratic solving. | `REUSE_DIRECT` | Computes canonical discriminants and closed-form real roots in $\mathbb{Q}(\sqrt{d})$. |
| **Method Registry & Evaluator** | `src/mke_product/domain/registry.py` | Catalog of 9 quadratic methods with 5D orthogonal assessment. | `REUSE_DIRECT` | Assesses problem-level mathematical applicability and capability states. |
| **Host Independent Verifier** | `src/mke_product/domain/verifier.py` | Zero-CAS residual checks, Viète relations, sign stability, SHA-256 integrity fingerprinting. | `REUSE_DIRECT` | Issues tamper-evident `VerificationCertificate` (`verification_scope = "FINAL_SOLUTION"`). |
| **Workspace Dependency DAG** | `src/mke_product/domain/dag.py` | Directed acyclic graph with cycle detection and topological invalidation cascade. | `REUSE_DIRECT` | Extended at application layer to coordinate full workspace invalidation. |
| **Cryptographic Identity** | `src/mke_product/domain/identity.py` | Deterministic SHA-256 semantic problem identity and cache keys with canonical assumption sorting. | `REUSE_DIRECT` | Generates stable memoization and reactive revision hashes. |
| **JSON Schema Exporter** | `src/mke_product/domain/schema.py` | Deterministic JSON Schema Draft 2020-12 generator. | `REUSE_DIRECT` | Contract synchronization with frontend clients. |
| **Historical AI Validator** | `src/mke_product/ai/validator.py` | Coupled to legacy CAS parser contracts and `OperationType`. | `DO_NOT_USE` | Excluded from S1 vertical slice. |
| **Win32 Job Object Controller** | `src/mke_product/worker/controller.py` | Windows OS process containment infrastructure. | `DO_NOT_USE` | Excluded from S1 pure-Python application vertical slice. |
| **Historical IPC Protocols** | `src/mke_product/protocol/` (`v1, v2, v3`) | Historical worker IPC protocol schemas. | `REGRESSION_ONLY` | Preserved intact for historical regression test suite. |
| **Parked B3 Complex Solver** | `product/p03c-p1c-04-b3-exact-complex-preflight` | Complex quadratic solver preflight. | `PARKED` | Untouched at `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`. |

---

## 3. Proposed Package Architecture: `src/mke_product/application/`

```
src/mke_product/application/
├── __init__.py              # Clean public exports for application orchestration
├── errors.py                # Application error taxonomy, exceptions, and parser error mapping
├── dto.py                   # Pydantic v2 DTO request/response discriminated unions
├── normalizer.py            # Exact AST -> PolynomialQDegree2 normalizer in Q[x]
├── orchestrator.py          # End-to-end Application Service pipeline coordinator
├── degenerate.py            # Exact solver and verifier for DegenerateEquationIR
└── traces/                  # Deterministic step-by-step solution trace engines
    ├── __init__.py          # Registry of trace generators
    ├── base.py              # BaseTraceGenerator abstract protocol
    ├── formula_standard.py  # QUAD_FORMULA_STANDARD step generator
    ├── formula_reduced.py   # QUAD_FORMULA_REDUCED step generator
    ├── viete_sum.py         # QUAD_VIETE_SPECIAL_SUM step generator
    └── viete_dif.py         # QUAD_VIETE_SPECIAL_DIF step generator
```

---

## 4. Exact Normalization & Parser Error Mapping Contract

### 4.1 Bounded Polynomial Mathematical Model
Normalizer operates on bounded exact univariate polynomial expressions:
$$P \in \mathbb{Q}[x] \quad \text{with} \quad \deg(P) \le 2$$
represented internally as `PolynomialQDegree2(c2: Rational, c1: Rational, c0: Rational)`.

> [!IMPORTANT]
> **No Quotient Ring Identification:** We do NOT model this as $\mathbb{Q}[x]/\langle x^3 \rangle$. $x^3$ is not identified with zero; it is an out-of-scope degree.
> **Fail-Closed Intermediate Degree Bounding:** Any intermediate subexpression whose computed degree exceeds 2 is rejected **immediately** with `DEGREE_OUT_OF_SCOPE`, without waiting for potential algebraic cancellation.
> Example: `(x^2 + 1)*(x + 1) - x^3` is rejected at `(x^2 + 1)*(x + 1)` because the product degree is 3.

### 4.2 AST Node Normalization Rules
1. **`IntegerLiteral(v)`:** $(0, 0, \text{Rational}(v, 1))$.
2. **`Variable("x")`:** $(0, \text{Rational}(1, 1), 0)$.
3. **`Group(inner)`:** $\mathcal{N}(\text{inner})$.
4. **`UnaryOp(op, operand)`:**
   - `"+"` $\implies \mathcal{N}(\text{operand})$
   - `"-"` $\implies (-c_2, -c_1, -c_0)$.
5. **`BinaryOp("+", L, R)`:** $(c_{2,L} + c_{2,R}, c_{1,L} + c_{1,R}, c_{0,L} + c_{0,R})$.
6. **`BinaryOp("-", L, R)`:** $(c_{2,L} - c_{2,R}, c_{1,L} - c_{1,R}, c_{0,L} - c_{0,R})$.
7. **`BinaryOp("*", L, R)`:**
   Let $P_L = (c_{2,L}, c_{1,L}, c_{0,L})$ and $P_R = (c_{2,R}, c_{1,R}, c_{0,R})$.
   - Product degree check: if $(c_{2,L} \cdot c_{2,R} \neq 0) \lor (c_{2,L} c_{1,R} + c_{1,L} c_{2,R} \neq 0)$, raise `DEGREE_OUT_OF_SCOPE`.
   - Result:
     $$c_2' = c_{2,L} c_{0,R} + c_{1,L} c_{1,R} + c_{0,L} c_{2,R}$$
     $$c_1' = c_{1,L} c_{0,R} + c_{0,L} c_{1,R}$$
     $$c_0' = c_{0,L} c_{0,R}$$
8. **`BinaryOp("/", L, R)`:**
   Let $P_R = \mathcal{N}(R)$.
   - If $P_R.c_2 \neq 0 \lor P_R.c_1 \neq 0$: denominator contains variable $x \implies$ raise `NON_POLYNOMIAL_INPUT`.
   - If $P_R.c_0.is\_zero$: raise `DIVISION_BY_ZERO`.
   - If $P_R = (0, 0, k)$ with $k \neq 0 \in \mathbb{Q} \implies (\frac{c_{2,L}}{k}, \frac{c_{1,L}}{k}, \frac{c_{0,L}}{k})$.
9. **`Power(base, exponent)`:**
   - $e = 0 \implies (0, 0, \text{Rational}(1, 1))$.
   - $e = 1 \implies \mathcal{N}(\text{base})$.
   - $e = 2 \implies$ if $P_{\text{base}}.c_2 \neq 0$ raise `DEGREE_OUT_OF_SCOPE`. If $P_{\text{base}} = c_1 x + c_0$, return $(c_1^2, 2 c_1 c_0, c_0^2)$.
10. **`Equation(left, right)`:**
    $$P_{\text{eq}} = \mathcal{N}(\text{left}) - \mathcal{N}(\text{right}) \implies (a, b, c) = (P_{\text{eq}}.c_2, P_{\text{eq}}.c_1, P_{\text{eq}}.c_0)$$

### 4.3 Robust Parser Error Mapping
The application layer wraps the intake parser with structured error mapping:

| Lexical / Syntactic Event | Concrete Trigger | Mapped `ApplicationErrorCode` | Localized Message (VI) |
| :--- | :--- | :--- | :--- |
| Character other than digit/x/op | Input `y^2 - 4 = 0` | `UNSUPPORTED_VARIABLE` | Biến số không được hỗ trợ. MVP V1 chỉ hỗ trợ biến 'x'. |
| Function token (sin, cos, log) | Input `sin(x) = 0` | `UNSUPPORTED_SYNTAX` | Hàm siêu việt không thuộc phạm vi đa thức bậc hai. |
| Exponent $> 2$ at parse | Input `x^3 = 0` | `DEGREE_OUT_OF_SCOPE` | Bậc của phương trình vượt quá giới hạn bậc hai (deg <= 2). |
| Implicit multiplication | Input `2x = 4` | `IMPLICIT_MULTIPLICATION_UNSUPPORTED` | Phép nhân ẩn không được hỗ trợ. Vui lòng viết rõ '2*x'. |
| Input length $> 256$ | Length $= 257$ | `INPUT_LIMIT_EXCEEDED` | Độ dài chuỗi vượt quá giới hạn cho phép (tối đa 256 ký tự). |
| Nesting depth $> 16$ | Nesting $= 17$ | `INPUT_LIMIT_EXCEEDED` | Độ sâu dấu ngoặc vượt quá giới hạn an toàn (tối đa 16 cấp). |
| Missing operand / syntax | Input `x^2 + = 0` | `SYNTAX_ERROR` | Cú pháp phương trình không hợp lệ. |

---

## 5. Application Request & Response Contracts (Discriminated Unions)

### 5.1 Request Contracts (`src/mke_product/application/dto.py`)

```python
class RawEquationInput(BaseModel):
    """Raw text equation input mode."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["RAW_TEXT"] = "RAW_TEXT"
    raw_query: str = Field(..., min_length=1, max_length=256, description="Raw equation string e.g. 'x^2 - 5*x + 6 = 0'")
    target_variable: Literal["x"] = "x"


class CanonicalCoefficientInput(BaseModel):
    """Direct coefficient parameter input mode for reactive live editing."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["COEFFICIENTS"] = "COEFFICIENTS"
    a: RationalFraction = Field(..., description="Leading coefficient a")
    b: RationalFraction = Field(..., description="Linear coefficient b")
    c: RationalFraction = Field(..., description="Constant term c")
    target_variable: Literal["x"] = "x"


class MethodSwitchInput(BaseModel):
    """Method-only recomputation mode on previously analyzed coefficients."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["METHOD_SWITCH"] = "METHOD_SWITCH"
    a: RationalFraction
    b: RationalFraction
    c: RationalFraction
    selected_method_id: str
    target_variable: Literal["x"] = "x"


InputPayloadUnion = Annotated[
    Union[RawEquationInput, CanonicalCoefficientInput, MethodSwitchInput],
    Field(discriminator="input_mode")
]


class SolveRequest(BaseModel):
    """Client request container for equation analysis and solving."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_payload: InputPayloadUnion
    selected_method_id: Optional[str] = Field(
        None, description="Explicit method selection. If None, highest-priority available method is executed."
    )
    schema_version: str = "1.0.0"
```

### 5.2 Canonical Problem Discriminated Union

```python
class CanonicalQuadraticProblemView(BaseModel):
    """Canonical problem representation for true quadratic equations (a != 0)."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_type: Literal["QUADRATIC"] = "QUADRATIC"
    problem_id: str
    raw_query: Optional[str] = None
    equation_latex: str = Field(..., description="e.g. x^2 - 5x + 6 = 0")
    category: Literal[ProblemCategory.ALGEBRA_QUADRATIC] = ProblemCategory.ALGEBRA_QUADRATIC
    classification: Literal[EquationClassificationType.QUADRATIC] = EquationClassificationType.QUADRATIC
    a: RationalFraction
    b: RationalFraction
    c: RationalFraction
    discriminant: QuadraticDiscriminant
    semantic_revision_hash: str


class CanonicalDegenerateProblemView(BaseModel):
    """Canonical problem representation for degenerate equations (a == 0). Zero discriminant invented."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    problem_type: Literal["DEGENERATE"] = "DEGENERATE"
    problem_id: str
    raw_query: Optional[str] = None
    equation_latex: str = Field(..., description="e.g. 2x - 4 = 0")
    category: Literal[ProblemCategory.ALGEBRA_QUADRATIC] = ProblemCategory.ALGEBRA_QUADRATIC
    classification: Literal[
        EquationClassificationType.LINEAR,
        EquationClassificationType.IDENTITY,
        EquationClassificationType.CONTRADICTION
    ]
    a: RationalFraction = Field(default_factory=lambda: RationalFraction(numerator=0, denominator=1))
    b: RationalFraction
    c: RationalFraction
    linear_root: Optional[RationalFraction] = None
    semantic_revision_hash: str


CanonicalProblemUnion = Annotated[
    Union[CanonicalQuadraticProblemView, CanonicalDegenerateProblemView],
    Field(discriminator="problem_type")
]
```

### 5.3 Response State Machine Union

```python
class MethodOptionView(BaseModel):
    """Orthogonal assessment profile of a single registered method."""
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
    has_trace_available: bool
    pedagogical_priority: int


class VerifiedSolutionView(BaseModel):
    """Verified execution result and step-by-step trace."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    method_id: str
    outcome: SolutionOutcome
    roots: List[RealRootValue]
    final_answer_latex: str
    trace: Optional[SolutionTrace] = None
    certificate: VerificationCertificate


class SolvedResponse(BaseModel):
    """Response state when problem is analyzed AND an applicable/available method is verified."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["SOLVED"] = "SOLVED"
    problem: CanonicalProblemUnion
    available_methods: List[MethodOptionView]
    selected_method_id: str
    solution: VerifiedSolutionView


class AnalyzedNoExecutionResponse(BaseModel):
    """Response state when problem is analyzed but no trace executed (e.g. unavailable method selected or degenerate linear)."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["ANALYZED_NO_EXECUTION"] = "ANALYZED_NO_EXECUTION"
    problem: CanonicalProblemUnion
    available_methods: List[MethodOptionView] = Field(default_factory=list)
    selected_method_id: Optional[str] = None
    degenerate_solution: Optional[DegenerateSolutionView] = None
    analysis_message_vi: str


class ErrorResponse(BaseModel):
    """Response state when a fatal intake, parse, normalization, or invariant error occurs."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    response_status: Literal["ERROR"] = "ERROR"
    error_code: ApplicationErrorCode
    message_vi: str
    message_en: str
    span: Optional[Tuple[int, int]] = None
    details: Dict[str, Any] = Field(default_factory=dict)


SolveResponseUnion = Annotated[
    Union[SolvedResponse, AnalyzedNoExecutionResponse, ErrorResponse],
    Field(discriminator="response_status")
]
```

---

## 6. Degenerate Equation Verification & Trust Model

### 6.1 Degenerate Solver & Verifier (`src/mke_product/application/degenerate.py`)
Degenerate equations ($a = 0$) do not use `HostIndependentVerifier.verify_quadratic_solution()`. They are verified deterministically by `verify_degenerate_solution()`:

1. **LINEAR ($b \neq 0$):**
   - Exact root: $r = -c/b \in \mathbb{Q}$.
   - Independent verification: Check exact rational residual $b \cdot r + c == 0$.
   - Yields `VerificationCertificate` certifying `outcome = VERIFIED_COMPLETE`.
2. **IDENTITY ($b = 0, c = 0$):**
   - Verification: Check $b == 0 \land c == 0$. Residual is identically zero for all $x \in \mathbb{R}$.
   - Certifies `INFINITE_REAL_SOLUTIONS`.
3. **CONTRADICTION ($b = 0, c \neq 0$):**
   - Verification: Check $b == 0 \land c \neq 0 \implies 0 \cdot x + c \neq 0$.
   - Certifies `NO_REAL_SOLUTIONS_CONTRADICTION` ($S = \emptyset$).

### 6.2 Verification Scope & Trust Model
- **`verification_scope = "FINAL_SOLUTION"`:** The `VerificationCertificate` explicitly certifies that the final mathematical root set / solution claim is independently verified over $\mathbb{Q}$ or $\mathbb{Q}(\sqrt{d})$.
- **Trace Generators as Presentation Formatters:** Step-by-step traces are deterministic presentation formatters derived from the canonical exact mathematical state. They are structurally typed but not individually theorem-proven in S1 (trace-level step proof engine is a planned S3 extension).

---

## 7. Selected Method Semantics & Deterministic Selection Policy

The orchestrator enforces a strictly deterministic selection policy without silent fallbacks:

```python
def resolve_method_selection(
    assessments: List[MethodAssessment],
    requested_method_id: Optional[str]
) -> tuple[MethodAssessment, Optional[ApplicationErrorCode]]:
    assessment_map = {m.method_id: m for m in assessments}

    if requested_method_id is not None:
        if requested_method_id not in assessment_map:
            return None, ApplicationErrorCode.METHOD_NOT_FOUND
        target = assessment_map[requested_method_id]
        if target.mathematical_applicability != MathematicalApplicability.APPLICABLE:
            return target, ApplicationErrorCode.METHOD_NOT_APPLICABLE
        if target.execution_availability != ExecutionAvailability.AVAILABLE:
            return target, ApplicationErrorCode.METHOD_NOT_EXECUTABLE
        return target, None

    # Default automated selection:
    # Filter methods with APPLICABLE and AVAILABLE
    candidates = [
        m for m in assessments
        if m.mathematical_applicability == MathematicalApplicability.APPLICABLE
        and m.execution_availability == ExecutionAvailability.AVAILABLE
    ]
    # Tie-breaker: lowest pedagogical_priority number (1 is highest), then registry insertion order
    candidates.sort(key=lambda m: m.pedagogical_priority)
    return candidates[0], None
```

---

## 8. Corrected Application Workspace DAG

The Application Workspace DAG extends the domain DAG with intake, parameter, and response projection nodes:

```
[RAW_TEXT Mode]                                    [COEFFICIENT Mode]
   (raw_query)                                  (direct_coefficients)
        |                                                 |
        v                                                 |
(ast_parsed_node)                                         |
        |                                                 |
        +-----------------------+-------------------------+
                                |
                                v
                     [coefficients: (a,b,c)]
                         /           \
                        v             v
             [classification]     [discriminant] (if a != 0)
                        \             /
                         v           v
                      [exact_solution_set]
                         /           \
                        v             v
             [method_assessments]   [semantic_identity]
                        \             /
                         v           v
                  [selected_method_id]
                         /           \
                        v             v
             [solution_trace]     [verification_certificate]
                        \             /
                         v           v
                     [solve_response]
```

---

## 9. Future Product Extension Points (Decoupled Architecture)

To support future frontend capabilities without polluting core mathematical models:

1. **Learning Support / Knowledge Cards Service:**
   An optional sidecar service `LearningSupportService` queries `(problem_category, selected_method_id)` to attach:
   - `QuickTipCard` (e.g. "Mẹo nhẩm nhanh: Khi $a+b+c=0$, nghiệm luôn là 1 và $c/a$").
   - `FormulaReferenceCard` (LaTeX formulas, conditions, GDPT 2018 grade mapping).
   - `RelatedProblemRecommendation` (retrieval of similar quadratic equations).
2. **Interactive Parabola Graph Canvas:**
   Frontend derives vertex $(-\frac{b}{2a}, -\frac{\Delta}{4a})$, roots, axis of symmetry, and y-intercept directly from `CanonicalQuadraticProblemView` without backend rendering coupling.
3. **Persistent Session State:**
   Frontend serializes `problem.semantic_revision_hash` and `selected_method_id` into URL parameters or localStorage.

---

## 10. Comprehensive Acceptance Matrix (Full Canonical IDs)

| Case ID | Intake Mode | Input Payload | Expected Classification / $(a,b,c)$ | Expected Outcome / Roots | Expected Applicable Methods | Executable in S1 | Verification Outcome | Expected Status / Error Code |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1** | `RAW_TEXT` | `x^2 - 5*x + 6 = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SUM_PRODUCT` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q2** | `RAW_TEXT` | `x^2 - 2 = 0` | `QUADRATIC` (1, 0, -2) | `TWO_DISTINCT_REAL_ROOTS` $\{-\sqrt{2}, \sqrt{2}\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q3** | `RAW_TEXT` | `x^2 - 2*x + 1 = 0` | `QUADRATIC` (1, -2, 1) | `ONE_REPEATED_REAL_ROOT` $\{1\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SPECIAL_SUM` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_SUM` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q4** | `RAW_TEXT` | `x^2 + 1 = 0` | `QUADRATIC` (1, 0, 1) | `NO_REAL_ROOTS` $\emptyset$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_COMPLETE_SQUARE` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q5** | `RAW_TEXT` | `2*x^2 - 5*x + 2 = 0` | `QUADRATIC` (2, -5, 2) | `TWO_DISTINCT_REAL_ROOTS` $\{1/2, 2\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q6** | `RAW_TEXT` | `x^2 + 6 = 5*x` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q7** | `RAW_TEXT` | `(x - 2)*(x - 3) = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q8** | `RAW_TEXT` | `(x + 1)^2 = 0` | `QUADRATIC` (1, 2, 1) | `ONE_REPEATED_REAL_ROOT` $\{-1\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SPECIAL_DIF` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_DIF` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q9** | `RAW_TEXT` | `(1/2)*x^2 - (5/4)*x + 3/4 = 0` | `QUADRATIC` (1/2, -5/4, 3/4) | `TWO_DISTINCT_REAL_ROOTS` $\{1, 3/2\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_SUM` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_SUM` | `VERIFIED_COMPLETE` | `SOLVED` |
| **C1** | `COEFFICIENTS` | `a=1, b=-5, c=6` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **M1** | `METHOD_SWITCH` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_FORMULA_REDUCED"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods | `QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **M2** | `METHOD_SWITCH` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_MAGIC_METHOD"` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`METHOD_NOT_FOUND`) |
| **M3** | `METHOD_SWITCH` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_VIETE_SPECIAL_SUM"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` | Canonical Q1 methods | None (Requested is not applicable) | N/A | `ANALYZED_NO_EXECUTION` (`METHOD_NOT_APPLICABLE`) |
| **M4** | `METHOD_SWITCH` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_COMPLETE_SQUARE"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` | Canonical Q1 methods | None (Requested is unavailable in S1) | N/A | `ANALYZED_NO_EXECUTION` (`METHOD_NOT_EXECUTABLE`) |
| **D1** | `RAW_TEXT` | `2*x - 4 = 0` | `LINEAR` (0, 2, -4) | `ONE_REAL_LINEAR_ROOT` $\{2\}$ | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **D2** | `RAW_TEXT` | `0 = 0` | `IDENTITY` (0, 0, 0) | `INFINITE_REAL_SOLUTIONS` | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **D3** | `RAW_TEXT` | `1 = 0` | `CONTRADICTION` (0, 0, 1) | `NO_REAL_SOLUTIONS_CONTRADICTION` | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **E1** | `RAW_TEXT` | `x^2 + = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`SYNTAX_ERROR`) |
| **E2** | `RAW_TEXT` | `x^3 - 2*x + 1 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DEGREE_OUT_OF_SCOPE`) |
| **E3** | `RAW_TEXT` | `(x^2 + 1)*(x + 1) = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DEGREE_OUT_OF_SCOPE`) |
| **E4** | `RAW_TEXT` | `y^2 - 4 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`UNSUPPORTED_VARIABLE`) |
| **E5** | `RAW_TEXT` | `1/x = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`NON_POLYNOMIAL_INPUT`) |
| **E6** | `RAW_TEXT` | `x^2 / 0 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DIVISION_BY_ZERO`) |
| **E7** | `RAW_TEXT` | `sin(x) = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`UNSUPPORTED_SYNTAX`) |
| **E8** | `RAW_TEXT` | `2x = 4` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`IMPLICIT_MULTIPLICATION_UNSUPPORTED`) |
| **E9** | `RAW_TEXT` | (Length = 257 chars) | N/A | N/A | N/A | N/A | N/A | `ERROR` (`INPUT_LIMIT_EXCEEDED`) |

---

## 11. Implementation Stages for S1

- **Stage S1-01: Application Normalizer & Error Mapping (`src/mke_product/application/normalizer.py`, `errors.py`)**
  - Implement `PolynomialQDegree2` and AST reduction.
  - Implement typed error mapping from parser/lexer exceptions.
- **Stage S1-02: Degenerate Solver & Verifier (`src/mke_product/application/degenerate.py`)**
  - Implement exact evaluation and residual verification for LINEAR, IDENTITY, and CONTRADICTION equations.
- **Stage S1-03: Solution Trace Generators (`src/mke_product/application/traces/`)**
  - Implement deterministic step generators for `QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`.
- **Stage S1-04: Application Orchestrator & Discriminated DTOs (`src/mke_product/application/orchestrator.py`, `dto.py`)**
  - Implement request dispatch for `RAW_TEXT`, `COEFFICIENTS`, and `METHOD_SWITCH`.
  - Implement state machine construction (`SOLVED`, `ANALYZED_NO_EXECUTION`, `ERROR`).
- **Stage S1-05: Comprehensive Acceptance & Regression Verification**
  - Execute full 27-case acceptance matrix (Q1–Q9, C1, M1–M4, D1–D3, E1–E9).
  - Verify zero regressions across full 947-test repository suite.

---

## 12. Unresolved Questions & Implementation Recommendation

- **Unresolved Questions:** None. All 11 architectural blockers have been resolved with strict discriminated union typing, exact degenerate verification, truthful method selection semantics, and fail-closed normalization bounds.
- **Implementation Recommendation:** **`GO FOR S1 IMPLEMENTATION AUTHORIZATION`** upon independent auditor approval.
