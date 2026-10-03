"""MKE MVP V1 — Milestone K1 Knowledge Loader & Referential Integrity Validator.

Provides deterministic static loaders, schema validation, cross-entity referential
integrity checks, relation subset invariants, and combined content hashing for the
MKE K1 Quick Tips and Related Problem Forms pedagogical knowledge dataset.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import TypeAdapter

from mke_product.knowledge.k1_schemas import (
    KnowledgeEntityStatus,
    QuickTipKnowledge,
    RelatedProblemFormKnowledge,
)
from mke_product.knowledge.loader import (
    DEFAULT_DATA_DIR,
    _read_json_bytes,
    _read_json_file,
    load_concepts,
    load_formulas,
    load_methods,
    load_provenances,
    load_theorems,
    validate_knowledge_dataset,
)

_QUICK_TIP_LIST_ADAPTER = TypeAdapter(List[QuickTipKnowledge])
_PROBLEM_FORM_LIST_ADAPTER = TypeAdapter(List[RelatedProblemFormKnowledge])


def load_quick_tips(data_dir: Optional[Path] = None) -> List[QuickTipKnowledge]:
    """Loads and strictly validates all quick solving tip definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_bytes = _read_json_bytes(directory / "tips.json")
    return _QUICK_TIP_LIST_ADAPTER.validate_json(raw_bytes)


def load_problem_forms(data_dir: Optional[Path] = None) -> List[RelatedProblemFormKnowledge]:
    """Loads and strictly validates all related problem form definitions."""
    directory = data_dir or DEFAULT_DATA_DIR
    raw_bytes = _read_json_bytes(directory / "problem_forms.json")
    return _PROBLEM_FORM_LIST_ADAPTER.validate_json(raw_bytes)


