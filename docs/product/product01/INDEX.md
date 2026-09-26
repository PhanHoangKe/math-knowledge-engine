# Math Knowledge Engine (MKE) — PRODUCT-01 Specification Repository

**Directory:** `docs/product/product01/`  
**Current Review Baseline:** Revision 0.3.1 (Targeted Remediation Candidate)  
**Historical Review Baselines:** Revision 0.2, Revision 0.3  
**Governance Roles:**  
- **Project Owner:** Sole Phase & Implementation Approver  
- **ChatGPT:** Chief Architect & Independent Analytical Reviewer  
- **Anty:** Implementation & Documentation Agent  

---

## 1. Directory Structure & Overview

```
docs/product/product01/
├── INDEX.md                                # Directory index & governance overview
├── MANIFEST.md                             # Cryptographic SHA-256 manifest of all files
├── REMEDIATION_MATRIX_R1_R7.md             # Traceability matrix for audit directives
├── OWNER_DECISION_REGISTER.md              # Active owner decisions & architectural gates
├── EVIDENCE_INVENTORY.md                   # Baseline specifications & technical standards
├── PRODUCT02A_AUTHORIZATION_PROPOSAL.md    # Formal proposal for Phase P02A implementation scope
├── rev0.2/                                 # Historical baseline (Rev 0.2 audit)
├── rev0.3/                                 # Historical baseline (Rev 0.3 audit)
└── rev0.3.1/                               # Authoritative Candidate for Final Contract Freeze
    ├── PRODUCT01_PRD.md
    ├── PRODUCT01_SYSTEM_ARCHITECTURE.md
    ├── PRODUCT01_CAPABILITY_MATRIX.md
    ├── PRODUCT01_VERIFICATION_CONTRACT.md
    ├── PRODUCT01_TECHNOLOGY_DECISIONS.md
    ├── PRODUCT01_SECURITY_AND_RISK_REGISTER.md
    └── PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md
```

---

## 2. Key Governance Directives

1. **PRODUCT-02A Implementation Unauthorized:** No code implementation or test execution is permitted until Revision 0.3.1 is approved by the Project Owner.
2. **Core Repository Baseline Frozen:** The core repository (`src/mke/`, `data/`, `config/`, `schema/`, `tests/g4p1/`, historical evidence archives, and research files) remains 100% frozen. Development is proposed for external sibling workspace `../mke-product`.
3. **Mathematical & Domain Integrity:** Equation domain is the Real numbers $\mathbb{R}$ with rational coefficients $\mathbb{Q}$. Independent branches for `SOLVE` (linear foundation) and `CHECK_CANDIDATE` (linear, bounded $x^2$, and rational equations with original-domain validation).
