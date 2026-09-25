"""Tests for Dev01Adapter connecting knowledge dataset to DEV-01 verification engine."""

import pytest
from pathlib import Path

from mke.knowledge.dev01_adapter import Dev01Adapter
from mke.knowledge.repository import MethodKnowledgeRepository


def test_adapter_evaluates_problem():
    """Verify single problem evaluation through Dev01Adapter."""
    repo = MethodKnowledgeRepository()
    adapter = Dev01Adapter(repo=repo)

    prob = repo.get_problem("PROB_FAM01_V01")
    assert prob is not None
    anns = repo.get_annotations_for_problem(prob.problem_id)
    assert len(anns) > 0

    res = adapter.evaluate_problem_method(prob, anns[0])
    assert res.verifier_is_verified_solution is True
    assert res.verifier_verified_roots == ["-2"]
    assert res.has_discrepancy is False


def test_adapter_evaluates_transfer_pair():
    """Verify transfer pair evaluation detects unsafe transfer with extraneous roots."""
    repo = MethodKnowledgeRepository()
    adapter = Dev01Adapter(repo=repo)

    pairs = repo.list_transfer_pairs()
    # Find the transfer pair from FAM04 to FAM11
    pair_f04_f11 = next(p for p in pairs if p.source_problem_id == "PROB_FAM04_V01")
    assert pair_f04_f11 is not None

    tp_res = adapter.evaluate_transfer_pair(pair_f04_f11)
    assert tp_res["audited_status"] == "UNSAFE_COPY"
    assert any("2" in r for r in tp_res["rejected_transferred_roots"])
    assert "3" in tp_res["valid_transferred_roots"]


def test_adapter_run_full_dev_validation():
    """Verify full validation produces metrics and preserves discrepancies."""
    adapter = Dev01Adapter()
    summary = adapter.validate_dataset()

    assert summary["total_problems"] == 41
    assert summary["normalizable_count"] == 41
    assert summary["solution_verified_count"] >= 35
    # Discrepancies exist for near misses and must NOT be zero (Adjustment 7: preserve discrepancies)
    assert summary["discrepancy_count"] > 0


def test_adapter_export_reports(tmp_path):
    """Verify report export generates all 5 expected artifacts."""
    adapter = Dev01Adapter()
    exported = adapter.export_reports(reports_dir=tmp_path)

    assert (tmp_path / "DEV02A_DATASET_VALIDATION.json").exists()
    assert (tmp_path / "DEV02A_ANNOTATION_REVIEW.csv").exists()
    assert (tmp_path / "DEV02A_DISCREPANCIES.json").exists()
    assert (tmp_path / "DEV02A_DATASET_MANIFEST.json").exists()
    assert (tmp_path / "SHA256SUMS.txt").exists()
