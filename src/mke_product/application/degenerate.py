"""MKE MVP V1 — Degenerate Equation Exact Solver and Host Verifier.

Provides exact deterministic solving and independent host verification for
univariate equations where a == 0 (linear, identity, and contradiction cases).
Zero floating-point or CAS authority: all arithmetic is performed over Q.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mke_product.core.rational import Rational
from mke_product.domain.models import (
    EquationClassificationType,
    RationalFraction,
    SolutionOutcome,
    VerificationCertificate,
    VerificationOutcome,
)


class DegenerateSolveResult(BaseModel):
    """Immutable result of solving a degenerate univariate polynomial equation (a == 0)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    classification: EquationClassificationType = Field(
        ..., description="Degenerate equation classification (LINEAR, IDENTITY, or CONTRADICTION)"
    )
    outcome: SolutionOutcome = Field(
        ..., description="Exact solution outcome"
    )
    linear_root: Optional[RationalFraction] = Field(
        default=None, description="Exact rational root -c/b when classification is LINEAR, None otherwise"
    )

    @model_validator(mode="after")
    def _validate_degenerate_solve_result(self) -> DegenerateSolveResult:
        if self.classification == EquationClassificationType.LINEAR:
            if self.outcome != SolutionOutcome.ONE_REAL_LINEAR_ROOT:
                raise ValueError(
                    f"Degenerate LINEAR classification requires outcome ONE_REAL_LINEAR_ROOT, got {self.outcome}"
                )
            if self.linear_root is None:
                raise ValueError("Degenerate LINEAR classification requires linear_root to be set")
        elif self.classification == EquationClassificationType.IDENTITY:
            if self.outcome != SolutionOutcome.INFINITE_REAL_SOLUTIONS:
                raise ValueError(
                    f"Degenerate IDENTITY classification requires outcome INFINITE_REAL_SOLUTIONS, got {self.outcome}"
                )
            if self.linear_root is not None:
                raise ValueError("Degenerate IDENTITY classification must have linear_root=None")
        elif self.classification == EquationClassificationType.CONTRADICTION:
            if self.outcome != SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION:
                raise ValueError(
                    f"Degenerate CONTRADICTION classification requires outcome NO_REAL_SOLUTIONS_CONTRADICTION, got {self.outcome}"
                )
            if self.linear_root is not None:
                raise ValueError("Degenerate CONTRADICTION classification must have linear_root=None")
        else:
            raise ValueError(f"Invalid classification for DegenerateSolveResult: {self.classification}")
        return self


def solve_exact_degenerate(b: Rational, c: Rational) -> DegenerateSolveResult:
    """Solve degenerate equation b*x + c = 0 exactly over Q without CAS or floating point."""
    if not b.is_zero:
        root_rat = -c / b
        return DegenerateSolveResult(
            classification=EquationClassificationType.LINEAR,
            outcome=SolutionOutcome.ONE_REAL_LINEAR_ROOT,
            linear_root=RationalFraction.from_rational(root_rat),
        )
    elif c.is_zero:
        return DegenerateSolveResult(
            classification=EquationClassificationType.IDENTITY,
            outcome=SolutionOutcome.INFINITE_REAL_SOLUTIONS,
            linear_root=None,
        )
    else:
        return DegenerateSolveResult(
            classification=EquationClassificationType.CONTRADICTION,
            outcome=SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION,
            linear_root=None,
        )


