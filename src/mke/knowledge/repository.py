"""Method Knowledge Repository for MKE.

High-level interface providing access to method templates, families, problems,
annotations, and transfer pairs, backed by deterministic JSONL files and SQLite indexer.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

from mke.knowledge.indexer import KnowledgeBaseIndexer
from mke.knowledge.schemas import (
    FamilyRecord,
    MethodAnnotation,
    MethodTemplate,
    ProblemRecord,
    TransferPairRecord,
)


class MethodKnowledgeRepository:
    """Repository facade managing knowledge base and pilot dev dataset."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        db_path: Optional[Path | str] = None,
        knowledge_dir: Optional[Path | str] = None,
        dataset_dir: Optional[Path | str] = None,
    ):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        else:
            self.base_dir = Path(base_dir)

        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else self.base_dir / "data" / "knowledge"
        self.dev_pilot_dir = Path(dataset_dir) if dataset_dir else self.base_dir / "data" / "dev_pilot"

        self.methods_file = self.knowledge_dir / "methods.jsonl"
        self.families_file = self.dev_pilot_dir / "families.jsonl"
        self.problems_file = self.dev_pilot_dir / "problems.jsonl"
        self.annotations_file = self.dev_pilot_dir / "annotations.jsonl"
        self.transfer_pairs_file = self.dev_pilot_dir / "transfer_pairs.jsonl"

        if db_path is None:
            self.db_path = self.knowledge_dir / "mke_kb.db"
        else:
            self.db_path = Path(db_path)

        self.indexer = KnowledgeBaseIndexer(self.db_path)

    def rebuild_index(self) -> Dict[str, int]:
        """Rebuild SQLite index deterministically from JSONL files."""
        return self.indexer.rebuild_from_jsonl(
            methods_path=self.methods_file,
            families_path=self.families_file,
            problems_path=self.problems_file,
            annotations_path=self.annotations_file,
            transfer_pairs_path=self.transfer_pairs_file,
        )

    def get_method(self, method_id: str) -> Optional[MethodTemplate]:
        raw = self.indexer.get_method(method_id)
        if raw is None and self.methods_file.exists():
            # If DB index not built yet, fallback to building
            self.rebuild_index()
            raw = self.indexer.get_method(method_id)
        return MethodTemplate.model_validate(raw) if raw else None

    def list_methods(self) -> List[MethodTemplate]:
        raw_list = self.indexer.list_methods()
        if not raw_list and self.methods_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.list_methods()
        return [MethodTemplate.model_validate(r) for r in raw_list]

    def get_family(self, family_id: str) -> Optional[FamilyRecord]:
        raw = self.indexer.get_family(family_id)
        if raw is None and self.families_file.exists():
            self.rebuild_index()
            raw = self.indexer.get_family(family_id)
        return FamilyRecord.model_validate(raw) if raw else None

    def list_families(self) -> List[FamilyRecord]:
        raw_list = self.indexer.list_families()
        if not raw_list and self.families_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.list_families()
        return [FamilyRecord.model_validate(r) for r in raw_list]

    def get_problem(self, problem_id: str) -> Optional[ProblemRecord]:
        raw = self.indexer.get_problem(problem_id)
        if raw is None and self.problems_file.exists():
            self.rebuild_index()
            raw = self.indexer.get_problem(problem_id)
        return ProblemRecord.model_validate(raw) if raw else None

    def list_problems(
        self, family_id: Optional[str] = None, equation_class: Optional[str] = None
    ) -> List[ProblemRecord]:
        raw_list = self.indexer.list_problems(family_id=family_id, equation_class=equation_class)
        if not raw_list and self.problems_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.list_problems(family_id=family_id, equation_class=equation_class)
        return [ProblemRecord.model_validate(r) for r in raw_list]

    def get_annotations_for_problem(self, problem_id: str) -> List[MethodAnnotation]:
        raw_list = self.indexer.get_annotations_for_problem(problem_id)
        if not raw_list and self.annotations_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.get_annotations_for_problem(problem_id)
        return [MethodAnnotation.model_validate(r) for r in raw_list]

    def get_transfer_pairs_for_problem(self, problem_id: str) -> List[TransferPairRecord]:
        raw_list = self.indexer.get_transfer_pairs_for_problem(problem_id)
        if not raw_list and self.transfer_pairs_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.get_transfer_pairs_for_problem(problem_id)
        return [TransferPairRecord.model_validate(r) for r in raw_list]

    def list_transfer_pairs(self) -> List[TransferPairRecord]:
        raw_list = self.indexer.list_transfer_pairs()
        if not raw_list and self.transfer_pairs_file.exists():
            self.rebuild_index()
            raw_list = self.indexer.list_transfer_pairs()
        return [TransferPairRecord.model_validate(r) for r in raw_list]

    def get_problems_for_method(self, method_id: str) -> List[ProblemRecord]:
        """Find problems that have an annotation matching method_id."""
        conn = self.indexer.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT p.raw_json
            FROM problems p
            JOIN annotations a ON p.problem_id = a.problem_id
            WHERE a.method_id = ?
            ORDER BY p.problem_id;
            """,
            (method_id,),
        )
        return [ProblemRecord.model_validate_json(row["raw_json"]) for row in cursor.fetchall()]


KnowledgeRepository = MethodKnowledgeRepository
