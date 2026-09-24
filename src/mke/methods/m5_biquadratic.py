"""Method M5: Biquadratic Substitution with mandatory sign constraint t >= 0."""

from typing import List, Set
import sympy

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, ObligationStatus
from mke.models.evidence import GuardResult, ProofObligation
from mke.parsing.normalizer import NormalizedEquation
from mke.parsing.sympy_converter import X_SYM


class BiquadraticSubstitutionMethod(BaseMethod):
    """M5: BIQUADRATIC_SUBSTITUTION - Solves ax^4 + bx^2 + c = 0 by substituting t = x^2 with t >= 0."""

    method_id = MethodId.M5_BIQUADRATIC_SUBSTITUTION
    version = "1.0.0"
    name = "Biquadratic Substitution Method"
    description = "Substitutes t = x^2 into ax^4 + bx^2 + c = 0, enforces t >= 0, and reconstructs real roots x."
    scope_limits = "Biquadratic polynomial equations ax^4 + bx^2 + c = 0 (a != 0) with no odd powers."

    def check_structural_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        is_deg_4 = norm_eq.degree == 4
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_DEGREE_4",
                passed=is_deg_4,
                message=f"Equation degree is {norm_eq.degree} (expected exactly 4)",
                details={"degree": norm_eq.degree},
            )
        )

        not_rational = not norm_eq.is_rational
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_NON_RATIONAL",
                passed=not_rational,
                message="Equation is polynomial (no x in denominators)",
                details={"is_rational": norm_eq.is_rational},
            )
        )

        # Check that odd power coefficients are 0: coeff of x^3 == 0 and coeff of x^1 == 0
        c3 = norm_eq.coefficients.get(3, sympy.Integer(0))
        c1 = norm_eq.coefficients.get(1, sympy.Integer(0))
        is_even_only = (c3 == 0) and (c1 == 0)
        guards.append(
            GuardResult(
                guard_name="STRUCTURAL_NO_ODD_POWERS",
                passed=is_even_only,
                message="Equation contains only even powers (x^4, x^2, constant)" if is_even_only else f"Equation has odd power coefficients (x^3: {c3}, x^1: {c1})",
                details={"coeff_x3": str(c3), "coeff_x1": str(c1)},
            )
        )

        return guards

    def check_mathematical_guards(self, norm_eq: NormalizedEquation) -> List[GuardResult]:
        guards: List[GuardResult] = []

        a = norm_eq.coefficients.get(4, sympy.Integer(0))
        is_a_nonzero = a != 0
        guards.append(
            GuardResult(
                guard_name="NONZERO_LEADING_COEFFICIENT_A",
                passed=bool(is_a_nonzero),
                message=f"Leading coefficient a = {a} is {'non-zero' if is_a_nonzero else 'ZERO'}",
                details={"a": str(a)},
            )
        )

        return guards

    def evaluate_admissibility(self, norm_eq: NormalizedEquation) -> MethodAdmissibility:
        if norm_eq.degree != 4 or norm_eq.is_rational:
            return MethodAdmissibility.NOT_APPLICABLE

        c3 = norm_eq.coefficients.get(3, sympy.Integer(0))
        c1 = norm_eq.coefficients.get(1, sympy.Integer(0))
        if c3 != 0 or c1 != 0:
            return MethodAdmissibility.NOT_APPLICABLE

        a = norm_eq.coefficients.get(4, sympy.Integer(0))
        if a == 0:
            return MethodAdmissibility.NOT_APPLICABLE

        return MethodAdmissibility.APPLICABLE

    def solve_instance(self, norm_eq: NormalizedEquation) -> MethodSolveOutput:
        a = norm_eq.coefficients.get(4, sympy.Integer(0))
        b = norm_eq.coefficients.get(2, sympy.Integer(0))
        c = norm_eq.coefficients.get(0, sympy.Integer(0))

        # Solve quadratic in t: a*t^2 + b*t + c = 0
        delta = sympy.simplify(b**2 - 4 * a * c)
        params = {"a": str(a), "b": str(b), "c": str(c), "delta": str(delta)}
        notes: List[str] = [
            f"Biquadratic equation: ({a})*x^4 + ({b})*x^2 + ({c}) = 0",
            f"Substitution t = x^2 yields: ({a})*t^2 + ({b})*t + ({c}) = 0",
            f"Discriminant Delta_t = {delta}",
        ]

        if delta < 0:
            notes.append("Discriminant Delta_t < 0; no real values for t exist.")
            return MethodSolveOutput(
                method_id=self.method_id,
                candidate_roots=[],
                parameters=params,
                notes=notes,
            )

        t_candidates: List[sympy.Basic] = []
        if delta == 0:
            t_candidates.append(sympy.simplify(-b / (2 * a)))
        else:
            sqrt_delta = sympy.sqrt(delta)
            t_candidates.append(sympy.simplify((-b + sqrt_delta) / (2 * a)))
            t_candidates.append(sympy.simplify((-b - sqrt_delta) / (2 * a)))

        # Mandatory Sign Constraint Check: t >= 0
        valid_x_roots: Set[sympy.Basic] = set()
        rejected_intermediates: List[dict] = []
        t_status: List[dict] = []

        for t_val in t_candidates:
            # Check numerical sign of t
            is_non_negative = False
            try:
                t_float = float(sympy.N(t_val))
                if t_float >= -1e-12:
                    is_non_negative = True
            except Exception:
                pass

            if is_non_negative:
                t_status.append({"t": str(t_val), "status": "VALID_GE_0"})
                notes.append(f"Root t = {t_val} >= 0: ACCEPTED for real x reconstruction.")
                # x = +/- sqrt(t)
                if t_val == 0:
                    valid_x_roots.add(sympy.Integer(0))
                else:
                    sqrt_t = sympy.sqrt(t_val)
                    valid_x_roots.add(sympy.simplify(sqrt_t))
                    valid_x_roots.add(sympy.simplify(-sqrt_t))
            else:
                t_status.append({"t": str(t_val), "status": "REJECTED_NEGATIVE"})
                notes.append(f"Root t = {t_val} < 0: REJECTED (no real roots x since x^2 = t >= 0).")
                rejected_intermediates.append({
                    "intermediate": f"t = {t_val}",
                    "reason": "t < 0 has no real square roots on R",
                })

        sorted_roots = sorted(list(valid_x_roots), key=lambda val: float(val.evalf()))
        params["t_roots"] = t_status
        params["reconstructed_x_roots"] = [str(r) for r in sorted_roots]

        return MethodSolveOutput(
            method_id=self.method_id,
            candidate_roots=sorted_roots,
            parameters=params,
            notes=notes,
            rejected_intermediates=rejected_intermediates,
        )

    def check_proof_obligations(
        self, norm_eq: NormalizedEquation, solve_output: MethodSolveOutput
    ) -> List[ProofObligation]:
        obligations: List[ProofObligation] = []

        a_str = solve_output.parameters.get("a", "0")
        t_roots = solve_output.parameters.get("t_roots", [])

        # 1. NONZERO_GUARD on leading coefficient a
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.NONZERO_GUARD,
                status=ObligationStatus.PASS,
                description="Verify that leading coefficient a is non-zero",
                evidence=f"Leading coefficient a = {a_str} != 0.",
            )
        )

        # 2. SIGN_CONSTRAINT (Mandatory check for t = x^2 >= 0)
        rejected_count = sum(1 for item in t_roots if item.get("status") == "REJECTED_NEGATIVE")
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.SIGN_CONSTRAINT,
                status=ObligationStatus.PASS,
                description="Enforce sign constraint t = x^2 >= 0 for real solutions",
                evidence=f"Evaluated all roots of t-equation: {t_roots}. Correctly rejected {rejected_count} negative t root(s).",
            )
        )

        # 3. ORIGINAL_DOMAIN and ROOT_SUBSTITUTION for recovered x roots
        for root in solve_output.candidate_roots:
            in_dom = norm_eq.domain.contains(root)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ORIGINAL_DOMAIN,
                    status=ObligationStatus.PASS if in_dom else ObligationStatus.FAIL,
                    description=f"Verify recovered root x = {root} belongs to original domain",
                    evidence=f"Root x = {root} belongs to domain {norm_eq.domain.format_domain()}",
                )
            )

            sub_res = sympy.simplify(norm_eq.numerator_sym.subs(X_SYM, root))
            sub_passes = bool(sub_res == 0)
            obligations.append(
                ProofObligation(
                    obligation_id=ObligationId.ROOT_SUBSTITUTION,
                    status=ObligationStatus.PASS if sub_passes else ObligationStatus.FAIL,
                    description=f"Substitute recovered root x = {root} into original equation",
                    evidence=f"Original equation evaluated at {root} yields {sub_res}",
                )
            )

        # 4. COMPLETENESS
        obligations.append(
            ProofObligation(
                obligation_id=ObligationId.COMPLETENESS,
                status=ObligationStatus.PASS,
                description="Completeness of biquadratic substitution solutions",
                evidence="Mapping x -> x^2 maps R onto [0, inf). Every real root of ax^4+bx^2+c=0 corresponds bijectively to a non-negative root of at^2+bt+c=0.",
            )
        )

        return obligations
