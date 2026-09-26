# PRODUCT-01 — Roadmap, acceptance gates and evidence inventory draft

Status: DRAFT FOR INDEPENDENT REVIEW, revision 0.2, 2026-09-26. No gate in this roadmap authorizes itself.

## Recommended decision

Approve a local modular Product architecture with immutable original problems, bounded mathematical profiles, explicit proof obligations, and a separate verification policy. Start with a narrow, verified linear and rational arithmetic core in PRODUCT-02A; add broader R1 algebra workflows only after passing independent Product gates.

**Revision 0.2 Status:** Revision 0.1 received **CONDITIONAL ACCEPT** from the Chief Architect and Project Owner. This revision 0.2 resolves blockers B1–B4 and the two architectural requirements. **PRODUCT-02A implementation is NOT YET AUTHORIZED.** Research G4 remains on HOLD. DEV-02A remains the frozen baseline. DEV-02B is permanently stopped.

## Delivery stages and gates

| Gate | Scope / output | Exit evidence and decision |
|---|---|---|
| **G0: PRODUCT-01 design review** | These seven drafts (rev 0.2), source assessment, ADRs, missing evidence, and protected boundaries | Owner approves/amends major choices; independent ChatGPT architecture review resolves blockers. This is design acceptance only. |
| **G1: PRODUCT-02A foundation authorization** | Approved schemas, new Product location, protected-path manifest, dependency plan, finite grammar, and Product case protocol | Written owner authorization naming permitted source/data paths, scope and commands. Independent reviewer agrees mathematical obligations and oracles before implementation. |
| **G2: PRODUCT-02A foundation acceptance** | Text/structured parsing, original-domain snapshot, rational arithmetic, linear/constant solve, typed trace, separate checker, local job API, bounded worker, record export | Newly produced Product evidence for the narrow gate below; independent audit and owner acceptance. No inference that R1 UI/ingestion/advanced algebra is ready. |
| **G3: R1 workbench acceptance** | Remaining PR-01–17: quadratic/factor/rational scope, multi-method traces, editor, manual image/PDF transcription, plots, records and accessible UI | Complete R1 evaluation matrix, resource/security evidence, dependency/license manifest, reviewed explanations and owner release decision. |
| **PRODUCT-R2-GATE** | Each new discipline/provider gets a separate expansion gate | Module-specific schemas, method/checker scope, independent oracles, security/isolation evidence and owner approval. |

## Precise next implementation gate proposal: PRODUCT-02A

PRODUCT-02A is the foundational implementation gate. It isolates a strictly finite mathematical subset to establish the end-to-end architecture before any broader algebra or UI work.

### 1. Mathematical Scope & Grammar
- **Scope:** Exact rational arithmetic, real linear and constant polynomial equations over $\mathbb{Q}$ ($ax + b = 0$), exact rational candidate checking, and explicit domain definedness checking. General rational equations are strictly **excluded**.
- **Finite Grammar:**
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
- **Operator Precedence:** Parentheses (1) > Exponentiation (2) > Unary minus (3) > Multiplication/Division (4) > Addition/Subtraction (5). Unary minus binds looser than exponentiation ($-x^2 \equiv -(x^2)$). Ambiguous juxtapositions (`1/2x`) are strictly parenthesized or left-associative (`(1/2)*x`).

### 2. Undefinedness & Exponent-Zero Rules
- Zero denominator ($n/0$) is strictly undefined. $D_k(x) \neq 0$ predicates are extracted into $D_0$ prior to any transformation.
- $0^0 \implies$ Strictly `UNDEFINED_INDETERMINATE`.
- $x^0 \implies$ Treated as $1$ with explicit domain condition $x \neq 0$. Rejected by P02A linear solver guards.
- Non-zero $c^0 \implies 1$ ($c \in \mathbb{Q} \setminus \{0\}$).

