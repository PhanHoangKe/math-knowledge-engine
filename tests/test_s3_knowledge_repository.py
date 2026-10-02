"""Unit and integration tests for MKE S3 KnowledgeRepository.

Verifies O(1) indexed lookups, immutability, entity counts, MethodRegistry 1:1 match,
direct & transitive prerequisite traversal, cycle detection, and topological ordering.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mke_product.domain.registry import MethodRegistry
from mke_product.knowledge.repository import (
    EntityNotFoundError,
    KnowledgeRepository,
    PrerequisiteCycleError,
)
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    LocalizedText,
    ProvenanceStatus,
    SourceProvenance,
)


@pytest.fixture
def repo() -> KnowledgeRepository:
    return KnowledgeRepository()


def test_repository_loads_accepted_dataset(repo: KnowledgeRepository) -> None:
    counts = repo.get_entity_counts()
    assert counts["provenances"] == 3
    assert counts["formulas"] == 5
    assert counts["theorems"] == 1
    assert counts["concepts"] == 14
    assert counts["methods"] == 9


def test_repository_dataset_content_hash(repo: KnowledgeRepository) -> None:
    assert repo.get_dataset_content_hash() == "e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66"


def test_repository_matches_registry_one_to_one(repo: KnowledgeRepository) -> None:
    registry = MethodRegistry()
    registry_ids = {m.method_id for m in registry.list_all()}
    repo_ids = {m.method_id for m in repo.list_methods()}
    assert repo_ids == registry_ids
    assert len(repo_ids) == 9


def test_indexed_lookups_return_exact_entities(repo: KnowledgeRepository) -> None:
    # 1. Method
    method = repo.get_method("QUAD_FORMULA_STANDARD")
    assert method.method_id == "QUAD_FORMULA_STANDARD"
    assert "concept_discriminant" in method.prerequisite_concept_ids

    # 2. Concept
    concept = repo.get_concept("concept_discriminant")
    assert concept.concept_id == "concept_discriminant"
    assert "concept_quadratic_equation" in concept.prerequisite_concept_ids

    # 3. Formula
    formula = repo.get_formula("FORMULA_DISCRIMINANT")
    assert formula.formula_id == "FORMULA_DISCRIMINANT"

    # 4. Theorem
    theorem = repo.get_theorem("THEOREM_VIETA_RELATIONS")
    assert theorem.theorem_id == "THEOREM_VIETA_RELATIONS"

    # 5. Provenance
    prov = repo.get_provenance("SRC_MKE_S1_ORCHESTRATOR")
    assert prov.source_id == "SRC_MKE_S1_ORCHESTRATOR"


def test_unknown_id_fails_deterministically(repo: KnowledgeRepository) -> None:
    with pytest.raises(EntityNotFoundError) as exc_info:
        repo.get_method("UNKNOWN_METHOD")
    assert "MethodKnowledge with ID 'UNKNOWN_METHOD' not found" in str(exc_info.value)

    with pytest.raises(EntityNotFoundError):
        repo.get_concept("concept_nonexistent")

    with pytest.raises(EntityNotFoundError):
        repo.get_formula("FORMULA_UNKNOWN")

    with pytest.raises(EntityNotFoundError):
        repo.get_theorem("THEOREM_UNKNOWN")

    with pytest.raises(EntityNotFoundError):
        repo.get_provenance("SRC_UNKNOWN")


def test_returned_entities_are_immutable(repo: KnowledgeRepository) -> None:
    method = repo.get_method("QUAD_FORMULA_STANDARD")
    with pytest.raises(ValidationError):
        method.method_id = "MUTATED"  # type: ignore[misc]

    concept = repo.get_concept("concept_discriminant")
    with pytest.raises(ValidationError):
        concept.concept_id = "MUTATED"  # type: ignore[misc]


def test_direct_prerequisites_traversal(repo: KnowledgeRepository) -> None:
    prereqs = repo.get_direct_prerequisites("concept_parabola_vertex")
    prereq_ids = [p.concept_id for p in prereqs]
    assert sorted(prereq_ids) == ["concept_axis_symmetry", "concept_parabola"]

    root_prereqs = repo.get_direct_prerequisites("concept_real_number")
    assert root_prereqs == []


def test_transitive_prerequisites_traversal(repo: KnowledgeRepository) -> None:
    # concept_parabola_vertex -> [concept_axis_symmetry, concept_parabola] -> concept_quadratic_equation -> concept_polynomial_coefficient -> concept_real_number
    trans_prereqs = repo.get_transitive_prerequisites("concept_parabola_vertex")
    trans_ids = [p.concept_id for p in trans_prereqs]

    assert "concept_axis_symmetry" in trans_ids
    assert "concept_parabola" in trans_ids
    assert "concept_quadratic_equation" in trans_ids
    assert "concept_polynomial_coefficient" in trans_ids
    assert "concept_real_number" in trans_ids

    # Verify dependency order: concept_real_number must appear before concept_quadratic_equation
    assert trans_ids.index("concept_real_number") < trans_ids.index("concept_quadratic_equation")
    assert trans_ids.index("concept_quadratic_equation") < trans_ids.index("concept_parabola")


def test_topological_prerequisite_order(repo: KnowledgeRepository) -> None:
    topo_concepts = repo.get_topological_prerequisite_order()
    assert len(topo_concepts) == 14
    topo_ids = [c.concept_id for c in topo_concepts]

    # Verify that for every concept, all of its prerequisites appear earlier in the list
    seen_ids = set()
    for concept in topo_concepts:
        for prereq_id in concept.prerequisite_concept_ids:
            assert prereq_id in seen_ids, (
                f"Prerequisite '{prereq_id}' must appear before '{concept.concept_id}' in topological order."
            )
        seen_ids.add(concept.concept_id)


def test_cycle_detection_in_prerequisites() -> None:
    cyclic_dataset = {
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
        "concepts": [
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
        ],
        "methods": [],
    }

    with pytest.raises(PrerequisiteCycleError):
        KnowledgeRepository(dataset=cyclic_dataset)


def test_o1_indexed_lookups_architecture(repo: KnowledgeRepository) -> None:
    """Demonstrates that lookups operate on dictionary mappings rather than linear scans."""
    assert isinstance(repo._methods, dict)
    assert isinstance(repo._concepts, dict)
    assert isinstance(repo._formulas, dict)
    assert isinstance(repo._theorems, dict)
    assert isinstance(repo._provenances, dict)

    # Fast key lookups
    for method in repo.list_methods():
        assert repo.get_method(method.method_id) is method
