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


def test_r3_s1_f1_negative_untrusted_strings_check_root_satisfaction():
    """F1: Malformed and untrusted strings must return (False, sympy.nan) without evaluation."""
    x = sympy.Symbol("x", real=True)
    payloads = [
        "__import__('builtins').sum((1, 2, 3))",
        "lambda: 42",
        "import os; os.system('echo hi')",
        "x + 1",
        "invalid_syntax_!!!",
    ]
    for p in payloads:
        accepted, residue = check_root_satisfaction(x, p, x)
        assert accepted is False
        assert residue is sympy.nan or str(residue) == "nan"


def test_r3_s1_f2_negative_untrusted_roots_completeness():
    """F2: Completeness auditor rejects untrusted and malformed root strings."""
    eq = normalize_equation(Parser.from_text("x - 10 = 0").parse_equation())
    untrusted = [
        "__import__('builtins').len('hello')",
        "10.0; import sys",
        "not_a_number",
    ]
    ob, cert = audit_independent_completeness(eq, untrusted)
    assert ob.status != ObligationStatus.PASS
    assert cert.status != ObligationStatus.PASS
    assert "10" in cert.missing_roots


def test_r3_s1_f2_negative_forged_verified_root_certificate():
    """F2: Forged VerifiedRoot with mismatched equation or false certificate is rejected."""
    from mke.models.evidence import ExactProofCertificate, VerifiedRoot

    eq = normalize_equation(Parser.from_text("x - 5 = 0").parse_equation())
    fake_cert = ExactProofCertificate(
        status=ExactVerificationStatus.EXACT_PASS,
        is_exact_pass=True,
        candidate_root="5",
        residue="0",
        method="FORGED",
    )
    # 1. Wrong equation fingerprint
    forged_wrong_fingerprint = VerifiedRoot(
        value=sympy.Integer(5),
        value_str="5",
        equation_fingerprint="x - 999",
        certificate=fake_cert,
    )
    ob, cert = audit_independent_completeness(eq, [forged_wrong_fingerprint])
    assert ob.status != ObligationStatus.PASS
    assert "5" in cert.missing_roots

    # 2. Forged root that does not satisfy equation
    forged_invalid_val = VerifiedRoot(
        value=sympy.Integer(99),
        value_str="99",
        equation_fingerprint=str(eq.numerator_sym),
        certificate=fake_cert,
    )
    ob2, cert2 = audit_independent_completeness(eq, [forged_invalid_val])
    assert ob2.status != ObligationStatus.PASS


def test_r3_s1_f3_negative_empty_domain_nonempty_roots():
    """F3: Empty domain equation with non-empty claimed roots must return FAIL."""
    eq = normalize_equation(Parser.from_text("x / (x - x) = 0").parse_equation())
    assert eq.domain.is_empty_domain
    ob, cert = audit_independent_completeness(eq, ["0", "1"])
    assert ob.status == ObligationStatus.FAIL
    assert cert.status == ObligationStatus.FAIL
    assert cert.extraneous_roots == ["0", "1"]


def test_r3_s1_f4_negative_algebraic_number_numerical_observation_unresolved():
    """F4: Unbounded evalf non-zero observation must be UNRESOLVED, never EXACT_FAIL."""
    x = sympy.Symbol("x", real=True)
    z = sympy.Symbol("z")
    algebraic_root = sympy.CRootOf(z**3 - z - 1, 0)
    cert = verify_root_exact(x - 2, algebraic_root, x)
    assert cert.status == ExactVerificationStatus.UNRESOLVED
    assert cert.method == "NUMERICAL_OBSERVATION_UNRESOLVED"
    assert cert.is_exact_pass is False


def test_r3_s2_f5_inexact_sympy_float_rejected_unresolved():
    """F5: Inexact Float must fail closed as UNRESOLVED with INEXACT_FLOAT_UNSUPPORTED."""
    x = sympy.Symbol("x", real=True)
    expr = x - (1 + sympy.Rational(1, 10**30))
    cand = sympy.Float("1.0", 15)

    cert = verify_root_exact(expr, cand)
    assert cert.is_exact_pass is False
    assert cert.status == ExactVerificationStatus.UNRESOLVED
    assert cert.method == "INEXACT_FLOAT_UNSUPPORTED"

    # Float candidate on simple equation
    cert_float = verify_root_exact(x - 1, 1.0)
    assert cert_float.is_exact_pass is False
    assert cert_float.status == ExactVerificationStatus.UNRESOLVED
    assert cert_float.method == "INEXACT_FLOAT_UNSUPPORTED"

    # Float inside expression
    cert_expr_float = verify_root_exact(x - 1.0, 1)
    assert cert_expr_float.is_exact_pass is False
    assert cert_expr_float.status == ExactVerificationStatus.UNRESOLVED
    assert cert_expr_float.method == "INEXACT_FLOAT_UNSUPPORTED"


def test_r3_s2_f5_mixed_float_algebraic_rejected_unresolved():
    """F5: Float mixed with algebraic expressions must fail closed as UNRESOLVED."""
    x = sympy.Symbol("x", real=True)
    cand = sympy.Float("1.0", 15) + sympy.sqrt(2)
    cert = verify_root_exact(x - (1 + sympy.sqrt(2)), cand)
    assert cert.is_exact_pass is False
    assert cert.status == ExactVerificationStatus.UNRESOLVED
    assert cert.method == "INEXACT_FLOAT_UNSUPPORTED"


def test_r3_s2_f5_exact_control_rational_must_pass():
    """F5 Control: Exact rational values must continue to pass cleanly."""
    x = sympy.Symbol("x", real=True)
    cert = verify_root_exact(x - sympy.Rational(1, 2), sympy.Rational(1, 2))
    assert cert.is_exact_pass is True
    assert cert.status == ExactVerificationStatus.EXACT_PASS


def test_r3_s2_f6_mixed_correct_and_incorrect_root_cannot_pass():
    """F6: Completeness audit with mixed valid and invalid roots cannot receive PASS."""
    norm_eq = normalize_equation(Parser.from_text("x - 1 = 0").parse_equation())
    ob, cert = audit_independent_completeness(norm_eq, ["1", "2"])
    assert ob.status != ObligationStatus.PASS
    assert cert.status != ObligationStatus.PASS
    assert "2" not in cert.verified_roots
    assert "1" in cert.verified_roots
    assert "2" in cert.extraneous_roots or "2" in cert.details.get("rejected_candidates", [])


def test_r3_s2_f6_mixed_correct_and_malformed_root_cannot_pass():
    """F6: Completeness audit with mixed valid and malformed candidate cannot receive PASS."""
    norm_eq = normalize_equation(Parser.from_text("x - 1 = 0").parse_equation())
    ob, cert = audit_independent_completeness(norm_eq, ["1", "not_a_root"])
    assert ob.status != ObligationStatus.PASS
    assert cert.status != ObligationStatus.PASS
    assert "not_a_root" not in cert.verified_roots
    assert "1" in cert.verified_roots
    assert (
        "not_a_root" in cert.extraneous_roots
        or "not_a_root" in cert.details.get("rejected_candidates", [])
    )


def test_r3_s2_f6_clean_valid_batch_must_pass():
    """F6 Control: Valid batch matching canonical roots must receive PASS."""
    norm_eq = normalize_equation(Parser.from_text("x - 1 = 0").parse_equation())
    ob, cert = audit_independent_completeness(norm_eq, ["1"])
    assert ob.status == ObligationStatus.PASS
    assert cert.status == ObligationStatus.PASS
    assert cert.verified_roots == ["1"]
    assert len(cert.extraneous_roots) == 0

