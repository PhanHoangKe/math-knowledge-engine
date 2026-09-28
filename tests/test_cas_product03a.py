"""
Acceptance Test Suite for MKE Multi-Engine CAS (Product-03A v0/R1).

Covers:
- Test A: SOLVE quadratic (x^2 - 4 = 0 -> {-2, 2})
- Test B: DIFFERENTIATE (x^2 + 3*x -> 2*x + 3)
- Test C: INTEGRATE (x^2 -> x^3/3 + C; definite integration with safe bounds)
- Test D: SIMPLIFY ((x+1)*(x-1) -> x^2 - 1; rational functions with domain preservation)
- Test E: PLOT_2D (smooth curves, asymptote split on 1/(x-2))
- Test F: NATIVE ROUTING (2*x + 4 = 10 -> mke_native_v1)
- Test G: DOMAIN PRESERVATION (removable singularities, composite zeros, multiple excluded points)
- Test H: MALICIOUS INPUT REJECTION (__import__, eval, code injection, options injection)
- Test I: RESOURCE SAFETY (deep nesting > 16, huge digits > 256, 1/0, 0^0, composite zeros)
- Test J: SUPERVISED TIMEOUT (killable child worker process on hard deadline)
- Test K: REGISTRY & CAPABILITIES (Engine registry, status, metadata)
"""

import math
import time
import unittest

from mke_product.cas.contracts import EngineStatus, ExecutionRequest, OperationType
from mke_product.cas.native_adapter import NativeMKEAdapter
from mke_product.cas.registry import CASRegistry
from mke_product.cas.router import CASRouter, execute_cas_operation
from mke_product.cas.safety import (
    ASTSafetyError,
    DivisionByZeroError,
    ExpressionBoundsError,
    check_input_bounds,
    extract_domain_restrictions,
    inspect_ast_safety,
    parse_safe_numeric_bound,
    sanitize_execution_options,
)
from mke_product.cas.sympy_adapter import SymPyAdapter


