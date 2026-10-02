"""Unit and integration tests for MKE S3 KnowledgeRepository.

Verifies O(1) indexed lookups, immutability guarantees, defensive deep copying,
custom dataset validation (shape, types, duplicate IDs, complete foreign-key matrix),
canonical in-memory dataset hashing equivalence, MethodRegistry 1:1 match, direct &
transitive prerequisite traversal, cycle detection, and deterministic topological ordering.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mke_product.domain.registry import MethodRegistry
from mke_product.knowledge.loader import load_knowledge_dataset
from mke_product.knowledge.repository import (
    EntityNotFoundError,
    KnowledgeRepository,
    KnowledgeRepositoryError,
    PrerequisiteCycleError,
)
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    FormulaKnowledge,
    LocalizedText,
    MethodKnowledge,
    ProvenanceStatus,
    SourceProvenance,
    TheoremKnowledge,
)


@pytest.fixture
def repo() -> KnowledgeRepository:
    return KnowledgeRepository()


# ============================================================================
# 1. CORE REPOSITORY OPERATIONS & INDEXED LOOKUPS
# ============================================================================

def test_repository_loads_accepted_dataset(repo: KnowledgeRepository) -> None:
    counts = repo.get_entity_counts()
    assert counts["provenances"] == 3
    assert counts["formulas"] == 5
    assert counts["theorems"] == 1
    assert counts["concepts"] == 14
    assert counts["methods"] == 9


def test_repository_dataset_content_hash(repo: KnowledgeRepository) -> None:
    assert repo.get_dataset_content_hash() == "e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66"


def test_custom_in_memory_hash_matches_production_loader() -> None:
    accepted_dataset = load_knowledge_dataset()
    custom_repo = KnowledgeRepository(dataset=accepted_dataset)
    assert (
        custom_repo.get_dataset_content_hash()
        == "e689055c355bf91b748e1bb0909359ffa13177a8f334bc25df9caf8c2cf8ca66"
    )


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


# ============================================================================
# 2. DEFENSIVE ISOLATION & IMMUTABILITY
# ============================================================================

def test_returned_entities_are_immutable_and_defensively_copied(repo: KnowledgeRepository) -> None:
    # 1. Pydantic immutability assignment rejection
    method = repo.get_method("QUAD_FORMULA_STANDARD")
    with pytest.raises(ValidationError):
        method.method_id = "MUTATED"  # type: ignore[misc]

    concept = repo.get_concept("concept_discriminant")
    with pytest.raises(ValidationError):
        concept.concept_id = "MUTATED"  # type: ignore[misc]

    # 2. In-place list mutation on returned entity does NOT pollute repository internals
    method.prerequisite_concept_ids.append("concept_injected_evil")
    fresh_method = repo.get_method("QUAD_FORMULA_STANDARD")
    assert "concept_injected_evil" not in fresh_method.prerequisite_concept_ids

    concept.prerequisite_concept_ids.clear()
    fresh_concept = repo.get_concept("concept_discriminant")
    assert len(fresh_concept.prerequisite_concept_ids) > 0


def test_custom_dataset_ingestion_defensive_isolation() -> None:
    prov = SourceProvenance(
        source_id="SRC_CUSTOM",
        source_type="ENGINE_SPEC",
        title="Custom Spec",
        author_or_institution="Author",
        locator="spec.py",
        verification_status=ProvenanceStatus.VERIFIED,
    )
    concept_a = ConceptKnowledge(
        concept_id="concept_isolated_a",
        title=LocalizedText(vi="A", en="A"),
        definition=LocalizedText(vi="A", en="A"),
        prerequisite_concept_ids=[],
        provenance_refs=["SRC_CUSTOM"],
    )
    dataset = {
        "provenances": [prov],
        "formulas": [],
        "theorems": [],
        "concepts": [concept_a],
        "methods": [],
    }

    custom_repo = KnowledgeRepository(dataset=dataset)
    initial_hash = custom_repo.get_dataset_content_hash()

    # Mutate original object in outer scope
    concept_a.prerequisite_concept_ids.append("concept_mutated_after_init")

    # Verify repository copy is pristine
    repo_concept = custom_repo.get_concept("concept_isolated_a")
    assert repo_concept.prerequisite_concept_ids == []

    # Verify hash remains completely stable
    assert custom_repo.get_dataset_content_hash() == initial_hash


# ============================================================================
# 3. CUSTOM DATASET SHAPE & TYPE VALIDATION
# ============================================================================

def test_custom_dataset_rejects_non_mapping() -> None:
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(dataset=["not_a_dict"])  # type: ignore[arg-type]
    assert "Custom dataset must be a mapping/dict" in str(exc_info.value)


def test_custom_dataset_rejects_missing_or_unexpected_categories() -> None:
    # Missing category
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(dataset={"provenances": [], "formulas": [], "theorems": [], "concepts": []})
    assert "missing required categories" in str(exc_info.value)

    # Unexpected category
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(
            dataset={
                "provenances": [],
                "formulas": [],
                "theorems": [],
                "concepts": [],
                "methods": [],
                "extra_cat": [],
            }
        )
    assert "unexpected categories" in str(exc_info.value)


def test_custom_dataset_rejects_non_list_or_raw_dict_entities() -> None:
    # Non-list collection
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(
            dataset={
                "provenances": "not_a_list",  # type: ignore[dict-item]
                "formulas": [],
                "theorems": [],
                "concepts": [],
                "methods": [],
            }
        )
    assert "must be a list" in str(exc_info.value)

    # Raw dict instead of Pydantic model
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(
            dataset={
                "provenances": [{"source_id": "SRC_RAW"}],  # type: ignore[list-item]
                "formulas": [],
                "theorems": [],
                "concepts": [],
                "methods": [],
            }
        )
    assert "must be an instance of SourceProvenance" in str(exc_info.value)


# ============================================================================
# 4. COMPLETE DUPLICATE-ID TEST COVERAGE
# ============================================================================

def _base_valid_dataset() -> dict:
    prov = SourceProvenance(
        source_id="SRC_BASE",
        source_type="ENGINE_SPEC",
        title="Spec",
        author_or_institution="Author",
        locator="spec.py",
        verification_status=ProvenanceStatus.VERIFIED,
    )
    concept = ConceptKnowledge(
        concept_id="concept_base",
        title=LocalizedText(vi="Khái niệm gốc", en="Base Concept"),
        definition=LocalizedText(vi="Định nghĩa", en="Definition"),
        provenance_refs=["SRC_BASE"],
    )
    formula = FormulaKnowledge(
        formula_id="FORMULA_BASE",
        title=LocalizedText(vi="Công thức gốc", en="Base Formula"),
        latex_template="a = b",
        domain_conditions=LocalizedText(vi="Đk", en="Cond"),
        related_concept_ids=["concept_base"],
        provenance_refs=["SRC_BASE"],
    )
    theorem = TheoremKnowledge(
        theorem_id="THEOREM_BASE",
        title=LocalizedText(vi="Định lý gốc", en="Base Theorem"),
        statement=LocalizedText(vi="Phát biểu", en="Statement"),
        formal_statement_latex="P \\implies Q",
        related_concept_ids=["concept_base"],
        provenance_refs=["SRC_BASE"],
    )
    method = MethodKnowledge(
        method_id="METHOD_BASE",
        title=LocalizedText(vi="Phương pháp gốc", en="Base Method"),
        summary=LocalizedText(vi="Tóm tắt", en="Summary"),
        learning_objective=LocalizedText(vi="Mục tiêu", en="Objective"),
        formal_description=LocalizedText(vi="Mô tả", en="Description"),
        prerequisite_concept_ids=["concept_base"],
        formula_refs=["FORMULA_BASE"],
        theorem_refs=["THEOREM_BASE"],
        provenance_refs=["SRC_BASE"],
    )
    return {
        "provenances": [prov],
        "concepts": [concept],
        "formulas": [formula],
        "theorems": [theorem],
        "methods": [method],
    }


def test_custom_dataset_constructs_with_valid_theorem() -> None:
    ds = _base_valid_dataset()
    repo = KnowledgeRepository(dataset=ds)
    assert repo.get_theorem("THEOREM_BASE").theorem_id == "THEOREM_BASE"
    assert repo.get_entity_counts()["theorems"] == 1


@pytest.mark.parametrize(
    "category, duplicate_entity_fn, expected_field",
    [
        (
            "provenances",
            lambda ds: ds["provenances"][0].model_copy(deep=True),
            "SRC_BASE",
        ),
        (
            "formulas",
            lambda ds: ds["formulas"][0].model_copy(deep=True),
            "FORMULA_BASE",
        ),
        (
            "theorems",
            lambda ds: ds["theorems"][0].model_copy(deep=True),
            "THEOREM_BASE",
        ),
        (
            "concepts",
            lambda ds: ds["concepts"][0].model_copy(deep=True),
            "concept_base",
        ),
        (
            "methods",
            lambda ds: ds["methods"][0].model_copy(deep=True),
            "METHOD_BASE",
        ),
    ],
)
def test_duplicate_id_detection_across_all_categories(
    category: str, duplicate_entity_fn: Any, expected_field: str
) -> None:
    ds = _base_valid_dataset()
    ds[category].append(duplicate_entity_fn(ds))
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(dataset=ds)
    assert f"Duplicate entity ID '{expected_field}'" in str(exc_info.value)


# ============================================================================
# 5. COMPLETE DANGLING-REFERENCE TEST MATRIX (14 CASES)
# ============================================================================

@pytest.mark.parametrize(
    "mutator_fn, expected_missing_ref",
    [
        # 1. Formula -> missing concept
        (
            lambda ds: ds["formulas"].append(
                FormulaKnowledge(
                    formula_id="FORMULA_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    latex_template="x=1",
                    domain_conditions=LocalizedText(vi="A", en="A"),
                    related_concept_ids=["concept_missing"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "concept_missing",
        ),
        # 2. Formula -> missing provenance
        (
            lambda ds: ds["formulas"].append(
                FormulaKnowledge(
                    formula_id="FORMULA_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    latex_template="x=1",
                    domain_conditions=LocalizedText(vi="A", en="A"),
                    related_concept_ids=["concept_base"],
                    provenance_refs=["SRC_MISSING"],
                )
            ),
            "SRC_MISSING",
        ),
        # 3. Theorem -> missing concept
        (
            lambda ds: ds["theorems"].append(
                TheoremKnowledge(
                    theorem_id="THEOREM_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    statement=LocalizedText(vi="A", en="A"),
                    formal_statement_latex="P",
                    related_concept_ids=["concept_missing"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "concept_missing",
        ),
        # 4. Theorem -> missing provenance
        (
            lambda ds: ds["theorems"].append(
                TheoremKnowledge(
                    theorem_id="THEOREM_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    statement=LocalizedText(vi="A", en="A"),
                    formal_statement_latex="P",
                    related_concept_ids=["concept_base"],
                    provenance_refs=["SRC_MISSING"],
                )
            ),
            "SRC_MISSING",
        ),
        # 5. Concept -> missing prerequisite concept
        (
            lambda ds: ds["concepts"].append(
                ConceptKnowledge(
                    concept_id="concept_dangling",
                    title=LocalizedText(vi="A", en="A"),
                    definition=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_missing"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "concept_missing",
        ),
        # 6. Concept -> missing related concept
        (
            lambda ds: ds["concepts"].append(
                ConceptKnowledge(
                    concept_id="concept_dangling",
                    title=LocalizedText(vi="A", en="A"),
                    definition=LocalizedText(vi="A", en="A"),
                    related_concept_ids=["concept_missing"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "concept_missing",
        ),
        # 7. Concept -> missing formula
        (
            lambda ds: ds["concepts"].append(
                ConceptKnowledge(
                    concept_id="concept_dangling",
                    title=LocalizedText(vi="A", en="A"),
                    definition=LocalizedText(vi="A", en="A"),
                    formula_refs=["FORMULA_MISSING"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "FORMULA_MISSING",
        ),
        # 8. Concept -> missing method
        (
            lambda ds: ds["concepts"].append(
                ConceptKnowledge(
                    concept_id="concept_dangling",
                    title=LocalizedText(vi="A", en="A"),
                    definition=LocalizedText(vi="A", en="A"),
                    method_refs=["METHOD_MISSING"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "METHOD_MISSING",
        ),
        # 9. Concept -> missing provenance
        (
            lambda ds: ds["concepts"].append(
                ConceptKnowledge(
                    concept_id="concept_dangling",
                    title=LocalizedText(vi="A", en="A"),
                    definition=LocalizedText(vi="A", en="A"),
                    provenance_refs=["SRC_MISSING"],
                )
            ),
            "SRC_MISSING",
        ),
        # 10. Method -> missing prerequisite concept
        (
            lambda ds: ds["methods"].append(
                MethodKnowledge(
                    method_id="METHOD_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    summary=LocalizedText(vi="A", en="A"),
                    learning_objective=LocalizedText(vi="A", en="A"),
                    formal_description=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_missing"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "concept_missing",
        ),
        # 11. Method -> missing formula
        (
            lambda ds: ds["methods"].append(
                MethodKnowledge(
                    method_id="METHOD_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    summary=LocalizedText(vi="A", en="A"),
                    learning_objective=LocalizedText(vi="A", en="A"),
                    formal_description=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_base"],
                    formula_refs=["FORMULA_MISSING"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "FORMULA_MISSING",
        ),
        # 12. Method -> missing theorem
        (
            lambda ds: ds["methods"].append(
                MethodKnowledge(
                    method_id="METHOD_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    summary=LocalizedText(vi="A", en="A"),
                    learning_objective=LocalizedText(vi="A", en="A"),
                    formal_description=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_base"],
                    theorem_refs=["THEOREM_MISSING"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "THEOREM_MISSING",
        ),
        # 13. Method -> missing related method
        (
            lambda ds: ds["methods"].append(
                MethodKnowledge(
                    method_id="METHOD_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    summary=LocalizedText(vi="A", en="A"),
                    learning_objective=LocalizedText(vi="A", en="A"),
                    formal_description=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_base"],
                    related_method_ids=["METHOD_MISSING"],
                    provenance_refs=["SRC_BASE"],
                )
            ),
            "METHOD_MISSING",
        ),
        # 14. Method -> missing provenance
        (
            lambda ds: ds["methods"].append(
                MethodKnowledge(
                    method_id="METHOD_DANGLING",
                    title=LocalizedText(vi="A", en="A"),
                    summary=LocalizedText(vi="A", en="A"),
                    learning_objective=LocalizedText(vi="A", en="A"),
                    formal_description=LocalizedText(vi="A", en="A"),
                    prerequisite_concept_ids=["concept_base"],
                    provenance_refs=["SRC_MISSING"],
                )
            ),
            "SRC_MISSING",
        ),
    ],
)
def test_complete_dangling_reference_rejection_matrix(
    mutator_fn: Any, expected_missing_ref: str
) -> None:
    ds = _base_valid_dataset()
    mutator_fn(ds)
    with pytest.raises(KnowledgeRepositoryError) as exc_info:
        KnowledgeRepository(dataset=ds)
    assert expected_missing_ref in str(exc_info.value)


# ============================================================================
# 6. PREREQUISITE TRAVERSAL & TOPOLOGICAL ORDER
# ============================================================================

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

    # Fast key lookups verify correct retrieval of models
    for method in repo.list_methods():
        assert repo.get_method(method.method_id).method_id == method.method_id
