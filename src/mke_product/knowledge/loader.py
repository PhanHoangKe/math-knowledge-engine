"""MKE MVP V1 — S3 Static Knowledge Loader & Referential Integrity Validator.

Provides deterministic static loaders, validation utilities, acyclicity checks,
and content hashing for the MKE S3 pedagogical knowledge dataset.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mke_product.domain.registry import MethodRegistry
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    FormulaKnowledge,
    MethodKnowledge,
    SourceProvenance,
    TheoremKnowledge,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


def _read_json_file(path: Path) -> Any:
    """Reads and decodes a UTF-8 JSON file."""
    if not path.is_file():
        raise FileNotFoundError(f"Knowledge dataset file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_provenances(data_dir: Optional[Path] = None) -> List[SourceProvenance]:
    """Loads and validates all source provenance definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_data = _read_json_file(directory / "provenance.json")
    if not isinstance(raw_data, list):
        raise ValueError("provenance.json must contain a JSON array of objects.")
    return [SourceProvenance.model_validate(item) for item in raw_data]


def load_formulas(data_dir: Optional[Path] = None) -> List[FormulaKnowledge]:
    """Loads and validates all formula knowledge definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_data = _read_json_file(directory / "formulas.json")
    if not isinstance(raw_data, list):
        raise ValueError("formulas.json must contain a JSON array of objects.")
    return [FormulaKnowledge.model_validate(item) for item in raw_data]


def load_theorems(data_dir: Optional[Path] = None) -> List[TheoremKnowledge]:
    """Loads and validates all theorem knowledge definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_data = _read_json_file(directory / "theorems.json")
    if not isinstance(raw_data, list):
        raise ValueError("theorems.json must contain a JSON array of objects.")
    return [TheoremKnowledge.model_validate(item) for item in raw_data]


def load_concepts(data_dir: Optional[Path] = None) -> List[ConceptKnowledge]:
    """Loads and validates all concept knowledge definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_data = _read_json_file(directory / "concepts.json")
    if not isinstance(raw_data, list):
        raise ValueError("concepts.json must contain a JSON array of objects.")
    return [ConceptKnowledge.model_validate(item) for item in raw_data]


def load_methods(data_dir: Optional[Path] = None) -> List[MethodKnowledge]:
    """Loads and validates all method knowledge definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_data = _read_json_file(directory / "methods.json")
    if not isinstance(raw_data, list):
        raise ValueError("methods.json must contain a JSON array of objects.")
    return [MethodKnowledge.model_validate(item) for item in raw_data]


