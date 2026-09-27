"""Main deterministic linear equation solver for MKE Product."""

from __future__ import annotations
from typing import Optional, Dict

from ..parser.ast import Equation
from ..evaluator.budget import EvaluationBudget
from ..evaluator.evaluator import check_candidate
from ..evaluator.result import CandidateCheckStatus
from ..evaluator.errors import (
    DomainError,
    EvaluationResourceLimitError,
)
from .errors import OutOfScopeError
from .result import (
    SolutionClassification,
    SolverScopeStatus,
    SolverEvidence,
    SolverResult,
)
from .tracker import OperationTracker
from .scope import check_equation_scope
from .affine import (
    extract_affine,
    _check_bits,
)


def solve_equation(
    equation: Equation,
    budget: Optional[EvaluationBudget] = None,
) -> SolverResult:
    """Solve an affine linear equation over R with exact rational coefficients Q.

    Guarantees:
    - Pre-simplification inspection rejects non-linear terms, x^0, and variable denominators.
    - Owner Decision MKE-S3-ADR-001: Proven constant-domain undefinedness takes precedence
      over variable-dependent exponent-zero scope abstention.
    - Constant undefinedness (e.g. division by 0, 0^0) produces DOMAIN_ERROR.
    - Single shared S3 operation budget covers preflight traversal, variable-dependency
      memoization, constant-expression evaluations, affine extraction, and solver reduction arithmetic.
    - For unique roots, result is submitted to independent S2 check_candidate() with its own budget,
      maintaining modular separation between solver search and independent verification.
    - Never uses floating-point numbers, heuristics, or external symbolic libraries.
    - Never returns UNIQUE_ROOT, DomainSet(R), or EmptySet if resource limits are exhausted.
    """
    if not isinstance(equation, Equation):
        raise TypeError(f"solve_equation requires an Equation AST, got: {type(equation).__name__}")

    effective_budget = budget if budget is not None else EvaluationBudget()
    tracker = OperationTracker(effective_budget)
    var_memo: Dict[int, bool] = {}

    # Step 1: Pre-simplification safety inspection with shared resource tracking
    scope_failure = check_equation_scope(
        equation,
        effective_budget,
        tracker=tracker,
        var_memo=var_memo,
    )
    if scope_failure is not None:
        status, err_code, err_msg, span = scope_failure
        return SolverResult(
            status=status,
            equation=equation,
            error_code=err_code,
            error_message=err_msg,
            error_span=span,
        )

    # Step 2: Exact affine extraction (sharing tracker and memoized variable info)
    try:
        aff_l = extract_affine(equation.left, effective_budget, tracker, var_memo=var_memo)
        aff_r = extract_affine(equation.right, effective_budget, tracker, var_memo=var_memo)

        tracker.count_step(equation.span)
        norm_a = aff_l.a - aff_r.a
        tracker.count_step(equation.span)
        norm_b = aff_l.b - aff_r.b
        _check_bits(norm_a, effective_budget, None)
        _check_bits(norm_b, effective_budget, None)

    except OutOfScopeError as err:
        return SolverResult(
            status=SolverScopeStatus.OUT_OF_SCOPE,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
        )
    except DomainError as err:
        return SolverResult(
            status=SolverScopeStatus.DOMAIN_ERROR,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
        )
    except EvaluationResourceLimitError as err:
        return SolverResult(
            status=SolverScopeStatus.RESOURCE_EXHAUSTED,
            equation=equation,
            error_code=err.code,
            error_message=err.message,
            error_span=err.span,
        )

    # Step 3: Classification and verification
    # Case A: Unique root (a != 0)
    if not norm_a.is_zero:
        try:
            tracker.count_step(equation.span)
            root = -norm_b / norm_a
            _check_bits(root, effective_budget, None)
        except EvaluationResourceLimitError as err:
            return SolverResult(
                status=SolverScopeStatus.RESOURCE_EXHAUSTED,
                equation=equation,
                error_code=err.code,
                error_message=err.message,
            )

        # Independent verification via S2 candidate verifier
        # S2 runs as an independent verification pass with its own evaluation budget,
        # preserving modular separation between solver engine and candidate certification.
        candidate_check = check_candidate(equation, root, budget=effective_budget)

        if candidate_check.status == CandidateCheckStatus.VALID:
            evidence = SolverEvidence(
                equation_str=str(equation),
                left_affine=(aff_l.a, aff_l.b),
                right_affine=(aff_r.a, aff_r.b),
                normalized_a=norm_a,
                normalized_b=norm_b,
                classification=SolutionClassification.UNIQUE_ROOT,
                root=root,
                candidate_check=candidate_check,
                step_trace=(
                    ("STEP_01_SCOPE_PREFLIGHT", "PRE_SIMPLIFICATION_IN_SCOPE"),
                    ("STEP_02_AFFINE_EXTRACTION", "EXACT_AFFINE_CONVERSION"),
                    ("STEP_03_EQUATION_REDUCTION", "NORMALIZED_AX_PLUS_B_EQUALS_ZERO"),
                    ("STEP_04_ROOT_ISOLATION", "SOLVE_LINEAR_UNIQUE_ROOT"),
                    ("STEP_05_INDEPENDENT_VERIFICATION", "S2_CHECK_CANDIDATE_VALID"),
                ),
                diagnostics=(
                    ("root", str(root)),
                    ("steps", str(tracker.operations_count)),
                ),
            )
            return SolverResult(
                status=SolverScopeStatus.IN_SCOPE,
                equation=equation,
                classification=SolutionClassification.UNIQUE_ROOT,
                root=root,
                evidence=evidence,
            )
        elif candidate_check.status == CandidateCheckStatus.RESOURCE_EXHAUSTED:
            return SolverResult(
                status=SolverScopeStatus.RESOURCE_EXHAUSTED,
                equation=equation,
                error_code=candidate_check.error_code,
                error_message="Resource limit exceeded during independent candidate verification.",
            )
        elif candidate_check.status == CandidateCheckStatus.DOMAIN_ERROR:
            return SolverResult(
                status=SolverScopeStatus.DOMAIN_ERROR,
                equation=equation,
                error_code=candidate_check.error_code,
                error_message="Domain error encountered during independent candidate verification.",
            )
        else:
            return SolverResult(
                status=SolverScopeStatus.INTERNAL_VERIFICATION_FAILURE,
                equation=equation,
                error_code="ERR_INTERNAL_VERIFICATION_FAILURE",
                error_message=f"Independent candidate verification rejected candidate root: {candidate_check.status.value}",
            )

    # Case B: All reals (a == 0 and b == 0)
    elif norm_b.is_zero:
        evidence = SolverEvidence(
            equation_str=str(equation),
            left_affine=(aff_l.a, aff_l.b),
            right_affine=(aff_r.a, aff_r.b),
            normalized_a=norm_a,
            normalized_b=norm_b,
            classification=SolutionClassification.ALL_REALS,
            root=None,
            step_trace=(
                ("STEP_01_SCOPE_PREFLIGHT", "PRE_SIMPLIFICATION_IN_SCOPE"),
                ("STEP_02_AFFINE_EXTRACTION", "EXACT_AFFINE_CONVERSION"),
                ("STEP_03_EQUATION_REDUCTION", "NORMALIZED_AX_PLUS_B_EQUALS_ZERO"),
                ("STEP_04_IDENTITY_CLASSIFICATION", "ALGEBRAIC_IDENTITY_ALL_REALS"),
            ),
            diagnostics=(
                ("algebraic_justification", "0*x + 0 = 0 holds for all x in Real domain"),
                ("steps", str(tracker.operations_count)),
            ),
        )
        return SolverResult(
            status=SolverScopeStatus.IN_SCOPE,
            equation=equation,
            classification=SolutionClassification.ALL_REALS,
            root=None,
            evidence=evidence,
        )

    # Case C: Empty set (a == 0 and b != 0)
    else:
        evidence = SolverEvidence(
            equation_str=str(equation),
            left_affine=(aff_l.a, aff_l.b),
            right_affine=(aff_r.a, aff_r.b),
            normalized_a=norm_a,
            normalized_b=norm_b,
            classification=SolutionClassification.NO_SOLUTION,
            root=None,
            step_trace=(
                ("STEP_01_SCOPE_PREFLIGHT", "PRE_SIMPLIFICATION_IN_SCOPE"),
                ("STEP_02_AFFINE_EXTRACTION", "EXACT_AFFINE_CONVERSION"),
                ("STEP_03_EQUATION_REDUCTION", "NORMALIZED_AX_PLUS_B_EQUALS_ZERO"),
                ("STEP_04_CONTRADICTION_CLASSIFICATION", "ALGEBRAIC_CONTRADICTION_EMPTY_SET"),
            ),
            diagnostics=(
                ("algebraic_justification", f"0*x + ({norm_b}) = 0 has no solution in Real domain"),
                ("steps", str(tracker.operations_count)),
            ),
        )
        return SolverResult(
            status=SolverScopeStatus.IN_SCOPE,
            equation=equation,
            classification=SolutionClassification.NO_SOLUTION,
            root=None,
            evidence=evidence,
        )
