"""Solution transfer auditor to prevent unsafe copying of solutions across problems."""

from typing import List, Set, Tuple
import sympy

from mke.models.enums import TransferValidity
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


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
        sym_r = sympy.sympify(r_raw)
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
