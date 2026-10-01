"""Unit, integration, protocol, adversarial, and live Windows AppContainer tests for P1C-04-B2 quadratic surd solver and dispatcher.

Milestone: PRODUCT-03C-P1C-04-B2-R1
Author: Antigravity (Implementation Engineer)
Auditor: ChatGPT
"""

import json
import math
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
import pytest
from pydantic import ValidationError

from mke_product.ai.ir import PublicValidationDiagnostic
from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation
from mke_product.protocol.dispatcher import dispatch_request
from mke_product.protocol.errors import (
    ProtocolInputLimitError,
    ProtocolMissingFieldError,
    ProtocolUnexpectedFieldError,
    ProtocolUnknownOperationError,
    ProtocolUnsupportedVersionError,
)
from mke_product.protocol.schema import (
    OPERATION_CHECK_CANDIDATE,
    OPERATION_SOLVE,
    OPERATION_SOLVE_QUADRATIC,
    OPERATION_SOLVE_QUADRATIC_SURD,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
)
from mke_product.protocol.validator import validate_request_dict
from mke_product.solver.quadratic_surd import (
    NonQuadraticSurdExpressionError,
    extract_quadratic_coefficients,
    reduce_equation_quadratic_surd,
    solve_quadratic_surd_equation,
)
from mke_product.cas.bridge import (
    ControlledDispatchBridge,
    ControlledDispatchResult,
    ExecutionStatus,
    HostQuadraticSurdResourceLimitError,
    IntakeStatus,
    QuadraticControlledDispatchResult,
    QuadraticSurdControlledDispatchResult,
    QuadraticSurdRoot,
    RationalRoot,
    SurdRationalComponent,
    VerificationStatus,
    _host_normalize_discriminant_squarefree,
)


# ============================================================================
# 1. Protocol Version and Operation Matrix (v3 and cross-version)
# ============================================================================

class TestProtocolVersionOperationMatrixV3:
    """Validate strict schema version and operation matrix enforcement for v3."""

    def test_v3_solve_quadratic_surd_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        }
        val = validate_request_dict(req)
        assert val["schema_version"] == SCHEMA_VERSION_V3
        assert val["operation"] == OPERATION_SOLVE_QUADRATIC_SURD

    def test_v3_solve_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v3'" in str(exc_info.value)

    def test_v3_solve_quadratic_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v3'" in str(exc_info.value)

    def test_v3_check_candidate_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 2 = 0",
            "candidate": "2",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v3'" in str(exc_info.value)

    def test_v1_solve_quadratic_surd_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v1'" in str(exc_info.value)

    def test_v2_solve_quadratic_surd_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v2'" in str(exc_info.value)

    def test_v3_extra_field_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
            "extra_field": "disallowed",
        }
        with pytest.raises(ProtocolUnexpectedFieldError):
            validate_request_dict(req)

    def test_v3_missing_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
        }
        with pytest.raises(ProtocolMissingFieldError):
            validate_request_dict(req)

    def test_v3_non_ascii_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 – 2 = 0",  # en-dash
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)

    def test_v3_oversized_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 + " + "1 + " * 100 + "0 = 0",
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)


# ============================================================================
# 2. Worker Quadratic Surd Solver Kernel Tests
# ============================================================================

