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

import math
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
from mke_product.cas.contracts import (
    DomainCertainty,
    EngineStatus,
    ExecutionRequest,
    OperationType,
    VerificationStatus,
)
from mke_product.cas.router import CASRouter, EngineRouter, execute_cas_operation
from mke_product.cas.safety import extract_domain_restrictions, inspect_ast_safety
from mke_product.cas.sympy_adapter import execute_sympy_direct
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


# ==============================================================================
# 4. P1B-R1 DOMAIN IDENTITIES & PERIODIC TRIGONOMETRIC TESTS
# ==============================================================================

def test_transcendental_identity_ln_domain():
    """Verify ln(x) = ln(x) -> (0, oo) with SUCCESS."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\ln(x) = \\ln(x)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "(0, oo)" in res.symbolic_result
    assert res.domain_certainty == DomainCertainty.PROVEN_REALS


def test_transcendental_identity_log_domain():
    """Verify log(x-1, 2) = log(x-1, 2) -> (1, oo) with SUCCESS."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\log(x-1, 2) = \\log(x-1, 2)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "(1, oo)" in res.symbolic_result
    assert res.domain_certainty == DomainCertainty.PROVEN_REALS


def test_transcendental_identity_tan_domain():
    """Verify tan(x) = tan(x) -> All real numbers except pi/2 + k*pi (k integer)."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\tan(x) = \\tan(x)",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "All real numbers except" in res.symbolic_result
    assert "pi/2 + k*pi" in res.symbolic_result
    assert res.domain_certainty == DomainCertainty.EXPLICIT_EXCLUSIONS


def test_transcendental_identity_injected_failure():
    """Verify injected domain calculation failure fails closed with UNRESOLVED / NOT_FULLY_DETERMINED."""
    from unittest.mock import patch
    with patch("sympy.solveset", side_effect=RuntimeError("Injected solveset crash")):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="\\ln(x) = \\ln(x)",
        )
        res = execute_sympy_direct(req)
        assert res.mathematical_status == EngineStatus.UNRESOLVED
        assert res.verification_status == VerificationStatus.UNRESOLVED
        assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_periodic_trig_sin_half():
    """Verify sin(x) = 1/2 produces complete two-family general solution with k in Z."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(x) = 1/2",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "pi/6 + 2*k*pi" in res.symbolic_result
    assert "5*pi/6 + 2*k*pi" in res.symbolic_result
    assert "k in Z" in res.symbolic_result
    assert res.verification_evidence.get("solution_type") == "periodic_family"


def test_periodic_trig_cos_zero():
    """Verify cos(x) = 0 -> x = pi/2 + k*pi (k in Z)."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\cos(x) = 0",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "pi/2 + k*pi" in res.symbolic_result
    assert "k in Z" in res.symbolic_result


def test_periodic_trig_tan_one():
    """Verify tan(x) = 1 -> x = pi/4 + k*pi (k in Z)."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\tan(x) = 1",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "pi/4 + k*pi" in res.symbolic_result
    assert "k in Z" in res.symbolic_result


def test_periodic_trig_transformed_arg():
    """Verify sin(2*x - pi/6) = 1/2 -> x = pi/6 + k*pi, x = pi/2 + k*pi (k in Z)."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(2*x - \\pi/6) = 1/2",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "pi/6 + k*pi" in res.symbolic_result
    assert "pi/2 + k*pi" in res.symbolic_result
    assert "k in Z" in res.symbolic_result


def test_periodic_trig_empty_set():
    """Verify sin(x) = 2 and cos(x) = -3 produce empty solution set."""
    res_sin = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(x) = 2",
    )
    assert res_sin.mathematical_status == EngineStatus.SUCCESS
    assert res_sin.symbolic_result == "{}"

    res_cos = execute_cas_operation(
        OperationType.SOLVE,
        "\\cos(x) = -3",
    )
    assert res_cos.mathematical_status == EngineStatus.SUCCESS
    assert res_cos.symbolic_result == "{}"


def test_periodic_trig_unsupported_nonlinear_fail_closed():
    """Verify non-elementary periodic equation fails closed with OUT_OF_SCOPE / UNRESOLVED."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(x) + \\cos(x) = x",
    )
    assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
    assert res.verification_status == VerificationStatus.UNRESOLVED
    assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_domain_error_invalid_log_and_tan():
    """Verify invalid constant log arguments, bases, and tan poles strictly raise DOMAIN_ERROR."""
    res_neg_log = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\log(-4, 2)",
    )
    assert res_neg_log.mathematical_status == EngineStatus.DOMAIN_ERROR
    assert res_neg_log.verification_status == VerificationStatus.ERROR

    res_base_1 = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\log(5, 1)",
    )
    assert res_base_1.mathematical_status == EngineStatus.DOMAIN_ERROR
    assert res_base_1.verification_status == VerificationStatus.ERROR

    res_neg_base = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\log(8, -2)",
    )
    assert res_neg_base.mathematical_status == EngineStatus.DOMAIN_ERROR
    assert res_neg_base.verification_status == VerificationStatus.ERROR

    res_ln_0 = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\ln(0)",
    )
    assert res_ln_0.mathematical_status == EngineStatus.DOMAIN_ERROR
    assert res_ln_0.verification_status == VerificationStatus.ERROR

    res_tan_pole = execute_cas_operation(
        OperationType.SIMPLIFY,
        "\\tan(\\pi/2)",
    )
    assert res_tan_pole.mathematical_status == EngineStatus.DOMAIN_ERROR
    assert res_tan_pole.verification_status == VerificationStatus.ERROR


