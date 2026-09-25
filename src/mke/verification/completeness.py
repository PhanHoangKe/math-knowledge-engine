"""Independent Completeness Auditor for Math Knowledge Engine (MKE).

Provides an independent verification gate that constructs canonical real root sets
directly from normalized equation polynomials and domain constraints, strictly
verifying candidate root coverage without trusting solver self-declarations.
"""

from fractions import Fraction
from typing import Any, Dict, List, Optional, Set, Tuple
import sympy

from mke.models.domain import contains_inexact_float, is_proven_real_number, verify_root_exact
from mke.models.enums import ObligationId, ObligationStatus
from mke.models.evidence import CompletenessCertificate, ProofObligation, VerifiedRoot
from mke.parsing.normalizer import NormalizedEquation


def _roots_match(set_a: Set[sympy.Basic], set_b: Set[sympy.Basic]) -> bool:
    """Exact algebraic equality check between two finite sets of numbers."""
    if len(set_a) != len(set_b):
        return False
    for a in set_a:
        if contains_inexact_float(a):
            return False
    for b in set_b:
        if contains_inexact_float(b):
            return False
    for a in set_a:
        matched = False
        for b in set_b:
            if a == b:
                matched = True
                break
            try:
                diff = sympy.cancel(a - b)
                if diff == 0 or getattr(diff, "is_zero", None) is True:
                    matched = True
                    break
            except Exception:
                pass
        if not matched:
            return False
    return True


