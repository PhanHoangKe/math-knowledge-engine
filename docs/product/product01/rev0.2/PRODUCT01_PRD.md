# PRODUCT-01 — Product requirements draft

Status: DRAFT FOR OWNER AND INDEPENDENT ARCHITECTURAL REVIEW  
Date: 2026-09-26 | Revision: 0.2 | Implementation authorization: NONE

## Decision requested and report navigation

Approve or amend a bounded local mathematical workbench, then separately authorize the PRODUCT-02A implementation gate specified in [Roadmap and gates](PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md). All architectural decisions here are proposals. The project owner approves major decisions; ChatGPT coordinates and independently audits; the execution agent implements only an approved scope.

**Revision 0.2 Status:** Revision 0.1 received **CONDITIONAL ACCEPT** from the Chief Architect and Project Owner. This revision 0.2 directly resolves the four authorization blockers (B1: Mathematical scope freezing; B2: Practical Windows isolation model; B3: Feasible independent evaluation pathway; B4: Protected-path manifest for accepted/research assets) and the two architectural requirements (multi-domain extensibility; release/dependency boundaries).

This report consists of seven drafts: this PRD, [Architecture](PRODUCT01_SYSTEM_ARCHITECTURE.md), [Capabilities](PRODUCT01_CAPABILITY_MATRIX.md), [Verification](PRODUCT01_VERIFICATION_CONTRACT.md), [Technology](PRODUCT01_TECHNOLOGY_DECISIONS.md), [Security and risks](PRODUCT01_SECURITY_AND_RISK_REGISTER.md), and [Roadmap, gates and evidence inventory](PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md). The last document inventories inspected local evidence; the technology document inventories official web sources.

These drafts are outside the repository and accepted source trees. No implementation, test, benchmark, research execution, commit, PR, tag, release or publication is part of PRODUCT-01. DEV-02A remains frozen. Research G4 remains HOLD; the owner's statement that V1-B2 accepted static preflight only is controlling. No runtime or algorithm validation follows from it. DEV-02B is permanently stopped.

## Product purpose and users

MKE should help users enter a mathematical problem, inspect its interpretation, choose a supported task, compare genuinely different methods when available, and see exactly which conclusions have been checked. Expansion toward broad mathematical computing is a long-term capability program, not a launch promise of parity with any platform.

Primary initial users are secondary-school and early undergraduate learners and tutors checking real algebra problems, teachers wanting inspectable solution derivations, and self-directed students debugging their own work. Secondary users are developers and researchers needing an inspectable local algebra engine with machine-readable evidence. The design prioritizes explicitness, domain preservation and trustworthy status communication over broad heuristic answer coverage.

Non-goals for the initial product:
- Universal CAS replacement: MKE does not attempt to match Mathematica, Maple or broad SymPy feature breadth.
- Black-box homework solver: MKE will not output unverified answers or invent undocumented intermediate steps.
- Automatic word-problem or diagram solver: Natural-language and diagram reasoning are long-term research areas outside the initial workbench scope.
- Cloud-dependent SaaS: The primary product is a local, private, single-user desktop application.

## Workflows

1. **Text/Formula input:** The user enters an equation or expression via structured text or a visual math editor (MathLive). The system parses it through a restricted, allowlisted grammar, extracts domain definedness predicates, checks structural guards, and displays the interpreted AST and canonical domain for confirmation.
2. **Solving with distinct methods:** The user requests a complete solution. The system evaluates structural and mathematical guards against its versioned method catalogue, executes applicable methods independently, checks step obligations, and verifies candidate soundness and completeness.
3. **Checking a candidate solution:** The user provides an equation and a candidate value. The system substitutes the candidate into the unreduced original expressions, checks domain validity, computes exact rational residuals, and reports candidate status without running a full solver.
4. **Step-by-step derivation review:** The user inspects the intermediate steps of a solved problem. Each step displays the mathematical transformation, rule name, justification, and independent verification status.
5. **Multimodal ingestion (Deferred R2):** The user provides an image or PDF containing a printed formula. The system displays the crop, proposes a transcription, and requires explicit user confirmation before any solving.

## Initial release requirements and acceptance