class TestWorkerQuadraticSurdSolverKernel:
    """Validate mathematical correctness and containment of pure-Python surd solver."""

    def test_solve_surd_x2_minus_2(self):
        eq = parse_equation("x^2 - 2 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.radicand == 2
        assert res.discriminant == Rational(8)
        assert len(res.roots) == 2
        r1, r2 = res.roots
        assert r1.rational_part == Rational(0)
        assert r1.sqrt_coefficient == Rational(-1)
        assert r1.radicand == 2
        assert r2.rational_part == Rational(0)
        assert r2.sqrt_coefficient == Rational(1)
        assert r2.radicand == 2

    def test_solve_surd_x2_minus_8(self):
        # x^2 - 8 = 0 -> roots +- 2*sqrt(2), Delta = 32
        eq = parse_equation("x^2 - 8 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.discriminant == Rational(32)
        assert res.roots[0].rational_part == Rational(0)
        assert res.roots[0].sqrt_coefficient == Rational(-2)
        assert res.roots[0].radicand == 2
        assert res.roots[1].rational_part == Rational(0)
        assert res.roots[1].sqrt_coefficient == Rational(2)
        assert res.roots[1].radicand == 2

    def test_solve_surd_x2_minus_18(self):
        # x^2 - 18 = 0 -> roots +- 3*sqrt(2), Delta = 72
        eq = parse_equation("x^2 - 18 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.roots[0].sqrt_coefficient == Rational(-3)
        assert res.roots[1].sqrt_coefficient == Rational(3)

    def test_solve_surd_2x2_minus_1(self):
        # 2*x^2 - 1 = 0 -> roots +- sqrt(2)/2, Delta = 8
        eq = parse_equation("2*x^2 - 1 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.roots[0].sqrt_coefficient == Rational(-1, 2)
        assert res.roots[1].sqrt_coefficient == Rational(1, 2)

    def test_solve_surd_x2_plus_x_minus_1(self):
        # x^2 + x - 1 = 0 -> roots (-1 +- sqrt(5))/2, Delta = 5
        eq = parse_equation("x^2 + x - 1 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 5
        assert res.discriminant == Rational(5)
        assert res.roots[0].rational_part == Rational(-1, 2)
        assert res.roots[0].sqrt_coefficient == Rational(-1, 2)
        assert res.roots[0].radicand == 5
        assert res.roots[1].rational_part == Rational(-1, 2)
        assert res.roots[1].sqrt_coefficient == Rational(1, 2)
        assert res.roots[1].radicand == 5

    def test_solve_surd_3x2_plus_6x_plus_1(self):
        # 3*x^2 + 6*x + 1 = 0 -> Delta = 36 - 12 = 24 = 4*6 -> k=2, d=6
        # roots: (-6 +- 2*sqrt(6))/6 = -1 +- (1/3)*sqrt(6)
        eq = parse_equation("3*x^2 + 6*x + 1 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 6
        assert res.discriminant == Rational(24)
        assert res.roots[0].rational_part == Rational(-1)
        assert res.roots[0].sqrt_coefficient == Rational(-1, 3)
        assert res.roots[0].radicand == 6
        assert res.roots[1].rational_part == Rational(-1)
        assert res.roots[1].sqrt_coefficient == Rational(1, 3)
        assert res.roots[1].radicand == 6

    def test_solve_surd_shifted_square(self):
        # (x - 1)^2 = 2 -> x^2 - 2x - 1 = 0 -> Delta = 4 - 4(1)(-1) = 8 = 4*2
        # roots: (2 +- 2*sqrt(2))/2 = 1 +- sqrt(2)
        eq = parse_equation("(x - 1)^2 = 2")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.roots[0].rational_part == Rational(1)
        assert res.roots[0].sqrt_coefficient == Rational(-1)
        assert res.roots[1].rational_part == Rational(1)
        assert res.roots[1].sqrt_coefficient == Rational(1)

    def test_solve_surd_x2_minus_50(self):
        # x^2 - 50 = 0 -> roots +- 5*sqrt(2), Delta = 200 = 100*2 -> k=10, d=2
        eq = parse_equation("x^2 - 50 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.roots[0].sqrt_coefficient == Rational(-5)
        assert res.roots[1].sqrt_coefficient == Rational(5)

    def test_solve_surd_fractional_constant(self):
        # x^2 - 1/2 = 0 -> Delta = 0 - 4(1)(-1/2) = 2 -> k=1, d=2
        eq = parse_equation("x^2 - 1/2 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "SUCCESS"
        assert res.radicand == 2
        assert res.roots[0].sqrt_coefficient == Rational(-1, 2)
        assert res.roots[1].sqrt_coefficient == Rational(1, 2)

    def test_rational_roots_fail_closed_out_of_scope(self):
        # x^2 - 4 = 0 has rational roots -> must fail closed on v3 surd solver
        eq = parse_equation("x^2 - 4 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_RATIONAL_QUADRATIC_IN_SURD_SOLVER"

    def test_unique_repeated_root_fail_closed(self):
        # (x - 1)^2 = 0 has rational root 1 -> must fail closed on v3 surd solver
        eq = parse_equation("(x - 1)^2 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_OUT_OF_SCOPE"

    def test_negative_discriminant_fail_closed(self):
        # x^2 + 1 = 0 has no real roots
        eq = parse_equation("x^2 + 1 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_OUT_OF_SCOPE"

    def test_degenerate_affine_fail_closed(self):
        eq = parse_equation("2*x + 4 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_DEGENERATE_AFFINE_EQUATION"

    def test_degree_3_fail_closed(self):
        eq = parse_equation("x*x*x = 1")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "OUT_OF_SCOPE"

    def test_division_by_zero_domain_error(self):
        eq = parse_equation("x^2 + 1/0 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_DIV_ZERO"

    def test_zero_power_zero_domain_error(self):
        eq = parse_equation("x^2 + 0^0 = 0")
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_ZERO_POWER_ZERO"


# ============================================================================
# 3. Dispatcher Integration Tests (v3 SOLVE_QUADRATIC_SURD)
# ============================================================================

class TestDispatcherV3Integration:
    """Validate dispatcher execution for v3 SOLVE_QUADRATIC_SURD."""

    def test_v3_dispatch_success_surd(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V3
        assert res["operation"] == OPERATION_SOLVE_QUADRATIC_SURD
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "TWO_DISTINCT_REAL_ROOTS"
        assert res["radicand"] == "2"
        assert res["discriminant"] == {"numerator": "8", "denominator": "1"}
        assert len(res["roots"]) == 2
        assert res["roots"][0] == {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        assert res["roots"][1] == {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        assert res["is_provisional_evidence"] is True

    def test_v3_dispatch_rational_out_of_scope(self):
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 4 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V3
        assert res["outcome"] == "OUT_OF_SCOPE"
        assert res["status"] == "ERR_RATIONAL_QUADRATIC_IN_SURD_SOLVER"


# ============================================================================
# 4. Host Normalization and Squarefree Certification Tests
# ============================================================================

class TestHostSurdNormalization:
    """Test independent host AST quadratic normalization and squarefree certification."""

    def test_host_normalize_integers(self):
        k, d = _host_normalize_discriminant_squarefree(Rational(8))
        assert k == Rational(2)
        assert d == 2

        k, d = _host_normalize_discriminant_squarefree(Rational(32))
        assert k == Rational(4)
        assert d == 2

        k, d = _host_normalize_discriminant_squarefree(Rational(5))
        assert k == Rational(1)
        assert d == 5

        k, d = _host_normalize_discriminant_squarefree(Rational(24))
        assert k == Rational(2)
        assert d == 6

        k, d = _host_normalize_discriminant_squarefree(Rational(200))
        assert k == Rational(10)
        assert d == 2

    def test_host_normalize_fractions(self):
        k, d = _host_normalize_discriminant_squarefree(Rational(8, 9))
        assert k == Rational(2, 3)
        assert d == 2

        k, d = _host_normalize_discriminant_squarefree(Rational(2, 1))
        assert k == Rational(1)
        assert d == 2

    def test_host_normalize_perfect_square_returns_d1(self):
        s, d = _host_normalize_discriminant_squarefree(Rational(4))
        assert s == Rational(2)
        assert d == 1

        with pytest.raises(HostQuadraticSurdResourceLimitError):
            _host_normalize_discriminant_squarefree(Rational(0))
        with pytest.raises(HostQuadraticSurdResourceLimitError):
            _host_normalize_discriminant_squarefree(Rational(-4))


# ============================================================================
# 5. Normalization Attack Matrix & Resource Limits (Requirement 7 & 8)
# ============================================================================

class TestNormalizationBoundaryAndResourceLimits:
    """Validate 65537^2 certification boundary, 512-bit limit, and remainder certification."""

    def test_host_normalization_2_65537_sq_fails_certification(self):
        p = 65537
        delta_val = 2 * (p * p)
        with pytest.raises(HostQuadraticSurdResourceLimitError) as exc_info:
            _host_normalize_discriminant_squarefree(Rational(delta_val))
        assert "exceeds 32-bit certification bound" in str(exc_info.value)

    def test_host_normalization_3_65537_sq_fails_certification(self):
        p = 65537
        delta_val = 3 * (p * p)
        with pytest.raises(HostQuadraticSurdResourceLimitError) as exc_info:
            _host_normalize_discriminant_squarefree(Rational(delta_val))
        assert "exceeds 32-bit certification bound" in str(exc_info.value)

    def test_host_normalization_5_65537_sq_fails_certification(self):
        p = 65537
        delta_val = 5 * (p * p)
        with pytest.raises(HostQuadraticSurdResourceLimitError) as exc_info:
            _host_normalize_discriminant_squarefree(Rational(delta_val))
        assert "exceeds 32-bit certification bound" in str(exc_info.value)

    def test_worker_normalization_2_65537_sq_fails_certification(self):
        p = 65537
        c_val = p * p
        eq = parse_equation(f"2*x^2 - {c_val} = 0")  # Delta = 8 * 65537^2, R = 2 * 65537^2 >= 2^32
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "RESOURCE_EXHAUSTED"
        assert res.error_code == "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT"

    def test_worker_normalization_3_65537_sq_fails_certification(self):
        p = 65537
        c_val = p * p
        eq = parse_equation(f"4*x^2 + 1 = {4*c_val*3 + 1}")  # Delta = 0 - 4(4)(-3*p^2) = 48*p^2
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "RESOURCE_EXHAUSTED"
        assert res.error_code == "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT"

    def test_worker_normalization_5_65537_sq_fails_certification(self):
        p = 65537
        c_val = p * p
        eq = parse_equation(f"x^2 - {5 * c_val} = 0")  # Delta = 20 * 65537^2, R = 5 * 65537^2 >= 2^32
        res = solve_quadratic_surd_equation(eq)
        assert res.status == "RESOURCE_EXHAUSTED"
        assert res.error_code == "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT"

    def test_normalization_2_to_100_squared_times_2_succeeds(self):
        # M = (2^100)^2 * 2 = 2^201 (202 bits <= 512 bits)
        big_k = 1 << 100
        delta_val = (big_k * big_k) * 2
        s, d = _host_normalize_discriminant_squarefree(Rational(delta_val))
        assert s == Rational(big_k)
        assert d == 2

    def test_host_normalization_512_bit_working_product_boundary(self):
        # Discriminant numerator p and denominator q are each bounded by 256 bits
        # Product M = p * q can be up to 512 bits
        p_256 = 1 << 255  # 256 bits: 2^255 = (2^127)^2 * 2
        s, d = _host_normalize_discriminant_squarefree(Rational(p_256, 1))
        assert s == Rational(1 << 127)
        assert d == 2

        # 257-bit numerator rejected
        p_257 = 1 << 256
        with pytest.raises(HostQuadraticSurdResourceLimitError):
            _host_normalize_discriminant_squarefree(Rational(p_257, 1))

        # 257-bit denominator rejected
        q_257 = 1 << 256
        with pytest.raises(HostQuadraticSurdResourceLimitError):
            _host_normalize_discriminant_squarefree(Rational(1, q_257))

    def test_near_boundary_32_bit_remainder_certification(self):
        # Certified near-boundary squarefree prime R = 4294967291 < 2^32 (2^32 = 4294967296)
        prime_near_32 = 4294967291
        s, d = _host_normalize_discriminant_squarefree(Rational(prime_near_32))
        assert s == Rational(1)
        assert d == prime_near_32


# ============================================================================
# 6. Direct Public Model Strictness Tests (Requirement 6)
# ============================================================================

class TestPublicSurdModelsStrictContract:
    """Validate strict Pydantic validation on public B2 types."""

    def test_surd_rational_valid_cases(self):
        r0 = SurdRationalComponent(numerator=0, denominator=1)
        assert r0.numerator == 0 and r0.denominator == 1

        r1 = SurdRationalComponent(numerator=-1, denominator=2)
        assert r1.numerator == -1 and r1.denominator == 2

        r2 = SurdRationalComponent(numerator=1, denominator=3)
        assert r2.numerator == 1 and r2.denominator == 3

        huge = (1 << 256) - 1
        r_huge = SurdRationalComponent(numerator=-huge, denominator=1)
        assert r_huge.numerator == -huge

    def test_surd_rational_rejects_unreduced(self):
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=2, denominator=4)
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=3, denominator=6)
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=-10, denominator=15)

    def test_surd_rational_rejects_noncanonical_zero(self):
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=0, denominator=2)
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=0, denominator=5)

    def test_surd_rational_rejects_257_bit(self):
        huge_257 = 1 << 256
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=huge_257, denominator=1)
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=1, denominator=huge_257)

    def test_surd_rational_rejects_zero_or_negative_denominator(self):
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=1, denominator=0)
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=1, denominator=-2)

    def test_surd_rational_rejects_bool_and_float(self):
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=True, denominator=1)  # bool rejected
        with pytest.raises(ValidationError):
            SurdRationalComponent(numerator=1.5, denominator=1)  # float rejected

    def test_quadratic_surd_root_valid(self):
        root = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        assert root.radicand == 2
        assert root.sqrt_coefficient.numerator == 1

    def test_quadratic_surd_root_rejects_zero_sqrt_coefficient(self):
        with pytest.raises(ValidationError):
            QuadraticSurdRoot(
                rational_part=SurdRationalComponent(numerator=1, denominator=1),
                sqrt_coefficient=SurdRationalComponent(numerator=0, denominator=1),
                radicand=2,
            )

    def test_quadratic_surd_root_rejects_invalid_radicands(self):
        rp = SurdRationalComponent(numerator=0, denominator=1)
        sc = SurdRationalComponent(numerator=1, denominator=1)

        with pytest.raises(ValidationError):
            QuadraticSurdRoot(rational_part=rp, sqrt_coefficient=sc, radicand=0)
        with pytest.raises(ValidationError):
            QuadraticSurdRoot(rational_part=rp, sqrt_coefficient=sc, radicand=1)
        with pytest.raises(ValidationError):
            QuadraticSurdRoot(rational_part=rp, sqrt_coefficient=sc, radicand=1 << 32)
        with pytest.raises(ValidationError):
            QuadraticSurdRoot(rational_part=rp, sqrt_coefficient=sc, radicand=-2)

    def test_quadratic_surd_dispatch_result_valid(self):
        diag = PublicValidationDiagnostic(
            is_valid=True,
            is_cas_ready=True,
            status="VALID",
            target_operation="SOLVE_QUADRATIC_SURD",
            issues=[],
            uncertainties=[],
        )
        r_minus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=-1, denominator=1),
            radicand=2,
        )
        r_plus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        res = QuadraticSurdControlledDispatchResult(
            intake_status=IntakeStatus.VALIDATED,
            intake_diagnostic=diag,
            execution_status=ExecutionStatus.SUCCESS,
            verification_status=VerificationStatus.VERIFIED_COMPLETE,
            is_verified=True,
            solution_type="TWO_DISTINCT_REAL_ROOTS",
            verified_surd_roots=[r_minus, r_plus],
            discriminant=RationalRoot(numerator=8, denominator=1),
            radicand=2,
            completeness_proven=True,
        )
        assert res.representation == "QUADRATIC_SURD"
        assert len(res.verified_surd_roots) == 2
        assert res.radicand == 2

    def test_quadratic_surd_dispatch_result_rejects_invalid_root_counts(self):
        diag = PublicValidationDiagnostic(
            is_valid=True,
            is_cas_ready=True,
            status="VALID",
            target_operation="SOLVE_QUADRATIC_SURD",
            issues=[],
            uncertainties=[],
        )
        r_minus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=-1, denominator=1),
            radicand=2,
        )
        r_plus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        # 1 root
        with pytest.raises(ValidationError):
            QuadraticSurdControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diag,
                execution_status=ExecutionStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED_COMPLETE,
                is_verified=True,
                verified_surd_roots=[r_minus],
                discriminant=RationalRoot(numerator=8, denominator=1),
                radicand=2,
            )
        # 3 roots
        with pytest.raises(ValidationError):
            QuadraticSurdControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diag,
                execution_status=ExecutionStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED_COMPLETE,
                is_verified=True,
                verified_surd_roots=[r_minus, r_plus, r_plus],
                discriminant=RationalRoot(numerator=8, denominator=1),
                radicand=2,
            )

    def test_quadratic_surd_dispatch_result_rejects_mismatched_roots(self):
        diag = PublicValidationDiagnostic(
            is_valid=True,
            is_cas_ready=True,
            status="VALID",
            target_operation="SOLVE_QUADRATIC_SURD",
            issues=[],
            uncertainties=[],
        )
        # Different rational parts
        r1 = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=-1, denominator=1),
            radicand=2,
        )
        r2 = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=1, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        with pytest.raises(ValidationError):
            QuadraticSurdControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diag,
                execution_status=ExecutionStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED_COMPLETE,
                is_verified=True,
                verified_surd_roots=[r1, r2],
                discriminant=RationalRoot(numerator=8, denominator=1),
                radicand=2,
            )

        # Reversed order (positive first)
        r_pos = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        r_neg = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=-1, denominator=1),
            radicand=2,
        )
        with pytest.raises(ValidationError):
            QuadraticSurdControlledDispatchResult(
                intake_status=IntakeStatus.VALIDATED,
                intake_diagnostic=diag,
                execution_status=ExecutionStatus.SUCCESS,
                verification_status=VerificationStatus.VERIFIED_COMPLETE,
                is_verified=True,
                verified_surd_roots=[r_pos, r_neg],
                discriminant=RationalRoot(numerator=8, denominator=1),
                radicand=2,
            )

    def test_canonical_serialization_no_float(self):
        diag = PublicValidationDiagnostic(
            is_valid=True,
            is_cas_ready=True,
            status="VALID",
            target_operation="SOLVE_QUADRATIC_SURD",
            issues=[],
            uncertainties=[],
        )
        r_minus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=-1, denominator=1),
            radicand=2,
        )
        r_plus = QuadraticSurdRoot(
            rational_part=SurdRationalComponent(numerator=0, denominator=1),
            sqrt_coefficient=SurdRationalComponent(numerator=1, denominator=1),
            radicand=2,
        )
        res = QuadraticSurdControlledDispatchResult(
            intake_status=IntakeStatus.VALIDATED,
            intake_diagnostic=diag,
            execution_status=ExecutionStatus.SUCCESS,
            verification_status=VerificationStatus.VERIFIED_COMPLETE,
            is_verified=True,
            solution_type="TWO_DISTINCT_REAL_ROOTS",
            verified_surd_roots=[r_minus, r_plus],
            discriminant=RationalRoot(numerator=8, denominator=1),
            radicand=2,
            completeness_proven=True,
        )
        json_str = res.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["representation"] == "QUADRATIC_SURD"
        assert parsed["radicand"] == 2
        assert parsed["verified_surd_roots"][0]["sqrt_coefficient"]["numerator"] == -1
        assert parsed["verified_surd_roots"][1]["sqrt_coefficient"]["numerator"] == 1
        # Confirm no float types in entire tree
        def check_no_floats(obj):
            if isinstance(obj, float):
                raise AssertionError(f"Found float in serialized output: {obj}")
            if isinstance(obj, dict):
                for v in obj.values():
                    check_no_floats(v)
            elif isinstance(obj, list):
                for item in obj:
                    check_no_floats(item)
        check_no_floats(parsed)


