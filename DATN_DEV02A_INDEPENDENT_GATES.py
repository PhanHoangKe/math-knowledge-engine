"""Dependency-free adversarial gates for the DEV-02A pilot dataset.

This intentionally checks the persisted artifacts independently of the application
validator, so a validator/data agreement cannot mask a shared defect.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).parent
PILOT = ROOT / "data" / "dev_pilot"

def load(name):
    return [json.loads(x) for x in (PILOT / name).read_text(encoding="utf-8").splitlines() if x.strip()]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    families, problems, annotations, pairs = [load(x) for x in ("families.jsonl", "problems.jsonl", "annotations.jsonl", "transfer_pairs.jsonl")]
    assert len(families) == 15 and len(problems) == 41 and len(annotations) == 43 and len(pairs) == 4
    assert all(x["review_status"] == "PROVISIONAL" for rows in (families, problems, annotations, pairs) for x in rows)
    assert all(x["split"] == "DEV" for x in problems)
    fam = {x["family_id"]: x for x in families}
    assert fam["FAM_11_RAT_EXTRANEOUS_TRANSFER"]["dependent_family_ids"] == ["FAM_04_QUAD_TWO_ROOTS"]
    assert fam["FAM_11_RAT_EXTRANEOUS_TRANSFER"]["split_group_id"] == fam["FAM_04_QUAD_TWO_ROOTS"]["split_group_id"]
    assert len({x["problem_id"] for x in problems}) == 41
    assert len({x["annotation_id"] for x in annotations}) == 43
    assert len({x["pair_id"] for x in pairs}) == 4
    assert any(x["pair_id"] == "PAIR_MANDATORY_FAM04_FAM11_03" and x["proposed_transfer_status"] == "UNSAFE_COPY" for x in pairs)
    manifest = json.loads((PILOT / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["file_hashes"].items():
        assert sha256(PILOT / name) == expected, (name, sha256(PILOT / name), expected)
    print("DEV02A independent gates: 10/10 PASS")

if __name__ == "__main__":
    main()
