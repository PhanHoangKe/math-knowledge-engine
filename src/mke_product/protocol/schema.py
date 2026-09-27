"""Constants, serialization helpers, and schemas for MKE Product protocol."""

from __future__ import annotations
from typing import Optional, Dict, Any, List

from ..core.rational import Rational
from ..parser.errors import Span

SCHEMA_VERSION = "mke.p02a.v1"
OPERATION_SOLVE = "SOLVE"
OPERATION_CHECK_CANDIDATE = "CHECK_CANDIDATE"
SUPPORTED_OPERATIONS = (OPERATION_SOLVE, OPERATION_CHECK_CANDIDATE)

MAX_PAYLOAD_BYTES = 4096
MAX_EQUATION_CHARS = 256


def serialize_rational(val: Optional[Rational]) -> Optional[Dict[str, str]]:
    """Serialize an exact Rational to transport format with decimal strings.

    Guarantee:
    - Never uses JSON floats or approximations.
    - Preserves canonical sign and coprime reduction from Rational.
    - Decimal integer strings work for arbitrarily large integers.
    """
    if val is None:
        return None
    return {
        "numerator": str(val.numerator),
        "denominator": str(val.denominator),
    }


def serialize_span(span: Optional[Span]) -> Optional[List[int]]:
    """Serialize source Span to [start, end] list."""
    if span is None:
        return None
    return [span.start, span.end]
