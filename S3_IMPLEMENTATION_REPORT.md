# MKE PRODUCT-02A-S3 Implementation Report
**Milestone:** Exact Linear Equation Solver (including S3-R1 Preflight Remediation and S3-R2 Final Solver Remediation)  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `75d3b6a57198740ac1154ee6f309099b199cfcf9`  
**S3-R1 Base Commit:** `8c5382159bbd88d82e67a1b1e8e44f75a23a85aa`  
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

## 4. S3 Resource Accounting Policy

S3 enforces a unified, auditable resource-accounting policy across solver execution:

1. **Preflight Traversal:** Each visited AST node during preflight traversal is charged 1 operation step.
2. **Memoized Variable-Dependency Tracking:** Variable-dependency analysis is memoized bottom-up by immutable AST node identity (`id(node)`). Initial node visits charge 1 operation step; subsequent lookups are $O(1)$ and incur zero redundant tree traversals.
3. **Constant-Expression Evaluations:** Constant base evaluations ($0^0$) and denominator evaluations ($1/(2-2)$) during preflight and extraction are charged step-by-step against the shared `OperationTracker`.
4. **Affine Extraction:** Each AST node visited during affine extraction charges 1 operation step.
5. **Reduction Arithmetic:** Normalized coefficient subtractions ($a_L - a_R$, $b_L - b_R$) and root isolation division ($-b / a$) charge 1 operation step each.
6. **Fail-Closed Guarantees:**
   - If the operation budget is exceeded at any point during preflight, extraction, or reduction, the solver immediately returns `RESOURCE_EXHAUSTED`.
   - Resource exhaustion never produces `UNIQUE_ROOT`, `DomainSet(R)`, or `EmptySet`.
   - The engine never assumes an uninspected hazard is safe.
7. **S2 Independent Verification Boundary:** The S2 candidate verifier (`check_candidate()`) is called as an independent verification pass with its own evaluation budget (`effective_budget`), preserving modular separation between the solver and verifier.
8. **Sandbox Scope Clarification:** Software operation and bit-length budgets bound algorithm complexity within the Python runtime; they do not implement OS-level process sandboxing or kernel hardware isolation.

---

## 5. Test Suite & Reproducibility

### 5.1 Test Execution
Command:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Output:
```
Ran 179 tests in 0.038s

OK
```

### 5.2 Test Inventory (179 Total Tests)
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Baseline Solver Tests (`tests/test_solver.py`):** 31 tests.
- **S3-R1 Remediation Regressions (`tests/test_solver.py`):** 11 tests.
- **S3-R2 Final Solver Regressions (`tests/test_solver.py`):** 25 tests:
  - `test_owner_decision_a_exponent_zero_and_div_zero_left`: `x^0 + 1/0 = 0`
  - `test_owner_decision_a_div_zero_and_exponent_zero_right`: `1/0 + x^0 = 0`
  - `test_owner_decision_a_exponent_zero_and_zero_to_zero_left`: `x^0 + 0^0 = 0`
  - `test_owner_decision_a_zero_to_zero_and_exponent_zero_right`: `0^0 + x^0 = 0`
  - `test_owner_decision_a_shifted_var_exponent_zero_and_div_zero`: `(x-1)^0 + 1/(2-2) = 0`
  - `test_owner_decision_a_div_zero_and_shifted_var_exponent_zero`: `1/(2-2) + (x-1)^0 = 0`
  - `test_mixed_hazard_nonlinear_and_div_zero_left`: `x^2 + 1/0 = 0`
  - `test_mixed_hazard_div_zero_and_nonlinear_right`: `1/0 + x^2 = 0`
  - `test_mixed_hazard_rational_fraction_and_div_zero_left`: `x/(x-1) + 1/0 = 0`
  - `test_mixed_hazard_div_zero_and_rational_fraction_right`: `1/0 + x/(x-1) = 0`
  - `test_mixed_hazard_rational_fraction_and_zero_to_zero_left`: `x/(x-1) + 0^0 = 0`
  - `test_mixed_hazard_zero_to_zero_and_rational_fraction_right`: `0^0 + x/(x-1) = 0`
  - `test_multiple_domain_errors_preserves_domain_error_category`: `1/0 + 0^0 = 0` vs `0^0 + 1/0 = 0`
  - `test_exponent_zero_precedence_over_nonlinear_multiplication`: `x*(x^0) = 0`
  - `test_exponent_zero_precedence_over_quadratic_power`: `x^0 + x^2 = 0`
  - `test_exponent_zero_precedence_over_quadratic_power_reversed`: `x^2 + x^0 = 0`
  - `test_exponent_zero_precedence_over_rational_fraction`: `(x^0)/(x-1) = 0`
  - `test_budget_exhaustion_during_preflight_traversal`: preflight traversal exhaustion
  - `test_budget_exhaustion_during_preflight_constant_subexpression`: preflight constant evaluation exhaustion
  - `test_budget_exhaustion_during_affine_extraction`: affine extraction exhaustion
  - `test_resource_exhaustion_never_produces_solution_classification`: fail-closed contract
  - `test_s2_independent_verification_present_and_valid`: S2 candidate check verification
  - `test_no_regression_unique_root`: $3x + 6 = 0 \implies x = -2$
  - `test_no_regression_all_reals`: $x + 1 = x + 1 \implies \text{DomainSet(R)}$
  - `test_no_regression_empty_set`: $x + 1 = x + 2 \implies \text{EmptySet}$

### 5.3 Holdout Dataset Isolation
The 179 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 6. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
