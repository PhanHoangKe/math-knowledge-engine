"""Deterministic lexer for mathematical equations.

Enforces:
- ASCII integer literals, single variable 'x'.
- Operators +, -, *, /, ^.
- Parentheses (, ) and equation equals =.
- Rejection of implicit multiplication (2x, 1/2x, x(x+1), (x)(x+1), etc.).
- Bounded input length and token count.
- Accurate source spans for every token.
"""

from typing import List

from .tokens import Token, TokenType
from .errors import (
    Span,
    LexerError,
    ImplicitMultiplicationError,
    InputBoundsExceededError,
)

MAX_INPUT_LENGTH = 256
MAX_TOKEN_COUNT = 64


def tokenize(text: str) -> List[Token]:
    """Tokenize mathematical input string into a sequence of Tokens ending with EOF.

    Raises:
        InputBoundsExceededError: if input exceeds size or token limits.
        LexerError: if invalid characters or malformed tokens are encountered.
        ImplicitMultiplicationError: if implicit multiplication is detected.
    """
    if len(text) > MAX_INPUT_LENGTH:
        raise InputBoundsExceededError(
            f"Input length {len(text)} exceeds maximum allowed limit of {MAX_INPUT_LENGTH} characters."
        )

    tokens: List[Token] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Whitespace
        if ch.isspace():
            i += 1
            continue

        start = i

        # Digits / Integer literals
        if ch.isdigit():
            while i < n and text[i].isdigit():
                i += 1
            val = text[start:i]
            tokens.append(Token(TokenType.INTEGER, val, Span(start, i)))
            continue

        # Single variable 'x'
        if ch == "x":
            tokens.append(Token(TokenType.VARIABLE, "x", Span(start, start + 1)))
            i += 1
            continue

        # Operators and punctuation
        if ch == "+":
            tokens.append(Token(TokenType.PLUS, "+", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "-":
            tokens.append(Token(TokenType.MINUS, "-", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "*":
            tokens.append(Token(TokenType.STAR, "*", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "/":
            tokens.append(Token(TokenType.SLASH, "/", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "^":
            tokens.append(Token(TokenType.CARET, "^", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "(":
            tokens.append(Token(TokenType.LPAREN, "(", Span(start, start + 1)))
            i += 1
            continue
        elif ch == ")":
            tokens.append(Token(TokenType.RPAREN, ")", Span(start, start + 1)))
            i += 1
            continue
        elif ch == "=":
            tokens.append(Token(TokenType.EQUALS, "=", Span(start, start + 1)))
            i += 1
            continue

        # Any other character is invalid
        raise LexerError(
            f"Illegal character {ch!r} at position {start}.",
            Span(start, start + 1),
        )

    # Check token count limit (excluding EOF)
    if len(tokens) > MAX_TOKEN_COUNT:
        raise InputBoundsExceededError(
            f"Token count {len(tokens)} exceeds maximum allowed limit of {MAX_TOKEN_COUNT} tokens."
        )

    # Check for implicit multiplication between adjacent tokens
    # Left token in {INTEGER, VARIABLE, RPAREN} followed by right token in {INTEGER, VARIABLE, LPAREN}
    IMPLICIT_LEFT = {TokenType.INTEGER, TokenType.VARIABLE, TokenType.RPAREN}
    IMPLICIT_RIGHT = {TokenType.INTEGER, TokenType.VARIABLE, TokenType.LPAREN}

    for idx in range(len(tokens) - 1):
        t_left = tokens[idx]
        t_right = tokens[idx + 1]
        if t_left.type in IMPLICIT_LEFT and t_right.type in IMPLICIT_RIGHT:
            combined_span = Span(t_left.span.start, t_right.span.end)
            raise ImplicitMultiplicationError(
                f"Ambiguous implicit multiplication between '{t_left.value}' and '{t_right.value}' is rejected; "
                f"explicit '*' is required.",
                combined_span,
            )

    tokens.append(Token(TokenType.EOF, "", Span(n, n)))
    return tokens
