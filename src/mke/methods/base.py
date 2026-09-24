"""Base abstract class for all mathematical solving methods."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import sympy

from mke.models.enums import MethodAdmissibility, MethodId
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation


@dataclass
class MethodSolveOutput:
    """Raw output of solving an equation instance using a specific method."""

    method_id: MethodId
    candidate_roots: List[sympy.Basic] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_identity_on_domain: bool = False
    is_contradiction: bool = False
    notes: List[str] = field(default_factory=list)
    rejected_intermediates: List[Dict[str, Any]] = field(default_factory=list)


class BaseMethod(ABC):
    """Abstract mathematical method template."""

    method_id: MethodId
    version: str = "1.0.0"
    name: str
    description: str
    scope_limits: str

    @abstractmethod
    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        """Check syntax, degree, and algebraic structure requirements."""
        pass

    @abstractmethod
    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        """Check algebraic domain, non-degeneracy, and coefficient conditions."""
        pass

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        """Determine whether the method is APPLICABLE, NOT_APPLICABLE, or OUT_OF_SCOPE."""
        struct_guards = self.check_structural_guards(norm_eq)
        if any(not g.passed for g in struct_guards):
            return MethodAdmissibility.NOT_APPLICABLE

        math_guards = self.check_mathematical_guards(norm_eq)
        if any(not g.passed for g in math_guards):
            return MethodAdmissibility.NOT_APPLICABLE

        return MethodAdmissibility.APPLICABLE

    @abstractmethod
    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        """Execute the method algorithmically on the normalized equation."""
        pass

    @abstractmethod
    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        """Verify all proof obligations (domain, equivalence, root substitution, completeness)."""
        pass
