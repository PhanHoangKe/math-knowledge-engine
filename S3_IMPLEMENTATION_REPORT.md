# MKE PRODUCT-02A-S3 Implementation Report
**Milestone:** Exact Linear Equation Solver (including S3-R1 Preflight Remediation)  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `75d3b6a57198740ac1154ee6f309099b199cfcf9`  
**S3-R1 Base Commit:** `eb8880469224ca1aa50b430b804a13e2a4600d20`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
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
- `scope.py`:
  - `check_equation_scope(equation, budget)`: Pre-simplification safety inspection performed on the unreduced AST before any normalization.
  - S3-R1 Hazard Collection Architecture: Inspects the full AST to collect all hazards before classifying, guaranteeing permutation-invariance across commutativity and AST traversal order.
  - Authoritative classification priority:
    1. Resource limit exhaustion (`RESOURCE_EXHAUSTED`).
    2. Proven constant domain violations (`DOMAIN_ERROR_DIVISION_BY_ZERO`, `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).
    3. Variable-dependent base raised to exponent zero ($x^0$, $(x-1)^0$, $0 \cdot x^0$) returns `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`.
    4. Variable-dependent denominators ($(x-1)/(x-1) = 1$, $1/x = 0$) return `OUT_OF_SCOPE_RATIONAL_FRACTION`.
    5. Variable-dependent quadratic powers ($x^2$, $0 \cdot x^2$, $x^2 - x^2$) and variable products ($x \cdot x$) return `OUT_OF_SCOPE_NONLINEAR`.
    6. Unsupported variables return `OUT_OF_SCOPE_UNSUPPORTED_VARIABLE`.
- `affine.py`:
  - `AffineForm(a, b)`: Immutable exact representation of $a \cdot x + b$ with $a, b \in \mathbb{Q}$.
  - `extract_affine(node, budget, tracker)`: Deterministic extraction from verified in-scope AST nodes.
  - Enforces operation step count and integer bit-length limits during coefficient arithmetic.
- `result.py`:
  - `SolutionClassification`: Canonical enum: `UNIQUE_ROOT`, `ALL_REALS` (`DomainSet(R)`), `NO_SOLUTION` (`EmptySet`).
  - `SolverScopeStatus`: `IN_SCOPE`, `OUT_OF_SCOPE`, `DOMAIN_ERROR`, `RESOURCE_EXHAUSTED`, `INTERNAL_VERIFICATION_FAILURE`.
  - `SolverEvidence`: Structured provisional evidence payload recording affine components, normalized $(a, b)$, classification, root, S2 check result, step trace, and diagnostics.
  - `SolverResult`: Immutable return type containing status, classification, root, error details, and evidence.
- `solver.py`:
  - `solve_equation(equation, budget=None) -> SolverResult`: Public entry point.

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

## 3. S3-R1 Scope Preflight Remediation

S3-R1 addresses audit findings regarding preflight hazard detection precedence:

### 3.1 Issue 1: Binding Exponent-Zero Guard
- **Problem:** In S3 baseline, AST pre-order traversal could encounter a non-linear multiplication or rational fraction error before reaching an exponent-zero subtree, incorrectly yielding `OUT_OF_SCOPE_NONLINEAR` instead of `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`.
- **Resolution:** Full AST hazard collection guarantees `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO` takes precedence over all other out-of-scope conditions (e.g. `x*(x^0)=0`, `1/(x^0)=1`, `(x^0)^2=1`, `x^0+x^2=1`, `x^2+x^0=1`).

### 3.2 Issue 2: Original Constant Undefinedness Priority
- **Problem:** Constant domain errors ($1/0$, $0^0$) must never be masked by out-of-scope errors located in earlier traversal positions.
- **Resolution:** Provable constant undefinedness takes priority over out-of-scope classification, ensuring commutativity invariance (e.g., `1/0 + x^2 = 0` and `x^2 + 1/0 = 0` both return `DOMAIN_ERROR_DIVISION_BY_ZERO`; `0^0 + x/(x-1) = 0` and `x/(x-1) + 0^0 = 0` both return `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).

### 3.3 Unresolved Specification Conflict (x^0 vs. Constant Undefinedness)
- **Tension:** `FREEZE_ADDENDUM.md` §3.1 mandates that any equation with a variable base raised to power 0 immediately returns `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO` prior to reduction (Precedence #1). Conversely, `PRODUCT01_PRD.md` §2 and S3 verification contracts mandate that expressions with provable constant domain violations must report `DOMAIN_ERROR` prior to solver execution.
- **Current Behavior in S3-R1:** Constant domain undefinedness is prioritized over `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO` (i.e. `x^0 + 1/0 = 0` returns `DOMAIN_ERROR_DIVISION_BY_ZERO`). This ensures that mathematically invalid expressions are never treated as valid algebraic structures. A formal ruling from the Chief Architect is documented as an open clarification.

---

## 4. Test Suite & Reproducibility

### 4.1 Test Execution
Command:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Output:
```
Ran 154 tests in 0.027s

OK
```

### 4.2 Test Inventory
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Baseline Solver Tests (`tests/test_solver.py`):** 31 tests.
- **S3-R1 Remediation Regressions (`tests/test_solver.py`):** 11 tests:
  - `test_issue1_exponent_zero_binding_multiplication`: `x*(x^0) = 0`
  - `test_issue1_exponent_zero_binding_denominator`: `1/(x^0) = 1`
  - `test_issue1_exponent_zero_binding_nested_power`: `(x^0)^2 = 1`
  - `test_issue1_exponent_zero_binding_addition_left`: `x^0 + x^2 = 1`
  - `test_issue1_exponent_zero_binding_addition_right`: `x^2 + x^0 = 1`
  - `test_issue2_constant_undefinedness_division_by_zero_left`: `1/0 + x^2 = 0`
  - `test_issue2_constant_undefinedness_division_by_zero_right`: `x^2 + 1/0 = 0`
  - `test_issue2_constant_undefinedness_zero_to_zero_left`: `0^0 + x/(x-1) = 0`
  - `test_issue2_constant_undefinedness_zero_to_zero_right`: `x/(x-1) + 0^0 = 0`
  - `test_permutation_invariance_nonlinear_and_rational`: `x^2 + 1/x = 0` vs `1/x + x^2 = 0`
  - `test_simultaneous_exponent_zero_and_constant_undefinedness`: `x^0 + 1/0 = 0`

### 4.3 Holdout Dataset Isolation
The 154 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 5. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
