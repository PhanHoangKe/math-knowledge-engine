"""MKE MVP V1 — Application Orchestrator & Pipeline Coordinator.

Implements the end-to-end Pure Python Application Service coordinating:
1. Deterministic intake dispatch (RAW_TEXT vs COEFFICIENTS).
2. Exact normalization & bounded polynomial evaluation in Q[x].
3. Degenerate classification and first-principles exact verification (a == 0).
4. Multi-method orthogonal assessment catalog (a != 0).
5. Single-authority method selection resolution.
6. Deterministic step-by-step solution trace execution.
7. Host independent verification with tamper-evident certification.
8. Discriminated response state machine generation (SOLVED, ANALYZED_NO_EXECUTION, ERROR).

Guarantees:
- Zero float, CAS, or LLM authority.
- Strict fail-closed error handling.
- Mandatory semantic identity invariance between RAW_TEXT and COEFFICIENTS.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from mke_product.application.degenerate import (
    DegenerateSolveResult,
    solve_exact_degenerate,
    verify_degenerate_solution,
)
from mke_product.application.dto import (
    AnalyzedNoExecutionResponse,
    CanonicalCoefficientInput,
    CanonicalDegenerateProblemView,
    CanonicalProblemUnion,
    CanonicalQuadraticProblemView,
    DegenerateSolutionView,
    ErrorResponse,
    MethodOptionView,
    NoExecutionReasonCode,
    RawEquationInput,
    SolvedResponse,
    SolveRequest,
    SolveResponseUnion,
    VerifiedSolutionView,
)
from mke_product.application.errors import (
    ApplicationError,
    ApplicationErrorCode,
    map_parser_exception_to_application_error,
)
from mke_product.application.normalizer import normalize_raw_equation
from mke_product.application.traces import TRACE_GENERATORS, generate_solution_trace
from mke_product.core.rational import Rational
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.identity import compute_semantic_quadratic_identity
from mke_product.domain.models import (
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    MethodAssessment,
    RationalFraction,
    SolutionOutcome,
    VerificationOutcome,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.domain.verifier import HostIndependentVerifier
from mke_product.parser.errors import MKEParserError


def format_equation_latex(a_rat: Rational, b_rat: Rational, c_rat: Rational) -> str:
    """Format exact canonical LaTeX string for a*x^2 + b*x + c = 0."""
    parts: List[str] = []

    # Quadratic term
    if not a_rat.is_zero:
        if a_rat == Rational(1, 1):
            parts.append("x^2")
        elif a_rat == Rational(-1, 1):
            parts.append("-x^2")
        elif a_rat > Rational(0, 1):
            parts.append(f"{RationalFraction.from_rational(a_rat).to_latex()}x^2")
        else:
            parts.append(f"-{RationalFraction.from_rational(-a_rat).to_latex()}x^2")

    # Linear term
    if not b_rat.is_zero:
        if not parts:
            if b_rat == Rational(1, 1):
                parts.append("x")
            elif b_rat == Rational(-1, 1):
                parts.append("-x")
            elif b_rat > Rational(0, 1):
                parts.append(f"{RationalFraction.from_rational(b_rat).to_latex()}x")
            else:
                parts.append(f"-{RationalFraction.from_rational(-b_rat).to_latex()}x")
        else:
            if b_rat == Rational(1, 1):
                parts.append("+ x")
            elif b_rat == Rational(-1, 1):
                parts.append("- x")
            elif b_rat > Rational(0, 1):
                parts.append(f"+ {RationalFraction.from_rational(b_rat).to_latex()}x")
            else:
                parts.append(f"- {RationalFraction.from_rational(-b_rat).to_latex()}x")

    # Constant term
    if not c_rat.is_zero:
        if not parts:
            parts.append(RationalFraction.from_rational(c_rat).to_latex())
        else:
            if c_rat > Rational(0, 1):
                parts.append(f"+ {RationalFraction.from_rational(c_rat).to_latex()}")
            else:
                parts.append(f"- {RationalFraction.from_rational(-c_rat).to_latex()}")

    if not parts:
        return "0 = 0"

    lhs = " ".join(parts)
    return f"{lhs} = 0"


def format_canonical_source_equation(
    a: RationalFraction, b: RationalFraction, c: RationalFraction
) -> str:
    """Construct deterministic canonical source query string from coefficients."""
    if a.numerator != 0:
        return f"{a}*x^2 + {b}*x + {c} = 0"
    return f"{b}*x + {c} = 0"


def _assess_to_view(m: MethodAssessment, registry: MethodRegistry) -> MethodOptionView:
    """Map domain MethodAssessment to application MethodOptionView."""
    has_trace = m.method_id in TRACE_GENERATORS
    method_def = registry.get(m.method_id)
    return MethodOptionView(
        method_id=m.method_id,
        title_vi=method_def.title_vi,
        mathematical_applicability=m.mathematical_applicability,
        support_status=m.support_status,
        execution_availability=m.execution_availability,
        pedagogical_recommendation=m.pedagogical_recommendation,
        verification_capability=m.verification_capability,
        reasons=m.reasons,
        prerequisites=m.prerequisite_status,
        has_trace_available=has_trace,
        pedagogical_priority=m.pedagogical_priority,
    )


def solve_request(request: SolveRequest) -> SolveResponseUnion:
    """Execute end-to-end application orchestration for a SolveRequest.

    Coordinates intake, normalization, degenerate solving/verification,
    method assessment, method selection policy, trace generation, host verification,
    and returns a discriminated SolveResponseUnion.
    """
    # ------------------------------------------------------------------------
    # 1. INTAKE DISPATCH & NORMALIZATION
    # ------------------------------------------------------------------------
    if isinstance(request.input_payload, RawEquationInput):
        raw_text = request.input_payload.raw_query
        try:
            a_rat, b_rat, c_rat = normalize_raw_equation(raw_text)
        except ApplicationError as exc:
            return ErrorResponse(
                error_code=exc.error_code,
                message_vi=exc.message_vi,
                message_en=exc.message_en,
                span=exc.span,
                details=exc.details,
            )
        except MKEParserError as exc:
            app_err = map_parser_exception_to_application_error(exc)
            return ErrorResponse(
                error_code=app_err.error_code,
                message_vi=app_err.message_vi,
                message_en=app_err.message_en,
                span=app_err.span,
                details=app_err.details,
            )
        except Exception as exc:
            return ErrorResponse(
                error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
                message_vi=f"Lỗi không xác định khi chuẩn hóa phương trình: {exc}",
                message_en=f"Unhandled error during intake normalization: {exc}",
            )
        raw_query_str = raw_text
    elif isinstance(request.input_payload, CanonicalCoefficientInput):
        a_frac = request.input_payload.a
        b_frac = request.input_payload.b
        c_frac = request.input_payload.c
        a_rat = a_frac.to_rational()
        b_rat = b_frac.to_rational()
        c_rat = c_frac.to_rational()
        raw_query_str = format_canonical_source_equation(a_frac, b_frac, c_frac)
    else:
        return ErrorResponse(
            error_code=ApplicationErrorCode.SYNTAX_ERROR,
            message_vi="Định dạng đầu vào không hợp lệ.",
            message_en="Unsupported or invalid input payload type.",
        )

    # ------------------------------------------------------------------------
    # 2. SEMANTIC IDENTITY & PROBLEM VIEW BASE DATA
    # ------------------------------------------------------------------------
    semantic_hash = compute_semantic_quadratic_identity(
        a_rat, b_rat, c_rat, target_var="x", schema_version=request.schema_version
    )
    problem_id = f"prob_{semantic_hash[:16]}"
    eq_latex = format_equation_latex(a_rat, b_rat, c_rat)

    # ------------------------------------------------------------------------
    # 3. BRANCH: DEGENERATE EQUATION (a == 0)
    # ------------------------------------------------------------------------
    if a_rat.is_zero:
        deg_result = solve_exact_degenerate(b_rat, c_rat)
        cert = verify_degenerate_solution(
            b=b_rat, c=c_rat, candidate=deg_result, problem_hash=semantic_hash
        )
        if cert.outcome != VerificationOutcome.VERIFIED_COMPLETE:
            return ErrorResponse(
                error_code=ApplicationErrorCode.VERIFICATION_FAILED,
                message_vi="Xác minh phương trình suy biến thất bại.",
                message_en="Host verification failed for degenerate equation.",
            )

        if deg_result.classification == EquationClassificationType.LINEAR:
            root_lat = deg_result.linear_root.to_latex() if deg_result.linear_root else ""
            final_answer_latex = f"x = {root_lat}"
            analysis_msg = (
                f"Phương trình bậc nhất một ẩn có nghiệm duy nhất x = {root_lat}."
            )
        elif deg_result.classification == EquationClassificationType.IDENTITY:
            final_answer_latex = "S = \\mathbb{R}"
            analysis_msg = (
                "Phương trình nghiệm đúng với mọi số thực x (vô số nghiệm)."
            )
        else:  # CONTRADICTION
            final_answer_latex = "S = \\emptyset"
            analysis_msg = (
                "Phương trình vô nghiệm thực do xuất hiện mâu thuẫn toán học."
            )

        deg_problem_view = CanonicalDegenerateProblemView(
            problem_id=problem_id,
            raw_query=raw_query_str,
            equation_latex=eq_latex,
            classification=deg_result.classification,
            a=RationalFraction.from_rational(a_rat),
            b=RationalFraction.from_rational(b_rat),
            c=RationalFraction.from_rational(c_rat),
            linear_root=deg_result.linear_root,
            semantic_revision_hash=semantic_hash,
        )

        deg_solution_view = DegenerateSolutionView(
            classification=deg_result.classification,
            outcome=deg_result.outcome,
            linear_root=deg_result.linear_root,
            final_answer_latex=final_answer_latex,
            verification_scope="FINAL_SOLUTION",
            certificate=cert,
        )

        return AnalyzedNoExecutionResponse(
            problem=deg_problem_view,
            available_methods=[],
            selected_method_id=request.selected_method_id,
            degenerate_solution=deg_solution_view,
            reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
            analysis_message_vi=analysis_msg,
        )

    # ------------------------------------------------------------------------
    # 4. BRANCH: TRUE QUADRATIC EQUATION (a != 0)
    # ------------------------------------------------------------------------
    disc = compute_quadratic_discriminant(a_rat, b_rat, c_rat)

    quad_problem_view = CanonicalQuadraticProblemView(
        problem_id=problem_id,
        raw_query=raw_query_str,
        equation_latex=eq_latex,
        a=RationalFraction.from_rational(a_rat),
        b=RationalFraction.from_rational(b_rat),
        c=RationalFraction.from_rational(c_rat),
        discriminant=disc,
        semantic_revision_hash=semantic_hash,
    )

    # Multi-method orthogonal assessment catalog
    registry = MethodRegistry()
    assessments = registry.assess_quadratic(a_rat, b_rat, c_rat)
    method_views = [_assess_to_view(m, registry) for m in assessments]
    assessment_dict = {m.method_id: m for m in assessments}

    # Method Selection Policy Resolution
    if request.selected_method_id is not None:
        requested_id = request.selected_method_id
        if requested_id not in assessment_dict:
            return ErrorResponse(
                error_code=ApplicationErrorCode.METHOD_NOT_FOUND,
                message_vi=f"Không tìm thấy phương pháp giải '{requested_id}'.",
                message_en=f"Method '{requested_id}' not found in registry.",
                details={"requested_method_id": requested_id},
            )

        target_assessment = assessment_dict[requested_id]
        target_def = registry.get(requested_id)
        if target_assessment.mathematical_applicability != MathematicalApplicability.APPLICABLE:
            reason_str = ", ".join(target_assessment.reasons) if target_assessment.reasons else "Không thỏa mãn điều kiện áp dụng."
            return AnalyzedNoExecutionResponse(
                problem=quad_problem_view,
                available_methods=method_views,
                selected_method_id=requested_id,
                reason_code=NoExecutionReasonCode.METHOD_NOT_APPLICABLE,
                analysis_message_vi=f"Phương pháp '{target_def.title_vi}' không áp dụng được: {reason_str}",
            )

        if target_assessment.execution_availability != ExecutionAvailability.AVAILABLE:
            return AnalyzedNoExecutionResponse(
                problem=quad_problem_view,
                available_methods=method_views,
                selected_method_id=requested_id,
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi=f"Phương pháp '{target_def.title_vi}' chưa hỗ trợ sinh lời giải chi tiết trong phiên bản này.",
            )

        chosen_method_id = requested_id
    else:
        # Automated selection: Filter APPLICABLE + AVAILABLE
        candidates = [
            m for m in assessments
            if m.mathematical_applicability == MathematicalApplicability.APPLICABLE
            and m.execution_availability == ExecutionAvailability.AVAILABLE
        ]
        if not candidates:
            return AnalyzedNoExecutionResponse(
                problem=quad_problem_view,
                available_methods=method_views,
                selected_method_id=None,
                reason_code=NoExecutionReasonCode.METHOD_NOT_EXECUTABLE,
                analysis_message_vi="Không có phương pháp giải nào khả dụng để thực thi.",
            )

        # Sort tie-breaker by pedagogical_priority (lowest int = highest priority)
        candidates.sort(key=lambda m: m.pedagogical_priority)
        chosen_method_id = candidates[0].method_id

    # ------------------------------------------------------------------------
    # 5. SOLUTION TRACE GENERATION
    # ------------------------------------------------------------------------
    try:
        trace = generate_solution_trace(chosen_method_id, a_rat, b_rat, c_rat)
    except Exception as exc:
        return ErrorResponse(
            error_code=ApplicationErrorCode.METHOD_EXECUTION_FAILED,
            message_vi=f"Lỗi khi thực thi phương pháp '{chosen_method_id}': {exc}",
            message_en=f"Execution failed for method '{chosen_method_id}': {exc}",
            details={"method_id": chosen_method_id},
        )

    # ------------------------------------------------------------------------
    # 6. HOST INDEPENDENT VERIFICATION
    # ------------------------------------------------------------------------
    verifier = HostIndependentVerifier()
    try:
        cert = verifier.verify_quadratic_solution(
            a_rat=a_rat,
            b_rat=b_rat,
            c_rat=c_rat,
            outcome=trace.solution_outcome,
            roots=trace.roots,
            problem_hash=semantic_hash,
        )
    except Exception as exc:
        return ErrorResponse(
            error_code=ApplicationErrorCode.VERIFICATION_FAILED,
            message_vi=f"Lỗi xác minh độc lập: {exc}",
            message_en=f"Verification exception: {exc}",
            details={"method_id": chosen_method_id},
        )

    if cert.outcome != VerificationOutcome.VERIFIED_COMPLETE:
        return ErrorResponse(
            error_code=ApplicationErrorCode.VERIFICATION_FAILED,
            message_vi="Xác minh độc lập cho kết quả giải phương trình bậc hai thất bại.",
            message_en="Host independent verification failed for quadratic solution.",
            details={"method_id": chosen_method_id, "cert_outcome": cert.outcome.value},
        )

    # ------------------------------------------------------------------------
    # 7. CONSTRUCT VERIFIED SOLUTION & SOLVED RESPONSE
    # ------------------------------------------------------------------------
    solution_view = VerifiedSolutionView(
        method_id=chosen_method_id,
        outcome=trace.solution_outcome,
        roots=trace.roots,
        final_answer_latex=trace.final_answer_latex,
        trace=trace,
        verification_scope="FINAL_SOLUTION",
        certificate=cert,
    )

    return SolvedResponse(
        problem=quad_problem_view,
        available_methods=method_views,
        selected_method_id=chosen_method_id,
        solution=solution_view,
    )
