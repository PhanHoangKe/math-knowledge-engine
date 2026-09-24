"""Pytest configuration and common fixtures."""

import pytest
from mke.parsing.limits import ParserLimits
from mke.verification.engine import VerificationEngine


@pytest.fixture
def default_limits() -> ParserLimits:
    return ParserLimits()


@pytest.fixture
def verification_engine() -> VerificationEngine:
    return VerificationEngine()
