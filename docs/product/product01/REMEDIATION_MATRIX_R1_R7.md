# PRODUCT-01 Remediation Traceability Matrix (Revision 0.3.1)

**Document Version:** 1.1  
**Target Specification:** Revision 0.3.1  
**Auditor:** ChatGPT (Chief Architect)  
**Agent:** Anty  
**Date:** September 2026  

---

## 1. Compliance Summary Table

| Directive | Core Requirement & Revision 0.3.1 Remediation | Addressing Documents in `rev0.3.1/` | Specific Clauses | Status |
| :--- | :--- | :--- | :--- | :--- |
| **D1: Grammar & Exponents** | One authoritative grammar. Explicit multiplication required (`2*x`). Parse bounded $x^2$ and rational equations for `CHECK_CANDIDATE`, while `SOLVE` abstains. $x^0$ evaluates to 1 on original domain; $0^0$ is `UNDEFINED`. | `PRODUCT01_PRD.md`<br/>`PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_VERIFICATION_CONTRACT.md` | PRD §2.2<br/>CAP §1.1<br/>VER §1 | **REMEDIATED** |
| **D2: Domain & Branching** | Equation domain is Real numbers $\mathbb{R}$ with rational coefficients $\mathbb{Q}$. For $0*x=0$, return `DomainSet(R)`. `SOLVE` and `CHECK_CANDIDATE` are independent branches, not sequential tiers. | `PRODUCT01_PRD.md`<br/>`PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_VERIFICATION_CONTRACT.md` | PRD §2.1, §2.3<br/>CAP §1.1, §3<br/>VER §1, §2 | **REMEDIATED** |
| **D3: Reconciled Release Matrix** | P02A = narrow exact linear; R1 = verified algebra workbench with quadratics and local web UI; R2 = optional systems and separately gated manual PDF/image ingestion. Automated OCR requires separate later gate. Cloud/multiuser = proposals only. | `PRODUCT01_CAPABILITY_MATRIX.md`<br/>`PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md` | CAP §2<br/>ROAD §1 | **REMEDIATED** |
| **D4: Evaluation Protocol** | Covers exact rational arithmetic, linear/degenerate solving, candidate checking (original-domain exclusions, tiny non-zero residuals), syntax/boundary. 80 Dev / 80 Holdout stratified. 160 cases specified as planned (not existing). Resource/security tests as explicit extra gate suites. | `PRODUCT01_VERIFICATION_CONTRACT.md`<br/>`PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md` | VER §3.1, §3.2<br/>ROAD §2 | **REMEDIATED** |
| **D5: Protected Paths & Workspace** | Match actual repository: `src/mke/`, `data/`, `config/`, `schema/`, `tests/g4p1/`, historical evidence archives, local tracked/untracked research files. Acknowledge GitHub cannot verify dirty local tree; sibling workspace `../mke-product` mandatory. | `PRODUCT01_PRD.md`<br/>`PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_SECURITY_AND_RISK_REGISTER.md` | PRD §4<br/>ARCH §3.1<br/>SEC §2 | **REMEDIATED** |
| **D6: Security Status & Resource Limits** | Unimplemented security controls labeled **PLANNED / UNVERIFIED**. Separate 256 MiB per-process and 512 MiB job-wide limits. Error handling/tests specified rather than guaranteed. No blanket claims on all OCR model weights. | `PRODUCT01_SYSTEM_ARCHITECTURE.md`<br/>`PRODUCT01_TECHNOLOGY_DECISIONS.md`<br/>`PRODUCT01_SECURITY_AND_RISK_REGISTER.md` | ARCH §2.1, §2.2<br/>TECH §1, §2<br/>SEC §1, §2 | **REMEDIATED** |
