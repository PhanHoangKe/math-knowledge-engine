"""Adapter registry and deterministic dispatch service for domain adapters."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from mke_product.coverage.adapters import DomainAdapter
from mke_product.coverage.contracts import ProblemIR, ProblemKind


class AdapterRegistryError(Exception):
    """Base exception for adapter registry operations."""
    pass


class DuplicateAdapterError(AdapterRegistryError):
    """Raised when registering an adapter with an already existing adapter_id."""
    pass


class UnsupportedProblemError(AdapterRegistryError):
    """Raised when no registered adapter can handle the given ProblemIR."""
    pass


class AmbiguousAdapterError(AdapterRegistryError):
    """Raised when multiple adapters claim capability to handle the same ProblemIR."""
    pass


class AdapterRegistry:
    """Deterministic, fail-closed registry managing domain adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, DomainAdapter] = {}
        self._registration_order: List[str] = []

    def register(self, adapter: DomainAdapter) -> None:
        """Register a domain adapter. Rejects duplicate adapter IDs."""
        if adapter.adapter_id in self._adapters:
            raise DuplicateAdapterError(
                f"Adapter with ID {adapter.adapter_id!r} is already registered."
            )
        self._adapters[adapter.adapter_id] = adapter
        self._registration_order.append(adapter.adapter_id)

    def get_adapter(self, adapter_id: str) -> Optional[DomainAdapter]:
        """Lookup an adapter by ID."""
        return self._adapters.get(adapter_id)

    def list_adapters(self) -> Tuple[DomainAdapter, ...]:
        """Return all registered adapters in deterministic registration order."""
        return tuple(self._adapters[aid] for aid in self._registration_order)

    def adapters_for_kind(self, kind: ProblemKind) -> Tuple[DomainAdapter, ...]:
        """Return all registered adapters declaring support for the given ProblemKind."""
        return tuple(
            self._adapters[aid]
            for aid in self._registration_order
            if kind in self._adapters[aid].supported_problem_kinds
        )

    def resolve(self, ir: ProblemIR) -> DomainAdapter:
        """Resolve exactly one handling adapter for the given ProblemIR.
        
        Fail-closed rules:
        - Filters registered adapters supporting ir.problem_kind.
        - Evaluates adapter.can_handle(ir).
        - If 0 matching adapters -> raises UnsupportedProblemError.
        - If >1 matching adapters -> raises AmbiguousAdapterError (no silent first-match).
        """
        candidate_adapters = self.adapters_for_kind(ir.problem_kind)
        matching_adapters: List[DomainAdapter] = []

        for adapter in candidate_adapters:
            if adapter.can_handle(ir):
                matching_adapters.append(adapter)

        if not matching_adapters:
            raise UnsupportedProblemError(
                f"No registered domain adapter can handle ProblemIR with id={ir.problem_id!r}, "
                f"kind={ir.problem_kind.value!r}."
            )

        if len(matching_adapters) > 1:
            matched_ids = [a.adapter_id for a in matching_adapters]
            raise AmbiguousAdapterError(
                f"Ambiguous adapter resolution for ProblemIR id={ir.problem_id!r}: "
                f"multiple adapters claim capability: {matched_ids}."
            )

        return matching_adapters[0]
