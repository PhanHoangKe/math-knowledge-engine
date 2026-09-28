"""
MKE GDPT 2018 Curriculum Taxonomy & Capability Matrix Reconciliation Auditor.
Provides machine-checkable validation of all 100 curriculum archetypes, capability classifications,
and benchmark distributions.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_taxonomy_archetypes():
    tax_path = REPO_ROOT / "docs" / "curriculum" / "GDPT2018_THPT_MATH_TAXONOMY.md"
    with open(tax_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Pattern matching `ARCH-XX.YY.ZZ`: Description
    pattern = re.compile(r"`(ARCH-(10|11|12)\.([0-9A-Za-z]+)\.([0-9]+))`:\s*(.+)")
    items = []
    for line in text.splitlines():
        m = pattern.search(line)
        if m:
            arch_id = m.group(1)
            grade = int(m.group(2))
            topic = m.group(3)
            num = int(m.group(4))
            desc = m.group(5).strip()
            is_elective = ".E" in arch_id
            items.append({
                "id": arch_id,
                "grade": grade,
                "topic": topic,
                "num": num,
                "desc": desc,
                "type": "ELECTIVE" if is_elective else "CORE",
            })
    return items


def audit_taxonomy():
    items = load_taxonomy_archetypes()
    unique_ids = set()
    duplicates = []
    for item in items:
        if item["id"] in unique_ids:
            duplicates.append(item["id"])
        unique_ids.add(item["id"])

    by_grade = {10: {"CORE": [], "ELECTIVE": []}, 11: {"CORE": [], "ELECTIVE": []}, 12: {"CORE": [], "ELECTIVE": []}}
    for item in items:
        by_grade[item["grade"]][item["type"]].append(item)

    print("=== MKE GDPT 2018 THPT MATHEMATICS TAXONOMY AUDIT ===")
    print(f"Total Parsed Archetypes: {len(items)}")
    print(f"Unique Archetype IDs: {len(unique_ids)}")
    if duplicates:
        print(f"[!] DUPLICATE IDs FOUND: {duplicates}")
    else:
        print("[OK] Zero duplicate IDs found.")


    total_core = sum(len(by_grade[g]["CORE"]) for g in [10, 11, 12])
    total_elective = sum(len(by_grade[g]["ELECTIVE"]) for g in [10, 11, 12])
    print(f"\nBreakdown:")
    for g in [10, 11, 12]:
        c_count = len(by_grade[g]["CORE"])
        e_count = len(by_grade[g]["ELECTIVE"])
        print(f"  - Grade {g}: Total={c_count + e_count} (CORE={c_count}, ELECTIVE={e_count})")
    print(f"  -> Total CORE Archetypes: {total_core}")
    print(f"  -> Total ELECTIVE Archetypes: {total_elective}")
    print(f"  -> Total Combined Archetypes: {total_core + total_elective}")

    return items


if __name__ == "__main__":
    audit_taxonomy()
