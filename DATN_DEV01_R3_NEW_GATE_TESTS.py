"""Independent follow-up checks for Math Knowledge Engine DEV-01-R3.

These tests are EXTERNAL to the submitted repository, with deliberately harmless
built-in arithmetic strings. A failing security test does not demonstrate an
exploit reachable from the current CLI: the affected functions are lower-level APIs.
"""
import sympy
from mke.models.domain import check_root_satisfaction, verify_root_exact
from mke.models.enums import ExactVerificationStatus, ObligationStatus, SolutionProofStatus
from mke.parsing.parser import Parser
from mke.parsing.normalizer import normalize_equation
from mke.verification.completeness import audit_independent_completeness
from mke.verification.engine import VerificationEngine


def test_expected_exact_rejection_still_works():
    x = sympy.Symbol('x', real=True)
    cert = verify_root_exact(x, sympy.Rational(1, 10**26), x)
    assert cert.status == ExactVerificationStatus.EXACT_FAIL
    assert cert.is_exact_pass is False


def test_expected_missing_root_detection_still_works():
    eq = normalize_equation(Parser.from_text('x*(x-1)/1=0').parse_equation())
    ob, cert = audit_independent_completeness(eq, ['0'])
    assert ob.status != ObligationStatus.PASS
    assert '1' in cert.missing_roots


def test_expected_public_verifier_behaves_on_standard_quadratic():
    res = VerificationEngine().verify('x^2 - 5*x + 6=0')
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert set(res.verified_roots) == {'2','3'}


def test_untrusted_wrapper_must_not_interpret_python_as_residue():
    """Invalid root must not be run as Python through residue formatting.

    The expression only computes a harmless integer if evaluated.
    """
    x = sympy.Symbol('x', real=True)
    text = "__import__('builtins').sum((7, 11))"
    cert = verify_root_exact(x, text, x)
    assert cert.status == ExactVerificationStatus.EXACT_FAIL
    accepted, residue = check_root_satisfaction(x, text, x)
    assert accepted is False
    assert residue != 18, 'Untrusted input was evaluated as Python by the compatibility wrapper'


def test_completeness_must_not_evaluate_or_accept_untrusted_root_strings():
    """A provided string is NOT an exact-verified typed root certificate."""
    eq = normalize_equation(Parser.from_text('x - 18=0').parse_equation())
    text = "__import__('builtins').sum((7, 11))"
    ob, cert = audit_independent_completeness(eq, [text])
    assert ob.status != ObligationStatus.PASS, 'Unverified arbitrary text obtained completeness PASS'


def test_empty_domain_cannot_certify_a_nonempty_claimed_root_list():
    eq = normalize_equation(Parser.from_text('x/0=0').parse_equation())
    ob, cert = audit_independent_completeness(eq, ['1'])
    assert ob.status != ObligationStatus.PASS, 'Empty domain cannot have a nonempty certified solution set'


def test_exact_fail_must_not_be_just_uncertified_numeric_refutation():
    """Numerical approximation without a certified error interval isn't an exact proof."""
    x = sympy.Symbol('x', real=True)
    z = sympy.Symbol('z')
    algebraic_root = sympy.CRootOf(z**3 - z - 1, 0)
    cert = verify_root_exact(x - 1, algebraic_root, x)
    assert not (
        cert.status == ExactVerificationStatus.EXACT_FAIL
        and cert.method == 'NUMERICAL_REFUTATION'
    ), 'EXACT_FAIL was certified from an unbounded numerical approximation alone'
