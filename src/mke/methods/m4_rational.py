"""Method M4: Rational Equation solver with domain preservation and extraneous root filtering."""

from typing import List, Set
import sympy

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.models.domain import is_proven_real_number, check_root_satisfaction
from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, ObligationStatus
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


class RationalEquationMethod(BaseMethod):
    """M4: RATIONAL_EQUATION - Solves P(x)/Q(x) = 0 preserving Q(x) != 0 domain constraints."""

    method_id = MethodId.M4_RATIONAL_EQUATION
    version = "1.0.0"
    name = "Rational Equation Method"
    description = "Clears denominators to solve polynomial numerator while strictly filtering extraneous roots."
    scope_limits = "Rational equations with polynomial numerator and denominator of degree <= 4."

    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        # Structural guard: equation must contain rational terms / fractions
        is_rational = norm_eq.is_rational
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_CONTAINS_FRACTION",
                passed=is_rational,
                message="Equation contains algebraic fraction(s) with denominators" if is_rational else "Equation has no fractions; polynomial methods should be used",
                details={"is_rational": is_rational},
            )
        )

        return guards

    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        has_conditions = len(norm_eq.domain.conditions) > 0 or not norm_eq.domain.is_all_reals()
        guards.append(
            GuardResult(
                guard_name="ORIGINAL_DOMAIN_CONSTRAINTS_DEFINED",
                passed=True,
                message=f"Original domain constraints recorded: {norm_eq.domain.format_domain()}",
                details={"domain": norm_eq.domain.format_domain(), "conditions_count": len(norm_eq.domain.conditions)},
            )
        )

        return guards

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        if not norm_eq.is_rational:
            return MethodAdmissibility.NOT_APPLICABLE
        return MethodAdmissibility.APPLICABLE

    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        # Case 1: Identity on domain, e.g. (x-2)/(x-2) = 1
        if norm_eq.is_identity:
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                is_identity_on_domain=True,
                notes=[
                    f"Cleared equation reduces to 0 = 0 (identity).",
                    f"Solution set is the ENTIRE original domain: {norm_eq.domain.format_domain()}.",
                ],
            )

        # Case 2: Contradiction, e.g. 1/(x-2) = 0 => 1 = 0
        if norm_eq.is_contradiction or norm_eq.numerator_poly is None:
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                is_contradiction=True,
                notes=["Cleared numerator is non-zero constant; no solutions exist."],
            )

        # Case 3: Solve cleared polynomial numerator P(x) = 0
        numer_poly = norm_eq.numerator_poly
        deg = numer_poly.degree()
        raw_roots: Set[sympy.Basic] = set()

        is_exhaustive_enumeration = True
        solveset_type = "PolynomialFormulas"

        if deg == 1:
            a = numer_poly.coeff_monomial((1,))
            b = numer_poly.coeff_monomial((0,))
            raw_roots.add(sympy.simplify(-b / a))
            is_exhaustive_enumeration = True
        elif deg == 2:
            a = numer_poly.coeff_monomial((2,))
            b = numer_poly.coeff_monomial((1,))
            c = numer_poly.coeff_monomial((0,))
            delta = b**2 - 4 * a * c
            if delta == 0:
                raw_roots.add(sympy.simplify(-b / (2 * a)))
            elif delta > 0:
                raw_roots.add(sympy.simplify((-b + sympy.sqrt(delta)) / (2 * a)))
                raw_roots.add(sympy.simplify((-b - sympy.sqrt(delta)) / (2 * a)))
            is_exhaustive_enumeration = True
        else:
            # General polynomial solve via solveset for degree <= 4
            sym_sol = sympy.solveset(sympy.Eq(numer_poly.as_expr(), 0), X_SYM, domain=sympy.S.Reals)
            solveset_type = type(sym_sol).__name__

            if sym_sol is sympy.EmptySet or sym_sol == sympy.EmptySet:
                raw_roots = set()
                is_exhaustive_enumeration = True
            elif isinstance(sym_sol, sympy.FiniteSet):
                raw_roots = set()
                all_proven_real = True
                for r in sym_sol:
                    if is_proven_real_number(r):
                        raw_roots.add(r)
                    else:
                        all_proven_real = False
                is_exhaustive_enumeration = all_proven_real
            elif isinstance(sym_sol, sympy.Intersection):
                # Symbolic intersection with Reals, e.g. Intersection(Reals, FiniteSet(...))
                raw_roots = set()
                for arg in sym_sol.args:
                    if isinstance(arg, sympy.FiniteSet):
                        for r in arg:
                            if is_proven_real_number(r):
                                raw_roots.add(r)
                # Unresolved intersection: SymPy could not symbolically prove exhaustive real simplification
                is_exhaustive_enumeration = False
            elif isinstance(sym_sol, sympy.Union):
                raw_roots = set()
                for arg in sym_sol.args:
                    if isinstance(arg, sympy.FiniteSet):
                        for r in arg:
                            if is_proven_real_number(r):
                                raw_roots.add(r)
                is_exhaustive_enumeration = False
            elif isinstance(sym_sol, (sympy.ConditionSet, sympy.ImageSet, sympy.ComplexRegion)):
                raw_roots = set()
                is_exhaustive_enumeration = False
            else:
                raw_roots = set()
                is_exhaustive_enumeration = False

        # Filter roots by original domain
        valid_roots: List[sympy.Basic] = []
        rejected: List[dict] = []
        notes = [f"Roots of cleared numerator: {[str(r) for r in raw_roots]}"]

        def _safe_sort_key(val: sympy.Basic):
            try:
                if val.is_real:
                    return (0, float(val.evalf()))
            except Exception:
                pass
            return (1, str(val))

        for r in sorted(list(raw_roots), key=_safe_sort_key):
            if norm_eq.domain.contains(r):
                valid_roots.append(r)
                notes.append(f"Root x = {r} ACCEPTED (in domain {norm_eq.domain.format_domain()})")
            else:
                rejected.append({
                    "root": str(r),
                    "reason": f"Violates domain constraint: {norm_eq.domain.format_domain()}",
                })
                notes.append(f"Root x = {r} REJECTED (extraneous root / denominator zero)")

        return MethodSolveOutput(
            method_id=self.method_id,
            candidate_roots=valid_roots,
            parameters={
                "cleared_numerator": str(numer_poly.as_expr()),
                "unfiltered_roots": [str(r) for r in raw_roots],
                "extraneous_roots": [rj["root"] for rj in rejected],
                "is_exhaustive_enumeration": is_exhaustive_enumeration,
                "solveset_type": solveset_type,
            },
            notes=notes,
            rejected_intermediates=rejected,
        )

    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        obligations: List[ProofObligation] = []

        # 1. Check extraneous roots recorded
        extraneous = solve_output.parameters.get("extraneous_roots", [])
        if extraneous:
            for ext in extraneous:
                obligations.append(
                    ProofObligation(
                        obligation_id=ObligationId.ORIGINAL_DOMAIN,
                        status=ObligationStatus.PASS,
                        description=f"Extraneous root check for candidate x = {ext}",
                        evidence=f"Root x = {ext} makes at least one original denominator zero. Correctly detected and excluded from solution set.",
                    )
                )

        # 2. Check valid roots
        for root in solve_output.candidate_roots:
            in_dom = norm_eq.domain.contains(root)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ORIGINAL_DOMAIN,
                    status=ObligationStatus.PASS if in_dom else ObligationStatus.FAIL,
                    description=f"Verify root x = {root} lies in original domain",
                    evidence=f"Root x = {root} belongs to domain {norm_eq.domain.format_domain()}",
                )
            )

            # Check substitution
            sub_passes, sub_res = check_root_satisfaction(norm_eq.numerator_sym, root)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ROOT_SUBSTITUTION,
                    status=ObligationStatus.PASS if sub_passes else ObligationStatus.FAIL,
                    description=f"Substitute root x = {root} into cleared numerator",
                    evidence=f"Numerator evaluated at {root} is {sub_res}",
                )
            )

        # 3. COMPLETENESS
        is_exhaustive = solve_output.parameters.get("is_exhaustive_enumeration", True)
        if norm_eq.domain.is_undetermined:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.UNRESOLVED,
                    description="Completeness of rational equation solution set",
                    evidence="Original domain is undetermined; cannot prove completeness on R.",
                )
            )
        elif not is_exhaustive:
            solveset_type = solve_output.parameters.get("solveset_type", "Unknown")
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.UNRESOLVED,
                    description="Completeness of rational equation solution set",
                    evidence=f"Polynomial solver returned symbolic representation '{solveset_type}' which could not be exhaustively proven complete over R. Found candidate roots may be incomplete.",
                )
            )
        elif solve_output.is_identity_on_domain:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Completeness of rational equation solution set",
                    evidence=f"Rational equation is an identity 0/Q(x)=0 on domain {norm_eq.domain.format_domain()}; all domain points are solutions.",
                )
            )
        else:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Completeness of rational equation solution set",
                    evidence="By theorem: on domain {x | Q(x) != 0}, P(x)/Q(x) = 0 <=> P(x) = 0. All roots of P(x) in domain were preserved and all extraneous roots eliminated.",
                )
            )

        return obligations