def load_knowledge_dataset(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Loads the complete S3 knowledge dataset into a validated mapping."""
    directory = data_dir or DEFAULT_DATA_DIR
    dataset = {
        "provenances": load_provenances(directory),
        "formulas": load_formulas(directory),
        "theorems": load_theorems(directory),
        "concepts": load_concepts(directory),
        "methods": load_methods(directory),
    }
    validate_knowledge_dataset(dataset)
    return dataset


def _check_concept_acyclicity(concepts: List[ConceptKnowledge]) -> None:
    """Verifies that concept prerequisite dependencies form a Directed Acyclic Graph (DAG)."""
    graph: Dict[str, List[str]] = {c.concept_id: c.prerequisite_concept_ids for c in concepts}
    visited: Dict[str, int] = {}  # 0 = unvisited, 1 = visiting, 2 = visited

    def dfs(node: str, path: List[str]) -> None:
        visited[node] = 1
        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue  # Foreign key integrity check handles unknown references separately
            state = visited.get(neighbor, 0)
            if state == 1:
                cycle = " -> ".join(path + [neighbor])
                raise ValueError(f"Cycle detected in concept prerequisites: {cycle}")
            if state == 0:
                dfs(neighbor, path + [neighbor])
        visited[node] = 2

    for concept_id in graph:
        if visited.get(concept_id, 0) == 0:
            dfs(concept_id, [concept_id])


def validate_knowledge_dataset(
    dataset: Dict[str, Any],
    registry_method_ids: Optional[Set[str]] = None,
) -> None:
    """Strictly validates referential integrity, duplicate avoidance, and DAG constraints.

    Parameters
    ----------
    dataset:
        Mapping containing provenances, formulas, theorems, concepts, and methods.
    registry_method_ids:
        Optional set of expected S1 method IDs. If None, loaded from MethodRegistry.
    """
    provenances: List[SourceProvenance] = dataset["provenances"]
    formulas: List[FormulaKnowledge] = dataset["formulas"]
    theorems: List[TheoremKnowledge] = dataset["theorems"]
    concepts: List[ConceptKnowledge] = dataset["concepts"]
    methods: List[MethodKnowledge] = dataset["methods"]

    # 1. Duplicate ID validation
    prov_ids = [p.source_id for p in provenances]
    if len(prov_ids) != len(set(prov_ids)):
        raise ValueError(f"Duplicate source_id found in provenances: {prov_ids}")
    prov_id_set = set(prov_ids)

    form_ids = [f.formula_id for f in formulas]
    if len(form_ids) != len(set(form_ids)):
        raise ValueError(f"Duplicate formula_id found in formulas: {form_ids}")
    form_id_set = set(form_ids)

    thm_ids = [t.theorem_id for t in theorems]
    if len(thm_ids) != len(set(thm_ids)):
        raise ValueError(f"Duplicate theorem_id found in theorems: {thm_ids}")
    thm_id_set = set(thm_ids)

    concept_ids = [c.concept_id for c in concepts]
    if len(concept_ids) != len(set(concept_ids)):
        raise ValueError(f"Duplicate concept_id found in concepts: {concept_ids}")
    concept_id_set = set(concept_ids)

    method_ids = [m.method_id for m in methods]
    if len(method_ids) != len(set(method_ids)):
        raise ValueError(f"Duplicate method_id found in methods: {method_ids}")
    method_id_set = set(method_ids)

    # 2. Method Registry 1:1 set equality validation
    if registry_method_ids is None:
        registry = MethodRegistry()
        expected_method_ids = {m.method_id for m in registry.list_all()}
    else:
        expected_method_ids = set(registry_method_ids)

    if method_id_set != expected_method_ids:
        missing = expected_method_ids - method_id_set
        extra = method_id_set - expected_method_ids
        raise ValueError(
            f"MethodKnowledge IDs do not match MethodRegistry 1:1. Missing: {missing}, Extra: {extra}"
        )

    # 3. Referential integrity: Provenances
    for entity in formulas:
        for ref in entity.provenance_refs:
            if ref not in prov_id_set:
                raise ValueError(f"Formula '{entity.formula_id}' references unknown provenance: '{ref}'")

    for entity in theorems:
        for ref in entity.provenance_refs:
            if ref not in prov_id_set:
                raise ValueError(f"Theorem '{entity.theorem_id}' references unknown provenance: '{ref}'")

    for entity in concepts:
        for ref in entity.provenance_refs:
            if ref not in prov_id_set:
                raise ValueError(f"Concept '{entity.concept_id}' references unknown provenance: '{ref}'")

    for entity in methods:
        for ref in entity.provenance_refs:
            if ref not in prov_id_set:
                raise ValueError(f"Method '{entity.method_id}' references unknown provenance: '{ref}'")

    # 4. Referential integrity: Concepts
    for entity in formulas:
        for ref in entity.related_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"Formula '{entity.formula_id}' references unknown concept: '{ref}'")

    for entity in theorems:
        for ref in entity.related_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"Theorem '{entity.theorem_id}' references unknown concept: '{ref}'")

    for entity in concepts:
        for ref in entity.prerequisite_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"Concept '{entity.concept_id}' references unknown prerequisite concept: '{ref}'")
        for ref in entity.related_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"Concept '{entity.concept_id}' references unknown related concept: '{ref}'")
        for ref in entity.formula_refs:
            if ref not in form_id_set:
                raise ValueError(f"Concept '{entity.concept_id}' references unknown formula: '{ref}'")
        for ref in entity.method_refs:
            if ref not in method_id_set:
                raise ValueError(f"Concept '{entity.concept_id}' references unknown method: '{ref}'")

    for entity in methods:
        for ref in entity.prerequisite_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"Method '{entity.method_id}' references unknown prerequisite concept: '{ref}'")
        for ref in entity.formula_refs:
            if ref not in form_id_set:
                raise ValueError(f"Method '{entity.method_id}' references unknown formula: '{ref}'")
        for ref in entity.theorem_refs:
            if ref not in thm_id_set:
                raise ValueError(f"Method '{entity.method_id}' references unknown theorem: '{ref}'")
        for ref in entity.related_method_ids:
            if ref not in method_id_set:
                raise ValueError(f"Method '{entity.method_id}' references unknown related method: '{ref}'")

    # 5. Acyclicity of concept prerequisites
    _check_concept_acyclicity(concepts)


def compute_dataset_content_hash(data_dir: Optional[Path] = None) -> str:
    """Computes a deterministic unkeyed SHA-256 digest over the canonical JSON dataset files."""
    directory = data_dir or DEFAULT_DATA_DIR
    target_files = sorted(["concepts.json", "formulas.json", "methods.json", "provenance.json", "theorems.json"])
    hasher = hashlib.sha256()

    for filename in target_files:
        file_path = directory / filename
        data = _read_json_file(file_path)
        # Canonical compact deterministic JSON bytes
        canonical_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        hasher.update(filename.encode("utf-8"))
        hasher.update(canonical_bytes)

    return hasher.hexdigest()
