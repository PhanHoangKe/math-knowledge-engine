# PRODUCT-01 — Mathematical verification contract draft

Status: DRAFT, revision 0.2, 2026-09-26. Normative proposed Product semantics; not a claim of implemented verification.

## Claims and mathematical objects

Let $P_0$ be the immutable interpreted original problem, $D_0$ its original domain (declared domain intersected with definedness constraints), and $S_0 = \{x \in D_0 : L_0(x) = R_0(x)\}$ for an equation. Every result, step and certificate binds to the problem revision, original AST digest, domain digest and relevant assumption set. A certificate for a normalized equation cannot silently be used for $P_0$.

A solver proposes candidates $C$ and a derivation. A verifier determines what is justified. Candidate soundness means $C \subseteq S_0$. Completeness means $S_0 \subseteq C_{\text{claimed}}$ and every element of $C_{\text{claimed}}$ is sound ($C_{\text{claimed}} = S_0$). These are distinct claims. An empty candidate list is trivially sound but proves neither emptiness nor successful solving. An identity answer is the set $D_0$, not the string "all reals" unless $D_0 = \mathbb{R}$ is explicitly established.

Set representations:
- `FiniteSet(exact_values: List[ExactValue])`: Exhaustive list of discrete solutions.
- `EmptySet()`: Proven absence of solutions on $D_0$.
- `DomainSet(domain_definition)`: Identity equation where all points in $D_0$ satisfy the equation.
- `ConditionalSet(bound_variable, predicates)`: Solutions characterized by ongoing constraints.
- `ApproximateSet(values, search_region, precision)`: Uncertified numerical approximations (never labeled `VERIFIED`).

Typed values:
- `ExactRational(numerator: int, denominator: int > 0)`: Implemented exact rational numbers in canonical reduced form ($\gcd(p, q) = 1$). This is the **only** exact candidate value type supported in the foundational PRODUCT-02A gate.
- `RealAlgebraicNumber(minimal_polynomial, isolating_interval)`: Future exact representation for non-rational algebraic roots (e.g. $\sqrt{2}$). Strictly **capability-gated** and marked `UNSUPPORTED_IN_P02A`.

## Separate correctness contracts

| ID | Claim | Required evidence | Failure / unknown behavior |
|---|---|---|---|
| VC-01 | Original interpretation fixed | User-confirmed revision for images/PDF/ambiguity; text preview and explicit declared domain; source/AST mapping | Unconfirmed or ambiguous input blocks solving. User confirmation validates intent, not recognition quality or mathematical truth. |
| VC-02 | Original domain preserved | Definedness predicates extracted from every original division node before reduction; membership checks over original predicates; exact realness | Unknown exclusion/domain predicate prevents complete-set verification; candidate with $d_i(x)=0$ rejected as `UNDEFINED_OUTSIDE_D0`. |
| VC-03 | Candidate soundness | Every proposed root $r$ satisfies $r \in D_0$ and $L_0(r) - R_0(r) = 0$ under exact arithmetic | Any failing candidate disproves the method or marks the candidate `CONTRADICTION_INVALID`. Zero false exact passes. |
| VC-04 | Exhaustive completeness | Proof that no roots exist in $D_0 \setminus C$; degree bounds for polynomials; factor exhaustive analysis | Incomplete search or unproven branch downgrades status to `PARTIALLY_VERIFIED` (candidate sound only). |
| VC-05 | Transformation validity | Step-by-step equivalence check; reversible operations or explicit branch splitting; domain preservation per step | Non-equivalent step marks derivation `REFUTED`. Candidate answers may be checked separately but derivation cannot be endorsed. |
| VC-06 | Distinct method integrity | Execution traces of distinct methods must demonstrate distinct algebraic strategies (e.g. factoring vs formula) | If two methods share identical internal transformations, the duplicate is suppressed; no invented second method. |

## Step rules and obligations

Every derivation step $k$ transforms expression $E_{k-1}$ to $E_k$ under an explicit rule:
- Rule name (e.g. `ADD_TO_BOTH_SIDES`, `FACTOR_POLYNOMIAL`, `APPLY_QUADRATIC_FORMULA`).
- Mathematical premises (e.g. $A = B \implies A + C = B + C$).
- Application conditions (e.g. non-zero divisor, non-negative radicand).
- Domain delta: tracks whether step narrows or expands domain (e.g. multiplying by an expression containing $x$ introduces potential extraneous roots; requires validation against $D_0$).
- Verification obligation: independent check of the equivalence or implication $E_{k-1} \iff E_k$.

