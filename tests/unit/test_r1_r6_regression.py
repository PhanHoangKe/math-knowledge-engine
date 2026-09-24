"""Independent Regression Test Suite (R1 - R6) for DEV-01-R1 remediation."""

from fractions import Fraction
import pytest
import sympy

from mke.domain.extractor import extract_original_domain
from mke.models.enums import MethodId, SolutionProofStatus, TransferValidity
from mke.models.domain import OriginalDomain, DomainCondition
from mke.parsing.exceptions import CoefficientMagnitudeError, InvalidExponentError, OutOfScopeSyntaxError
from mke.parsing.limits import ParserLimits
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer, safe_parse_candidate_root


@pytest.fixture
def engine() -> VerificationEngine:
    return VerificationEngine()


# ---------------------------------------------------------------------------
# R1: Operator Precedence (-x^2 parses as -(x^2), not (-x)^2)
# ---------------------------------------------------------------------------

def test_r1_operator_precedence_negative_power(engine):
    """R1.1: -x^2 + 4 = 0 must solve to x = +/- 2."""
    res = engine.verify("-x^2 + 4 = 0")
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert sorted(res.verified_roots) == ["-2", "2"]
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_r1_operator_precedence_parenthesized_vs_unparenthesized():
    """R1.2: -x^2 vs (-x)^2 AST structures and values."""
    ast_unparen = Parser.from_text("-x^2 = 0").parse_equation()
    ast_paren = Parser.from_text("(-x)^2 = 0").parse_equation()

    # -x^2 has UnaryOpNode at top of LHS
    assert ast_unparen.left.__class__.__name__ == "UnaryOpNode"
    assert ast_unparen.left.op == "-"
    assert ast_unparen.left.operand.__class__.__name__ == "BinaryOpNode"
    assert ast_unparen.left.operand.op == "^"

    # (-x)^2 has BinaryOpNode at top of LHS
    assert ast_paren.left.__class__.__name__ == "BinaryOpNode"
    assert ast_paren.left.op == "^"
    assert ast_paren.left.left.__class__.__name__ == "UnaryOpNode"


def test_r1_negative_number_power():
    """R1.3: -2^2 must evaluate to -4, while (-2)^2 evaluates to 4."""
    norm_unparen = normalize_equation(Parser.from_text("-2^2 = x").parse_equation())
    # -2^2 - x = 0 => -x - 4 = 0 => x = -4
    assert norm_unparen.coefficients.get(0) == sympy.Integer(-4)

    norm_paren = normalize_equation(Parser.from_text("(-2)^2 = x").parse_equation())
    # (-2)^2 - x = 0 => -x + 4 = 0 => x = 4
    assert norm_paren.coefficients.get(0) == sympy.Integer(4)


def test_r1_roundtrip_ast_math_string():
    """R1.4: AST -> to_math_string() -> re-parse preserves exact AST semantics."""
    test_expressions = [
        "-x^2 = 0",
        "(-x)^2 = 0",
        "-(x + 1) = 0",
        "2 * (-x) = 0",
        "-x * 2 = 0",
        "x^2 - 5*x + 6 = 0",
        "(x - 2) / (x - 2) = 1",
    ]
    for expr_str in test_expressions:
        ast1 = Parser.from_text(expr_str).parse_equation()
        serialized = ast1.to_math_string()
        ast2 = Parser.from_text(serialized).parse_equation()
        assert ast1 == ast2, f"Roundtrip failed for '{expr_str}': serialized to '{serialized}'"


# ---------------------------------------------------------------------------
# R2: Exact Domain Arithmetic (No Float Epsilon Conflation)
# ---------------------------------------------------------------------------

def test_r2_exact_domain_close_roots_not_conflated():
    """R2.1: Values separated by < 1e-12 must NOT be conflated by float epsilon."""
    # Exclude 1 / 10^13 (which is 1e-13 > 0, but < 1e-12)
    small_excl = Fraction(1, 10**13)
    cond = DomainCondition(
        raw_expression_str="x - 1/10000000000000",
        condition_str="x != 1/10000000000000",
        excluded_values={small_excl},
    )
    domain = OriginalDomain([cond])

    # With the old abs(...) < 1e-12, 0 would be conflated with 1e-13!
    assert domain.contains(0) is True, "0 should be in domain, not conflated with 1e-13"
    assert domain.contains(Fraction(0, 1)) is True
    assert domain.contains(small_excl) is False, "Exact excluded value must NOT be in domain"


def test_r2_exact_symbolic_algebraic_comparison():
    """R2.2: Exact algebraic equivalence (e.g. sqrt(2) == 2/sqrt(2))."""
    sqrt2 = sympy.sqrt(2)
    cond = DomainCondition(
        raw_expression_str="x - sqrt(2)",
        condition_str="x != sqrt(2)",
        excluded_values={sqrt2},
    )
    domain = OriginalDomain([cond])

    # Mathematically identical algebraic number must be excluded
    ident_sqrt2 = 2 / sympy.sqrt(2)
    assert domain.contains(ident_sqrt2) is False

    # Distinct float or close approximation must NOT be falsely excluded
    approx = Fraction(141421356237, 100000000000)  # 1.41421356237
    assert domain.contains(approx) is True


# ---------------------------------------------------------------------------
# R3: Denominator Identically Zero => Empty Domain
# ---------------------------------------------------------------------------

