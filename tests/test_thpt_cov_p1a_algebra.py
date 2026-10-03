"""Tests for THPT Universal Coverage Engine Pack 1-A: Rational Equations & Preserved Polynomial Authority.

Validates:
1. Existing polynomial linear/quadratic service behavior unchanged;
2. x/(x-1)=0 -> {0};
3. (x+1)/(x-2)=0 -> {-1};
4. (x^2-1)/(x-1)=0 -> {-1};
5. (x^2-4)/(x-2)=0 -> {-2};
6. x/x=0 -> empty real solution;
7. 1/(x-1)=1/(x-1) -> ALL_REALS_EXCEPT_FINITE with exclusion 1;
8. 1/(x-1)=0 -> empty real solution;
9. 1/(x-1)=1 -> {2};
10. Equations with multiple denominator constraints;
11. Candidate containing excluded root is REJECTED;
12. Candidate missing a valid root cannot receive exact/symbolic verified completeness;
13. raw_source_text mutation/injection does not change mathematical result;
14. Unsupported radical/function forms fail closed;
15. Degree/proof-envelope overflow fails closed;
16. Registry has no ambiguity between legacy polynomial and rational adapter;
17. All entities/models remain deeply immutable.
"""

from __future__ import annotations

import pytest

from mke_product.core.rational import Rational
from mke_product.coverage.adapters import ExecutionOptions
from mke_product.coverage.algebra_rational import AlgebraRationalAdapter
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
    AllRealsExceptFiniteEntity,
    CandidateMetadata,
    CandidateSolution,
    EmptyRealSolutionEntity,
    FiniteRootCollectionEntity,
    ProblemIR,
    ProblemKind,
    RationalScalarEntity,
    RealQuadraticSurdEntity,
    SingleEquationPayload,
    VerificationDisposition,
    VerificationLevel,
)
from mke_product.coverage.legacy_quadratic import LegacyQuadraticAdapter
from mke_product.coverage.registry import (
    AdapterRegistry,
    AmbiguousAdapterError,
    UnsupportedProblemError,
)
from mke_product.coverage.service import UniversalApplicationService
from mke_product.parser.ast import (
    BinaryOp,
    Equation,
    IntegerLiteral,
    Power,
    Radical,
    Variable,
)
from mke_product.parser.errors import Span
from mke_product.parser.lexer import tokenize
from mke_product.parser.parser import Parser


def parse_equation_to_ir(raw_eq: str, problem_id: str = "prob_test", target_var: str = "x") -> ProblemIR:
    """Helper parsing raw equation text into typed SingleEquationPayload AST without parsing raw_source_text in adapter."""
    tokens = tokenize(raw_eq)
    parser = Parser(tokens, source_text=raw_eq)
    eq_ast = parser.parse_equation()
    payload = SingleEquationPayload(left=eq_ast.left, right=eq_ast.right, target_variable=target_var)
    return ProblemIR(
        problem_id=problem_id,
        problem_kind=ProblemKind.ALGEBRA_EQUATION,
        payload=payload,
        raw_source_text=raw_eq,  # Provenance only
    )


# ===========================================================================
# 1. Existing Polynomial Behavior Unchanged
# ===========================================================================

