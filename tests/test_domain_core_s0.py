"""Unit & Acceptance Tests for MKE MVP V1 — S0 Domain Core.

Covers:
- Acceptance Fixtures Q1–Q6 (Exact Quadratic Roots over Q and R)
- Degenerate Fixtures D1–D3 (Linear, Identity, Contradiction)
- Orthogonal MethodAssessment & Method Registry
- Host Independent Verifier & Tamper Resistance
- Reactive Dependency DAG & Cycle Rejection
- Revision & Cache Identity Stability
- Strict Model Validation & JSON Schema Export
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
    HostIndependentVerifier,
    MathematicalApplicability,
    MethodAssessment,
    MethodDefinition,
    MethodRegistry,
    NodeNotFoundError,
    PedagogicalRecommendation,
    ProblemCategory,
    ProblemIR,
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
# 1. ACCEPTANCE FIXTURES Q1–Q6 (EXACT QUADRATIC EQUATIONS)
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
        assert cert.no_real_root_verified is True

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
# 2. DEGENERATE FIXTURES D1–D3 (CLASSIFICATION ROUTING)
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

        # Test Pydantic model representation
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
# 3. METHOD REGISTRY & ORTHOGONAL ASSESSMENT
# ============================================================================

class TestMethodRegistryAndOrthogonalAssessment:
    """Test orthogonal dimensions of MethodAssessment and MethodRegistry."""

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

        # Graphical Analysis: APPLICABLE, SUPPORTED, AVAILABLE, RECOMMENDED, NOT_APPLICABLE for verification
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
# 4. HOST INDEPENDENT VERIFIER & TAMPER RESISTANCE
# ============================================================================

class TestHostVerifierAndTamperResistance:
    """Test independent host verifier gate and rejection of corrupt candidates."""

    def test_tamper_rejected_fake_rational_root(self):
        """Worker injects wrong root x = 4 for x^2 - 5x + 6 = 0 => Verification Fails."""
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.RATIONAL,
                rational_value=RationalFraction(numerator=4, denominator=1),
                latex_str="4",
            )
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(
            a, b, c,
            outcome=SolutionOutcome.TWO_DISTINCT_REAL_ROOTS,
            roots=fake_roots,
            problem_hash="tamper_hash",
        )
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED
        assert cert.vieta_relations_checked is False

    def test_tamper_rejected_fake_surd_radicand(self):
        """Worker claims x = 3 +- 3*sqrt(5) for -x^2 + 6x + 9 = 0 (true is sqrt(2)) => Fails."""
        a = Rational(-1, 1)
        b = Rational(6, 1)
        c = Rational(9, 1)

        fake_roots = [
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(-3),
                radicand=5,  # Fake! True is 2
                latex_str="3 - 3\\sqrt{5}",
            ),
            RealRootValue(
                root_type=SolutionRootType.REAL_SURD,
                surd_base=RationalFraction.from_int(3),
                surd_factor=RationalFraction.from_int(3),
                radicand=5,  # Fake!
                latex_str="3 + 3\\sqrt{5}",
            ),
        ]
        verifier = HostIndependentVerifier()
        cert = verifier.verify_quadratic_solution(
            a, b, c,
            outcome=SolutionOutcome.TWO_DISTINCT_REAL_ROOTS,
            roots=fake_roots,
            problem_hash="tamper_surd",
        )
        assert cert.outcome == VerificationOutcome.VERIFICATION_FAILED


# ============================================================================
# 5. REACTIVE DEPENDENCY DAG & INVALIDATION
# ============================================================================

class TestReactiveDependencyDAG:
    """Test workspace dependency DAG, topological invalidation, and cycle rejection."""

    def test_canonical_quadratic_dag_invalidation(self):
        dag = build_quadratic_workspace_dag()

        # Check all nodes initially valid
        assert dag.is_valid("coefficients") is True
        assert dag.is_valid("discriminant") is True
        assert dag.is_valid("roots") is True
        assert dag.is_valid("pedagogical_view") is True

        # Invalidate coefficients => invalidates all downstream in topological order
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

        # Invalidate only Input A
        inv = dag.invalidate("n_input_a")
        assert inv == ["n_input_a", "n_child_a"]
        assert dag.is_valid("n_input_a") is False
        assert dag.is_valid("n_child_a") is False

        # Input B and Child B remain valid!
        assert dag.is_valid("n_input_b") is True
        assert dag.is_valid("n_child_b") is True

    def test_cycle_insertion_rejected(self):
        dag = DependencyGraph()
        dag.add_node("A", "Node A")
        dag.add_node("B", "Node B")
        dag.add_node("C", "Node C")

        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        # Adding C -> A would form a cycle A -> B -> C -> A
        with pytest.raises(CycleDetectedError):
            dag.add_edge("C", "A")

        # Adding self loop A -> A rejected
        with pytest.raises(CycleDetectedError):
            dag.add_edge("A", "A")


# ============================================================================
# 6. REVISION IDENTITY & COMPUTATION CACHE IDENTITY
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

    def test_engine_config_change_alters_cache_key(self):
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)

        sem_id = compute_semantic_quadratic_identity(a, b, c)

        cfg1 = compute_engine_config_identity(engine_version="1.0.0", verifier_version="1.0.0")
        cfg2 = compute_engine_config_identity(engine_version="1.0.0", verifier_version="1.1.0")

        cache1 = compute_computation_cache_identity(sem_id, cfg1)
        cache2 = compute_computation_cache_identity(sem_id, cfg2)

        # Semantic hash is unchanged, but cache key MUST differ!
        assert cfg1 != cfg2
        assert cache1 != cache2


# ============================================================================
# 7. STRICT MODEL VALIDATION & JSON SCHEMA EXPORT
# ============================================================================

class TestStrictValidationAndJsonSchema:
    """Test Pydantic v2 strictness, extra-field rejection, and schema generation."""

    def test_extra_fields_forbidden(self):
        """Extra / unknown fields must raise ValidationError."""
        with pytest.raises(ValidationError):
            RationalFraction(numerator=1, denominator=2, unknown_field="hack")

    def test_deterministic_json_schema_export(self):
        schema = export_mvp_v1_json_schema()
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["version"] == "1.0.0"
        assert "QuadraticProblemIR" in schema["definitions"]
        assert "MethodAssessment" in schema["definitions"]
        assert "VerificationCertificate" in schema["definitions"]

        schema_str = export_mvp_v1_json_schema_str()
        assert len(schema_str) > 500


# ============================================================================
# 8. EXTENDED DOMAIN & EDGE CASE COVERAGE
# ============================================================================

class TestExtendedDomainCoverage:
    """Test full IR object composition, geometry contracts, traces, and exact arithmetic edge cases."""

    def test_quadratic_problem_ir_construction(self):
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        disc = compute_quadratic_discriminant(a, b, c)

        prob = QuadraticProblemIR(
            problem_id="prob_quad_01",
            raw_query="x^2 - 5x + 6 = 0",
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash=compute_semantic_quadratic_identity(a, b, c),
            a=RationalFraction.from_rational(a),
            b=RationalFraction.from_rational(b),
            c=RationalFraction.from_rational(c),
            equation_string="x^2 - 5*x + 6 = 0",
            discriminant=disc,
        )
        assert prob.a.numerator == 1
        assert prob.coefficient_domain == "Q"
        assert prob.solution_domain == "R"
        assert prob.classification == EquationClassificationType.QUADRATIC

    def test_geometry_problem_ir_and_proof_trace(self):
        from mke_product.domain import (
            GeometricPredicate,
            GeometricPrimitive,
            GeometricRelation,
            GeometryProblemIR,
            PrimitiveType,
            ProofOutcome,
            ProofStep,
            ProofTrace,
        )

        primitives = [
            GeometricPrimitive(id="triangle_ABC", type=PrimitiveType.TRIANGLE, parent_ids=["A", "B", "C"]),
            GeometricPrimitive(id="M", type=PrimitiveType.POINT),
            GeometricPrimitive(id="AM", type=PrimitiveType.SEGMENT, parent_ids=["A", "M"]),
        ]
        givens = [
            GeometricRelation(predicate=GeometricPredicate.NON_DEGENERATE_TRIANGLE, target_ids=["triangle_ABC"]),
            GeometricRelation(predicate=GeometricPredicate.EQUAL_LENGTH, target_ids=["AB", "AC"]),
            GeometricRelation(predicate=GeometricPredicate.MIDPOINT, target_ids=["M", "BC"]),
        ]
        goals = [
            GeometricRelation(predicate=GeometricPredicate.PERPENDICULAR, target_ids=["AM", "BC"]),
        ]

        geom_prob = GeometryProblemIR(
            problem_id="geom_prob_01",
            raw_query="Cho tam giác ABC cân tại A. M là trung điểm BC. Chứng minh AM vuông góc BC.",
            category=ProblemCategory.GEOMETRY_TRIANGLE,
            semantic_revision_hash="hash_geom_01",
            primitives=primitives,
            givens=givens,
            goals=goals,
        )
        assert len(geom_prob.primitives) == 3
        assert len(geom_prob.givens) == 3
        assert len(geom_prob.goals) == 1

        proof_steps = [
            ProofStep(
                step_id="step_1",
                canonical_rule_id="RULE_TRIANGLE_CONGRUENCE_SSS",
                statement_vi="Xét ΔABM và ΔACM có AB=AC, MB=MC, AM chung.",
                deduction_latex="\\Delta ABM = \\Delta ACM",
                premise_step_ids=[],
            ),
            ProofStep(
                step_id="step_2",
                canonical_rule_id="RULE_CORRESPONDING_ANGLES_SUPPLEMENTARY",
                statement_vi="Suy ra góc AMB = góc AMC = 90°.",
                deduction_latex="AM \\perp BC",
                premise_step_ids=["step_1"],
            ),
        ]
        proof = ProofTrace(
            proof_method_id="PROOF_CONGRUENCE_SSS",
            outcome=ProofOutcome.VERIFIED_PROOF,
            steps=proof_steps,
            qed_conclusion_vi="Vậy AM vuông góc BC (đpcm).",
        )
        assert proof.outcome == ProofOutcome.VERIFIED_PROOF
        assert len(proof.steps) == 2

    def test_squarefree_decomposition_comprehensive(self):
        assert decompose_integer_squarefree(0) == (0, 0)
        assert decompose_integer_squarefree(1) == (1, 1)
        assert decompose_integer_squarefree(4) == (2, 1)
        assert decompose_integer_squarefree(8) == (2, 2)
        assert decompose_integer_squarefree(9) == (3, 1)
        assert decompose_integer_squarefree(12) == (2, 3)
        assert decompose_integer_squarefree(18) == (3, 2)
        assert decompose_integer_squarefree(72) == (6, 2)
        assert decompose_integer_squarefree(100) == (10, 1)
        assert decompose_integer_squarefree(144) == (12, 1)
        # 2 * 3^2 * 5^3 = 2 * 9 * 125 = 2250 => k = 3 * 5 = 15, d = 2 * 5 = 10 => 15^2 * 10 = 225 * 10 = 2250
        assert decompose_integer_squarefree(2250) == (15, 10)

    def test_rational_squarefree_decomposition(self):
        # 2/9 => (1/3, 2)
        s, d = decompose_rational_squarefree(Rational(2, 9))
        assert s == Rational(1, 3)
        assert d == 2

        # 4/9 => (2/3, 1)
        s, d = decompose_rational_squarefree(Rational(4, 9))
        assert s == Rational(2, 3)
        assert d == 1

        # 50/8 = 25/4 => (5/2, 1)
        s, d = decompose_rational_squarefree(Rational(50, 8))
        assert s == Rational(5, 2)
        assert d == 1

    def test_dag_upstream_and_downstream_queries(self):
        dag = build_quadratic_workspace_dag()
        downstream = dag.get_downstream_nodes("discriminant")
        assert "roots" in downstream
        assert "method_assessments" in downstream
        assert "pedagogical_view" in downstream
        assert "coefficients" not in downstream

        upstream = dag.get_upstream_nodes("pedagogical_view")
        assert "coefficients" in upstream
        assert "discriminant" in upstream
        assert "roots" in upstream

