# PRODUCT-01 — Mathematical Verification Contract Draft

Status: DRAFT, revision 0.3, 2026-09-26. Normative proposed Product semantics; not a claim of implemented verification.

## Claims and Mathematical Objects

Let $P_0$ be the immutable interpreted original problem, $D_0$ its original domain (declared domain intersected with definedness constraints), and $S_0 = \{x \in D_0 : L_0(x) = R_0(x)\}$ for an equation. Every result, step, and certificate binds to the problem revision, original AST digest, domain digest, and relevant assumption set. A certificate for a normalized equation cannot silently be used for $P_0$.

A solver proposes candidate solution sets $C$ and an algebraic derivation. A verifier independently determines what is mathematically justified:
- **Candidate Soundness:** $C \subseteq S_0$. Every proposed root satisfies the original unreduced equation on $D_0$.
- **Exhaustive Completeness:** $S_0 \subseteq C_{\text{claimed}}$ and every element of $C_{\text{claimed}}$ is sound ($C_{\text{claimed}} = S_0$).

These are completely distinct claims. An empty candidate list is trivially sound but proves neither emptiness nor successful solving. An identity answer is the domain set $D_0$, not the string "all reals" unless $D_0 = \mathbb{R}$ is explicitly established.

### Typed Mathematical Values
- `ExactRational(numerator: int, denominator: int > 0)`: Canonical irreducible representation of rational numbers where $\gcd(|p|, q) = 1$ and $q > 0$. **This is the only exact value type implemented and authorized in PRODUCT-02A.**
- `RealAlgebraicNumber(minimal_polynomial, isolating_interval)`: Future exact representation for irrational algebraic numbers (e.g. $\sqrt{2}$). Strictly **capability-gated** and marked `UNSUPPORTED_IN_P02A`.

### Set Representations
- `FiniteSet(elements: List[ExactValue])`: Exhaustive discrete solution set.
- `EmptySet()`: Proven absence of solutions on $D_0$.
- `DomainSet(domain_definition)`: Identity equation where all points in $D_0$ satisfy the equation.
- `ConditionalSet(bound_variable, predicates)`: Solutions characterized by ongoing constraints.
- `ApproximateSet(values, search_region, precision)`: Uncertified numerical approximations (never labeled `VERIFIED`).

## Separate Correctness Contracts

| ID | Claim | Required Evidence | Failure / Unknown Behavior |
|---|---|---|---|
| **VC-01** | Original interpretation fixed | User-confirmed revision for text/editor input; canonical AST mapping and explicit declared domain | Unconfirmed or ambiguous input blocks solving. User confirmation validates intent, not mathematical truth. |
| **VC-02** | Original domain preserved | Definedness predicates extracted from every original division node before reduction; membership checks over original predicates | Unknown exclusion/domain predicate prevents complete-set verification; candidate with $D_k(r)=0$ rejected as `UNDEFINED_OUTSIDE_D0`. |
| **VC-03** | Candidate soundness | Every proposed root $r$ satisfies $r \in D_0$ and $L_0(r) - R_0(r) = 0$ under exact rational arithmetic | Any failing candidate disproves the method or marks candidate `CONTRADICTION_INVALID`. Zero false exact passes. |
| **VC-04** | Exhaustive completeness | Proof that no roots exist in $D_0 \setminus C$; elementary field algebra degree bounds for linear equations; factor exhaustive analysis | Incomplete search or unproven branch downgrades status to `PARTIALLY_VERIFIED` (candidate sound only). |
| **VC-05** | Transformation validity | Step-by-step equivalence check; reversible operations or explicit branch splitting; domain preservation per step | Non-equivalent step marks derivation `REFUTED`. Candidate answers may be checked separately but derivation cannot be endorsed. |
| **VC-06** | Distinct method integrity | Execution traces of distinct methods must demonstrate distinct algebraic strategies (e.g. factoring vs formula) | If two methods share identical internal transformations, the duplicate is suppressed; no invented second method. |

