from fractions import Fraction
from typing import List, Set, Tuple
import sympy

from mke.models.enums import TransferValidity
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.parser import Parser
from mke.parsing.sympy_converter import ast_to_sympy, X_SYM


def safe_parse_candidate_root(r_raw: sympy.Basic | str | int | float | Fraction) -> sympy.Basic:
    """Parse candidate root safely using exact constructors or safe AST parsing without sympify()."""
    if isinstance(r_raw, sympy.Basic):
        return r_raw
    if isinstance(r_raw, int):
        return sympy.Integer(r_raw)
    if isinstance(r_raw, Fraction):
        return sympy.Rational(r_raw.numerator, r_raw.denominator)
    if isinstance(r_raw, float):
        frac = Fraction(str(r_raw))
        return sympy.Rational(frac.numerator, frac.denominator)
    if isinstance(r_raw, str):
        s = r_raw.strip()
        try:
            frac = Fraction(s)
            return sympy.Rational(frac.numerator, frac.denominator)
        except Exception:
            pass
        # Parse expression safely via Parser and ast_to_sympy (NO sympify, eval, or exec)
        parser = Parser.from_text(s)
        expr_ast = parser.parse_expression()
        return ast_to_sympy(expr_ast)
    raise TypeError(f"Unsupported candidate root type: {type(r_raw)}")


def audit_solution_transfer(
    target_norm_eq: NormalizedEquation,
    source_candidate_roots: List[sympy.Basic | str | int | float],
    source_problem_id: str = "SOURCE_INSTANCE",
) -> Tuple[TransferValidity, List[str], List[str]]:
    """Audit the transfer of candidate roots from a source problem to a target equation.

    Catches UNSAFE_COPY where solutions of a relaxed or pre-conditioned problem (e.g. T1: x^2-5x+6=0)
    are blindly copied to a constrained problem (e.g. T2: (x^2-5x+6)/(x-2)=0).
    """
    valid_roots: List[str] = []
    rejected_roots: List[str] = []

    for r_raw in source_candidate_roots:
        try:
            sym_r = safe_parse_candidate_root(r_raw)
        except Exception as e:
            rejected_roots.append(f"Candidate root '{r_raw}' rejected: unsafe or unparseable ({e})")
            continue
        # Check domain constraint of target problem
        if not target_norm_eq.domain.contains(sym_r):
            rejected_roots.append(
                f"Root x = {sym_r} violates target domain: excluded by {target_norm_eq.domain.format_domain()}"
            )
            continue

        # Check equation satisfaction
        sub_res = sympy.simplify(target_norm_eq.numerator_sym.subs(X_SYM, sym_r))
        if sub_res == 0:
            valid_roots.append(str(sym_r))
        else:
            rejected_roots.append(
                f"Root x = {sym_r} does not satisfy target numerator: residue = {sub_res}"
            )

    if rejected_roots:
        # Transfer included roots that are invalid for the target!
        return (TransferValidity.UNSAFE_COPY, valid_roots, rejected_roots)

    return (TransferValidity.REINSTANTIATED_VALID, valid_roots, rejected_roots)
