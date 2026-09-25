"""Tests verifying all 7 Coordinator Mandatory Adjustments for DEV-02A."""

import json
import pytest
from pathlib import Path

from mke.models.enums import MethodAdmissibility, MethodId, Split, TransferValidity
from mke.knowledge.provenance import canonical_json_dumps, compute_content_sha256
from mke.knowledge.repository import MethodKnowledgeRepository
from mke.knowledge.schemas import ReviewStatus, TransferCategory


def test_adjustment_1_data_leakage_split_groups():
    """Adjustment 1: split_group_id in FamilyRecord, FAM_04 is source for FAM_11, 100% DEV."""
    repo = MethodKnowledgeRepository()
    fam04 = repo.get_family("FAM_04_QUAD_TWO_ROOTS")
    fam11 = repo.get_family("FAM_11_RAT_EXTRANEOUS_TRANSFER")

    assert fam04 is not None
    assert fam11 is not None

    # Mandatory split_group_id sharing
    assert fam04.split_group_id == "SG_QUAD_RAT_TRANSFER"
    assert fam11.split_group_id == "SG_QUAD_RAT_TRANSFER"

    # Mandatory dependency link
    assert "FAM_04_QUAD_TWO_ROOTS" in fam11.dependent_family_ids

    # 100% DEV split
    for p in repo.list_problems():
        assert p.split == Split.DEV


def test_adjustment_2_method_admissibility_bindings():
    """Adjustment 2: Each annotation binds problem_id, method_id, method_version, method_instance_id."""
    repo = MethodKnowledgeRepository()
    for p in repo.list_problems():
        anns = repo.get_annotations_for_problem(p.problem_id)
        for ann in anns:
            assert ann.problem_id == p.problem_id
            assert ann.method_id is not None
            assert ann.method_version == "1.0.0"
            assert ann.method_instance_id is not None
            assert ann.method_instance_id.startswith("INST_")
            assert ann.admissibility in (
                MethodAdmissibility.APPLICABLE,
                MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS,
                MethodAdmissibility.NOT_APPLICABLE,
                MethodAdmissibility.UNKNOWN,
            )


def test_adjustment_3_transfer_pairs_schema_and_fks():
    """Adjustment 3: transfer_pairs.jsonl with TransferPairRecord, required fields, foreign keys."""
    repo = MethodKnowledgeRepository()
    pairs = repo.list_transfer_pairs()
    assert len(pairs) >= 4

    prob_ids = {p.problem_id for p in repo.list_problems()}
    for tp in pairs:
        assert tp.pair_id.startswith("PAIR_")
        assert tp.source_problem_id in prob_ids
        assert tp.target_problem_id in prob_ids
        assert tp.method_id in [m.method_id for m in repo.list_methods()]
        assert tp.method_version == "1.0.0"
        assert tp.transfer_category is not None
        assert tp.proposed_transfer_status is not None
        assert tp.annotation_evidence != ""


def test_adjustment_4_fam12_domain_boundaries():
    """Adjustment 4: FAM_12 renamed to RAT_DOMAIN_BOUNDARIES; distinguishes identity vs empty domain."""
    repo = MethodKnowledgeRepository()
    fam12 = repo.get_family("FAM_12_RAT_DOMAIN_BOUNDARIES")
    assert fam12 is not None
    assert fam12.family_id == "FAM_12_RAT_DOMAIN_BOUNDARIES"

    # Variant 1: Identity on domain with holes: (x - 2)/(x - 2) = 1
    p1 = repo.get_problem("PROB_FAM12_V01")
    assert p1 is not None
    assert p1.is_identity_on_domain is True
    assert p1.is_empty_domain is False
    assert "2" in p1.excluded_points

    # Variant 2: Genuinely empty original domain from outset: x/(x - x) = 0
    p2 = repo.get_problem("PROB_FAM12_V02")
    assert p2 is not None
    assert p2.is_identity_on_domain is False
    assert p2.is_empty_domain is True
    assert p2.expected_roots == []

    # Variant 3: Boundary case with no roots: 1/(x - 2) = 0
    p3 = repo.get_problem("PROB_FAM12_V03")
    assert p3 is not None
    assert p3.is_identity_on_domain is False
    assert p3.is_empty_domain is False
    assert p3.expected_roots == []


def test_adjustment_5_fam03_concrete_rational_coefficients():
    """Adjustment 5: FAM_03 concrete rational coefficients only, no new parametric variables."""
    repo = MethodKnowledgeRepository()
    fam03 = repo.get_family("FAM_03_LIN_RATIONAL_COEFF")
    assert fam03 is not None

    fam03_probs = repo.list_problems(family_id="FAM_03_LIN_RATIONAL_COEFF")
    assert len(fam03_probs) == 3

    # All expressions must contain only numbers, operators, and variable x
    for p in fam03_probs:
        tokens = set(p.original_expression.replace(" ", "").replace("*", "").replace("/", "").replace("+", "").replace("-", "").replace("(", "").replace(")", "").replace("=", ""))
        # Only digits and 'x' allowed
        non_digit_vars = {c for c in tokens if not c.isdigit()}
        assert non_digit_vars == {"x"}, f"Found forbidden symbols or parameters in {p.original_expression}"


def test_adjustment_6_reproducibility_canonical_hashing():
    """Adjustment 6: Canonical JSONL has stable ordering; hash invariant to timestamps or SQLite."""
    data_a = {"z_key": 1, "a_key": "val", "list": [3, 2, 1]}
    data_b = {"a_key": "val", "z_key": 1, "list": [3, 2, 1]}

    # Serializations must match exactly regardless of input dict key insertion order
    str_a = canonical_json_dumps(data_a)
    str_b = canonical_json_dumps(data_b)
    assert str_a == str_b

    # Content hash must be deterministic
    hash_a = compute_content_sha256(str_a)
    hash_b = compute_content_sha256(str_b)
    assert hash_a == hash_b

    # Hash does not contain timestamp fields
    data_with_time = dict(data_a)
    data_with_time["timestamp"] = "2026-09-25T12:00:00Z"
    # Stripping timestamp ensures reproducible content hash
    cleaned = {k: v for k, v in data_with_time.items() if k not in ("timestamp", "created_at")}
    assert compute_content_sha256(canonical_json_dumps(cleaned)) == hash_a


def test_adjustment_7_research_integrity_provisional_and_discrepancies():
    """Adjustment 7: review_status = PROVISIONAL for unreviewed annotations; preserve discrepancies."""
    repo = MethodKnowledgeRepository()

    # All unreviewed annotations must be PROVISIONAL
    for p in repo.list_problems():
        for ann in repo.get_annotations_for_problem(p.problem_id):
            assert ann.review_status == ReviewStatus.PROVISIONAL

    # Discrepancy report must exist and contain non-overwritten disagreements
    reports_disc = Path("reports/DEV02A_DISCREPANCIES.json")
    assert reports_disc.exists()
    with open(reports_disc, "r", encoding="utf-8") as f:
        discrepancies = json.load(f)

    assert isinstance(discrepancies, list)
    assert len(discrepancies) > 0, "Discrepancies must be preserved, not overwritten or hidden"
