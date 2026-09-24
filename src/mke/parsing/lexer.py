"""Safe mathematical lexer with strict bounds and token whitelisting."""

from fractions import Fraction
from typing import List

from mke.parsing.exceptions import (
    CoefficientMagnitudeError,
    InputLengthExceededError,
    InvalidSyntaxError,
    OutOfScopeSyntaxError,
    TokenCountExceededError,
)
from mke.parsing.limits import ParserLimits, DEFAULT_LIMITS
from mke.parsing.tokens import Token, TokenKind

OUT_OF_SCOPE_FUNCTIONS = {
    "sqrt", "cbrt", "root",
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan",
    "log", "ln", "exp", "abs",
}

OUT_OF_SCOPE_VARIABLES = {
    "y", "z", "t", "u", "v", "w", "a", "b", "c", "d", "n", "m", "k",
}


class Lexer:
    """Scans raw mathematical strings into whitelisted tokens under strict resource limits."""

    def __init__(self, text: str, limits: ParserLimits = DEFAULT_LIMITS):
        self.text = text
        self.limits = limits
        self.pos = 0
        self.length = len(text)

        if self.length > limits.max_input_length:
            raise InputLengthExceededError(
                f"Input length {self.length} exceeds maximum allowed limit {limits.max_input_length}"
            )

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            if len(tokens) >= self.limits.max_tokens:
                raise TokenCountExceededError(
                    f"Token count exceeded limit {self.limits.max_tokens}"
                )

            ch = self.text[self.pos]

            if ch.isspace():
                self.pos += 1
                continue

            start_pos = self.pos

            # Number
            if ch.isdigit() or (ch == "." and self.pos + 1 < self.length and self.text[self.pos + 1].isdigit()):
                num_tok = self._scan_number(start_pos)
                tokens.append(num_tok)
                continue

            # Identifier (Variable 'x' or out-of-scope identifier)
            if ch.isalpha() or ch == "_":
                ident_tok = self._scan_identifier(start_pos)
                tokens.append(ident_tok)
                continue

            # Operators
            if ch == "+":
                tokens.append(Token(TokenKind.PLUS, "+", position=start_pos))
                self.pos += 1
            elif ch == "-":
                tokens.append(Token(TokenKind.MINUS, "-", position=start_pos))
                self.pos += 1
            elif ch == "*":
                if self.pos + 1 < self.length and self.text[self.pos + 1] == "*":
                    # Support ** as exponentiation ^
                    tokens.append(Token(TokenKind.CARET, "^", position=start_pos))
                    self.pos += 2
                else:
                    tokens.append(Token(TokenKind.STAR, "*", position=start_pos))
                    self.pos += 1
            elif ch == "/":
                tokens.append(Token(TokenKind.SLASH, "/", position=start_pos))
                self.pos += 1
            elif ch == "^":
                tokens.append(Token(TokenKind.CARET, "^", position=start_pos))
                self.pos += 1
            elif ch == "(":
                tokens.append(Token(TokenKind.LPAREN, "(", position=start_pos))
                self.pos += 1
            elif ch == ")":
                tokens.append(Token(TokenKind.RPAREN, ")", position=start_pos))
                self.pos += 1
            elif ch == "=":
                if self.pos + 1 < self.length and self.text[self.pos + 1] == "=":
                    # Support == as =
                    tokens.append(Token(TokenKind.EQUALS, "=", position=start_pos))
                    self.pos += 2
                else:
                    tokens.append(Token(TokenKind.EQUALS, "=", position=start_pos))
                    self.pos += 1
            # Out of scope operators
            elif ch in ("<", ">", "!"):
                raise OutOfScopeSyntaxError(
                    f"Relational / inequality operator '{ch}' is outside DEV-01 scope",
                    position=start_pos,
                )
            elif ch in (";", ":", ",", "[", "]", "{", "}", "&", "|", "~", "%", "@", "$", "`", "\"", "'"):
                raise OutOfScopeSyntaxError(
                    f"Unsupported character or operator '{ch}'",
                    position=start_pos,
                )
            else:
                raise InvalidSyntaxError(
                    f"Unexpected character: '{ch}'", position=start_pos
                )

        tokens.append(Token(TokenKind.EOF, position=self.pos))
        return tokens

    def _scan_number(self, start_pos: int) -> Token:
        has_dot = False
        while self.pos < self.length:
            c = self.text[self.pos]
            if c.isdigit():
                self.pos += 1
            elif c == "." and not has_dot:
                has_dot = True
                self.pos += 1
            else:
                break

        num_str = self.text[start_pos : self.pos]
        if has_dot:
            # Parse as exact decimal fraction
            parts = num_str.split(".")
            integer_part = int(parts[0]) if parts[0] else 0
            fractional_str = parts[1]
            if not fractional_str:
                raise InvalidSyntaxError(f"Invalid decimal literal '{num_str}'", position=start_pos)
            frac_denom = 10 ** len(fractional_str)
            frac_num = int(fractional_str)
            frac_val = Fraction(integer_part) + Fraction(frac_num, frac_denom)
        else:
            frac_val = Fraction(int(num_str), 1)

        if abs(frac_val.numerator) > self.limits.max_coefficient_magnitude or (
            frac_val.denominator > self.limits.max_coefficient_magnitude
        ):
            raise CoefficientMagnitudeError(
                f"Numeric constant '{num_str}' exceeds maximum magnitude limit {self.limits.max_coefficient_magnitude}",
                position=start_pos,
            )

        return Token(TokenKind.NUMBER, value=num_str, number_value=frac_val, position=start_pos)

    def _scan_identifier(self, start_pos: int) -> Token:
        while self.pos < self.length and (self.text[self.pos].isalnum() or self.text[self.pos] == "_"):
            self.pos += 1

        ident = self.text[start_pos : self.pos]

        if ident == "x":
            return Token(TokenKind.VARIABLE, value="x", position=start_pos)

        lower_ident = ident.lower()
        if lower_ident in OUT_OF_SCOPE_FUNCTIONS:
            raise OutOfScopeSyntaxError(
                f"Mathematical function '{ident}' is outside DEV-01 scope (radicals/transcendental functions not supported)",
                position=start_pos,
            )

        if lower_ident in OUT_OF_SCOPE_VARIABLES or len(ident) == 1:
            raise OutOfScopeSyntaxError(
                f"Variable '{ident}' is outside DEV-01 scope (only single variable 'x' is supported in DEV-01)",
                position=start_pos,
            )

        raise OutOfScopeSyntaxError(
            f"Identifier '{ident}' is outside DEV-01 scope",
            position=start_pos,
        )
