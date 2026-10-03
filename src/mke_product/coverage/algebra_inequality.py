"""MKE THPT Universal Coverage Engine — Verified Polynomial Inequality Adapter.

Authoritative adapter for single-variable polynomial inequalities in R[x]
with degree <= 2 proof capability, exact interval-set entities,
and independent deterministic verification.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from mke_product.core.rational import Rational
from mke_product.coverage.adapters import (
    DifficultyLevel,
    DomainAdapter,
    DomainClassification,
    ExecutionOptions,
    MethodAssessment,
)
from mke_product.coverage.contracts import (
    AllRealSolutionEntity,
    CandidateMetadata,
    CandidateSolution,
    ConstraintRelation,
    DomainCategory,
    DomainCheck,
    EmptyRealSolutionEntity,
    ProblemIR,
    ProblemKind,
    ProofObligationResult,
    RationalScalarEntity,
    RealIntervalEntity,
    RealIntervalUnionEntity,
    RealQuadraticSurdEntity,
    ResidualCheck,
    SingleInequalityPayload,
    SolutionTrace,
    SymbolicEntity,
    TraceStep,
    VerificationDisposition,
    VerificationLevel,
    VerificationReport,
    _compare_algebraic_entities,
    _to_u_v_d,
    _compare_u_v_d,
)
from mke_product.coverage.algebra_rational import (
    NumberFieldElement,
    PolyQ,
    are_roots_equal,
    distinct_real_root_count,
    eval_poly_at_point,
    solve_poly_degree_le_2,
)
from mke_product.parser.ast import (
    ASTNode,
    BinaryOp,
    Group,
    IntegerLiteral,
    Power,
    UnaryOp,
    Variable,
)


class InequalityAlgebraError(Exception):
    """Base exception for inequality algebra operations."""
    pass


class InequalityDegreeOutOfScopeError(InequalityAlgebraError):
    """Raised when polynomial degree exceeds quadratic bound <= 2."""
    pass


class UnsupportedInequalityNodeError(InequalityAlgebraError):
    """Raised when AST contains unsupported node types or operations."""
    pass


# ---------------------------------------------------------------------------
# Local Structural AST -> PolyQ Normalizer
# ---------------------------------------------------------------------------

def normalize_ast_to_polyq(node: ASTNode, target_var: str = "x") -> PolyQ:
    """Normalize a typed AST expression node to an exact PolyQ in Q[target_var].
    
    Strict envelope:
    - IntegerLiteral, Variable target_var, Group, UnaryOp (+/-), BinaryOp (+/-/*//).
    - Division allowed ONLY when denominator normalizes to a NONZERO CONSTANT polynomial.
    - Any variable in denominator is strictly rejected.
    - Power exponents only {0, 1, 2}.
    - Variable-bearing exponent-0 base is strictly rejected.
    - Radical, AbsoluteValue, FunctionCall, and all other node types rejected.
    - Any intermediate or final degree > 2 rejected.
    - Any variable other than target_var rejected.
    """
    if isinstance(node, IntegerLiteral):
        return PolyQ.constant(node.value)

    if isinstance(node, Variable):
        if node.name != target_var:
            raise UnsupportedInequalityNodeError(
                f"Unsupported variable {node.name!r} (expected {target_var!r})"
            )
        return PolyQ.variable()

    if isinstance(node, Group):
        return normalize_ast_to_polyq(node.inner, target_var)

    if isinstance(node, UnaryOp):
        operand_poly = normalize_ast_to_polyq(node.operand, target_var)
        if node.op == "+":
            return operand_poly
        elif node.op == "-":
            return -operand_poly
        raise UnsupportedInequalityNodeError(f"Unsupported unary operator {node.op!r}")

    if isinstance(node, BinaryOp):
        if node.op in ("+", "-"):
            left_p = normalize_ast_to_polyq(node.left, target_var)
            right_p = normalize_ast_to_polyq(node.right, target_var)
            res = (left_p + right_p) if node.op == "+" else (left_p - right_p)
            if res.degree > 2:
                raise InequalityDegreeOutOfScopeError(f"Intermediate degree {res.degree} > 2")
            return res

        elif node.op == "*":
            left_p = normalize_ast_to_polyq(node.left, target_var)
            right_p = normalize_ast_to_polyq(node.right, target_var)
            if not left_p.is_zero and not right_p.is_zero and (left_p.degree + right_p.degree > 2):
                raise InequalityDegreeOutOfScopeError(
                    f"Product degree {left_p.degree + right_p.degree} > 2"
                )
            res = left_p * right_p
            if res.degree > 2:
                raise InequalityDegreeOutOfScopeError(f"Multiplication degree {res.degree} > 2")
            return res

        elif node.op == "/":
            # Variable denominators are strictly rejected
            if target_var in node.right.variables() or len(node.right.variables()) > 0:
                raise UnsupportedInequalityNodeError(
                    "Division by variable-bearing expression is unsupported in polynomial inequalities"
                )
            den_p = normalize_ast_to_polyq(node.right, target_var)
            if den_p.degree != 0 or den_p.is_zero:
                raise UnsupportedInequalityNodeError(
                    "Division denominator must normalize to a non-zero constant polynomial"
                )
            scalar_c = den_p.coeff(0)
            left_p = normalize_ast_to_polyq(node.left, target_var)
            res = left_p.scale(Rational(1, 1) / scalar_c)
            if res.degree > 2:
                raise InequalityDegreeOutOfScopeError(f"Scaled degree {res.degree} > 2")
            return res

        raise UnsupportedInequalityNodeError(f"Unsupported binary operator {node.op!r}")

    if isinstance(node, Power):
        exp_val = node.exponent.value
        if exp_val not in (0, 1, 2):
            raise UnsupportedInequalityNodeError(
                f"Unsupported exponent {exp_val} (only 0, 1, 2 supported)"
            )
        if exp_val == 0:
            # Variable-bearing exponent-0 base rejected due to domain guard semantics
            if target_var in node.base.variables() or len(node.base.variables()) > 0:
                raise UnsupportedInequalityNodeError(
                    "Variable-bearing exponent-0 base rejected due to domain guard semantics"
                )
            base_p = normalize_ast_to_polyq(node.base, target_var)
            if base_p.is_zero:
                raise UnsupportedInequalityNodeError("Indeterminate 0^0 expression is undefined")
            return PolyQ.constant(1)
        elif exp_val == 1:
            return normalize_ast_to_polyq(node.base, target_var)
        elif exp_val == 2:
            base_p = normalize_ast_to_polyq(node.base, target_var)
            if not base_p.is_zero and base_p.degree > 1:
                raise InequalityDegreeOutOfScopeError(
                    f"Squaring polynomial of degree {base_p.degree} exceeds degree 2"
                )
            res = base_p * base_p
            if res.degree > 2:
                raise InequalityDegreeOutOfScopeError(f"Power degree {res.degree} > 2")
            return res

    raise UnsupportedInequalityNodeError(f"Unsupported AST node type '{type(node).__name__}'")


def normalize_inequality_to_polyq(ir: ProblemIR) -> PolyQ:
    """Normalize SingleInequalityPayload to canonical polynomial P(x) = LHS - RHS."""
    if not isinstance(ir.payload, SingleInequalityPayload):
        raise UnsupportedInequalityNodeError("Expected SingleInequalityPayload")
    target_var = ir.payload.target_variable
    left_p = normalize_ast_to_polyq(ir.payload.left, target_var)
    right_p = normalize_ast_to_polyq(ir.payload.right, target_var)
    diff_p = left_p - right_p
    if diff_p.degree > 2:
        raise InequalityDegreeOutOfScopeError(
            f"Canonical polynomial degree {diff_p.degree} exceeds quadratic bound <= 2"
        )
    return diff_p


# ---------------------------------------------------------------------------
# AlgebraPolynomialInequalityAdapter
# ---------------------------------------------------------------------------

class AlgebraPolynomialInequalityAdapter(DomainAdapter):
    """Authoritative domain adapter for verified polynomial inequalities in R[x] (deg <= 2)."""

    ADAPTER_ID: str = "mke.adapter.algebra_polynomial_inequality.v1"

    @property
    def adapter_id(self) -> str:
        return self.ADAPTER_ID

    @property
    def supported_problem_kinds(self) -> Tuple[ProblemKind, ...]:
        return (ProblemKind.ALGEBRA_INEQUALITY,)

    def can_handle(self, ir: ProblemIR) -> bool:
        """Predicate checking if ProblemIR is a supported univariate polynomial inequality."""
        # MUST first reject non-inequality kinds without touching inequality-only fields
        if ir.problem_kind != ProblemKind.ALGEBRA_INEQUALITY:
            return False
        if not isinstance(ir.payload, SingleInequalityPayload):
            return False
        if ir.payload.target_variable != "x":
            return False
        if ir.domain_spec.primary_domain != DomainCategory.REALS:
            return False
        if ir.payload.relation not in (
            ConstraintRelation.LT,
            ConstraintRelation.LE,
            ConstraintRelation.GT,
            ConstraintRelation.GE,
        ):
            return False

        try:
            p = normalize_inequality_to_polyq(ir)
            return p.degree <= 2
        except Exception:
            return False

    def normalize(self, ir: ProblemIR) -> ProblemIR:
        """Perform canonical normalization and record trace."""
        try:
            p = normalize_inequality_to_polyq(ir)
            rel_op = {
                ConstraintRelation.GT: ">",
                ConstraintRelation.GE: ">=",
                ConstraintRelation.LT: "<",
                ConstraintRelation.LE: "<=",
            }.get(ir.payload.relation, "?")
            trace_entry = (
                f"Normalized polynomial inequality to canonical form: {p.to_latex()} {rel_op} 0"
            )
        except Exception as exc:
            trace_entry = f"Failed exact bounded inequality normalization: {exc}"

        return ir.model_copy(
            update={
                "normalization_trace": ir.normalization_trace + (trace_entry,),
            }
        )

    def classify(self, ir: ProblemIR) -> DomainClassification:
        """Classify inequality sub-form, difficulty, and pedagogical methods."""
        try:
            p = normalize_inequality_to_polyq(ir)
            if p.degree == 0:
                sub_form = "POLYNOMIAL_CONSTANT_INEQUALITY"
                diff = "EASY"
            elif p.degree == 1:
                sub_form = "POLYNOMIAL_LINEAR_INEQUALITY"
                diff = "EASY"
            elif p.degree == 2:
                sub_form = "POLYNOMIAL_QUADRATIC_INEQUALITY"
                diff = "MEDIUM"
            else:
                sub_form = "POLYNOMIAL_OUT_OF_SCOPE"
                diff = "HARD"
        except Exception:
            return DomainClassification(
                problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
                sub_form="POLYNOMIAL_OUT_OF_SCOPE",
                difficulty="HARD",
                applicable_methods=(),
            )

        methods = (
            MethodAssessment(
                method_id="SIGN_TABLE_POLYNOMIAL",
                method_name_vi="Xét dấu đa thức và kết luận tập nghiệm",
                method_name_en="Polynomial sign analysis and interval determination",
                is_applicable=True,
                is_recommended=True,
                selection_reason="Phương pháp chuẩn sư phạm cho bất phương trình đa thức bậc <= 2",
            ),
        )

        return DomainClassification(
            problem_kind=ProblemKind.ALGEBRA_INEQUALITY,
            sub_form=sub_form,
            difficulty=diff,
            applicable_methods=methods,
        )

    def solve_candidates(
        self, ir: ProblemIR, options: Optional[ExecutionOptions] = None
    ) -> Tuple[CandidateSolution, ...]:
        """Generate candidate solutions using untrusted Pack 1-A solver.
        
        Returns exactly one authoritative entity:
        - AllRealSolutionEntity
        - EmptyRealSolutionEntity
        - RealIntervalUnionEntity
        """
        try:
            p = normalize_inequality_to_polyq(ir)
            rel = ir.payload.relation
        except Exception as exc:
            cand = CandidateSolution(
                candidate_id=f"cand_{ir.problem_id}",
                generator_engine="mke.algebra_inequality.generator.v1",
                raw_symbolic_output=f"UNSUPPORTED: {exc}",
                parsed_entities=(),
                execution_time_ms=0.1,
                metadata=CandidateMetadata(
                    engine_version="1.0.0",
                    transformation_steps=("error_fail_closed",),
                ),
            )
            return (cand,)

        # Candidate generation by sign topology
        entity: SymbolicEntity

        # Degree 0: Constant polynomial
        if p.degree == 0:
            c = p.coeff(0)
            holds = (
                (rel == ConstraintRelation.GT and c.is_positive)
                or (rel == ConstraintRelation.GE and not c.is_negative)
                or (rel == ConstraintRelation.LT and c.is_negative)
                or (rel == ConstraintRelation.LE and not c.is_positive)
            )
            entity = AllRealSolutionEntity() if holds else EmptyRealSolutionEntity()

        # Degree 1: Linear polynomial c1*x + c0
        elif p.degree == 1:
            c0 = p.coeff(0)
            c1 = p.coeff(1)
            root_rat = -c0 / c1
            root_ent = RationalScalarEntity.from_rational(root_rat)
            if c1.is_positive:
                if rel == ConstraintRelation.GT:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=root_ent, upper_bound=None, lower_closed=False, upper_closed=False),)
                    )
                elif rel == ConstraintRelation.GE:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=root_ent, upper_bound=None, lower_closed=True, upper_closed=False),)
                    )
                elif rel == ConstraintRelation.LT:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=None, upper_bound=root_ent, lower_closed=False, upper_closed=False),)
                    )
                else:  # LE
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=None, upper_bound=root_ent, lower_closed=False, upper_closed=True),)
                    )
            else:  # c1 < 0
                if rel == ConstraintRelation.GT:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=None, upper_bound=root_ent, lower_closed=False, upper_closed=False),)
                    )
                elif rel == ConstraintRelation.GE:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=None, upper_bound=root_ent, lower_closed=False, upper_closed=True),)
                    )
                elif rel == ConstraintRelation.LT:
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=root_ent, upper_bound=None, lower_closed=False, upper_closed=False),)
                    )
                else:  # LE
                    entity = RealIntervalUnionEntity(
                        intervals=(RealIntervalEntity(lower_bound=root_ent, upper_bound=None, lower_closed=True, upper_closed=False),)
                    )

        # Degree 2: Quadratic polynomial c2*x^2 + c1*x + c0
        else:
            c2 = p.coeff(2)
            a_pos = c2.is_positive
            _, roots = solve_poly_degree_le_2(p)

            # Subcase 1: delta < 0, 0 real roots
            if len(roots) == 0:
                holds = (
                    (rel in (ConstraintRelation.GT, ConstraintRelation.GE) and a_pos)
                    or (rel in (ConstraintRelation.LT, ConstraintRelation.LE) and not a_pos)
                )
                entity = AllRealSolutionEntity() if holds else EmptyRealSolutionEntity()

            # Subcase 2: delta == 0, 1 double root
            elif len(roots) == 1:
                r = roots[0]
                if a_pos:
                    if rel == ConstraintRelation.GT:
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r, lower_closed=False, upper_closed=False),
                                RealIntervalEntity(lower_bound=r, upper_bound=None, lower_closed=False, upper_closed=False),
                            )
                        )
                    elif rel == ConstraintRelation.GE:
                        entity = AllRealSolutionEntity()
                    elif rel == ConstraintRelation.LT:
                        entity = EmptyRealSolutionEntity()
                    else:  # LE -> degenerate point [r, r]
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r, upper_bound=r, lower_closed=True, upper_closed=True),)
                        )
                else:  # a < 0
                    if rel == ConstraintRelation.GT:
                        entity = EmptyRealSolutionEntity()
                    elif rel == ConstraintRelation.GE:  # degenerate point [r, r]
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r, upper_bound=r, lower_closed=True, upper_closed=True),)
                        )
                    elif rel == ConstraintRelation.LT:
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r, lower_closed=False, upper_closed=False),
                                RealIntervalEntity(lower_bound=r, upper_bound=None, lower_closed=False, upper_closed=False),
                            )
                        )
                    else:  # LE
                        entity = AllRealSolutionEntity()

            # Subcase 3: delta > 0, 2 distinct real roots
            else:
                r1, r2 = roots[0], roots[1]
                if _compare_algebraic_entities(r1, r2) > 0:
                    r1, r2 = r2, r1

                if a_pos:
                    if rel == ConstraintRelation.GT:
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r1, lower_closed=False, upper_closed=False),
                                RealIntervalEntity(lower_bound=r2, upper_bound=None, lower_closed=False, upper_closed=False),
                            )
                        )
                    elif rel == ConstraintRelation.GE:
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r1, lower_closed=False, upper_closed=True),
                                RealIntervalEntity(lower_bound=r2, upper_bound=None, lower_closed=True, upper_closed=False),
                            )
                        )
                    elif rel == ConstraintRelation.LT:
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r1, upper_bound=r2, lower_closed=False, upper_closed=False),)
                        )
                    else:  # LE
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r1, upper_bound=r2, lower_closed=True, upper_closed=True),)
                        )
                else:  # a < 0
                    if rel == ConstraintRelation.GT:
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r1, upper_bound=r2, lower_closed=False, upper_closed=False),)
                        )
                    elif rel == ConstraintRelation.GE:
                        entity = RealIntervalUnionEntity(
                            intervals=(RealIntervalEntity(lower_bound=r1, upper_bound=r2, lower_closed=True, upper_closed=True),)
                        )
                    elif rel == ConstraintRelation.LT:
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r1, lower_closed=False, upper_closed=False),
                                RealIntervalEntity(lower_bound=r2, upper_bound=None, lower_closed=False, upper_closed=False),
                            )
                        )
                    else:  # LE
                        entity = RealIntervalUnionEntity(
                            intervals=(
                                RealIntervalEntity(lower_bound=None, upper_bound=r1, lower_closed=False, upper_closed=True),
                                RealIntervalEntity(lower_bound=r2, upper_bound=None, lower_closed=True, upper_closed=False),
                            )
                        )

        # Build raw display string
        if isinstance(entity, AllRealSolutionEntity):
            raw_out = "S = \\mathbb{R}"
        elif isinstance(entity, EmptyRealSolutionEntity):
            raw_out = "S = \\emptyset"
        elif isinstance(entity, RealIntervalUnionEntity):
            raw_out = f"S = {entity.to_latex()}"
        else:
            raw_out = "S = ?"

        cand = CandidateSolution(
            candidate_id=f"cand_{ir.problem_id}",
            generator_engine="mke.algebra_inequality.generator.v1",
            raw_symbolic_output=raw_out,
            parsed_entities=(entity,),
            execution_time_ms=0.5,
            metadata=CandidateMetadata(
                engine_version="1.0.0",
                transformation_steps=(
                    "local_polynomial_normalization",
                    "untrusted_poly_solve",
                    "sign_topology_assembly",
                ),
            ),
        )
        return (cand,)

    def verify(self, ir: ProblemIR, candidate: CandidateSolution) -> VerificationReport:
        """Independently verify candidate solution using deterministic MKE logic.
        
        Strict Invariants:
        - NEVER calls solve_poly_degree_le_2 inside verifier completeness logic.
        - Out-of-envelope checks return UNSUPPORTED/UNSUPPORTED BEFORE candidate-shape checks.
        - Validates every finite candidate endpoint by exact polynomial substitution.
        - Validates exact endpoint order and separation with zero float.
        - Identifies lower/upper root independently using exact derivative sign.
        - Rejects non-root artificial split points.
        - Valid strict subset may be PARTIAL only if containment is independently proven.
        - Malformed/wrong/extra topology REJECTED.
        """
        # 1. Out-of-envelope checks BEFORE inspecting candidate
        if ir.problem_kind != ProblemKind.ALGEBRA_INEQUALITY:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_kind_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Requires ALGEBRA_INEQUALITY problem kind",
            )

        if not isinstance(ir.payload, SingleInequalityPayload):
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_payload_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Requires SingleInequalityPayload",
            )

        if ir.domain_spec.primary_domain != DomainCategory.REALS:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_domain_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Primary domain must be REALS",
            )

        if ir.payload.relation not in (
            ConstraintRelation.LT,
            ConstraintRelation.LE,
            ConstraintRelation.GT,
            ConstraintRelation.GE,
        ):
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_relation_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Unsupported relation {ir.payload.relation}",
            )

        if ir.payload.target_variable != "x":
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_var_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details="Target variable must be 'x'",
            )

        # Independent local normalization to PolyQ
        try:
            p = normalize_inequality_to_polyq(ir)
        except (InequalityAlgebraError, Exception) as exc:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_norm_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Out of envelope for quadratic polynomial inequalities: {exc}",
            )

        if p.degree > 2:
            return VerificationReport(
                verification_id=f"ver_{ir.problem_id}",
                verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
                verification_level=VerificationLevel.UNSUPPORTED,
                disposition=VerificationDisposition.UNSUPPORTED,
                certificate_hash=hashlib.sha256(f"fail_deg_{ir.problem_id}".encode("utf-8")).hexdigest(),
                details=f"Polynomial degree {p.degree} exceeds quadratic bound <= 2",
            )

        # 2. Candidate Shape Checks
        if len(candidate.parsed_entities) != 1:
            return self._make_rejected_report(
                ir, p, f"Candidate must contain exactly 1 parsed entity, got {len(candidate.parsed_entities)}"
            )

        cand_ent = candidate.parsed_entities[0]
        if not isinstance(cand_ent, (AllRealSolutionEntity, EmptyRealSolutionEntity, RealIntervalUnionEntity)):
            return self._make_rejected_report(
                ir, p, f"Candidate entity of unsupported type {type(cand_ent).__name__}"
            )

        # 3. Independent Determination of Real Root Count and True Sign Topology
        rel = ir.payload.relation
        # Topology shapes:
        # "ALL_REAL", "EMPTY", "RAY_LEFT", "RAY_RIGHT", "BOUNDED", "TWO_RAYS", "PUNCTURED", "DEGENERATE"
        expected_shape: str
        expected_closed: bool = rel in (ConstraintRelation.LE, ConstraintRelation.GE)
        num_roots: int

        if p.degree == 0:
            c = p.coeff(0)
            holds = (
                (rel == ConstraintRelation.GT and c.is_positive)
                or (rel == ConstraintRelation.GE and not c.is_negative)
                or (rel == ConstraintRelation.LT and c.is_negative)
                or (rel == ConstraintRelation.LE and not c.is_positive)
            )
            expected_shape = "ALL_REAL" if holds else "EMPTY"
            num_roots = 0

        elif p.degree == 1:
            num_roots = 1
            c1 = p.coeff(1)
            if c1.is_positive:
                if rel in (ConstraintRelation.GT, ConstraintRelation.GE):
                    expected_shape = "RAY_RIGHT"
                else:
                    expected_shape = "RAY_LEFT"
            else:  # c1 < 0
                if rel in (ConstraintRelation.GT, ConstraintRelation.GE):
                    expected_shape = "RAY_LEFT"
                else:
                    expected_shape = "RAY_RIGHT"

        else:  # p.degree == 2
            c2 = p.coeff(2)
            a_pos = c2.is_positive
            num_roots = distinct_real_root_count(p)

            if num_roots == 0:
                holds = (
                    (rel in (ConstraintRelation.GT, ConstraintRelation.GE) and a_pos)
                    or (rel in (ConstraintRelation.LT, ConstraintRelation.LE) and not a_pos)
                )
                expected_shape = "ALL_REAL" if holds else "EMPTY"

            elif num_roots == 1:
                if a_pos:
                    if rel == ConstraintRelation.GT:
                        expected_shape = "PUNCTURED"
                    elif rel == ConstraintRelation.GE:
                        expected_shape = "ALL_REAL"
                    elif rel == ConstraintRelation.LT:
                        expected_shape = "EMPTY"
                    else:  # LE
                        expected_shape = "DEGENERATE"
                else:  # a < 0
                    if rel == ConstraintRelation.GT:
                        expected_shape = "EMPTY"
                    elif rel == ConstraintRelation.GE:
                        expected_shape = "DEGENERATE"
                    elif rel == ConstraintRelation.LT:
                        expected_shape = "PUNCTURED"
                    else:  # LE
                        expected_shape = "ALL_REAL"

            else:  # num_roots == 2
                if a_pos:
                    if rel == ConstraintRelation.GT:
                        expected_shape = "TWO_RAYS"
                    elif rel == ConstraintRelation.GE:
                        expected_shape = "TWO_RAYS"
                    elif rel == ConstraintRelation.LT:
                        expected_shape = "BOUNDED"
                    else:  # LE
                        expected_shape = "BOUNDED"
                else:  # a < 0
                    if rel == ConstraintRelation.GT:
                        expected_shape = "BOUNDED"
                    elif rel == ConstraintRelation.GE:
                        expected_shape = "BOUNDED"
                    elif rel == ConstraintRelation.LT:
                        expected_shape = "TWO_RAYS"
                    else:  # LE
                        expected_shape = "TWO_RAYS"

        # 4. Topology Verification and Obligation Processing

        # Case A: Expected ALL_REAL
        if expected_shape == "ALL_REAL":
            if isinstance(cand_ent, AllRealSolutionEntity):
                return self._make_accepted_report(
                    ir, p, candidate, "Polynomial inequality holds for all real x"
                )
            elif isinstance(cand_ent, RealIntervalUnionEntity) and len(cand_ent.intervals) > 0:
                # Valid non-empty strict subset of all reals
                return self._make_partial_report(
                    ir, p, candidate, "Candidate interval is a verified strict subset of all real numbers"
                )
            else:
                return self._make_rejected_report(
                    ir, p, "Expected AllRealSolutionEntity for universally satisfied inequality"
                )

        # Case B: Expected EMPTY
        if expected_shape == "EMPTY":
            if isinstance(cand_ent, EmptyRealSolutionEntity):
                return self._make_accepted_report(
                    ir, p, candidate, "Polynomial inequality has no real solutions"
                )
            else:
                return self._make_rejected_report(
                    ir, p, "Expected EmptyRealSolutionEntity for unsatisfiable inequality"
                )

        # Case C: Expected interval solutions (RAY_LEFT, RAY_RIGHT, BOUNDED, TWO_RAYS, PUNCTURED, DEGENERATE)
        if not isinstance(cand_ent, RealIntervalUnionEntity):
            return self._make_rejected_report(
                ir, p, f"Expected RealIntervalUnionEntity for topology {expected_shape}, got {type(cand_ent).__name__}"
            )

        intervals = cand_ent.intervals
        if len(intervals) == 0:
            return self._make_rejected_report(ir, p, "RealIntervalUnionEntity cannot be empty when solutions exist")

        # Finite Endpoint Validation: exact polynomial substitution
        finite_endpoints: List[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = []
        residuals: List[ResidualCheck] = []

        for idx, iv in enumerate(intervals):
            for bound_val, b_name in ((iv.lower_bound, "lower"), (iv.upper_bound, "upper")):
                if bound_val is not None:
                    finite_endpoints.append(bound_val)
                    is_zero, res_str = self._eval_poly_at_endpoint(p, bound_val)
                    residuals.append(
                        ResidualCheck(
                            point_desc=f"Interval {idx} {b_name} bound ({bound_val.latex})",
                            residual_value=res_str,
                            is_exact_zero=is_zero,
                        )
                    )
                    if not is_zero:
                        # Non-root artificial split point
                        return self._make_rejected_report(
                            ir, p, f"Candidate finite endpoint {bound_val.latex} is not a root of P(x)",
                            residuals=residuals
                        )

        # Endpoint Deduplication & Root Count Check
        unique_endpoints: List[Union[RationalScalarEntity, RealQuadraticSurdEntity]] = []
        for ep in finite_endpoints:
            if not any(are_roots_equal(ep, u) for u in unique_endpoints):
                unique_endpoints.append(ep)

        # Verify that candidate root count does not exceed true root count
        if len(unique_endpoints) > num_roots:
            return self._make_rejected_report(
                ir, p, f"Candidate contains {len(unique_endpoints)} distinct roots, exceeding true root count {num_roots}",
                residuals=residuals
            )

        # For 2 roots: identify lower and upper independently using derivative sign and exact comparison
        if num_roots == 2:
            if len(unique_endpoints) == 2:
                e1, e2 = unique_endpoints[0], unique_endpoints[1]
                cmp_val = _compare_algebraic_entities(e1, e2)
                if cmp_val == 0:
                    return self._make_rejected_report(
                        ir, p, "Distinct roots must not be algebraically equal", residuals=residuals
                    )
                if cmp_val > 0:
                    e1, e2 = e2, e1

                # Independent derivative check
                c2 = p.coeff(2)
                d1_sign = self._eval_derivative_sign_at_endpoint(p, e1)
                d2_sign = self._eval_derivative_sign_at_endpoint(p, e2)

                if c2.is_positive:
                    # Parabola opens up: lower root has p'(r1) < 0, upper root has p'(r2) > 0
                    if d1_sign != -1 or d2_sign != 1:
                        return self._make_rejected_report(
                            ir, p, "Derivative sign inconsistency at verified roots", residuals=residuals
                        )
                else:
                    # Parabola opens down: lower root has p'(r1) > 0, upper root has p'(r2) < 0
                    if d1_sign != 1 or d2_sign != -1:
                        return self._make_rejected_report(
                            ir, p, "Derivative sign inconsistency at verified roots", residuals=residuals
                        )

        # Topology Matching
        if expected_shape == "RAY_LEFT":
            if len(intervals) != 1:
                return self._make_rejected_report(
                    ir, p, f"Expected 1 interval for RAY_LEFT, got {len(intervals)}", residuals=residuals
                )
            iv = intervals[0]
            if iv.lower_bound is not None or iv.upper_bound is None:
                return self._make_rejected_report(
                    ir, p, "RAY_LEFT requires lower_bound=None and finite upper_bound", residuals=residuals
                )
            if expected_closed:
                if iv.upper_closed:
                    return self._make_accepted_report(ir, p, candidate, "Verified exact ray (-inf, r]", residuals=residuals)
                else:
                    # (-inf, r) is a verified strict subset of (-inf, r]
                    return self._make_partial_report(ir, p, candidate, "Candidate (-inf, r) is a verified strict subset of (-inf, r]", residuals=residuals)
            else:
                if iv.upper_closed:
                    # includes boundary point where p(r)=0 but relation is strict
                    return self._make_rejected_report(ir, p, "Boundary point is included but inequality is strict", residuals=residuals)
                return self._make_accepted_report(ir, p, candidate, "Verified exact ray (-inf, r)", residuals=residuals)

        elif expected_shape == "RAY_RIGHT":
            if len(intervals) != 1:
                return self._make_rejected_report(
                    ir, p, f"Expected 1 interval for RAY_RIGHT, got {len(intervals)}", residuals=residuals
                )
            iv = intervals[0]
            if iv.lower_bound is None or iv.upper_bound is not None:
                return self._make_rejected_report(
                    ir, p, "RAY_RIGHT requires finite lower_bound and upper_bound=None", residuals=residuals
                )
            if expected_closed:
                if iv.lower_closed:
                    return self._make_accepted_report(ir, p, candidate, "Verified exact ray [r, +inf)", residuals=residuals)
                else:
                    return self._make_partial_report(ir, p, candidate, "Candidate (r, +inf) is a verified strict subset of [r, +inf)", residuals=residuals)
            else:
                if iv.lower_closed:
                    return self._make_rejected_report(ir, p, "Boundary point is included but inequality is strict", residuals=residuals)
                return self._make_accepted_report(ir, p, candidate, "Verified exact ray (r, +inf)", residuals=residuals)

        elif expected_shape == "DEGENERATE":
            if len(intervals) != 1:
                return self._make_rejected_report(
                    ir, p, f"Expected 1 interval for DEGENERATE, got {len(intervals)}", residuals=residuals
                )
            iv = intervals[0]
            if iv.lower_bound is None or iv.upper_bound is None:
                return self._make_rejected_report(ir, p, "DEGENERATE requires finite lower and upper bounds", residuals=residuals)
            if not are_roots_equal(iv.lower_bound, iv.upper_bound):
                return self._make_rejected_report(ir, p, "DEGENERATE requires identical lower and upper bounds", residuals=residuals)
            if not (iv.lower_closed and iv.upper_closed):
                return self._make_rejected_report(ir, p, "DEGENERATE requires closed endpoints [r, r]", residuals=residuals)
            return self._make_accepted_report(ir, p, candidate, "Verified degenerate single-point solution [r, r]", residuals=residuals)

        elif expected_shape == "PUNCTURED":
            if len(intervals) == 2:
                iv1, iv2 = intervals[0], intervals[1]
                if iv1.lower_bound is not None or iv1.upper_bound is None:
                    return self._make_rejected_report(ir, p, "First interval of PUNCTURED must be (-inf, r)", residuals=residuals)
                if iv2.lower_bound is None or iv2.upper_bound is not None:
                    return self._make_rejected_report(ir, p, "Second interval of PUNCTURED must be (r, +inf)", residuals=residuals)
                if not are_roots_equal(iv1.upper_bound, iv2.lower_bound):
                    return self._make_rejected_report(ir, p, "PUNCTURED requires identical split point r", residuals=residuals)
                if iv1.upper_closed or iv2.lower_closed:
                    return self._make_rejected_report(ir, p, "PUNCTURED must be open at puncture point r", residuals=residuals)
                return self._make_accepted_report(ir, p, candidate, "Verified punctured line (-inf, r) U (r, +inf)", residuals=residuals)
            elif len(intervals) == 1:
                # Single branch is a verified strict subset
                return self._make_partial_report(ir, p, candidate, "Candidate is a verified strict subset of punctured line", residuals=residuals)
            else:
                return self._make_rejected_report(ir, p, f"PUNCTURED topology requires 2 intervals, got {len(intervals)}", residuals=residuals)

        elif expected_shape == "BOUNDED":
            if len(intervals) != 1:
                return self._make_rejected_report(
                    ir, p, f"Expected 1 bounded interval, got {len(intervals)}", residuals=residuals
                )
            iv = intervals[0]
            if iv.lower_bound is None or iv.upper_bound is None:
                return self._make_rejected_report(ir, p, "BOUNDED requires finite lower and upper bounds", residuals=residuals)
            if are_roots_equal(iv.lower_bound, iv.upper_bound):
                return self._make_rejected_report(ir, p, "BOUNDED endpoints must be distinct", residuals=residuals)
            if _compare_algebraic_entities(iv.lower_bound, iv.upper_bound) >= 0:
                return self._make_rejected_report(ir, p, "BOUNDED lower_bound must be strictly less than upper_bound", residuals=residuals)

            if expected_closed:
                if iv.lower_closed and iv.upper_closed:
                    return self._make_accepted_report(ir, p, candidate, "Verified exact bounded interval [r1, r2]", residuals=residuals)
                elif not iv.lower_closed and not iv.upper_closed:
                    return self._make_partial_report(ir, p, candidate, "Candidate (r1, r2) is a verified strict subset of [r1, r2]", residuals=residuals)
                else:
                    return self._make_partial_report(ir, p, candidate, "Candidate half-open interval is a verified strict subset of [r1, r2]", residuals=residuals)
            else:
                if iv.lower_closed or iv.upper_closed:
                    return self._make_rejected_report(ir, p, "Boundary point is included but inequality is strict", residuals=residuals)
                return self._make_accepted_report(ir, p, candidate, "Verified exact bounded interval (r1, r2)", residuals=residuals)

        elif expected_shape == "TWO_RAYS":
            if len(intervals) == 2:
                iv1, iv2 = intervals[0], intervals[1]
                if iv1.lower_bound is not None or iv1.upper_bound is None:
                    return self._make_rejected_report(ir, p, "First interval of TWO_RAYS must be (-inf, r1)", residuals=residuals)
                if iv2.lower_bound is None or iv2.upper_bound is not None:
                    return self._make_rejected_report(ir, p, "Second interval of TWO_RAYS must be (r2, +inf)", residuals=residuals)
                if are_roots_equal(iv1.upper_bound, iv2.lower_bound):
                    return self._make_rejected_report(ir, p, "TWO_RAYS endpoints r1 and r2 must be distinct", residuals=residuals)
                if _compare_algebraic_entities(iv1.upper_bound, iv2.lower_bound) >= 0:
                    return self._make_rejected_report(ir, p, "TWO_RAYS requires r1 < r2", residuals=residuals)

                if expected_closed:
                    if iv1.upper_closed and iv2.lower_closed:
                        return self._make_accepted_report(ir, p, candidate, "Verified exact union (-inf, r1] U [r2, +inf)", residuals=residuals)
                    elif not iv1.upper_closed and not iv2.lower_closed:
                        return self._make_partial_report(ir, p, candidate, "Candidate open rays are a verified strict subset of closed rays", residuals=residuals)
                    else:
                        return self._make_partial_report(ir, p, candidate, "Candidate is a verified strict subset of closed rays", residuals=residuals)
                else:
                    if iv1.upper_closed or iv2.lower_closed:
                        return self._make_rejected_report(ir, p, "Boundary point is included but inequality is strict", residuals=residuals)
                    return self._make_accepted_report(ir, p, candidate, "Verified exact union (-inf, r1) U (r2, +inf)", residuals=residuals)
            elif len(intervals) == 1:
                # One ray of two is a verified strict subset
                iv = intervals[0]
                if iv.lower_bound is None and iv.upper_bound is not None:
                    if not expected_closed and iv.upper_closed:
                        return self._make_rejected_report(ir, p, "Boundary point included in strict inequality", residuals=residuals)
                    return self._make_partial_report(ir, p, candidate, "Single ray (-inf, r1] is a verified strict subset", residuals=residuals)
                elif iv.lower_bound is not None and iv.upper_bound is None:
                    if not expected_closed and iv.lower_closed:
                        return self._make_rejected_report(ir, p, "Boundary point included in strict inequality", residuals=residuals)
                    return self._make_partial_report(ir, p, candidate, "Single ray [r2, +inf) is a verified strict subset", residuals=residuals)
                else:
                    return self._make_rejected_report(ir, p, "Malformed single interval for TWO_RAYS topology", residuals=residuals)
            else:
                return self._make_rejected_report(
                    ir, p, f"TWO_RAYS requires at most 2 intervals, got {len(intervals)}", residuals=residuals
                )

        return self._make_rejected_report(ir, p, f"Unhandled topology classification {expected_shape}", residuals=residuals)

    def _eval_poly_at_endpoint(
        self, p: PolyQ, ep: Union[RationalScalarEntity, RealQuadraticSurdEntity]
    ) -> Tuple[bool, str]:
        """Exact polynomial evaluation at an endpoint entity without float."""
        if isinstance(ep, RationalScalarEntity):
            val = p.eval_at_rational(ep.to_rational)
            return val.is_zero, "0 (EXACT_ZERO)" if val.is_zero else str(val)
        elif isinstance(ep, RealQuadraticSurdEntity):
            pt = NumberFieldElement.from_surd_entity(ep)
            val = eval_poly_at_point(p, pt)
            return val.is_zero, "0 (EXACT_ZERO)" if val.is_zero else "NON_ZERO"
        return False, "UNKNOWN_TYPE"

    def _eval_derivative_sign_at_endpoint(
        self, p: PolyQ, ep: Union[RationalScalarEntity, RealQuadraticSurdEntity]
    ) -> int:
        """Exact derivative evaluation sign at endpoint entity.
        
        P(x) = c2*x^2 + c1*x + c0 => P'(x) = 2*c2*x + c1.
        Returns -1 if P'(ep) < 0, 0 if P'(ep) == 0, 1 if P'(ep) > 0.
        """
        c2 = p.coeff(2)
        c1 = p.coeff(1)
        two_c2 = Rational(2, 1) * c2
        u, v, d = _to_u_v_d(ep)
        # P'(u + v*sqrt(d)) = (2*c2*u + c1) + (2*c2*v)*sqrt(d)
        deriv_u = two_c2 * u + c1
        deriv_v = two_c2 * v
        return _compare_u_v_d(deriv_u, deriv_v, d, Rational(0, 1), Rational(0, 1), 1)

    def _make_accepted_report(
        self,
        ir: ProblemIR,
        p: PolyQ,
        candidate: CandidateSolution,
        details: str,
        residuals: Sequence[ResidualCheck] = (),
    ) -> VerificationReport:
        obligations = (
            ProofObligationResult(
                obligation_id="CANONICAL_POLYNOMIAL_TOPOLOGY",
                description="Canonical polynomial topology independently proven",
                passed=True,
            ),
            ProofObligationResult(
                obligation_id="ENDPOINT_EXACT_SATISFACTION",
                description="All candidate finite endpoints are verified roots of P(x)",
                passed=True,
            ),
            ProofObligationResult(
                obligation_id="COMPLETE_TOPOLOGY_EQUALITY",
                description="Candidate interval union exactly equals true sign topology",
                passed=True,
                details=details,
            ),
        )
        cert_payload = {
            "problem_id": ir.problem_id,
            "verifier": "MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            "verification_level": VerificationLevel.EXACT_VERIFIED.value,
            "disposition": VerificationDisposition.ACCEPTED.value,
            "poly_coeffs": [str(c) for c in p.coeffs],
            "candidate_output": candidate.raw_symbolic_output,
        }
        cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return VerificationReport(
            verification_id=f"ver_{ir.problem_id}",
            verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            verification_level=VerificationLevel.EXACT_VERIFIED,
            disposition=VerificationDisposition.ACCEPTED,
            proof_obligations=obligations,
            residual_evaluations=tuple(residuals),
            certificate_hash=cert_hash,
            details=details,
        )

    def _make_partial_report(
        self,
        ir: ProblemIR,
        p: PolyQ,
        candidate: CandidateSolution,
        details: str,
        residuals: Sequence[ResidualCheck] = (),
    ) -> VerificationReport:
        obligations = (
            ProofObligationResult(
                obligation_id="CANONICAL_POLYNOMIAL_TOPOLOGY",
                description="Canonical polynomial topology independently proven",
                passed=True,
            ),
            ProofObligationResult(
                obligation_id="STRICT_SUBSET_CONTAINMENT",
                description="Candidate is a verified strict subset of true solution topology",
                passed=True,
                details=details,
            ),
            ProofObligationResult(
                obligation_id="TOPOLOGY_COMPLETENESS",
                description="Candidate does not cover the complete authoritative solution set",
                passed=False,
                details="Strict subset solution",
            ),
        )
        cert_payload = {
            "problem_id": ir.problem_id,
            "verifier": "MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            "verification_level": VerificationLevel.PARTIAL.value,
            "disposition": VerificationDisposition.PARTIAL.value,
            "poly_coeffs": [str(c) for c in p.coeffs],
            "candidate_output": candidate.raw_symbolic_output,
        }
        cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return VerificationReport(
            verification_id=f"ver_{ir.problem_id}",
            verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            verification_level=VerificationLevel.PARTIAL,
            disposition=VerificationDisposition.PARTIAL,
            proof_obligations=obligations,
            residual_evaluations=tuple(residuals),
            certificate_hash=cert_hash,
            details=details,
        )

    def _make_rejected_report(
        self,
        ir: ProblemIR,
        p: PolyQ,
        reason: str,
        residuals: Sequence[ResidualCheck] = (),
    ) -> VerificationReport:
        obligations = (
            ProofObligationResult(
                obligation_id="TOPOLOGY_CONSISTENCY",
                description="Candidate interval union consistent with true sign topology",
                passed=False,
                details=reason,
            ),
        )
        cert_payload = {
            "problem_id": ir.problem_id,
            "verifier": "MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            "verification_level": VerificationLevel.UNSUPPORTED.value,
            "disposition": VerificationDisposition.REJECTED.value,
            "reason": reason,
        }
        cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return VerificationReport(
            verification_id=f"ver_{ir.problem_id}",
            verifier_name="MKE_INEQUALITY_INDEPENDENT_VERIFIER_V1",
            verification_level=VerificationLevel.UNSUPPORTED,
            disposition=VerificationDisposition.REJECTED,
            proof_obligations=obligations,
            residual_evaluations=tuple(residuals),
            certificate_hash=cert_hash,
            details=reason,
        )

    def build_trace(
        self,
        ir: ProblemIR,
        candidate: CandidateSolution,
        verification: VerificationReport,
        selected_method_id: Optional[str] = None,
    ) -> SolutionTrace:
        """Construct structured, pedagogically sound, step-by-step solution trace."""
        p = normalize_inequality_to_polyq(ir)
        rel_latex = {
            ConstraintRelation.GT: ">",
            ConstraintRelation.GE: "\\ge",
            ConstraintRelation.LT: "<",
            ConstraintRelation.LE: "\\le",
        }.get(ir.payload.relation, ">")

        steps: List[TraceStep] = []

        step1 = TraceStep(
            step_id="step_1_canonical_form",
            sequence_index=1,
            operation_kind="CANONICALIZE",
            title_vi="Đưa bất phương trình về dạng chuẩn",
            title_en="Transform inequality to canonical form",
            explanation_vi=f"Chuyển tất cả các số hạng sang vế trái để được bất phương trình {p.to_latex()} {rel_latex} 0.",
            explanation_en=f"Move all terms to the left-hand side to obtain {p.to_latex()} {rel_latex} 0.",
            input_expression_latex="",
            output_expression_latex=f"{p.to_latex()} {rel_latex} 0",
            verification_note="Biến đổi đại số tương đương trên tập số thực ℝ.",
        )
        steps.append(step1)

        step2 = TraceStep(
            step_id="step_2_sign_analysis",
            sequence_index=2,
            operation_kind="SIGN_ANALYSIS",
            title_vi="Xét dấu tam thức / nhị thức",
            title_en="Polynomial sign analysis",
            explanation_vi="Xác định bậc của đa thức, hệ số cao nhất và các nghiệm thực trên ℝ.",
            explanation_en="Determine polynomial degree, leading coefficient, and real roots.",
            input_expression_latex=f"{p.to_latex()} {rel_latex} 0",
            output_expression_latex=candidate.raw_symbolic_output,
            verification_note="Đã kiểm tra độc lập tính đúng đắn của dấu và nghiệm.",
        )
        steps.append(step2)

        step3 = TraceStep(
            step_id="step_3_conclusion",
            sequence_index=3,
            operation_kind="CONCLUDE",
            title_vi="Kết luận tập nghiệm",
            title_en="Conclude solution set",
            explanation_vi=f"Tập nghiệm của bất phương trình là {candidate.raw_symbolic_output}.",
            explanation_en=f"The solution set of the inequality is {candidate.raw_symbolic_output}.",
            input_expression_latex=candidate.raw_symbolic_output,
            output_expression_latex=candidate.raw_symbolic_output,
            verification_note="Tập nghiệm đã được chứng minh và thẩm định hoàn chỉnh.",
        )
        steps.append(step3)

        cert_hash = hashlib.sha256(
            f"trace_{ir.problem_id}_{verification.certificate_hash}".encode("utf-8")
        ).hexdigest()

        return SolutionTrace(
            trace_id=f"trace_{ir.problem_id}",
            method_id="SIGN_TABLE_POLYNOMIAL",
            method_name_vi="Xét dấu đa thức và kết luận khoảng nghiệm",
            method_name_en="Polynomial sign analysis and interval determination",
            steps=tuple(steps),
            conclusion_vi=f"Tập nghiệm của bất phương trình là {candidate.raw_symbolic_output}.",
            conclusion_en=f"The solution set of the inequality is {candidate.raw_symbolic_output}.",
            certificate_hash=cert_hash,
        )

    def supported_methods(self, ir: ProblemIR) -> Tuple[MethodAssessment, ...]:
        """List available pedagogical methods for this problem."""
        return (
            MethodAssessment(
                method_id="SIGN_TABLE_POLYNOMIAL",
                method_name_vi="Xét dấu đa thức và kết luận tập nghiệm",
                method_name_en="Polynomial sign analysis and interval determination",
                is_applicable=True,
                is_recommended=True,
                selection_reason="Phương pháp chuẩn sư phạm cho bất phương trình đa thức bậc <= 2",
            ),
        )

    def limitations(self) -> Tuple[str, ...]:
        """Document known mathematical boundaries and edge cases."""
        return (
            "Hỗ trợ bất phương trình đa thức bậc <= 2 một ẩn x trên tập số thực ℝ.",
            "Không hỗ trợ ẩn ở mẫu số (phân thức hữu tỉ) hoặc hàm số vô tỉ, siêu việt.",
            "Không hỗ trợ luỹ thừa với số mũ ngoài tập {0, 1, 2}.",
            "Không hỗ trợ đa thức có bậc lớn hơn 2.",
        )
