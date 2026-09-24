"""Safe recursive descent parser building unreduced mathematical AST."""

from typing import List

from mke.models.ast_nodes import (
    ASTNode,
    BinaryOpNode,
    EquationNode,
    NumberNode,
    UnaryOpNode,
    VariableNode,
)
from mke.parsing.exceptions import (
    ASTDepthExceededError,
    InvalidExponentError,
    InvalidSyntaxError,
    NodeCountExceededError,
)
from mke.parsing.lexer import Lexer
from mke.parsing.limits import ParserLimits, DEFAULT_LIMITS
from mke.parsing.tokens import Token, TokenKind


class Parser:
    """Parses token streams into an AST conforming to finite grammar and safety limits."""

    def __init__(self, tokens: List[Token], limits: ParserLimits = DEFAULT_LIMITS):
        self.tokens = tokens
        self.limits = limits
        self.pos = 0
        self.current_depth = 0
        self.total_nodes = 0

    @classmethod
    def from_text(cls, text: str, limits: ParserLimits = DEFAULT_LIMITS) -> "Parser":
        lexer = Lexer(text, limits=limits)
        tokens = lexer.tokenize()
        return cls(tokens, limits=limits)

    def parse_equation(self) -> EquationNode:
        """Parse a full equation containing an equals sign '='."""
        lhs = self._parse_expression()

        tok = self._current_token()
        if tok.kind != TokenKind.EQUALS:
            raise InvalidSyntaxError(
                f"Expected '=' in equation, found {tok.value or tok.kind.value}",
                position=tok.position,
            )
        self._advance()

        rhs = self._parse_expression()

        final_tok = self._current_token()
        if final_tok.kind != TokenKind.EOF:
            raise InvalidSyntaxError(
                f"Unexpected token after equation: '{final_tok.value or final_tok.kind.value}'",
                position=final_tok.position,
            )

        eq_node = EquationNode(lhs, rhs)
        self._check_tree_limits(eq_node)
        return eq_node

    def parse_expression(self) -> ASTNode:
        """Parse a mathematical expression."""
        expr = self._parse_expression()
        final_tok = self._current_token()
        if final_tok.kind != TokenKind.EOF:
            raise InvalidSyntaxError(
                f"Unexpected token after expression: '{final_tok.value or final_tok.kind.value}'",
                position=final_tok.position,
            )
        self._check_tree_limits(expr)
        return expr

    # --- Recursive descent grammar rules ---

    def _parse_expression(self) -> ASTNode:
        self.current_depth += 1
        if self.current_depth > self.limits.max_ast_depth:
            raise ASTDepthExceededError(
                f"AST depth {self.current_depth} exceeds maximum allowed depth {self.limits.max_ast_depth}"
            )
        try:
            node = self._parse_term()
            while self._current_token().kind in (TokenKind.PLUS, TokenKind.MINUS):
                op_tok = self._advance()
                op = op_tok.value
                right = self._parse_term()
                node = BinaryOpNode(op, node, right)
                self._increment_nodes()
            return node
        finally:
            self.current_depth -= 1

    def _parse_term(self) -> ASTNode:
        node = self._parse_unary()
        while self._current_token().kind in (TokenKind.STAR, TokenKind.SLASH):
            op_tok = self._advance()
            op = op_tok.value
            right = self._parse_unary()
            node = BinaryOpNode(op, node, right)
            self._increment_nodes()
        return node

    def _parse_unary(self) -> ASTNode:
        tok = self._current_token()
        if tok.kind in (TokenKind.PLUS, TokenKind.MINUS):
            self._advance()
            operand = self._parse_unary()
            self._increment_nodes()
            return UnaryOpNode(tok.value, operand)
        return self._parse_power()

    def _parse_power(self) -> ASTNode:
        node = self._parse_primary()
        if self._current_token().kind == TokenKind.CARET:
            op_tok = self._advance()
            # Right operand of exponentiation must be a non-negative integer within limits
            exp_node = self._parse_unary()
            if isinstance(exp_node, UnaryOpNode) and exp_node.op == "-" and isinstance(exp_node.operand, NumberNode):
                exp_int = -exp_node.operand.value.numerator
                raise InvalidExponentError(
                    f"Negative exponent '^{exp_int}' is not supported in polynomial scope. Use division '/' instead.",
                    position=op_tok.position,
                )
            # Validate exponent
            if not isinstance(exp_node, NumberNode) or exp_node.value.denominator != 1:
                raise InvalidExponentError(
                    f"Exponent must be an exact integer, got '{exp_node.to_math_string()}'",
                    position=op_tok.position,
                )
            exp_int = exp_node.value.numerator
            if exp_int < 0:
                raise InvalidExponentError(
                    f"Negative exponent '^{exp_int}' is not supported in polynomial scope. Use division '/' instead.",
                    position=op_tok.position,
                )
            if exp_int > self.limits.max_exponent:
                raise InvalidExponentError(
                    f"Exponent '^{exp_int}' exceeds maximum allowed exponent {self.limits.max_exponent}",
                    position=op_tok.position,
                )
            node = BinaryOpNode("^", node, exp_node)
            self._increment_nodes()
        return node

    def _parse_primary(self) -> ASTNode:
        tok = self._current_token()
        if tok.kind == TokenKind.NUMBER:
            self._advance()
            self._increment_nodes()
            return NumberNode(tok.number_value, raw_literal=tok.value)
        elif tok.kind == TokenKind.VARIABLE:
            self._advance()
            self._increment_nodes()
            return VariableNode(tok.value)
        elif tok.kind == TokenKind.LPAREN:
            self._advance()
            expr = self._parse_expression()
            close_tok = self._current_token()
            if close_tok.kind != TokenKind.RPAREN:
                raise InvalidSyntaxError(
                    f"Expected closing parenthesis ')', found {close_tok.value or close_tok.kind.value}",
                    position=close_tok.position,
                )
            self._advance()
            return expr
        else:
            raise InvalidSyntaxError(
                f"Unexpected token in primary expression: {tok.value or tok.kind.value}",
                position=tok.position,
            )

    # --- Internal helpers ---

    def _current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenKind.EOF, position=len(self.tokens))

    def _advance(self) -> Token:
        tok = self._current_token()
        self.pos += 1
        return tok

    def _increment_nodes(self) -> None:
        self.total_nodes += 1
        if self.total_nodes > self.limits.max_node_count:
            raise NodeCountExceededError(
                f"AST node count exceeded limit of {self.limits.max_node_count}"
            )

    def _check_tree_limits(self, root: ASTNode) -> None:
        depth = root.depth()
        if depth > self.limits.max_ast_depth:
            raise ASTDepthExceededError(
                f"AST depth {depth} exceeds maximum allowed depth {self.limits.max_ast_depth}"
            )
        count = root.node_count()
        if count > self.limits.max_node_count:
            raise NodeCountExceededError(
                f"AST node count {count} exceeds maximum allowed limit {self.limits.max_node_count}"
            )
