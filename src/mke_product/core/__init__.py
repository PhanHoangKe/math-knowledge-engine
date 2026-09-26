"""Core exact mathematical primitives for MKE Product."""

from .rational import Rational
from .errors import (
    MKEProductError,
    RationalError,
    ZeroDenominatorError,
    DivisionByZeroError,
    InvalidRationalInputError,
)

__all__ = [
    "Rational",
    "MKEProductError",
    "RationalError",
    "ZeroDenominatorError",
    "DivisionByZeroError",
    "InvalidRationalInputError",
]