class DegenerateHostVerifier:
    """Independent host verification engine for degenerate equations (a == 0)."""

    VERIFIER_NAME: str = "MKE_DEGENERATE_HOST_VERIFIER_V1"
    VERIFIER_VERSION: str = "1.0.0"

    def verify_degenerate_solution(
        self,
        b: Rational,
        c: Rational,
        candidate: DegenerateSolveResult,
        problem_hash: str = "",
    ) -> VerificationCertificate:
        """Verify the mathematical correctness of a degenerate solution candidate.

        Performs:
        1. Exact independent classification from (b, c).
        2. Expected outcome & root derivation from first principles.
        3. Match against candidate classification, outcome, and root.
        4. Exact residual evaluation over Q when linear (b*r + c == 0).
        5. Exact canonical identity derivation for identity and contradiction.
        6. Issues tamper-evident VerificationCertificate without synthetic discriminants.
        """
        identities: List[str] = []
        residuals: List[str] = []
        all_checks_valid = True

        # 1. Derive expected truth independently from (b, c)
        if not b.is_zero:
            expected_class = EquationClassificationType.LINEAR
            expected_outcome = SolutionOutcome.ONE_REAL_LINEAR_ROOT
            expected_root: Optional[Rational] = -c / b
        elif c.is_zero:
            expected_class = EquationClassificationType.IDENTITY
            expected_outcome = SolutionOutcome.INFINITE_REAL_SOLUTIONS
            expected_root = None
        else:
            expected_class = EquationClassificationType.CONTRADICTION
            expected_outcome = SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION
            expected_root = None

        # 2. Check candidate against expected truth
        if candidate.classification != expected_class:
            all_checks_valid = False

        if candidate.outcome != expected_outcome:
            all_checks_valid = False

        if expected_class == EquationClassificationType.LINEAR:
            if candidate.linear_root is None:
                all_checks_valid = False
            else:
                cand_root_rat = candidate.linear_root.to_rational()
                res = b * cand_root_rat + c
                if res.is_zero:
                    residuals.append(f"Residual f({cand_root_rat}) = 0 (EXACT_ZERO)")
                else:
                    all_checks_valid = False
                    residuals.append(f"Residual f({cand_root_rat}) = {res} != 0 (FAILED)")

                if expected_root is not None and cand_root_rat == expected_root and res.is_zero:
                    identities.append(
                        f"Linear equation {b}*x + ({c}) = 0 uniquely solved by x = {cand_root_rat}."
                    )
                else:
                    all_checks_valid = False

        elif expected_class == EquationClassificationType.IDENTITY:
            if candidate.linear_root is not None:
                all_checks_valid = False
            else:
                identities.append("0*x + 0 == 0 for all x in R")

        else:  # CONTRADICTION
            if candidate.linear_root is not None:
                all_checks_valid = False
            else:
                identities.append(f"0*x + ({c}) == 0 has no solution because c != 0")

        final_outcome = (
            VerificationOutcome.VERIFIED_COMPLETE
            if all_checks_valid
            else VerificationOutcome.VERIFICATION_FAILED
        )

        # Build deterministic integrity fingerprint (unkeyed SHA-256 digest)
        candidate_outcome_val = getattr(candidate.outcome, "value", str(candidate.outcome))
        sig_payload = {
            "verifier": self.VERIFIER_NAME,
            "version": self.VERIFIER_VERSION,
            "problem_hash": problem_hash,
            "b": str(b),
            "c": str(c),
            "expected_classification": expected_class.value,
            "candidate_outcome": candidate_outcome_val,
            "verification_outcome": final_outcome.value,
            "identities": identities,
            "residuals": residuals,
        }
        sig_str = json.dumps(sig_payload, sort_keys=True)
        cert_sig = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()
        cert_id = hashlib.sha256(f"cert:degenerate:{problem_hash}:{cert_sig}".encode("utf-8")).hexdigest()[:16]

        return VerificationCertificate(
            certificate_id=cert_id,
            problem_hash=problem_hash,
            outcome=final_outcome,
            verifier_name=self.VERIFIER_NAME,
            verifier_version=self.VERIFIER_VERSION,
            verified_at_utc=datetime.utcnow(),
            algebraic_identities_passed=identities,
            residual_checks=residuals,
            vieta_relations_checked=False,
            multiplicity_verified=False,
            no_real_roots_verified=(expected_class == EquationClassificationType.CONTRADICTION and all_checks_valid),
            integrity_fingerprint=cert_sig,
            certificate_signature=cert_sig,
        )


def verify_degenerate_solution(
    b: Rational,
    c: Rational,
    candidate: DegenerateSolveResult,
    problem_hash: str = "",
) -> VerificationCertificate:
    """Convenience functional gateway for degenerate host verification."""
    verifier = DegenerateHostVerifier()
    return verifier.verify_degenerate_solution(b=b, c=c, candidate=candidate, problem_hash=problem_hash)
