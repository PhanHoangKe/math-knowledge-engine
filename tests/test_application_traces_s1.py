"""Comprehensive test suite for S1-03 Deterministic Multi-Method Solution Trace Engines.

Verifies:
1. QUAD_FORMULA_STANDARD deterministic step generation and exact kernel parity.
2. QUAD_FORMULA_REDUCED deterministic step generation and exact kernel parity across even, odd, fractional b.
3. QUAD_VIETE_SPECIAL_SUM deterministic step generation, repeated root handling, and strict fail-closed non-applicability.
4. QUAD_VIETE_SPECIAL_DIF deterministic step generation, repeated root handling, and strict fail-closed non-applicability.
5. TRACE_GENERATORS registry matching exact S1 execution availability in MethodRegistry.
6. Adversarial runtime type rejection (TypeError for float/str/int) and a == 0 rejection (TraceInvalidInputError).
7. Complete end-to-end cross-verification with HostIndependentVerifier.verify_quadratic_solution.
"""

from __future__ import annotations

import os
import sys
import unittest

# Ensure src is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from mke_product.application.traces import (
    ReducedQuadraticFormulaTraceGenerator,
    StandardQuadraticFormulaTraceGenerator,
    TRACE_GENERATORS,
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
    VieteSpecialDifTraceGenerator,
    VieteSpecialSumTraceGenerator,
    generate_solution_trace,
    get_trace_generator,
)
from mke_product.core.rational import Rational
from mke_product.domain.exact import solve_exact_quadratic
from mke_product.domain.models import (
    ExecutionAvailability,
    SolutionOutcome,
    SolutionRootType,
    SolutionTrace,
    VerificationOutcome,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.domain.verifier import HostIndependentVerifier


class TestStandardQuadraticFormulaTrace(unittest.TestCase):
    """Tests for Standard Quadratic Formula trace generator (QUAD_FORMULA_STANDARD)."""

    def setUp(self):
        self.generator = StandardQuadraticFormulaTraceGenerator()
        self.verifier = HostIndependentVerifier()

    def _verify_trace_contract(self, trace: SolutionTrace, a: Rational, b: Rational, c: Rational):
        self.assertEqual(trace.method_id, "QUAD_FORMULA_STANDARD")
        self.assertTrue(trace.is_complete)
        self.assertTrue(len(trace.steps) >= 3)
        # Check contiguous step numbering
        for idx, step in enumerate(trace.steps, start=1):
            self.assertEqual(step.step_number, idx)
            self.assertTrue(len(step.latex_expression) > 0)
            self.assertTrue(len(step.explanation_vi) > 0)
            self.assertTrue(len(step.why_this_step_vi or "") > 0)
            self.assertIsNotNone(step.rule_or_theorem_used)

        # Cross-check mathematical truth with HostIndependentVerifier
        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_quad_std"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_standard_formula_rational_distinct_roots(self):
        # x^2 - 5*x + 6 = 0 -> roots {2, 3}
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(2, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 1))
        self.assertEqual(trace.final_answer_latex, "S = \\left\\{ 2, 3 \\right\\}")
        self._verify_trace_contract(trace, a, b, c)

    def test_standard_formula_repeated_real_root(self):
        # x^2 - 2*x + 1 = 0 -> root {1}
        a = Rational(1, 1)
        b = Rational(-2, 1)
        c = Rational(1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(len(trace.roots), 1)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.final_answer_latex, "x = 1")
        self._verify_trace_contract(trace, a, b, c)

    def test_standard_formula_no_real_roots(self):
        # x^2 + 1 = 0 -> no real roots
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.NO_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 0)
        self.assertEqual(trace.final_answer_latex, "S = \\emptyset")
        self._verify_trace_contract(trace, a, b, c)

    def test_standard_formula_surd_roots(self):
        # x^2 - 2 = 0 -> roots {-sqrt(2), sqrt(2)}
        a = Rational(1, 1)
        b = Rational(0, 1)
        c = Rational(-2, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(trace.roots[0].radicand, 2)
        self.assertEqual(trace.roots[1].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(trace.roots[1].radicand, 2)
        self._verify_trace_contract(trace, a, b, c)

    def test_standard_formula_non_monic_rational(self):
        # 2*x^2 - 5*x + 2 = 0 -> roots {1/2, 2}
        a = Rational(2, 1)
        b = Rational(-5, 1)
        c = Rational(2, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 2))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(2, 1))
        self._verify_trace_contract(trace, a, b, c)

    def test_standard_formula_fractional_coefficients(self):
        # (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> roots {1, 3/2}
        a = Rational(1, 2)
        b = Rational(-5, 4)
        c = Rational(3, 4)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 2))
        self._verify_trace_contract(trace, a, b, c)