## PRODUCT-02A Finite Grammar, Operator Precedence, and Typed Semantics (R1)

The foundational implementation gate PRODUCT-02A defines a strictly finite, deterministic grammar and typed semantics, isolated from broader algebra profiles.

### 1. Formal EBNF Grammar

```ebnf
Equation        ::= Expression "=" Expression
Expression      ::= [ "+" | "-" ] Term { ( "+" | "-" ) Term }
Term            ::= Factor { ( "*" | "/" ) Factor }
Factor          ::= Atom [ ( "^" | "**" ) Power ]
Power           ::= [ "+" | "-" ] Integer | "(" Expression ")"
Atom            ::= Integer | Variable | "(" Expression ")"
Variable        ::= "x"
Integer         ::= [0-9]+
```

### 2. Operator Precedence and Associativity Table

| Precedence Level | Operators | Associativity | Description |
|---|---|---|---|
| 1 (Highest) | `( ... )` | Non-associative | Grouping and sub-expressions |
| 2 | `^`, `**` | Right-associative | Exponentiation ($2^3 = 8$) |
| 3 | Unary `+`, `-` | Right-associative | Unary sign ($-x^2 \equiv -(x^2)$; $(-x)^2 \equiv (-x)^2$) |
| 4 | `*`, `/` | Left-associative | Multiplication and division ($(1/2)*x$) |
| 5 (Lowest) | `+`, `-` | Left-associative | Addition and subtraction |

### 3. Rejection of Ambiguous Implicit Multiplication (R1)
To eliminate silent misinterpretation:
- **Explicit Multiplication Required:** Compound terms, parenthesized factors, and variable products must use explicit `*` (e.g. `(x)*(x+1)`, `2*(x+1)`, `x*y`).
- **Permitted Single-Token Juxtaposition:** Only single integer literal immediately preceding the single variable `x` (e.g. `2x`, `12x`) is recognized as a canonical shorthand for `2*x`.
- **Strict Rejection of Ambiguous Forms:** Any ambiguous juxtaposition such as `1/2x`, `x y`, `x(x+1)`, or `(x)(x+1)` is **strictly rejected with a syntax error** requiring explicit operators or parentheses (`1/(2*x)` or `(1/2)*x`). Juxtaposition is never silently resolved by heuristic guessing.

### 4. Unary Minus Binding & Exponent Rules
- Unary minus binds tighter than binary addition/subtraction, but looser than exponentiation:
  - `-x^2` parses strictly as `-(x^2)` (or `-1 * x^2`).
  - `(-x)^2` requires explicit parentheses.
  - Chained unary signs (e.g. `--x`, `+-x`) are rejected by structural syntax validation.
- In PRODUCT-02A, constant exponents must be non-negative integers $\le 4$. Variable exponents (e.g. $2^x$) are rejected by structural guards.

### 5. Zero Denominators and Nested Definedness Policy
- Division by an explicit zero constant (e.g. `5/0`, `0/0`) is invalid syntax/semantics; parsing fails closed with `SYNTAX_DIVISION_BY_ZERO`.
- For any division node $A / B(x)$, the denominator definedness condition $B(x) \neq 0$ is immediately extracted into $D_0$ before any algebraic rewriting or cancellation.
- If an equation contains nested denominators (e.g. $1 / (x / 2)$ or $1 / (x - 1)$), definedness predicates are extracted recursively for every division node.
- A candidate $x = r$ is valid if and only if $B(r) \neq 0$ for all extracted denominator expressions. If any denominator evaluates to zero, the candidate is classified as `UNDEFINED_OUTSIDE_D0`.

### 6. Coherent Exponent-Zero Decision Table