The workbench focuses on a narrow, verified core. The first implementation gate (PRODUCT-02A) isolates a strictly finite subset: linear and constant polynomial equations over Q, exact rational candidate checking, and exact arithmetic. Subsequent R1 gates expand this core to quadratics and factorable polynomials.

| ID | Requirement | Acceptance criteria |
|---|---|---|
| PR-01 | Single-machine local startup | Backend and UI launch via a single command, bind strictly to loopback (`127.0.0.1`), generate a session authentication secret, and become ready within 5 seconds without internet access. |
| PR-02 | Visual and text input | User can enter expressions via keyboard text or visual math editor. Both produce identical canonical ASTs for identical mathematical input. Invalid syntax displays precise error locations. |
| PR-03 | Immutable source and interpretation | Every saved run retains raw input string, original AST, domain predicates, and interpretation revision. Editing creates a new revision. Exclusions and source hashes are preserved. |
| PR-04 | Bounded exact rational arithmetic | All rational arithmetic uses exact typed representations (`ExactRational` with integer numerator and denominator > 0). Undefined division ($n/0$) is explicit. Approximate display never replaces the exact result. |
| PR-05 | Bounded equation solving (P02A: Linear/constant; R1: Quadratic & factorable) | In PRODUCT-02A: strictly real linear and constant polynomial equations over Q ($ax+b=0$). In R1: quadratics and factorable polynomials. All in-scope cases return correct complete sets ($S_0$). Degeneracy ($0x=0 \implies \mathbb{R}$, $0x=c \implies \emptyset$) handled explicitly. General rational-equation solving is excluded from P02A; out-of-scope equations are rejected by structural guards and never silently simplified. |
| PR-06 | Distinct methods where supported | On eligible equations (e.g. quadratics in R1), independently execute distinct strategies (e.g. factorization vs quadratic formula) with distinct traces. Single-method cases report exactly one method; no artificial method duplication. |
| PR-07 | Step-by-step explanations | Every displayed step cites a typed rule, premises, conditions, and check result. Explanation traces must be verified; unverified steps cannot receive a passing badge. |
| PR-08 | Candidate verification as distinct contract | Checking a candidate ($x = r \in \mathbb{Q}$) is evaluated against the unreduced original expressions $L_0(r), R_0(r)$ independently of solving. If $r \notin D_0$, reports `UNDEFINED_OUTSIDE_D0`. Zero false exact passes. |
| PR-09 | Numerical approximation of exact results | Numerical decimal values (via mpmath) are provided as convenience views with explicit working precision and uncertified rounding caveats. Numerical evidence can never upgrade an unverified symbolic claim. |
| PR-10 | Image ingestion (Deferred R2) | PNG/JPEG input with manual crop and mandatory user confirmation. No solving from unconfirmed transcription. Malformed/oversized files fail within resource policy. OCR remains disabled until R2. |
| PR-11 | PDF ingestion (Deferred R2) | Up to 10 pages / 20 MiB, select page and crop; mandatory user confirmation. Encrypted/unsupported documents receive clear errors. Embedded scripts, links, and attachments do not execute. |
| PR-12 | Two-dimensional illustrative graph | Visual plots for supported expressions, clearly indicating domain exclusions, poles, and holes. Never connects lines across known undefined points. Plots cannot certify roots or completeness. |
| PR-13 | Versioned method knowledge browsing | All approved method records are versioned, reference-backed, and retrievable by ID/class. Unknown IDs fail explicitly. Index rebuilds preserve record digests. |
| PR-14 | Reproducible records and export | Export/import preserves semantic digests, method/checker versions, original domain, steps, and verification statuses. Tampered records are rejected. |
| PR-15 | Local operation, isolation and resource budgets | Core operations run strictly air-gapped. Windows process isolation utilizes Win32 Job Objects for process-tree termination and memory/CPU limits, coupled with restricted filesystem paths and loopback-only network binding. Failure of any mandatory isolation control triggers fail-closed shutdown. |
| PR-16 | Accessible explanation and correction flow | Workflows are fully keyboard-navigable. Mathematical statuses are conveyed in text as well as color. High-contrast and screen-reader accessible. |
| PR-17 | Local records control and privacy | User can inspect, export, or delete any record and linked local blobs. No telemetry or data transmission without explicit user configuration. |

