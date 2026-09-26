# MKE PRODUCT-02A-S2 Implementation Report
**Milestone:** Exact Semantic Evaluation & Candidate Verification  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `813c242d77aaf05ee9886fd5196de5cbd1943e21`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
**Execution Agent:** Anty  
**Auditor:** ChatGPT  
**Approval Authority:** Project Owner  

---

## 1. Overview & Architecture

Milestone S2 delivers deterministic, exact semantic evaluation and independent candidate verification for mathematical equations over the rational field $\mathbb{Q}$, built strictly on top of:
1. S0 exact rational core (`mke_product.core.rational.Rational`).
2. S1 immutable AST and parser (`mke_product.parser`).

The implementation resides in `src/mke_product/evaluator/` with clean decoupling from future solving and rewriting stages.

### Components
- `errors.py`: Authoritative typed evaluation and domain errors:
  - `EvaluationError`: Base evaluation exception.
  - `DomainError`: Base domain violation error.
  - `ZeroDenominatorEvaluationError`: Division by zero (`DOMAIN_ERROR_DIVISION_BY_ZERO`).
  - `UndefinedZeroToZeroError`: $0^0$ indeterminate / undefined in $\mathbb{R}$ (`DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).
  - `EvaluationResourceLimitError`: Operation count or bit-length budget exhaustion (`RESOURCE_LIMIT_EXCEEDED`).
  - `InvalidCandidateError`: Rejection of floats, booleans, malformed string representations, or complex numbers (`INVALID_CANDIDATE`).
  - `UnsupportedEvaluationError`: Handling unsupported or unbound AST constructs.
- `budget.py`: `EvaluationBudget`:
  - `max_operations: int = 10000`
  - `max_integer_bits: int = 4096`
  - `max_candidate_bits: int = 4096`
- `result.py`:
  - `CandidateCheckStatus`: Enumeration of verification statuses (`VALID_SOLUTION`, `NOT_A_SOLUTION`, `DOMAIN_ERROR_DIVISION_BY_ZERO`, `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`, `RESOURCE_LIMIT_EXCEEDED`, `EVALUATION_ERROR`, `INVALID_CANDIDATE`).
  - `DomainObligation`: Structured recording of AST domain obligations (denominators $\neq 0$, power base $\neq 0$ when exponent is $0$).
  - `CandidateCheckResult`: Frozen dataclass capturing exact verification outcomes, evaluated sides, error codes, domain obligations, and execution metrics.
- `evaluator.py`:
  - `ExpressionEvaluator`: Tree-walking evaluator operating over immutable AST nodes in exact $\mathbb{Q}$ arithmetic.
  - `coerce_candidate`: Strict rational coercion rejecting floating-point numbers (`float`) and bools.
  - `extract_domain_obligations`: Static domain obligation extractor.
  - `check_candidate`: Public entry point verifying a candidate against an equation AST or string.

---

## 2. Domain Safety & Semantics

### 2.1 Unreduced AST Domain Safety
As mandated by PRODUCT-01 rev0.3.1 and `FREEZE_ADDENDUM.md`, algebraic simplification must never erase or hide domain singularities present in the original formulation.
- For $(x-1)/(x-1) = 1$ at $x=1$, evaluation encounters $(1-1)/(1-1) = 0/0$, returning `DOMAIN_ERROR_DIVISION_BY_ZERO`.
- For $(x-1)/(x-1) = 1$ at $x=2$, both sides evaluate to $1/1$, returning `VALID_SOLUTION`.

### 2.2 $0^0$ Semantics
Under the frozen MKE real-domain specification:
- Any variable base raised to exponent zero has the domain obligation $\text{base} \neq 0$.
- $x^0 = 1$ at $x=0$ yields `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`.
- $(x-1)^0 = 1$ at $x=1$ yields `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`.
- $x^0 = 1$ at $x=2$ yields `VALID_SOLUTION`.

### 2.3 Strict No-Short-Circuiting in Subtrees
Multiplication by zero never hides an undefined subtree. In evaluating `BinaryOp(left, "*", right)`:
- Both `left` and `right` subtrees are unconditionally evaluated before computing the product.
- Thus, $0 \cdot (1/x) = 0$ at $x=0$ triggers `DOMAIN_ERROR_DIVISION_BY_ZERO` rather than returning $0$.

### 2.4 Strict Rational Arithmetic (Zero Floats)
Candidates are strictly constrained to $\mathbb{Q}$. Python `float` inputs are rejected deterministically with `InvalidCandidateError`. Equality comparisons are exact over $\mathbb{Q}$.

---

## 3. Resource Bounds & Safety

The evaluation loop tracks every arithmetic operation and inspects integer bit-lengths:
- Exceeding `max_operations` (default 10,000) raises `EvaluationResourceLimitError`.
- Intermediate integer bit lengths exceeding `max_integer_bits` (default 4,096 bits) raise `EvaluationResourceLimitError`.
- Candidate numerators or denominators exceeding `max_candidate_bits` (default 4,096 bits) are rejected.
- AST nodes remain strictly immutable throughout evaluation.

---

## 4. Test Suite Summary

Total Test Count: **99 passed, 0 failed, 0 errors**.
- **Pre-existing tests:** 65 passed (28 S0 rational tests, 37 S1 parser tests).
- **New S2 tests:** 34 passed (`tests/test_evaluator.py`).

### S2 Test Coverage:
1. Mandatory representative cases:
   - $(x-1)/(x-1) = 1$ at $x=1$ (division by zero domain error).
   - $(x-1)/(x-1) = 1$ at $x=2$ (valid solution).
   - $x^0 = 1$ at $x=0$ ($0^0$ domain error).
   - $x^0 = 1$ at $x=2$ (valid solution).
   - $(x-1)^0 = 1$ at $x=1$ ($0^0$ domain error).
   - $2x + 3 = 7$ at $x=2$ (valid solution) and $x=3$ (not a solution).
   - $0 \cdot (1/x) = 0$ at $x=0$ (multiplication by zero does not mask domain error).
   - $(1/x) \cdot 0 = 0$ at $x=0$ (reverse operand order does not mask domain error).
   - $x^2 - 4 = 0$ at $x=2$, $x=-2$ (valid solutions) and $x=1$ (not a solution).
   - $-x^2 = 1$ at $x=1$ (not a solution: $-1 \neq 1$).
   - $(-x)^2 = 1$ at $x=1$ (valid solution: $1 = 1$).
2. Candidate validation:
   - Strings ("2/3", "-5", "4"), `Rational`, `Fraction`, `int`.
   - Rejection of `float`, `bool`, malformed strings ("2.5.1", "abc", "1/0"), and unsupported candidate types.
   - Rejection of non-Equation ASTs in `check_candidate`.
3. Resource limits and safety:
   - Operation budget exhaustion.
   - Integer bit budget exhaustion.
   - Candidate bit budget exhaustion.
   - AST immutability verification.
   - Static domain obligation extraction.
4. Direct expression evaluator checks:
   - Linear evaluation, unbound variable handling, unsupported AST nodes.
