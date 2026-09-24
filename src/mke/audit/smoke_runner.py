"""Smoke test suite execution engine."""

import json
from pathlib import Path
import time
from typing import Any, Dict, List
import sympy

from mke.methods.catalogue import CATALOGUE
from mke.methods.m3_factorization import audit_division_step
from mke.models.enums import MethodAdmissibility, MethodId, ObligationStatus, TransferValidity
from mke.parsing.parser import Parser
from mke.parsing.normalizer import normalize_equation
from mke.parsing.sympy_converter import X_SYM
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


class SmokeSuiteRunner:
    """Runs the handcrafted smoke test suite independently of production pipelines."""

    def __init__(self, fixtures_path: Path | str | None = None):
        if fixtures_path is None:
            # Default to data/smoke/smoke_fixtures.json
            fixtures_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "smoke" / "smoke_fixtures.json"
        self.fixtures_path = Path(fixtures_path)
        self.engine = VerificationEngine()

    def load_fixtures(self) -> List[Dict[str, Any]]:
        with open(self.fixtures_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_all(self) -> Dict[str, Any]:
        fixtures = self.load_fixtures()
        results: List[Dict[str, Any]] = []
        start_suite = time.perf_counter()

        pass_count = 0
        fail_count = 0

        for fix in fixtures:
            case_res = self.run_case(fix)
            results.append(case_res)
            if case_res["passed"]:
                pass_count += 1
            else:
                fail_count += 1

        total_suite_time = (time.perf_counter() - start_suite) * 1000.0

        return {
            "total_tests": len(fixtures),
            "passed": pass_count,
            "failed": fail_count,
            "skipped": 0,
            "total_execution_time_ms": round(total_suite_time, 2),
            "results": results,
        }

    def run_case(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        cid = fixture["id"]
        eq_text = fixture["equation"]
        start_t = time.perf_counter()

        verification = self.engine.verify(eq_text)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        checks: List[Dict[str, Any]] = []
        overall_passed = True

        # Check 1: Out of scope check (T8)
        if fixture.get("expected_out_of_scope"):
            is_out = "OUT_OF_SCOPE" in verification.explanation or "OUT_OF_SCOPE" in verification.domain_str
            checks.append({"check": "OUT_OF_SCOPE", "passed": is_out, "detail": verification.explanation})
            if not is_out:
                overall_passed = False

        # Check 2: Domain check
        if "expected_domain" in fixture:
            exp_dom = fixture["expected_domain"]
            act_dom = verification.domain_str
            dom_ok = exp_dom == act_dom
            checks.append({"check": "DOMAIN_PRESERVATION", "passed": dom_ok, "expected": exp_dom, "actual": act_dom})
            if not dom_ok:
                overall_passed = False

        # Check 3: Method check
        if "expected_method" in fixture:
            exp_m = fixture["expected_method"]
            act_m = verification.method_instance.method_id.value if verification.method_instance else None
            m_ok = exp_m == act_m
            checks.append({"check": "METHOD_IDENTIFICATION", "passed": m_ok, "expected": exp_m, "actual": act_m})
            if not m_ok:
                overall_passed = False

        # Check 4: Solution roots check
        if "expected_roots" in fixture and not fixture.get("expected_is_identity_on_domain"):
            exp_roots = sorted(fixture["expected_roots"])
            act_roots = sorted(verification.verified_roots)
            roots_ok = exp_roots == act_roots
            checks.append({"check": "VERIFIED_ROOTS", "passed": roots_ok, "expected": exp_roots, "actual": act_roots})
            if not roots_ok:
                overall_passed = False

        # Check 5: Identity on domain check (T3)
        if fixture.get("expected_is_identity_on_domain"):
            ident_ok = verification.is_identity_on_domain
            checks.append({"check": "IDENTITY_ON_DOMAIN", "passed": ident_ok, "actual": ident_ok})
            if not ident_ok:
                overall_passed = False

        # Special Check: T2 transfer test
        if "transfer_test" in fixture:
            t_cfg = fixture["transfer_test"]
            # Reconstruct normalized equation for target
            target_ast = Parser.from_text(eq_text).parse_equation()
            target_norm = normalize_equation(target_ast, raw_text=eq_text)
            trans_res, val_roots, rej_roots = audit_solution_transfer(
                target_norm, t_cfg["copied_roots"], source_problem_id=t_cfg["source_id"]
            )
            trans_ok = (trans_res.value == t_cfg["expected_transfer_validity"]) and any(
                t_cfg["rejected_transferred_root"] in r for r in rej_roots
            )
            checks.append({
                "check": "TRANSFER_AUDIT_UNSAFE_COPY",
                "passed": trans_ok,
                "expected_validity": t_cfg["expected_transfer_validity"],
                "actual_validity": trans_res.value,
                "rejected_roots": rej_roots,
            })
            if not trans_ok:
                overall_passed = False

        # Special Check: T4 division audit test
        if "division_test" in fixture:
            d_cfg = fixture["division_test"]
            # Audit dividing x*(x-1)=0 by x
            orig_poly = sympy.Poly(X_SYM * (X_SYM - 1), X_SYM)
            div_poly = sympy.Poly(X_SYM, X_SYM)
            res_poly = sympy.Poly(X_SYM - 1, X_SYM)
            div_ob = audit_division_step(orig_poly, div_poly, res_poly)
            div_ok = div_ob.status.value == d_cfg["expected_obligation_status"] and div_ob.counterexample is not None
            checks.append({
                "check": "DIVISION_ROOT_LOSS_DETECTION",
                "passed": div_ok,
                "obligation_status": div_ob.status.value,
                "counterexample": div_ob.counterexample,
            })
            if not div_ok:
                overall_passed = False

        # Special Check: T5 M2 leading coefficient a=0 rejection
        if "m2_check" in fixture:
            m2_cfg = fixture["m2_check"]
            m2_method = CATALOGUE.get_method(MethodId.M2_QUADRATIC_FORMULA)
            t5_ast = Parser.from_text(eq_text).parse_equation()
            t5_norm = normalize_equation(t5_ast, raw_text=eq_text)
            m2_adm = m2_method.evaluate_admissibility(t5_norm)
            m2_guards = m2_method.check_mathematical_guards(t5_norm)
            failed_guard = next((g for g in m2_guards if g.guard_name == m2_cfg["failed_guard"]), None)
            m2_ok = (
                m2_adm.value == m2_cfg["expected_admissibility"]
                and failed_guard is not None
                and not failed_guard.passed
            )
            checks.append({
                "check": "M2_A_ZERO_REJECTION",
                "passed": m2_ok,
                "actual_admissibility": m2_adm.value,
                "failed_guard": failed_guard.guard_name if failed_guard else None,
            })
            if not m2_ok:
                overall_passed = False

        # Special Check: T6 biquadratic sign constraint
        if "expected_t_roots" in fixture:
            t_cfg = fixture["expected_t_roots"]
            t_params = verification.method_instance.parameters.get("t_roots", []) if verification.method_instance else []
            t_ok = len(t_params) == len(t_cfg)
            checks.append({
                "check": "SIGN_CONSTRAINT_T_GE_0",
                "passed": t_ok,
                "t_roots_evaluation": t_params,
            })
            if not t_ok:
                overall_passed = False

        return {
            "id": cid,
            "name": fixture["name"],
            "equation": eq_text,
            "passed": overall_passed,
            "duration_ms": round(duration_ms, 2),
            "checks": checks,
            "verification_summary": verification.summary(),
        }
