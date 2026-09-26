"""Token definitions and lexical primitives for the mathematical parser."""

from enum import Enum, auto
from typing import NamedTuple
from .errors import Span


class TokenType(Enum):
    """Enumeration of all supported mathematical token types."""
    INTEGER = auto()
    VARIABLE = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    LPAREN = auto()
    RPAREN = auto()
    EQUALS = auto()
    EOF = auto()


class Token(NamedTuple):
    """Immutable token with source span tracking."""
    type: TokenType
    value: str
    span: Span

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.span})"
