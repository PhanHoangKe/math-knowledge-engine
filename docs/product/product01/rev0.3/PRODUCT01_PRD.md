# PRODUCT-01 — Product Requirements Document

Status: DRAFT FOR OWNER AND INDEPENDENT ARCHITECTURAL REVIEW  
Date: 2026-09-26 | Revision: 0.3 | Implementation Authorization: NONE

## Decision Requested and Report Navigation

Approve or amend a bounded local mathematical algebra workbench, then separately authorize the PRODUCT-02A foundational implementation gate specified in [Roadmap and Gates](PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md). All architectural decisions in this document are design proposals. The Project Owner approves major decisions; ChatGPT acts as Chief Architect and independent analytical reviewer; Anty (execution agent) implements only an approved scope.

**Revision 0.3 Status:** Revision 0.2 received a REMEDIATE decision from the Chief Architect. This revision 0.3 performs a strictly bounded documentation-only correction across all seven documents, resolving issues R1–R7:
- **R1 (Mathematical Semantics):** Reconciles the authoritative P02A finite grammar across all documents, resolves unary-minus binding, enforces exponent limits, mandates explicit exponent-zero semantics ($0^0 \implies \text{UNDEFINED}$), rejects ambiguous implicit multiplication, separates syntactic validity from capability eligibility, enforces strict normalization of rational roots ($-b/a$), and bases linear completeness on elementary field algebra rather than broad FTA claims.
- **R2 (Technology Factual Corrections):** Corrects FastAPI license to MIT, corrects principal Pix2Text code license to MIT, distinguishes library code licenses from deep-learning model weight rights, and replaces unconditional zero-vulnerability claims with a recorded, severity-based dependency scanning policy.
- **R3 (Release Boundaries):** Establishes an authoritative feature-by-release matrix. Manual image/PDF document ingestion is proposed for deferral to R2 (pending explicit Project Owner decision), keeping R1 focused on verified text/visual algebra.
- **R4 (Repository & Workspace Protection):** Proposes a completely separate sibling Product workspace (`../mke-product`), situated entirely outside the repository `<MKE_REPO_ROOT>`, preserving the accepted DEV-02A baseline and G4 research boundary under strict pre/post task manifests.
- **R5 (Security & Process Contract):** Distinguishes Job-wide memory limits from per-process limits, defines process creation ordering (`CREATE_SUSPENDED` -> `AssignProcessToJobObject` -> `ResumeThread`), prohibits breakaway flags, defines explicit outbound egress blocking, uses HTTP/JSON only (deferring WebSocket), defines safe session bootstrap and Host/Origin validation, and marks browser PDF sandbox limits as unresolved design questions.
- **R6 (Evaluation Protocol):** Distinguishes the planned 160-case test specification from an authored, independently reviewed, and sealed dataset; stratifies development and holdout cases across mathematical families; and defines explicit acceptance categories for runtime, security, and cancellation.
- **R7 (Schemas & Provenance):** Removes invented hash values, specifies canonical RFC 8785 AST serialization, treats multi-domain schema compatibility as an enforceable contract with regression tests, and reconciles numerical and operational limits.

**Governance Reminders:** DEV-02A remains frozen. DEV-02B remains stopped. Research G4 remains on HOLD with all prior restrictions. No restricted research fixtures or probes (P01–P12) may enter Product. PRODUCT-02A implementation is NOT YET AUTHORIZED.

## Product Purpose and Target Users

MKE provides an inspectable, local mathematical calculation and verification environment. It helps users enter mathematical equations, inspect their interpretation, choose an applicable solving method, review step-by-step derivations, and verify candidate soundness and complete-set correctness under exact arithmetic.

Primary users:
- Secondary and undergraduate students learning and checking algebra.
- Tutors and educators requiring verified step-by-step derivations.
- Self-directed learners debugging algebraic transformations.
- Researchers and developers needing an inspectable local engine with machine-readable verification certificates.

Non-goals for the initial product:
- Universal CAS replacement: MKE does not seek feature parity with broad symbolic systems (Mathematica, Maple, broad SymPy).
- Black-box homework solver: MKE will not output unverified answers or invent undocumented intermediate steps.
- Automatic word-problem or diagram solver: Natural-language and diagram interpretation are long-term research areas outside the initial workbench scope.
- Cloud-dependent SaaS: MKE is designed as a local, private, single-user desktop application.

## User Workflows

