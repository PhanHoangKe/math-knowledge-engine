"""Tests for THPT Universal Coverage Engine P1 Benchmark Schemas & Metrics Harness."""

from __future__ import annotations

from typing import Tuple
import pytest

from mke_product.coverage.benchmark import (
    BenchmarkCase,
    BenchmarkDifficulty,
    BenchmarkDomain,
    BenchmarkEvaluationResult,
    BenchmarkRightsStatus,
    BenchmarkSourceType,
    BenchmarkSplit,
    ExpectedAnswerType,
    GradeBand,
    ScalarAnswerSpec,
    calculate_benchmark_metrics,
    run_benchmark_suite,
)
from mke_product.coverage.contracts import (
    VerificationDisposition,
    VerificationLevel,
)


def make_synthetic_case(case_id: str) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case_id,
        grade_band=GradeBand.GRADE_10,
        domain=BenchmarkDomain.ALGEBRA,
        family="QUADRATIC_EQUATION",
        subfamily="STANDARD_FORM",
        source_type=BenchmarkSourceType.PROJECT_AUTHORED,
        source_locator="synthetic_test",
        rights_status=BenchmarkRightsStatus.PROJECT_AUTHORED,
        expected_answer=ScalarAnswerSpec(value="0"),
        expected_answer_type=ExpectedAnswerType.SCALAR,
        split=BenchmarkSplit.DEV,
    )


class TestBenchmarkMetricsAndRunner:
    def test_empty_benchmark_metrics_deterministic(self):
        metrics = calculate_benchmark_metrics([])
        assert metrics.total_cases == 0
        assert metrics.overall_correct_rate == 0.0
        assert metrics.verified_correct_rate == 0.0
        assert metrics.coverage_rate == 0.0
        assert metrics.false_verified_count == 0
        assert metrics.release_gate_passed is True

    def test_rates_use_all_cases_in_denominator(self):
        # 4 total cases:
        # 1 correct EXACT_VERIFIED
        # 1 correct SYMBOLIC_VERIFIED
        # 1 correct PARTIAL
        # 1 UNSUPPORTED
        results = (
            BenchmarkEvaluationResult(
                case_id="c1",
                is_correct=True,
                verification_level=VerificationLevel.EXACT_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=10.0,
            ),
            BenchmarkEvaluationResult(
                case_id="c2",
                is_correct=True,
                verification_level=VerificationLevel.SYMBOLIC_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=20.0,
            ),
            BenchmarkEvaluationResult(
                case_id="c3",
                is_correct=True,
                verification_level=VerificationLevel.PARTIAL,
                disposition=VerificationDisposition.PARTIAL,
                is_false_verified=False,
                latency_ms=30.0,
            ),
            BenchmarkEvaluationResult(
                case_id="c4",
                is_correct=False,
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                is_false_verified=False,
                latency_ms=5.0,
            ),
        )

        metrics = calculate_benchmark_metrics(results)
        assert metrics.total_cases == 4
        assert metrics.correct_count == 3
        assert metrics.overall_correct_rate == 0.75  # 3/4
        # Verified correct only counts EXACT_VERIFIED and SYMBOLIC_VERIFIED (2/4)
        assert metrics.verified_correct_count == 2
        assert metrics.verified_correct_rate == 0.5   # 2/4
        assert metrics.partial_rate == 0.25          # 1/4
        assert metrics.unsupported_rate == 0.25      # 1/4
        assert metrics.coverage_rate == 0.75         # (4 - 1)/4
        assert metrics.false_verified_count == 0
        assert metrics.release_gate_passed is True

    def test_cross_checked_not_counted_in_verified_correct(self):
        results = (
            BenchmarkEvaluationResult(
                case_id="c1",
                is_correct=True,
                verification_level=VerificationLevel.CROSS_CHECKED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=15.0,
            ),
        )
        metrics = calculate_benchmark_metrics(results)
        assert metrics.total_cases == 1
        assert metrics.correct_count == 1
        assert metrics.overall_correct_rate == 1.0
        assert metrics.verified_correct_count == 0
        assert metrics.verified_correct_rate == 0.0
        assert metrics.cross_checked_rate == 1.0

    def test_false_verified_fails_release_gate(self):
        # A wrong answer marked EXACT_VERIFIED
        results = (
            BenchmarkEvaluationResult(
                case_id="c1",
                is_correct=False,
                verification_level=VerificationLevel.EXACT_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=True,
                latency_ms=10.0,
            ),
        )
        metrics = calculate_benchmark_metrics(results)
        assert metrics.false_verified_count == 1
        assert metrics.release_gate_passed is False

    def test_derived_false_verified_when_flag_not_set(self):
        # Even if is_false_verified=False is passed, metric derivation catches it
        results = (
            BenchmarkEvaluationResult(
                case_id="c1",
                is_correct=False,
                verification_level=VerificationLevel.SYMBOLIC_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=10.0,
            ),
        )
        metrics = calculate_benchmark_metrics(results)
        assert metrics.false_verified_count == 1
        assert metrics.release_gate_passed is False

    def test_latency_metrics_calculation(self):
        results = tuple(
            BenchmarkEvaluationResult(
                case_id=f"c_{i}",
                is_correct=True,
                verification_level=VerificationLevel.EXACT_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=float(i * 10),
            )
            for i in range(1, 11)  # 10, 20, ..., 100
        )
        metrics = calculate_benchmark_metrics(results)
        assert metrics.median_latency_ms == 55.0
        assert metrics.p95_latency_ms == 100.0

    def test_run_benchmark_suite_ordering_preserved(self):
        cases = (make_synthetic_case("case_1"), make_synthetic_case("case_2"))

        def dummy_evaluator(c: BenchmarkCase) -> BenchmarkEvaluationResult:
            return BenchmarkEvaluationResult(
                case_id=c.case_id,
                is_correct=True,
                verification_level=VerificationLevel.EXACT_VERIFIED,
                disposition=VerificationDisposition.ACCEPTED,
                is_false_verified=False,
                latency_ms=5.0,
                actual_answer="0",
            )

        eval_results, summary = run_benchmark_suite(cases, dummy_evaluator)
        assert len(eval_results) == 2
        assert eval_results[0].case_id == "case_1"
        assert eval_results[1].case_id == "case_2"
        assert summary.total_cases == 2
        assert summary.overall_correct_rate == 1.0
        assert summary.release_gate_passed is True
