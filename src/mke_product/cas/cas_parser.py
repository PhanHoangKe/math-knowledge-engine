"""
CAS Expression and Equation Parser with arbitrary non-negative integer exponents.

Uses the frozen MKE lexer for tokenization, guaranteeing that input syntax
is strictly checked and no arbitrary Python code/builtins can enter the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Set

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
    InputBoundsExceededError,
    ParserError,
    Span,
)
from mke_product.parser.lexer import tokenize
from mke_product.parser.tokens import Token, TokenType

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


class CASParser:
    """Safe, bounded AST parser for general CAS expressions and equations."""

    def __init__(self, tokens: List[Token], source_text: str = "") -> None:
        self._tokens = tokens
        self._source_text = source_text
        self._pos = 0
        self._nesting_depth = 0

    @property
    def current(self) -> Token:
        return self._tokens[self._pos]

    def advance(self) -> Token:
        tok = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def parse_equation(self) -> Equation:
        """Parse equation: expression = expression."""
        left = self.parse_expression()
        if self.current.type != TokenType.EQUALS:
            raise ParserError(
                f"Expected '=' separating equation sides at position {self.current.span.start}.",
                self.current.span,
            )
        eq_tok = self.advance()
        right = self.parse_expression()
        if self.current.type != TokenType.EOF:
            raise ParserError(
                f"Unexpected token {self.current.value!r} after equation end at position {self.current.span.start}.",
                self.current.span,
            )
        return Equation(
            left=left,
            right=right,
            span=Span(left.span.start, right.span.end),
        )

    def parse_expression(self) -> ASTNode:
        """Parse expression: [ add_op ] term { add_op term }."""
        tok = self.current
        if tok.type == TokenType.PLUS:
            self.advance()
            term = self.parse_term()
            node = UnaryOp(op="+", operand=term, span=Span(tok.span.start, term.span.end))
        elif tok.type == TokenType.MINUS:
            self.advance()
            term = self.parse_term()
            node = UnaryOp(op="-", operand=term, span=Span(tok.span.start, term.span.end))
        else:
            node = self.parse_term()

        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            op = "+" if op_tok.type == TokenType.PLUS else "-"
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
        while self.current.type in (TokenType.STAR, TokenType.SLASH):
            op_tok = self.advance()
            op = "*" if op_tok.type == TokenType.STAR else "/"
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
        if self.current.type == TokenType.CARET:
            self.advance()
            if self.current.type != TokenType.INTEGER:
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
        if tok.type == TokenType.INTEGER:
            self.advance()
            return IntegerLiteral(value=int(tok.value), span=tok.span)

        if tok.type == TokenType.VARIABLE:
            self.advance()
            return Variable(name="x", span=tok.span)

        if tok.type == TokenType.LPAREN:
            lparen_span = tok.span
            self.advance()
            self._nesting_depth += 1
            if self._nesting_depth > MAX_NESTING_DEPTH:
                raise InputBoundsExceededError(
                    f"Parentheses nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                    lparen_span,
                )

            inner = self.parse_expression()
            if self.current.type != TokenType.RPAREN:
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
            f"Unexpected token {tok.value!r} at position {tok.span.start}; expected integer, 'x', or '('.",
            tok.span,
        )


def parse_cas_expression(text: str) -> ASTNode:
    """Parse expression with arbitrary integer exponents."""
    tokens = tokenize(text)
    parser = CASParser(tokens, source_text=text)
    node = parser.parse_expression()
    if parser.current.type != TokenType.EOF:
        raise ParserError(
            f"Unexpected trailing tokens at position {parser.current.span.start}.",
            parser.current.span,
        )
    return node


def parse_cas_equation(text: str) -> Equation:
    """Parse equation with arbitrary integer exponents."""
    tokens = tokenize(text)
    parser = CASParser(tokens, source_text=text)
    return parser.parse_equation()
