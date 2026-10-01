"""MKE MVP V1 — Host Independent Verification Gateway.

Provides untrusted-candidate verification for quadratic equations over Q and R.
Zero CAS or AI authority: every identity is checked from first principles
using exact rational arithmetic over Q and Q(sqrt(d)).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import List, Tuple

from mke_product.core.rational import Rational
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.models import (
    QuadraticDiscriminant,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
    VerificationCertificate,
    VerificationOutcome,
)


class HostIndependentVerifier:
    """Independent host verification engine for quadratic algebraic truth."""

    VERIFIER_NAME: str = "MKE_HOST_INDEPENDENT_VERIFIER_V1"
    VERIFIER_VERSION: str = "1.0.0"

    def verify_quadratic_solution(
        self,
        a_rat: Rational,
        b_rat: Rational,
        c_rat: Rational,
        outcome: SolutionOutcome,
        roots: List[RealRootValue],
        problem_hash: str = "",
    ) -> VerificationCertificate:
        """Verify the mathematical correctness of a quadratic solution candidate.

        Performs:
        1. Exact discriminant calculation and outcome consistency check.
        2. Exact residual evaluation for each root over Q or Q(sqrt(d)).
        3. Viète relations check (Sum = -b/a, Product = c/a).
        4. Derivative multiplicity check for repeated roots.
        5. Exact canonical identity check for no-real-root cases.
        """
        if a_rat.is_zero:
            raise ValueError("HostIndependentVerifier requires a != 0 for quadratic verification")

        disc = compute_quadratic_discriminant(a_rat, b_rat, c_rat)
        identities: List[str] = []
        residuals: List[str] = []
        vieta_passed = False
        multiplicity_passed = False
        no_real_root_passed = False
        all_checks_valid = True

        # 1. Outcome vs Discriminant Consistency
        if disc.is_negative:
            if outcome != SolutionOutcome.NO_REAL_ROOTS or len(roots) != 0:
                all_checks_valid = False
            else:
                # Prove (2ax+b)^2 - Delta >= -Delta > 0
                no_real_root_passed = True
                identities.append(
                    f"Discriminant Δ = {disc.value} < 0. "
                    f"Canonical identity 4a(ax² + bx + c) = (2ax + b)² - ({disc.value}) >= {-disc.value.to_rational()} > 0 "
                    f"proves ax² + bx + c has constant sign and zero real roots in ℝ."
                )

        elif disc.is_zero:
            if outcome != SolutionOutcome.ONE_REPEATED_REAL_ROOT or len(roots) != 1:
                all_checks_valid = False
            else:
                root_item = roots[0]
                if root_item.root_type != SolutionRootType.RATIONAL or root_item.rational_value is None:
                    all_checks_valid = False
                else:
                    r = root_item.rational_value.to_rational()
                    # Residual: a*r^2 + b*r + c == 0
                    res = a_rat * r * r + b_rat * r + c_rat
                    if not res.is_zero:
                        all_checks_valid = False
                        residuals.append(f"Residual f({r}) = {res} != 0 (FAILED)")
                    else:
                        residuals.append(f"Residual f({r}) = 0 (EXACT_ZERO)")

                    # Derivative: 2a*r + b == 0
                    deriv = Rational(2, 1) * a_rat * r + b_rat
                    if deriv.is_zero:
                        multiplicity_passed = True
                        identities.append(f"Derivative f'({r}) = 2a({r}) + b = 0 verifies multiplicity 2.")
                    else:
                        all_checks_valid = False

                    # Viète sum: r + r = 2r == -b/a
                    v_sum = r + r
                    expected_sum = -b_rat / a_rat
                    v_prod = r * r
                    expected_prod = c_rat / a_rat
                    if v_sum == expected_sum and v_prod == expected_prod:
                        vieta_passed = True
                        identities.append(f"Viète relations verified: 2r = {v_sum} == -b/a, r² = {v_prod} == c/a.")
                    else:
                        all_checks_valid = False

        else:  # disc.is_positive
            if outcome != SolutionOutcome.TWO_DISTINCT_REAL_ROOTS or len(roots) != 2:
                all_checks_valid = False
            else:
                if disc.is_rational_square:
                    # Expect two distinct rational roots
                    for i, root_item in enumerate(roots):
                        if root_item.root_type != SolutionRootType.RATIONAL or root_item.rational_value is None:
                            all_checks_valid = False
                            continue
                        r = root_item.rational_value.to_rational()
                        res = a_rat * r * r + b_rat * r + c_rat
                        if not res.is_zero:
                            all_checks_valid = False
                            residuals.append(f"Residual f(x_{i+1}={r}) = {res} != 0 (FAILED)")
                        else:
                            residuals.append(f"Residual f(x_{i+1}={r}) = 0 (EXACT_ZERO)")

                    if all_checks_valid and len(roots) == 2:
                        r1 = roots[0].rational_value.to_rational()
                        r2 = roots[1].rational_value.to_rational()
                        # Viète sum & product
                        v_sum = r1 + r2
                        expected_sum = -b_rat / a_rat
                        v_prod = r1 * r2
                        expected_prod = c_rat / a_rat
                        if v_sum == expected_sum and v_prod == expected_prod and (r1 != r2):
                            vieta_passed = True
                            identities.append(
                                f"Viète relations verified: x₁ + x₂ = {v_sum} == -b/a, x₁ * x₂ = {v_prod} == c/a."
                            )
                        else:
                            all_checks_valid = False

                else:
                    # Expect two distinct real quadratic surds
                    d_expected = disc.squarefree_kernel
                    for i, root_item in enumerate(roots):
                        if (
                            root_item.root_type != SolutionRootType.REAL_SURD
                            or root_item.surd_base is None
                            or root_item.surd_factor is None
                            or root_item.radicand != d_expected
                        ):
                            all_checks_valid = False
                            continue

                        u = root_item.surd_base.to_rational()
                        v = root_item.surd_factor.to_rational()
                        d = root_item.radicand

                        # (u + v*sqrt(d))^2 = (u^2 + v^2*d) + 2uv*sqrt(d)
                        # a*(u^2 + v^2*d) + b*u + c == 0
                        # 2a*u*v + b*v == v*(2au + b) == 0
                        const_part = a_rat * (u * u + v * v * Rational(d, 1)) + b_rat * u + c_rat
                        surd_part = Rational(2, 1) * a_rat * u * v + b_rat * v

                        if const_part.is_zero and surd_part.is_zero:
                            residuals.append(f"Residual f(x_{i+1}={root_item.latex_str}): const=0, surd_coeff=0 (EXACT_ZERO)")
                        else:
                            all_checks_valid = False
                            residuals.append(f"Residual f(x_{i+1}={root_item.latex_str}): const={const_part}, surd={surd_part} (FAILED)")

                    if all_checks_valid and len(roots) == 2:
                        u1 = roots[0].surd_base.to_rational()
                        v1 = roots[0].surd_factor.to_rational()
                        u2 = roots[1].surd_base.to_rational()
                        v2 = roots[1].surd_factor.to_rational()

                        # Conjugate sum: (u1 + u2) + (v1 + v2)*sqrt(d)
                        sum_u = u1 + u2
                        sum_v = v1 + v2
                        expected_sum = -b_rat / a_rat

                        # Conjugate product: (u1*u2 + v1*v2*d) + (u1*v2 + u2*v1)*sqrt(d)
                        prod_const = u1 * u2 + v1 * v2 * Rational(d_expected, 1)
                        prod_surd = u1 * v2 + u2 * v1
                        expected_prod = c_rat / a_rat

                        if (
                            sum_u == expected_sum
                            and sum_v.is_zero
                            and prod_const == expected_prod
                            and prod_surd.is_zero
                        ):
                            vieta_passed = True
                            identities.append(
                                f"Viète algebraic invariants over ℚ(√{d_expected}) verified: "
                                f"x₁ + x₂ = {sum_u} == -b/a, x₁ * x₂ = {prod_const} == c/a."
                            )
                        else:
                            all_checks_valid = False

        final_outcome = (
            VerificationOutcome.VERIFIED_COMPLETE
            if all_checks_valid
            else VerificationOutcome.VERIFICATION_FAILED
        )

        # Build cryptographic / structural signature
        sig_payload = {
            "verifier": self.VERIFIER_NAME,
            "version": self.VERIFIER_VERSION,
            "problem_hash": problem_hash,
            "a": str(a_rat),
            "b": str(b_rat),
            "c": str(c_rat),
            "outcome": final_outcome.value,
            "identities": identities,
            "residuals": residuals,
        }
        sig_str = json.dumps(sig_payload, sort_keys=True)
        cert_sig = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()
        cert_id = hashlib.sha256(f"cert:{problem_hash}:{cert_sig}".encode("utf-8")).hexdigest()[:16]

        return VerificationCertificate(
            certificate_id=cert_id,
            problem_hash=problem_hash,
            outcome=final_outcome,
            verifier_name=self.VERIFIER_NAME,
            verifier_version=self.VERIFIER_VERSION,
            verified_at_utc=datetime.utcnow(),
            algebraic_identities_passed=identities,
            residual_checks=residuals,
            vieta_relations_checked=vieta_passed,
            multiplicity_verified=multiplicity_passed,
            no_real_root_verified=no_real_root_passed,
            certificate_signature=cert_sig,
        )
