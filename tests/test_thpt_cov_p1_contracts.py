"""Tests for THPT Universal Coverage Engine P1 Core Contracts & Deep Immutability."""

from __future__ import annotations

from typing import Any
import pytest
from pydantic import ValidationError

from mke_product.core.rational import Rational
from mke_product.coverage.benchmark import (
    BenchmarkCase,
    BenchmarkDifficulty,
    BenchmarkDomain,
    BenchmarkRightsStatus,
    BenchmarkSourceType,
    BenchmarkSplit,
    ExpectedAnswerSpec,
    ExpectedAnswerType,
    FiniteSetAnswerSpec,
    GradeBand,
    ScalarAnswerSpec,
)
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
    AssumptionSpec,
    CalculusOpKind,
    CalculusOperationPayload,
    CandidateMetadata,
    CandidateSolution,
    ConstraintRelation,
    DomainCategory,
    DomainSpecification,
    EmptyRealSolutionEntity,
    FiniteRootCollectionEntity,
    FunctionAnalysisPayload,
    GeometricElementKind,
    GeometricElementSpec,
    GeometryCoordinatePayload,
    MatrixOpKind,
    MatrixOperationPayload,
    PayloadKind,
    ProblemIR,
    ProblemKind,
    ProblemTarget,
    ProofObligationResult,
    RationalScalarEntity,
    RealQuadraticSurdEntity,
    SingleEquationPayload,
    SingleInequalityPayload,
    SolutionTrace,
    SourceInputKind,
    SystemOfEquationsPayload,
    TraceStep,
    VerificationDisposition,
    VerificationLevel,
    VerificationReport,
)
from mke_product.parser.ast import IntegerLiteral, Variable


# ---------------------------------------------------------------------------
# Helper: Recursive Immutability Inspector
# ---------------------------------------------------------------------------

def assert_recursively_immutable(obj: Any, visited: set | None = None) -> None:
    """Recursively traverse an object graph and assert no mutable list, dict, or set exists."""
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return
    visited.add(obj_id)

    # Check for mutable collections
    assert not isinstance(obj, list), f"Found mutable list at {type(obj)}: {obj}"
    assert not isinstance(obj, dict), f"Found mutable dict at {type(obj)}: {obj}"
    assert not isinstance(obj, set), f"Found mutable set at {type(obj)}: {obj}"

    if isinstance(obj, tuple):
        for item in obj:
            assert_recursively_immutable(item, visited)
    elif hasattr(obj, "__dict__"):
        for key, val in vars(obj).items():
            if not key.startswith("__"):
                assert_recursively_immutable(val, visited)
    elif hasattr(obj, "__slots__"):
        for slot in obj.__slots__:
            if hasattr(obj, slot):
                assert_recursively_immutable(getattr(obj, slot), visited)


# ---------------------------------------------------------------------------
# Test Enum Sets
# ---------------------------------------------------------------------------

class TestP1Enums:
    def test_problem_kind_exact_set(self):
        expected = {
            "ALGEBRA_EQUATION", "ALGEBRA_INEQUALITY", "ALGEBRA_SYSTEM",
            "EXPONENTIAL_EQUATION", "EXPONENTIAL_INEQUALITY",
            "LOGARITHMIC_EQUATION", "LOGARITHMIC_INEQUALITY",
            "TRIGONOMETRIC_EQUATION", "TRIGONOMETRIC_INEQUALITY",
            "FUNCTION_ANALYSIS", "DERIVATIVE", "LIMIT",
            "ANTIDERIVATIVE", "DEFINITE_INTEGRAL", "OPTIMIZATION",
            "COMPLEX_NUMBER", "MATRIX", "VECTOR",
            "COORDINATE_GEOMETRY_2D", "COORDINATE_GEOMETRY_3D",
            "COMBINATORICS", "PROBABILITY", "STATISTICS",
            "WORD_PROBLEM", "GEOMETRY_TEXT", "UNKNOWN",
        }
        actual = {k.value for k in ProblemKind}
        assert actual == expected

    def test_verification_level_exact_set(self):
        expected = {"EXACT_VERIFIED", "SYMBOLIC_VERIFIED", "CROSS_CHECKED", "PARTIAL", "UNSUPPORTED"}
        actual = {lvl.value for lvl in VerificationLevel}
        assert actual == expected
        assert "UNRESOLVED" not in actual

    def test_verification_disposition_exact_set(self):
        expected = {"ACCEPTED", "PARTIAL", "REJECTED", "UNSUPPORTED"}
        actual = {d.value for d in VerificationDisposition}
        assert actual == expected

    def test_expected_answer_type_exact_set(self):
        expected = {
            "FINITE_SET", "INTERVAL_SET", "EXPRESSION", "SCALAR",
            "TUPLE_SET", "MATRIX", "BOOLEAN", "STATISTICAL_VALUE", "STRUCTURED",
        }
        actual = {t.value for t in ExpectedAnswerType}
        assert actual == expected

    def test_benchmark_split_exact_set(self):
        expected = {"DEV", "HOLDOUT", "ADVERSARIAL"}
        actual = {s.value for s in BenchmarkSplit}
        assert actual == expected