| Base Expression ($B$) | Exponent ($E$) | Semantic Meaning in PRODUCT-02A | Domain / Verification Impact |
|---|---|---|---|
| Non-zero constant $c \in \mathbb{Q} \setminus \{0\}$ | `0` | Evaluates to exact rational `1` | Valid constant atom; $D_0$ unaffected. |
| Explicit zero `0` | `0` | Strictly `UNDEFINED_INDETERMINATE` | Expression rejected by parser/checker; $0^0$ has no defined value in P02A. |
| Variable $x$ | `0` | $x^0 = 1$ for $x \neq 0$ | Introduces domain exclusion condition $x \neq 0$ into $D_0$. In PRODUCT-02A, rejected by linear solver guards. |
| Compound expression $f(x)$ | `0` | $(f(x))^0 = 1$ for $f(x) \neq 0$ | Introduces condition $f(x) \neq 0$. Rejected by P02A linear solver guards. |

### 7. Four-Tier Separation of Validity and Eligibility (R1)
MKE strictly separates four tiers of expression handling:
1. **Tier 1: Syntactic Validity:** Does the input string conform to the formal EBNF grammar, with balanced parentheses, valid tokens, and no ambiguous implicit multiplication? If not $\implies$ `SYNTAX_ERROR`.
2. **Tier 2: Semantic Definedness:** Are all constant sub-expressions mathematically defined (no $n/0$, no $0^0$), and are variable definedness conditions well-formed in $D_0$? If not $\implies$ `UNDEFINED_EXPRESSION_ERROR`.
3. **Tier 3: SOLVE Capability Eligibility:** Does the unreduced AST satisfy the structural capability guards of active solver methods (e.g. degree $\le 1$, no variable in denominators)? If not $\implies$ solver returns `ABSTAIN` (`OUT_OF_SCOPE_FOR_SOLVER`).
4. **Tier 4: CHECK_CANDIDATE Eligibility:** Can the candidate $r \in \mathbb{Q}$ be evaluated on the unreduced AST without division by zero? If $r \notin D_0 \implies$ `UNDEFINED_OUTSIDE_D0`. If $r \in D_0 \implies$ evaluates exact rational residual.

### 8. Structural Capability Guards & Anti-Simplification Invariant
Before solving, the input AST is inspected by structural capability guards:
- `P02A-G1` (Variable Unicity): Only the single variable `x` is permitted.
- `P02A-G2` (Polynomial Degree $\le 1$): Maximum degree in `x` must be $\le 1$. Degree $> 1$ ($x^2$, $x*x$) fails with `GUARD_FAIL_DEGREE_EXCEEDED`.
- `P02A-G3` (No Variable Denominators): No denominator may contain variable `x`. If found, fails with `GUARD_FAIL_RATIONAL_DENOMINATOR_VARIABLE`.
- `P02A-G4` (Supported Atom Guard): Only integers, rational fractions, variable `x`, and standard arithmetic operators are permitted.
- **CRITICAL ANTI-SIMPLIFICATION INVARIANT:** Structural guards are evaluated on the **original, unreduced AST**. The system MUST NOT simplify or cancel terms before checking guards. In $\frac{x-1}{x-1} = 1$, the denominator contains $x$. The system MUST NOT cancel $\frac{x-1}{x-1} \to 1$ to turn this into an in-scope $1=1$ linear equation. It must reject it as `OUT_OF_SCOPE_FOR_SOLVER`.

### 9. Exact Linear Solving and Elementary Field Completeness (R1)

#### Exact Root Computation: $-b/a$
For linear equations passing guards, the equation is reduced to canonical form $a \cdot x + b = 0$, where $a, b \in \mathbb{Q}$ ($a = p_a/q_a, b = p_b/q_b$ with $q_a, q_b > 0$).
When $a \neq 0$, the unique root is computed via field division:
$$r = -\frac{b}{a} = -\frac{p_b \cdot q_a}{q_b \cdot p_a}$$
The resulting rational is normalized into canonical reduced form: $r = \texttt{ExactRational}(p, q)$ where $q > 0$ and $\gcd(|p|, q) = 1$. Rational values are never constructed from improperly mixed or unreduced Fraction fields.

