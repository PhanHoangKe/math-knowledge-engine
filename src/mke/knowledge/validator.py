"""Knowledge Base and Dataset Integrity Validator for MKE.

Performs rigorous structural, relational, and data leakage checks:
1. Schema validation against Pydantic models.
2. ID uniqueness (methods, families, problems, annotations, transfer pairs).
3. Foreign key reference integrity.
4. Split group dependency integrity (dependent families must share split_group_id).
5. Split purity verification (100% DEV, 0% VALIDATION/TEST).
6. Cross-family expression leakage and duplicate detection.
7. Manifest and content hash verification.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import json

from mke.models.enums import Split
from mke.knowledge.provenance import compute_file_sha256, read_jsonl
from mke.knowledge.schemas import (
    FamilyRecord,
    MethodAnnotation,
    MethodTemplate,
    ProblemRecord,
    TransferPairRecord,
)


@dataclass
class ValidationIssue:
    severity: str  # "ERROR" or "WARNING"
    category: str
    message: str
    record_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetValidationReport:
    is_valid: bool
    total_errors: int
    total_warnings: int
    issues: List[ValidationIssue]
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "record_id": i.record_id,
                    "details": i.details,
                }
                for i in self.issues
            ],
            "stats": self.stats,
        }


class KnowledgeBaseValidator:
    """Validates structural and relational integrity of knowledge base and dataset."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
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
        self.manifest_file = self.dev_pilot_dir / "manifest.json"

    def validate_all(self) -> DatasetValidationReport:
        issues: List[ValidationIssue] = []
        stats: Dict[str, Any] = {}

        # 1. Load and schema validate Methods
        methods_map: Dict[str, MethodTemplate] = {}
        if not self.methods_file.exists():
            issues.append(ValidationIssue("ERROR", "FILE_MISSING", f"Methods file missing: {self.methods_file}"))
        else:
            for item in read_jsonl(self.methods_file):
                mid = str(item.get("method_id", ""))
                if mid in methods_map:
                    issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"Duplicate method_id: {mid}", mid))
                try:
                    m = MethodTemplate.model_validate(item)
                    methods_map[m.method_id.value] = m
                except Exception as e:
                    issues.append(ValidationIssue("ERROR", "SCHEMA_ERROR", f"Invalid MethodTemplate: {e}", mid))
        stats["methods_count"] = len(methods_map)

        # 2. Load and schema validate Families
        families_map: Dict[str, FamilyRecord] = {}
        split_group_map: Dict[str, str] = {}
        if not self.families_file.exists():
            issues.append(ValidationIssue("ERROR", "FILE_MISSING", f"Families file missing: {self.families_file}"))
        else:
            for item in read_jsonl(self.families_file):
                fid = str(item.get("family_id", ""))
                if fid in families_map:
                    issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"Duplicate family_id: {fid}", fid))
                try:
                    f = FamilyRecord.model_validate(item)
                    families_map[f.family_id] = f
                    split_group_map[f.family_id] = f.split_group_id
                except Exception as e:
                    issues.append(ValidationIssue("ERROR", "SCHEMA_ERROR", f"Invalid FamilyRecord: {e}", fid))
        stats["families_count"] = len(families_map)

        # 3. Check Family dependency and split group integrity
        for fid, fam in families_map.items():
            for dep_id in fam.dependent_family_ids:
                if dep_id not in families_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Family {fid} references non-existent dependent family {dep_id}", fid))
                else:
                    dep_fam = families_map[dep_id]
                    if fam.split_group_id != dep_fam.split_group_id:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                "SPLIT_GROUP_LEAKAGE",
                                f"Family {fid} depends on {dep_id} but they have different split_group_id ({fam.split_group_id} vs {dep_fam.split_group_id}). They must share split_group_id to prevent data leakage.",
                                fid,
                            )
                        )

        # 4. Load and schema validate Problems
        problems_map: Dict[str, ProblemRecord] = {}
        seen_expressions: Dict[str, str] = {}  # expr -> problem_id
        for item in read_jsonl(self.problems_file) if self.problems_file.exists() else []:
            pid = str(item.get("problem_id", ""))
            if pid in problems_map:
                issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"Duplicate problem_id: {pid}", pid))

            try:
                prob = ProblemRecord.model_validate(item)
                problems_map[prob.problem_id] = prob

                # Foreign key: family_id must exist
                if prob.family_id not in families_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Problem {pid} references unknown family_id: {prob.family_id}", pid))

                # Split purity check: strictly DEV, zero VALIDATION or TEST
                if prob.split != Split.DEV:
                    issues.append(ValidationIssue("ERROR", "UNAPPROVED_SPLIT", f"Problem {pid} has split {prob.split}. Only DEV_PILOT (DEV) is permitted in DEV-02A.", pid))

                # Check duplicate expression
                expr_clean = prob.original_expression.replace(" ", "")
                if expr_clean in seen_expressions:
                    issues.append(
                        ValidationIssue(
                            "WARNING",
                            "DUPLICATE_EXPRESSION",
                            f"Problem {pid} has identical expression to {seen_expressions[expr_clean]}: {prob.original_expression}",
                            pid,
                        )
                    )
                else:
                    seen_expressions[expr_clean] = pid

            except Exception as e:
                issues.append(ValidationIssue("ERROR", "SCHEMA_ERROR", f"Invalid ProblemRecord: {e}", pid))
        stats["problems_count"] = len(problems_map)

        # 5. Load and schema validate Annotations
        annotations_map: Dict[str, MethodAnnotation] = {}
        for item in read_jsonl(self.annotations_file) if self.annotations_file.exists() else []:
            aid = str(item.get("annotation_id", ""))
            if aid in annotations_map:
                issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"Duplicate annotation_id: {aid}", aid))
            try:
                ann = MethodAnnotation.model_validate(item)
                annotations_map[ann.annotation_id] = ann

                # Foreign key checks
                if ann.problem_id not in problems_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Annotation {aid} references unknown problem_id: {ann.problem_id}", aid))
                if ann.method_id.value not in methods_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Annotation {aid} references unknown method_id: {ann.method_id}", aid))

            except Exception as e:
                issues.append(ValidationIssue("ERROR", "SCHEMA_ERROR", f"Invalid MethodAnnotation: {e}", aid))
        stats["annotations_count"] = len(annotations_map)

        # 6. Load and schema validate Transfer Pairs
        transfer_map: Dict[str, TransferPairRecord] = {}
        for item in read_jsonl(self.transfer_pairs_file) if self.transfer_pairs_file.exists() else []:
            tpid = str(item.get("pair_id", ""))
            if tpid in transfer_map:
                issues.append(ValidationIssue("ERROR", "DUPLICATE_ID", f"Duplicate pair_id: {tpid}", tpid))
            try:
                tp = TransferPairRecord.model_validate(item)
                transfer_map[tp.pair_id] = tp

                # Foreign key checks
                if tp.source_problem_id not in problems_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Transfer pair {tpid} references unknown source_problem_id: {tp.source_problem_id}", tpid))
                if tp.target_problem_id not in problems_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Transfer pair {tpid} references unknown target_problem_id: {tp.target_problem_id}", tpid))
                if tp.method_id.value not in methods_map:
                    issues.append(ValidationIssue("ERROR", "BROKEN_REFERENCE", f"Transfer pair {tpid} references unknown method_id: {tp.method_id}", tpid))

                # Check split group consistency of source and target
                src_prob = problems_map.get(tp.source_problem_id)
                tgt_prob = problems_map.get(tp.target_problem_id)
                if src_prob and tgt_prob:
                    src_sg = split_group_map.get(src_prob.family_id)
                    tgt_sg = split_group_map.get(tgt_prob.family_id)
                    if src_sg and tgt_sg and src_sg != tgt_sg:
                        issues.append(
                            ValidationIssue(
                                "ERROR",
                                "TRANSFER_SPLIT_GROUP_MISMATCH",
                                f"Transfer pair {tpid} connects source {tp.source_problem_id} (split_group: {src_sg}) to target {tp.target_problem_id} (split_group: {tgt_sg}). Transfer pairs must belong to the same split_group to avoid cross-split leakage.",
                                tpid,
                            )
                        )

            except Exception as e:
                issues.append(ValidationIssue("ERROR", "SCHEMA_ERROR", f"Invalid TransferPairRecord: {e}", tpid))
        stats["transfer_pairs_count"] = len(transfer_map)

        # 7. Manifest validation
        if self.manifest_file.exists():
            try:
                manifest_data = json.loads(self.manifest_file.read_text(encoding="utf-8"))
                file_hashes = manifest_data.get("file_hashes", {})
                for fname, expected_hash in file_hashes.items():
                    fpath = self.dev_pilot_dir / fname
                    if not fpath.exists():
                        issues.append(ValidationIssue("ERROR", "MANIFEST_ERROR", f"Manifest file entry missing on disk: {fname}"))
                    else:
                        actual_hash = compute_file_sha256(fpath)
                        if actual_hash != expected_hash:
                            issues.append(
                                ValidationIssue(
                                    "ERROR",
                                    "HASH_MISMATCH",
                                    f"Hash mismatch for {fname}: expected {expected_hash}, got {actual_hash}",
                                    fname,
                                )
                            )
            except Exception as e:
                issues.append(ValidationIssue("ERROR", "MANIFEST_ERROR", f"Error reading manifest: {e}"))

        total_errors = sum(1 for i in issues if i.severity == "ERROR")
        total_warnings = sum(1 for i in issues if i.severity == "WARNING")

        return DatasetValidationReport(
            is_valid=(total_errors == 0),
            total_errors=total_errors,
            total_warnings=total_warnings,
            issues=issues,
            stats=stats,
        )
