# PRODUCT-01 Capability Matrix: Math Knowledge Engine (MKE)

**Document Version:** 0.3.1 (Targeted Remediation - Final Specification Freeze)  
**Status:** Under Review  
**Author:** Anty (Implementation Agent)  
**Reviewer:** ChatGPT (Chief Architect & Independent Reviewer)  
**Approval Authority:** Project Owner  
**Date:** September 2026  

---

## 1. Domain Specification & Capability Architecture

MKE evaluates equations whose variable belongs to the **Real domain $\mathbb{R}$**, with input coefficients restricted to the **Rational numbers $\mathbb{Q}$**. 

### 1.1 Independent Operational Branches
Unlike rigid sequential pipelines, MKE separates algebraic solving from candidate verification into independent functional branches:

| Capability Branch | Scope in Phase P02A | Behavior on Bounded $x^2$ | Behavior on Rational Fractions |
| :--- | :--- | :--- | :--- |
| **SOLVE** | Affine linear equations: $ax + b = 0$ ($a, b \in \mathbb{Q}$). Returns unique root $x = -b/a$, `DomainSet(R)` for $0x=0$, or `EmptySet` for $0x=c$. | **Abstains:** Returns `OUT_OF_SCOPE_NONLINEAR`. | **Abstains:** Returns `OUT_OF_SCOPE_RATIONAL_FRACTION`. |
| **CHECK_CANDIDATE** | Evaluates exact candidate $c \in \mathbb{Q}$ against original equation $L(x) = R(x)$. | **Evaluates:** Substitutes $c$ into quadratic AST, verifies $|L(c) - R(c)| = 0$. | **Evaluates:** Validates original domain ($Denom(c) \neq 0$). If valid, evaluates $|L(c) - R(c)| = 0$. |

---

## 2. Release-by-Release Capability Matrix

| Feature / Area | Phase P02A (Linear Foundation) | Release 1 (Algebra Workbench) | Release 2 (Classroom & Manual Ingestion) | Long-Term Proposal Only |
| :--- | :--- | :--- | :--- | :--- |
| **Equation Classes (SOLVE)** | Affine linear ($ax + b = 0$ over $\mathbb{R}$) | Quadratic ($ax^2 + bx + c = 0$), multi-step linear | Systems of 2-3 linear equations, piecewise linear | Polynomials, General Non-linear |
| **Verification Scope (CHECK)** | Linear, bounded $x^2$, and rational equations | Quadratic, systems verification | Systems, piecewise candidate validation | General analytic verification |
| **Coefficient Domain** | Exact Rational $\mathbb{Q}$ | Exact Rational $\mathbb{Q}$, finite decimals | Radicals $\sqrt{d}$ (quadratic extensions) | Complex numbers $\mathbb{C}$, Approximations |
| **Document Ingestion** | None (ASCII / Unicode math strings) | None (MathJSON, basic LaTeX) | Separately gated manual PDF/image ingestion | Automated OCR pipeline (requires separate gate) |
| **User Interface** | CLI / stdio, Local loopback HTTP testbed | Local Web UI, Single-user desktop packaging | Classroom batch grading interface | Multi-user Cloud SaaS |
| **Process Sandboxing** | Win32 Job Object (256 MiB proc / 512 MiB job) | Sandboxed worker pool | Containerized local daemons | Microvm / Firecracker cloud isolation |

---

## 3. Mathematical Edge Cases & Solution Taxonomy

| Equation Form | Condition | Solver Output | Verification (`CHECK_CANDIDATE`) for candidate $c$ |
| :--- | :--- | :--- | :--- |
| $ax + b = 0$ | $a \neq 0, a, b \in \mathbb{Q}$ | Unique root: $x = -b/a \in \mathbb{Q}$ | `VALID` if $c = -b/a$, else `INVALID` |
| $0 \cdot x = 0$ | $a = 0, b = 0$ | `DomainSet(R)` (Identity over $\mathbb{R}$) | `VALID` for any $c \in \mathbb{Q}$ |
| $0 \cdot x + b = 0$ | $a = 0, b \neq 0$ | `EmptySet` (Inconsistent / No Solution) | `INVALID` for any $c \in \mathbb{Q}$ |
| $\frac{x^2 - 1}{x - 1} = 0$ | Rational fraction | `OUT_OF_SCOPE_RATIONAL_FRACTION` | $c = 1 \implies$ `DOMAIN_ERROR_DIVISION_BY_ZERO`; $c = -1 \implies$ `VALID` |
| $x^2 - 4 = 0$ | Bounded quadratic | `OUT_OF_SCOPE_NONLINEAR` | $c = 2, -2 \implies$ `VALID`; $c = 3 \implies$ `INVALID` |
