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
Ran 216 tests in 0.026s

OK
```

### 5.2 Test Inventory (216 Total Tests)
- **S0 Rational Core (`tests/test_rational.py`):** 24 tests.
- **S1 Parser & Immutable AST (`tests/test_parser.py`):** 41 tests.
- **S2 Semantic Evaluation & Verification (`tests/test_evaluator.py`):** 47 tests.
- **S3 Linear Equation Solver (`tests/test_solver.py`):** 72 tests (31 baseline + 11 R1 + 25 R2 + 5 R3).
- **S4-A Protocol & Dispatcher (`tests/test_protocol.py`):** 32 tests:
  - *SOLVE Operations (11 tests):*
    * `test_solve_unique_root`: `2*x+3=7` differential verification against S3.
    * `test_solve_fractional_coefficients`: `(1/2)*x + (3/4) = 0` $\implies x = -3/2$.
    * `test_solve_domain_set_r`: `x = x` identity.
    * `test_solve_domain_set_r_constant_identity`: `1 = 1` identity.
    * `test_solve_empty_set_constant_contradiction`: `1 = 2` contradiction.
    * `test_solve_empty_set_zero_times_x_equals_constant`: `0*x = 5` contradiction.
    * `test_solve_nonlinear_scope_abstention`: `x^2 - 4 = 0`.
    * `test_solve_variable_exponent_zero_abstention`: `x^0 = 1`.
    * `test_solve_mixed_hazard_owner_ruling_a`: Owner Decision ADR-001 ($x^0 + 1/0 = 0$, $1/0 + x^0 = 0$, $x^0 + 0^0 = 0$).
    * `test_solve_resource_exhausted`: Budget exhaustion produces `RESOURCE_EXHAUSTED` and `definedness: null`.
    * `test_solve_syntax_error`: Syntax error reporting with span.
  - *CHECK_CANDIDATE Operations (6 tests):*
    * `test_candidate_valid`: `(x-1)/(x-1)=1` with candidate `"2"`.
    * `test_candidate_invalid`: `2*x=4` with candidate `"3"` (residual 2).
    * `test_candidate_domain_error_division_by_zero`: `(x-1)/(x-1)=1` with candidate `"1"`.
    * `test_candidate_domain_error_zero_to_zero`: `x^0=1` with candidate `"0"`.
    * `test_candidate_tiny_nonzero_rational_residual`: $x = 1/7$ with candidate `"1/5"` (residual $2/35$).
    * `test_candidate_resource_exhausted`: Budget exhaustion produces `RESOURCE_EXHAUSTED`.
  - *Validation, Security & Framing (15 tests):*
    * `test_unsupported_protocol_version`: Rejects `"mke.p02a.v2"`.
    * `test_unsupported_operation`: Rejects unknown operations (`"INTEGRATE"`).
    * `test_missing_required_fields`: Enforces presence of all required fields.
    * `test_unexpected_extra_fields`: Strict allowlist rejection of extra fields.
    * `test_invalid_types_on_solve`: Type checking on all fields.
    * `test_json_float_candidate_rejected`: Rejects JSON floats (e.g. `2.5`).
    * `test_json_bool_candidate_rejected`: Rejects JSON booleans (e.g. `True`).
    * `test_json_null_candidate_rejected`: Rejects JSON `null`.
    * `test_malformed_candidate_string_rejected`: Rejects `"abc"`, `"02"`, `"1/0"`.
    * `test_oversized_payload_rejected`: Rejects payloads > 4096 bytes before parsing.
    * `test_oversized_equation_rejected`: Rejects equations > 256 characters.
    * `test_non_ascii_equation_rejected`: Rejects non-ASCII unicode characters.
    * `test_exact_rational_decimal_string_serialization`: Verifies string formatting of numbers.
    * `test_json_roundtrip_bytes_and_str`: Verifies `dispatch_json` with string and bytes.
    * `test_provisional_evidence_flag_consistency`: Verifies `is_provisional_evidence` behavior.

### 5.3 Holdout Dataset Isolation
The 216 tests reported above represent executed developer verification and regression suites in the open product repository. The 80 sealed holdout cases remain completely unaccessed and reserved for independent certification.

---

## 6. Protected Workspace Integrity
- Protected historical repository (`d:\Math Knowledge Engine`) was checked read-only: hash `a5615ff5909d1582ac21f3278900865b8534d6ffd5f8918ab2ef5a38cfa37f76` preserved without modification.
- All development conducted exclusively in `d:\mke-product`.
