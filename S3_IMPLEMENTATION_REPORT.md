# MKE PRODUCT-02A-S3 Implementation Report
**Milestone:** Exact Linear Equation Solver (including S3-R1 Preflight Remediation, S3-R2 Final Solver Remediation, and S3-R3 Test Evidence Closure)  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `75d3b6a57198740ac1154ee6f309099b199cfcf9`  
**S3-R1 Base Commit:** `8c5382159bbd88d82e67a1b1e8e44f75a23a85aa`  
**S3-R2 Base Commit:** `1cbcc72cdcacad845a740386cfcb1cde0bd5f86e`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
**Owner Decision Record:** `S3_OWNER_DECISION_RECORD.md` (MKE-S3-ADR-001)  
**Execution Agent:** Anty  
**Chief Architect & Auditor:** ChatGPT  
**Approval Authority:** Project Owner  

---

## 1. Overview & Architecture

Milestone S3 implements the P02A `SOLVE` branch for affine linear equations over $\mathbb{R}$ with exact rational coefficients $\mathbb{Q}$, building upon:
1. S0 exact rational core (`mke_product.core.rational.Rational`).
2. S1 immutable AST and parser (`mke_product.parser`).
3. S2 independent semantic evaluation and candidate verification (`mke_product.evaluator`).

The solver is located in `src/mke_product/solver/` and maintains strict decoupling: S3 calls S2 `check_candidate()` to independently verify computed roots, while S2 remains completely unaware and independent of S3.

### Components
- `errors.py`: Authoritative typed solver exceptions:
  - `SolverError`: Base solver exception.
  - `OutOfScopeError`: Base exception for equations outside P02A linear scope.
  - `OutOfScopeVariableExponentZeroError`: Code `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`.
  - `OutOfScopeNonlinearError`: Code `OUT_OF_SCOPE_NONLINEAR`.
  - `OutOfScopeRationalFractionError`: Code `OUT_OF_SCOPE_RATIONAL_FRACTION`.
- `tracker.py`:
  - `OperationTracker(budget)`: Shared solver operation budget counter across preflight traversal, memoized variable inspection, constant evaluation, affine extraction, and reduction arithmetic.
