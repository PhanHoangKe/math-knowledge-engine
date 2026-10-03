"""MKE MVP V1 — Milestone K1-02-R1 Curated Knowledge Dataset Test Suite.

Verifies:
1. Exact cardinalities (3 tips, 6 problem forms) and exact canonical IDs.
2. Canonical lexicographic ordering in raw JSON dataset files and loader enforcement.
3. Bilingual completeness and non-empty pedagogical text across all fields.
4. Exact mathematical conditions using the closed PredicateId language.
5. Referential integrity to existing S3 entities (provenances, methods, concepts, formulas, theorems).
6. Relation subset invariants (guaranteed_method_ids ⊆ related_method_ids, guaranteed_tip_ids ⊆ related_tip_ids).
7. Empty example reference policy (worked_example_ids and practice_example_ids must be empty).
8. Provenance verification gate (VERIFIED entities only reference VERIFIED sources, rejects UNVERIFIED).
9. Fail-closed rejection of malformed, duplicate, dangling, or unverified references.
10. Content hashing invariance (S3 hash byte-frozen, K1 combined hash deterministic).
11. Repeated load determinism (load_quick_tips() and load_problem_forms() are idempotent and deterministic).
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
from mke_product.knowledge.schemas import ProvenanceStatus, SourceProvenance

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

    def test_loader_rejects_non_canonical_tip_ordering(self):
        dataset = load_k1_knowledge_dataset()
        # Reverse tips order
        dataset["tips"] = list(reversed(dataset["tips"]))
        with pytest.raises(ValueError, match="tips dataset must be in canonical lexicographic tip_id order"):
            validate_k1_knowledge_dataset(dataset)

    def test_loader_rejects_non_canonical_problem_form_ordering(self):
        dataset = load_k1_knowledge_dataset()
        # Reverse problem_forms order
        dataset["problem_forms"] = list(reversed(dataset["problem_forms"]))
        with pytest.raises(ValueError, match="problem_forms dataset must be in canonical lexicographic form_id order"):
            validate_k1_knowledge_dataset(dataset)


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

    def test_incomplete_forms_sound_wording(self):
        forms = {f.form_id: f for f in load_problem_forms()}

        # Incomplete C=0 must note b=0 repeated root distinction
        form_c = forms["QUAD_FORM_INCOMPLETE_C_ZERO"]
        assert "Khi b=0" in form_c.summary.vi or "b=0" in form_c.summary.vi
        assert "When b = 0" in form_c.summary.en or "b = 0" in form_c.summary.en

        # Incomplete B=0 must specify real domain sign cases for -c/a
        form_b = forms["QUAD_FORM_INCOMPLETE_B_ZERO"]
        assert "-c/a > 0" in form_b.summary.vi and "-c/a < 0" in form_b.summary.vi
        assert "-c/a > 0" in form_b.summary.en and "-c/a < 0" in form_b.summary.en


class TestK102StatusAndGovernanceMatrix:
    """Verifies explicit status attributes of all tips and forms."""

    def test_all_quick_tips_status_verified(self):
        tips = load_quick_tips()
        for tip in tips:
            assert tip.status == KnowledgeEntityStatus.VERIFIED, (
                f"QuickTip '{tip.tip_id}' status is not VERIFIED: {tip.status}"
            )

    def test_all_problem_forms_status_verified(self):
        forms = load_problem_forms()
        for form in forms:
            assert form.status == KnowledgeEntityStatus.VERIFIED, (
                f"ProblemForm '{form.form_id}' status is not VERIFIED: {form.status}"
            )


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
                    assert prov_map[ref].verification_status == ProvenanceStatus.VERIFIED

        for form in dataset["problem_forms"]:
            if form.status == KnowledgeEntityStatus.VERIFIED:
                for ref in form.provenance_refs:
                    assert prov_map[ref].verification_status == ProvenanceStatus.VERIFIED


class TestK102FailClosedValidation:
    """Verifies that invalid relations or foreign keys trigger fail-closed ValueError."""

    def test_rejects_unknown_provenance_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["provenance_refs"] = ("UNKNOWN_SOURCE_ID",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown provenance"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_provenance_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["provenance_refs"] = ("UNKNOWN_SOURCE_ID",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown provenance"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_method_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["related_method_ids"] = ("NON_EXISTENT_METHOD",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown method"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_method_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["related_method_ids"] = ("NON_EXISTENT_METHOD",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown related method"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_guaranteed_method_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["guaranteed_method_ids"] = ("NON_EXISTENT_METHOD",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown guaranteed method"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_concept_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["related_concept_ids"] = ("NON_EXISTENT_CONCEPT",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown concept"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_concept_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["prerequisite_concept_ids"] = ("NON_EXISTENT_CONCEPT",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown prerequisite concept"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_formula_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["formula_refs"] = ("NON_EXISTENT_FORMULA",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown formula"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_formula_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["formula_refs"] = ("NON_EXISTENT_FORMULA",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown formula"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_theorem_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["theorem_refs"] = ("NON_EXISTENT_THEOREM",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown theorem"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_unknown_theorem_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["theorem_refs"] = ("NON_EXISTENT_THEOREM",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown theorem"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_dangling_related_problem_form_in_tip(self):
        dataset = load_k1_knowledge_dataset()
        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["related_problem_form_ids"] = ("DANGLING_FORM_ID",)
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references unknown problem form"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_dangling_related_tip_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["related_tip_ids"] = ("DANGLING_TIP_ID",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown related tip"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_dangling_guaranteed_tip_in_problem_form(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["guaranteed_tip_ids"] = ("DANGLING_TIP_ID",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references unknown guaranteed tip"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_guaranteed_method_not_in_related_methods(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
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

    def test_rejects_non_empty_practice_example_references(self):
        dataset = load_k1_knowledge_dataset()
        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["practice_example_ids"] = ("PRACTICE_001",)
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="Practice examples must be empty in K1-02 dataset"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_verified_tip_referencing_unverified_provenance(self):
        dataset = load_k1_knowledge_dataset()
        # Inject an unverified provenance source into dataset
        unverified_prov = SourceProvenance(
            source_id="SRC_UNVERIFIED_SOURCE",
            title="Unverified Source",
            author_or_institution="Unknown",
            publication_year=2026,
            source_type="ENGINE_SPEC",
            locator="test",
            verification_status=ProvenanceStatus.UNVERIFIED,
        )
        dataset["provenances"] = dataset["provenances"] + [unverified_prov]

        tip_dict = dataset["tips"][0].model_dump()
        tip_dict["provenance_refs"] = ("SRC_UNVERIFIED_SOURCE",)
        tip_dict["status"] = KnowledgeEntityStatus.VERIFIED
        dataset["tips"] = [QuickTipKnowledge.model_validate(tip_dict)] + dataset["tips"][1:]

        with pytest.raises(ValueError, match="references non-VERIFIED provenance"):
            validate_k1_knowledge_dataset(dataset)

    def test_rejects_verified_problem_form_referencing_unverified_provenance(self):
        dataset = load_k1_knowledge_dataset()
        unverified_prov = SourceProvenance(
            source_id="SRC_UNVERIFIED_SOURCE",
            title="Unverified Source",
            author_or_institution="Unknown",
            publication_year=2026,
            source_type="ENGINE_SPEC",
            locator="test",
            verification_status=ProvenanceStatus.UNVERIFIED,
        )
        dataset["provenances"] = dataset["provenances"] + [unverified_prov]

        form_dict = dataset["problem_forms"][0].model_dump()
        form_dict["provenance_refs"] = ("SRC_UNVERIFIED_SOURCE",)
        form_dict["status"] = KnowledgeEntityStatus.VERIFIED
        dataset["problem_forms"] = [RelatedProblemFormKnowledge.model_validate(form_dict)] + dataset["problem_forms"][1:]

        with pytest.raises(ValueError, match="references non-VERIFIED provenance"):
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


class TestK102MalformedDataAndLoaderDeterminism:
    """Verifies loader error handling on malformed files and repeated load determinism."""

    def test_load_quick_tips_rejects_malformed_json(self, tmp_path: Path):
        bad_json = tmp_path / "tips.json"
        bad_json.write_text("{ this is not valid json }", encoding="utf-8")

        with pytest.raises(Exception):
            load_quick_tips(data_dir=tmp_path)

    def test_load_quick_tips_rejects_invalid_schema(self, tmp_path: Path):
        bad_schema = tmp_path / "tips.json"
        bad_schema.write_text(json.dumps([{"invalid_field": "test"}]), encoding="utf-8")

        with pytest.raises(Exception):
            load_quick_tips(data_dir=tmp_path)

    def test_load_problem_forms_rejects_malformed_json(self, tmp_path: Path):
        bad_json = tmp_path / "problem_forms.json"
        bad_json.write_text("{ this is not valid json }", encoding="utf-8")

        with pytest.raises(Exception):
            load_problem_forms(data_dir=tmp_path)

    def test_load_problem_forms_rejects_invalid_schema(self, tmp_path: Path):
        bad_schema = tmp_path / "problem_forms.json"
        bad_schema.write_text(json.dumps([{"invalid_field": "test"}]), encoding="utf-8")

        with pytest.raises(Exception):
            load_problem_forms(data_dir=tmp_path)

    def test_repeated_load_quick_tips_is_deterministic(self):
        t1 = load_quick_tips()
        t2 = load_quick_tips()
        assert t1 == t2
        assert [t.model_dump() for t in t1] == [t.model_dump() for t in t2]

    def test_repeated_load_problem_forms_is_deterministic(self):
        f1 = load_problem_forms()
        f2 = load_problem_forms()
        assert f1 == f2
        assert [f.model_dump() for f in f1] == [f.model_dump() for f in f2]


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
