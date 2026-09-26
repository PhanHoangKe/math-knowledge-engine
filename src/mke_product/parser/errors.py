"""Typed error hierarchy for lexical and syntactic mathematical parsing."""

from typing import Optional
from ..core.errors import MKEProductError


class Span:
    """Character span [start, end) within source text."""

    __slots__ = ("start", "end")

    def __init__(self, start: int, end: int) -> None:
        self.start = start
        self.end = end

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Span):
            return False
        return self.start == other.start and self.end == other.end

    def __repr__(self) -> str:
        return f"Span({self.start}, {self.end})"

    def to_tuple(self) -> tuple[int, int]:
        return (self.start, self.end)


class MKEParserError(MKEProductError):
    """Base exception for all parsing and tokenization failures."""

    def __init__(self, message: str, span: Optional[Span] = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span

    def __str__(self) -> str:
        if self.span is not None:
            return f"[{self.span.start}:{self.span.end}] {self.message}"
        return self.message


class LexerError(MKEParserError):
    """Raised when encountering illegal characters or malformed tokens."""
    pass


class ParserError(MKEParserError):
    """Raised on grammatical violations or unexpected tokens."""
    pass


class ImplicitMultiplicationError(ParserError):
    """Raised when implicit multiplication (e.g., '2x', '1/2x', '(x)(x+1)') is encountered."""
    pass


class InputBoundsExceededError(MKEParserError):
    """Raised when input length, token count, or nesting depth limits are exceeded."""
    pass