#### Elementary Field Algebra Completeness Proof
Completeness of linear equations over $\mathbb{Q}$ is established by **elementary field axioms**:
1. In the field $\mathbb{Q}$, every non-zero element $a \in \mathbb{Q} \setminus \{0\}$ possesses a unique multiplicative inverse $a^{-1} \in \mathbb{Q}$.
2. Applying field operations:
   $$a \cdot x + b = 0 \iff a \cdot x = -b \iff a^{-1} \cdot (a \cdot x) = a^{-1} \cdot (-b) \iff (a^{-1} a) \cdot x = -a^{-1} b \iff 1 \cdot x = -a^{-1} b \iff x = -a^{-1} b$$
3. Each algebraic step is a strict biconditional equivalence ($\iff$) over $\mathbb{Q}$. Therefore, $x = -b/a$ is guaranteed to be the unique solution on $D_0 = \mathbb{R}$.
4. This elementary field-algebra proof provides an exact, self-contained completeness certificate, eliminating the need to cite the broader Fundamental Theorem of Algebra (FTA).

### 10. Design-Only Expected Outcomes for the Six Mandated Scenarios

```text
Scenario 1: 2*x + 3 = 7
- SOLVE:
  - Canonical Form: 2*x - 4 = 0 (a = 2, b = -4).
  - Exact Root: r = -(-4)/2 = 4/2 = 2/1 -> ExactRational(2, 1).
  - Completeness: Elementary field algebra (a != 0 -> unique inverse a^-1).
  - Result: FiniteSet({ExactRational(2, 1)}). Status: VERIFIED.
- CHECK_CANDIDATE(x = 2):
  - Domain Check: D0 = RealDomain. 2 in D0.
  - Evaluation: L0(2) = 2*(2) + 3 = 7; R0(2) = 7. Residual: 7 - 7 = 0.
  - Status: VERIFIED_VALID.

Scenario 2: 0*x = 0
- SOLVE:
  - Canonical Form: 0*x + 0 = 0 (a = 0, b = 0).
  - Completeness: For all x in D0, 0*x = 0 is an identity.
  - Result: DomainSet(RealDomain). Status: VERIFIED.
- CHECK_CANDIDATE(x = 5/7):
  - Domain Check: 5/7 in D0.
  - Evaluation: L0(5/7) = 0*(5/7) = 0; R0(5/7) = 0. Residual: 0 - 0 = 0.
  - Status: VERIFIED_VALID.

Scenario 3: 0*x = 3
- SOLVE:
  - Canonical Form: 0*x - 3 = 0 (a = 0, b = -3).
  - Completeness: 0*x = 0 != 3 for all x in D0 (contradiction).
  - Result: EmptySet(). Status: VERIFIED.
- CHECK_CANDIDATE(x = 0):
  - Domain Check: 0 in D0.
  - Evaluation: L0(0) = 0; R0(0) = 3. Residual: 0 - 3 = -3 != 0.
  - Status: CONTRADICTION_INVALID.

Scenario 4: (x - 1)/(x - 1) = 1
- SOLVE:
  - Structural Guards: Guard P02A-G3 detects variable x in denominator (x - 1).
  - Anti-Simplification Invariant: System refuses to cancel (x-1)/(x-1) -> 1.
  - Result: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Rational equation solver deferred to R1).
- CHECK_CANDIDATE(x = 1):
  - Domain Check: Denominator at x=1 evaluates to 1 - 1 = 0 -> 1 not in D0.
  - Result: UNDEFINED_OUTSIDE_D0. Status: UNDEFINED_OUTSIDE_D0.
- CHECK_CANDIDATE(x = 2):
  - Domain Check: Denominator at x=2 evaluates to 2 - 1 = 1 != 0 -> 2 in D0.
  - Evaluation: L0(2) = (2 - 1)/(2 - 1) = 1/1 = 1; R0(2) = 1. Residual: 1 - 1 = 0.
  - Status: VERIFIED_VALID.

Scenario 5: x*(x - 1) = 0
- SOLVE:
  - Structural Guards: Guard P02A-G2 detects degree 2 (quadratic term x^2 - x).
  - Result: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Quadratic solver deferred to R1).
- CHECK_CANDIDATE(x = 0): Residual 0 -> VERIFIED_VALID.
- CHECK_CANDIDATE(x = 1): Residual 0 -> VERIFIED_VALID.
- CHECK_CANDIDATE(x = 2): Residual 2 != 0 -> CONTRADICTION_INVALID.

Scenario 6: Exact Nonzero Rational Residual Smaller than Float Epsilon
- Problem: 3*x - 1 + 1/10000000000000000 = 0  (3*x - 1 + 10^-16 = 0)
- Candidate: x = 1/3 (ExactRational(1, 3))
- Float Tolerance Evaluation (Failure Mode):
  - In float64, 3*(1/3) - 1 + 1e-16 evaluates within standard tolerance (abs(res) < 1e-15).
  - Naive floating-point checkers falsely return PASS (False Positive).
- Exact Rational Evaluation (PRODUCT-02A Mode):
  - Computes exact rational value: 3*(1/3) - 1 + 1/10^16 = 1/10^16.
  - Exact comparison: Fraction(1, 10000000000000000) != 0.
  - Result: CONTRADICTION_INVALID (Zero false exact passes).
```

