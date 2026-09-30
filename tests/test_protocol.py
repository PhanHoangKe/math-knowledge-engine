"""Authoritative test suite for MKE Product S4-A versioned protocol and dispatcher."""

from __future__ import annotations
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.core.rational import Rational
from mke_product.parser.parser import parse_equation
from mke_product.evaluator.budget import EvaluationBudget
from mke_product.evaluator.evaluator import check_candidate
from mke_product.solver.solver import solve_equation
from mke_product.solver.quadratic_surd import solve_quadratic_surd_equation
from mke_product.protocol import (
    dispatch_request,
    dispatch_json,
    SCHEMA_VERSION,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
    OPERATION_SOLVE,
    OPERATION_CHECK_CANDIDATE,
    OPERATION_SOLVE_QUADRATIC,
    OPERATION_SOLVE_QUADRATIC_SURD,
    MAX_RESPONSE_BYTES,
    MIN_RESPONSE_BYTES,
    MAX_JSON_NESTING_DEPTH,
)


class TestProtocolSolveDispatch(unittest.TestCase):
    """Mathematical dispatch and response mapping for SOLVE operation."""

    def test_solve_unique_root(self):
        """2*x+3=7 -> SUCCESS, UNIQUE_ROOT, root=2."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "2*x+3=7",
        }
        res = dispatch_request(req)
        self.assertEqual(res["schema_version"], SCHEMA_VERSION)
        self.assertEqual(res["operation"], OPERATION_SOLVE)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "UNIQUE_ROOT")
        self.assertEqual(res["classification"], "UNIQUE_ROOT")
        self.assertEqual(res["root"], {"numerator": "2", "denominator": "1"})
        self.assertTrue(res["definedness"])
        self.assertIsNone(res["error"])
        self.assertTrue(res["is_provisional_evidence"])
        self.assertIsNotNone(res["evidence"])

        # Differential verification against direct S3 solve_equation
        direct = solve_equation(parse_equation("2*x+3=7"))
        self.assertEqual(res["root"]["numerator"], str(direct.root.numerator))
        self.assertEqual(res["root"]["denominator"], str(direct.root.denominator))

    def test_solve_fractional_coefficients(self):
        """(1/2)*x + (3/4) = 0 -> root = -3/2."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "(1/2)*x + (3/4) = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "UNIQUE_ROOT")
        self.assertEqual(res["root"], {"numerator": "-3", "denominator": "2"})

    def test_solve_domain_set_r(self):
        """x = x -> DomainSet(R)."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x = x",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "DomainSet(R)")
        self.assertEqual(res["classification"], "DomainSet(R)")
        self.assertIsNone(res["root"])
        self.assertTrue(res["definedness"])
        self.assertIsNone(res["error"])
        self.assertTrue(res["is_provisional_evidence"])

    def test_solve_domain_set_r_constant_identity(self):
        """1 = 1 -> DomainSet(R)."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "1 = 1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "DomainSet(R)")
        self.assertEqual(res["classification"], "DomainSet(R)")
        self.assertIsNone(res["root"])

    def test_solve_empty_set_constant_contradiction(self):
        """1 = 2 -> EmptySet."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "1 = 2",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "EmptySet")
        self.assertEqual(res["classification"], "EmptySet")
        self.assertIsNone(res["root"])
        self.assertTrue(res["definedness"])
        self.assertIsNone(res["error"])

    def test_solve_empty_set_zero_times_x_equals_constant(self):
        """0*x = 5 -> EmptySet."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "0*x = 5",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "EmptySet")
        self.assertEqual(res["classification"], "EmptySet")
        self.assertIsNone(res["root"])

    def test_solve_nonlinear_scope_abstention(self):
        """x^2 - 4 = 0 -> OUT_OF_SCOPE, OUT_OF_SCOPE_NONLINEAR."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x^2 - 4 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "OUT_OF_SCOPE")
        self.assertEqual(res["status"], "OUT_OF_SCOPE_NONLINEAR")
        self.assertIsNone(res["root"])
        self.assertIsNone(res["definedness"])
        self.assertIsNotNone(res["error"])
        self.assertEqual(res["error"]["code"], "OUT_OF_SCOPE_NONLINEAR")

    def test_solve_variable_exponent_zero_abstention(self):
        """x^0 = 1 -> OUT_OF_SCOPE, OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x^0 = 1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "OUT_OF_SCOPE")
        self.assertEqual(res["status"], "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")
        self.assertIsNone(res["root"])
        self.assertIsNone(res["definedness"])
        self.assertEqual(res["error"]["code"], "OUT_OF_SCOPE_VARIABLE_EXPONENT_ZERO")

    def test_solve_mixed_hazard_owner_ruling_a(self):
        """Owner Decision MKE-S3-ADR-001: Proven constant domain error takes precedence."""
        # x^0 + 1/0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO
        res1 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x^0 + 1/0 = 0",
        })
        self.assertEqual(res1["outcome"], "DOMAIN_ERROR")
        self.assertEqual(res1["status"], "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertFalse(res1["definedness"])

        # 1/0 + x^0 = 0 -> DOMAIN_ERROR_DIVISION_BY_ZERO
        res2 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "1/0 + x^0 = 0",
        })
        self.assertEqual(res2["outcome"], "DOMAIN_ERROR")
        self.assertEqual(res2["status"], "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertFalse(res2["definedness"])

        # x^0 + 0^0 = 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO
        res3 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x^0 + 0^0 = 0",
        })
        self.assertEqual(res3["outcome"], "DOMAIN_ERROR")
        self.assertEqual(res3["status"], "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")
        self.assertFalse(res3["definedness"])

    def test_solve_resource_exhausted(self):
        """Budget exhaustion produces RESOURCE_EXHAUSTED outcome and UNKNOWN (null) definedness."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x = 1",
        }
        res = dispatch_request(req, budget=EvaluationBudget(max_operations=5))
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
        self.assertIsNone(res["classification"])
        self.assertIsNone(res["root"])
        self.assertIsNone(res["definedness"])
        self.assertIsNotNone(res["error"])

    def test_solve_syntax_error(self):
        """Malformed mathematical syntax yields SYNTAX_ERROR with accurate span."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "2*x+=7",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertEqual(res["status"], "ERR_SYNTAX_ParserError")
        self.assertIsNone(res["definedness"])
        self.assertEqual(res["error"]["span"], [4, 5])
        self.assertFalse(res["is_provisional_evidence"])