class TestReducedQuadraticFormulaTrace(unittest.TestCase):
    """Tests for Reduced Quadratic Formula trace generator (QUAD_FORMULA_REDUCED)."""

    def setUp(self):
        self.generator = ReducedQuadraticFormulaTraceGenerator()
        self.std_generator = StandardQuadraticFormulaTraceGenerator()
        self.verifier = HostIndependentVerifier()

    def _verify_trace_contract(self, trace: SolutionTrace, a: Rational, b: Rational, c: Rational):
        self.assertEqual(trace.method_id, "QUAD_FORMULA_REDUCED")
        self.assertTrue(trace.is_complete)
        self.assertTrue(len(trace.steps) >= 3)
        for idx, step in enumerate(trace.steps, start=1):
            self.assertEqual(step.step_number, idx)
            self.assertTrue(len(step.latex_expression) > 0)
            self.assertTrue(len(step.explanation_vi) > 0)
            self.assertTrue(len(step.why_this_step_vi or "") > 0)
            self.assertIsNotNone(step.rule_or_theorem_used)

        # Cross-check mathematical truth with HostIndependentVerifier
        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_quad_red"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

        # Ensure exact parity of root values with standard formula generator
        std_trace = self.std_generator.generate_trace(a, b, c)
        self.assertEqual(trace.solution_outcome, std_trace.solution_outcome)
        self.assertEqual(trace.roots, std_trace.roots)
        self.assertEqual(trace.final_answer_latex, std_trace.final_answer_latex)

    def test_reduced_formula_even_integer_b(self):
        # x^2 - 4*x + 3 = 0 -> b' = -2, Delta' = 1, roots {1, 3}
        a = Rational(1, 1)
        b = Rational(-4, 1)
        c = Rational(3, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 1))
        self._verify_trace_contract(trace, a, b, c)

    def test_reduced_formula_odd_integer_b(self):
        # x^2 - 5*x + 6 = 0 -> b' = -5/2, Delta' = 1/4, roots {2, 3}
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(2, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 1))
        self._verify_trace_contract(trace, a, b, c)

    def test_reduced_formula_fractional_b(self):
        # (1/2)*x^2 - (5/4)*x + 3/4 = 0 -> b' = -5/8, Delta' = 1/64, roots {1, 3/2}
        a = Rational(1, 2)
        b = Rational(-5, 4)
        c = Rational(3, 4)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 2))
        self._verify_trace_contract(trace, a, b, c)

    def test_reduced_formula_negative_delta_prime(self):
        # x^2 + 2*x + 5 = 0 -> b' = 1, Delta' = -4 < 0
        a = Rational(1, 1)
        b = Rational(2, 1)
        c = Rational(5, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.NO_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 0)
        self._verify_trace_contract(trace, a, b, c)

    def test_reduced_formula_zero_delta_prime(self):
        # x^2 - 2*x + 1 = 0 -> b' = -1, Delta' = 0 -> root {1}
        a = Rational(1, 1)
        b = Rational(-2, 1)
        c = Rational(1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(len(trace.roots), 1)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self._verify_trace_contract(trace, a, b, c)

    def test_reduced_formula_surd_roots(self):
        # x^2 - 2*x - 1 = 0 -> b' = -1, Delta' = 2 -> roots {1 - sqrt(2), 1 + sqrt(2)}
        a = Rational(1, 1)
        b = Rational(-2, 1)
        c = Rational(-1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(trace.roots[0].radicand, 2)
        self.assertEqual(trace.roots[1].root_type, SolutionRootType.REAL_SURD)
        self.assertEqual(trace.roots[1].radicand, 2)
        self._verify_trace_contract(trace, a, b, c)


class TestVieteSpecialSumTrace(unittest.TestCase):
    """Tests for Viète Special Sum trace generator (QUAD_VIETE_SPECIAL_SUM)."""

    def setUp(self):
        self.generator = VieteSpecialSumTraceGenerator()
        self.verifier = HostIndependentVerifier()

    def test_viete_sum_applicable_monic(self):
        # x^2 - 3*x + 2 = 0 -> a+b+c = 1 - 3 + 2 = 0 -> roots {1, 2}
        a = Rational(1, 1)
        b = Rational(-3, 1)
        c = Rational(2, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.method_id, "QUAD_VIETE_SPECIAL_SUM")
        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(2, 1))
        self.assertEqual(trace.final_answer_latex, "S = \\left\\{ 1, 2 \\right\\}")

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_sum_1"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_sum_applicable_non_monic(self):
        # 2*x^2 - 5*x + 3 = 0 -> a+b+c = 2 - 5 + 3 = 0 -> roots {1, 3/2}
        a = Rational(2, 1)
        b = Rational(-5, 1)
        c = Rational(3, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(3, 2))

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_sum_2"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_sum_applicable_repeated_root(self):
        # x^2 - 2*x + 1 = 0 -> a+b+c = 1 - 2 + 1 = 0, c/a = 1 -> repeated root {1}
        a = Rational(1, 1)
        b = Rational(-2, 1)
        c = Rational(1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(len(trace.roots), 1)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(1, 1))
        self.assertEqual(trace.final_answer_latex, "x = 1")

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_sum_rep"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_sum_non_applicable_fails_closed(self):
        # x^2 - 5*x + 6 = 0 -> a+b+c = 2 != 0
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        with self.assertRaises(TraceMethodNotApplicableError) as ctx:
            self.generator.generate_trace(a, b, c)
        self.assertIn("QUAD_VIETE_SPECIAL_SUM requires a + b + c == 0", str(ctx.exception))


class TestVieteSpecialDifTrace(unittest.TestCase):
    """Tests for Viète Special Difference trace generator (QUAD_VIETE_SPECIAL_DIF)."""

    def setUp(self):
        self.generator = VieteSpecialDifTraceGenerator()
        self.verifier = HostIndependentVerifier()

    def test_viete_dif_applicable_monic(self):
        # x^2 + 3*x + 2 = 0 -> a - b + c = 1 - 3 + 2 = 0 -> roots {-2, -1}
        a = Rational(1, 1)
        b = Rational(3, 1)
        c = Rational(2, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.method_id, "QUAD_VIETE_SPECIAL_DIF")
        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(-2, 1))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(-1, 1))
        self.assertEqual(trace.final_answer_latex, "S = \\left\\{ -2, -1 \\right\\}")

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_dif_1"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_dif_applicable_non_monic(self):
        # 2*x^2 + 5*x + 3 = 0 -> a - b + c = 2 - 5 + 3 = 0 -> roots {-3/2, -1}
        a = Rational(2, 1)
        b = Rational(5, 1)
        c = Rational(3, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)
        self.assertEqual(len(trace.roots), 2)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(-3, 2))
        self.assertEqual(trace.roots[1].rational_value.to_rational(), Rational(-1, 1))

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_dif_2"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_dif_applicable_repeated_root(self):
        # x^2 + 2*x + 1 = 0 -> a - b + c = 1 - 2 + 1 = 0, -c/a = -1 -> repeated root {-1}
        a = Rational(1, 1)
        b = Rational(2, 1)
        c = Rational(1, 1)
        trace = self.generator.generate_trace(a, b, c)

        self.assertEqual(trace.solution_outcome, SolutionOutcome.ONE_REPEATED_REAL_ROOT)
        self.assertEqual(len(trace.roots), 1)
        self.assertEqual(trace.roots[0].rational_value.to_rational(), Rational(-1, 1))
        self.assertEqual(trace.final_answer_latex, "x = -1")

        cert = self.verifier.verify_quadratic_solution(
            a, b, c, trace.solution_outcome, trace.roots, problem_hash="test_viete_dif_rep"
        )
        self.assertEqual(cert.outcome, VerificationOutcome.VERIFIED_COMPLETE)

    def test_viete_dif_non_applicable_fails_closed(self):
        # x^2 + 5*x + 6 = 0 -> a - b + c = 1 - 5 + 6 = 2 != 0
        a = Rational(1, 1)
        b = Rational(5, 1)
        c = Rational(6, 1)
        with self.assertRaises(TraceMethodNotApplicableError) as ctx:
            self.generator.generate_trace(a, b, c)
        self.assertIn("QUAD_VIETE_SPECIAL_DIF requires a - b + c == 0", str(ctx.exception))


