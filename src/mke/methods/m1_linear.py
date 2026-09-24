"""Method M1: Linear Equation solver with strict coefficient guard and degeneracy analysis."""

from fractions import Fraction
from typing import List
import sympy

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, ObligationStatus
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


class LinearEquationMethod(BaseMethod):
    """M1: LINEAR_EQUATION - Solves ax + b = 0 with rigorous guard on coefficient 'a'."""

    method_id = MethodId.M1_LINEAR_EQUATION
    version = "1.0.0"
    name = "Linear Equation Method"
    description = "Solves linear equation ax + b = 0 over real numbers with degeneracy handling."
    scope_limits = "Degree <= 1 polynomial equation in one variable x."

    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        is_deg_le_1 = norm_eq.degree <= 1
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_DEGREE_LE_1",
                passed=is_deg_le_1,
                message=f"Equation degree is {norm_eq.degree} (expected <= 1)",
                details={"degree": norm_eq.degree},
            )
        )

        not_rational = not norm_eq.is_rational
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_NON_RATIONAL",
                passed=not_rational,
                message="Equation does not contain algebraic fractions in x" if not_rational else "Equation contains fractions; M4:RATIONAL_EQUATION should precede M1",
                details={"is_rational": norm_eq.is_rational},
            )
        )

        return guards

    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        # Extract coefficients a (x^1) and b (x^0)
        a = norm_eq.coefficients.get(1, sympy.Integer(0))
        b = norm_eq.coefficients.get(0, sympy.Integer(0))

        if norm_eq.is_identity:
            a = sympy.Integer(0)
            b = sympy.Integer(0)
        elif norm_eq.is_contradiction:
            a = sympy.Integer(0)

        is_nonzero_a = a != 0
        guards.append(
            GuardResult(
                guard_name="NONZERO_COEFFICIENT_A",
                passed=bool(is_nonzero_a),
                message=f"Coefficient of x is {'non-zero (' + str(a) + ')' if is_nonzero_a else 'zero (degenerate linear)'}",
                details={"a": str(a), "b": str(b)},
            )
        )

        return guards

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        # Degree must be <= 1 and not rational
        if norm_eq.degree > 1 or norm_eq.is_rational:
            return MethodAdmissibility.NOT_APPLICABLE

        a = norm_eq.coefficients.get(1, sympy.Integer(0))
        if norm_eq.is_identity or norm_eq.is_contradiction or a == 0:
            # Degenerate linear branch: applicable with obligations
            return MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS

        return MethodAdmissibility.APPLICABLE

    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        a = norm_eq.coefficients.get(1, sympy.Integer(0))
        b = norm_eq.coefficients.get(0, sympy.Integer(0))

        if norm_eq.is_identity or (a == 0 and b == 0):
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                parameters={"a": "0", "b": "0"},
                is_identity_on_domain=True,
                notes=["Degenerate linear identity 0*x = 0; all domain elements are solutions."],
            )

        if norm_eq.is_contradiction or (a == 0 and b != 0):
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                parameters={"a": "0", "b": str(b)},
                is_contradiction=True,
                notes=[f"Degenerate linear contradiction 0*x + ({b}) = 0; empty solution set."],
            )

        # Standard linear solution: x = -b / a
        root = sympy.simplify(-b / a)
        return MethodSolveOutput(
            method_id=self.method_id,
            candidate_roots=[root],
            parameters={"a": str(a), "b": str(b)},
            notes=[f"Standard linear root x = -({b}) / ({a}) = {root}"],
        )

    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        obligations: List[ProofObligation] = []

        a_str = solve_output.parameters.get("a", "0")
        b_str = solve_output.parameters.get("b", "0")

        # 1. NONZERO_GUARD
        if solve_output.is_identity_on_domain or solve_output.is_contradiction:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.NONZERO_GUARD,
                    status=ObligationStatus.PASS,
                    description="Check that coefficient a is non-zero before division",
                    evidence=f"Degeneracy handled without dividing by a: a={a_str}, b={b_str}",
                )
            )
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.PARAMETER_BRANCH,
                    status=ObligationStatus.PASS,
                    description="Handle degenerate parameter branches a=0",
                    evidence=f"Branch evaluated: {'identity (0=0)' if solve_output.is_identity_on_domain else 'contradiction (' + b_str + '=0)'}",
                )
            )
        else:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.NONZERO_GUARD,
                    status=ObligationStatus.PASS,
                    description="Check that coefficient a is non-zero before division",
                    evidence=f"Leading coefficient a = {a_str} != 0, division -b/a is safe.",
                )
            )

        # 2. ORIGINAL_DOMAIN and ROOT_SUBSTITUTION for candidates
        for root in solve_output.candidate_roots:
            in_dom = norm_eq.domain.contains(root)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ORIGINAL_DOMAIN,
                    status=ObligationStatus.PASS if in_dom else ObligationStatus.FAIL,
                    description=f"Verify candidate root x = {root} belongs to original domain",
                    evidence=f"Candidate {root} {'in' if in_dom else 'NOT in'} domain {norm_eq.domain.format_domain()}",
                    counterexample=None if in_dom else f"x = {root} excluded by domain",
                )
            )

            # Substitute root into original numerator
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

        # 3. COMPLETENESS
        if solve_output.is_identity_on_domain:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Prove all solutions in the domain have been found",
                    evidence=f"Degenerate identity 0=0 holds for all x in {norm_eq.domain.format_domain()}",
                )
            )
        elif solve_output.is_contradiction:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Prove all solutions in the domain have been found",
                    evidence="Contradiction b != 0 has no solutions in R",
                )
            )
        else:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.PASS,
                    description="Prove all solutions in the domain have been found",
                    evidence="A non-degenerate degree-1 polynomial has exactly one root on C, hence at most one on R.",
                )
            )

        return obligations
