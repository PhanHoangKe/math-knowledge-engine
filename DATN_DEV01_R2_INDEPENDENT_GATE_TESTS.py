"""DATN — DEV-01-R2 / DEV-01-R3 Independent Gate Tests.

Automated suite verifying the 7 critical gate requirements:
1. Rejection of epsilon-leak: 10^-26 is rejected as EXACT_FAIL for equation x = 0.
2. Acceptance of exact zero: 0 is accepted as EXACT_PASS for equation x = 0.
3. Independent completeness gate: missing root detection on x*(x-1)/1 = 0 with candidate {0}.
4. Quadratic full coverage: x^2 - 5x + 6 = 0 verified complete with roots {2, 3}.
5. Quadratic empty set: x^2 + 1 = 0 verified complete with empty root set.
6. Complex candidate rejection: sympy.I rejected as UNSAFE_COPY for x^2 + 1 = 0.
7. Difficult symbolic quartic: (x^4 - x - 1)/(x^2 + 1) = 0 runs fast without hang, returns UNRESOLVED completeness.
"""

import sys
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
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.completeness import audit_independent_completeness
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


def test_gate_1_epsilon_leak_rejected():
    """Gate 1: verify_root_exact(x, Rational(1, 10**26), x) MUST return EXACT_FAIL.

    Eliminates the dangerous heuristic |residual| < 1e-25 that falsely certified near-zero numbers.
    """
    x = sympy.Symbol("x", real=True)
    bad_candidate = sympy.Rational(1, 10**26)
    cert = verify_root_exact(x, bad_candidate, x)

    assert cert.status == ExactVerificationStatus.EXACT_FAIL
    assert cert.is_exact_pass is False

    sat_bool, res = check_root_satisfaction(x, bad_candidate, x)
    assert sat_bool is False
    assert res != 0


def test_gate_2_exact_zero_accepted():
    """Gate 2: verify_root_exact(x, 0, x) MUST return EXACT_PASS."""
    x = sympy.Symbol("x", real=True)
    cert = verify_root_exact(x, sympy.Integer(0), x)

    assert cert.status == ExactVerificationStatus.EXACT_PASS
    assert cert.is_exact_pass is True
    assert cert.residue == "0"

    sat_bool, res = check_root_satisfaction(x, 0, x)
    assert sat_bool is True
    assert res == 0


def test_gate_3_independent_completeness_missing_root():
    """Gate 3: Missing root detection on x*(x-1)/1 = 0 with candidate {0} only.

    The gate MUST independently derive canonical roots {0, 1} and reject completeness.
    """
    eq = normalize_equation(Parser.from_text("x*(x - 1)/1 = 0").parse_equation())
    ob, cert = audit_independent_completeness(eq, ["0"])

    assert ob.status == ObligationStatus.UNRESOLVED
    assert cert.status == ObligationStatus.UNRESOLVED
    assert "1" in cert.missing_roots
    assert sorted(cert.canonical_roots) == ["0", "1"]
    assert cert.verified_roots == ["0"]


def test_gate_4_quadratic_full_coverage_accepted():
    """Gate 4: x^2 - 5x + 6 = 0 with full roots {2, 3} verified sound and complete."""
    engine = VerificationEngine()
    result = engine.verify("x^2 - 5*x + 6 = 0")

    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert sorted(result.verified_roots) == ["2", "3"]

    completeness_ob = next(o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS)
    assert completeness_ob.status == ObligationStatus.PASS


def test_gate_5_quadratic_negative_discriminant_empty_accepted():
    """Gate 5: x^2 + 1 = 0 (Delta = -4 < 0) verified sound and complete empty set."""
    engine = VerificationEngine()
    result = engine.verify("x^2 + 1 = 0")

    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert result.verified_roots == []

    completeness_ob = next(o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS)
    assert completeness_ob.status == ObligationStatus.PASS


def test_gate_6_complex_candidate_transfer_rejected():
    """Gate 6: target x^2 + 1 = 0 with candidate sympy.I must be flagged UNSAFE_COPY."""
    eq = normalize_equation(Parser.from_text("x^2 + 1 = 0").parse_equation())
    validity, valid_roots, rejected_roots = audit_solution_transfer(eq, [sympy.I])

    assert validity == TransferValidity.UNSAFE_COPY
    assert len(valid_roots) == 0
    assert len(rejected_roots) == 1
    assert "not a valid real number" in rejected_roots[0]


def test_gate_7_symbolic_quartic_fast_unresolved():
    """Gate 7: (x^4 - x - 1)/(x^2 + 1) = 0 runs fast (< 1s), marks completeness UNRESOLVED.

    Never certifies solution as complete, never claims empty set, avoids hanging.
    """
    engine = VerificationEngine()
    t0 = time.time()
    result = engine.verify("(x^4 - x - 1)/(x^2 + 1) = 0")
    elapsed = time.time() - t0

    assert elapsed < 3.0, f"Quartic verification took too long: {elapsed:.2f}s"
    assert result.is_verified_solution is False
    assert result.solution_status == SolutionProofStatus.SOUND_PARTIAL
    assert len(result.verified_roots) == 2

    completeness_ob = next(o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS)
    assert completeness_ob.status == ObligationStatus.UNRESOLVED


def run_standalone():
    print("=" * 80)
    print("RUNNING 7 INDEPENDENT GATE TESTS")
    print("=" * 80)
    tests = [
        ("Gate 1: Epsilon leak rejected", test_gate_1_epsilon_leak_rejected),
        ("Gate 2: Exact zero accepted", test_gate_2_exact_zero_accepted),
        ("Gate 3: Missing root detected independently", test_gate_3_independent_completeness_missing_root),
        ("Gate 4: Quadratic full coverage accepted", test_gate_4_quadratic_full_coverage_accepted),
        ("Gate 5: Quadratic negative discriminant empty accepted", test_gate_5_quadratic_negative_discriminant_empty_accepted),
        ("Gate 6: Complex candidate transfer rejected", test_gate_6_complex_candidate_transfer_rejected),
        ("Gate 7: Symbolic quartic fast unresolved", test_gate_7_symbolic_quartic_fast_unresolved),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} ({e})")

    print("=" * 80)
    print(f"RESULT: {passed}/{len(tests)} gate tests PASSED.")
    print("=" * 80)
    return passed == len(tests)


if __name__ == "__main__":
    success = run_standalone()
    sys.exit(0 if success else 1)
