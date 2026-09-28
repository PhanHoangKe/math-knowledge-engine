"""Unit and regression tests for P03C-P1B Transcendental AST and Solvers.

Tests:
1. Typed AST nodes for FunctionCall and NamedConstant.
2. Safe tokenization and parsing for sin, cos, tan, exp, log, ln, pi, e.
3. Multi-argument log parsing (log(arg, base), \\log_{base}(arg)) and comma isolation.
4. AST to SymPy bridge safety (no eval/exec/sympify).
5. Domain extraction (log arguments > 0, base > 0 & != 1, tan cos != 0).
6. Trig simplification (e.g. sin(x+pi/4) - cos(x-pi/4) = 0).
7. Transcendental differentiation with chain rule.
8. Exact log evaluation (e.g. log_2(12) - log_2(3) = 2).
9. Domain-guarded equation solving with extraneous root elimination.
"""

import pytest
import sympy

from mke_product.cas.ast_bridge import ast_to_sympy, ast_to_sympy_expr
from mke_product.cas.cas_parser import (
    CASParser,
    CASPower,
    Inequality,
    LinearSystem,
    is_top_level_system,
    parse_cas_equation,
    parse_cas_expression,
    tokenize_cas,
)
from mke_product.cas.contracts import EngineStatus, ExecutionRequest, OperationType
from mke_product.cas.router import CASRouter, execute_cas_operation
from mke_product.cas.safety import extract_domain_restrictions, inspect_ast_safety
from mke_product.parser.ast import (
    ASTNode,
    Equation,
    FunctionCall,
    IntegerLiteral,
    NamedConstant,
    Power,
    Variable,
)
from mke_product.parser.errors import ImplicitMultiplicationError, ParserError


# ==============================================================================
# 1. AST & PARSER UNIT TESTS
# ==============================================================================

def test_ast_function_call_and_constants_creation():
    """Verify typed AST creation and immutability for FunctionCall and NamedConstant."""
    pi_const = NamedConstant(name="pi", span=(0, 2))
    e_const = NamedConstant(name="e", span=(0, 1))
    assert pi_const.name == "pi"
    assert e_const.name == "e"
    assert pi_const.variables() == set()
    assert e_const.variables() == set()

    x_var = Variable(name="x", span=(0, 1))
    sin_call = FunctionCall(name="sin", args=(x_var,), span=(0, 6))
    assert sin_call.name == "sin"
    assert sin_call.variables() == {"x"}

    log2_call = FunctionCall(
        name="log",
        args=(x_var, IntegerLiteral(value=2, span=(0, 1))),
        span=(0, 9),
    )
    assert log2_call.name == "log"
    assert len(log2_call.args) == 2
    assert log2_call.variables() == {"x"}


def test_parse_trigonometric_functions():
    """Verify parsing sin, cos, tan in ASCII and LaTeX syntax."""
    expr1 = parse_cas_expression("sin(x)")
    assert isinstance(expr1, FunctionCall)
    assert expr1.name == "sin"

    expr2 = parse_cas_expression("\\cos(2*x)")
    assert isinstance(expr2, FunctionCall)
    assert expr2.name == "cos"

    expr3 = parse_cas_expression("\\tan(x + \\pi/4)")
    assert isinstance(expr3, FunctionCall)
    assert expr3.name == "tan"


def test_parse_power_on_trig_functions():
    """Verify parsing powers on function names e.g. \\sin^2(x)."""
    expr = parse_cas_expression("\\sin^2(x)")
    assert isinstance(expr, Power)
    assert isinstance(expr.base, FunctionCall)
    assert expr.base.name == "sin"
    assert expr.exponent.value == 2


def test_parse_exponential_and_constants():
    """Verify parsing exp(x), e^x, 2^(x+1), pi."""
    expr1 = parse_cas_expression("exp(3*x)")
    assert isinstance(expr1, FunctionCall)
    assert expr1.name == "exp"

    expr2 = parse_cas_expression("e^(2*x)")
    assert isinstance(expr2, CASPower)
    assert isinstance(expr2.base, NamedConstant)
    assert expr2.base.name == "e"

    expr3 = parse_cas_expression("2^(x+1)")
    assert isinstance(expr3, CASPower)


def test_parse_logarithms_and_subscripts():
    """Verify parsing ln(x), log(x), log(x, 2), \\log_2(x), \\log_{2}(x)."""
    expr_ln = parse_cas_expression("\\ln(x)")
    assert isinstance(expr_ln, FunctionCall)
    assert expr_ln.name == "ln"

    expr_log1 = parse_cas_expression("log(x)")
    assert isinstance(expr_log1, FunctionCall)
    assert len(expr_log1.args) == 1

    expr_log2 = parse_cas_expression("log(x, 2)")
    assert isinstance(expr_log2, FunctionCall)
    assert len(expr_log2.args) == 2

    expr_log_sub = parse_cas_expression("\\log_2(x)")
    assert isinstance(expr_log_sub, FunctionCall)
    assert len(expr_log_sub.args) == 2

    expr_log_sub_brace = parse_cas_expression("\\log_{2}(x+1)")
    assert isinstance(expr_log_sub_brace, FunctionCall)
    assert len(expr_log_sub_brace.args) == 2


def test_comma_inside_function_call_does_not_trigger_system():
    """CRITICAL: Commas inside function calls must not trigger LinearSystem parsing."""
    text = "log(x-1, 2) + log(x+1, 2) = 3"
    assert not is_top_level_system(text)
    eq = parse_cas_equation(text)
    assert isinstance(eq, Equation)

    # Top-level system should correctly be detected
    sys_text = "2*x + y = 5, x - y = 1"
    assert is_top_level_system(sys_text)


