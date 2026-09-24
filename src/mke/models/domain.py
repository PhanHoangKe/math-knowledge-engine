"""Original Mathematical Domain representation and condition tracking."""

from __future__ import annotations
from fractions import Fraction
from typing import Any, Dict, List, Set, Union
import sympy


def is_proven_real_number(sym_val: sympy.Basic) -> bool:
    """Verify strictly whether sym_val is a concrete real number with no free variables or imaginary part.

    Rejects:
    - Complex numbers (e.g. sympy.I, 1 + 2*I)
    - Free symbols or algebraic expressions with variables (e.g. x, y, x + 1)
    - Non-number objects
    """
    if not isinstance(sym_val, sympy.Basic):
        return False

    # 1. Reject expressions with free variables
    if len(sym_val.free_symbols) > 0:
        return False

    # 2. Fast check for standard realness
    if sym_val.is_real is True:
        return True
    if sym_val.is_real is False:
        return False

    # 3. Check for explicit imaginary unit
    if sym_val.has(sympy.I):
        try:
            im_val = sympy.im(sym_val.evalf(50))
            if abs(im_val) > 1e-25:
                return False
        except Exception:
            return False

    # 4. Check numerical evaluation
    try:
        val_evalf = sym_val.evalf(50)
        if val_evalf.is_real is True:
            return True
        im_val = sympy.im(val_evalf)
        if abs(im_val) < 1e-25 and not sympy.re(val_evalf).is_infinite:
            return True
        return False
    except Exception:
        return False


def check_root_satisfaction(
    expr: sympy.Basic, r: sympy.Basic, var: sympy.Symbol | None = None
) -> tuple[bool, sympy.Basic]:
    """Check whether root r satisfies polynomial/expression expr == 0.

    Uses exact evaluation and high-precision numerical zero detection (evalf(50) < 1e-25)
    to avoid catastrophic hangs in sympy.simplify() on nested radicals (e.g. Ferrari quartic roots).
    """
    if var is None:
        var = sympy.Symbol("x", real=True)
    raw_sub = expr.subs(var, r)
    if raw_sub == 0 or getattr(raw_sub, "is_zero", None) is True:
        return True, sympy.Integer(0)
    try:
        val = raw_sub.evalf(50)
        if abs(val) < 1e-25:
            return True, sympy.Integer(0)
    except Exception:
        pass
    try:
        simp = sympy.simplify(raw_sub)
        if simp == 0 or getattr(simp, "is_zero", None) is True:
            return True, sympy.Integer(0)
        return False, simp
    except Exception:
        return False, raw_sub


class DomainCondition:
    """Represents an individual domain constraint (e.g., denominator != 0)."""

    def __init__(
        self,
        raw_expression_str: str,
        condition_str: str,
        excluded_values: Set[Union[Fraction, sympy.Basic]],
        source_description: str = "division_denominator_nonzero",
        is_empty_domain: bool = False,
        is_undetermined: bool = False,
    ):
        self.raw_expression_str = raw_expression_str
        self.condition_str = condition_str
        self.excluded_values = set(excluded_values)
        self.source_description = source_description
        self.is_empty_domain = is_empty_domain
        self.is_undetermined = is_undetermined

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_expression": self.raw_expression_str,
            "condition": self.condition_str,
            "excluded_values": [str(v) for v in sorted(self.excluded_values, key=str)],
            "source_description": self.source_description,
            "is_empty_domain": self.is_empty_domain,
            "is_undetermined": self.is_undetermined,
        }

    def __repr__(self) -> str:
        return f"DomainCondition('{self.condition_str}', excluded={self.excluded_values}, empty={self.is_empty_domain})"


