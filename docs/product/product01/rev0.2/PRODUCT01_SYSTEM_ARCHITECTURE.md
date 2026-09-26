# PRODUCT-01 — System architecture draft

Status: DRAFT, revision 0.2, 2026-09-26. All decisions require owner approval. No implementation authorized.

## Existing-system assessment

Repository root inspected read-only: `<MKE_REPO_ROOT>`. HEAD returned `753382a023835dbdbe6b074ca6101a3292d3474c`, the target commit named by the DEV-02A closure audit. 

**Critical Working-Tree Finding:** The working tree contains pre-existing deleted scratch files, untracked audit logs, and historical research packages (`src/mke/g4p1/`, `tests/g4p1/`). Therefore, a matching Git HEAD commit is **not** sufficient evidence that the local working tree is clean or immutable. Product development cannot assume a pristine checkout and must strictly protect accepted baselines through an isolated Product workspace and pre/post task integrity manifests.

| Evidence | Observed interface or structure | Product implication and limits |
|---|---|---|
| Parser and limits [L04] | `Parser.from_text(text, limits)`, `parse_equation()`, `parse_expression()`; finite operator AST; 300 characters, 150 tokens, depth 15, nodes 250, exponent/degree 4 | Useful bounded grammar pattern. Must remain independent of SymPy's `parse_expr` to prevent arbitrary code execution (`eval`). |
| Converter/domain/normalizer [L05] | `ast_to_sympy(node)` constructs whitelisted SymPy nodes; `extract_original_domain(unreduced_ast)`; `normalize_equation(eq_ast, raw_text, limits)` returns `NormalizedEquation` | Preserve denominator conditions before cancellation. Converter must use explicit safe constructors (`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`), strictly forbidding `parse_expr`. |
| Models [L06] | `VerificationResult`, `ProofObligation`, `ExactProofCertificate`, `CompletenessCertificate`, `VerifiedRoot`; separate method/solution flags | Strong starting vocabulary. Models must be immutable (`frozen=True`) to prevent caller tampering. String root serialization replaced by typed `ExactRational`. |
| Methods [L07] | `BaseMethod.check_structural_guards`, `check_mathematical_guards`, `evaluate_admissibility`, `solve_instance`, `check_proof_obligations`; `MethodSolveOutput` | Interface pattern reusable by explicit adapter. Structural guards evaluate on raw AST before any algebraic simplification. |
| Engine/completeness [L08] | `VerificationEngine.verify(equation_str, method_id=None)`; heuristic chooses M1–M5; `audit_independent_completeness` | Existing dispatcher selects one method. Independent checker must be decoupled from solver heuristics, relying on pure exact arithmetic. |
| Knowledge schemas [L09] | SQLite method catalogue; metadata, principles, references | Reusable catalogue architecture. Method records are static data, never executable plugins. |

## Proposed architectural decisions

1. **Modular Monolith:** A single, clean Python codebase with strict internal module boundaries, running locally on a personal computer.
2. **Immutable Original Problem Model:** The interpreted problem ($P_0$), original domain ($D_0$), and AST are permanently fixed upon confirmation and cannot be modified by solvers or normalizers.
3. **Decoupled Verification Subsystem:** Solvers propose candidate solution sets and derivations; verification obligations are independently checked by dedicated checkers using exact rational arithmetic (`fractions.Fraction`).
4. **Pre-simplification Structural Guards:** Input ASTs are evaluated by structural capability guards *before* simplification. Equations exceeding the active profile (e.g. rational equations in PRODUCT-02A) are rejected with `ABSTAIN`, preventing silent transformation into in-scope equations.
5. **Multi-layer Windows Security Architecture:** Win32 Job Objects govern process lifetime, tree termination, and memory/CPU limits. Filesystem isolation is enforced via dedicated scratch directories and restricted OS tokens/ACLs. Network access is disabled via loopback-only binding and firewall rules.
6. **Workspace Partitioning:** Product development resides in an isolated directory (`product/`), physically separated from the accepted DEV-02A baseline and G4 research artifacts.