class TestProtocolCheckCandidateDispatch(unittest.TestCase):
    """Mathematical dispatch and response mapping for CHECK_CANDIDATE operation."""

    def test_candidate_valid(self):
        """(x-1)/(x-1)=1 with candidate 2 -> VALID."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "(x-1)/(x-1)=1",
            "candidate": "2",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["candidate"], {"numerator": "2", "denominator": "1"})
        self.assertTrue(res["exact_equality"])
        self.assertEqual(res["residual"], {"numerator": "0", "denominator": "1"})
        self.assertEqual(res["left_value"], {"numerator": "1", "denominator": "1"})
        self.assertEqual(res["right_value"], {"numerator": "1", "denominator": "1"})
        self.assertTrue(res["definedness"])
        self.assertIsNone(res["error"])
        self.assertTrue(res["is_provisional_evidence"])

    def test_candidate_invalid(self):
        """2*x=4 with candidate 3 -> INVALID."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "2*x=4",
            "candidate": "3",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "INVALID")
        self.assertEqual(res["candidate"], {"numerator": "3", "denominator": "1"})
        self.assertFalse(res["exact_equality"])
        self.assertEqual(res["residual"], {"numerator": "2", "denominator": "1"})
        self.assertEqual(res["left_value"], {"numerator": "6", "denominator": "1"})
        self.assertEqual(res["right_value"], {"numerator": "4", "denominator": "1"})
        self.assertTrue(res["definedness"])

    def test_candidate_domain_error_division_by_zero(self):
        """(x-1)/(x-1)=1 with candidate 1 -> DOMAIN_ERROR_DIVISION_BY_ZERO."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "(x-1)/(x-1)=1",
            "candidate": "1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "DOMAIN_ERROR")
        self.assertEqual(res["status"], "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertEqual(res["candidate"], {"numerator": "1", "denominator": "1"})
        self.assertIsNone(res["exact_equality"])
        self.assertIsNone(res["residual"])
        self.assertFalse(res["definedness"])
        self.assertEqual(res["error"]["code"], "DOMAIN_ERROR_DIVISION_BY_ZERO")
        self.assertEqual(res["error"]["span"], [6, 11])

    def test_candidate_domain_error_zero_to_zero(self):
        """x^0=1 with candidate 0 -> DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^0=1",
            "candidate": "0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "DOMAIN_ERROR")
        self.assertEqual(res["status"], "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")
        self.assertEqual(res["candidate"], {"numerator": "0", "denominator": "1"})
        self.assertFalse(res["definedness"])
        self.assertEqual(res["error"]["code"], "DOMAIN_ERROR_UNDEFINED_ZERO_TO_ZERO")

    def test_candidate_tiny_nonzero_rational_residual(self):
        """x = 1/7 with candidate 1/5 -> residual 2/35."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x = 1/7",
            "candidate": "1/5",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "INVALID")
        self.assertFalse(res["exact_equality"])
        self.assertEqual(res["residual"], {"numerator": "2", "denominator": "35"})
        self.assertEqual(res["left_value"], {"numerator": "1", "denominator": "5"})
        self.assertEqual(res["right_value"], {"numerator": "1", "denominator": "7"})

    def test_candidate_resource_exhausted(self):
        """Candidate check resource budget exhaustion yields UNKNOWN definedness."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x = 1",
            "candidate": "1",
        }
        res = dispatch_request(req, budget=EvaluationBudget(max_operations=1))
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], "ERR_RESOURCE_EXHAUSTED_STEP_LIMIT")
        self.assertIsNone(res["definedness"])


