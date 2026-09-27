# MKE PRODUCT-02A-S4-A Protocol & Dispatch Contract

**Milestone:** Stable Protocol & Mathematical Dispatch  
**Schema Version:** `mke.p02a.v1`  
**Branch:** `product/p02a-foundation`  
**Baseline Commit:** `608ca98002619432db4754df2351b3e44b06170f`  
**Frozen Specification:** `31cdb61cc84a21b8ebe093765f0a71a606776196`  
**Owner Decision Reference:** `S3_OWNER_DECISION_RECORD.md` (`MKE-S3-ADR-001`)  
**Authorization:** S4-A ONLY (S4-B Sandboxed Worker and S4-C API Host require separate gates)  

---

## 1. Overview & Purpose

MKE Product Milestone S4-A establishes a small, stable, versioned JSON protocol and a side-effect-free in-memory application dispatcher over the accepted S0–S3 mathematical kernel:
- **S0:** Exact rational arithmetic core ($\mathbb{Q}$).
- **S1:** Immutable Equation AST and grammar-enforcing parser.
- **S2:** Independent exact semantic evaluator and rational candidate verifier.
- **S3:** Exact affine linear equation solver ($a \cdot x + b = 0$).

S4-A operates strictly in-process with zero network sockets, zero HTTP listeners, zero dynamic code execution, and zero external dependencies.

---

## 2. Versioned Request Protocol

### 2.1 Supported Operations
The protocol authorizes exactly two discrete operations:
1. `SOLVE`: Formulate and solve an affine linear equation over $\mathbb{R}$ with exact coefficients in $\mathbb{Q}$.
2. `CHECK_CANDIDATE`: Independently verify whether a given exact rational candidate satisfies an unreduced equation AST.

### 2.2 Request Schemas

#### Operation: `SOLVE`
```json
{
  "schema_version": "mke.p02a.v1",
  "operation": "SOLVE",
  "equation": "2*x+3=7"
}
```
- `schema_version` (string, required): Exactly `"mke.p02a.v1"`.
- `operation` (string, required): Exactly `"SOLVE"`.
- `equation` (string, required): ASCII mathematical equation string (max 256 characters).
- Disallowed: Any additional fields (strict allowlist).

#### Operation: `CHECK_CANDIDATE`
```json
{
  "schema_version": "mke.p02a.v1",
  "operation": "CHECK_CANDIDATE",
  "equation": "(x-1)/(x-1)=1",
  "candidate": "2"
}
```
- `schema_version` (string, required): Exactly `"mke.p02a.v1"`.
- `operation` (string, required): Exactly `"CHECK_CANDIDATE"`.
- `equation` (string, required): ASCII mathematical equation string (max 256 characters).
- `candidate` (string, required): Exact ASCII rational string formatted as `[sign]integer[/denominator]`.
- Strict typing: JSON numbers (e.g. `2`, `2.5`), booleans (`true`), arrays, objects, and `null` are strictly rejected with `ERR_PROTOCOL_INVALID_TYPE`.
- Disallowed: Any additional fields.

---

## 3. Input Safety & Framing Ceilings

Requests are validated against explicit conservative bounds BEFORE AST parsing or mathematical execution:

| Parameter | Limit | Failure Code |
| :--- | :--- | :--- |
| **Max Payload Size** | 4,096 bytes (UTF-8) | `ERR_PAYLOAD_TOO_LARGE` |
| **Max Response Size** | 16,384 bytes (16 KiB default) | `ERR_RESPONSE_LIMIT_EXCEEDED` |
| **Min Response Size** | 512 bytes (enforceable floor) | `ValueError` (invalid config) |
| **Max JSON Nesting Depth** | 16 levels (`{}` or `[]`) | `ERR_PROTOCOL_MALFORMED_STRUCTURE` |
| **JSON Encoding** | Strict UTF-8 JSON object | `ERR_PROTOCOL_JSON_DECODE` / `ERR_PROTOCOL_MALFORMED_STRUCTURE` |
| **Max Equation Length** | 256 ASCII characters | `ERR_PROTOCOL_INPUT_LIMIT` |
| **Max Token Count** | 64 tokens | `InputBoundsExceededError` |
| **Max Nesting Depth** | 16 parenthesis levels | `InputBoundsExceededError` |
| **Character Set** | ASCII digits, `x`, `+`, `-`, `*`, `/`, `^`, `(`, `)`, `=` | `LexerError` / `ERR_PROTOCOL_INPUT_LIMIT` |
| **Candidate Length** | 256 characters | `ERR_PROTOCOL_INPUT_LIMIT` |

---

## 4. Response Contract & Outcome Taxonomy

Every response unambiguously reports the protocol version, requested operation, high-level outcome category, fine-grained mathematical status, definedness, exact rational numbers, and provisional evidence indicators.

