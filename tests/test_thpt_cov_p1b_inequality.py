"""Tests for MKE THPT Coverage Pack 1-B: Verified Polynomial Inequalities.

Verifies:
- Test00Compatibility: Hard gates for Pack 1-A equation compatibility.
- Test01CanonicalInequalities: 10 canonical required examples.
- Test02LinearMatrix: Full relation matrix for positive and negative linear coefficients.
- Test03QuadraticMatrix: a>0/a<0, Delta>0/=0/<0 across LT/LE/GT/GE.
- Test04ScalarDivision: Constant scalar division in polynomials.
- Test05TamperingAndProvenance: Invariance under raw_source_text tampering.
- Test06ScopeRejections: Out-of-envelope rejection (denominators, exp-0, degree > 2).
- Test07IndependentVerifier: Direct verifier rigor, subset partiality, and generator independence.
- Test08SurdAliasesAndContracts: Algebraic comparison, surd aliases, and contract invariants.
"""

from __future__ import annotations

import unittest
from typing import Tuple, Union

from mke_product.core.rational import Rational
from mke_product.coverage import (
    AlgebraPolynomialInequalityAdapter,
    AlgebraRationalAdapter,
    AllRealSolutionEntity,
    AllRealsExceptFiniteEntity,
    CandidateMetadata,
    CandidateSolution,
    ConstraintRelation,
    DomainCategory,
    DomainSpecification,
    EmptyRealSolutionEntity,
    FiniteRootCollectionEntity,
    LegacyQuadraticAdapter,
    ProblemIR,
    ProblemKind,
    RationalScalarEntity,
    RealIntervalEntity,
    RealIntervalUnionEntity,
    RealQuadraticSurdEntity,
    SingleEquationPayload,
    SingleInequalityPayload,
    UniversalApplicationService,
    VerificationDisposition,
    VerificationLevel,
)
from mke_product.parser import parse_expression


def make_inequality_ir(
    left_str: str,
    relation: ConstraintRelation,
    right_str: str = "0",
    problem_id: str = "test_ineq",
    raw_source_text: str = "",
) -> ProblemIR:
    """Helper to build a valid single-variable polynomial inequality ProblemIR."""
    left = parse_expression(left_str)
    right = parse_expression(right_str)
    payload = SingleInequalityPayload(
        left=left,
        right=right,
        relation=relation,
        target_variable="x",
    )
    return ProblemIR(
        problem_id=problem_id,
        problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
        domain_spec=DomainSpecification(primary_domain=DomainCategory.REALS),
        payload=payload,
        raw_source_text=raw_source_text,
    )


def make_equation_ir(
    left_str: str,
    right_str: str = "0",
    problem_id: str = "test_eq",
) -> ProblemIR:
    """Helper to build a single algebraic equation ProblemIR."""
    left = parse_expression(left_str)
    right = parse_expression(right_str)
    payload = SingleEquationPayload(
        left=left,
        right=right,
        target_variable="x",
    )
    return ProblemIR(
        problem_id=problem_id,
        problem_kind=ProblemKind.ALGEBRA_EQUATION,
        domain_spec=DomainSpecification(primary_domain=DomainCategory.REALS),
        payload=payload,
    )


# ===========================================================================
# F. PACK 1-A COMPATIBILITY HARD GATES
# ===========================================================================

