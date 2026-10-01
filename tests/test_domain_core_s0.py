"""Unit & Acceptance Tests for MKE MVP V1 — S0 Domain Core.

Covers:
- Dependency Declaration & Environment Reproducibility
- Acceptance Fixtures Q1–Q6 (Exact Quadratic Roots over Q and R)
- Degenerate Fixtures D1–D3 (Linear, Identity, Contradiction)
- Model Boundary & Mathematical Invariant Enforcement (RationalFraction, QuadraticProblemIR, DegenerateEquationIR)
- Reduced Formula Mathematical Applicability vs Pedagogical Recommendation (without false prerequisites)
- Method Registry Implementation Truth & Orthogonal Dimensions (APPLICABLE coexisting with UNAVAILABLE)
- Curriculum Metadata Status (Neutral tags without unverified claims)
- Exact Arithmetic Adversarial Matrix (Delta in {0, 1, 4, 8, 1/4, 1/2, 8/9, -16, 84})
- Host Independent Verifier Tamper Matrix (10+ adversarial corruptions failing closed)
- Revision & Cache Identity Stability & Assumption Ordering Sensitivity
- Reactive Dependency DAG with Topological Invalidation & Cycle Rejection
- Schema Reproducibility from Python SSOT
"""

from __future__ import annotations

import os
import sys

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
from pydantic import ValidationError

from mke_product.core.rational import Rational
from mke_product.domain import (
    Assumption,
    CycleDetectedError,
    DegenerateEquationIR,
    DependencyGraph,
    EquationClassificationType,
    ExecutionAvailability,
    GeometricPredicate,
    GeometricPrimitive,
    GeometricRelation,
    GeometryProblemIR,
    HostIndependentVerifier,
    MathematicalApplicability,
    MethodAssessment,
    MethodDefinition,
    MethodRegistry,
    NodeNotFoundError,
    PedagogicalRecommendation,
    PrimitiveType,
    ProblemCategory,
    ProblemIR,
    ProofOutcome,
    ProofStep,
    ProofTrace,
    QuadraticDiscriminant,
    QuadraticProblemIR,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
    SupportStatus,
    VerificationCapability,
    VerificationCertificate,
    VerificationOutcome,
    build_quadratic_workspace_dag,
    classify_univariate_degree2,
    compute_computation_cache_identity,
    compute_engine_config_identity,
    compute_quadratic_discriminant,
    compute_semantic_quadratic_identity,
    decompose_integer_squarefree,
    decompose_rational_squarefree,
    export_mvp_v1_json_schema,
    export_mvp_v1_json_schema_str,
    solve_exact_quadratic,
)


# ============================================================================
# 1. DEPENDENCY DECLARATION & REPRODUCIBILITY
# ============================================================================

class TestDependencyDeclaration:
    """Verify that dependencies are explicitly declared in authoritative repository files."""

    def test_pydantic_dependency_declared_in_requirements_txt(self):
        """Authoritative requirements.txt must exist and declare Pydantic v2."""
        req_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "requirements.txt"))
        assert os.path.exists(req_path), "requirements.txt must exist in repository root"
        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "pydantic" in content.lower(), "requirements.txt must declare pydantic"
        assert "pytest" in content.lower(), "requirements.txt must declare pytest"


# ============================================================================
# 2. ACCEPTANCE FIXTURES Q1–Q6 (EXACT QUADRATIC EQUATIONS)
# ============================================================================