- `scope.py`:
  - `check_equation_scope(equation, budget, tracker, var_memo)`: Pre-simplification safety inspection performed on the unreduced AST before any normalization.
  - Hazard Collection Architecture: Inspects the full AST to collect all hazards before classifying, guaranteeing permutation-invariance across commutativity and AST traversal order.
  - Authoritative classification priority (per Owner Decision MKE-S3-ADR-001):
    1. Resource limit exhaustion (fail closed immediately as `RESOURCE_EXHAUSTED`).
    2. Proven original constant-domain violations (`DOMAIN_ERROR_DIVISION_BY_ZERO`, `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).
    3. Variable-dependent base raised to exponent zero ($x^0$, $(x-1)^0$, $0 \cdot x^0$) returns `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`.
    4. Variable-dependent denominators ($(x-1)/(x-1) = 1$, $1/x = 0$) return `OUT_OF_SCOPE_RATIONAL_FRACTION`.
    5. Variable-dependent quadratic powers ($x^2$, $0 \cdot x^2$, $x^2 - x^2$) and variable products ($x \cdot x$) return `OUT_OF_SCOPE_NONLINEAR`.
    6. Unsupported variables return `OUT_OF_SCOPE_UNSUPPORTED_VARIABLE`.
- `affine.py`:
  - `AffineForm(a, b)`: Immutable exact representation of $a \cdot x + b$ with $a, b \in \mathbb{Q}$.
  - `extract_affine(node, budget, tracker, var_memo)`: Deterministic extraction from verified in-scope AST nodes.
  - Enforces operation step count and integer bit-length limits during coefficient arithmetic.
- `result.py`:
  - `SolutionClassification`: Canonical enum: `UNIQUE_ROOT`, `ALL_REALS` (`DomainSet(R)`), `NO_SOLUTION` (`EmptySet`).
  - `SolverScopeStatus`: `IN_SCOPE`, `OUT_OF_SCOPE`, `DOMAIN_ERROR`, `RESOURCE_EXHAUSTED`, `INTERNAL_VERIFICATION_FAILURE`.
  - `SolverEvidence`: Structured provisional evidence payload recording affine components, normalized $(a, b)$, classification, root, S2 check result, step trace, and diagnostics.
  - `SolverResult`: Immutable return type containing status, classification, root, error details, and evidence.
- `solver.py`:
  - `solve_equation(equation, budget=None) -> SolverResult`: Public entry point coordinating preflight, extraction, reduction arithmetic, and S2 independent verification.

---

## 2. Mathematical Semantics & Solution Classification

An in-scope affine equation is reduced to normalized form $a \cdot x + b = 0$ with $a = a_L - a_R$ and $b = b_L - b_R$ over $\mathbb{Q}$:

### 2.1 Case A: $a \neq 0$ (`UNIQUE_ROOT`)
- Exact rational root computed as $x_0 = -b/a \in \mathbb{Q}$.
- The root and original AST are submitted to S2 `check_candidate(equation, x_0)`.
- The outcome is declared `UNIQUE_ROOT` if and only if S2 returns `VALID`.
- Fail-closed guarantee: If S2 returns `INVALID`, `DOMAIN_ERROR`, or `RESOURCE_EXHAUSTED`, the solver returns `INTERNAL_VERIFICATION_FAILURE`, `DOMAIN_ERROR`, or `RESOURCE_EXHAUSTED` respectively.

### 2.2 Case B: $a = 0 \land b = 0$ (`DomainSet(R)`)
- Algebraic identity $0 \cdot x + 0 \equiv 0$ holds for every real number $x \in \mathbb{R}$.
- Preflight ensures everywhere-definedness on $\mathbb{R}$.
- Justification is purely algebraic; no finite empirical sampling is used.

### 2.3 Case C: $a = 0 \land b \neq 0$ (`EmptySet`)
- Algebraic contradiction $0 \cdot x + b = b \neq 0$ has no solution in $\mathbb{R}$.
- Classified as `EmptySet` (`NO_SOLUTION`).

---

## 3. Owner Ruling MKE-S3-ADR-001 & Mixed-Hazard Precedence

The Project Owner has explicitly approved Decision **MKE-S3-ADR-001** (recorded in full in `S3_OWNER_DECISION_RECORD.md`):

1. **Precedence Rule:** Proven original constant-domain undefinedness ($1/0$, $0^0$) takes precedence over variable-dependent exponent-zero scope abstention ($x^0$).
2. **Rationale:** Mathematically undefined expressions must not be masked as mere solver scope limitations.
3. **Mandatory Examples:**
   - $x^0 + 1/0 = 0 \implies \text{DOMAIN\_ERROR\_DIVISION\_BY\_ZERO}$
   - $1/0 + x^0 = 0 \implies \text{DOMAIN\_ERROR\_DIVISION\_BY\_ZERO}$
   - $x^0 + 0^0 = 0 \implies \text{DOMAIN\_ERROR\_UNDEFINED\_ZERO\_TO\_ZERO}$
   - $0^0 + x^0 = 0 \implies \text{DOMAIN\_ERROR\_UNDEFINED\_ZERO\_TO\_ZERO}$
   - $x \cdot (x^0) = 0 \implies \text{OUT\_OF\_SCOPE\_VARIABLE\_EXPONENT\_ZERO}$
   - $x^0 + x^2 = 0 \implies \text{OUT\_OF\_SCOPE\_VARIABLE\_EXPONENT\_ZERO}$
   - $x^2 + x^0 = 0 \implies \text{OUT\_OF\_SCOPE\_VARIABLE\_EXPONENT\_ZERO}$
   - $x^2 + 1/0 = 0 \implies \text{DOMAIN\_ERROR\_DIVISION\_BY\_ZERO}$
4. **Deterministic Tie-Break Policy for Multiple Domain Errors:** When an equation contains multiple distinct constant domain violations (e.g. $1/0 + 0^0 = 0$ vs $0^0 + 1/0 = 0$), the solver guarantees status `DOMAIN_ERROR`. The reported error code and span correspond to the leftmost violation in AST pre-order traversal order.

---

## 4. S3-R3 Operation-Count Calculations & Stage Coverage

S3 enforces auditable resource accounting where every solver stage charges exact operation steps to a shared `OperationTracker`:

### 4.1 Stage 1: Constant-Evaluation Boundary (`x/0 = 0`)
- **AST Nodes (5 total):** `Equation`, `BinaryOp(/)`, `Variable(x)`, `IntegerLiteral(0)` [denominator], `IntegerLiteral(0)` [rhs].
- **Step Breakdown:**
  1. *Variable-dependency memoization:* Visits all 5 nodes in post/pre-order ($\text{ops } 1 \dots 5$).
  2. *Preflight AST traversal:*
     - Visits `Equation` ($\text{op } 6$).
     - Visits `BinaryOp(/)` ($\text{op } 7$).
     - Detects constant denominator `IntegerLiteral(0)` and invokes `ExpressionEvaluator.evaluate(IntegerLiteral(0))`.
     - Inside `evaluate`: Attempts step 8.
- **Boundary Verification:**
  - With `max_operations = 7`: Exhaustion occurs strictly *inside* constant denominator evaluation on step 8 ($8 > 7$). Spy instrumentation proves `ExpressionEvaluator.evaluate` was entered with `operations_count == 7`. Returns `RESOURCE_EXHAUSTED`.
  - With `max_operations = 11`: `evaluate` completes on step 8 (evaluating to zero, recording domain violation). Traversal visits remaining nodes `Variable(x)` ($\text{op } 9$), left `IntegerLiteral(0)` ($\text{op } 10$), and right `IntegerLiteral(0)` ($\text{op } 11$). Preflight completes and returns `DOMAIN_ERROR_DIVISION_BY_ZERO`.

### 4.2 Stage 2: Affine-Extraction Boundary (`x = 1`)
- **AST Nodes (3 total):** `Equation`, `Variable(x)`, `IntegerLiteral(1)`.
- **Step Breakdown:**
  1. *Variable-dependency memoization:* Visits 3 nodes ($\text{ops } 1 \dots 3$).
  2. *Preflight AST traversal:* Visits 3 nodes ($\text{ops } 4 \dots 6$). Preflight completes cleanly at operation 6.
  3. *Affine extraction (lhs):* `extract_affine(Variable(x))` runs on step 7 ($7 \le 7$).
  4. *Affine extraction (rhs):* `extract_affine(IntegerLiteral(1))` attempts step 8.
- **Boundary Verification:**
  - With `max_operations = 7`: Extraction of lhs succeeds, and extraction of rhs exhausts on step 8 ($8 > 7$). Spy instrumentation proves `extract_affine` was called for lhs (`Variable`, entered at step 6) and rhs (`IntegerLiteral`, entered at step 7). Returns `RESOURCE_EXHAUSTED`.

### 4.3 Stage 3: Root-Isolation Boundary (`x = 1`)
- **Step Breakdown:**
  1. Preflight memoization: $\text{ops } 1 \dots 3$.
  2. Preflight traversal: $\text{ops } 4 \dots 6$.
  3. Affine extraction lhs (`Variable x`): $\text{op } 7$.
  4. Affine extraction rhs (`IntegerLiteral 1`): $\text{op } 8$.
  5. Affine normalization $a = a_L - a_R$: $\text{op } 9$.
  6. Affine normalization $b = b_L - b_R$: $\text{op } 10$.
  7. Root isolation $x_0 = -b / a$: $\text{op } 11$.
- **Boundary Verification:**
  - With `max_operations = 10`: Normalization completes cleanly at step 10. Root isolation attempts step 11 ($11 > 10$) and exhausts inside `solve_equation`. Returns `RESOURCE_EXHAUSTED` with `classification = None`.
  - With `max_operations = 11`: Root isolation succeeds at step 11. S3 invokes independent S2 candidate verification with its own fresh budget. Returns `UNIQUE_ROOT` with root $1$ and verified S2 evidence.

### 4.4 S2 Budget Independence & Fail-Closed Guarantee
- **Modular Decoupling:** S2 candidate verification (`check_candidate()`) runs as an independent verification pass with its own evaluation budget (`effective_budget`), preserving modular separation between the solver and verifier.
- **Fail-Closed:** Resource exhaustion at any point never produces a solved classification (`UNIQUE_ROOT`, `DomainSet(R)`, or `EmptySet`).
- **Runtime Scope:** Software operation and bit-length budgets bound algorithm complexity within the Python runtime; they do not implement OS-level process sandboxing or kernel hardware isolation.

---

## 5. Test Suite & Reproducibility

### 5.1 Test Execution
Command:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Output:
```
Ran 184 tests in 0.030s

OK
```

### 5.2 Test Inventory (184 Total Tests)
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Baseline Solver Tests (`tests/test_solver.py`):** 31 tests.
- **S3-R1 Preflight Remediation Regressions (`tests/test_solver.py`):** 11 tests.
- **S3-R2 Final Solver Regressions (`tests/test_solver.py`):** 25 tests.
- **S3-R3 Stage Boundary Regressions (`tests/test_solver.py`):** 5 tests:
  - `test_constant_evaluation_boundary_exhaustion`: `x/0 = 0` (max_ops=7 exhausts inside constant eval; max_ops=11 returns DOMAIN_ERROR; instrumented with ExpressionEvaluator spy).
  - `test_affine_extraction_boundary_exhaustion`: `x = 1` (max_ops=7 exhausts inside rhs extract_affine; instrumented with extract_affine spy).
  - `test_root_isolation_boundary_exhaustion`: `x = 1` (max_ops=10 exhausts during root isolation; max_ops=11 completes S3 and passes S2 verification).
  - `test_s2_separate_budget_preservation`: verifies S2 independent budget is preserved and not depleted by S3 steps.
  - `test_resource_exhaustion_never_produces_solved_classification_exhaustive`: parameterized verification across all boundary stages.

### 5.3 Holdout Dataset Isolation
The 184 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 6. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
