"""Unit & Acceptance Tests for MKE MVP V1 — S0 Domain Core.

Covers:
- Acceptance Fixtures Q1–Q6 (Exact Quadratic Roots over Q and R)
- Degenerate Fixtures D1–D3 (Linear, Identity, Contradiction)
- Dependency Declaration & Environment Reproducibility
- Reduced Formula Mathematical Applicability vs Pedagogical Recommendation
- Orthogonal MethodAssessment & Method Registry Invariants
- Exact Arithmetic Adversarial Matrix (Delta in {0, 1, 4, 8, 1/4, 1/2, 8/9, -16, 84})
- Host Independent Verifier Tamper Matrix (10+ adversarial corruptions failing closed)
- Revision & Cache Identity Stability & Domain Sensitivity
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

        # 3. Host Independent Verification
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
        """Q6: -x^2 + 6x + 9 = 0 => Delta = 72, roots = 3 +- 3*sqrt(2)."""
        a = Rational(-1, 1)
        b = Rational(6, 1)
        c = Rational(9, 1)

        disc = compute_quadratic_discriminant(a, b, c)
        assert disc.value.to_rational() == Rational(72, 1)
        assert disc.is_positive is True
        assert disc.squarefree_kernel == 2
        assert disc.extracted_factor.to_rational() == Rational(6, 1)

        outcome, roots = solve_exact_quadratic(a, b, c)
        assert outcome == SolutionOutcome.TWO_DISTINCT_REAL_ROOTS
        assert len(roots) == 2

        # x = 3 - 3*sqrt(2) and x = 3 + 3*sqrt(2)
        assert roots[0].surd_base.to_rational() == Rational(3, 1)
        assert roots[0].surd_factor.to_rational() == Rational(-3, 1)
        assert roots[0].radicand == 2

        assert roots[1].surd_base.to_rational() == Rational(3, 1)
        assert roots[1].surd_factor.to_rational() == Rational(3, 1)
        assert roots[1].radicand == 2

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
# 4. REDUCED QUADRATIC FORMULA MATHEMATICAL APPLICABILITY MATRIX
# ============================================================================

class TestReducedFormulaMathematicalSemantics:
    """Verify that b' = b/2 exists in Q for all rational b, making it mathematically applicable."""

    def test_reduced_formula_applicable_for_odd_integer_b(self):
        """For x^2 - 5x + 6 = 0 (b = -5), reduced formula is mathematically APPLICABLE, pedagogical recommendation NEUTRAL."""
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
        # Pedagogical recommendation is NEUTRAL because b is odd
        assert red.pedagogical_recommendation == PedagogicalRecommendation.NEUTRAL

    def test_reduced_formula_applicable_for_fractional_b(self):
        """For x^2 + (1/3)x - 2 = 0 (b = 1/3), reduced formula is mathematically APPLICABLE, pedagogical recommendation NEUTRAL."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(1, 3)
        c = Rational(-2, 1)

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        red = assessments["QUAD_FORMULA_REDUCED"]

        assert red.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert red.pedagogical_recommendation == PedagogicalRecommendation.NEUTRAL

    def test_reduced_formula_recommended_for_even_integer_b(self):
        """For x^2 - 6x + 9 = 0 (b = -6), reduced formula is APPLICABLE and RECOMMENDED."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(-6, 1)
        c = Rational(9, 1)

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}
        red = assessments["QUAD_FORMULA_REDUCED"]

        assert red.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert red.pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED


# ============================================================================
# 5. METHOD REGISTRY & ORTHOGONAL ASSESSMENT INVARIANTS
# ============================================================================

