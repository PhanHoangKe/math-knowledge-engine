# MKE MVP V1 — S2-05-R1 REACTIVE COEFFICIENT WORKSPACE & REVISION FLOW REPORT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-02  
**Target Milestone:** S2-05-R1 Reactive Race, Provenance & Acceptance Closeout  
**Branch:** `product/mvp-v1-s2-05-reactive-coefficients`  
**Authoritative S2-05 Baseline Lineage:**
- Authoritative S2-05 Baseline HEAD: `aba7d60f3946ae5571cd9cc4d7ccee6411b1fc75`
- Accepted S2-04 Baseline: `10b9317126f8d02ebd24a0681fe42b5205f4a594`
- Accepted S2-03 Baseline: `fecb6c23d01e90e010f76aed0446e0ed96cf35d9`
- Accepted S2-02 Backend/Transport Baseline: `6e96ebbe083677a69c69127bae6a57a24d11a674`
- Accepted S1 Baseline: `3058b6e904f38003a650a79105ae615226bdbc17`
- Parked B3 Baseline: `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (Untouched)

---

## 1. Executive Summary & R1 Closeout Actions

Stage **S2-05-R1** delivers critical safety, race immunity, provenance preservation, and audit alignment for the live reactive algebra workspace:

1. **Authoritative Delivery Baseline SHA Fixed:** Recorded that the true remote S2-05 implementation commit audited by the coordinator is `aba7d60f3946ae5571cd9cc4d7ccee6411b1fc75`.
2. **Immediate Invalidation on Every Coefficient Edit:** On every coefficient keystroke (valid, invalid, empty, zero denominator, or unsafe integer), `useAlgebraWorkspace` cancels pending debounce, immediately increments `sequenceRef.current`, and aborts any active in-flight request. Stale late-arriving responses cannot overwrite newer drafts or corrupt workspace state.
3. **Strict Method Switch Provenance:** `METHOD_SWITCH` preserves the current `sourceMode` (`COEFFICIENTS` stays `COEFFICIENTS`, `RAW_TEXT` stays `RAW_TEXT`) and uses the newest backend canonical coefficients without re-derivation.
4. **Observational Revision History Only:** Removed all rollback/restore APIs, callbacks, and buttons. History serves as an immutable, bounded, in-memory observational log (maximum 15 entries) deduplicated across the entire session by `semantic_revision_hash`.
5. **Transport Detail Whitelist Aligned to Real Backend Contract:** Aligned safe whitelist to known context fields (`error_type`, `limit_bytes`, `declared_bytes`, `streamed_bytes_exceeded`, `header`, `reason`, `path`, `status_code`, `validation_errors`), strictly excluding raw request inputs (`received_content_type`) and secrets.
6. **Error Reactive Status Truthfulness:** Set `reactiveStatus = 'error'` on network/transport failure during coefficient editing, preserving the last accepted backend problem revision while retaining the user draft.

---

## 2. Architecture & Data Flow

```text
[ Raw Text Input ]                             [ Direct Rational Editor (a, b, c) ]
       │                                                       │
       │ (Immediate Submit)                                    │ (Every edit: cancel debounce, bump seq, abort in-flight)
       ▼                                                       ▼ (Debounce 350ms, selected_method_id = null)
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           useAlgebraWorkspace State Machine                             │
│                                                                                         │
│ - Request Origin: RAW_TEXT | COEFFICIENT_EDIT | METHOD_SWITCH                           │
│ - Source Mode: RAW_TEXT | COEFFICIENTS (preserved during METHOD_SWITCH)                 │
│ - Sequence Counter: Monotonic uint & AbortController (immediate race guard)             │
│ - Bounded Session History: max 15 entries, deduplicated across entire history by hash   │
│ - Reactive Status: idle | debouncing | recomputing | invalid | updated | error          │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼ (Relative Fetch /api/v1/algebra/solve)
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               Vite Proxy -> FastAPI Transport                           │
│ - Raw Text: SolveRequest { input_mode: 'RAW_TEXT', raw_query: '...' }                   │
│ - Coefficients: SolveRequest { input_mode: 'COEFFICIENTS', a, b, c }                    │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                Pure S1 Mathematical Service                             │
│ - SolvedResponse (Quadratic) / AnalyzedNoExecutionResponse (Degenerate)                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Verification & Acceptance Evidence

### A. Frontend Verification Suite

