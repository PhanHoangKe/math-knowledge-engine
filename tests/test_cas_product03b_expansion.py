"""
Comprehensive test suite for MKE PRODUCT-03B Mathematical Expansion (v0).
Covers:
1. SOLVE_SYSTEM (2x2 linear equation systems with rational coefficients)
   - Unique solution
   - Inconsistent / No solution (EmptySet)
   - Dependent / Infinitely many solutions (Parametric)
   - Non-linear rejection (OUT_OF_SCOPE)
   - Multivariate (>2 variables) rejection (OUT_OF_SCOPE)
   - Malicious pattern rejection
2. SOLVE_INEQUALITY (Single-variable polynomial inequalities with degree <= 2)
   - Linear inequalities (<, <=, >, >=, ≤, ≥)
   - Quadratic inequalities (2 real roots, 1 root, no real roots)
   - Strict vs non-strict intervals
   - Union of intervals
   - Full reals / Empty set solutions
   - Higher degree (>2) rejection (OUT_OF_SCOPE)
   - Multivariate inequality rejection (OUT_OF_SCOPE)
3. AST Safety & Supervised Process Execution
4. Domain certainty & honest verification status contracts
"""

import pytest
import sympy

from mke_product.cas.contracts import (
    DomainCertainty,
    EngineStatus,
    ExecutionRequest,
    OperationType,
    VerificationStatus,
)
from mke_product.cas.router import EngineRouter


@pytest.fixture
def router() -> EngineRouter:
    return EngineRouter()


class TestProduct03BLinearSystem:
    """Test suite for SOLVE_SYSTEM operation (2x2 linear systems)."""

    def test_solve_system_unique_integer_solution(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x + y = 10, x - y = 2",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "x = 6, y = 4"
        assert res.verification_evidence is not None
        assert res.verification_evidence["system_type"] == "unique"
        assert res.verification_evidence["solution"] == {"x": "6", "y": "4"}
        assert res.domain_certainty == DomainCertainty.PROVEN_REALS
        assert res.verification_status == VerificationStatus.COMPUTED

    def test_solve_system_unique_rational_solution(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="2*x + 3*y = 5, x - y = 1",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert "x = 8/5" in res.symbolic_result
        assert "y = 3/5" in res.symbolic_result
        assert "\\frac{8}{5}" in res.latex_output
        assert "\\frac{3}{5}" in res.latex_output
        assert res.verification_evidence["system_type"] == "unique"

    def test_solve_system_inconsistent_empty_solution(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x + y = 1, x + y = 2",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert "No solution" in res.symbolic_result
        assert "Inconsistent system" in res.symbolic_result
        assert res.latex_output == "\\emptyset"
        assert res.verification_evidence["system_type"] == "inconsistent"
        assert res.solution_set == []

    def test_solve_system_dependent_infinitely_many_solutions(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x + y = 2, 2*x + 2*y = 4",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert "Infinitely many solutions" in res.symbolic_result
        assert res.verification_evidence["system_type"] == "dependent"

    def test_solve_system_reject_nonlinear_quadratic(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x^2 + y = 1, x - y = 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "Non-linear" in res.error_message or "out of scope" in res.error_message

    def test_solve_system_reject_three_variables(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x + y + z = 1, x - y = 2",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "maximum 2 variables" in res.error_message

    def test_solve_system_with_negative_coefficients_and_fractions(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="-3*x + 4*y = 11, 2*x - y = -4",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "x = -1, y = 2"


class TestProduct03BInequality:
    """Test suite for SOLVE_INEQUALITY operation (degree <= 2 polynomial inequalities)."""

    def test_solve_linear_inequality_less_equal(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="2*x + 3 <= 7",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "(-oo, 2]"
        assert "\\left(-\\infty, 2\\right]" in res.latex_output
        assert res.domain_certainty == DomainCertainty.PROVEN_REALS
        assert res.verification_status == VerificationStatus.COMPUTED

    def test_solve_linear_inequality_strict_greater(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="3*x - 9 > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "(3, oo)"
        assert "\\left(3, \\infty\\right)" in res.latex_output

    def test_solve_quadratic_inequality_two_intervals_union(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 - 4 > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "(-oo, -2) U (2, oo)"
        assert "\\left(-\\infty, -2\\right) \\cup \\left(2, \\infty\\right)" in res.latex_output

    def test_solve_quadratic_inequality_closed_interval(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 - 4 <= 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "[-2, 2]"
        assert "\\left[-2, 2\\right]" in res.latex_output

    def test_solve_quadratic_inequality_always_true(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 + 1 > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "(-oo, oo)"
        assert res.latex_output == "\\mathbb{R}"

    def test_solve_quadratic_inequality_always_false_empty_set(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 + 1 < 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "No real solution"
        assert res.latex_output == "\\emptyset"
        assert res.solution_set == []

    def test_solve_inequality_unicode_operators(self, router: EngineRouter):
        req1 = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="2*x + 3 ≤ 7",
            options={"in_process": True},
        )
        res1 = router.execute(req1)
        assert res1.mathematical_status == EngineStatus.SUCCESS
        assert res1.symbolic_result == "(-oo, 2]"

        req2 = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="2*x - 4 ≥ 0",
            options={"in_process": True},
        )
        res2 = router.execute(req2)
        assert res2.mathematical_status == EngineStatus.SUCCESS
        assert res2.symbolic_result == "[2, oo)"

    def test_solve_inequality_reject_cubic_degree_three(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^3 - 4*x > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "degree 3 > 2 are out of scope" in res.error_message

    def test_solve_inequality_reject_multivariate(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x + y > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "Multivariate inequalities" in res.error_message


class TestProduct03BSupervisedWorker:
    """Verify supervised subprocess execution runner handles new operations with hard timeout."""

    def test_supervised_system_solve(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="2*x + 3*y = 5, x - y = 1",
            options={"in_process": False, "timeout_sec": 5.0},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert "x = 8/5" in res.symbolic_result
        assert res.selected_engine == "sympy_cas_v0"

    def test_supervised_inequality_solve(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 - 4 <= 0",
            options={"in_process": False, "timeout_sec": 5.0},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "[-2, 2]"
        assert res.selected_engine == "sympy_cas_v0"


class TestProduct03BSecurityAndIntegrity:
    """Security tests against malicious injections on expanded operations."""

    def test_reject_forbidden_python_patterns(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="__import__('os').system('dir'), x = 1",
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SECURITY_REJECTED
        assert res.verification_status == VerificationStatus.ERROR

    def test_reject_eval_in_inequality(self, router: EngineRouter):
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="eval('x') > 0",
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SECURITY_REJECTED
