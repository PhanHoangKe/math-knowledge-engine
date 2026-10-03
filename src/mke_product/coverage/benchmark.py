"""MKE THPT Coverage Benchmark Schemas and In-Memory Harness Skeleton."""

from __future__ import annotations

import statistics
import time
from enum import Enum
from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from mke_product.coverage.contracts import (
    ProblemIR,
    SourceInputKind,
    VerificationDisposition,
    VerificationLevel,
)


class ExpectedAnswerType(str, Enum):
    """Closed enum of expected answer types."""
    FINITE_SET = "FINITE_SET"
    INTERVAL_SET = "INTERVAL_SET"
    EXPRESSION = "EXPRESSION"
    SCALAR = "SCALAR"
    TUPLE_SET = "TUPLE_SET"
    MATRIX = "MATRIX"
    BOOLEAN = "BOOLEAN"
    STATISTICAL_VALUE = "STATISTICAL_VALUE"
    STRUCTURED = "STRUCTURED"


class BenchmarkRightsStatus(str, Enum):
    """Intellectual property rights status for benchmark cases."""
    PROJECT_AUTHORED = "PROJECT_AUTHORED"
    OPEN_LICENSED = "OPEN_LICENSED"
    PUBLIC_DOMAIN_CONFIRMED = "PUBLIC_DOMAIN_CONFIRMED"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    SOURCE_LOCATOR_ONLY = "SOURCE_LOCATOR_ONLY"


class BenchmarkSourceType(str, Enum):
    """Origin source category."""
    OFFICIAL_PUBLIC = "OFFICIAL_PUBLIC"
    OPEN_LICENSED = "OPEN_LICENSED"
    PROJECT_AUTHORED = "PROJECT_AUTHORED"
    DERIVED_METAMORPHIC = "DERIVED_METAMORPHIC"


class BenchmarkSplit(str, Enum):
    """Dataset partition."""
    DEV = "DEV"
    HOLDOUT = "HOLDOUT"
    ADVERSARIAL = "ADVERSARIAL"


class GradeBand(str, Enum):
    """Target educational grade band."""
    GRADE_10 = "GRADE_10"
    GRADE_11 = "GRADE_11"
    GRADE_12 = "GRADE_12"
    NATIONAL_EXAM = "NATIONAL_EXAM"


class BenchmarkDomain(str, Enum):
    """Broad mathematical domain."""
    ALGEBRA = "ALGEBRA"
    CALCULUS = "CALCULUS"
    GEOMETRY = "GEOMETRY"
    DISCRETE = "DISCRETE"
    TRANSCENDENTAL = "TRANSCENDENTAL"


class BenchmarkDifficulty(str, Enum):
    """Difficulty classification."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    OLYMPIAD = "OLYMPIAD"


# ---------------------------------------------------------------------------
# Typed Expected Answer Specifications
# ---------------------------------------------------------------------------

class ScalarAnswerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_type: Literal[ExpectedAnswerType.SCALAR] = ExpectedAnswerType.SCALAR
    value: str


class FiniteSetAnswerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_type: Literal[ExpectedAnswerType.FINITE_SET] = ExpectedAnswerType.FINITE_SET
    elements: Tuple[str, ...] = Field(default_factory=tuple)


class IntervalSetAnswerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_type: Literal[ExpectedAnswerType.INTERVAL_SET] = ExpectedAnswerType.INTERVAL_SET
    intervals: Tuple[str, ...] = Field(default_factory=tuple)


class ExpressionAnswerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_type: Literal[ExpectedAnswerType.EXPRESSION] = ExpectedAnswerType.EXPRESSION
    expression_latex: str


class StructuredAnswerSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    answer_type: Literal[ExpectedAnswerType.STRUCTURED] = ExpectedAnswerType.STRUCTURED
    payload_pairs: Tuple[Tuple[str, str], ...] = Field(default_factory=tuple)


ExpectedAnswerSpec = Annotated[
    Union[
        ScalarAnswerSpec,
        FiniteSetAnswerSpec,
        IntervalSetAnswerSpec,
        ExpressionAnswerSpec,
        StructuredAnswerSpec,
    ],
    Field(discriminator="answer_type"),
]


# ---------------------------------------------------------------------------
# Benchmark Case Schema
# ---------------------------------------------------------------------------

class BenchmarkCase(BaseModel):
    """Authoritative schema for THPT coverage benchmark evaluation."""
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    case_id: str = Field(..., min_length=1)
    benchmark_version: str = Field(default="1.0.0")
    grade_band: GradeBand = GradeBand.GRADE_10
    domain: BenchmarkDomain = BenchmarkDomain.ALGEBRA
    family: str = "QUADRATIC_EQUATION"
    subfamily: str = "STANDARD_FORM"
    source_type: BenchmarkSourceType = BenchmarkSourceType.PROJECT_AUTHORED
    source_locator: str = ""
    rights_status: BenchmarkRightsStatus = BenchmarkRightsStatus.PROJECT_AUTHORED
    input_mode: SourceInputKind = SourceInputKind.STRUCTURED_IR
    problem_text: str = ""
    structured_problem: Optional[ProblemIR] = None
    expected_answer: ExpectedAnswerSpec
    expected_answer_type: ExpectedAnswerType
    expected_domain: str = "R"
    required_verification_obligations: Tuple[str, ...] = Field(default_factory=tuple)
    split: BenchmarkSplit = BenchmarkSplit.DEV
    difficulty: BenchmarkDifficulty = BenchmarkDifficulty.MEDIUM
    tags: Tuple[str, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Evaluation Results and Summary Metrics
# ---------------------------------------------------------------------------

class BenchmarkEvaluationResult(BaseModel):
    """Evaluation result for a single benchmark case."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    is_correct: bool
    verification_level: VerificationLevel
    disposition: VerificationDisposition
    is_false_verified: bool
    latency_ms: float = Field(default=0.0, ge=0.0)
    actual_answer: str = ""
    error_message: Optional[str] = None


