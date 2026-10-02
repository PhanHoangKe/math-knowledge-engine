"""MKE MVP V1 — In-Memory Knowledge Repository.

Provides O(1) indexed lookups, immutability guarantees, defensive copying,
referential-integrity validation, and deterministic prerequisite traversal
over the accepted MKE S3 pedagogical knowledge dataset.
"""

from __future__ import annotations

import hashlib
import json
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
            self._validate_custom_dataset(raw_dataset)
        else:
            raw_dataset = load_knowledge_dataset(data_dir)

        # Build defensive copies for internal storage to prevent outer object mutation
        self._methods: Dict[str, MethodKnowledge] = {
            m.method_id: m.model_copy(deep=True) for m in raw_dataset.get("methods", [])
        }
        self._concepts: Dict[str, ConceptKnowledge] = {
            c.concept_id: c.model_copy(deep=True) for c in raw_dataset.get("concepts", [])
        }
        self._formulas: Dict[str, FormulaKnowledge] = {
            f.formula_id: f.model_copy(deep=True) for f in raw_dataset.get("formulas", [])
        }
        self._theorems: Dict[str, TheoremKnowledge] = {
            t.theorem_id: t.model_copy(deep=True) for t in raw_dataset.get("theorems", [])
        }
        self._provenances: Dict[str, SourceProvenance] = {
            p.source_id: p.model_copy(deep=True) for p in raw_dataset.get("provenances", [])
        }

        self._data_dir = data_dir
        if data_dir is not None or dataset is None:
            self._cached_content_hash: Optional[str] = compute_dataset_content_hash(data_dir)
        else:
            self._cached_content_hash = self._compute_in_memory_hash()

        # Validate prerequisite acyclicity on initialization
        self.get_topological_prerequisite_order()

    def _validate_custom_dataset(self, dataset: Dict[str, Any]) -> None:
        """Validates duplicate keys and referential integrity for custom injected datasets."""
        # 1. Duplicate ID validation
        categories = [
            ("provenances", "source_id"),
            ("formulas", "formula_id"),
            ("theorems", "theorem_id"),
            ("concepts", "concept_id"),
            ("methods", "method_id"),
        ]
        id_sets: Dict[str, Set[str]] = {}
        for cat_name, id_field in categories:
            items = dataset.get(cat_name, [])
            seen: Set[str] = set()
            for item in items:
                eid = getattr(item, id_field)
                if eid in seen:
                    raise KnowledgeRepositoryError(
                        f"Duplicate entity ID '{eid}' found in custom dataset category '{cat_name}'."
                    )
                seen.add(eid)
            id_sets[cat_name] = seen

        # 2. Referential integrity validation
        # Provenance refs
        for cat_name, items in [
            ("concepts", dataset.get("concepts", [])),
            ("methods", dataset.get("methods", [])),
            ("formulas", dataset.get("formulas", [])),
            ("theorems", dataset.get("theorems", [])),
        ]:
            for item in items:
                for pref in getattr(item, "provenance_refs", []):
                    if pref not in id_sets["provenances"]:
                        raise KnowledgeRepositoryError(
                            f"Entity '{getattr(item, cat_name[:-1] + '_id')}' references missing provenance '{pref}'."
                        )

        # Concept prerequisites & related concepts
        for c in dataset.get("concepts", []):
            for prereq_id in c.prerequisite_concept_ids:
                if prereq_id not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing prerequisite concept '{prereq_id}'."
                    )
            for rel_id in c.related_concept_ids:
                if rel_id not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing related concept '{rel_id}'."
                    )

        # Method prerequisites, formulas, theorems, related methods
        for m in dataset.get("methods", []):
            for prereq_id in m.prerequisite_concept_ids:
                if prereq_id not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing prerequisite concept '{prereq_id}'."
                    )
            for f_id in m.formula_refs:
                if f_id not in id_sets["formulas"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing formula '{f_id}'."
                    )
            for t_id in m.theorem_refs:
                if t_id not in id_sets["theorems"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing theorem '{t_id}'."
                    )
            for rel_m_id in m.related_method_ids:
                if rel_m_id not in id_sets["methods"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing related method '{rel_m_id}'."
                    )

        # Theorem related formulas
        for t in dataset.get("theorems", []):
            for f_id in t.related_formula_refs:
                if f_id not in id_sets["formulas"]:
                    raise KnowledgeRepositoryError(
                        f"Theorem '{t.theorem_id}' references missing related formula '{f_id}'."
                    )

    def _compute_in_memory_hash(self) -> str:
        """Computes a deterministic SHA-256 hash across in-memory entities."""
        hasher = hashlib.sha256()
        canonical_data = {
            "provenances": [p.model_dump(mode="json") for p in sorted(self._provenances.values(), key=lambda x: x.source_id)],
            "formulas": [f.model_dump(mode="json") for f in sorted(self._formulas.values(), key=lambda x: x.formula_id)],
            "theorems": [t.model_dump(mode="json") for t in sorted(self._theorems.values(), key=lambda x: x.theorem_id)],
            "concepts": [c.model_dump(mode="json") for c in sorted(self._concepts.values(), key=lambda x: x.concept_id)],
            "methods": [m.model_dump(mode="json") for m in sorted(self._methods.values(), key=lambda x: x.method_id)],
        }
        encoded = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        hasher.update(encoded)
        return hasher.hexdigest()

    # ------------------------------------------------------------------------
    # Indexed Single-Entity Lookups (O(1)) with Defensive Copying
    # ------------------------------------------------------------------------

    def get_method(self, method_id: str) -> MethodKnowledge:
        """Retrieves a MethodKnowledge entity by its canonical method_id."""
        if method_id not in self._methods:
            raise EntityNotFoundError("MethodKnowledge", method_id)
        return self._methods[method_id].model_copy(deep=True)

    def get_concept(self, concept_id: str) -> ConceptKnowledge:
        """Retrieves a ConceptKnowledge entity by its concept_id."""
        if concept_id not in self._concepts:
            raise EntityNotFoundError("ConceptKnowledge", concept_id)
        return self._concepts[concept_id].model_copy(deep=True)

    def get_formula(self, formula_id: str) -> FormulaKnowledge:
        """Retrieves a FormulaKnowledge entity by its formula_id."""
        if formula_id not in self._formulas:
            raise EntityNotFoundError("FormulaKnowledge", formula_id)
        return self._formulas[formula_id].model_copy(deep=True)

    def get_theorem(self, theorem_id: str) -> TheoremKnowledge:
        """Retrieves a TheoremKnowledge entity by its theorem_id."""
        if theorem_id not in self._theorems:
            raise EntityNotFoundError("TheoremKnowledge", theorem_id)
        return self._theorems[theorem_id].model_copy(deep=True)

    def get_provenance(self, source_id: str) -> SourceProvenance:
        """Retrieves a SourceProvenance entity by its source_id."""
        if source_id not in self._provenances:
            raise EntityNotFoundError("SourceProvenance", source_id)
        return self._provenances[source_id].model_copy(deep=True)

    # ------------------------------------------------------------------------
    # Bulk Listing Operations (Deterministic Canonical Sorting)
    # ------------------------------------------------------------------------

    def list_methods(self) -> List[MethodKnowledge]:
        """Returns all MethodKnowledge entities sorted canonically by method_id."""
        return [self._methods[k].model_copy(deep=True) for k in sorted(self._methods.keys())]

    def list_concepts(self) -> List[ConceptKnowledge]:
        """Returns all ConceptKnowledge entities sorted canonically by concept_id."""
        return [self._concepts[k].model_copy(deep=True) for k in sorted(self._concepts.keys())]

    def list_formulas(self) -> List[FormulaKnowledge]:
        """Returns all FormulaKnowledge entities sorted canonically by formula_id."""
        return [self._formulas[k].model_copy(deep=True) for k in sorted(self._formulas.keys())]

    def list_theorems(self) -> List[TheoremKnowledge]:
        """Returns all TheoremKnowledge entities sorted canonically by theorem_id."""
        return [self._theorems[k].model_copy(deep=True) for k in sorted(self._theorems.keys())]

    def list_provenances(self) -> List[SourceProvenance]:
        """Returns all SourceProvenance entities sorted canonically by source_id."""
        return [self._provenances[k].model_copy(deep=True) for k in sorted(self._provenances.keys())]

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
            concept = self._concepts[cid]
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