def test_syntax_error_malformed_inputs_invalid_input():
    """Verify actual malformed syntax and parsing failures return INVALID_INPUT."""
    malformed_cases = [
        "\\log(",
        "\\sin(+-)",
        "\\tan)x(",
        "\\sin(x",
        "1 + * 2",
    ]
    for expr in malformed_cases:
        res = execute_cas_operation(OperationType.SIMPLIFY, expr)
        assert res.mathematical_status == EngineStatus.INVALID_INPUT
        assert res.verification_status == VerificationStatus.ERROR


def test_periodic_trig_adversarial_sin_3x_zero():
    """Verify sin(3*x) = 0 produces exact family x = k*pi/3 (k in Z) and algebraic substitution holds."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(3*x) = 0",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "k*pi/3" in res.symbolic_result
    assert "k in Z" in res.symbolic_result

    # Algebraic verification across parameter range k in [-3, 3]
    for k_val in range(-3, 4):
        x_val = k_val * math.pi / 3
        # sin(3 * (k*pi/3)) = sin(k*pi) = 0
        val = math.sin(3 * x_val)
        assert abs(val) < 1e-12, f"Failed at k={k_val}: sin(3*{x_val}) = {val}"


def test_periodic_trig_adversarial_cos_2x_one():
    """Verify cos(2*x) = 1 produces exact family x = k*pi (k in Z) and algebraic substitution holds."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\cos(2*x) = 1",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "k*pi" in res.symbolic_result
    assert "k in Z" in res.symbolic_result

    # Algebraic verification across parameter range k in [-3, 3]
    for k_val in range(-3, 4):
        x_val = k_val * math.pi
        val = math.cos(2 * x_val)
        assert abs(val - 1.0) < 1e-12, f"Failed at k={k_val}: cos(2*{x_val}) = {val}"


def test_periodic_trig_adversarial_tan_2x_one():
    """Verify tan(2*x) = 1 produces exact family x = pi/8 + k*pi/2 (k in Z) and algebraic substitution holds."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\tan(2*x) = 1",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "pi/8" in res.symbolic_result
    assert "k*pi/2" in res.symbolic_result
    assert "k in Z" in res.symbolic_result

    # Algebraic verification across parameter range k in [-3, 3]
    for k_val in range(-3, 4):
        x_val = math.pi / 8 + k_val * math.pi / 2
        val = math.tan(2 * x_val)
        assert abs(val - 1.0) < 1e-12, f"Failed at k={k_val}: tan(2*{x_val}) = {val}"


def test_periodic_trig_adversarial_negative_coefficient():
    """Verify transformed affine trigonometric equation with negative coefficient sin(-2*x + pi/3) = 1/2."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\sin(-2*x + \\pi/3) = 1/2",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert "k in Z" in res.symbolic_result
    # Families are x = pi/12 + k*pi or x = -pi/4 + k*pi
    assert "pi/12" in res.symbolic_result
    assert "-pi/4" in res.symbolic_result or "3*pi/4" in res.symbolic_result or "pi/4" in res.symbolic_result

    # Verification across parameters k in [-2, 2]
    # Family 1: x = pi/12 + k*pi -> -2x + pi/3 = -pi/6 - 2k*pi + pi/3 = pi/6 - 2k*pi -> sin = 1/2
    for k_val in range(-2, 3):
        x1 = math.pi / 12 + k_val * math.pi
        v1 = math.sin(-2 * x1 + math.pi / 3)
        assert abs(v1 - 0.5) < 1e-12, f"Failed family 1 at k={k_val}"

        x2 = -math.pi / 4 + k_val * math.pi
        v2 = math.sin(-2 * x2 + math.pi / 3)
        assert abs(v2 - 0.5) < 1e-12, f"Failed family 2 at k={k_val}"