## Completeness profiles for the first release

1. **Linear Profile (PRODUCT-02A & R1):** Linear polynomial equation $ax + b = 0$ over $\mathbb{Q}$.
   - If $a \neq 0$: Exactly one root $x = -b/a$. Completeness is guaranteed by the Fundamental Theorem of Algebra (degree 1).
   - If $a = 0, b = 0$: Identity on $D_0$. $S_0 = D_0$.
   - If $a = 0, b \neq 0$: Contradiction ($b = 0$ impossible). $S_0 = \emptyset$.
2. **Quadratic Profile (R1):** Polynomial equation $ax^2 + bx + c = 0$ ($a \neq 0$). Completeness verified by discriminant $\Delta = b^2 - 4ac$ and at most 2 real roots.
3. **Factored Polynomial Profile (R1):** $\prod_{i=1}^k P_i(x) = 0$. Completeness requires solving each factor $P_i(x) = 0$ completely and taking the union of root sets on $D_0$.
4. **Rational Equation Profile (R1/R2 — Excluded from P02A):** $\frac{N(x)}{D(x)} = 0$. Completeness requires finding all roots of $N(x) = 0$ on $D_0$ and verifying that $D(r) \neq 0$ for all roots.

## PRODUCT-02A Finite Grammar, Operator Precedence, and Typed Semantics

The foundational implementation gate PRODUCT-02A defines a strictly finite, deterministic grammar and typed semantics, isolated from the broader R1 grammar.

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

### 2. Operator Precedence and Associativity

| Precedence Level | Operators | Associativity | Description |
|---|---|---|---|
| 1 (Highest) | `( ... )` | Non-associative | Grouping and sub-expressions |
| 2 | `^`, `**` | Right-associative | Exponentiation ($2^3 = 8$) |
| 3 | Unary `+`, `-` | Right-associative | Unary sign ($ -x^2 \equiv -(x^2) $; $ (-x)^2 \equiv (-x)^2 $) |
| 4 | `*`, `/` | Left-associative | Multiplication and division ($ 1/2*x \equiv (1/2)*x $) |
| 5 (Lowest) | `+`, `-` | Left-associative | Addition and subtraction |

### 3. Explicit Multiplication and Unary Minus Rules
- **Multiplication:** Explicit `*` is preferred. Single-token implicit juxtaposition `2x` is canonicalized by the lexer to `2*x`. Ambiguous juxtapositions such as `x y`, `1/2x`, or juxtaposed parentheses `(x)(x+1)` must be explicitly written with `*` (`(x)*(x+1)`) or parenthesized unambiguously. Juxtaposition `1/2x` is parsed strictly as `(1/2)*x` under left-to-right precedence; users wanting $1/(2x)$ must write `1/(2*x)`.
- **Unary Minus:** Unary minus binds tighter than binary `+` and `-`, but looser than exponentiation:
  - `-x^2` parses as `-(x^2)`.
  - To express $(-x)^2$, explicit parentheses `(-x)^2` are required.
  - Chained unary signs (e.g. `--x`) are rejected by structural syntax validation.

### 4. Zero Denominators and Undefinedness Policy
- Any division by an explicit zero constant (e.g. `5/0`, `0/0`) is invalid syntax/semantics; input parsing fails closed with `SYNTAX_DIVISION_BY_ZERO`.
- For division by an expression $E / D(x)$, a definedness constraint $D(x) \neq 0$ is immediately extracted into $D_0$ before any algebraic rewriting or cancellation.
- If a candidate $x = r$ causes any denominator in the unreduced original equation to evaluate to zero ($D(r) = 0$), the candidate is strictly outside the domain:
  $$\text{Status: } \texttt{UNDEFINED_OUTSIDE_D0}$$
- No division by zero is ever evaluated or tolerated.

### 5. Coherent Exponent-Zero Decision Table

| Base Expression ($B$) | Exponent ($E$) | Semantic Meaning in PRODUCT-02A | Domain / Verification Impact |
|---|---|---|---|
| Non-zero constant $c \in \mathbb{Q} \setminus \{0\}$ | `0` | Evaluates to exact rational `1` | Valid constant atom; $D_0$ unaffected. |
| Explicit zero `0` | `0` | Strictly `UNDEFINED_INDETERMINATE` | Expression rejected by parser/checker; $0^0$ has no defined value in P02A. |
| Variable $x$ | `0` | $x^0 = 1$ for $x \neq 0$ | Introduces domain exclusion condition $x \neq 0$ into $D_0$. In PRODUCT-02A, rejected by structural linear solver guard. |
| Compound expression $f(x)$ | `0` | $(f(x))^0 = 1$ for $f(x) \neq 0$ | Introduces condition $f(x) \neq 0$. Rejected by P02A linear solver guards. |

