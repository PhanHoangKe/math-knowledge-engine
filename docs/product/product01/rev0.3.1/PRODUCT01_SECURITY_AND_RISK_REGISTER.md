# PRODUCT-01 Security & Risk Register: Math Knowledge Engine (MKE)

**Document Version:** 0.3.1 (Targeted Remediation - Final Specification Freeze)  
**Status:** Under Review  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Approval Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Security Governance & Control Status

In strict accordance with audit directives, all unimplemented security controls are formally classified as **PLANNED / UNVERIFIED**. Security behavior is not guaranteed until verified against explicit runtime test suites.

---

## 2. Risk Register & Control Specification

| Risk ID | Threat Category | Threat Description | Planned Security Control | Control Status |
| :--- | :--- | :--- | :--- | :--- |
| **RSK-SEC-01** | Process Security | Worker process escapes sandbox or spawns detached child processes. | Win32 Job Object with `JOB_OBJECT_LIMIT_BREAKAWAY_OK` cleared. Process created suspended. | **PLANNED / UNVERIFIED** |
| **RSK-SEC-02** | Resource Exhaustion | Memory exhaustion via deep AST nesting or large allocations. | Dual quota: 256 MiB per-process limit, 512 MiB job-wide limit. | **PLANNED / UNVERIFIED** |
| **RSK-SEC-03** | Network Egress | Unauthorized outbound telemetry or socket connection from worker. | Loopback-only binding (`127.0.0.1`), outbound sockets blocked. | **PLANNED / UNVERIFIED** |
| **RSK-SEC-04** | API Rebinding | DNS rebinding or Host header forgery targeting local HTTP testbed. | Strict `Host` header validation (`127.0.0.1:<port>`), startup session tokens. | **PLANNED / UNVERIFIED** |
| **RSK-SEC-05** | Math Integrity | Ambiguous syntax (`1/2x`) causing divergent interpretations. | Strict parser grammar rejection (`AMBIGUOUS_IMPLICIT_MULTIPLICATION_REJECTED`). | **SPECIFIED IN CONTRACT** |
| **RSK-SEC-06** | Math Integrity | Original-domain violations (e.g. division by zero in unreduced form). | Pre-evaluation domain check in `CHECK_CANDIDATE` rejecting invalid candidates. | **SPECIFIED IN CONTRACT** |
| **RSK-SEC-07** | Workspace Mutation | Accidental mutation of dirty core working tree (`src/mke/`, historical data). | External sibling workspace `../mke-product` proposed for implementation. | **PLANNED / PENDING OWNER** |
| **RSK-SEC-08** | Ingestion Licensing | Inadvertent commercial violation via deep-learning OCR model weights. | Manual ingestion deferred to R2; automated OCR requires separate later gate. | **MANAGED VIA ROADMAP** |
