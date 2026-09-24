"""Unit tests for safe mathematical lexer."""

from fractions import Fraction
import pytest

from mke.parsing.exceptions import (
    CoefficientMagnitudeError,
    InputLengthExceededError,
    InvalidSyntaxError,
    OutOfScopeSyntaxError,
    TokenCountExceededError,
)
from mke.parsing.lexer import Lexer
from mke.parsing.limits import ParserLimits
from mke.parsing.tokens import TokenKind


def test_tokenize_simple_equation():
    lexer = Lexer("2*x + 3 = 7")
    tokens = lexer.tokenize()
    kinds = [t.kind for t in tokens]
    assert kinds == [
        TokenKind.NUMBER,
        TokenKind.STAR,
        TokenKind.VARIABLE,
        TokenKind.PLUS,
        TokenKind.NUMBER,
        TokenKind.EQUALS,
        TokenKind.NUMBER,
        TokenKind.EOF,
    ]
    assert tokens[0].number_value == Fraction(2, 1)
    assert tokens[2].value == "x"


def test_tokenize_power_and_double_star():
    lexer1 = Lexer("x^2")
    tokens1 = lexer1.tokenize()
    assert tokens1[1].kind == TokenKind.CARET

    lexer2 = Lexer("x**2")
    tokens2 = lexer2.tokenize()
    assert tokens2[1].kind == TokenKind.CARET


def test_tokenize_decimal_numbers():
    lexer = Lexer("2.5*x - 0.75 = 0")
    tokens = lexer.tokenize()
    assert tokens[0].number_value == Fraction(5, 2)
    assert tokens[4].number_value == Fraction(3, 4)


def test_out_of_scope_variable():
    lexer = Lexer("y + 1 = 0")
    with pytest.raises(OutOfScopeSyntaxError) as exc_info:
        lexer.tokenize()
    assert "Variable 'y' is outside DEV-01 scope" in str(exc_info.value)


def test_out_of_scope_function_sqrt():
    lexer = Lexer("sqrt(x + 2) = x")
    with pytest.raises(OutOfScopeSyntaxError) as exc_info:
        lexer.tokenize()
    assert "sqrt" in str(exc_info.value)


def test_out_of_scope_operators():
    with pytest.raises(OutOfScopeSyntaxError):
        Lexer("x < 5").tokenize()

    with pytest.raises(OutOfScopeSyntaxError):
        Lexer("x > 0").tokenize()

    with pytest.raises(OutOfScopeSyntaxError):
        Lexer("x != 2").tokenize()


def test_input_length_exceeded():
    limits = ParserLimits(max_input_length=10)
    with pytest.raises(InputLengthExceededError):
        Lexer("x^2 + 5*x + 6 = 0", limits=limits)


def test_token_count_exceeded():
    limits = ParserLimits(max_tokens=3)
    with pytest.raises(TokenCountExceededError):
        Lexer("1 + 2 + 3 + 4", limits=limits).tokenize()


def test_coefficient_magnitude_exceeded():
    limits = ParserLimits(max_coefficient_magnitude=100)
    with pytest.raises(CoefficientMagnitudeError):
        Lexer("101*x = 0", limits=limits).tokenize()