### 6. Structural Capability Guards for PRODUCT-02A

Before solving, the input AST is inspected by structural capability guards. If any guard fails, the solver immediately returns `OUT_OF_SCOPE_FOR_SOLVER` (`ABSTAIN`) without modifying the AST.

1. **Guard `P02A-G1` (Variable Unicity):** Only the single variable `x` is permitted. Any other symbol or parameter triggers `GUARD_FAIL_UNKNOWN_VARIABLE`.
2. **Guard `P02A-G2` (Polynomial Degree $\le 1$):** After expanding polynomial terms without dividing by variables, the degree in `x` must be $\le 1$. Expressions with $x^2$, $x*x$, or higher powers fail with `GUARD_FAIL_DEGREE_EXCEEDED`.
3. **Guard `P02A-G3` (No Variable Denominators):** No denominator may contain the variable `x`. If `x` appears in any denominator node, the equation is a rational equation, which triggers `GUARD_FAIL_RATIONAL_DENOMINATOR_VARIABLE`.
4. **Guard `P02A-G4` (Supported Atom Guard):** Only integers, rational fractions, variable `x`, and standard arithmetic operators are permitted. Transcendental functions, radicals, and imaginary numbers fail with `GUARD_FAIL_UNSUPPORTED_ATOM`.
5. **CRITICAL ANTI-SIMPLIFICATION INVARIANT:** Structural guards are evaluated on the **original, unreduced AST**. The system MUST NOT simplify or cancel terms before checking guards. For example, in $\frac{x-1}{x-1} = 1$, the denominator contains $x$. The system MUST NOT cancel $\frac{x-1}{x-1} \to 1$ to turn this into an in-scope $1=1$ linear equation. It must reject it as `OUT_OF_SCOPE_FOR_SOLVER`.

### 7. Separate Rules for `SOLVE` vs `CHECK_CANDIDATE`

#### Contract A: `SOLVE(eq, x)`
- **Input:** Equation AST $L_0(x) = R_0(x)$.
- **Prerequisite:** Passes all structural guards `P02A-G1` through `P02A-G4`.
- **Method:**
  1. Transform to canonical form $a \cdot x + b = 0$, where $a, b \in \mathbb{Q}$ are exact rational coefficients computed via `fractions.Fraction`.
  2. Case 1 ($a \neq 0$): Unique root $x = -b/a \in \mathbb{Q}$. Returns `FiniteSet({ExactRational(-b.numerator, b.denominator * a)})`. Completeness: FTA degree 1. Status: `VERIFIED`.
  3. Case 2 ($a = 0, b = 0$): Degenerate identity $0 \cdot x = 0$. Solution set is entire real domain: `DomainSet(RealDomain)`. Status: `VERIFIED`.
  4. Case 3 ($a = 0, b \neq 0$): Degenerate contradiction $0 \cdot x + b = 0$. Solution set is empty: `EmptySet()`. Status: `VERIFIED`.

#### Contract B: `CHECK_CANDIDATE(eq, x, candidate)`
- **Input:** Unreduced original equation AST $L_0(x) = R_0(x)$, and candidate $r = \texttt{ExactRational}(p, q)$ ($q > 0$).
- **Method:**
  1. **Domain Evaluation:** Evaluate every denominator expression $D_k(x)$ in $L_0$ and $R_0$ at $x = r$ using exact rational arithmetic. If any $D_k(r) == 0$, immediately halt and return:
     $$\text{Status: } \texttt{UNDEFINED_OUTSIDE_D0}, \quad \text{Reason: "Candidate violates domain condition } D_k(x) \neq 0\text{"}$$
  2. **Exact Substitution:** Substitute $x = r$ into $L_0$ and $R_0$. Evaluate both sides to exact rational values $v_L = L_0(r) \in \mathbb{Q}$ and $v_R = R_0(r) \in \mathbb{Q}$.
  3. **Exact Residual:** Compute residual $\Delta = v_L - v_R \in \mathbb{Q}$.
     - If $\Delta == 0$: Returns `VERIFIED_VALID` (candidate is a sound root).
     - If $\Delta \neq 0$: Returns `CONTRADICTION_INVALID` (candidate does not satisfy equation).