### 4.1 Outcome Hierarchy
1. `SUCCESS`: Valid protocol request that completed mathematical execution (producing a unique root, identity, contradiction, or verified candidate outcome).
2. `SYNTAX_ERROR`: Mathematical expression could not be parsed according to S1 EBNF grammar (definedness `null`).
3. `PROTOCOL_ERROR`: Request framing violation, schema mismatch, invalid data types, extra fields, malformed candidate string, or transport decode errors:
   - Malformed JSON syntax $\implies$ `ERR_PROTOCOL_JSON_DECODE`.
   - Isolated Unicode surrogates / unencodable chars $\implies$ `ERR_PROTOCOL_JSON_DECODE`.
   - Invalid UTF-8 bytes $\implies$ `ERR_PROTOCOL_JSON_DECODE`.
   - Root not a JSON object $\implies$ `ERR_PROTOCOL_MALFORMED_STRUCTURE`.
   - Duplicate JSON object keys $\implies$ `ERR_PROTOCOL_MALFORMED_STRUCTURE`.
   - JSON nesting depth $> 16$ levels $\implies$ `ERR_PROTOCOL_MALFORMED_STRUCTURE`.
   - Dict payload $> 4096$ UTF-8 bytes $\implies$ `ERR_PAYLOAD_TOO_LARGE`.
   - Non-string keys or unsupported value types $\implies$ `ERR_PROTOCOL_INVALID_TYPE`.
4. `DOMAIN_ERROR`: Expression contains proven mathematical undefinedness in $\mathbb{R}$ ($1/0$, $0^0$). Reserved exclusively for definedness `false`.
5. `OUT_OF_SCOPE`: Equation contains constructs outside S3 affine linear capability ($x^2$, $x \cdot x$, $x^0$, variable denominators) (definedness `null`).
6. `RESOURCE_EXHAUSTED`: Execution exceeded configured operation or bit-length budgets, or serialized response exceeded `max_response_bytes` (`ERR_RESPONSE_LIMIT_EXCEEDED`, definedness `null`).
7. `INTERNAL_VERIFICATION_FAILURE`: S3 computed a root that failed independent S2 certification (definedness `null`).
8. `UNSUPPORTED`: Expression exceeds evaluation capabilities (definedness `null`).

### 4.2 Enforceable Response Limit Invariant
The response builder `_build_bounded_response` establishes an explicit, enforceable invariant:
- Every successful return satisfies `len(serialized_bytes) <= max_response_bytes`.
- Configurable limits smaller than `MIN_RESPONSE_BYTES = 512` are rejected with `ValueError` rather than returning an oversized fallback envelope.
- The deterministic error envelope (`ERR_RESPONSE_LIMIT_EXCEEDED`) requires $\approx 313$ bytes, guaranteed to fit in any valid `max_response_bytes >= 512`.
- Exact numbers and provisional evidence are never truncated or fabricated.

### 4.3 Exact Rational Serialization
All mathematical numbers (roots, candidates, residuals, left/right evaluated values) are transmitted as explicit decimal strings:
```json
{
  "numerator": "-3",
  "denominator": "2"
}
```
**Rule:** No IEEE 754 floating-point values are ever serialized for mathematical quantities. Canonical signs and coprime reductions from `Rational` are preserved.

### 4.4 Three-Valued Definedness Contract
The response field `definedness` represents original-domain mathematical definedness on $\mathbb{R}$:
- `true`: Proven everywhere-defined on $\mathbb{R}$ or at the evaluated candidate.
- `false`: Proven undefined in original expression ($1/0$, $0^0$). Reserved exclusively for mathematical `DOMAIN_ERROR`.
- `null`: UNKNOWN (e.g. `SYNTAX_ERROR`, `PROTOCOL_ERROR`, execution budget exhausted before definedness could be proved, or expression is out of scope).

### 4.4 Example Responses

#### SOLVE: Unique Root
```json
{
  "schema_version": "mke.p02a.v1",
  "operation": "SOLVE",
  "outcome": "SUCCESS",
  "status": "UNIQUE_ROOT",
  "classification": "UNIQUE_ROOT",
  "root": {
    "numerator": "2",
    "denominator": "1"
  },
  "definedness": true,
  "error": null,
  "is_provisional_evidence": true,
  "evidence": { ... }
}
```

#### CHECK_CANDIDATE: Invalid Candidate with Exact Residual
```json
{
  "schema_version": "mke.p02a.v1",
  "operation": "CHECK_CANDIDATE",
  "outcome": "SUCCESS",
  "status": "INVALID",
  "candidate": {
    "numerator": "1",
    "denominator": "5"
  },
  "exact_equality": false,
  "residual": {
    "numerator": "2",
    "denominator": "35"
  },
  "left_value": { "numerator": "1", "denominator": "5" },
  "right_value": { "numerator": "1", "denominator": "7" },
  "definedness": true,
  "error": null,
  "is_provisional_evidence": true,
  "diagnostics": { ... }
}
```

