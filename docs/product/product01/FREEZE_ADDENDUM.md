# PRODUCT-01 Freeze Addendum: Binding Normative Contract

**Document Version:** 1.0 (Binding Final Freeze Addendum)  
**Target Specification:** Revision 0.3.1  
**Status:** Authoritative Freeze Addendum (Conditionally Accepted Baseline)  
**Governance Authority:** Project Owner  
**Chief Architect & Auditor:** ChatGPT  
**Implementation Agent:** Anty  
**Date:** September 2026  

---

## 1. Purpose & Precedence Hierarchy

This document serves as the final, authoritative addendum to PRODUCT-01 Revision 0.3.1. In the event of any ambiguity or conflict between historical specifications (Revision 0.2, Revision 0.3) and Revision 0.3.1, the hierarchy of precedence is:
1. **FREEZE_ADDENDUM.md** (This document — Highest Precedence)
2. **Revision 0.3.1 Specifications** (`docs/product/product01/rev0.3.1/`)
3. **Preserved Clauses from Revision 0.2 / 0.3** (Explicitly enumerated below)

Historical clauses from rev0.2/rev0.3 that contradict rev0.3.1 or this addendum are strictly **superseded** and **never automatically inherited**.

---

## 2. Harmonization of Normative Clauses

### 2.1 Essential Clauses Preserved as Normative from rev0.2 / rev0.3
The following requirements from earlier drafts remain strictly normative:
- **Typed Evidence Architecture:** Every verification event must produce a typed, machine-verifiable evidence payload with RFC 8785 canonical SHA-256 digests.
- **Certificate Obligations:** Solvers and verifiers must generate structured certificates containing exact substitution proofs, variable bindings, and deterministic result enums.
- **Step Trace Provenance:** Step-by-step traces must record deterministic step-rule IDs, algebraic justification codes, and sub-AST hashes.
- **Security Invariants:** Unprivileged worker process execution, strict kernel containment, zero outbound network communication, and deterministic resource exhaustion handling.

### 2.2 Clauses Formally Superseded by rev0.3.1 & Addendum
- **Domain Definition:** Superseded by Real domain $\mathbb{R}$ with rational coefficients $\mathbb{Q}$. $0 \cdot x = 0 \implies \text{DomainSet(R)}$.
- **Architecture Pipeline:** Superseded by independent operational branches (`SOLVE` vs `CHECK_CANDIDATE`) replacing rigid sequential tiers.
- **Syntax Enforcement:** Superseded by mandatory explicit multiplication (`2*x`); implicit multiplication is unconditionally rejected.
- **Vulnerability Policy:** Superseded by risk-based CVSS v3 scanning policy, abandoning blanket zero-vulnerability assertions.
- **Arithmetic Engine:** Superseded by exact rational arithmetic (`fractions.Fraction`) over $\mathbb{Q}$, eliminating IEEE 754 floating drift.

### 2.3 Clauses Formally Deferred
- **Interactive WebSockets:** Deferred to Release 1+.
- **Automated OCR Ingestion:** Deferred to a distinct gate post-Release 2.
- **Cloud & Multi-Tenant Infrastructure:** Deferred to long-term architectural proposals only.

---

## 3. Exponent-Zero Semantics & SOLVE Pre-Simplification Guard

### 3.1 Pre-Simplification SOLVE Guard
In Phase P02A, **any expression containing a variable-dependent base raised to the power of zero** (e.g., $x^0$, $(x-1)^0$, $(2*x + 3)^0$) is classified as **`OUT_OF_SCOPE_FOR_SOLVER`** prior to algebraic reduction. The linear solver engine abstains immediately with error code:
`OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`

### 3.2 CHECK_CANDIDATE Original-Domain Evaluation
The candidate verification engine (`CHECK_CANDIDATE`) accepts equations with constant exponents $\in \{0, 1, 2\}$ and evaluates candidates directly against the **original unreduced domain of definition**:
- **Equation $x^0 = 1$:**
  - Candidate $x = 0$: Evaluates $0^0$, which is mathematically indeterminate/undefined $\implies$ **`DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`** (`INVALID`).
  - Candidate $x = 2$: Evaluates $2^0 = 1$, which equals RHS $1 \implies$ **`VALID`**.
- **Equation $(x - 1)^0 = 1$:**
  - Candidate $x = 1$: Evaluates $(1 - 1)^0 = 0^0 \implies$ **`DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`** (`INVALID`).
  - Candidate $x = 3$: Evaluates $(3 - 1)^0 = 2^0 = 1 \implies$ **`VALID`**.

