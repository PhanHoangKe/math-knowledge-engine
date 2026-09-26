# PRODUCT-01 — Security and risk register draft

Status: DRAFT, revision 0.2, 2026-09-26. Controls below are proposed and unimplemented unless explicitly described as inspected legacy evidence.

## Security objective and assets

The primary security objective of MKE is to protect:
1. **Mathematical Integrity:** A mathematically incorrect `VERIFIED` label is a release-critical integrity failure, treated with the same severity as a remote code execution vulnerability.
2. **Local Machine & User Files:** Protect user filesystem, credentials, and host availability against malformed inputs, malicious files, or rogue dependency behavior.
3. **Historical Baselines & Evidence:** Protect the frozen DEV-02A codebase and G4 evidence archives against accidental modification or deletion.

Threat actors include:
- Maliciously crafted mathematical inputs designed to exploit parser vulnerabilities (e.g. `eval` injection).
- Malformed documents (PDF/images) exploiting decompression bombs or parser bugs.
- Malicious websites attempting cross-origin requests to `http://127.0.0.1:<port>`.
- Deceptive or hallucinated outputs from upstream CAS engines or third-party models.

Deployment Scope: Single-user local desktop application on Windows. Internet-facing, multi-tenant, or cloud deployments are strictly out of scope and require a dedicated threat model and owner approval.

## Mandatory control design

### 1. Allowlisted Grammar & AST Parsing (No `eval`, No `sympy.parse_expr`)
- **Vulnerability Note:** Official SymPy documentation confirms that `sympy.parse_expr` internally relies on Python's `eval()` function with arbitrary symbol substitution. Passing untrusted user strings to `sympy.parse_expr` is strictly prohibited.
- **Enforcement:** MKE implements a custom, restricted recursive-descent lexer and parser. Input strings are mapped to canonical internal `ExpressionAST` nodes. Conversion to SymPy occurs exclusively via whitelisted safe constructors (`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`). Any unknown function, object path, import, or macro is rejected at the lexer stage.

### 2. Practical Multi-Layer Windows Execution & Isolation Architecture
The Windows execution model enforces defense-in-depth across distinct operating-system mechanisms:

```
+──────────────────────────────────────────────────────────────────────────────────────────+
| CONTROL LAYER               | OS MECHANISM               | SCOPE / ENFORCEMENT           |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
| 1. Process Tree Termination | Win32 Job Object           | JOB_OBJECT_LIMIT_KILL_ON_JOB_ |
|                             |                            | CLOSE terminates tree cleanly |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
| 2. Memory & CPU Ceilings    | Win32 Job Object           | 512 MB Commit Limit           |
|                             | Extended Limit Info        | 1 CPU Core Rate Limit         |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
| 3. Filesystem Isolation     | Dedicated Scratch CWD      | Worker restricted to scratch; |
|                             | Restricted Process Token   | Write access stripped for all |
|                             | / NTFS ACLs                | repository paths              |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
| 4. Network Isolation        | Loopback-only Binding      | FastAPI binds 127.0.0.1 only; |
|                             | Windows Filtering Platform | 0 outbound network access     |
|                             | (WFP) / Firewall rule      | for worker processes          |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
| 5. API Authentication       | Ephemeral Session Secret   | 32-byte token required on all |
|                             | Strict CORS & CSRF Nonce   | requests; blocks browser CSRF |
+─────────────────────────────+────────────────────────────+───────────────────────────────+
```

- **Important Limitation Clarification:** Windows Job Objects provide robust process-group lifetime control and memory/CPU caps, but **Job Objects do not sandbox the filesystem or network.** Filesystem isolation requires configuring restricted working directories and applying restricted process tokens (`CreateRestrictedToken`) or NTFS ACLs. Network isolation requires binding exclusively to `127.0.0.1` and configuring Windows firewall/WFP rules for worker executables.
- **Fail-Closed Enforcement:** If any mandatory isolation control (e.g. Job Object assignment, scratch directory creation, or session token generation) fails at startup or cannot be verified on the host machine, the engine **fails closed** and refuses to execute rather than falling back to unisolated execution.

