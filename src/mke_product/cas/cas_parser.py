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
    AbsoluteValue,
    ASTNode,
    BinaryOp,
    Equation,
    FunctionCall,
    Group,
    IntegerLiteral,
    NamedConstant,
    Power,
    Radical,
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
    """Power expression with arbitrary exponent (IntegerLiteral or general ASTNode)."""
    base: ASTNode
    exponent: ASTNode
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.base.walk()
        yield from self.exponent.walk()

    def variables(self) -> Set[str]:
        return self.base.variables() | self.exponent.variables()

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
    UNDERSCORE = auto()
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
    LBRACE = auto()
    RBRACE = auto()
    SQRT = auto()
    ABS = auto()
    SIN = auto()
    COS = auto()
    TAN = auto()
    EXP = auto()
    LOG = auto()
    LN = auto()
    PI = auto()
    E_CONST = auto()
    PIPE = auto()
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

        # LaTeX commands
        if text.startswith("\\sqrt", i):
            tokens.append(CASToken(CASTokenType.SQRT, "\\sqrt", Span(start, start + 5)))
            i += 5
            continue
        if text.startswith("\\sin", i):
            tokens.append(CASToken(CASTokenType.SIN, "\\sin", Span(start, start + 4)))
            i += 4
            continue
        if text.startswith("\\cos", i):
            tokens.append(CASToken(CASTokenType.COS, "\\cos", Span(start, start + 4)))
            i += 4
            continue
        if text.startswith("\\tan", i):
            tokens.append(CASToken(CASTokenType.TAN, "\\tan", Span(start, start + 4)))
            i += 4
            continue
        if text.startswith("\\exp", i):
            tokens.append(CASToken(CASTokenType.EXP, "\\exp", Span(start, start + 4)))
            i += 4
            continue
        if text.startswith("\\log", i):
            tokens.append(CASToken(CASTokenType.LOG, "\\log", Span(start, start + 4)))
            i += 4
            continue
        if text.startswith("\\ln", i):
            tokens.append(CASToken(CASTokenType.LN, "\\ln", Span(start, start + 3)))
            i += 3
            continue
        if text.startswith("\\pi", i):
            tokens.append(CASToken(CASTokenType.PI, "\\pi", Span(start, start + 3)))
            i += 3
            continue

        # Named mathematical functions & constants (ASCII)
        if text.startswith("sqrt", i) and (i + 4 >= n or not (text[i + 4].isalnum() or text[i + 4] == "_")):
            tokens.append(CASToken(CASTokenType.SQRT, "sqrt", Span(start, start + 4)))
            i += 4
            continue

        if text.startswith("abs", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.ABS, "abs", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("sin", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.SIN, "sin", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("cos", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.COS, "cos", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("tan", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.TAN, "tan", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("exp", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.EXP, "exp", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("log", i) and (i + 3 >= n or not (text[i + 3].isalnum() or text[i + 3] == "_")):
            tokens.append(CASToken(CASTokenType.LOG, "log", Span(start, start + 3)))
            i += 3
            continue

        if text.startswith("ln", i) and (i + 2 >= n or not (text[i + 2].isalnum() or text[i + 2] == "_")):
            tokens.append(CASToken(CASTokenType.LN, "ln", Span(start, start + 2)))
            i += 2
            continue

        if text.startswith("pi", i) and (i + 2 >= n or not (text[i + 2].isalnum() or text[i + 2] == "_")):
            tokens.append(CASToken(CASTokenType.PI, "pi", Span(start, start + 2)))
            i += 2
            continue

        # Mathematical constant e (Euler's number)
        if ch in ("e", "E") and (i + 1 >= n or not (text[i + 1].isalnum() or text[i + 1] == "_")):
            tokens.append(CASToken(CASTokenType.E_CONST, ch, Span(start, start + 1)))
            i += 1
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
            tokens.append(CASTokenType.LE if isinstance(CASTokenType.LE, CASToken) else CASToken(CASTokenType.LE, "<=", Span(start, start + 1)))
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
        if ch == "_":
            tokens.append(CASToken(CASTokenType.UNDERSCORE, "_", Span(start, start + 1)))
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
        if ch == "{":
            tokens.append(CASToken(CASTokenType.LBRACE, "{", Span(start, start + 1)))
            i += 1
            continue
        if ch == "}":
            tokens.append(CASToken(CASTokenType.RBRACE, "}", Span(start, start + 1)))
            i += 1
            continue
        if ch == "|":
            tokens.append(CASToken(CASTokenType.PIPE, "|", Span(start, start + 1)))
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

    # Check for implicit multiplication
    left_implicits = {
        CASTokenType.INTEGER,
        CASTokenType.VARIABLE,
        CASTokenType.PI,
        CASTokenType.E_CONST,
        CASTokenType.RPAREN,
        CASTokenType.RBRACKET,
        CASTokenType.RBRACE,
    }
    right_implicits = {
        CASTokenType.VARIABLE,
        CASTokenType.PI,
        CASTokenType.E_CONST,
        CASTokenType.LPAREN,
        CASTokenType.LBRACKET,
        CASTokenType.LBRACE,
        CASTokenType.SQRT,
        CASTokenType.ABS,
        CASTokenType.SIN,
        CASTokenType.COS,
        CASTokenType.TAN,
        CASTokenType.EXP,
        CASTokenType.LOG,
        CASTokenType.LN,
    }

    # Classify each PIPE as OPEN or CLOSE
    pipe_kinds: Dict[int, str] = {}
    pipe_stack: List[int] = []
    for idx, tok in enumerate(tokens):
        if tok.type == CASTokenType.PIPE:
            if idx == 0:
                pipe_kinds[idx] = "OPEN"
                pipe_stack.append(idx)
            else:
                prev_tok = tokens[idx - 1]
                if prev_tok.type in (
                    CASTokenType.PLUS,
                    CASTokenType.MINUS,
                    CASTokenType.STAR,
                    CASTokenType.SLASH,
                    CASTokenType.CARET,
                    CASTokenType.UNDERSCORE,
                    CASTokenType.EQUALS,
                    CASTokenType.LT,
                    CASTokenType.LE,
                    CASTokenType.GT,
                    CASTokenType.GE,
                    CASTokenType.LPAREN,
                    CASTokenType.LBRACKET,
                    CASTokenType.LBRACE,
                    CASTokenType.COMMA,
                    CASTokenType.SEMICOLON,
                ) or (prev_tok.type == CASTokenType.PIPE and pipe_kinds.get(idx - 1) == "OPEN"):
                    pipe_kinds[idx] = "OPEN"
                    pipe_stack.append(idx)
                elif pipe_stack:
                    pipe_kinds[idx] = "CLOSE"
                    pipe_stack.pop()
                else:
                    pipe_kinds[idx] = "OPEN"
                    pipe_stack.append(idx)

    # Track RBRACE tokens closing subscript or power groups
    brace_is_subscript_or_caret_stack: List[bool] = []
    subscript_or_caret_rbraces: Set[int] = set()
    for idx, tok in enumerate(tokens):
        if tok.type == CASTokenType.LBRACE:
            is_sub = (idx > 0 and tokens[idx - 1].type in (CASTokenType.CARET, CASTokenType.UNDERSCORE))
            brace_is_subscript_or_caret_stack.append(is_sub)
        elif tok.type == CASTokenType.RBRACE:
            if brace_is_subscript_or_caret_stack:
                is_sub = brace_is_subscript_or_caret_stack.pop()
                if is_sub:
                    subscript_or_caret_rbraces.add(idx)

    for idx in range(len(tokens) - 1):
        curr_t = tokens[idx]
        next_t = tokens[idx + 1]

        # An integer/variable that is an exponent or subscript does NOT multiply the following parenthesized argument of a function
        if idx > 0 and tokens[idx - 1].type in (CASTokenType.CARET, CASTokenType.UNDERSCORE):
            continue

        # A closing brace for a subscript or power does NOT multiply the following parenthesized argument
        if curr_t.type == CASTokenType.RBRACE and idx in subscript_or_caret_rbraces:
            continue

        if curr_t.type in left_implicits and next_t.type in right_implicits:
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected between '{curr_t.value}' and '{next_t.value}'. Use explicit '*' (e.g. '{curr_t.value}*{next_t.value}').",
                Span(curr_t.span.start, next_t.span.end),
            )
        if curr_t.type in (CASTokenType.RPAREN, CASTokenType.RBRACKET, CASTokenType.RBRACE) and next_t.type == CASTokenType.INTEGER:
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected between '{curr_t.value}' and '{next_t.value}'. Use explicit '*'.",
                Span(curr_t.span.start, next_t.span.end),
            )
        if curr_t.type in left_implicits and next_t.type == CASTokenType.PIPE and pipe_kinds.get(idx + 1) == "OPEN":
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected between '{curr_t.value}' and '|'. Use explicit '*' (e.g. '{curr_t.value}*|').",
                Span(curr_t.span.start, next_t.span.end),
            )
        if curr_t.type == CASTokenType.PIPE and pipe_kinds.get(idx) == "CLOSE" and next_t.type in (
            CASTokenType.INTEGER,
            CASTokenType.VARIABLE,
            CASTokenType.PI,
            CASTokenType.E_CONST,
            CASTokenType.LPAREN,
            CASTokenType.SQRT,
            CASTokenType.ABS,
            CASTokenType.SIN,
            CASTokenType.COS,
            CASTokenType.TAN,
            CASTokenType.EXP,
            CASTokenType.LOG,
            CASTokenType.LN,
        ):
            raise ImplicitMultiplicationError(
                f"Implicit multiplication detected after '|'. Use explicit '*'.",
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
            if self.current.type == CASTokenType.INTEGER:
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
            elif self.current.type in (
                CASTokenType.LPAREN,
                CASTokenType.LBRACE,
                CASTokenType.VARIABLE,
                CASTokenType.PI,
                CASTokenType.E_CONST,
                CASTokenType.SIN,
                CASTokenType.COS,
                CASTokenType.TAN,
                CASTokenType.EXP,
                CASTokenType.LOG,
                CASTokenType.LN,
                CASTokenType.SQRT,
                CASTokenType.ABS,
                CASTokenType.MINUS,
                CASTokenType.PLUS,
            ):
                exp_node = self.parse_primary()
                return CASPower(
                    base=base,
                    exponent=exp_node,
                    span=Span(base.span.start, exp_node.span.end),
                )
            else:
                raise ParserError(
                    f"Expected exponent expression after '^', found {self.current.value!r}.",
                    self.current.span,
                )
        return base

    def parse_primary(self) -> ASTNode:
        """Parse primary: integer_literal | variable | constants | functions | grouping."""
        tok = self.current
        if tok.type == CASTokenType.INTEGER:
            self.advance()
            return IntegerLiteral(value=int(tok.value), span=tok.span)

        if tok.type == CASTokenType.VARIABLE:
            self.advance()
            return Variable(name=tok.value, span=tok.span)

        if tok.type == CASTokenType.PI:
            self.advance()
            return NamedConstant(name="pi", span=tok.span)

        if tok.type == CASTokenType.E_CONST:
            self.advance()
            return NamedConstant(name="e", span=tok.span)

        if tok.type in (CASTokenType.LPAREN, CASTokenType.LBRACE):
            is_brace = (tok.type == CASTokenType.LBRACE)
            closing_type = CASTokenType.RBRACE if is_brace else CASTokenType.RPAREN
            opening_char = "{" if is_brace else "("
            closing_char = "}" if is_brace else ")"
            lparen_span = tok.span
            self.advance()
            self._nesting_depth += 1
            if self._nesting_depth > MAX_NESTING_DEPTH:
                raise InputBoundsExceededError(
                    f"Nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                    lparen_span,
                )

            inner = self.parse_expression()
            if self.current.type != closing_type:
                raise ParserError(
                    f"Expected matching closing '{closing_char}' for '{opening_char}' at position {lparen_span.start}.",
                    self.current.span,
                )
            rparen_tok = self.advance()
            self._nesting_depth -= 1
            return Group(
                inner=inner,
                span=Span(lparen_span.start, rparen_tok.span.end),
            )

        if tok.type in (CASTokenType.SIN, CASTokenType.COS, CASTokenType.TAN, CASTokenType.EXP, CASTokenType.LN):
            func_tok = self.advance()
            func_name = func_tok.value.lstrip("\\").lower()

            # Check for power on function name, e.g. \sin^2(x)
            func_power_node: Optional[ASTNode] = None
            if self.current.type == CASTokenType.CARET:
                self.advance()
                if self.current.type == CASTokenType.INTEGER:
                    exp_tok = self.advance()
                    exp_val = int(exp_tok.value)
                    exp_lit = IntegerLiteral(value=exp_val, span=exp_tok.span)
                    func_power_node = exp_lit
                else:
                    func_power_node = self.parse_primary()

            # Parse argument
            if self.current.type in (CASTokenType.LPAREN, CASTokenType.LBRACE):
                is_brace = (self.current.type == CASTokenType.LBRACE)
                closing_type = CASTokenType.RBRACE if is_brace else CASTokenType.RPAREN
                opening_char = "{" if is_brace else "("
                closing_char = "}" if is_brace else ")"
                open_tok = self.advance()
                self._nesting_depth += 1
                if self._nesting_depth > MAX_NESTING_DEPTH:
                    raise InputBoundsExceededError(
                        f"Nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                        open_tok.span,
                    )
                arg_expr = self.parse_expression()
                if self.current.type != closing_type:
                    raise ParserError(
                        f"Expected matching closing '{closing_char}' for '{func_tok.value}{opening_char}' at position {open_tok.span.start}.",
                        self.current.span,
                    )
                close_tok = self.advance()
                self._nesting_depth -= 1
                end_pos = close_tok.span.end
            else:
                arg_expr = self.parse_primary()
                end_pos = arg_expr.span.end

            fc = FunctionCall(
                name=func_name,
                args=(arg_expr,),
                span=Span(func_tok.span.start, end_pos),
            )
            if func_power_node is not None:
                if isinstance(func_power_node, IntegerLiteral) and func_power_node.value in (0, 1, 2):
                    return Power(base=fc, exponent=func_power_node, span=Span(func_tok.span.start, end_pos))
                return CASPower(base=fc, exponent=func_power_node, span=Span(func_tok.span.start, end_pos))
            return fc

        if tok.type == CASTokenType.LOG:
            func_tok = self.advance()
            func_name = "log"
            base_arg: Optional[ASTNode] = None

            # Check for subscript base: \log_2(x) or \log_{2}(x)
            if self.current.type == CASTokenType.UNDERSCORE:
                self.advance()
                if self.current.type in (CASTokenType.LBRACE, CASTokenType.LPAREN):
                    is_brace = (self.current.type == CASTokenType.LBRACE)
                    closing_type = CASTokenType.RBRACE if is_brace else CASTokenType.RPAREN
                    self.advance()
                    base_arg = self.parse_expression()
                    if self.current.type != closing_type:
                        raise ParserError(
                            f"Expected closing bracket for log base at position {self.current.span.start}.",
                            self.current.span,
                        )
                    self.advance()
                else:
                    base_arg = self.parse_primary()

            # Parse log argument(s)
            if self.current.type in (CASTokenType.LPAREN, CASTokenType.LBRACE):
                is_brace = (self.current.type == CASTokenType.LBRACE)
                closing_type = CASTokenType.RBRACE if is_brace else CASTokenType.RPAREN
                opening_char = "{" if is_brace else "("
                closing_char = "}" if is_brace else ")"
                open_tok = self.advance()
                self._nesting_depth += 1
                if self._nesting_depth > MAX_NESTING_DEPTH:
                    raise InputBoundsExceededError(
                        f"Nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                        open_tok.span,
                    )
                first_arg = self.parse_expression()
                args_list = [first_arg]
                if self.current.type == CASTokenType.COMMA:
                    self.advance()
                    second_arg = self.parse_expression()
                    args_list.append(second_arg)
                if self.current.type != closing_type:
                    raise ParserError(
                        f"Expected matching closing '{closing_char}' for '{func_tok.value}{opening_char}' at position {open_tok.span.start}.",
                        self.current.span,
                    )
                close_tok = self.advance()
                self._nesting_depth -= 1
                end_pos = close_tok.span.end

                if base_arg is not None:
                    # e.g. \log_2(x) -> (x, 2)
                    fc_args = (args_list[0], base_arg)
                else:
                    fc_args = tuple(args_list)

                return FunctionCall(
                    name=func_name,
                    args=fc_args,
                    span=Span(func_tok.span.start, end_pos),
                )
            else:
                arg_expr = self.parse_primary()
                fc_args = (arg_expr, base_arg) if base_arg is not None else (arg_expr,)
                return FunctionCall(
                    name=func_name,
                    args=fc_args,
                    span=Span(func_tok.span.start, arg_expr.span.end),
                )

        if tok.type == CASTokenType.SQRT:
            start_span = tok.span
            self.advance()
            if self.current.type == CASTokenType.LPAREN:
                self.advance()
                self._nesting_depth += 1
                if self._nesting_depth > MAX_NESTING_DEPTH:
                    raise InputBoundsExceededError(
                        f"Parentheses nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                        start_span,
                    )
                radicand = self.parse_expression()
                if self.current.type != CASTokenType.RPAREN:
                    raise ParserError(
                        f"Expected matching closing ')' for 'sqrt(' at position {start_span.start}.",
                        self.current.span,
                    )
                end_tok = self.advance()
                self._nesting_depth -= 1
                return Radical(
                    radicand=radicand,
                    span=Span(start_span.start, end_tok.span.end),
                )
            elif self.current.type == CASTokenType.LBRACE:
                self.advance()
                self._nesting_depth += 1
                if self._nesting_depth > MAX_NESTING_DEPTH:
                    raise InputBoundsExceededError(
                        f"Braces nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                        start_span,
                    )
                radicand = self.parse_expression()
                if self.current.type != CASTokenType.RBRACE:
                    raise ParserError(
                        f"Expected matching closing '}}' for '\\sqrt{{' at position {start_span.start}.",
                        self.current.span,
                    )
                end_tok = self.advance()
                self._nesting_depth -= 1
                return Radical(
                    radicand=radicand,
                    span=Span(start_span.start, end_tok.span.end),
                )
            else:
                raise ParserError(
                    f"Expected '(' or '{{' after 'sqrt' at position {start_span.start}.",
                    self.current.span,
                )

        if tok.type == CASTokenType.ABS:
            start_span = tok.span
            self.advance()
            if self.current.type != CASTokenType.LPAREN:
                raise ParserError(
                    f"Expected '(' after 'abs' at position {start_span.start}.",
                    self.current.span,
                )
            self.advance()
            self._nesting_depth += 1
            if self._nesting_depth > MAX_NESTING_DEPTH:
                raise InputBoundsExceededError(
                    f"Parentheses nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                    start_span,
                )
            inner = self.parse_expression()
            if self.current.type != CASTokenType.RPAREN:
                raise ParserError(
                    f"Expected matching closing ')' for 'abs(' at position {start_span.start}.",
                    self.current.span,
                )
            end_tok = self.advance()
            self._nesting_depth -= 1
            return AbsoluteValue(
                inner=inner,
                span=Span(start_span.start, end_tok.span.end),
            )

        if tok.type == CASTokenType.PIPE:
            start_span = tok.span
            self.advance()
            self._nesting_depth += 1
            if self._nesting_depth > MAX_NESTING_DEPTH:
                raise InputBoundsExceededError(
                    f"Absolute value nesting depth exceeds maximum limit of {MAX_NESTING_DEPTH}.",
                    start_span,
                )
            inner = self.parse_expression()
            if self.current.type != CASTokenType.PIPE:
                raise ParserError(
                    f"Expected matching closing '|' for '|' at position {start_span.start}.",
                    self.current.span,
                )
            end_tok = self.advance()
            self._nesting_depth -= 1
            return AbsoluteValue(
                inner=inner,
                span=Span(start_span.start, end_tok.span.end),
            )

        raise ParserError(
            f"Unexpected token {tok.value!r} at position {tok.span.start}; expected integer, variable, constant, function, '(', 'sqrt', 'abs', or '|'.",
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


def is_top_level_system(text: str) -> bool:
    """Check if text contains top-level comma, semicolon, or newline separating equations outside parentheses/brackets/braces."""
    clean_text = text.strip()
    if clean_text.startswith("[") and clean_text.endswith("]"):
        clean_text = clean_text[1:-1].strip()

    depth = 0
    for ch in clean_text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch in (",", ";", "\n") and depth == 0:
            return True
    return False


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
        if ch in "([{":
            depth += 1
            current_part.append(ch)
        elif ch in ")]}":
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