def load_k1_knowledge_dataset(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Loads the complete combined S3 + K1 knowledge dataset into a validated mapping."""
    directory = data_dir or DEFAULT_DATA_DIR
    dataset = {
        "provenances": load_provenances(directory),
        "formulas": load_formulas(directory),
        "theorems": load_theorems(directory),
        "concepts": load_concepts(directory),
        "methods": load_methods(directory),
        "tips": load_quick_tips(directory),
        "problem_forms": load_problem_forms(directory),
    }
    validate_k1_knowledge_dataset(dataset)
    return dataset


def validate_k1_knowledge_dataset(
    dataset: Dict[str, Any],
    registry_method_ids: Optional[Set[str]] = None,
) -> None:
    """Strictly validates referential integrity and relation invariants across S3 and K1 entities.

    Parameters
    ----------
    dataset:
        Mapping containing provenances, formulas, theorems, concepts, methods, tips, and problem_forms.
    registry_method_ids:
        Optional set of expected S1 method IDs. If None, passed through to S3 validator.
    """
    # 1. First validate underlying S3 knowledge dataset invariants (provenance, concepts DAG, methods)
    validate_knowledge_dataset(dataset, registry_method_ids=registry_method_ids)

    provenances = dataset["provenances"]
    formulas = dataset["formulas"]
    theorems = dataset["theorems"]
    concepts = dataset["concepts"]
    methods = dataset["methods"]
    tips: List[QuickTipKnowledge] = dataset["tips"]
    problem_forms: List[RelatedProblemFormKnowledge] = dataset["problem_forms"]

    # Build lookup dictionaries and sets
    prov_map = {p.source_id: p for p in provenances}
    form_id_set = {f.formula_id for f in formulas}
    thm_id_set = {t.theorem_id for t in theorems}
    concept_id_set = {c.concept_id for c in concepts}
    method_id_set = {m.method_id for m in methods}

    # 2. Duplicate ID validation for K1 entities
    tip_ids = [t.tip_id for t in tips]
    if len(tip_ids) != len(set(tip_ids)):
        raise ValueError(f"Duplicate tip_id found in tips dataset: {tip_ids}")
    tip_id_set = set(tip_ids)

    form_ids = [f.form_id for f in problem_forms]
    if len(form_ids) != len(set(form_ids)):
        raise ValueError(f"Duplicate form_id found in problem_forms dataset: {form_ids}")
    problem_form_id_set = set(form_ids)

    # 3. Referential integrity and provenance status for Quick Tips
    for tip in tips:
        for ref in tip.provenance_refs:
            if ref not in prov_map:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown provenance: '{ref}'")
            if tip.status == KnowledgeEntityStatus.VERIFIED and prov_map[ref].verification_status != "VERIFIED":
                raise ValueError(
                    f"VERIFIED QuickTip '{tip.tip_id}' references non-VERIFIED provenance '{ref}' "
                    f"(status: '{prov_map[ref].verification_status}')."
                )

        for ref in tip.related_method_ids:
            if ref not in method_id_set:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown method: '{ref}'")

        for ref in tip.related_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown concept: '{ref}'")

        for ref in tip.formula_refs:
            if ref not in form_id_set:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown formula: '{ref}'")

        for ref in tip.theorem_refs:
            if ref not in thm_id_set:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown theorem: '{ref}'")

        for ref in tip.related_problem_form_ids:
            if ref not in problem_form_id_set:
                raise ValueError(f"QuickTip '{tip.tip_id}' references unknown problem form: '{ref}'")

    # 4. Referential integrity, relation invariants, and example policy for Problem Forms
    for form in problem_forms:
        for ref in form.provenance_refs:
            if ref not in prov_map:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown provenance: '{ref}'")
            if form.status == KnowledgeEntityStatus.VERIFIED and prov_map[ref].verification_status != "VERIFIED":
                raise ValueError(
                    f"VERIFIED ProblemForm '{form.form_id}' references non-VERIFIED provenance '{ref}' "
                    f"(status: '{prov_map[ref].verification_status}')."
                )

        for ref in form.related_method_ids:
            if ref not in method_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown related method: '{ref}'")

        for ref in form.guaranteed_method_ids:
            if ref not in method_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown guaranteed method: '{ref}'")

        # Relation invariant: guaranteed_method_ids ⊆ related_method_ids
        rel_method_set = set(form.related_method_ids)
        for g_method in form.guaranteed_method_ids:
            if g_method not in rel_method_set:
                raise ValueError(
                    f"ProblemForm '{form.form_id}' has guaranteed_method '{g_method}' "
                    f"that is not contained in its related_method_ids."
                )

        for ref in form.related_tip_ids:
            if ref not in tip_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown related tip: '{ref}'")

        for ref in form.guaranteed_tip_ids:
            if ref not in tip_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown guaranteed tip: '{ref}'")

        # Relation invariant: guaranteed_tip_ids ⊆ related_tip_ids
        rel_tip_set = set(form.related_tip_ids)
        for g_tip in form.guaranteed_tip_ids:
            if g_tip not in rel_tip_set:
                raise ValueError(
                    f"ProblemForm '{form.form_id}' has guaranteed_tip '{g_tip}' "
                    f"that is not contained in its related_tip_ids."
                )

        for ref in form.prerequisite_concept_ids:
            if ref not in concept_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown prerequisite concept: '{ref}'")

        for ref in form.formula_refs:
            if ref not in form_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown formula: '{ref}'")

        for ref in form.theorem_refs:
            if ref not in thm_id_set:
                raise ValueError(f"ProblemForm '{form.form_id}' references unknown theorem: '{ref}'")

        # Empty example reference enforcement policy (deferred to Example Registry milestone)
        if len(form.worked_example_ids) > 0:
            raise ValueError(
                f"ProblemForm '{form.form_id}' contains worked_example_ids: {form.worked_example_ids}. "
                "Worked examples must be empty in K1-02 dataset."
            )
        if len(form.practice_example_ids) > 0:
            raise ValueError(
                f"ProblemForm '{form.form_id}' contains practice_example_ids: {form.practice_example_ids}. "
                "Practice examples must be empty in K1-02 dataset."
            )


def compute_k1_dataset_content_hash(data_dir: Optional[Path] = None) -> str:
    """Computes a deterministic unkeyed SHA-256 digest over the combined S3 + K1 canonical JSON dataset files."""
    directory = data_dir or DEFAULT_DATA_DIR
    target_files = sorted([
        "concepts.json",
        "formulas.json",
        "methods.json",
        "problem_forms.json",
        "provenance.json",
        "theorems.json",
        "tips.json",
    ])
    hasher = hashlib.sha256()

    for filename in target_files:
        file_path = directory / filename
        data = _read_json_file(file_path)
        # Canonical compact deterministic JSON bytes
        canonical_bytes = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        hasher.update(filename.encode("utf-8"))
        hasher.update(canonical_bytes)

    return hasher.hexdigest()