## Deployment and trust boundaries

The system operates as a single-user desktop application on Windows:

```
+─────────────────────────────────────────────────────────────────────────────────────────+
|                                    USER ENVIRONMENT                                     |
|  Web Browser (Chromium / Gecko)                                                         |
|  - UI: React / TypeScript                                                               |
|  - Math Editor: MathLive                                                                |
|  - Bounded Document Preview: Sandboxed Iframe (PDF.js / Canvas, max 10MB/10 pages)      |
+────────────────────────────────────────────┬────────────────────────────────────────────+
                                             | HTTP / WebSocket
                                             | Loopback Only: 127.0.0.1:<port>
                                             | Header: X-MKE-Session-Token (Bearer Auth)
+────────────────────────────────────────────▼────────────────────────────────────────────+
|                                  LOCAL BACKEND HOST                                     |
|  FastAPI / Uvicorn Server (Python 3.12)                                                 |
|  - Strict CORS: origin == 127.0.0.1:<port>                                              |
|  - Ephemeral Session Secret generated at startup                                        |
|  - Dispatcher & Catalogue Router                                                        |
+────────────────────────────────────────────┬────────────────────────────────────────────+
                                             | Subprocess Pipe (stdin/stdout)
                                             | Isolated Win32 Job Object
+────────────────────────────────────────────▼────────────────────────────────────────────+
|                             ISOLATED WORKER PROCESS (Air-Gapped)                        |
|  Worker Runtime (Python 3.12)                                                           |
|  - Win32 Job Object Limits: Max 512 MB Commit, 1 CPU Core, Kill-On-Job-Close            |
|  - Filesystem: CWD = Isolated Scratch Temp Dir; Read-Only Project Access (Restricted)  |
|  - Network: 0 bytes outbound (Loopback-only / WFP block rule)                           |
|  - Engine: Custom Safe Parser -> Whitelisted SymPy Constructors -> Exact Verifier       |
|  - Fail-Closed: If Job Object or ACL assignment fails, engine aborts startup             |
+─────────────────────────────────────────────────────────────────────────────────────────+
```

