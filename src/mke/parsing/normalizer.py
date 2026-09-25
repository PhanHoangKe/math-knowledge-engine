"""Equation normalization preserving domain audit trail and polynomial classification."""

from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional
import sympy

from mke.domain.extractor import extract_original_domain
from mke.models.ast_nodes import EquationNode
from mke.models.domain import OriginalDomain
from mke.parsing.exceptions import CoefficientMagnitudeError, OutOfScopeSyntaxError
from mke.parsing.limits import ParserLimits, DEFAULT_LIMITS
from mke.parsing.sympy_converter import ast_to_sympy, X_SYM


@dataclass
class NormalizedEquation:
    """Canonical representation of an equation with its full normalization history and domain."""

    raw_input: str
    raw_ast: EquationNode
    domain: OriginalDomain
    normalization_trace: List[str]

    # Canonical rational form: P(x) / Q(x) = 0
    numerator_sym: sympy.Expr
    denominator_sym: sympy.Expr
    numerator_poly: Optional[sympy.Poly]
    denominator_poly: Optional[sympy.Poly]

    is_rational: bool
    degree: int
    is_identity: bool
    is_contradiction: bool
    coefficients: Dict[int, sympy.Basic] = field(default_factory=dict)
    has_variable_denominator: bool = False


def normalize_equation(
    eq_ast: EquationNode,
    raw_text: str = "",
    limits: ParserLimits = DEFAULT_LIMITS,
) -> NormalizedEquation:
    """Normalize an equation AST into canonical polynomial/rational form with full trace."""
    trace: List[str] = []
    trace.append(f"Original input: {raw_text or eq_ast.to_math_string()}")
    trace.append(f"Unreduced AST: {eq_ast.to_math_string()}")

    # Step 1: Extract domain directly from unreduced AST
    domain = extract_original_domain(eq_ast)
    trace.append(f"Extracted original domain: {domain.format_domain()}")
    if domain.conditions:
        for c in domain.conditions:
            trace.append(f"  Constraint: {c.condition_str} (excluded: {c.excluded_values})")

    if domain.is_empty_domain:
        trace.append("Domain is empty set (division by zero in expression); equation has no real solutions.")
        return NormalizedEquation(
            raw_input=raw_text or eq_ast.to_math_string(),
            raw_ast=eq_ast,
            domain=domain,
            normalization_trace=trace,
            numerator_sym=sympy.Integer(1),
            denominator_sym=sympy.Integer(0),
            numerator_poly=None,
            denominator_poly=None,
            is_rational=True,
            degree=0,
            is_identity=False,
            is_contradiction=True,
            coefficients={},
            has_variable_denominator=True,
        )

    # Step 2: Convert to SymPy using whitelisted constructors
    lhs_sym = ast_to_sympy(eq_ast.left)
    rhs_sym = ast_to_sympy(eq_ast.right)
    trace.append(f"SymPy constructed: Eq({lhs_sym}, {rhs_sym})")

    # Step 3: Move all terms to LHS: LHS - RHS = 0
    diff_sym = sympy.Add(lhs_sym, sympy.Mul(sympy.Integer(-1), rhs_sym))
    trace.append(f"Difference expression (LHS - RHS): {diff_sym}")

    # Step 4: Rational reduction to P(x) / Q(x) = 0 without canceling original constraints
    combined = sympy.together(diff_sym)
    numer, denom = sympy.fraction(combined)
    trace.append(f"Rational canonical form: ({numer}) / ({denom}) = 0")

    # Step 5: Check denominator and distinguish constant non-zero denominators from variable denominators
    denom_has_x = X_SYM in denom.free_symbols
    orig_divs = eq_ast.collect_divisions()
    orig_denom_has_x = any("x" in d.right.collect_variables() for d in orig_divs)

    # Strictly preserve domain exclusions and variable denominators even after algebraic cancellation
    has_variable_denominator = (
        denom_has_x
        or orig_denom_has_x
        or len(domain.excluded_values) > 0
        or len(domain.conditions) > 0
        or domain.is_empty_domain
    )
    is_rational = has_variable_denominator

    denom_poly: Optional[sympy.Poly] = None
    if denom_has_x:
        try:
            denom_poly = sympy.Poly(denom, X_SYM)
            if denom_poly.degree() > limits.max_polynomial_degree:
                raise OutOfScopeSyntaxError(
                    f"Denominator degree {denom_poly.degree()} exceeds maximum supported degree {limits.max_polynomial_degree}"
                )
        except sympy.PolynomialError as e:
            raise OutOfScopeSyntaxError(f"Non-polynomial denominator: {e}")

    # Step 6: Expand numerator polynomial
    expanded_numer = sympy.expand(numer)
    trace.append(f"Expanded numerator: {expanded_numer}")

    is_identity = expanded_numer == 0
    is_contradiction = expanded_numer.is_number and expanded_numer != 0

    numer_poly: Optional[sympy.Poly] = None
    degree = 0
    coeffs: Dict[int, sympy.Basic] = {}

    if not is_identity and not is_contradiction:
        if X_SYM in expanded_numer.free_symbols:
            try:
                numer_poly = sympy.Poly(expanded_numer, X_SYM)
                degree = numer_poly.degree()
                trace.append(f"Numerator polynomial degree: {degree}")

                if degree > limits.max_polynomial_degree:
                    raise OutOfScopeSyntaxError(
                        f"Equation polynomial degree {degree} exceeds maximum supported degree {limits.max_polynomial_degree}"
                    )

                for deg, coef in enumerate(numer_poly.all_coeffs()[::-1]):
                    coeffs[deg] = coef
                    try:
                        if abs(float(coef)) > limits.max_coefficient_magnitude:
                            raise CoefficientMagnitudeError(
                                f"Coefficient {coef} for x^{deg} exceeds maximum allowed magnitude {limits.max_coefficient_magnitude}"
                            )
                    except (TypeError, ValueError):
                        pass
            except sympy.PolynomialError as e:
                raise OutOfScopeSyntaxError(f"Non-polynomial expression: {e}")
        else:
            # Constant expression
            is_contradiction = True
            degree = 0
    elif is_identity:
        degree = 0
        trace.append("Numerator is identically zero (identity equation on valid domain)")
    elif is_contradiction:
        degree = 0
        trace.append(f"Contradiction: {expanded_numer} = 0 (no solution)")

    return NormalizedEquation(
        raw_input=raw_text or eq_ast.to_math_string(),
        raw_ast=eq_ast,
        domain=domain,
        normalization_trace=trace,
        numerator_sym=numer,
        denominator_sym=denom,
        numerator_poly=numer_poly,
        denominator_poly=denom_poly,
        is_rational=is_rational,
        degree=degree,
        is_identity=is_identity,
        is_contradiction=is_contradiction,
        coefficients=coeffs,
        has_variable_denominator=has_variable_denominator,
    )