### 3. Bounded Document Preview (PDF and Images)
- **Browser-Sandbox Isolation:** Document previews render inside an iframe configured with `sandbox="allow-scripts"` (strictly omitting `allow-same-origin`, `allow-top-navigation`, and `allow-modals`).
- **Realistic Memory Boundary:** A Python backend cannot enforce a hard OS-level memory ceiling on a browser tab. To prevent browser tab crashing or denial of service:
  - File size hard ceilings: Maximum 10 MiB for images, 20 MiB for PDFs.
  - Dimension limits: Images exceeding 4096 x 4096 pixels are rejected *prior* to full rasterization.
  - Page limit: PDFs exceeding 10 pages are rejected.
  - Web Worker timeout: Client-side rendering workers are aborted if rendering takes > 5.0 seconds.

### 4. Workspace Partitioning & Repository Protection
- All Product code, build outputs, and test artifacts are placed in a dedicated `product/` directory outside historical research directories.
- Protected repository paths (`src/mke/g4p1/`, `tests/g4p1/`, historical archives) are monitored via pre-task and post-task SHA-256 manifests.
- Automatic repository cleanups (`git clean -fdx`) are strictly prohibited to prevent data loss of untracked audit or research files.

## Risk register

| Risk ID | Threat / Scenario | Impact | Proposed Mitigation |
|---|---|---|---|
| **R-01** | Arbitrary code execution via `sympy.parse_expr` | Critical | Strictly forbid `sympy.parse_expr`. Implement custom AST parser mapping tokens exclusively to safe constructors (`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`). |
| **R-02** | Worker memory exhaustion or runaway subprocess on Windows | High | Win32 Job Object with 512 MB commit ceiling, 1 CPU core limit, and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. 10.0-second task timeout. |
| **R-03** | Localhost API CSRF attack from malicious browser tab | High | Ephemeral session-scoped bearer token generated at startup; strict CORS limited to `127.0.0.1:<port>`; mandatory `X-MKE-Session-Token` header on all mutating requests. |
| **R-04** | Silent mathematical out-of-scope simplification | Critical | Pre-simplification structural guards. Equations with variables in denominators or degree > 1 are rejected before any algebraic rewriting. |
| **R-05** | Deceptive claim of AI agreement as mathematical truth | High | Four-level independence taxonomy. Clear UI disclosure that AI agreement is not human review. External scientific claims held on HOLD until accredited human review. |
| **R-06** | Accidental modification of accepted DEV-02A or G4 research files | Critical | Strict workspace partitioning (`product/`). Pre-task and post-task hash manifests. Explicit prohibition of `git clean -fdx`. |
| **R-07** | Decompression bomb or malformed PDF/image crash | Medium | Strict file size ceilings (10 MiB image / 20 MiB PDF), max 10 pages, max 4096x4096px, and iframe sandboxing. |
| **R-08** | Pix2Text model weights license contamination | High | OCR capability remains completely disabled by default. Dedicated R2 licensing and offline execution gate required before activation. |

## Privacy and retention proposal

- **100% Local Processing:** Core solving, verification, and rendering operate strictly air-gapped on `127.0.0.1`. Zero outbound network calls.
- **Local Data Retention:** All problem records, AST digests, and evidence traces are stored locally in the user's private data folder.
- **User Records Control:** Users can inspect, export, or permanently delete individual records or the entire local store at any time.
- **No Telemetry:** No analytics, crash reports, or telemetry data are collected or transmitted.

## Resource policy and failure UX

- **Per-Task Timeout:** 10.0 seconds. If exceeded, the Job Object terminates the worker process tree immediately.
- **Per-Task Memory Ceiling:** 512 MB. If exceeded, the Job Object terminates the worker process tree immediately.
- **Total Suite Timeout:** 60.0 seconds for automated test suites.
- **Failure User Experience:** When a worker is terminated due to resource exhaustion or timeout, the UI displays a clear, honest badge: `ABSTAIN (Resource Limit Exceeded: Timeout 10s / Memory 512MB)`. The system never displays partial or guessed results after an abort.

## Incident and release response

Any report of a false exact `VERIFIED` outcome, domain loss, silent simplification, or sandbox escape is classified as a Severity-1 blocker:
1. Immediate reproduction using exact input string and AST digest.
2. Automated regression test generated and added to the permanent test suite.
3. Affected capability or method disabled in the capability catalogue until formal patch and independent review approval.

## Evidence boundary

All security claims in this document are design proposals for future implementation gates. No security mechanisms were executed or validated during PRODUCT-01. Verification of these controls is a mandatory prerequisite for gate G2 (PRODUCT-02A acceptance).
