"""Typed error hierarchy for lexical and syntactic mathematical parsing."""

from dataclasses import dataclass
from typing import Optional, Tuple
from ..core.errors import MKEProductError


@dataclass(frozen=True, slots=True)
class Span:
    """Immutable character span [start, end) within source text."""
    start: int
    end: int

    def __repr__(self) -> str:
        return f"Span({self.start}, {self.end})"

    def to_tuple(self) -> Tuple[int, int]:
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