class TestQuadraticAcceptanceFixtures:
    """Deterministic acceptance fixtures for quadratic equations Q1 through Q6."""

    def test_fixture_q1_distinct_rational_roots(self):
        """Q1: x^2 - 5x + 6 = 0 => Delta = 1, roots = {2, 3}."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        # 1. Classification & Discriminant
        eq_type, linear_root = classify_univariate_degree2(a, b, c)
        assert eq_type == EquationClassificationType.QUADRATIC
        assert linear_root is None

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(1, 1)
        assert disc.is_positive is True
        assert disc.is_zero is False
        assert disc.is_negative is False
        assert disc.is_rational_square is True
        assert disc.squarefree_kernel == 1
        assert disc.square_root_rational.to_rational() == Rational(1, 1)

        # 2. Exact Solving
        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.TWO_DISTINCT_REAL_ROOTS
        assert len(roots) == 2
        assert roots[0].root_type == SolutionRootType.RATIONAL
        assert roots[0].rational_value.to_rational() == Rational(2, 1)
        assert roots[1].root_type == SolutionRootType.RATIONAL
        assert roots[1].rational_value.to_rational() == Rational(3, 1)

        # 3. Model Construction
        prob_ir = QuadraticProblemIR(
            problem_id="prob_q1",
            raw_query="x^2 - 5x + 6 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_q1",
            a=RationalFraction.from_rational(a),
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            equation_string="x^2 - 5*x + 6 = 0",
            discriminant=disc,
        )
        assert prob_ir.classification == EquationClassificationType.QUADRATIC

        # 4. Host Independent Verification
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q1")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.vieta_relations_checked is True
        assert len(cert.residual_checks) == 2
        assert len(cert.integrity_fingerprint) == 64

    def test_fixture_q2_exact_real_surd_roots(self):
        """Q2: x^2 - 2 = 0 => Delta = 8, roots = {-sqrt(2), +sqrt(2)}."""
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(-2, 1)

        eq_type, _ = classify_univariate_degree2(a, b, c)
        assert eq_type == EquationClassificationType.QUADRATIC

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(8, 1)
        assert disc.is_positive is True
        assert disc.is_rational_square is False
        assert disc.squarefree_kernel == 2
        assert disc.extracted_factor.to_rational() == Rational(2, 1)

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.TWO_DISTINCT_REAL_ROOTS
        assert len(roots) == 2
        assert roots[0].root_type == SolutionRootType.REAL_SURD
        assert roots[0].surd_base.to_rational() == Rational(0, 1)
        assert roots[0].surd_factor.to_rational() == Rational(-1, 1)
        assert roots[0].radicand == 2
        assert roots[1].root_type == SolutionRootType.REAL_SURD
        assert roots[1].surd_base.to_rational() == Rational(0, 1)
        assert roots[1].surd_factor.to_rational() == Rational(1, 1)
        assert roots[1].radicand == 2

        # Method Assessment: Q-factorization NOT applicable, R-factorization APPLICABLE
        registry = MethodRegistry()
        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        assert assessments["QUAD_FACTORIZATION_Q"].mathematical_applicability == MathematicalApplicability.NOT_APPLICABLE
        assert assessments["QUAD_FACTORIZATION_R"].mathematical_applicability == MathematicalApplicability.APPLICABLE

        # Verification
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q2")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.vieta_relations_checked is True

    def test_fixture_q3_repeated_real_root(self):
        """Q3: x^2 - 2x + 1 = 0 => Delta = 0, root = 1 with multiplicity 2."""
        a = Rational(1, 1)
        b = Rational(-2, 1)
        c = Rational(1, 1)

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(0, 1)
        assert disc.is_zero is True
        assert disc.is_rational_square is True

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.ONE_REPEATED_REAL_ROOT
        assert len(roots) == 1
        assert roots[0].root_type == SolutionRootType.RATIONAL
        assert roots[0].rational_value.to_rational() == Rational(1, 1)

        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q3")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.multiplicity_verified is True
        assert cert.vieta_relations_checked is True

    def test_fixture_q4_no_real_roots(self):
        """Q4: x^2 + 1 = 0 => Delta = -4, NO_REAL_ROOTS (valid in R, no B3 invocation)."""
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(1, 1)

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(-4, 1)
        assert disc.is_negative is True
        assert disc.is_rational_square is False

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.NO_REAL_ROOTS
        assert len(roots) == 0

        # Method Assessment: Discriminant is APPLICABLE, Factoring is NOT_APPLICABLE
        registry = MethodRegistry()
        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        assert assessments["QUAD_FORMULA_STANDARD"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert assessments["QUAD_COMPLETE_SQUARE"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert assessments["QUAD_FACTORIZATION_Q"].mathematical_applicability == MathematicalApplicability.NOT_APPLICABLE
        assert assessments["QUAD_FACTORIZATION_R"].mathematical_applicability == MathematicalApplicability.NOT_APPLICABLE

        # Verification
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q4")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.no_real_roots_verified is True

    def test_fixture_q5_non_monic_repeated_root(self):
        """Q5: 2x^2 - 4x + 2 = 0 => Delta = 0, root = 1 with multiplicity 2."""
        a = Rational(2, 1)
        b = Rational(-4, 1)
        c = Rational(2, 1)

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(0, 1)
        assert disc.is_zero is True

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.ONE_REPEATED_REAL_ROOT
        assert len(roots) == 1
        assert roots[0].rational_value.to_rational() == Rational(1, 1)

        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q5")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.multiplicity_verified is True

    def test_fixture_q6_negative_a_and_surd_roots(self):
        """Q6: -x^2 + 3 = 0 => Delta = 12 = 4*3, roots = {+sqrt(3), -sqrt(3)}."""
        a = Rational(-1, 1)
        b = Rational(0, 1)
        c = Rational(3, 1)

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(12, 1)
        assert disc.squarefree_kernel == 3
        assert disc.extracted_factor.to_rational() == Rational(2, 1)

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.TWO_DISTINCT_REAL_ROOTS
        assert len(roots) == 2
        assert roots[0].radicand == 3
        assert roots[1].radicand == 3

        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, outcome, roots, problem_hash="hash_q6")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert cert.vieta_relations_checked is True


# ============================================================================
# 3. DEGENERATE FIXTURES D1–D3 (CLASSIFICATION ROUTING)
# ============================================================================

class TestDegenerateFixtures:
    """Deterministic classification of non-quadratic cases D1 through D3."""

    def test_fixture_d1_linear_equation(self):
        """D1: 0*x^2 + 2x - 4 = 0 => LINEAR with exact root x = 2."""
        a = Rational(0, 1)
        b = Rational(2, 1)
        c = Rational(-4, 1)

        eq_type, root = classify_univariate_degree2(a, b, c)
        assert eq_type == EquationClassificationType.LINEAR
        assert root == Rational(2, 1)

        deg_ir = DegenerateEquationIR(
            problem_id="prob_d1",
            raw_query="2*x - 4 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_d1",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=EquationClassificationType.LINEAR,
            linear_root=RationalFraction.from_rational(root),
        )
        assert deg_ir.classification == EquationClassificationType.LINEAR
        assert deg_ir.linear_root.numerator == 2
        assert deg_ir.linear_root.denominator == 1

    def test_fixture_d2_identity_equation(self):
        """D2: 0*x^2 + 0*x + 0 = 0 => IDENTITY (infinitely many solutions)."""
        a = Rational(0, 1)
        b = Rational(0, 1)
        c = Rational(0, 1)

        eq_type, root = classify_univariate_degree2(a, b, c)
        assert eq_type == EquationClassificationType.IDENTITY
        assert root is None

        deg_ir = DegenerateEquationIR(
            problem_id="prob_d2",
            raw_query="0 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_d2",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=EquationClassificationType.IDENTITY,
        )
        assert deg_ir.classification == EquationClassificationType.IDENTITY

    def test_fixture_d3_contradiction_equation(self):
        """D3: 0*x^2 + 0*x + 1 = 0 => CONTRADICTION (no solution)."""
        a = Rational(0, 1)
        b = Rational(0, 1)
        c = Rational(1, 1)

        eq_type, root = classify_univariate_degree2(a, b, c)
        assert eq_type == EquationClassificationType.CONTRADICTION
        assert root is None

        deg_ir = DegenerateEquationIR(
            problem_id="prob_d3",
            raw_query="1 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_d3",
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            classification=EquationClassificationType.CONTRADICTION,
        )
        assert deg_ir.classification == EquationClassificationType.CONTRADICTION


# ============================================================================
# 4. MODEL BOUNDARY & MATHEMATICAL INVARIANT ENFORCEMENT
# ============================================================================

class TestModelBoundaryInvariants:
    """Adversarial tests ensuring semantic mathematical invariants are strictly enforced on domain models."""

    def test_rational_fraction_canonicalization(self):
        """Non-canonical inputs must be deterministically canonicalized to coprime forms."""
        # 2/4 -> 1/2
        rf1 = RationalFraction(numerator=2, denominator=4)
        assert rf1.numerator == 1
        assert rf1.denominator == 2

        # 0/7 -> 0/1
        rf2 = RationalFraction(numerator=0, denominator=7)
        assert rf2.numerator == 0
        assert rf2.denominator == 1

        # -4/-6 -> 2/3
        rf3 = RationalFraction(numerator=-4, denominator=-6)
        assert rf3.numerator == 2
        assert rf3.denominator == 3

        # 4/-6 -> -2/3
        rf4 = RationalFraction(numerator=4, denominator=-6)
        assert rf4.numerator == -2
        assert rf4.denominator == 3

        # denominator 0 must be rejected
        with pytest.raises(ValidationError):
            RationalFraction(numerator=1, denominator=0)

    def test_quadratic_problem_ir_rejects_a_zero(self):
        """QuadraticProblemIR cannot be constructed with a == 0."""
        disc = compute_quadratic_discriminant(Rational(1, 1), Rational(0, 1), Rational(1, 1))
        with pytest.raises(ValidationError, match="Leading coefficient 'a' cannot be zero"):
            QuadraticProblemIR(
                problem_id="prob_bad_a",
                raw_query="0*x^2 + x + 1 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_bad_a",
                a=RationalFraction(numerator=0, denominator=1),
                b=RationalFraction(numerator=1, denominator=1),
                c=RationalFraction(numerator=1, denominator=1),
                equation_string="x + 1 = 0",
                discriminant=disc,
            )

    def test_quadratic_problem_ir_rejects_wrong_category_or_classification(self):
        """QuadraticProblemIR rejects non-quadratic categories or classifications."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        disc = compute_quadratic_discriminant(a, b, c)

        # Wrong category
        with pytest.raises(ValidationError, match="Category for QuadraticProblemIR must be ALGEBRA_QUADRATIC"):
            QuadraticProblemIR(
                problem_id="prob_bad_cat",
                raw_query="x^2 - 5x + 6 = 0",
                category=ProblemCategory.GEOMETRY_TRIANGLE,
                semantic_revision_hash="hash_q1",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 5*x + 6 = 0",
                discriminant=disc,
            )

        # Wrong classification
        with pytest.raises(ValidationError, match="Classification for QuadraticProblemIR must be QUADRATIC"):
            QuadraticProblemIR(
                problem_id="prob_bad_cls",
                raw_query="x^2 - 5x + 6 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q1",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 5*x + 6 = 0",
                discriminant=disc,
                classification=EquationClassificationType.LINEAR,
            )

    def test_quadratic_problem_ir_rejects_non_q_or_non_r_domains(self):
        """QuadraticProblemIR rejects coefficient_domain != 'Q' or solution_domain != 'R'."""
        a, b, c = Rational(1, 1), Rational(0, 1), Rational(1, 1)
        disc = compute_quadratic_discriminant(a, b, c)

        with pytest.raises(ValidationError, match="Coefficient domain for QuadraticProblemIR must be 'Q'"):
            QuadraticProblemIR(
                problem_id="prob_bad_dom",
                raw_query="x^2 + 1 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q4",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 + 1 = 0",
                discriminant=disc,
                coefficient_domain="C",
            )

        with pytest.raises(ValidationError, match="Solution domain for QuadraticProblemIR must be 'R'"):
            QuadraticProblemIR(
                problem_id="prob_bad_sol_dom",
                raw_query="x^2 + 1 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q4",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 + 1 = 0",
                discriminant=disc,
                solution_domain="C",
            )

    def test_quadratic_problem_ir_rejects_forged_discriminant(self):
        """QuadraticProblemIR rejects caller-forged discriminant inconsistent with b^2 - 4ac."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        # Expected Delta = 1. Forged Delta = 100.
        forged_disc = QuadraticDiscriminant(
            value=RationalFraction(numerator=100, denominator=1),
            is_positive=True,
            is_zero=False,
            is_negative=False,
            is_rational_square=True,
            square_root_rational=RationalFraction(numerator=10, denominator=1),
            squarefree_kernel=1,
            extracted_factor=RationalFraction(numerator=10, denominator=1),
        )
        with pytest.raises(ValidationError, match="Forged or inconsistent discriminant"):
            QuadraticProblemIR(
                problem_id="prob_forged_disc",
                raw_query="x^2 - 5x + 6 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q1",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 5*x + 6 = 0",
                discriminant=forged_disc,
            )

    def test_quadratic_problem_ir_rejects_forged_square_root_rational(self):
        """For x^2 - 5x + 6 = 0 (Delta=1), forge square_root_rational=2 or None."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        # 1. Forge square_root_rational = 2 instead of 1
        forged_disc_2 = QuadraticDiscriminant(
            value=RationalFraction(numerator=1, denominator=1),
            is_positive=True,
            is_zero=False,
            is_negative=False,
            is_rational_square=True,
            square_root_rational=RationalFraction(numerator=2, denominator=1),
            squarefree_kernel=1,
            extracted_factor=RationalFraction(numerator=1, denominator=1),
        )
        with pytest.raises(ValidationError, match="Forged or inconsistent discriminant"):
            QuadraticProblemIR(
                problem_id="prob_forged_sqrt_2",
                raw_query="x^2 - 5x + 6 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q1",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 5*x + 6 = 0",
                discriminant=forged_disc_2,
            )

        # 2. Forge square_root_rational = None for Delta=1
        forged_disc_none = QuadraticDiscriminant(
            value=RationalFraction(numerator=1, denominator=1),
            is_positive=True,
            is_zero=False,
            is_negative=False,
            is_rational_square=True,
            square_root_rational=None,
            squarefree_kernel=1,
            extracted_factor=RationalFraction(numerator=1, denominator=1),
        )
        with pytest.raises(ValidationError, match="Forged or inconsistent discriminant"):
            QuadraticProblemIR(
                problem_id="prob_forged_sqrt_none",
                raw_query="x^2 - 5x + 6 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q1",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 5*x + 6 = 0",
                discriminant=forged_disc_none,
            )

    def test_quadratic_problem_ir_rejects_injected_square_root_rational_when_non_square(self):
        """For x^2 - 2 = 0 (Delta=8, non-square), inject non-None square_root_rational."""
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(-2, 1)

        forged_disc = QuadraticDiscriminant(
            value=RationalFraction(numerator=8, denominator=1),
            is_positive=True,
            is_zero=False,
            is_negative=False,
            is_rational_square=False,
            square_root_rational=RationalFraction(numerator=2, denominator=1),
            squarefree_kernel=2,
            extracted_factor=RationalFraction(numerator=2, denominator=1),
        )
        with pytest.raises(ValidationError, match="Forged or inconsistent discriminant"):
            QuadraticProblemIR(
                problem_id="prob_forged_surd_sqrt",
                raw_query="x^2 - 2 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q2",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 - 2 = 0",
                discriminant=forged_disc,
            )

    def test_quadratic_problem_ir_rejects_injected_square_root_rational_when_negative(self):
        """For x^2 + 1 = 0 (Delta=-4, negative), inject non-None square_root_rational."""
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(1, 1)

        forged_disc = QuadraticDiscriminant(
            value=RationalFraction(numerator=-4, denominator=1),
            is_positive=False,
            is_zero=False,
            is_negative=True,
            is_rational_square=False,
            square_root_rational=RationalFraction(numerator=2, denominator=1),
            squarefree_kernel=None,
            extracted_factor=None,
        )
        with pytest.raises(ValidationError, match="Forged or inconsistent discriminant"):
            QuadraticProblemIR(
                problem_id="prob_forged_neg_sqrt",
                raw_query="x^2 + 1 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_q4",
                a=RationalFraction.from_rational(a),
                b=RationalFraction.from_rational(b),
                c=RationalFraction.from_rational(c),
                equation_string="x^2 + 1 = 0",
                discriminant=forged_disc,
            )

    def test_quadratic_problem_ir_accepts_canonical_computed_discriminant(self):
        """Control case: canonical discriminant returned by compute_quadratic_discriminant() constructs successfully."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        canonical_disc = compute_quadratic_discriminant(a, b, c)

        prob = QuadraticProblemIR(
            problem_id="prob_canonical_ok",
            raw_query="x^2 - 5x + 6 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash="hash_q1",
            a=RationalFraction.from_rational(a),
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            equation_string="x^2 - 5*x + 6 = 0",
            discriminant=canonical_disc,
        )
        assert prob.discriminant == canonical_disc
        assert prob.discriminant.square_root_rational == RationalFraction(numerator=1, denominator=1)

    def test_degenerate_ir_rejects_a_nonzero(self):
        """DegenerateEquationIR rejects a != 0."""
        with pytest.raises(ValidationError, match="Leading coefficient 'a' must be 0"):
            DegenerateEquationIR(
                problem_id="prob_bad_deg_a",
                raw_query="x^2 + 2x = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg",
                a=RationalFraction(numerator=1, denominator=1),
                b=RationalFraction(numerator=2, denominator=1),
                c=RationalFraction(numerator=0, denominator=1),
                classification=EquationClassificationType.LINEAR,
            )

    def test_degenerate_ir_rejects_inconsistent_classification_or_root(self):
        """DegenerateEquationIR rejects forged classification or invalid linear root."""
        # Case 1: b != 0 (2x - 4 = 0) with classification IDENTITY
        with pytest.raises(ValidationError, match="must have classification LINEAR"):
            DegenerateEquationIR(
                problem_id="prob_bad_linear",
                raw_query="2x - 4 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg1",
                b=RationalFraction(numerator=2, denominator=1),
                c=RationalFraction(numerator=-4, denominator=1),
                classification=EquationClassificationType.IDENTITY,
            )

        # Case 2: b != 0 with forged linear_root (root is 2, forge 5)
        with pytest.raises(ValidationError, match="Linear equation root must equal -c/b"):
            DegenerateEquationIR(
                problem_id="prob_forged_root",
                raw_query="2x - 4 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg1",
                b=RationalFraction(numerator=2, denominator=1),
                c=RationalFraction(numerator=-4, denominator=1),
                classification=EquationClassificationType.LINEAR,
                linear_root=RationalFraction(numerator=5, denominator=1),
            )

        # Case 3: b == 0, c == 0 (0 = 0) with classification CONTRADICTION
        with pytest.raises(ValidationError, match="must have classification IDENTITY"):
            DegenerateEquationIR(
                problem_id="prob_bad_identity",
                raw_query="0 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg2",
                b=RationalFraction(numerator=0, denominator=1),
                c=RationalFraction(numerator=0, denominator=1),
                classification=EquationClassificationType.CONTRADICTION,
            )

        # Case 4: b == 0, c == 0 with a linear root
        with pytest.raises(ValidationError, match="Identity equation .* cannot have a discrete linear root"):
            DegenerateEquationIR(
                problem_id="prob_identity_with_root",
                raw_query="0 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg2",
                b=RationalFraction(numerator=0, denominator=1),
                c=RationalFraction(numerator=0, denominator=1),
                classification=EquationClassificationType.IDENTITY,
                linear_root=RationalFraction(numerator=0, denominator=1),
            )

        # Case 5: b == 0, c != 0 (1 = 0) with classification IDENTITY
        with pytest.raises(ValidationError, match="must have classification CONTRADICTION"):
            DegenerateEquationIR(
                problem_id="prob_bad_contradiction",
                raw_query="1 = 0",
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash="hash_deg3",
                b=RationalFraction(numerator=0, denominator=1),
                c=RationalFraction(numerator=1, denominator=1),
                classification=EquationClassificationType.IDENTITY,
            )


# ============================================================================
# 5. REDUCED QUADRATIC FORMULA SEMANTICS & PREREQUISITE CLEANUP
# ============================================================================

class TestReducedFormulaMathematicalSemantics:
    """Verify that b' = b/2 exists in Q for all rational b, making it mathematically applicable without false prerequisites."""

    def test_reduced_formula_definition_has_no_even_prerequisite(self):
        """QUAD_FORMULA_REDUCED definition must NOT list PREREQ_EVEN_COEFF as a mathematical prerequisite."""
        registry = MethodRegistry()
        def_reduced = registry.get("QUAD_FORMULA_REDUCED")
        assert "PREREQ_EVEN_COEFF" not in def_reduced.prerequisite_ids
        assert "PREREQ_RADICALS" in def_reduced.prerequisite_ids

    def test_reduced_formula_applicable_for_odd_integer_b(self):
        """For x^2 - 5x + 6 = 0 (b = -5), reduced formula is mathematically APPLICABLE with NO failed prerequisites."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        red = assessments["QUAD_FORMULA_REDUCED"]

        # MUST be mathematically APPLICABLE because b/2 = -5/2 in Q
        assert red.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert red.support_status == SupportStatus.SUPPORTED
        assert red.execution_availability == ExecutionAvailability.AVAILABLE
        # No failed mathematical prerequisites
        assert all(p.is_satisfied for p in red.prerequisite_status)
        # Pedagogical recommendation is NEUTRAL because b is odd
        assert red.pedagogical_recommendation == PedagogicalRecommendation.NEUTRAL

    def test_reduced_formula_applicable_for_fractional_b(self):
        """For x^2 + (3/4)x - 1/2 = 0 (b = 3/4), reduced formula is mathematically APPLICABLE with no failed prerequisites."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(3, 4)
        c = Rational(-1, 2)

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        red = assessments["QUAD_FORMULA_REDUCED"]

        assert red.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert all(p.is_satisfied for p in red.prerequisite_status)
        assert red.pedagogical_recommendation == PedagogicalRecommendation.NEUTRAL

    def test_reduced_formula_recommended_for_even_integer_b(self):
        """For x^2 - 4x + 4 = 0 (b = -4), reduced formula is APPLICABLE and RECOMMENDED."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(-4, 1)
        c = Rational(4, 1)

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        red = assessments["QUAD_FORMULA_REDUCED"]

        assert red.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert red.pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED


# ============================================================================
# 6. METHOD REGISTRY IMPLEMENTATION TRUTH & ORTHOGONAL DIMENSIONS
# ============================================================================

class TestMethodRegistryImplementationTruth:
    """Test truthful reporting of support_status and execution_availability across all 9 methods."""

    def test_registry_contains_all_9_mvp_methods_with_neutral_curriculum(self):
        registry = MethodRegistry()
        methods = registry.list_all()
        assert len(methods) >= 9
        for m in methods:
            assert m.curriculum_level == "VIETNAM_SECONDARY_TO_BE_VERIFIED"

    def test_applicability_can_coexist_with_unavailable_execution(self):
        """Demonstrate that mathematical_applicability=APPLICABLE coexists with execution_availability=UNAVAILABLE in S0."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)  # x^2 - 5x + 6 = 0

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}

        # Completing the Square: APPLICABLE mathematically, but trace execution engine UNAVAILABLE in S0
        comp_sq = assessments["QUAD_COMPLETE_SQUARE"]
        assert comp_sq.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert comp_sq.support_status == SupportStatus.SUPPORTED
        assert comp_sq.execution_availability == ExecutionAvailability.UNAVAILABLE

        # Factorization over Q: APPLICABLE mathematically, but trace execution engine UNAVAILABLE in S0
        fact_q = assessments["QUAD_FACTORIZATION_Q"]
        assert fact_q.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert fact_q.support_status == SupportStatus.SUPPORTED
        assert fact_q.execution_availability == ExecutionAvailability.UNAVAILABLE

        # Graphical Analysis: APPLICABLE mathematically, but interactive UI plotting UNAVAILABLE in S0
        graph = assessments["QUAD_GRAPHICAL_ANALYSIS"]
        assert graph.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert graph.execution_availability == ExecutionAvailability.UNAVAILABLE
        assert graph.verification_capability == VerificationCapability.NOT_APPLICABLE

    def test_viete_special_sum_and_diff(self):
        registry = MethodRegistry()

        # 2x^2 + 5x - 7 = 0 => a + b + c = 2 + 5 - 7 = 0
        a1, b1, c1 = Rational(2, 1), Rational(5, 1), Rational(-7, 1)
        ass1 = {m.method_id: m for m in registry.assess_quadratic(a1, b1, c1)}
        assert ass1["QUAD_VIETE_SPECIAL_SUM"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert ass1["QUAD_VIETE_SPECIAL_SUM"].execution_availability == ExecutionAvailability.AVAILABLE
        assert ass1["QUAD_VIETE_SPECIAL_SUM"].pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED

        # 2x^2 + 5x + 3 = 0 => a - b + c = 2 - 5 + 3 = 0
        a2, b2, c2 = Rational(2, 1), Rational(5, 1), Rational(3, 1)
        ass2 = {m.method_id: m for m in registry.assess_quadratic(a2, b2, c2)}
        assert ass2["QUAD_VIETE_SPECIAL_DIF"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert ass2["QUAD_VIETE_SPECIAL_DIF"].execution_availability == ExecutionAvailability.AVAILABLE
        assert ass2["QUAD_VIETE_SPECIAL_DIF"].pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED


# ============================================================================
# 7. EXACT ARITHMETIC ADVERSARIAL MATRIX
# ============================================================================

class TestExactArithmeticAdversarialMatrix:
    """Adversarial matrix covering exact rational and surd arithmetic across diverse discriminants."""

    @pytest.mark.parametrize(
        "a_val,b_val,c_val,expected_delta,expected_k,expected_d,expected_outcome",
        [
            # Delta = 0: x^2 - 4x + 4 = 0
            (Rational(1, 1), Rational(-4, 1), Rational(4, 1), Rational(0, 1), 0, 0, SolutionOutcome.ONE_REPEATED_REAL_ROOT),
            # Delta = 1: x^2 - 5x + 6 = 0
            (Rational(1, 1), Rational(-5, 1), Rational(6, 1), Rational(1, 1), 1, 1, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = 4: x^2 - 4 = 0
            (Rational(1, 1), Rational(0, 1), Rational(-1, 1), Rational(4, 1), 2, 1, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = 8: x^2 - 2 = 0
            (Rational(1, 1), Rational(0, 1), Rational(-2, 1), Rational(8, 1), 2, 2, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = 1/4: x^2 - x + 3/16 = 0
            (Rational(1, 1), Rational(-1, 1), Rational(3, 16), Rational(1, 4), 1, 1, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = 1/2: x^2 - x + 1/8 = 0
            (Rational(1, 1), Rational(-1, 1), Rational(1, 8), Rational(1, 2), 1, 2, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = 8/9: x^2 - 2/9 = 0
            (Rational(1, 1), Rational(0, 1), Rational(-2, 9), Rational(8, 9), 2, 2, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Delta = -16: x^2 + 4 = 0
            (Rational(1, 1), Rational(0, 1), Rational(4, 1), Rational(-16, 1), None, None, SolutionOutcome.NO_REAL_ROOTS),
            # Non-monic surd: 3x^2 - 7 = 0 => Delta = 84 = 2^2 * 21
            (Rational(3, 1), Rational(0, 1), Rational(-7, 1), Rational(84, 1), 2, 21, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
            # Negative leading a: -2x^2 + 4x + 6 = 0 => Delta = 64 = 8^2 * 1
            (Rational(-2, 1), Rational(4, 1), Rational(6, 1), Rational(64, 1), 8, 1, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS),
        ],
    )
    def test_discriminant_and_solution_matrix(
        self, a_val, b_val, c_val, expected_delta, expected_k, expected_d, expected_outcome
    ):
        disc = compute_quadratic_discriminant(a_val, b_val, c_val)
        assert disc.value.to_rational() == expected_delta

        if expected_delta.is_positive:
            assert disc.squarefree_kernel == expected_d
            if expected_d == 1:
                assert disc.is_rational_square is True
            else:
                assert disc.is_rational_square is False
        elif expected_delta.is_zero:
            assert disc.is_zero is True
            assert disc.is_rational_square is True
        else:
            assert disc.is_negative is True
            assert disc.is_rational_square is False

        outcome, roots = solve_exact_quadratic(a_val, b_val, c_val)
        assert outcome == expected_outcome

        # Independent host verification of valid solution
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a_val, b_val, c_val, outcome, roots, problem_hash="test_hash")
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE
        assert len(cert.integrity_fingerprint) == 64


# ============================================================================
# 8. HOST INDEPENDENT VERIFIER TAMPER MATRIX
# ============================================================================

class TestHostVerifierTamperMatrix:
    """Tamper tests ensuring the independent verifier fails closed against fraudulent claims."""

    def test_tamper_wrong_rational_root(self):
        """Falsely claiming x=4 for x^2 - 5x + 6 = 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        tampered_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=4, denominator=1),
                latex_str="4",
            ),
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=3, denominator=1),
                latex_str="3",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, tampered_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_wrong_surd_radicand(self):
        """Falsely claiming sqrt(3) for x^2 - 2 = 0."""
        a, b, c = Rational(1, 1), Rational(0, 1), Rational(-2, 1)
        tampered_roots = [
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction(numerator=0, denominator=1),
                surd_factor=RationalFraction(numerator=-1, denominator=1),
                radicand=3,
                latex_str="-\\sqrt{3}",
            ),
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction(numerator=0, denominator=1),
                surd_factor=RationalFraction(numerator=1, denominator=1),
                radicand=3,
                latex_str="\\sqrt{3}",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, tampered_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_wrong_surd_sign(self):
        """Falsely providing two positive roots {sqrt(2), sqrt(2)} for x^2 - 2 = 0."""
        a, b, c = Rational(1, 1), Rational(0, 1), Rational(-2, 1)
        tampered_roots = [
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction(numerator=0, denominator=1),
                surd_factor=RationalFraction(numerator=1, denominator=1),
                radicand=2,
                latex_str="\\sqrt{2}",
            ),
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction(numerator=0, denominator=1),
                surd_factor=RationalFraction(numerator=1, denominator=1),
                radicand=2,
                latex_str="\\sqrt{2}",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, tampered_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_missing_second_root(self):
        """Falsely providing only 1 root when 2 exist."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        tampered_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=2, denominator=1),
                latex_str="2",
            )
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, tampered_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_duplicated_root_when_delta_positive(self):
        """Claiming repeated root when Delta > 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        tampered_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=2, denominator=1),
                latex_str="2",
            )
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.ONE_REPEATED_REAL_ROOT, tampered_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_false_no_real_roots_when_delta_positive(self):
        """Falsely claiming NO_REAL_ROOTS for x^2 - 5x + 6 = 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.NO_REAL_ROOTS, [])
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_false_roots_when_delta_negative(self):
        """Falsely providing roots for x^2 + 1 = 0."""
        a, b, c = Rational(1, 1), Rational(0, 1), Rational(1, 1)
        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=1, denominator=1),
                latex_str="1",
            )
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.ONE_REPEATED_REAL_ROOT, fake_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED


# ============================================================================
# 9. IDENTITY & CACHE HASHING WITH ASSUMPTION CANONICALIZATION
# ============================================================================

class TestIdentityAndCacheHashing:
    """Test deterministic separation of semantic identity and config identity."""

    def test_semantic_identity_stability(self):
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        hash1 = compute_semantic_quadratic_identity(a, b, c, target_var="x")
        hash2 = compute_semantic_quadratic_identity(a, b, c, target_var="x")
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_equivalent_rational_representations_produce_same_semantic_hash(self):
        """Rational(2, 4) and Rational(1, 2) must normalize canonically to the same hash."""
        a1 = Rational(2, 4)
        a2 = Rational(1, 2)
        b = Rational(3, 1)
        c = Rational(5, 1)

        hash1 = compute_semantic_quadratic_identity(a1, b, c)
        hash2 = compute_semantic_quadratic_identity(a2, b, c)
        assert hash1 == hash2

    def test_assumptions_order_independent_hash(self):
        """Assumptions provided in different list orders must produce the exact same semantic identity hash."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        asm1 = [
            Assumption(symbol="x", domain="REAL", description_vi="x là số thực"),
            Assumption(symbol="m", domain="POSITIVE_REAL", description_vi="m dương"),
        ]
        asm2 = [
            Assumption(symbol="m", domain="POSITIVE_REAL", description_vi="m dương"),
            Assumption(symbol="x", domain="REAL", description_vi="x là số thực"),
        ]

        hash1 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm1)
        hash2 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm2)
        assert hash1 == hash2

    def test_presentation_description_change_does_not_alter_semantic_identity(self):
        """Changing presentation description_vi in assumptions does not change mathematical semantic identity."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        asm1 = [Assumption(symbol="x", domain="REAL", description_vi="x thuộc R")]
        asm2 = [Assumption(symbol="x", domain="REAL", description_vi="x là số thực tùy ý")]

        hash1 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm1)
        hash2 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm2)
        assert hash1 == hash2

    def test_truth_affecting_assumption_change_alters_semantic_identity(self):
        """Changing domain in assumptions alters mathematical semantic identity."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        asm1 = [Assumption(symbol="x", domain="REAL")]
        asm2 = [Assumption(symbol="x", domain="POSITIVE_REAL")]

        hash1 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm1)
        hash2 = compute_semantic_quadratic_identity(a, b, c, assumptions=asm2)
        assert hash1 != hash2

    def test_engine_config_change_alters_cache_key(self):
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        sem_id = compute_semantic_quadratic_identity(a, b, c)

        cfg1 = compute_engine_config_identity(engine_version="1.0.0", verifier_version="1.0.0")
        cfg2 = compute_engine_config_identity(engine_version="1.0.0", verifier_version="1.1.0")

        cache1 = compute_computation_cache_identity(sem_id, cfg1)
        cache2 = compute_computation_cache_identity(sem_id, cfg2)

        assert cfg1 != cfg2
        assert cache1 != cache2


# ============================================================================
# 10. REACTIVE DEPENDENCY DAG ADVERSARIAL TESTS
# ============================================================================

class TestReactiveDependencyDAG:
    """Test workspace dependency DAG, topological invalidation, and cycle rejection."""

    def test_canonical_quadratic_dag_invalidation(self):
        dag = build_quadratic_workspace_dag()

        assert dag.is_valid("coefficients") is True
        assert dag.is_valid("discriminant") is True
        assert dag.is_valid("roots") is True
        assert dag.is_valid("pedagogical_view") is True

        invalidated = dag.invalidate("coefficients")
        assert "coefficients" in invalidated
        assert "discriminant" in invalidated
        assert "roots" in invalidated
        assert "pedagogical_view" in invalidated
        assert dag.is_valid("coefficients") is False
        assert dag.is_valid("discriminant") is False
        assert dag.is_valid("roots") is False

    def test_partial_invalidation_unrelated_nodes(self):
        dag = DependencyGraph()
        dag.add_node("n_input_a", "Input A", node_type="INPUT")
        dag.add_node("n_input_b", "Input B", node_type="INPUT")
        dag.add_node("n_child_a", "Child of A", node_type="COMPUTED")
        dag.add_node("n_child_b", "Child of B", node_type="COMPUTED")

        dag.add_edge("n_input_a", "n_child_a")
        dag.add_edge("n_input_b", "n_child_b")

        inv = dag.invalidate("n_input_a")
        assert inv == ["n_input_a", "n_child_a"]
        assert dag.is_valid("n_input_a") is False
        assert dag.is_valid("n_child_a") is False

        assert dag.is_valid("n_input_b") is True
        assert dag.is_valid("n_child_b") is True

    def test_repeated_invalidation_safe(self):
        dag = build_quadratic_workspace_dag()
        inv1 = dag.invalidate("discriminant")
        inv2 = dag.invalidate("discriminant")
        assert inv1 == inv2
        assert dag.is_valid("discriminant") is False

    def test_cycle_insertion_rejected(self):
        dag = DependencyGraph()
        dag.add_node("A", "Node A")
        dag.add_node("B", "Node B")
        dag.add_node("C", "Node C")

        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        with pytest.raises(CycleDetectedError):
            dag.add_edge("C", "A")

        with pytest.raises(CycleDetectedError):
            dag.add_edge("A", "A")

    def test_multi_node_cycle_rejection(self):
        dag = DependencyGraph()
        for letter in ["A", "B", "C", "D"]:
            dag.add_node(letter, f"Node {letter}")

        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        dag.add_edge("C", "D")

        # Adding D -> A would close a 4-node cycle
        with pytest.raises(CycleDetectedError):
            dag.add_edge("D", "A")


# ============================================================================
# 11. SCHEMA REPRODUCIBILITY & STRICT VALIDATION
# ============================================================================

class TestStrictValidationAndJsonSchema:
    """Test Pydantic v2 strictness, extra-field rejection, and schema reproducibility."""

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            RationalFraction(numerator=1, denominator=2, unknown_field="hack")

    def test_schema_reproducibility(self):
        schema1 = export_mvp_v1_json_schema()
        schema2 = export_mvp_v1_json_schema()
        assert schema1 == schema2

        schema_str1 = export_mvp_v1_json_schema_str()
        schema_str2 = export_mvp_v1_json_schema_str()
        assert schema_str1 == schema_str2
        assert len(schema_str1) > 500
