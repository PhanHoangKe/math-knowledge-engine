"""DEV-01-R2 Soundness Regression Test Suite.

Verifies fixes for all 5 coordinator findings in DEV-01-R2:
1. M4 completeness proof obligations and solveset result handling (mandatory test: (x^4 - x - 1)/(x^2 + 1) = 0).
2. Real domain verification rejecting complex/imaginary numbers and free symbols in contains() and transfer.
3. Empty domain consistency (is_verified_method=False, is_verified_solution=True, method_instance=None).
4. Structured resource limit and syntax error classification (RESOURCE_LIMIT, OUT_OF_SCOPE, SYNTAX_ERROR).
5. AST tree structure round-trip preservation (1 + (x - 2) = 0, x + 0.25 = 0, x * (x / 2) = 0).
"""

from fractions import Fraction
import pytest
import sympy

from mke.models.domain import OriginalDomain, is_proven_real_number
from mke.models.enums import (
    MethodId,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    TransferValidity,
)
from mke.parsing import (
    ASTDepthExceededError,
    CoefficientMagnitudeError,
    InputLengthExceededError,
    InvalidExponentError,
    InvalidSyntaxError,
    OutOfScopeSyntaxError,
    Parser,
    ParserLimits,
    TokenCountExceededError,
    normalize_equation,
)
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


# ==============================================================================
# Requirement 1: M4 Completeness & Solveset Result Handling
# ==============================================================================

def test_m4_quartic_solveset_unresolved_completeness():
    """Mandatory test: (x^4 - x - 1) / (x^2 + 1) = 0 has real roots.

    System must:
    - NOT conclude no solutions exist.
    - Find the 2 real roots.
    - Mark COMPLETENESS obligation as UNRESOLVED.
    - NOT grant is_verified_solution = True.
    - Report solution_status = SOUND_PARTIAL.
    """
    engine = VerificationEngine()
    result = engine.verify("(x^4 - x - 1) / (x^2 + 1) = 0")

    assert result.method_instance is not None
    assert result.method_instance.method_id == MethodId.M4_RATIONAL_EQUATION
    assert result.is_verified_method is True

    # Critical requirement: incomplete proof must NEVER be certified as verified solution
    assert result.is_verified_solution is False
    assert result.solution_status == SolutionProofStatus.SOUND_PARTIAL

    # Must find the real roots, NOT conclude empty set
    assert len(result.verified_roots) == 2
    assert "no real solutions" not in result.explanation.lower()

    # Completeness obligation must be UNRESOLVED
    completeness_ob = next(
        (o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS), None
    )
    assert completeness_ob is not None
    assert completeness_ob.status == ObligationStatus.UNRESOLVED


def test_m4_truly_empty_real_roots():
    """(x^4 + 1) / (x^2 + 1) = 0 has NO real roots (x^4 + 1 > 0).

    System must distinguish this truly empty set from unhandled solveset types,
    proving completeness and certifying is_verified_solution = True.
    """
    engine = VerificationEngine()
    result = engine.verify("(x^4 + 1) / (x^2 + 1) = 0")

    assert result.method_instance is not None
    assert result.method_instance.method_id == MethodId.M4_RATIONAL_EQUATION
    assert result.is_verified_method is True
    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert len(result.verified_roots) == 0

    completeness_ob = next(
        (o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS), None
    )
    assert completeness_ob is not None
    assert completeness_ob.status == ObligationStatus.PASS


def test_m4_extraneous_root_excluded_completeness():
    """(x^3 - 1) / (x - 1) = 0: x = 1 is root of numerator, but excluded by denominator x != 1.

    Solution set is proven empty on original domain.
    """
    engine = VerificationEngine()
    result = engine.verify("(x^3 - 1) / (x - 1) = 0")

    assert result.is_verified_method is True
    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert len(result.verified_roots) == 0

    domain_obs = [o for o in result.obligations if o.obligation_id == ObligationId.ORIGINAL_DOMAIN]
    assert len(domain_obs) > 0
    assert any("x = 1" in o.description or "x = 1" in o.evidence for o in domain_obs)


def test_m4_cubic_complete_enumeration():
    """(x^3 - 8) / (x + 1) = 0: x = 2 is unique real root in domain."""
    engine = VerificationEngine()
    result = engine.verify("(x^3 - 8) / (x + 1) = 0")

    assert result.is_verified_method is True
    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert result.verified_roots == ["2"]

    completeness_ob = next(
        (o for o in result.obligations if o.obligation_id == ObligationId.COMPLETENESS), None
    )
    assert completeness_ob is not None
    assert completeness_ob.status == ObligationStatus.PASS


# ==============================================================================
# Requirement 2: Real Domain Verification & Solution Transfer Rejection
# ==============================================================================

def test_is_proven_real_number():
    """Verify is_proven_real_number strictly accepts real numbers and rejects others."""
    # Accepted real numbers
    assert is_proven_real_number(sympy.Integer(5)) is True
    assert is_proven_real_number(sympy.Rational(1, 4)) is True
    assert is_proven_real_number(sympy.sqrt(2)) is True
    assert is_proven_real_number(-sympy.sqrt(3) / 2) is True

    # Rejected complex numbers
    assert is_proven_real_number(sympy.I) is False
    assert is_proven_real_number(1 + 2 * sympy.I) is False
    assert is_proven_real_number(sympy.sqrt(-1)) is False

    # Rejected free symbols and expressions
    assert is_proven_real_number(sympy.Symbol("x")) is False
    assert is_proven_real_number(sympy.Symbol("y")) is False
    assert is_proven_real_number(sympy.Symbol("x") + 1) is False


