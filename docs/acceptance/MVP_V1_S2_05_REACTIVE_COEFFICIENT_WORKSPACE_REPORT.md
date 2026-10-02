# MKE MVP V1 — S2-05 REACTIVE COEFFICIENT WORKSPACE & REVISION FLOW REPORT

**Role:** Antigravity (“Anty”) — Implementation Engineer  
**Coordinator / Independent Auditor:** ChatGPT  
**Project Owner:** Kế Phan Hoàng  
**Repository:** `PhanHoangKe/math-knowledge-engine`  
**Date:** 2026-10-02  
**Target Milestone:** S2-05 Reactive Coefficient Workspace & Revision Flow  
**Branch:** `product/mvp-v1-s2-05-reactive-coefficients`  
**Parent Lineage:**
- Accepted S2-04 Baseline: `10b9317126f8d02ebd24a0681fe42b5205f4a594`
- Accepted S2-03 Baseline: `fecb6c23d01e90e010f76aed0446e0ed96cf35d9`
- Accepted S2-02 Backend/Transport Baseline: `6e96ebbe083677a69c69127bae6a57a24d11a674`
- Accepted S1 Baseline: `3058b6e904f38003a650a79105ae615226bdbc17`
- Parked B3 Baseline: `cdb73dd689eed30e326b6fd8ece2f7b8b4984a61` (Untouched)

---

## 1. Executive Summary

Stage S2-05 extends the deterministic React algebra workspace with live, reactive rational coefficient editing ($a, b, c$), bidirectional request provenance tracking, bounded in-memory session revision history, and tightened transport detail projections.

### Core Architectural Principles & Invariants Preserved
1. **Absolute Backend Mathematical Authority:** The browser performs zero mathematical solving, zero discriminant calculations, zero GCD or Euclidean algorithm reductions, zero root reconstruction, and zero certificate fabrication.
2. **Exact Rational Representation:** Fraction inputs (e.g. $2/4$) are preserved and transmitted unreduced to the backend as `{ numerator: 2, denominator: 4 }`. Denominators are strictly validated to be positive integers $\ge 1$.
3. **Reactive Debounce & Race Immunity:** Direct coefficient editing is debounced at a centralized constant of `350ms`. Monotonic sequence counters and `AbortController` cancellation ensure stale or out-of-order in-flight responses are immediately discarded without workspace corruption.
4. **Selected Method Reset UX Semantic:** Keystroke coefficient edits produce a newly defined mathematical revision and strictly send `selected_method_id: null`. Method switching explicitly retains latest backend canonical coefficients and sends the targeted `selected_method_id`.
5. **Bidirectional Provenance Tracking:** The workspace explicitly distinguishes between `RAW_TEXT` and `COEFFICIENTS` origin, updating reactive badges and revision metadata with full Vietnamese and English localization.
6. **Bounded In-Memory Session Revision History:** Maintains up to 15 unique mathematical problem revisions deduplicated by authoritative backend `semantic_revision_hash`. Users can inspect and restore previous workspace revisions seamlessly.
7. **Transport Detail Whitelist Hardening (Section 32):** Narrowed `TransportErrorPanel` scalar detail whitelisting to known context keys (`expected_content_type`, `max_bytes`, `actual_bytes`, `safe_expected_field`, `field`, `reason`, `path`), eliminating leakage of raw sentinels or duplicate error keys.

---

## 2. Architecture & Data Flow

