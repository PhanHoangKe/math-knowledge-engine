# PRODUCT-01 Technology Decisions: Math Knowledge Engine (MKE)

**Document Version:** 0.3 (Review Draft - Contract Freeze Remediation)  
**Status:** Under Review (Remediated per R1-R7 Directives)  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Approval Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Context & Architectural Principles

The technical stack for the Math Knowledge Engine is chosen under rigorous engineering constraints:
1. **Mathematical Soundness:** Pure, deterministic exact rational arithmetic; zero floating-point approximation drift in core reasoning.
2. **Strict Host Isolation:** Native, low-overhead Windows OS-level process sandboxing via Win32 Job Objects.
3. **Licensing Transparency & Safety:** Rigorous audit of all runtime dependencies, distinguishing permissive code licenses from restrictive or non-commercial model weight licenses.
4. **Minimal Attack Surface:** Preference for stateless, synchronous HTTP/JSON protocols over stateful WebSocket channels in early releases.

---

## 2. Core Technology Stack & Architectural Decision Records (ADR)

### ADR-01: Exact Rational Arithmetic Engine
- **Decision:** Python standard library `fractions.Fraction` backed by arbitrary-precision integers (`int`).
- **Rationale:** The mathematical domain of Phase P02A is strictly linear equations over $\mathbb{Q}$. `fractions.Fraction` automatically simplifies fractions to canonical lowest terms ($p/q$ where $\gcd(p, q) = 1$ and $q > 0$) using the Euclidean algorithm. It completely eliminates IEEE 754 floating-point inaccuracies ($0.1 + 0.2 \neq 0.3$) and avoids heavy external CAS dependencies (e.g., SymPy).
- **Compliance with R1:** Directly powers the $-b/a$ exact root calculation and the independent verification substitution pass.

### ADR-02: Native Windows Process Sandboxing (Win32 Job Objects)
- **Decision:** Direct Win32 Job Object isolation via `ctypes` / Win32 API rather than Docker/containers or unconstrained child processes.
- **Rationale:** MKE targets local Windows desktop and classroom environments without requiring Hyper-V, WSL2, or Docker daemon privileges. Win32 Job Objects provide deterministic operating system kernel enforcement:
  - Hard memory quota (`JOB_OBJECT_LIMIT_JOB_MEMORY` set to 512 MB, per-process limit 256 MB).
  - Child process breakaway prohibition (`JOB_OBJECT_LIMIT_BREAKAWAY_OK` strictly cleared).
  - Automatic process tree cleanup on controller exit (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`).
- **Creation Lifecycle (Directive R5):** Host controller executes:
  1. `CreateJobObjectW`
  2. `SetInformationJobObject` with basic and extended resource limits.
  3. `CreateProcessW` with `CREATE_SUSPENDED`.
  4. `AssignProcessToJobObject`.
  5. `ResumeThread`.

### ADR-03: Local API Protocol — HTTP/JSON vs WebSockets (Directive R5)
- **Decision:** Synchronous HTTP/JSON via FastAPI & Uvicorn for Phase P02A. **WebSockets are explicitly deferred to Release 1+**.
- **Rationale:** 
  - Phase P02A workflows are discrete request-response cycles (Parse $\rightarrow$ Solve $\rightarrow$ Verify). 
  - Stateless HTTP POST endpoints have a significantly smaller attack surface than long-lived WebSocket sessions.
  - Eliminates state synchronization, connection drops, and socket hijacking vulnerabilities in the initial release.
  - Security hardening: Server binds strictly to loopback `127.0.0.1`, validates `Host` headers to prevent DNS rebinding, and requires an ephemeral startup session token.

### ADR-04: Canonical Serialization Engine (RFC 8785 / JCS) (Directive R7)
- **Decision:** Strict RFC 8785 (JSON Canonicalization Scheme) implementation for all AST representations, cryptographic hashes, and verification receipts.
- **Rationale:** Standard `json.dumps()` in Python does not guarantee canonical key ordering, whitespace minimization, or standard ECMAScript number formatting. RFC 8785 produces byte-identical serialized output across heterogeneous runtimes, ensuring that `ast_sha256` and verification receipts are verifiable across platforms.

---

## 3. Dependency Licensing & Vulnerability Management (Directive R2)

### 3.1 Pinned Dependency License Audit

| Component | Repository Code License | Model Weights / Assets License | Commercial Use Permitted? | Architectural Status |
| :--- | :--- | :--- | :--- | :--- |
| **Python Standard Library** | PSF License | N/A | Yes | **Core Runtime** |
| **FastAPI** | **MIT** | N/A | Yes | **Core HTTP Service** |
| **Uvicorn** | **BSD-3-Clause** | N/A | Yes | **Core ASGI Server** |
| **Pydantic** | **MIT** | N/A | Yes | **Data Validation** |
| **Pix2Text** | **MIT** | **Restricted / Academic Non-Commercial** | **Conditional / No** | **Deferred to Release 2** |
| **PyMuPDF / fitz** | **AGPL-3.0** | N/A | **High Risk (Copyleft)** | **Disallowed** (evaluating `pdfminer.six`) |

### 3.2 Vulnerability Policy
- Replacement of "zero vulnerability" claims with an active, automated scanning policy using `pip-audit`.
- Critical and High vulnerabilities block release candidate promotion. Medium and Low vulnerabilities are evaluated with documented compensating controls.
- Full CycloneDX Software Bill of Materials (SBOM) produced for every release package.