- **Independence:** `CHECK_CANDIDATE` can evaluate candidates on equations that are `OUT_OF_SCOPE_FOR_SOLVER` (e.g. checking a rational equation or quadratic equation), provided the expressions can be evaluated at $x = r$.

### 8. Design-Only Expected Outcomes for the Six Mandated Scenarios

These scenarios represent normative design specifications for PRODUCT-02A. They are NOT executed test runs.

```text
Scenario 1: 2*x + 3 = 7
- SOLVE:
  - Guards: Passes P02A-G1..G4 (linear polynomial, a=2, b=-4).
  - Reduction: 2*x - 4 = 0 -> x = 4/2 = 2.
  - Result: FiniteSet({ExactRational(2, 1)}).
  - Status: VERIFIED.
- CHECK_CANDIDATE(x = 2):
  - Domain: No denominators present. D0 = RealDomain. 2 in D0.
  - Evaluation: L0(2) = 2*(2) + 3 = 7; R0(2) = 7. Residual: 7 - 7 = 0.
  - Status: VERIFIED_VALID.

Scenario 2: 0*x = 0
- SOLVE:
  - Guards: Passes P02A-G1..G4 (constant polynomial, a=0, b=0).
  - Reduction: 0*x + 0 = 0 (identity).
  - Result: DomainSet(RealDomain).
  - Status: VERIFIED.
- CHECK_CANDIDATE(x = 5/7):
  - Domain: D0 = RealDomain. 5/7 in D0.
  - Evaluation: L0(5/7) = 0*(5/7) = 0; R0(5/7) = 0. Residual: 0 - 0 = 0.
  - Status: VERIFIED_VALID (valid for any rational candidate).

Scenario 3: 0*x = 3
- SOLVE:
  - Guards: Passes P02A-G1..G4 (constant polynomial, a=0, b=-3).
  - Reduction: 0*x - 3 = 0 (contradiction).
  - Result: EmptySet().
  - Status: VERIFIED.
- CHECK_CANDIDATE(x = 0):
  - Domain: D0 = RealDomain. 0 in D0.
  - Evaluation: L0(0) = 0; R0(0) = 3. Residual: 0 - 3 = -3 != 0.
  - Status: CONTRADICTION_INVALID.

Scenario 4: (x - 1)/(x - 1) = 1
- SOLVE:
  - Guards: Guard P02A-G3 detects variable x in denominator (x - 1).
  - Anti-Simplification Invariant: Solver refuses to silently cancel (x-1)/(x-1) -> 1.
  - Result: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Rational equation solver deferred to R1).
  - Status: ABSTAIN.
- CHECK_CANDIDATE(x = 1):
  - Domain Check: Denominator at x=1 evaluates to 1 - 1 = 0.
  - Result: UNDEFINED_OUTSIDE_D0 (candidate excluded from original domain).
  - Status: UNDEFINED_OUTSIDE_D0.
- CHECK_CANDIDATE(x = 2):
  - Domain Check: Denominator at x=2 evaluates to 2 - 1 = 1 != 0. 2 in D0.
  - Evaluation: L0(2) = (2 - 1)/(2 - 1) = 1/1 = 1; R0(2) = 1. Residual: 1 - 1 = 0.
  - Status: VERIFIED_VALID.

Scenario 5: x*(x - 1) = 0
- SOLVE:
  - Guards: Guard P02A-G2 detects degree 2 (quadratic term x^2 - x).
  - Result: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Quadratic solver deferred to R1).
  - Status: ABSTAIN.
- CHECK_CANDIDATE(x = 0):
  - Domain Check: No denominators. 0 in D0.
  - Evaluation: L0(0) = 0*(0 - 1) = 0; R0(0) = 0. Residual: 0.
  - Status: VERIFIED_VALID.
- CHECK_CANDIDATE(x = 1):
  - Domain Check: 1 in D0.
  - Evaluation: L0(1) = 1*(1 - 1) = 0; R0(1) = 0. Residual: 0.
  - Status: VERIFIED_VALID.
- CHECK_CANDIDATE(x = 2):
  - Domain Check: 2 in D0.
  - Evaluation: L0(2) = 2*(2 - 1) = 2; R0(2) = 0. Residual: 2 != 0.
  - Status: CONTRADICTION_INVALID.

Scenario 6: Exact Nonzero Rational Residual Smaller than Float Epsilon
- Problem: 3*x - 1 + 1/10000000000000000 = 0  (i.e. 3*x - 1 + 10^-16 = 0)
- Candidate: x = 1/3 (ExactRational(1, 3))
- Float Arithmetic Behavior (Failure Case):
  - Evaluates 3*(1/3) - 1 + 1e-16 = 1 - 1 + 1e-16.
  - In IEEE 754 float64, 1.0 - 1.0 + 1e-16 = 1e-16.
  - Under a naive floating-point tolerance check (e.g. abs(residual) < 1e-15), this candidate would be falsely accepted as valid (False Positive).
- PRODUCT-02A Exact Rational Behavior:
  - Computes exact rational value: 3*(1/3) - 1 + 1/10^16 = 1 - 1 + 1/10^16 = 1/10^16.
  - Exact residual comparison: Fraction(1, 10000000000000000) != 0.
  - Result: CONTRADICTION_INVALID.
  - Status: CONTRADICTION_INVALID (Sound exact refutation; zero false exact passes).
```

