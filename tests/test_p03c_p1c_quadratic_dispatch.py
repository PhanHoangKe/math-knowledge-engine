"""Unit, integration, and protocol tests for P1C-04-B1 quadratic solver and dispatcher.

Milestone: PRODUCT-03C-P1C-04-B1
Author: Antigravity (Implementation Engineer)
Auditor: ChatGPT
"""

import json
import pytest

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
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
)
from mke_product.protocol.validator import validate_request_dict
from mke_product.solver.quadratic import (
    NonQuadraticExpressionError,
    extract_quadratic_coefficients,
    reduce_equation_quadratic,
    solve_quadratic_equation,
)


class TestProtocolVersionOperationMatrix:
    """Validate strict schema version and operation matrix enforcement."""

    def test_v1_solve_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        val = validate_request_dict(req)
        assert val["operation"] == OPERATION_SOLVE

    def test_v1_check_candidate_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "2*x + 4 = 0",
            "candidate": "-2",
        }
        val = validate_request_dict(req)
        assert val["operation"] == OPERATION_CHECK_CANDIDATE

    def test_v1_solve_quadratic_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v1'" in str(exc_info.value)

    def test_v2_solve_quadratic_allowed(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        val = validate_request_dict(req)
        assert val["schema_version"] == SCHEMA_VERSION_V2
        assert val["operation"] == OPERATION_SOLVE_QUADRATIC

    def test_v2_solve_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v2'" in str(exc_info.value)

    def test_v2_check_candidate_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 4 = 0",
            "candidate": "2",
        }
        with pytest.raises(ProtocolUnknownOperationError) as exc_info:
            validate_request_dict(req)
        assert "not supported in schema version 'mke.p02a.v2'" in str(exc_info.value)

    def test_unknown_schema_version_rejected(self):
        req = {
            "schema_version": "mke.p99.v1",
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        with pytest.raises(ProtocolUnsupportedVersionError):
            validate_request_dict(req)

    def test_v2_extra_field_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
            "options": {"timeout": 5},
        }
        with pytest.raises(ProtocolUnexpectedFieldError):
            validate_request_dict(req)

    def test_v2_non_ascii_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 – 4 = 0",  # en-dash
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)

    def test_v2_oversized_equation_rejected(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 + " + "1 + " * 100 + "0 = 0",
        }
        with pytest.raises(ProtocolInputLimitError):
            validate_request_dict(req)


class TestWorkerQuadraticSolverKernel:
    """Validate mathematical correctness and containment of pure-Python quadratic solver."""

    def test_two_distinct_rational_roots(self):
        eq = parse_equation("x^2 - 4 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-2), Rational(2)]
        assert res.discriminant == Rational(16)

    def test_two_distinct_fractional_roots(self):
        eq = parse_equation("3*x^2 - 5*x + 2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(2, 3), Rational(1)]
        assert res.discriminant == Rational(1)

    def test_unique_repeated_root(self):
        eq = parse_equation("(x - 1)^2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "UNIQUE_REAL_ROOT"
        assert res.roots == [Rational(1)]
        assert res.discriminant == Rational(0)

    def test_no_real_roots_negative_discriminant(self):
        eq = parse_equation("x^2 + 1 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "NO_REAL_ROOT"
        assert res.roots == []
        assert res.discriminant == Rational(-4)

    def test_multiplication_quadratic(self):
        eq = parse_equation("(x + 1)*(x - 1) = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-1), Rational(1)]
        assert res.discriminant == Rational(4)

    def test_repeated_variable_multiplication(self):
        eq = parse_equation("x*x = 4")
        res = solve_quadratic_equation(eq)
        assert res.status == "SUCCESS"
        assert res.classification == "TWO_DISTINCT_REAL_ROOTS"
        assert res.roots == [Rational(-2), Rational(2)]

    def test_irrational_roots_fail_closed(self):
        eq = parse_equation("x^2 - 2 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert res.roots == []

    def test_positive_non_square_fractional_discriminant_fail_closed(self):
        # 2*x^2 + 2*x + 0 = 0 -> Delta = 4 (square)
        # x^2 + x - 1/2 = 0 -> Delta = 1 - 4(1)(-1/2) = 3 (non-square)
        eq = parse_equation("2*x^2 + 2*x - 1 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"

    def test_degenerate_affine_rejected(self):
        eq = parse_equation("0*x^2 + x = 1")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_DEGENERATE_AFFINE_EQUATION"

    def test_pure_linear_rejected(self):
        eq = parse_equation("2*x + 4 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"
        assert res.error_code == "ERR_DEGENERATE_AFFINE_EQUATION"

    def test_degree_3_rejected(self):
        eq = parse_equation("x*x*x = 1")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"

    def test_variable_denominator_rejected(self):
        eq = parse_equation("1/(x - 1) = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "OUT_OF_SCOPE"

    def test_division_by_zero_constant_domain_error(self):
        eq = parse_equation("x^2 + 1/0 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_DIV_ZERO"

    def test_zero_power_zero_domain_error(self):
        eq = parse_equation("x^2 + 0^0 = 0")
        res = solve_quadratic_equation(eq)
        assert res.status == "DOMAIN_ERROR"
        assert res.error_code == "ERR_DOMAIN_ZERO_POWER_ZERO"


class TestDispatcherQuadraticIntegration:
    """Validate dispatcher execution for v2 SOLVE_QUADRATIC and v1 regression."""

    def test_v2_solve_quadratic_two_roots(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["operation"] == OPERATION_SOLVE_QUADRATIC
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "TWO_DISTINCT_REAL_ROOTS"
        assert res["roots"] == [
            {"numerator": "-2", "denominator": "1"},
            {"numerator": "2", "denominator": "1"},
        ]
        assert res["discriminant"] == {"numerator": "16", "denominator": "1"}
        assert res["definedness"] is True
        assert res["error"] is None

    def test_v2_solve_quadratic_no_real_root(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 + 1 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["operation"] == OPERATION_SOLVE_QUADRATIC
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "NO_REAL_ROOT"
        assert res["roots"] == []
        assert res["discriminant"] == {"numerator": "-4", "denominator": "1"}

    def test_v2_solve_quadratic_unique_root(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "(x - 1)^2 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "UNIQUE_REAL_ROOT"
        assert res["roots"] == [{"numerator": "1", "denominator": "1"}]
        assert res["discriminant"] == {"numerator": "0", "denominator": "1"}

    def test_v2_solve_quadratic_irrational_roots(self):
        req = {
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 2 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V2
        assert res["outcome"] == "OUT_OF_SCOPE"
        assert res["status"] == "ERR_UNSUPPORTED_EXACT_ROOT_REPRESENTATION"
        assert res["roots"] is None

    def test_v1_solve_regression_unchanged(self):
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE,
            "equation": "2*x + 4 = 0",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V1
        assert res["operation"] == OPERATION_SOLVE
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "UNIQUE_ROOT"
        assert res["root"] == {"numerator": "-2", "denominator": "1"}

    def test_v1_check_candidate_on_quadratic(self):
        # Existing S2 evaluator evaluates x^2 - 4 at x = 2
        req = {
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 4 = 0",
            "candidate": "2",
        }
        res = dispatch_request(req)
        assert res["schema_version"] == SCHEMA_VERSION_V1
        assert res["operation"] == OPERATION_CHECK_CANDIDATE
        assert res["outcome"] == "SUCCESS"
        assert res["status"] == "VALID"
        assert res["exact_equality"] is True
        assert res["residual"] == {"numerator": "0", "denominator": "1"}
