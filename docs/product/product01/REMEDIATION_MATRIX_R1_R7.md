# PRODUCT-01 Remediation Traceability Matrix (Directives R1 – R7)

**Document Version:** 1.0  
**Target Specification:** Revision 0.3  
**Auditor:** ChatGPT (Chief Architect)  
**Agent:** Anty  
**Date:** September 2026  

---

## 1. Compliance Summary Table

| Directive | Core Requirement | Addressing Documents in `rev0.3/` | Specific Sections / Clauses | Compliance Status |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | **Mathematical Semantics & Grammar**<br/>- Authoritative P02A grammar (single var `x`, rational coefs, degree $\le 1$)<br/>- Reject ambiguous implicit multiplication (`1/2x`, `2x`)<br/>- 4-tier capability separation (valid, defined, solve, check)<br/>- Exponent limits ($^0, ^1$), $0^0 \implies \text{UNDEFINED}$<br/>- Pre-simplification structural guards against rational fractions<br/>- Exact root $-b/a$ via field algebra of $\mathbb{Q}$ | `PRODUCT01_PRD.md`<br/>`PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_VERIFICATION_CONTRACT.md` | PRD §2.1–§2.3<br/>CAP §2.1–§2.4<br/>ARCH §2<br/>VER §2.1–§2.4 | **FULL COMPLIANCE** |
| **R2** | **Technology Factual Corrections**<br/>- FastAPI license corrected to MIT<br/>- Pix2Text repository code license MIT, weights restricted<br/>- PyMuPDF AGPL-3.0 risk noted / disallowed<br/>- Replace "zero-vulnerability" claims with CVSS-based scanning policy | `PRODUCT01_TECHNOLOGY_DECISIONS.md`<br/>`PRODUCT01_SECURITY_AND_RISK_REGISTER.md` | TECH §3.1–§3.2<br/>SEC §2, §3 | **FULL COMPLIANCE** |
| **R3** | **Release Boundaries & Matrix**<br/>- Authoritative release matrix (P02A vs R1 vs R2 vs R3+)<br/>- Manual image/PDF ingestion scheduled for R2 (pending owner decision) | `PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md` | CAP §3<br/>ROAD §1 | **FULL COMPLIANCE** |
| **R4** | **Repository & Workspace Protection**<br/>- Dedicated sibling workspace `../mke-product` proposed<br/>- Core paths protected (`core/`, `schemas/`, `tests/fixtures/`)<br/>- Prohibition of `git clean -fdx`; pre/post manifests | `PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md` | ARCH §3<br/>ROAD §4 | **FULL COMPLIANCE** |
| **R5** | **Security & Process Contract**<br/>- Win32 Job Object creation order (`CREATE_SUSPENDED` $\rightarrow$ `Assign` $\rightarrow$ `Resume`)<br/>- Hard memory ceiling (256 MB), breakaway prohibited<br/>- Outbound network egress blocked<br/>- Local HTTP/JSON only (WebSockets deferred)<br/>- Session bootstrap & Host/Origin validation<br/>- Browser PDF sandbox limits marked unresolved | `PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_SECURITY_AND_RISK_REGISTER.md`<br/>`PRODUCT01_TECHNOLOGY_DECISIONS.md` | ARCH §4.1–§4.3<br/>SEC §1, §4<br/>TECH §2 (ADR-02, ADR-03) | **FULL COMPLIANCE** |
| **R6** | **Evaluation Protocol**<br/>- Planned 160-case specification (80 Dev / 80 Holdout)<br/>- Stratified across 5 case families<br/>- Runtime, API-security, cancellation categories included<br/>- No claim of AI as human ground truth | `PRODUCT01_VERIFICATION_CONTRACT.md`<br/>`PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md` | VER §3.1–§3.3<br/>ROAD §2, §3 | **FULL COMPLIANCE** |
| **R7** | **Schemas & Provenance**<br/>- Removal of invented or speculative hashes<br/>- RFC 8785 canonical AST serialization (JCS)<br/>- Multi-domain schema regression contract | `PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_VERIFICATION_CONTRACT.md` | CAP §4<br/>ARCH §5<br/>VER §4 | **FULL COMPLIANCE** |

---

## 2. Detailed Verification Notes

### Mathematical Clarifications (R1)
- **Implicit Multiplication:** The system grammar unequivocally forbids juxtaposition multiplication. The expression `1/2x` produces a parse failure `AMBIGUOUS_IMPLICIT_MULTIPLICATION_REJECTED` rather than evaluating as either $(1/2)x$ or $1/(2x)$.
- **Field Algebra vs FTA:** The solver documentation explicitly states that linear completeness is derived from the field properties of $\mathbb{Q}$ ($a \neq 0 \implies \exists! a^{-1} \in \mathbb{Q}$ such that $x = -a^{-1}b$), entirely dispensing with unnecessary references to the Fundamental Theorem of Algebra.
- **Structural Guard:** Expressions containing variables in any denominator (such as $\frac{x^2-1}{x-1} = 0$ or $\frac{x}{x} = 1$) are rejected at the pre-simplification stage as `OUT_OF_SCOPE_RATIONAL_FRACTION`, avoiding unsound cancellation or false linear domain reduction.

### Dependency & Security Hardening (R2 & R5)
- All technology matrices accurately reflect upstream repository licenses.
- The Win32 Job Object lifecycle strictly guarantees that untrusted worker processes never run uncontained: process initialization begins suspended, memory caps are locked, breakaway privileges are revoked, and loopback socket restrictions are applied prior to thread resumption.
