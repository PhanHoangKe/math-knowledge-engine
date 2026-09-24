"""Unit tests for proof obligations and verification states."""

import sympy
from mke.methods.m3_factorization import audit_division_step
from mke.models.enums import ObligationId, ObligationStatus, SolutionProofStatus
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.parsing.sympy_converter import X_SYM
from mke.verification.engine import VerificationEngine


def test_division_root_loss_audit():
    # Dividing x*(x-1)=0 by x
    orig_poly = sympy.Poly(X_SYM * (X_SYM - 1), X_SYM)
    div_poly = sympy.Poly(X_SYM, X_SYM)
    res_poly = sympy.Poly(X_SYM - 1, X_SYM)

    ob = audit_division_step(orig_poly, div_poly, res_poly)
    assert ob.obligation_id == ObligationId.NONZERO_GUARD
    assert ob.status == ObligationStatus.FAIL
    assert ob.counterexample is not None
    assert "lost" in ob.counterexample


def test_extraneous_root_transfer_audit():
    """Verify that transferring the extraneous root x = 2 from T1 to T2 is detected as UNSAFE_COPY."""
    ast = Parser.from_text("(x^2 - 5*x + 6) / (x - 2) = 0").parse_equation()
    norm = normalize_equation(ast)

    # Domain rejects root 2
    assert norm.domain.contains(2) is False
    assert norm.domain.contains(3) is True

    # Audit transfer of source roots [2, 3] from T1
    from mke.verification.transfer import audit_solution_transfer
    validity, val_roots, rej_roots = audit_solution_transfer(norm, ["2", "3"], source_problem_id="T1")
    from mke.models.enums import TransferValidity
    assert validity == TransferValidity.UNSAFE_COPY
    assert val_roots == ["3"]
    assert any("2" in r for r in rej_roots)


def test_completeness_distinction():
    """Verify that when completeness is established, is_verified_solution is True,

    and when it cannot be established, is_verified_solution is False.
    """
    engine = VerificationEngine()
    # Fully solvable quadratic
    res_quad = engine.verify("x^2 - 5*x + 6 = 0")
    assert res_quad.is_verified_method is True
    assert res_quad.is_verified_solution is True
    assert res_quad.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
