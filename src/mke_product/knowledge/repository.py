"""MKE MVP V1 — In-Memory Knowledge Repository.

Provides O(1) indexed lookups, immutability guarantees, defensive copying,
referential-integrity validation, and deterministic prerequisite traversal
over the accepted MKE S3 pedagogical knowledge dataset.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
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
            m.method_id: m.model_copy(deep=True) for m in raw_dataset["methods"]
        }
        self._concepts: Dict[str, ConceptKnowledge] = {
            c.concept_id: c.model_copy(deep=True) for c in raw_dataset["concepts"]
        }
        self._formulas: Dict[str, FormulaKnowledge] = {
            f.formula_id: f.model_copy(deep=True) for f in raw_dataset["formulas"]
        }
        self._theorems: Dict[str, TheoremKnowledge] = {
            t.theorem_id: t.model_copy(deep=True) for t in raw_dataset["theorems"]
        }
        self._provenances: Dict[str, SourceProvenance] = {
            p.source_id: p.model_copy(deep=True) for p in raw_dataset["provenances"]
        }

        self._data_dir = data_dir
        if data_dir is not None or dataset is None:
            self._cached_content_hash: Optional[str] = compute_dataset_content_hash(data_dir)
        else:
            self._cached_content_hash = self._compute_in_memory_hash()

        # Validate prerequisite acyclicity on initialization
        self.get_topological_prerequisite_order()

    def _validate_custom_dataset(self, dataset: Any) -> None:
        """Strictly validates custom/injected dataset shape, model types, duplicate keys, and foreign-key integrity."""
        # 1. Shape and mapping validation
        if not isinstance(dataset, Mapping):
            raise KnowledgeRepositoryError(
                f"Custom dataset must be a mapping/dict, got {type(dataset).__name__}."
            )

        expected_categories = {
            "provenances": (SourceProvenance, "source_id"),
            "formulas": (FormulaKnowledge, "formula_id"),
            "theorems": (TheoremKnowledge, "theorem_id"),
            "concepts": (ConceptKnowledge, "concept_id"),
            "methods": (MethodKnowledge, "method_id"),
        }

        dataset_keys = set(dataset.keys())
        missing_categories = set(expected_categories.keys()) - dataset_keys
        if missing_categories:
            raise KnowledgeRepositoryError(
                f"Custom dataset is missing required categories: {sorted(missing_categories)}."
            )

        unexpected_categories = dataset_keys - set(expected_categories.keys())
        if unexpected_categories:
            raise KnowledgeRepositoryError(
                f"Custom dataset contains unexpected categories: {sorted(unexpected_categories)}."
            )

        # 2. Collection types and item model types validation
        id_sets: Dict[str, Set[str]] = {}
        for cat_name, (expected_cls, id_field) in expected_categories.items():
            collection = dataset[cat_name]
            if not isinstance(collection, list):
                raise KnowledgeRepositoryError(
                    f"Category '{cat_name}' must be a list, got {type(collection).__name__}."
                )

            seen_ids: Set[str] = set()
            for idx, item in enumerate(collection):
                if not isinstance(item, expected_cls):
                    raise KnowledgeRepositoryError(
                        f"Item at index {idx} in category '{cat_name}' must be an instance of {expected_cls.__name__}, got {type(item).__name__}."
                    )
                eid = getattr(item, id_field)
                if eid in seen_ids:
                    raise KnowledgeRepositoryError(
                        f"Duplicate entity ID '{eid}' found in custom dataset category '{cat_name}'."
                    )
                seen_ids.add(eid)

            id_sets[cat_name] = seen_ids

        # 3. Complete Foreign-Key Integrity Matrix
        # 3a. FormulaKnowledge
        for f in dataset["formulas"]:
            for pref in f.provenance_refs:
                if pref not in id_sets["provenances"]:
                    raise KnowledgeRepositoryError(
                        f"Formula '{f.formula_id}' references missing provenance '{pref}'."
                    )
            for cid in f.related_concept_ids:
                if cid not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Formula '{f.formula_id}' references missing concept '{cid}'."
                    )

        # 3b. TheoremKnowledge
        for t in dataset["theorems"]:
            for pref in t.provenance_refs:
                if pref not in id_sets["provenances"]:
                    raise KnowledgeRepositoryError(
                        f"Theorem '{t.theorem_id}' references missing provenance '{pref}'."
                    )
            for cid in t.related_concept_ids:
                if cid not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Theorem '{t.theorem_id}' references missing concept '{cid}'."
                    )

        # 3c. ConceptKnowledge
        for c in dataset["concepts"]:
            for pref in c.provenance_refs:
                if pref not in id_sets["provenances"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing provenance '{pref}'."
                    )
            for pid in c.prerequisite_concept_ids:
                if pid not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing prerequisite concept '{pid}'."
                    )
            for rcid in c.related_concept_ids:
                if rcid not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing related concept '{rcid}'."
                    )
            for fid in c.formula_refs:
                if fid not in id_sets["formulas"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing formula '{fid}'."
                    )
            for mid in c.method_refs:
                if mid not in id_sets["methods"]:
                    raise KnowledgeRepositoryError(
                        f"Concept '{c.concept_id}' references missing method '{mid}'."
                    )

        # 3d. MethodKnowledge
        for m in dataset["methods"]:
            for pref in m.provenance_refs:
                if pref not in id_sets["provenances"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing provenance '{pref}'."
                    )
            for pid in m.prerequisite_concept_ids:
                if pid not in id_sets["concepts"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing prerequisite concept '{pid}'."
                    )
            for fid in m.formula_refs:
                if fid not in id_sets["formulas"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing formula '{fid}'."
                    )
            for tid in m.theorem_refs:
                if tid not in id_sets["theorems"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing theorem '{tid}'."
                    )
            for rmid in m.related_method_ids:
                if rmid not in id_sets["methods"]:
                    raise KnowledgeRepositoryError(
                        f"Method '{m.method_id}' references missing related method '{rmid}'."
                    )

    def _compute_in_memory_hash(self) -> str:
        """Computes a deterministic unkeyed SHA-256 digest over in-memory entities matching production loader semantics."""
        logical_files = {
            "concepts.json": [c.model_dump(mode="json") for c in sorted(self._concepts.values(), key=lambda x: x.concept_id)],
            "formulas.json": [f.model_dump(mode="json") for f in sorted(self._formulas.values(), key=lambda x: x.formula_id)],
            "methods.json": [m.model_dump(mode="json") for m in sorted(self._methods.values(), key=lambda x: x.method_id)],
            "provenance.json": [p.model_dump(mode="json") for p in sorted(self._provenances.values(), key=lambda x: x.source_id)],
            "theorems.json": [t.model_dump(mode="json") for t in sorted(self._theorems.values(), key=lambda x: x.theorem_id)],
        }
        target_files = sorted(["concepts.json", "formulas.json", "methods.json", "provenance.json", "theorems.json"])
        hasher = hashlib.sha256()

        for filename in target_files:
            data = logical_files[filename]
            canonical_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            hasher.update(filename.encode("utf-8"))
            hasher.update(canonical_bytes)

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