1. **Text/Formula Input:** The user enters an equation or expression via structured text or a visual math editor (MathLive). The system parses it through an allowlisted grammar, extracts domain definedness predicates, checks structural guards, and displays the interpreted AST and canonical domain for confirmation.
2. **Solving with Distinct Methods:** The user requests a complete solution. The system evaluates structural guards against its versioned method catalogue, executes applicable methods independently, checks step obligations, and verifies candidate soundness and completeness.
3. **Checking a Candidate Solution:** The user provides an equation and a candidate value. The system substitutes the candidate into the unreduced original expressions, checks domain validity, computes exact rational residuals, and reports candidate status without running a full solver.
4. **Step-by-Step Derivation Review:** The user inspects the intermediate steps of a solved problem. Each step displays the mathematical transformation, rule name, justification, and independent verification status.
5. **Multimodal Ingestion (Proposed for R2):** The user provides an image or PDF containing a printed formula. The system displays the crop, proposes a transcription, and requires explicit user confirmation before any solving.

## Authoritative Feature-by-Release Matrix (R3)

| Capability / Feature | PRODUCT-02A (Foundation Gate) | PRODUCT-R1 (Workbench Release) | PRODUCT-R2 (Expansion Gate) | PRODUCT-R3+ (Long-Term) |
|---|---|---|---|---|
| **Input Channels** | Strict ASCII text & JSON API | Text & MathLive Visual Editor | Text, MathLive, Image & PDF Ingestion | Handwriting, Diagrams, Voice |
| **Document Ingestion** | Excluded | Proposed Deferral (Pending Owner Decision) | Manual crop, PDF page select, user confirmation | Batch document ingestion |
| **Automated OCR** | Excluded | Excluded | Gated under separate licensing/accuracy review | Multimodal deep models |
| **Exact Number Types** | `ExactRational` ($p/q$, $q > 0$) | `ExactRational` | `ExactRational`, `RealAlgebraicNumber` (gated) | Complex algebraic, Transcendental |
| **Equation Scope** | Real linear & constant polynomials ($ax+b=0$) over $\mathbb{Q}$ | Linear, quadratic ($ax^2+bx+c=0$), factorable polynomials over $\mathbb{Q}$ | General rational equations, real univariate inequalities, small linear systems | Multivariate systems, polynomial ideals, ODEs |
| **Solving Methods** | Single linear isolation method | Multiple distinct methods (factoring vs quadratic formula) | Substitution, sign charts, Gaussian elimination | Groebner bases, Risch algorithm |
| **Candidate Checking** | Exact rational substitution on unreduced AST | Exact rational substitution on unreduced AST | Exact algebraic & certified interval checking | Arbitrary precision / certified enclosures |
| **Transport Protocol** | Loopback HTTP/JSON only (`127.0.0.1`) | Loopback HTTP/JSON | HTTP/JSON & Authenticated WebSocket | IPC / Local socket options |
| **UI Framework** | CLI / Headless API test harness | React + TypeScript web interface | Rich visual workbench + step debugger | Notebook interface |
| **Visualization** | None | 2D illustrative function plots (poles/holes) | Multi-curve, parametric, sign chart views | 3D surface, vector field plots |
| **External Provers/LLM**| Strictly Prohibited | Strictly Prohibited | Sandboxed explanation LLM (off by default) | Lean 4 formal proof templates |

## Initial Release Requirements and Acceptance