### 3. Structural Capability Guards
- `GUARD_DEGREE`: Input polynomial degree in $x$ must be $\le 1$. Degree $> 1$ returns `OUT_OF_SCOPE_FOR_SOLVER` (`ABSTAIN`).
- `GUARD_DENOMINATOR_VARIABLE`: No variable $x$ permitted in denominators. Variable in denominator returns `OUT_OF_SCOPE_FOR_SOLVER` (`ABSTAIN`).
- `GUARD_ATOM`: No radicals, transcendental functions, or non-rational constants.
- **Anti-Simplification Invariant:** Raw AST is evaluated *before* simplification. The engine strictly refuses to cancel terms (e.g. $\frac{x-1}{x-1} \to 1$) to force an out-of-scope equation into an in-scope linear solver.

### 4. Separate Contracts: `SOLVE` vs `CHECK_CANDIDATE`
- `SOLVE(eq, x)`: Solves $ax+b=0$ over $\mathbb{Q}$.
  - $a \neq 0 \implies \{-b/a\}$ (`VERIFIED`, FTA degree-1 complete set).
  - $a = 0, b = 0 \implies D_0 = \mathbb{R}$ (`VERIFIED`, `DomainSet(RealDomain)`).
  - $a = 0, b \neq 0 \implies \emptyset$ (`VERIFIED`, `EmptySet()`).
- `CHECK_CANDIDATE(eq, x, candidate)`: Substitutes $x = r \in \mathbb{Q}$ into unreduced $L_0, R_0$.
  - If any denominator evaluates to $0 \implies$ `UNDEFINED_OUTSIDE_D0`.
  - Evaluates exact residual $\Delta = L_0(r) - R_0(r) \in \mathbb{Q}$.
  - $\Delta == 0 \implies$ `VERIFIED_VALID`. $\Delta \neq 0 \implies$ `CONTRADICTION_INVALID`.
- **Implemented Types:** Restricted strictly to `ExactRational(numerator: int, denominator: int > 0)`. `RealAlgebraicNumber` is capability-gated.

### 5. Design-Only Expected Outcomes for the Six Scenarios

```text
1. 2*x + 3 = 7:
   - SOLVE: FiniteSet({ExactRational(2, 1)}), VERIFIED.
   - CHECK_CANDIDATE(2): 2 in D0, Residual: 7 - 7 = 0 -> VERIFIED_VALID.
2. 0*x = 0:
   - SOLVE: DomainSet(RealDomain), VERIFIED.
   - CHECK_CANDIDATE(r): Residual: 0 -> VERIFIED_VALID for any r in Q.
3. 0*x = 3:
   - SOLVE: EmptySet(), VERIFIED.
   - CHECK_CANDIDATE(r): Residual: -3 != 0 -> CONTRADICTION_INVALID.
4. (x - 1)/(x - 1) = 1:
   - SOLVE: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Denominator contains x; no silent cancel).
   - CHECK_CANDIDATE(1): Denominator evaluates to 0 -> UNDEFINED_OUTSIDE_D0.
   - CHECK_CANDIDATE(2): Denominator != 0, Residual: 0 -> VERIFIED_VALID.
5. x*(x - 1) = 0:
   - SOLVE: ABSTAIN (OUT_OF_SCOPE_FOR_SOLVER: Degree 2 detected).
   - CHECK_CANDIDATE(0): Residual: 0 -> VERIFIED_VALID.
   - CHECK_CANDIDATE(1): Residual: 0 -> VERIFIED_VALID.
   - CHECK_CANDIDATE(2): Residual: 2 != 0 -> CONTRADICTION_INVALID.
6. Exact Nonzero Residual Smaller than Float Epsilon:
   - Problem: 3*x - 1 + 10^-16 = 0, Candidate: x = 1/3.
   - Float Epsilon Check: abs(res) < 1e-15 would falsely accept (False Positive).
   - Exact Rational Check: Fraction(1, 10^16) != 0 -> CONTRADICTION_INVALID.
```

## Independent Product evaluation program

### 1. Four Levels of Trust & Independence
1. **Level 1: Independently Specified Obligations:** Formal criteria ($L_0(r) - R_0(r) = 0$, $\prod D_k(r) \neq 0$) defined independently of solver heuristics.
2. **Level 2: Independently Implemented Checkers:** Dedicated verification algorithms using pure `fractions.Fraction`, sharing zero code or state with solvers.
3. **Level 3: Independently Constructed Oracles:** Analytically pre-calculated exact rational test tables and offline baseline calculations.
4. **Level 4: Independent Human Mathematical Review:** Qualified human mathematicians reviewing formulations, step derivations, and certificates.

