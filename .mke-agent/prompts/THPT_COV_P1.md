MKE PRODUCT — THPT-COV-P1 UNIVERSAL CORE IMPLEMENTATION

ROLE
You are Antigravity ("Anty"), Implementation Engineer.
ChatGPT is Coordinator / Independent Auditor.
Project Owner: Kế Phan Hoàng.
Repository: PhanHoangKe/math-knowledge-engine.

BASELINE
Start from exactly:
37cc383631600853381da0ce8e5457ab746e1da1

First read:
docs/preflight/MVP_V1_THPT_COV_P0_UNIVERSAL_COVERAGE_PREFLIGHT.md

That accepted P0-R1 document is authoritative.

AUTOMATION RULES
- The external runner handles baseline tests, final tests, git commit and push.
- Do NOT run git commit, git push, git checkout, git reset, git rebase, or force operations.
- Do NOT modify files outside the allowed P1 scope.
- Do NOT modify frontend.
- Do NOT modify existing parser, worker, K1 data, quadratic authority, registry, verifier, or transport/API.
- Implement code and tests only, then return a concise delivery report.

P1 PURPOSE
Implement only the universal infrastructure that lets future math domains plug into MKE without rewriting the application.

CREATE A DEDICATED PACKAGE
Prefer:
src/mke_product/coverage/__init__.py
src/mke_product/coverage/contracts.py
src/mke_product/coverage/adapters.py
src/mke_product/coverage/registry.py
src/mke_product/coverage/legacy_quadratic.py
src/mke_product/coverage/service.py
src/mke_product/coverage/benchmark.py

Tests should be isolated under names beginning:
tests/test_thpt_cov_p1_

NO NEW MATHEMATICAL DOMAIN IN P1.

CONTRACTS
Implement closed string enums from the accepted preflight, including:
ProblemKind
SourceInputKind
ProblemTarget
DomainCategory
ConstraintRelation
PayloadKind
VerificationLevel
VerificationDisposition
ExpectedAnswerType
BenchmarkRightsStatus
BenchmarkSourceType
BenchmarkSplit

VerificationLevel must be exactly:
EXACT_VERIFIED
SYMBOLIC_VERIFIED
CROSS_CHECKED
PARTIAL
UNSUPPORTED

VerificationDisposition must be exactly:
ACCEPTED
PARTIAL
REJECTED
UNSUPPORTED

LEGAL VERIFICATION PAIRS
EXACT_VERIFIED -> ACCEPTED only
SYMBOLIC_VERIFIED -> ACCEPTED only
CROSS_CHECKED -> ACCEPTED only
PARTIAL -> PARTIAL only
UNSUPPORTED -> UNSUPPORTED or REJECTED
Contradictory pairs must fail model validation.

PROBLEM IR
Implement frozen, extra-forbid, deeply immutable ProblemIR with:
problem_id
ir_version = "mke.problem_ir.v1"
problem_kind
source_input_kind
target
variables
parameters
domain_spec
assumptions
payload
ast_payload
raw_source_text
provenance
normalization_trace

raw_source_text is DISPLAY/PROVENANCE ONLY and must never be reparsed as mathematical authority.

Reuse the accepted mke_product.parser.ast ASTNode hierarchy. Do not invent a second expression language.

ASSUMPTIONS
Use typed immutable AssumptionSpec. No raw mathematical assumption strings that a downstream CAS reparses.

DISCRIMINATED PAYLOADS
Implement typed immutable variants:
SingleEquationPayload
SystemOfEquationsPayload
SingleInequalityPayload
FunctionAnalysisPayload
CalculusOperationPayload
MatrixOperationPayload
GeometryCoordinatePayload

Use literal payload_kind discriminators and an Annotated discriminated union.

AUTHORITATIVE KIND -> PAYLOAD MAPPING
At P1 allow only:
ALGEBRA_EQUATION, EXPONENTIAL_EQUATION, LOGARITHMIC_EQUATION, TRIGONOMETRIC_EQUATION -> SINGLE_EQUATION

