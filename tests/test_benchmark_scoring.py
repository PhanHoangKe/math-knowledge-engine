"""
Unit tests for MKE THPT Benchmark Scoring & Normalization Logic.
Validates exact outcome categorization against known correct, wrong, and adversarial responses.
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
    normalize_solution_set,
    normalize_solution_token,
)

class TestBenchmarkScoringSuite:
    """Rigorous tests for benchmark evaluation logic."""

    def test_normalization_tokens(self):
        assert normalize_solution_token(" 5 / 2 ") == "5/2"
        assert normalize_solution_token("\\frac{2}{3}") == "(2/3)"
        assert normalize_solution_token("\\sqrt{3}") == "sqrt(3)"

    def test_normalization_set(self):
        sol_raw = [" x = 2 ", "x=-1", "  3/2  "]
        sol_norm = normalize_solution_set(sol_raw)
        assert sol_norm == {"2", "-1", "3/2"}

    def test_extraneous_root_leak_detection(self):
        # Known extraneous roots: ["0", "-3"]
        leaked, roots = check_extraneous_root_leak({"0", "4"}, ["0", "-3"])
        assert leaked is True
        assert roots == ["0"]

        # Clean set
        leaked_clean, roots_clean = check_extraneous_root_leak({"4"}, ["0", "-3"])
        assert leaked_clean is False
        assert roots_clean == []

    def test_scoring_success_exact_set(self):
        problem = {
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
        assert res["extraneous_roots_leaked"] == 0

    def test_scoring_extraneous_root_leak_outcome(self):
        problem = {
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["4"],
                "extraneous_roots": ["0"]
            }
        }
        # Engine incorrectly includes 0 in solution set
        mock_resp = {
            "symbolic_result": "{0, 4}",
            "solution_set": ["0", "4"]
        }
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.EXTRANEOUS_ROOT_LEAK
        assert res["matched_ground_truth"] is False
        assert res["extraneous_roots_leaked"] == 1
        assert res["leaked_roots"] == ["0"]

    def test_scoring_genuine_wrong_answer(self):
        problem = {
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["2", "-2"]
            }
        }
        mock_resp = {
            "symbolic_result": "{3, -3}",
            "solution_set": ["3", "-3"]
        }
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.GENUINE_WRONG_ANSWER
        assert res["matched_ground_truth"] is False

    def test_scoring_unsupported_modality(self):
        problem = {
            "input_modality": "VIETNAMESE_WORD_PROBLEM",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["x = 15", "y = 10"]
            }
        }
        mock_resp = {}
        res = evaluate_benchmark_response(problem, "SUCCESS", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.UNSUPPORTED_MODALITY
        assert res["matched_ground_truth"] is False

    def test_scoring_unsupported_grammar(self):
        problem = {
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["2*x + 1"]
            }
        }
        mock_resp = {"error_message": "Grammar unsupported in engine"}
        res = evaluate_benchmark_response(problem, "OUT_OF_SCOPE", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.UNSUPPORTED_GRAMMAR
        assert res["matched_ground_truth"] is False

    def test_scoring_timeout(self):
        problem = {
            "input_modality": "SYMBOLIC_TYPED",
            "ground_truth": {
                "solution_type": "EXACT_SET",
                "exact_solution_set": ["1"]
            }
        }
        mock_resp = {"error_message": "Process timed out after 5.0s"}
        res = evaluate_benchmark_response(problem, "TIMEOUT", mock_resp)
        assert res["outcome"] == BenchmarkOutcome.TIMEOUT
        assert res["matched_ground_truth"] is False
