"""DEV-01 Verification Adapter for Knowledge Base and Pilot Dataset.

Connects the Knowledge Base representation with the DEV-01 mathematical verification engine:
- Evaluates problem instances through safe Parser, Normalizer, and MethodCatalogue.
- Runs full VerificationEngine verification.
- Compares candidate annotations with machine-checked evidence without auto-overriding either.
- Exports discrepancy reports for research auditing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import json
import shutil

from mke.knowledge.provenance import compute_file_sha256
from mke.knowledge.repository import MethodKnowledgeRepository
from mke.knowledge.schemas import MethodAnnotation, ProblemRecord, TransferPairRecord
from mke.knowledge.validator import KnowledgeBaseValidator
from mke.methods.catalogue import CATALOGUE
from mke.models.enums import MethodAdmissibility, MethodId, SolutionProofStatus
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


@dataclass
class AdapterEvaluationResult:
    problem_id: str
    method_id: str
    original_expression: str
    canonical_representation: str
    domain_str: str
    annotated_admissibility: str
    verifier_admissibility: str
    verifier_is_verified_solution: bool
    verifier_solution_status: str
    verifier_verified_roots: List[str]
    expected_roots: Optional[List[str]]
    has_discrepancy: bool
    discrepancy_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "method_id": self.method_id,
            "original_expression": self.original_expression,
            "canonical_representation": self.canonical_representation,
            "domain_str": self.domain_str,
            "annotated_admissibility": self.annotated_admissibility,
            "verifier_admissibility": self.verifier_admissibility,
            "verifier_is_verified_solution": self.verifier_is_verified_solution,
            "verifier_solution_status": self.verifier_solution_status,
            "verifier_verified_roots": self.verifier_verified_roots,
            "expected_roots": self.expected_roots,
            "has_discrepancy": self.has_discrepancy,
            "discrepancy_reasons": self.discrepancy_reasons,
        }


class Dev01Adapter:
    """Adapter bridging Knowledge Base dataset with DEV-01 verification core."""

    def __init__(
        self,
        repo: Optional[MethodKnowledgeRepository] = None,
        base_dir: Optional[Path | str] = None,
        knowledge_dir: Optional[Path | str] = None,
        dataset_dir: Optional[Path | str] = None,
    ):
        if repo is not None:
            self.repo = repo
        else:
            self.repo = MethodKnowledgeRepository(
                base_dir=base_dir,
                knowledge_dir=knowledge_dir,
                dataset_dir=dataset_dir,
            )
        self.engine = VerificationEngine()

    def evaluate_problem_method(
        self, problem: ProblemRecord, annotation: MethodAnnotation
    ) -> AdapterEvaluationResult:
        """Run a problem through DEV-01 and compare with annotation."""
        expr = problem.original_expression
        ast = Parser.from_text(expr).parse_equation()
        norm = normalize_equation(ast, raw_text=expr)

        # 1. Method admissibility according to DEV-01 Catalogue
        method_impl = CATALOGUE.get_method(annotation.method_id)
        verifier_admiss = method_impl.evaluate_admissibility(norm)

        # 2. Solution verification via VerificationEngine
        ver_result = self.engine.verify(expr)

        discrepancies: List[str] = []

        # Check admissibility agreement
        ann_adm = annotation.admissibility
        if ann_adm != MethodAdmissibility.UNKNOWN:
            if ann_adm == MethodAdmissibility.APPLICABLE and verifier_admiss not in (
                MethodAdmissibility.APPLICABLE,
                MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS,
            ):
                discrepancies.append(
                    f"Admissibility mismatch: annotation claims APPLICABLE but verifier returned {verifier_admiss.value}"
                )
            elif ann_adm == MethodAdmissibility.NOT_APPLICABLE and verifier_admiss in (
                MethodAdmissibility.APPLICABLE,
                MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS,
            ):
                discrepancies.append(
                    f"Admissibility mismatch: annotation claims NOT_APPLICABLE but verifier returned {verifier_admiss.value}"
                )

        # Check roots agreement if expected_roots specified
        if problem.expected_roots is not None:
            expected_set = set(problem.expected_roots)
            actual_set = set(ver_result.verified_roots)
            if expected_set != actual_set:
                discrepancies.append(
                    f"Solution root set mismatch: expected {sorted(list(expected_set))}, verifier produced {sorted(list(actual_set))}"
                )

        has_discrepancy = len(discrepancies) > 0

        return AdapterEvaluationResult(
            problem_id=problem.problem_id,
            method_id=annotation.method_id.value,
            original_expression=expr,
            canonical_representation=norm.canonical_str() if hasattr(norm, "canonical_str") else str(norm.numerator_sym) + " = 0",
            domain_str=norm.domain.format_domain(),
            annotated_admissibility=ann_adm.value,
            verifier_admissibility=verifier_admiss.value,
            verifier_is_verified_solution=ver_result.is_verified_solution,
            verifier_solution_status=ver_result.solution_status.value,
            verifier_verified_roots=ver_result.verified_roots,
            expected_roots=problem.expected_roots,
            has_discrepancy=has_discrepancy,
            discrepancy_reasons=discrepancies,
        )

    def evaluate_transfer_pair(self, pair: TransferPairRecord) -> Dict[str, Any]:
        """Evaluate a transfer pair using SolutionTransferAuditor."""
        src_prob = self.repo.get_problem(pair.source_problem_id)
        tgt_prob = self.repo.get_problem(pair.target_problem_id)

        if not src_prob or not tgt_prob:
            raise ValueError(f"Transfer pair {pair.pair_id} references missing problem record.")

        tgt_ast = Parser.from_text(tgt_prob.original_expression).parse_equation()
        tgt_norm = normalize_equation(tgt_ast, raw_text=tgt_prob.original_expression)

        src_roots = src_prob.expected_roots or []

        validity, valid_roots, rejected_roots = audit_solution_transfer(
            target_norm_eq=tgt_norm,
            source_candidate_roots=src_roots,
            source_problem_id=src_prob.problem_id,
        )

        has_discrepancy = (validity != pair.proposed_transfer_status)
        return {
            "pair_id": pair.pair_id,
            "source_problem_id": pair.source_problem_id,
            "target_problem_id": pair.target_problem_id,
            "proposed_status": pair.proposed_transfer_status.value,
            "audited_status": validity.value,
            "valid_transferred_roots": valid_roots,
            "rejected_transferred_roots": rejected_roots,
            "has_discrepancy": has_discrepancy,
        }

    def run_full_dev_validation(self) -> Dict[str, Any]:
        """Evaluate all problems and transfer pairs in DEV_PILOT against DEV-01."""
        problems = self.repo.list_problems()
        problem_evals: List[AdapterEvaluationResult] = []
        discrepancies: List[Dict[str, Any]] = []

        for p in problems:
            annotations = self.repo.get_annotations_for_problem(p.problem_id)
            for ann in annotations:
                res = self.evaluate_problem_method(p, ann)
                problem_evals.append(res)
                if res.has_discrepancy:
                    discrepancies.append(res.to_dict())

        transfer_pairs = self.repo.list_transfer_pairs()
        transfer_evals = []
        for tp in transfer_pairs:
            tp_res = self.evaluate_transfer_pair(tp)
            transfer_evals.append(tp_res)
            if tp_res["has_discrepancy"]:
                discrepancies.append({
                    "transfer_pair_id": tp.pair_id,
                    "type": "TRANSFER_DISCREPANCY",
                    "details": tp_res,
                })

        return {
            "total_evaluations": len(problem_evals),
            "total_transfer_evaluations": len(transfer_evals),
            "discrepancies_count": len(discrepancies),
            "discrepancies": discrepancies,
            "problem_evaluations": [e.to_dict() for e in problem_evals],
            "transfer_evaluations": transfer_evals,
        }

    def validate_dataset(self) -> Dict[str, Any]:
        """Convenience evaluation method returning summary metrics."""
        eval_res = self.run_full_dev_validation()
        problems = self.repo.list_problems()

        total_probs = len(problems)
        prob_evals = eval_res["problem_evaluations"]
        method_verified = sum(
            1 for e in prob_evals
            if e["annotated_admissibility"] in ("APPLICABLE", "APPLICABLE_WITH_OBLIGATIONS")
        )
        sol_verified = sum(1 for e in prob_evals if e["verifier_is_verified_solution"])
        match_gt = sum(1 for e in prob_evals if not e["has_discrepancy"])

        return {
            "total_problems": total_probs,
            "normalizable_count": total_probs,
            "method_verified_count": method_verified,
            "solution_verified_count": sol_verified,
            "match_ground_truth_count": match_gt,
            "discrepancy_count": eval_res["discrepancies_count"],
            "discrepancies": eval_res["discrepancies"],
            "raw_evaluations": eval_res,
        }

    def export_reports(self, reports_dir: Path | str = "reports") -> Dict[str, Path]:
        """Generate and export all DEV-02A reports."""
        r_dir = Path(reports_dir)
        r_dir.mkdir(parents=True, exist_ok=True)

        validator = KnowledgeBaseValidator(
            knowledge_dir=self.repo.knowledge_dir,
            dataset_dir=self.repo.dev_pilot_dir,
        )
        val_report = validator.validate_all()

        # 1. DEV02A_DATASET_VALIDATION.json
        val_path = r_dir / "DEV02A_DATASET_VALIDATION.json"
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(val_report.to_dict(), f, indent=2, ensure_ascii=False)

        # 2. DEV02A_ANNOTATION_REVIEW.csv
        ann_csv_path = r_dir / "DEV02A_ANNOTATION_REVIEW.csv"
        with open(ann_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "annotation_id",
                "problem_id",
                "method_id",
                "method_version",
                "method_instance_id",
                "admissibility",
                "review_status",
                "provenance",
                "annotation_evidence",
            ])
            for p in self.repo.list_problems():
                for ann in self.repo.get_annotations_for_problem(p.problem_id):
                    writer.writerow([
                        ann.annotation_id,
                        ann.problem_id,
                        ann.method_id.value,
                        ann.method_version,
                        ann.method_instance_id or "",
                        ann.admissibility.value,
                        ann.review_status.value,
                        ann.provenance,
                        ann.annotation_evidence,
                    ])

        # 3. DEV02A_DISCREPANCIES.json
        dev_res = self.run_full_dev_validation()
        disc_path = r_dir / "DEV02A_DISCREPANCIES.json"
        with open(disc_path, "w", encoding="utf-8") as f:
            json.dump(dev_res["discrepancies"], f, indent=2, ensure_ascii=False)

        # 4. DEV02A_DATASET_MANIFEST.json
        manifest_src = self.repo.dev_pilot_dir / "manifest.json"
        manifest_dest = r_dir / "DEV02A_DATASET_MANIFEST.json"
        if manifest_src.exists():
            shutil.copyfile(manifest_src, manifest_dest)

        # 5. SHA256SUMS.txt
        sums_path = r_dir / "SHA256SUMS.txt"
        files_to_hash = [
            self.repo.methods_file,
            self.repo.knowledge_dir / "manifest.json",
            self.repo.families_file,
            self.repo.problems_file,
            self.repo.annotations_file,
            self.repo.transfer_pairs_file,
            self.repo.dev_pilot_dir / "manifest.json",
            val_path,
            ann_csv_path,
            disc_path,
            manifest_dest,
        ]
        with open(sums_path, "w", encoding="utf-8") as f:
            for fp in files_to_hash:
                if fp.exists():
                    f_hash = compute_file_sha256(fp)
                    rel_p = fp.as_posix()
                    f.write(f"{f_hash}  {rel_p}\n")

        return {
            "validation_report": val_path,
            "annotation_review_csv": ann_csv_path,
            "discrepancies_report": disc_path,
            "dataset_manifest": manifest_dest,
            "sha256sums": sums_path,
        }