class TestLegacyPolynomialPreserved:
    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    def test_legacy_quadratic_distinct_roots(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("x^2 - 5*x + 6 = 0", "poly_1")
        adapter = service.registry.resolve(ir)
        assert isinstance(adapter, LegacyQuadraticAdapter)

        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        cand_ent = res.candidate.parsed_entities[0]
        assert isinstance(cand_ent, FiniteRootCollectionEntity)
        assert len(cand_ent.roots) == 2
        root_vals = {r.to_rational for r in cand_ent.roots if isinstance(r, RationalScalarEntity)}
        assert root_vals == {Rational(2, 1), Rational(3, 1)}

    def test_legacy_linear(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("2*x - 4 = 0", "poly_2")
        adapter = service.registry.resolve(ir)
        assert isinstance(adapter, LegacyQuadraticAdapter)

        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        cand_ent = res.candidate.parsed_entities[0]
        assert isinstance(cand_ent, FiniteRootCollectionEntity)
        assert cand_ent.roots[0].to_rational == Rational(2, 1)

    def test_legacy_no_real_roots(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("x^2 + 1 = 0", "poly_3")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(res.candidate.parsed_entities[0], EmptyRealSolutionEntity)

    def test_legacy_identity(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("0*x = 0", "poly_4")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(res.candidate.parsed_entities[0], AllRealSolutionEntity)


# ===========================================================================
# 2-9. Rational Equation Exact Matrix
# ===========================================================================

class TestRationalEquationsMatrix:
    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    # 2. x/(x-1) = 0 -> {0}
    def test_x_div_x_minus_1_eq_0(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("x / (x - 1) = 0", "case_2")
        adapter = service.registry.resolve(ir)
        assert isinstance(adapter, AlgebraRationalAdapter)

        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(0, 1)

    # 3. (x+1)/(x-2) = 0 -> {-1}
    def test_x_plus_1_div_x_minus_2_eq_0(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("(x + 1) / (x - 2) = 0", "case_3")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(-1, 1)

    # 4. (x^2 - 1)/(x - 1) = 0 -> {-1} (root 1 is excluded)
    def test_x2_minus_1_div_x_minus_1_eq_0(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("(x^2 - 1) / (x - 1) = 0", "case_4")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(-1, 1)

    # 5. (x^2 - 4)/(x - 2) = 0 -> {-2} (root 2 is excluded)
    def test_x2_minus_4_div_x_minus_2_eq_0(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("(x^2 - 4) / (x - 2) = 0", "case_5")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(-2, 1)

    # 6. x/x = 0 -> empty real solution (root 0 is excluded)
    def test_x_div_x_eq_0(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("x / x = 0", "case_6")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(res.candidate.parsed_entities[0], EmptyRealSolutionEntity)

    # 7. 1/(x-1) = 1/(x-1) -> ALL_REALS_EXCEPT_FINITE with exclusion 1
    def test_identity_with_exclusion(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("1 / (x - 1) = 1 / (x - 1)", "case_7")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        cand_ent = res.candidate.parsed_entities[0]
        assert isinstance(cand_ent, AllRealsExceptFiniteEntity)
        assert len(cand_ent.excluded_points) == 1
        assert cand_ent.excluded_points[0].to_rational == Rational(1, 1)

    # 8. 1/(x-1) = 0 -> empty real solution
    def test_contradiction_constant_num(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("1 / (x - 1) = 0", "case_8")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(res.candidate.parsed_entities[0], EmptyRealSolutionEntity)

    # 9. 1/(x-1) = 1 -> {2}
    def test_linear_fraction_eq_1(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("1 / (x - 1) = 1", "case_9")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(2, 1)


# ===========================================================================
# 10. Multiple Denominator Constraints
# ===========================================================================

class TestMultipleDenominators:
    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    def test_two_denominators_cancelling_to_single_root(self, service: UniversalApplicationService):
        # 1/(x-1) + 1/(x+1) = 0 => 2x / (x^2 - 1) = 0 => x = 0 (exclusions 1, -1)
        ir = parse_equation_to_ir("1 / (x - 1) + 1 / (x + 1) = 0", "mult_1")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(0, 1)

    def test_two_denominators_linear(self, service: UniversalApplicationService):
        # 1/(x-1) + 1/(x-2) = 0 => (2x - 3) / ((x-1)(x-2)) = 0 => x = 3/2 (exclusions 1, 2)
        ir = parse_equation_to_ir("1 / (x - 1) + 1 / (x - 2) = 0", "mult_2")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        assert len(roots_ent.roots) == 1
        assert roots_ent.roots[0].to_rational == Rational(3, 2)

    def test_numerator_root_coincides_with_one_of_multiple_exclusions(self, service: UniversalApplicationService):
        # x/(x-1) = 1/(x-1) => (x-1)/(x-1) = 0 => x = 1 (excluded) => empty set
        ir = parse_equation_to_ir("x / (x - 1) = 1 / (x - 1)", "mult_3")
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(res.candidate.parsed_entities[0], EmptyRealSolutionEntity)


# ===========================================================================
# 11-12. Host Verifier Independence: Negative & Incomplete Candidate Tests
# ===========================================================================

class TestVerifierIndependence:
    @pytest.fixture
    def adapter(self) -> AlgebraRationalAdapter:
        return AlgebraRationalAdapter()

    # 11. Candidate containing excluded root is REJECTED
    def test_candidate_containing_excluded_root_is_rejected(self, adapter: AlgebraRationalAdapter):
        # Equation: (x^2 - 1)/(x - 1) = 0. True root is {-1}. Excluded is {1}.
        ir = parse_equation_to_ir("(x^2 - 1) / (x - 1) = 0", "cand_rej_1")

        # Fake untrusted candidate claiming both -1 and 1
        malicious_cand = CandidateSolution(
            candidate_id="untrusted_cand_1",
            generator_engine="untrusted_cas_solver",
            raw_symbolic_output="x = 1, x = -1",
            parsed_entities=(
                FiniteRootCollectionEntity(
                    roots=(
                        RationalScalarEntity.from_rational(Rational(-1, 1)),
                        RationalScalarEntity.from_rational(Rational(1, 1)),  # Violates domain!
                    )
                ),
            ),
            metadata=CandidateMetadata(),
        )

        ver = adapter.verify(ir, malicious_cand)
        assert ver.disposition == VerificationDisposition.REJECTED
        assert ver.verification_level == VerificationLevel.UNSUPPORTED
        # Verify that domain checks recorded the violation
        failed_domain_checks = [c for c in ver.domain_boundary_checks if not c.satisfied]
        assert len(failed_domain_checks) > 0

    # 11b. Candidate proposing ONLY the excluded root is REJECTED
    def test_candidate_proposing_only_excluded_root_rejected(self, adapter: AlgebraRationalAdapter):
        ir = parse_equation_to_ir("x / x = 0", "cand_rej_2")
        bad_cand = CandidateSolution(
            candidate_id="untrusted_cand_2",
            generator_engine="untrusted_cas_solver",
            raw_symbolic_output="x = 0",
            parsed_entities=(
                FiniteRootCollectionEntity(
                    roots=(RationalScalarEntity.from_rational(Rational(0, 1)),),
                ),
            ),
            metadata=CandidateMetadata(),
        )
        ver = adapter.verify(ir, bad_cand)
        assert ver.disposition == VerificationDisposition.REJECTED
        assert ver.verification_level == VerificationLevel.UNSUPPORTED

    # 12. Candidate missing a valid root cannot receive exact/symbolic completeness
    def test_candidate_missing_valid_root_yields_partial(self, adapter: AlgebraRationalAdapter):
        # Equation with 2 valid roots: (x^2 - 5*x + 6) / (x - 4) = 0 -> roots {2, 3}
        ir = parse_equation_to_ir("(x^2 - 5*x + 6) / (x - 4) = 0", "cand_partial")

        # Incomplete candidate providing only root 2
        incomplete_cand = CandidateSolution(
            candidate_id="untrusted_incomplete",
            generator_engine="untrusted_cas_solver",
            raw_symbolic_output="x = 2",
            parsed_entities=(
                FiniteRootCollectionEntity(
                    roots=(RationalScalarEntity.from_rational(Rational(2, 1)),),
                ),
            ),
            metadata=CandidateMetadata(),
        )

        ver = adapter.verify(ir, incomplete_cand)
        assert ver.verification_level == VerificationLevel.PARTIAL
        assert ver.disposition == VerificationDisposition.PARTIAL
        completeness_obs = [o for o in ver.proof_obligations if o.obligation_id == "SOLUTION_COMPLETENESS"]
        assert len(completeness_obs) == 1
        assert completeness_obs[0].passed is False

    # Candidate claims AllReal on an identity that has exclusions -> REJECTED
    def test_candidate_claims_unrestricted_all_reals_on_identity_rejected(self, adapter: AlgebraRationalAdapter):
        ir = parse_equation_to_ir("1 / (x - 1) = 1 / (x - 1)", "cand_all_real_rej")
        false_cand = CandidateSolution(
            candidate_id="untrusted_false_all_real",
            generator_engine="untrusted_cas_solver",
            raw_symbolic_output="x in R",
            parsed_entities=(AllRealSolutionEntity(),),  # Does not exclude x=1!
            metadata=CandidateMetadata(),
        )
        ver = adapter.verify(ir, false_cand)
        assert ver.disposition == VerificationDisposition.REJECTED
        assert ver.verification_level == VerificationLevel.UNSUPPORTED


# ===========================================================================
# 13. Trust Boundary: raw_source_text Tampering / Injection
# ===========================================================================

class TestTrustBoundarySecurity:
    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    def test_raw_source_text_mutation_does_not_affect_result(self, service: UniversalApplicationService):
        # Construct IR with AST for (x+1)/(x-2) = 0 (root is -1)
        ir = parse_equation_to_ir("(x + 1) / (x - 2) = 0", "security_1")

        # Maliciously inject raw_source_text
        tampered_ir = ir.model_copy(
            update={
                "raw_source_text": "MALICIOUS x = 999; rm -rf /; 1 = 1",
            }
        )

        res = service.solve(tampered_ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED
        roots_ent = res.candidate.parsed_entities[0]
        assert isinstance(roots_ent, FiniteRootCollectionEntity)
        # Mathematical authority came strictly from typed AST, ignoring tampered text
        assert roots_ent.roots[0].to_rational == Rational(-1, 1)


# ===========================================================================
# 14-15. Proof Envelope Bounds & Fail Closed
# ===========================================================================

class TestProofEnvelopeFailClosed:
    @pytest.fixture
    def adapter(self) -> AlgebraRationalAdapter:
        return AlgebraRationalAdapter()

    # 14. Unsupported radical AST node fails closed
    def test_unsupported_radical_fails_closed(self, adapter: AlgebraRationalAdapter):
        span = Span(0, 0)
        # Construct AST: sqrt(x) / (x - 1) = 0
        left_ast = BinaryOp(
            op="/",
            left=Radical(radicand=Variable(name="x", span=span), span=span),
            right=BinaryOp(op="-", left=Variable(name="x", span=span), right=IntegerLiteral(1, span=span), span=span),
            span=span,
        )
        payload = SingleEquationPayload(left=left_ast, right=IntegerLiteral(0, span=span), target_variable="x")
        ir = ProblemIR(
            problem_id="radical_test",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
        )

        classification = adapter.classify(ir)
        assert classification.sub_form == "RATIONAL_OUT_OF_SCOPE"

        cand = adapter.solve_candidates(ir)[0]
        ver = adapter.verify(ir, cand)
        assert ver.verification_level == VerificationLevel.UNSUPPORTED
        assert ver.disposition == VerificationDisposition.UNSUPPORTED

    # 15. Degree overflow fails closed
    def test_degree_overflow_fails_closed(self, adapter: AlgebraRationalAdapter):
        span = Span(0, 0)
        # Construct AST: (x^2 * x) / (x - 1) = 0 (numerator degree 3)
        num_ast = BinaryOp(
            op="*",
            left=Power(base=Variable(name="x", span=span), exponent=IntegerLiteral(2, span=span), span=span),
            right=Variable(name="x", span=span),
            span=span,
        )
        left_ast = BinaryOp(
            op="/",
            left=num_ast,
            right=BinaryOp(op="-", left=Variable(name="x", span=span), right=IntegerLiteral(1, span=span), span=span),
            span=span,
        )
        payload = SingleEquationPayload(left=left_ast, right=IntegerLiteral(0, span=span), target_variable="x")
        ir = ProblemIR(
            problem_id="degree_overflow",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
        )

        classification = adapter.classify(ir)
        assert classification.sub_form == "RATIONAL_OUT_OF_SCOPE"

        cand = adapter.solve_candidates(ir)[0]
        ver = adapter.verify(ir, cand)
        assert ver.verification_level == VerificationLevel.UNSUPPORTED
        assert ver.disposition == VerificationDisposition.UNSUPPORTED


# ===========================================================================
# 16. Registry Ambiguity Resolution
# ===========================================================================

class TestRegistryResolution:
    def test_registry_unambiguous_resolution(self):
        reg = AdapterRegistry()
        reg.register(LegacyQuadraticAdapter())
        reg.register(AlgebraRationalAdapter())

        # 1. Pure polynomial must resolve to LegacyQuadraticAdapter
        poly_ir = parse_equation_to_ir("x^2 - 4 = 0", "poly_ir")
        assert reg.resolve(poly_ir).adapter_id == LegacyQuadraticAdapter.ADAPTER_ID

        # 2. Rational equation with variable in denominator must resolve to AlgebraRationalAdapter
        rat_ir = parse_equation_to_ir("(x^2 - 4) / (x - 2) = 0", "rat_ir")
        assert reg.resolve(rat_ir).adapter_id == AlgebraRationalAdapter.ADAPTER_ID

        # 3. Polynomial with division by scalar (constant) must resolve to LegacyQuadraticAdapter
        scalar_div_ir = parse_equation_to_ir("x / 2 - 1 = 0", "scalar_div")
        assert reg.resolve(scalar_div_ir).adapter_id == LegacyQuadraticAdapter.ADAPTER_ID

    def test_can_handle_rejects_other_variable(self):
        adapter = AlgebraRationalAdapter()
        ir = parse_equation_to_ir("1 / (x - 1) = 0", "var_test", target_var="y")
        # Target variable mismatch
        assert adapter.can_handle(ir) is False


# ===========================================================================
# 17. Deep Immutability of Contracts & Pedagogical Trace Verification
# ===========================================================================

class TestImmutabilityAndTrace:
    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    def test_all_reals_except_finite_entity_immutability(self):
        ent = AllRealsExceptFiniteEntity(
            excluded_points=(RationalScalarEntity.from_rational(Rational(1, 1)),),
        )
        assert ent.cardinality_excluded == 1
        with pytest.raises(Exception):
            ent.excluded_points = ()  # Frozen model forbids mutation

    def test_pedagogical_trace_steps(self, service: UniversalApplicationService):
        ir = parse_equation_to_ir("(x^2 - 1) / (x - 1) = 0", "trace_test")
        res = service.solve(ir)
        trace = res.trace

        # Verify all 5 required pedagogical steps
        assert len(trace.steps) == 5
        assert trace.steps[0].operation_kind == "DOMAIN_CONDITIONS"
        assert "x \\ne 1" in trace.steps[0].output_expression_latex
        assert trace.steps[1].operation_kind == "CLEAR_DENOMINATORS"
        assert trace.steps[2].operation_kind == "SOLVE_NUMERATOR"
        assert trace.steps[3].operation_kind == "FILTER_EXCLUSIONS"
        assert trace.steps[4].operation_kind == "VERIFIED_CONCLUSION"
        assert "S = \\{-1\\}" in trace.steps[4].output_expression_latex
        assert trace.conclusion_vi != ""