R1 limits: maximum 300 expression characters, 150 tokens, depth 15, 250 AST nodes, input coefficient magnitude at most $10^9$, exponent at most 4; derived integer growth additionally bounded by an implementation-approved bit budget. Structural validation applies equally across text, editor, JSON, and future multimodal inputs.

R1 introduces no parameter solving, symbolic irrational input constants, complex input domains, inequalities, trigonometric functions, arbitrary user code execution, remote plugins, handwriting recognition, automatic word-problem solving, or general formal proof. Unsupported input remains visible with a specific reason and editable source.

## Intermediate expansion

R2 adds capabilities individually after their own correctness, security, and resource gates:
- Biquadratic substitution ($t = x^2, t \ge 0$).
- General rational equations with rigorous denominator root exclusion and case splitting.
- Real univariate inequalities with sign charts.
- Small exact linear systems and matrix operations (leveraging the multi-domain extensible IR).
- Bounded calculus operations (symbolic derivatives, definite integrals with explicit domain continuity).
- Bracketed numerical root finding with certified interval arithmetic.
- Automatic printed-formula OCR (subject to model-specific license and privacy review).
- Optional explanation-only LLM assistant (strictly sandboxed, provider-neutral, off by default).

Each expansion must publish task-level scope, verification dimensions, and unsupported cases before shipping. Numerical convergence is not a completeness proof. Integration may yield an unevaluated result. A differential equation answer requires domain/initial-condition checks. No intermediate capability inherits acceptance just because an upstream library supplies a function.

## Long-term capabilities

Potential modules include multivariate and complex algebra, constrained optimization, probability/statistics, discrete mathematics, number theory, geometry, differential equations/PDEs, units, notebooks, advanced visualization, and selected Lean-checked proof templates. Multimodal expansion may cover handwriting and diagrams only after dedicated interpretation evaluation. Multiuser hosting is a separate security/product decision. There is no promised date or comprehensive discipline coverage.

## Confidence communication

A result card starts with the interpreted problem, original domain, and answer scope. It presents separate badges for domain preservation, transformations, candidate soundness, completeness, and formal proof, with evidence behind each:
- `VERIFIED`: The explicitly named claim and trusted checker passed all obligations under an exact, certified mode.
- `PARTIALLY_VERIFIED`: Candidate soundness is proven, but complete-set proof is unknown or out of scope.
- `NUMERICALLY_CHECKED`: Candidate satisfies numerical tolerances, but lacks exact symbolic proof.
- `UNVERIFIED`: A proposal is generated by a solver/heuristic, but verification has not run or cannot decide.
- `ABSTAIN`: The problem exceeds structural guards or supported capability boundaries.
- `REFUTED`: The candidate or derivation has been disproved by an exact counterexample or failed obligation.

"Verified" never means universal certainty or complete independence. Recognition confidence concerns transcription and is strictly separated from mathematical verification. Agreement between multiple AI agents (e.g. Antigravity and ChatGPT) is corroboration, NOT independent mathematical ground truth. No aggregate "98% correct" score is permitted without an explicit, calibrated evaluation metric.

Example: "Candidate $x = 2$ satisfies the original equation. Completeness has not been established." If an obligation fails, the failed method is shown as rejected with its specific reason. An explanation cannot override that failure.

## Success and exclusions

Success is correct, inspectable behavior on a narrow declared scope and predictable, fail-closed handling elsewhere. Measure task coverage and abstention separately from soundness. Do not optimize answer rate by weakening verification.

**Strict Exclusions and Workspace Boundaries:**
- **Product Workspace Separation:** All Product development occurs in an isolated Product workspace (`<WORKSPACE_ROOT>/product` or dedicated directory), strictly partitioned from the accepted DEV-02A baseline and G4 research artifacts.
- **Repository Integrity:** A matching Git HEAD does not guarantee working-tree cleanliness. A pre-task and post-task hash manifest must verify that zero protected files (e.g. `src/mke/g4p1/`, `tests/g4p1/`, historical G0–G4 archives) are altered, created, or deleted. Automatic repository cleanup commands (`git clean -fdx`, `git reset --hard`) are strictly forbidden.
- **No Research Asset Import:** The Product test suite must be newly authored. Importing or reusing G4 research fixtures, probes (P01–P12), seeds, harnesses, trial records, or DEV-02B assets is strictly prohibited.
