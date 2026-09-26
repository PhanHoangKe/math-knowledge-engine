# PRODUCT-01 — Capability matrix and method design draft

Status: DRAFT, revision 0.2, 2026-09-26. Proposed scope, not implementation evidence.

## Reading the matrix

"Observed legacy" means inspected declarations/source or a stated historical audit scope. It is not a newly tested Product capability. P02A, R1, R2, and R3 are proposed release stages. A library feature is only a possible implementation mechanism; Product support requires a registered capability and acceptance evidence. PR IDs refer to [PRD](PRODUCT01_PRD.md); gates refer to [Roadmap](PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md).

| Discipline/task | Observed legacy evidence | P02A foundational gate | R1 commitment | R2 expansion | Long-term R3+ | Verification limit / fallback |
|---|---|---|---|---|---|---|
| Rational arithmetic | Fraction-based numeric AST and exact constructors | Bounded exact rational arithmetic (`ExactRational`); zero denominator detection | Bounded exact evaluation, PR-04 | Units and richer numeric constants | Mixed symbolic/numeric expressions | Original division definedness required; $n/0$ undefined |
| Real linear/constant equations | M1 catalogue and engine selection; historical audit | Exact rational coefficients $ax+b=0$; FTA degree-1 complete set; degeneracy ($0x=0, 0x=c$) | Exact rational coefficients; degeneracy, PR-05 | Parameter case splitting | Systems with symbolic parameters | $a=0$ branches explicit; no division by zero |
| Exact rational candidate check | Candidate substitution logic in legacy verification | Substitute $r \in \mathbb{Q}$ into unreduced $L_0, R_0$; domain check; exact residual | In-scope for all R1 equations, PR-08 | Candidate checking for algebraic numbers | General membership proofs | If $r \notin D_0 \implies$ `UNDEFINED_OUTSIDE_D0`; residual $\neq 0 \implies$ `CONTRADICTION_INVALID` |
| Quadratics | M2 and M3 interfaces/catalogue; historical audit | **UNSUPPORTED in P02A** (guard rejects degree 2) | Formula; factorization when Q-factorable; PR-05/06 | Completing the square as separately reviewed method | Complex/parameterized domain | Discriminant, branch and multiplicity evidence; distinct real roots as set |
| Factorable cubic/quartic | Completeness reconstruction for factors degree <=2 | **UNSUPPORTED in P02A** | Only Q-factorization into factors <=2 with verified product and exhaustive factor roots | Exact real algebraic root isolation | Broader polynomial systems | Irreducible cubic/general quartic not R1; no claim that every degree-4 equation is solved |
| Rational equations | Unreduced denominator extraction; M4 | **UNSUPPORTED in P02A** (guard rejects variable in denominator; no silent cancellation) | Normalized numerator <=2 and each original denominator polynomial <=2; PR-05 | Broader nested rational structure and denominator roots | Piecewise/multivariate rational functions | All original definedness predicates retained; unresolved domain -> no complete badge |
| Biquadratic substitution | M5 interface/catalogue and engine dispatch | **UNSUPPORTED** | Not registered in R1 | $t=x^2, t \ge 0$, complete lifting | General substitutions with verified inverse branches | Cannot inherit legacy acceptance as Product acceptance |
| Inequalities/absolute value | Explicitly outside legacy scope docs | **UNSUPPORTED** | Unsupported | Real univariate sign charts and case splits | Multivariate constraint sets | Boundaries, strictness and intervals need separate checker |
| Linear algebra | Not established in inspected source | **UNSUPPORTED** | Unsupported | Small rational systems, determinant/rank; numerical linear solve separately | Sparse/tensor/symbolic systems | Exact rank certificates or numeric residual/conditioning; distinguish singular/ill-conditioned |
| Calculus | Not established | **UNSUPPORTED** | Unsupported | Selected derivatives, antiderivatives and definite integrals with continuity checks | Differential equations, multivariate calculus, vector analysis | Continuity and singularity checks mandatory; indefinite integral requires domain of validity |

## Capability registration design

A capability is a typed record registered in the engine catalogue. Capabilities are strictly bounded:
```text
CapabilityRegistration {
  capability_id: string,               # e.g. "mke.algebra.solve.linear.v1"
  domain: CapabilityDomain,            # SCALAR_ALGEBRA | LINEAR_ALGEBRA | CALCULUS
  object_type: MathematicalObjectType, # SCALAR_EXPRESSION | MATRIX_EXPRESSION | CALCULUS_EXPRESSION
  task_kind: TaskKind,                 # SOLVE | CHECK_CANDIDATE | SIMPLIFY | EVALUATE
  profile: CapabilityProfile,          # Structural rules, degree bounds, domain requirements
  implemented_exact_types: [string],   # ["ExactRational"] in P02A; ["RealAlgebraicNumber"] in R2
  method_ids: [string],                # Registered solver methods implementing this capability
  verifier_id: string,                 # Independent verification contract binding
  is_active: bool,                     # Enabled/disabled state (default: disabled until gate approval)
}
```

The capability catalogue rejects ad-hoc invocation: if a problem's AST fails structural guards for all active registered capabilities, the system immediately returns `ABSTAIN` with a structured explanation, rather than attempting speculative simplification.

## Method representation

A method implements a specific algebraic strategy to produce a solution and derivation trace:
```text
MethodSpecification {
  method_id: string,                   # e.g. "method.linear.isolate.v1"
  capability_id: string,               # Binds to specific capability registration
  version: string,                     # Semantic version of algorithm
  name: string,                        # Human-readable title
  mathematical_principle: string,      # Formal algebraic theorem or basis
  structural_guards: [GuardCheck],     # Pre-conditions on AST structure (evaluated on raw AST)
  mathematical_guards: [GuardCheck],   # Domain and coefficient conditions
  output_schema_version: string,       # Typed trace schema
}
```

