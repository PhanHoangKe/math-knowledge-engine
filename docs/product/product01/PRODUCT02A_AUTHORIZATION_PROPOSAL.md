# Phase PRODUCT-02A Implementation Authorization Proposal

**Document Version:** 1.0  
**Target Phase:** Phase P02A — Exact Linear Kernel & Win32 Sandbox  
**Governance State:** PROPOSAL ONLY — STRICTLY UNAUTHORIZED UNTIL OWNER APPROVAL  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Executive Notice & Implementation Status

> [!CAUTION]
> **PHASE PRODUCT-02A IMPLEMENTATION IS CURRENTLY NOT AUTHORIZED.**  
> Neither implementation source code, test execution, nor project harness runs may commence until the Project Owner provides written, explicit authorization based on this proposal and the approval of Revision 0.3 specifications.

---

## 2. Proposed Scope of Work (Phase P02A)

Upon receiving explicit Project Owner authorization, Phase P02A will execute under the following strictly bounded constraints:

### 2.1 Deliverables
1. **P02A Lexer & Parser:** Conforming strictly to the EBNF grammar defined in `PRODUCT01_VERIFICATION_CONTRACT.md` §2.1. Strictly single variable `x`, exact rational coefficients, non-negative integer exponents $\in \{0, 1\}$, explicit rejection of implicit multiplication.
2. **Pre-simplification Structural Guard:** Rejection of expressions with variables in denominators (`OUT_OF_SCOPE_RATIONAL_FRACTION`).
3. **Exact $\mathbb{Q}$ Linear Solver:** Deterministic reduction to $ax + b = 0$ and computation of root $x = -b/a$ via `fractions.Fraction`.
4. **Independent Verifier:** Exact rational substitution verification evaluating $L(c) - R(c) = 0$.
5. **Win32 Job Object Execution Wrapper:** Hardened process sandboxing with suspended creation, memory quota (256 MB), breakaway disabled, and network isolation.
6. **Offline Test Suite:** Complete implementation of the 80 Development Test Cases across the 5 specified families.

### 2.2 Strict Invariants & Non-Goals
- **Zero Ingestion OCR:** No integration of Pix2Text, PyMuPDF, or image processing.
- **Zero WebSockets:** No stateful WebSocket implementations; CLI and local HTTP POST only.
- **No Quadratic/Non-Linear Solvers:** Equations with degree $> 1$ or multiple variables terminate with deterministic `OUT_OF_SCOPE` errors.

---

## 3. Workspace Isolation Proposal

To guarantee zero regression or accidental modification of the frozen repository baseline:
- Implementation will take place in the external sibling workspace:  
  `../mke-product/` (or relative path approved by the Project Owner).
- The root repository `PhanHoangKe/math-knowledge-engine` will remain frozen at branch `dev02a-method-knowledge-base` / `docs/product01-review`.

---

## 4. Proposed Authorization Directive Template

For convenience, the Project Owner may authorize Phase P02A by executing the following directive:

```text
PROJECT OWNER DIRECTIVE: PRODUCT-02A AUTHORIZATION
- Revision 0.3 Specifications: APPROVED (FINAL CONTRACT FREEZE)
- Workspace Location: APPROVED at ../mke-product
- Scope: Bounded Phase P02A Exact Linear Kernel & Win32 Sandbox ONLY
- Execution: 80 Development test cases authorized; 80 Holdout cases remain SEALED
- Core Repository: STRICTLY FROZEN
```