def test_domain_contains_rejects_imaginary_and_symbols():
    """OriginalDomain.contains() must reject non-real numbers and expressions with variables."""
    domain = OriginalDomain()
    assert domain.contains(sympy.I) is False
    assert domain.contains(1 + 2 * sympy.I) is False
    assert domain.contains(sympy.Symbol("y")) is False
    assert domain.contains(sympy.Symbol("x") + 1) is False

    # Valid real numbers pass
    assert domain.contains(Fraction(1, 4)) is True
    assert domain.contains(sympy.Integer(0)) is True
    assert domain.contains(sympy.sqrt(5)) is True


def test_audit_solution_transfer_rejects_complex_candidate():
    """Mandatory test: target x^2 + 1 = 0, candidate transferred sympy.I -> UNSAFE_COPY."""
    eq_ast = Parser.from_text("x^2 + 1 = 0").parse_equation()
    target_norm = normalize_equation(eq_ast)

    validity, valid_roots, rejected_roots = audit_solution_transfer(
        target_norm_eq=target_norm,
        source_candidate_roots=[sympy.I],
    )

    assert validity == TransferValidity.UNSAFE_COPY
    assert len(valid_roots) == 0
    assert len(rejected_roots) == 1
    assert "not a valid real number" in rejected_roots[0]


def test_audit_solution_transfer_rejects_free_symbol():
    """Transfer of symbolic expression 'x + 1' must be rejected as UNSAFE_COPY."""
    eq_ast = Parser.from_text("x^2 - 4 = 0").parse_equation()
    target_norm = normalize_equation(eq_ast)

    validity, valid_roots, rejected_roots = audit_solution_transfer(
        target_norm_eq=target_norm,
        source_candidate_roots=[sympy.Symbol("x") + 1],
    )

    assert validity == TransferValidity.UNSAFE_COPY
    assert len(valid_roots) == 0
    assert len(rejected_roots) == 1


# ==============================================================================
# Requirement 3: Consistent Verification State on Empty Domain
# ==============================================================================

def test_empty_domain_verification_state():
    """When D = empty, solution set empty is proven purely by domain evidence.

    Must have:
    - method_instance = None
    - is_verified_method = False (no method was applied)
    - is_verified_solution = True (empty solution set proven)
    - solution_status = SOUND_AND_COMPLETE_IN_SCOPE
    - verified_roots = []
    """
    engine = VerificationEngine()
    result = engine.verify("x / 0 = 0")

    assert result.method_instance is None
    assert result.is_verified_method is False
    assert result.is_verified_solution is True
    assert result.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
    assert len(result.verified_roots) == 0
    assert "domain evidence" in result.explanation.lower()


# ==============================================================================
# Requirement 4: Resource Limit & Syntax Error Classification
# ==============================================================================

def test_resource_limit_input_length():
    """Input length exceeded returns structured RESOURCE_LIMIT result."""
    lim = ParserLimits(max_input_length=15)
    engine = VerificationEngine(limits=lim)
    result = engine.verify("x + 1234567890 = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "RESOURCE_LIMIT: InputLengthExceededError" in result.explanation


def test_resource_limit_token_count():
    """Token count exceeded returns structured RESOURCE_LIMIT result."""
    lim = ParserLimits(max_tokens=3)
    engine = VerificationEngine(limits=lim)
    result = engine.verify("x + 1 + 2 = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "RESOURCE_LIMIT: TokenCountExceededError" in result.explanation


def test_resource_limit_ast_depth():
    """AST depth exceeded returns structured RESOURCE_LIMIT result."""
    lim = ParserLimits(max_ast_depth=2)
    engine = VerificationEngine(limits=lim)
    result = engine.verify("(x + 1) * (x + 2) = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "RESOURCE_LIMIT: ASTDepthExceededError" in result.explanation


def test_resource_limit_coefficient_magnitude():
    """Coefficient magnitude exceeded returns structured RESOURCE_LIMIT result."""
    lim = ParserLimits(max_coefficient_magnitude=50)
    engine = VerificationEngine(limits=lim)
    result = engine.verify("x + 999 = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "RESOURCE_LIMIT: CoefficientMagnitudeError" in result.explanation


def test_resource_limit_exponent():
    """Exponent exceeding max degree returns structured RESOURCE_LIMIT result."""
    engine = VerificationEngine()
    result = engine.verify("x^5 = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "RESOURCE_LIMIT: InvalidExponentError" in result.explanation


def test_out_of_scope_syntax():
    """Out of scope functions return OUT_OF_SCOPE."""
    engine = VerificationEngine()
    result = engine.verify("sin(x) = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "OUT_OF_SCOPE" in result.explanation


def test_syntax_error_classification():
    """Invalid syntax returns SYNTAX_ERROR."""
    engine = VerificationEngine()
    result = engine.verify("x + = 0")

    assert result.is_verified_solution is False
    assert result.is_verified_method is False
    assert result.solution_status == SolutionProofStatus.UNDETERMINED
    assert "SYNTAX_ERROR" in result.explanation


# ==============================================================================
# Requirement 5: AST Tree Structure Preservation under Round-trip
# ==============================================================================

@pytest.mark.parametrize(
    "eq_str",
    [
        "1 + (x - 2) = 0",
        "x + 0.25 = 0",
        "x * (x / 2) = 0",
        "(x + 1) * (x - 2) = 0",
        "(x - 1) / (x + 1) = 0",
        "x^2 + 2*x + 1 = 0",
    ],
)
def test_ast_round_trip_preservation(eq_str: str):
    """to_math_string() must preserve exact AST tree structure when re-parsed."""
    ast1 = Parser.from_text(eq_str).parse_equation()
    rendered = ast1.to_math_string()
    ast2 = Parser.from_text(rendered).parse_equation()

    assert ast1 == ast2, f"AST structure changed on round-trip: '{eq_str}' -> '{rendered}'"
