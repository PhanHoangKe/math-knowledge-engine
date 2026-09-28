"""
Acceptance Test Suite for MKE Multi-Engine CAS (Product-03A v0).

Covers:
- Test A: SOLVE quadratic (x^2 - 4 = 0 -> {-2, 2})
- Test B: DIFFERENTIATE (x^2 + 3*x -> 2*x + 3)
- Test C: INTEGRATE (x^2 -> x^3/3 + C)
- Test D: SIMPLIFY ((x+1)*(x-1) -> x^2 - 1)
- Test E: PLOT_2D (smooth curves, asymptote split on 1/(x-2))
- Test F: NATIVE ROUTING (2*x + 4 = 10 -> mke_native_v1)
- Test G: DOMAIN PRESERVATION ((x-1)/(x-1) = 1 -> x != 1)
- Test H: MALICIOUS INPUT REJECTION (__import__, eval, code injection)
- Test I: RESOURCE SAFETY (deep nesting > 16, huge digits > 256, 1/0, 0^0)
- Test K: REGISTRY & CAPABILITIES (Engine registry, status, metadata)
"""

import math
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
        self.assertGreaterEqual(len(segment["x"]), 50)
        self.assertEqual(len(segment["x"]), len(segment["y"]))

    def test_plot_2d_asymptote_detection(self):
        req = ExecutionRequest(
            operation=OperationType.PLOT_2D,
            expression="1 / (x - 2)",
            options={"x_min": 0, "x_max": 4, "points": 100},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIsNotNone(res.plot_data)
        # Should split across the singularity at x = 2
        self.assertGreaterEqual(len(res.plot_data["segments"]), 2)
        # Discontinuities tracked
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
            preferred_engine="mke_native_v1",  # Native cannot solve quadratic, router handles fallback/dispatch
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.engine_used, "sympy_cas_v0")
        self.assertEqual(res.solution_set, ["-4", "4"])

    # -------------------------------------------------------------------------
    # Test G: DOMAIN PRESERVATION
    # -------------------------------------------------------------------------
    def test_domain_preservation_removable_singularity(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="(x - 1) / (x - 1) = 1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertTrue(any("x != 1" in note for note in res.domain_notes))

    # -------------------------------------------------------------------------
    # Test H: MALICIOUS INPUT REJECTION
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

    def test_zero_power_zero_detection(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="0^0",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.INVALID_INPUT)
        self.assertIn("Indeterminate form 0^0", res.error_message or "")

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

        active = registry.list_active_engines()
        active_ids = [e.engine_id for e in active]
        self.assertIn("mke_native_v1", active_ids)
        self.assertIn("sympy_cas_v0", active_ids)
        self.assertNotIn("scipy_numerical", active_ids)
        self.assertNotIn("sagemath_cas", active_ids)


if __name__ == "__main__":
    unittest.main()
