# PRODUCT-01 Technology Decisions: Math Knowledge Engine (MKE)

**Document Version:** 0.3.1 (Targeted Remediation - Final Specification Freeze)  
**Status:** Under Review  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Approval Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Core Architectural Decisions

### ADR-01: Exact Rational Arithmetic over Real Domain
- **Decision:** Python standard library `fractions.Fraction` backed by arbitrary-precision integers (`int`).
- **Rationale:** While equations describe relations over the Real domain $\mathbb{R}$, all problem inputs and candidate solutions in Phase P02A belong to the Rational field $\mathbb{Q}$. `fractions.Fraction` guarantees zero floating-point approximation drift, exact reduction via Euclidean GCD, and exact cancellation checking without external CAS dependencies.

### ADR-02: Native Windows Process Sandboxing
- **Decision:** Win32 Job Object isolation with separate 256 MiB per-process and 512 MiB job-wide memory limits.
- **Status:** **PLANNED / UNVERIFIED** pending execution phase.
- **Rationale:** Native OS kernel limits avoid the overhead and privilege requirements of Docker/Hyper-V while providing hard memory ceilings and preventing child process detachment.

### ADR-03: Local API Protocol
- **Decision:** Synchronous HTTP/JSON via FastAPI & Uvicorn bound strictly to `127.0.0.1`. WebSockets and stateful channels are deferred to Release 1+.
- **Rationale:** Discrete request-response cycles for SOLVE and CHECK_CANDIDATE minimize attack surface and avoid session hijacking risks.

---

## 2. Dependency Licensing & Auditing Policy

| Component | Code License | Weights / Asset License | Commercial & Educational Status |
| :--- | :--- | :--- | :--- |
| **Python Standard Library** | PSF License | N/A | Fully Permissive |
| **FastAPI** | MIT | N/A | Fully Permissive |
| **Uvicorn** | BSD-3-Clause | N/A | Fully Permissive |
| **Pydantic** | MIT | N/A | Fully Permissive |
| **Pix2Text** | MIT (code) | Distinct non-commercial / research terms | **Deferred to Release 2; requires separate licensing audit.** |
| **PyMuPDF / fitz** | AGPL-3.0 | N/A | **Disallowed from core engine** (evaluating permissive alternatives). |

*Note on Model Weights:* No blanket claims are made regarding all OCR model licenses. Specific weights used in Release 2 will be individually audited prior to deployment.