class TestProtocolValidationAndSecurity(unittest.TestCase):
    """Validation, schema enforcement, type checking, and attack resistance."""

    def test_unsupported_protocol_version(self):
        """Unsupported schema_version is rejected deterministically."""
        req = {
            "schema_version": "mke.p02a.v99",
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNSUPPORTED_VERSION")

    def test_unsupported_operation(self):
        """Unknown operation is rejected deterministically."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": "INTEGRATE",
            "equation": "x=1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

    def test_missing_required_fields(self):
        """Missing required fields rejected with ERR_PROTOCOL_MISSING_FIELD."""
        # Missing schema_version
        res1 = dispatch_request({"operation": OPERATION_SOLVE, "equation": "x=1"})
        self.assertEqual(res1["status"], "ERR_PROTOCOL_MISSING_FIELD")

        # Missing operation
        res2 = dispatch_request({"schema_version": SCHEMA_VERSION, "equation": "x=1"})
        self.assertEqual(res2["status"], "ERR_PROTOCOL_MISSING_FIELD")

        # Missing equation on SOLVE
        res3 = dispatch_request({"schema_version": SCHEMA_VERSION, "operation": OPERATION_SOLVE})
        self.assertEqual(res3["status"], "ERR_PROTOCOL_MISSING_FIELD")

        # Missing candidate on CHECK_CANDIDATE
        res4 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
        })
        self.assertEqual(res4["status"], "ERR_PROTOCOL_MISSING_FIELD")

    def test_unexpected_extra_fields(self):
        """Extra disallowed fields rejected under strict allowlist."""
        # Extra field on SOLVE
        res1 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "extra_field": 123,
        })
        self.assertEqual(res1["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res1["status"], "ERR_PROTOCOL_UNEXPECTED_FIELD")

        # Candidate supplied to SOLVE
        res2 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "candidate": "1",
        })
        self.assertEqual(res2["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res2["status"], "ERR_PROTOCOL_UNEXPECTED_FIELD")

    def test_invalid_types_on_solve(self):
        """Non-string fields rejected with ERR_PROTOCOL_INVALID_TYPE."""
        # equation is int
        res1 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": 123,
        })
        self.assertEqual(res1["status"], "ERR_PROTOCOL_INVALID_TYPE")

        # operation is boolean
        res2 = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": True,
            "equation": "x=1",
        })
        self.assertEqual(res2["status"], "ERR_PROTOCOL_INVALID_TYPE")

        # schema_version is list
        res3 = dispatch_request({
            "schema_version": ["mke.p02a.v1"],
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        })
        self.assertEqual(res3["status"], "ERR_PROTOCOL_INVALID_TYPE")

    def test_json_float_candidate_rejected(self):
        """JSON float candidate is rejected with ERR_PROTOCOL_INVALID_TYPE."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": 2.5,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIn("got float", res["error"]["message"])

    def test_json_bool_candidate_rejected(self):
        """JSON boolean candidate is rejected with ERR_PROTOCOL_INVALID_TYPE."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": True,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIn("got bool", res["error"]["message"])

    def test_json_null_candidate_rejected(self):
        """JSON null candidate is rejected with ERR_PROTOCOL_INVALID_TYPE."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": None,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")

    def test_malformed_candidate_string_rejected(self):
        """Malformed rational string rejected as PROTOCOL_ERROR."""
        cases = [
            ("abc", "ERR_INVALID_CANDIDATE_MALFORMED"),
            ("02", "ERR_INVALID_CANDIDATE_MALFORMED"),
            ("1/0", "ERR_INVALID_CANDIDATE_MALFORMED"),
            ("1/2/3", "ERR_INVALID_CANDIDATE_MALFORMED"),
            ("1.5", "ERR_INVALID_CANDIDATE_MALFORMED"),
        ]
        for cand, expected_code in cases:
            req = {
                "schema_version": SCHEMA_VERSION,
                "operation": OPERATION_CHECK_CANDIDATE,
                "equation": "x=1",
                "candidate": cand,
            }
            res = dispatch_request(req)
            self.assertEqual(res["outcome"], "PROTOCOL_ERROR", f"Failed for candidate {cand!r}")
            self.assertEqual(res["status"], expected_code)

    def test_oversized_payload_rejected(self):
        """Payload exceeding 4096 bytes is rejected before parsing."""
        huge_payload = json.dumps({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=" + ("1+" * 3000) + "1",
        })
        self.assertGreater(len(huge_payload), 4096)
        res = dispatch_request(huge_payload)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")

    def test_oversized_equation_rejected(self):
        """Equation exceeding 256 characters rejected with ERR_PROTOCOL_INPUT_LIMIT."""
        long_eq = "x + " + "1 + " * 70 + "1 = 0"
        self.assertGreater(len(long_eq), 256)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": long_eq,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INPUT_LIMIT")

    def test_non_ascii_equation_rejected(self):
        """Equation with non-ASCII characters rejected with ERR_PROTOCOL_INPUT_LIMIT."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x + \uff12 = 0",  # fullwidth digit '2'
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INPUT_LIMIT")

    def test_exact_rational_decimal_string_serialization(self):
        """Ensure no float representation appears anywhere in serialized numbers."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "3*x + 1 = 0",
        }
        raw_json = dispatch_json(json.dumps(req))
        data = json.loads(raw_json)
        self.assertIsInstance(data["root"]["numerator"], str)
        self.assertIsInstance(data["root"]["denominator"], str)
        self.assertEqual(data["root"]["numerator"], "-1")
        self.assertEqual(data["root"]["denominator"], "3")

    def test_json_roundtrip_bytes_and_str(self):
        """Convenience dispatch_json accepts both bytes and string."""
        payload_str = json.dumps({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        })
        out1 = dispatch_json(payload_str)
        out2 = dispatch_json(payload_str.encode("utf-8"))
        self.assertEqual(out1, out2)
        d = json.loads(out1)
        self.assertEqual(d["outcome"], "SUCCESS")
        self.assertEqual(d["root"], {"numerator": "1", "denominator": "1"})

    def test_provisional_evidence_flag_consistency(self):
        """Verify is_provisional_evidence flag is consistent across outcomes."""
        # 1. Success SOLVE: True
        res_sol = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        })
        self.assertTrue(res_sol["is_provisional_evidence"])

        # 2. Check Candidate: True
        res_cand = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": "1",
        })
        self.assertTrue(res_cand["is_provisional_evidence"])

        # 3. Protocol error: False
        res_err = dispatch_request({"invalid": "json"})
        self.assertFalse(res_err["is_provisional_evidence"])

        # 4. Syntax error: False
        res_syn = dispatch_request({
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x==1",
        })
        self.assertFalse(res_syn["is_provisional_evidence"])


