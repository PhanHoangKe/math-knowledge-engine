# MKE PRODUCT-02A-S4-A Implementation Report

**Milestone:** Stable Protocol & Mathematical Dispatch (S4-A)  
**Branch:** `product/p02a-foundation`  
**Base Commit:** `608ca98002619432db4754df2351b3e44b06170f`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
**Protocol Contract:** `S4_PROTOCOL_CONTRACT.md`  
**Owner Decision Record:** `S3_OWNER_DECISION_RECORD.md` (`MKE-S3-ADR-001`)  
**Execution Agent:** Anty  
**Chief Architect & Auditor:** ChatGPT  
**Approval Authority:** Project Owner  

---

## 1. Overview & Architecture

Milestone S4-A implements a small, stable, versioned protocol and side-effect-free application dispatcher (`src/mke_product/protocol/`) over the accepted S0–S3 mathematical kernel:
- **Zero Network Exposure:** No socket listeners, HTTP servers, or external network dependencies.
- **Strict Decoupling:** Independent dispatch for `SOLVE` (S3) and `CHECK_CANDIDATE` (S2); mathematical solving and candidate verification are not coupled into a mandatory pipeline.
- **Exact Number Transport:** Numerical values (coefficients, roots, candidates, residuals) are serialized exclusively as decimal integer strings (`"numerator"`, `"denominator"`), eliminating floating-point rounding errors.
- **Strict Framing Validation:** Payload size, character length, field allowlists, and strict typing are validated BEFORE any AST parsing or mathematical execution.
- **Clear Outcome Separation:** Distinction between protocol framing errors (`PROTOCOL_ERROR`), mathematical syntax errors (`SYNTAX_ERROR`), invalid candidates (`INVALID`), and empty sets (`EmptySet`).
- **Three-Valued Definedness:** Explicit reporting of original-domain definedness on $\mathbb{R}$ (`true`, `false`, `null`).
- **Provisional Evidence Tier:** Structured evidence payloads are explicitly flagged as provisional inspection payloads (`is_provisional_evidence: true`), pending RFC 8785 canonicalization in future milestones.

### Protocol Package Components
- `errors.py`: Authoritative typed protocol errors (`ProtocolPayloadTooLargeError`, `ProtocolJsonDecodeError`, `ProtocolMissingFieldError`, `ProtocolUnexpectedFieldError`, `ProtocolInvalidTypeError`, `ProtocolUnsupportedVersionError`, `ProtocolUnknownOperationError`, `ProtocolInputLimitError`).
- `schema.py`: Constants (`SCHEMA_VERSION = "mke.p02a.v1"`, `OPERATIONS`), limits (4096 bytes, 256 characters), and exact rational decimal-string serializer (`serialize_rational`).
- `validator.py`: `parse_and_validate_raw_payload()` and `validate_request_dict()` enforcing strict JSON decoding, payload size limits, schema version matching, operation allowlists, and field type checking.
- `dispatcher.py`: `dispatch_request()` and `dispatch_json()` providing side-effect-free in-memory execution and response mapping.

---

## 2. Operational Dispatch & Response Taxonomy

### 2.1 Operation: `SOLVE`
- Equation string validated and parsed via S1 `parse_equation()`.
- Dispatched to S3 `solve_equation(equation_ast, budget=budget)`.
- Outcomes:
  * `SUCCESS`: `UNIQUE_ROOT`, `DomainSet(R)`, `EmptySet` (definedness `true`).
  * `DOMAIN_ERROR`: Proven constant undefinedness $1/0$, $0^0$ (definedness `false`).
  * `OUT_OF_SCOPE`: Non-linear, power-0, variable denominator terms (definedness `null`).
  * `RESOURCE_EXHAUSTED`: Operation or bit budget limit exceeded (definedness `null`).
  * `INTERNAL_VERIFICATION_FAILURE`: Root failed independent S2 certification (definedness `null`).

### 2.2 Operation: `CHECK_CANDIDATE`
- Equation string parsed via S1 `parse_equation()`.
- Candidate string validated against exact ASCII rational grammar.
- Dispatched to S2 `check_candidate(equation_ast, candidate_str, budget=budget)`.
- Outcomes:
  * `SUCCESS`: `VALID` (equality `true`, residual $0$), `INVALID` (equality `false`, exact rational residual).
  * `DOMAIN_ERROR`: Expression undefined at candidate (definedness `false`).
  * `RESOURCE_EXHAUSTED`: Budget limit exceeded (definedness `null`).
  * `UNSUPPORTED`: Expression outside evaluation capabilities (definedness `null`).

### 2.3 Protocol & Syntax Errors
- `PROTOCOL_ERROR`: Malformed JSON, missing/extra fields, non-string candidate (e.g. float `2.5` or bool `true`), payload > 4096 bytes, equation > 256 characters, unsupported version or operation.
- `SYNTAX_ERROR`: Unparseable mathematical syntax, unclosed parentheses, or invalid operators with accurate source span `[start, end]`.

