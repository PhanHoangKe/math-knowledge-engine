"""Tests for THPT Universal Coverage Engine P1 LegacyQuadraticAdapter & Facade."""

from __future__ import annotations

from typing import Tuple
import pytest

from mke_product.application.dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    SolvedResponse,
    SolveRequest,
)
from mke_product.application.orchestrator import solve_request
from mke_product.core.rational import Rational
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
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
from mke_product.coverage.service import UniversalApplicationService
from mke_product.domain.models import RationalFraction
from mke_product.parser.lexer import tokenize
from mke_product.parser.parser import Parser


def parse_equation_to_ir(raw_eq: str, problem_id: str = "prob_test", target_var: str = "x") -> ProblemIR:
    """Helper to parse raw equation into typed SingleEquationPayload AST without parsing raw_source_text in adapter."""
    tokens = tokenize(raw_eq)
    parser = Parser(tokens, source_text=raw_eq)
    eq_ast = parser.parse_equation()
    payload = SingleEquationPayload(left=eq_ast.left, right=eq_ast.right, target_variable=target_var)
    return ProblemIR(
        problem_id=problem_id,
        problem_kind=ProblemKind.ALGEBRA_EQUATION,
        payload=payload,
        raw_source_text=raw_eq,  # For provenance only
    )


class TestLegacyQuadraticAdapterEquivalence:
    """Tests the 8 mandatory equivalence cases between direct solve_request and LegacyQuadraticAdapter."""

    @pytest.fixture
    def adapter(self) -> LegacyQuadraticAdapter:
        return LegacyQuadraticAdapter()

    @pytest.fixture
    def service(self) -> UniversalApplicationService:
        return UniversalApplicationService()

    # 1. x^2 - 5*x + 6 = 0 -> two rational roots (2, 3)
    def test_case_1_two_rational_roots(self, adapter: LegacyQuadraticAdapter, service: UniversalApplicationService):
        ir = parse_equation_to_ir("x^2 - 5*x + 6 = 0", "case_1")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        assert len(cand.parsed_entities) == 1
        roots_coll = cand.parsed_entities[0]
        assert isinstance(roots_coll, FiniteRootCollectionEntity)
        assert len(roots_coll.roots) == 2

        # UniversalApplicationService E2E check
        res = service.solve(ir)
        assert res.verification.verification_level == VerificationLevel.EXACT_VERIFIED
        assert res.verification.disposition == VerificationDisposition.ACCEPTED

    # 2. x^2 + 2*x + 1 = 0 -> repeated root (-1)
    def test_case_2_repeated_rational_root(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("x^2 + 2*x + 1 = 0", "case_2")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        roots_coll = cand.parsed_entities[0]
        assert isinstance(roots_coll, FiniteRootCollectionEntity)
        assert len(roots_coll.roots) == 1
        r = roots_coll.roots[0]
        assert isinstance(r, RationalScalarEntity)
        assert r.to_rational == Rational(-1, 1)

    # 3. x^2 + 1 = 0 -> no real roots (empty set)
    def test_case_3_no_real_roots(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("x^2 + 1 = 0", "case_3")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(cand.parsed_entities[0], EmptyRealSolutionEntity)

    # 4. x^2 - 2 = 0 -> exact real surds (+-sqrt(2))
    def test_case_4_exact_real_surds(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("x^2 - 2 = 0", "case_4")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        roots_coll = cand.parsed_entities[0]
        assert isinstance(roots_coll, FiniteRootCollectionEntity)
        assert len(roots_coll.roots) == 2
        for r in roots_coll.roots:
            assert isinstance(r, RealQuadraticSurdEntity)
            assert r.d == 2

    # 5. 2*x - 4 = 0 -> degenerate linear (x = 2)
    def test_case_5_degenerate_linear(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("2*x - 4 = 0", "case_5")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        roots_coll = cand.parsed_entities[0]
        assert isinstance(roots_coll, FiniteRootCollectionEntity)
        assert len(roots_coll.roots) == 1
        r = roots_coll.roots[0]
        assert isinstance(r, RationalScalarEntity)
        assert r.to_rational == Rational(2, 1)

    # 6. 0*x = 0 -> identity (all reals)
    def test_case_6_degenerate_identity(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("0*x = 0", "case_6")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(cand.parsed_entities[0], AllRealSolutionEntity)

    # 7. 0*x + 5 = 0 -> contradiction (empty set)
    def test_case_7_degenerate_contradiction(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("0*x + 5 = 0", "case_7")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        assert isinstance(cand.parsed_entities[0], EmptyRealSolutionEntity)

    # 8. (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> fractional coefficients (1, 3/2)
    def test_case_8_fractional_coefficients(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("(1/2)*x^2 - (5/4)*x + 3/4 = 0", "case_8")
        assert adapter.can_handle(ir) is True

        cand, ver, trace = adapter.solve_legacy_facade(ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
        assert ver.disposition == VerificationDisposition.ACCEPTED
        roots_coll = cand.parsed_entities[0]
        assert isinstance(roots_coll, FiniteRootCollectionEntity)
        assert len(roots_coll.roots) == 2


class TestLegacyQuadraticFailClosedBehavior:
    """Verifies fail-closed behavior on out-of-scope expressions."""

    @pytest.fixture
    def adapter(self) -> LegacyQuadraticAdapter:
        return LegacyQuadraticAdapter()

    def test_rejects_degree_higher_than_two(self, adapter: LegacyQuadraticAdapter):
        # x^3 - 1 = 0 (degree 3)
        tokens = tokenize("x^2 * x - 1 = 0")
        parser = Parser(tokens)
        eq_ast = parser.parse_equation()
        payload = SingleEquationPayload(left=eq_ast.left, right=eq_ast.right, target_variable="x")
        ir = ProblemIR(
            problem_id="prob_deg3",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
        )
        assert adapter.can_handle(ir) is False

    def test_rejects_division_by_variable(self, adapter: LegacyQuadraticAdapter):
        # 1/x = 0 (rational expression)
        tokens = tokenize("1/x = 0")
        parser = Parser(tokens)
        eq_ast = parser.parse_equation()
        payload = SingleEquationPayload(left=eq_ast.left, right=eq_ast.right, target_variable="x")
        ir = ProblemIR(
            problem_id="prob_rational",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
        )
        assert adapter.can_handle(ir) is False

    def test_rejects_unsupported_target_variable(self, adapter: LegacyQuadraticAdapter):
        ir = parse_equation_to_ir("x^2 - 1 = 0", "prob_var_y", target_var="y")
        assert adapter.can_handle(ir) is False

    def test_does_not_call_raw_source_text_mutation(self, adapter: LegacyQuadraticAdapter):
        # Even if raw_source_text is altered to gibberish, adapter operates on typed AST
        ir = parse_equation_to_ir("x^2 - 4 = 0", "prob_tamper")
        tampered_ir = ir.model_copy(update={"raw_source_text": "MALICIOUS_RAW_TEXT_INJECTION"})
        assert adapter.can_handle(tampered_ir) is True
        cand, ver, trace = adapter.solve_legacy_facade(tampered_ir)
        assert ver.verification_level == VerificationLevel.EXACT_VERIFIED
