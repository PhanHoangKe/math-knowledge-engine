"""Authoritative recursive-descent parser for the frozen P02A mathematical grammar.

EBNF Reference (PRODUCT-01 rev0.3.1):
    equation        ::= expression "=" expression ;
    expression      ::= [ add_op ] term { add_op term } ;
    add_op          ::= "+" | "-" ;
    term            ::= factor { mul_op factor } ;
    mul_op          ::= "*" | "/" ;
    factor          ::= power ;
    power           ::= primary [ "^" exponent ] ;
    exponent        ::= "0" | "1" | "2" ;
    primary         ::= integer_literal | variable | "(" expression ")" ;
    variable        ::= "x" ;
    integer_literal ::= digit { digit } ;
"""

from typing import List

from .tokens import Token, TokenType
from .errors import Span, ParserError, InputBoundsExceededError
from .lexer import tokenize
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

MAX_NESTING_DEPTH = 16


class Parser:
    """Deterministic, bounded mathematical parser."""

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
        """Parse an equation of the form: expression = expression."""
        left = self.parse_expression()

        if self.current.type != TokenType.EQUALS:
            raise ParserError(
                f"Expected '=' in equation, found {self.current.value!r}.",
                self.current.span,
            )
        self.advance()  # consume '='

        right = self.parse_expression()

        # Check for multiple equality signs
        if self.current.type == TokenType.EQUALS:
            raise ParserError(
                "Multiple '=' operators are forbidden in a single equation.",
                self.current.span,
            )

        # Check for unexpected trailing tokens
        if self.current.type != TokenType.EOF:
            raise ParserError(
                f"Unexpected trailing token {self.current.value!r} after equation.",
                self.current.span,
            )

        eq_span = Span(left.span.start, right.span.end)
        return Equation(left=left, right=right, span=eq_span)

    def parse_expression(self) -> ASTNode:
        """Parse: [ add_op ] term { add_op term }."""
        # Optional leading unary operator (+ or -)
        if self.current.type in {TokenType.PLUS, TokenType.MINUS}:
            op_tok = self.advance()
            term = self.parse_term()
            node: ASTNode = UnaryOp(
                op=op_tok.value,
                operand=term,
                span=Span(op_tok.span.start, term.span.end),
            )
        else:
            node = self.parse_term()

        # Binary addition / subtraction (left-associative)
        while self.current.type in {TokenType.PLUS, TokenType.MINUS}:
            op_tok = self.advance()
            right = self.parse_term()
            node = BinaryOp(
                op=op_tok.value,
                left=node,
                right=right,
                span=Span(node.span.start, right.span.end),
            )

        return node

    def parse_term(self) -> ASTNode:
        """Parse: factor { mul_op factor }."""
        node = self.parse_factor()

        # Binary multiplication / division (left-associative)
        while self.current.type in {TokenType.STAR, TokenType.SLASH}:
            op_tok = self.advance()
            right = self.parse_factor()
            node = BinaryOp(
                op=op_tok.value,
                left=node,
                right=right,
                span=Span(node.span.start, right.span.end),
            )

        return node

    def parse_factor(self) -> ASTNode:
        """Parse factor: power ::= primary [ "^" exponent ]."""
        base = self.parse_primary()

        if self.current.type == TokenType.CARET:
            caret_tok = self.advance()

            if self.current.type != TokenType.INTEGER:
                raise ParserError(
                    f"Expected non-negative integer exponent in {{0, 1, 2}} after '^', found {self.current.value!r}.",
                    self.current.span,
                )

            exp_tok = self.advance()
            val = int(exp_tok.value)
            if val not in {0, 1, 2}:
                raise ParserError(
                    f"Unsupported exponent value {val}. Phase P02A strictly restricts exponents to {{0, 1, 2}}.",
                    exp_tok.span,
                )

            exp_node = IntegerLiteral(value=val, span=exp_tok.span)
            return Power(
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


def parse(text: str) -> Equation:
    """Convenience entry point: tokenize and parse an equation string."""
    tokens = tokenize(text)
    parser = Parser(tokens, source_text=text)
    return parser.parse_equation()
