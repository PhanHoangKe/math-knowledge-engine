"""Deterministic unit test suite for exact rational arithmetic core.

Covers:
- Positive, negative, unreduced fractions, and negative denominators.
- All four arithmetic operations (+, -, *, /) with exact rational and integer operands.
- Zero numerator canonicalization and zero denominator rejection.
- Division by zero exceptions.
- Arbitrary-precision large integers and tiny nonzero rational quantities.
- Immutability enforcement and deterministic normalization.
- Strict rejection of floating-point conversions.
"""

import os
import sys
import unittest
from fractions import Fraction

# Ensure src is on path for unittest discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.core.rational import Rational
from mke_product.core.errors import (
    ZeroDenominatorError,
    DivisionByZeroError,
    InvalidRationalInputError,
)


class TestRationalConstruction(unittest.TestCase):
    """Tests for construction, canonical reduction, and normalization."""

    def test_canonical_reduction(self):
        r1 = Rational(4, 8)
        self.assertEqual(r1.numerator, 1)
        self.assertEqual(r1.denominator, 2)

        r2 = Rational(-6, -9)
        self.assertEqual(r2.numerator, 2)
        self.assertEqual(r2.denominator, 3)

        r3 = Rational(10, -25)
        self.assertEqual(r3.numerator, -2)
        self.assertEqual(r3.denominator, 5)

    def test_negative_denominator_normalization(self):
        r1 = Rational(5, -2)
        self.assertEqual(r1.numerator, -5)
        self.assertEqual(r1.denominator, 2)

        r2 = Rational(-7, -3)
        self.assertEqual(r2.numerator, 7)
        self.assertEqual(r2.denominator, 3)

    def test_zero_numerator(self):
        r = Rational(0, 15)
        self.assertEqual(r.numerator, 0)
        self.assertEqual(r.denominator, 1)
        self.assertTrue(r.is_zero)
        self.assertFalse(r.is_positive)
        self.assertFalse(r.is_negative)
        self.assertEqual(r.sign, 0)

    def test_zero_denominator_rejection(self):
        with self.assertRaises(ZeroDenominatorError):
            Rational(5, 0)

        with self.assertRaises(ZeroDenominatorError):
            Rational(0, 0)

        with self.assertRaises(ZeroDenominatorError):
            Rational("3/0")

    def test_string_parsing(self):
        self.assertEqual(Rational("3/4"), Rational(3, 4))
        self.assertEqual(Rational("-7/5"), Rational(-7, 5))
        self.assertEqual(Rational("6/-8"), Rational(-3, 4))
        self.assertEqual(Rational("42"), Rational(42, 1))

    def test_invalid_types_and_float_rejection(self):
        with self.assertRaises(InvalidRationalInputError):
            Rational(0.5)

        with self.assertRaises(InvalidRationalInputError):
            Rational(1, 2.0)

        with self.assertRaises(InvalidRationalInputError):
            Rational("not_a_number")

        with self.assertRaises(InvalidRationalInputError):
            Rational("1/2/3")


class TestRationalArithmetic(unittest.TestCase):
    """Tests for exact rational arithmetic operations."""

    def test_addition(self):
        r1 = Rational(1, 3)
        r2 = Rational(1, 6)
        res = r1 + r2
        self.assertEqual(res, Rational(1, 2))
        self.assertEqual(res.to_tuple(), (1, 2))

        # With integer
        self.assertEqual(r1 + 2, Rational(7, 3))
        self.assertEqual(2 + r1, Rational(7, 3))

    def test_subtraction(self):
        r1 = Rational(3, 4)
        r2 = Rational(1, 2)
        res = r1 - r2
        self.assertEqual(res, Rational(1, 4))

        # With integer
        self.assertEqual(r1 - 1, Rational(-1, 4))
        self.assertEqual(1 - r1, Rational(1, 4))

    def test_multiplication(self):
        r1 = Rational(-2, 5)
        r2 = Rational(15, 4)
        res = r1 * r2
        self.assertEqual(res, Rational(-3, 2))

        # With integer
        self.assertEqual(r1 * 5, Rational(-2, 1))
        self.assertEqual(5 * r1, Rational(-2, 1))

    def test_division(self):
        r1 = Rational(3, 7)
        r2 = Rational(9, 14)
        res = r1 / r2
        self.assertEqual(res, Rational(2, 3))

        # With integer
        self.assertEqual(r1 / 3, Rational(1, 7))
        self.assertEqual(3 / r1, Rational(7, 1))

    def test_division_by_zero(self):
        r = Rational(3, 4)
        zero = Rational(0, 1)

        with self.assertRaises(DivisionByZeroError):
            _ = r / zero

        with self.assertRaises(DivisionByZeroError):
            _ = r / 0

        with self.assertRaises(DivisionByZeroError):
            _ = 5 / zero

    def test_unary_operations(self):
        r = Rational(5, 7)
        self.assertEqual(-r, Rational(-5, 7))
        self.assertEqual(+r, Rational(5, 7))
        self.assertEqual(abs(-r), Rational(5, 7))


