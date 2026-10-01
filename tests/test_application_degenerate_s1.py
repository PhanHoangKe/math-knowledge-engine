"""Comprehensive test suite for S1-02 Exact Degenerate Solver & Independent Verifier.

Verifies:
1. Exact degenerate equation solving (LINEAR, IDENTITY, CONTRADICTION) over Q.
2. DegenerateSolveResult model invariants, immutability, and rejection of extra fields.
3. Independent host verification for degenerate candidates.
4. Fail-closed rejection of forged/adversarial candidates without exceptions.
5. Deterministic tamper-evident certificate fingerprint generation without timestamp contamination.
6. End-to-end integration with AST normalizer (normalize_raw_equation) and S0 domain models.
"""

from __future__ import annotations

import os
import sys
import unittest
import pydantic

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.application.degenerate import (
    DegenerateHostVerifier,
    DegenerateSolveResult,
    solve_exact_degenerate,
    verify_degenerate_solution,
)
from mke_product.application.normalizer import normalize_raw_equation
from mke_product.core.rational import Rational
from mke_product.domain.exact import classify_univariate_degree2
from mke_product.domain.models import (
    DegenerateEquationIR,
    EquationClassificationType,
    ProblemCategory,
    RationalFraction,
    SolutionOutcome,
    VerificationCertificate,
    VerificationOutcome,
)


class TestDegenerateSolveExact(unittest.TestCase):
    """Tests for exact deterministic solving of degenerate equations (a == 0)."""

    def test_linear_integer_positive_root(self):
        # 2*x - 4 = 0 -> x = 2
        res = solve_exact_degenerate(Rational(2, 1), Rational(-4, 1))
        self.assertEqual(res.classification, EquationClassificationType.LINEAR)
        self.assertEqual(res.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)
        self.assertIsNotNone(res.linear_root)
        self.assertEqual(res.linear_root.to_rational(), Rational(2, 1))

    def test_linear_fractional_negative_root(self):
        # 3*x + 1 = 0 -> x = -1/3
        res = solve_exact_degenerate(Rational(3, 1), Rational(1, 1))
        self.assertEqual(res.classification, EquationClassificationType.LINEAR)
        self.assertEqual(res.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)
        self.assertIsNotNone(res.linear_root)
        self.assertEqual(res.linear_root.to_rational(), Rational(-1, 3))

    def test_linear_fractional_coefficients(self):
        # (2/3)*x + (5/7) = 0 -> x = -(5/7) / (2/3) = -15/14
        res = solve_exact_degenerate(Rational(2, 3), Rational(5, 7))
        self.assertEqual(res.classification, EquationClassificationType.LINEAR)
        self.assertEqual(res.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)
        self.assertIsNotNone(res.linear_root)
        self.assertEqual(res.linear_root.to_rational(), Rational(-15, 14))

    def test_linear_negative_leading_coeff(self):
        # -5*x + 10 = 0 -> x = 2
        res = solve_exact_degenerate(Rational(-5, 1), Rational(10, 1))
        self.assertEqual(res.classification, EquationClassificationType.LINEAR)
        self.assertEqual(res.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)
        self.assertIsNotNone(res.linear_root)
        self.assertEqual(res.linear_root.to_rational(), Rational(2, 1))

    def test_identity_equation(self):
        # 0*x + 0 = 0 -> infinitely many solutions
        res = solve_exact_degenerate(Rational(0, 1), Rational(0, 1))
        self.assertEqual(res.classification, EquationClassificationType.IDENTITY)
        self.assertEqual(res.outcome, SolutionOutcome.INFINITE_REAL_SOLUTIONS)
        self.assertIsNone(res.linear_root)

    def test_contradiction_positive_c(self):
        # 0*x + 1 = 0 -> no solution
        res = solve_exact_degenerate(Rational(0, 1), Rational(1, 1))
        self.assertEqual(res.classification, EquationClassificationType.CONTRADICTION)
        self.assertEqual(res.outcome, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION)
        self.assertIsNone(res.linear_root)

    def test_contradiction_negative_c(self):
        # 0*x - 7 = 0 -> no solution
        res = solve_exact_degenerate(Rational(0, 1), Rational(-7, 1))
        self.assertEqual(res.classification, EquationClassificationType.CONTRADICTION)
        self.assertEqual(res.outcome, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION)
        self.assertIsNone(res.linear_root)