---

## 4. Reconciled 160-Case Planned Test Allocation

The 160 offline evaluation cases are planned test specifications, equally partitioned into Development (DEV) and Sealed Holdout (HOLDOUT) sets:

| Family ID | Test Family Description | DEV Cases | HOLDOUT Cases | Total Planned Cases |
| :--- | :--- | :--- | :--- | :--- |
| **FAM-01** | **Exact Rational Arithmetic:** Arbitrary precision $\mathbb{Q}$, Euclidean GCD reduction, signs, zero-numerator handling. | 20 | 20 | 40 |
| **FAM-02** | **Linear & Degenerate Solving:** Unique roots ($x = -b/a$ in $\mathbb{R}$), identities ($0x = 0 \implies \text{DomainSet(R)}$), contradictions ($0x = c \implies \emptyset$). | 20 | 20 | 40 |
| **FAM-03** | **Candidate & Domain Checking:** Verification of exact roots across linear, bounded $x^2$, and rational equations; original-domain exclusions ($0^0$, division by zero); tiny non-zero rational residuals. | 20 | 20 | 40 |
| **FAM-04** | **Parser & Ambiguity Rejection:** Rejection of implicit multiplication (`2x`, `1/2x`), unsupported exponents ($x^3$), invalid characters, malformed tokens. | 10 | 10 | 20 |
| **FAM-05** | **Semantic Undefinedness:** Literal division by zero ($E/0$), constant indeterminate forms ($0^0$), nested zero denominators. | 10 | 10 | 20 |
| **Total** | | **80** | **80** | **160** |

> [!IMPORTANT]
> **Specification Notice:** The 160 cases defined above represent **planned test specifications**. No claim is made that concrete test fixtures or independent human evaluations exist until formally authored, supplied, and inspected.

### 4.1 Separate Mandatory Gate Suites (Non-Algebraic)
Resource consumption and security isolation are evaluated via dedicated, independent gate suites:
1. **Resource Limits Suite:** Enforces 256 MiB per-process limit and 512 MiB job-wide limit under allocation stress.
2. **Process Isolation Suite:** Confirms revocation of `JOB_OBJECT_LIMIT_BREAKAWAY_OK` on spawned child processes.
3. **Network Egress Suite:** Validates that loopback sockets allow only local binding and that outbound connections fail closed.
4. **API Security Suite:** Enforces `Host` header matching, `Origin` isolation, and `X-MKE-Session-Token` presence.

---

## 5. Actionable PLANNED Security Contracts

All security controls remain designated as **`PLANNED / UNVERIFIED`** until verified during Phase P02A runtime testing.

| Security Domain | Actionable Planned Implementation | Target Behavior & Error Code |
| :--- | :--- | :--- |
| **Filesystem Isolation** | Worker process launched with restricted ACL token; read-only access to standard libraries; write access restricted strictly to dedicated ephemeral scratch folder. | Unauthorized filesystem write rejected with Win32 `ERROR_ACCESS_DENIED`. |
| **Outbound Egress** | Worker process sockets bound strictly to `127.0.0.1`; outbound egress blocked via Windows Firewall or transport filtering. | Outbound connect attempt fails immediately $\implies$ `ERR_NETWORK_DISALLOWED`. |
| **Session Bootstrap** | Host controller generates a cryptographically random 256-bit token at startup; client requests must supply `X-MKE-Session-Token`. | Missing or invalid token returns HTTP `401 Unauthorized`. |
| **Host & Origin Validation** | Middleware checks request headers; `Host` must strictly equal `127.0.0.1:<port>` or `localhost:<port>`. Cross-origin browser calls blocked. | Header mismatch returns HTTP `403 Forbidden` (`ERR_HOST_HEADER_MISMATCH`). |
| **Resource Failure Handling** | If worker exceeds 256 MiB process or 512 MiB job limits, Windows kernel kills process; controller intercepts termination message. | Host returns deterministic error payload `ERR_WORKER_RESOURCE_EXHAUSTED`. |

---

## 6. Repository Protected Paths Distinction

- **GitHub-Observed Tracked Paths:** `src/mke/`, `config/`, `schema/`, `tests/g4p1/`.
- **Locally Reported Protected Paths:** Local uncommitted research files, adversarial test scripts, historical evidence logs, and environment configuration.
- **Isolation Policy:** Because remote git/GitHub cannot observe or guarantee the integrity of uncommitted local working tree artifacts, all Phase P02A development is quarantined to the external sibling directory **`../mke-product`**, leaving the root repository working tree completely untouched.