# ---------------------------------------------------------------------------
# Test ProblemIR Construction and Discriminator Invariants
# ---------------------------------------------------------------------------

class TestProblemIRAndPayloads:
    def test_valid_single_equation_problem_ir(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        payload = SingleEquationPayload(left=x, right=c, target_variable="x")
        ir = ProblemIR(
            problem_id="p1_eq_001",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.ALGEBRA_EQUATION
        assert ir.payload.payload_kind == PayloadKind.SINGLE_EQUATION

    def test_valid_single_inequality_problem_ir(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        payload = SingleInequalityPayload(left=x, right=c, relation=ConstraintRelation.GT, target_variable="x")
        ir = ProblemIR(
            problem_id="p1_ineq_001",
            problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.ALGEBRA_INEQUALITY
        assert ir.payload.payload_kind == PayloadKind.SINGLE_INEQUALITY

    def test_valid_system_of_equations_problem_ir(self):
        x = Variable("x")
        y = Variable("y")
        c1 = IntegerLiteral(1)
        c2 = IntegerLiteral(2)
        payload = SystemOfEquationsPayload(
            equations=((x, c1), (y, c2)),
            target_variables=("x", "y"),
        )
        ir = ProblemIR(
            problem_id="p1_sys_001",
            problem_kind=ProblemKind.ALGEBRA_SYSTEM,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.ALGEBRA_SYSTEM
        assert ir.payload.payload_kind == PayloadKind.SYSTEM_OF_EQUATIONS

    def test_valid_calculus_derivative_problem_ir(self):
        x = Variable("x")
        payload = CalculusOperationPayload(
            expression=x,
            operation=CalculusOpKind.DERIVATIVE,
            variable="x",
        )
        ir = ProblemIR(
            problem_id="p1_calc_001",
            problem_kind=ProblemKind.DERIVATIVE,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.DERIVATIVE
        assert ir.payload.payload_kind == PayloadKind.CALCULUS_OPERATION

    def test_valid_matrix_operation_problem_ir(self):
        c1 = IntegerLiteral(1)
        payload = MatrixOperationPayload(
            matrix_elements=((c1, c1), (c1, c1)),
            operation=MatrixOpKind.DETERMINANT,
        )
        ir = ProblemIR(
            problem_id="p1_mat_001",
            problem_kind=ProblemKind.MATRIX,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.MATRIX
        assert ir.payload.payload_kind == PayloadKind.MATRIX_OPERATION

    def test_valid_geometry_coordinate_problem_ir(self):
        payload = GeometryCoordinatePayload(
            dimension=2,
            elements=(GeometricElementSpec(element_id="A", kind=GeometricElementKind.POINT),),
            query_target="distance",
        )
        ir = ProblemIR(
            problem_id="p1_geo_001",
            problem_kind=ProblemKind.COORDINATE_GEOMETRY_2D,
            payload=payload,
        )
        assert ir.problem_kind == ProblemKind.COORDINATE_GEOMETRY_2D
        assert ir.payload.payload_kind == PayloadKind.GEOMETRY_COORDINATE

    def test_rejects_mismatched_kind_and_payload(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        eq_payload = SingleEquationPayload(left=x, right=c, target_variable="x")
        mat_payload = MatrixOperationPayload(matrix_elements=((c,),), operation=MatrixOpKind.RANK)

        # ALGEBRA_EQUATION + MATRIX_OPERATION
        with pytest.raises(ValidationError, match="requires payload_kind 'SINGLE_EQUATION'"):
            ProblemIR(problem_id="err_1", problem_kind=ProblemKind.ALGEBRA_EQUATION, payload=mat_payload)

        # DERIVATIVE + SINGLE_EQUATION
        with pytest.raises(ValidationError, match="requires payload_kind 'CALCULUS_OPERATION'"):
            ProblemIR(problem_id="err_2", problem_kind=ProblemKind.DERIVATIVE, payload=eq_payload)

    def test_rejects_unsupported_p1_problem_kind_payload(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        eq_payload = SingleEquationPayload(left=x, right=c, target_variable="x")

        # Kinds without P1 payload contracts must fail closed
        unsupported_kinds = [
            ProblemKind.OPTIMIZATION,
            ProblemKind.COMPLEX_NUMBER,
            ProblemKind.VECTOR,
            ProblemKind.COMBINATORICS,
            ProblemKind.PROBABILITY,
            ProblemKind.STATISTICS,
            ProblemKind.WORD_PROBLEM,
            ProblemKind.GEOMETRY_TEXT,
            ProblemKind.UNKNOWN,
        ]
        for kind in unsupported_kinds:
            with pytest.raises(ValidationError, match="has no supported payload contract in P1"):
                ProblemIR(problem_id=f"unsupported_{kind.value}", problem_kind=kind, payload=eq_payload)


# ---------------------------------------------------------------------------
# Test Deep Immutability
# ---------------------------------------------------------------------------

class TestDeepImmutability:
    def test_problem_ir_field_reassignment_forbidden(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        ir = ProblemIR(
            problem_id="p1_001",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=SingleEquationPayload(left=x, right=c),
        )
        with pytest.raises(ValidationError):
            ir.problem_id = "mutated"  # type: ignore

    def test_problem_ir_unknown_fields_forbidden(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        with pytest.raises(ValidationError):
            ProblemIR(
                problem_id="p1_001",
                problem_kind=ProblemKind.ALGEBRA_EQUATION,
                payload=SingleEquationPayload(left=x, right=c),
                unknown_extra_field="invalid",  # type: ignore
            )

    def test_tuple_collections_cannot_be_mutated(self):
        ir = ProblemIR(
            problem_id="p1_001",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=SingleEquationPayload(left=Variable("x"), right=IntegerLiteral(0)),
            variables=("x",),
            assumptions=(
                AssumptionSpec(variable="x", relation=ConstraintRelation.GT, bound_expression=IntegerLiteral(0)),
            ),
        )
        assert not hasattr(ir.variables, "append")
        assert not hasattr(ir.variables, "clear")
        assert not hasattr(ir.assumptions, "append")
        with pytest.raises(TypeError):
            ir.variables[0] = "y"  # type: ignore

    def test_recursive_immutability_on_authoritative_objects(self):
        x = Variable("x")
        c = IntegerLiteral(0)
        payload = SingleEquationPayload(left=x, right=c, target_variable="x")
        assumption = AssumptionSpec(
            variable="x",
            relation=ConstraintRelation.GE,
            bound_expression=c,
            target_domain=DomainCategory.REALS,
        )
        ir = ProblemIR(
            problem_id="p1_imm_001",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=payload,
            assumptions=(assumption,),
        )
        assert_recursively_immutable(ir)

        candidate = CandidateSolution(
            candidate_id="cand_001",
            generator_engine="test.engine",
            raw_symbolic_output="x = 0",
            parsed_entities=(
                FiniteRootCollectionEntity(
                    roots=(RationalScalarEntity(numerator=0, denominator=1),)
                ),
            ),
            assumptions_used=(assumption,),
            metadata=CandidateMetadata(engine_version="1.0", transformation_steps=("step1",)),
        )
        assert_recursively_immutable(candidate)


# ---------------------------------------------------------------------------
# Test CandidateSolution and SymbolicEntity
# ---------------------------------------------------------------------------

class TestCandidateSolutionContracts:
    def test_candidate_solution_contains_no_truth_boolean(self):
        fields = CandidateSolution.model_fields.keys()
        assert "is_correct" not in fields
        assert "trusted" not in fields
        assert "is_verified" not in fields
        assert "verified" not in fields

    def test_candidate_metadata_is_immutable(self):
        meta = CandidateMetadata(engine_version="1.0.0", flags=(("fast_mode", "true"),))
        with pytest.raises(ValidationError):
            meta.engine_version = "2.0.0"  # type: ignore
        assert_recursively_immutable(meta)

    def test_symbolic_entities_structure(self):
        rat = RationalScalarEntity(numerator=2, denominator=3, latex="\\frac{2}{3}")
        assert rat.to_rational == Rational(2, 3)

        surd = RealQuadraticSurdEntity(p=1, q=1, d=2, r=1, latex="1 + \\sqrt{2}")
        roots = FiniteRootCollectionEntity(roots=(rat, surd))
        assert roots.cardinality == 2

        empty = EmptyRealSolutionEntity()
        all_reals = AllRealSolutionEntity()
        assert empty.entity_kind == "EMPTY_REAL_SOLUTION"
        assert all_reals.entity_kind == "ALL_REAL_SOLUTION"


# ---------------------------------------------------------------------------
# Test VerificationReport Truth Table Invariants
# ---------------------------------------------------------------------------

class TestVerificationReportInvariants:
    def test_exact_verified_requires_accepted(self):
        report = VerificationReport(
            verification_id="ver_001",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.EXACT_VERIFIED,
            disposition=VerificationDisposition.ACCEPTED,
            certificate_hash="abc123hash",
        )
        assert report.verification_level == VerificationLevel.EXACT_VERIFIED

        # Contradictory: EXACT_VERIFIED + REJECTED
        with pytest.raises(ValidationError, match="requires disposition ACCEPTED"):
            VerificationReport(
                verification_id="ver_002",
                verifier_name="TEST_VERIFIER",
                verification_level=VerificationLevel.EXACT_VERIFIED,
                disposition=VerificationDisposition.REJECTED,
                certificate_hash="abc123hash",
            )

    def test_symbolic_verified_requires_accepted(self):
        report = VerificationReport(
            verification_id="ver_001",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.SYMBOLIC_VERIFIED,
            disposition=VerificationDisposition.ACCEPTED,
            certificate_hash="abc123hash",
        )
        assert report.disposition == VerificationDisposition.ACCEPTED

        with pytest.raises(ValidationError, match="requires disposition ACCEPTED"):
            VerificationReport(
                verification_id="ver_002",
                verifier_name="TEST_VERIFIER",
                verification_level=VerificationLevel.SYMBOLIC_VERIFIED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash="abc123hash",
            )

    def test_cross_checked_requires_accepted(self):
        report = VerificationReport(
            verification_id="ver_001",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.CROSS_CHECKED,
            disposition=VerificationDisposition.ACCEPTED,
            certificate_hash="abc123hash",
        )
        assert report.verification_level == VerificationLevel.CROSS_CHECKED

        with pytest.raises(ValidationError, match="requires disposition ACCEPTED"):
            VerificationReport(
                verification_id="ver_002",
                verifier_name="TEST_VERIFIER",
                verification_level=VerificationLevel.CROSS_CHECKED,
                disposition=VerificationDisposition.REJECTED,
                certificate_hash="abc123hash",
            )

    def test_partial_requires_partial(self):
        report = VerificationReport(
            verification_id="ver_001",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.PARTIAL,
            disposition=VerificationDisposition.PARTIAL,
            certificate_hash="abc123hash",
        )
        assert report.disposition == VerificationDisposition.PARTIAL

        with pytest.raises(ValidationError, match="requires disposition PARTIAL"):
            VerificationReport(
                verification_id="ver_002",
                verifier_name="TEST_VERIFIER",
                verification_level=VerificationLevel.PARTIAL,
                disposition=VerificationDisposition.ACCEPTED,
                certificate_hash="abc123hash",
            )

    def test_unsupported_allows_unsupported_or_rejected(self):
        r1 = VerificationReport(
            verification_id="ver_001",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.UNSUPPORTED,
            disposition=VerificationDisposition.UNSUPPORTED,
            certificate_hash="abc123hash",
        )
        r2 = VerificationReport(
            verification_id="ver_002",
            verifier_name="TEST_VERIFIER",
            verification_level=VerificationLevel.UNSUPPORTED,
            disposition=VerificationDisposition.REJECTED,
            certificate_hash="abc123hash",
        )
        assert r1.disposition == VerificationDisposition.UNSUPPORTED
        assert r2.disposition == VerificationDisposition.REJECTED

        # Contradictory: UNSUPPORTED + ACCEPTED
        with pytest.raises(ValidationError, match="cannot have disposition ACCEPTED"):
            VerificationReport(
                verification_id="ver_003",
                verifier_name="TEST_VERIFIER",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.ACCEPTED,
                certificate_hash="abc123hash",
            )


# ---------------------------------------------------------------------------
# Test BenchmarkCase Schemas and Answer Types
# ---------------------------------------------------------------------------

class TestBenchmarkCaseContracts:
    def test_valid_benchmark_case(self):
        case = BenchmarkCase(
            case_id="THPT_DEV_001",
            grade_band=GradeBand.GRADE_10,
            domain=BenchmarkDomain.ALGEBRA,
            family="QUADRATIC_EQUATION",
            subfamily="STANDARD_FORM",
            source_type=BenchmarkSourceType.OFFICIAL_PUBLIC,
            source_locator="De_Thi_2024_Cau_1",
            rights_status=BenchmarkRightsStatus.SOURCE_LOCATOR_ONLY,
            expected_answer=ScalarAnswerSpec(value="3"),
            expected_answer_type=ExpectedAnswerType.SCALAR,
            split=BenchmarkSplit.DEV,
        )
        assert case.rights_status == BenchmarkRightsStatus.SOURCE_LOCATOR_ONLY
        assert case.source_type == BenchmarkSourceType.OFFICIAL_PUBLIC
        assert_recursively_immutable(case)

    def test_problem_ir_with_provenance_is_recursively_immutable(self):
        from mke_product.coverage.contracts import ProblemProvenance
        prov = ProblemProvenance(
            source_name="Ky Thi THPT 2024",
            source_reference="Ma de 101 - Cau 32",
            license_or_rights="PUBLIC",
            citation_text="De thi tot nghiep THPT 2024 mon Toan",
            tags=(("year", "2024"), ("grade", "12")),
        )
        ir = ProblemIR(
            problem_id="p1_prov_001",
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            payload=SingleEquationPayload(left=Variable("x"), right=IntegerLiteral(0)),
            provenance=prov,
        )
        assert_recursively_immutable(ir)
        assert ir.provenance is not None
        assert ir.provenance.source_name == "Ky Thi THPT 2024"

    def test_all_nine_expected_answer_specs_supported(self):
        from mke_product.coverage.benchmark import (
            BooleanAnswerSpec,
            ExpressionAnswerSpec,
            FiniteSetAnswerSpec,
            IntervalSetAnswerSpec,
            MatrixAnswerSpec,
            ScalarAnswerSpec,
            StatisticalValueAnswerSpec,
            StructuredAnswerSpec,
            TupleSetAnswerSpec,
        )

        specs = [
            (ExpectedAnswerType.SCALAR, ScalarAnswerSpec(value="5")),
            (ExpectedAnswerType.FINITE_SET, FiniteSetAnswerSpec(elements=("1", "2"))),
            (ExpectedAnswerType.INTERVAL_SET, IntervalSetAnswerSpec(intervals=("[0, 1)",))),
            (ExpectedAnswerType.EXPRESSION, ExpressionAnswerSpec(expression_latex="2x + 1")),
            (ExpectedAnswerType.STRUCTURED, StructuredAnswerSpec(payload_pairs=(("k", "v"),))),
            (ExpectedAnswerType.TUPLE_SET, TupleSetAnswerSpec(tuples=(("1", "2"), ("3", "4")))),
            (ExpectedAnswerType.MATRIX, MatrixAnswerSpec(rows=(("1", "0"), ("0", "1")))),
            (ExpectedAnswerType.BOOLEAN, BooleanAnswerSpec(value=True)),
            (ExpectedAnswerType.STATISTICAL_VALUE, StatisticalValueAnswerSpec(metric_name="mean", numeric_value="7.5")),
        ]

        assert len(specs) == 9

        for ans_type, spec in specs:
            case = BenchmarkCase(
                case_id=f"case_{ans_type.value}",
                expected_answer=spec,
                expected_answer_type=ans_type,
            )
            assert case.expected_answer_type == ans_type
            assert_recursively_immutable(case)

    def test_benchmark_case_rejects_mismatched_answer_type(self):
        with pytest.raises(ValidationError, match="expected_answer_type mismatch"):
            BenchmarkCase(
                case_id="case_mismatch",
                expected_answer=ScalarAnswerSpec(value="5"),
                expected_answer_type=ExpectedAnswerType.FINITE_SET,
            )