class TestDegenerateSolveResultInvariants(unittest.TestCase):
    """Tests enforcing semantic mathematical invariants and immutability of DegenerateSolveResult."""

    def test_linear_requires_linear_root(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.LINEAR,
                outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
                linear_root=None,
            )

    def test_linear_requires_correct_outcome(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.LINEAR,
                outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
                linear_root=RationalFraction(numerator=2, denominator=1),
            )

    def test_identity_forbids_linear_root(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.IDENTITY,
                outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
                linear_root=RationalFraction(numerator=0, denominator=1),
            )

    def test_identity_requires_correct_outcome(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.IDENTITY,
                outcome=SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
                linear_root=None,
            )

    def test_contradiction_forbids_linear_root(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.CONTRADICTION,
                outcome=SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
                linear_root=RationalFraction(numerator=1, denominator=1),
            )

    def test_contradiction_requires_correct_outcome(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.CONTRADICTION,
                outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
                linear_root=None,
            )

    def test_quadratic_classification_rejected(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.QUADRATIC,
                outcome=SolutionOutcome.TWO_DISTINCT_REAL_ROOTS,
                linear_root=None,
            )

    def test_extra_fields_forbidden(self):
        with self.assertRaises(pydantic.ValidationError):
            DegenerateSolveResult(
                classification=EquationClassificationType.IDENTITY,
                outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
                linear_root=None,
                extra_field="untrusted",
            )

    def test_immutability(self):
        res = solve_exact_degenerate(Rational(2, 1), Rational(-4, 1))
        with self.assertRaises(pydantic.ValidationError):
            res.outcome = SolutionOutcome.INFINITE_REAL_SOLUTIONS


class TestDegenerateHostVerifier(unittest.TestCase):
    """Tests for independent host verification of degenerate solutions."""

    def setUp(self):
        self.verifier = DegenerateHostVerifier()

    def test_verify_linear_valid(self):
        b = Rational(2, 1)
        c = Rational(-4, 1)
        cand = solve_exact_degenerate(b, c)
        cert = self.verifier.verify_degenerate_solution(b, c, cand, problem_hash="prob_lin_1")

        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(cert.verifier_name, "MKE_DEGENERATE_HOST_VERIFIER_V1")
        self.assertEqual(cert.verifier_version, "1.0.0")
        self.assertEqual(cert.problem_hash, "prob_lin_1")
        self.assertFalse(cert.vieta_relations_checked)
        self.assertFalse(cert.multiplicity_verified)
        self.assertFalse(cert.no_real_roots_verified)
        self.assertTrue(len(cert.residual_checks) > 0)
        self.assertIn("EXACT_ZERO", cert.residual_checks[0])
        self.assertTrue(len(cert.algebraic_identities_passed) > 0)
        self.assertTrue(len(cert.integrity_fingerprint) == 64)

    def test_verify_identity_valid(self):
        b = Rational(0, 1)
        c = Rational(0, 1)
        cand = solve_exact_degenerate(b, c)
        cert = self.verifier.verify_degenerate_solution(b, c, cand, problem_hash="prob_id_1")

        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertEqual(cert.verifier_name, "MKE_DEGENERATE_HOST_VERIFIER_V1")
        self.assertFalse(cert.no_real_roots_verified)
        self.assertIn("0*x + 0 == 0 for all x in R", cert.algebraic_identities_passed)

    def test_verify_contradiction_valid(self):
        b = Rational(0, 1)
        c = Rational(5, 1)
        cand = solve_exact_degenerate(b, c)
        cert = self.verifier.verify_degenerate_solution(b, c, cand, problem_hash="prob_contra_1")

        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)
        self.assertTrue(cert.no_real_roots_verified)
        self.assertTrue(any("has no solution" in ident for ident in cert.algebraic_identities_passed))

    def test_verify_linear_forged_root_fails(self):
        b = Rational(2, 1)
        c = Rational(-4, 1)
        # Truth is x = 2. Candidate claims x = 3.
        forged_cand = DegenerateSolveResult(
            classification=EquationClassificationType.LINEAR,
            outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
            linear_root=RationalFraction(numerator=3, denominator=1),
        )
        cert = self.verifier.verify_degenerate_solution(b, c, forged_cand, problem_hash="forged_1")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFICATION_FAILED)
        self.assertTrue(any("FAILED" in r for r in cert.residual_checks))

    def test_verify_forged_classification_linear_as_identity_fails(self):
        b = Rational(2, 1)
        c = Rational(-4, 1)
        # Truth is LINEAR. Candidate claims IDENTITY.
        forged_cand = DegenerateSolveResult(
            classification=EquationClassificationType.IDENTITY,
            outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
            linear_root=None,
        )
        cert = self.verifier.verify_degenerate_solution(b, c, forged_cand, problem_hash="forged_2")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFICATION_FAILED)

    def test_verify_forged_classification_identity_as_contradiction_fails(self):
        b = Rational(0, 1)
        c = Rational(0, 1)
        # Truth is IDENTITY. Candidate claims CONTRADICTION.
        forged_cand = DegenerateSolveResult(
            classification=EquationClassificationType.CONTRADICTION,
            outcome=SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
            linear_root=None,
        )
        cert = self.verifier.verify_degenerate_solution(b, c, forged_cand, problem_hash="forged_3")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFICATION_FAILED)

    def test_verify_forged_classification_contradiction_as_identity_fails(self):
        b = Rational(0, 1)
        c = Rational(5, 1)
        # Truth is CONTRADICTION. Candidate claims IDENTITY.
        forged_cand = solve_exact_degenerate(Rational(0, 1), Rational(0, 1))
        cert = self.verifier.verify_degenerate_solution(b, c, forged_cand, problem_hash="forged_4")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFICATION_FAILED)

    def test_functional_gateway_parity(self):
        b = Rational(3, 1)
        c = Rational(9, 1)
        cand = solve_exact_degenerate(b, c)
        cert1 = self.verifier.verify_degenerate_solution(b, c, cand, "hash_gw")
        cert2 = verify_degenerate_solution(b, c, cand, "hash_gw")

        self.assertEqual(cert1.outcome, cert2.outcome)
        self.assertEqual(cert1.integrity_fingerprint, cert2.integrity_fingerprint)
        self.assertEqual(cert1.certificate_id, cert2.certificate_id)


