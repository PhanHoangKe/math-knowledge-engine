"""Security tests verifying resistance to injection attacks and resource exhaustion."""

import pytest

from mke.parsing.exceptions import (
    ASTDepthExceededError,
    CoefficientMagnitudeError,
    InputLengthExceededError,
    OutOfScopeSyntaxError,
    ParserError,
)
from mke.parsing.limits import ParserLimits
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine


INJECTION_PAYLOADS = [
    "__import__('os').system('calc')",
    "eval('1+1') = 0",
    "exec('import sys') = 0",
    "os.remove('file.txt') = 0",
    "open('test.txt') = 0",
    "__class__.__subclasses__() = 0",
    "x + (lambda: 1)() = 0",
    "system('dir') = 0",
]


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_security_injection_payloads_safely_rejected(payload: str):
    """Verify that Python code injection payloads are safely rejected by parser without execution."""
    engine = VerificationEngine()
    result = engine.verify(payload)
    # Must be marked OUT_OF_SCOPE, PARSER_ERROR, or have empty/undetermined status
    assert result.is_verified_solution is False
    assert result.solution_status.value in ("UNDETERMINED", "OUT_OF_SCOPE")
    assert "OUT_OF_SCOPE" in result.explanation or "SYNTAX" in result.explanation or "INTERNAL" in result.explanation


def test_security_deep_nesting_dos():
    """Verify protection against deep nesting AST recursion bomb."""
    deep_expr = "(" * 30 + "x" + ")" * 30 + " = 0"
    engine = VerificationEngine()
    result = engine.verify(deep_expr)
    assert result.is_verified_solution is False
    assert "AST depth" in result.explanation or "limit" in result.explanation


def test_security_huge_input_length():
    """Verify input length limits prevent memory exhaustion."""
    huge_input = "x + " + "1 + " * 300 + "1 = 0"
    engine = VerificationEngine()
    result = engine.verify(huge_input)
    assert result.is_verified_solution is False
    assert "length" in result.explanation or "limit" in result.explanation


def test_security_huge_coefficient():
    """Verify that coefficients exceeding magnitude limits are rejected."""
    huge_num_eq = "99999999999999999999999999999999999999999999999*x = 0"
    engine = VerificationEngine()
    result = engine.verify(huge_num_eq)
    assert result.is_verified_solution is False
    assert "magnitude" in result.explanation or "limit" in result.explanation


def test_security_unsupported_operators_and_delimiters():
    """Verify that shell-like or programming delimiters are rejected."""
    delimiters = [
        "x; rm -rf /",
        "x & y = 0",
        "x | y = 0",
        "x $ y = 0",
        "x `ls` = 0",
        "x [0] = 0",
    ]
    for d in delimiters:
        engine = VerificationEngine()
        result = engine.verify(d)
        assert result.is_verified_solution is False
