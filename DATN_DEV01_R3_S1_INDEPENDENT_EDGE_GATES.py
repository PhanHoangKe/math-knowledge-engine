"""Independent DEV-01-R3-S1 tests. Intentionally fail on audited source when unsafe.
Run: PYTHONPATH=src python -m pytest -v /path/to/this/file
No production source code modified.
"""
import sympy as sp
from mke.models.domain import verify_root_exact
from mke.models.enums import ExactVerificationStatus, ObligationStatus
from mke.parsing import Parser, normalize_equation
from mke.verification.completeness import audit_independent_completeness


def test_control_exact_rational_root_still_passes():
    x = sp.Symbol("x", real=True)
    assert verify_root_exact(x - 1, sp.Integer(1), x).status == ExactVerificationStatus.EXACT_PASS


def test_f5_inexact_sympy_float_must_not_get_exact_certificate():
    """SymPy Float 1.0 with 15-digit precision is NOT 1 + 10^-30."""
    x = sp.Symbol("x", real=True)
    expr = x - sp.Rational(10**30 + 1, 10**30)
    approx = sp.Float("1.0", 15)
    assert approx != sp.Rational(10**30 + 1, 10**30)
    cert = verify_root_exact(expr, approx, x)
    assert cert.status != ExactVerificationStatus.EXACT_PASS, (
        f"Approximate input was erroneously certified: {cert.status}, method={cert.method}"
    )


def test_f6_mixed_correct_and_incorrect_root_cannot_pass():
    norm = normalize_equation(Parser.from_text("x-1=0").parse_equation())
    ob, cert = audit_independent_completeness(norm, ["1", "2"])
    assert ob.status != ObligationStatus.PASS, (
        f"Invalid submitted root '2' silently discarded, but PASS returned: {cert.model_dump()}"
    )


def test_f6_mixed_correct_and_malformed_root_cannot_pass():
    norm = normalize_equation(Parser.from_text("x-1=0").parse_equation())
    ob, cert = audit_independent_completeness(norm, ["1", "not_a_root"])
    assert ob.status != ObligationStatus.PASS, (
        f"Malformed submitted root silently discarded, but PASS returned: {cert.model_dump()}"
    )


def test_control_correct_singleton_audit_passes():
    norm = normalize_equation(Parser.from_text("x-1=0").parse_equation())
    ob, _ = audit_independent_completeness(norm, ["1"])
    assert ob.status == ObligationStatus.PASS