| ID | Requirement | Authoritative Acceptance Criteria |
|---|---|---|
| **PR-01** | Single-machine local startup | Backend and UI launch via a single command, bind strictly to loopback (`127.0.0.1`), generate a session authentication secret, and become ready within 5.0 seconds without internet access. |
| **PR-02** | Visual and text input | User can enter expressions via keyboard text or visual math editor. Both produce identical canonical ASTs for identical mathematical input. Ambiguous implicit multiplication is rejected. |
| **PR-03** | Immutable source and interpretation | Every saved run retains raw input string, original AST, domain predicates, and interpretation revision. Editing creates a new revision. Exclusions and source hashes are preserved. |
| **PR-04** | Bounded exact rational arithmetic | All rational arithmetic uses exact typed representations (`ExactRational` with integer numerator and denominator $q > 0$, $\gcd(|p|, q) = 1$). Undefined division ($n/0$) is explicit. Approximate display never replaces the exact result. |
| **PR-05** | Bounded equation solving (P02A: Linear; R1: Quadratic & factorable) | In PRODUCT-02A: strictly real linear and constant polynomial equations over $\mathbb{Q}$ ($ax+b=0$). In R1: quadratics and factorable polynomials. All in-scope cases return correct complete sets ($S_0$). Degeneracy ($0x=0 \implies \mathbb{R}$, $0x=c \implies \emptyset$) handled explicitly. General rational equations are excluded from P02A; out-of-scope equations are rejected by structural guards and never silently simplified. |
| **PR-06** | Distinct methods where supported | On eligible equations (e.g. quadratics in R1), independently execute distinct strategies (e.g. factorization vs quadratic formula) with distinct traces. Single-method cases report exactly one method; no artificial method duplication. |
| **PR-07** | Step-by-step explanations | Every displayed step cites a typed rule, premises, conditions, and check result. Explanation traces must be verified; unverified steps cannot receive a passing badge. |
| **PR-08** | Candidate verification as distinct contract | Checking a candidate ($x = r \in \mathbb{Q}$) is evaluated against unreduced original expressions $L_0(r), R_0(r)$ independently of solving. If $r \notin D_0$, reports `UNDEFINED_OUTSIDE_D0`. Zero false exact passes. |
| **PR-09** | Numerical approximation of exact results | Numerical decimal values (via mpmath) are provided as convenience views with explicit working precision and uncertified rounding caveats. Numerical evidence can never upgrade an unverified symbolic claim. |
| **PR-10** | Document ingestion (Proposed for R2) | Manual crop and mandatory user confirmation. No solving from unconfirmed transcription. Malformed/oversized files fail within resource policy. Sequenced under R2 gate pending owner decision. |
| **PR-11** | Two-dimensional illustrative graph | Visual plots for supported expressions, clearly indicating domain exclusions, poles, and holes. Never connects lines across known undefined points. Plots cannot certify roots or completeness. |
| **PR-12** | Versioned method knowledge browsing | All approved method records are versioned, reference-backed, and retrievable by ID/class. Unknown IDs fail explicitly. Index rebuilds preserve record digests. |
| **PR-13** | Reproducible records and export | Export/import preserves semantic digests, method/checker versions, original domain, steps, and verification statuses. Tampered records are rejected. |
| **PR-14** | Local operation, isolation and resource budgets | Core operations run strictly air-gapped. Windows process isolation utilizes Win32 Job Objects with aggregate commit limit (512 MB) and per-process limits (256 MB), coupled with restricted scratch filesystem paths and explicit outbound egress blocking. Failure of any mandatory isolation control triggers fail-closed shutdown. |
| **PR-15** | Accessible explanation and correction flow | Workflows are fully keyboard-navigable. Mathematical statuses are conveyed in text as well as color. High-contrast and screen-reader accessible. |
| **PR-16** | Local records control and privacy | User can inspect, export, or permanently delete any record and linked local blobs. No telemetry or data transmission without explicit user configuration. |

**Expression Complexity Limits:** Maximum 300 expression characters, 150 tokens, AST depth at most 15, total AST nodes at most 250, input coefficient magnitude at most $10^9$, exponent at most 4. In PRODUCT-02A, degree in $x$ is strictly $\le 1$. Structural validation applies equally across text, editor, and API payloads.

## Confidence Communication

A result card starts with the interpreted problem, original domain, and answer scope. It presents separate badges for domain preservation, transformations, candidate soundness, completeness, and formal proof, with evidence behind each:
- `VERIFIED`: The explicitly named claim and trusted checker passed all obligations under an exact, certified mode.
- `PARTIALLY_VERIFIED`: Candidate soundness is proven, but complete-set proof is unknown or out of scope.
- `NUMERICALLY_CHECKED`: Candidate satisfies numerical tolerances, but lacks exact symbolic proof.
- `UNVERIFIED`: A proposal is generated by a solver/heuristic, but verification has not run or cannot decide.
- `ABSTAIN`: The problem exceeds structural guards or supported capability boundaries.
- `REFUTED`: The candidate or derivation has been disproved by an exact counterexample or failed obligation.

"Verified" never means universal certainty or complete independence. Recognition confidence concerns transcription and is strictly separated from mathematical verification. Agreement between multiple AI agents (e.g. Antigravity and ChatGPT) is automated software cross-checking, NOT independent human mathematical ground truth. No aggregate "98% correct" score is permitted without an explicit, calibrated evaluation metric.

## Success and Exclusions

Success is correct, inspectable behavior on a narrow declared scope and predictable, fail-closed handling elsewhere. Measure task coverage and abstention separately from soundness. Do not optimize answer rate by weakening verification.

**Strict Exclusions and Workspace Boundaries:**
- **Product Workspace Separation:** All Product development occurs in an isolated sibling Product workspace (`../mke-product`), strictly partitioned from `<MKE_REPO_ROOT>` and historical research artifacts.
- **Repository Integrity:** A matching Git HEAD does not guarantee working-tree cleanliness. A pre-task and post-task hash manifest must verify that zero protected files (e.g. `src/mke/g4p1/`, `tests/g4p1/`, historical G0–G4 archives) are altered, created, or deleted. Automatic repository cleanup commands (`git clean -fdx`, `git reset --hard`) are strictly forbidden.
- **No Research Asset Import:** The Product test suite must be newly authored. Importing or reusing G4 research fixtures, probes (P01–P12), seeds, harnesses, trial records, or DEV-02B assets is strictly prohibited.
