"""DEV-01-R3 Proof Gate & Independent Completeness Regression Test Suite.

Verifies:
1. True root 0 exact pass.
2. Rational candidate wrong by 10^-26 exact fail (no epsilon leak).
3. Degree 2 candidate missing a root (x*(x-1)/1 = 0 with {0}) returns UNRESOLVED completeness.
4. Difficult symbolic quartic (x^4 - x - 1)/(x^2 + 1) = 0 safe UNRESOLVED, no hang.
5. Complex input I rejected and domain preserved.
"""

from fractions import Fraction
import time
import pytest
import sympy

from mke.models.domain import check_root_satisfaction, verify_root_exact
from mke.models.enums import (
    ExactVerificationStatus,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    TransferValidity,
)
from mke.parsing import Parser, normalize_equation
from mke.verification.completeness import audit_independent_completeness
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


def test_r3_true_root_zero():
    """Requirement C: True root 0 must be EXACT_PASS."""
    x = sympy.Symbol("x", real=True)
    cert = verify_root_exact(x, 0, x)
    assert cert.status == ExactVerificationStatus.EXACT_PASS
    assert cert.is_exact_pass is True
    assert cert.residue == "0"

    sat, res = check_root_satisfaction(x, 0, x)
    assert sat is True
    assert res == 0


def test_r3_rational_candidate_wrong_10_minus_26():
    """Requirement C: Rational candidate 10^-26 on x = 0 must be EXACT_FAIL, never True."""
    x = sympy.Symbol("x", real=True)
    bad_val = sympy.Rational(1, 10**26)
    cert = verify_root_exact(x, bad_val, x)
    assert cert.status == ExactVerificationStatus.EXACT_FAIL
    assert cert.is_exact_pass is False

    sat, res = check_root_satisfaction(x, bad_val, x)
    assert sat is False
    assert res == bad_val


def test_r3_degree_2_missing_candidate_root():
    """Requirement C: Degree 2 with missing candidate root must fail completeness."""
    eq = normalize_equation(Parser.from_text("x*(x - 1)/1 = 0").parse_equation())
    ob, cert = audit_independent_completeness(eq, ["0"])

    assert ob.status == ObligationStatus.UNRESOLVED
    assert cert.status == ObligationStatus.UNRESOLVED
    assert "1" in cert.missing_roots
    assert cert.canonical_roots == ["0", "1"]
    assert cert.verified_roots == ["0"]


def test_r3_difficult_symbolic_quartic_safe_unresolved():
    """Requirement C: Difficult symbolic quartic returns fast and marks UNRESOLVED safely."""
    engine = VerificationEngine()
    t0 = time.time()
    res = engine.verify("(x^4 - x - 1)/(x^2 + 1) = 0")
    elapsed = time.time() - t0

    assert elapsed < 3.0
    assert res.is_verified_solution is False
    assert res.solution_status == SolutionProofStatus.SOUND_PARTIAL
    assert len(res.verified_roots) == 2

    comp_ob = next(o for o in res.obligations if o.obligation_id == ObligationId.COMPLETENESS)
    assert comp_ob.status == ObligationStatus.UNRESOLVED


def test_r3_complex_input_i_rejected():
    """Requirement C: Complex input I rejected and domain preserved."""
    eq = normalize_equation(Parser.from_text("x^2 + 1 = 0").parse_equation())
    validity, valid, rejected = audit_solution_transfer(eq, [sympy.I])

    assert validity == TransferValidity.UNSAFE_COPY
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "not a valid real number" in rejected[0]
