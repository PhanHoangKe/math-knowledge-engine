"""Integration tests for P03C-P1A algebraic operations over CASRouter and supervised process execution."""

import unittest
from mke_product.cas.contracts import (
    EngineStatus,
    ExecutionRequest,
    OperationType,
    VerificationStatus,
)
from mke_product.cas.router import CASRouter


class TestP03CP1AAPIIntegration(unittest.TestCase):
    """Test supervised execution and envelope serialization for P1A features."""

    def setUp(self):
        self.router = CASRouter()

    def test_supervised_radical_solve(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression=r"\sqrt{x + 3} = x + 1",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{1}")
        d = res.to_dict()
        self.assertEqual(d["mathematical_status"], "SUCCESS")
        self.assertIn("verification_evidence", d)
        self.assertEqual(d["verification_evidence"]["extraneous_roots"], ["-2"])

    def test_supervised_absolute_value_solve(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="|3*x - 2| = x + 4",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(set(res.solution_set), {"-1/2", "3"})

    def test_supervised_rational_equation_solve(self):
        req = ExecutionRequest(
            operation=OperationType.SOLVE,
            expression="(2*x + 1) / (x - 1) = 3",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.SUCCESS)
        self.assertEqual(res.symbolic_result, "{4}")

    def test_constant_negative_radical_rejection(self):
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            expression="sqrt(0 - 9)",
        )
        res = self.router.execute(req)
        self.assertEqual(res.status, EngineStatus.DOMAIN_ERROR)


if __name__ == "__main__":
    unittest.main()