## Evidence Model and Trust Independence (R6)

MKE strictly distinguishes four distinct levels of trust and independence:
1. **Level 1: Independently Specified Mathematical Obligations:** Mathematical definitions, domain conditions, and proof criteria specified independently of solver heuristics. Solvers propose; obligation definitions govern pass/fail criteria.
2. **Level 2: Independently Implemented Checker Algorithms:** Verification algorithms implemented in separate code paths from solvers, sharing zero intermediate flags or solver shortcuts, using pure exact rational arithmetic (`fractions.Fraction`) and direct AST substitution.
3. **Level 3: Independently Constructed Test Oracles:** Deterministically pre-calculated exact rational test tables, known mathematical identities, and offline reference calculations that serve as immutable verification baselines.
4. **Level 4: Independent Human Mathematical Review:** Qualified human mathematicians independently reviewing problem statements, step explanations, mathematical rules, and verification certificates.

### Dual-Track Evaluation Pathway
- **AI Agents Are Not Human Ground Truth:** Agreement between multiple AI agents (e.g. Anty and ChatGPT) constitutes automated software cross-checking, NOT independent human mathematical ground truth.
- **Track 1 (Internal Development QA):** Relies on Levels 1, 2, and 3. Uses independent exact rational checkers, property-based testing, deterministic test oracles, and holdout suites. This authorizes internal development progress (e.g. gates G1, G2, G3).
- **Track 2 (External / Scientific Claims):** Requires Level 4 (independent human mathematical review). Any claims of "scientific publication validation" or "formally certified universal algebra workbench" remain on **HOLD** until accredited independent human review is obtained.

## Multidimensional States and UI Projection

Each dimension is evaluated independently as `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`:

| Display Badge | Exact Mathematical Requirements |
|---|---|
| **VERIFIED** | All mandatory dimensions for the claimed scope PASS; no failed or unresolved dependency. Includes domain, step equivalence, candidate soundness, and elementary field completeness. |
| **PARTIALLY_VERIFIED** | Candidate soundness is proven, but complete-set proof is unknown or out of scope. |
| **NUMERICALLY_CHECKED** | Candidate satisfies numerical tolerances, but lacks exact symbolic proof. Displayed with uncertified uncertainty. |
| **UNVERIFIED** | A proposal is generated by a solver, but verification has not run or cannot decide. |
| **ABSTAIN** | The problem exceeds structural guards or supported capability boundaries. Displays specific reason. |
| **REFUTED** | The candidate or derivation has been disproved by an exact counterexample or failed obligation. |

## Acceptance Obligations

Release blocks on any false exact pass, domain loss, unsupported completeness claim, failed obligation promoted to success, missing dependency in evidence, or unhandled division by zero.
