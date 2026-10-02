"""MKE MVP V1 — In-Memory Knowledge Repository.

Provides O(1) indexed lookups, immutability guarantees, and deterministic
prerequisite traversal over the accepted MKE S3 pedagogical knowledge dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mke_product.knowledge.loader import (
    compute_dataset_content_hash,
    load_knowledge_dataset,
)
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    FormulaKnowledge,
    MethodKnowledge,
    SourceProvenance,
    TheoremKnowledge,
)


class KnowledgeRepositoryError(Exception):
    """Base exception for all KnowledgeRepository operational errors."""


class EntityNotFoundError(KnowledgeRepositoryError):
    """Raised when an entity is requested by an unknown primary key ID."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        super().__init__(f"{entity_type} with ID '{entity_id}' not found in KnowledgeRepository.")
        self.entity_type = entity_type
        self.entity_id = entity_id


class PrerequisiteCycleError(KnowledgeRepositoryError):
    """Raised when a cycle is detected during concept prerequisite graph traversal."""


class KnowledgeRepository:
    """Immutable, indexed in-memory repository for MKE pedagogical knowledge entities."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        dataset: Optional[Dict[str, Any]] = None,
    ) -> None:
        if dataset is not None:
            raw_dataset = dataset
        else:
            raw_dataset = load_knowledge_dataset(data_dir)

        # Build immutable indexed lookup dictionaries
        self._methods: Dict[str, MethodKnowledge] = {
            m.method_id: m for m in raw_dataset["methods"]
        }
        self._concepts: Dict[str, ConceptKnowledge] = {
            c.concept_id: c for c in raw_dataset["concepts"]
        }
        self._formulas: Dict[str, FormulaKnowledge] = {
            f.formula_id: f for f in raw_dataset["formulas"]
        }
        self._theorems: Dict[str, TheoremKnowledge] = {
            t.theorem_id: t for t in raw_dataset["theorems"]
        }
        self._provenances: Dict[str, SourceProvenance] = {
            p.source_id: p for p in raw_dataset["provenances"]
        }

        self._data_dir = data_dir
        self._cached_content_hash: Optional[str] = (
            compute_dataset_content_hash(data_dir) if data_dir is not None or dataset is None else None
        )

        # Validate prerequisite acyclicity on initialization
        self.get_topological_prerequisite_order()

    # ------------------------------------------------------------------------
    # Indexed Single-Entity Lookups (O(1))
    # ------------------------------------------------------------------------

    def get_method(self, method_id: str) -> MethodKnowledge:
        """Retrieves a MethodKnowledge entity by its canonical method_id."""
        if method_id not in self._methods:
            raise EntityNotFoundError("MethodKnowledge", method_id)
        return self._methods[method_id]

    def get_concept(self, concept_id: str) -> ConceptKnowledge:
        """Retrieves a ConceptKnowledge entity by its concept_id."""
        if concept_id not in self._concepts:
            raise EntityNotFoundError("ConceptKnowledge", concept_id)
        return self._concepts[concept_id]

    def get_formula(self, formula_id: str) -> FormulaKnowledge:
        """Retrieves a FormulaKnowledge entity by its formula_id."""
        if formula_id not in self._formulas:
            raise EntityNotFoundError("FormulaKnowledge", formula_id)
        return self._formulas[formula_id]

    def get_theorem(self, theorem_id: str) -> TheoremKnowledge:
        """Retrieves a TheoremKnowledge entity by its theorem_id."""
        if theorem_id not in self._theorems:
            raise EntityNotFoundError("TheoremKnowledge", theorem_id)
        return self._theorems[theorem_id]

    def get_provenance(self, source_id: str) -> SourceProvenance:
        """Retrieves a SourceProvenance entity by its source_id."""
        if source_id not in self._provenances:
            raise EntityNotFoundError("SourceProvenance", source_id)
        return self._provenances[source_id]

    # ------------------------------------------------------------------------
    # Bulk Listing Operations (Deterministic Canonical Sorting)
    # ------------------------------------------------------------------------

    def list_methods(self) -> List[MethodKnowledge]:
        """Returns all MethodKnowledge entities sorted canonically by method_id."""
        return [self._methods[k] for k in sorted(self._methods.keys())]

    def list_concepts(self) -> List[ConceptKnowledge]:
        """Returns all ConceptKnowledge entities sorted canonically by concept_id."""
        return [self._concepts[k] for k in sorted(self._concepts.keys())]

    def list_formulas(self) -> List[FormulaKnowledge]:
        """Returns all FormulaKnowledge entities sorted canonically by formula_id."""
        return [self._formulas[k] for k in sorted(self._formulas.keys())]

    def list_theorems(self) -> List[TheoremKnowledge]:
        """Returns all TheoremKnowledge entities sorted canonically by theorem_id."""
        return [self._theorems[k] for k in sorted(self._theorems.keys())]

    def list_provenances(self) -> List[SourceProvenance]:
        """Returns all SourceProvenance entities sorted canonically by source_id."""
        return [self._provenances[k] for k in sorted(self._provenances.keys())]

    # ------------------------------------------------------------------------
    # Metadata & Statistics
    # ------------------------------------------------------------------------

    def get_dataset_content_hash(self) -> str:
        """Returns the deterministic SHA-256 content hash of the underlying dataset."""
        if self._cached_content_hash is None:
            self._cached_content_hash = compute_dataset_content_hash(self._data_dir)
        return self._cached_content_hash

    def get_entity_counts(self) -> Dict[str, int]:
        """Returns exact counts for all indexed entity categories."""
        return {
            "methods": len(self._methods),
            "concepts": len(self._concepts),
            "formulas": len(self._formulas),
            "theorems": len(self._theorems),
            "provenances": len(self._provenances),
        }

    # ------------------------------------------------------------------------
    # Concept Prerequisite Traversal & Ordering
    # ------------------------------------------------------------------------

    def get_direct_prerequisites(self, concept_id: str) -> List[ConceptKnowledge]:
        """Returns direct prerequisite concepts for a given concept_id."""
        target = self.get_concept(concept_id)
        return [self.get_concept(pid) for pid in target.prerequisite_concept_ids]

    def get_transitive_prerequisites(self, concept_id: str) -> List[ConceptKnowledge]:
        """Returns all transitive prerequisite concepts in topological dependency order.

        Parameters
        ----------
        concept_id:
            Target concept identifier.

        Returns
        -------
        List[ConceptKnowledge]:
            Ordered list of prerequisite concepts where dependencies appear before dependents.
        """
        self.get_concept(concept_id)  # Validate existence
        visited: Set[str] = set()
        visiting: Set[str] = set()
        ordered_ids: List[str] = []

        def dfs(cid: str) -> None:
            visiting.add(cid)
            concept = self.get_concept(cid)
            # Sort prerequisite IDs for deterministic traversal order
            for prereq_id in sorted(concept.prerequisite_concept_ids):
                if prereq_id in visiting:
                    raise PrerequisiteCycleError(
                        f"Prerequisite cycle detected involving '{cid}' and '{prereq_id}'."
                    )
                if prereq_id not in visited:
                    dfs(prereq_id)
            visiting.remove(cid)
            if cid not in visited and cid != concept_id:
                visited.add(cid)
                ordered_ids.append(cid)

        dfs(concept_id)
        return [self.get_concept(cid) for cid in ordered_ids]

    def get_topological_prerequisite_order(self) -> List[ConceptKnowledge]:
        """Computes a deterministic topological learning order across all concepts.

        Uses Kahn's algorithm with lexicographical priority queueing to guarantee
        that every prerequisite appears strictly before any dependent concept,
        and that identical datasets produce byte-for-byte identical orderings.
        """
        all_concepts = self.list_concepts()
        all_ids = sorted([c.concept_id for c in all_concepts])

        # Graph representation: prereq -> list of dependent concepts
        in_degree: Dict[str, int] = {cid: 0 for cid in all_ids}
        dependents: Dict[str, List[str]] = {cid: [] for cid in all_ids}

        for concept in all_concepts:
            for prereq_id in concept.prerequisite_concept_ids:
                if prereq_id not in self._concepts:
                    raise EntityNotFoundError("ConceptKnowledge", prereq_id)
                dependents[prereq_id].append(concept.concept_id)
                in_degree[concept.concept_id] += 1

        # Zero in-degree queue with deterministic sorting
        zero_in_degree = [cid for cid in all_ids if in_degree[cid] == 0]
        zero_in_degree.sort()

        topological_order: List[str] = []

        while zero_in_degree:
            curr = zero_in_degree.pop(0)
            topological_order.append(curr)

            # Sort dependents for deterministic insertion
            for dependent_id in sorted(dependents[curr]):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    zero_in_degree.append(dependent_id)
                    zero_in_degree.sort()

        if len(topological_order) != len(all_ids):
            unresolved = [cid for cid in all_ids if cid not in topological_order]
            raise PrerequisiteCycleError(
                f"Cycle detected in concept prerequisites; unresolved concepts: {unresolved}"
            )

        return [self.get_concept(cid) for cid in topological_order]
