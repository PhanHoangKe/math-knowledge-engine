"""MKE MVP V1 — Solution Trace Engine Package.

Provides deterministic multi-method solution trace generation for supported quadratic methods:
- QUAD_FORMULA_STANDARD: Standard quadratic formula
- QUAD_FORMULA_REDUCED: Reduced quadratic formula (b' = b/2)
- QUAD_VIETE_SPECIAL_SUM: Special Viète sum (a + b + c = 0)
- QUAD_VIETE_SPECIAL_DIF: Special Viète difference (a - b + c = 0)
"""

from __future__ import annotations

from typing import Dict

from mke_product.application.traces.base import (
    BaseTraceGenerator,
    RULE_CONCLUSION,
    RULE_IDENTIFY_COEFFICIENTS,
    RULE_QUADRATIC_DISCRIMINANT,
    RULE_QUADRATIC_FORMULA,
    RULE_REAL_DISCRIMINANT_SIGN,
    RULE_REDUCED_DISCRIMINANT,
    RULE_REDUCED_QUADRATIC_FORMULA,
    RULE_VIETE_PRODUCT,
    RULE_VIETE_SPECIAL_DIF,
    RULE_VIETE_SPECIAL_SUM,
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
)
from mke_product.application.traces.formula_reduced import ReducedQuadraticFormulaTraceGenerator
from mke_product.application.traces.formula_standard import StandardQuadraticFormulaTraceGenerator
from mke_product.application.traces.viete_dif import VieteSpecialDifTraceGenerator
from mke_product.application.traces.viete_sum import VieteSpecialSumTraceGenerator
from mke_product.core.rational import Rational
from mke_product.domain.models import SolutionTrace

# Deterministic registry of executable quadratic trace generators in S1
TRACE_GENERATORS: Dict[str, BaseTraceGenerator] = {
    StandardQuadraticFormulaTraceGenerator.METHOD_ID: StandardQuadraticFormulaTraceGenerator(),
    ReducedQuadraticFormulaTraceGenerator.METHOD_ID: ReducedQuadraticFormulaTraceGenerator(),
    VieteSpecialSumTraceGenerator.METHOD_ID: VieteSpecialSumTraceGenerator(),
    VieteSpecialDifTraceGenerator.METHOD_ID: VieteSpecialDifTraceGenerator(),
}


def get_trace_generator(method_id: str) -> BaseTraceGenerator:
    """Retrieve the deterministic trace generator instance for a method ID."""
    if method_id not in TRACE_GENERATORS:
        raise TraceMethodUnavailableError(
            f"Trace generator for method '{method_id}' is unavailable or not supported in S1."
        )
    return TRACE_GENERATORS[method_id]


def generate_solution_trace(
    method_id: str, a: Rational, b: Rational, c: Rational
) -> SolutionTrace:
    """Generate deterministic exact-kernel-backed SolutionTrace."""
    generator = get_trace_generator(method_id)
    return generator.generate_trace(a, b, c)


__all__ = [
    "BaseTraceGenerator",
    "StandardQuadraticFormulaTraceGenerator",
    "ReducedQuadraticFormulaTraceGenerator",
    "VieteSpecialSumTraceGenerator",
    "VieteSpecialDifTraceGenerator",
    "TRACE_GENERATORS",
    "get_trace_generator",
    "generate_solution_trace",
    "TraceGenerationError",
    "TraceMethodNotApplicableError",
    "TraceInvalidInputError",
    "TraceInvariantError",
    "TraceMethodUnavailableError",
    "RULE_IDENTIFY_COEFFICIENTS",
    "RULE_QUADRATIC_DISCRIMINANT",
    "RULE_REAL_DISCRIMINANT_SIGN",
    "RULE_QUADRATIC_FORMULA",
    "RULE_REDUCED_DISCRIMINANT",
    "RULE_REDUCED_QUADRATIC_FORMULA",
    "RULE_VIETE_SPECIAL_SUM",
    "RULE_VIETE_SPECIAL_DIF",
    "RULE_VIETE_PRODUCT",
    "RULE_CONCLUSION",
]
