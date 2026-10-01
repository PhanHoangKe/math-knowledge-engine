"""MKE MVP V1 — Solution Trace Architecture & Base Contracts.

Defines the abstract base class, typed error hierarchy, and invariant enforcement
for deterministic quadratic solution trace generators.
Zero LLM or floating-point authority: all mathematics is derived from exact Rational/Kernel state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from mke_product.core.rational import Rational
from mke_product.domain.exact import solve_exact_quadratic
from mke_product.domain.models import (
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionStep,
    SolutionTrace,
)


# ============================================================================
# 1. TRACE ERROR TAXONOMY
# ============================================================================

class TraceGenerationError(Exception):
    """Base exception for all solution trace generation failures."""
    pass


class TraceMethodNotApplicableError(TraceGenerationError):
    """Raised when an executable method's mathematical preconditions are not met."""
    pass


class TraceInvalidInputError(TraceGenerationError):
    """Raised when equation coefficients violate domain preconditions (e.g. a == 0)."""
    pass


class TraceInvariantError(TraceGenerationError):
    """Raised when trace output fails internal mathematical consistency with exact kernel."""
    pass


class TraceMethodUnavailableError(TraceGenerationError, KeyError):
    """Raised when a requested method ID is unknown or has no executable generator in S1."""
    pass


# ============================================================================
# 2. STABLE MACHINE-ORIENTED RULE IDENTIFIERS
# ============================================================================

RULE_IDENTIFY_COEFFICIENTS = "RULE_IDENTIFY_COEFFICIENTS"
RULE_QUADRATIC_DISCRIMINANT = "RULE_QUADRATIC_DISCRIMINANT"
RULE_REAL_DISCRIMINANT_SIGN = "RULE_REAL_DISCRIMINANT_SIGN"
RULE_QUADRATIC_FORMULA = "RULE_QUADRATIC_FORMULA"
RULE_REDUCED_DISCRIMINANT = "RULE_REDUCED_DISCRIMINANT"
RULE_REDUCED_QUADRATIC_FORMULA = "RULE_REDUCED_QUADRATIC_FORMULA"
RULE_VIETE_SPECIAL_SUM = "RULE_VIETE_SPECIAL_SUM"
RULE_VIETE_SPECIAL_DIF = "RULE_VIETE_SPECIAL_DIF"
RULE_VIETE_PRODUCT = "RULE_VIETE_PRODUCT"
RULE_CONCLUSION = "RULE_CONCLUSION"


# ============================================================================
# 3. BASE TRACE GENERATOR
# ============================================================================

def validate_rational_coefficient(val: Any, name: str) -> None:
    """Validate that an input coefficient is strictly an instance of core Rational."""
    if not isinstance(val, Rational):
        raise TypeError(
            f"Coefficient '{name}' must be an instance of Rational, got {type(val).__name__}."
        )


def format_final_answer_latex(outcome: SolutionOutcome, roots: List[RealRootValue]) -> str:
    """Format canonical final answer LaTeX string."""
    if outcome == SolutionOutcome.NO_REAL_ROOTS or len(roots) == 0:
        return "S = \\emptyset"
    if outcome == SolutionOutcome.ONE_REPEATED_REAL_ROOT or len(roots) == 1:
        return f"x = {roots[0].latex_str}"
    # Two distinct roots
    return f"S = \\left\\{{ {roots[0].latex_str}, {roots[1].latex_str} \\right\\}}"


class BaseTraceGenerator(ABC):
    """Abstract base class for deterministic quadratic solution trace generators."""

    @property
    @abstractmethod
    def method_id(self) -> str:
        """The canonical method identifier."""
        pass

    def validate_inputs(self, a: Rational, b: Rational, c: Rational) -> None:
        """Validate input types and quadratic leading coefficient non-zero invariant."""
        validate_rational_coefficient(a, "a")
        validate_rational_coefficient(b, "b")
        validate_rational_coefficient(c, "c")

        if a.is_zero:
            raise TraceInvalidInputError(
                "Leading coefficient 'a' cannot be zero for quadratic trace generation (a != 0 required)."
            )

    @abstractmethod
    def _generate_trace_steps(
        self,
        a: Rational,
        b: Rational,
        c: Rational,
        kernel_outcome: SolutionOutcome,
        kernel_roots: List[RealRootValue],
    ) -> List[SolutionStep]:
        """Generate ordered list of SolutionStep objects."""
        pass

    def generate_trace(self, a: Rational, b: Rational, c: Rational) -> SolutionTrace:
        """Execute deterministic trace generation with exact kernel cross-verification."""
        self.validate_inputs(a, b, c)

        # 1. Exact mathematical truth from core kernel
        kernel_outcome, kernel_roots = solve_exact_quadratic(a, b, c)

        # 2. Build pedagogical steps
        steps = self._generate_trace_steps(a, b, c, kernel_outcome, kernel_roots)

        # 3. Verify step numbering invariants (1, 2, ..., N contiguous)
        if not steps:
            raise TraceInvariantError("Trace generator produced empty step list.")
        for idx, step in enumerate(steps, start=1):
            if step.step_number != idx:
                raise TraceInvariantError(
                    f"Step numbering invariant violated: expected {idx}, got {step.step_number}."
                )

        # 4. Final answer LaTeX
        final_answer = format_final_answer_latex(kernel_outcome, kernel_roots)

        return SolutionTrace(
            method_id=self.method_id,
            solution_outcome=kernel_outcome,
            roots=kernel_roots,
            steps=steps,
            final_answer_latex=final_answer,
            is_complete=True,
        )
