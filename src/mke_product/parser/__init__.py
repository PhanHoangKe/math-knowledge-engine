"""Mathematical lexer, parser, and immutable AST package for MKE Product."""

from .tokens import Token, TokenType
from .errors import (
    Span,
    MKEParserError,
    LexerError,
    ParserError,
    ImplicitMultiplicationError,
    InputBoundsExceededError,
)
from .ast import (
    ASTNode,
    IntegerLiteral,
    Variable,
    Group,
    UnaryOp,
    BinaryOp,
    Power,
    Equation,
)
from .lexer import tokenize, MAX_INPUT_LENGTH, MAX_TOKEN_COUNT
from .parser import Parser, parse, MAX_NESTING_DEPTH

__all__ = [
    "Token",
    "TokenType",
    "Span",
    "MKEParserError",
    "LexerError",
    "ParserError",
    "ImplicitMultiplicationError",
    "InputBoundsExceededError",
    "ASTNode",
    "IntegerLiteral",
    "Variable",
    "Group",
    "UnaryOp",
    "BinaryOp",
    "Power",
    "Equation",
    "tokenize",
    "parse",
    "Parser",
    "MAX_INPUT_LENGTH",
    "MAX_TOKEN_COUNT",
    "MAX_NESTING_DEPTH",
]
