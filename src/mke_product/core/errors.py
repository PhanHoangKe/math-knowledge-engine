"""Core exceptions for the MKE Product math engine."""

class MKEProductError(Exception):
    """Base exception for all MKE Product errors."""
    pass


class RationalError(MKEProductError):
    """Base exception for exact rational arithmetic operations."""
    pass


class ZeroDenominatorError(RationalError, ValueError):
    """Raised when constructing a rational number with a denominator of zero."""
    pass


class DivisionByZeroError(RationalError, ZeroDivisionError):
    """Raised when an exact rational division by zero is attempted."""
    pass


class InvalidRationalInputError(RationalError, TypeError, ValueError):
    """Raised when an invalid or non-exact type (e.g., float) is passed to Rational."""
    pass
