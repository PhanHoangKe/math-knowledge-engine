"""Typed, immutable Abstract Syntax Tree (AST) nodes for mathematical expressions and equations.

Preserves exact syntactic structure:
- Parentheses grouping (Group).
- Original operator order and subtrees.
- No normalization or simplification of x^0, 0^0, (x-1)/(x-1), or x*x.
- Source spans for every node.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Set, Dict, Any

from .errors import Span


class ASTNode(ABC):
    """Abstract base class for all immutable AST nodes."""

    @property
    @abstractmethod
    def span(self) -> Span:
        """Source span of the AST node."""
        pass

    @abstractmethod
    def walk(self) -> Iterator[ASTNode]:
        """Iterate over self and all descendant nodes in pre-order."""
        pass

    @abstractmethod
    def variables(self) -> Set[str]:
        """Return the set of all variable names occurring in this node."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Deterministic inspection dictionary (non-normative debug/testing format)."""
        pass


@dataclass(frozen=True, slots=True)
class IntegerLiteral(ASTNode):
    """Non-negative integer literal."""
    value: int
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self

    def variables(self) -> Set[str]:
        return set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "IntegerLiteral",
            "value": self.value,
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"IntegerLiteral({self.value})"


@dataclass(frozen=True, slots=True)
class Variable(ASTNode):
    """Single variable symbol (strictly 'x' in Phase P02A)."""
    name: str
    span: Span

    def __post_init__(self) -> None:
        if self.name != "x":
            raise ValueError(f"Only variable 'x' is supported in P02A, got: {self.name!r}")

    def walk(self) -> Iterator[ASTNode]:
        yield self

    def variables(self) -> Set[str]:
        return {self.name}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Variable",
            "name": self.name,
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"Variable({self.name!r})"


@dataclass(frozen=True, slots=True)
class Group(ASTNode):
    """Explicit parentheses grouping: ( expression )."""
    inner: ASTNode
    span: Span

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.inner.walk()

    def variables(self) -> Set[str]:
        return self.inner.variables()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Group",
            "inner": self.inner.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"Group({self.inner!r})"


@dataclass(frozen=True, slots=True)
class UnaryOp(ASTNode):
    """Unary prefix operator (+ or -)."""
    op: str
    operand: ASTNode
    span: Span

    def __post_init__(self) -> None:
        if self.op not in {"+", "-"}:
            raise ValueError(f"Unsupported unary operator: {self.op!r}")

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.operand.walk()

    def variables(self) -> Set[str]:
        return self.operand.variables()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"UnaryOp({self.op!r}, {self.operand!r})"


@dataclass(frozen=True, slots=True)
class BinaryOp(ASTNode):
    """Binary arithmetic operator (+, -, *, /)."""
    op: str
    left: ASTNode
    right: ASTNode
    span: Span

    def __post_init__(self) -> None:
        if self.op not in {"+", "-", "*", "/"}:
            raise ValueError(f"Unsupported binary operator: {self.op!r}")

    def walk(self) -> Iterator[ASTNode]:
        yield self
        yield from self.left.walk()
        yield from self.right.walk()

    def variables(self) -> Set[str]:
        return self.left.variables() | self.right.variables()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"BinaryOp({self.op!r}, {self.left!r}, {self.right!r})"


@dataclass(frozen=True, slots=True)
class Power(ASTNode):
    """Power expression: base ^ exponent, where exponent in {0, 1, 2}."""
    base: ASTNode
    exponent: IntegerLiteral
    span: Span

    def __post_init__(self) -> None:
        if self.exponent.value not in {0, 1, 2}:
            raise ValueError(f"Exponent must be in {{0, 1, 2}}, got: {self.exponent.value}")

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
class Equation(ASTNode):
    """Equality relation between two expressions: left = right."""
    left: ASTNode
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
            "type": "Equation",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "span": self.span.to_tuple(),
        }

    def __repr__(self) -> str:
        return f"Equation({self.left!r}, {self.right!r})"
