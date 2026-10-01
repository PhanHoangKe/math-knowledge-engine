"""MKE MVP V1 Application Layer.

Orchestrates user intake, bounded AST normalization, method selection,
independent verification, and discriminated DTO state machine generation.
"""

from .degenerate import (
    DegenerateHostVerifier,
    DegenerateSolveResult,
    solve_exact_degenerate,
    verify_degenerate_solution,
)
from .dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    CanonicalDegenerateProblemView,
    CanonicalProblemUnion,
    CanonicalQuadraticProblemView,
    DegenerateSolutionView,
    ErrorResponse,
    InputPayloadUnion,
    MethodOptionView,
    NoExecutionReasonCode,
    RawEquationInput,
    SolvedResponse,
    SolveRequest,
    SolveResponseUnion,
    VerifiedSolutionView,
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
from .orchestrator import (
    format_canonical_source_equation,
    format_equation_latex,
    solve_request,
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
    # Errors & Mapping
    "ApplicationError",
    "ApplicationErrorCode",
    "map_parser_exception_to_application_error",
    # Normalizer
    "PolynomialQDegree2",
    "normalize_equation",
    "normalize_expression",
    "normalize_raw_equation",
    # Degenerate
    "DegenerateHostVerifier",
    "DegenerateSolveResult",
    "solve_exact_degenerate",
    "verify_degenerate_solution",
    # Solution Traces
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
    # DTOs & State Machine
    "RawEquationInput",
    "CanonicalCoefficientInput",
    "InputPayloadUnion",
    "SolveRequest",
    "CanonicalQuadraticProblemView",
    "CanonicalDegenerateProblemView",
    "CanonicalProblemUnion",
    "MethodOptionView",
    "VerifiedSolutionView",
    "DegenerateSolutionView",
    "NoExecutionReasonCode",
    "SolvedResponse",
    "AnalyzedNoExecutionResponse",
    "ErrorResponse",
    "SolveResponseUnion",
    # Orchestrator
    "solve_request",
    "format_equation_latex",
    "format_canonical_source_equation",
]
