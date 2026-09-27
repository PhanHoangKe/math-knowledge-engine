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
from mke_product.protocol import (
    dispatch_request,
    dispatch_json,
    SCHEMA_VERSION,
    OPERATION_SOLVE,
    OPERATION_CHECK_CANDIDATE,
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
            "schema_version": "mke.p02a.v2",
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
        # Force ceiling smaller than standard response
        res = dispatch_request(req, max_response_bytes=60)
        self.assertEqual(res["outcome"], "RESOURCE_EXHAUSTED")
        self.assertEqual(res["status"], "ERR_RESPONSE_LIMIT_EXCEEDED")
        self.assertIsNone(res["definedness"])
        self.assertFalse(res["is_provisional_evidence"])
        self.assertEqual(res["error"]["code"], "ERR_RESPONSE_LIMIT_EXCEEDED")

        # dispatch_json helper also respects max_response_bytes
        raw_json = dispatch_json(json.dumps(req), max_response_bytes=60)
        self.assertIn("ERR_RESPONSE_LIMIT_EXCEEDED", raw_json)

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


if __name__ == "__main__":
    unittest.main()
