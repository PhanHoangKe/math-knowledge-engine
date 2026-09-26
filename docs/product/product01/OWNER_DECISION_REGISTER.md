# PRODUCT-01 Owner Decision & Governance Register

**Document Version:** 1.0  
**Current Governance State:** PHASE CONTRACT REVIEW (PRODUCT-02A NOT AUTHORIZED)  
**Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Active Decisions Requiring Project Owner Action

| Decision ID | Area | Context & Proposed Recommendation | Impact & Rationale | Status |
| :--- | :--- | :--- | :--- | :--- |
| **DEC-OWN-01** | **Implementation Workspace Boundary** | **Proposal:** Establish external sibling workspace `../mke-product` for all Phase P02A implementation, leaving `PhanHoangKe/math-knowledge-engine` strictly for frozen core baselines and documentation. | Protects the historical core repository and G4 baseline from accidental code pollution, dependency conflicts, or git mutations. | **AWAITING OWNER DECISION** |
| **DEC-OWN-02** | **Release 2 Document Ingestion Engine** | **Proposal:** Defer image/PDF document ingestion to Release 2; conduct licensing and technical audit of Pix2Text pre-trained model weights versus permissive alternatives (e.g. Tesseract / custom models). | Pix2Text repository code is MIT, but pre-trained weights carry non-commercial restrictions that may restrict commercial deployment. | **AWAITING OWNER DECISION** |
| **DEC-OWN-03** | **PRODUCT-01 Revision 0.3 Contract Freeze** | **Proposal:** Approve Revision 0.3 across all seven PRODUCT-01 documents as the authoritative, frozen design contract for the MKE product line. | Closes all open items from Directives R1 through R7; establishes unambiguous acceptance criteria for Phase P02A. | **SUBMITTED FOR APPROVAL** |
| **DEC-OWN-04** | **Phase P02A Implementation Authorization** | **Proposal:** Issue formal directive authorizing commencement of Phase P02A (Exact Linear Kernel & Win32 Sandbox) strictly upon approval of DEC-OWN-01 and DEC-OWN-03. | Guarantees that no code is written without explicit baseline lock and agreed acceptance gates. | **BLOCKED ON DEC-01 & 03** |

---

## 2. Invariant Policies Confirmed

1. **Sole Approval Authority:** Only the Project Owner can authorize phase transitions, new implementation workspaces, or schema modifications.
2. **Reviewer Mandate:** ChatGPT serves as Chief Architect and independent auditor; all deliverables require formal verification before sign-off.
3. **Implementation Restraint:** Anty operates strictly within bounded static authoring directives; zero unauthorized execution, commits, or publish actions.
