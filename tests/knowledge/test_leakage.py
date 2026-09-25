"""Tests for Data Leakage Prevention and Split Isolation policies."""

import pytest
from pathlib import Path

from mke.models.enums import Split
from mke.knowledge.repository import MethodKnowledgeRepository
from mke.knowledge.validator import KnowledgeBaseValidator


def test_zero_leakage_100_percent_dev_split():
    """Verify strictly 100% of DEV_PILOT records are in DEV split."""
    repo = MethodKnowledgeRepository()
    problems = repo.list_problems()

    assert len(problems) > 0
    for p in problems:
        assert p.split == Split.DEV, f"Problem {p.problem_id} has forbidden split: {p.split}"


def test_split_group_integrity_dependent_families():
    """Verify families with dependency links share the same split_group_id."""
    repo = MethodKnowledgeRepository()
    families = repo.list_families()
    fam_map = {f.family_id: f for f in families}

    for f in families:
        for dep_id in f.dependent_family_ids:
            assert dep_id in fam_map, f"Missing dependent family: {dep_id}"
            dep_fam = fam_map[dep_id]
            assert f.split_group_id == dep_fam.split_group_id, (
                f"Split group mismatch between {f.family_id} ({f.split_group_id}) "
                f"and dependent {dep_id} ({dep_fam.split_group_id})"
            )


def test_split_group_integrity_transfer_pairs():
    """Verify source and target families of transfer pairs share the same split_group_id."""
    repo = MethodKnowledgeRepository()
    pairs = repo.list_transfer_pairs()
    families = {f.family_id: f for f in repo.list_families()}
    problems = {p.problem_id: p for p in repo.list_problems()}

    for tp in pairs:
        src_prob = problems[tp.source_problem_id]
        tgt_prob = problems[tp.target_problem_id]
        src_fam = families[src_prob.family_id]
        tgt_fam = families[tgt_prob.family_id]

        assert src_fam.split_group_id == tgt_fam.split_group_id, (
            f"Transfer pair {tp.pair_id} crosses split groups: "
            f"source {src_fam.family_id} ({src_fam.split_group_id}) vs "
            f"target {tgt_fam.family_id} ({tgt_fam.split_group_id})"
        )


def test_validator_flags_non_dev_split_violation(tmp_path):
    """Verify validator flags any record with TEST or VALIDATION split as a critical error."""
    k_dir = tmp_path / "data" / "knowledge"
    d_dir = tmp_path / "data" / "dev_pilot"
    k_dir.mkdir(parents=True)
    d_dir.mkdir(parents=True)

    real_validator = KnowledgeBaseValidator()
    import shutil
    shutil.copyfile(real_validator.methods_file, k_dir / "methods.jsonl")
    shutil.copyfile(real_validator.families_file, d_dir / "families.jsonl")

    # Inject a problem with split = TEST
    bad_prob = (
        '{"problem_id":"PROB_LEAKED_01","family_id":"FAM_01_LIN_BASIC",'
        '"variant_id":"V99","split":"TEST","original_expression":"x=0",'
        '"canonical_representation":"x = 0","raw_ast":{},"domain_str":"R",'
        '"excluded_points":[],"equation_class":"LINEAR","near_miss_category":"POSITIVE",'
        '"expected_roots":["0"],"is_identity_on_domain":false,"is_empty_domain":false,'
        '"provenance":"TEST","license_status":"CC-BY-4.0","review_status":"PROVISIONAL"}\n'
    )
    with open(d_dir / "problems.jsonl", "w", encoding="utf-8") as f:
        f.write(bad_prob)
    with open(d_dir / "annotations.jsonl", "w", encoding="utf-8") as f:
        f.write("")
    with open(d_dir / "transfer_pairs.jsonl", "w", encoding="utf-8") as f:
        f.write("")

    val = KnowledgeBaseValidator(base_dir=tmp_path)
    res = val.validate_all()
    assert res.is_valid is False
    err_cats = [i.category for i in res.issues if i.severity == "ERROR"]
    assert "UNAPPROVED_SPLIT" in err_cats
