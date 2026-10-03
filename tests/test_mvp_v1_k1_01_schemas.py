"""MKE MVP V1 — Milestone K1-01 Schema Contracts Test Suite.

Verifies strict Pydantic v2 validation, immutability, extra-field rejection,
relation-list hygiene, evidence partition integrity, and fail-closed defaults
for all K1 QuickTip and ProblemForm schema contracts.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from mke_product.knowledge.schemas import (
    CurriculumMappingStatus,
    CurriculumRef,
    LocalizedText,
)
from mke_product.knowledge.k1_schemas import (
    ConditionExpr,
    DifficultyLevel,
    FormMatchStatus,
    KnowledgeEntityStatus,
    PredicateId,
    ProblemFormAssessmentView,
    QuickTipAssessmentView,
    QuickTipKnowledge,
    RelatedProblemFormKnowledge,
    TipApplicability,
    TipCategory,
    TipExecutionAvailability,
    TipRecommendation,
)


# ============================================================================
# 1. ENUM INTEGRITY TESTS
# ============================================================================

def test_01_knowledge_entity_status_exact_values():
    assert set(e.value for e in KnowledgeEntityStatus) == {
        "PROVISIONAL",
        "VERIFIED",
        "DEPRECATED",
    }


def test_02_difficulty_level_exact_values():
    assert set(e.value for e in DifficultyLevel) == {
        "BASIC",
        "INTERMEDIATE",
        "ADVANCED",
    }


def test_03_tip_category_exact_values():
    assert set(e.value for e in TipCategory) == {
        "COEFFICIENT_RELATION",
        "REDUCED_ARITHMETIC",
        "ROOT_PRODUCT_SUM",
        "SPECIAL_STRUCTURE",
        "TRANSFORMATION",
    }


def test_04_predicate_id_exact_frozen_set():
    expected_predicates = {
        "A_NONZERO",
        "A_EQ_ONE",
        "B_NONZERO",
        "C_NONZERO",
        "B_EVEN_INTEGER",
        "DISCRIMINANT_NONNEGATIVE",
        "DISCRIMINANT_RATIONAL_SQUARE",
        "A_PLUS_B_PLUS_C_ZERO",
        "A_MINUS_B_PLUS_C_ZERO",
        "B_ZERO",
        "C_ZERO",
        "ROOTS_ARE_INTEGERS",
    }
    assert set(e.value for e in PredicateId) == expected_predicates


def test_04b_assessment_enums_exact_values():
    assert set(e.value for e in TipApplicability) == {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
    assert set(e.value for e in TipRecommendation) == {"RECOMMENDED", "NEUTRAL", "DISCOURAGED"}
    assert set(e.value for e in TipExecutionAvailability) == {"AVAILABLE", "UNAVAILABLE"}
    assert set(e.value for e in FormMatchStatus) == {"MATCH", "NO_MATCH", "UNKNOWN"}


# ============================================================================
# 2. CONDITION EXPR TESTS
# ============================================================================

def test_05_condition_expr_valid_all_of():
    cond = ConditionExpr(all_of=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO])
    assert cond.all_of == [PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO]
    assert cond.any_of == []
    assert cond.none_of == []


def test_06_condition_expr_valid_any_of():
    cond = ConditionExpr(any_of=[PredicateId.B_ZERO, PredicateId.C_ZERO])
    assert cond.any_of == [PredicateId.B_ZERO, PredicateId.C_ZERO]


def test_07_condition_expr_valid_none_of():
    cond = ConditionExpr(none_of=[PredicateId.B_EVEN_INTEGER])
    assert cond.none_of == [PredicateId.B_EVEN_INTEGER]


def test_08_empty_condition_expr_rejected():
    with pytest.raises(ValidationError, match="ConditionExpr must not be empty"):
        ConditionExpr(all_of=[], any_of=[], none_of=[])


def test_09_duplicate_predicate_in_clause_rejected():
    with pytest.raises(ValidationError, match="all_of contains duplicate predicates"):
        ConditionExpr(all_of=[PredicateId.A_NONZERO, PredicateId.A_NONZERO])

    with pytest.raises(ValidationError, match="any_of contains duplicate predicates"):
        ConditionExpr(any_of=[PredicateId.B_ZERO, PredicateId.B_ZERO])

    with pytest.raises(ValidationError, match="none_of contains duplicate predicates"):
        ConditionExpr(none_of=[PredicateId.C_ZERO, PredicateId.C_ZERO])


def test_10_all_of_none_of_direct_contradiction_rejected():
    with pytest.raises(ValidationError, match="direct logical contradiction"):
        ConditionExpr(
            all_of=[PredicateId.A_NONZERO, PredicateId.B_EVEN_INTEGER],
            none_of=[PredicateId.B_EVEN_INTEGER],
        )


def test_11_model_frozen_mutation_rejected():
    cond = ConditionExpr(all_of=[PredicateId.A_NONZERO])
    with pytest.raises(ValidationError):
        cond.all_of = [PredicateId.A_EQ_ONE]  # type: ignore


def test_12_extra_field_rejected():
    with pytest.raises(ValidationError):
        ConditionExpr(all_of=[PredicateId.A_NONZERO], extra_clause=[])  # type: ignore


def test_13_strict_enum_behavior():
    with pytest.raises(ValidationError):
        ConditionExpr(all_of=["INVALID_PREDICATE"])  # type: ignore


# ============================================================================
# 3. QUICK TIP KNOWLEDGE TESTS
# ============================================================================

@pytest.fixture
def valid_quick_tip_kwargs():
    return {
        "tip_id": "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
        "title": LocalizedText(vi="Nhẩm nghiệm khi a+b+c=0", en="Root mental calculation when a+b+c=0"),
        "summary": LocalizedText(
            vi="Nếu a+b+c=0 thì phương trình có một nghiệm x=1 và nghiệm kia là x=c/a.",
            en="If a+b+c=0, the equation has one root x=1 and the other root x=c/a.",
        ),
        "category": TipCategory.COEFFICIENT_RELATION,
        "applicability_condition": ConditionExpr(
            all_of=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO]
        ),
        "recognition_guidance": LocalizedText(
            vi="Tính tổng ba hệ số a, b, c. Nếu bằng 0 thì áp dụng ngay.",
            en="Sum the three coefficients a, b, c. If zero, apply immediately.",
        ),
        "explanation": LocalizedText(
            vi="P(1) = a(1)^2 + b(1) + c = a+b+c = 0. Theo Viète x1*x2 = c/a nên x2 = c/a.",
            en="P(1) = a(1)^2 + b(1) + c = a+b+c = 0. By Vieta x1*x2 = c/a, hence x2 = c/a.",
        ),
        "quick_steps": [
            LocalizedText(vi="1. Kiểm tra a + b + c = 0.", en="1. Check if a + b + c = 0."),
            LocalizedText(vi="2. Kết luận x1 = 1 và x2 = c/a.", en="2. Conclude x1 = 1 and x2 = c/a."),
        ],
        "valid_scope": LocalizedText(
            vi="Phương trình bậc hai một ẩn có hệ số a khác 0 và tổng a+b+c=0.",
            en="Univariate quadratic equation with a!=0 and sum a+b+c=0.",
        ),
        "invalid_scope": LocalizedText(
            vi="Không áp dụng khi a=0 hoặc khi a+b+c!=0.",
            en="Not applicable when a=0 or when a+b+c!=0.",
        ),
        "related_method_ids": ["QUAD_VIETE_SPECIAL_SUM"],
        "related_concept_ids": ["CONCEPT_QUADRATIC_EQUATION"],
        "formula_refs": ["FORMULA_QUADRATIC_VIETE_PRODUCT"],
        "theorem_refs": ["THEOREM_VIETE_RELATIONS"],
        "related_problem_form_ids": ["QUAD_FORM_SPECIAL_SUM_ZERO"],
        "curriculum_refs": [
            CurriculumRef(
                framework="GDPT_2018",
                subject="TOAN",
                grade_band="GRADE_9",
                topic="PHUONG_TRINH_BAC_HAI_MOT_AN",
                competency_ref="TOAN_9_VIETE_SPECIAL",
                source_document="Chuong trinh GDPT 2018 Mon Toan",
                source_locator="Muc 5.2.3",
                status=CurriculumMappingStatus.PROVISIONAL_MAPPING,
            )
        ],
        "provenance_refs": ["SRC_SGK_TOAN_9_KNTT"],
        "version": "1.0.0",
    }


def test_14_valid_quick_tip_knowledge(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert tip.tip_id == "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"
    assert tip.status == KnowledgeEntityStatus.PROVISIONAL
    assert tip.version == "1.0.0"


def test_15_quick_tip_default_status_provisional(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert tip.status == KnowledgeEntityStatus.PROVISIONAL


def test_16_invalid_tip_id_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["tip_id"] = "lowercase_tip"
    with pytest.raises(ValidationError, match="Must match pattern"):
        QuickTipKnowledge(**kwargs)

    kwargs["tip_id"] = "TIP WITH SPACE"
    with pytest.raises(ValidationError, match="Must match pattern"):
        QuickTipKnowledge(**kwargs)

    kwargs["tip_id"] = ""
    with pytest.raises(ValidationError, match="Must match pattern"):
        QuickTipKnowledge(**kwargs)


def test_17_empty_provenance_refs_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["provenance_refs"] = []
    with pytest.raises(ValidationError, match="provenance_refs must contain at least one"):
        QuickTipKnowledge(**kwargs)


def test_18_empty_provenance_id_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["provenance_refs"] = [""]
    with pytest.raises(ValidationError, match="must contain non-empty, non-whitespace string IDs"):
        QuickTipKnowledge(**kwargs)


def test_19_duplicate_provenance_ids_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["provenance_refs"] = ["SRC_KNTT_1", "SRC_KNTT_1"]
    with pytest.raises(ValidationError, match="contains duplicate ID"):
        QuickTipKnowledge(**kwargs)


def test_20_empty_quick_steps_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["quick_steps"] = []
    with pytest.raises(ValidationError, match="quick_steps must contain at least one step"):
        QuickTipKnowledge(**kwargs)


# ============================================================================
# 4. RELATED PROBLEM FORM KNOWLEDGE TESTS
# ============================================================================

@pytest.fixture
def valid_problem_form_kwargs():
    return {
        "form_id": "QUAD_FORM_SPECIAL_SUM_ZERO",
        "title": LocalizedText(
            vi="Phương trình bậc hai có a+b+c=0",
            en="Quadratic equation with a+b+c=0",
        ),
        "summary": LocalizedText(
            vi="Dạng phương trình bậc hai một ẩn có tổng các hệ số bằng 0.",
            en="Quadratic equation archetype where the sum of coefficients equals zero.",
        ),
        "canonical_structure_latex": "ax^2 + bx + c = 0 \\quad (a + b + c = 0)",
        "recognition_condition": ConditionExpr(
            all_of=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO]
        ),
        "recognition_guidance": LocalizedText(
            vi="Kiểm tra hệ số a khác 0 và tính tổng a+b+c.",
            en="Verify coefficient a!=0 and calculate sum a+b+c.",
        ),
        "related_method_ids": ["QUAD_VIETE_SPECIAL_SUM", "QUAD_FORMULA_STANDARD"],
        "guaranteed_method_ids": ["QUAD_VIETE_SPECIAL_SUM"],
        "related_tip_ids": ["QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"],
        "guaranteed_tip_ids": ["QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"],
        "prerequisite_concept_ids": ["CONCEPT_QUADRATIC_EQUATION"],
        "formula_refs": ["FORMULA_QUADRATIC_VIETE_PRODUCT"],
        "theorem_refs": ["THEOREM_VIETE_RELATIONS"],
        "worked_example_ids": [],
        "practice_example_ids": [],
        "curriculum_refs": [
            CurriculumRef(
                framework="GDPT_2018",
                subject="TOAN",
                grade_band="GRADE_9",
                topic="PHUONG_TRINH_BAC_HAI_MOT_AN",
                source_document="Chuong trinh GDPT 2018 Mon Toan",
                source_locator="Muc 5.2.3",
                status=CurriculumMappingStatus.PROVISIONAL_MAPPING,
            )
        ],
        "provenance_refs": ["SRC_SGK_TOAN_9_KNTT"],
        "difficulty": DifficultyLevel.BASIC,
        "version": "1.0.0",
    }


def test_21_valid_related_problem_form_knowledge(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert form.form_id == "QUAD_FORM_SPECIAL_SUM_ZERO"
    assert form.status == KnowledgeEntityStatus.PROVISIONAL
    assert form.difficulty == DifficultyLevel.BASIC
    assert form.worked_example_ids == []
    assert form.practice_example_ids == []


def test_22_problem_form_default_status_provisional(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert form.status == KnowledgeEntityStatus.PROVISIONAL


def test_23_invalid_form_id_rejected(valid_problem_form_kwargs):
    kwargs = valid_problem_form_kwargs.copy()
    kwargs["form_id"] = "invalid-form-id"
    with pytest.raises(ValidationError, match="Must match pattern"):
        RelatedProblemFormKnowledge(**kwargs)


def test_24_relation_list_duplicate_rejected(valid_problem_form_kwargs):
    kwargs = valid_problem_form_kwargs.copy()
    kwargs["related_method_ids"] = ["QUAD_FORMULA_STANDARD", "QUAD_FORMULA_STANDARD"]
    with pytest.raises(ValidationError, match="contains duplicate ID"):
        RelatedProblemFormKnowledge(**kwargs)


def test_25_relation_list_empty_id_rejected(valid_problem_form_kwargs):
    kwargs = valid_problem_form_kwargs.copy()
    kwargs["related_method_ids"] = [" "]
    with pytest.raises(ValidationError, match="must contain non-empty, non-whitespace string IDs"):
        RelatedProblemFormKnowledge(**kwargs)


def test_26_worked_example_ids_supported_empty(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert form.worked_example_ids == []
    assert form.practice_example_ids == []


# ============================================================================
# 5. RUNTIME ASSESSMENT VIEW TESTS
# ============================================================================

def test_27_valid_quick_tip_assessment_view():
    view = QuickTipAssessmentView(
        tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
        mathematical_applicability=TipApplicability.APPLICABLE,
        pedagogical_recommendation=TipRecommendation.RECOMMENDED,
        execution_availability=TipExecutionAvailability.AVAILABLE,
        matched_predicates=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO],
        failed_predicates=[],
        unknown_predicates=[],
        reason_codes=["REASON_COEFFICIENTS_SUM_ZERO"],
    )
    assert view.mathematical_applicability == TipApplicability.APPLICABLE
    assert view.pedagogical_recommendation == TipRecommendation.RECOMMENDED


def test_28_overlapping_matched_failed_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence: Predicates present in both matched and failed"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.NOT_APPLICABLE,
            pedagogical_recommendation=TipRecommendation.DISCOURAGED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=[PredicateId.A_NONZERO],
            failed_predicates=[PredicateId.A_NONZERO],
            unknown_predicates=[],
        )


def test_29_overlapping_matched_unknown_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence: Predicates present in both matched and unknown"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.UNKNOWN,
            pedagogical_recommendation=TipRecommendation.NEUTRAL,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=[PredicateId.A_NONZERO],
            failed_predicates=[],
            unknown_predicates=[PredicateId.A_NONZERO],
        )


def test_30_duplicate_predicate_evidence_rejected():
    with pytest.raises(ValidationError, match="matched_predicates contains duplicate predicates"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=[PredicateId.A_NONZERO, PredicateId.A_NONZERO],
            failed_predicates=[],
            unknown_predicates=[],
        )


def test_31_valid_problem_form_assessment_view():
    view = ProblemFormAssessmentView(
        form_id="QUAD_FORM_SPECIAL_SUM_ZERO",
        mathematical_match=FormMatchStatus.MATCH,
        matched_predicates=[PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO],
        failed_predicates=[],
        unknown_predicates=[],
        reason_codes=["REASON_FORM_SPECIAL_SUM_MATCH"],
    )
    assert view.mathematical_match == FormMatchStatus.MATCH


def test_32_contradictory_form_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence: Predicates present in both failed and unknown"):
        ProblemFormAssessmentView(
            form_id="QUAD_FORM_SPECIAL_SUM_ZERO",
            mathematical_match=FormMatchStatus.NO_MATCH,
            matched_predicates=[],
            failed_predicates=[PredicateId.A_PLUS_B_PLUS_C_ZERO],
            unknown_predicates=[PredicateId.A_PLUS_B_PLUS_C_ZERO],
        )


def test_33_duplicate_reason_code_rejected():
    with pytest.raises(ValidationError, match="contains duplicate ID"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=[PredicateId.A_NONZERO],
            reason_codes=["CODE_A", "CODE_A"],
        )


def test_34_empty_reason_code_rejected():
    with pytest.raises(ValidationError, match="must contain non-empty, non-whitespace string IDs"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=[PredicateId.A_NONZERO],
            reason_codes=[""],
        )


# ============================================================================
# 6. SEMVER, REUSE & SERIALIZATION TESTS
# ============================================================================

def test_35_valid_version_semver(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["version"] = "2.1.4"
    tip = QuickTipKnowledge(**kwargs)
    assert tip.version == "2.1.4"


def test_36_malformed_version_rejected(valid_quick_tip_kwargs):
    kwargs = valid_quick_tip_kwargs.copy()
    kwargs["version"] = "v1.0"
    with pytest.raises(ValidationError, match="Must follow 'MAJOR.MINOR.PATCH' format"):
        QuickTipKnowledge(**kwargs)


def test_37_localized_text_reuse_works(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert isinstance(tip.title, LocalizedText)
    assert tip.title.vi == "Nhẩm nghiệm khi a+b+c=0"
    assert tip.title.en == "Root mental calculation when a+b+c=0"


def test_38_curriculum_ref_reuse_works(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert len(tip.curriculum_refs) == 1
    assert isinstance(tip.curriculum_refs[0], CurriculumRef)
    assert tip.curriculum_refs[0].source_locator == "Muc 5.2.3"


def test_39_model_dump_validate_deterministic_roundtrip(valid_quick_tip_kwargs):
    tip1 = QuickTipKnowledge(**valid_quick_tip_kwargs)
    dumped = tip1.model_dump()
    tip2 = QuickTipKnowledge.model_validate(dumped)
    assert tip1 == tip2


def test_40_json_serialization_deterministic_value_content(valid_problem_form_kwargs):
    form1 = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    json_str = form1.model_dump_json()
    form2 = RelatedProblemFormKnowledge.model_validate_json(json_str)
    assert form1 == form2
