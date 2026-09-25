"""Original Mathematical Domain representation and condition tracking."""

from __future__ import annotations
from fractions import Fraction
from typing import Any, Dict, List, Optional, Set, Union
import sympy

from mke.models.enums import ExactVerificationStatus
from mke.models.evidence import ExactProofCertificate


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


def verify_root_exact(
    expr: sympy.Basic, r: sympy.Basic | Fraction | int | float | str, var: sympy.Symbol | None = None
) -> ExactProofCertificate:
    """Rigorous verification gate deciding whether candidate root r satisfies expr == 0.

    Requirements:
    1. Zero epsilon tolerance for proof: |residual| < epsilon is NEVER sufficient for EXACT_PASS.
    2. Rational arithmetic: exact decision in Q (e.g. Rational(1, 10**26) -> EXACT_FAIL).
    3. Algebraic reduction: exact algebraic zero via substitution, cancel(), expand(), radsimp().
    4. Provable numerical refutation: if |residual| > 1e-6, candidate is provably not a root (EXACT_FAIL).
    5. Safe unresolved fallback: if numerical residue is small but algebraic proof cannot reduce to 0
       within limits, returns UNRESOLVED (fail-closed).
    """
    if var is None:
        var = sympy.Symbol("x", real=True)

    # 1. Normalize candidate r safely
    if isinstance(r, int):
        sym_r = sympy.Integer(r)
    elif isinstance(r, Fraction):
        sym_r = sympy.Rational(r.numerator, r.denominator)
    elif isinstance(r, float):
        try:
            frac = Fraction(str(r))
            sym_r = sympy.Rational(frac.numerator, frac.denominator)
        except Exception:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_FAIL,
                is_exact_pass=False,
                candidate_root=str(r),
                residue=str(r),
                method="FLOAT_CONVERSION_FAILURE",
                diagnostic="Float cannot be converted to exact rational",
            )
    elif isinstance(r, str):
        try:
            frac = Fraction(r.strip())
            sym_r = sympy.Rational(frac.numerator, frac.denominator)
        except Exception:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_FAIL,
                is_exact_pass=False,
                candidate_root=str(r),
                residue=str(r),
                method="STRING_PARSE_FAILURE",
                diagnostic="String cannot be parsed as exact rational",
            )
    elif isinstance(r, sympy.Basic):
        sym_r = r
    else:
        return ExactProofCertificate(
            status=ExactVerificationStatus.EXACT_FAIL,
            is_exact_pass=False,
            candidate_root=str(r),
            residue=str(r),
            method="UNSUPPORTED_TYPE",
            diagnostic=f"Unsupported root type: {type(r)}",
        )

    # 2. Reject non-real numbers (complex units, free variables)
    if not is_proven_real_number(sym_r):
        return ExactProofCertificate(
            status=ExactVerificationStatus.EXACT_FAIL,
            is_exact_pass=False,
            candidate_root=str(sym_r),
            residue=str(sym_r),
            method="REJECT_NON_REAL",
            diagnostic="Candidate is not a provably real concrete number (imaginary unit or free variable detected)",
        )

    # 3. Direct exact substitution
    try:
        raw_sub = expr.subs(var, sym_r)
    except Exception as e:
        return ExactProofCertificate(
            status=ExactVerificationStatus.UNRESOLVED,
            is_exact_pass=False,
            candidate_root=str(sym_r),
            residue=str(e),
            method="SUBSTITUTION_ERROR",
            diagnostic=f"Error evaluating substitution: {str(e)}",
        )

    if raw_sub == 0 or getattr(raw_sub, "is_zero", None) is True:
        return ExactProofCertificate(
            status=ExactVerificationStatus.EXACT_PASS,
            is_exact_pass=True,
            candidate_root=str(sym_r),
            residue="0",
            method="EXACT_ALGEBRAIC_ZERO",
        )

    # 4. Exact Rational Field Decision
    if (sym_r.is_rational or isinstance(sym_r, (sympy.Integer, sympy.Rational))) and (
        raw_sub.is_rational or isinstance(raw_sub, (sympy.Integer, sympy.Rational))
    ):
        if raw_sub == 0:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_PASS,
                is_exact_pass=True,
                candidate_root=str(sym_r),
                residue="0",
                method="RATIONAL_FIELD_EVAL",
            )
        else:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_FAIL,
                is_exact_pass=False,
                candidate_root=str(sym_r),
                residue=str(raw_sub),
                method="RATIONAL_FIELD_EVAL",
                diagnostic=f"Exact rational non-zero residue: {raw_sub}",
            )

    # 5. Exact Algebraic Reduction (for radicals and algebraic numbers)
    try:
        canceled = sympy.cancel(raw_sub)
        if canceled == 0 or getattr(canceled, "is_zero", None) is True:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_PASS,
                is_exact_pass=True,
                candidate_root=str(sym_r),
                residue="0",
                method="ALGEBRAIC_CANCEL_ZERO",
            )
    except Exception:
        pass

    try:
        expanded = sympy.expand(raw_sub)
        if expanded == 0 or getattr(expanded, "is_zero", None) is True:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_PASS,
                is_exact_pass=True,
                candidate_root=str(sym_r),
                residue="0",
                method="ALGEBRAIC_EXPAND_ZERO",
            )
    except Exception:
        pass

    try:
        rad = sympy.radsimp(raw_sub)
        if rad == 0 or getattr(rad, "is_zero", None) is True:
            return ExactProofCertificate(
                status=ExactVerificationStatus.EXACT_PASS,
                is_exact_pass=True,
                candidate_root=str(sym_r),
                residue="0",
                method="ALGEBRAIC_RADSIMP_ZERO",
            )
    except Exception:
        pass

    # 6. Unresolved Numerical Observation (evalf is for triage, not exact proof)
    try:
        val = raw_sub.evalf(50)
        if abs(val) > 1e-6:
            return ExactProofCertificate(
                status=ExactVerificationStatus.UNRESOLVED,
                is_exact_pass=False,
                candidate_root=str(sym_r),
                residue=str(raw_sub),
                method="NUMERICAL_OBSERVATION_UNRESOLVED",
                diagnostic=f"Numerical evaluation suggests non-zero residue (|{val}| > 1e-6), but without certified algebraic proof or bounded interval error, exact proof status is UNRESOLVED.",
            )
    except Exception:
        pass

    # 7. Fail-Closed Unresolved: Near-zero residual without exact symbolic certificate
    return ExactProofCertificate(
        status=ExactVerificationStatus.UNRESOLVED,
        is_exact_pass=False,
        candidate_root=str(sym_r),
        residue=str(raw_sub),
        method="UNRESOLVED_SYMBOLIC_RADICAL",
        diagnostic="Residual is near zero, but exact symbolic reduction could not prove 0 within algebraic gate limits. Epsilon approximation is strictly prohibited from granting proof.",
    )