def test_supervised_transcendental_identity_and_trig_solver():
    """Verify execution of transcendental identity and periodic trig through supervised EngineRouter."""
    router = EngineRouter()
    
    # 1. Identity ln(x) = ln(x)
    req_id = ExecutionRequest(
        operation=OperationType.SOLVE,
        expression="\\ln(x) = \\ln(x)",
    )
    res_id = router.execute(req_id)
    assert res_id.mathematical_status == EngineStatus.SUCCESS
    assert "(0, oo)" in res_id.symbolic_result

    # 2. Periodic sin(x) = 1/2
    req_trig = ExecutionRequest(
        operation=OperationType.SOLVE,
        expression="\\sin(x) = 1/2",
    )
    res_trig = router.execute(req_trig)
    assert res_trig.mathematical_status == EngineStatus.SUCCESS
    assert "pi/6 + 2*k*pi" in res_trig.symbolic_result
    assert "k in Z" in res_trig.symbolic_result


def test_counterexample_2_pow_x_eq_x_sq_fails_closed():
    """Task A Counterexample 1: 2^x = x^2 has 2, 4 and a negative root in (-1, 0).
    The engine must NOT return partial roots {2, 4} as a complete SUCCESS solution set.
    It must fail closed with OUT_OF_SCOPE / UNRESOLVED.
    """
    res = execute_cas_operation(
        OperationType.SOLVE,
        "2^x = x^2",
    )
    assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
    assert res.verification_status == VerificationStatus.UNRESOLVED
    assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_counterexample_ln_x_plus_x_eq_zero_fails_closed():
    """Task A Counterexample 2: ln(x) + x = 0 has root x = W(1) ~ 0.56714.
    The engine must NOT claim an empty set {} or uncertified LambertW as complete SUCCESS.
    It must fail closed with OUT_OF_SCOPE / UNRESOLVED.
    """
    res = execute_cas_operation(
        OperationType.SOLVE,
        "\\ln(x) + x = 0",
    )
    assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
    assert res.verification_status == VerificationStatus.UNRESOLVED
    assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_counterexample_mixed_transcendental_fails_closed():
    """Task A Counterexample 3: Genuinely unsupported mixed transcendental equations fail closed."""
    cases = [
        "\\sin(x) + x = 1",
        "\\exp(x) - \\cos(x) = 2",
        "x*\\log(x, 2) = 4",
    ]
    for expr in cases:
        res = execute_cas_operation(OperationType.SOLVE, expr)
        assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
        assert res.verification_status == VerificationStatus.UNRESOLVED
        assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_counterexample_2_pow_x_plus_3_pow_x_eq_7_fails_closed():
    """Task 1 Mandatory Counterexample: 2^x + 3^x = 7 has real root in (1, 2).
    SymPy solve cannot solve this multi-base sum and returns empty candidate list.
    The engine must NEVER certify an empty candidate list as SUCCESS with {}.
    It MUST fail closed with OUT_OF_SCOPE or UNRESOLVED.
    """
    res = execute_cas_operation(
        OperationType.SOLVE,
        "2^x + 3^x = 7",
    )
    assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
    assert res.symbolic_result != "{}"
    assert res.symbolic_result is None
    assert res.verification_status == VerificationStatus.UNRESOLVED
    assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED


def test_proven_empty_exponential_equation():
    """Verify that a genuine mathematically proven empty exponential equation 2^(x+1) = -4 yields {} with SUCCESS."""
    res = execute_cas_operation(
        OperationType.SOLVE,
        "2^(x+1) = -4",
    )
    assert res.mathematical_status == EngineStatus.SUCCESS
    assert res.symbolic_result == "{}"


def test_simulated_empty_candidates_on_unclassified_fails_closed():
    """Verify that empty candidate list on unclassified transcendental equations fails closed."""
    cases = [
        "2^x + 5^x = 10",
        "3^x + 4^x = 25",  # has root x=2, but multi-base must not claim {} if solver fails
        "\\log(x, 2) + \\log(x, 3) = 5",  # multi-base log
    ]
    for expr in cases:
        res = execute_cas_operation(OperationType.SOLVE, expr)
        if res.mathematical_status == EngineStatus.SUCCESS:
            assert res.symbolic_result != "{}"
        else:
            assert res.mathematical_status in (EngineStatus.OUT_OF_SCOPE, EngineStatus.UNRESOLVED)
            assert res.domain_certainty == DomainCertainty.NOT_FULLY_DETERMINED