class TestTraceRegistryAndCapabilityConsistency(unittest.TestCase):
    """Tests verifying trace generator registry consistency with MethodRegistry."""

    def test_trace_registry_keys_match_available_methods(self):
        available_methods = {
            m_id
            for m_id, caps in MethodRegistry.S0_CAPABILITY_MATRIX.items()
            if caps["execution_availability"] == ExecutionAvailability.AVAILABLE
        }
        self.assertEqual(set(TRACE_GENERATORS.keys()), available_methods)

    def test_unavailable_methods_raise_error(self):
        unavailable_ids = [
            "QUAD_FACTORIZATION_Q",
            "QUAD_FACTORIZATION_R",
            "QUAD_COMPLETE_SQUARE",
            "QUAD_VIETE_SUM_PRODUCT",
            "QUAD_GRAPHICAL_ANALYSIS",
        ]
        for m_id in unavailable_ids:
            with self.assertRaises(TraceMethodUnavailableError):
                get_trace_generator(m_id)

    def test_unknown_method_raises_error(self):
        with self.assertRaises(TraceMethodUnavailableError):
            get_trace_generator("NON_EXISTENT_METHOD")

    def test_gateway_function_delegation(self):
        a = Rational(1, 1)
        b = Rational(-5, 1)
        c = Rational(6, 1)
        trace = generate_solution_trace("QUAD_FORMULA_STANDARD", a, b, c)
        self.assertEqual(trace.method_id, "QUAD_FORMULA_STANDARD")
        self.assertEqual(trace.solution_outcome, SolutionOutcome.TWO_DISTINCT_REAL_ROOTS)