class TestCASProduct03A(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = CASRouter()

    # -------------------------------------------------------------------------
    # Test A: SOLVE Quadratic & Polynomials
    # -------------------------------------------------------------------------
    def test_solve_quadratic_exact_roots(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 4 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertIn("-2", res.result_str)
        self.assertIn("2", res.result_str)
        self.assertEqual(res.solution_set, ["-2", "2"])
        self.assertIsNotNone(res.latex_str)

    def test_solve_quadratic_expression_only(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 9",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.solution_set, ["-3", "3"])

    def test_solve_cubic(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^3 - 8 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIn("2", res.solution_set)

    def test_exact_realness_no_complex_roots(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 + 1 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.solution_set, [])
        self.assertEqual(res.result_str, "{}")

    # -------------------------------------------------------------------------
    # Test B: DIFFERENTIATE
    # -------------------------------------------------------------------------
    def test_differentiate_polynomial(self):
        req = ExecutionRequest(
            operation=OperationType.DIFFERENTIATE,
            expression="x^2 + 3*x",
            options={"variable": "x"},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertEqual(res.result_str, "2*x + 3")
        self.assertIn("2 x + 3", res.latex_str or "2*x + 3")

    def test_differentiate_higher_order(self):
        req = ExecutionRequest(
            operation=OperationType.DIFFERENTIATE,
            expression="x^4",
            options={"variable": "x", "order": 2},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.result_str, "12*x^2")

    # -------------------------------------------------------------------------
    # Test C: INTEGRATE
    # -------------------------------------------------------------------------
    def test_integrate_indefinite(self):
        req = ExecutionRequest(
            operation=OperationType.INTEGRATE,
            expression="x^2",
            options={"variable": "x"},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertTrue(res.result_str.endswith("+ C"))
        self.assertIn("x^3", res.result_str)
        self.assertIn("3", res.result_str)
        self.assertIn("+ C", res.latex_str or "")

    def test_integrate_definite(self):
        req = ExecutionRequest(
            operation=OperationType.INTEGRATE,
            expression="x^2",
            options={"variable": "x", "lower": 0, "upper": 3},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.result_str, "9")

    def test_integrate_definite_fractional_bounds(self):
        req = ExecutionRequest(
            operation=OperationType.INTEGRATE,
            expression="x",
            options={"variable": "x", "lower": "1/2", "upper": "3/2"},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.result_str, "1")

    # -------------------------------------------------------------------------
    # Test D: SIMPLIFY
    # -------------------------------------------------------------------------
    def test_simplify_polynomial_expansion(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="(x + 1) * (x - 1)",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertEqual(res.result_str, "x^2 - 1")

    def test_simplify_rational(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="(x^2 - 1) / (x - 1)",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.result_str, "x + 1")
        self.assertTrue(len(res.domain_notes) > 0)
        self.assertIn("x != 1", res.domain_notes[0])

    # -------------------------------------------------------------------------
    # Test E: PLOT_2D
    # -------------------------------------------------------------------------
    def test_plot_2d_smooth_curve(self):
        req = ExecutionRequest(
            operation=OperationType.PLOT_2D,
            expression="x^2 - 1",
            options={"x_min": -3, "x_max": 3, "points": 100},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIsNotNone(res.plot_data)
        self.assertEqual(len(res.plot_data["segments"]), 1)
        segment = res.plot_data["segments"][0]
        self.assertGreaterEqual(len(segment), 50)
        self.assertIn("x", segment[0])
        self.assertIn("y", segment[0])

    def test_plot_2d_asymptote_detection(self):
        req = ExecutionRequest(
            operation=OperationType.PLOT_2D,
            expression="1 / (x - 2)",
            options={"x_min": 0, "x_max": 4, "points": 100},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIsNotNone(res.plot_data)
        self.assertGreaterEqual(len(res.plot_data["segments"]), 2)
        self.assertIn(2.0, [round(d, 1) for d in res.plot_data["discontinuities"]])

    # -------------------------------------------------------------------------
    # Test F: NATIVE ROUTING
    # -------------------------------------------------------------------------
    def test_native_routing_linear_equation(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="2*x + 4 = 10",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "mke_native_v1")
        self.assertEqual(res.solution_set, ["3"])
        self.assertIn("steps", res.details)
        self.assertGreater(len(res.details["steps"]), 0)

    def test_forced_native_engine(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="3*x - 9 = 0",
            preferred_engine="mke_native_v1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "mke_native_v1")
        self.assertEqual(res.solution_set, ["3"])

    def test_nonlinear_falls_to_sympy(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 16 = 0",
            preferred_engine="mke_native_v1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertEqual(res.solution_set, ["-4", "4"])

    # -------------------------------------------------------------------------
    # Test G: DOMAIN PRESERVATION & SINGULARITIES
    # -------------------------------------------------------------------------
    def test_domain_preservation_removable_singularity(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="(x - 1) / (x - 1) = 1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertTrue(any("x != 1" in note for note in res.domain_notes))

    def test_multiple_excluded_points(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="((x - 2) * (x - 3)) / ((x - 2) * (x - 4))",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        notes = res.domain_notes
        self.assertTrue(any("x != 2" in n for n in notes))
        self.assertTrue(any("x != 4" in n for n in notes))

    def test_variable_exponent_zero_domain_restriction(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^0 = 1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertTrue(any("x != 0" in n for n in res.domain_notes))

    # -------------------------------------------------------------------------
    # Test H: MALICIOUS INPUT & OPTION REJECTION
    # -------------------------------------------------------------------------
    def test_reject_python_dunder_and_builtins(self):
        malicious_inputs = [
            "__import__('os').system('dir')",
            "eval('1+1')",
            "exec('x=1')",
            "globals()",
            "locals()",
            "open('file.txt')",
            "system('whoami')",
            "import os",
            "def foo(): pass",
            "lambda x: x",
        ]
        for bad_input in malicious_inputs:
            with self.subTest(bad_input=bad_input):
                req = ExecutionRequest(
                    operation=OperationType.SIMPLIFY,
                    expression=bad_input,
                )
                res = self.router.execute(req)
                self.assertEqual(res.status, EngineStatus.SECURITY_REJECTED)
                self.assertIsNotNone(res.error_message)

    def test_reject_invalid_token_characters(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x + $y = 0",
        )
        res = self.router.execute(req)
        self.assertIn(res.status, [EngineStatus.INVALID_INPUT, EngineStatus.SECURITY_REJECTED])

    def test_reject_malicious_options(self):
        bad_options = [
            {"lower": "__import__('os').system('calc')"},
            {"upper": "eval('1+1')"},
            {"order": "system('whoami')"},
            {"num_points": "100; os.system('dir')"},
            {"unknown_key": "injected_payload"},
        ]
        for opt in bad_options:
            with self.subTest(opt=opt):
                req = ExecutionRequest(
                    operation=OperationType.INTEGRATE,
                    expression="x^2",
                    options=opt,
                )
                res = self.router.execute(req)
                self.assertEqual(res.status, EngineStatus.INVALID_INPUT)

    # -------------------------------------------------------------------------
    # Test I: RESOURCE SAFETY & MATHEMATICAL BOUNDS
    # -------------------------------------------------------------------------
    def test_reject_excessive_nesting_depth(self):
        deep_expr = "(" * 20 + "x" + ")" * 20
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression=deep_expr,
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.RESOURCE_LIMIT_EXCEEDED)

    def test_reject_huge_integer_literal(self):
        huge_expr = "x + " + "9" * 300
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression=huge_expr,
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.RESOURCE_LIMIT_EXCEEDED)

    def test_reject_input_length_exceeded(self):
        long_expr = "x + " + "+".join(["1"] * 2500)
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression=long_expr,
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.RESOURCE_LIMIT_EXCEEDED)

    def test_division_by_zero_detection(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="1 / 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
        self.assertIn("Division by zero", res.error_message or "")

    def test_composite_constant_zero_denominator_rejected(self):
        cases = ["1 / (2 - 2)", "x / (10 - 10)", "5 / (3 * 0)"]
        for expr in cases:
            with self.subTest(expr=expr):
                req = ExecutionRequest(
                    operation=OperationType.SIMPLIFY,
                    expression=expr,
                )
                res = self.router.execute(req)
                self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
                self.assertIn("Division by zero", res.error_message or "")

    def test_zero_power_zero_detection(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="0^0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
        self.assertIn("Indeterminate form 0^0", res.error_message or "")

    def test_composite_zero_power_zero_detection(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="(5 - 5)^0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
        self.assertIn("Indeterminate form 0^0", res.error_message or "")

    # -------------------------------------------------------------------------
    # Test J: SUPERVISED TIMEOUT & CHILD WORKER REAPING
    # -------------------------------------------------------------------------
    def test_supervised_process_terminates_on_timeout(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 4 = 0",
            options={"sleep_seconds": 1.0},
            timeout_sec=0.1,  # Short deadline triggers timeout termination
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.RESOURCE_EXHAUSTED)
        self.assertIn("Computation timed out", res.error_message or "")

    # -------------------------------------------------------------------------
    # Test K: REGISTRY & CAPABILITIES
    # -------------------------------------------------------------------------
    def test_engine_registry_listing(self):
        registry = CASRegistry()
        engines = registry.list_engines()
        engine_ids = [e.engine_id for e in engines]
        self.assertIn("mke_native_v1", engine_ids)
        self.assertIn("sympy_cas_v0", engine_ids)
        self.assertIn("scipy_numerical", engine_ids)
        self.assertIn("sagemath_cas", engine_ids)

    # -------------------------------------------------------------------------
    # Test L: DOMAIN CERTAINTY & CONTRACT TESTS
    # -------------------------------------------------------------------------
    def test_domain_certainty_polynomial_proven_reals(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="2*x + 3 = 7",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.domain_certainty.value, "PROVEN_REALS")
        self.assertEqual(res.domain_restrictions, [])

        # Quadratic polynomial via SymPy
        req2 = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 4 = 0",
        )
        res2 = self.router.execute(req2)
        self.assertEqual(res2.status, EngineStatus.SUCCESS)
        self.assertEqual(res2.domain_certainty.value, "PROVEN_REALS")
        self.assertEqual(res2.domain_restrictions, [])

    def test_domain_certainty_rational_explicit_exclusions(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="(x^2 - 1)/(x - 1)",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.domain_certainty.value, "EXPLICIT_EXCLUSIONS")
        self.assertIn("x != 1", res.domain_restrictions)

    def test_domain_certainty_rejection_not_applicable(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="2x + 1 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
        self.assertEqual(res.domain_certainty.value, "NOT_APPLICABLE")

    # -------------------------------------------------------------------------
    # Test M: VERIFICATION EVIDENCE & STATUS CONTRACT
    # -------------------------------------------------------------------------
    def test_native_adapter_verification_status_with_evidence(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="3*x + 6 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "mke_native_v1")
        self.assertEqual(res.verification_status.value, "VERIFIED_WITH_EVIDENCE")
        self.assertIsNotNone(res.verification_evidence)

    def test_sympy_adapter_verification_status_computed(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="x^2 - 5*x + 6 = 0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertEqual(res.verification_status.value, "COMPUTED")

    def test_execution_response_to_dict_contract_fields(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="2*x + 4 = 10",
        )
        res = self.router.execute(req)
        d = res.to_dict()
        self.assertIn("domain_certainty", d)
        self.assertEqual(d["domain_certainty"], "PROVEN_REALS")
        self.assertIn("verification_status", d)
        self.assertEqual(d["verification_status"], "VERIFIED_WITH_EVIDENCE")


if __name__ == "__main__":
    unittest.main()