### 2. Dual-Track Pathway for Single-Machine User
- **AI Agents Are Not Human Ground Truth:** Cross-agent agreement between Antigravity and ChatGPT is automated consistency checking, not human mathematical ground truth.
- **Track 1 (Internal Development QA):** Relies on Levels 1, 2, and 3. Authorizes milestone gates G1, G2, and G3.
- **Track 2 (External / Scientific Claims):** Requires Level 4 (human mathematical review). Any claims of "certified universal algebra engine" or scientific publication remain on **HOLD** until accredited human review is completed.

### 3. Product-Only Test Data Protocol (PRODUCT-02A 160-case Suite)
The 160 cases for PRODUCT-02A are newly authored specifically for Product verification. They have distinct identifiers, documented provenance, and are strictly partitioned:

| Category | Case Count | ID Range | Description |
|---|---|---|---|
| **Rational Arithmetic** | 40 | `TEST-P02A-001` .. `040` | Exact addition, subtraction, multiplication, division, precedence, zero numerator, large integer numerators |
| **Linear Solve** | 40 | `TEST-P02A-041` .. `080` | Standard linear equations, integer and fractional roots, negative coefficients, large rational constants |
| **Degeneracy & Inconsistency**| 20 | `TEST-P02A-081` .. `100` | $0x = 0$ (identity on domain), $0x = c$ (empty set), near-degenerate forms |
| **Candidate Check** | 30 | `TEST-P02A-101` .. `130` | Valid roots, invalid candidates, candidate outside $D_0$ ($D(r)=0$), tiny exact residuals smaller than $10^{-15}$ |
| **Boundary & Adversarial** | 30 | `TEST-P02A-131` .. `160` | Quadratic terms ($x^2$), rational equations with variable denominators, $0^0$, malformed syntax, length limit exceeding |

- **Strict Holdout Partition:** 80 development cases / 80 holdout cases.
- **Strict Isolation Invariant:** Strictly prohibited from importing or referencing any restricted G4 research fixtures, probes (P01–P12), seeds, harnesses, trial records, or DEV-02B assets.

## Workspace Isolation, Protected-Path Manifest, and Repository Integrity (Task D)

### 1. Working-Tree State & Need for Physical Isolation
Inspection of `<MKE_REPO_ROOT>` confirms HEAD at commit `753382a023835dbdbe6b074ca6101a3292d3474c` (DEV-02A accepted baseline). However, the working tree contains pre-existing untracked files and deleted scratch files. Therefore, a matching Git HEAD does not prove the working tree is clean.

### 2. Dedicated Product Workspace
All Product source code, tests, build outputs, and execution scratch directories will reside in a completely partitioned workspace directory:
```text
<WORKSPACE_ROOT>/product\
├── src\mke_product\
├── tests\product\
├── data\
└── scratch\
```

### 3. Protected Repository Paths (Immutable Baseline)
The following paths are permanently protected and read-only:
- `src/mke/g4p1/` (G4 Evidence Trust code) — **PROTECTED**
- `tests/g4p1/` (G4 test specifications) — **PROTECTED**
- `evidence_archive/`, `audit_logs_r1/`, `closure_audit_logs/` — **PROTECTED**
- Historical specifications: `G4P0_*`, `G4P1_*`, `DEV02A_*` — **PROTECTED**
- Git commit history up to DEV-02A closure — **PROTECTED**

### 4. Pre-Task and Post-Task Hash Manifest Verification
Before any implementation task is executed, a verification script generates a complete manifest of all files across the repository, recording path, Git status (tracked, untracked, deleted), and SHA-256 hash. After task completion, a post-task verification confirms:
1. Zero files within protected paths were modified, created, or deleted.
2. Only files within `product/` or explicitly authorized directories were touched.

### 5. Prohibition of Automatic Repository Cleanups
Commands such as `git clean -fdx` or `git reset --hard` are strictly prohibited. Untracked research artifacts and historical audit logs must be preserved as-is.

### 6. Provenance Requirements for Legacy Adaptation
If any parsing pattern or data model from DEV-02A is later adapted into Product code, it must be copied explicitly into `product/` with a documented provenance header citing source file, original commit SHA, and license compatibility.