ALGEBRA_INEQUALITY, EXPONENTIAL_INEQUALITY, LOGARITHMIC_INEQUALITY, TRIGONOMETRIC_INEQUALITY -> SINGLE_INEQUALITY

ALGEBRA_SYSTEM -> SYSTEM_OF_EQUATIONS

FUNCTION_ANALYSIS -> FUNCTION_ANALYSIS

DERIVATIVE, LIMIT, ANTIDERIVATIVE, DEFINITE_INTEGRAL -> CALCULUS_OPERATION

MATRIX -> MATRIX_OPERATION

COORDINATE_GEOMETRY_2D, COORDINATE_GEOMETRY_3D -> GEOMETRY_COORDINATE

ProblemKind values without a P1 payload contract, including OPTIMIZATION, COMPLEX_NUMBER, VECTOR, COMBINATORICS, PROBABILITY, STATISTICS, WORD_PROBLEM, GEOMETRY_TEXT and UNKNOWN, must fail closed when constructing authoritative ProblemIR.

Reject every mismatched problem_kind/payload_kind pair.

DEEP IMMUTABILITY
No authoritative list, dict or mutable set may be embedded in ProblemIR, payloads, AssumptionSpec, CandidateSolution, VerificationReport, SolutionTrace or BenchmarkCase.
Use tuples/frozensets/typed frozen models.
Add recursive mutation tests, not only field-reassignment tests.

CANDIDATE SOLUTION
CandidateSolution is UNTRUSTED output and must contain no is_correct / verified / trusted boolean.
Use typed immutable CandidateMetadata.
raw_symbolic_output is diagnostic only.
Verification must consume typed parsed_entities, never sympify/parse_expr the display string.

SYMBOLIC ENTITY
Design the smallest typed immutable SymbolicEntity representation needed for the legacy quadratic facade:
- exact rational root/scalar
- exact real quadratic surd root
- finite root collection
- empty real solution
- all-real solution
Display strings may exist but are never reparsed.

VERIFICATION REPORT
Frozen transport-neutral model with:
verification_id
verifier_name
verification_level
disposition
proof_obligations
identities_checked
counterexamples
residual_evaluations
domain_boundary_checks
certificate_hash
details

No passed: bool.
certificate_hash is a deterministic unkeyed SHA-256 integrity fingerprint, not a signature.

SOLUTION TRACE
Create generic immutable TraceStep and SolutionTrace contracts without React/UI concepts.
Do not replace existing quadratic trace classes.

DOMAIN ADAPTER
Create UI-independent abstract DomainAdapter with immutable return collections and the accepted conceptual methods:
adapter_id
supported_problem_kinds
can_handle
normalize
classify
solve_candidates
verify
build_trace
supported_methods
limitations

ADAPTER REGISTRY
Implement deterministic AdapterRegistry:
- unique adapter_id
- deterministic registration order
- lookup by ProblemKind
- resolve exactly one can_handle=True adapter
- zero match -> explicit unsupported
- multiple matches -> fail closed ambiguity
- never silently first-match-wins

LEGACY QUADRATIC ADAPTER
Implement facade only. Do NOT rewrite quadratic mathematics.
Use typed SingleEquationPayload / AST.
Do NOT reparse ProblemIR.raw_source_text.
Use existing normalization to derive exact coefficients.
Construct existing CanonicalCoefficientInput / SolveRequest and delegate to application.orchestrator.solve_request.
The existing quadratic verifier/method registry/trace authority remains unchanged.

can_handle only when exact existing normalization accepts the typed equation as current degree <=2 single-variable scope.
Non-polynomial, degree >2, x in denominator, unsupported target variable and other legacy guards remain fail-closed.

Provide semantic equivalence tests against direct solve_request for:
1. x^2 - 5*x + 6 = 0
2. x^2 + 2*x + 1 = 0
3. x^2 + 1 = 0
4. x^2 - 2 = 0
5. 2*x - 4 = 0
6. 0*x = 0
7. 0*x + 5 = 0
8. (1/2)*x^2 - (5/4)*x + 3/4 = 0

