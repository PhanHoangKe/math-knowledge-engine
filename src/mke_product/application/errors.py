"""MKE MVP V1 Application Layer Error Taxonomy and Deterministic Exception Mapping.

Defines the typed application error codes and deterministic parser-exception
to application-error mapping. Zero human-readable string parsing is used.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from mke_product.core.errors import MKEProductError
from mke_product.parser.errors import (
    ImplicitMultiplicationError,
    InputBoundsExceededError,
    LexerError,
    MKEParserError,
    ParserError,
    Span,
    UnsupportedExponentError,
    UnsupportedSyntaxError,
    UnsupportedVariableError,
)


class ApplicationErrorCode(str, Enum):
    """Deterministic machine-readable error codes for the application intake & normalization pipeline."""
    SYNTAX_ERROR = "SYNTAX_ERROR"
    INPUT_LIMIT_EXCEEDED = "INPUT_LIMIT_EXCEEDED"
    UNSUPPORTED_SYNTAX = "UNSUPPORTED_SYNTAX"
    UNSUPPORTED_VARIABLE = "UNSUPPORTED_VARIABLE"
    IMPLICIT_MULTIPLICATION_UNSUPPORTED = "IMPLICIT_MULTIPLICATION_UNSUPPORTED"
    NON_POLYNOMIAL_INPUT = "NON_POLYNOMIAL_INPUT"
    DEGREE_OUT_OF_SCOPE = "DEGREE_OUT_OF_SCOPE"
    DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
    METHOD_NOT_APPLICABLE = "METHOD_NOT_APPLICABLE"
    METHOD_NOT_EXECUTABLE = "METHOD_NOT_EXECUTABLE"
    METHOD_EXECUTION_FAILED = "METHOD_EXECUTION_FAILED"
    DOMAIN_CONTRACT_ERROR = "DOMAIN_CONTRACT_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApplicationError(MKEProductError):
    """Typed application exception carrying machine error code, bilingual messages, and optional span."""

    def __init__(
        self,
        error_code: ApplicationErrorCode,
        message_vi: str,
        message_en: str,
        span: Optional[Span] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(f"[{error_code.value}] {message_en}")
        self.error_code = error_code
        self.message_vi = message_vi
        self.message_en = message_en
        self.span = span
        self.details = details or {}

    @property
    def span_tuple(self) -> Optional[Tuple[int, int]]:
        return self.span.to_tuple() if self.span is not None else None


def map_parser_exception_to_application_error(exc: Exception) -> ApplicationError:
    """Deterministically map parser exceptions to typed ApplicationError instances.

    Guarantees:
    - Zero human-readable message string matching.
    - Preserves source Span from parser exceptions.
    - Maps based purely on Python exception type hierarchy.
    """
    if isinstance(exc, UnsupportedVariableError):
        return ApplicationError(
            error_code=ApplicationErrorCode.UNSUPPORTED_VARIABLE,
            message_vi="Biến số không được hỗ trợ. MVP V1 chỉ hỗ trợ biến 'x'.",
            message_en="Unsupported variable in input. MVP V1 strictly supports only variable 'x'.",
            span=exc.span,
        )

    if isinstance(exc, UnsupportedSyntaxError):
        return ApplicationError(
            error_code=ApplicationErrorCode.UNSUPPORTED_SYNTAX,
            message_vi="Hàm số hoặc ký hiệu cú pháp không thuộc phạm vi đa thức bậc hai.",
            message_en="Unsupported syntax or transcendental function in input.",
            span=exc.span,
        )

    if isinstance(exc, UnsupportedExponentError):
        return ApplicationError(
            error_code=ApplicationErrorCode.DEGREE_OUT_OF_SCOPE,
            message_vi="Bậc của phương trình vượt quá giới hạn bậc hai (deg <= 2).",
            message_en="Exponent exceeds quadratic polynomial degree bound (deg <= 2).",
            span=exc.span,
        )

    if isinstance(exc, ImplicitMultiplicationError):
        return ApplicationError(
            error_code=ApplicationErrorCode.IMPLICIT_MULTIPLICATION_UNSUPPORTED,
            message_vi="Phép nhân ẩn không được hỗ trợ. Vui lòng viết rõ dấu nhân '*'.",
            message_en="Implicit multiplication is unsupported. Please use explicit '*' operator.",
            span=exc.span,
        )

    if isinstance(exc, InputBoundsExceededError):
        return ApplicationError(
            error_code=ApplicationErrorCode.INPUT_LIMIT_EXCEEDED,
            message_vi="Giới hạn độ dài chuỗi (256), token (64) hoặc độ sâu lồng (16) bị vượt quá.",
            message_en="Input bounds exceeded: max length 256, max tokens 64, or max nesting depth 16.",
            span=exc.span,
        )

    if isinstance(exc, ParserError):
        return ApplicationError(
            error_code=ApplicationErrorCode.SYNTAX_ERROR,
            message_vi="Cú pháp phương trình không hợp lệ.",
            message_en="Syntax error in mathematical equation.",
            span=exc.span,
        )

    if isinstance(exc, LexerError):
        return ApplicationError(
            error_code=ApplicationErrorCode.UNSUPPORTED_SYNTAX,
            message_vi="Ký tự hoặc biểu thức không hợp lệ trong đầu vào.",
            message_en="Illegal character or syntax in input.",
            span=exc.span,
        )

    if isinstance(exc, MKEParserError):
        return ApplicationError(
            error_code=ApplicationErrorCode.SYNTAX_ERROR,
            message_vi="Lỗi phân tích cú pháp biểu thức toán học.",
            message_en="Mathematical parsing error.",
            span=exc.span,
        )

    return ApplicationError(
        error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
        message_vi="Lỗi không xác định trong quá trình xử lý đầu vào.",
        message_en=f"Unhandled exception during intake: {exc}",
    )