## Major unresolved design questions

| Question ID | Description | Status in Rev 0.2 | Resolution / Path Forward |
|---|---|---|---|
| **DQ-01** | Mathematical scope of PRODUCT-02A | **RESOLVED** | Frozen to linear/constant polynomial equations over $\mathbb{Q}$, exact rational candidate checking, and exact arithmetic. General rational equations deferred. |
| **DQ-02** | Windows isolation model | **RESOLVED** | Multi-layer architecture: Win32 Job Objects (process-tree/memory/CPU) + NTFS scratch ACLs + loopback binding + session token auth. Fail closed on control failure. |
| **DQ-03** | Feasible independent evaluation pathway | **RESOLVED** | 4-level independence taxonomy. Dual-track pathway: Internal QA (Levels 1–3) vs External scientific validation (Level 4, human review). Product-only 160-case suite. |
| **DQ-04** | Repository protection & workspace isolation | **RESOLVED** | Dedicated `product/` workspace directory. Protected-path manifest. Prohibition of `git clean -fdx`. |
| **DQ-05** | Multi-domain extensibility | **RESOLVED** | Versioned polymorphic mathematical objects (`SCALAR_EXPRESSION`, `MATRIX_EXPRESSION`, `CALCULUS_EXPRESSION`). Scalar-v1 invariance demonstrated. |
| **DQ-06** | SymPy parser security | **RESOLVED** | Strict prohibition of `sympy.parse_expr` due to `eval()`. Custom allowlisted AST parser mapping to whitelisted constructors only. |
| **DQ-07** | Multimodal OCR licensing & governance | **RESOLVED** | Pix2Text model weights licensing analyzed. Automated OCR disabled by default; gated under dedicated R2 review. |
| **DQ-08** | Product-02A implementation authorization | **OPEN** | Requires written Project Owner approval following Chief Architect review of Revision 0.2 drafts. |

## Evidence-backed recommendations and rejected alternatives

1. **Adopted:** Bounded local monolith running strictly on `127.0.0.1` with session authentication.
2. **Adopted:** Win32 Job Objects for process-tree termination and memory commit ceilings (512 MB).
3. **Adopted:** Exact rational candidate check evaluated on unreduced original ASTs.
4. **Rejected:** Direct reliance on `sympy.parse_expr` (rejected due to `eval` vulnerability).
5. **Rejected:** Claiming Windows Job Objects provide complete filesystem/network sandboxing.
6. **Rejected:** Claiming AI agent agreement represents independent human mathematical review.
7. **Rejected:** Reusing or importing G4 research probes, seeds, or harnesses into the Product test suite.
8. **Rejected:** Running automatic repository cleanup commands (`git clean -fdx`).

## Local evidence inventory

- `DEV-02A Closure Audit`: Established accepted baseline commit `753382a023835dbdbe6b074ca6101a3292d3474c`.
- `G4-P1 Baseline`: Research evidence trust architecture currently on HOLD.
- `Inspected Working Tree`: Confirmed HEAD match; identified pre-existing untracked files and deleted scratch scripts; established requirement for workspace partitioning.

## Missing or limited evidence

- Runtime performance measurements on large rational expressions under Windows Job Objects.
- Empirical memory footprint of browser-based Web Worker PDF rasterization under low-memory configurations.
- Independent human mathematical review panel for external scientific certification.

## Web evidence inventory and source handling

- [SymPy 1.14.0 Documentation - Parsing Modules](https://docs.sympy.org/latest/modules/parsing.html): Confirms `parse_expr` relies on Python `eval`.
- [Microsoft Learn - Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects): Documents `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` and process-tree termination.
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/): Documents local bearer token authentication and CORS middleware.
- [Pix2Text Documentation](https://pix2text.readthedocs.io/): Documents OCR architecture and model dependencies.

## Completion and handoff

Revision 0.2 of the seven PRODUCT-01 drafts is complete. All blockers B1–B4 and the two architectural requirements have been comprehensively resolved in documentation.

**Next Step:** Submit Revision 0.2 to the Chief Architect (ChatGPT) for independent architectural audit. Implementation of PRODUCT-02A remains strictly unauthorized until explicit, written Project Owner approval.
