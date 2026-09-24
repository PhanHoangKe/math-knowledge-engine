"""Unit tests for Original Mathematical Domain preservation."""

from fractions import Fraction
import sympy

from mke.domain.extractor import extract_original_domain
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser


def test_polynomial_domain_is_all_reals():
    ast = Parser.from_text("x^2 - 5*x + 6 = 0").parse_equation()
    domain = extract_original_domain(ast)
    assert domain.is_all_reals()
    assert domain.format_domain() == "R"
    assert domain.contains(2)
    assert domain.contains(0)


def test_rational_domain_preservation_t3():
    """T3 Case: (x-2)/(x-2) = 1.

    Even though algebraic simplification reduces to 1 = 1, the unreduced AST
    MUST preserve the domain constraint x != 2.
    """
    raw_input = "(x - 2) / (x - 2) = 1"
    ast = Parser.from_text(raw_input).parse_equation()

    domain = extract_original_domain(ast)
    assert not domain.is_all_reals()
    assert domain.format_domain() == "R \\ {2}"
    assert not domain.contains(2)
    assert domain.contains(1)
    assert domain.contains(3)

    # Normalize equation: verify that normalization does NOT erase domain exclusion
    norm = normalize_equation(ast, raw_text=raw_input)
    assert norm.is_identity  # Reduced form is identity 0 = 0
    assert norm.domain.format_domain() == "R \\ {2}"
    assert not norm.domain.contains(2)


def test_multiple_denominators_domain():
    raw_input = "1 / (x - 1) + 1 / (x + 1) = 0"
    ast = Parser.from_text(raw_input).parse_equation()
    domain = extract_original_domain(ast)

    assert not domain.is_all_reals()
    assert domain.format_domain() == "R \\ {-1, 1}"
    assert not domain.contains(1)
    assert not domain.contains(-1)
    assert domain.contains(0)
