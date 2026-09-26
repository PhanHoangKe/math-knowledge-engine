# Phase PRODUCT-02A Implementation Authorization Proposal

**Document Version:** 1.1  
**Target Phase:** Phase P02A — Exact Linear Foundation & Win32 Sandbox  
**Governance State:** PROPOSAL ONLY — STRICTLY UNAUTHORIZED UNTIL OWNER APPROVAL  
**Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Governance Notice

> [!CAUTION]
> **PHASE PRODUCT-02A IMPLEMENTATION IS CURRENTLY NOT AUTHORIZED.**  
> Zero implementation code, test execution, or harness runs may take place until the Project Owner explicitly approves Revision 0.3.1 and authorizes the sibling workspace.

---

## 2. Bounded Scope for Phase P02A

1. **Mathematical Scope:** Affine linear equations ($ax + b = 0$) over Real domain $\mathbb{R}$ with rational coefficients $\mathbb{Q}$. Returns exact $-b/a$, `DomainSet(R)` for $0x=0$, or `EmptySet` for $0x=c$.
2. **Authoritative Grammar:** Single variable `x`, explicit multiplication required (`*`), exponents $\in \{0, 1, 2\}$. Bounded $x^2$ and rational expressions parsed for candidate checking.
3. **Independent `CHECK_CANDIDATE`:** Validates candidate $c \in \mathbb{Q}$ against original domain (rejecting division by zero in unreduced expressions) and confirms $|L(c) - R(c)| == 0$.
4. **Win32 Job Object Execution:** Sandboxed worker with 256 MiB per-process limit and 512 MiB job-wide limit. Outbound egress blocked.
5. **Workspace:** Isolated in `../mke-product`.
