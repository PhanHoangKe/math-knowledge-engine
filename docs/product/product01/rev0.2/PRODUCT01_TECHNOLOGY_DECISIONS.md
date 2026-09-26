# PRODUCT-01 — Technology decisions draft

Status: DRAFT, revision 0.2, 2026-09-26. Recommendations subject to owner approval and version-specific integration gates.

## Evaluation basis

Official project documentation, source licenses, and vendor terms were consulted on 2026-09-26. Links below are the web evidence inventory; pages on moving branches or "latest" documentation are not immutable release evidence. No packages were installed or executed during PRODUCT-01.

The legacy repository declares Python >=3.10, SymPy 1.14.0, Pydantic 2.13.5, Typer 0.25.1, Rich 13.9.4 and optional pytest 9.1.1. Historical closure evidence records Python 3.12.14 and mpmath 1.3.0 as well. Proposed Product baseline: evaluate a supported Python 3.12 patch with pinned SymPy 1.14.0 as the first compatibility candidate; resolve security/compatibility and lock all transitive dependencies before implementation acceptance. No automatic upgrade of the accepted baseline.

## Proposed decisions

### T01 — React and TypeScript: adopt provisionally for the local interface

- **Required capability:** Stateful editor, interpretation comparison, method cards, job status and evidence inspection. React provides component/state composition; TypeScript improves contract maintenance but does not validate runtime messages. A client application served by the local API is sufficient; server-side rendering is unnecessary.
- **Installation/runtime:** Node/package manager for a pinned frontend build; a supported modern browser for runtime. Budget a modest local build process and browser memory, to be measured. No per-call license charge. React is MIT and TypeScript Apache-2.0; distribution must retain required notices. [React TypeScript guide](https://react.dev/learn/typescript), [React license](https://github.com/react/react/blob/main/LICENSE), [TypeScript license](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt).
- **Integration:** Generate or maintain explicit API types alongside runtime schema checks; avoid passing large symbolic trees repeatedly through UI state. Fallback is a plain-text editor and accessible result tables, not a second framework.

### T02 — FastAPI, Pydantic and Uvicorn: adopt provisionally for the local boundary

- **Required capability:** Local HTTP/JSON and WebSocket communication between the browser interface and calculation backend; typed request validation and serialization.
- **Security & Binding Constraints:**
  - Must bind strictly to loopback IPv4 `127.0.0.1` (never `0.0.0.0`).
  - Generate an ephemeral 32-byte session authentication token at startup, requiring an `X-MKE-Session-Token` header on all requests to prevent cross-site request forgery (CSRF) from other browser tabs.
  - Strict CORS policy restricting origins exclusively to `http://127.0.0.1:<port>`.
- **License & References:** FastAPI and Uvicorn are BSD-3-Clause; Pydantic is MIT. [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/), [Pydantic documentation](https://docs.pydantic.dev/).

### T03 — SymPy: adopt as a bounded symbolic proposal engine

- **Required capability:** Algebraic expansion, polynomial reduction, and symbolic manipulation for solver engines.
- **CRITICAL SECURITY REQUIREMENT (Prohibition of `parse_expr`):**
  - **Vulnerability Note:** Official SymPy documentation confirms that `sympy.parsing.sympy_parser.parse_expr` internally relies on Python's `eval()` function: *"The code is evaluated using Python's eval function"* ([SymPy 1.14.0 documentation](https://docs.sympy.org/latest/modules/parsing.html)). Passing untrusted user strings to `sympy.parse_expr` is strictly prohibited.
  - **Enforcement:** MKE must use its own restricted, allowlisted AST parser. Conversion to SymPy occurs exclusively via safe, explicit constructors (`Integer`, `Rational`, `Symbol`, `Add`, `Mul`, `Pow`). Direct string parsing by SymPy is disallowed.
- **Verification Decoupling:** SymPy's solver outputs are treated as **unverified proposals**. Verification obligations are independently evaluated by dedicated checkers using pure exact arithmetic (`fractions.Fraction`) and AST substitution, without relying on SymPy's internal solver flags.
- **License:** SymPy is BSD-3-Clause. [SymPy license](https://github.com/sympy/sympy/blob/master/LICENSE).

### T04 — mpmath: adopt for approximate views; do not use as proof

- **Required capability:** High-precision decimal rendering for user inspection (e.g. 20 and 50 decimal digits).
- **Contract Boundary:** mpmath evaluations are strictly labeled as convenience numerical approximations (`ApproximateSet`), with uncertified rounding caveats. Numerical evaluations can never upgrade an unverified symbolic claim to `VERIFIED`.
- **License:** mpmath is BSD-3-Clause. [mpmath documentation](https://mpmath.org/doc/current/).

### T05 — SciPy and NumPy: defer to numerical expansion

- **Decision:** Excluded from PRODUCT-02A and R1. Evaluate during R2 numerical expansion for bracketed root finding and linear algebra.
- **License:** NumPy and SciPy are BSD-3-Clause.

### T06 — MathLive: adopt provisionally for input and math display

- **Required capability:** Interactive mathematical formula editing and accessible LaTeX rendering in the browser.
- **Constraints:** MathLive's exported LaTeX string is treated as unvalidated input. It is parsed through MKE's restricted AST parser; no raw LaTeX commands or macro expansions are executed.
- **License:** MathLive is MIT. [MathLive repository](https://github.com/arnog/mathlive).

### T07 — Pix2Text: conditional candidate for R2; disabled by default

- **Required capability:** Formula OCR from images/PDFs.
- **Licensing & Governance Analysis:**
  - The Pix2Text library code is released under Apache-2.0.
  - However, the underlying deep learning model weights used by Pix2Text and its dependencies (e.g. CnOCR, CnSTD) have distinct licensing terms. Some model weights carry non-commercial restrictions, research-only licenses, or require attribution.
- **Decision:** Automated OCR is strictly **DISABLED** in PRODUCT-01 and PRODUCT-02A. R1 supports only manual image/PDF crop and transcription. Any activation of Pix2Text in R2 requires:
  1. Complete licensing audit of specific downloaded model weights.
  2. Air-gapped, offline execution validation.
  3. Mandatory user confirmation of every proposed transcription before solving.
- **References:** [Pix2Text documentation](https://pix2text.readthedocs.io/), [Breezedeus Pix2Text repository](https://github.com/breezedeus/pix2text).

### T08 — PDF.js: adopt provisionally for bounded source preview

- **Required capability:** Displaying PDF pages in the browser to allow users to select and crop printed formulas.
- **Security Constraints:**
  - Executed inside a sandboxed iframe (`sandbox="allow-scripts"`).
  - Script execution, external link navigation, and form actions within the PDF are disabled.
  - Strict input ceilings: Maximum 10 pages, maximum 20 MiB file size.
  - Client-side Web Worker rasterization with a 5.0-second timeout to prevent renderer lockup.
- **License:** Apache-2.0. [PDF.js repository](https://github.com/mozilla/pdf.js).

### T09 — SQLite, JSON/JSONL and native plotting: adopt

- **Required capability:** Local persistence for problem records, calculation evidence, and the versioned method knowledge base.
- **Decision:** SQLite for indexed query of method records and saved problems; JSON/JSONL for immutable evidence export and reproducible calculation archives. Native SVG / Canvas rendering for 2D plots.
- **License:** SQLite is Public Domain.

### T10 — Wolfram APIs: optional, disabled pending commercial and provenance decisions

- **Status:** Prohibited in PRODUCT-02A and R1. Any future remote CAS connectivity must be user-opt-in, require user-supplied credentials, and run strictly through a rate-budgeted local proxy.

### T11 — Lean 4/mathlib: optional narrow proof extension

- **Status:** Deferred to future formal proof expansion gates. Requires dedicated isolated runner and strict theorem-mapping validation.

### T12 — Optional LLM: provider-neutral, off by default

- **Status:** Disabled by default. May be evaluated in R2 strictly for explanatory text generation; LLM outputs have zero write access to mathematical verification fields or evidence statuses.

## Resource and cost planning

| Component | Proposed Baseline | Licensing | Memory / CPU Budget | Local Cost |
|---|---|---|---|---|
| Runtime | Python 3.12 (pinned) | PSF License | 128 MB baseline host | $0.00 |
| Symbolic Engine | SymPy 1.14.0 (pinned) | BSD-3-Clause | Inside 512 MB worker cap | $0.00 |
| Numerical Engine | mpmath 1.3.0 (pinned) | BSD-3-Clause | Inside worker cap | $0.00 |
| Backend Framework| FastAPI / Uvicorn | BSD-3-Clause | ~80 MB baseline | $0.00 |
| Frontend | React + MathLive | MIT | Browser tab budget | $0.00 |
| Storage | SQLite + JSONL | Public Domain | Disk bound by user records | $0.00 |

## Alternatives and rejected defaults

1. **Rejected: Direct use of `sympy.parse_expr`:** Rejected due to inherent remote code execution vulnerability (`eval`). Replaced by custom allowlisted parser.
2. **Rejected: Full Electron bundle for R1:** Rejected in favor of lightweight local browser UI served over loopback, reducing distribution footprint and attack surface.
3. **Rejected: Automatic OCR solving:** Rejected due to transcription error rates and model licensing ambiguities. Replaced by mandatory manual confirmation.
4. **Rejected: Automatic repository cleanups (`git clean`):** Rejected to prevent data loss of historical audit trails and research artifacts.

## Evidence completeness and remaining dependency work

Prior to gate G2 (PRODUCT-02A acceptance), a complete locked dependency manifest (`poetry.lock` or `requirements.txt` with SHA-256 hashes) must be established and independently audited for licensing compliance and zero vulnerability alerts.
