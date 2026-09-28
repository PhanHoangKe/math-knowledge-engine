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

import time
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


class TestProduct03BR1SoundnessAndCounterexamples:
    """Test suite for P03B-R1 Counterexamples A-E and Domain Soundness."""

    def test_counterexample_a_strict_inequality_variable_denominator(self, router: EngineRouter):
        """Counterexample A: (x-1)/(x-1) > 0 must be rejected with OUT_OF_SCOPE, not (-oo, oo)."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="(x-1)/(x-1) > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "variable denominators" in res.error_message or "out of scope" in res.error_message

    def test_counterexample_b_nonstrict_inequality_variable_denominator(self, router: EngineRouter):
        """Counterexample B: (x-1)/(x-1) >= 0 must be rejected with OUT_OF_SCOPE, not (-oo, oo)."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="(x-1)/(x-1) >= 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "variable denominators" in res.error_message or "out of scope" in res.error_message

    def test_counterexample_c_system_variable_denominator(self, router: EngineRouter):
        """Counterexample C: (x-1)/(x-1) = 1, y = 2 must be rejected with OUT_OF_SCOPE."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="(x-1)/(x-1) = 1, y = 2",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "variable denominators" in res.error_message or "out of scope" in res.error_message

    def test_counterexample_d_linear_system_success(self, router: EngineRouter):
        """Counterexample D: 2*x + 3*y = 5, x - y = 1 returns SUCCESS (x = 8/5, y = 3/5)."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="2*x + 3*y = 5, x - y = 1",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert "x = 8/5" in res.symbolic_result
        assert "y = 3/5" in res.symbolic_result
        assert res.verification_evidence["system_type"] == "unique"

    def test_counterexample_e_quadratic_inequality_success(self, router: EngineRouter):
        """Counterexample E: x^2 - 4 > 0 returns SUCCESS ((-oo, -2) U (2, oo))."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x^2 - 4 > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "(-oo, -2) U (2, oo)"
        assert res.domain_certainty == DomainCertainty.PROVEN_REALS

    def test_domain_certainty_univariate_rational_point_exclusions(self, router: EngineRouter):
        """Single point exclusions yield EXPLICIT_EXCLUSIONS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x^2 - 1)/(x - 1)",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.domain_certainty == DomainCertainty.EXPLICIT_EXCLUSIONS
        assert "x != 1" in res.domain_restrictions

    def test_domain_certainty_multivariate_denominator_not_fully_determined(self):
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import assess_domain_certainty, extract_domain_restrictions
        ast = parse_cas_expression("(x + y) / (x - y)")
        restrictions = extract_domain_restrictions(ast)
        certainty = assess_domain_certainty(ast, restrictions)
        assert certainty == "NOT_FULLY_DETERMINED"

    def test_domain_certainty_none_ast_not_fully_determined(self):
        from mke_product.cas.safety import assess_domain_certainty
        certainty = assess_domain_certainty(None, [])
        assert certainty == "NOT_FULLY_DETERMINED"

    def test_solve_system_reject_original_ast_variable_bypass(self, router: EngineRouter):
        """x + 0*z = 1, y = 2 has 3 variables in original AST; must be OUT_OF_SCOPE."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_SYSTEM,
            raw_input="x + 0*z = 1, y = 2",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "3 variables in original input" in res.error_message or "out of scope" in res.error_message

    def test_solve_inequality_reject_original_ast_variable_bypass(self, router: EngineRouter):
        """x - x + y > 0 has 2 variables in original AST; must be OUT_OF_SCOPE."""
        req = ExecutionRequest(
            operation=OperationType.SOLVE_INEQUALITY,
            raw_input="x - x + y > 0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.OUT_OF_SCOPE
        assert "2 variables in original input" in res.error_message or "out of scope" in res.error_message

    def test_domain_certainty_reducible_quadratic_denominator(self):
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import assess_domain_certainty, extract_domain_restrictions
        ast = parse_cas_expression("1 / (x^2 - 4)")
        restrictions = extract_domain_restrictions(ast)
        certainty = assess_domain_certainty(ast, restrictions)
        assert certainty == "EXPLICIT_EXCLUSIONS"
        assert "x != -2" in restrictions
        assert "x != 2" in restrictions

    def test_domain_certainty_irreducible_quadratic_denominator_proven_reals(self):
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import assess_domain_certainty, extract_domain_restrictions
        ast = parse_cas_expression("1 / (x^2 + 1)")
        restrictions = extract_domain_restrictions(ast)
        certainty = assess_domain_certainty(ast, restrictions)
        assert certainty == "PROVEN_REALS"
        assert restrictions == []

    def test_domain_certainty_irrational_quadratic_roots_not_fully_determined(self):
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import assess_domain_certainty, extract_domain_restrictions
        ast = parse_cas_expression("1 / (x^2 - 2)")
        restrictions = extract_domain_restrictions(ast)
        certainty = assess_domain_certainty(ast, restrictions)
        assert certainty == "NOT_FULLY_DETERMINED"

    def test_domain_certainty_cubic_denominator_not_fully_determined(self):
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import assess_domain_certainty, extract_domain_restrictions
        ast = parse_cas_expression("1 / (x^3 - 1)")
        restrictions = extract_domain_restrictions(ast)
        certainty = assess_domain_certainty(ast, restrictions)
        assert certainty == "NOT_FULLY_DETERMINED"

    def test_zero_power_composite_linear_base_explicit_exclusions(self, router: EngineRouter):
        """(x-1)^0 has domain restriction x != 1 and must receive EXPLICIT_EXCLUSIONS, never PROVEN_REALS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x - 1)^0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "1"
        assert res.domain_certainty == DomainCertainty.EXPLICIT_EXCLUSIONS
        assert "x != 1" in res.domain_restrictions

    def test_zero_power_identically_zero_base_domain_error(self, router: EngineRouter):
        """(x-x)^0 is 0^0 everywhere and must return DOMAIN_ERROR / INVALID_INPUT."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x - x)^0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status in {EngineStatus.DOMAIN_ERROR, EngineStatus.INVALID_INPUT}
        assert res.verification_status == VerificationStatus.ERROR
        assert "0^0" in res.error_message or "undefined" in res.error_message.lower()

    def test_zero_power_variable_base_explicit_exclusions(self, router: EngineRouter):
        """x^0 has domain restriction x != 0 and receives EXPLICIT_EXCLUSIONS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="x^0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "1"
        assert res.domain_certainty == DomainCertainty.EXPLICIT_EXCLUSIONS
        assert "x != 0" in res.domain_restrictions

    def test_zero_power_irreducible_quadratic_base_proven_reals(self, router: EngineRouter):
        """(x^2+1)^0 has no real zeros (x^2+1 >= 1 > 0) and receives PROVEN_REALS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x^2 + 1)^0",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "1"
        assert res.domain_certainty == DomainCertainty.PROVEN_REALS
        assert res.domain_restrictions == []

    def test_division_by_identically_zero_expression_domain_error(self, router: EngineRouter):
        """1/(x-x) is division by zero everywhere and must return DOMAIN_ERROR / INVALID_INPUT."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="1 / (x - x)",
            options={"in_process": True},
        )
        res = router.execute(req)
        assert res.mathematical_status in {EngineStatus.DOMAIN_ERROR, EngineStatus.INVALID_INPUT}
        assert res.verification_status == VerificationStatus.ERROR
        assert "zero" in res.error_message.lower()

    # -------------------------------------------------------------------------
    # Supervised Child-Process & Pre-Dispatch Resource Isolation Tests
    # -------------------------------------------------------------------------
    def test_supervised_zero_power_composite_linear_base_explicit_exclusions(self, router: EngineRouter):
        """Supervised child worker execution of (x-1)^0 yields EXPLICIT_EXCLUSIONS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x - 1)^0",
            timeout_sec=5.0,
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "1"
        assert res.domain_certainty == DomainCertainty.EXPLICIT_EXCLUSIONS
        assert "x != 1" in res.domain_restrictions

    def test_supervised_zero_power_identically_zero_base_domain_error(self, router: EngineRouter):
        """Supervised child worker execution of (x-x)^0 yields DOMAIN_ERROR."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x - x)^0",
            timeout_sec=5.0,
        )
        res = router.execute(req)
        assert res.mathematical_status in {EngineStatus.DOMAIN_ERROR, EngineStatus.INVALID_INPUT}
        assert res.verification_status == VerificationStatus.ERROR

    def test_supervised_division_by_identically_zero_domain_error(self, router: EngineRouter):
        """Supervised child worker execution of 1/(x-x) yields DOMAIN_ERROR."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="1 / (x - x)",
            timeout_sec=5.0,
        )
        res = router.execute(req)
        assert res.mathematical_status in {EngineStatus.DOMAIN_ERROR, EngineStatus.INVALID_INPUT}
        assert res.verification_status == VerificationStatus.ERROR

    def test_supervised_zero_power_irreducible_quadratic_base_proven_reals(self, router: EngineRouter):
        """Supervised child worker execution of (x^2+1)^0 yields PROVEN_REALS."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="(x^2 + 1)^0",
            timeout_sec=5.0,
        )
        res = router.execute(req)
        assert res.mathematical_status == EngineStatus.SUCCESS
        assert res.symbolic_result == "1"
        assert res.domain_certainty == DomainCertainty.PROVEN_REALS

    def test_pre_dispatch_inspect_ast_safety_zero_symbolic_evaluations(self):
        """Verify pre-dispatch inspect_ast_safety never calls sympy.simplify or sympy.solve on variable subtrees."""
        from unittest.mock import patch
        import sympy
        from mke_product.cas.cas_parser import parse_cas_expression
        from mke_product.cas.safety import inspect_ast_safety

        def forbidden_simplify(*args, **kwargs):
            raise AssertionError("sympy.simplify called in pre-dispatch inspect_ast_safety!")

        def forbidden_solve(*args, **kwargs):
            raise AssertionError("sympy.solve called in pre-dispatch inspect_ast_safety!")

        with patch.object(sympy, "simplify", side_effect=forbidden_simplify), \
             patch.object(sympy, "solve", side_effect=forbidden_solve):
            # None of these should invoke sympy.simplify or sympy.solve during pre-dispatch AST safety inspection
            inspect_ast_safety(parse_cas_expression("(x - 1)^0"))
            inspect_ast_safety(parse_cas_expression("(x - x)^0"))
            inspect_ast_safety(parse_cas_expression("1 / (x - x)"))
            inspect_ast_safety(parse_cas_expression("(x^2 + 1)^0"))
            inspect_ast_safety(parse_cas_expression("x^0"))

    def test_supervisor_hard_timeout_evasion_prevention(self, router: EngineRouter):
        """Verify slow symbolic computations running in child worker are strictly terminated by supervisor."""
        req = ExecutionRequest(
            operation=OperationType.SIMPLIFY,
            raw_input="x^2 + x",
            options={"sleep_seconds": 1.5},
            timeout_sec=0.3,
        )
        start_t = time.monotonic()
        res = router.execute(req)
        elapsed = time.monotonic() - start_t
        assert elapsed < 1.2, f"Supervisor hung for {elapsed:.2f}s, expected termination around 0.3s"
        assert res.mathematical_status == EngineStatus.RESOURCE_EXHAUSTED
        assert "timed out" in res.error_message.lower()



