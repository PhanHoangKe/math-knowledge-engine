"""Tests for MethodKnowledgeRepository and SQLite indexer."""

import pytest
from pathlib import Path

from mke.knowledge.repository import MethodKnowledgeRepository
from mke.models.enums import MethodId


def test_repository_list_and_get_methods():
    """Verify loading and retrieving method templates."""
    repo = MethodKnowledgeRepository()
    methods = repo.list_methods()
    assert len(methods) == 5
    m1 = repo.get_method("M1:LINEAR_EQUATION")
    assert m1 is not None
    assert m1.method_id == MethodId.M1_LINEAR_EQUATION
    assert m1.name_en == "Linear Equation Isolation Method"


def test_repository_list_and_get_families():
    """Verify loading and retrieving seed families."""
    repo = MethodKnowledgeRepository()
    families = repo.list_families()
    assert len(families) == 15
    fam_04 = repo.get_family("FAM_04_QUAD_TWO_ROOTS")
    assert fam_04 is not None
    assert fam_04.split_group_id == "SG_QUAD_RAT_TRANSFER"


def test_repository_list_and_get_problems():
    """Verify loading and querying problem records."""
    repo = MethodKnowledgeRepository()
    problems = repo.list_problems()
    assert len(problems) == 41

    fam01_probs = repo.list_problems(family_id="FAM_01_LIN_BASIC")
    assert len(fam01_probs) == 3

    p01 = repo.get_problem("PROB_FAM01_V01")
    assert p01 is not None
    assert p01.original_expression == "2*x + 4 = 0"
    assert p01.expected_roots == ["-2"]


def test_repository_annotations_and_transfer_pairs():
    """Verify retrieving annotations and transfer pairs."""
    repo = MethodKnowledgeRepository()
    anns = repo.get_annotations_for_problem("PROB_FAM01_V01")
    assert len(anns) >= 1
    assert anns[0].method_id == MethodId.M1_LINEAR_EQUATION

    pairs = repo.list_transfer_pairs()
    assert len(pairs) == 4

    p_pairs = repo.get_transfer_pairs_for_problem("PROB_FAM04_V01")
    assert len(p_pairs) >= 1


def test_sqlite_indexer_deterministic_rebuild(tmp_path):
    """Verify SQLite indexer rebuilds deterministically."""
    db_file = tmp_path / "test_mke_kb.db"
    repo = MethodKnowledgeRepository(db_path=db_file)
    counts = repo.rebuild_index()

    assert counts["methods"] == 5
    assert counts["families"] == 15
    assert counts["problems"] == 41
    assert counts["annotations"] == 43
    assert counts["transfer_pairs"] == 4

    # Query from the newly built SQLite database
    methods = repo.list_methods()
    assert len(methods) == 5