class TestDeterministicIntegrityFingerprint(unittest.TestCase):
    """Tests verifying certificate integrity fingerprint properties."""

    def test_fingerprint_repeatability(self):
        b = Rational(2, 5)
        c = Rational(-7, 3)
        cand = solve_exact_degenerate(b, c)
        cert_a = verify_degenerate_solution(b, c, cand, "problem_fixed_123")
        cert_b = verify_degenerate_solution(b, c, cand, "problem_fixed_123")

        # Despite verified_at_utc timestamps differing, the integrity_fingerprint must be identical
        self.assertEqual(cert_a.integrity_fingerprint, cert_b.integrity_fingerprint)
        self.assertEqual(cert_a.certificate_id, cert_b.certificate_id)

    def test_fingerprint_distinction_on_coefficients(self):
        cand1 = solve_exact_degenerate(Rational(2, 1), Rational(-4, 1))
        cert1 = verify_degenerate_solution(Rational(2, 1), Rational(-4, 1), cand1, "prob")

        cand2 = solve_exact_degenerate(Rational(2, 1), Rational(-6, 1))
        cert2 = verify_degenerate_solution(Rational(2, 1), Rational(-6, 1), cand2, "prob")

        self.assertNotEqual(cert1.integrity_fingerprint, cert2.integrity_fingerprint)


class TestDegeneratePipelineIntegration(unittest.TestCase):
    """End-to-end integration tests connecting AST normalizer, degenerate solver, and domain models."""

    def test_pipeline_linear_equation(self):
        raw_eq = "2*x - 4 = 0"
        a, b, c = normalize_raw_equation(raw_eq)
        self.assertTrue(a.is_zero)

        cls_type, expected_root = classify_univariate_degree2(a, b, c)
        self.assertEqual(cls_type, EquationClassificationType.LINEAR)
        self.assertEqual(expected_root, Rational(2, 1))

        solve_res = solve_exact_degenerate(b, c)
        self.assertEqual(solve_res.classification, cls_type)
        self.assertEqual(solve_res.outcome, SolutionOutcome.ONE_REAL_LINEAR_ROOT)

        # Reconcile with domain DegenerateEquationIR
        ir = DegenerateEquationIR(
            problem_id="eq_linear_1",
            raw_query=raw_eq,
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_lin_1",
            target_variable="x",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=cls_type,
            linear_root=solve_res.linear_root,
        )
        self.assertEqual(ir.linear_root.to_rational(), Rational(2, 1))

        # Host verification
        cert = verify_degenerate_solution(b, c, solve_res, problem_hash="eq_linear_1_hash")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_pipeline_identity_equation(self):
        raw_eq = "0 = 0"
        a, b, c = normalize_raw_equation(raw_eq)
        self.assertTrue(a.is_zero)

        cls_type, expected_root = classify_univariate_degree2(a, b, c)
        self.assertEqual(cls_type, EquationClassificationType.IDENTITY)
        self.assertIsNone(expected_root)

        solve_res = solve_exact_degenerate(b, c)
        self.assertEqual(solve_res.classification, cls_type)
        self.assertEqual(solve_res.outcome, SolutionOutcome.INFINITE_REAL_SOLUTIONS)

        ir = DegenerateEquationIR(
            problem_id="eq_id_1",
            raw_query=raw_eq,
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_id_1",
            target_variable="x",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=cls_type,
            linear_root=None,
        )
        self.assertIsNone(ir.linear_root)

        cert = verify_degenerate_solution(b, c, solve_res, problem_hash="eq_id_1_hash")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_pipeline_contradiction_equation(self):
        raw_eq = "5 = 0"
        a, b, c = normalize_raw_equation(raw_eq)
        self.assertTrue(a.is_zero)

        cls_type, expected_root = classify_univariate_degree2(a, b, c)
        self.assertEqual(cls_type, EquationClassificationType.CONTRADICTION)
        self.assertIsNone(expected_root)

        solve_res = solve_exact_degenerate(b, c)
        self.assertEqual(solve_res.classification, cls_type)
        self.assertEqual(solve_res.outcome, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION)

        ir = DegenerateEquationIR(
            problem_id="eq_contra_1",
            raw_query=raw_eq,
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_contra_1",
            target_variable="x",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=cls_type,
            linear_root=None,
        )
        self.assertIsNone(ir.linear_root)

        cert = verify_degenerate_solution(b, c, solve_res, problem_hash="eq_contra_1_hash")
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)


if __name__ == "__main__":
    unittest.main()
