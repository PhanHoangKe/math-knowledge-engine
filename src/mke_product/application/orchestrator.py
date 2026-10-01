"""MKE MVP V1 — Application Orchestrator & Pipeline Coordinator.

Implements the end-to-end Pure Python Application Service coordinating:
1. Deterministic intake dispatch (RAW_TEXT vs COEFFICIENTS).
2. Exact normalization & bounded polynomial evaluation in Q[x].
3. Canonical Domain IR authoritative gate (QuadraticProblemIR, DegenerateEquationIR).
4. Degenerate classification and first-principles exact verification (a == 0).
5. Multi-method orthogonal assessment catalog (a != 0).
6. Single-authority method selection resolution.
7. Deterministic step-by-step solution trace execution with fail-closed contract mapping.
8. Host independent verification with tamper-evident certification.
9. Discriminated response state machine generation (SOLVED, ANALYZED_NO_EXECUTION, ERROR).

Guarantees:
- Zero float, CAS, or LLM authority.
- Authoritative Domain IR validation before constructing application views.
- Strict client-facing error message sanitization (zero internal exception leakage).
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
from mke_product.application.traces import (
    TRACE_GENERATORS,
    TraceGenerationError,
    TraceInvalidInputError,
    TraceInvariantError,
    TraceMethodNotApplicableError,
    TraceMethodUnavailableError,
    generate_solution_trace,
)
from mke_product.core.rational import Rational
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.identity import compute_semantic_quadratic_identity
from mke_product.domain.models import (
    DegenerateEquationIR,
    EquationClassificationType,
    ExecutionAvailability,
    MathematicalApplicability,
    MethodAssessment,
    ProblemCategory,
    QuadraticProblemIR,
    RationalFraction,
    SolutionOutcome,
    SupportStatus,
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
    """Construct deterministic clean parseable canonical source query string from coefficients."""
    parts: List[str] = []

    # Quadratic term
    if a.numerator != 0:
        if a.denominator == 1:
            if a.numerator == 1:
                parts.append("x^2")
            elif a.numerator == -1:
                parts.append("-x^2")
            elif a.numerator > 0:
                parts.append(f"{a.numerator}*x^2")
            else:
                parts.append(f"-{abs(a.numerator)}*x^2")
        else:
            if a.numerator > 0:
                parts.append(f"({a.numerator}/{a.denominator})*x^2")
            else:
                parts.append(f"-({abs(a.numerator)}/{a.denominator})*x^2")

    # Linear term
    if b.numerator != 0:
        if not parts:
            if b.denominator == 1:
                if b.numerator == 1:
                    parts.append("x")
                elif b.numerator == -1:
                    parts.append("-x")
                elif b.numerator > 0:
                    parts.append(f"{b.numerator}*x")
                else:
                    parts.append(f"-{abs(b.numerator)}*x")
            else:
                if b.numerator > 0:
                    parts.append(f"({b.numerator}/{b.denominator})*x")
                else:
                    parts.append(f"-({abs(b.numerator)}/{b.denominator})*x")
        else:
            if b.denominator == 1:
                if b.numerator == 1:
                    parts.append("+ x")
                elif b.numerator == -1:
                    parts.append("- x")
                elif b.numerator > 0:
                    parts.append(f"+ {b.numerator}*x")
                else:
                    parts.append(f"- {abs(b.numerator)}*x")
            else:
                if b.numerator > 0:
                    parts.append(f"+ ({b.numerator}/{b.denominator})*x")
                else:
                    parts.append(f"- ({abs(b.numerator)}/{b.denominator})*x")

    # Constant term
    if c.numerator != 0:
        if not parts:
            if c.denominator == 1:
                parts.append(str(c.numerator))
            else:
                if c.numerator > 0:
                    parts.append(f"{c.numerator}/{c.denominator}")
                else:
                    parts.append(f"-{abs(c.numerator)}/{c.denominator}")
        else:
            if c.denominator == 1:
                if c.numerator > 0:
                    parts.append(f"+ {c.numerator}")
                else:
                    parts.append(f"- {abs(c.numerator)}")
            else:
                if c.numerator > 0:
                    parts.append(f"+ {c.numerator}/{c.denominator}")
                else:
                    parts.append(f"- {abs(c.numerator)}/{c.denominator}")

    if not parts:
        return "0 = 0"

    return f"{' '.join(parts)} = 0"


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

    Coordinates intake, normalization, Domain IR validation, degenerate solving/verification,
    method assessment, method selection policy, trace generation, host verification,
    and returns a discriminated SolveResponseUnion.
    """
    # ------------------------------------------------------------------------
    # 1. INTAKE DISPATCH & NORMALIZATION
    # ------------------------------------------------------------------------
    if isinstance(request.input_payload, RawEquationInput):
        raw_text = request.input_payload.raw_query
        raw_query_provenance = "USER_TEXT"
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
        except Exception:
            return ErrorResponse(
                error_code=ApplicationErrorCode.NORMALIZATION_ERROR,
                message_vi="Không thể chuẩn hóa phương trình do lỗi nội bộ.",
                message_en="Internal error while normalizing the equation.",
            )
        raw_query_str = raw_text
    elif isinstance(request.input_payload, CanonicalCoefficientInput):
        a_frac = request.input_payload.a
        b_frac = request.input_payload.b
        c_frac = request.input_payload.c
        raw_query_provenance = "SYSTEM_CANONICAL_COEFFICIENTS"
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
    # 2. SEMANTIC IDENTITY & PROBLEM IDENTIFIERS
    # ------------------------------------------------------------------------
    semantic_hash = compute_semantic_quadratic_identity(
        a_rat, b_rat, c_rat, target_var="x", schema_version=request.schema_version
    )
    problem_id = f"prob_{semantic_hash[:16]}"
    eq_latex = format_equation_latex(a_rat, b_rat, c_rat)
    canonical_eq_string = format_canonical_source_equation(
        RationalFraction.from_rational(a_rat),
        RationalFraction.from_rational(b_rat),
        RationalFraction.from_rational(c_rat),
    )

    # ------------------------------------------------------------------------
    # 3. BRANCH: DEGENERATE EQUATION (a == 0)
    # ------------------------------------------------------------------------
    if a_rat.is_zero:
        deg_result = solve_exact_degenerate(b_rat, c_rat)

        # Authoritative Domain IR Gate
        try:
            deg_ir = DegenerateEquationIR(
                problem_id=problem_id,
                raw_query=raw_query_str,
                raw_query_provenance=raw_query_provenance,
                category=ProblemCategory.ALGEBRA_QUADRATIC,
                semantic_revision_hash=semantic_hash,
                schema_version=request.schema_version,
                target_variable="x",
                a=RationalFraction(numerator=0, denominator=1),
                b=RationalFraction.from_rational(b_rat),
                c=RationalFraction.from_rational(c_rat),
                classification=deg_result.classification,
                linear_root=deg_result.linear_root,
            )
        except Exception:
            return ErrorResponse(
                error_code=ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
                message_vi="Lỗi vi phạm hợp đồng miền phương trình suy biến.",
                message_en="Domain contract error while constructing DegenerateEquationIR.",
            )

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

        # Derive application view directly from validated Domain IR
        deg_problem_view = CanonicalDegenerateProblemView(
            problem_id=deg_ir.problem_id,
            raw_query=deg_ir.raw_query,
            equation_latex=eq_latex,
            classification=deg_ir.classification,
            a=deg_ir.a,
            b=deg_ir.b,
            c=deg_ir.c,
            linear_root=deg_ir.linear_root,
            semantic_revision_hash=deg_ir.semantic_revision_hash,
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
            selected_method_id=None,
            degenerate_solution=deg_solution_view,
            reason_code=NoExecutionReasonCode.DEGENERATE_EXACT_SOLUTION,
            analysis_message_vi=analysis_msg,
        )

    # ------------------------------------------------------------------------
    # 4. BRANCH: TRUE QUADRATIC EQUATION (a != 0)
    # ------------------------------------------------------------------------
    disc = compute_quadratic_discriminant(a_rat, b_rat, c_rat)

    # Authoritative Domain IR Gate
    try:
        quad_ir = QuadraticProblemIR(
            problem_id=problem_id,
            raw_query=raw_query_str,
            raw_query_provenance=raw_query_provenance,
            category=ProblemCategory.ALGEBRA_QUADRATIC,
            semantic_revision_hash=semantic_hash,
            schema_version=request.schema_version,
            target_variable="x",
            a=RationalFraction.from_rational(a_rat),
            b=RationalFraction.from_rational(b_rat),
            c=RationalFraction.from_rational(c_rat),
            coefficient_domain="Q",
            solution_domain="R",
            equation_string=canonical_eq_string,
            discriminant=disc,
            classification=EquationClassificationType.QUADRATIC,
        )
    except Exception:
        return ErrorResponse(
            error_code=ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
            message_vi="Lỗi vi phạm hợp đồng miền đa thức bậc hai.",
            message_en="Domain contract error while constructing QuadraticProblemIR.",
        )

    # Derive application view directly from validated Domain IR
    quad_problem_view = CanonicalQuadraticProblemView(
        problem_id=quad_ir.problem_id,
        raw_query=quad_ir.raw_query,
        equation_latex=eq_latex,
        a=quad_ir.a,
        b=quad_ir.b,
        c=quad_ir.c,
        discriminant=quad_ir.discriminant,
        semantic_revision_hash=quad_ir.semantic_revision_hash,
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
    except (
        TraceMethodNotApplicableError,
        TraceMethodUnavailableError,
        TraceInvalidInputError,
        TraceInvariantError,
    ):
        return ErrorResponse(
            error_code=ApplicationErrorCode.DOMAIN_CONTRACT_ERROR,
            message_vi="Lỗi vi phạm tính nhất quán của hệ thống phương pháp giải.",
            message_en="Domain contract violation in solution trace execution.",
            details={"method_id": chosen_method_id},
        )
    except TraceGenerationError:
        return ErrorResponse(
            error_code=ApplicationErrorCode.METHOD_EXECUTION_FAILED,
            message_vi="Không thể thực thi phương pháp đã chọn.",
            message_en="Unable to execute the selected method.",
            details={"method_id": chosen_method_id},
        )
    except Exception:
        return ErrorResponse(
            error_code=ApplicationErrorCode.INTERNAL_ERROR,
            message_vi="Lỗi nội bộ khi thực thi phương pháp giải.",
            message_en="Internal error during method execution.",
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
    except Exception:
        return ErrorResponse(
            error_code=ApplicationErrorCode.VERIFICATION_FAILED,
            message_vi="Xác minh độc lập cho kết quả giải phương trình bậc hai thất bại.",
            message_en="Host independent verification failed.",
            details={"method_id": chosen_method_id},
        )

    if cert.outcome != VerificationOutcome.VERIFIED_COMPLETE:
        return ErrorResponse(
            error_code=ApplicationErrorCode.VERIFICATION_FAILED,
            message_vi="Xác minh độc lập cho kết quả giải phương trình bậc hai thất bại.",
            message_en="Host independent verification failed for quadratic solution.",
            details={"method_id": chosen_method_id},
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
