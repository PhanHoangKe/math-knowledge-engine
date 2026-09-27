# MKE Architecture Decision Record (ADR)

**Decision ID:** MKE-S3-ADR-001  
**Title:** Precedence of Proven Constant-Domain Errors over Exponent-Zero Scope Abstention  
**Status:** Approved  
**Authority:** Explicit Project Owner Approval  
**Date:** 2026-09-27  
**Branch:** `product/p02a-foundation`  
**Milestone:** MKE PRODUCT-02A-S3-R2  

---

## 1. Context & Specification Tension

During the mathematical audit of Milestone S3 (Exact Linear Equation Solver), a normative tension was identified when an equation simultaneously contains both a variable-dependent base raised to power zero (e.g., $x^0$) and a mathematically provable constant-domain undefinedness (e.g., $1/0$ or $0^0$):

1. **FREEZE_ADDENDUM.md (§3.1):** Mandates that any expression containing a variable-dependent base raised to the power of zero (such as $x^0$, $(x-1)^0$, or $0 \cdot x^0$) must be classified as `OUT_OF_SCOPE_FOR_SOLVER` prior to algebraic reduction, and the solver must abstain immediately with error code `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO` (Precedence #1).
2. **PRODUCT01_PRD.md (§2, Fig 2) & Verification Contract:** Mandates that definedness validation precedes algebraic solving. Expressions containing mathematically undefined original constant terms (such as division by zero $1/0$ or indeterminate form $0^0$) must be rejected with typed domain failure `DOMAIN_ERROR` (`DOMAIN_ERROR_DIVISION_BY_ZERO`, `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`) rather than being treated as well-formed equations.

---

## 2. Decision

The Project Owner has explicitly ruled on Option A:

> **Proven original constant-domain undefinedness takes precedence over variable-dependent exponent-zero solver abstention.**

When an unreduced equation AST contains both a provable constant-domain violation and a variable-dependent exponent zero term:
- The solver preflight inspection MUST classify the equation as `SolverScopeStatus.DOMAIN_ERROR` with the appropriate typed error code (`DOMAIN_ERROR_DIVISION_BY_ZERO` or `DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO`).
- Scope abstention (`OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO`) is subordinate to proven constant-domain undefinedness.

---

## 3. Rationale

Mathematically provable constant undefinedness (e.g. $1/0$, $0^0$) renders the expression ill-formed over $\mathbb{R}$. Masking a fatal domain error behind an engine scope abstention code would misrepresent an ill-defined mathematical object as a well-defined equation that is merely outside the solver's feature set. Constant undefinedness is an absolute failure of mathematical definedness on $\mathbb{R}$, which must be reported with precision.

---

## 4. Applicability & Unchanged Rules

1. **Applicability:** This decision applies strictly to the S3 `SOLVE` branch preflight hazard classification for mixed-hazard equations containing both constant-domain violations and out-of-scope terms.
2. **Unchanged Rule:** Any equation containing a variable-dependent base raised to power zero ($x^0$, $(x-1)^0$, $0 \cdot x^0$), where NO provable constant-domain failure exists, returns `OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO` with binding precedence over other out-of-scope conditions (such as rational fractions or non-linear terms).
3. **Deterministic Tie-Break Policy for Multiple Domain Errors:** When an equation contains multiple independent constant-domain violations (e.g., $1/0 + 0^0 = 0$ vs. $0^0 + 1/0 = 0$):
   - The result category is guaranteed to be `SolverScopeStatus.DOMAIN_ERROR`.
   - The reported error code and source span deterministically correspond to the first domain error encountered in AST pre-order traversal order (left-to-right).
   - Reordering operands preserves the category `DOMAIN_ERROR`, while the specific subcode reflects the leftmost encountered violation.

---

## 5. Formal Limitations & Frozen Document Status

- **Implementation Clarification:** This record constitutes an approved implementation clarification and binding ruling for the Product branch.
- **Frozen Documents Untouched:** This record does NOT modify `FREEZE_ADDENDUM.md`, `rev0.3.1` documents, documentation branches, or their historical git commits.
- **Future Reconciliations:** Any future synchronization or modification of the frozen normative specifications requires separate, explicit Project Owner authorization.