class TestAdversarialTraceInputsAndInvariants(unittest.TestCase):
    """Adversarial input, type purity, and deterministic invariant tests."""

    def test_reject_float_a(self):
        with self.assertRaises(TypeError):
            generate_solution_trace("QUAD_FORMULA_STANDARD", 1.0, Rational(-5, 1), Rational(6, 1))  # type: ignore

    def test_reject_float_b(self):
        with self.assertRaises(TypeError):
            generate_solution_trace("QUAD_FORMULA_STANDARD", Rational(1, 1), -5.0, Rational(6, 1))  # type: ignore

    def test_reject_float_c(self):
        with self.assertRaises(TypeError):
            generate_solution_trace("QUAD_FORMULA_STANDARD", Rational(1, 1), Rational(-5, 1), 6.0)  # type: ignore

    def test_reject_string_input(self):
        with self.assertRaises(TypeError):
            generate_solution_trace("QUAD_FORMULA_STANDARD", "1", Rational(-5, 1), Rational(6, 1))  # type: ignore

    def test_reject_raw_int(self):
        with self.assertRaises(TypeError):
            generate_solution_trace("QUAD_FORMULA_STANDARD", 1, Rational(-5, 1), Rational(6, 1))  # type: ignore

    def test_reject_zero_a(self):
        with self.assertRaises(TraceInvalidInputError) as ctx:
            generate_solution_trace("QUAD_FORMULA_STANDARD", Rational(0, 1), Rational(2, 1), Rational(3, 1))
        self.assertIn("Leading coefficient 'a' cannot be zero", str(ctx.exception))

    def test_deterministic_model_dump(self):
        a = Rational(2, 3)
        b = Rational(-5, 7)
        c = Rational(-1, 4)
        trace1 = generate_solution_trace("QUAD_FORMULA_STANDARD", a, b, c)
        trace2 = generate_solution_trace("QUAD_FORMULA_STANDARD", a, b, c)

        self.assertEqual(trace1.model_dump(), trace2.model_dump())


if __name__ == "__main__":
    unittest.main()