| Test Suite | Tests | Result | Coverage Description |
|:---|:---:|:---:|:---|
| `reactiveCoefficients.test.tsx` | 10 | **PASS** | Valid edit stale request rejection, invalid edit stale request rejection, $c=6 \to 7$ exact request, debounce restart ($6 \to 7 \to 8 \to 9$), fractional unreduced payload, Degenerate $\leftrightarrow$ Quadratic transitions, method switch provenance, debounce cancellations, and retry provenance. |
| `revisionHistory.test.ts` | 2 | **PASS** | Monotonic recording, entire-history hash deduplication ($A \to B \to A$), method switch deduplication, and 15-entry FIFO bounding directly through `useAlgebraWorkspace`. |
| `revisionHistoryPanel.test.tsx` | 2 | **PASS** | Observational rendering, empty state, provenance badges, and assertion that zero rollback/restore buttons exist. |
| `TransportErrorPanel.test.tsx` | 3 | **PASS** | Structured 422 `validation_errors`, safe scalar fields (`limit_bytes`, `reason`, `path`, `status_code`), and complete DOM exclusion of injected secrets. |
| `coefficientEditor.test.tsx` | 5 | **PASS** | Safe-integer lexical regex, positive denominator checks, unreduced fraction preservation ($2/4$), and hydration. |
| `frontendPurity.test.ts` | 1 | **PASS** | Static audit verifying zero client math, zero discriminant formulas, zero GCD, and zero fraction reduction. |
| `apiClient.test.ts` | 15 | **PASS** | Relative API client tests covering all status codes and network error paths. |
| `LiveWorkspace.test.tsx` | 15 | **PASS** | Component workspace integration, method switching, loading states, and error panels. |
| `workspaceState.test.ts` | 8 | **PASS** | Workspace hook state machine transitions. |
| `preferences.test.tsx` | 8 | **PASS** | Theme and locale persistence. |
| `i18n.test.ts` | 4 | **PASS** | Translation key parity and interpolation. |
| `apiContract.test.ts` | 3 | **PASS** | OpenAPI DTO type validation. |
| `MathLatex.test.tsx` | 3 | **PASS** | Offline KaTeX rendering and security flags. |
| `App.test.tsx` | 7 | **PASS** | App shell rendering and default Vietnamese atmospheric branding. |
| **Total Frontend Tests** | **86** | **PASS** | **14/14 test files passed (100%)** |

### B. Type & Schema Verification
- `npm run check:api`: **PASSED** (OpenAPI schema and generated TypeScript types in 100% sync).
- `npm run typecheck`: **PASSED** (0 errors across app and node configurations).
- `npm run build`: **PASSED** (Production bundle built in 1.07s).

### C. Backend Full S1/S0 & Transport Regressions
- **Full S1/S0 Mathematical Service Gate:**
  `pytest -q tests/test_application_s1_acceptance.py tests/test_application_orchestrator_s1.py tests/test_application_traces_s1.py tests/test_application_degenerate_s1.py tests/test_application_normalizer_s1.py tests/test_domain_core_s0.py`
  **Result:** `278 passed in 1.05s` (100% pass).
- **Transport Smoke & Acceptance Gate:**
  `pytest -q tests/test_transport_fastapi_s2_smoke.py tests/test_transport_fastapi_s2_acceptance.py`
  **Result:** `149 passed in 4.73s` (100% pass).
- **Legacy Browser UI Acceptance Gate:**
  `pytest -q tests/test_browser_canonical_ui.py`
  **Result:** `21 passed in 49.24s` (21/21 passed).
- **Total Backend & Legacy Acceptance Tests:** **448/448 PASSED (100%)**.

### D. Live Proxy Observed Evidence (127.0.0.1:5173 ➔ 127.0.0.1:8000)
1. **RAW_TEXT Query (`x^2 - 5*x + 6 = 0`):**
   - Status: `SOLVED` | Problem Type: `QUADRATIC`
   - Hash: `a90c7685c251fead21937972b8d21edc3a7c43bf84d70eeb3fab935e3cf80761`
2. **COEFFICIENTS Direct Edit ($c=7$, `selected_method_id: null`):**
   - Status: `SOLVED` | Problem Type: `QUADRATIC`
   - Hash: `cd037df717cabab510e002895246181684ba6d6a67ad1b32b61f7989072e42f5` (Distinct from initial raw solve)
3. **DEGENERATE Transition ($a=0, b=2, c=-4$):**
   - Status: `ANALYZED_NO_EXECUTION` | Reason Code: `DEGENERATE_EXACT_SOLUTION` | Problem Type: `DEGENERATE`
   - Hash: `de4bff83d58457c17bd06aad4a1609ae008bdbf7aa7fe0d05bd5ae60035941c5`
4. **METHOD_SWITCH ($c=7$, `selected_method_id: 'QUAD_COMPLETE_SQUARE'`):**
   - Status: `ANALYZED_NO_EXECUTION` | Reason Code: `ANALYZED_NO_EXECUTION`
   - Hash: `cd037df717cabab510e002895246181684ba6d6a67ad1b32b61f7989072e42f5` (Hash strictly preserved across method switches).

---

## 4. Documentation Erratum Note

As noted in Section 26, the term `EQUATION_STRUCTURE_ERROR` mentioned in earlier S2-04 documentation was descriptive wording only and is **NOT** a backend `ApplicationErrorCode` or part of the OpenAPI schema.

---

## 5. Scope Invariants Checklist

- [x] Backend source code (`src/mke_product/`): **UNTOUCHED**
- [x] S1 pure mathematical logic: **UNTOUCHED**
- [x] FastAPI transport semantics: **UNTOUCHED**
- [x] Legacy UI (`ui/ui00/`): **UNTOUCHED**
- [x] Historical evidence (`evidence/p03b/`): **100% IMMUTABLE & RESTORED**
- [x] Parked B3 baseline (`cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`): **UNTOUCHED**
- [x] Zero client-side mathematical derivations, GCD calculations, or fraction reductions.
- [x] Zero new npm runtime dependencies.