---

## 3. RFC 8785 Canonical Evidence Roadmap

In compliance with the frozen design contract:
1. Current evidence payloads in S4-A are provisional diagnostic inspection payloads (`is_provisional_evidence: true`).
2. Production certificates require:
   - Implementation of RFC 8785 JSON Canonicalization Scheme (JCS) deterministic sorting and whitespace elimination.
   - SHA-256 canonical hashing of the resulting byte stream.
   - Immutable certificate schema freezing separating mathematical assertions from runtime diagnostics.
   - Digital cryptographic signatures (e.g. Ed25519) by an authorized key.

---

## 4. Security Boundary & Future Trust Architecture (S4-B / S4-C)

- S4-A is strictly an in-memory library; it exposes no HTTP listener and connects to no external networks.
- Future multi-process architecture:
  `Client -> S4-C API Host (framing checks) -> S4-B Sandboxed Worker (Win32 Job Object) -> S4-A Dispatcher -> S0-S3 Kernel`.
- Mandatory S4-B security controls (to be verified on Windows runtime in milestone S4-B):
  * `CREATE_SUSPENDED` worker launch assigned to Win32 Job Object before `ResumeThread`.
  * 256 MiB per-process / 512 MiB job-wide memory ceilings.
  * `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
  * Breakaway prevention (`JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK` disabled).
  * OS-enforced outbound network blocking (WFP / AppContainer).
  * Filesystem confinement (read-only binaries, scratch temp only).
  * Status: **PLANNED / UNVERIFIED** until S4-B implementation.

---

## 5. Test Suite & Reproducibility

### 5.1 Test Execution
Command:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Output:
```
Ran 227 tests in 0.045s

OK
```

### 5.2 Test Inventory (227 Total Tests)
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Linear Equation Solver (`tests/test_solver.py`):** 72 tests (31 baseline + 11 R1 + 25 R2 + 5 R3).
- **S4-A Protocol & Dispatcher (`tests/test_protocol.py`):** 43 tests (32 baseline + 11 S4-A-R1 regressions):
  - *SOLVE Operations (11 tests)*
  - *CHECK_CANDIDATE Operations (6 tests)*
  - *Validation, Security & Framing (15 tests)*
  - *S4-A-R1 Boundary Remediations (11 tests):*
    * `test_excessive_tokens_solve_caught_cleanly`: Equation <= 256 chars with > 64 tokens caught for SOLVE.
    * `test_excessive_tokens_check_candidate_caught_cleanly`: Equation <= 256 chars with > 64 tokens caught for CHECK_CANDIDATE.
    * `test_excessive_parenthesis_nesting_solve_caught_cleanly`: Parentheses nesting > 16 levels caught for SOLVE.
    * `test_excessive_parenthesis_nesting_check_candidate_caught_cleanly`: Parentheses nesting > 16 levels caught for CHECK_CANDIDATE.
    * `test_duplicate_json_keys_rejected`: Rejects duplicate JSON keys via `_reject_duplicate_keys_hook`.
    * `test_dict_input_size_limit_enforced`: Dict payload size limit ceiling (4096 bytes) enforced without unbounded serialization.
    * `test_non_string_dict_key_rejected`: Rejects non-string dict keys with `ERR_PROTOCOL_INVALID_TYPE`.
    * `test_excessive_json_nesting_rejected`: Handles excessive JSON nesting safely without uncaught recursion errors.
    * `test_candidate_whitespace_rejected_at_protocol_boundary`: Rejects candidate with surrounding or internal whitespace.
    * `test_response_size_limit_fails_closed`: Response exceeding `MAX_RESPONSE_BYTES` (16 KiB) fails closed with `ERR_RESPONSE_LIMIT_EXCEEDED` and `definedness: null`.
    * `test_syntax_error_definedness_null`: Ensures `SYNTAX_ERROR` returns `definedness: null`.

### 5.3 S4-A-R1 Remediation Summary
1. **Unhandled S1 Input Limits:** Dispatcher catches `MKEParserError` / `InputBoundsExceededError`, deterministically returning structured syntax errors with `definedness: null`.
2. **Strict Transport Validation:** Bounded dict input size calculation, duplicate JSON key rejection, non-string dict key rejection, candidate whitespace rejection.
3. **Definedness Semantics:** `SYNTAX_ERROR` produces `definedness: null`, reserving `false` solely for mathematical `DOMAIN_ERROR`.
4. **Response Bounds:** Enforced `MAX_RESPONSE_BYTES = 16384` ceiling, failing closed with `ERR_RESPONSE_LIMIT_EXCEEDED` and `definedness: null`.
5. **Documentation & Reproducibility:** Documented local loopback API host (`127.0.0.1` only) in `S4_PROTOCOL_CONTRACT.md`; added `sys.path.insert(0, ...)` to `tests/test_protocol.py`.

### 5.4 Holdout Dataset Isolation
The 227 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 6. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
