"""Mandatory smoke test cases T1 to T8."""

import pytest
from mke.audit.smoke_runner import SmokeSuiteRunner


@pytest.fixture(scope="module")
def smoke_results():
    runner = SmokeSuiteRunner()
    return runner.run_all()


def test_smoke_suite_all_pass(smoke_results):
    """Verify that all handcrafted smoke test cases pass without failures."""
    assert smoke_results["failed"] == 0
    assert smoke_results["passed"] == smoke_results["total_tests"]
    assert smoke_results["total_tests"] >= 8


def test_smoke_t1_standard_quadratic(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T1")
    assert case["passed"] is True
    # Verify roots {2, 3}
    roots_check = next(chk for chk in case["checks"] if chk["check"] == "VERIFIED_ROOTS")
    assert roots_check["passed"] is True
    assert sorted(roots_check["actual"]) == ["2", "3"]


def test_smoke_t2_rational_unsafe_copy_detection(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T2")
    assert case["passed"] is True
    # Root 3 verified
    roots_check = next(chk for chk in case["checks"] if chk["check"] == "VERIFIED_ROOTS")
    assert roots_check["actual"] == ["3"]
    # Domain is R \ {2}
    dom_check = next(chk for chk in case["checks"] if chk["check"] == "DOMAIN_PRESERVATION")
    assert dom_check["actual"] == "R \\ {2}"
    # Unsafe copy detected
    trans_check = next(chk for chk in case["checks"] if chk["check"] == "TRANSFER_AUDIT_UNSAFE_COPY")
    assert trans_check["passed"] is True
    assert trans_check["actual_validity"] == "UNSAFE_COPY"


def test_smoke_t3_rational_identity_domain_preservation(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T3")
    assert case["passed"] is True
    dom_check = next(chk for chk in case["checks"] if chk["check"] == "DOMAIN_PRESERVATION")
    assert dom_check["actual"] == "R \\ {2}"
    ident_check = next(chk for chk in case["checks"] if chk["check"] == "IDENTITY_ON_DOMAIN")
    assert ident_check["actual"] is True


def test_smoke_t4_zero_product_root_loss_detection(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T4")
    assert case["passed"] is True
    roots_check = next(chk for chk in case["checks"] if chk["check"] == "VERIFIED_ROOTS")
    assert sorted(roots_check["actual"]) == ["0", "1"]
    div_check = next(chk for chk in case["checks"] if chk["check"] == "DIVISION_ROOT_LOSS_DETECTION")
    assert div_check["passed"] is True
    assert div_check["obligation_status"] == "FAIL"


def test_smoke_t5_quadratic_a_zero_rejection(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T5")
    assert case["passed"] is True
    m2_check = next(chk for chk in case["checks"] if chk["check"] == "M2_A_ZERO_REJECTION")
    assert m2_check["passed"] is True
    assert m2_check["actual_admissibility"] == "NOT_APPLICABLE"


def test_smoke_t6_biquadratic_sign_constraint(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T6")
    assert case["passed"] is True
    roots_check = next(chk for chk in case["checks"] if chk["check"] == "VERIFIED_ROOTS")
    assert sorted(roots_check["actual"]) == ["-1", "1"]
    t_check = next(chk for chk in case["checks"] if chk["check"] == "SIGN_CONSTRAINT_T_GE_0")
    assert t_check["passed"] is True


def test_smoke_t7_empty_real_solution_set(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T7")
    assert case["passed"] is True
    roots_check = next(chk for chk in case["checks"] if chk["check"] == "VERIFIED_ROOTS")
    assert roots_check["actual"] == []


def test_smoke_t8_out_of_scope_rejection(smoke_results):
    case = next(c for c in smoke_results["results"] if c["id"] == "T8")
    assert case["passed"] is True
    out_check = next(chk for chk in case["checks"] if chk["check"] == "OUT_OF_SCOPE")
    assert out_check["passed"] is True
