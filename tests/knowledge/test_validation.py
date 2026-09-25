"""Tests for KnowledgeBaseValidator integrity checks."""

import pytest
import tempfile
from pathlib import Path

from mke.knowledge.validator import KnowledgeBaseValidator


def test_validator_on_production_data():
    """Verify production data passes all validator checks with 0 errors."""
    validator = KnowledgeBaseValidator()
    report = validator.validate_all()

    assert report.is_valid is True
    assert report.total_errors == 0
    assert report.stats["methods_count"] == 5
    assert report.stats["families_count"] == 15
    assert report.stats["problems_count"] == 41
    assert report.stats["annotations_count"] == 43
    assert report.stats["transfer_pairs_count"] == 4


def test_validator_detects_missing_file(tmp_path):
    """Verify validator flags error when files are missing."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    validator = KnowledgeBaseValidator(base_dir=empty_dir)
    report = validator.validate_all()

    assert report.is_valid is False
    assert report.total_errors > 0
    error_cats = [i.category for i in report.issues if i.severity == "ERROR"]
    assert "FILE_MISSING" in error_cats


def test_validator_detects_broken_foreign_key(tmp_path):
    """Verify validator flags invalid foreign key references."""
    # Create valid methods
    k_dir = tmp_path / "data" / "knowledge"
    d_dir = tmp_path / "data" / "dev_pilot"
    k_dir.mkdir(parents=True)
    d_dir.mkdir(parents=True)

    # Copy real methods
    real_validator = KnowledgeBaseValidator()
    import shutil
    shutil.copyfile(real_validator.methods_file, k_dir / "methods.jsonl")

    # Write problem referencing non-existent family
    prob_line = (
        '{"problem_id":"PROB_INVALID_01","family_id":"FAM_NON_EXISTENT",'
        '"variant_id":"V01","split":"DEV","original_expression":"x=0",'
        '"canonical_representation":"x = 0","raw_ast":{},"domain_str":"R",'
        '"excluded_points":[],"equation_class":"LINEAR","near_miss_category":"POSITIVE",'
        '"expected_roots":["0"],"is_identity_on_domain":false,"is_empty_domain":false,'
        '"provenance":"TEST","license_status":"CC-BY-4.0","review_status":"PROVISIONAL"}\n'
    )
    with open(d_dir / "problems.jsonl", "w", encoding="utf-8") as f:
        f.write(prob_line)

    with open(d_dir / "families.jsonl", "w", encoding="utf-8") as f:
        f.write("")
    with open(d_dir / "annotations.jsonl", "w", encoding="utf-8") as f:
        f.write("")
    with open(d_dir / "transfer_pairs.jsonl", "w", encoding="utf-8") as f:
        f.write("")

    val = KnowledgeBaseValidator(base_dir=tmp_path)
    res = val.validate_all()
    assert res.is_valid is False
    err_cats = [i.category for i in res.issues if i.severity == "ERROR"]
    assert "BROKEN_REFERENCE" in err_cats
