"""Tests for THPT Universal Coverage Engine P1 AdapterRegistry."""

from __future__ import annotations

from typing import Optional, Set, Tuple
import pytest

from mke_product.coverage.adapters import (
    DomainAdapter,
    DomainClassification,
    ExecutionOptions,
    MethodAssessment,
)
from mke_product.coverage.contracts import (
    CandidateSolution,
    ProblemIR,
    ProblemKind,
    SingleEquationPayload,
    SolutionTrace,
    VerificationReport,
)
from mke_product.coverage.registry import (
    AdapterRegistry,
    AmbiguousAdapterError,
    DuplicateAdapterError,
    UnsupportedProblemError,
)
from mke_product.parser.ast import IntegerLiteral, Variable


class MockAdapter(DomainAdapter):
    def __init__(self, adapter_id: str, kinds: Set[ProblemKind], handles: bool = True):
        self._adapter_id = adapter_id
        self._kinds = kinds
        self._handles = handles

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def supported_problem_kinds(self) -> Set[ProblemKind]:
        return self._kinds

    def can_handle(self, ir: ProblemIR) -> bool:
        return self._handles

    def normalize(self, ir: ProblemIR) -> ProblemIR:
        return ir

    def classify(self, ir: ProblemIR) -> DomainClassification:
        return DomainClassification(problem_kind=ir.problem_kind, sub_form="MOCK")

    def solve_candidates(self, ir: ProblemIR, options: Optional[ExecutionOptions] = None) -> Tuple[CandidateSolution, ...]:
        return ()

    def verify(self, ir: ProblemIR, candidate: CandidateSolution) -> VerificationReport:
        raise NotImplementedError

    def build_trace(self, ir: ProblemIR, candidate: CandidateSolution, verification: VerificationReport, selected_method_id: Optional[str] = None) -> SolutionTrace:
        raise NotImplementedError

    def supported_methods(self, ir: ProblemIR) -> Tuple[MethodAssessment, ...]:
        return ()

    def limitations(self) -> Tuple[str, ...]:
        return ("Mock adapter",)


def make_dummy_ir(kind: ProblemKind = ProblemKind.ALGEBRA_EQUATION) -> ProblemIR:
    return ProblemIR(
        problem_id="dummy_01",
        problem_kind=kind,
        payload=SingleEquationPayload(left=Variable("x"), right=IntegerLiteral(0)),
    )


class TestAdapterRegistry:
    def test_empty_registry(self):
        reg = AdapterRegistry()
        assert reg.list_adapters() == ()
        assert reg.get_adapter("unknown") is None

    def test_register_and_deterministic_order(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION})
        a2 = MockAdapter("adapter_2", {ProblemKind.EXPONENTIAL_EQUATION})
        a3 = MockAdapter("adapter_3", {ProblemKind.ALGEBRA_EQUATION})

        reg.register(a1)
        reg.register(a2)
        reg.register(a3)

        assert reg.list_adapters() == (a1, a2, a3)
        assert reg.get_adapter("adapter_2") is a2

    def test_rejects_duplicate_adapter_id(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION})
        a1_dup = MockAdapter("adapter_1", {ProblemKind.DERIVATIVE})

        reg.register(a1)
        with pytest.raises(DuplicateAdapterError, match="is already registered"):
            reg.register(a1_dup)

    def test_adapters_for_kind(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION, ProblemKind.EXPONENTIAL_EQUATION})
        a2 = MockAdapter("adapter_2", {ProblemKind.ALGEBRA_EQUATION})
        a3 = MockAdapter("adapter_3", {ProblemKind.DERIVATIVE})

        reg.register(a1)
        reg.register(a2)
        reg.register(a3)

        alg_adapters = reg.adapters_for_kind(ProblemKind.ALGEBRA_EQUATION)
        assert alg_adapters == (a1, a2)

        calc_adapters = reg.adapters_for_kind(ProblemKind.DERIVATIVE)
        assert calc_adapters == (a3,)

        mat_adapters = reg.adapters_for_kind(ProblemKind.MATRIX)
        assert mat_adapters == ()

    def test_resolve_unique_matching_adapter(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION})
        a2 = MockAdapter("adapter_2", {ProblemKind.EXPONENTIAL_EQUATION})
        reg.register(a1)
        reg.register(a2)

        ir = make_dummy_ir(ProblemKind.ALGEBRA_EQUATION)
        resolved = reg.resolve(ir)
        assert resolved is a1

    def test_resolve_unsupported_problem(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.EXPONENTIAL_EQUATION})
        reg.register(a1)

        ir = make_dummy_ir(ProblemKind.ALGEBRA_EQUATION)
        with pytest.raises(UnsupportedProblemError, match="No registered domain adapter can handle"):
            reg.resolve(ir)

    def test_resolve_ambiguous_matching_adapters_fails_closed(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION}, handles=True)
        a2 = MockAdapter("adapter_2", {ProblemKind.ALGEBRA_EQUATION}, handles=True)
        reg.register(a1)
        reg.register(a2)

        ir = make_dummy_ir(ProblemKind.ALGEBRA_EQUATION)
        with pytest.raises(AmbiguousAdapterError, match="Ambiguous adapter resolution"):
            reg.resolve(ir)

    def test_adapter_with_declared_kind_but_can_handle_false_is_not_selected(self):
        reg = AdapterRegistry()
        a_declined = MockAdapter("adapter_declined", {ProblemKind.ALGEBRA_EQUATION}, handles=False)
        a_capable = MockAdapter("adapter_capable", {ProblemKind.ALGEBRA_EQUATION}, handles=True)
        reg.register(a_declined)
        reg.register(a_capable)

        ir = make_dummy_ir(ProblemKind.ALGEBRA_EQUATION)
        resolved = reg.resolve(ir)
        assert resolved is a_capable

    def test_registered_tuple_is_immutable_externally(self):
        reg = AdapterRegistry()
        a1 = MockAdapter("adapter_1", {ProblemKind.ALGEBRA_EQUATION})
        reg.register(a1)
        adapters = reg.list_adapters()
        assert isinstance(adapters, tuple)
        assert not hasattr(adapters, "append")
