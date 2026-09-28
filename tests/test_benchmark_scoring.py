"""
Comprehensive Unit Tests for MKE THPT Benchmark Scoring & Telemetry Engine (P03C-P1A).
Tests domain-aware normalization, multi-format evaluations, false-success attacks,
and extraneous root telemetry invariants.
"""

import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from scripts.benchmark_scoring import (
    BenchmarkOutcome,
    check_extraneous_root_leak,
    evaluate_benchmark_response,
    normalize_math_string,
    parse_interval_tokens,
    parse_system_solution,
)

class TestBenchmarkScoringSuite:
    """Rigorous verification suite for benchmark scoring engine."""

    def test_normalization_tokens(self):
        assert normalize_math_string(" 5 / 2 ") == "5/2"
        assert normalize_math_string("\\frac{2}{3}") == "(2/3)"
        assert normalize_math_string("\\sqrt{3}") == "sqrt(3)"
        assert normalize_math_string("(-\\infty, 2) \\cup (3, +\\infty)") == "(-oo,2)u(3,oo)"

    def test_interval_token_parsing(self):
        intervals = parse_interval_tokens("(-oo, 2) U (3, +oo)")
        assert intervals == {"(-oo,2)", "(3,oo)"}

    def test_system_solution_parsing(self):
        sol_list = ["x = 2", "y = -1"]
        sys_dict = parse_system_solution(sol_list)
        assert sys_dict == {"x": "2", "y": "-1"}

    def test_extraneous_root_leak_detection(self):
        leaked, roots = check_extraneous_root_leak({"0", "4"}, ["0", "-3"])
        assert leaked is True
        assert roots == ["0"]

        leaked_clean, roots_clean = check_extraneous_root_leak({"4"}, ["0", "-3"])
        assert leaked_clean is False
        assert roots_clean == []

    def test_scoring_success_exact_set(self):
        problem = {
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["1", "4"]
            }
        }
        mock_resp = {
            "symbolic_result": "{1, 4}",
            "solution_set": ["1", "4"]
        }
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.SUCCESS
        assert res["matched_ground_truth"] is True

    def test_scoring_extraneous_root_leak_outcome(self):
        problem = {
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["4"],
                "extraneous_roots": ["0"]
            }
        }
        mock_resp = {
            "symbolic_result": "{0, 4}",
            "solution_set": ["0", "4"]
        }
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.EXTRANEOUS_ROOT_LEAK
        assert res["matched_ground_truth"] is False
        assert res["telemetry"]["admitted_invalid_roots_count"] == 1

    def test_false_success_attack_on_boolean_array(self):
        """Verify that an empty response or string is NEVER accepted as True/False success."""
        problem = {
            "format_type": "FORMAT_II_TRUE_FALSE",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "BOOLEAN_ARRAY",
                "boolean_values": {"a": True, "b": False, "c": True, "d": False}
            }
        }
        # Engine outputs empty set or text
        mock_resp = {"symbolic_result": "{}", "solution_set": []}
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.GENUINE_WRONG_ANSWER
        assert res["matched_ground_truth"] is False

    def test_true_false_full_and_partial_scoring(self):
        problem = {
            "format_type": "FORMAT_II_TRUE_FALSE",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "BOOLEAN_ARRAY",
                "boolean_values": {"a": True, "b": False, "c": True, "d": False}
            }
        }
        # Correct booleans
        mock_correct = {"boolean_values": {"a": True, "b": False, "c": True, "d": False}}
        res_corr = evaluate_benchmark_response(problem, "SUCCESS", mock_correct)
        assert res_corr["outcome"] == BenchmarkOutcome.SUCCESS
        assert res_corr["matched_ground_truth"] is True
        assert res_corr["correct_statements_count"] == 4

        # Partial booleans (3/4)
        mock_partial = {"boolean_values": {"a": True, "b": True, "c": True, "d": False}}
        res_part = evaluate_benchmark_response(problem, "SUCCESS", mock_partial)
        assert res_part["outcome"] == BenchmarkOutcome.GENUINE_WRONG_ANSWER
        assert res_part["matched_ground_truth"] is False
        assert res_part["correct_statements_count"] == 3

    def test_mcq_choice_and_mathematical_fallback(self):
        problem = {
            "format_type": "FORMAT_I_MCQ",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "CHOICE_KEY",
                "correct_choice": "B",
                "exact_solution_set": ["(-oo, 2) U (3, oo)"]
            }
        }
        # Explicit choice key B
        mock_key = {"selected_choice": "B"}
        res_key = evaluate_benchmark_response(problem, "SUCCESS", mock_key)
        assert res_key["outcome"] == BenchmarkOutcome.SUCCESS
        assert res_key["matched_ground_truth"] is True

        # Mathematical fallback
        mock_math = {"symbolic_result": "(-oo, 2) U (3, +oo)"}
        res_math = evaluate_benchmark_response(problem, "SUCCESS", mock_math)
        assert res_math["outcome"] == BenchmarkOutcome.SUCCESS
        assert res_math["matched_ground_truth"] is True

        # Wrong choice key
        mock_wrong = {"selected_choice": "A"}
        res_wrong = evaluate_benchmark_response(problem, "SUCCESS", mock_wrong)
        assert res_wrong["outcome"] == BenchmarkOutcome.GENUINE_WRONG_ANSWER
        assert res_wrong["matched_ground_truth"] is False

    def test_system_of_equations_scoring(self):
        problem = {
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x = 2", "y = -1"]
            }
        }
        mock_resp = {"solution_set": ["x = 2", "y = -1"]}
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.SUCCESS
        assert res["matched_ground_truth"] is True

    def test_domain_error_never_classified_as_success_for_empty_set(self):
        """Ensure DOMAIN_ERROR or INVALID_INPUT is NEVER scored as SUCCESS."""
        problem = {
            "format_type": "FORMAT_III_SHORT_ANSWER",
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": []
            }
        }
        mock_resp = {"error_message": "Division by zero"}
        res = evaluate_benchmark_response(problem, "DOMAIN_ERROR", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.DOMAIN_REJECTED
        assert res["matched_ground_truth"] is False