class TestProtocolRemediationS4AR1(unittest.TestCase):
    """Regressions and boundary tests for S4-A-R1 remediation."""

    def test_excessive_tokens_solve_caught_cleanly(self):
        """Equation within 256 characters but exceeding 64 tokens caught for SOLVE."""
        # 33 ones + 33 pluses + 'x' + '=' + '0' = 69 tokens; string length is 69 chars (< 256 chars)
        eq = "x" + "+1" * 33 + "=0"
        self.assertLessEqual(len(eq), 256)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": eq,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertEqual(res["status"], "ERR_SYNTAX_InputBoundsExceededError")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertIn("tokens", res["error"]["message"])

    def test_excessive_tokens_check_candidate_caught_cleanly(self):
        """Equation within 256 characters but exceeding 64 tokens caught for CHECK_CANDIDATE."""
        eq = "x" + "+1" * 33 + "=0"
        self.assertLessEqual(len(eq), 256)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": eq,
            "candidate": "0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertEqual(res["status"], "ERR_SYNTAX_InputBoundsExceededError")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertIn("tokens", res["error"]["message"])

    def test_excessive_parenthesis_nesting_solve_caught_cleanly(self):
        """Equation exceeding 16 parenthesis levels caught for SOLVE."""
        # 17 levels of parentheses: (((...((x))...))) = 0
        eq = "(" * 17 + "x" + ")" * 17 + "=0"
        self.assertLessEqual(len(eq), 256)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": eq,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertEqual(res["status"], "ERR_SYNTAX_InputBoundsExceededError")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertIn("nesting depth", res["error"]["message"])

    def test_excessive_parenthesis_nesting_check_candidate_caught_cleanly(self):
        """Equation exceeding 16 parenthesis levels caught for CHECK_CANDIDATE."""
        eq = "(" * 17 + "x" + ")" * 17 + "=0"
        self.assertLessEqual(len(eq), 256)
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": eq,
            "candidate": "1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertEqual(res["status"], "ERR_SYNTAX_InputBoundsExceededError")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertIn("nesting depth", res["error"]["message"])

    def test_duplicate_json_keys_rejected(self):
        """Duplicate JSON object keys must be rejected before mathematical dispatch."""
        payload = '{"schema_version": "mke.p02a.v1", "schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "x=1"}'
        res = dispatch_request(payload)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertIsNone(res["definedness"])
        self.assertIn("Duplicate", res["error"]["message"])

    def test_dict_input_size_limit_enforced(self):
        """Dict payload exceeding 4096 bytes is rejected without unbounded serialization."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=" + "1" * 4500,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_non_string_dict_key_rejected(self):
        """Non-string dictionary key rejected with ERR_PROTOCOL_INVALID_TYPE."""
        req = {
            123: "SOLVE",
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res["definedness"])

    def test_excessive_json_nesting_rejected(self):
        """Excessive JSON nesting handled safely without uncaught recursion errors."""
        payload = '{"a": ' * 200 + '{"schema_version": "mke.p02a.v1"}' + '}' * 200
        res = dispatch_request(payload)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertIn("nesting depth", res["error"]["message"])
        self.assertIsNone(res["definedness"])

    def test_candidate_whitespace_rejected_at_protocol_boundary(self):
        """Candidate string with leading, trailing, or internal whitespace is strictly rejected."""
        # 1. Surrounding whitespace
        req1 = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": " 1 ",
        }
        res1 = dispatch_request(req1)
        self.assertEqual(res1["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res1["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res1["definedness"])

        # 2. Internal whitespace
        req2 = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": "1/ 2",
        }
        res2 = dispatch_request(req2)
        self.assertEqual(res2["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res2["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res2["definedness"])

        # 3. Tab character
        req3 = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": "\t1",
        }
        res3 = dispatch_request(req3)
        self.assertEqual(res3["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res3["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res3["definedness"])

    def test_response_size_limit_fails_closed(self):
        """Response exceeding MAX_RESPONSE_BYTES fails closed with ERR_RESPONSE_LIMIT_EXCEEDED."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        # Configurations smaller than MIN_RESPONSE_BYTES (512) are rejected with ValueError
        with self.assertRaises(ValueError):
            dispatch_request(req, max_response_bytes=60)

        with self.assertRaises(ValueError):
            dispatch_json(json.dumps(req), max_response_bytes=60)

        # Valid configurable limit (512 bytes): SOLVE response (~1355 bytes) exceeding 512 bytes fails closed
        req_solve = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        res = dispatch_request(req_solve, max_response_bytes=512)
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], "ERR_RESPONSE_LIMIT_EXCEEDED")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertEqual(res["error"]["code"], "ERR_RESPONSE_LIMIT_EXCEEDED")

        # Serialized length must satisfy effective limit
        serialized = json.dumps(res, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(serialized), 512)

        # dispatch_json helper also respects max_response_bytes
        raw_json = dispatch_json(json.dumps(req_solve), max_response_bytes=512)
        self.assertIn("ERR_RESPONSE_LIMIT_EXCEEDED", raw_json)
        self.assertLessEqual(len(raw_json.encode("utf-8")), 512)

    def test_syntax_error_definedness_null(self):
        """SYNTAX_ERROR returns definedness null, not false."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x++1=0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SYNTAX_ERROR")
        self.assertIsNone(res["definedness"])


class TestProtocolRemediationS4AR2(unittest.TestCase):
    """Regressions and boundary tests for S4-A-R2 remediation."""

    def test_response_limit_rejects_invalid_configuration(self):
        """max_response_bytes smaller than MIN_RESPONSE_BYTES (512) is rejected with ValueError."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        with self.assertRaises(ValueError):
            dispatch_request(req, max_response_bytes=60)

        with self.assertRaises(ValueError):
            dispatch_request(req, max_response_bytes=511)

        with self.assertRaises(ValueError):
            dispatch_request(req, max_response_bytes="invalid")

        with self.assertRaises(ValueError):
            dispatch_json(json.dumps(req), max_response_bytes=60)

    def test_response_limit_valid_smaller_ceiling(self):
        """A valid smaller ceiling (e.g. 512) enforces serialized limit and fails closed when exceeded."""
        # 1. Normal response fitting within 512 bytes (CHECK_CANDIDATE response is ~486 bytes)
        req_cand = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x=1",
            "candidate": "1",
        }
        res_ok = dispatch_request(req_cand, max_response_bytes=512)
        self.assertEqual(res_ok["outcome"], "SUCCESS")
        serialized_ok = json.dumps(res_ok, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(serialized_ok), 512)

        # 2. When response exceeds the smaller ceiling (SOLVE response is ~1355 bytes > 512 bytes), fails closed
        req_solve = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
        }
        res_solve = dispatch_request(req_solve, max_response_bytes=512)
        self.assertEqual(res_solve["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res_solve["status"], "ERR_RESPONSE_LIMIT_EXCEEDED")
        self.assertIsNone(res_solve["definedness"])
        self.assertFalse(res_solve["is_provisional_evidence"])
        # Invariant: serialized fallback length MUST satisfy <= 512 bytes
        serialized_fallback = json.dumps(res_solve, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(serialized_fallback), 512)

        # 3. Valid configurable limit accommodating SOLVE response (e.g. 2048 bytes)
        res_solve_2k = dispatch_request(req_solve, max_response_bytes=2048)
        self.assertEqual(res_solve_2k["outcome"], "SUCCESS")
        serialized_2k = json.dumps(res_solve_2k, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(serialized_2k), 2048)

        # dispatch_json helper also respects the valid smaller ceiling
        raw_json = dispatch_json(json.dumps(req_solve), max_response_bytes=512)
        self.assertIn("ERR_RESPONSE_LIMIT_EXCEEDED", raw_json)
        self.assertLessEqual(len(raw_json.encode("utf-8")), 512)

    def test_response_limit_default_max_response_bytes(self):
        """Default MAX_RESPONSE_BYTES=16384 satisfies serialized limit invariant."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "2*x+3=7",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        serialized = json.dumps(res, separators=(",", ":")).encode("utf-8")
        self.assertLessEqual(len(serialized), MAX_RESPONSE_BYTES)

    def test_json_error_classification_malformed_syntax(self):
        """Malformed JSON string produces ERR_PROTOCOL_JSON_DECODE (not malformed structure)."""
        bad_payloads = [
            "{invalid json",
            '{"schema_version": "mke.p02a.v1", "operation": }',
            '{"incomplete": ',
            "{",
        ]
        for p in bad_payloads:
            res = dispatch_request(p)
            self.assertEqual(res["outcome"], "PROTOCOL_ERROR", f"Failed for {p!r}")
            self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE", f"Failed for {p!r}")
            self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
            self.assertIsNone(res["definedness"])

    def test_json_error_classification_incorrect_root_structure(self):
        """Valid JSON with non-dict root produces ERR_PROTOCOL_MALFORMED_STRUCTURE."""
        non_dict_payloads = [
            "[1, 2, 3]",
            '"just a string"',
            "12345",
            "true",
            "null",
        ]
        for p in non_dict_payloads:
            res = dispatch_request(p)
            self.assertEqual(res["outcome"], "PROTOCOL_ERROR", f"Failed for {p!r}")
            self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE", f"Failed for {p!r}")
            self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
            self.assertIsNone(res["definedness"])

    def test_json_error_classification_duplicate_keys(self):
        """Valid JSON with duplicate object keys produces ERR_PROTOCOL_MALFORMED_STRUCTURE."""
        p = '{"schema_version": "mke.p02a.v1", "schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "x=1"}'
        res = dispatch_request(p)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertIn("Duplicate", res["error"]["message"])
        self.assertIsNone(res["definedness"])

    def test_invalid_unicode_isolated_surrogates_in_string(self):
        """Isolated Unicode surrogate in string payload is caught as ERR_PROTOCOL_JSON_DECODE."""
        surrogate_payload = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "\ud800=0"}'
        res = dispatch_request(surrogate_payload)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])

    def test_invalid_unicode_isolated_surrogates_in_dict(self):
        """Isolated Unicode surrogate in dict payload is caught as ERR_PROTOCOL_JSON_DECODE."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "\ud800=0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])

    def test_invalid_unicode_malformed_utf8_bytes(self):
        """Malformed UTF-8 bytes payload is caught as ERR_PROTOCOL_JSON_DECODE without uncaught exceptions."""
        malformed_bytes = b"\xff\xfe\x00\x00"
        res = dispatch_request(malformed_bytes)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])

    def test_dict_multibyte_unicode_oversized_in_unexpected_field(self):
        """Dict with oversized multibyte Unicode in unexpected field triggers ERR_PAYLOAD_TOO_LARGE.

        Guarantees that genuine byte bound is enforced before unexpected-field checking.
        """
        # Emoji '\U0001F600' is 1 char but 4 UTF-8 bytes; 1500 emojis = 6000 bytes > 4096 MAX_PAYLOAD_BYTES
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": "\U0001F600" * 1500,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        # Must be ERR_PAYLOAD_TOO_LARGE, NOT ERR_PROTOCOL_UNEXPECTED_FIELD
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertEqual(res["error"]["code"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_dict_rejects_unsupported_value_types(self):
        """Dict payload with unsupported value types is rejected predictably with ERR_PROTOCOL_INVALID_TYPE."""
        unsupported_req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "custom_object": object(),
        }
        res = dispatch_request(unsupported_req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_INVALID_TYPE")
        self.assertIsNone(res["definedness"])

    def test_json_nesting_ceiling_enforced_on_otherwise_valid_request(self):
        """Otherwise valid request wrapped in structures exceeding MAX_JSON_NESTING_DEPTH (16) fails with ERR_PROTOCOL_MALFORMED_STRUCTURE."""
        # 17 levels of wrapper objects around an otherwise valid request
        valid_inner = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "x=1"}'
        deeply_wrapped = '{"wrap": ' * 17 + valid_inner + '}' * 17
        res = dispatch_request(deeply_wrapped)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertIn("nesting depth", res["error"]["message"])
        self.assertIsNone(res["definedness"])

    def test_json_nesting_ceiling_deep_arrays(self):
        """Deeply nested arrays exceeding MAX_JSON_NESTING_DEPTH fail with ERR_PROTOCOL_MALFORMED_STRUCTURE."""
        deep_arr = "[" * 20 + "]" * 20
        res = dispatch_request(deep_arr)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_MALFORMED_STRUCTURE")
        self.assertIn("nesting depth", res["error"]["message"])

    def test_valid_ordinary_request_within_nesting_ceiling(self):
        """Valid ordinary request parses and executes normally within nesting ceiling."""
        req_str = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "x=1"}'
        res = dispatch_request(req_str)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "UNIQUE_ROOT")
        self.assertEqual(res["root"], {"numerator": "1", "denominator": "1"})
        self.assertTrue(res["definedness"])