class TestRationalComparisonsAndEquality(unittest.TestCase):
    """Tests for exact equality, signs, and order relations."""

    def test_exact_equality(self):
        self.assertEqual(Rational(1, 2), Rational(2, 4))
        self.assertEqual(Rational(-3, 5), Rational(3, -5))
        self.assertNotEqual(Rational(1, 2), Rational(1, 3))

        # Float equality is strictly False (no tolerance equality)
        self.assertFalse(Rational(1, 2) == 0.5)

    def test_ordering(self):
        self.assertTrue(Rational(1, 3) < Rational(1, 2))
        self.assertTrue(Rational(-1, 2) < Rational(-1, 3))
        self.assertTrue(Rational(2, 3) > Rational(1, 2))
        self.assertTrue(Rational(3, 4) >= Rational(6, 8))
        self.assertTrue(Rational(3, 4) <= Rational(6, 8))

        # Float comparison raises error
        with self.assertRaises(InvalidRationalInputError):
            _ = Rational(1, 2) < 0.5

    def test_sign_and_properties(self):
        pos = Rational(3, 4)
        neg = Rational(-3, 4)
        zero = Rational(0, 1)

        self.assertEqual(pos.sign, 1)
        self.assertTrue(pos.is_positive)
        self.assertFalse(pos.is_negative)

        self.assertEqual(neg.sign, -1)
        self.assertFalse(neg.is_positive)
        self.assertTrue(neg.is_negative)

        self.assertEqual(zero.sign, 0)
        self.assertTrue(zero.is_zero)

        self.assertTrue(Rational(4, 1).is_integer)
        self.assertFalse(Rational(4, 3).is_integer)


class TestRationalBoundaryAndExtremeCases(unittest.TestCase):
    """Tests for large integers and tiny rational quantities."""

    def test_large_exact_integers(self):
        # 100-digit integers
        p = 10**100
        q = 10**99
        r = Rational(p, q)
        self.assertEqual(r, Rational(10, 1))
        self.assertEqual(r.numerator, 10)
        self.assertEqual(r.denominator, 1)

        # Large exact arithmetic
        a = Rational(10**50 + 1, 10**50)
        b = Rational(10**50 - 1, 10**50)
        diff = a - b
        self.assertEqual(diff, Rational(2, 10**50))
        self.assertEqual(diff, Rational(1, 5 * 10**49))

    def test_tiny_nonzero_quantities(self):
        tiny = Rational(1, 10**100)
        self.assertFalse(tiny.is_zero)
        self.assertTrue(tiny.is_positive)
        self.assertTrue(tiny > 0)
        self.assertNotEqual(tiny, Rational(0, 1))

        # Precision preservation
        self.assertEqual(tiny + tiny, Rational(2, 10**100))
        self.assertEqual(tiny + tiny, Rational(1, 5 * 10**99))

    def test_immutability(self):
        r = Rational(2, 3)
        with self.assertRaises(AttributeError):
            r.numerator = 5
        with self.assertRaises(AttributeError):
            r.denominator = 5
        with self.assertRaises(AttributeError):
            del r.numerator

    def test_hashable_and_set_dict_membership(self):
        r1 = Rational(1, 2)
        r2 = Rational(2, 4)
        r3 = Rational(3, 4)

        s = {r1, r2, r3}
        self.assertEqual(len(s), 2)
        self.assertIn(Rational(1, 2), s)

        d = {r1: "half", r3: "three-quarters"}
        self.assertEqual(d[r2], "half")

    def test_deterministic_representations(self):
        r = Rational(7, 11)
        self.assertEqual(r.to_tuple(), (7, 11))
        self.assertEqual(r.to_dict(), {"numerator": 7, "denominator": 11})
        self.assertEqual(str(r), "7/11")
        self.assertEqual(repr(r), "Rational(7, 11)")

        r_int = Rational(9, 1)
        self.assertEqual(str(r_int), "9")
        self.assertEqual(repr(r_int), "Rational(9)")