## Evidence model and trust independence

~~~text
Evidence {
  evidence_id, claim_id, claim_kind, statement_digest,
  original_problem_revision, original_ast_digest, domain_digest,
  method_instance_ref?, step_ref?,
  outcome:"PASS"|"FAIL"|"UNKNOWN"|"NOT_APPLICABLE",
  mode:"EXACT_RATIONAL"|"EXACT_ALGEBRAIC"|"CAS_SYMBOLIC"|
       "NUMERIC_OBSERVATION"|"CERTIFIED_INTERVAL"|"FORMAL_KERNEL"|
       "HUMAN_REVIEW",
  checker_id, checker_version, checker_digest,
  algorithm_family, trusted_dependencies:[{name,version,digest?}],
  premises:[evidence_id], artifact_ref?, counterexample?,
  precision?, tolerance?, interval?, elapsed_time,
  resource_termination?, diagnostic
}
~~~

### The Four Distinct Levels of Trust and Independence

To avoid deceptive verification claims, MKE strictly distinguishes four distinct levels of independence:

1. **Level 1: Independently Specified Mathematical Obligations:** Mathematical definitions, domain conditions, and proof criteria specified independently of solver heuristics. Solvers propose; obligation definitions govern pass/fail criteria.
2. **Level 2: Independently Implemented Checker Algorithms:** Verification algorithms implemented in separate code paths from solvers, sharing zero intermediate flags or solver shortcuts, using pure exact rational arithmetic (`fractions.Fraction`) and direct AST substitution.
3. **Level 3: Independently Constructed Test Oracles:** Deterministically pre-calculated exact rational test tables, known mathematical identities, and offline reference calculations that serve as immutable verification baselines.
4. **Level 4: Independent Human Mathematical Review:** Qualified human mathematicians independently reviewing problem statements, step explanations, mathematical rules, and verification certificates.

### Single-Machine User Reality and Dual-Track Evaluation Pathway

The user possesses one personal computer, an internet connection, and currently does not have a designated human mathematician reviewer. In this operating environment:
- **AI Agents Are Not Human Ground Truth:** Agreement between multiple AI agents (e.g. Antigravity and ChatGPT) constitutes automated software cross-checking, NOT independent human mathematical ground truth.
- **Dual-Track Evaluation Pathway:**
  - **Track 1 (Internal Development QA):** Relies on Levels 1, 2, and 3. Uses independent exact rational checkers, property-based testing, deterministic test oracles, and holdout suites. This authorizes internal development progress (e.g. gates G1, G2, G3).
  - **Track 2 (External / Scientific Claims):** Requires Level 4 (independent human mathematical review). Any claims of "scientific publication validation" or "formally certified universal algebra workbench" remain on **HOLD** until accredited independent human review is obtained.

## Multidimensional states and UI projection

Each dimension is PASS/FAIL/UNKNOWN/NOT_APPLICABLE; interpretation uses confirmed/ambiguous/unconfirmed. Formal is NOT_APPLICABLE when not attempted, never PASS by default. A false mathematical claim additionally gets REFUTED; this is necessary because "unverified" alone hides established failure.

Projection is computed per named claim/result card, not by averaging evidence:

| Display | Exact requirements |
|---|---|
| VERIFIED | All mandatory dimensions for the claimed scope PASS; no failed or unresolved dependency. For "complete solution by this method," includes domain, applicability, all presented steps, soundness and completeness. Badge includes mode such as "exact, CAS-backed" or "formal." |
| PARTIALLY_VERIFIED | At least one substantive claim proven, but some required dimensions UNKNOWN; every unknown visible. No known-false claim is included in the accepted answer. Soundness-only badge is allowed without complete-set wording. |
| NUMERICALLY_CHECKED | Candidate passes declared numerical checks but lacks exact evidence; domain conditions relevant to evaluation checked to the stated level. No exact/complete badge; uncertified uncertainty shown. |
| UNVERIFIED | A proposal is representable but no substantive claim has adequate evidence; only in an explicitly marked proposal area. |
| ABSTAIN | No endorsed answer due to unsupported input, ambiguity, lack of applicable methods, budget, cancellation or policy failure; include reason and any separately verified subclaims. |
| REFUTED | Counterexample or exact failed obligation disproves a proposed claim/method. Never rendered as a successful method or hidden behind fluent prose. |

For a candidate-check task, `VERIFIED` means only that the named candidate is in $S_0$; completeness is `NOT_APPLICABLE` and the title must say "candidate verified." For arithmetic evaluation, completeness is `NOT_APPLICABLE`. If an answer set is independently verified but its derivation has a failed edge, the answer and derivation get separate cards/statuses: the failed method is `REFUTED`, and the answer cannot be described as established by that method.

If the original proposed set contained a false root, retain the refutation. A later corrected set can have a new passing claim with a new ID and explicit provenance; this is legitimate correction, not conversion of failure into success. Presentation and LLM outputs have no write access to evidence/status fields.

## Numerical contract

R1 decimal approximations are convenience views of exact values. They record requested working precision and formatting precision; displayed digits alone do not constitute a certified error bound. R2 root checking uses a stated residual metric, for example $|f(x)|/(1+\text{scale}(f,x))$, plus interval/domain, precision, tolerances and convergence status. The scaling function must be fixed per capability.

A small residual for a flat/ill-conditioned function can coexist with large root error. Sign change can support existence only with justified continuity on a bracket; it is not uniqueness. Certified interval claims require outward-rounded arithmetic and a reviewed inclusion theorem, not arbitrary high precision. Sampling does not prove an interval contains no roots. mpmath/SymPy numerical pathways sharing mpmath are not independent numerical oracles.

Numerical reference comparison in evaluation reports uses both absolute and relative tolerances specified per case; tolerances are never reused as exact symbolic acceptance rules. Non-finite values, overflow, singularities and stagnation are explicit outcomes.

## Formal extension contract

Lean 4/mathlib is optional and deferred. A proof adapter may instantiate approved templates for rational/polynomial identities and bounded algebra theorems. Arbitrary uploaded Lean programs are not accepted. The process is isolated and can be terminated. Only allowed imports and tactics run.

The claim digest binds the Lean theorem to the original problem and all domain assumptions. The audit records the emitted statement, exact toolchain/mathlib commits, kernel check, axioms used and translator version. Reject sorry/admit, newly asserted axioms and prohibited oracle-like proof shortcuts. A proof of the wrong encoded problem does not satisfy VC-01/02. Formal success on one step does not make an entire solution formally verified.

## Worked contract scenarios (not executed evaluation cases)

- $(x^2-25)/(x-5)=0$: original domain excludes 5. Cancellation gives $x+5=0$ on that domain; $-5$ is valid. Reintroducing 5 is a domain failure.
- $(x-7)/(x-7)=1$: identity on $\mathbb{R} \setminus \{7\}$, not all reals.
- $(x-6)(x+2)=0$: dividing by $x+2$ without a branch loses $-2$; completeness fails even though 6 is sound.
- $0 \cdot x = 0$ vs $0 \cdot x = 3$: identity vs contradiction, with no attempt to divide by zero.
- A tiny nonzero rational residue remains an exact refutation, independent of how close it is to zero numerically.
- A timed-out factorization returns no complete set; checked candidates may remain in a separate partial result.
- An OCR minus sign read as plus creates a different original problem revision. Correct solving of that revision does not establish faithful recognition of the source image.

These examples specify expected reasoning behavior; they are not runtime findings, benchmark scores or reused research evaluation assets.

## Acceptance obligations

Release blocks on any false exact pass, domain loss, unsupported completeness claim, failed obligation promoted to success, missing dependency in evidence, or formal label without a valid theorem mapping. The independent Product suite and thresholds are in the roadmap. Human review covers mathematical meaning and explanation faithfulness; automated checker success is never the sole authority for admitting a new method family.
