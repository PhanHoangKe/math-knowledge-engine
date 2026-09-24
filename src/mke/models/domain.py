"""Original Mathematical Domain representation and condition tracking."""

from __future__ import annotations
from fractions import Fraction
from typing import Any, Dict, List, Set, Union
import sympy


class DomainCondition:
    """Represents an individual domain constraint (e.g., denominator != 0)."""

    def __init__(
        self,
        raw_expression_str: str,
        condition_str: str,
        excluded_values: Set[Union[Fraction, sympy.Basic]],
        source_description: str = "division_denominator_nonzero",
    ):
        self.raw_expression_str = raw_expression_str
        self.condition_str = condition_str
        self.excluded_values = set(excluded_values)
        self.source_description = source_description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_expression": self.raw_expression_str,
            "condition": self.condition_str,
            "excluded_values": [str(v) for v in sorted(self.excluded_values, key=str)],
            "source_description": self.source_description,
        }

    def __repr__(self) -> str:
        return f"DomainCondition('{self.condition_str}', excluded={self.excluded_values})"


class OriginalDomain:
    """Rigorous representation of the domain over R for an equation or expression.

    Crucial Requirement: The original domain is extracted from the UNREDUCED AST
    before any algebraic simplifications or denominator cancellations.
    """

    def __init__(self, conditions: List[DomainCondition] | None = None):
        self.conditions: List[DomainCondition] = conditions or []
        self._excluded_values: Set[Union[Fraction, sympy.Basic]] = set()
        for cond in self.conditions:
            self._excluded_values.update(cond.excluded_values)

    @property
    def excluded_values(self) -> Set[Union[Fraction, sympy.Basic]]:
        return set(self._excluded_values)

    def add_condition(self, condition: DomainCondition) -> None:
        self.conditions.append(condition)
        self._excluded_values.update(condition.excluded_values)

    def is_all_reals(self) -> bool:
        return len(self._excluded_values) == 0

    def contains(self, x_val: Union[Fraction, int, float, sympy.Basic]) -> bool:
        """Check whether a real candidate value x_val lies within the domain."""
        sym_val = sympy.sympify(x_val)
        for excl in self._excluded_values:
            sym_excl = sympy.sympify(excl)
            try:
                if bool(sympy.Eq(sym_val, sym_excl)) or abs(float(sym_val) - float(sym_excl)) < 1e-12:
                    return False
            except (TypeError, ValueError):
                if sym_val == sym_excl:
                    return False
        return True

    def format_domain(self) -> str:
        """Human-readable representation of the domain."""
        if not self._excluded_values:
            return "R"
        sorted_excl = sorted([str(v) for v in self._excluded_values])
        return f"R \\ {{{', '.join(sorted_excl)}}}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_str": self.format_domain(),
            "is_all_reals": self.is_all_reals(),
            "excluded_values": [str(v) for v in sorted(self._excluded_values, key=str)],
            "conditions": [c.to_dict() for c in self.conditions],
        }

    def __repr__(self) -> str:
        return f"OriginalDomain({self.format_domain()})"
