"""Independent counter-audit test cases (A1 - A7) proposed by the Research Auditor."""

import pytest
from mke.models.enums import MethodId, SolutionProofStatus
from mke.verification.engine import VerificationEngine


@pytest.fixture
def engine() -> VerificationEngine:
    return VerificationEngine()


def test_case_a1_biquadratic_four_roots(engine):
    """A1: x^4 - 5*x^2 + 4 = 0 => {-2, -1, 1, 2}.

    Verifies that M5 uses x = +/- sqrt(t), so t=4 yields x = +/- 2.
    """
    res = engine.verify("x^4 - 5*x^2 + 4 = 0")
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert res.method_instance.method_id == MethodId.M5_BIQUADRATIC_SUBSTITUTION
    assert sorted(res.verified_roots) == ["-1", "-2", "1", "2"]
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_case_a2_biquadratic_with_zero_root(engine):
    """A2: x^4 - 4*x^2 = 0 => {-2, 0, 2}."""
    res = engine.verify("x^4 - 4*x^2 = 0")
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert sorted(res.verified_roots) == ["-2", "0", "2"]


def test_case_a3_rational_extraneous_root_empty_set(engine):
    """A3: (x^2 - 1)/(x - 1) = 2 => Vô nghiệm (x=1 làm mẫu số bằng 0)."""
    res = engine.verify("(x^2 - 1) / (x - 1) = 2")
    assert res.domain_str == "R \\ {1}"
    assert res.method_instance.method_id == MethodId.M4_RATIONAL_EQUATION
    assert res.is_verified_solution is True
    # The cleared equation gives x=1, which is excluded by domain -> solution set is empty
    assert res.verified_roots == []
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_case_a4_rational_identity_exclusion(engine):
    """A4: (x - 3)/(x - 3) = 1 => R \\ {3}."""
    res = engine.verify("(x - 3) / (x - 3) = 1")
    assert res.domain_str == "R \\ {3}"
    assert res.is_identity_on_domain is True
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_case_a5_nested_denominators(engine):
    """A5: 1/(x/(x-1)) = (x-1)/x => R \\ {0, 1}.

    Critical test: verifies that nested fraction denominators are not lost.
    """
    res = engine.verify("1 / (x / (x - 1)) = (x - 1) / x")
    assert res.domain_str == "R \\ {0, 1}"
    assert not res.is_all_reals_domain
    assert res.is_identity_on_domain is True
    assert res.is_verified_solution is True
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_case_a6_biquadratic_negative_t_roots(engine):
    """A6: x^4 + 5*x^2 + 4 = 0 => Vô nghiệm thực (t=-1, t=-4 đều < 0)."""
    res = engine.verify("x^4 + 5*x^2 + 4 = 0")
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert res.verified_roots == []
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_case_a7_degree_8_out_of_scope(engine):
    """A7: x^4 * x^4 = 0 => Bậc sau chuẩn hóa là 8 > 4 -> OUT_OF_SCOPE."""
    res = engine.verify("x^4 * x^4 = 0")
    assert res.is_verified_method is False
    assert res.is_verified_solution is False
    assert res.solution_status == SolutionProofStatus.UNDETERMINED
    assert "OUT_OF_SCOPE" in res.explanation
    assert "degree 8" in res.explanation