```text
[ Raw Text Query ]                      [ Direct Coefficient Editor (a, b, c) ]
       │                                                   │
       │ (Immediate Submit)                                │ (Debounce: 350ms, selected_method_id = null)
       ▼                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    useAlgebraWorkspace State Machine                        │
│                                                                             │
│ - Request Origin: RAW_TEXT | COEFFICIENT_EDIT | METHOD_SWITCH               │
│ - Source Mode: RAW_TEXT | COEFFICIENTS                                      │
│ - Sequence Counter: Monotonic uint & AbortController                        │
│ - Bounded Session History: max 15 entries, deduplicated by revision hash    │
│ - Reactive Status: idle | debouncing | recomputing | invalid | updated      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼ (Relative Fetch /api/v1/algebra/solve)
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Vite Proxy -> FastAPI Transport                      │
│ - Raw Text: SolveRequest { input_mode: 'RAW_TEXT', raw_query: '...' }       │
│ - Coefficients: SolveRequest { input_mode: 'COEFFICIENTS', a, b, c }        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Pure S1 Math Backend                              │
│ - SolvedResponse (Quadratic) / AnalyzedNoExecutionResponse (Degenerate)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Frontend Atomic Workspace Hydration                        │
│ - CoefficientsDraft hydrated from authoritative backend problem view        │
│ - Solved / Degenerate layouts updated atomically                            │
│ - Bounded Session Revision Entry recorded & deduplicated                    │
│ - KaTeX offline math rendering (throwOnError: false, trust: false)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implemented Components & Modules

### A. Coefficient Utilities (`src/frontend/src/utils/coefficients.ts`)
- `validateIntegerString(input, mustBePositive)`: Validates integer lexical syntax (regex `/^-?\d+$/` or `/^\d+$/`), safe integer range `Number.isSafeInteger`, and positive denominator $\ge 1$.
- `validateCoefficientsDraft(draft)`: Validates all 6 numerator/denominator fields ($a, b, c$) without reducing fractions or altering signs.
- `draftToRationalPayload(draft)`: Converts valid string drafts into exact integer `{ numerator, denominator }` records.
- `hydrateDraftFromBackend(a, b, c)`: Authoritatively syncs draft inputs with backend canonical fractions.

### B. Coefficient Editor Panel (`src/frontend/src/components/CoefficientEditorPanel/`)
- 6 integer inputs with HTML5 `inputMode="numeric"`, explicit ARIA associations (`aria-describedby`), and localized labels.
- Live reactive status indicator (`debouncing`, `recomputing`, `updated`, `invalid`).
- Provenance badge (`Phiên bản đang chỉnh sửa theo hệ số` / `Coefficient-edited revision`).
- Reset button restoring inputs to backend canonical values.
- Informational notice when $a = 0$ explaining degenerate representation.

### C. Bounded Revision History Panel (`src/frontend/src/components/RevisionHistoryPanel/`)
- Displays up to 15 recent session problem revisions.
- Shows provenance badge (`RAW_TEXT` vs `COEFFICIENTS`), equation classification, and LaTeX preview.
- Includes `Khôi phục phiên bản` / `Restore revision` action button to restore historical parameters into the live workspace.
- Deduplicates consecutive entries sharing the same `semantic_revision_hash`.

### D. Transport Hardening (`src/frontend/src/components/TransportErrorPanel/`)
- Strict whitelist for scalar details: `['expected_content_type', 'max_bytes', 'actual_bytes', 'safe_expected_field', 'field', 'reason', 'path']`.
- Completely prevents duplicate top-level messages or sentinel leaks.

### E. AppShell & Workspace Integration (`src/frontend/src/components/AppShell/` & `useAlgebraWorkspace.ts`)
- Full bidirectional reactivity between equation input and coefficient editor.
- Provenance-aware error retries via `retryLastRequest()`.
- Unified sequence guards across keystrokes, query edits, clears, and unmount.

---

## 4. Verification & Test Evidence

### A. Frontend Verification Suite

| Test Suite | Tests | Result | Description |
|:---|:---:|:---:|:---|
| `coefficientEditor.test.tsx` | 5 | **PASS** | Validates safe integers, unreduced fractions ($2/4$), invalid inputs, hydration, and reset action. |
| `reactiveCoefficients.test.tsx` | 4 | **PASS** | Tests 350ms debounce, method switching with coefficient preservation, Quadratic $\leftrightarrow$ Degenerate transitions, and cancellation on query edit. |
| `revisionHistory.test.ts` | 3 | **PASS** | Tests monotonic recording, hash-based deduplication, and FIFO 15-entry bounding. |
| `revisionHistoryPanel.test.tsx` | 2 | **PASS** | Tests empty state rendering, item lists, provenance badges, and restore callback. |
| `frontendPurity.test.ts` | 1 | **PASS** | Static audit verifying zero client math, zero discriminant calculations, zero GCD, and zero fraction reduction across all production files. |
| `apiClient.test.ts` | 15 | **PASS** | Relative API client tests covering all status codes and network error paths. |
| `LiveWorkspace.test.tsx` | 15 | **PASS** | End-to-end component tests covering workspace layouts and interactions. |
| `workspaceState.test.ts` | 8 | **PASS** | Core workspace hook state machine tests. |
| `preferences.test.tsx` | 8 | **PASS** | Theme and locale persistence tests. |
| `i18n.test.ts` | 4 | **PASS** | Translation parity and placeholder validation. |
| `apiContract.test.ts` | 3 | **PASS** | Contract type validation and schema assertions. |
| `MathLatex.test.tsx` | 3 | **PASS** | Offline KaTeX rendering and delimiter stripping tests. |
| `App.test.tsx` | 7 | **PASS** | Full App shell rendering and localization tests. |
| **Total Frontend Tests** | **78** | **PASS** | **13/13 test files passed (100%)** |

### B. Type & Schema Verification
- `npm run check:api`: **PASSED** (Zero OpenAPI / TypeScript drift).
- `npm run typecheck`: **PASSED** (Both app and node tsconfigs compiled with 0 errors).
- `npm run build`: **PASSED** (Vite production bundle built cleanly in 1.23s).

### C. Backend & Legacy Browser UI Regressions
- `pytest tests/test_transport_fastapi_s2_smoke.py tests/test_transport_fastapi_s2_acceptance.py tests/test_browser_canonical_ui.py`: **170 PASSED** in 55.83s.
- `pytest tests/test_application_s1_acceptance.py`: **60 PASSED** in 0.47s.
- **Total Backend & Legacy Acceptance Tests:** **230 PASSED (100%)**.

---

## 5. Non-Regression & Scope Invariant Checklist

- [x] Backend source code (`src/mke_product/`) untouched.
- [x] S1 pure mathematical logic untouched.
- [x] FastAPI transport semantics untouched.
- [x] Legacy UI (`ui/ui00/`) untouched.
- [x] Historical evidence (`evidence/p03b/`) untouched.
- [x] Parked B3 baseline (`cdb73dd689eed30e326b6fd8ece2f7b8b4984a61`) untouched.
- [x] No client-side mathematical solvers, discriminants, GCDs, or fraction reductions added.
- [x] Zero new npm runtime dependencies introduced.

---

## 6. Conclusion & Recommendation

Stage S2-05 is complete, fully verified, and ready for audit review on branch `product/mvp-v1-s2-05-reactive-coefficients`.
