"""Tests for Knowledge Base Pydantic Schemas."""

import pytest
from pydantic import ValidationError

from mke.models.enums import MethodAdmissibility, MethodId, ObligationId, Split, TransferValidity
from mke.knowledge.schemas import (
    DatasetManifest,
    EquationClass,
    FamilyRecord,
    MethodAnnotation,
    MethodInstance,
    MethodTemplate,
    ProblemRecord,
    ReviewStatus,
    TransferCategory,
    TransferPairRecord,
)


def test_method_template_valid():
    """Verify valid MethodTemplate instantiates properly."""
    mt = MethodTemplate(
        method_id=MethodId.M1_LINEAR_EQUATION,
        method_version="1.0.0",
        name_vi="Phương pháp giải bậc nhất",
        name_en="Linear Method",
        mathematical_scope="ax + b = 0",
        structural_preconditions=["deg(P) == 1"],
        mathematical_preconditions=["a != 0"],
        required_proof_obligations=[ObligationId.NONZERO_GUARD],
        parameterization_schema={"a": "float", "b": "float"},
        expected_transformation_type="ISOLATION",
        possible_failure_modes=["DIV_BY_ZERO"],
        supported_equation_classes=[EquationClass.LINEAR],
        prerequisite_mathematical_concepts=["Rational arithmetic"],
        human_readable_explanation="Chuyển vế ax = -b rồi chia cho a",
    )
    assert mt.method_id == MethodId.M1_LINEAR_EQUATION
    assert mt.review_status == ReviewStatus.PROVISIONAL


def test_method_instance_valid():
    """Verify MethodInstance schema."""
    inst = MethodInstance(
        instance_id="INST_P01_M1",
        method_id=MethodId.M1_LINEAR_EQUATION,
        parameters={"a": "2", "b": "4"},
        explanation="2*x + 4 = 0 => x = -2",
    )
    assert inst.instance_id == "INST_P01_M1"
    assert inst.method_version == "1.0.0"


def test_family_record_valid():
    """Verify FamilyRecord schema and split_group_id."""
    fam = FamilyRecord(
        family_id="FAM_01_LIN_BASIC",
        name="Linear Basic",
        description="Linear equations ax + b = 0",
        equation_class=EquationClass.LINEAR,
        split_group_id="SG_LIN_BASIC",
        dependent_family_ids=[],
        supported_methods=[MethodId.M1_LINEAR_EQUATION],
    )
    assert fam.split_group_id == "SG_LIN_BASIC"
    assert fam.review_status == ReviewStatus.PROVISIONAL


def test_problem_record_valid():
    """Verify ProblemRecord schema with required fields."""
    prob = ProblemRecord(
        problem_id="PROB_FAM01_V01",
        family_id="FAM_01_LIN_BASIC",
        variant_id="V01",
        split=Split.DEV,
        original_expression="2*x + 4 = 0",
        canonical_representation="2*x + 4 = 0",
        raw_ast={"type": "Equation"},
        domain_str="R",
        excluded_points=[],
        equation_class=EquationClass.LINEAR,
        near_miss_category=TransferCategory.POSITIVE,
        expected_roots=["-2"],
        is_identity_on_domain=False,
        is_empty_domain=False,
    )
    assert prob.problem_id == "PROB_FAM01_V01"
    assert prob.split == Split.DEV
    assert prob.expected_roots == ["-2"]


def test_method_annotation_valid():
    """Verify MethodAnnotation schema and foreign key binding fields."""
    ann = MethodAnnotation(
        annotation_id="ANN_PROB_FAM01_V01_M1",
        problem_id="PROB_FAM01_V01",
        method_id=MethodId.M1_LINEAR_EQUATION,
        method_version="1.0.0",
        method_instance_id="INST_PROB_FAM01_V01_M1",
        admissibility=MethodAdmissibility.APPLICABLE,
        review_status=ReviewStatus.PROVISIONAL,
        annotation_evidence="Degree 1 polynomial, leading coeff 2 != 0",
    )
    assert ann.method_instance_id == "INST_PROB_FAM01_V01_M1"
    assert ann.admissibility == MethodAdmissibility.APPLICABLE


def test_transfer_pair_record_valid():
    """Verify TransferPairRecord schema with safety and transfer category."""
    pair = TransferPairRecord(
        pair_id="TP_FAM04_FAM11_01",
        source_problem_id="PROB_FAM04_V01",
        target_problem_id="PROB_FAM11_V01",
        method_id=MethodId.M2_QUADRATIC_FORMULA,
        transfer_category=TransferCategory.TRANSFER_NEAR_MISS,
        guard_obligations=[ObligationId.ORIGINAL_DOMAIN],
        proposed_transfer_status=TransferValidity.UNSAFE_COPY,
        annotation_evidence="Denominator becomes zero at x=2",
        review_status=ReviewStatus.PROVISIONAL,
    )
    assert pair.proposed_transfer_status == TransferValidity.UNSAFE_COPY
    assert pair.guard_obligations == [ObligationId.ORIGINAL_DOMAIN]


def test_dataset_manifest_valid():
    """Verify DatasetManifest schema."""
    manifest = DatasetManifest(
        dataset_name="DEV_PILOT",
        split=Split.DEV,
        file_hashes={"problems.jsonl": "abc123sha"},
        record_counts={"problems": 41},
    )
    assert manifest.split == Split.DEV
    assert manifest.record_counts["problems"] == 41


def test_invalid_pydantic_schema_raises():
    """Verify invalid inputs raise validation error."""
    with pytest.raises(ValidationError):
        # Missing required fields
        FamilyRecord(
            family_id="FAM_TEST",
            name="Test",
            # missing description, equation_class, split_group_id
        )