def audit_independent_completeness(
    norm_eq: NormalizedEquation,
    verified_roots: List[Any],
    solve_output: Optional[Any] = None,
) -> Tuple[ProofObligation, CompletenessCertificate]:
    """Independently audit completeness of verified roots against canonical mathematical truth.

    Rules:
    1. If original domain is empty (D = empty):
       - If verified_roots is empty -> PASS.
       - If verified_roots is non-empty -> FAIL (empty domain cannot have solutions).
    2. If original domain is undetermined, cannot prove completeness -> UNRESOLVED.
    3. If equation is an identity (0 = 0 on D), all D is solution -> PASS if solver recognized identity.
    4. If equation is a contradiction (c = 0, c != 0), canonical roots = empty -> PASS if verified_roots is empty.
    5. Polynomial equations (degree 1, 2, biquadratic 4):
       - Construct canonical root set directly from coefficients (linear formula, quadratic formula / discriminant).
       - Filter by original domain D.
       - Compare verified_roots with canonical domain roots.
       - Any missing root -> UNRESOLVED / FAIL (never grant VERIFIED_SOLUTION).
    6. Higher degree polynomials (degree 3, 4):
       - If real_roots() proves 0 real roots on R and verified_roots is empty -> PASS.
       - If irreducible with complex/symbolic roots that cannot be verified complete by canonical formula -> UNRESOLVED.
    """
    domain = norm_eq.domain
    raw_candidates_str: List[str] = [
        r.value_str if isinstance(r, VerifiedRoot) else str(r) for r in verified_roots
    ]

    # Case 1: Empty Domain
    if domain.is_empty_domain:
        if len(verified_roots) > 0:
            cert = CompletenessCertificate(
                certificate_id="CERT_EMPTY_DOMAIN_FAIL",
                algorithm="EMPTY_DOMAIN_CANONICAL_PROOF",
                polynomial_degree=0,
                canonical_roots=[],
                verified_roots=[],
                extraneous_roots=raw_candidates_str,
                status=ObligationStatus.FAIL,
                details={
                    "explanation": "Original domain is empty set; no real points exist in D, but non-empty roots were claimed.",
                    "rejected_candidates": raw_candidates_str,
                },
            )
            ob = ProofObligation(
                obligation_id=ObligationId.COMPLETENESS,
                status=ObligationStatus.FAIL,
                description="Independent completeness audit on empty domain with non-empty roots",
                evidence="Domain has no real points; claimed roots are extraneous.",
                counterexample=raw_candidates_str[0] if raw_candidates_str else None,
                certificate=cert.model_dump(),
            )
            return ob, cert
        else:
            cert = CompletenessCertificate(
                certificate_id="CERT_EMPTY_DOMAIN",
                algorithm="EMPTY_DOMAIN_CANONICAL_PROOF",
                polynomial_degree=0,
                canonical_roots=[],
                verified_roots=[],
                status=ObligationStatus.PASS,
                details={"explanation": "Original domain is empty set; no real points exist in D."},
            )
            ob = ProofObligation(
                obligation_id=ObligationId.COMPLETENESS,
                status=ObligationStatus.PASS,
                description="Independent completeness audit on empty domain",
                evidence="Domain has no real points; solution set is strictly empty on R.",
                certificate=cert.model_dump(),
            )
            return ob, cert

    # Case 2: Undetermined Domain
    if domain.is_undetermined:
        cert = CompletenessCertificate(
            certificate_id="CERT_UNDETERMINED_DOMAIN",
            algorithm="UNDETERMINED_DOMAIN",
            polynomial_degree=0,
            status=ObligationStatus.UNRESOLVED,
            details={
                "explanation": "Original domain constraints could not be determined.",
                "submitted_roots": raw_candidates_str,
            },
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=ObligationStatus.UNRESOLVED,
            description="Independent completeness audit",
            evidence="Original domain is undetermined; cannot prove completeness on R.",
            certificate=cert.model_dump(),
        )
        return ob, cert

    # Case 3: Identity on Domain (e.g. (x-2)/(x-2) = 1)
    if norm_eq.is_identity:
        is_ident = bool(solve_output and getattr(solve_output, "is_identity_on_domain", False))
        cert = CompletenessCertificate(
            certificate_id="CERT_IDENTITY_ON_DOMAIN",
            algorithm="IDENTITY_REDUCTION",
            polynomial_degree=0,
            status=ObligationStatus.PASS if is_ident else ObligationStatus.UNRESOLVED,
            details={"domain": domain.format_domain()},
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=ObligationStatus.PASS if is_ident else ObligationStatus.UNRESOLVED,
            description="Independent completeness audit on identity equation",
            evidence=f"Cleared equation is identity 0=0; all points in domain {domain.format_domain()} are valid solutions.",
            certificate=cert.model_dump(),
        )
        return ob, cert

    # Case 4: Contradiction (e.g. 1/(x-2) = 0 => 1 = 0)
    if norm_eq.is_contradiction or norm_eq.numerator_poly is None:
        passed = (len(verified_roots) == 0)
        cert = CompletenessCertificate(
            certificate_id="CERT_CONTRADICTION_EMPTY",
            algorithm="NON_ZERO_CONSTANT_NUMERATOR",
            polynomial_degree=0,
            canonical_roots=[],
            verified_roots=[],
            extraneous_roots=[] if passed else raw_candidates_str,
            status=ObligationStatus.PASS if passed else ObligationStatus.FAIL,
            details={"rejected_candidates": [] if passed else raw_candidates_str},
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=ObligationStatus.PASS if passed else ObligationStatus.FAIL,
            description="Independent completeness audit on contradiction equation",
            evidence="Cleared numerator is non-zero constant; no real solutions exist.",
            certificate=cert.model_dump(),
        )
        return ob, cert

    # Case 5: Polynomial Numerator P(x)
    poly = norm_eq.numerator_poly
    deg = poly.degree()
    coeffs: Dict[str, str] = {f"c{k}": str(poly.coeff_monomial((k,))) for k in range(deg + 1)}

    eq_expr = norm_eq.numerator_sym
    var = (
        norm_eq.numerator_poly.gen
        if (norm_eq.numerator_poly is not None and getattr(norm_eq.numerator_poly, "gen", None) is not None)
        else sympy.Symbol("x", real=True)
    )

    # Safely extract and re-verify candidates: NO sympify, NO eval, NO parse_expr!
    valid_verified_roots_sym: Set[sympy.Basic] = set()
    valid_verified_roots_str: List[str] = []
    rejected_candidates_str: List[str] = []

    for item in verified_roots:
        item_str = item.value_str if isinstance(item, VerifiedRoot) else str(item)

        if contains_inexact_float(item):
            rejected_candidates_str.append(item_str)
            continue

        cand_sym: Optional[sympy.Basic] = None
        if isinstance(item, VerifiedRoot):
            if contains_inexact_float(item.value):
                rejected_candidates_str.append(item_str)
                continue
            if item.equation_fingerprint == str(eq_expr) and item.certificate.is_exact_pass:
                val = item.value
                if isinstance(val, int):
                    cand_sym = sympy.Integer(val)
                elif isinstance(val, Fraction):
                    cand_sym = sympy.Rational(val.numerator, val.denominator)
                elif isinstance(val, sympy.Basic) and not contains_inexact_float(val):
                    cand_sym = val
                else:
                    cand_sym = None
            else:
                cand_sym = None
        elif isinstance(item, int):
            cand_sym = sympy.Integer(item)
        elif isinstance(item, Fraction):
            cand_sym = sympy.Rational(item.numerator, item.denominator)
        elif isinstance(item, (sympy.Integer, sympy.Rational)):
            cand_sym = item
        elif isinstance(item, sympy.Basic):
            if not contains_inexact_float(item):
                cand_sym = item
            else:
                cand_sym = None
        elif isinstance(item, str):
            try:
                frac = Fraction(item.strip())
                cand_sym = sympy.Rational(frac.numerator, frac.denominator)
            except (ValueError, ZeroDivisionError, TypeError):
                cand_sym = None
        else:
            cand_sym = None

        if (
            cand_sym is not None
            and not contains_inexact_float(cand_sym)
            and is_proven_real_number(cand_sym)
            and domain.contains(cand_sym)
        ):
            c = verify_root_exact(eq_expr, cand_sym, var)
            if c.is_exact_pass:
                valid_verified_roots_sym.add(cand_sym)
                valid_verified_roots_str.append(item_str)
            else:
                rejected_candidates_str.append(item_str)
        else:
            rejected_candidates_str.append(item_str)

    seen_valid = set()
    dedup_valid_str: List[str] = []
    for s in valid_verified_roots_str:
        if s not in seen_valid:
            seen_valid.add(s)
            dedup_valid_str.append(s)

    has_rejected = len(rejected_candidates_str) > 0

    # Degree 1: P(x) = ax + b
    if deg == 1:
        a = poly.coeff_monomial((1,))
        b = poly.coeff_monomial((0,))
        if a == 0:
            if b == 0:
                canonical_roots: Set[sympy.Basic] = set()
                can_pass = not has_rejected
            else:
                canonical_roots = set()
                can_pass = (not has_rejected) and (len(valid_verified_roots_sym) == 0)
        else:
            r_exact = sympy.Rational(-b, a) if isinstance(a, int) and isinstance(b, int) else sympy.cancel(-b / a)
            canonical_roots = {r_exact} if domain.contains(r_exact) else set()
            can_pass = (not has_rejected) and _roots_match(canonical_roots, valid_verified_roots_sym)

        missing = [str(r) for r in sorted(list(canonical_roots), key=str) if not any(_roots_match({r}, {v}) for v in valid_verified_roots_sym)]
        unmatched_valid = [str(v) for v in sorted(list(valid_verified_roots_sym), key=str) if not any(_roots_match({v}, {r}) for r in canonical_roots)]
        all_extraneous = rejected_candidates_str + unmatched_valid

        if can_pass:
            status = ObligationStatus.PASS
        elif has_rejected or len(all_extraneous) > 0:
            status = ObligationStatus.FAIL
        else:
            status = ObligationStatus.UNRESOLVED

        details_dict: Dict[str, Any] = {}
        if rejected_candidates_str:
            details_dict["rejected_candidates"] = rejected_candidates_str

        cert = CompletenessCertificate(
            certificate_id="CERT_INDEP_CANONICAL_DEGREE_1",
            algorithm="DEGREE_1_CANONICAL_FORMULA",
            polynomial_degree=1,
            coefficients=coeffs,
            canonical_roots=[str(r) for r in sorted(list(canonical_roots), key=str)],
            verified_roots=dedup_valid_str,
            missing_roots=missing,
            extraneous_roots=all_extraneous,
            status=status,
            details=details_dict,
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=status,
            description="Independent completeness audit: degree 1 linear equation",
            evidence=(
                f"Canonical root(s) {cert.canonical_roots} independently derived from coefficients and verified against domain."
                if can_pass else
                f"Candidate roots {verified_roots} do not match canonical root set {cert.canonical_roots}. Missing: {missing}, Extraneous: {all_extraneous}."
            ),
            certificate=cert.model_dump(),
        )
        return ob, cert

    # Degree 2: P(x) = ax^2 + bx + c
    if deg == 2:
        a = poly.coeff_monomial((2,))
        b = poly.coeff_monomial((1,))
        c = poly.coeff_monomial((0,))
        delta = b**2 - 4 * a * c
        coeffs["delta"] = str(delta)

        canonical_roots = set()
        if delta < 0:
            # Negative discriminant: NO real roots in R
            can_pass = (not has_rejected) and (len(valid_verified_roots_sym) == 0)
        elif delta == 0:
            r0 = sympy.cancel(-b / (2 * a))
            if domain.contains(r0):
                canonical_roots.add(r0)
            can_pass = (not has_rejected) and _roots_match(canonical_roots, valid_verified_roots_sym)
        else:
            # delta > 0
            sqrt_delta = sympy.sqrt(delta)
            r1 = sympy.cancel((-b - sqrt_delta) / (2 * a))
            r2 = sympy.cancel((-b + sqrt_delta) / (2 * a))
            for r_cand in (r1, r2):
                if domain.contains(r_cand):
                    canonical_roots.add(r_cand)
            can_pass = (not has_rejected) and _roots_match(canonical_roots, valid_verified_roots_sym)

        missing = [str(r) for r in sorted(list(canonical_roots), key=str) if not any(_roots_match({r}, {v}) for v in valid_verified_roots_sym)]
        unmatched_valid = [str(v) for v in sorted(list(valid_verified_roots_sym), key=str) if not any(_roots_match({v}, {r}) for r in canonical_roots)]
        all_extraneous = rejected_candidates_str + unmatched_valid

        if can_pass:
            status = ObligationStatus.PASS
        elif has_rejected or len(all_extraneous) > 0:
            status = ObligationStatus.FAIL
        else:
            status = ObligationStatus.UNRESOLVED

        details_dict = {}
        if rejected_candidates_str:
            details_dict["rejected_candidates"] = rejected_candidates_str

        cert = CompletenessCertificate(
            certificate_id="CERT_INDEP_CANONICAL_DEGREE_2",
            algorithm="DEGREE_2_CANONICAL_DISCRIMINANT",
            polynomial_degree=2,
            coefficients=coeffs,
            canonical_roots=[str(r) for r in sorted(list(canonical_roots), key=str)],
            verified_roots=dedup_valid_str,
            missing_roots=missing,
            extraneous_roots=all_extraneous,
            status=status,
            details=details_dict,
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=status,
            description="Independent completeness audit: degree 2 quadratic equation",
            evidence=(
                f"Canonical roots {cert.canonical_roots} derived independently from discriminant delta={delta} and verified against domain."
                if can_pass else
                f"Independent completeness check failed: candidate roots {verified_roots} do not cover canonical root set {cert.canonical_roots}. Missing: {missing}, Extraneous: {all_extraneous}."
            ),
            certificate=cert.model_dump(),
        )
        return ob, cert

    # Degree 4 Biquadratic: P(x) = ax^4 + bx^2 + c (x^3 and x coeffs are 0)
    if deg == 4 and poly.coeff_monomial((3,)) == 0 and poly.coeff_monomial((1,)) == 0:
        a = poly.coeff_monomial((4,))
        b = poly.coeff_monomial((2,))
        c = poly.coeff_monomial((0,))
        delta_u = b**2 - 4 * a * c
        coeffs["delta_u"] = str(delta_u)
        canonical_roots = set()

        if delta_u >= 0:
            sqrt_du = sympy.sqrt(delta_u)
            u_vals = [(-b - sqrt_du) / (2 * a), (-b + sqrt_du) / (2 * a)]
            for u in u_vals:
                u_simp = sympy.cancel(u)
                if u_simp == 0:
                    canonical_roots.add(sympy.Integer(0))
                elif u_simp > 0:
                    canonical_roots.add(sympy.cancel(-sympy.sqrt(u_simp)))
                    canonical_roots.add(sympy.cancel(sympy.sqrt(u_simp)))

        canonical_domain_roots = {r for r in canonical_roots if domain.contains(r)}
        can_pass = (not has_rejected) and _roots_match(canonical_domain_roots, valid_verified_roots_sym)
        missing = [str(r) for r in sorted(list(canonical_domain_roots), key=str) if not any(_roots_match({r}, {v}) for v in valid_verified_roots_sym)]
        unmatched_valid = [str(v) for v in sorted(list(valid_verified_roots_sym), key=str) if not any(_roots_match({v}, {r}) for r in canonical_domain_roots)]
        all_extraneous = rejected_candidates_str + unmatched_valid

        if can_pass:
            status = ObligationStatus.PASS
        elif has_rejected or len(all_extraneous) > 0:
            status = ObligationStatus.FAIL
        else:
            status = ObligationStatus.UNRESOLVED

        details_dict = {}
        if rejected_candidates_str:
            details_dict["rejected_candidates"] = rejected_candidates_str

        cert = CompletenessCertificate(
            certificate_id="CERT_INDEP_CANONICAL_BIQUADRATIC",
            algorithm="BIQUADRATIC_CANONICAL_SUBSTITUTION",
            polynomial_degree=4,
            coefficients=coeffs,
            canonical_roots=[str(r) for r in sorted(list(canonical_domain_roots), key=str)],
            verified_roots=dedup_valid_str,
            missing_roots=missing,
            extraneous_roots=all_extraneous,
            status=status,
            details=details_dict,
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=status,
            description="Independent completeness audit: degree 4 biquadratic equation",
            evidence=(
                f"Canonical biquadratic roots {cert.canonical_roots} derived independently and verified against domain."
                if can_pass else
                f"Biquadratic completeness check failed: verified roots {verified_roots} do not match canonical roots {cert.canonical_roots}. Missing: {missing}, Extraneous: {all_extraneous}."
            ),
            certificate=cert.model_dump(),
        )
        return ob, cert

    # General Degree 3 or 4:
    # 1. Check if real_roots() is strictly empty (e.g. x^4 + 1 = 0)
    try:
        rr = poly.real_roots()
    except Exception:
        rr = None

    if rr is not None and len(rr) == 0:
        can_pass = (not has_rejected) and (len(valid_verified_roots_sym) == 0)
        status = ObligationStatus.PASS if can_pass else ObligationStatus.FAIL
        all_extraneous = rejected_candidates_str + [str(v) for v in sorted(list(valid_verified_roots_sym), key=str)]
        details_dict = {}
        if rejected_candidates_str:
            details_dict["rejected_candidates"] = rejected_candidates_str

        cert = CompletenessCertificate(
            certificate_id="CERT_INDEP_REAL_ROOT_ISOLATION_EMPTY",
            algorithm="STURM_REAL_ROOT_ISOLATION",
            polynomial_degree=deg,
            coefficients=coeffs,
            canonical_roots=[],
            verified_roots=dedup_valid_str,
            extraneous_roots=all_extraneous,
            status=status,
            details=details_dict,
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=status,
            description=f"Independent completeness audit: degree {deg} polynomial proven empty on R",
            evidence="Real root isolation proves polynomial numerator has zero real roots on R.",
            certificate=cert.model_dump(),
        )
        return ob, cert

    # 2. Check if polynomial completely factors into linear and quadratic factors over Q
    try:
        _, factors = poly.factor_list()
        all_factors_degree_le_2 = all(f.degree() <= 2 for f, _ in factors)
    except Exception:
        all_factors_degree_le_2 = False

    if all_factors_degree_le_2:
        canonical_roots = set()
        for f, _ in factors:
            f_deg = f.degree()
            if f_deg == 1:
                fa = f.coeff_monomial((1,))
                fb = f.coeff_monomial((0,))
                canonical_roots.add(sympy.cancel(-fb / fa))
            elif f_deg == 2:
                fa = f.coeff_monomial((2,))
                fb = f.coeff_monomial((1,))
                fc = f.coeff_monomial((0,))
                f_delta = fb**2 - 4 * fa * fc
                if f_delta == 0:
                    canonical_roots.add(sympy.cancel(-fb / (2 * fa)))
                elif f_delta > 0:
                    sq_d = sympy.sqrt(f_delta)
                    canonical_roots.add(sympy.cancel((-fb - sq_d) / (2 * fa)))
                    canonical_roots.add(sympy.cancel((-fb + sq_d) / (2 * fa)))

        canonical_domain_roots = {r for r in canonical_roots if domain.contains(r)}
        can_pass = (not has_rejected) and _roots_match(canonical_domain_roots, valid_verified_roots_sym)
        missing = [str(r) for r in sorted(list(canonical_domain_roots), key=str) if not any(_roots_match({r}, {v}) for v in valid_verified_roots_sym)]
        unmatched_valid = [str(v) for v in sorted(list(valid_verified_roots_sym), key=str) if not any(_roots_match({v}, {r}) for r in canonical_domain_roots)]
        all_extraneous = rejected_candidates_str + unmatched_valid

        if can_pass:
            status = ObligationStatus.PASS
        elif has_rejected or len(all_extraneous) > 0:
            status = ObligationStatus.FAIL
        else:
            status = ObligationStatus.UNRESOLVED

        details_dict = {}
        if rejected_candidates_str:
            details_dict["rejected_candidates"] = rejected_candidates_str

        cert = CompletenessCertificate(
            certificate_id="CERT_INDEP_POLYNOMIAL_FACTORIZATION_COMPLETE",
            algorithm="Q_FACTORIZATION_INDEPENDENT_AUDIT",
            polynomial_degree=deg,
            coefficients=coeffs,
            canonical_roots=[str(r) for r in sorted(list(canonical_domain_roots), key=str)],
            verified_roots=dedup_valid_str,
            missing_roots=missing,
            extraneous_roots=all_extraneous,
            status=status,
            details=details_dict,
        )
        ob = ProofObligation(
            obligation_id=ObligationId.COMPLETENESS,
            status=status,
            description=f"Independent completeness audit: factored degree {deg} polynomial",
            evidence=(
                f"Polynomial factors into degree <= 2 components over Q. Canonical roots {cert.canonical_roots} verified against domain."
                if can_pass else
                f"Candidate roots {verified_roots} do not match canonical factored roots {cert.canonical_roots}. Missing: {missing}, Extraneous: {all_extraneous}."
            ),
            certificate=cert.model_dump(),
        )
        return ob, cert

    # 3. Higher degree polynomial with irreducible factor of degree >= 3 (e.g. x^4 - x - 1 = 0)
    details_dict = {
        "reason": f"Polynomial of degree {deg} is irreducible with degree >= 3 factors over Q; cannot be exhaustively proven complete over R."
    }
    if rejected_candidates_str:
        details_dict["rejected_candidates"] = rejected_candidates_str

    cert = CompletenessCertificate(
        certificate_id="CERT_INDEP_UNRESOLVED_HIGHER_DEGREE",
        algorithm="UNRESOLVED_COMPLEX_SYMBOLIC_DEGREE_3_4",
        polynomial_degree=deg,
        coefficients=coeffs,
        canonical_roots=[],
        verified_roots=dedup_valid_str,
        extraneous_roots=rejected_candidates_str,
        status=ObligationStatus.UNRESOLVED,
        details=details_dict,
    )
    ob = ProofObligation(
        obligation_id=ObligationId.COMPLETENESS,
        status=ObligationStatus.UNRESOLVED,
        description=f"Independent completeness audit: irreducible degree {deg} polynomial",
        evidence=f"Polynomial of degree {deg} has irreducible higher-order factors. In accordance with mathematical soundness rules, completeness cannot be certified and is UNRESOLVED.",
        certificate=cert.model_dump(),
    )
    return ob, cert
