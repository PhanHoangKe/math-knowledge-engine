"""Catalogue of mathematical equation solving methods."""

from typing import Dict, List, Tuple

from mke.methods.base import BaseMethod
from mke.methods.m1_linear import LinearEquationMethod
from mke.methods.m2_quadratic import QuadraticFormulaMethod
from mke.methods.m3_factorization import FactorizationMethod
from mke.methods.m4_rational import RationalEquationMethod
from mke.methods.m5_biquadratic import BiquadraticSubstitutionMethod
from mke.models.enums import MethodAdmissibility, MethodId
from mke.models.evidence import GuardResult
from mke.parsing.normalizer import NormalizedEquation


class MethodCatalogue:
    """Registry and query interface for all supported mathematical methods."""

    def __init__(self):
        self._methods: Dict[MethodId, BaseMethod] = {
            MethodId.M1_LINEAR_EQUATION: LinearEquationMethod(),
            MethodId.M2_QUADRATIC_FORMULA: QuadraticFormulaMethod(),
            MethodId.M3_FACTORIZATION: FactorizationMethod(),
            MethodId.M4_RATIONAL_EQUATION: RationalEquationMethod(),
            MethodId.M5_BIQUADRATIC_SUBSTITUTION: BiquadraticSubstitutionMethod(),
        }

    def get_method(self, method_id: MethodId | str) -> BaseMethod:
        if isinstance(method_id, str):
            for k in self._methods:
                if k.value == method_id:
                    return self._methods[k]
            raise KeyError(f"Method '{method_id}' not found in catalogue.")
        return self._methods[method_id]

    def list_methods(self) -> List[BaseMethod]:
        return list(self._methods.values())

    def find_applicable_methods(
        self, norm_eq: NormalizedEquation
    ) -> List[Tuple[BaseMethod, MethodAdmissibility, List[GuardResult]]]:
        """Evaluate admissibility and guards for all catalogue methods on an equation."""
        results = []
        for method in self._methods.values():
            struct_guards = method.check_structural_guards(norm_eq)
            math_guards = method.check_mathematical_guards(norm_eq)
            all_guards = struct_guards + math_guards
            admissibility = method.evaluate_admissibility(norm_eq)
            results.append((method, admissibility, all_guards))
        return results


CATALOGUE = MethodCatalogue()
