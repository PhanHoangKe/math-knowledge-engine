# PRODUCT-01 Evidence & Reference Inventory

**Document Version:** 1.0  
**Repository:** `docs/product/product01/`  
**Date:** September 2026  

---

## 1. Baseline Specifications & Prior Directives

| Baseline Identifier | Description / Artifact Reference | Cryptographic SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| **G4-P0 Mathematical Spec** | Frozen G4 Mathematical Specification | `468fd52c7879609a4c22e6ad5d1f9f9baeedddb0c62b3a5ff1c8b919ed5966ed` | **FROZEN / BASELINE** |
| **G4-P1-I0-R4B** | Implementation Baseline Delta | `954278f5e963e26acd2e20913653a5dce06726fc69b54a261028691e950a0552` | **FROZEN / BASELINE** |
| **G4-P1-D1** | Design Baseline Alignment | `454abe6492539196b9fa5b9aaae6989db9b76452526c06e832bda58ae222164b` | **FROZEN / BASELINE** |
| **G4-P1-I1-R2** | Final Evidence Delta Candidate | `6b4d02d1d0f47d5c10036d40e2754a24b3048ac267e96f5012c9cb4d3d0b2c5e` | **FROZEN / BASELINE** |
| **G4-P1-V1A** | Static Corrections Baseline | `42d3da9e99d12fe80c84120685ca24080df330ecf8097f98bf6fe2812f7a1e2d` | **FROZEN / BASELINE** |
| **G4-P1-V1B1** | Pre-Execution Static Delta | `7cf29616d6ae452f1430932204c643fb46b5a34a974b88f61543b5993e50c7bb` | **FROZEN / BASELINE** |

---

## 2. External Technical Standards & RFCs

1. **RFC 8785:** JSON Canonicalization Scheme (JCS) — Internet Engineering Task Force (IETF). Canonical, deterministic serialization format for cryptographic hashing of Abstract Syntax Trees and verification proofs.
2. **IEEE 754-2019:** Standard for Floating-Point Arithmetic. Used in MKE documentation as the negative reference standard; MKE Phase P02A avoids IEEE 754 in favor of exact rational arithmetic over $\mathbb{Q}$.
3. **Microsoft Win32 API Documentation:**
   - `CreateJobObjectW`, `SetInformationJobObject` (`JOBOBJECT_BASIC_LIMIT_INFORMATION`, `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`).
   - `CreateProcessW` (`CREATE_SUSPENDED`), `AssignProcessToJobObject`, `ResumeThread`.
4. **SemVer 2.0.0:** Semantic Versioning Specification for API schemas and multi-domain regression contracts.

---

## 3. Git Handoff Provenance

- **Origin Remote:** `https://github.com/PhanHoangKe/math-knowledge-engine.git`
- **Base Commit:** `af5e891e844e2be764a2987eeb3f321d026f0e2a` (Merge pull request #1 from PhanHoangKe/dev02a-method-knowledge-base)
- **Target Branch:** `docs/product01-review`
- **Scope of Handoff:** Documentation exclusively under `docs/product/product01/`. Zero mutations to existing code branches.
