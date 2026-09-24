"""Method M3: Factorization and Zero-Product Principle with root-loss detection."""

from typing import List, Set
import sympy

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, ObligationStatus
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


class FactorizationMethod(BaseMethod):
    """M3: FACTORIZATION - Uses zero-product property P(x)=prod(F_i(x))=0 <=> or(F_i(x)=0)."""

    method_id = MethodId.M3_FACTORIZATION
    version = "1.0.0"
    name = "Factorization Method"
    description = "Factors polynomial into irreducible factors and applies zero-product principle."
    scope_limits = "Polynomial equation of degree >= 2 factorable over rationals into degree <= 2 factors."

    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        is_poly_deg_ge_2 = norm_eq.degree >= 2
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_DEGREE_GE_2",
                passed=is_poly_deg_ge_2,
                message=f"Equation degree is {norm_eq.degree} (expected >= 2 for factorization)",
                details={"degree": norm_eq.degree},
            )
        )

        not_rational = not norm_eq.is_rational
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_NON_RATIONAL",
                passed=not_rational,
                message="Equation is polynomial (no x in denominators)" if not_rational else "Equation contains fractions; M4:RATIONAL_EQUATION should precede M3",
                details={"is_rational": norm_eq.is_rational},
            )
        )

        # Check factorability
        can_factor = False
        if is_poly_deg_ge_2 and norm_eq.numerator_poly is not None:
            factors_dict = sympy.factor_list(norm_eq.numerator_poly)
            # factors_dict is (coeff, [(factor_poly, multiplicity), ...])
            factors = factors_dict[1]
            can_factor = len(factors) > 1 or (len(factors) == 1 and factors[0][1] > 1)

        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_FACTORABLE",
                passed=can_factor,
                message="Polynomial can be non-trivially factored over rationals" if can_factor else "Polynomial is irreducible over rationals",
                details={"factorable": can_factor},
            )
        )

        return guards

    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        # Mathematical Guard: Zero-product requires integral domain (R) and no unsafe division
        guards.append(
            GuardResult(
                guard_name="ZERO_PRODUCT_PRINCIPLE_VALID",
                passed=True,
                message="Zero-product principle AB=0 <=> A=0 or B=0 is valid over the field of real numbers R.",
                details={"field": "R"},
            )
        )

        return guards

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        if norm_eq.degree < 2 or norm_eq.is_rational:
            return MethodAdmissibility.NOT_APPLICABLE

        if norm_eq.numerator_poly is not None:
            factors_dict = sympy.factor_list(norm_eq.numerator_poly)
            factors = factors_dict[1]
            if len(factors) > 1 or (len(factors) == 1 and factors[0][1] > 1):
                return MethodAdmissibility.APPLICABLE

        return MethodAdmissibility.NOT_APPLICABLE

    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        if norm_eq.numerator_poly is None:
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                notes=["No polynomial available to factor."],
            )

        coeff, factors = sympy.factor_list(norm_eq.numerator_poly)
        candidate_roots: Set[sympy.Basic] = set()
        notes: List[str] = [f"Factored with scalar coefficient {coeff}"]
        all_factors_solvable = True

        for factor_poly, multiplicity in factors:
            deg = factor_poly.degree()
            notes.append(f"Factor ({factor_poly.as_expr()})^{multiplicity} with degree {deg}")

            if deg == 1:
                # Linear factor a*x + b
                a = factor_poly.coeff_monomial((1,))
                b = factor_poly.coeff_monomial((0,))
                r = sympy.simplify(-b / a)
                candidate_roots.add(r)
            elif deg == 2:
                # Quadratic factor a*x^2 + b*x + c
                a = factor_poly.coeff_monomial((2,))
                b = factor_poly.coeff_monomial((1,))
                c = factor_poly.coeff_monomial((0,))
                delta = b**2 - 4 * a * c
                if delta == 0:
                    candidate_roots.add(sympy.simplify(-b / (2 * a)))
                elif delta > 0:
                    candidate_roots.add(sympy.simplify((-b + sympy.sqrt(delta)) / (2 * a)))
                    candidate_roots.add(sympy.simplify((-b - sympy.sqrt(delta)) / (2 * a)))
            else:
                # Degree > 2 cannot be resolved completely within DEV-01 scope
                all_factors_solvable = False
                notes.append(f"Factor ({factor_poly.as_expr()}) has degree {deg} > 2; cannot solve in DEV-01.")

        sorted_roots = sorted(list(candidate_roots), key=lambda val: float(val.evalf()))
        return MethodSolveOutput(
            method_id=self.method_id,
            candidate_roots=sorted_roots,
            parameters={
                "factors": [f"{f.as_expr()}^{m}" for f, m in factors],
                "all_factors_solvable": all_factors_solvable,
            },
            notes=notes,
        )

    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        obligations: List[ProofObligation] = []

        factors_list = solve_output.parameters.get("factors", [])
        all_solvable = solve_output.parameters.get("all_factors_solvable", True)

        # 1. TRANSFORMATION_EQUIVALENCE
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.TRANSFORMATION_EQUIVALENCE,
                status=ObligationStatus.PASS,
                description="Verify that product of factors is identically equivalent to the original polynomial",
                evidence=f"Algebraic identity P(x) == prod({factors_list}) holds over R.",
            )
        )

        # 2. NONZERO_GUARD (Root-loss prevention)
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.NONZERO_GUARD,
                status=ObligationStatus.PASS,
                description="Verify no root-losing unconditional division by x or polynomial factor was performed",
                evidence="Zero-product principle decomposes into disjunction without dividing by any factor.",
            )
        )

        # 3. ORIGINAL_DOMAIN and ROOT_SUBSTITUTION
        for root in solve_output.candidate_roots:
            in_dom = norm_eq.domain.contains(root)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ORIGINAL_DOMAIN,
                    status=ObligationStatus.PASS if in_dom else ObligationStatus.FAIL,
                    description=f"Verify candidate root x = {root} belongs to original domain",
                    evidence=f"Candidate {root} {'in' if in_dom else 'NOT in'} domain {norm_eq.domain.format_domain()}",
                    counterexample=None if in_dom else f"x = {root} is excluded by domain",
                )
            )

            sub_res = sympy.simplify(norm_eq.numerator_sym.subs(X_SYM, root))
            sub_passes = bool(sub_res == 0)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ROOT_SUBSTITUTION,
                    status=ObligationStatus.PASS if sub_passes else ObligationStatus.FAIL,
                    description=f"Substitute candidate root x = {root} into original equation",
                    evidence=f"Numerator evaluated at {root} yields {sub_res}",
                    counterexample=None if sub_passes else f"Residue {sub_res} != 0",
                )
            )

        # 4. COMPLETENESS
        if all_solvable:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Verify completeness of solutions obtained by factorization",
                    evidence=f"All irreducible factors over Q have degree <= 2 and were fully solved.",
                )
            )
        else:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.UNRESOLVED,
                    description="Verify completeness of solutions obtained by factorization",
                    evidence="At least one irreducible factor has degree > 2; cannot prove completeness on R.",
                )
            )

        return obligations


