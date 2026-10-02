"""Unit tests for MKE S3 Knowledge Schemas.

Verifies strict Pydantic v2 validation, immutability, extra field rejection,
bilingual constraints, and negative guard tests against runtime solver state leakage.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    CurriculumMappingStatus,
    CurriculumRef,
    FormulaKnowledge,
    LocalizedText,
    MethodKnowledge,
    ProvenanceStatus,
    SourceProvenance,
    TheoremKnowledge,
)


def test_localized_text_valid() -> None:
    text = LocalizedText(vi="Xin chào", en="Hello")
    assert text.vi == "Xin chào"
    assert text.en == "Hello"


def test_localized_text_rejects_empty_or_whitespace() -> None:
    with pytest.raises(ValidationError):
        LocalizedText(vi="", en="Hello")

    with pytest.raises(ValidationError):
        LocalizedText(vi="Xin chào", en="   ")

    with pytest.raises(ValidationError):
        LocalizedText(vi="   ", en="   ")


def test_localized_text_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LocalizedText(vi="Xin chào", en="Hello", extra_field="forbidden")  # type: ignore[call-arg]


def test_localized_text_immutability() -> None:
    text = LocalizedText(vi="Xin chào", en="Hello")
    with pytest.raises(ValidationError):
        text.vi = "Chào bạn"  # type: ignore[misc]


def test_curriculum_ref_valid_and_frozen() -> None:
    ref = CurriculumRef(
        framework="GDPT_2018",
        subject="TOAN",
        grade_band="GRADE_9",
        topic="PHUONG_TRINH_BAC_HAI_MOT_AN",
        source_document="Chương trình GDPT 2018 Môn Toán",
        source_locator="Trang 45, Mục 2",
        status=CurriculumMappingStatus.VERIFIED_MAPPING,
    )
    assert ref.framework == "GDPT_2018"
    assert ref.competency_ref is None
    with pytest.raises(ValidationError):
        ref.framework = "CCSS"  # type: ignore[misc]


def test_source_provenance_valid_and_extra_rejection() -> None:
    prov = SourceProvenance(
        source_id="SRC_MKE_S1_ORCHESTRATOR",
        source_type="ENGINE_SPEC",
        title="MKE S1 Algebra Execution Engine Specification",
        author_or_institution="MKE Core Team",
        publication_year=2026,
        locator="src/mke_product/domain/registry.py",
        verification_status=ProvenanceStatus.VERIFIED,
    )
    assert prov.source_id == "SRC_MKE_S1_ORCHESTRATOR"

    with pytest.raises(ValidationError):
        SourceProvenance(
            source_id="SRC_TEST",
            source_type="ENGINE_SPEC",
            title="Test",
            author_or_institution="Team",
            locator="test.py",
            verification_status=ProvenanceStatus.VERIFIED,
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


def test_formula_knowledge_schema_validation() -> None:
    formula = FormulaKnowledge(
        formula_id="FORMULA_DISCRIMINANT",
        title=LocalizedText(vi="Biệt thức", en="Discriminant"),
        latex_template=r"\Delta = b^2 - 4ac",
        variables_description={"Delta": LocalizedText(vi="Biệt thức", en="Discriminant")},
        domain_conditions=LocalizedText(vi="a != 0", en="a != 0"),
        related_concept_ids=["concept_discriminant"],
        provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
    )
    assert formula.formula_id == "FORMULA_DISCRIMINANT"
    assert formula.version == "1.0.0"

    with pytest.raises(ValidationError):
        FormulaKnowledge(
            formula_id="FORMULA_DISCRIMINANT",
            title=LocalizedText(vi="Biệt thức", en="Discriminant"),
            latex_template=r"\Delta = b^2 - 4ac",
            domain_conditions=LocalizedText(vi="a != 0", en="a != 0"),
            extra="extra",  # type: ignore[call-arg]
        )


def test_theorem_knowledge_schema_validation() -> None:
    thm = TheoremKnowledge(
        theorem_id="THEOREM_VIETA_RELATIONS",
        title=LocalizedText(vi="Định lý Vi-ét", en="Viète's Theorem"),
        statement=LocalizedText(vi="Tổng và tích nghiệm", en="Sum and product of roots"),
        formal_statement_latex=r"x_1 + x_2 = -b/a \land x_1 x_2 = c/a",
        hypotheses=[LocalizedText(vi="a != 0", en="a != 0")],
        conclusions=[LocalizedText(vi="x_1 + x_2 = -b/a", en="x_1 + x_2 = -b/a")],
        related_concept_ids=["concept_vieta_relations"],
        provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
    )
    assert thm.theorem_id == "THEOREM_VIETA_RELATIONS"


def test_concept_knowledge_schema_validation() -> None:
    concept = ConceptKnowledge(
        concept_id="concept_discriminant",
        title=LocalizedText(vi="Biệt thức", en="Discriminant"),
        definition=LocalizedText(vi="Biệt thức Delta = b^2 - 4ac", en="Discriminant Delta = b^2 - 4ac"),
        prerequisite_concept_ids=["concept_quadratic_equation"],
        related_concept_ids=["concept_real_root"],
        formula_refs=["FORMULA_DISCRIMINANT"],
        method_refs=["QUAD_FORMULA_STANDARD"],
        curriculum_refs=[],
        provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
    )
    assert concept.concept_id == "concept_discriminant"


def test_method_knowledge_schema_negative_runtime_leak_guard() -> None:
    """Ensure MethodKnowledge strictly forbids dynamic equation-specific solver fields."""
    valid_kwargs = {
        "method_id": "QUAD_FORMULA_STANDARD",
        "title": LocalizedText(vi="Công thức chuẩn", en="Standard Formula"),
        "summary": LocalizedText(vi="Giải qua Delta", en="Solves via Delta"),
        "learning_objective": LocalizedText(vi="Nắm công thức", en="Master formula"),
        "formal_description": LocalizedText(vi="Mô tả", en="Description"),
        "applicability_guidance": [LocalizedText(vi="Mọi phương trình", en="All quadratics")],
        "non_applicability_guidance": [LocalizedText(vi="Khi a = 0", en="When a = 0")],
        "prerequisite_concept_ids": ["concept_quadratic_equation"],
        "formula_refs": ["FORMULA_DISCRIMINANT"],
        "theorem_refs": [],
        "common_mistakes": [LocalizedText(vi="Sai dấu", en="Sign error")],
        "diagnostic_tips": [LocalizedText(vi="Tính Delta", en="Compute Delta")],
        "related_method_ids": ["QUAD_FORMULA_REDUCED"],
        "curriculum_refs": [],
        "provenance_refs": ["SRC_MKE_S1_ORCHESTRATOR"],
    }

    # Verify valid construction
    method = MethodKnowledge(**valid_kwargs)
    assert method.method_id == "QUAD_FORMULA_STANDARD"

    # Verify rejection of dynamic runtime solver state
    forbidden_runtime_fields = [
        {"applicability": "APPLICABLE"},
        {"is_applicable": True},
        {"discriminant": 16},
        {"roots": [1, 2]},
        {"steps": ["Step 1", "Step 2"]},
        {"recommendation_level": "RECOMMENDED"},
        {"equation": "x^2 - 5x + 6 = 0"},
    ]

    for forbidden_field in forbidden_runtime_fields:
        kwargs_with_forbidden = {**valid_kwargs, **forbidden_field}
        with pytest.raises(ValidationError):
            MethodKnowledge(**kwargs_with_forbidden)  # type: ignore[arg-type]


def test_strict_type_coercion_rejection() -> None:
    """Verifies that strict=True rejects implicit type coercion in Python data structures."""
    # 1. String year must NOT coerce to integer
    with pytest.raises(ValidationError):
        SourceProvenance(
            source_id="SRC_TEST",
            source_type="ENGINE_SPEC",
            title="Test",
            author_or_institution="Team",
            publication_year="2026",  # type: ignore[arg-type]
            locator="test.py",
            verification_status=ProvenanceStatus.VERIFIED,
        )

    # 2. Float year must NOT coerce to integer
    with pytest.raises(ValidationError):
        SourceProvenance(
            source_id="SRC_TEST",
            source_type="ENGINE_SPEC",
            title="Test",
            author_or_institution="Team",
            publication_year=2026.0,  # type: ignore[arg-type]
            locator="test.py",
            verification_status=ProvenanceStatus.VERIFIED,
        )

    # 3. Tuple must NOT coerce to List
    with pytest.raises(ValidationError):
        FormulaKnowledge(
            formula_id="FORMULA_DISCRIMINANT",
            title=LocalizedText(vi="Biệt thức", en="Discriminant"),
            latex_template=r"\Delta = b^2 - 4ac",
            variables_description={"Delta": LocalizedText(vi="Biệt thức", en="Discriminant")},
            domain_conditions=LocalizedText(vi="a != 0", en="a != 0"),
            related_concept_ids=("concept_discriminant",),  # type: ignore[arg-type]
            provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
        )


def test_strict_type_adapter_json_validation() -> None:
    """Verifies that TypeAdapter validate_json enforces strict types from raw JSON."""
    from mke_product.knowledge.loader import _PROVENANCE_LIST_ADAPTER

    # String integer in JSON must be rejected in strict mode
    invalid_json = b"""[
      {
        "author_or_institution": "Team",
        "locator": "test.py",
        "publication_year": "2026",
        "source_id": "SRC_TEST",
        "source_type": "ENGINE_SPEC",
        "title": "Title",
        "verification_status": "VERIFIED"
      }
    ]"""
    with pytest.raises(ValidationError):
        _PROVENANCE_LIST_ADAPTER.validate_json(invalid_json)

    # Valid JSON with integer year and string enum must pass
    valid_json = b"""[
      {
        "author_or_institution": "Team",
        "locator": "test.py",
        "publication_year": 2026,
        "source_id": "SRC_TEST",
        "source_type": "ENGINE_SPEC",
        "title": "Title",
        "verification_status": "VERIFIED"
      }
    ]"""
    result = _PROVENANCE_LIST_ADAPTER.validate_json(valid_json)
    assert len(result) == 1
    assert result[0].publication_year == 2026
    assert result[0].verification_status == ProvenanceStatus.VERIFIED