# ============================================================================
# 7. ControlledDispatchBridge B2 End-to-End Tests with Mock Controller
# ============================================================================

class MockBridgeWorkerController:
    """Mock worker controller for controlled dispatch bridge testing."""

    def __init__(
        self,
        solve_res: Optional[Dict[str, Any]] = None,
        check_res: Optional[Dict[str, Any]] = None,
        check_res_list: Optional[List[Dict[str, Any]]] = None,
        solve_delay_sec: float = 0.0,
    ):
        self.solve_res = solve_res
        self.check_res = check_res
        self.check_res_list = list(check_res_list) if check_res_list else []
        self.solve_delay_sec = solve_delay_sec
        self.call_history: List[Tuple[Dict[str, Any], Optional[float]]] = []

    def execute_request(self, req: Dict[str, Any], timeout_sec: Optional[float] = None) -> Dict[str, Any]:
        self.call_history.append((req, timeout_sec))
        op = req.get("operation")
        schema = req.get("schema_version")

        if self.solve_delay_sec > 0:
            import time
            time.sleep(self.solve_delay_sec)

        if op == OPERATION_SOLVE:
            if self.solve_res is not None:
                return self.solve_res
            return {
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_SOLVE,
                "outcome": "SUCCESS",
                "status": "UNIQUE_ROOT",
                "classification": "UNIQUE_ROOT",
                "root": {"numerator": "-2", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": False,
            }
        elif op == OPERATION_SOLVE_QUADRATIC:
            if self.solve_res is not None:
                return self.solve_res
            return {
                "schema_version": SCHEMA_VERSION_V2,
                "operation": OPERATION_SOLVE_QUADRATIC,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {"numerator": "-2", "denominator": "1"},
                    {"numerator": "2", "denominator": "1"},
                ],
                "discriminant": {"numerator": "16", "denominator": "1"},
                "definedness": True,
                "error": None,
                "is_provisional_evidence": False,
            }
        elif op == OPERATION_SOLVE_QUADRATIC_SURD:
            if self.solve_res is not None:
                return self.solve_res
            # Standard default surd response for x^2 - 2 = 0
            return {
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        elif op == OPERATION_CHECK_CANDIDATE:
            if self.check_res_list:
                return self.check_res_list.pop(0)
            if self.check_res is not None:
                return self.check_res
            cand = req.get("candidate")
            if "/" in cand:
                n, d = cand.split("/")
            else:
                n, d = cand, "1"
            return {
                "schema_version": SCHEMA_VERSION_V1,
                "operation": OPERATION_CHECK_CANDIDATE,
                "outcome": "SUCCESS",
                "status": "VALID",
                "candidate": {"numerator": n, "denominator": d},
                "exact_equality": True,
                "residual": {"numerator": "0", "denominator": "1"},
                "left_value": {"numerator": "0", "denominator": "1"},
                "right_value": {"numerator": "0", "denominator": "1"},
                "definedness": True,
                "is_provisional_evidence": True,
            }
        return {
            "schema_version": schema or SCHEMA_VERSION_V1,
            "operation": op,
            "outcome": "PROTOCOL_ERROR",
            "status": "ERR_UNKNOWN_OPERATION",
        }


def make_test_ir(expr: str):
    """Helper to create a validated IR dict for bridge dispatch."""
    from mke_product.ai.ir import (
        MathIntermediateRepresentation,
        ProblemCategory,
        QuestionFormat,
        SourceSpan,
    )
    return MathIntermediateRepresentation(
        problem_category=ProblemCategory.EQUATION_SINGLE,
        question_format=QuestionFormat.FREE_FORM,
        raw_query=expr,
        primary_expressions=[expr],
        target_variables=["x"],
        source_spans=[
            SourceSpan(
                start_char=0,
                end_char=len(expr),
                source_fragment=expr,
                semantic_role="EQUATION",
            )
        ],
    ).model_dump()


class TestControlledDispatchBridgeB2Surd:
    """Test end-to-end controlled dispatch bridge with quadratic surd equations."""

    def test_b2_surd_x2_minus_2_success(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert res.radicand == 2
        assert res.discriminant.numerator == 8
        assert res.discriminant.denominator == 1
        assert len(res.verified_surd_roots) == 2
        r1, r2 = res.verified_surd_roots
        assert r1.rational_part.numerator == 0
        assert r1.sqrt_coefficient.numerator == -1
        assert r1.radicand == 2
        assert r2.rational_part.numerator == 0
        assert r2.sqrt_coefficient.numerator == 1
        assert r2.radicand == 2
        assert res.completeness_proven is True
        assert len(mock.call_history) == 1
        req, _ = mock.call_history[0]
        assert req["schema_version"] == SCHEMA_VERSION_V3
        assert req["operation"] == OPERATION_SOLVE_QUADRATIC_SURD

    def test_b2_surd_x2_plus_x_minus_1(self):
        ir = make_test_ir("x^2 + x - 1 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "-1", "denominator": "2"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "2"},
                        "radicand": "5",
                    },
                    {
                        "rational_part": {"numerator": "-1", "denominator": "2"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "2"},
                        "radicand": "5",
                    },
                ],
                "discriminant": {"numerator": "5", "denominator": "1"},
                "radicand": "5",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 + x - 1 = 0", ir_payload=ir, _controller=mock)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.is_verified is True
        assert res.radicand == 5
        assert res.verified_surd_roots[0].rational_part.numerator == -1
        assert res.verified_surd_roots[0].rational_part.denominator == 2
        assert res.verified_surd_roots[0].sqrt_coefficient.numerator == -1
        assert res.verified_surd_roots[0].sqrt_coefficient.denominator == 2
        assert res.verified_surd_roots[1].rational_part.numerator == -1
        assert res.verified_surd_roots[1].rational_part.denominator == 2
        assert res.verified_surd_roots[1].sqrt_coefficient.numerator == 1
        assert res.verified_surd_roots[1].sqrt_coefficient.denominator == 2

    def test_b2_routing_b1_rational_quadratic_preserves_v2(self):
        ir = make_test_ir("x^2 - 4 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 4 = 0", ir_payload=ir, _controller=mock)
        assert isinstance(res, QuadraticControlledDispatchResult)
        assert res.is_verified is True
        assert len(mock.call_history) == 3  # 1 SOLVE_QUADRATIC + 2 CHECK_CANDIDATE
        assert mock.call_history[0][0]["schema_version"] == SCHEMA_VERSION_V2

    def test_b2_routing_b0_linear_preserves_v1(self):
        ir = make_test_ir("2*x + 4 = 0")
        mock = MockBridgeWorkerController()
        res = ControlledDispatchBridge._dispatch_internal(raw_query="2*x + 4 = 0", ir_payload=ir, _controller=mock)
        assert not isinstance(res, QuadraticControlledDispatchResult)
        assert not isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.is_verified is True
        assert len(mock.call_history) == 2  # 1 SOLVE + 1 CHECK_CANDIDATE
        assert mock.call_history[0][0]["schema_version"] == SCHEMA_VERSION_V1


# ============================================================================
# 8. Expanded v3 Wire Adversarial Matrix (Requirement 9)
# ============================================================================

class TestAdversarialV3WireExpanded:
    """Test comprehensive wire response format and value validation."""

    def test_257_bit_rational_part_numerator_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        huge = str(1 << 257)
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": huge, "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": huge, "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_257_bit_sqrt_coeff_denominator_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        huge = str(1 << 257)
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": huge},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": huge},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_negative_denominator_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "-1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_zero_denominator_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "0"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_leading_plus_in_decimal_string_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "+1", "denominator": "1"},  # leading plus
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_unnecessary_leading_zero_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-01", "denominator": "1"},  # leading zero
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_zero_sqrt_coefficient_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "0", "denominator": "1"},  # zero sqrt coeff
                        "radicand": "2",
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "0", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_invalid_radicand_values_rejected(self):
        for invalid_rad in ["0", "1", str(1 << 32), "-2"]:
            ir = make_test_ir("x^2 - 2 = 0")
            mock = MockBridgeWorkerController(
                solve_res={
                    "schema_version": SCHEMA_VERSION_V3,
                    "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                    "outcome": "SUCCESS",
                    "status": "TWO_DISTINCT_REAL_ROOTS",
                    "roots": [
                        {
                            "rational_part": {"numerator": "0", "denominator": "1"},
                            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                            "radicand": invalid_rad,
                        },
                        {
                            "rational_part": {"numerator": "0", "denominator": "1"},
                            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                            "radicand": invalid_rad,
                        },
                    ],
                    "discriminant": {"numerator": "8", "denominator": "1"},
                    "radicand": invalid_rad,
                    "definedness": True,
                    "error": None,
                    "is_provisional_evidence": True,
                }
            )
            res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
            assert res.execution_status == ExecutionStatus.ENGINE_ERROR
            assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_noncanonical_equivalent_radicand_rejected(self):
        # For x^2 - 8 = 0, canonical root is +- 2*sqrt(2). Worker returns +- 1*sqrt(8)
        ir = make_test_ir("x^2 - 8 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "8",  # not squarefree / not canonical
                    },
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
                        "radicand": "8",
                    },
                ],
                "discriminant": {"numerator": "32", "denominator": "1"},
                "radicand": "8",  # host expects 2
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 8 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"


