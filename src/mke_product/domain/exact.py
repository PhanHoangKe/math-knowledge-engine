"""MKE MVP V1 — Exact Arithmetic & Quadratic Kernel.

Provides exact rational and real quadratic-surd arithmetic over Q and R.
Zero floating-point arithmetic is permitted as authority for exact algebra.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from mke_product.core.rational import Rational
from mke_product.domain.models import (
    EquationClassificationType,
    QuadraticDiscriminant,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
)


def decompose_integer_squarefree(n: int) -> Tuple[int, int]:
    """Decompose a non-negative integer n into k^2 * d where d is squarefree.

    Args:
        n: Non-negative integer.

    Returns:
        (k, d) where n = k^2 * d and d is squarefree (1 if n is a perfect square).
    """
    if n < 0:
        raise ValueError(f"decompose_integer_squarefree requires non-negative integer, got {n}")
    if n == 0:
        return 0, 0
    if n == 1:
        return 1, 1

    k = 1
    d = 1
    rem = n

    # Extract factor 2
    count_2 = 0
    while rem % 2 == 0:
        count_2 += 1
        rem //= 2
    if count_2 > 0:
        k *= 2 ** (count_2 // 2)
        if count_2 % 2 == 1:
            d *= 2

    # Extract odd prime factors
    p = 3
    while p * p <= rem:
        if rem % p == 0:
            count_p = 0
            while rem % p == 0:
                count_p += 1
                rem //= p
            k *= p ** (count_p // 2)
            if count_p % 2 == 1:
                d *= p
        p += 2

    # If remainder is > 1, it must be prime (hence squarefree)
    if rem > 1:
        d *= rem

    return k, d


def decompose_rational_squarefree(r: Rational) -> Tuple[Rational, int]:
    """Decompose a strictly positive rational number r into s * sqrt(d) where s in Q and d in N is squarefree.

    For r = p/q > 0:
      sqrt(r) = sqrt(p*q) / q.
      Let p*q = k^2 * d with d squarefree.
      Then sqrt(r) = (k/q) * sqrt(d).

    Returns:
        (s, d) where s = Rational(k, q) and d is squarefree integer >= 1.
    """
    if not r.is_positive:
        raise ValueError(f"decompose_rational_squarefree requires strictly positive rational, got {r}")

    p = r.numerator
    q = r.denominator
    product = p * q
    k, d = decompose_integer_squarefree(product)
    s = Rational(k, q)
    return s, d


def compute_quadratic_discriminant(a: Rational, b: Rational, c: Rational) -> QuadraticDiscriminant:
    """Compute exact discriminant Delta = b^2 - 4ac and its squarefree properties."""
    delta = b * b - Rational(4, 1) * a * c
    delta_frac = RationalFraction.from_rational(delta)

    if delta.is_negative:
        return QuadraticDiscriminant(
            value=delta_frac,
            is_positive=False,
            is_zero=False,
            is_negative=True,
            is_rational_square=False,
            square_root_rational=None,
            squarefree_kernel=None,
            extracted_factor=None,
        )
    elif delta.is_zero:
        zero_frac = RationalFraction.from_int(0)
        return QuadraticDiscriminant(
            value=delta_frac,
            is_positive=False,
            is_zero=True,
            is_negative=False,
            is_rational_square=True,
            square_root_rational=zero_frac,
            squarefree_kernel=0,
            extracted_factor=zero_frac,
        )
    else:  # delta > 0
        s, d = decompose_rational_squarefree(delta)
        s_frac = RationalFraction.from_rational(s)
        is_square = (d == 1)
        return QuadraticDiscriminant(
            value=delta_frac,
            is_positive=True,
            is_zero=False,
            is_negative=False,
            is_rational_square=is_square,
            square_root_rational=s_frac if is_square else None,
            squarefree_kernel=d,
            extracted_factor=s_frac,
        )


def classify_univariate_degree2(
    a: Rational, b: Rational, c: Rational, var: str = "x"
) -> Tuple[EquationClassificationType, Optional[Rational]]:
    """Deterministically classify an equation a*x^2 + b*x + c = 0.

    Returns:
        (classification, linear_root_if_applicable)
    """
    if not a.is_zero:
        return EquationClassificationType.QUADRATIC, None
    elif not b.is_zero:
        # a == 0, b != 0: Linear equation b*x + c = 0 => x = -c / b
        root = -c / b
        return EquationClassificationType.LINEAR, root
    elif c.is_zero:
        # a == 0, b == 0, c == 0: 0 = 0 (Identity, all reals)
        return EquationClassificationType.IDENTITY, None
    else:
        # a == 0, b == 0, c != 0: c = 0 with c != 0 (Contradiction)
        return EquationClassificationType.CONTRADICTION, None


def _format_surd_latex(u: Rational, v: Rational, d: int) -> str:
    """Format u + v*sqrt(d) into clean LaTeX."""
    # u is rational base, v is rational factor, d is squarefree radicand
    surd_part: str
    abs_v = abs(v)
    if abs_v == Rational(1, 1):
        surd_part = f"\\sqrt{{{d}}}"
    elif abs_v.denominator == 1:
        surd_part = f"{abs_v.numerator}\\sqrt{{{d}}}"
    else:
        surd_part = f"\\frac{{{abs_v.numerator}\\sqrt{{{d}}}}}{{{abs_v.denominator}}}"

    if u.is_zero:
        if v.is_negative:
            return f"-{surd_part}"
        return surd_part

    u_latex = RationalFraction.from_rational(u).to_latex()
    if v.is_negative:
        return f"{u_latex} - {surd_part}"
    return f"{u_latex} + {surd_part}"


def solve_exact_quadratic(
    a: Rational, b: Rational, c: Rational
) -> Tuple[SolutionOutcome, List[RealRootValue]]:
    """Solve ax^2 + bx + c = 0 over R with exact rational or surd arithmetic.

    Precondition: a != 0.
    """
    if a.is_zero:
        raise ValueError("solve_exact_quadratic requires a != 0")

    disc = compute_quadratic_discriminant(a, b, c)

    if disc.is_negative:
        return SolutionOutcome.NO_REAL_ROOTS, []

    two_a = Rational(2, 1) * a

    if disc.is_zero:
        root_rat = -b / two_a
        root_frac = RationalFraction.from_rational(root_rat)
        root_val = RealRootValue(
            root_type=SolutionRootType.RATIONAL,
            rational_value=root_frac,
            surd_base=None,
            surd_factor=None,
            radicand=None,
            approximate_float=root_rat.numerator / root_rat.denominator,
            latex_str=root_frac.to_latex(),
        )
        return SolutionOutcome.ONE_REPEATED_REAL_ROOT, [root_val]

    # disc.is_positive
    s = disc.extracted_factor.to_rational()
    d = disc.squarefree_kernel

    if disc.is_rational_square:
        # Two distinct rational roots
        r1 = (-b - s) / two_a
        r2 = (-b + s) / two_a
        # Order canonically
        if r2 < r1:
            r1, r2 = r2, r1
        frac1 = RationalFraction.from_rational(r1)
        frac2 = RationalFraction.from_rational(r2)
        val1 = RealRootValue(
            root_type=SolutionRootType.RATIONAL,
            rational_value=frac1,
            approximate_float=r1.numerator / r1.denominator,
            latex_str=frac1.to_latex(),
        )
        val2 = RealRootValue(
            root_type=SolutionRootType.RATIONAL,
            rational_value=frac2,
            approximate_float=r2.numerator / r2.denominator,
            latex_str=frac2.to_latex(),
        )
        return SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, [val1, val2]
    else:
        # Two distinct real quadratic surds
        u = -b / two_a
        v = abs(s / two_a)  # canonical positive magnitude for step
        u_frac = RationalFraction.from_rational(u)
        v_neg_frac = RationalFraction.from_rational(-v)
        v_pos_frac = RationalFraction.from_rational(v)

        approx1 = (u.numerator / u.denominator) - (v.numerator / v.denominator) * math.sqrt(d)
        approx2 = (u.numerator / u.denominator) + (v.numerator / v.denominator) * math.sqrt(d)

        val1 = RealRootValue(
            root_type=SolutionRootType.REAL_SURD,
            surd_base=u_frac,
            surd_factor=v_neg_frac,
            radicand=d,
            approximate_float=approx1,
            latex_str=_format_surd_latex(u, -v, d),
        )
        val2 = RealRootValue(
            root_type=SolutionRootType.REAL_SURD,
            surd_base=u_frac,
            surd_factor=v_pos_frac,
            radicand=d,
            approximate_float=approx2,
            latex_str=_format_surd_latex(u, v, d),
        )
        return SolutionOutcome.TWO_DISTINCT_REAL_ROOTS, [val1, val2]