def test_implicit_multiplication_rejection_for_transcendentals():
    """Verify explicit multiplication requirement for constants and functions."""
    with pytest.raises(ImplicitMultiplicationError):
        tokenize_cas("2sin(x)")

    with pytest.raises(ImplicitMultiplicationError):
        tokenize_cas("2pi")

    with pytest.raises(ImplicitMultiplicationError):
        tokenize_cas("2e^x")

    with pytest.raises(ImplicitMultiplicationError):
        tokenize_cas("x\\cos(x)")


# ==============================================================================
# 2. AST BRIDGE & SAFETY TESTS
# ==============================================================================

def test_ast_bridge_transcendental_objects():
    """Verify AST to SymPy translation produces clean SymPy objects without eval/exec."""
    sin_ast = parse_cas_expression("\\sin(x)")
    sym_sin = ast_to_sympy_expr(sin_ast)
    assert isinstance(sym_sin, sympy.sin)

    log_ast = parse_cas_expression("log(x, 2)")
    sym_log = ast_to_sympy_expr(log_ast)
    assert sympy.simplify(sym_log - sympy.log(sympy.Symbol("x", real=True)) / sympy.log(2)) == 0

    pi_ast = parse_cas_expression("\\pi")
    sym_pi = ast_to_sympy_expr(pi_ast)
    assert sym_pi == sympy.pi

    e_ast = parse_cas_expression("e")
    sym_e = ast_to_sympy_expr(e_ast)
    assert sym_e == sympy.E


def test_domain_restriction_extraction():
    """Verify domain extraction for logarithms and tangent."""
    log_eq = parse_cas_equation("log(x-1, 2) = 3")
    restrs = extract_domain_restrictions(log_eq)
    assert any("x - 1 > 0" in r or "x > 1" in r for r in restrs)

    tan_expr = parse_cas_expression("\\tan(2*x)")
    restrs_tan = extract_domain_restrictions(tan_expr)
    assert any("cos(2*x) != 0" in r for r in restrs_tan)


# ==============================================================================
# 3. CAS SOLVER EXECUTION TESTS
# ==============================================================================

def test_trig_simplification():
    """Verify trigonometric identity simplification."""
    # sin(x + pi/4) - cos(x - pi/4) = 0
    res = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\sin(x + \\pi/4) - \\cos(x - \\pi/4)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert res.symbolic_result == "0"

    # sin^2(x) + cos^2(x) = 1
    res2 = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\sin^2(x) + \\cos^2(x)",
    )
    assert res2.mathematical_status == EngineStatus.SUCCESS
    assert res2.symbolic_result == "1"


def test_exact_logarithm_evaluation():
    """Verify exact logarithm evaluation: log_2(12) - log_2(3) = 2."""
    res = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\log(12, 2) - \\log(3, 2)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert res.symbolic_result == "2"

    res_ln = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\ln(e^3)",
    )
    assert res_ln.mathematical_status == EngineStatus.SUCCESS
    assert res_ln.symbolic_result == "3"


def test_transcendental_differentiation():
    """Verify differentiation of compositions of transcendental functions."""
    # d/dx [sin(2*x) + exp(3*x)] = 2*cos(2*x) + 3*exp(3*x)
    res = execute_cas_operation(
        OperationType.DIFFERENTIATE,
        "\\sin(2*x) + \\exp(3*x)",
        variable="x",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "2*cos(2*x)" in res.symbolic_result or "2*cos(2*x) + 3*exp(3*x)" in res.symbolic_result
    assert "3*exp(3*x)" in res.symbolic_result

    # d/dx [log(x, 2)]
    res_log = execute_cas_operation(
        OperationType.DIFFERENTIATE,
        "\\log(x, 2)",
        variable="x",
    )
    assert res_log.mathematical_status == EngineStatus.SUCCESS
    assert "log(2)" in res_log.symbolic_result


def test_log_equation_solving_and_extraneous_root_elimination():
    """CRITICAL: Verify log equation solving with extraneous root elimination.
    
    log_2(x-1) + log_2(x+1) = 3
    Algebraic roots: x = 3, x = -3.
    x = -3 is extraneous because log_2(-4) is undefined in the real domain.
    Expected solution set: {3}.
    """
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\log(x-1, 2) + \\log(x+1, 2) = 3",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert res.symbolic_result == "{3}"
    assert "-3" in res.verification_evidence.get("extraneous_roots", [])


def test_log_equality_equation():
    """Verify log_2(x^2 - 3) = log_2(2*x) -> {3} with extraneous root -1 eliminated."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\log(x^2 - 3, 2) = \\log(2*x, 2)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert res.symbolic_result == "{3}"
    assert "-1" in res.verification_evidence.get("extraneous_roots", [])


def test_exponential_equation_solving():
    """Verify solving exponential equations: 2^(x+1) = 8 -> {2}, exp(2*x) - 3*exp(x) + 2 = 0."""
    res1 = execute_cas_operation(
        OperationType.SOLVE,
        "2^(x+1) = 8",
    )
    assert res1.mathematical_status == EngineStatus.SUCCESS
    assert res1.symbolic_result == "{2}"

    res2 = execute_cas_operation(
        OperationType.SOLVE,
        "\\exp(2*x) - 3*\\exp(x) + 2 = 0",
    )
    assert res2.mathematical_status == EngineStatus.SUCCESS
    assert "0" in res2.symbolic_result
    assert "log(2)" in res2.symbolic_result or "ln(2)" in res2.symbolic_result
