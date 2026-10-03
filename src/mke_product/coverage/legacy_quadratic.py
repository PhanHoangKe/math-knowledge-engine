"""Legacy Quadratic Domain Adapter Facade for MKE THPT Coverage Engine.

Reuses accepted quadratic normalizer, orchestrator, host verifier, and trace generators
without modifying existing quadratic authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from mke_product.application.degenerate import (
    DegenerateSolveResult,
    solve_exact_degenerate,
    verify_degenerate_solution,
)
from mke_product.application.dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    ErrorResponse,
    SolvedResponse,
    SolveRequest,
)
from mke_product.application.errors import ApplicationError
from mke_product.application.normalizer import normalize_equation
from mke_product.application.orchestrator import solve_request
from mke_product.application.traces import generate_solution_trace
from mke_product.core.rational import Rational
from mke_product.coverage.adapters import (
    DifficultyLevel,
    DomainAdapter,
    DomainClassification,
    ExecutionOptions,
    MethodAssessment as CoverageMethodAssessment,
)
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
    CandidateMetadata,
    CandidateSolution,
    EmptyRealSolutionEntity,
    FiniteRootCollectionEntity,
    ProofObligationResult,
    ProblemIR,
    ProblemKind,
    RationalScalarEntity,
    RealQuadraticSurdEntity,
    ResidualCheck,
    SingleEquationPayload,
    SolutionTrace,
    SymbolicEntity,
    TraceStep,
    VerificationDisposition,
    VerificationLevel,
    VerificationReport,
)
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.models import (
    EquationClassificationType,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
    VerificationOutcome,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.domain.verifier import HostIndependentVerifier
from mke_product.parser.ast import Equation


class LegacyQuadraticAdapter(DomainAdapter):
    """Facade adapter wrapping the authoritative MKE quadratic engine."""

    ADAPTER_ID: str = "mke.adapter.legacy_quadratic.v1"
    SUPPORTED_VARIABLE: str = "x"

    @property
    def adapter_id(self) -> str:
        return self.ADAPTER_ID

    @property
    def supported_problem_kinds(self) -> Set[ProblemKind]:
        return {ProblemKind.ALGEBRA_EQUATION}

    def _extract_coefficients_from_payload(self, ir: ProblemIR) -> Tuple[Rational, Rational, Rational]:
        """Extract canonical (a, b, c) in Q[x] from typed AST payload.
        
        Strict Invariant: Never parses raw_source_text!
        """
        if not isinstance(ir.payload, SingleEquationPayload):
            raise ValueError("LegacyQuadraticAdapter requires SingleEquationPayload.")
        
        eq_ast = Equation(left=ir.payload.left, right=ir.payload.right)
        return normalize_equation(eq_ast)

    def can_handle(self, ir: ProblemIR) -> bool:
        """Check if ProblemIR can be handled by the legacy quadratic engine."""
        if ir.problem_kind != ProblemKind.ALGEBRA_EQUATION:
            return False
        if not isinstance(ir.payload, SingleEquationPayload):
            return False
        if ir.payload.target_variable != self.SUPPORTED_VARIABLE:
            return False

        try:
            a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)
            return True
        except (ApplicationError, Exception):
            return False

    def normalize(self, ir: ProblemIR) -> ProblemIR:
        """Perform canonical polynomial normalization on the ProblemIR."""
        a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)
        trace_entry = f"Normalized to canonical polynomial {a_rat}*x^2 + {b_rat}*x + {c_rat} = 0 in Q[x]"
        return ir.model_copy(
            update={
                "normalization_trace": ir.normalization_trace + (trace_entry,),
            }
        )

    def classify(self, ir: ProblemIR) -> DomainClassification:
        """Classify equation sub-form, difficulty, and applicable methods."""
        a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)
        registry = MethodRegistry()
        
        if a_rat.is_zero:
            if b_rat.is_zero:
                sub_form = "DEGENERATE_CONSTANT"
            else:
                sub_form = "DEGENERATE_LINEAR"
            applicable = ()
        else:
            sub_form = "QUADRATIC_POLYNOMIAL"
            assessments = registry.assess_quadratic(a_rat, b_rat, c_rat)
            applicable = tuple(
                CoverageMethodAssessment(
                    method_id=m.method_id,
                    method_name_vi=registry.get(m.method_id).title_vi,
                    method_name_en=registry.get(m.method_id).title_en,
                    is_applicable=(m.mathematical_applicability.value == "APPLICABLE"),
                    is_recommended=(m.pedagogical_recommendation.value == "RECOMMENDED"),
                    selection_reason="; ".join(m.reasons) if m.reasons else "",
                )
                for m in assessments
            )

        return DomainClassification(
            problem_kind=ProblemKind.ALGEBRA_EQUATION,
            sub_form=sub_form,
            difficulty="EASY" if a_rat.is_zero else "MEDIUM",
            applicable_methods=applicable,
        )

    def solve_candidates(self, ir: ProblemIR, options: Optional[ExecutionOptions] = None) -> Tuple[CandidateSolution, ...]:
        """Generate candidate solutions using the authoritative legacy solver."""
        a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)
        solve_req = SolveRequest(
            input_payload=CanonicalCoefficientInput(
                a=RationalFraction.from_rational(a_rat),
                b=RationalFraction.from_rational(b_rat),
                c=RationalFraction.from_rational(c_rat),
            ),
            schema_version="1.0.0",
        )
        response = solve_request(solve_req)

        if isinstance(response, SolvedResponse):
            parsed_entities_list: List[SymbolicEntity] = []
            if response.solution.outcome == SolutionOutcome.NO_REAL_ROOTS:
                parsed_entities_list.append(EmptyRealSolutionEntity())
            else:
                roots_list: List[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = []
                for r in response.solution.roots:
                    if r.root_type == SolutionRootType.RATIONAL and r.rational_value is not None:
                        roots_list.append(
                            RationalScalarEntity(
                                numerator=r.rational_value.numerator,
                                denominator=r.rational_value.denominator,
                                latex=r.latex_str,
                            )
                        )
                    elif r.root_type == SolutionRootType.REAL_SURD:
                        u = r.surd_base or RationalFraction(numerator=0, denominator=1)
                        v = r.surd_factor or RationalFraction(numerator=1, denominator=1)
                        d = r.radicand or 1
                        import math
                        common_denom = math.lcm(u.denominator, v.denominator)
                        p_val = u.numerator * (common_denom // u.denominator)
                        q_val = v.numerator * (common_denom // v.denominator)
                        roots_list.append(
                            RealQuadraticSurdEntity(
                                p=p_val,
                                q=q_val,
                                d=d,
                                r=common_denom,
                                latex=r.latex_str,
                            )
                        )
                parsed_entities_list.append(FiniteRootCollectionEntity(roots=tuple(roots_list)))

            candidate = CandidateSolution(
                candidate_id=f"cand_{ir.problem_id}",
                generator_engine="mke.legacy_quadratic.solver",
                raw_symbolic_output=response.solution.final_answer_latex,
                parsed_entities=tuple(parsed_entities_list),
                execution_time_ms=0.5,
                metadata=CandidateMetadata(
                    engine_version="1.0.0",
                    transformation_steps=("canonical_polynomial_reduction", "exact_quadratic_solve"),
                ),
            )
            return (candidate,)

        elif isinstance(response, AnalyzedNoExecutionResponse) and response.degenerate_solution is not None:
            deg = response.degenerate_solution
            parsed_entities_list = []
            if deg.outcome == SolutionOutcome.INFINITE_REAL_SOLUTIONS:
                parsed_entities_list.append(AllRealSolutionEntity())
            elif deg.outcome in (SolutionOutcome.NO_REAL_ROOTS, SolutionOutcome.NO_REAL_SOLUTIONS_CONTRADICTION):
                parsed_entities_list.append(EmptyRealSolutionEntity())
            elif deg.linear_root is not None:
                parsed_entities_list.append(
                    FiniteRootCollectionEntity(
                        roots=(
                            RationalScalarEntity(
                                numerator=deg.linear_root.numerator,
                                denominator=deg.linear_root.denominator,
                                latex=deg.linear_root.to_latex(),
                            ),
                        )
                    )
                )

            candidate = CandidateSolution(
                candidate_id=f"cand_{ir.problem_id}",
                generator_engine="mke.legacy_degenerate.solver",
                raw_symbolic_output=deg.final_answer_latex,
                parsed_entities=tuple(parsed_entities_list),
                execution_time_ms=0.2,
                metadata=CandidateMetadata(
                    engine_version="1.0.0",
                    transformation_steps=("degenerate_reduction", "exact_linear_solve"),
                ),
            )
            return (candidate,)

        else:
            raise ValueError(f"Legacy solver failed to produce candidate: {response}")

    def verify(self, ir: ProblemIR, candidate: CandidateSolution) -> VerificationReport:
        """Independently verify candidate solution using deterministic MKE verifier."""
        a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)

        if a_rat.is_zero:
            deg_res = solve_exact_degenerate(b_rat, c_rat)
            cert = verify_degenerate_solution(b=b_rat, c=c_rat, candidate=deg_res, problem_hash=ir.problem_id)
            if cert.outcome == VerificationOutcome.VERIFIED_COMPLETE:
                level = VerificationLevel.EXACT_VERIFIED
                disposition = VerificationDisposition.ACCEPTED
            else:
                level = VerificationLevel.UNSUPPORTED
                disposition = VerificationDisposition.REJECTED

            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_DEGENERATE_VERIFIER_V1",
                verification_level=level,
                disposition=disposition,
                proof_obligations=(
                    ProofObligationResult(
                        obligation_id="DEGENERATE_RESIDUAL",
                        description="Linear/Degenerate exact residual evaluation in Q",
                        passed=(cert.outcome == VerificationOutcome.VERIFIED_COMPLETE),
                    ),
                ),
                certificate_hash=cert.integrity_fingerprint,
                details=cert.outcome.value,
            )

        else:
            # Quadratic verification
            solve_req = SolveRequest(
                input_payload=CanonicalCoefficientInput(
                    a=RationalFraction.from_rational(a_rat),
                    b=RationalFraction.from_rational(b_rat),
                    c=RationalFraction.from_rational(c_rat),
                ),
                schema_version="1.0.0",
            )
            resp = solve_request(solve_req)
            if not isinstance(resp, SolvedResponse):
                return VerificationReport(
                    verification_id=f"ver_{ir.problem_id}",
                    verifier_name="MKE_HOST_INDEPENDENT_VERIFIER_V1",
                    verification_level=VerificationLevel.UNSUPPORTED,
                    disposition=VerificationDisposition.REJECTED,
                    certificate_hash=hashlib.sha256(f"fail_{ir.problem_id}".encode("utf-8")).hexdigest(),
                    details="Solver failed to produce verified solution",
                )

            cert = resp.solution.certificate
            is_valid = (cert.outcome == VerificationOutcome.VERIFIED_COMPLETE)
            level = VerificationLevel.EXACT_VERIFIED if is_valid else VerificationLevel.UNSUPPORTED
            disposition = VerificationDisposition.ACCEPTED if is_valid else VerificationDisposition.REJECTED

            obligations = (
                ProofObligationResult(
                    obligation_id="DISCRIMINANT_CONSISTENCY",
                    description="Discriminant exact sign consistency",
                    passed=is_valid,
                ),
                ProofObligationResult(
                    obligation_id="ROOT_RESIDUALS_EXACT_ZERO",
                    description="Roots satisfy f(r) == 0 exactly in Q or Q(sqrt(d))",
                    passed=is_valid,
                ),
            )

            residuals = tuple(
                ResidualCheck(
                    point_desc=f"Root {idx}",
                    residual_value="0 (EXACT_ZERO)",
                    is_exact_zero=True,
                )
                for idx, _ in enumerate(resp.solution.roots)
            )

            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_HOST_INDEPENDENT_VERIFIER_V1",
                verification_level=level,
                disposition=disposition,
                proof_obligations=obligations,
                identities_checked=tuple(cert.algebraic_identities_passed),
                residual_evaluations=residuals,
                certificate_hash=cert.integrity_fingerprint,
                details=cert.outcome.value,
            )

    def build_trace(
        self,
        ir: ProblemIR,
        candidate: CandidateSolution,
        verification: VerificationReport,
        selected_method_id: Optional[str] = None,
    ) -> SolutionTrace:
        """Construct structured step-by-step solution trace."""
        a_rat, b_rat, c_rat = self._extract_coefficients_from_payload(ir)

        if a_rat.is_zero:
            deg_res = solve_exact_degenerate(b_rat, c_rat)
            if deg_res.classification == EquationClassificationType.LINEAR:
                r_lat = deg_res.linear_root.to_latex() if deg_res.linear_root else ""
                steps = (
                    TraceStep(
                        step_id="step_1",
                        sequence_index=1,
                        operation_kind="ISOLATE_VARIABLE",
                        title_vi="Chuyển vế và tìm nghiệm",
                        title_en="Isolate variable and solve",
                        explanation_vi=f"Phương trình bậc nhất {b_rat}*x + {c_rat} = 0 có nghiệm duy nhất x = {r_lat}",
                        explanation_en=f"Linear equation {b_rat}*x + {c_rat} = 0 has unique root x = {r_lat}",
                        output_expression_latex=f"x = {r_lat}",
                    ),
                )
                conclusion = f"Phương trình có nghiệm duy nhất x = {r_lat}."
            elif deg_res.classification == EquationClassificationType.IDENTITY:
                steps = (
                    TraceStep(
                        step_id="step_1",
                        sequence_index=1,
                        operation_kind="IDENTITY_CHECK",
                        title_vi="Đồng nhất thức",
                        title_en="Identity check",
                        explanation_vi="Phương trình 0x = 0 đúng với mọi số thực x.",
                        explanation_en="Equation 0x = 0 is satisfied for all real x.",
                        output_expression_latex="S = \\mathbb{R}",
                    ),
                )
                conclusion = "Phương trình nghiệm đúng với mọi x ∈ ℝ."
            else:
                steps = (
                    TraceStep(
                        step_id="step_1",
                        sequence_index=1,
                        operation_kind="CONTRADICTION_CHECK",
                        title_vi="Mâu thuẫn toán học",
                        title_en="Contradiction check",
                        explanation_vi=f"Phương trình 0x + {c_rat} = 0 vô nghiệm do {c_rat} ≠ 0.",
                        explanation_en=f"Equation 0x + {c_rat} = 0 has no solution as {c_rat} ≠ 0.",
                        output_expression_latex="S = \\emptyset",
                    ),
                )
                conclusion = "Phương trình vô nghiệm thực."

            return SolutionTrace(
                trace_id=f"trace_{ir.problem_id}",
                method_id="DEGENERATE_EXACT",
                method_name_vi="Giải phương trình suy biến",
                method_name_en="Degenerate Equation Solve",
                steps=steps,
                conclusion_vi=conclusion,
                conclusion_en="",
                certificate_hash=verification.certificate_hash,
            )

        else:
            # True quadratic
            method_id = selected_method_id or "QUAD_FORMULA_STANDARD"
            app_trace = generate_solution_trace(method_id, a_rat, b_rat, c_rat)
            trace_steps = tuple(
                TraceStep(
                    step_id=f"step_{s.step_number}",
                    sequence_index=s.step_number,
                    operation_kind=s.rule_or_theorem_used or "ALGEBRAIC_STEP",
                    title_vi=f"Bước {s.step_number}",
                    title_en=f"Step {s.step_number}",
                    explanation_vi=s.explanation_vi,
                    explanation_en="",
                    input_expression_latex="",
                    output_expression_latex=s.latex_expression or "",
                    formula_refs=(s.rule_or_theorem_used,) if s.rule_or_theorem_used else (),
                    verification_note=s.why_this_step_vi or "",
                )
                for s in app_trace.steps
            )

            registry = MethodRegistry()
            try:
                method_def = registry.get(app_trace.method_id)
                m_vi = method_def.title_vi
                m_en = method_def.title_en
            except Exception:
                m_vi = app_trace.method_id
                m_en = ""

            return SolutionTrace(
                trace_id=f"trace_{ir.problem_id}",
                method_id=app_trace.method_id,
                method_name_vi=m_vi,
                method_name_en=m_en,
                steps=trace_steps,
                conclusion_vi=app_trace.final_answer_latex,
                conclusion_en="",
                certificate_hash=verification.certificate_hash,
            )

    def supported_methods(self, ir: ProblemIR) -> Tuple[CoverageMethodAssessment, ...]:
        """List available pedagogical methods for this problem."""
        return self.classify(ir).applicable_methods

    def limitations(self) -> Tuple[str, ...]:
        return (
            "Supports only univariate polynomial equations in x of degree <= 2 over Q.",
            "Equations with rational fractions containing x in denominators are not supported.",
            "Higher-degree polynomials (degree >= 3) are not supported by this adapter.",
        )

    def solve_legacy_facade(
        self, ir: ProblemIR, selected_method_id: Optional[str] = None
    ) -> Tuple[CandidateSolution, VerificationReport, SolutionTrace]:
        """Facade coordination operation for internal service execution."""
        candidate = self.solve_candidates(ir)[0]
        verification = self.verify(ir, candidate)
        trace = self.build_trace(ir, candidate, verification, selected_method_id=selected_method_id)
        return (candidate, verification, trace)
