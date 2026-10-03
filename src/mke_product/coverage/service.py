"""Internal Universal Application Service for MKE THPT Coverage Engine."""

from __future__ import annotations

from typing import Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from mke_product.coverage.adapters import ExecutionOptions
from mke_product.coverage.contracts import (
    CandidateSolution,
    ProblemIR,
    SolutionTrace,
    VerificationReport,
)
from mke_product.coverage.algebra_inequality import AlgebraPolynomialInequalityAdapter
from mke_product.coverage.algebra_rational import AlgebraRationalAdapter
from mke_product.coverage.legacy_quadratic import LegacyQuadraticAdapter
from mke_product.coverage.registry import AdapterRegistry


class UniversalSolveResult(BaseModel):
    """Immutable result from universal coverage application execution."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    ir: ProblemIR
    candidate: CandidateSolution
    verification: VerificationReport
    trace: SolutionTrace


class UniversalApplicationService:
    """Internal service coordinating ProblemIR resolution, solving, verification, and tracing."""

    def __init__(self, registry: Optional[AdapterRegistry] = None) -> None:
        if registry is None:
            registry = AdapterRegistry()
            registry.register(LegacyQuadraticAdapter())
            registry.register(AlgebraRationalAdapter())
            registry.register(AlgebraPolynomialInequalityAdapter())
        self._registry = registry

    @property
    def registry(self) -> AdapterRegistry:
        return self._registry

    def solve(
        self,
        ir: ProblemIR,
        selected_method_id: Optional[str] = None,
        options: Optional[ExecutionOptions] = None,
    ) -> UniversalSolveResult:
        """Resolve adapter and execute end-to-end solve, verification, and trace pipeline."""
        adapter = self._registry.resolve(ir)
        normalized_ir = adapter.normalize(ir)
        candidates = adapter.solve_candidates(normalized_ir, options=options)
        if not candidates:
            raise ValueError(f"Adapter {adapter.adapter_id!r} produced zero candidate solutions.")

        primary_candidate = candidates[0]
        verification = adapter.verify(normalized_ir, primary_candidate)
        trace = adapter.build_trace(
            normalized_ir,
            primary_candidate,
            verification,
            selected_method_id=selected_method_id,
        )

        return UniversalSolveResult(
            ir=normalized_ir,
            candidate=primary_candidate,
            verification=verification,
            trace=trace,
        )