class OriginalDomain:
    """Rigorous representation of the domain over R for an equation or expression.

    Crucial Requirement: The original domain is extracted from the UNREDUCED AST
    before any algebraic simplifications or denominator cancellations.
    """

    def __init__(
        self,
        conditions: List[DomainCondition] | None = None,
        is_empty_domain: bool = False,
        is_undetermined: bool = False,
    ):
        self.conditions: List[DomainCondition] = conditions or []
        self._excluded_values: Set[Union[Fraction, sympy.Basic]] = set()
        self.is_empty_domain = is_empty_domain or any(c.is_empty_domain for c in self.conditions)
        self.is_undetermined = is_undetermined or any(c.is_undetermined for c in self.conditions)
        for cond in self.conditions:
            self._excluded_values.update(cond.excluded_values)

    @property
    def excluded_values(self) -> Set[Union[Fraction, sympy.Basic]]:
        return set(self._excluded_values)

    def add_condition(self, condition: DomainCondition) -> None:
        self.conditions.append(condition)
        if condition.is_empty_domain:
            self.is_empty_domain = True
        if condition.is_undetermined:
            self.is_undetermined = True
        self._excluded_values.update(condition.excluded_values)

    def is_all_reals(self) -> bool:
        if self.is_empty_domain or self.is_undetermined:
            return False
        return len(self._excluded_values) == 0

    def contains(self, x_val: Union[Fraction, int, float, str, sympy.Basic]) -> bool:
        """Check whether a real candidate value x_val lies within the domain.

        Exact mathematical comparison without float epsilon conflation,
        strictly avoiding unsafe string sympify(), and rejecting non-real / complex values.
        """
        if self.is_empty_domain or self.is_undetermined:
            return False

        # Convert x_val safely to exact SymPy/Fraction representation
        if isinstance(x_val, Fraction):
            sym_val: sympy.Basic = sympy.Rational(x_val.numerator, x_val.denominator)
        elif isinstance(x_val, int):
            sym_val = sympy.Integer(x_val)
        elif isinstance(x_val, sympy.Basic):
            sym_val = x_val
        elif isinstance(x_val, float):
            try:
                frac = Fraction(str(x_val))
                sym_val = sympy.Rational(frac.numerator, frac.denominator)
            except Exception:
                return False
        elif isinstance(x_val, str):
            try:
                frac = Fraction(x_val.strip())
                sym_val = sympy.Rational(frac.numerator, frac.denominator)
            except Exception:
                # Do NOT call sympify(str) on untrusted strings
                return False
        else:
            return False

        # Candidate must be provably a real concrete number (reject complex, symbols, etc.)
        if not is_proven_real_number(sym_val):
            return False

        for excl in self._excluded_values:
            if isinstance(excl, Fraction):
                sym_excl: sympy.Basic = sympy.Rational(excl.numerator, excl.denominator)
            elif isinstance(excl, int):
                sym_excl = sympy.Integer(excl)
            elif isinstance(excl, sympy.Basic):
                sym_excl = excl
            else:
                sym_excl = excl

            # 1. Exact equality comparison
            if sym_val == sym_excl:
                return False

            # 2. Exact algebraic difference simplification
            try:
                diff = sympy.simplify(sym_val - sym_excl)
                if diff == 0 or diff.is_zero is True:
                    return False
            except Exception:
                pass

        return True

    def format_domain(self) -> str:
        """Human-readable representation of the domain."""
        if self.is_empty_domain:
            return "\\emptyset"
        if self.is_undetermined:
            return "UNDETERMINED"
        if not self._excluded_values:
            return "R"
        sorted_excl = sorted([str(v) for v in self._excluded_values])
        return f"R \\ {{{', '.join(sorted_excl)}}}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_str": self.format_domain(),
            "is_all_reals": self.is_all_reals(),
            "is_empty_domain": self.is_empty_domain,
            "is_undetermined": self.is_undetermined,
            "excluded_values": [str(v) for v in sorted(self._excluded_values, key=str)],
            "conditions": [c.to_dict() for c in self.conditions],
        }

    def __repr__(self) -> str:
        return f"OriginalDomain({self.format_domain()})"
