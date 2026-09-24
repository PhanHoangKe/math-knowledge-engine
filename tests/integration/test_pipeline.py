"""Integration tests for the complete verification pipeline."""

from mke.models.enums import MethodId, SolutionProofStatus, Split
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine, result_to_problem_record


def test_end_to_end_linear_pipeline():
    engine = VerificationEngine()
    result = engine.verify("4*x + 8 = 0")

    assert result.is_verified_method is True
    assert result.is_verified_solution is True
    assert result.verified_roots == ["-2"]
    assert result.method_instance.method_id == MethodId.M1_LINEAR_EQUATION

    # Convert to ProblemRecord
    ast_dict = Parser.from_text("4*x + 8 = 0").parse_equation().to_dict()
    record = result_to_problem_record(
        result, family_id="FAM_LIN", problem_id="P_001", split=Split.DEV, raw_ast_dict=ast_dict
    )
    assert record.family_id == "FAM_LIN"
    assert record.problem_id == "P_001"
    assert record.split == Split.DEV
    assert record.exact_solution == ["-2"]
    assert record.is_verified_solution is True


def test_end_to_end_rational_pipeline():
    engine = VerificationEngine()
    result = engine.verify("(x^2 - 5*x + 6) / (x - 2) = 0")

    assert result.domain_str == "R \\ {2}"
    assert result.verified_roots == ["3"]
    assert result.method_instance.method_id == MethodId.M4_RATIONAL_EQUATION
    assert result.is_verified_solution is True


def test_end_to_end_biquadratic_pipeline():
    engine = VerificationEngine()
    result = engine.verify("x^4 - 5*x^2 + 4 = 0")

    assert result.is_verified_method is True
    assert result.is_verified_solution is True
    assert sorted(result.verified_roots) == ["-1", "-2", "1", "2"]
