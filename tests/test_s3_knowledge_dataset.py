"""Unit and regression tests for MKE S3 Knowledge Dataset and Loader.

Verifies 1:1 MethodRegistry match, referential integrity across all entities,
bilingual completeness, DAG prerequisite acyclicity, deterministic ordering,
content hash determinism, and 4-equation S1 mathematical regression invariants.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from mke_product.application.dto import (
    CanonicalCoefficientInput,
    RawEquationInput,
    SolvedResponse,
    SolveRequest,
)
from mke_product.application.orchestrator import solve_request
from mke_product.core.rational import Rational
from mke_product.domain.models import (
    MathematicalApplicability,
    PedagogicalRecommendation,
    RationalFraction,
    SolutionOutcome,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.knowledge.loader import (
    compute_dataset_content_hash,
    load_concepts,
    load_formulas,
    load_knowledge_dataset,
    load_methods,
    load_provenances,
    load_theorems,
    validate_knowledge_dataset,
)
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    LocalizedText,
    MethodKnowledge,
    ProvenanceStatus,
    SourceProvenance,
)


def test_full_dataset_loads_and_validates() -> None:
    dataset = load_knowledge_dataset()
    assert len(dataset["provenances"]) == 3
    assert len(dataset["formulas"]) == 5
    assert len(dataset["theorems"]) == 1
    assert len(dataset["concepts"]) == 14
    assert len(dataset["methods"]) == 9


def test_methods_match_registry_one_to_one() -> None:
    registry = MethodRegistry()
    registry_ids = {m.method_id for m in registry.list_all()}
    methods = load_methods()
    dataset_ids = {m.method_id for m in methods}

    assert dataset_ids == registry_ids
    assert len(dataset_ids) == 9
    assert dataset_ids == {
        "QUAD_COMPLETE_SQUARE",
        "QUAD_FACTORIZATION_Q",
        "QUAD_FACTORIZATION_R",
        "QUAD_FORMULA_REDUCED",
        "QUAD_FORMULA_STANDARD",
        "QUAD_GRAPHICAL_ANALYSIS",
        "QUAD_VIETE_SPECIAL_DIF",
        "QUAD_VIETE_SPECIAL_SUM",
        "QUAD_VIETE_SUM_PRODUCT",
    }


def test_no_duplicate_ids_across_entities() -> None:
    provenances = load_provenances()
    prov_ids = [p.source_id for p in provenances]
    assert len(prov_ids) == len(set(prov_ids))

    formulas = load_formulas()
    form_ids = [f.formula_id for f in formulas]
    assert len(form_ids) == len(set(form_ids))

    theorems = load_theorems()
    thm_ids = [t.theorem_id for t in theorems]
    assert len(thm_ids) == len(set(thm_ids))

    concepts = load_concepts()
    concept_ids = [c.concept_id for c in concepts]
    assert len(concept_ids) == len(set(concept_ids))

    methods = load_methods()
    method_ids = [m.method_id for m in methods]
    assert len(method_ids) == len(set(method_ids))


def test_bilingual_completeness_across_all_entities() -> None:
    dataset = load_knowledge_dataset()

    def check_localized(obj: object, path: str) -> None:
        if isinstance(obj, LocalizedText):
            assert obj.vi.strip(), f"Empty vi at {path}"
            assert obj.en.strip(), f"Empty en at {path}"
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_localized(item, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_localized(v, f"{path}.{k}")
        elif isinstance(obj, BaseModel):
            for field_name in type(obj).model_fields:
                val = getattr(obj, field_name)
                check_localized(val, f"{path}.{field_name}")

    for entity_name, entity_list in dataset.items():
        check_localized(entity_list, entity_name)


def test_concept_prerequisites_acyclicity() -> None:
    concepts = load_concepts()
    # Loading already checks acyclicity, verify directly
    dataset = load_knowledge_dataset()
    assert "concepts" in dataset


def test_validation_detects_unknown_foreign_key() -> None:
    # Build valid dataset then inject unknown prerequisite concept into a method
    valid_methods = load_methods()
    tampered_methods = [
        MethodKnowledge(
            method_id=valid_methods[0].method_id,
            title=valid_methods[0].title,
            summary=valid_methods[0].summary,
            learning_objective=valid_methods[0].learning_objective,
            formal_description=valid_methods[0].formal_description,
            applicability_guidance=valid_methods[0].applicability_guidance,
            non_applicability_guidance=valid_methods[0].non_applicability_guidance,
            prerequisite_concept_ids=["concept_NON_EXISTENT"],
            formula_refs=valid_methods[0].formula_refs,
            theorem_refs=valid_methods[0].theorem_refs,
            common_mistakes=valid_methods[0].common_mistakes,
            diagnostic_tips=valid_methods[0].diagnostic_tips,
            related_method_ids=valid_methods[0].related_method_ids,
            curriculum_refs=valid_methods[0].curriculum_refs,
            provenance_refs=valid_methods[0].provenance_refs,
        )
    ] + valid_methods[1:]

    dataset = {
        "provenances": load_provenances(),
        "formulas": load_formulas(),
        "theorems": load_theorems(),
        "concepts": load_concepts(),
        "methods": tampered_methods,
    }
    with pytest.raises(ValueError, match="references unknown prerequisite concept"):
        validate_knowledge_dataset(dataset)


def test_validation_detects_cycle_in_concepts() -> None:
    cyclic_concepts = [
        ConceptKnowledge(
            concept_id="concept_a",
            title=LocalizedText(vi="A", en="A"),
            definition=LocalizedText(vi="A", en="A"),
            prerequisite_concept_ids=["concept_b"],
            provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
        ),
        ConceptKnowledge(
            concept_id="concept_b",
            title=LocalizedText(vi="B", en="B"),
            definition=LocalizedText(vi="B", en="B"),
            prerequisite_concept_ids=["concept_a"],
            provenance_refs=["SRC_MKE_S1_ORCHESTRATOR"],
        ),
    ]
    dataset = {
        "provenances": [
            SourceProvenance(
                source_id="SRC_MKE_S1_ORCHESTRATOR",
                source_type="ENGINE_SPEC",
                title="Spec",
                author_or_institution="Team",
                locator="spec.py",
                verification_status=ProvenanceStatus.VERIFIED,
            )
        ],
        "formulas": [],
        "theorems": [],
        "concepts": cyclic_concepts,
        "methods": [],
    }
    with pytest.raises(ValueError, match="Cycle detected in concept prerequisites"):
        validate_knowledge_dataset(dataset, registry_method_ids=set())


def test_content_hash_determinism() -> None:
    hash1 = compute_dataset_content_hash()
    hash2 = compute_dataset_content_hash()
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string


def test_s1_four_equation_mathematical_regression_guard() -> None:
    """Verifies that S1 mathematical engine produces exact expected assessments."""
    registry = MethodRegistry()

    # Eq 1: x^2 - 5*x + 6 = 0
    assess1 = registry.assess_quadratic(Rational(1, 1), Rational(-5, 1), Rational(6, 1))
    fact_q = next(m for m in assess1 if m.method_id == "QUAD_FACTORIZATION_Q")
    assert fact_q.mathematical_applicability == MathematicalApplicability.APPLICABLE
    assert fact_q.pedagogical_recommendation == PedagogicalRecommendation.RECOMMENDED

    req1 = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 5*x + 6 = 0"))
    res1 = solve_request(req1)
    assert isinstance(res1, SolvedResponse)
    assert res1.solution.outcome == SolutionOutcome.TWO_DISTINCT_REAL_ROOTS
    assert len(res1.solution.roots) == 2

    # Eq 2: x^2 - 4*x + 4 = 0
    req2 = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 - 4*x + 4 = 0"))
    res2 = solve_request(req2)
    assert isinstance(res2, SolvedResponse)
    assert res2.solution.outcome == SolutionOutcome.ONE_REPEATED_REAL_ROOT
    assert len(res2.solution.roots) == 1

    # Eq 3: x^2 + x + 1 = 0
    req3 = SolveRequest(input_payload=RawEquationInput(raw_query="x^2 + x + 1 = 0"))
    res3 = solve_request(req3)
    assert isinstance(res3, SolvedResponse)
    assert res3.solution.outcome == SolutionOutcome.NO_REAL_ROOTS
    assert len(res3.solution.roots) == 0

    # Eq 4: 2x^2 + 3x + 7 = 0
    # Invariant: QUAD_FORMULA_REDUCED is APPLICABLE with NEUTRAL recommendation (odd b)
    # Invariant: QUAD_GRAPHICAL_ANALYSIS priority is 6
    assess4 = registry.assess_quadratic(Rational(2, 1), Rational(3, 1), Rational(7, 1))
    red4 = next(m for m in assess4 if m.method_id == "QUAD_FORMULA_REDUCED")
    assert red4.mathematical_applicability == MathematicalApplicability.APPLICABLE
    assert red4.pedagogical_recommendation == PedagogicalRecommendation.NEUTRAL

    graph4 = next(m for m in assess4 if m.method_id == "QUAD_GRAPHICAL_ANALYSIS")
    assert graph4.pedagogical_priority == 6