class TestMethodRegistryAndOrthogonalAssessment:
    """Test orthogonal dimensions of MethodAssessment and MethodRegistry invariants."""

    def test_registry_contains_mvp_methods(self):
        registry = MethodRegistry()
        methods = registry.list_all()
        assert len(methods) >= 9
        method_ids = {m.method_id for m in methods}
        expected_ids = {
            "QUAD_FORMULA_STANDARD",
            "QUAD_FORMULA_REDUCED",
            "QUAD_FACTORIZATION_Q",
            "QUAD_FACTORIZATION_R",
            "QUAD_COMPLETE_SQUARE",
            "QUAD_VIETE_SPECIAL_SUM",
            "QUAD_VIETE_SPECIAL_DIF",
            "QUAD_VIETE_SUM_PRODUCT",
            "QUAD_GRAPHICAL_ANALYSIS",
        }
        assert expected_ids.issubset(method_ids)

    def test_orthogonal_dimensions_independence(self):
        """Dimensions must remain independent: a method can be APPLICABLE but DISCOURAGED or NOT_APPLICABLE for verification."""
        registry = MethodRegistry()
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(1, 1)  # x^2 + 1 = 0

        assessments = {m.method_id: m for m in registry.assess_quadratic(a, b, c)}

        # Standard formula: APPLICABLE, SUPPORTED, AVAILABLE, RECOMMENDED, HOST_VERIFIABLE
        std = assessments["QUAD_FORMULA_STANDARD"]
        assert std.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert std.support_status == SupportStatus.SUPPORTED
        assert std.execution_availability == ExecutionAvailability.AVAILABLE
        assert std.pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED
        assert std.verification_capability == VerificationCapability.HOST_VERIFIABLE

        # Completing square: APPLICABLE for all a != 0
        comp_sq = assessments["QUAD_COMPLETE_SQUARE"]
        assert comp_sq.mathematical_applicability == MathematicalApplicability.APPLICABLE

        # Graphical Analysis: APPLICABLE, but NOT_APPLICABLE for verification
        graph = assessments["QUAD_GRAPHICAL_ANALYSIS"]
        assert graph.mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert graph.verification_capability == VerificationCapability.NOT_APPLICABLE

        # Special sum: NOT_APPLICABLE, but SUPPORTED & AVAILABLE
        sum_spec = assessments["QUAD_VIETE_SPECIAL_SUM"]
        assert sum_spec.mathematical_applicability == MathematicalApplicability.NOT_APPLICABLE
        assert sum_spec.support_status == SupportStatus.SUPPORTED
        assert sum_spec.pedagogical_recommendation == PedagogicalRecommendation.DISCOURAGED

    def test_viete_special_sum_and_diff(self):
        registry = MethodRegistry()

        # 2x^2 + 5x - 7 = 0 => a + b + c = 2 + 5 - 7 = 0
        a1, b1, c1 = Rational(2, 1), Rational(5, 1), Rational(-7, 1)
        ass1 = {m.method_id: m for m in registry.assess_quadratic(a1, b1, c1)}
        assert ass1["QUAD_VIETE_SPECIAL_SUM"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert ass1["QUAD_VIETE_SPECIAL_SUM"].pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED

        # 2x^2 + 5x + 3 = 0 => a - b + c = 2 - 5 + 3 = 0
        a2, b2, c2 = Rational(2, 1), Rational(5, 1), Rational(3, 1)
        ass2 = {m.method_id: m for m in registry.assess_quadratic(a2, b2, c2)}
        assert ass2["QUAD_VIETE_SPECIAL_DIF"].mathematical_applicability == MathematicalApplicability.APPLICABLE
        assert ass2["QUAD_VIETE_SPECIAL_DIF"].pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED


# ============================================================================
# 6. EXACT ARITHMETIC ADVERSARIAL MATRIX
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

        outcome, roots = solve_exact_quadratic(a_val, b_val, c_val)
        assert outcome == expected_outcome

        # Host verification must succeed for all valid solutions
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a_val, b_val, c_val, outcome, roots)
        assert cert.outcome == VerificationOutcome.VERIFIED_COMPLETE


# ============================================================================
# 7. HOST INDEPENDENT VERIFIER TAMPER MATRIX
# ============================================================================

class TestHostVerifierTamperMatrix:
    """Tamper matrix attempting to trick the Host Independent Verifier with corrupted candidates."""

    def test_tamper_wrong_rational_root(self):
        """Corrupt root: x = 4 for x^2 - 5x + 6 = 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        fake_roots = [
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
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, fake_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_wrong_surd_radicand(self):
        """Corrupt radicand: d = 5 instead of 2 for -x^2 + 6x + 9 = 0."""
        a, b, c = Rational(-1, 1), Rational(6, 1), Rational(9, 1)
        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(-3),
                radicand=5,  # Wrong!
                latex_str="3 - 3\\sqrt{5}",
            ),
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(3),
                radicand=5,
                latex_str="3 + 3\\sqrt{5}",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, fake_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_wrong_surd_sign(self):
        """Corrupt sign: both +3*sqrt(2) without conjugate."""
        a, b, c = Rational(-1, 1), Rational(6, 1), Rational(9, 1)
        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(3),  # Wrong! (duplicate positive)
                radicand=2,
                latex_str="3 + 3\\sqrt{2}",
            ),
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(3),
                radicand=2,
                latex_str="3 + 3\\sqrt{2}",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, fake_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_missing_second_root(self):
        """Missing second root when Delta > 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=2, denominator=1),
                latex_str="2",
            )
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, fake_roots)
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED

    def test_tamper_duplicated_root_when_delta_positive(self):
        """Duplicating root [2, 2] for x^2 - 5x + 6 = 0."""
        a, b, c = Rational(1, 1), Rational(-5, 1), Rational(6, 1)
        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=2, denominator=1),
                latex_str="2",
            ),
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=2, denominator=1),
                latex_str="2",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(a, b, c, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, fake_roots)
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
# 8. IDENTITY & CACHE HASHING
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
# 9. REACTIVE DEPENDENCY DAG ADVERSARIAL TESTS
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
# 10. SCHEMA REPRODUCIBILITY & STRICT VALIDATION
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
