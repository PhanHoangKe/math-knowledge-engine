"""Property-based invariant testing with independent oracle validation."""

from fractions import Fraction
import random
import pytest

from mke.parsing.parser import Parser
from mke.parsing.sympy_converter import ast_to_sympy, X_SYM
from mke.verification.engine import VerificationEngine


def independent_eval_fraction(expr_str: str, x_val: Fraction) -> Fraction | None:
    """Independent oracle: evaluates simple rational expression in Python Fraction arithmetic.

    Does NOT use SymPy's solver or normalizer to avoid circular oracle validation.
    """
    # Safe simple evaluator for polynomial and rational expressions
    # Replace variable 'x' with fraction literal
    tokens = expr_str.replace(" ", "")
    # Evaluates by converting AST to Python operations on Fraction
    ast = Parser.from_text(f"{expr_str} = 0").parse_equation().left
    
    def eval_node(node) -> Fraction | None:
        from mke.models.ast_nodes import NumberNode, VariableNode, UnaryOpNode, BinaryOpNode
        if isinstance(node, NumberNode):
            return node.value
        elif isinstance(node, VariableNode):
            return x_val
        elif isinstance(node, UnaryOpNode):
            sub = eval_node(node.operand)
            if sub is None:
                return None
            return -sub if node.op == "-" else sub
        elif isinstance(node, BinaryOpNode):
            l = eval_node(node.left)
            r = eval_node(node.right)
            if l is None or r is None:
                return None
            if node.op == "+":
                return l + r
            elif node.op == "-":
                return l - r
            elif node.op == "*":
                return l * r
            elif node.op == "/":
                if r == 0:
                    return None  # Division by zero!
                return l / r
            elif node.op == "^":
                if r.denominator != 1 or r.numerator < 0:
                    return None
                return l ** r.numerator
        return None

    return eval_node(ast)


@pytest.mark.parametrize("seed", list(range(10)))
def test_property_linear_roots_satisfy_independent_oracle(seed: int):
    """Property: Every root returned by linear solver satisfies original equation under independent evaluation."""
    rng = random.Random(seed)
    # Generate random linear: a*x + b = 0 with a in [-10, 10] \ {0}, b in [-20, 20]
    a = rng.choice([n for n in range(-10, 11) if n != 0])
    b = rng.randint(-20, 20)

    eq_str = f"{a}*x + {b} = 0"
    engine = VerificationEngine()
    result = engine.verify(eq_str)

    assert result.is_verified_solution is True
    assert len(result.verified_roots) == 1

    root_frac = Fraction(result.verified_roots[0])
    # Evaluate using independent oracle
    eval_res = independent_eval_fraction(f"{a}*x + {b}", root_frac)
    assert eval_res == Fraction(0, 1)


@pytest.mark.parametrize("seed", list(range(10)))
def test_property_quadratic_roots_satisfy_independent_oracle(seed: int):
    """Property: For quadratics with integer roots r1, r2, roots satisfy independent oracle."""
    rng = random.Random(seed + 100)
    r1 = rng.randint(-5, 5)
    r2 = rng.randint(-5, 5)

    # (x - r1)*(x - r2) = x^2 - (r1+r2)*x + r1*r2
    b = -(r1 + r2)
    c = r1 * r2

    eq_str = f"x^2 + ({b})*x + ({c}) = 0"
    engine = VerificationEngine()
    result = engine.verify(eq_str)

    assert result.is_verified_solution is True
    assert len(result.verified_roots) >= 1

    for r_str in result.verified_roots:
        r_frac = Fraction(r_str)
        # Check against domain
        assert result.is_all_reals_domain or r_str not in result.excluded_points
        # Evaluate via independent oracle
        eval_res = independent_eval_fraction(f"x^2 + ({b})*x + ({c})", r_frac)
        assert eval_res == Fraction(0, 1)


@pytest.mark.parametrize("seed", list(range(5)))
def test_property_extraneous_root_invariant(seed: int):
    """Property Invariant: Denominator roots MUST NEVER appear in verified_roots."""
    rng = random.Random(seed + 200)
    r = rng.randint(-5, 5)
    e = rng.choice([n for n in range(-5, 6) if n != r])

    # (x - r)*(x - e) / (x - e) = 0
    # Numerator: x^2 - (r+e)*x + r*e
    b = -(r + e)
    c = r * e
    eq_str = f"(x^2 + ({b})*x + ({c})) / (x - {e}) = 0"

    engine = VerificationEngine()
    result = engine.verify(eq_str)

    # e MUST be in excluded points
    assert str(e) in result.excluded_points
    # e MUST NEVER be in verified_roots
    assert str(e) not in result.verified_roots
    # If r is not excluded, r must be in verified roots
    assert str(r) in result.verified_roots