Every method execution produces a `MethodSolveOutput` containing:
- Candidate solution set $C$.
- Sequence of step derivations, each citing rule name, premises, conditions, and domain deltas.
- Method-specific justification certificates.

## Distinct-method policy

MKE enforces strict truth in method presentation:
1. **Algorithmic Distinction:** Two methods registered for the same capability must implement genuinely distinct mathematical strategies. For example, for quadratic equations in R1:
   - Method 1: Factoring over $\mathbb{Q}$ (finding rational roots via rational root theorem / split-the-middle).
   - Method 2: Quadratic Formula (discriminant $\Delta = b^2 - 4ac$, radical evaluation).
2. **No Invented Methods:** If only one method exists for a task (such as linear equation solving in PRODUCT-02A), the UI displays exactly one method. The system will never artificially duplicate steps, re-order trivial terms, or invent cosmetic variations to claim "multiple methods."
3. **Independent Traces:** Each method must execute independently. A failure in one method trace does not contaminate or suppress another valid method.

## Expansion invariants

1. **Pre-simplification Guard Evaluation:** Guards always evaluate on the original unreduced AST. Out-of-scope expressions are never silently simplified into in-scope equations.
2. **Domain Preservation Invariant:** Transformations cannot delete domain constraints. If an equation has a denominator $D(x)$, the condition $D(x) \neq 0$ must remain bound to all downstream steps and certificates.
3. **No Automatic Upgrade:** Acceptance of a foundation gate (PRODUCT-02A) does not authorize subsequent capability gates (R1, R2). Each capability requires independent gate submission, test suite verification, and owner authorization.

## Multidisciplinary Extensibility Design (Task E)

The initial Product focus is on scalar algebra. However, the system architecture and intermediate representation (IR) are explicitly designed to expand into multi-disciplinary mathematics (Linear Algebra, Calculus) without invalidating existing scalar-v1 schemas, records, or verification contracts.

### 1. Versioned Polymorphic Mathematical Objects

Mathematical expressions are modeled with an explicit type discriminator and schema version:
```json
{
  "$schema": "https://mke.local/schemas/math_object_v1.json",
  "object_type": "SCALAR_EXPRESSION | MATRIX_EXPRESSION | CALCULUS_EXPRESSION",
  "schema_version": "v1.0",
  "body": { ... }
}
```

### 2. Linear Algebra Extension Example (R2/R3)

```text
MatrixExpressionAST {
  object_type: "MATRIX_EXPRESSION",
  schema_version: "v2.0",
  dimensions: { rows: int, cols: int },
  entries: List[List[ScalarExpressionAST]],
  matrix_properties?: { is_square: bool, is_symmetric?: bool }
}
```
- **Capability Registration:**
  - `capability_id`: `"mke.linear_algebra.solve_system.v1"`
  - `domain`: `LINEAR_ALGEBRA`
  - `object_type`: `MATRIX_EXPRESSION`
  - `task_kind`: `SOLVE`
- **Domain Conditions:** Dimension compatibility (e.g. $A \cdot x = b$ requires $\text{cols}(A) == \text{rows}(x)$ and $\text{rows}(A) == \text{rows}(b)$); non-singularity condition $\det(A) \neq 0$ for unique invertibility.
- **Verification Obligations:** Matrix equality check: $A \cdot x_{\text{candidate}} - b = 0$ over exact rational vector space; determinant rank certificates.

### 3. Calculus Extension Example (R2/R3)

```text
CalculusExpressionAST {
  object_type: "CALCULUS_EXPRESSION",
  schema_version: "v2.0",
  operator: "DERIVATIVE" | "DEFINITE_INTEGRAL" | "INDEFINITE_INTEGRAL",
  target_expression: ScalarExpressionAST,
  variable: SymbolAST,
  bounds?: { lower: ScalarExpressionAST, upper: ScalarExpressionAST },
  order?: int
}
```
- **Capability Registration:**
  - `capability_id`: `"mke.calculus.derivative.v1"`
  - `domain`: `CALCULUS`
  - `object_type`: `CALCULUS_EXPRESSION`
  - `task_kind`: `EVALUATE`
- **Domain Conditions:** Differentiability on open interval $(a, b)$; continuity of integrand on closed interval $[a, b]$ for Riemann integration; singularity avoidance.
- **Verification Obligations:** Fundamental Theorem of Calculus: $\frac{d}{dx} \left( \int_a^x f(t) dt \right) = f(x)$; symbolic differentiation rule step obligations.

### 4. Non-Invalidation Proof for Scalar-v1

The multi-domain extension maintains complete backwards compatibility with scalar-v1:
1. **Isolated Routing:** The engine dispatcher routes requests strictly by matching `(domain, object_type, task_kind)`. Requests with `object_type: "SCALAR_EXPRESSION"` are processed exclusively by scalar handlers.
2. **Schema Stability:** Scalar-v1 schemas and calculation records remain completely unmodified. A linear equation record produced in PRODUCT-02A retains identical validation hashes and interpretation semantics even after matrix or calculus capabilities are activated in the engine catalogue.
3. **No Cross-Contamination:** Linear algebra and calculus engines do not alter scalar AST definition nodes or exact rational types. They consume scalar expressions as sub-components (e.g. matrix entries or integrands) without mutating their underlying contracts.