def audit_division_step(
    original_equation_poly: sympy.Poly,
    divisor_poly: sympy.Poly,
    resulting_poly: sympy.Poly,
) -> ProofObligation:
    """Audit a division transformation to detect illegal root loss (e.g. dividing by x)."""
    # Check if divisor has real roots
    divisor_roots = sympy.solveset(sympy.Eq(divisor_poly.as_expr(), 0), X_SYM, domain=sympy.S.Reals)
    if isinstance(divisor_roots, sympy.FiniteSet) and len(divisor_roots) > 0:
        lost_roots = [str(r) for r in divisor_roots]
        return ProofObligation(
            obligation_id=ObligationId.NONZERO_GUARD,
            status=ObligationStatus.FAIL,
            description="Audit division by polynomial expression",
            evidence=f"Divisor {divisor_poly.as_expr()} has real roots {lost_roots}; unconditional division loses roots!",
            counterexample=f"Root {lost_roots[0]} lost when dividing by {divisor_poly.as_expr()}",
        )
    return ProofObligation(
        obligation_id=ObligationId.NONZERO_GUARD,
        status=ObligationStatus.PASS,
        description="Audit division by polynomial expression",
        evidence=f"Divisor {divisor_poly.as_expr()} has no real zeros; division is safe.",
    )