def test_r3_constant_zero_division_empty_domain(engine):
    """R3.1: x / 0 = 0 has empty domain and no solutions."""
    res = engine.verify("x / 0 = 0")
    assert res.domain_str == "\\emptyset"
    assert res.is_all_reals_domain is False
    assert res.is_verified_solution is True
    assert res.verified_roots == []
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_r3_identically_zero_polynomial_denominator(engine):
    """R3.2: 1 / (x - x) = 0 has identically zero denominator and empty domain."""
    res = engine.verify("1 / (x - x) = 0")
    assert res.domain_str == "\\emptyset"
    assert res.is_all_reals_domain is False
    assert res.is_verified_solution is True
    assert res.verified_roots == []
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_r3_domain_contains_returns_false_on_empty_domain():
    """R3.3: contains() on an empty domain always returns False for all points."""
    dom = OriginalDomain(is_empty_domain=True)
    assert dom.is_empty_domain is True
    assert dom.is_all_reals() is False
    assert dom.contains(0) is False
    assert dom.contains(100) is False
    assert dom.contains(Fraction(-5, 2)) is False
    assert dom.contains(sympy.Integer(42)) is False
    assert dom.format_domain() == "\\emptyset"


# ---------------------------------------------------------------------------
# R4: Resource Bounds & Intermediate Expression Growth
# ---------------------------------------------------------------------------

def test_r4_high_degree_rejection_out_of_scope(engine):
    """R4.1: Higher degree equation (degree 8) is cleanly rejected as OUT_OF_SCOPE."""
    res = engine.verify("x^4 * x^4 = 0")
    assert res.is_verified_method is False
    assert res.is_verified_solution is False
    assert res.solution_status == SolutionProofStatus.UNDETERMINED
    assert "OUT_OF_SCOPE" in res.explanation
    assert "degree 8" in res.explanation


def test_r4_coefficient_magnitude_limit():
    """R4.2: Polynomial coefficient exceeding limits triggers CoefficientMagnitudeError.

    Tests both:
    1. Lexer catching literal coefficient exceeding magnitude.
    2. Normalizer catching expanded intermediate coefficient exceeding magnitude.
    """
    limits = ParserLimits(max_coefficient_magnitude=1000)

    # 1. Lexer check
    with pytest.raises(CoefficientMagnitudeError):
        Parser.from_text("5000*x + 1 = 0", limits=limits).parse_equation()

    # 2. Normalizer expansion check (inputs < 1000, but product 200 * 200 = 40000 > 1000)
    ast = Parser.from_text("(200*x + 1) * (200*x + 1) = 0", limits=limits).parse_equation()
    with pytest.raises(CoefficientMagnitudeError):
        normalize_equation(ast, limits=limits)


# ---------------------------------------------------------------------------
# R5: Method M5 Symbolic Sign & Complex Root Handling
# ---------------------------------------------------------------------------

def test_r5_m5_symbolic_sign_all_negative(engine):
    """R5.1: x^4 + 5*x^2 + 4 = 0 has t = -1, -4 (< 0). Real roots empty, PASS."""
    res = engine.verify("x^4 + 5*x^2 + 4 = 0")
    assert res.is_verified_method is True
    assert res.is_verified_solution is True
    assert res.method_instance.method_id == MethodId.M5_BIQUADRATIC_SUBSTITUTION
    assert res.verified_roots == []
    assert res.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE


def test_r5_m5_safe_sorting_no_complex_crash():
    """R5.2: Ensure safe sort key handles complex/algebraic expressions without float() crash."""
    from mke.methods.m5_biquadratic import BiquadraticSubstitutionMethod
    m5 = BiquadraticSubstitutionMethod()
    # x^4 - 2 = 0 => t^2 - 2 = 0 => t = sqrt(2) >= 0 => x = +/- 2^(1/4)
    ast = Parser.from_text("x^4 - 2 = 0").parse_equation()
    norm = normalize_equation(ast)
    out = m5.solve_instance(norm)
    assert len(out.candidate_roots) == 2


# ---------------------------------------------------------------------------
# R6: Elimination of Unsafe sympify() on Untrusted Inputs
# ---------------------------------------------------------------------------

def test_r6_transfer_rejects_code_injection_strings():
    """R6.1: audit_solution_transfer safely parses/rejects untrusted strings without code execution."""
    ast = Parser.from_text("x^2 - 4 = 0").parse_equation()
    norm = normalize_equation(ast)

    injection_strings = [
        "__import__('os').system('calc')",
        "eval('2+2')",
        "exec('x=1')",
        "os.remove('file.txt')",
    ]
    val, valid, rejected = audit_solution_transfer(norm, injection_strings)
    assert val == TransferValidity.UNSAFE_COPY
    assert len(valid) == 0
    assert len(rejected) == len(injection_strings)
    for r in rejected:
        assert "rejected" in r.lower() or "unsafe" in r.lower()


def test_r6_domain_contains_rejects_code_injection_strings():
    """R6.2: OriginalDomain.contains safely rejects malicious strings without sympify()."""
    ast = Parser.from_text("x^2 - 4 = 0").parse_equation()
    norm = normalize_equation(ast)
    domain = norm.domain

    assert domain.contains("__import__('os').system('calc')") is False
    assert domain.contains("eval('1+1')") is False
    assert domain.contains("open('/etc/passwd')") is False