def check_root_satisfaction(
    expr: sympy.Basic, r: sympy.Basic | Fraction | int | float | str, var: sympy.Symbol | None = None
) -> tuple[bool, sympy.Basic]:
    """Compatibility wrapper returning (bool, residue).

    Bool is True ONLY on EXACT_PASS.
    Residue is computed directly from typed candidate or safe rational parsing.
    Untrusted or ungrammatical inputs return (False, sympy.nan) without executing or sympifying code.
    """
    cert = verify_root_exact(expr, r, var)
    if cert.is_exact_pass:
        return True, sympy.Integer(0)

    # Safely convert r to typed candidate for direct evaluation without sympify(str)
    sym_r: Optional[sympy.Basic] = None
    if isinstance(r, int):
        sym_r = sympy.Integer(r)
    elif isinstance(r, Fraction):
        sym_r = sympy.Rational(r.numerator, r.denominator)
    elif isinstance(r, float):
        try:
            frac = Fraction(str(r))
            sym_r = sympy.Rational(frac.numerator, frac.denominator)
        except Exception:
            sym_r = None
    elif isinstance(r, str):
        # Whitelisted parsing of integer / rational fraction ONLY.
        # NEVER call sympify, parse_expr, or eval!
        try:
            frac = Fraction(r.strip())
            sym_r = sympy.Rational(frac.numerator, frac.denominator)
        except (ValueError, ZeroDivisionError, TypeError):
            sym_r = None
    elif isinstance(r, sympy.Basic):
        sym_r = r

    if sym_r is not None and is_proven_real_number(sym_r):
        try:
            target_var = var if var is not None else sympy.Symbol("x", real=True)
            raw_sub = expr.subs(target_var, sym_r)
            if isinstance(raw_sub, sympy.Basic):
                return False, raw_sub
            return False, sympy.Integer(raw_sub) if isinstance(raw_sub, int) else sympy.nan
        except Exception:
            return False, sympy.nan

    # Non-grammatical string or unsupported type: return non-executable sentinel
    return False, sympy.nan



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