### Clarification on Windows Job Objects
Windows Job Objects provide operating-system-level controls for process grouping, memory allocation limits, CPU rate limits, and guaranteed process-tree termination (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`). However, **Job Objects do not provide filesystem or network sandboxing.** Filesystem isolation is achieved by restricting working directories, applying restricted process tokens (`CreateRestrictedToken`), and enforcing strict path validation in software. Network isolation is achieved by binding to `127.0.0.1` and configuring Windows Filtering Platform (WFP) rules for worker executables.

## Fifteen subsystem contracts

1. **Subsystem 1: Ingestion & Input Manager:** Accepts raw text, LaTeX from MathLive, or local files. Validates size ceilings (300 chars for text; 10 MiB for images/PDFs).
2. **Subsystem 2: Document Preview Sandbox:** Renders PDF pages and image crops inside a browser-isolated iframe with restricted permissions (`sandbox="allow-scripts"`). No direct filesystem access from renderer.
3. **Subsystem 3: Parser & AST Normalizer:** Parses input using a restricted, allowlisted grammar. Strictly forbids passing unvalidated strings to `sympy.parse_expr` due to underlying `eval()`. Produces canonical `ExpressionAST`.
4. **Subsystem 4: Converter & CAS Interface:** Maps allowlisted AST nodes to SymPy expressions using explicit, safe constructors (`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`). Enforces strict timeout on CAS operations.
5. **Subsystem 5: Domain & Definedness Extractor:** Traverses unreduced AST, identifies division and power nodes, and extracts definedness predicates ($D_k(x) \neq 0$) into the immutable original domain $D_0$.
6. **Subsystem 6: Candidate Verifier:** Independently evaluates proposed candidate solutions ($x = r \in \mathbb{Q}$) by exact substitution into unreduced $L_0(r), R_0(r)$ using `fractions.Fraction`. Evaluates domain conditions and exact residuals without relying on solver flags.
7. **Subsystem 7: Transformation & Step Auditor:** Verifies algebraic validity of intermediate step derivations. Checks rule applicability, premise truth, and domain preservation per step.
8. **Subsystem 8: Completeness Auditor:** Verifies whether a solution set is proven complete. Under PRODUCT-02A linear profile, applies Fundamental Theorem of Algebra degree-1 rule; under R1, evaluates polynomial factor completeness.
9. **Subsystem 9: Capability Catalogue & Dispatcher:** Maintains versioned registry of mathematical capabilities. Evaluates structural capability guards against raw AST and routes problems only to eligible, active methods.
10. **Subsystem 10: Method Solver Engines:** Implements specific algebraic algorithms (e.g. linear isolation, quadratic factoring). Emits candidate solutions and structured step derivations.
11. **Subsystem 11: Method Knowledge Base:** Read-only SQLite catalogue storing method principles, historical references, and capability bindings. Static data; no dynamic code execution.
12. **Subsystem 12: Numerical Approximation Service:** Evaluates exact solutions to decimal representations via mpmath at requested precision (e.g. 20, 50 digits). Emits uncertified approximation badges; never replaces exact proof.
13. **Subsystem 13: Plot & Visualization Service:** Generates 2D function sample points, identifies poles and domain holes, and formats visual data for frontend rendering. Never connects across undefined points.
14. **Subsystem 14: Evidence Store & Export Manager:** Persists calculation records, AST digests, domain conditions, step traces, and verification certificates as immutable JSON/JSONL records.
15. **Subsystem 15: Worker Isolation & Resource Supervisor:** Spawns and manages worker processes inside Win32 Job Objects. Enforces 512 MB memory limit, 10s per-task timeout, process-tree termination, scratch directory isolation, and fail-closed shutdown on control failure.

## Proposed interface schemas

Mathematical objects use a versioned, polymorphic JSON schema enabling seamless multi-domain expansion:

```json
{
  "$schema": "https://mke.local/schemas/math_record_v1.json",
  "record_id": "REC-P02A-20260926-001",
  "schema_version": "v1.0",
  "problem": {
    "raw_input": "2*x + 3 = 7",
    "object_type": "SCALAR_EXPRESSION",
    "variable": "x",
    "original_ast": {
      "type": "Equation",
      "lhs": { "type": "Add", "args": [ { "type": "Mul", "args": [ {"type": "Integer", "value": 2}, {"type": "Symbol", "name": "x"} ] }, {"type": "Integer", "value": 3} ] },
      "rhs": { "type": "Integer", "value": 7 }
    },
    "original_domain": {
      "declared": "RealDomain",
      "exclusions": []
    },
    "ast_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "execution": {
    "task_kind": "SOLVE",
    "capability_id": "mke.algebra.solve.linear.v1",
    "method_id": "method.linear.isolate.v1",
    "method_version": "1.0.0"
  },
  "solution": {
    "set_type": "FiniteSet",
    "elements": [
      { "type": "ExactRational", "numerator": 2, "denominator": 1 }
    ]
  },
  "verification": {
    "candidate_soundness": "PASS",
    "exhaustive_completeness": "PASS",
    "domain_preservation": "PASS",
    "overall_status": "VERIFIED",
    "evidence": [
      {
        "evidence_id": "EVID-001",
        "claim_kind": "CANDIDATE_SOUNDNESS",
        "mode": "EXACT_RATIONAL",
        "outcome": "PASS",
        "checker_id": "checker.exact_rational.v1",
        "residual": "0"
      },
      {
        "evidence_id": "EVID-002",
        "claim_kind": "EXHAUSTIVE_COMPLETENESS",
        "mode": "ALGEBRAIC_DEGREE_BOUND",
        "outcome": "PASS",
        "checker_id": "checker.linear_completeness.v1",
        "degree": 1
      }
    ]
  }
}
```

## API lifecycle and failure behavior

1. **Startup Check:** Backend verifies loopback binding, generates an ephemeral 32-byte cryptographic session token, tests Win32 Job Object availability, and confirms read-only permissions on protected paths. If any check fails, backend aborts startup immediately (fail closed).
2. **Task Submission (`POST /api/v1/solve`):** Client submits problem string and optional candidate. Server checks input length, parses AST, runs structural guards.
3. **Execution & Supervision:** Worker process launched inside dedicated Job Object with a 10.0-second timeout.
4. **Failure Modes:**
   - Syntax error: Returns `400 Bad Request` with exact token offset.
   - Out of scope: Returns `200 OK` with status `ABSTAIN` and guard failure details.
   - Timeout (10s): Job Object terminates worker process tree cleanly; returns `200 OK` with status `ABSTAIN` and diagnostic `TIMEOUT_EXCEEDED`.
   - Memory limit (512 MB): Job Object triggers out-of-memory termination; returns `ABSTAIN` with diagnostic `RESOURCE_LIMIT_EXCEEDED`.

## Multimodal specifics

Multimodal ingestion (images and PDFs) is strictly deferred to R2 and operates under bounded constraints:
- Input files are held in an isolated temporary blob store with random UUID names; no raw filesystem paths are exposed.
- Image files are capped at 10 MiB, with dimensions verified before full memory decoding (max 4096 x 4096 px).
- PDFs are capped at 20 MiB and maximum 10 pages.
- Client-side rendering runs in a sandboxed iframe. OCR engines (such as Pix2Text) remain completely disabled until the dedicated R2 gate.
- Mandatory user confirmation is enforced: the engine will never execute solving directly on unconfirmed OCR transcription.

## Knowledge, storage and reproducibility

### Workspace Partitioning & Protected Baseline
To prevent accidental corruption of historical research and accepted baselines:
1. **Product Workspace:** All Product development, build artifacts, test suites, and temporary scratch directories reside strictly in `<WORKSPACE_ROOT>/product\` (or a dedicated external directory).
2. **Protected Paths:**
   - `src/mke/g4p1/` (G4 Evidence Trust source code) — READ-ONLY / PROTECTED.
   - `tests/g4p1/` (G4 test specifications) — READ-ONLY / PROTECTED.
   - `evidence_archive/`, `audit_logs_r1/`, `closure_audit_logs/` — READ-ONLY / PROTECTED.
   - Root markdown specifications (`G4P0_*`, `G4P1_*`, `DEV02A_*`) — READ-ONLY / PROTECTED.
3. **Integrity Verification:** A pre-task and post-task hash manifest script verifies that zero files within protected paths are created, modified, or deleted.
4. **Prohibition of Automatic Cleanup:** Commands such as `git clean -fdx` or `git reset --hard` are strictly prohibited. Untracked files and historical records must be preserved.

## Concise dependency map and extension rule

```
[User Browser]
      │
      ▼
[FastAPI / Local API Layer] (Loopback 127.0.0.1, Session Token Auth)
      │
      ├──► [Custom Safe AST Parser] (No eval, No sympy.parse_expr)
      │          │
      │          ▼
      ├──► [Capability Catalogue & Structural Guards] (Pre-simplification evaluation)
      │          │
      │          ▼
      ├──► [Worker Isolation Host] (Win32 Job Objects, 512MB RAM, Process Tree Kill)
      │          │
      │          ├──► [Whitelisted SymPy AST Converter] (Explicit constructors only)
      │          │
      │          ├──► [Method Solver Engines] (Linear P02A; Quadratic R1)
      │          │
      │          └──► [Independent Exact Verifier] (fractions.Fraction, Domain Check)
      │
      └──► [Evidence & Record Store] (Immutable JSON/JSONL, SHA-256 bound)
```

**Extension Rule:** Any new mathematical domain (e.g. Linear Algebra, Calculus) must be added as a distinct module implementing the typed capability interface. New modules register their own AST object types and verifiers. They are prohibited from altering existing scalar AST definitions, scalar schemas, or verification algorithms.
