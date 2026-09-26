# PRODUCT-01 Security & Risk Register: Math Knowledge Engine (MKE)

**Document Version:** 0.3 (Review Draft - Contract Freeze Remediation)  
**Status:** Under Review (Remediated per R1-R7 Directives)  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Approval Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Security Governance & Threat Model

The Math Knowledge Engine processes mathematical expressions that may originate from untrusted external sources (user input, imported documents, third-party integration). The security architecture enforces defense-in-depth across:
1. **Mathematical Input Boundaries:** Rejection of malicious, ambiguous, or computationally explosive expressions.
2. **Process Execution Boundaries:** Hardened Win32 Job Object isolation preventing privilege escalation, persistence, memory exhaustion, or child process escape.
3. **Network Isolation:** Strict air-gapping and loopback binding.
4. **Vulnerability Management Policy:** Concrete, risk-prioritized vulnerability mitigation replacing unrealistic "zero vulnerability" claims.

---

## 2. Vulnerability Management Policy (Directive R2)

In strict compliance with **Directive R2**, MKE abandons blanket "zero-vulnerability" claims in favor of an industry-standard, risk-based vulnerability management policy:

| Severity Level | CVSS v3 Score | Maximum Remediation Timeframe | Release Gate Blocking Status |
| :--- | :--- | :--- | :--- |
| **Critical** | 9.0 – 10.0 | Immediate (within 24 hours of disclosure) | **Hard Gate Blocker:** Release halted immediately. |
| **High** | 7.0 – 8.9 | Within 7 calendar days | **Hard Gate Blocker:** Cannot ship without formal Owner waiver. |
| **Medium** | 4.0 – 6.9 | Within 30 calendar days | **Conditional:** Permitted if compensatory controls are active. |
| **Low** | 0.1 – 3.9 | Scheduled in next minor release cycle | **Informational:** Documented in known risk log. |

### Continuous Dependency Audit
- Automated scanning of pinned dependencies using `pip-audit` and `safety` against the National Vulnerability Database (NVD) and GitHub Advisory Database.
- Strict software bill of materials (SBOM) generated in CycloneDX JSON format for every release candidate.

---

## 3. Third-Party Dependency & Licensing Risk Analysis (Directive R2)

| Dependency | Stated License | Verified Repository Code License | Model Weights / Assets License | Security & Compliance Risk Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | MIT | **MIT** (tiangolo/fastapi) | N/A (Code only) | **Low Risk:** Fully permissive open-source license. High maintenance activity, rapid patch cadence. |
| **Uvicorn** | BSD-3-Clause | **BSD-3-Clause** | N/A (Code only) | **Low Risk:** Permissive license. Configured strictly for local loopback (`127.0.0.1`). |
| **Pydantic** | MIT | **MIT** | N/A (Code only) | **Low Risk:** Input validation and schema serialization engine. Core dependency. |
| **Pix2Text** | MIT | **MIT** (Breezedeus/Pix2Text)| **Restricted / Non-Commercial Weights** | **High Compliance Risk:** While the repository source code is MIT-licensed, pre-trained neural model weights carry proprietary or academic non-commercial terms. **Mitigation:** Deferred to Release 2; will not be bundled in Phase P02A or Release 1. |
| **PyMuPDF / fitz**| AGPL-3.0 | **AGPL-3.0** | N/A | **Severe Licensing Risk:** AGPL copyleft viral obligations would taint proprietary codebases. **Mitigation:** Disallowed from core engine. Evaluating permissive alternatives (e.g., `pdfminer.six` under MIT) for future document ingestion. |

---

## 4. Comprehensive Threat & Risk Register (Directives R1–R7)

| Risk ID | Category | Threat / Vulnerability Description | Impact | Likelihood | Mitigation & Enforcement Mechanism | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-SEC-01** | Process Security | Worker process escapes sandbox or spawns detached child processes via Win32 breakaway. | Critical | Low | Win32 Job Object configured with `JOB_OBJECT_LIMIT_BREAKAWAY_OK` cleared and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` set. `CreateProcessW` called suspended. | **Mitigated** |
| **RSK-SEC-02** | Denial of Service | Memory exhaustion via deeply nested ASTs or high-degree polynomials. | High | Medium | Hard memory ceiling (256 MB) on Job Object; strict input length limits ($N \le 256$ chars); AST depth cap = 16. | **Mitigated** |
| **RSK-SEC-03** | Network / Egress | Unauthorized outbound telemetry or network communication from execution worker. | High | Low | Worker processes strictly prohibited from opening outbound sockets; Windows firewall isolation; zero external dependencies at runtime. | **Mitigated** |
| **RSK-SEC-04** | API / Rebinding | DNS rebinding or CSRF attacks targeting local FastAPI HTTP interface. | High | Medium | Strict Host header validation (`127.0.0.1:<port>`), loopback binding only, startup cryptographic session token validation. Defer WebSockets to R1+. | **Mitigated** |
| **RSK-SEC-05** | Math Integrity | Ambiguous implicit multiplication (`1/2x`) leading to divergent or unsound interpretations. | High | High | Strict parser grammar rejection (`AMBIGUOUS_IMPLICIT_MULTIPLICATION_REJECTED`). Ambiguity is never guessed. | **Mitigated** |
| **RSK-SEC-06** | Math Integrity | Indeterminate $0^0$ or division by zero causing solver crashes or unsound identity proofs. | High | Medium | 4-tier semantic definedness validation; explicit rejection of $0^0$ and $E/0$ before solver invocation. | **Mitigated** |
| **RSK-SEC-07** | Repository | Accidental overwrite or corruption of frozen MKE repository baseline during development. | Critical | Medium | External sibling workspace (`../mke-product`); write-protection of core paths; ban on `git clean -fdx`; pre/post SHA manifests. | **Mitigated** |
| **RSK-SEC-08** | Client UI Sandbox | PDF rendering vulnerabilities in client-side web/desktop viewers. | Medium | Medium | Marked explicitly as **Unresolved** in P02A; client-side PDF ingestion deferred to Release 2 pending containerized sandbox design. | **Recorded / Open** |

---

## 5. Security Verification & Test Protocol

In Phase P02A pre-implementation planning, the security testing suite defines negative test specifications across 4 key vectors:
1. **Parser Bomb Vectors:** Exponential nested parentheses `((((...))))`, oversized integer literals ($10^{1000}$), and malformed unicode strings.
2. **Breakaway & Process Injection Vectors:** Attempted invocation of subprocesses, DLL injection, or thread creation breaking job boundaries.
3. **Network Access Probes:** Worker attempts to resolve DNS or bind to external interfaces must result in immediate operational termination.
4. **Header Forgery Probes:** HTTP requests with forged `Host: attacker.com` or unauthorized CORS headers must receive immediate `403 Forbidden` responses.
