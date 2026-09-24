"""DATN — DEV-01-R2 Independent Verification Script.

Automated recheck script for the Coordinator to verify the 5 critical mathematical soundness
and AST preservation remediations in DEV-01-R2.
"""

from fractions import Fraction
import sys
import sympy

from mke.models.domain import OriginalDomain, is_proven_real_number
from mke.models.enums import (
    MethodId,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    TransferValidity,
)
from mke.parsing import (
    Parser,
    ParserLimits,
    normalize_equation,
)
from mke.verification.engine import VerificationEngine
from mke.verification.transfer import audit_solution_transfer


def run_all_checks() -> bool:
    print("=" * 80)
    print("DATN DEV-01-R2: INDEPENDENT MATHEMATICAL SOUNDNESS RECHECK")
    print("=" * 80)

    engine = VerificationEngine()
    passed_count = 0
    total_checks = 6

    # --------------------------------------------------------------------------
    # Check 1: M4 Completeness & Solveset Handling on Quartic Rational
    # --------------------------------------------------------------------------
    print("\n[CHECK 1/6] M4 Solveset Handling: (x^4 - x - 1) / (x^2 + 1) = 0")
    res1 = engine.verify("(x^4 - x - 1) / (x^2 + 1) = 0")
    c1_ok = (
        res1.method_instance is not None
        and res1.method_instance.method_id == MethodId.M4_RATIONAL_EQUATION
        and res1.is_verified_method is True
        and res1.is_verified_solution is False  # Must NOT grant verified solution!
        and res1.solution_status == SolutionProofStatus.SOUND_PARTIAL
        and len(res1.verified_roots) == 2  # Must find the 2 real roots, NOT conclude empty set!
        and any(o.obligation_id == ObligationId.COMPLETENESS and o.status == ObligationStatus.UNRESOLVED for o in res1.obligations)
    )
    if c1_ok:
        print("  PASS: Found 2 real roots, COMPLETENESS=UNRESOLVED, is_verified_solution=False, status=SOUND_PARTIAL.")
        passed_count += 1
    else:
        print(f"  FAIL: is_verified_solution={res1.is_verified_solution}, roots={res1.verified_roots}, status={res1.solution_status}")

    # --------------------------------------------------------------------------
    # Check 2: M4 Truly Empty Real Roots vs Completeness
    # --------------------------------------------------------------------------
    print("\n[CHECK 2/6] M4 Truly Empty Root Proof: (x^4 + 1) / (x^2 + 1) = 0")
    res2 = engine.verify("(x^4 + 1) / (x^2 + 1) = 0")
    c2_ok = (
        res2.is_verified_method is True
        and res2.is_verified_solution is True
        and res2.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
        and len(res2.verified_roots) == 0
        and any(o.obligation_id == ObligationId.COMPLETENESS and o.status == ObligationStatus.PASS for o in res2.obligations)
    )
    if c2_ok:
        print("  PASS: Formally proved empty set on R, COMPLETENESS=PASS, is_verified_solution=True.")
        passed_count += 1
    else:
        print(f"  FAIL: is_verified_solution={res2.is_verified_solution}, status={res2.solution_status}")

    # --------------------------------------------------------------------------
    # Check 3: Real Domain & Solution Transfer Rejection of Complex / Symbols
    # --------------------------------------------------------------------------
    print("\n[CHECK 3/6] Real Domain & Transfer Rejection: target x^2 + 1 = 0, candidate sympy.I")
    eq3 = normalize_equation(Parser.from_text("x^2 + 1 = 0").parse_equation())
    val3, valid3, rej3 = audit_solution_transfer(eq3, [sympy.I, 1 + 2*sympy.I, sympy.Symbol("y")])
    c3_ok = (
        val3 == TransferValidity.UNSAFE_COPY
        and len(valid3) == 0
        and len(rej3) == 3
        and not OriginalDomain().contains(sympy.I)
        and not OriginalDomain().contains(sympy.Symbol("x"))
    )
    if c3_ok:
        print("  PASS: sympy.I and free variables strictly rejected as UNSAFE_COPY. OriginalDomain.contains() returns False.")
        passed_count += 1
    else:
        print(f"  FAIL: TransferValidity={val3}, valid={valid3}, rejected={rej3}")

    # --------------------------------------------------------------------------
    # Check 4: Consistent Verification State on Empty Domain
    # --------------------------------------------------------------------------
    print("\n[CHECK 4/6] Empty Domain State Consistency: x / 0 = 0")
    res4 = engine.verify("x / 0 = 0")
    c4_ok = (
        res4.method_instance is None
        and res4.is_verified_method is False  # Must be False: no method applied!
        and res4.is_verified_solution is True  # Empty solution set proven by domain
        and res4.solution_status == SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
        and len(res4.verified_roots) == 0
    )
    if c4_ok:
        print("  PASS: is_verified_method=False, is_verified_solution=True, method_instance=None. Proven purely by domain evidence.")
        passed_count += 1
    else:
        print(f"  FAIL: is_verified_method={res4.is_verified_method}, is_verified_solution={res4.is_verified_solution}, method={res4.method_instance}")

    # --------------------------------------------------------------------------
    # Check 5: Resource Limit & Scope Error Classification
    # --------------------------------------------------------------------------
    print("\n[CHECK 5/6] Resource Limits & Error Classification")
    res_lim1 = VerificationEngine(limits=ParserLimits(max_input_length=10)).verify("x + 123456789 = 0")
    res_lim2 = VerificationEngine().verify("x^5 = 0")
    res_scope = VerificationEngine().verify("sin(x) = 0")
    res_syntax = VerificationEngine().verify("x + = 0")
    c5_ok = (
        "RESOURCE_LIMIT: InputLengthExceededError" in res_lim1.explanation
        and "RESOURCE_LIMIT: InvalidExponentError" in res_lim2.explanation
        and "OUT_OF_SCOPE" in res_scope.explanation
        and "SYNTAX_ERROR" in res_syntax.explanation
        and not any(r.is_verified_solution for r in [res_lim1, res_lim2, res_scope, res_syntax])
    )
    if c5_ok:
        print("  PASS: Structured classification for RESOURCE_LIMIT, OUT_OF_SCOPE, and SYNTAX_ERROR verified without false verification.")
        passed_count += 1
    else:
        print("  FAIL: Resource/scope classification mismatch.")

    # --------------------------------------------------------------------------
    # Check 6: AST Round-trip Structure Preservation
    # --------------------------------------------------------------------------
    print("\n[CHECK 6/6] AST Round-trip Structure Preservation")
    test_eqs = ["1 + (x - 2) = 0", "x + 0.25 = 0", "x * (x / 2) = 0"]
    c6_ok = True
    for eq in test_eqs:
        ast_orig = Parser.from_text(eq).parse_equation()
        math_str = ast_orig.to_math_string()
        ast_reparsed = Parser.from_text(math_str).parse_equation()
        if ast_orig != ast_reparsed:
            print(f"  FAIL on '{eq}': rendered '{math_str}', AST mismatch!")
            c6_ok = False
            break
    if c6_ok:
        print(f"  PASS: All round-trip cases preserved exact AST trees: {test_eqs}")
        passed_count += 1

    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed_count}/{total_checks} independent recheck suites PASSED.")
    print("=" * 80)
    return passed_count == total_checks


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
