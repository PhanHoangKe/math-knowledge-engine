"""MKE MVP V1 Application Layer.

Orchestrates user intake, bounded AST normalization, method selection, and trace execution.
"""

from .degenerate import (
    DegenerateHostVerifier,
    DegenerateSolveResult,
    solve_exact_degenerate,
    verify_degenerate_solution,
)
from .errors import (
    ApplicationError,
    ApplicationErrorCode,
    map_parser_exception_to_application_error,
)
from .normalizer import (
    PolynomialQDegree2,
    normalize_equation,
    normalize_expression,
    normalize_raw_equation,
)
from .traces import (
    BaseTraceGenerator,
    ReducedQuadraticFormulaTraceGenerator,
    StandardQuadraticFormulaTraceGenerator,
    TRACE_GENERATORS,
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
    VieteSpecialDifTraceGenerator,
    VieteSpecialSumTraceGenerator,
    generate_solution_trace,
    get_trace_generator,
)

__all__ = [
    "ApplicationError",
    "ApplicationErrorCode",
    "map_parser_exception_to_application_error",
    "PolynomialQDegree2",
    "normalize_equation",
    "normalize_expression",
    "normalize_raw_equation",
    "DegenerateHostVerifier",
    "DegenerateSolveResult",
    "solve_exact_degenerate",
    "verify_degenerate_solution",
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
]