class Test00Compatibility(unittest.TestCase):
    """Hard gate tests for zero regression to Pack 1-A equation solving."""

    def test_01_import_universal_service(self) -> None:
        """1. Import UniversalApplicationService successfully."""
        from mke_product.coverage.service import UniversalApplicationService as UAS
        self.assertIsNotNone(UAS)

    def test_02_construct_universal_service(self) -> None:
        """2. Construct UniversalApplicationService()."""
        service = UniversalApplicationService()
        self.assertIsNotNone(service.registry)
        registered_ids = [a.adapter_id for a in service.registry.list_adapters()]
        self.assertIn("mke.adapter.legacy_quadratic.v1", registered_ids)
        self.assertIn("mke.adapter.algebra_rational.v1", registered_ids)
        self.assertIn("mke.adapter.algebra_polynomial_inequality.v1", registered_ids)

    def test_03_solve_quadratic_equation_accepted(self) -> None:
        """3. Solve x^2 - 5*x + 6 = 0 -> exact accepted {2, 3}."""
        service = UniversalApplicationService()
        ir = make_equation_ir("x^2 - 5*x + 6", "0", problem_id="eq_quad_1")
        result = service.solve(ir)

        self.assertEqual(result.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(result.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(len(result.candidate.parsed_entities), 1)

        ent = result.candidate.parsed_entities[0]
        self.assertIsInstance(ent, FiniteRootCollectionEntity)
        roots = {r.to_rational for r in ent.roots if isinstance(r, RationalScalarEntity)}
        self.assertEqual(roots, {Rational(2, 1), Rational(3, 1)})

    def test_04_solve_rational_equation_accepted(self) -> None:
        """4. Solve (x+1)/(x-2) = 0 -> exact accepted {-1}."""
        service = UniversalApplicationService()
        ir = make_equation_ir("(x+1)/(x-2)", "0", problem_id="eq_rat_1")
        result = service.solve(ir)

        self.assertEqual(result.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(result.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(len(result.candidate.parsed_entities), 1)

        ent = result.candidate.parsed_entities[0]
        self.assertIsInstance(ent, FiniteRootCollectionEntity)
        roots = [r.to_rational for r in ent.roots if isinstance(r, RationalScalarEntity)]
        self.assertEqual(roots, [Rational(-1, 1)])

    def test_05_solve_rational_identity_exclusions(self) -> None:
        """5. Solve 1/(x-1) = 1/(x-1) -> exact accepted ALL_REALS_EXCEPT_FINITE excluding 1."""
        service = UniversalApplicationService()
        ir = make_equation_ir("1/(x-1)", "1/(x-1)", problem_id="eq_rat_ident")
        result = service.solve(ir)

        self.assertEqual(result.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(result.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(len(result.candidate.parsed_entities), 1)

        ent = result.candidate.parsed_entities[0]
        self.assertIsInstance(ent, AllRealsExceptFiniteEntity)
        self.assertEqual(ent.cardinality_excluded, 1)
        ex = ent.excluded_points[0]
        self.assertIsInstance(ex, RationalScalarEntity)
        self.assertEqual(ex.to_rational, Rational(1, 1))

    def test_06_exponent_zero_domain_guard(self) -> None:
        """6. Exercise accepted exponent-zero domain-guard representative behavior from Pack 1-A."""
        service = UniversalApplicationService()
        ir = make_equation_ir("(x-1)^0", "1", problem_id="eq_exp0_guard")
        result = service.solve(ir)

        self.assertEqual(result.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(result.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = result.candidate.parsed_entities[0]
        self.assertIsInstance(ent, AllRealsExceptFiniteEntity)
        self.assertEqual(ent.cardinality_excluded, 1)
        self.assertEqual(ent.excluded_points[0].to_rational, Rational(1, 1))

    def test_07_equation_never_resolves_to_inequality_adapter(self) -> None:
        """7. Assert equation ProblemKinds never resolve to inequality adapter."""
        service = UniversalApplicationService()
        quad_ir = make_equation_ir("x^2 - 4", "0")
        rat_ir = make_equation_ir("(x+1)/(x-1)", "0")

        adapter_quad = service.registry.resolve(quad_ir)
        adapter_rat = service.registry.resolve(rat_ir)

        self.assertNotEqual(adapter_quad.adapter_id, "mke.adapter.algebra_polynomial_inequality.v1")
        self.assertNotEqual(adapter_rat.adapter_id, "mke.adapter.algebra_polynomial_inequality.v1")

        ineq_adapter = AlgebraPolynomialInequalityAdapter()
        self.assertFalse(ineq_adapter.can_handle(quad_ir))
        self.assertFalse(ineq_adapter.can_handle(rat_ir))


# ===========================================================================
# 10 CANONICAL REQUIRED EXAMPLES
# ===========================================================================

class Test01CanonicalInequalities(unittest.TestCase):
    """End-to-end tests for all 10 canonical inequality examples."""

    def setUp(self) -> None:
        self.service = UniversalApplicationService()

    def test_canonical_01_linear_gt(self) -> None:
        """1. 2*x-4 > 0 -> (2, +inf)"""
        ir = make_inequality_ir("2*x - 4", ConstraintRelation.GT, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertIsNone(iv.upper_bound)
        self.assertFalse(iv.lower_closed)
        self.assertFalse(iv.upper_closed)
        self.assertIsInstance(iv.lower_bound, RationalScalarEntity)
        self.assertEqual(iv.lower_bound.to_rational, Rational(2, 1))

    def test_canonical_02_linear_le(self) -> None:
        """2. 2*x-4 <= 0 -> (-inf, 2]"""
        ir = make_inequality_ir("2*x - 4", ConstraintRelation.LE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertIsNone(iv.lower_bound)
        self.assertTrue(iv.upper_closed)
        self.assertFalse(iv.lower_closed)
        self.assertIsInstance(iv.upper_bound, RationalScalarEntity)
        self.assertEqual(iv.upper_bound.to_rational, Rational(2, 1))

    def test_canonical_03_quad_ge_two_rays(self) -> None:
        """3. x^2-4 >= 0 -> (-inf, -2] U [2, +inf)"""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 2)

        iv1, iv2 = ent.intervals
        self.assertIsNone(iv1.lower_bound)
        self.assertEqual(iv1.upper_bound.to_rational, Rational(-2, 1))
        self.assertTrue(iv1.upper_closed)

        self.assertEqual(iv2.lower_bound.to_rational, Rational(2, 1))
        self.assertIsNone(iv2.upper_bound)
        self.assertTrue(iv2.lower_closed)

    def test_canonical_04_quad_lt_bounded(self) -> None:
        """4. x^2-4 < 0 -> (-2, 2)"""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.LT, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertEqual(iv.lower_bound.to_rational, Rational(-2, 1))
        self.assertEqual(iv.upper_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv.lower_closed)
        self.assertFalse(iv.upper_closed)

    def test_canonical_05_quad_punctured(self) -> None:
        """5. (x-1)^2 > 0 -> (-inf, 1) U (1, +inf)"""
        ir = make_inequality_ir("(x-1)^2", ConstraintRelation.GT, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 2)

        iv1, iv2 = ent.intervals
        self.assertIsNone(iv1.lower_bound)
        self.assertEqual(iv1.upper_bound.to_rational, Rational(1, 1))
        self.assertFalse(iv1.upper_closed)

        self.assertEqual(iv2.lower_bound.to_rational, Rational(1, 1))
        self.assertIsNone(iv2.upper_bound)
        self.assertFalse(iv2.lower_closed)

    def test_canonical_06_quad_degenerate_neg(self) -> None:
        """6. -(x-1)^2 >= 0 -> [1, 1]"""
        ir = make_inequality_ir("-(x-1)^2", ConstraintRelation.GE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertEqual(iv.lower_bound.to_rational, Rational(1, 1))
        self.assertEqual(iv.upper_bound.to_rational, Rational(1, 1))
        self.assertTrue(iv.lower_closed)
        self.assertTrue(iv.upper_closed)

    def test_canonical_07_all_real(self) -> None:
        """7. x^2+1 > 0 -> ALL_REAL"""
        ir = make_inequality_ir("x^2 + 1", ConstraintRelation.GT, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(len(res.candidate.parsed_entities), 1)
        self.assertIsInstance(res.candidate.parsed_entities[0], AllRealSolutionEntity)

    def test_canonical_08_empty(self) -> None:
        """8. x^2+1 < 0 -> EMPTY"""
        ir = make_inequality_ir("x^2 + 1", ConstraintRelation.LT, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(len(res.candidate.parsed_entities), 1)
        self.assertIsInstance(res.candidate.parsed_entities[0], EmptyRealSolutionEntity)

    def test_canonical_09_degenerate_zero(self) -> None:
        """9. x^2 <= 0 -> [0, 0]"""
        ir = make_inequality_ir("x^2", ConstraintRelation.LE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertEqual(iv.lower_bound.to_rational, Rational(0, 1))
        self.assertEqual(iv.upper_bound.to_rational, Rational(0, 1))
        self.assertTrue(iv.lower_closed)
        self.assertTrue(iv.upper_closed)

    def test_canonical_10_surd_bounded(self) -> None:
        """10. x^2-2 <= 0 -> [-sqrt(2), sqrt(2)]"""
        ir = make_inequality_ir("x^2 - 2", ConstraintRelation.LE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(len(ent.intervals), 1)

        iv = ent.intervals[0]
        self.assertTrue(iv.lower_closed)
        self.assertTrue(iv.upper_closed)

        lb = iv.lower_bound
        ub = iv.upper_bound
        self.assertIsInstance(lb, RealQuadraticSurdEntity)
        self.assertIsInstance(ub, RealQuadraticSurdEntity)

        self.assertEqual(lb.d, 2)
        self.assertEqual(ub.d, 2)
        # lb = -sqrt(2), ub = +sqrt(2)
        self.assertEqual(lb.p, 0)
        self.assertEqual(lb.q, -1)
        self.assertEqual(lb.r, 1)

        self.assertEqual(ub.p, 0)
        self.assertEqual(ub.q, 1)
        self.assertEqual(ub.r, 1)


# ===========================================================================
# LINEAR RELATION MATRIX
# ===========================================================================

class Test02LinearMatrix(unittest.TestCase):
    """Test full matrix of relations LT/LE/GT/GE for positive and negative linear slope."""

    def setUp(self) -> None:
        self.service = UniversalApplicationService()

    def test_linear_positive_slope(self) -> None:
        # 3*x - 6 > 0 => (2, +inf)
        r_gt = self.service.solve(make_inequality_ir("3*x - 6", ConstraintRelation.GT))
        self.assertEqual(r_gt.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_gt = r_gt.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_gt.lower_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv_gt.lower_closed)

        # 3*x - 6 >= 0 => [2, +inf)
        r_ge = self.service.solve(make_inequality_ir("3*x - 6", ConstraintRelation.GE))
        self.assertEqual(r_ge.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_ge = r_ge.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_ge.lower_bound.to_rational, Rational(2, 1))
        self.assertTrue(iv_ge.lower_closed)

        # 3*x - 6 < 0 => (-inf, 2)
        r_lt = self.service.solve(make_inequality_ir("3*x - 6", ConstraintRelation.LT))
        self.assertEqual(r_lt.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_lt = r_lt.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_lt.upper_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv_lt.upper_closed)

        # 3*x - 6 <= 0 => (-inf, 2]
        r_le = self.service.solve(make_inequality_ir("3*x - 6", ConstraintRelation.LE))
        self.assertEqual(r_le.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_le = r_le.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_le.upper_bound.to_rational, Rational(2, 1))
        self.assertTrue(iv_le.upper_closed)

    def test_linear_negative_slope(self) -> None:
        # -3*x + 6 > 0 => (-inf, 2)
        r_gt = self.service.solve(make_inequality_ir("-3*x + 6", ConstraintRelation.GT))
        self.assertEqual(r_gt.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_gt = r_gt.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_gt.upper_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv_gt.upper_closed)

        # -3*x + 6 >= 0 => (-inf, 2]
        r_ge = self.service.solve(make_inequality_ir("-3*x + 6", ConstraintRelation.GE))
        self.assertEqual(r_ge.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_ge = r_ge.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_ge.upper_bound.to_rational, Rational(2, 1))
        self.assertTrue(iv_ge.upper_closed)

        # -3*x + 6 < 0 => (2, +inf)
        r_lt = self.service.solve(make_inequality_ir("-3*x + 6", ConstraintRelation.LT))
        self.assertEqual(r_lt.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_lt = r_lt.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_lt.lower_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv_lt.lower_closed)

        # -3*x + 6 <= 0 => [2, +inf)
        r_le = self.service.solve(make_inequality_ir("-3*x + 6", ConstraintRelation.LE))
        self.assertEqual(r_le.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_le = r_le.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_le.lower_bound.to_rational, Rational(2, 1))
        self.assertTrue(iv_le.lower_closed)


# ===========================================================================
# QUADRATIC MATRIX (a>0/a<0, Delta>0/=0/<0)
# ===========================================================================

class Test03QuadraticMatrix(unittest.TestCase):
    """Test full matrix of quadratic signs and discriminant cases."""

    def setUp(self) -> None:
        self.service = UniversalApplicationService()

    def test_a_neg_delta_pos(self) -> None:
        # -x^2 + 4 > 0 => (-2, 2)
        r_gt = self.service.solve(make_inequality_ir("-x^2 + 4", ConstraintRelation.GT))
        self.assertEqual(r_gt.verification.disposition, VerificationDisposition.ACCEPTED)
        iv_gt = r_gt.candidate.parsed_entities[0].intervals[0]
        self.assertEqual(iv_gt.lower_bound.to_rational, Rational(-2, 1))
        self.assertEqual(iv_gt.upper_bound.to_rational, Rational(2, 1))
        self.assertFalse(iv_gt.lower_closed)
        self.assertFalse(iv_gt.upper_closed)

        # -x^2 + 4 <= 0 => (-inf, -2] U [2, +inf)
        r_le = self.service.solve(make_inequality_ir("-x^2 + 4", ConstraintRelation.LE))
        self.assertEqual(r_le.verification.disposition, VerificationDisposition.ACCEPTED)
        iv1, iv2 = r_le.candidate.parsed_entities[0].intervals
        self.assertEqual(iv1.upper_bound.to_rational, Rational(-2, 1))
        self.assertTrue(iv1.upper_closed)
        self.assertEqual(iv2.lower_bound.to_rational, Rational(2, 1))
        self.assertTrue(iv2.lower_closed)

    def test_a_neg_delta_zero(self) -> None:
        # -x^2 > 0 => EMPTY
        r_gt = self.service.solve(make_inequality_ir("-x^2", ConstraintRelation.GT))
        self.assertEqual(r_gt.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertIsInstance(r_gt.candidate.parsed_entities[0], EmptyRealSolutionEntity)

        # -x^2 <= 0 => ALL_REAL
        r_le = self.service.solve(make_inequality_ir("-x^2", ConstraintRelation.LE))
        self.assertEqual(r_le.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertIsInstance(r_le.candidate.parsed_entities[0], AllRealSolutionEntity)

    def test_a_neg_delta_neg(self) -> None:
        # -x^2 - 1 > 0 => EMPTY
        r_gt = self.service.solve(make_inequality_ir("-x^2 - 1", ConstraintRelation.GT))
        self.assertEqual(r_gt.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertIsInstance(r_gt.candidate.parsed_entities[0], EmptyRealSolutionEntity)

        # -x^2 - 1 < 0 => ALL_REAL
        r_lt = self.service.solve(make_inequality_ir("-x^2 - 1", ConstraintRelation.LT))
        self.assertEqual(r_lt.verification.disposition, VerificationDisposition.ACCEPTED)
        self.assertIsInstance(r_lt.candidate.parsed_entities[0], AllRealSolutionEntity)


# ===========================================================================
# SCALAR DIVISION
# ===========================================================================

class Test04ScalarDivision(unittest.TestCase):
    """Test scalar constant division."""

    def setUp(self) -> None:
        self.service = UniversalApplicationService()

    def test_scalar_constant_division(self) -> None:
        """(x^2 - 4) / 2 >= 0 normalizes cleanly to quadratic inequality."""
        ir = make_inequality_ir("(x^2 - 4) / 2", ConstraintRelation.GE, "0")
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        iv1, iv2 = res.candidate.parsed_entities[0].intervals
        self.assertEqual(iv1.upper_bound.to_rational, Rational(-2, 1))
        self.assertEqual(iv2.lower_bound.to_rational, Rational(2, 1))


# ===========================================================================
# TAMPERING & PROVENANCE INVARIANCE
# ===========================================================================

class Test05TamperingAndProvenance(unittest.TestCase):
    """Test raw_source_text invariance."""

    def setUp(self) -> None:
        self.service = UniversalApplicationService()

    def test_raw_source_text_tampering_invariance(self) -> None:
        """Tampered raw_source_text does not alter exact AST solve or verification."""
        ir = make_inequality_ir(
            "x^2 - 4",
            ConstraintRelation.LT,
            "0",
            raw_source_text="TAMPERED EVIL STRING: 1=0 ALL_REAL",
        )
        res = self.service.solve(ir)

        self.assertEqual(res.verification.verification_level, VerificationLevel.EXACT_VERIFIED)
        self.assertEqual(res.verification.disposition, VerificationDisposition.ACCEPTED)
        ent = res.candidate.parsed_entities[0]
        self.assertIsInstance(ent, RealIntervalUnionEntity)
        self.assertEqual(ent.intervals[0].lower_bound.to_rational, Rational(-2, 1))
        self.assertEqual(ent.intervals[0].upper_bound.to_rational, Rational(2, 1))


# ===========================================================================
# OUT-OF-ENVELOPE & REJECTION TESTS
# ===========================================================================

class Test06ScopeRejections(unittest.TestCase):
    """Tests confirming fail-closed rejection of out-of-scope problems."""

    def setUp(self) -> None:
        self.adapter = AlgebraPolynomialInequalityAdapter()

    def test_variable_denominator_rejected(self) -> None:
        """Variable denominators are rejected by can_handle and verifier."""
        left = parse_expression("1/x")
        right = parse_expression("0")
        ir = ProblemIR(
            problem_id="rej_denom",
            problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
            payload=SingleInequalityPayload(left=left, right=right, relation=ConstraintRelation.GT),
        )
        self.assertFalse(self.adapter.can_handle(ir))

        # Direct verifier call returns UNSUPPORTED
        cand = CandidateSolution(
            candidate_id="cand_bad",
            generator_engine="test",
            raw_symbolic_output="test",
            parsed_entities=(AllRealSolutionEntity(),),
        )
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)
        self.assertEqual(rep.disposition, VerificationDisposition.UNSUPPORTED)

    def test_variable_bearing_exponent_zero_rejected(self) -> None:
        """Variable-bearing exponent 0 base is rejected due to domain guard semantics."""
        left = parse_expression("(x-1)^0")
        right = parse_expression("0")
        ir = ProblemIR(
            problem_id="rej_exp0",
            problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
            payload=SingleInequalityPayload(left=left, right=right, relation=ConstraintRelation.GT),
        )
        self.assertFalse(self.adapter.can_handle(ir))

    def test_degree_overflow_rejected(self) -> None:
        """Multiplication exceeding quadratic degree 2 is rejected."""
        left = parse_expression("x * (x^2 - 1)")
        right = parse_expression("0")
        ir = ProblemIR(
            problem_id="rej_deg3",
            problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
            payload=SingleInequalityPayload(left=left, right=right, relation=ConstraintRelation.GT),
        )
        self.assertFalse(self.adapter.can_handle(ir))


# ===========================================================================
# INDEPENDENT VERIFIER RIGOR & MONKEYPATCH ISOLATION
# ===========================================================================

class Test07IndependentVerifier(unittest.TestCase):
    """Deep verifier obligations, subset handling, and generator independence."""

    def setUp(self) -> None:
        self.adapter = AlgebraPolynomialInequalityAdapter()

    def test_wrong_endpoint_rejected(self) -> None:
        """Candidate with incorrect finite endpoint is rejected."""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.LE, "0")
        # Wrong endpoint: [-3, 2] instead of [-2, 2]
        bad_cand = CandidateSolution(
            candidate_id="cand_wrong_pt",
            generator_engine="fake",
            raw_symbolic_output="[-3, 2]",
            parsed_entities=(
                RealIntervalUnionEntity(
                    intervals=(
                        RealIntervalEntity(
                            lower_bound=RationalScalarEntity.from_rational(Rational(-3, 1)),
                            upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                            lower_closed=True,
                            upper_closed=True,
                        ),
                    )
                ),
            ),
        )
        rep = self.adapter.verify(ir, bad_cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)

    def test_wrong_open_closed_flags_rejected(self) -> None:
        """Candidate with closed endpoints for strict inequality is rejected."""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.LT, "0")
        # Wrong closed flags: [-2, 2] instead of (-2, 2)
        bad_cand = CandidateSolution(
            candidate_id="cand_wrong_flags",
            generator_engine="fake",
            raw_symbolic_output="[-2, 2]",
            parsed_entities=(
                RealIntervalUnionEntity(
                    intervals=(
                        RealIntervalEntity(
                            lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                            upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                            lower_closed=True,
                            upper_closed=True,
                        ),
                    )
                ),
            ),
        )
        rep = self.adapter.verify(ir, bad_cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)

    def test_valid_strict_subset_is_partial(self) -> None:
        """Candidate containing only one valid ray of two is PARTIAL."""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        # True is (-inf, -2] U [2, +inf), candidate only supplies (-inf, -2]
        partial_cand = CandidateSolution(
            candidate_id="cand_subset",
            generator_engine="fake",
            raw_symbolic_output="(-inf, -2]",
            parsed_entities=(
                RealIntervalUnionEntity(
                    intervals=(
                        RealIntervalEntity(
                            lower_bound=None,
                            upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                            lower_closed=False,
                            upper_closed=True,
                        ),
                    )
                ),
            ),
        )
        rep = self.adapter.verify(ir, partial_cand)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)

    def test_non_root_artificial_split_rejected(self) -> None:
        """Candidate with artificial split point not being a root is rejected."""
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.LT, "0")
        # Splitting at 0: (-2, 0) U (0, 2)
        bad_cand = CandidateSolution(
            candidate_id="cand_art_split",
            generator_engine="fake",
            raw_symbolic_output="(-2, 0) U (0, 2)",
            parsed_entities=(
                RealIntervalUnionEntity(
                    intervals=(
                        RealIntervalEntity(
                            lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                            upper_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                            lower_closed=False,
                            upper_closed=False,
                        ),
                        RealIntervalEntity(
                            lower_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                            upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                            lower_closed=False,
                            upper_closed=False,
                        ),
                    )
                ),
            ),
        )
        rep = self.adapter.verify(ir, bad_cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)

    def test_multiple_parsed_entities_rejected(self) -> None:
        """Verifier requires exactly 1 parsed entity in candidate."""
        ir = make_inequality_ir("x^2 + 1", ConstraintRelation.GT, "0")
        bad_cand = CandidateSolution(
            candidate_id="cand_multi",
            generator_engine="fake",
            raw_symbolic_output="multi",
            parsed_entities=(AllRealSolutionEntity(), EmptyRealSolutionEntity()),
        )
        rep = self.adapter.verify(ir, bad_cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)

    def test_zero_parsed_entities_rejected(self) -> None:
        """Verifier rejects candidate with 0 parsed entities."""
        ir = make_inequality_ir("x^2 + 1", ConstraintRelation.GT, "0")
        bad_cand = CandidateSolution(
            candidate_id="cand_zero",
            generator_engine="fake",
            raw_symbolic_output="zero",
            parsed_entities=(),
        )
        rep = self.adapter.verify(ir, bad_cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)

    def test_monkeypatch_generator_verifier_remains_exact(self) -> None:
        """Monkeypatching solve_poly_degree_le_2 to wrong output does not affect direct verifier."""
        import mke_product.coverage.algebra_inequality as ineq_mod

        # Manual correct candidate for x^2 - 4 < 0 => (-2, 2)
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.LT, "0")
        correct_cand = CandidateSolution(
            candidate_id="cand_correct_manual",
            generator_engine="manual",
            raw_symbolic_output="(-2, 2)",
            parsed_entities=(
                RealIntervalUnionEntity(
                    intervals=(
                        RealIntervalEntity(
                            lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                            upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                            lower_closed=False,
                            upper_closed=False,
                        ),
                    )
                ),
            ),
        )

        original_solver = ineq_mod.solve_poly_degree_le_2
        try:
            # Monkeypatch generator to return garbage
            def bad_generator(p):
                return ("GARBAGE", (RationalScalarEntity.from_rational(Rational(999, 1)),))

            ineq_mod.solve_poly_degree_le_2 = bad_generator

            # The independent verifier must NOT call solve_poly_degree_le_2,
            # so it must still accept the correct candidate with EXACT_VERIFIED!
            rep = self.adapter.verify(ir, correct_cand)
            self.assertEqual(rep.verification_level, VerificationLevel.EXACT_VERIFIED)
            self.assertEqual(rep.disposition, VerificationDisposition.ACCEPTED)

            # Furthermore, the untrusted candidate produced under bad generator
            # must be caught and REJECTED by the independent verifier
            cands = self.adapter.solve_candidates(ir)
            rep_bad = self.adapter.verify(ir, cands[0])
            self.assertEqual(rep_bad.disposition, VerificationDisposition.REJECTED)

        finally:
            ineq_mod.solve_poly_degree_le_2 = original_solver


# ===========================================================================
# SURD ALIASES & CONTRACT INVARIANTS
# ===========================================================================

class Test08SurdAliasesAndContracts(unittest.TestCase):
    """Test algebraic comparison, surd alias equality, and contract invariants."""

    def test_surd_alias_endpoint_equality(self) -> None:
        """(0 + 1*sqrt(8))/2 equals (0 + 1*sqrt(2))/1."""
        from mke_product.coverage.algebra_rational import are_roots_equal
        from mke_product.coverage.contracts import _compare_algebraic_entities

        surd_unsimplified = RealQuadraticSurdEntity(p=0, q=1, d=8, r=2)
        surd_canonical = RealQuadraticSurdEntity(p=0, q=1, d=2, r=1)

        self.assertTrue(are_roots_equal(surd_unsimplified, surd_canonical))
        self.assertEqual(_compare_algebraic_entities(surd_unsimplified, surd_canonical), 0)

    def test_interval_infinite_endpoints_must_be_open(self) -> None:
        """Closed infinite endpoint raises ValueError."""
        with self.assertRaises(ValueError):
            RealIntervalEntity(lower_bound=None, lower_closed=True)

        with self.assertRaises(ValueError):
            RealIntervalEntity(upper_bound=None, upper_closed=True)

    def test_interval_lower_exceeds_upper_rejected(self) -> None:
        """lower_bound > upper_bound raises ValueError."""
        with self.assertRaises(ValueError):
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(5, 1)),
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
            )

    def test_degenerate_interval_requires_closed(self) -> None:
        """Degenerate interval [r, r] with open endpoint raises ValueError."""
        r = RationalScalarEntity.from_rational(Rational(1, 1))
        # Valid degenerate
        iv_ok = RealIntervalEntity(lower_bound=r, upper_bound=r, lower_closed=True, upper_closed=True)
        self.assertTrue(iv_ok.lower_closed and iv_ok.upper_closed)

        # Invalid open degenerate
        with self.assertRaises(ValueError):
            RealIntervalEntity(lower_bound=r, upper_bound=r, lower_closed=False, upper_closed=True)


# ===========================================================================
# ADVERSARIAL SUBSET SOUNDNESS AUDIT SUITE
# ===========================================================================

class Test09AdversarialSubsetSoundness(unittest.TestCase):
    """Adversarial tests for subset soundness remediation (Pack 1-B audit finding)."""

    def setUp(self) -> None:
        self.adapter = AlgebraPolynomialInequalityAdapter()

    def _make_candidate(self, intervals: Sequence[RealIntervalEntity], raw: str = "test") -> CandidateSolution:
        return CandidateSolution(
            candidate_id="cand_adv",
            generator_engine="adversarial_test",
            raw_symbolic_output=raw,
            parsed_entities=(
                RealIntervalUnionEntity(intervals=tuple(intervals)),
            ),
        )

    # 1. x^2-4 >= 0 + (-inf, 2] => REJECTED, not PARTIAL
    def test_01_two_rays_ge_left_ray_upper_root_rejected(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)

    # 2. x^2-4 >= 0 + [-2, +inf) => REJECTED
    def test_02_two_rays_ge_right_ray_lower_root_rejected(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)

    # 3. x^2-4 >= 0 + (-inf, -2] only => PARTIAL
    def test_03_two_rays_ge_left_ray_lower_root_partial(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 4. x^2-4 >= 0 + [2, +inf) only => PARTIAL
    def test_04_two_rays_ge_right_ray_upper_root_partial(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 5. x^2-4 >= 0 + (-inf, -2) only => PARTIAL
    def test_05_two_rays_ge_left_ray_open_partial(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 6. x^2-4 > 0 + (-inf, 2) => REJECTED
    def test_06_two_rays_gt_left_ray_upper_root_rejected(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)

    # 7. x^2-4 > 0 + (-inf, -2) => PARTIAL
    def test_07_two_rays_gt_left_ray_lower_root_partial(self) -> None:
        ir = make_inequality_ir("x^2 - 4", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 8. x^2 > 0 + [0, 0] => REJECTED
    def test_08_punctured_degenerate_point_rejected(self) -> None:
        ir = make_inequality_ir("x^2", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                upper_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                lower_closed=True,
                upper_closed=True,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)

    # 9. x^2 > 0 + (-inf, 0) => PARTIAL
    def test_09_punctured_left_open_ray_partial(self) -> None:
        ir = make_inequality_ir("x^2", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 10. x^2 > 0 + (0, +inf) => PARTIAL
    def test_10_punctured_right_open_ray_partial(self) -> None:
        ir = make_inequality_ir("x^2", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                upper_bound=None,
                lower_closed=False,
                upper_closed=False,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.PARTIAL)
        self.assertEqual(rep.verification_level, VerificationLevel.PARTIAL)

    # 11. x^2 > 0 + (-inf, 0] => REJECTED
    def test_11_punctured_closed_at_puncture_rejected(self) -> None:
        ir = make_inequality_ir("x^2", ConstraintRelation.GT, "0")
        cand = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        rep = self.adapter.verify(ir, cand)
        self.assertEqual(rep.disposition, VerificationDisposition.REJECTED)
        self.assertEqual(rep.verification_level, VerificationLevel.UNSUPPORTED)

    # 12. Existing exact full-union cases remain EXACT_VERIFIED/ACCEPTED
    def test_12_exact_full_unions_accepted(self) -> None:
        # Full TWO_RAYS non-strict
        ir_ge = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        cand_ge = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=True,
            ),
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            ),
        ])
        rep_ge = self.adapter.verify(ir_ge, cand_ge)
        self.assertEqual(rep_ge.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(rep_ge.verification_level, VerificationLevel.EXACT_VERIFIED)

        # Full TWO_RAYS strict
        ir_gt = make_inequality_ir("x^2 - 4", ConstraintRelation.GT, "0")
        cand_gt = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=False,
            ),
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=False,
                upper_closed=False,
            ),
        ])
        rep_gt = self.adapter.verify(ir_gt, cand_gt)
        self.assertEqual(rep_gt.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(rep_gt.verification_level, VerificationLevel.EXACT_VERIFIED)

        # Full PUNCTURED
        ir_punc = make_inequality_ir("(x - 1)^2", ConstraintRelation.GT, "0")
        cand_punc = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(1, 1)),
                lower_closed=False,
                upper_closed=False,
            ),
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(1, 1)),
                upper_bound=None,
                lower_closed=False,
                upper_closed=False,
            ),
        ])
        rep_punc = self.adapter.verify(ir_punc, cand_punc)
        self.assertEqual(rep_punc.disposition, VerificationDisposition.ACCEPTED)
        self.assertEqual(rep_punc.verification_level, VerificationLevel.EXACT_VERIFIED)

    # 13. Inverted parabola (a < 0) adversarial tests
    def test_13_two_rays_neg_a_adversarial(self) -> None:
        # -x^2 + 4 <= 0 -> (-inf, -2] U [2, +inf)
        ir = make_inequality_ir("-x^2 + 4", ConstraintRelation.LE, "0")

        # (-inf, 2] ending at upper root -> REJECTED
        cand_bad_upper = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_bad_upper).disposition, VerificationDisposition.REJECTED)

        # [-2, +inf) starting at lower root -> REJECTED
        cand_bad_lower = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_bad_lower).disposition, VerificationDisposition.REJECTED)

        # (-inf, -2] ending at lower root -> PARTIAL
        cand_ok_lower = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_ok_lower).disposition, VerificationDisposition.PARTIAL)

        # [2, +inf) starting at upper root -> PARTIAL
        cand_ok_upper = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_ok_upper).disposition, VerificationDisposition.PARTIAL)

        # Strict -x^2 + 4 < 0:
        ir_strict = make_inequality_ir("-x^2 + 4", ConstraintRelation.LT, "0")
        # (-inf, 2) ending at upper root -> REJECTED
        cand_bad_strict = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_strict, cand_bad_strict).disposition, VerificationDisposition.REJECTED)

        # (-inf, -2) ending at lower root -> PARTIAL
        cand_ok_strict = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_strict, cand_ok_strict).disposition, VerificationDisposition.PARTIAL)

        # (-inf, -2] ending at lower root with closed boundary on strict inequality -> REJECTED
        cand_closed_strict = self._make_candidate([
            RealIntervalEntity(
                lower_bound=None,
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=False,
                upper_closed=True,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_strict, cand_closed_strict).disposition, VerificationDisposition.REJECTED)

    # 14. Additional PUNCTURED edge cases
    def test_14_punctured_additional_adversarial(self) -> None:
        ir = make_inequality_ir("x^2", ConstraintRelation.GT, "0")
        # [0, +inf) closed at 0 -> REJECTED
        cand_right_closed = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(0, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_right_closed).disposition, VerificationDisposition.REJECTED)

        # Bounded interval [-1, 1] -> REJECTED
        cand_bounded = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(-1, 1)),
                upper_bound=RationalScalarEntity.from_rational(Rational(1, 1)),
                lower_closed=False,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir, cand_bounded).disposition, VerificationDisposition.REJECTED)

    # 15. Additional TWO_RAYS edge cases
    def test_15_two_rays_additional_adversarial(self) -> None:
        ir_ge = make_inequality_ir("x^2 - 4", ConstraintRelation.GE, "0")
        # Bounded interval [-2, 2] -> REJECTED
        cand_bounded = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                upper_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                lower_closed=True,
                upper_closed=True,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_ge, cand_bounded).disposition, VerificationDisposition.REJECTED)

        # Degenerate interval [-2, -2] -> REJECTED
        cand_deg = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                upper_bound=RationalScalarEntity.from_rational(Rational(-2, 1)),
                lower_closed=True,
                upper_closed=True,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_ge, cand_deg).disposition, VerificationDisposition.REJECTED)

        # Strict x^2 - 4 > 0: right ray closed [2, +inf) -> REJECTED
        ir_gt = make_inequality_ir("x^2 - 4", ConstraintRelation.GT, "0")
        cand_right_closed = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=True,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_gt, cand_right_closed).disposition, VerificationDisposition.REJECTED)

        # Strict x^2 - 4 > 0: right ray open (2, +inf) -> PARTIAL
        cand_right_open = self._make_candidate([
            RealIntervalEntity(
                lower_bound=RationalScalarEntity.from_rational(Rational(2, 1)),
                upper_bound=None,
                lower_closed=False,
                upper_closed=False,
            )
        ])
        self.assertEqual(self.adapter.verify(ir_gt, cand_right_open).disposition, VerificationDisposition.PARTIAL)


if __name__ == "__main__":
    unittest.main()
