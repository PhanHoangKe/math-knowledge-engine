"""Unit tests for MKE MVP V1 Milestone K1 Schema Contracts.

Verifies:
- Exact frozen enums (KnowledgeEntityStatus, DifficultyLevel, TipCategory, PredicateId, etc.)
- Strict Pydantic model configuration (extra="forbid", frozen=True, strict=True)
- Deep immutability of all collection fields via immutable tuples
- Invariant bypass prevention (no clear/append/mutation on condition/relation/assessment collections)
- Disjoint predicate evidence partition on assessment views
- Closed Condition DSL integrity (non-vacuous, duplicate-free, non-contradictory)
- Regex validation for canonical IDs and SemVer
- Deterministic serialization and deserialization (Python tuples & JSON arrays)
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from mke_product.knowledge.k1_schemas import (
    CANONICAL_ID_REGEX,
    SEMVER_REGEX,
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
from mke_product.knowledge.schemas import CurriculumMappingStatus, CurriculumRef, LocalizedText


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_quick_tip_kwargs() -> dict:
    return {
        "tip_id": "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
        "title": LocalizedText(vi="Nhẩm nghiệm a + b + c = 0", en="Root inspection a + b + c = 0"),
        "summary": LocalizedText(vi="Khi a + b + c = 0 thì x1 = 1, x2 = c/a", en="When a + b + c = 0, x1 = 1, x2 = c/a"),
        "category": TipCategory.COEFFICIENT_RELATION,
        "applicability_condition": ConditionExpr(
            all_of=(PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO)
        ),
        "recognition_guidance": LocalizedText(
            vi="Kiểm tra tổng ba hệ số a, b, c",
            en="Check sum of three coefficients a, b, c",
        ),
        "explanation": LocalizedText(
            vi="Thay x = 1 vào f(x) = a(1)^2 + b(1) + c = a + b + c = 0. Do đó x = 1 là một nghiệm.",
            en="Substitute x = 1 into f(x) = a(1)^2 + b(1) + c = a + b + c = 0. Therefore x = 1 is a root.",
        ),
        "quick_steps": (
            LocalizedText(vi="1. Tính S = a + b + c", en="1. Compute S = a + b + c"),
            LocalizedText(vi="2. Kết luận x1 = 1, x2 = c/a", en="2. Conclude x1 = 1, x2 = c/a"),
        ),
        "valid_scope": LocalizedText(
            vi="Áp dụng cho mọi phương trình bậc hai có a != 0 và a + b + c = 0",
            en="Applies to any quadratic equation where a != 0 and a + b + c = 0",
        ),
        "invalid_scope": LocalizedText(
            vi="Không áp dụng khi a = 0 hoặc khi a + b + c != 0",
            en="Invalid when a = 0 or when a + b + c != 0",
        ),
        "related_method_ids": ("QUAD_VIETE_SPECIAL_SUM",),
        "related_concept_ids": ("concept_vietes_formulas",),
        "formula_refs": ("FORMULA_VIETE_SUM", "FORMULA_VIETE_PRODUCT"),
        "theorem_refs": ("THEOREM_VIETE_RELATIONS",),
        "related_problem_form_ids": ("QUAD_FORM_SPECIAL_SUM_ZERO",),
        "curriculum_refs": (
            CurriculumRef(
                framework="VN_GDPT_2018",
                subject="MATH",
                grade_band="G9",
                topic="QUADRATIC_EQUATIONS",
                competency_ref="COMP_ROOT_INSPECTION",
                source_document="SGK Toan 9 Tap 2",
                source_locator="Muc 5.2.3",
                status=CurriculumMappingStatus.VERIFIED_MAPPING,
            ),
        ),
        "provenance_refs": ("PROV_SGK_TOAN_9_TAP_2",),
        "status": KnowledgeEntityStatus.PROVISIONAL,
        "version": "1.0.0",
    }


@pytest.fixture
def valid_problem_form_kwargs() -> dict:
    return {
        "form_id": "QUAD_FORM_SPECIAL_SUM_ZERO",
        "title": LocalizedText(vi="Phương trình có a + b + c = 0", en="Equation with a + b + c = 0"),
        "summary": LocalizedText(
            vi="Dạng phương trình bậc hai có tổng các hệ số bằng 0",
            en="Quadratic equation archetype with coefficient sum equal to zero",
        ),
        "canonical_structure_latex": "ax^2 + bx + c = 0 \\quad (a + b + c = 0)",
        "recognition_condition": ConditionExpr(
            all_of=(PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO)
        ),
        "recognition_guidance": LocalizedText(
            vi="Nhận diện khi a + b + c = 0",
            en="Identify when a + b + c = 0",
        ),
        "related_method_ids": ("QUAD_VIETE_SPECIAL_SUM", "QUAD_STANDARD_FORMULA"),
        "guaranteed_method_ids": ("QUAD_VIETE_SPECIAL_SUM",),
        "related_tip_ids": ("QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",),
        "guaranteed_tip_ids": ("QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",),
        "prerequisite_concept_ids": ("concept_quadratic_equation",),
        "formula_refs": ("FORMULA_VIETE_SUM",),
        "theorem_refs": ("THEOREM_VIETE_RELATIONS",),
        "worked_example_ids": (),
        "practice_example_ids": (),
        "curriculum_refs": (
            CurriculumRef(
                framework="VN_GDPT_2018",
                subject="MATH",
                grade_band="G9",
                topic="QUADRATIC_EQUATIONS",
                competency_ref="COMP_RECOGNIZE_SPECIAL_FORM",
                source_document="SGK Toan 9 Tap 2",
                source_locator="Bai 6 Dạng 1",
                status=CurriculumMappingStatus.VERIFIED_MAPPING,
            ),
        ),
        "provenance_refs": ("PROV_SGK_TOAN_9_TAP_2",),
        "difficulty": DifficultyLevel.BASIC,
        "status": KnowledgeEntityStatus.PROVISIONAL,
        "version": "1.0.0",
    }


# ============================================================================
# 1. ENUM & CONSTANT TESTS
# ============================================================================

def test_01_knowledge_entity_status_exact_values():
    assert [e.value for e in KnowledgeEntityStatus] == ["PROVISIONAL", "VERIFIED", "DEPRECATED"]


def test_02_difficulty_level_exact_values():
    assert [e.value for e in DifficultyLevel] == ["BASIC", "INTERMEDIATE", "ADVANCED"]


def test_03_tip_category_exact_values():
    assert [e.value for e in TipCategory] == [
        "COEFFICIENT_RELATION",
        "REDUCED_ARITHMETIC",
        "ROOT_PRODUCT_SUM",
        "SPECIAL_STRUCTURE",
        "TRANSFORMATION",
    ]


def test_04_predicate_id_exact_frozen_set():
    expected = {
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
    actual = {p.value for p in PredicateId}
    assert actual == expected
    assert len(PredicateId) == 12


def test_04b_assessment_enums_exact_values():
    assert [e.value for e in TipApplicability] == ["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]
    assert [e.value for e in TipRecommendation] == ["RECOMMENDED", "NEUTRAL", "DISCOURAGED"]
    assert [e.value for e in TipExecutionAvailability] == ["AVAILABLE", "UNAVAILABLE"]
    assert [e.value for e in FormMatchStatus] == ["MATCH", "NO_MATCH", "UNKNOWN"]


# ============================================================================
# 2. CONDITIONEXPR & CLOSED CONDITION DSL TESTS
# ============================================================================

def test_05_condition_expr_valid_all_of():
    cond = ConditionExpr(all_of=(PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO))
    assert isinstance(cond.all_of, tuple)
    assert len(cond.all_of) == 2
    assert cond.any_of == ()
    assert cond.none_of == ()


def test_06_condition_expr_valid_any_of():
    cond = ConditionExpr(any_of=(PredicateId.B_ZERO, PredicateId.C_ZERO))
    assert isinstance(cond.any_of, tuple)
    assert len(cond.any_of) == 2


def test_07_condition_expr_valid_none_of():
    cond = ConditionExpr(none_of=(PredicateId.DISCRIMINANT_NONNEGATIVE,))
    assert isinstance(cond.none_of, tuple)
    assert len(cond.none_of) == 1


def test_08_empty_condition_expr_rejected():
    with pytest.raises(ValidationError, match="ConditionExpr must not be empty"):
        ConditionExpr()


def test_09_duplicate_predicate_in_clause_rejected():
    with pytest.raises(ValidationError, match="all_of contains duplicate predicates"):
        ConditionExpr(all_of=(PredicateId.A_NONZERO, PredicateId.A_NONZERO))


def test_10_all_of_none_of_direct_contradiction_rejected():
    with pytest.raises(ValidationError, match="direct logical contradiction"):
        ConditionExpr(
            all_of=(PredicateId.A_NONZERO,),
            none_of=(PredicateId.A_NONZERO,),
        )


# ============================================================================
# 3. DEEP IMMUTABILITY & INVARIANT BYPASS REGRESSION TESTS
# ============================================================================

def test_11_condition_expr_deep_immutability_and_mutation_rejection():
    cond = ConditionExpr(all_of=(PredicateId.A_NONZERO,))
    assert isinstance(cond.all_of, tuple)

    # 1. Tuples do not have clear()
    with pytest.raises(AttributeError):
        cond.all_of.clear()  # type: ignore

    # 2. Tuples do not have append()
    with pytest.raises(AttributeError):
        cond.all_of.append(PredicateId.B_ZERO)  # type: ignore

    # 3. Tuples do not support item assignment
    with pytest.raises(TypeError):
        cond.all_of[0] = PredicateId.B_ZERO  # type: ignore

    # 4. Model field reassignment rejected by frozen=True
    with pytest.raises(ValidationError):
        cond.all_of = ()  # type: ignore


def test_12_extra_field_rejected():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ConditionExpr(all_of=(PredicateId.A_NONZERO,), unauthorized_field="bad")  # type: ignore


def test_13_strict_enum_behavior():
    # Strict mode requires exact PredicateId enum or string parsing through JSON
    with pytest.raises(ValidationError):
        ConditionExpr(all_of=["NON_EXISTENT_PREDICATE"])  # type: ignore


# ============================================================================
# 4. QUICK TIP KNOWLEDGE MODEL TESTS
# ============================================================================

def test_14_valid_quick_tip_knowledge(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert tip.tip_id == "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"
    assert tip.status == KnowledgeEntityStatus.PROVISIONAL
    assert isinstance(tip.quick_steps, tuple)
    assert isinstance(tip.provenance_refs, tuple)
    assert isinstance(tip.related_method_ids, tuple)
    assert isinstance(tip.curriculum_refs, tuple)


def test_15_quick_tip_default_status_provisional(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    del kwargs["status"]
    tip = QuickTipKnowledge(**kwargs)
    assert tip.status == KnowledgeEntityStatus.PROVISIONAL


def test_16_invalid_tip_id_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["tip_id"] = "lower_case_tip"
    with pytest.raises(ValidationError, match="Must match pattern"):
        QuickTipKnowledge(**kwargs)


def test_17_empty_provenance_refs_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["provenance_refs"] = ()
    with pytest.raises(ValidationError, match="provenance_refs must contain at least one"):
        QuickTipKnowledge(**kwargs)


def test_18_empty_provenance_id_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["provenance_refs"] = ("   ",)
    with pytest.raises(ValidationError, match="provenance_refs must contain non-empty"):
        QuickTipKnowledge(**kwargs)


def test_19_duplicate_provenance_ids_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["provenance_refs"] = ("PROV_1", "PROV_1")
    with pytest.raises(ValidationError, match="provenance_refs contains duplicate ID"):
        QuickTipKnowledge(**kwargs)


def test_20_empty_quick_steps_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["quick_steps"] = ()
    with pytest.raises(ValidationError, match="quick_steps must contain at least one"):
        QuickTipKnowledge(**kwargs)


def test_20b_quick_tip_collection_deep_immutability(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert isinstance(tip.quick_steps, tuple)
    assert isinstance(tip.provenance_refs, tuple)
    assert isinstance(tip.related_method_ids, tuple)
    assert isinstance(tip.formula_refs, tuple)
    assert isinstance(tip.theorem_refs, tuple)
    assert isinstance(tip.curriculum_refs, tuple)

    with pytest.raises(AttributeError):
        tip.quick_steps.clear()  # type: ignore

    with pytest.raises(AttributeError):
        tip.provenance_refs.append("EXTRA_PROV")  # type: ignore

    with pytest.raises(AttributeError):
        tip.related_method_ids.clear()  # type: ignore


# ============================================================================
# 5. RELATED PROBLEM FORM KNOWLEDGE MODEL TESTS
# ============================================================================

def test_21_valid_related_problem_form_knowledge(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert form.form_id == "QUAD_FORM_SPECIAL_SUM_ZERO"
    assert form.difficulty == DifficultyLevel.BASIC
    assert form.status == KnowledgeEntityStatus.PROVISIONAL
    assert isinstance(form.related_method_ids, tuple)
    assert isinstance(form.guaranteed_method_ids, tuple)
    assert isinstance(form.worked_example_ids, tuple)


def test_22_problem_form_default_status_provisional(valid_problem_form_kwargs):
    kwargs = dict(valid_problem_form_kwargs)
    del kwargs["status"]
    form = RelatedProblemFormKnowledge(**kwargs)
    assert form.status == KnowledgeEntityStatus.PROVISIONAL


def test_23_invalid_form_id_rejected(valid_problem_form_kwargs):
    kwargs = dict(valid_problem_form_kwargs)
    kwargs["form_id"] = "123_INVALID_START"
    with pytest.raises(ValidationError, match="Must match pattern"):
        RelatedProblemFormKnowledge(**kwargs)


def test_24_relation_list_duplicate_rejected(valid_problem_form_kwargs):
    kwargs = dict(valid_problem_form_kwargs)
    kwargs["related_method_ids"] = ("M1", "M1")
    with pytest.raises(ValidationError, match="related_method_ids contains duplicate ID"):
        RelatedProblemFormKnowledge(**kwargs)


def test_25_relation_list_empty_id_rejected(valid_problem_form_kwargs):
    kwargs = dict(valid_problem_form_kwargs)
    kwargs["guaranteed_method_ids"] = ("",)
    with pytest.raises(ValidationError, match="guaranteed_method_ids must contain non-empty"):
        RelatedProblemFormKnowledge(**kwargs)


def test_26_worked_example_ids_supported_empty(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert form.worked_example_ids == ()
    assert form.practice_example_ids == ()


def test_26b_problem_form_collection_deep_immutability(valid_problem_form_kwargs):
    form = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    assert isinstance(form.related_method_ids, tuple)
    assert isinstance(form.guaranteed_method_ids, tuple)
    assert isinstance(form.related_tip_ids, tuple)
    assert isinstance(form.guaranteed_tip_ids, tuple)
    assert isinstance(form.prerequisite_concept_ids, tuple)
    assert isinstance(form.formula_refs, tuple)
    assert isinstance(form.theorem_refs, tuple)
    assert isinstance(form.worked_example_ids, tuple)
    assert isinstance(form.practice_example_ids, tuple)
    assert isinstance(form.curriculum_refs, tuple)
    assert isinstance(form.provenance_refs, tuple)

    with pytest.raises(AttributeError):
        form.related_method_ids.clear()  # type: ignore

    with pytest.raises(AttributeError):
        form.provenance_refs.append("PROV_NEW")  # type: ignore


# ============================================================================
# 6. DYNAMIC RUNTIME ASSESSMENT CONTRACT DTO TESTS
# ============================================================================

def test_27_valid_quick_tip_assessment_view():
    view = QuickTipAssessmentView(
        tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
        mathematical_applicability=TipApplicability.APPLICABLE,
        pedagogical_recommendation=TipRecommendation.RECOMMENDED,
        execution_availability=TipExecutionAvailability.AVAILABLE,
        matched_predicates=(PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO),
        failed_predicates=(PredicateId.B_EVEN_INTEGER,),
        unknown_predicates=(PredicateId.ROOTS_ARE_INTEGERS,),
        reason_codes=("RC_COEFF_SUM_ZERO_MATCHED",),
    )
    assert view.tip_id == "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"
    assert view.mathematical_applicability == TipApplicability.APPLICABLE
    assert isinstance(view.matched_predicates, tuple)
    assert isinstance(view.failed_predicates, tuple)
    assert isinstance(view.unknown_predicates, tuple)
    assert isinstance(view.reason_codes, tuple)


def test_28_overlapping_matched_failed_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=(PredicateId.A_NONZERO,),
            failed_predicates=(PredicateId.A_NONZERO,),
        )


def test_29_overlapping_matched_unknown_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=(PredicateId.A_NONZERO,),
            unknown_predicates=(PredicateId.A_NONZERO,),
        )


def test_30_duplicate_predicate_evidence_rejected():
    with pytest.raises(ValidationError, match="matched_predicates contains duplicate predicates"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            matched_predicates=(PredicateId.A_NONZERO, PredicateId.A_NONZERO),
        )


def test_31_valid_problem_form_assessment_view():
    view = ProblemFormAssessmentView(
        form_id="QUAD_FORM_SPECIAL_SUM_ZERO",
        mathematical_match=FormMatchStatus.MATCH,
        matched_predicates=(PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO),
        failed_predicates=(PredicateId.B_ZERO,),
        unknown_predicates=(),
        reason_codes=("RC_FORM_MATCH_EXACT",),
    )
    assert view.form_id == "QUAD_FORM_SPECIAL_SUM_ZERO"
    assert view.mathematical_match == FormMatchStatus.MATCH
    assert isinstance(view.matched_predicates, tuple)


def test_32_contradictory_form_evidence_rejected():
    with pytest.raises(ValidationError, match="Contradictory evidence"):
        ProblemFormAssessmentView(
            form_id="QUAD_FORM_SPECIAL_SUM_ZERO",
            mathematical_match=FormMatchStatus.MATCH,
            matched_predicates=(PredicateId.B_ZERO,),
            failed_predicates=(PredicateId.B_ZERO,),
        )


def test_32b_assessment_views_deep_immutability_and_partition_preservation():
    view = QuickTipAssessmentView(
        tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
        mathematical_applicability=TipApplicability.APPLICABLE,
        pedagogical_recommendation=TipRecommendation.RECOMMENDED,
        execution_availability=TipExecutionAvailability.AVAILABLE,
        matched_predicates=(PredicateId.A_NONZERO,),
        failed_predicates=(PredicateId.B_ZERO,),
        unknown_predicates=(),
    )
    # Proof: Cannot mutate matched_predicates in place to introduce overlap
    with pytest.raises(AttributeError):
        view.matched_predicates.append(PredicateId.B_ZERO)  # type: ignore

    with pytest.raises(AttributeError):
        view.matched_predicates.clear()  # type: ignore


def test_33_duplicate_reason_code_rejected():
    with pytest.raises(ValidationError, match="reason_codes contains duplicate ID"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            reason_codes=("RC_1", "RC_1"),
        )


def test_34_empty_reason_code_rejected():
    with pytest.raises(ValidationError, match="reason_codes must contain non-empty"):
        QuickTipAssessmentView(
            tip_id="QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
            mathematical_applicability=TipApplicability.APPLICABLE,
            pedagogical_recommendation=TipRecommendation.RECOMMENDED,
            execution_availability=TipExecutionAvailability.AVAILABLE,
            reason_codes=("",),
        )


# ============================================================================
# 7. VERSIONING & EXISTING S3 CONTRACT REUSE
# ============================================================================

def test_35_valid_version_semver(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert tip.version == "1.0.0"


def test_36_malformed_version_rejected(valid_quick_tip_kwargs):
    kwargs = dict(valid_quick_tip_kwargs)
    kwargs["version"] = "v1.0"
    with pytest.raises(ValidationError, match="Must follow 'MAJOR.MINOR.PATCH'"):
        QuickTipKnowledge(**kwargs)


def test_37_localized_text_reuse_works(valid_quick_tip_kwargs):
    tip = QuickTipKnowledge(**valid_quick_tip_kwargs)
    assert isinstance(tip.title, LocalizedText)
    assert tip.title.vi == "Nhẩm nghiệm a + b + c = 0"
    assert tip.title.en == "Root inspection a + b + c = 0"


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
    assert isinstance(tip2.quick_steps, tuple)


def test_40_json_serialization_deterministic_value_content(valid_problem_form_kwargs):
    form1 = RelatedProblemFormKnowledge(**valid_problem_form_kwargs)
    json_str = form1.model_dump_json()
    form2 = RelatedProblemFormKnowledge.model_validate_json(json_str)
    assert form1 == form2
    assert isinstance(form2.related_method_ids, tuple)


def test_41_json_array_deserializes_to_immutable_tuples():
    json_payload = json.dumps({
        "all_of": ["A_NONZERO", "A_PLUS_B_PLUS_C_ZERO"],
        "any_of": [],
        "none_of": ["B_ZERO"]
    })
    cond = ConditionExpr.model_validate_json(json_payload)
    assert isinstance(cond.all_of, tuple)
    assert isinstance(cond.any_of, tuple)
    assert isinstance(cond.none_of, tuple)
    assert cond.all_of == (PredicateId.A_NONZERO, PredicateId.A_PLUS_B_PLUS_C_ZERO)
    assert cond.none_of == (PredicateId.B_ZERO,)