class TestRegressionS0R1(unittest.TestCase):
    """Regression test suite for PRODUCT-02A-S0-R1 targeted remediation.

    Covers:
    - Defect 1: Equality and hash consistency across Rational, int, and Fraction.
    - Defect 1: Mixed-type set membership, set cardinality, and dictionary key lookup.
    - Defect 1: Equality and hash matching between canonically equivalent Rational instances.
    - Defect 2: Boolean semantics (__bool__) for zero, positive, and negative rationals.
    """

    def test_hash_consistency_with_int_and_fraction(self):
        # Rational(2), integer 2, Fraction(2, 1)
        r2 = Rational(2)
        i2 = 2
        f2 = Fraction(2, 1)

        self.assertEqual(r2, i2)
        self.assertEqual(r2, f2)
        self.assertEqual(i2, f2)

        self.assertEqual(hash(r2), hash(i2))
        self.assertEqual(hash(r2), hash(f2))

        # Rational(1, 2), Fraction(1, 2)
        r_half = Rational(1, 2)
        f_half = Fraction(1, 2)

        self.assertEqual(r_half, f_half)
        self.assertEqual(hash(r_half), hash(f_half))

        # Canonical equivalence
        r_unreduced = Rational(4, 8)
        self.assertEqual(r_unreduced, r_half)
        self.assertEqual(hash(r_unreduced), hash(r_half))

        # Negative fractions
        r_neg = Rational(-3, 5)
        f_neg = Fraction(-3, 5)
        self.assertEqual(r_neg, f_neg)
        self.assertEqual(hash(r_neg), hash(f_neg))

    def test_mixed_type_set_membership_and_cardinality(self):
        # Cardinality 1 for equivalent values across types
        s1 = {Rational(2), 2, Fraction(2, 1)}
        self.assertEqual(len(s1), 1)
        self.assertIn(Rational(2), s1)
        self.assertIn(2, s1)
        self.assertIn(Fraction(2, 1), s1)

        s2 = {Rational(1, 2), Fraction(1, 2), Rational(2, 4)}
        self.assertEqual(len(s2), 1)
        self.assertIn(Rational(1, 2), s2)
        self.assertIn(Fraction(1, 2), s2)
        self.assertIn(Rational(2, 4), s2)

    def test_mixed_type_dict_lookup(self):
        d = {
            Rational(2): "integer-two",
            Rational(1, 2): "fraction-half",
        }

        # Lookup with int and Fraction
        self.assertEqual(d[2], "integer-two")
        self.assertEqual(d[Fraction(2, 1)], "integer-two")
        self.assertEqual(d[Fraction(1, 2)], "fraction-half")
        self.assertEqual(d[Rational(2, 4)], "fraction-half")

    def test_boolean_semantics(self):
        # Zero cases must evaluate to False
        self.assertFalse(bool(Rational(0)))
        self.assertFalse(bool(Rational(0, 1)))
        self.assertFalse(bool(Rational(0, 42)))
        self.assertFalse(bool(Rational("0/5")))

        # Positive cases must evaluate to True
        self.assertTrue(bool(Rational(1, 2)))
        self.assertTrue(bool(Rational(42)))
        self.assertTrue(bool(Rational(1, 10**100)))

        # Negative cases must evaluate to True
        self.assertTrue(bool(Rational(-1, 2)))
        self.assertTrue(bool(Rational(-5)))
        self.assertTrue(bool(Rational(-1, 10**100)))

        # Direct conditional statement behavior
        zero_branch = False
        if not Rational(0):
            zero_branch = True
        self.assertTrue(zero_branch)

        pos_branch = False
        if Rational(3, 4):
            pos_branch = True
        self.assertTrue(pos_branch)

        neg_branch = False
        if Rational(-7, 8):
            neg_branch = True
        self.assertTrue(neg_branch)


if __name__ == "__main__":
    unittest.main()
