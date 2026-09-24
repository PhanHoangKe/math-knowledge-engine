"""Abstract Syntax Tree (AST) definitions for safe mathematical representation."""

from __future__ import annotations
from abc import ABC, abstractmethod
from fractions import Fraction
from typing import Any, Dict, List, Set


class ASTNode(ABC):
    """Base class for all safe mathematical AST nodes."""

    @abstractmethod
    def depth(self) -> int:
        """Calculate the maximum depth of this subtree."""
        pass

    @abstractmethod
    def node_count(self) -> int:
        """Count the total number of nodes in this subtree."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the AST node to a dictionary."""
        pass

    @abstractmethod
    def to_math_string(self) -> str:
        """Format the AST node into standard mathematical notation."""
        pass

    def collect_divisions(self) -> List[BinaryOpNode]:
        """Find all division nodes within this AST subtree."""
        return []

    def collect_variables(self) -> Set[str]:
        """Find all variable names within this AST subtree."""
        return set()


class NumberNode(ASTNode):
    """Represents an exact rational or integer constant."""

    def __init__(self, value: Fraction | int):
        if isinstance(value, int):
            self.value = Fraction(value, 1)
        elif isinstance(value, Fraction):
            self.value = value
        else:
            raise TypeError(f"NumberNode expects Fraction or int, got {type(value)}")

    def depth(self) -> int:
        return 1

    def node_count(self) -> int:
        return 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Number",
            "numerator": self.value.numerator,
            "denominator": self.value.denominator,
        }

    def to_math_string(self) -> str:
        if self.value.denominator == 1:
            return str(self.value.numerator)
        return f"{self.value.numerator}/{self.value.denominator}"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NumberNode) and self.value == other.value

    def __repr__(self) -> str:
        return f"NumberNode({self.value})"


class VariableNode(ASTNode):
    """Represents a mathematical variable (restricted to 'x' in DEV-01)."""

    def __init__(self, name: str):
        if name != "x":
            raise ValueError(f"Only variable 'x' is supported in DEV-01, got '{name}'")
        self.name = name

    def depth(self) -> int:
        return 1

    def node_count(self) -> int:
        return 1

    def to_dict(self) -> Dict[str, Any]:
        return {"type": "Variable", "name": self.name}

    def to_math_string(self) -> str:
        return self.name

    def collect_variables(self) -> Set[str]:
        return {self.name}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VariableNode) and self.name == other.name

    def __repr__(self) -> str:
        return f"VariableNode('{self.name}')"


class UnaryOpNode(ASTNode):
    """Represents a unary operation (+ or -)."""

    def __init__(self, op: str, operand: ASTNode):
        if op not in ("+", "-"):
            raise ValueError(f"Unsupported unary operator: {op}")
        self.op = op
        self.operand = operand

    def depth(self) -> int:
        return 1 + self.operand.depth()

    def node_count(self) -> int:
        return 1 + self.operand.node_count()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict(),
        }

    def to_math_string(self) -> str:
        operand_str = self.operand.to_math_string()
        if isinstance(self.operand, (BinaryOpNode, UnaryOpNode)):
            return f"{self.op}({operand_str})"
        return f"{self.op}{operand_str}"

    def collect_divisions(self) -> List[BinaryOpNode]:
        return self.operand.collect_divisions()

    def collect_variables(self) -> Set[str]:
        return self.operand.collect_variables()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, UnaryOpNode)
            and self.op == other.op
            and self.operand == other.operand
        )

    def __repr__(self) -> str:
        return f"UnaryOpNode('{self.op}', {self.operand!r})"


class BinaryOpNode(ASTNode):
    """Represents a binary operation (+, -, *, /, ^)."""

    ALLOWED_OPS = {"+", "-", "*", "/", "^"}

    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        if op not in self.ALLOWED_OPS:
            raise ValueError(f"Unsupported binary operator: {op}")
        self.op = op
        self.left = left
        self.right = right

    def depth(self) -> int:
        return 1 + max(self.left.depth(), self.right.depth())

    def node_count(self) -> int:
        return 1 + self.left.node_count() + self.right.node_count()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    def to_math_string(self) -> str:
        left_str = self.left.to_math_string()
        right_str = self.right.to_math_string()

        # Add parens for precedence if needed
        if isinstance(self.left, BinaryOpNode) and self._precedence(self.left.op) < self._precedence(self.op):
            left_str = f"({left_str})"
        if isinstance(self.right, BinaryOpNode):
            # For right operand, equal precedence in non-associative ops also needs parens
            if self._precedence(self.right.op) < self._precedence(self.op) or (
                self.op in ("-", "/", "^") and self._precedence(self.right.op) <= self._precedence(self.op)
            ):
                right_str = f"({right_str})"

        return f"{left_str} {self.op} {right_str}"

    @staticmethod
    def _precedence(op: str) -> int:
        if op in ("+", "-"):
            return 1
        if op in ("*", "/"):
            return 2
        if op == "^":
            return 3
        return 0

    def collect_divisions(self) -> List[BinaryOpNode]:
        divs = self.left.collect_divisions() + self.right.collect_divisions()
        if self.op == "/":
            divs.append(self)
        return divs

    def collect_variables(self) -> Set[str]:
        return self.left.collect_variables() | self.right.collect_variables()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, BinaryOpNode)
            and self.op == other.op
            and self.left == other.left
            and self.right == other.right
        )

    def __repr__(self) -> str:
        return f"BinaryOpNode('{self.op}', {self.left!r}, {self.right!r})"


class EquationNode(ASTNode):
    """Represents a mathematical equation with left and right expressions."""

    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def depth(self) -> int:
        return 1 + max(self.left.depth(), self.right.depth())

    def node_count(self) -> int:
        return 1 + self.left.node_count() + self.right.node_count()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Equation",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    def to_math_string(self) -> str:
        return f"{self.left.to_math_string()} = {self.right.to_math_string()}"

    def collect_divisions(self) -> List[BinaryOpNode]:
        return self.left.collect_divisions() + self.right.collect_divisions()

    def collect_variables(self) -> Set[str]:
        return self.left.collect_variables() | self.right.collect_variables()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, EquationNode)
            and self.left == other.left
            and self.right == other.right
        )

    def __repr__(self) -> str:
        return f"EquationNode({self.left!r}, {self.right!r})"


def ast_from_dict(data: Dict[str, Any]) -> ASTNode:
    """Reconstruct an AST from a serialized dictionary."""
    node_type = data.get("type")
    if node_type == "Number":
        return NumberNode(Fraction(data["numerator"], data["denominator"]))
    elif node_type == "Variable":
        return VariableNode(data["name"])
    elif node_type == "UnaryOp":
        return UnaryOpNode(data["op"], ast_from_dict(data["operand"]))
    elif node_type == "BinaryOp":
        return BinaryOpNode(
            data["op"],
            ast_from_dict(data["left"]),
            ast_from_dict(data["right"]),
        )
    elif node_type == "Equation":
        return EquationNode(
            ast_from_dict(data["left"]),
            ast_from_dict(data["right"]),
        )
    else:
        raise ValueError(f"Unknown AST node type: {node_type}")