class TestProtocolRemediationS4AR3(unittest.TestCase):
    """Regression tests for S4-A-R3 closure: escape-aware dict byte accounting and Unicode surrogates."""

    def test_dict_u0000_700_repetitions_rejected_as_payload_too_large(self):
        """Dict containing 700 U+0000 control chars in unexpected field exceeds 4096 JSON bytes and is rejected as ERR_PAYLOAD_TOO_LARGE."""
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": "\x00" * 700,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertEqual(res["error"]["code"], "ERR_PAYLOAD_TOO_LARGE")
        self.assertIsNone(res["definedness"])

    def test_dict_escaped_control_chars_quotes_and_backslashes(self):
        """Dict string byte calculation accurately accounts for 2-byte single-char escapes and 6-byte hex escapes."""
        # 2050 quotes -> 4100 bytes for quotes alone > 4096 MAX_PAYLOAD_BYTES
        req_quotes = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": '"' * 2050,
        }
        res_quotes = dispatch_request(req_quotes)
        self.assertEqual(res_quotes["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_quotes["status"], "ERR_PAYLOAD_TOO_LARGE")

        # 2050 backslashes -> 4100 bytes > 4096 MAX_PAYLOAD_BYTES
        req_bs = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": "\\" * 2050,
        }
        res_bs = dispatch_request(req_bs)
        self.assertEqual(res_bs["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_bs["status"], "ERR_PAYLOAD_TOO_LARGE")

        # 2050 newlines (\n) -> 4100 bytes > 4096 MAX_PAYLOAD_BYTES
        req_nl = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": "\n" * 2050,
        }
        res_nl = dispatch_request(req_nl)
        self.assertEqual(res_nl["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_nl["status"], "ERR_PAYLOAD_TOO_LARGE")

    def test_dict_multibyte_utf8_byte_accounting(self):
        """Dict string byte calculation accurately accounts for multibyte UTF-8 characters."""
        # 3-byte unicode character: \u4e2d (CJK character)
        # 1400 chars * 3 bytes = 4200 bytes > 4096 MAX_PAYLOAD_BYTES
        req = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "x=1",
            "unexpected_field": "\u4e2d" * 1400,
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PAYLOAD_TOO_LARGE")

    def test_raw_json_escaped_isolated_surrogate_rejected(self):
        """Raw ASCII JSON payload with escaped isolated surrogate (e.g. \\ud800) yields ERR_PROTOCOL_JSON_DECODE."""
        payload = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "\\ud800=0"}'
        res = dispatch_request(payload)
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertEqual(res["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res["definedness"])

        # Also test trailing surrogate \udfff
        payload_trailing = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "\\udfff=0"}'
        res_trailing = dispatch_request(payload_trailing)
        self.assertEqual(res_trailing["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_trailing["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertEqual(res_trailing["error"]["code"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res_trailing["definedness"])

        # In dict form with isolated surrogate in string
        req_dict = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION_SOLVE,
            "equation": "\ud800=0",
        }
        res_dict = dispatch_request(req_dict)
        self.assertEqual(res_dict["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_dict["status"], "ERR_PROTOCOL_JSON_DECODE")
        self.assertIsNone(res_dict["definedness"])

    def test_raw_json_ordinary_escaped_unicode_handled_correctly(self):
        """Ordinary escaped Unicode (e.g. \\u0078 for 'x') executes normally, while non-ASCII (\\u03c0 for 'π') triggers ERR_PROTOCOL_INPUT_LIMIT."""
        # \u0078 is ASCII 'x' -> 'x=1'
        payload_valid = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "\\u0078=1"}'
        res_valid = dispatch_request(payload_valid)
        self.assertEqual(res_valid["outcome"], "SUCCESS")
        self.assertEqual(res_valid["status"], "UNIQUE_ROOT")
        self.assertEqual(res_valid["root"], {"numerator": "1", "denominator": "1"})

        # \u03c0 is non-ASCII Greek pi -> valid Unicode scalar, but rejected by protocol ASCII requirement
        payload_pi = '{"schema_version": "mke.p02a.v1", "operation": "SOLVE", "equation": "\\u03c0*x=1"}'
        res_pi = dispatch_request(payload_pi)
        self.assertEqual(res_pi["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res_pi["status"], "ERR_PROTOCOL_INPUT_LIMIT")
        self.assertEqual(res_pi["error"]["code"], "ERR_PROTOCOL_INPUT_LIMIT")
        self.assertIn("ASCII", res_pi["error"]["message"])


class TestProtocolV3SolveQuadraticSurdDispatch(unittest.TestCase):
    """Protocol v3 SOLVE_QUADRATIC_SURD validation, matrix enforcement, and mathematical dispatch."""

    def test_v3_solve_quadratic_surd_standard(self):
        """x^2 - 2 = 0 -> SUCCESS, TWO_DISTINCT_REAL_ROOTS, radicand=2, roots=[-sqrt(2), +sqrt(2)]."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["schema_version"], SCHEMA_VERSION_V3)
        self.assertEqual(res["operation"], OPERATION_SOLVE_QUADRATIC_SURD)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "TWO_DISTINCT_REAL_ROOTS")
        self.assertEqual(res["discriminant"], {"numerator": "8", "denominator": "1"})
        self.assertEqual(res["radicand"], "2")
        self.assertTrue(res["definedness"])
        self.assertIsNone(res["error"])
        self.assertTrue(res["is_provisional_evidence"])
        self.assertEqual(len(res["roots"]), 2)
        # r1: 0 - 1*sqrt(2)
        self.assertEqual(res["roots"][0]["rational_part"], {"numerator": "0", "denominator": "1"})
        self.assertEqual(res["roots"][0]["sqrt_coefficient"], {"numerator": "-1", "denominator": "1"})
        self.assertEqual(res["roots"][0]["radicand"], "2")
        # r2: 0 + 1*sqrt(2)
        self.assertEqual(res["roots"][1]["rational_part"], {"numerator": "0", "denominator": "1"})
        self.assertEqual(res["roots"][1]["sqrt_coefficient"], {"numerator": "1", "denominator": "1"})
        self.assertEqual(res["roots"][1]["radicand"], "2")

    def test_v3_solve_quadratic_surd_fractional(self):
        """2*x^2 - 1 = 0 -> roots = [-sqrt(2)/2, +sqrt(2)/2]."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "2*x^2 - 1 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "TWO_DISTINCT_REAL_ROOTS")
        self.assertEqual(res["radicand"], "2")
        self.assertEqual(res["roots"][0]["sqrt_coefficient"], {"numerator": "-1", "denominator": "2"})
        self.assertEqual(res["roots"][1]["sqrt_coefficient"], {"numerator": "1", "denominator": "2"})

    def test_v3_solve_quadratic_surd_linear_term(self):
        """x^2 + x - 1 = 0 -> roots = [(-1-sqrt(5))/2, (-1+sqrt(5))/2]."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 + x - 1 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "TWO_DISTINCT_REAL_ROOTS")
        self.assertEqual(res["discriminant"], {"numerator": "5", "denominator": "1"})
        self.assertEqual(res["radicand"], "5")
        self.assertEqual(res["roots"][0]["rational_part"], {"numerator": "-1", "denominator": "2"})
        self.assertEqual(res["roots"][0]["sqrt_coefficient"], {"numerator": "-1", "denominator": "2"})
        self.assertEqual(res["roots"][1]["rational_part"], {"numerator": "-1", "denominator": "2"})
        self.assertEqual(res["roots"][1]["sqrt_coefficient"], {"numerator": "1", "denominator": "2"})

    def test_v3_solve_quadratic_surd_large_reducible_square(self):
        """Reducible large square factor: x^2 - 200 = 0 -> roots = [-10*sqrt(2), +10*sqrt(2)]."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 200 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "SUCCESS")
        self.assertEqual(res["status"], "TWO_DISTINCT_REAL_ROOTS")
        self.assertEqual(res["radicand"], "2")
        self.assertEqual(res["roots"][0]["sqrt_coefficient"], {"numerator": "-10", "denominator": "1"})
        self.assertEqual(res["roots"][1]["sqrt_coefficient"], {"numerator": "10", "denominator": "1"})

    def test_v3_counterexample_untested_prime_square_65537_fails_closed(self):
        """Counterexample M = 2 * 65537^2 (34 bits) fails closed with ERR_SURD_NORMALIZATION_RESOURCE_LIMIT."""
        # 65537^2 = 4295098369. Delta = 8 * 65537^2 = 34360786952 -> x^2 - 2*65537^2 = 0 -> x^2 - 8590196738 = 0
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 8590196738 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT")
        self.assertEqual(res["error"]["code"], "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT")

    def test_v3_counterexample_3_and_5_times_65537_squared_fails_closed(self):
        """M = 3 * 65537^2 and 5 * 65537^2 fail closed with ERR_SURD_NORMALIZATION_RESOURCE_LIMIT."""
        # 3 * 65537^2 = 12885295107
        res3 = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 12885295107 = 0",
        })
        self.assertEqual(res3["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res3["status"], "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT")

        # 5 * 65537^2 = 21475491845
        res5 = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 21475491845 = 0",
        })
        self.assertEqual(res5["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res5["status"], "ERR_SURD_NORMALIZATION_RESOURCE_LIMIT")

    def test_v3_rational_square_rejected_out_of_scope(self):
        """x^2 - 4 = 0 has rational roots and belongs to v2, rejected by v3 surd solver."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 4 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "OUT_OF_SCOPE")
        self.assertEqual(res["status"], "ERR_RATIONAL_QUADRATIC_IN_SURD_SOLVER")

    def test_v3_negative_discriminant_rejected_out_of_scope(self):
        """x^2 + 1 = 0 has Delta < 0, rejected by v3 surd solver."""
        req = {
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 + 1 = 0",
        }
        res = dispatch_request(req)
        self.assertEqual(res["outcome"], "OUT_OF_SCOPE")

    def test_v3_matrix_mismatch_rejections(self):
        """Cross-version operation mismatches rejected by validator."""
        # v1 + SOLVE_QUADRATIC_SURD
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V1,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

        # v2 + SOLVE_QUADRATIC_SURD
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V2,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

        # v3 + SOLVE
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE,
            "equation": "x = 1",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

        # v3 + SOLVE_QUADRATIC
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC,
            "equation": "x^2 - 4 = 0",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

        # v3 + CHECK_CANDIDATE
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_CHECK_CANDIDATE,
            "equation": "x^2 - 2 = 0",
            "candidate": "2",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNKNOWN_OPERATION")

    def test_v3_extra_field_rejected(self):
        """v3 request with extra options rejected."""
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x^2 - 2 = 0",
            "extra_field": 123,
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_UNEXPECTED_FIELD")

    def test_v3_non_ascii_rejected(self):
        """v3 non-ASCII equation rejected."""
        res = dispatch_request({
            "schema_version": SCHEMA_VERSION_V3,
            "operation": OPERATION_SOLVE_QUADRATIC_SURD,
            "equation": "x² - 2 = 0",
        })
        self.assertEqual(res["outcome"], "PROTOCOL_ERROR")
        self.assertEqual(res["status"], "ERR_PROTOCOL_INPUT_LIMIT")


if __name__ == "__main__":
    unittest.main()

