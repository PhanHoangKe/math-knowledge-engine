"""Token definitions for safe mathematical scanning."""

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Optional


class TokenKind(str, Enum):
    NUMBER = "NUMBER"
    VARIABLE = "VARIABLE"
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    CARET = "CARET"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EQUALS = "EQUALS"
    EOF = "EOF"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: Optional[str] = None
    number_value: Optional[Fraction] = None
    position: int = 0