Also prove:
- degree >2 unsupported
- variable denominator remains rejected
- unsupported target variable fail-closed
- adapter does not use SymPy as authority
- adapter does not parse raw_source_text
- existing solve_request source remains untouched

UNIVERSAL APPLICATION SERVICE
Internal Python only. No FastAPI route.
Consumes validated ProblemIR, resolves adapter, executes fail-closed.
Initially register only LegacyQuadraticAdapter.

BENCHMARK CONTRACT
Implement immutable BenchmarkCase with:
case_id
benchmark_version
grade_band
domain
family
subfamily
source_type
source_locator
rights_status
input_mode
problem_text
structured_problem: Optional[ProblemIR]
expected_answer
expected_answer_type
expected_domain
required_verification_obligations
split
difficulty
tags

ExpectedAnswerType exactly:
FINITE_SET
INTERVAL_SET
EXPRESSION
SCALAR
TUPLE_SET
MATRIX
BOOLEAN
STATISTICAL_VALUE
STRUCTURED

Expected answer must itself be a typed immutable discriminated model, never Any/dict.

BenchmarkRightsStatus exactly:
PROJECT_AUTHORED
OPEN_LICENSED
PUBLIC_DOMAIN_CONFIRMED
PERMISSION_GRANTED
SOURCE_LOCATOR_ONLY

BenchmarkSourceType at minimum:
OFFICIAL_PUBLIC
OPEN_LICENSED
PROJECT_AUTHORED
DERIVED_METAMORPHIC

BenchmarkSplit exactly:
DEV
HOLDOUT
ADVERSARIAL

BENCHMARK RUNNER
Pure in-memory runner only. No downloads/network/scraping.
Input immutable tuple of BenchmarkCase plus evaluator/service.
Return immutable per-case results and aggregate metrics.

Metrics use ALL eligible cases as denominator:
total_cases
correct_count
overall_correct_rate
verified_correct_count
verified_correct_rate
exact_verified_rate
symbolic_verified_rate
cross_checked_rate
partial_rate
unsupported_rate
coverage_rate
false_verified_count
median_latency_ms
p95_latency_ms

verified_correct_rate counts only correct EXACT_VERIFIED or SYMBOLIC_VERIFIED.
false_verified_count inspects only incorrect/incomplete EXACT_VERIFIED or SYMBOLIC_VERIFIED.
coverage_rate = (N - unsupported_count) / N.
release_gate_passed requires false_verified_count == 0.
Handle empty benchmark deterministically without divide-by-zero.

ABSOLUTE FREEZES
No changes under:
src/frontend/
src/mke_product/knowledge/data/
src/mke_product/knowledge/k1_schemas.py
src/mke_product/knowledge/k1_loader.py
src/mke_product/worker/
src/mke_product/parser/
existing application/orchestrator.py
existing application/normalizer.py
existing domain/verifier.py
existing domain/registry.py
existing transport/

No public API.
No worker allowlist expansion.
No parser grammar expansion.
No new SymPy domain adapter.
No K1 changes.

TESTS
Create focused P1 tests for:
- exact enum sets
- valid/mismatched/unsupported kind-payload contracts
- extra-forbid
- deep immutability including recursive detection of list/dict/set
- CandidateSolution no truth boolean
- legal/illegal verification states
- deterministic registry and ambiguity rejection
- all 8 legacy equivalence cases and fail-closed cases
- BenchmarkCase typing/immutability/rights-source separation
- benchmark denominator, levels, false-verified gate, deterministic median/p95, ordering and empty benchmark

FINAL RESPONSE
Return:
MKE PRODUCT — THPT-COV-P1 UNIVERSAL CORE IMPLEMENTATION REPORT
with changed files, architecture decisions, test summary, known limitations and readiness for independent audit.

Final line:
READY FOR INDEPENDENT THPT-COV-P1 AUDIT

Do not begin Pack 1.
