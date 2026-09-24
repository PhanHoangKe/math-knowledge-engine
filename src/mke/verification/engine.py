"""Comprehensive mathematical verification engine coordinating parsing, domain, methods, and obligations."""

from typing import List, Optional
import sympy

from mke.methods.catalogue import CATALOGUE
from mke.models.enums import (
    MethodAdmissibility,
    MethodId,
    ObligationId,
    ObligationStatus,
    SolutionProofStatus,
    Split,
)
from mke.models.evidence import (
    MethodInstance,
    ProofObligation,
    SolutionCandidate,
    VerificationResult,
)
from mke.models.problem import ProblemRecord
from mke.parsing.exceptions import (
    OutOfScopeSyntaxError,
    ParserError,
)
from mke.parsing.limits import ParserLimits, DEFAULT_LIMITS
from mke.parsing.normalizer import NormalizedEquation, normalize_equation
from mke.parsing.parser import Parser
from mke.parsing.sympy_converter import X_SYM


class VerificationEngine:
    """Verifies algebraic equation solvability, method admissibility, and solution completeness."""

    def __init__(self, limits: ParserLimits = DEFAULT_LIMITS):
        self.limits = limits

    def verify(
        self,
        equation_str: str,
        method_id: Optional[MethodId | str] = None,
    ) -> VerificationResult:
        """Run complete verification pipeline on an equation string."""
        # Step 1: Safe Parsing
        try:
            parser = Parser.from_text(equation_str, limits=self.limits)
            eq_ast = parser.parse_equation()
        except OutOfScopeSyntaxError as e:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str="UNKNOWN (OUT_OF_SCOPE)",
                is_all_reals_domain=False,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"OUT_OF_SCOPE: {e.message}",
            )
        except ParserError as e:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str="UNKNOWN (PARSER_ERROR)",
                is_all_reals_domain=False,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"SYNTAX_OR_LIMIT_ERROR: {e.message}",
            )
        except Exception as e:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str="UNKNOWN",
                is_all_reals_domain=False,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"INTERNAL_PARSER_ERROR: {type(e).__name__}: {str(e)}",
            )

        # Step 2: Normalization and Domain Extraction
        try:
            norm_eq = normalize_equation(eq_ast, raw_text=equation_str, limits=self.limits)
        except OutOfScopeSyntaxError as e:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str="UNKNOWN (OUT_OF_SCOPE)",
                is_all_reals_domain=False,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"OUT_OF_SCOPE: {e.message}",
            )
        except Exception as e:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str="UNKNOWN",
                is_all_reals_domain=False,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"NORMALIZATION_ERROR: {str(e)}",
            )

        domain = norm_eq.domain

        # If domain is empty set (division by zero in original expression), equation has no real solutions
        if domain.is_empty_domain:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str=domain.format_domain(),
                is_all_reals_domain=False,
                excluded_points=[],
                normalization_trace=norm_eq.normalization_trace,
                is_verified_method=True,
                is_verified_solution=True,
                solution_status=SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE,
                verified_roots=[],
                candidate_solutions=[],
                proof_obligations=[
                    ProofObligation(
                        obligation_id=ObligationId.ORIGINAL_DOMAIN,
                        status=ObligationStatus.PASS,
                        description="Check whether original domain contains any real numbers",
                        evidence="Domain is empty set (division by zero detected in expression).",
                    ),
                    ProofObligation(
                        obligation_id=ObligationId.COMPLETENESS,
                        status=ObligationStatus.PASS,
                        description="Completeness of empty solution set on empty domain",
                        evidence="Since the domain has no real points, the solution set is strictly empty on R.",
                    ),
                ],
                explanation="Proven complete on domain: original domain is empty (division by zero in expression), hence no real solutions exist.",
            )

        # Step 3: Select Method
        target_method_id = self._select_method(norm_eq, method_id)
        if target_method_id is None:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str=domain.format_domain(),
                is_all_reals_domain=domain.is_all_reals(),
                excluded_points=[str(v) for v in domain.excluded_values],
                normalization_trace=norm_eq.normalization_trace,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation="No applicable method found in catalogue for equation structure.",
            )

        method = CATALOGUE.get_method(target_method_id)

        # Step 4: Evaluate Guards and Admissibility
        struct_guards = method.check_structural_guards(norm_eq)
        math_guards = method.check_mathematical_guards(norm_eq)
        admissibility = method.evaluate_admissibility(norm_eq)

        method_inst = MethodInstance(
            method_id=method.method_id,
            version=method.version,
            equation_raw=equation_str,
            structural_guards=struct_guards,
            mathematical_guards=math_guards,
            admissibility=admissibility,
            admissibility_reason=f"Structural guards passed: {all(g.passed for g in struct_guards)}; Math guards passed: {all(g.passed for g in math_guards)}",
        )

        is_method_applicable = admissibility in (
            MethodAdmissibility.APPLICABLE,
            MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS,
        )

        if not is_method_applicable:
            return VerificationResult(
                problem_raw=equation_str,
                domain_str=domain.format_domain(),
                is_all_reals_domain=domain.is_all_reals(),
                excluded_points=[str(v) for v in domain.excluded_values],
                normalization_trace=norm_eq.normalization_trace,
                method_instance=method_inst,
                is_verified_method=False,
                is_verified_solution=False,
                solution_status=SolutionProofStatus.UNDETERMINED,
                explanation=f"Method {method.method_id.value} is NOT_APPLICABLE for this equation instance.",
            )

        # Step 5: Solve Instance and Check Proof Obligations
        solve_output = method.solve_instance(norm_eq)
        method_inst.parameters = solve_output.parameters
        obligations = method.check_proof_obligations(norm_eq, solve_output)

        # Step 6: Evaluate Candidate Solutions
        candidate_evals: List[SolutionCandidate] = []
        verified_roots: List[str] = []

        for r in solve_output.candidate_roots:
            in_dom = domain.contains(r)
            sub_res = sympy.simplify(norm_eq.numerator_sym.subs(X_SYM, r))
            sat_eq = bool(sub_res == 0)
            is_valid = in_dom and sat_eq

            if is_valid:
                verified_roots.append(str(r))

            candidate_evals.append(
                SolutionCandidate(
                    value_str=str(r),
                    in_domain=in_dom,
                    satisfies_equation=sat_eq,
                    is_valid_root=is_valid,
                    evidence=f"InDomain={in_dom}, SatisfiesEq={sat_eq} (residue={sub_res})",
                )
            )

        # Step 7: Synthesize Solution Proof Status
        # Crucial Requirement: Distinguish VERIFIED_METHOD from VERIFIED_SOLUTION!
        # Do not emit VERIFIED_SOLUTION without complete proof!
        has_failed_obligation = any(ob.status == ObligationStatus.FAIL for ob in obligations)
        has_unresolved_obligation = any(ob.status == ObligationStatus.UNRESOLVED for ob in obligations)
        completeness_ob = next((ob for ob in obligations if ob.obligation_id == ObligationId.COMPLETENESS), None)
        is_completeness_proven = completeness_ob is not None and completeness_ob.status == ObligationStatus.PASS
        if domain.is_undetermined:
            is_completeness_proven = False

        is_verified_method = True
        is_verified_solution = False

        if has_failed_obligation:
            solution_status = SolutionProofStatus.REFUTED
            explanation = "At least one proof obligation failed; solution refuted or extraneous roots present."
        elif has_unresolved_obligation or not is_completeness_proven:
            if verified_roots or solve_output.is_identity_on_domain:
                solution_status = SolutionProofStatus.SOUND_PARTIAL
                explanation = "Roots are soundly verified by substitution, but completeness is UNRESOLVED."
            else:
                solution_status = SolutionProofStatus.UNDETERMINED
                explanation = "Proof obligations could not be completely resolved."
        else:
            # All obligations PASS, including COMPLETENESS
            solution_status = SolutionProofStatus.SOUND_AND_COMPLETE_IN_SCOPE
            is_verified_solution = True
            if solve_output.is_identity_on_domain:
                explanation = f"Identity equation: all x in original domain {domain.format_domain()} are valid solutions."
            elif not verified_roots and not solve_output.is_identity_on_domain:
                explanation = "Proven complete on R: equation has no real solutions (empty set)."
            else:
                explanation = f"Verified sound and complete: solution set is {{{', '.join(verified_roots)}}}."

        return VerificationResult(
            problem_raw=equation_str,
            domain_str=domain.format_domain(),
            is_all_reals_domain=domain.is_all_reals(),
            excluded_points=[str(v) for v in domain.excluded_values],
            normalization_trace=norm_eq.normalization_trace,
            method_instance=method_inst,
            is_verified_method=is_verified_method,
            is_verified_solution=is_verified_solution,
            solution_status=solution_status,
            candidate_solutions=candidate_evals,
            verified_roots=verified_roots,
            is_identity_on_domain=solve_output.is_identity_on_domain,
            obligations=obligations,
            explanation=explanation,
        )

    def _select_method(
        self, norm_eq: NormalizedEquation, specified_method: Optional[MethodId | str]
    ) -> Optional[MethodId]:
        if specified_method:
            if isinstance(specified_method, str):
                for m in MethodId:
                    if m.value == specified_method:
                        return m
                raise KeyError(f"Unknown method ID: {specified_method}")
            return specified_method

        # Heuristic dispatch based on structural features:
        # 1. Rational equations
        if norm_eq.is_rational:
            return MethodId.M4_RATIONAL_EQUATION

        # 2. Factored equation: unreduced LHS is an explicit multiplication and RHS is 0
        from mke.models.ast_nodes import BinaryOpNode, NumberNode
        if (
            isinstance(norm_eq.raw_ast.left, BinaryOpNode)
            and norm_eq.raw_ast.left.op == "*"
            and isinstance(norm_eq.raw_ast.right, NumberNode)
            and norm_eq.raw_ast.right.value == 0
        ):
            return MethodId.M3_FACTORIZATION

        # 3. Biquadratic polynomial: deg 4, only even powers
        if norm_eq.degree == 4:
            c3 = norm_eq.coefficients.get(3, sympy.Integer(0))
            c1 = norm_eq.coefficients.get(1, sympy.Integer(0))
            if c3 == 0 and c1 == 0:
                return MethodId.M5_BIQUADRATIC_SUBSTITUTION

        # 4. Quadratic polynomial: deg 2, a != 0
        if norm_eq.degree == 2:
            a = norm_eq.coefficients.get(2, sympy.Integer(0))
            if a != 0:
                return MethodId.M2_QUADRATIC_FORMULA

        # 4. Linear polynomial: deg <= 1
        if norm_eq.degree <= 1:
            return MethodId.M1_LINEAR_EQUATION

        # 5. Factorable polynomial of degree >= 2
        if norm_eq.degree >= 2:
            return MethodId.M3_FACTORIZATION

        return None


