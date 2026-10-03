THPT-COV-P1-R1 remediation

Base: 85e21b6823c6c56a4f349a1b5579a03695385b3a

Fix these four audited contract defects only.

1. ProblemIR provenance uses a mutable Dict. Replace it with a typed frozen representation and add recursive immutability tests.

2. DomainAdapter.supported_problem_kinds returns Set. Change the interface and implementations to an immutable collection. Keep registry behavior deterministic.

3. Benchmark false_verified_count currently depends on is_false_verified supplied in each result. Derive false verification inside metric calculation from: is_correct is false AND verification_level is EXACT_VERIFIED or SYMBOLIC_VERIFIED. Add regression tests and ensure release_gate_passed becomes false when such a result exists.

4. ExpectedAnswerType has nine values but ExpectedAnswerSpec has only five variants. Add typed immutable variants for TUPLE_SET, MATRIX, BOOLEAN, and STATISTICAL_VALUE. Enforce consistency between BenchmarkCase.expected_answer_type and expected_answer.answer_type. Add tests for all nine types and mismatch rejection.

Keep all authoritative contracts recursively immutable. No Any or Dict mathematical answer payload.

Run focused THPT-COV-P1 tests and full pytest tests/ -q. Zero failures required.

Do not change frontend, parser, worker, K1/data, existing quadratic source, existing domain registry/verifier, or transport/API. Do not start Pack 1 or add a new math domain.

The runner handles Git operations.

Final line: READY FOR INDEPENDENT THPT-COV-P1-R1 AUDIT