class BenchmarkSummaryMetrics(BaseModel):
    """Aggregate benchmark summary metrics."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_cases: int
    correct_count: int
    overall_correct_rate: float
    verified_correct_count: int
    verified_correct_rate: float
    exact_verified_rate: float
    symbolic_verified_rate: float
    cross_checked_rate: float
    partial_rate: float
    unsupported_rate: float
    coverage_rate: float
    false_verified_count: int
    median_latency_ms: float
    p95_latency_ms: float
    release_gate_passed: bool


def calculate_benchmark_metrics(
    results: Sequence[BenchmarkEvaluationResult],
) -> BenchmarkSummaryMetrics:
    """Calculate standard benchmark metrics over all eligible cases."""
    total = len(results)
    if total == 0:
        return BenchmarkSummaryMetrics(
            total_cases=0,
            correct_count=0,
            overall_correct_rate=0.0,
            verified_correct_count=0,
            verified_correct_rate=0.0,
            exact_verified_rate=0.0,
            symbolic_verified_rate=0.0,
            cross_checked_rate=0.0,
            partial_rate=0.0,
            unsupported_rate=0.0,
            coverage_rate=0.0,
            false_verified_count=0,
            median_latency_ms=0.0,
            p95_latency_ms=0.0,
            release_gate_passed=True,
        )

    correct_count = sum(1 for r in results if r.is_correct)
    
    # Verified correct set: EXACT_VERIFIED or SYMBOLIC_VERIFIED
    verified_correct_count = sum(
        1 for r in results
        if r.is_correct and r.verification_level in (VerificationLevel.EXACT_VERIFIED, VerificationLevel.SYMBOLIC_VERIFIED)
    )

    exact_count = sum(1 for r in results if r.verification_level == VerificationLevel.EXACT_VERIFIED)
    symbolic_count = sum(1 for r in results if r.verification_level == VerificationLevel.SYMBOLIC_VERIFIED)
    cross_checked_count = sum(1 for r in results if r.verification_level == VerificationLevel.CROSS_CHECKED)
    partial_count = sum(1 for r in results if r.verification_level == VerificationLevel.PARTIAL)
    unsupported_count = sum(1 for r in results if r.verification_level == VerificationLevel.UNSUPPORTED)

    false_verified_count = sum(1 for r in results if r.is_false_verified)

    latencies = sorted([r.latency_ms for r in results])
    median_lat = statistics.median(latencies) if latencies else 0.0
    if latencies:
        p95_idx = int(0.95 * len(latencies))
        p95_lat = latencies[min(p95_idx, len(latencies) - 1)]
    else:
        p95_lat = 0.0

    return BenchmarkSummaryMetrics(
        total_cases=total,
        correct_count=correct_count,
        overall_correct_rate=round(correct_count / total, 4),
        verified_correct_count=verified_correct_count,
        verified_correct_rate=round(verified_correct_count / total, 4),
        exact_verified_rate=round(exact_count / total, 4),
        symbolic_verified_rate=round(symbolic_count / total, 4),
        cross_checked_rate=round(cross_checked_count / total, 4),
        partial_rate=round(partial_count / total, 4),
        unsupported_rate=round(unsupported_count / total, 4),
        coverage_rate=round((total - unsupported_count) / total, 4),
        false_verified_count=false_verified_count,
        median_latency_ms=round(median_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        release_gate_passed=(false_verified_count == 0),
    )


def run_benchmark_suite(
    cases: Tuple[BenchmarkCase, ...],
    evaluator: Callable[[BenchmarkCase], BenchmarkEvaluationResult],
) -> Tuple[Tuple[BenchmarkEvaluationResult, ...], BenchmarkSummaryMetrics]:
    """Execute in-memory benchmark evaluation across a tuple of cases."""
    results_list: List[BenchmarkEvaluationResult] = []
    for case in cases:
        res = evaluator(case)
        results_list.append(res)

    results_tuple = tuple(results_list)
    metrics = calculate_benchmark_metrics(results_tuple)
    return (results_tuple, metrics)
