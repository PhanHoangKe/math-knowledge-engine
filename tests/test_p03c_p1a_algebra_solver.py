"""Unit tests for P03C-P1A algebraic solver extensions (Radical, Rational, and Absolute Value Equations)."""

import unittest
from mke_product.cas.contracts import (
    EngineStatus,
    ExecutionRequest,
    OperationType,
    VerificationStatus,
)
from mke_product.cas.router import CASRouter


class TestP03CP1AAlgebraSolver(unittest.TestCase):
    """Test algebraic equation solving, root validation, and extraneous root elimination."""

    def setUp(self):
        self.router = CASRouter()

    def test_radical_equation_single_extraneous_elimination(self):
        # sqrt(x + 3) = x + 1 => algebraic squaring gives x=1, x=-2.
        # At x=-2: LHS = sqrt(1) = 1 != -1. Extraneous root -2 must be rejected!
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(x + 3) = x + 1",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{1}")
        self.assertEqual(res.solution_set, ["1"])
        self.assertIn("extraneous_roots", res.verification_evidence)
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["-2"])

    def test_radical_equation_quadratic_under_radical_extraneous_elimination(self):
        # sqrt(3*x^2 - 9*x + 1) = x - 2 => squaring: 2x^2 - 5x - 3 = 0 => x=3, x=-1/2.
        # At x=-1/2: RHS = -5/2 < 0. Extraneous root -1/2 must be rejected!
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(3*x^2 - 9*x + 1) = x - 2",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{3}")
        self.assertEqual(res.solution_set, ["3"])
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["-1/2"])

    def test_dual_radical_equation_negative_radicand_elimination(self):
        # sqrt(2*x^2 - 5*x - 9) = sqrt(x^2 - 2*x - 5) => x^2 - 3x - 4 = 0 => x=4, x=-1.
        # At x=-1: radicand 2(1) - 5(-1) - 9 = -2 < 0. Extraneous root -1 must be rejected!
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(2*x^2 - 5*x - 9) = sqrt(x^2 - 2*x - 5)",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{4}")
        self.assertEqual(res.solution_set, ["4"])
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["-1"])

    def test_radical_equation_no_real_solution(self):
        # sqrt(2*x - 1) = sqrt(x - 4) => x = -3 => radicands < 0 => empty set
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(2*x - 1) = sqrt(x - 4)",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{}")
        self.assertEqual(res.solution_set, [])
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["-3"])

    def test_rational_equation_division_by_zero_elimination(self):
        # (x^2 - 4)/(x - 2) = 4 => cross multiply gives x=2, but x=2 causes 0/0.
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="(x^2 - 4) / (x - 2) = 4",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{}")
        self.assertEqual(res.solution_set, [])
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["2"])

    def test_rational_equation_valid_root(self):
        # (x^2 - 3*x)/(x - 3) = 2 => x=2. x=2 is valid!
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="(x^2 - 3*x) / (x - 3) = 2",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{2}")
        self.assertEqual(res.solution_set, ["2"])

    def test_absolute_value_equation_two_roots(self):
        # |2*x - 3| = x + 1 => x = 4, x = 2/3.
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="|2*x - 3| = x + 1",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(set(res.solution_set), {"2/3", "4"})

    def test_absolute_value_equation_extraneous_root(self):
        # |x - 5| = 2*x - 4 => x = 3, x = -1.
        # At x=-1: RHS = -6 < 0. Extraneous root -1 must be rejected!
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="|x - 5| = 2*x - 4",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{3}")
        self.assertEqual(res.solution_set, ["3"])
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["-1"])

    def test_absolute_value_negative_rhs_no_solution(self):
        # |x - 2| = -3 => empty set
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="|x - 2| = -3",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{}")
        self.assertEqual(res.solution_set, [])

    def test_radical_calculus_differentiation(self):
        # d/dx(sqrt(x)) = 1/(2*sqrt(x))
        req = ExecutionRequest(
            operation=OperationType.DIFFERENTIATE,
            expression="sqrt(x)",
            variable="x",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIn("1/(2*sqrt(x))", res.symbolic_result)

    def test_radical_calculus_definite_integration(self):
        # integrate(sqrt(x), x=0..4) = 16/3
        req = ExecutionRequest(
            operation=OperationType.INTEGRATE,
            expression="sqrt(x)",
            variable="x",
            options={"lower": 0, "upper": 4, "in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "16/3")

    def test_exact_root_validation_tiny_epsilon_counterexample(self):
        # sqrt(x^2) = x - 1/1000000000000 => squaring gives x = 1/2000000000000.
        # But for x > 0: sqrt(x^2) = x != x - 10^-12.
        # With exact symbolic evaluation, this must yield EMPTY solution set.
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(x^2) = x - 1/1000000000000",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{}")
        self.assertEqual(res.solution_set, [])
        self.assertIn("extraneous_roots", res.verification_evidence)
        self.assertEqual(res.verification_evidence["extraneous_roots"], ["1/2000000000000"])

    def test_domain_preserving_identity_radical(self):
        # sqrt(x) = sqrt(x) => domain is [0, oo), NOT "All real numbers except x >= 0"
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(x) = sqrt(x)",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "[0, oo)")
        self.assertNotIn("All real numbers except", res.symbolic_result)

    def test_domain_preserving_identity_radical_and_rational(self):
        # sqrt(x - 2)/(x - 5) = sqrt(x - 2)/(x - 5) => domain is [2, 5) U (5, oo)
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="sqrt(x - 2) / (x - 5) = sqrt(x - 2) / (x - 5)",
            options={"in_process": True},
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertIn("[2, 5)", res.symbolic_result)
        self.assertIn("(5, oo)", res.symbolic_result)

    def test_injected_identity_domain_calculation_failure_fails_closed(self):
        from unittest.mock import patch
        from mke_product.cas.contracts import DomainCertainty
        with patch("sympy.solveset", side_effect=RuntimeError("Injected CAS failure")):
            req = ExecutionRequest(
                operation=OperationType.SOLVE,
                expression="sqrt(x) = sqrt(x)",
                options={"in_process": True},
            )
            res = self.router.execute(req)
            self.assertEqual(res.status, EngineStatus.UNRESOLVED)
            self.assertEqual(res.verification_status, VerificationStatus.UNRESOLVED)
            self.assertEqual(res.domain_certainty, DomainCertainty.NOT_FULLY_DETERMINED)

    def test_injected_conditionset_identity_domain_fails_closed(self):
        from unittest.mock import patch
        import sympy
        from mke_product.cas.contracts import DomainCertainty
        x = sympy.Symbol("x", real=True)
        unresolved_set = sympy.ConditionSet(x, sympy.Eq(x, 1), sympy.S.Reals)
        with patch("sympy.solveset", return_value=unresolved_set):
            req = ExecutionRequest(
                operation=OperationType.SOLVE,
                expression="sqrt(x) = sqrt(x)",
                options={"in_process": True},
            )
            res = self.router.execute(req)
            self.assertEqual(res.status, EngineStatus.UNRESOLVED)
            self.assertEqual(res.verification_status, VerificationStatus.UNRESOLVED)
            self.assertEqual(res.domain_certainty, DomainCertainty.NOT_FULLY_DETERMINED)


if __name__ == "__main__":
    unittest.main()


