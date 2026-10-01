# MKE MVP V1 — S1-P0 Backend Vertical Slice Architecture & Implementation Preflight

- **Document Identifier:** `docs/architecture/MVP_V1_S1_P0_BACKEND_VERTICAL_SLICE_PREFLIGHT.md`
- **Milestone:** MVP-V1-S1-P0-R2 (Final Backend Contract Closeout)
- **Document Version:** 1.2.0
- **Author:** Antigravity (Implementation Engineer)
- **Coordinator / Independent Auditor:** ChatGPT
- **Project Owner:** Kế Phan Hoàng
- **Repository:** `PhanHoangKe/math-knowledge-engine`
- **Working Branch:** `product/mvp-v1-s1-p0-backend-preflight`
- **Accepted S0 Baseline SHA:** `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`
- **Parent Preflight SHA:** `51964525bc7d3345e730ddce0ddc9c08f797b6ef`
- **Parked B3 Baseline SHA:** `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (`product/p03c-p1c-04-b3-exact-complex-preflight`)
- **Status:** `PENDING INDEPENDENT S1-P0-R2 FINAL AUDIT`
- **Date:** 2026-10-01

---

## 1. Executive Summary & Objective

The objective of `MVP-V1-S1-P0-R2` is to establish the final, frozen, mathematically rigorous backend vertical slice contract for the Math Knowledge Engine (MKE) MVP V1 algebra experience.

The vertical slice defines the pure-Python pipeline connecting:
1. **Intake Modes (Single Source of Authority):**
   - Raw equation string (`RawEquationInput`).
   - Direct canonical coefficient editing $[a, b, c]$ (`CanonicalCoefficientInput`).
   - Method selection is governed exclusively by `SolveRequest.selected_method_id` (zero dual-authority ambiguity).
2. **Deterministic Parsing & Typed Lexical Error Mapping:** Bounded P02A parser (`MAX_INPUT_LENGTH = 256`, `MAX_TOKEN_COUNT = 64`, `MAX_NESTING_DEPTH = 16`, variable $x$). Typed exception subclasses classify errors without string parsing.
3. **Exact Bounded Normalization:** Algebraic reduction in $\mathbb{Q}[x]$ for $\deg(P) \le 2$ via `PolynomialQDegree2`.
4. **Domain Classification & Discriminated IR Routing:**
   - $a \neq 0 \longrightarrow \text{QuadraticProblemIR}$ (with canonical $b^2 - 4ac$ discriminant).
   - $a = 0 \longrightarrow \text{DegenerateEquationIR}$ (LINEAR, IDENTITY, CONTRADICTION; zero discriminant invented).
5. **Orthogonal Method Assessment:** Exact assessment across all 9 canonical registry methods matching `MethodRegistry.assess_quadratic()` (including `QUAD_GRAPHICAL_ANALYSIS`).
6. **Selected Method Semantics & Trace Generation:** Deterministic execution without silent fallback for S1 executable methods (`QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`).
7. **Host Independent Verification:** Exact residual & invariant verification certifying final mathematical outcomes (`verification_scope = "FINAL_SOLUTION"`).
8. **Discriminated Response Union:** Strictly typed state machine (`SOLVED`, `ANALYZED_NO_EXECUTION`, `ERROR`) with complete `DegenerateSolutionView` definition and immutable invariants.

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
|  - All 9 Canonical Methods         |                       |  - Linear: b*r + c == 0            |
|  - Includes QUAD_GRAPHICAL_ANALYSIS|                       |  - Identity: 0 == 0                |
+------------------------------------+                       |  - Contradiction: c != 0           |
             |                                               +------------------------------------+
             v                                                                |
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
|   - VerifiedSolutionView   |       - DegenerateSolutionView        |           - Error Source Span    |
|   - Final Certificate      |       - Analysis Message              |                                  |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Component Reuse Classification Matrix (Accepted S0 Baseline)

Audited at baseline `ae9e533e99ba9d6a169a5fae27d6b5b245013f8e`:

| Component / Subsystem | Repository Path | Observed Constraints & Capabilities | Classification | Usage in S1 Vertical Slice |
| :--- | :--- | :--- | :--- | :--- |
| **Exact Rational Arithmetic** | `src/mke_product/core/rational.py` | Pure $\mathbb{Q}$ arithmetic ($p/q, \gcd(\|p\|, q)=1, q>0$), zero float authority. | `REUSE_DIRECT` | Foundational arithmetic authority for normalization and solvers. |
| **P02A Lexer & Parser** | `src/mke_product/parser/` | Bounded recursive descent grammar ($x$, exponents $\in \{0,1,2\}$, nesting $\le 16$, tokens $\le 64$, length $\le 256$). | `REUSE_VIA_ADAPTER` | Parses raw input string into raw `Equation` AST. Enriched with typed error subclasses. |
| **Domain Models & Invariants** | `src/mke_product/domain/models.py` | Pydantic v2 strict models with runtime semantic invariants (`QuadraticProblemIR`, `DegenerateEquationIR`, etc.). | `REUSE_DIRECT` | Immutable domain representations of mathematical truth. |
| **Exact Algebraic Kernel** | `src/mke_product/domain/exact.py` | Squarefree kernel decomposition, discriminant computation, exact real quadratic solving. | `REUSE_DIRECT` | Computes canonical discriminants and closed-form real roots in $\mathbb{Q}(\sqrt{d})$. |
| **Method Registry & Evaluator** | `src/mke_product/domain/registry.py` | Catalog of 9 quadratic methods with 5D orthogonal assessment. | `REUSE_DIRECT` | Assesses problem-level mathematical applicability and capability states. |
| **Host Independent Verifier** | `src/mke_product/domain/verifier.py` | Zero-CAS residual checks, Viète relations, sign stability, SHA-256 integrity fingerprinting. | `REUSE_DIRECT` | Issues tamper-evident `VerificationCertificate` certifying final mathematical root set. |
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

## 4. Exact Normalization & Deterministic Parser Error Classification

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

### 4.3 Deterministic Typed Parser Error Classification
The application layer classifies parsing failures using explicit exception types with source spans. **No human-readable message string matching is used.**

During S1-01, the parser error hierarchy is finalized with typed subclasses deriving from `MKEParserError`:

```python
class MKEParserError(MKEProductError):
    """Base exception for parser errors containing optional source Span."""
    def __init__(self, message: str, span: Optional[Span] = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span

class UnsupportedVariableError(MKEParserError):
    """Raised when variable symbol != 'x' is encountered."""
    pass

class UnsupportedSyntaxError(MKEParserError):
    """Raised when unsupported identifiers/functions (e.g. sin, cos, log) are encountered."""
    pass

class UnsupportedExponentError(MKEParserError):
    """Raised when an exponent literal > 2 is parsed in AST."""
    pass

class ImplicitMultiplicationError(ParserError):
    """Raised when implicit multiplication is detected between adjacent tokens."""
    pass

class InputBoundsExceededError(MKEParserError):
    """Raised when input length > 256, token count > 64, or nesting depth > 16."""
    pass
```

Deterministic mapping table:

| Exception Class Raised | Concrete Trigger | Mapped `ApplicationErrorCode` | Localized Message (VI) |
| :--- | :--- | :--- | :--- |
| `UnsupportedVariableError` | Input `y^2 - 4 = 0` | `UNSUPPORTED_VARIABLE` | Biến số không được hỗ trợ. MVP V1 chỉ hỗ trợ biến 'x'. |
| `UnsupportedSyntaxError` | Input `sin(x) = 0` | `UNSUPPORTED_SYNTAX` | Hàm siêu việt không thuộc phạm vi đa thức bậc hai. |
| `UnsupportedExponentError` | Input `x^3 = 0` | `DEGREE_OUT_OF_SCOPE` | Bậc của phương trình vượt quá giới hạn bậc hai (deg <= 2). |
| `ImplicitMultiplicationError` | Input `2x = 4` | `IMPLICIT_MULTIPLICATION_UNSUPPORTED` | Phép nhân ẩn không được hỗ trợ. Vui lòng viết rõ '2*x'. |
| `InputBoundsExceededError` | Length $> 256$, Depth $> 16$, Tokens $> 64$ | `INPUT_LIMIT_EXCEEDED` | Giới hạn độ dài chuỗi (256), token (64) hoặc độ sâu lồng (16) bị vượt quá. |
| `ParserError` (base) | Input `x^2 + = 0` | `SYNTAX_ERROR` | Cú pháp phương trình không hợp lệ. |

---

## 5. Application Request & Response Contracts (Discriminated Unions)

### 5.1 Request Contracts (`src/mke_product/application/dto.py`)

> [!NOTE]
> **Single Source of Method-Selection Authority:** `SolveRequest.selected_method_id` is the **only** field governing explicit method selection. `MethodSwitchInput` is removed.
> Live coefficient editing and method switching are supported statelessly via `CanonicalCoefficientInput` + `selected_method_id` with zero text parsing overhead.

```python
class RawEquationInput(BaseModel):
    """Raw text equation input mode."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["RAW_TEXT"] = "RAW_TEXT"
    raw_query: str = Field(..., min_length=1, max_length=256, description="Raw equation string e.g. 'x^2 - 5*x + 6 = 0'")
    target_variable: Literal["x"] = "x"


class CanonicalCoefficientInput(BaseModel):
    """Direct coefficient parameter input mode for reactive live editing and method switching."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_mode: Literal["COEFFICIENTS"] = "COEFFICIENTS"
    a: RationalFraction = Field(..., description="Leading coefficient a")
    b: RationalFraction = Field(..., description="Linear coefficient b")
    c: RationalFraction = Field(..., description="Constant term c")
    target_variable: Literal["x"] = "x"


InputPayloadUnion = Annotated[
    Union[RawEquationInput, CanonicalCoefficientInput],
    Field(discriminator="input_mode")
]


class SolveRequest(BaseModel):
    """Client request container for equation analysis and solving."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    input_payload: InputPayloadUnion
    selected_method_id: Optional[str] = Field(
        None, description="Explicit method selection ID. If None, highest-priority applicable method is executed."
    )
    schema_version: str = "1.0.0"
```

### 5.2 Direct Coefficient Provenance & Semantic Identity Equivalence

When `CanonicalCoefficientInput` is provided, the domain bridge constructs canonical problem representations deterministically:

1. **Equation Source String Construction:**
   - Quadratic ($a \neq 0$): `f"{a}*x^2 + {b}*x + {c} = 0"` using exact `RationalFraction` canonical strings (e.g. `1*x^2 + -5*x + 6 = 0`).
   - Degenerate ($a = 0$): `f"{b}*x + {c} = 0"` (e.g. `2*x + -4 = 0`).
2. **Explicit Provenance:**
   - `raw_query_provenance = "SYSTEM_CANONICAL_COEFFICIENTS"`.
3. **Mandatory Semantic Identity Equivalence Invariant:**
   For any equation whose coefficients evaluate to the same $(a, b, c) \in \mathbb{Q}^3$, the computed `semantic_revision_hash` is **strictly identical**, regardless of whether intake occurred via `RAW_TEXT` or `COEFFICIENTS`:
   $$\text{hash}(\text{RAW\_TEXT: } "x^2 - 5*x + 6 = 0") == \text{hash}(\text{COEFFICIENTS: } a=1, b=-5, c=6)$$
   This invariant is guaranteed because `compute_semantic_quadratic_identity()` in `src/mke_product/domain/identity.py` hashes only `(schema_version, category, target_variable, a, b, c, coefficient_domain, solution_domain, assumptions)` and excludes presentation strings or intake provenance.

### 5.3 Canonical Problem Discriminated Union

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

### 5.4 Degenerate Solution Contract (`DegenerateSolutionView`)

```python
class DegenerateSolutionView(BaseModel):
    """Immutable verified solution presentation for degenerate equations (a == 0)."""
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    outcome: Literal[
        SolutionOutcome.ONE_REAL_LINEAR_ROOT,
        SolutionOutcome.INFINITE_REAL_SOLUTIONS,
        SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
    ]
    linear_root: Optional[RationalFraction] = Field(
        None, description="Exact rational root -c/b when outcome is ONE_REAL_LINEAR_ROOT"
    )
    final_answer_latex: str = Field(..., description="Canonical LaTeX representation of the solution set")
    verification_scope: Literal["FINAL_SOLUTION"] = "FINAL_SOLUTION"
    certificate: VerificationCertificate

    @model_validator(mode="after")
    def _validate_degenerate_solution_invariants(self) -> DegenerateSolutionView:
        """Enforce strict consistency between outcome and root fields."""
        if self.outcome == SolutionOutcome.ONE_REAL_LINEAR_ROOT:
            if self.linear_root is None:
                raise ValueError("linear_root must be provided when outcome is ONE_REAL_LINEAR_ROOT.")
        elif self.outcome in (SolutionOutcome.INFINITE_REAL_SOLUTIONS, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION):
            if self.linear_root is not None:
                raise ValueError(f"linear_root must be None when outcome is {self.outcome}.")
        return self
```

### 5.5 Response State Machine Union

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
    verification_scope: Literal["FINAL_SOLUTION"] = "FINAL_SOLUTION"
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
   - Certifies `outcome = VERIFIED_COMPLETE` with `INFINITE_REAL_SOLUTIONS`.
3. **CONTRADICTION ($b = 0, c \neq 0$):**
   - Verification: Check $b == 0 \land c \neq 0 \implies 0 \cdot x + c \neq 0$.
   - Certifies `outcome = VERIFIED_COMPLETE` with `NO_REAL_SOLUTIONS_CONTRADICTION` ($S = \emptyset$).

### 6.2 Verification Scope & Trust Model
- **No Modification to Domain `VerificationCertificate`:** S0 `VerificationCertificate` has `extra="forbid"` and remains untouched.
- **Application Level Scope Annotation:** `VerifiedSolutionView` and `DegenerateSolutionView` wrap `VerificationCertificate` with `verification_scope = "FINAL_SOLUTION"`.
- **Scope Semantics:** The certificate verifies the **final mathematical solution set / root claim** from first principles over $\mathbb{Q}$ and $\mathbb{Q}(\sqrt{d})$.
- **Deterministic Step Formatting:** `SolutionTrace` steps are deterministic pedagogical derivations. They are structurally typed but are **NOT** independently theorem-proven in S1. No `StepVerificationCertificate` is claimed or introduced.

---

## 7. Method Registry & Deterministic Selection Policy

### 7.1 Canonical 9-Method Registry
The MKE method catalog contains exactly 9 canonical methods (`MethodRegistry`):

| Method ID | Vietnamese Pedagogical Title | Problem Family | S0/S1 Support Status | S0/S1 Execution Availability | Verification Capability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `QUAD_FORMULA_STANDARD` | Công thức nghiệm tổng quát | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `AVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_FORMULA_REDUCED` | Công thức nghiệm thu gọn | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `AVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_FACTORIZATION_Q` | Phân tích nhân tử trên $\mathbb{Q}$ (Tách ac) | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `UNAVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_FACTORIZATION_R` | Phân tích nhân tử trên $\mathbb{R}$ | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `UNAVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_COMPLETE_SQUARE` | Biến đổi tách bình phương | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `UNAVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SPECIAL_SUM` | Nhẩm nghiệm đặc biệt $a + b + c = 0$ | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `AVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SPECIAL_DIF` | Nhẩm nghiệm đặc biệt $a - b + c = 0$ | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `AVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_VIETE_SUM_PRODUCT` | Tìm hai số theo Tổng và Tích (Hệ thức Viète) | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `UNAVAILABLE` | `HOST_VERIFIABLE` |
| `QUAD_GRAPHICAL_ANALYSIS` | Khảo sát hình học đồ thị Parabol | `ALGEBRA_QUADRATIC` | `SUPPORTED` | `UNAVAILABLE` | `NOT_APPLICABLE` |

### 7.2 Selection Policy
```python
def resolve_method_selection(
    assessments: List[MethodAssessment],
    requested_method_id: Optional[str]
) -> tuple[Optional[MethodAssessment], Optional[ApplicationErrorCode]]:
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

    # Automated selection: Filter APPLICABLE + AVAILABLE
    candidates = [
        m for m in assessments
        if m.mathematical_applicability == MathematicalApplicability.APPLICABLE
        and m.execution_availability == ExecutionAvailability.AVAILABLE
    ]
    if not candidates:
        return None, None
    # Tie-breaker: lowest pedagogical_priority (1 = highest), then registry insertion order
    candidates.sort(key=lambda m: m.pedagogical_priority)
    return candidates[0], None
```

---

## 8. Corrected Application Workspace DAG

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

1. **Learning Support / Knowledge Cards Service:**
   An optional sidecar service `LearningSupportService` queries `(problem_category, selected_method_id)` to attach `QuickTipCard`, `FormulaReferenceCard`, and `RelatedProblemRecommendation`.
2. **Interactive Parabola Graph Canvas:**
   Frontend derives vertex $(-\frac{b}{2a}, -\frac{\Delta}{4a})$, roots, axis of symmetry, and y-intercept directly from `CanonicalQuadraticProblemView` without backend rendering coupling.
3. **Persistent Session State:**
   Frontend serializes `problem.semantic_revision_hash` and `selected_method_id` into URL parameters or localStorage.

---

## 10. Comprehensive Acceptance Matrix (32 Distinct Rows)

Every quadratic row is audited directly against `MethodRegistry.assess_quadratic()`, including `QUAD_GRAPHICAL_ANALYSIS`.

| Row ID | Group | Intake Mode | Input Payload / Parameters | Expected Classification / $(a,b,c)$ | Expected Outcome / Roots | Expected Applicable Methods (Assessments) | Executable in S1 | Verification Outcome | Expected Response Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1** | Quadratic | `RAW_TEXT` | `x^2 - 5*x + 6 = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SUM_PRODUCT`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q2** | Quadratic | `RAW_TEXT` | `x^2 - 2 = 0` | `QUADRATIC` (1, 0, -2) | `TWO_DISTINCT_REAL_ROOTS` $\{-\sqrt{2}, \sqrt{2}\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q3** | Quadratic | `RAW_TEXT` | `x^2 - 2*x + 1 = 0` | `QUADRATIC` (1, -2, 1) | `ONE_REPEATED_REAL_ROOT` $\{1\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SPECIAL_SUM`<br>`QUAD_VIETE_SUM_PRODUCT`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_SUM` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q4** | Quadratic | `RAW_TEXT` | `x^2 + 1 = 0` | `QUADRATIC` (1, 0, 1) | `NO_REAL_ROOTS` $\emptyset$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q5** | Quadratic | `RAW_TEXT` | `2*x^2 - 5*x + 2 = 0` | `QUADRATIC` (2, -5, 2) | `TWO_DISTINCT_REAL_ROOTS` $\{1/2, 2\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SUM_PRODUCT`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q6** | Quadratic | `RAW_TEXT` | `x^2 + 6 = 5*x` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods (7 methods) | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q7** | Quadratic | `RAW_TEXT` | `(x - 2)*(x - 3) = 0` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods (7 methods) | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q8** | Quadratic | `RAW_TEXT` | `(x + 1)^2 = 0` | `QUADRATIC` (1, 2, 1) | `ONE_REPEATED_REAL_ROOT` $\{-1\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SPECIAL_DIF`<br>`QUAD_VIETE_SUM_PRODUCT`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_DIF` | `VERIFIED_COMPLETE` | `SOLVED` |
| **Q9** | Quadratic | `RAW_TEXT` | `(1/2)*x^2 - (5/4)*x + 3/4 = 0` | `QUADRATIC` (1/2, -5/4, 3/4) | `TWO_DISTINCT_REAL_ROOTS` $\{1, 3/2\}$ | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_FACTORIZATION_Q`<br>`QUAD_FACTORIZATION_R`<br>`QUAD_COMPLETE_SQUARE`<br>`QUAD_VIETE_SPECIAL_SUM`<br>`QUAD_VIETE_SUM_PRODUCT`<br>`QUAD_GRAPHICAL_ANALYSIS` | `QUAD_FORMULA_STANDARD`<br>`QUAD_FORMULA_REDUCED`<br>`QUAD_VIETE_SPECIAL_SUM` | `VERIFIED_COMPLETE` | `SOLVED` |
| **C1** | Direct Coeff | `COEFFICIENTS` | `a=1, b=-5, c=6`, `selected_method_id=None` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods (7 methods) | `QUAD_FORMULA_STANDARD` (Default) | `VERIFIED_COMPLETE` | `SOLVED` |
| **C2** | Method Switch | `COEFFICIENTS` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_FORMULA_REDUCED"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` $\{2, 3\}$ | Canonical Q1 methods (7 methods) | `QUAD_FORMULA_REDUCED` | `VERIFIED_COMPLETE` | `SOLVED` |
| **C3** | Method Switch | `COEFFICIENTS` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_UNKNOWN_ID"` | `QUADRATIC` (1, -5, 6) | N/A | Canonical Q1 methods | None | N/A | `ERROR` (`METHOD_NOT_FOUND`) |
| **C4** | Method Switch | `COEFFICIENTS` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_VIETE_SPECIAL_SUM"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` | Canonical Q1 methods | None (Not Applicable: $1-5+6 \neq 0$) | N/A | `ANALYZED_NO_EXECUTION` (`METHOD_NOT_APPLICABLE`) |
| **C5** | Method Switch | `COEFFICIENTS` | `a=1, b=-5, c=6`, `selected_method_id="QUAD_COMPLETE_SQUARE"` | `QUADRATIC` (1, -5, 6) | `TWO_DISTINCT_REAL_ROOTS` | Canonical Q1 methods | None (Unavailable in S1) | N/A | `ANALYZED_NO_EXECUTION` (`METHOD_NOT_EXECUTABLE`) |
| **D1** | Degenerate | `RAW_TEXT` | `2*x - 4 = 0` | `LINEAR` (0, 2, -4) | `ONE_REAL_LINEAR_ROOT` $\{2\}$ | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **D2** | Degenerate | `RAW_TEXT` | `0 = 0` | `IDENTITY` (0, 0, 0) | `INFINITE_REAL_SOLUTIONS` | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **D3** | Degenerate | `RAW_TEXT` | `1 = 0` | `CONTRADICTION` (0, 0, 1) | `NO_REAL_SOLUTIONS_CONTRADICTION` | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **D4** | Degenerate | `COEFFICIENTS` | `a=0, b=2, c=-4`, `selected_method_id=None` | `LINEAR` (0, 2, -4) | `ONE_REAL_LINEAR_ROOT` $\{2\}$ | N/A (Degenerate) | N/A | `VERIFIED_COMPLETE` | `ANALYZED_NO_EXECUTION` |
| **E1** | Error/Scope | `RAW_TEXT` | `x^2 + = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`SYNTAX_ERROR`) |
| **E2** | Error/Scope | `RAW_TEXT` | `x^3 - 2*x + 1 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DEGREE_OUT_OF_SCOPE`) |
| **E3** | Error/Scope | `RAW_TEXT` | `(x^2 + 1)*(x + 1) = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DEGREE_OUT_OF_SCOPE`) |
| **E4** | Error/Scope | `RAW_TEXT` | `y^2 - 4 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`UNSUPPORTED_VARIABLE`) |
| **E5** | Error/Scope | `RAW_TEXT` | `1/x = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`NON_POLYNOMIAL_INPUT`) |
| **E6** | Error/Scope | `RAW_TEXT` | `x^2 / 0 = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`DIVISION_BY_ZERO`) |
| **E7** | Error/Scope | `RAW_TEXT` | `sin(x) = 0` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`UNSUPPORTED_SYNTAX`) |
| **E8** | Error/Scope | `RAW_TEXT` | `2x = 4` | N/A | N/A | N/A | N/A | N/A | `ERROR` (`IMPLICIT_MULTIPLICATION_UNSUPPORTED`) |
| **B1** | Bound Check | `RAW_TEXT` | Length $= 256$ chars (e.g. `x^2` + repeated `+ 0` padding `= 0`) | `QUADRATIC` (1, 0, 0) | `ONE_REPEATED_REAL_ROOT` $\{0\}$ | Canonical quadratic methods | `QUAD_FORMULA_STANDARD` | `VERIFIED_COMPLETE` | `SOLVED` (Resource check passes) |
| **B2** | Bound Check | `RAW_TEXT` | Length $= 257$ chars | N/A | N/A | N/A | N/A | N/A | `ERROR` (`INPUT_LIMIT_EXCEEDED`) |
| **B3** | Bound Check | `RAW_TEXT` | Nesting depth $= 16$ (16 pairs of parens) | `QUADRATIC` (1, 0, -1) | `TWO_DISTINCT_REAL_ROOTS` $\{-1, 1\}$ | Canonical quadratic methods | `QUAD_FORMULA_STANDARD` | `VERIFIED_COMPLETE` | `SOLVED` (Resource check passes) |
| **B4** | Bound Check | `RAW_TEXT` | Nesting depth $= 17$ (17 pairs of parens) | N/A | N/A | N/A | N/A | N/A | `ERROR` (`INPUT_LIMIT_EXCEEDED`) |
| **B5** | Bound Check | `RAW_TEXT` | Token count $= 64$ tokens | Valid parsed polynomial | Evaluated roots | Canonical quadratic methods | `QUAD_FORMULA_STANDARD` | `VERIFIED_COMPLETE` | `SOLVED` (Resource check passes) |
| **B6** | Bound Check | `RAW_TEXT` | Token count $= 65$ tokens | N/A | N/A | N/A | N/A | N/A | `ERROR` (`INPUT_LIMIT_EXCEEDED`) |

*Total Acceptance Matrix Row Count:* **32 rows** (9 Quadratic, 5 Direct/Method-Switch, 4 Degenerate, 8 Error/Scope, 6 Resource Boundary).

---

## 11. Response State Invariants & Schema Guarantees

The discriminated response union `SolveResponseUnion` enforces the following mathematical and schema guarantees:

1. **`SOLVED` Invariants:**
   - `response_status == "SOLVED"`.
   - `problem` is always a `CanonicalQuadraticProblemView` ($a \neq 0$) with exact canonical `discriminant`.
   - `solution` is `VerifiedSolutionView` with `solution.certificate.outcome == VerificationOutcome.VERIFIED_COMPLETE`.
   - `selected_method_id == solution.method_id`.
   - `solution.method_id` is guaranteed to have `mathematical_applicability == APPLICABLE` and `execution_availability == AVAILABLE`.
2. **`ANALYZED_NO_EXECUTION` Invariants:**
   - `response_status == "ANALYZED_NO_EXECUTION"`.
   - For quadratic problems: `problem` is `CanonicalQuadraticProblemView`. If `selected_method_id` is present, it points to a method with `UNAVAILABLE` or `NOT_APPLICABLE`. `solution` is strictly `None`. Cannot contain fake or fabricated execution traces.
   - For degenerate equations: `problem` is `CanonicalDegenerateProblemView` ($a = 0$). `degenerate_solution` is `DegenerateSolutionView` with `certificate.outcome == VerificationOutcome.VERIFIED_COMPLETE`.
3. **`ERROR` Invariants:**
   - `response_status == "ERROR"`.
   - Carries structured `error_code`, `message_vi`, `message_en`, and optional `span`.
   - Cannot contain verified mathematical roots, canonical problem views, or certificates.
4. **Intake Invariance Invariant:**
   - Intake mode (`RAW_TEXT` vs `COEFFICIENTS`) does not alter mathematical truth or semantic identity.
   - For any equivalent problem, `problem.semantic_revision_hash` is strictly invariant.
5. **No Undefined DTOs:**
   - All models (`SolvedResponse`, `AnalyzedNoExecutionResponse`, `ErrorResponse`, `DegenerateSolutionView`, `VerifiedSolutionView`, `CanonicalQuadraticProblemView`, `CanonicalDegenerateProblemView`, etc.) are fully specified and closed under Pydantic v2 `extra="forbid"`.

---

## 12. Implementation Stages for S1

- **Stage S1-01: Application Normalizer & Error Mapping (`src/mke_product/application/normalizer.py`, `errors.py`)**
  - Implement `PolynomialQDegree2` and AST reduction.
  - Implement typed parser error exception hierarchy and mapping.
- **Stage S1-02: Degenerate Solver & Verifier (`src/mke_product/application/degenerate.py`)**
  - Implement exact evaluation and residual verification for LINEAR, IDENTITY, and CONTRADICTION equations.
- **Stage S1-03: Solution Trace Generators (`src/mke_product/application/traces/`)**
  - Implement deterministic step generators for `QUAD_FORMULA_STANDARD`, `QUAD_FORMULA_REDUCED`, `QUAD_VIETE_SPECIAL_SUM`, `QUAD_VIETE_SPECIAL_DIF`.
- **Stage S1-04: Application Orchestrator & Discriminated DTOs (`src/mke_product/application/orchestrator.py`, `dto.py`)**
  - Implement request dispatch for `RAW_TEXT` and `COEFFICIENTS`.
  - Implement single-authority method selection resolution.
  - Implement state machine construction (`SOLVED`, `ANALYZED_NO_EXECUTION`, `ERROR`).
- **Stage S1-05: Comprehensive Acceptance & Regression Verification**
  - Execute full 32-case acceptance matrix (Q1–Q9, C1–C5, D1–D4, E1–E8, B1–B6).
  - Verify zero regressions across full repository test suite.

---

## 13. Unresolved Questions & Implementation Recommendation

- **Unresolved Questions:** None. All R2 closeout items (R2-01 through R2-08) are fully addressed and frozen.
- **Implementation Recommendation:** **`GO FOR S1 IMPLEMENTATION AUTHORIZATION`** upon independent auditor approval.
