"""Deterministic SQLite Indexer for MKE Knowledge Base.

Builds and queries an offline SQLite database directly from canonical JSONL files.
Guarantees:
- Rebuilds 100% deterministically from JSONL source of truth.
- Strictly parameterized SQL queries (no string interpolation).
- Fast lookup for methods, families, problems, annotations, and transfer pairs.
"""

from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from mke.knowledge.provenance import read_jsonl


SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS methods (
    method_id TEXT PRIMARY KEY,
    method_version TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    name_en TEXT NOT NULL,
    mathematical_scope TEXT NOT NULL,
    expected_transformation_type TEXT NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS families (
    family_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    equation_class TEXT NOT NULL,
    split_group_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS problems (
    problem_id TEXT PRIMARY KEY,
    family_id TEXT NOT NULL,
    variant_id TEXT NOT NULL,
    split TEXT NOT NULL,
    original_expression TEXT NOT NULL,
    canonical_representation TEXT NOT NULL,
    domain_str TEXT NOT NULL,
    equation_class TEXT NOT NULL,
    near_miss_category TEXT NOT NULL,
    is_identity_on_domain INTEGER NOT NULL,
    is_empty_domain INTEGER NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (family_id) REFERENCES families(family_id)
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    problem_id TEXT NOT NULL,
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    method_instance_id TEXT,
    admissibility TEXT NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (problem_id) REFERENCES problems(problem_id),
    FOREIGN KEY (method_id) REFERENCES methods(method_id)
);

CREATE TABLE IF NOT EXISTS transfer_pairs (
    pair_id TEXT PRIMARY KEY,
    source_problem_id TEXT NOT NULL,
    target_problem_id TEXT NOT NULL,
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    transfer_category TEXT NOT NULL,
    proposed_transfer_status TEXT NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (source_problem_id) REFERENCES problems(problem_id),
    FOREIGN KEY (target_problem_id) REFERENCES problems(problem_id),
    FOREIGN KEY (method_id) REFERENCES methods(method_id)
);

CREATE INDEX IF NOT EXISTS idx_families_split_group ON families(split_group_id);
CREATE INDEX IF NOT EXISTS idx_problems_family ON problems(family_id);
CREATE INDEX IF NOT EXISTS idx_problems_class ON problems(equation_class);
CREATE INDEX IF NOT EXISTS idx_annotations_problem ON annotations(problem_id);
CREATE INDEX IF NOT EXISTS idx_annotations_method ON annotations(method_id);
CREATE INDEX IF NOT EXISTS idx_transfer_source ON transfer_pairs(source_problem_id);
CREATE INDEX IF NOT EXISTS idx_transfer_target ON transfer_pairs(target_problem_id);
"""


class KnowledgeBaseIndexer:
    """Manages SQLite index creation and parameterized queries."""

    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path = str(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.executescript(SCHEMA_DDL)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def rebuild_from_jsonl(
        self,
        methods_path: Path | str,
        families_path: Path | str,
        problems_path: Path | str,
        annotations_path: Path | str,
        transfer_pairs_path: Path | str,
    ) -> Dict[str, int]:
        """Drop all tables and rebuild deterministically from canonical JSONL files."""
        conn = self.connect()
        cursor = conn.cursor()

        # Disable foreign keys temporarily during drop & recreate
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("DROP TABLE IF EXISTS transfer_pairs;")
        cursor.execute("DROP TABLE IF EXISTS annotations;")
        cursor.execute("DROP TABLE IF EXISTS problems;")
        cursor.execute("DROP TABLE IF EXISTS families;")
        cursor.execute("DROP TABLE IF EXISTS methods;")
        cursor.executescript(SCHEMA_DDL)
        cursor.execute("PRAGMA foreign_keys = ON;")

        counts = {}

        # 1. Methods
        methods_data = read_jsonl(methods_path)
        for m in sorted(methods_data, key=lambda x: str(x.get("method_id", ""))):
            cursor.execute(
                """
                INSERT INTO methods (
                    method_id, method_version, name_vi, name_en,
                    mathematical_scope, expected_transformation_type, review_status, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    m["method_id"],
                    m["method_version"],
                    m["name_vi"],
                    m["name_en"],
                    m["mathematical_scope"],
                    m["expected_transformation_type"],
                    m["review_status"],
                    json.dumps(m, ensure_ascii=False, sort_keys=True),
                ),
            )
        counts["methods"] = len(methods_data)

        # 2. Families
        families_data = read_jsonl(families_path)
        for f in sorted(families_data, key=lambda x: str(x.get("family_id", ""))):
            cursor.execute(
                """
                INSERT INTO families (
                    family_id, name, description, equation_class, split_group_id, review_status, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f["family_id"],
                    f["name"],
                    f["description"],
                    f["equation_class"],
                    f["split_group_id"],
                    f["review_status"],
                    json.dumps(f, ensure_ascii=False, sort_keys=True),
                ),
            )
        counts["families"] = len(families_data)

        # 3. Problems
        problems_data = read_jsonl(problems_path)
        for p in sorted(problems_data, key=lambda x: str(x.get("problem_id", ""))):
            cursor.execute(
                """
                INSERT INTO problems (
                    problem_id, family_id, variant_id, split, original_expression,
                    canonical_representation, domain_str, equation_class, near_miss_category,
                    is_identity_on_domain, is_empty_domain, review_status, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["problem_id"],
                    p["family_id"],
                    p["variant_id"],
                    p["split"],
                    p["original_expression"],
                    p["canonical_representation"],
                    p["domain_str"],
                    p["equation_class"],
                    p["near_miss_category"],
                    1 if p.get("is_identity_on_domain") else 0,
                    1 if p.get("is_empty_domain") else 0,
                    p["review_status"],
                    json.dumps(p, ensure_ascii=False, sort_keys=True),
                ),
            )
        counts["problems"] = len(problems_data)

        # 4. Annotations
        annotations_data = read_jsonl(annotations_path)
        for a in sorted(annotations_data, key=lambda x: str(x.get("annotation_id", ""))):
            cursor.execute(
                """
                INSERT INTO annotations (
                    annotation_id, problem_id, method_id, method_version,
                    method_instance_id, admissibility, review_status, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a["annotation_id"],
                    a["problem_id"],
                    a["method_id"],
                    a["method_version"],
                    a.get("method_instance_id"),
                    a["admissibility"],
                    a["review_status"],
                    json.dumps(a, ensure_ascii=False, sort_keys=True),
                ),
            )
        counts["annotations"] = len(annotations_data)

        # 5. Transfer Pairs
        transfer_data = read_jsonl(transfer_pairs_path)
        for tp in sorted(transfer_data, key=lambda x: str(x.get("pair_id", ""))):
            cursor.execute(
                """
                INSERT INTO transfer_pairs (
                    pair_id, source_problem_id, target_problem_id, method_id,
                    method_version, transfer_category, proposed_transfer_status,
                    review_status, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tp["pair_id"],
                    tp["source_problem_id"],
                    tp["target_problem_id"],
                    tp["method_id"],
                    tp["method_version"],
                    tp["transfer_category"],
                    tp["proposed_transfer_status"],
                    tp["review_status"],
                    json.dumps(tp, ensure_ascii=False, sort_keys=True),
                ),
            )
        counts["transfer_pairs"] = len(transfer_data)

        conn.commit()
        return counts

    # Parameterized query methods
    def get_method(self, method_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM methods WHERE method_id = ?;", (method_id,))
        row = cursor.fetchone()
        return json.loads(row["raw_json"]) if row else None

    def list_methods(self) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM methods ORDER BY method_id;")
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]

    def get_family(self, family_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM families WHERE family_id = ?;", (family_id,))
        row = cursor.fetchone()
        return json.loads(row["raw_json"]) if row else None

    def list_families(self) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM families ORDER BY family_id;")
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]

    def get_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM problems WHERE problem_id = ?;", (problem_id,))
        row = cursor.fetchone()
        return json.loads(row["raw_json"]) if row else None

    def list_problems(
        self, family_id: Optional[str] = None, equation_class: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        if family_id and equation_class:
            cursor.execute(
                "SELECT raw_json FROM problems WHERE family_id = ? AND equation_class = ? ORDER BY problem_id;",
                (family_id, equation_class),
            )
        elif family_id:
            cursor.execute(
                "SELECT raw_json FROM problems WHERE family_id = ? ORDER BY problem_id;",
                (family_id,),
            )
        elif equation_class:
            cursor.execute(
                "SELECT raw_json FROM problems WHERE equation_class = ? ORDER BY problem_id;",
                (equation_class,),
            )
        else:
            cursor.execute("SELECT raw_json FROM problems ORDER BY problem_id;")
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]

    def get_annotations_for_problem(self, problem_id: str) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute(
            "SELECT raw_json FROM annotations WHERE problem_id = ? ORDER BY annotation_id;",
            (problem_id,),
        )
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]

    def get_transfer_pairs_for_problem(self, problem_id: str) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute(
            """
            SELECT raw_json FROM transfer_pairs
            WHERE source_problem_id = ? OR target_problem_id = ?
            ORDER BY pair_id;
            """,
            (problem_id, problem_id),
        )
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]

    def list_transfer_pairs(self) -> List[Dict[str, Any]]:
        cursor = self.connect().cursor()
        cursor.execute("SELECT raw_json FROM transfer_pairs ORDER BY pair_id;")
        return [json.loads(r["raw_json"]) for r in cursor.fetchall()]
