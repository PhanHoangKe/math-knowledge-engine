"""
CAS Expression, Equation, System, and Inequality Parser.

Uses safe deterministic tokenization and recursive descent parsing,
guaranteeing that input syntax is strictly checked and no arbitrary Python code
or builtins can enter the computational pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from mke_product.parser.ast import (
    ASTNode,
    BinaryOp,
    Equation,
    Group,
    IntegerLiteral,
    Power,
    UnaryOp,
    Variable,
)
from mke_product.parser.errors import (
    ImplicitMultiplicationError,
    InputBoundsExceededError,
    LexerError,
    ParserError,
    Span,
)

MAX_INPUT_LENGTH = 4096
MAX_TOKEN_COUNT = 512
MAX_NESTING_DEPTH = 16


@dataclass(frozen=True, slots=True)
class CASPower(ASTNode):
    """Power expression with arbitrary non-negative integer exponent."""
    base: ASTNode
    exponent: IntegerLiteral
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.base.walk()
        yield from self.exponent.walk()

    def variables(self) -> Set[str]:
        return self.base.variables()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Power",
            "base": self.base.to_dict(),
            "exponent": self.exponent.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"Power({self.base!r}, {self.exponent!r})"


@dataclass(frozen=True, slots=True)
class Inequality(ASTNode):
    """Relational inequality expression (e.g. x^2 - 4 > 0, 2*x + 3 <= 7)."""
    left: ASTNode
    op: str  # '<', '<=', '>', '>=', '≤', '≥'
    right: ASTNode
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.left.walk()
        yield from self.right.walk()

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Inequality",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"Inequality({self.left!r} {self.op} {self.right!r})"


@dataclass(frozen=True, slots=True)
class LinearSystem(ASTNode):
    """System of linear equations (e.g. 2*x + 3*y = 5, x - y = 1)."""
    equations: List[Equation]
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self
        for eq in self.equations:
            yield from eq.walk()

    def variables(self) -> Set[str]:
        v: Set[str] = set()
        for eq in self.equations:
            v.update(eq.variables())
        return v

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "LinearSystem",
            "equations": [eq.to_dict() for eq in self.equations],
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"LinearSystem({self.equations!r})"


class CASTokenType(Enum):
    """Token types supported in general CAS mathematical input."""
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
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    COMMA = auto()
    SEMICOLON = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class CASToken:
    """Immutable CAS token with type, value, and source span."""
    type: CASTokenType
    value: str
    span: Span

    def __repr__(self) -> str:
        return f"CASToken({self.type.name}, {self.value!r}, {self.span})"


def tokenize_cas(text: str) -> List[CASToken]:
    """Strictly tokenize CAS input into a list of CASTokens ending with EOF."""
    if len(text) > MAX_INPUT_LENGTH:
        raise InputBoundsExceededError(
            f"Input length ({len(text)}) exceeds maximum allowed ({MAX_INPUT_LENGTH} characters)."
        )

    tokens: List[CASToken] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch in " \t\r\n":
            i += 1
            continue

        start = i

        # Numbers
        if "0" <= ch <= "9":
            while i < n and "0" <= text[i] <= "9":
                i += 1
            val = text[start:i]
            tokens.append(CASToken(CASTokenType.INTEGER, val, Span(start, i)))
            continue

        # Single letter variables [a-zA-Z]
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            var_name = ch
            i += 1
            tokens.append(CASToken(CASTokenType.VARIABLE, var_name, Span(start, i)))
            continue

        # Relational 2-char operators: <=, >=
        if ch == "<" and i + 1 < n and text[i + 1] == "=":
            tokens.append(CASToken(CASTokenType.LE, "<=", Span(start, start + 2)))
            i += 2
            continue
        if ch == ">" and i + 1 < n and text[i + 1] == "=":
            tokens.append(CASToken(CASTokenType.GE, ">=", Span(start, start + 2)))
            i += 2
            continue

        # Single-char relational operators
        if ch == "≤":
            tokens.append(CASToken(CASTokenType.LE, "<=", Span(start, start + 1)))
            i += 1
            continue
        if ch == "≥":
            tokens.append(CASToken(CASTokenType.GE, ">=", Span(start, start + 1)))
            i += 1
            continue
        if ch == "<":
            tokens.append(CASToken(CASTokenType.LT, "<", Span(start, start + 1)))
            i += 1
            continue
        if ch == ">":
            tokens.append(CASToken(CASTokenType.GT, ">", Span(start, start + 1)))
            i += 1
            continue

        # Arithmetic operators & punctuation
        if ch == "+":
            tokens.append(CASToken(CASTokenType.PLUS, "+", Span(start, start + 1)))
            i += 1
            continue
        if ch == "-":
            tokens.append(CASToken(CASTokenType.MINUS, "-", Span(start, start + 1)))
            i += 1
            continue
        if ch == "*":
            tokens.append(CASToken(CASTokenType.STAR, "*", Span(start, start + 1)))
            i += 1
            continue
        if ch == "/":
            tokens.append(CASToken(CASTokenType.SLASH, "/", Span(start, start + 1)))
            i += 1
            continue
        if ch == "^":
            tokens.append(CASToken(CASTokenType.CARET, "^", Span(start, start + 1)))
            i += 1
            continue
        if ch == "(":
            tokens.append(CASToken(CASTokenType.LPAREN, "(", Span(start, start + 1)))
            i += 1
            continue
        if ch == ")":
            tokens.append(CASToken(CASTokenType.RPAREN, ")", Span(start, start + 1)))
            i += 1
            continue
        if ch == "=":
            tokens.append(CASToken(CASTokenType.EQUALS, "=", Span(start, start + 1)))
            i += 1
            continue
        if ch == ",":
            tokens.append(CASToken(CASTokenType.COMMA, ",", Span(start, start + 1)))
            i += 1
            continue
        if ch == ";":
            tokens.append(CASToken(CASTokenType.SEMICOLON, ";", Span(start, start + 1)))
            i += 1
            continue
        if ch == "[":
            tokens.append(CASToken(CASTokenType.LBRACKET, "[", Span(start, start + 1)))
            i += 1
            continue
        if ch == "]":
            tokens.append(CASToken(CASTokenType.RBRACKET, "]", Span(start, start + 1)))
            i += 1
            continue

        raise LexerError(
            f"Invalid or unsupported character {ch!r} at position {start}.",
            Span(start, start + 1),
        )

    eof_span = Span(n, n)
    tokens.append(CASToken(CASTokenType.EOF, "", eof_span))

    if len(tokens) > MAX_TOKEN_COUNT:
        raise InputBoundsExceededError(
            f"Token count ({len(tokens)}) exceeds maximum limit of {MAX_TOKEN_COUNT}."
        )

    # Check for implicit multiplication (e.g. 2x, 1/2x, xy, x(x+1), (x)(y))
    for idx in range(len(tokens) - 1):
        curr_t = tokens[idx]
        next_t = tokens[idx + 1]

        if curr_t.type == CASTokenType.INTEGER and next_t.type in (CASTokenType.VARIABLE, CASTokenType.LPAREN):
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected between '{curr_t.value}' and '{next_t.value}'. Use explicit '*' (e.g. '{curr_t.value}*{next_t.value}').",
                Span(curr_t.span.start, next_t.span.end),
            )
        if curr_t.type == CASTokenType.VARIABLE and next_t.type in (CASTokenType.VARIABLE, CASTokenType.LPAREN):
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected between '{curr_t.value}' and '{next_t.value}'. Use explicit '*' (e.g. '{curr_t.value}*{next_t.value}').",
                Span(curr_t.span.start, next_t.span.end),
            )
        if curr_t.type == CASTokenType.RPAREN and next_t.type in (CASTokenType.VARIABLE, CASTokenType.LPAREN, CASTokenType.INTEGER):
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected after ')'. Use explicit '*'.",
                Span(curr_t.span.start, next_t.span.end),
            )

    return tokens


class CASParser:
    """Safe, bounded recursive descent AST parser for general CAS operations."""

    def __init__(self, tokens: List[CASToken], source_text: str = "") -> None:
        self._tokens = tokens
        self._source_text = source_text
        self._pos = 0
        self._nesting_depth = 0

    @property
    def current(self) -> CASToken:
        return self._tokens[self._pos]

    def advance(self) -> CASToken:
        tok = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def parse_equation(self) -> Equation:
        """Parse equation: expression = expression."""
        left = self.parse_expression()
        if self.current.type != CASTokenType.EQUALS:
            raise ParserError(
                f"Expected '=' separating equation sides at position {self.current.span.start}.",
                self.current.span,
            )
        self.advance()
        right = self.parse_expression()
        return Equation(
            left=left,
            right=right,
            span=Span(left.span.start, right.span.end),
        )

    def parse_inequality(self) -> Inequality:
        """Parse inequality: expression (< | <= | > | >= | ≤ | ≥) expression."""
        left = self.parse_expression()
        if self.current.type not in (CASTokenType.LT, CASTokenType.LE, CASTokenType.GT, CASTokenType.GE):
            raise ParserError(
                f"Expected inequality operator (<, <=, >, >=) at position {self.current.span.start}.",
                self.current.span,
            )
        op_tok = self.advance()
        right = self.parse_expression()
        if self.current.type != CASTokenType.EOF:
            raise ParserError(
                f"Unexpected token {self.current.value!r} after inequality end at position {self.current.span.start}.",
                self.current.span,
            )
        return Inequality(
            left=left,
            op=op_tok.value,
            right=right,
            span=Span(left.span.start, right.span.end),
        )

    def parse_expression(self) -> ASTNode:
        """Parse expression: [ add_op ] term { add_op term }."""
        tok = self.current
        if tok.type == CASTokenType.PLUS:
            self.advance()
            term = self.parse_term()
            node = UnaryOp(op="+", operand=term, span=Span(tok.span.start, term.span.end))
        elif tok.type == CASTokenType.MINUS:
            self.advance()
            term = self.parse_term()
            node = UnaryOp(op="-", operand=term, span=Span(tok.span.start, term.span.end))
        else:
            node = self.parse_term()

        while self.current.type in (CASTokenType.PLUS, CASTokenType.MINUS):
            op_tok = self.advance()
            op = "+" if op_tok.type == CASTokenType.PLUS else "-"
            right = self.parse_term()
            node = BinaryOp(
                op=op,
                left=node,
                right=right,
                span=Span(node.span.start, right.span.end),
            )
        return node

    def parse_term(self) -> ASTNode:
        """Parse term: factor { mul_op factor }."""
        node = self.parse_factor()
        while self.current.type in (CASTokenType.STAR, CASTokenType.SLASH):
            op_tok = self.advance()
            op = "*" if op_tok.type == CASTokenType.STAR else "/"
            right = self.parse_factor()
            node = BinaryOp(
                op=op,
                left=node,
                right=right,
                span=Span(node.span.start, right.span.end),
            )
        return node

    def parse_factor(self) -> ASTNode:
        """Parse factor: power ::= primary [ "^" exponent ]."""
        base = self.parse_primary()
        if self.current.type == CASTokenType.CARET:
            self.advance()
            if self.current.type != CASTokenType.INTEGER:
                raise ParserError(
                    f"Expected non-negative integer exponent after '^', found {self.current.value!r}.",
                    self.current.span,
                )
            exp_tok = self.advance()
            exp_val = int(exp_tok.value)
            exp_node = IntegerLiteral(value=exp_val, span=exp_tok.span)
            if exp_val in (0, 1, 2):
                return Power(
                    base=base,
                    exponent=exp_node,
                    span=Span(base.span.start, exp_tok.span.end),
                )
            return CASPower(
                base=base,
                exponent=exp_node,
                span=Span(base.span.start, exp_tok.span.end),
            )
        return base

    def parse_primary(self) -> ASTNode:
        """Parse primary: integer_literal | variable | "(" expression ")"."""
        tok = self.current
        if tok.type == CASTokenType.INTEGER:
            self.advance()
            return IntegerLiteral(value=int(tok.value), span=tok.span)

        if tok.type == CASTokenType.VARIABLE:
            self.advance()
            return Variable(name=tok.value, span=tok.span)

        if tok.type == CASTokenType.LPAREN:
            lparen_span = tok.span
            self.advance()
            self._nesting_depth += 1
            if self._nesting_depth > MAX_NESTING_DEPTH:
                raise InputBoundsExceededError(
                    f"Parentheses nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                    lparen_span,
                )

            inner = self.parse_expression()
            if self.current.type != CASTokenType.RPAREN:
                raise ParserError(
                    f"Expected matching closing ')' for '(' at position {lparen_span.start}.",
                    self.current.span,
                )
            rparen_tok = self.advance()
            self._nesting_depth -= 1
            return Group(
                inner=inner,
                span=Span(lparen_span.start, rparen_tok.span.end),
            )

        raise ParserError(
            f"Unexpected token {tok.value!r} at position {tok.span.start}; expected integer, variable, or '('.",
            tok.span,
        )


def parse_cas_expression(text: str) -> ASTNode:
    """Parse a single CAS mathematical expression."""
    tokens = tokenize_cas(text)
    parser = CASParser(tokens, source_text=text)
    node = parser.parse_expression()
    if parser.current.type != CASTokenType.EOF:
        raise ParserError(
            f"Unexpected trailing tokens at position {parser.current.span.start}.",
            parser.current.span,
        )
    return node


def parse_cas_equation(text: str) -> Equation:
    """Parse a single CAS mathematical equation (left = right)."""
    tokens = tokenize_cas(text)
    parser = CASParser(tokens, source_text=text)
    eq = parser.parse_equation()
    if parser.current.type != CASTokenType.EOF:
        raise ParserError(
            f"Unexpected trailing tokens after equation at position {parser.current.span.start}.",
            parser.current.span,
        )
    return eq


def parse_cas_inequality(text: str) -> Inequality:
    """Parse a single CAS mathematical inequality (e.g. x^2 - 4 > 0)."""
    tokens = tokenize_cas(text)
    parser = CASParser(tokens, source_text=text)
    return parser.parse_inequality()


def parse_cas_system(text: str) -> LinearSystem:
    """Parse a 2x2 system of linear equations separated by comma, semicolon, or newline."""
    clean_text = text.strip()
    if clean_text.startswith("[") and clean_text.endswith("]"):
        clean_text = clean_text[1:-1].strip()

    # Split on top-level commas/semicolons/newlines
    parts: List[str] = []
    current_part: List[str] = []
    depth = 0
    for ch in clean_text:
        if ch in "([":
            depth += 1
            current_part.append(ch)
        elif ch in ")]":
            depth = max(0, depth - 1)
            current_part.append(ch)
        elif ch in (",", ";", "\n") and depth == 0:
            part_str = "".join(current_part).strip()
            if part_str:
                parts.append(part_str)
            current_part = []
        else:
            current_part.append(ch)
    if current_part:
        part_str = "".join(current_part).strip()
        if part_str:
            parts.append(part_str)

    if len(parts) != 2:
        raise ParserError(
            f"2x2 linear equation system requires exactly 2 equations separated by comma or semicolon, got {len(parts)}.",
            Span(0, len(text)),
        )

    equations: List[Equation] = []
    for p in parts:
        eq = parse_cas_equation(p)
        equations.append(eq)

    return LinearSystem(
        equations=equations,
        span=Span(0, len(text)),
    )