#### PROTOCOL_ERROR: Type Violation (Float Rejected)
```json
{
  "schema_version": "mke.p02a.v1",
  "operation": "CHECK_CANDIDATE",
  "outcome": "PROTOCOL_ERROR",
  "status": "ERR_PROTOCOL_INVALID_TYPE",
  "error": {
    "code": "ERR_PROTOCOL_INVALID_TYPE",
    "message": "Field 'candidate' must be an exact ASCII rational string, got float.",
    "span": null
  },
  "definedness": null,
  "is_provisional_evidence": false
}
```

---

## 5. RFC 8785 Canonical Evidence & Production Certificate Roadmap

### 5.1 Current Status: Provisional Inspection Evidence
In S4-A, evidence structures included in responses (`res["evidence"]`) are provisional inspection payloads (`is_provisional_evidence: true`). They provide diagnostic step traces and affine decomposition for developer testing and auditing. They are **NOT** finalized cryptographic certificates.

### 5.2 Required Implementation for Production Certificates
To achieve production-grade mathematical certificates as mandated by the frozen specification, the following requirements remain necessary:
1. **RFC 8785 JSON Canonicalization Scheme (JCS):** Implementation of deterministic JSON serialization:
   - Lexicographical sorting of object keys by UTF-16 code units.
   - Strict whitespace elimination (no extraneous spaces or newlines).
   - Uniform character escaping and normalization.
2. **Deterministic Cryptographic Hashing:**
   - Calculation of SHA-256 digests over the UTF-8 byte stream produced by RFC 8785 JCS canonicalization.
   - Evidence payload hash binding: $H_{\text{evidence}} = \text{SHA-256}(\text{JCS}(\text{evidence}))$.
3. **Structured Certificate Schema Freeze:**
   - Formal schema definition separating immutable mathematical assertions (equation, normalized affine form, root, verification status) from ephemeral runtime diagnostics (steps, timing).
4. **Asymmetric Cryptographic Attestation:**
   - Ed25519 digital signature of the canonical evidence digest by an offline or HSM-protected signing key.

---

## 6. Security Boundary & Future Trust Architecture (S4-B / S4-C)

### 6.1 S4-A In-Process Scope
S4-A contains NO network listeners, NO external endpoints, NO subprocess spawning, and NO sandbox controls. It is an in-memory library dispatcher.

### 6.2 Target Multi-Process Trust Architecture
Untrusted callers must never directly invoke the mathematical kernel. The approved future architecture enforces strict defense-in-depth with an unsandboxed local loopback API host communicating via IPC with an isolated worker:

```
[ LOCAL CLIENT / CALLER ]
        │  HTTP Request (127.0.0.1 only)
        ▼
┌──────────────────────────────────────┐
│  S4-C LOCAL LOOPBACK API HOST        │
│  - Binds strictly to 127.0.0.1       │
│  - Never exposed to public HTTPS     │
│  - Rate limiting & request framing   │
│  - Schema & size limit validation    │
│  - Zero mathematical evaluation      │
└──────────────────┬───────────────────┘
                   │  IPC / Anonymous Pipe
                   ▼
┌──────────────────────────────────────┐
│    S4-B SANDBOXED WORKER (Isolated)  │
│  - Win32 Job Object isolation        │
│  - Outbound network strictly blocked │
│  - Restricted filesystem ACLs        │
│  - 256 MiB RAM limit per process     │
│  - Kill on job close                 │
│  - S4-A Protocol Dispatcher          │
│  - S0-S3 Mathematical Kernel         │
└──────────────────────────────────────┘
```

### 6.3 Mandatory S4-B Security Requirements (Planned / Unverified)
Before S4-B can be authorized, the worker implementation must prove:
1. **Suspended Worker Creation:** Process launched with `CREATE_SUSPENDED`, assigned to Win32 Job Object, and configured before `ResumeThread` executes any code.
2. **Strict Memory Ceilings:** 256 MiB per-process limit (`JobObjectExtendedLimitInformation.ProcessMemoryLimit`), 512 MiB job-wide limit.
3. **Kill on Close:** `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` guaranteed so orphaned child processes are terminated on host failure.
4. **Breakaway Prevention:** Disallowing `JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK` to prevent child processes from escaping the sandbox.
5. **OS-Enforced Network Isolation:** Windows Filtering Platform (WFP) or AppContainer blocking all outbound network traffic. *Note: Binding a server socket to 127.0.0.1 on the host is a local loopback interface, but does NOT constitute outbound network isolation for the sandboxed worker.*
6. **Filesystem Confinement:** Read-only access to application binaries; zero write access to system or user directories.

All OS sandboxing controls remain **PLANNED / UNVERIFIED** until real Windows runtime verification tests pass under milestone S4-B.
