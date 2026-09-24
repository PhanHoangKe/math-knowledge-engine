"""Method M2: Quadratic Formula with non-zero leading coefficient guard and discriminant analysis."""

from typing import List
import sympy

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, ObligationStatus
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


class QuadraticFormulaMethod(BaseMethod):
    """M2: QUADRATIC_FORMULA - Solves ax^2 + bx + c = 0 via discriminant."""

    method_id = MethodId.M2_QUADRATIC_FORMULA
    version = "1.0.0"
    name = "Quadratic Formula Method"
    description = "Solves quadratic equation ax^2 + bx + c = 0 over real numbers using discriminant Delta = b^2 - 4ac."
    scope_limits = "Polynomial equation of degree exactly 2 in single variable x."

    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        is_deg_2 = norm_eq.degree == 2
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_DEGREE_EXACTLY_2",
                passed=is_deg_2,
                message=f"Equation degree is {norm_eq.degree} (expected 2)",
                details={"degree": norm_eq.degree},
            )
        )

        not_rational = not norm_eq.is_rational
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_NON_RATIONAL",
                passed=not_rational,
                message="Equation is polynomial (no x in denominators)" if not_rational else "Equation contains fractions; M4:RATIONAL_EQUATION should precede M2",
                details={"is_rational": norm_eq.is_rational},
            )
        )

        return guards

    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        # Extract coefficients a (x^2), b (x^1), c (x^0)
        a = norm_eq.coefficients.get(2, sympy.Integer(0))
        b = norm_eq.coefficients.get(1, sympy.Integer(0))
        c = norm_eq.coefficients.get(0, sympy.Integer(0))

        is_nonzero_a = a != 0
        guards.append(
            GuardResult(
                guard_name="NONZERO_LEADING_COEFFICIENT_A",
                passed=bool(is_nonzero_a),
                message=f"Leading coefficient a = {a} is {'non-zero' if is_nonzero_a else 'ZERO (M2 is NOT APPLICABLE when a=0)'}",
                details={"a": str(a), "b": str(b), "c": str(c)},
            )
        )

        return guards

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        # If degree is not 2 or rational, not applicable
        if norm_eq.degree != 2 or norm_eq.is_rational:
            return MethodAdmissibility.NOT_APPLICABLE

        # If a == 0, M2 is strictly NOT_APPLICABLE (must not divide by 2*a)
        a = norm_eq.coefficients.get(2, sympy.Integer(0))
        if a == 0:
            return MethodAdmissibility.NOT_APPLICABLE

        return MethodAdmissibility.APPLICABLE

    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        a = norm_eq.coefficients.get(2, sympy.Integer(0))
        b = norm_eq.coefficients.get(1, sympy.Integer(0))
        c = norm_eq.coefficients.get(0, sympy.Integer(0))

        if a == 0:
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                parameters={"a": "0", "b": str(b), "c": str(c)},
                notes=["Leading coefficient a is 0; M2 cannot be applied."],
            )

        # Compute discriminant Delta = b^2 - 4ac
        delta = sympy.simplify(b**2 - 4 * a * c)
        params = {"a": str(a), "b": str(b), "c": str(c), "delta": str(delta)}

        if delta < 0:
            # Negative discriminant: no real roots (empty set)
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                parameters=params,
                notes=[f"Discriminant Delta = {delta} < 0; no real solutions exist."],
            )
        elif delta == 0:
            # Single double root: x = -b / (2a)
            r = sympy.simplify(-b / (2 * a))
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[r],
                parameters=params,
                notes=[f"Discriminant Delta = 0; single real double root x = {r}"],
            )
        else:
            # Two distinct real roots
            sqrt_delta = sympy.sqrt(delta)
            r1 = sympy.simplify((-b + sqrt_delta) / (2 * a))
            r2 = sympy.simplify((-b - sqrt_delta) / (2 * a))
            # Sort roots for deterministic output
            sorted_roots = sorted([r1, r2], key=lambda val: float(val.evalf()))
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=sorted_roots,
                parameters=params,
                notes=[f"Discriminant Delta = {delta} > 0; two real roots x = {sorted_roots}"],
            )

    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        obligations: List[ProofObligation] = []

        a_str = solve_output.parameters.get("a", "0")
        delta_str = solve_output.parameters.get("delta", "0")

        # 1. NONZERO_GUARD on leading coefficient a
        a_val = norm_eq.coefficients.get(2, sympy.Integer(0))
        is_a_nonzero = a_val != 0
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.NONZERO_GUARD,
                status=ObligationStatus.PASS if is_a_nonzero else ObligationStatus.FAIL,
                description="Verify that leading coefficient a is non-zero to allow division by 2a",
                evidence=f"Leading coefficient a = {a_str} {'!= 0' if is_a_nonzero else '== 0'}",
                counterexample=None if is_a_nonzero else "a = 0 violates quadratic requirement",
            )
        )

        # 2. Check candidate roots
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
        if not is_a_nonzero:
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.COMPLETENESS,
                    status=ObligationStatus.FAIL,
                    description="Completeness of quadratic formula solutions",
                    evidence="Cannot prove completeness because leading coefficient a is 0",
                    counterexample="a = 0",
                )
            )
        else:
            a_sym = norm_eq.coefficients.get(2, sympy.Integer(0))
            b_sym = norm_eq.coefficients.get(1, sympy.Integer(0))
            c_sym = norm_eq.coefficients.get(0, sympy.Integer(0))
            delta_val = sympy.simplify(b_sym**2 - 4 * a_sym * c_sym)

            if norm_eq.domain.is_undetermined:
                obligations.append(
                    ProofObligation(
                        obligation_id=ObligationId.COMPLETENESS,
                        status=ObligationStatus.UNRESOLVED,
                        description="Completeness of quadratic formula solutions on R",
                        evidence="Domain status is undetermined; cannot prove completeness on R.",
                    )
                )
            else:
                try:
                    if delta_val < 0:
                        evidence_text = f"Delta = {delta_val} < 0; proved by algebra that no real roots exist."
                    elif delta_val == 0:
                        evidence_text = "Delta = 0; exactly one double root exists by algebraic completeness."
                    else:
                        evidence_text = "Delta > 0; exactly two real roots exist by Fundamental Theorem of Algebra."
                    obligations.append(
                        ProofObligation(
                            obligation_id=ObligationId.COMPLETENESS,
                            status=ObligationStatus.PASS,
                            description="Completeness of quadratic formula solutions on R",
                            evidence=evidence_text,
                        )
                    )
                except Exception:
                    obligations.append(
                        ProofObligation(
                            obligation_id=ObligationId.COMPLETENESS,
                            status=ObligationStatus.UNRESOLVED,
                            description="Completeness of quadratic formula solutions on R",
                            evidence=f"Could not conclusively evaluate sign of discriminant Delta={delta_val}",
                        )
                    )

        return obligations