# ============================================================================
# 9. Complete Root-Pair Adversarial Matrix (Requirement 10)
# ============================================================================

class TestAdversarialRootPairComprehensive:
    """Validate root-pair consistency, symmetry, and host verification rejection."""

    def test_missing_root_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [
                    {
                        "rational_part": {"numerator": "0", "denominator": "1"},
                        "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
                        "radicand": "2",
                    },
                ],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_extra_root_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r, r, r],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.ENGINE_ERROR
        assert res.error_code == "ERR_MALFORMED_WORKER_RESPONSE"

    def test_duplicate_roots_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_neg],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_reversed_roots_order_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_pos = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_pos, r_neg],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_both_sqrt_coefficients_positive_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_pos = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_pos, r_pos],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_unequal_sqrt_coefficients_magnitudes_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_pos = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "2", "denominator": "1"},  # unequal magnitude
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_pos],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_different_rational_parts_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_pos = {
            "rational_part": {"numerator": "1", "denominator": "1"},  # different rational part
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_pos],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_different_radicands_between_roots_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_pos = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "3",  # different radicand
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_pos],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_wrong_top_level_radicand_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_plus = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_plus],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "3",  # top-level 3 vs root radicand 2
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_wrong_discriminant_rejected(self):
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_plus = {
            "rational_part": {"numerator": "0", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_plus],
                "discriminant": {"numerator": "12", "denominator": "1"},  # wrong discriminant
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"

    def test_internally_consistent_but_mathematically_wrong_pair_rejected(self):
        # Equation is x^2 - 2 = 0. Worker returns 1 +- sqrt(2)
        ir = make_test_ir("x^2 - 2 = 0")
        r_neg = {
            "rational_part": {"numerator": "1", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "-1", "denominator": "1"},
            "radicand": "2",
        }
        r_plus = {
            "rational_part": {"numerator": "1", "denominator": "1"},
            "sqrt_coefficient": {"numerator": "1", "denominator": "1"},
            "radicand": "2",
        }
        mock = MockBridgeWorkerController(
            solve_res={
                "schema_version": SCHEMA_VERSION_V3,
                "operation": OPERATION_SOLVE_QUADRATIC_SURD,
                "outcome": "SUCCESS",
                "status": "TWO_DISTINCT_REAL_ROOTS",
                "roots": [r_neg, r_plus],
                "discriminant": {"numerator": "8", "denominator": "1"},
                "radicand": "2",
                "definedness": True,
                "error": None,
                "is_provisional_evidence": True,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFICATION_FAILED
        assert res.error_code == "ERR_SURD_VERIFICATION_MISMATCH"


# ============================================================================
# 10. Worker Infrastructure Error Taxonomies
# ============================================================================

class TestWorkerInfrastructureTaxonomySurd:
    """Verify all worker infrastructure failure taxonomies are strictly mapped for surd."""

    @pytest.mark.parametrize(
        "worker_status,expected_exec,expected_err",
        [
            ("WORKER_TIMEOUT", "TIMEOUT", "ERR_TIMEOUT"),
            ("WORKER_RESOURCE_EXHAUSTED", "ENGINE_ERROR", "ERR_RESOURCE_EXHAUSTED"),
            ("WORKER_STARTUP_FAILURE", "ENGINE_ERROR", "ERR_WORKER_STARTUP_FAILURE"),
            ("WORKER_ASSIGNMENT_FAILURE", "ENGINE_ERROR", "ERR_WORKER_ASSIGNMENT_FAILURE"),
            ("WORKER_EXIT_FAILURE", "ENGINE_ERROR", "ERR_WORKER_EXIT_FAILURE"),
            ("WORKER_PROTOCOL_FAILURE", "ENGINE_ERROR", "ERR_WORKER_PROTOCOL_FAILURE"),
            ("ERR_RESOURCE_EXHAUSTED", "ENGINE_ERROR", "ERR_RESOURCE_EXHAUSTED"),
            ("ERR_PAYLOAD_TOO_LARGE", "ENGINE_ERROR", "ERR_PAYLOAD_TOO_LARGE"),
            ("ERR_RESPONSE_LIMIT_EXCEEDED", "ENGINE_ERROR", "ERR_RESPONSE_LIMIT_EXCEEDED"),
            ("PROTOCOL_ERROR", "ENGINE_ERROR", "ERR_PROTOCOL_ERROR"),
        ],
    )
    def test_worker_infrastructure_errors_solve_quadratic_surd(self, worker_status, expected_exec, expected_err):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(
            solve_res={
                "status": worker_status,
            }
        )
        res = ControlledDispatchBridge._dispatch_internal(raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == getattr(ExecutionStatus, expected_exec)
        assert res.verification_status == VerificationStatus.NOT_APPLICABLE
        assert res.is_verified is False
        assert res.error_code == expected_err


# ============================================================================
# 11. Cumulative Deadline & Monotonic Budget
# ============================================================================

class TestCumulativeDeadlineSurd:
    """Verify single worker call in B2 surd receives the full remaining budget."""

    def test_cumulative_deadline_surd_single_call(self):
        ir = make_test_ir("x^2 - 2 = 0")
        mock = MockBridgeWorkerController(solve_delay_sec=0.02)
        res = ControlledDispatchBridge._dispatch_internal(
            raw_query="x^2 - 2 = 0", ir_payload=ir, _controller=mock, _budget_sec=5.0
        )
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert len(mock.call_history) == 1
        req, timeout = mock.call_history[0]
        assert req["operation"] == OPERATION_SOLVE_QUADRATIC_SURD
        assert timeout is not None
        assert 0 < timeout <= 5.0


# ============================================================================
# 12. Architectural Boundary & Independence Tests
# ============================================================================

class TestBridgeArchitectureIndependenceSurd:
    """Verify architectural boundary: bridge.py must NOT import solver modules."""

    def test_bridge_does_not_import_solver_modules(self):
        import inspect
        from mke_product.cas import bridge
        source = inspect.getsource(bridge)
        assert "from mke_product.solver.quadratic_surd" not in source
        assert "import mke_product.solver.quadratic_surd" not in source
        assert "solve_quadratic_surd_equation" not in source
        assert "from mke_product.solver.quadratic" not in source
        assert "import mke_product.solver.quadratic" not in source
        assert "solve_quadratic_equation" not in source
        assert "from mke_product.solver.affine" not in source
        assert "import mke_product.solver.affine" not in source


# ============================================================================
# 13. Live Windows AppContainer Worker Integration Tests
# ============================================================================

@pytest.mark.skipif(sys.platform != "win32", reason="Windows AppContainer tests require Windows")
class TestLiveWindowsWorkerQuadraticSurdIntegration:
    """Live end-to-end integration tests with the real Windows AppContainer worker."""

    def test_live_worker_surd_x2_minus_2(self):
        ir = make_test_ir("x^2 - 2 = 0")
        res = ControlledDispatchBridge.dispatch("x^2 - 2 = 0", ir)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.intake_status == IntakeStatus.VALIDATED
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.solution_type == "TWO_DISTINCT_REAL_ROOTS"
        assert res.radicand == 2
        assert res.discriminant.numerator == 8
        assert res.discriminant.denominator == 1
        assert len(res.verified_surd_roots) == 2
        r1, r2 = res.verified_surd_roots
        assert r1.rational_part.numerator == 0
        assert r1.sqrt_coefficient.numerator == -1
        assert r1.sqrt_coefficient.denominator == 1
        assert r1.radicand == 2
        assert r2.rational_part.numerator == 0
        assert r2.sqrt_coefficient.numerator == 1
        assert r2.sqrt_coefficient.denominator == 1
        assert r2.radicand == 2
        assert res.completeness_proven is True

    def test_live_worker_surd_x2_plus_x_minus_1(self):
        ir = make_test_ir("x^2 + x - 1 = 0")
        res = ControlledDispatchBridge.dispatch("x^2 + x - 1 = 0", ir)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.radicand == 5
        assert res.discriminant.numerator == 5
        assert res.discriminant.denominator == 1
        r1, r2 = res.verified_surd_roots
        assert r1.rational_part.numerator == -1
        assert r1.rational_part.denominator == 2
        assert r1.sqrt_coefficient.numerator == -1
        assert r1.sqrt_coefficient.denominator == 2
        assert r1.radicand == 5
        assert r2.rational_part.numerator == -1
        assert r2.rational_part.denominator == 2
        assert r2.sqrt_coefficient.numerator == 1
        assert r2.sqrt_coefficient.denominator == 2
        assert r2.radicand == 5

    def test_live_worker_surd_3x2_plus_6x_plus_1(self):
        ir = make_test_ir("3*x^2 + 6*x + 1 = 0")
        res = ControlledDispatchBridge.dispatch("3*x^2 + 6*x + 1 = 0", ir)
        assert isinstance(res, QuadraticSurdControlledDispatchResult)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.radicand == 6
        assert res.discriminant.numerator == 24
        assert res.discriminant.denominator == 1
        r1, r2 = res.verified_surd_roots
        assert r1.rational_part.numerator == -1
        assert r1.rational_part.denominator == 1
        assert r1.sqrt_coefficient.numerator == -1
        assert r1.sqrt_coefficient.denominator == 3
        assert r1.radicand == 6
        assert r2.rational_part.numerator == -1
        assert r2.rational_part.denominator == 1
        assert r2.sqrt_coefficient.numerator == 1
        assert r2.sqrt_coefficient.denominator == 3
        assert r2.radicand == 6

    def test_live_worker_b1_quadratic_regression(self):
        ir = make_test_ir("x^2 - 4 = 0")
        res = ControlledDispatchBridge.dispatch("x^2 - 4 = 0", ir)
        assert isinstance(res, QuadraticControlledDispatchResult)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert len(res.verified_roots) == 2
        assert res.verified_roots[0].numerator == -2
        assert res.verified_roots[1].numerator == 2

    def test_live_worker_b0_linear_regression(self):
        ir = make_test_ir("2*x + 4 = 0")
        res = ControlledDispatchBridge.dispatch("2*x + 4 = 0", ir)
        assert res.execution_status == ExecutionStatus.SUCCESS
        assert res.verification_status == VerificationStatus.VERIFIED_COMPLETE
        assert res.is_verified is True
        assert res.verified_root is not None
        assert res.verified_root.numerator == -2
