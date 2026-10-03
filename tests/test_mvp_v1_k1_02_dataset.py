"""MKE MVP V1 — Milestone K1-02 Curated Knowledge Dataset Test Suite.

Verifies:
1. Exact cardinalities (3 tips, 6 problem forms) and exact canonical IDs.
2. Canonical lexicographic ordering in raw JSON dataset files.
3. Bilingual completeness and non-empty pedagogical text across all fields.
4. Exact mathematical conditions using the closed PredicateId language.
5. Referential integrity to existing S3 entities (provenances, methods, concepts, formulas, theorems).
6. Relation subset invariants (guaranteed_method_ids ⊆ related_method_ids, guaranteed_tip_ids ⊆ related_tip_ids).
7. Empty example reference policy (worked_example_ids and practice_example_ids must be empty).
8. Provenance verification gate (VERIFIED entities only reference VERIFIED sources).
9. Fail-closed rejection of malformed, duplicate, or dangling references.
10. Content hashing invariance (S3 hash byte-frozen, K1 combined hash deterministic).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from mke_product.knowledge.k1_loader import (
    compute_k1_dataset_content_hash,
    load_k1_knowledge_dataset,
    load_problem_forms,
    load_quick_tips,
    validate_k1_knowledge_dataset,
)
from mke_product.knowledge.k1_schemas import (
    DifficultyLevel,
    KnowledgeEntityStatus,
    PredicateId,
    QuickTipKnowledge,
    RelatedProblemFormKnowledge,
    TipCategory,
)
from mke_product.knowledge.loader import (
    DEFAULT_DATA_DIR,
    compute_dataset_content_hash,
    load_knowledge_dataset,
)

EXPECTED_S3_HASH = "e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66"

EXPECTED_TIP_IDS = [
    "QUAD_TIP_REDUCED_FORMULA_EVEN_B",
    "QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO",
    "QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",
]

EXPECTED_FORM_IDS = [
    "QUAD_FORM_COMPLETE_QUADRATIC",
    "QUAD_FORM_GENERAL_QUADRATIC",
    "QUAD_FORM_INCOMPLETE_B_ZERO",
    "QUAD_FORM_INCOMPLETE_C_ZERO",
    "QUAD_FORM_SPECIAL_DIF_ZERO",
    "QUAD_FORM_SPECIAL_SUM_ZERO",
]


class TestK102DatasetCardinalitiesAndOrdering:
    """Verifies exact counts, canonical IDs, and lexicographical JSON order."""

    def test_exact_tip_count_and_canonical_ids(self):
        tips = load_quick_tips()
        assert len(tips) == 3, f"Expected exactly 3 quick tips, found {len(tips)}"
        actual_ids = [t.tip_id for t in tips]
        assert actual_ids == EXPECTED_TIP_IDS

    def test_exact_problem_form_count_and_canonical_ids(self):
        forms = load_problem_forms()
        assert len(forms) == 6, f"Expected exactly 6 problem forms, found {len(forms)}"
        actual_ids = [f.form_id for f in forms]
        assert actual_ids == EXPECTED_FORM_IDS

    def test_raw_tips_json_lexicographical_ordering(self):
        tips_file = DEFAULT_DATA_DIR / "tips.json"
        with open(tips_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        raw_ids = [item["tip_id"] for item in raw_data]
        assert raw_ids == sorted(raw_ids), f"tips.json is not sorted lexicographically: {raw_ids}"

    def test_raw_problem_forms_json_lexicographical_ordering(self):
        forms_file = DEFAULT_DATA_DIR / "problem_forms.json"
        with open(forms_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        raw_ids = [item["form_id"] for item in raw_data]
        assert raw_ids == sorted(raw_ids), f"problem_forms.json is not sorted lexicographically: {raw_ids}"


class TestK102DatasetMathematicalConditions:
    """Verifies exact closed boolean predicate conditions for all tips and problem forms."""

    def test_quick_tip_mathematical_conditions(self):
        tips = {t.tip_id: t for t in load_quick_tips()}

        # Reduced formula tip
        t_red = tips["QUAD_TIP_REDUCED_FORMULA_EVEN_B"]
        assert t_red.category == TipCategory.REDUCED_ARITHMETIC
        assert t_red.applicability_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.B_EVEN_INTEGER,
        )
        assert len(t_red.applicability_condition.any_of) == 0
        assert len(t_red.applicability_condition.none_of) == 0

        # Special dif tip
        t_dif = tips["QUAD_TIP_SPECIAL_A_MINUS_B_PLUS_C_ZERO"]
        assert t_dif.category == TipCategory.COEFFICIENT_RELATION
        assert t_dif.applicability_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.A_MINUS_B_PLUS_C_ZERO,
        )
        assert len(t_dif.applicability_condition.any_of) == 0
        assert len(t_dif.applicability_condition.none_of) == 0

        # Special sum tip
        t_sum = tips["QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO"]
        assert t_sum.category == TipCategory.COEFFICIENT_RELATION
        assert t_sum.applicability_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.A_PLUS_B_PLUS_C_ZERO,
        )
        assert len(t_sum.applicability_condition.any_of) == 0
        assert len(t_sum.applicability_condition.none_of) == 0

    def test_problem_form_recognition_conditions(self):
        forms = {f.form_id: f for f in load_problem_forms()}

        # General quadratic: a != 0
        assert forms["QUAD_FORM_GENERAL_QUADRATIC"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
        )

        # Complete quadratic: a != 0, b != 0, c != 0
        assert forms["QUAD_FORM_COMPLETE_QUADRATIC"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.B_NONZERO,
            PredicateId.C_NONZERO,
        )

        # Incomplete B=0: a != 0, b = 0
        assert forms["QUAD_FORM_INCOMPLETE_B_ZERO"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.B_ZERO,
        )

        # Incomplete C=0: a != 0, c = 0
        assert forms["QUAD_FORM_INCOMPLETE_C_ZERO"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.C_ZERO,
        )

        # Special Difference: a != 0, a - b + c = 0
        assert forms["QUAD_FORM_SPECIAL_DIF_ZERO"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.A_MINUS_B_PLUS_C_ZERO,
        )

        # Special Sum: a != 0, a + b + c = 0
        assert forms["QUAD_FORM_SPECIAL_SUM_ZERO"].recognition_condition.all_of == (
            PredicateId.A_NONZERO,
            PredicateId.A_PLUS_B_PLUS_C_ZERO,
        )


class TestK102BilingualAndPedagogicalCompleteness:
    """Verifies that all textual explanations are bilingual and non-empty."""

    def test_tips_bilingual_fields(self):
        tips = load_quick_tips()
        for tip in tips:
            assert tip.title.en.strip() and tip.title.vi.strip()
            assert tip.summary.en.strip() and tip.summary.vi.strip()
            assert tip.recognition_guidance.en.strip() and tip.recognition_guidance.vi.strip()
            assert tip.explanation.en.strip() and tip.explanation.vi.strip()
            assert tip.valid_scope.en.strip() and tip.valid_scope.vi.strip()
            assert tip.invalid_scope.en.strip() and tip.invalid_scope.vi.strip()
            assert len(tip.quick_steps) >= 3
            for step in tip.quick_steps:
                assert step.en.strip() and step.vi.strip()

    def test_problem_forms_bilingual_fields(self):
        forms = load_problem_forms()
        for form in forms:
            assert form.title.en.strip() and form.title.vi.strip()
            assert form.summary.en.strip() and form.summary.vi.strip()
            assert form.canonical_structure_latex.strip()
            assert form.recognition_guidance.en.strip() and form.recognition_guidance.vi.strip()


class TestK102ReferentialIntegrityAndRelationInvariants:
    """Verifies relational invariants, foreign keys, and empty example lists."""

    def test_dataset_loads_and_validates_cleanly(self):
        dataset = load_k1_knowledge_dataset()
        assert "tips" in dataset
        assert "problem_forms" in dataset
        assert len(dataset["tips"]) == 3
        assert len(dataset["problem_forms"]) == 6

    def test_guaranteed_relations_subset_invariants(self):
        forms = load_problem_forms()
        for form in forms:
            # guaranteed_method_ids ⊆ related_method_ids
            assert set(form.guaranteed_method_ids).issubset(set(form.related_method_ids)), (
                f"Form '{form.form_id}' violates guaranteed_method_ids ⊆ related_method_ids"
            )
            # guaranteed_tip_ids ⊆ related_tip_ids
            assert set(form.guaranteed_tip_ids).issubset(set(form.related_tip_ids)), (
                f"Form '{form.form_id}' violates guaranteed_tip_ids ⊆ related_tip_ids"
            )

    def test_worked_and_practice_examples_are_strictly_empty(self):
        forms = load_problem_forms()
        for form in forms:
            assert len(form.worked_example_ids) == 0, f"Form '{form.form_id}' worked_example_ids must be empty"
            assert len(form.practice_example_ids) == 0, f"Form '{form.form_id}' practice_example_ids must be empty"

    def test_all_referenced_entities_exist_in_s3_and_k1(self):
        dataset = load_k1_knowledge_dataset()
        prov_ids = {p.source_id for p in dataset["provenances"]}
        method_ids = {m.method_id for m in dataset["methods"]}
        concept_ids = {c.concept_id for c in dataset["concepts"]}
        formula_ids = {f.formula_id for f in dataset["formulas"]}
        theorem_ids = {t.theorem_id for t in dataset["theorems"]}
        form_ids = {f.form_id for f in dataset["problem_forms"]}
        tip_ids = {t.tip_id for t in dataset["tips"]}

        # Check tips foreign keys
        for tip in dataset["tips"]:
            assert set(tip.provenance_refs).issubset(prov_ids)
            assert set(tip.related_method_ids).issubset(method_ids)
            assert set(tip.related_concept_ids).issubset(concept_ids)
            assert set(tip.formula_refs).issubset(formula_ids)
            assert set(tip.theorem_refs).issubset(theorem_ids)
            assert set(tip.related_problem_form_ids).issubset(form_ids)

        # Check problem forms foreign keys
        for form in dataset["problem_forms"]:
            assert set(form.provenance_refs).issubset(prov_ids)
            assert set(form.related_method_ids).issubset(method_ids)
            assert set(form.guaranteed_method_ids).issubset(method_ids)
            assert set(form.related_tip_ids).issubset(tip_ids)
            assert set(form.guaranteed_tip_ids).issubset(tip_ids)
            assert set(form.prerequisite_concept_ids).issubset(concept_ids)
            assert set(form.formula_refs).issubset(formula_ids)
            assert set(form.theorem_refs).issubset(theorem_ids)

    def test_provenance_verification_status_gate(self):
        dataset = load_k1_knowledge_dataset()
        prov_map = {p.source_id: p for p in dataset["provenances"]}

        for tip in dataset["tips"]:
            if tip.status == KnowledgeEntityStatus.VERIFIED:
                for ref in tip.provenance_refs:
                    assert prov_map[ref].verification_status == "VERIFIED"

        for form in dataset["problem_forms"]:
            if form.status == KnowledgeEntityStatus.VERIFIED:
                for ref in form.provenance_refs:
                    assert prov_map[ref].verification_status == "VERIFIED"


class TestK102FailClosedValidation:
    """Verifies that invalid relations or foreign keys trigger fail-closed ValueError."""

    def test_rejects_unknown_provenance_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["provenance_refs"] = ("UNKNOWN_SOURCE_ID",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown provenance"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_method_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["related_method_ids"] = ("NON_EXISTENT_METHOD",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown related method"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_guaranteed_method_not_in_related_methods(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        # Set guaranteed to standard formula but omit standard formula from related
        form_dict["guaranteed_method_ids"] = ("QUAD_FORMULA_STANDARD",)
        form_dict["related_method_ids"] = ("QUAD_COMPLETE_SQUARE",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="is not contained in its related_method_ids"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_guaranteed_tip_not_in_related_tips(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["guaranteed_tip_ids"] = ("QUAD_TIP_REDUCED_FORMULA_EVEN_B",)
        form_dict["related_tip_ids"] = ("QUAD_TIP_SPECIAL_A_PLUS_B_PLUS_C_ZERO",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="is not contained in its related_tip_ids"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_non_empty_worked_example_references(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["worked_example_ids"] = ("EXAMPLE_001",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="Worked examples must be empty in K1-02 dataset"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_duplicate_tip_ids(self):
        dataset = load_k1_knowledge_dataset()
        dataset["tips"] = dataset["tips"] + [dataset["tips"][0]]

        with pytest.raises(ValueError, match="Duplicate tip_id found"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_duplicate_form_ids(self):
        dataset = load_k1_knowledge_dataset()
        dataset["problem_forms"] = dataset["problem_forms"] + [dataset["problem_forms"][0]]

        with pytest.raises(ValueError, match="Duplicate form_id found"):
            validate_k1_knowledge_dataset(dataset)


class TestK102ContentHashing:
    """Verifies S3 hash freeze and deterministic K1 combined content hash."""

    def test_s3_content_hash_is_strictly_unchanged(self):
        s3_hash = compute_dataset_content_hash()
        assert s3_hash == EXPECTED_S3_HASH, f"S3 hash changed! Expected {EXPECTED_S3_HASH}, got {s3_hash}"

    def test_k1_combined_content_hash_is_deterministic(self):
        h1 = compute_k1_dataset_content_hash()
        h2 = compute_k1_dataset_content_hash()
        assert h1 == h2
        assert len(h1) == 64
        # Hash must differ from S3 hash because it includes tips.json and problem_forms.json
        assert h1 != s3_hash_val if (s3_hash_val := compute_dataset_content_hash()) else True
