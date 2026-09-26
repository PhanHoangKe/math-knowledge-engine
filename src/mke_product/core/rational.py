"""Immutable, typed, exact rational representation based on Python fractions.Fraction.

Conforms strictly to MKE PRODUCT-01-R2 / PRODUCT-02A-S0 contract:
- Exact rational arithmetic over Q with no floating-point conversions.
- Canonical normalization via Euclidean GCD and strictly positive denominator.
- Deterministic conversions to typed tuples and dictionaries.
- Explicit ZeroDenominatorError and DivisionByZeroError.
"""

from __future__ import annotations
import math
from fractions import Fraction
from typing import Any, Union, Tuple, Dict

from .errors import (
    ZeroDenominatorError,
    DivisionByZeroError,
    InvalidRationalInputError,
)


class Rational:
    """An immutable, exact rational number p/q with p, q in Z and q > 0."""

    __slots__ = ("_numerator", "_denominator", "_hash")

    def __init__(
        self,
        numerator: Union[int, str, Fraction, "Rational"],
        denominator: Union[int, str, None] = None,
    ) -> None:
        # Prevent floating point input directly
        if isinstance(numerator, float) or isinstance(denominator, float):
            raise InvalidRationalInputError(
                f"Floating-point values are forbidden in exact rational representation: "
                f"numerator={numerator!r}, denominator={denominator!r}"
            )

        num: int
        den: int

        if denominator is not None:
            if isinstance(denominator, str):
                try:
                    den = int(denominator)
                except ValueError as err:
                    raise InvalidRationalInputError(f"Invalid denominator string: {denominator!r}") from err
            elif isinstance(denominator, int):
                den = denominator
            else:
                raise InvalidRationalInputError(f"Unsupported denominator type: {type(denominator).__name__}")

            if den == 0:
                raise ZeroDenominatorError("Denominator cannot be zero in rational construction.")

            if isinstance(numerator, str):
                try:
                    num = int(numerator)
                except ValueError as err:
                    raise InvalidRationalInputError(f"Invalid numerator string: {numerator!r}") from err
            elif isinstance(numerator, int):
                num = numerator
            else:
                raise InvalidRationalInputError(f"Unsupported numerator type with explicit denominator: {type(numerator).__name__}")

        else:
            # Single argument construction
            if isinstance(numerator, Rational):
                num = numerator._numerator
                den = numerator._denominator
            elif isinstance(numerator, Fraction):
                num = numerator.numerator
                den = numerator.denominator
            elif isinstance(numerator, int):
                num = numerator
                den = 1
            elif isinstance(numerator, str):
                s = numerator.strip()
                if "/" in s:
                    parts = s.split("/")
                    if len(parts) != 2:
                        raise InvalidRationalInputError(f"Invalid fraction string format: {numerator!r}")
                    try:
                        num = int(parts[0].strip())
                        den = int(parts[1].strip())
                    except ValueError as err:
                        raise InvalidRationalInputError(f"Invalid integer in fraction string: {numerator!r}") from err
                    if den == 0:
                        raise ZeroDenominatorError("Denominator cannot be zero in rational construction.")
                else:
                    try:
                        num = int(s)
                        den = 1
                    except ValueError as err:
                        raise InvalidRationalInputError(f"Invalid integer string: {numerator!r}") from err
            else:
                raise InvalidRationalInputError(f"Unsupported input type for Rational: {type(numerator).__name__}")

        # Canonical normalization:
        # 1. Denominator must be strictly positive
        if den < 0:
            num = -num
            den = -den

        # 2. Reduce by Euclidean GCD
        g = math.gcd(abs(num), den)
        object.__setattr__(self, "_numerator", num // g)
        object.__setattr__(self, "_denominator", den // g)
        object.__setattr__(self, "_hash", None)

    # Immutability guards
    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"Rational instances are immutable; cannot set attribute '{name}'.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"Rational instances are immutable; cannot delete attribute '{name}'.")

    @property
    def numerator(self) -> int:
        """Canonical numerator p in lowest terms."""
        return self._numerator

    @property
    def denominator(self) -> int:
        """Canonical denominator q > 0 in lowest terms."""
        return self._denominator

    @property
    def sign(self) -> int:
        """Sign of the rational number: 1 if positive, -1 if negative, 0 if zero."""
        if self._numerator > 0:
            return 1
        elif self._numerator < 0:
            return -1
        return 0

    @property
    def is_zero(self) -> bool:
        """True if and only if numerator == 0."""
        return self._numerator == 0

    @property
    def is_positive(self) -> bool:
        """True if and only if numerator > 0."""
        return self._numerator > 0

    @property
    def is_negative(self) -> bool:
        """True if and only if numerator < 0."""
        return self._numerator < 0

    @property
    def is_integer(self) -> bool:
        """True if and only if denominator == 1."""
        return self._denominator == 1

    # Arithmetic Operations
    def __add__(self, other: Union[Rational, int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        new_num = self._numerator * other_rat._denominator + other_rat._numerator * self._denominator
        new_den = self._denominator * other_rat._denominator
        return Rational(new_num, new_den)

    def __radd__(self, other: Union[int, Fraction]) -> Rational:
        return self.__add__(other)

    def __sub__(self, other: Union[Rational, int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        new_num = self._numerator * other_rat._denominator - other_rat._numerator * self._denominator
        new_den = self._denominator * other_rat._denominator
        return Rational(new_num, new_den)

    def __rsub__(self, other: Union[int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        return other_rat.__sub__(self)

    def __mul__(self, other: Union[Rational, int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        return Rational(self._numerator * other_rat._numerator, self._denominator * other_rat._denominator)

    def __rmul__(self, other: Union[int, Fraction]) -> Rational:
        return self.__mul__(other)

    def __truediv__(self, other: Union[Rational, int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        if other_rat.is_zero:
            raise DivisionByZeroError("Exact rational division by zero.")
        return Rational(self._numerator * other_rat._denominator, self._denominator * other_rat._numerator)

    def __rtruediv__(self, other: Union[int, Fraction]) -> Rational:
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        return other_rat.__truediv__(self)

    def __neg__(self) -> Rational:
        return Rational(-self._numerator, self._denominator)

    def __pos__(self) -> Rational:
        return self

    def __abs__(self) -> Rational:
        return Rational(abs(self._numerator), self._denominator)

    # Comparison Operations
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, float):
            return False  # Strict rejection of floating comparison tolerance
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return False
        return (self._numerator == other_rat._numerator) and (self._denominator == other_rat._denominator)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, float):
            raise InvalidRationalInputError("Cannot compare exact Rational with float.")
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        return (self._numerator * other_rat._denominator) < (other_rat._numerator * self._denominator)

    def __le__(self, other: Any) -> bool:
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, float):
            raise InvalidRationalInputError("Cannot compare exact Rational with float.")
        other_rat = self._coerce(other)
        if other_rat is NotImplemented:
            return NotImplemented
        return (self._numerator * other_rat._denominator) > (other_rat._numerator * self._denominator)

    def __ge__(self, other: Any) -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __hash__(self) -> int:
        if self._hash is None:
            h = hash((self._numerator, self._denominator))
            object.__setattr__(self, "_hash", h)
        return self._hash

    # Representation and Serialization Helpers
    def to_tuple(self) -> Tuple[int, int]:
        """Deterministic tuple representation (numerator, denominator)."""
        return (self._numerator, self._denominator)

    def to_dict(self) -> Dict[str, int]:
        """Deterministic dictionary representation with exact integer fields."""
        return {"numerator": self._numerator, "denominator": self._denominator}

    def to_fraction(self) -> Fraction:
        """Convert to standard library Fraction."""
        return Fraction(self._numerator, self._denominator)

    def __str__(self) -> str:
        if self._denominator == 1:
            return str(self._numerator)
        return f"{self._numerator}/{self._denominator}"

    def __repr__(self) -> str:
        if self._denominator == 1:
            return f"Rational({self._numerator})"
        return f"Rational({self._numerator}, {self._denominator})"

    @classmethod
    def _coerce(cls, val: Any) -> Union[Rational, Any]:
        if isinstance(val, Rational):
            return val
        if isinstance(val, int):
            return Rational(val, 1)
        if isinstance(val, Fraction):
            return Rational(val.numerator, val.denominator)
        return NotImplemented
