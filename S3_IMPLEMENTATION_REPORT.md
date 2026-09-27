# MKE PRODUCT-02A-S3 Implementation Report
**Milestone:** Exact Linear Equation Solver  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `75d3b6a57198740ac1154ee6f309099b199cfcf9`  
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
  - Variable-dependent base raised to exponent zero ($x^0$, $(x-1)^0$, $0 \cdot x^0$) returns `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`.
  - Variable-dependent quadratic powers ($x^2$, $0 \cdot x^2$, $x^2 - x^2$) and variable products ($x \cdot x$) return `OUT_OF_SCOPE_NONLINEAR`.
  - Variable-dependent denominators ($(x-1)/(x-1) = 1$, $1/x = 0$) return `OUT_OF_SCOPE_RATIONAL_FRACTION`.
  - Original constant undefinedness ($1/0$, $0 \cdot (1/0)$, $0^0$) returns `DOMAIN_ERROR` (`DOMAIN_ERROR_DIVISION_BY_ZERO`, `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).
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

## 3. Test Suite & Reproducibility

### 3.1 Test Execution
Command:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Output:
```
Ran 143 tests in 0.014s

OK
```
*(Also verified via pytest: `143 passed in 0.24s`).*

### 3.2 Test Inventory
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Linear Equation Solver (`tests/test_solver.py`):** 31 tests.
  - Mandatory regressions:
    * `2*x + 3 = 7` $\implies$ UNIQUE_ROOT, $x = 2$
    * `(1/2)*x + (3/4) = 0` $\implies$ UNIQUE_ROOT, $x = -3/2$
    * `x/2 + 1 = 0` $\implies$ UNIQUE_ROOT, $x = -2$
    * `-3*x + 9 = 0` $\implies$ UNIQUE_ROOT, $x = 3$
    * `x = x` $\implies$ DomainSet(R)
    * `0*x = 0` $\implies$ DomainSet(R)
    * `1 = 1` $\implies$ DomainSet(R)
    * `0*x = 5` $\implies$ EmptySet
    * `1 = 2` $\implies$ EmptySet
    * `x^2 - 4 = 0` $\implies$ OUT_OF_SCOPE_NONLINEAR
    * `0*x^2 = 0` $\implies$ OUT_OF_SCOPE_NONLINEAR
    * `x^2 - x^2 = 0` $\implies$ OUT_OF_SCOPE_NONLINEAR
    * `(x-1)/(x-1) = 1` $\implies$ OUT_OF_SCOPE_RATIONAL_FRACTION
    * `x^0 = 1` $\implies$ OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO
    * `0*x^0 = 0` $\implies$ OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO
    * `1/0 = 0` $\implies$ DOMAIN_ERROR
    * `0*(1/0) = 0` $\implies$ DOMAIN_ERROR
    * `0^0 = 1` $\implies$ DOMAIN_ERROR
  - Additional algebraic property tests:
    * Variables on both sides (`5*x + 3 = 2*x + 9`).
    * Large exact rational coefficients (`1000000*x + 2000000 = 5000000`).
    * Negative signs and grouping (`-(2*x - 4) = 8`).
    * Product of variable terms (`x*x = 1`, `(x-x)*x = 0`).
    * Shifted variable power 0 (`(x-1)^0 = 1`).
    * Constant denominator zero expression (`x/(2-2) = 1`).
    * AST immutability preservation.
    * Operation budget exhaustion.
    * Integer bit budget exhaustion.
    * S2 fail-closed verification failure.
    * S2 fail-closed resource exhaustion.
    * Type checking on non-Equation AST.

### 3.3 Holdout Dataset Isolation
The 143 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 4. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
