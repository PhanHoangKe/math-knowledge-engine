"""MKE MVP V1 Application Layer.

Orchestrates user intake, bounded AST normalization, method selection, and trace execution.
"""

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

__all__ = [
    "ApplicationError",
    "ApplicationErrorCode",
    "map_parser_exception_to_application_error",
    "PolynomialQDegree2",
    "normalize_equation",
    "normalize_expression",
    "normalize_raw_equation",
]
