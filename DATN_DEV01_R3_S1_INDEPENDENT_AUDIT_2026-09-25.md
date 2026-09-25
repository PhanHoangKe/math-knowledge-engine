# DATN — Independent code audit of DEV-01-R3-S1
Audit date: 2026-09-25 (Vietnam).  Decision: CONDITIONAL REJECT; no DEV-02 yet.
Scope: Uploaded math_knowledge_engine_dev01_r3_s1.zip and its test code, plus independent adversarial checks. This is not a formal proof or a deployment-security certification.

## Artifact integrity and independently executed checks
- Uploaded archive SHA-256: e87931dd473598c3aaa7c63e93e66085265ce6073e7a3e1b1adfa2879b30294c — matches handoff.
- Independent audit environment: Python 3.13.5 / SymPy 1.14.0 / pytest 9.0.2, Linux; does not reproduce developer's Windows/Python 3.10 environment.
- Repository: 129/129 pytest PASS.
- Included independent DEV-01-R3 gate: 7/7 PASS.
- Included independent DEV-01-R2 recheck: 6/6 PASS. R2 gate set also reported 7/7 when run.
- Static AST walk detected zero direct sympify, eval, exec, parse_expr calls in src/mke. This does NOT guarantee all input-handling paths are safe.
- New external audit cases: 2 PASS, 3 FAIL. See DATN_DEV01_R3_S1_INDEPENDENT_EDGE_GATES.py and original test log.

## F5: Incorrect EXACT_PASS with lower-precision SymPy Float [HIGH]
Directly reproduce against mke.models.domain.verify_root_exact:
```python
x = sympy.Symbol('x', real=True)
expr = x - sympy.Rational(10**30 + 1, 10**30)   # exact root 1 + 10^-30
candidate = sympy.Float('1.0', 15)             # only an approximation
cert = verify_root_exact(expr, candidate, x)
# Observed: EXACT_PASS, method EXACT_ALGEBRAIC_ZERO; should NOT certify.
```
Root cause: unchecked sympy.Basic candidate permits inexact sympy.Float. expr.subs(x, candidate) rounds the nonzero residual to 0 at the candidate's precision, so the raw_sub == 0 branch incorrectly treats an inexact cancellation as exact algebraic proof. This is a low-level API test with a typed SymPy input, not evidence that the existing text parser generates this counterexample within its configured coefficient bounds. Future H1 imports/retrieved candidates make the trust boundary material.
Required fix: validate exactness/provenance of candidate and all expression coefficients BEFORE calling subs or using raw_sub == 0 as proof. Reject Float and numeric constructs with inexact constituents from EXACT_PASS unless a mathematically justified exact representation has been explicitly reconstructed and verified; approximation-only candidates are UNRESOLVED or a clear unsupported-input state. Apply the rule consistently in the compatibility wrapper, transfer and completeness auditors. Regression should cover this exact example and normal exact-rational positives. Do not mistake conversions such as Rational(str(inexact_value)) for proof that the original approximate value equals the intended exact number.

## F6: Completeness PASS after silently dropping submitted invalid claims [HIGH at external API boundary]
Directly reproduce against mke.verification.completeness.audit_independent_completeness:
```python
norm = normalize_equation(Parser.from_text('x-1=0').parse_equation())
for claimed in [['1', '2'], ['1', 'not_a_root']]:
    ob, cert = audit_independent_completeness(norm, claimed)
    # Observed: COMPLETENESS PASS; cert.verified_roots retains the invalid item!
    # Expected: no PASS for a claimed batch containing an invalid/unverified item.
```
Root cause: the function silently discards failed parsing, domain and exact-verification candidates from internal parsed_verified, compares only the surviving set against canonical roots, yet records ALL original submitted items in cert.verified_roots. An audit certificate can therefore say PASS while attesting a candidate set that includes an invalid root or unparseable text. The previous F2 test supplied only bad roots, so the bug was masked by a missing canonical root. This finding concerns the direct completeness API. The current VerificationEngine passes previously filtered VerifiedRoots to the auditor in its ordinary path; do not claim that this direct-batch bypass is already demonstrated through the user-facing CLI.
Required fix: define the boundary clearly: require validated VerifiedRoot objects, or gate EVERY submitted item and explicitly record rejection(s). A certificate must never label the original submitted set verified if it contains invalid elements. No PASS when any claimed element fails parsing, exact gate, real-domain membership or fingerprint validation. If an adapter filters rejected candidates, its certificate must describe only the trusted filtered subset and expose a non-PASS status for the untrusted original request. Distinguish invalid candidates from merely missing canonical roots in extraneous_roots / a rejection field. Repeat for linear, quadratic and biquadratic branches.

## Acceptance gate (bounded patch; no feature expansion)
1. All original repository tests pass, as do prior external R2/R3 gate scripts.
2. New independent tests F5/F6 pass unchanged; new positive tests for exact rational and legitimate complete candidate sets also pass.
3. Review verify_root_exact, check_root_satisfaction, audit_solution_transfer, audit_independent_completeness to ensure no route into EXACT_PASS bypasses candidate exactness and no certificate reports rejected items as verified.
4. Provide a small threat-model note distinguishing trusted typed internal roots, untrusted imported roots, and approximate numerical outputs. Document unsupported cases and fail closed.
5. Return updated clean source ZIP with SHA-256, original test logs and patch diff; do not claim formal security or universal mathematical correctness. Do not begin DEV-02 before review.
