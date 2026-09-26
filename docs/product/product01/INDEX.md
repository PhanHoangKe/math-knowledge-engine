# Math Knowledge Engine (MKE) — PRODUCT-01 Specification Repository

**Directory:** `docs/product/product01/`  
**Current Review Baseline:** Revision 0.3 (Contract Freeze Candidate)  
**Historical Review Baseline:** Revision 0.2 (Sanitized Pre-Remediation Baseline)  
**Governance Roles:**  
- **Project Owner:** Sole Phase & Implementation Approver  
- **ChatGPT:** Chief Architect & Independent Analytical Reviewer  
- **Anty:** Implementation & Documentation Agent  

---

## 1. Directory Structure & Overview

This directory contains the complete architectural, capability, verification, security, and roadmap documentation for the Math Knowledge Engine (MKE) Product Line.

```
docs/product/product01/
├── INDEX.md                                # This document: directory index & governance summary
├── MANIFEST.md                             # Cryptographic SHA-256 manifest of all directory files
├── REMEDIATION_MATRIX_R1_R7.md             # Formal traceability matrix for Review Directives R1–R7
├── OWNER_DECISION_REGISTER.md              # Action items and architectural decisions for Project Owner
├── EVIDENCE_INVENTORY.md                   # Inventory of baselines, standards, and references
├── PRODUCT02A_AUTHORIZATION_PROPOSAL.md    # Formal proposal for Phase P02A implementation scope
├── rev0.2/                                 # Historical baseline submitted for Rev 0.2 audit
│   ├── PRODUCT01_PRD.md
│   ├── PRODUCT01_SYSTEM_ARCHITECTURE.md
│   ├── PRODUCT01_CAPABILITY_MATRIX.md
│   ├── PRODUCT01_VERIFICATION_CONTRACT.md
│   ├── PRODUCT01_TECHNOLOGY_DECISIONS.md
│   ├── PRODUCT01_SECURITY_AND_RISK_REGISTER.md
│   └── PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md
└── rev0.3/                                 # Authoritative candidate for Final Contract Freeze
    ├── PRODUCT01_PRD.md                    # Core product requirements & user stories
    ├── PRODUCT01_SYSTEM_ARCHITECTURE.md    # End-to-end pipeline & Win32 sandbox architecture
    ├── PRODUCT01_CAPABILITY_MATRIX.md      # 4-tier capability taxonomy & structural guards
    ├── PRODUCT01_VERIFICATION_CONTRACT.md  # Formal verification, grammar, & test specifications
    ├── PRODUCT01_TECHNOLOGY_DECISIONS.md   # ADRs, licensed stack, & vulnerability policies
    ├── PRODUCT01_SECURITY_AND_RISK_REGISTER.md # Threat models, Win32 Job Objects, & egress controls
    └── PRODUCT01_ROADMAP_AND_ACCEPTANCE_GATES.md # Phase P02A gates & 160-case evaluation protocol
```

---

## 2. Key Governance Directives

1. **PRODUCT-02A Implementation Unauthorized:** No project code implementation, test execution, or solver prototyping is authorized until Revision 0.3 achieves unanimous freeze sign-off from the Project Owner and Chief Architect.
2. **Repository Baseline Preservation:** The core mathematical repository baseline (`dev02a-method-knowledge-base`) remains 100% frozen. All product development is proposed to occur in an external sibling directory (`../mke-product`).
3. **Deterministic & Sound Foundations:** All mathematical reasoning in Phase P02A is strictly exact over $\mathbb{Q}$, utilizing elementary field algebra and independent candidate verification.