def result_to_problem_record(
    result: VerificationResult,
    family_id: str = "FAM_001",
    problem_id: str = "PROB_001",
    split: Split = Split.DEV,
    raw_ast_dict: Optional[dict] = None,
) -> ProblemRecord:
    """Convert a VerificationResult into a research ProblemRecord compliant with schema."""
    inst = result.method_instance
    return ProblemRecord(
        family_id=family_id,
        problem_id=problem_id,
        split=split,
        raw_input=result.problem_raw,
        raw_ast=raw_ast_dict or {},
        domain_conditions=[],
        domain_str=result.domain_str,
        excluded_points=result.excluded_points,
        normalization_trace=result.normalization_trace,
        method_id=inst.method_id if inst else None,
        method_version=inst.version if inst else None,
        instantiation=inst.parameters if inst else None,
        structural_guards=inst.structural_guards if inst else [],
        mathematical_guards=inst.mathematical_guards if inst else [],
        admissibility=inst.admissibility if inst else MethodAdmissibility.UNKNOWN,
        obligations=result.obligations,
        is_verified_method=result.is_verified_method,
        is_verified_solution=result.is_verified_solution,
        transfer_validity=result.transfer_validity,
        solution_status=result.solution_status,
        exact_solution=result.verified_roots,
        is_identity_on_domain=result.is_identity_on_domain,
        candidate_solutions=result.candidate_solutions,
        completeness_explanation=result.explanation,
        counterexample=result.counterexample,
        reviewer_log=["Generated by VerificationEngine DEV-01"],
        provenance="DEV01_SYNTHETIC_SUITE",
        license_status="CC-BY-4.0",
    )
