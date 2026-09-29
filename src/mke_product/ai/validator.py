"""Deterministic Pre-Dispatch MKE-IR Validator.

Phase 3, 4 & 5: Validates mathematical intermediate representations against strict
schemas, question format rules, source-span fidelity, per-expression provenance,
variable declarations, and syntactic AST validity using frozen CAS parsers without execution.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Union

from mke_product.ai.ir import (
    SUPPORTED_MKE_IR_SCHEMA_VERSION,
    ProblemCategory,
    QuestionFormat,
    SemanticVerificationStatus,
    SourceSpan,
    ExtractedConstraint,
    QuestionSubpart,
    UncertaintyFlag,
    ValidationIssue,
    ValidationResult,
    MathIntermediateRepresentation,
)
from mke_product.cas.cas_parser import (
    parse_cas_expression,
    parse_cas_equation,
    parse_cas_inequality,
    parse_cas_system,
    ParserError,
)
from mke_product.cas.contracts import OperationType


IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
ALLOWED_CONSTRAINT_RELATIONS: Set[str] = {">", ">=", "<", "<=", "!=", "=", "in"}
ALLOWLISTED_OPTION_KEYS: Set[str] = {"A", "B", "C", "D"}

MAX_RAW_QUERY_CHARS = 4000
MAX_EXPRESSION_CHARS = 1000
MAX_SUBPART_STATEMENT_CHARS = 2000
MAX_OPTION_CHARS = 1000
MAX_METADATA_ENTRIES = 50
MAX_BRACKET_DEPTH = 20


class MKEIntakeValidator:
    """Deterministic Pre-Dispatch Validator for MKE AI Intake.

    Enforces:
    1. Authoritative raw query comparison and provenance tracking.
    2. Strict MKE-IR schema validation and supported version enforcement.
    3. Non-sensitive fixed error messages and safe allowlisted field paths.
    4. Per-expression provenance, cardinality, and semantic role verification.
    5. Constraint source fidelity and unconfirmed inferred constraint blocking.
    6. Multipart and answer option safety (structural pass without premature CAS dispatch).
    7. Source span fidelity against raw student query.
    8. Syntactic AST parsing via frozen CAS parsers without execution.
    """

    @classmethod
    def validate(
        cls,
        raw_query: str,
        ir_payload: Union[Dict[str, Any], MathIntermediateRepresentation]
    ) -> ValidationResult:
        """Perform full deterministic validation on raw query and MKE-IR payload."""
        issues: List[ValidationIssue] = []
        uncertainties: List[UncertaintyFlag] = []

        # -------------------------------------------------------------------
        # Step 1: Reject malformed or oversized authoritative input
        # -------------------------------------------------------------------
        if not isinstance(raw_query, str) or not raw_query.strip():
            return ValidationResult(
                is_valid=False,
                is_structurally_valid=False,
                is_syntactically_valid=False,
                is_source_faithful=False,
                is_cas_ready=False,
                semantic_status=SemanticVerificationStatus.UNLINKED,
                status="INVALID",
                issues=[ValidationIssue(
                    code="EMPTY_RAW_QUERY",
                    message="Raw student query must be a non-empty string.",
                    field_path="raw_query",
                    is_fatal=True
                )]
            )

        if len(raw_query) > MAX_RAW_QUERY_CHARS:
            return ValidationResult(
                is_valid=False,
                is_structurally_valid=False,
                is_syntactically_valid=False,
                is_source_faithful=False,
                is_cas_ready=False,
                semantic_status=SemanticVerificationStatus.UNLINKED,
                status="INVALID",
                issues=[ValidationIssue(
                    code="OVERSIZED_INPUT",
                    message="Raw student query length exceeds maximum allowed character limit.",
                    field_path="raw_query",
                    is_fatal=True
                )]
            )

        # -------------------------------------------------------------------
        # Step 2: Authoritative Raw Query Check & Schema Parsing (Task 1 & 5)
        # -------------------------------------------------------------------
        ir: MathIntermediateRepresentation
        if isinstance(ir_payload, MathIntermediateRepresentation):
            if ir_payload.raw_query != raw_query:
                issues.append(ValidationIssue(
                    code="RAW_QUERY_MISMATCH",
                    message="Payload raw_query does not match authoritative input query.",
                    field_path="raw_query",
                    is_fatal=True
                ))
            ir = ir_payload
        elif isinstance(ir_payload, dict):
            payload_copy = dict(ir_payload)
            if "raw_query" in payload_copy and payload_copy["raw_query"] is not None:
                if payload_copy["raw_query"] != raw_query:
                    issues.append(ValidationIssue(
                        code="RAW_QUERY_MISMATCH",
                        message="Payload raw_query does not match authoritative input query.",
                        field_path="raw_query",
                        is_fatal=True
                    ))
            else:
                # System-populated raw query
                payload_copy["raw_query"] = raw_query
                payload_copy["raw_query_provenance"] = "SYSTEM_POPULATED"

            try:
                ir = MathIntermediateRepresentation.model_validate(payload_copy)
            except Exception:
                return ValidationResult(
                    is_valid=False,
                    is_structurally_valid=False,
                    is_syntactically_valid=False,
                    is_source_faithful=False,
                    is_cas_ready=False,
                    semantic_status=SemanticVerificationStatus.UNLINKED,
                    status="INVALID",
                    issues=[ValidationIssue(
                        code="SCHEMA_VALIDATION_ERROR",
                        message="Payload failed MKE-IR schema validation. Structure does not conform to specification.",
                        field_path="root",
                        is_fatal=True
                    )]
                )
        else:
            return ValidationResult(
                is_valid=False,
                is_structurally_valid=False,
                is_syntactically_valid=False,
                is_source_faithful=False,
                is_cas_ready=False,
                semantic_status=SemanticVerificationStatus.UNLINKED,
                status="INVALID",
                issues=[ValidationIssue(
                    code="INVALID_PAYLOAD_TYPE",
                    message="Payload must be a dictionary or MathIntermediateRepresentation instance.",
                    field_path="root",
                    is_fatal=True
                )]
            )

        # Check Schema Version
        if ir.schema_version != SUPPORTED_MKE_IR_SCHEMA_VERSION:
            issues.append(ValidationIssue(
                code="UNSUPPORTED_SCHEMA_VERSION",
                message="MKE-IR schema version is unsupported.",
                field_path="schema_version",
                is_fatal=True
            ))

        # Check Metadata complexity
        if len(ir.metadata) > MAX_METADATA_ENTRIES:
            issues.append(ValidationIssue(
                code="EXCESSIVE_METADATA_ENTRIES",
                message="Metadata dictionary exceeds maximum allowed entry count.",
                field_path="metadata",
                is_fatal=True
            ))

        # Copy existing uncertainty flags from extraction
        uncertainties.extend(ir.uncertainty_flags)

        # -------------------------------------------------------------------
        # Step 3: Validate Question Format and Required Subparts (Task 3 & 4)
        # -------------------------------------------------------------------
        is_multipart_format = False

        if ir.question_format == QuestionFormat.MULTIPLE_CHOICE_4:
            is_multipart_format = True
            if not ir.given_options or not isinstance(ir.given_options, dict):
                issues.append(ValidationIssue(
                    code="MISSING_OPTIONS",
                    message="Multiple choice question format requires 4 options (A, B, C, D).",
                    field_path="given_options",
                    is_fatal=True
                ))
            else:
                expected_keys = {"A", "B", "C", "D"}
                raw_keys_set = set(k.upper() if isinstance(k, str) else "" for k in ir.given_options.keys())
                if raw_keys_set != expected_keys:
                    issues.append(ValidationIssue(
                        code="INVALID_OPTION_KEYS",
                        message="Multiple choice question options must contain exactly keys 'A', 'B', 'C', and 'D'.",
                        field_path="given_options",
                        is_fatal=True
                    ))
                for opt_k, opt_val in ir.given_options.items():
                    safe_path = f"given_options.{opt_k.upper()}" if (isinstance(opt_k, str) and opt_k.upper() in ALLOWLISTED_OPTION_KEYS) else "given_options"
                    if not isinstance(opt_val, str) or not opt_val.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_OPTION_TEXT",
                            message="Multiple choice option text cannot be empty.",
                            field_path=safe_path,
                            is_fatal=True
                        ))
                    elif len(opt_val) > MAX_OPTION_CHARS:
                        issues.append(ValidationIssue(
                            code="OPTION_TEXT_TOO_LONG",
                            message="Multiple choice option text exceeds maximum allowed character length.",
                            field_path=safe_path,
                            is_fatal=True
                        ))

        elif ir.question_format == QuestionFormat.TRUE_FALSE_4:
            is_multipart_format = True
            if len(ir.subparts) != 4:
                issues.append(ValidationIssue(
                    code="INVALID_TRUE_FALSE_SUBPARTS_COUNT",
                    message="Four-part True/False question must have exactly 4 subparts (a, b, c, d).",
                    field_path="subparts",
                    is_fatal=True
                ))
            else:
                expected_ids = {"a", "b", "c", "d"}
                actual_ids = {s.subpart_id.lower() for s in ir.subparts if isinstance(s.subpart_id, str)}
                if actual_ids != expected_ids:
                    issues.append(ValidationIssue(
                        code="INVALID_TRUE_FALSE_SUBPART_IDS",
                        message="Four-part True/False subparts must have IDs 'a', 'b', 'c', and 'd'.",
                        field_path="subparts",
                        is_fatal=True
                    ))
                for s_idx, s in enumerate(ir.subparts):
                    if not s.statement.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_SUBPART_STATEMENT",
                            message="Subpart statement cannot be empty.",
                            field_path=f"subparts[{s_idx}].statement",
                            is_fatal=True
                        ))
                    elif len(s.statement) > MAX_SUBPART_STATEMENT_CHARS:
                        issues.append(ValidationIssue(
                            code="SUBPART_STATEMENT_TOO_LONG",
                            message="Subpart statement exceeds maximum allowed character length.",
                            field_path=f"subparts[{s_idx}].statement",
                            is_fatal=True
                        ))

        elif ir.question_format == QuestionFormat.MULTI_PART_STEM:
            is_multipart_format = True
            if not ir.subparts or len(ir.subparts) == 0:
                issues.append(ValidationIssue(
                    code="MISSING_SUBPARTS",
                    message="Multi-part stem question format requires at least one subpart.",
                    field_path="subparts",
                    is_fatal=True
                ))
            else:
                seen_ids: Set[str] = set()
                for s_idx, s in enumerate(ir.subparts):
                    sid = s.subpart_id.lower()
                    if sid in seen_ids:
                        issues.append(ValidationIssue(
                            code="DUPLICATE_SUBPART_ID",
                            message="Duplicate subpart ID detected in multi-part question.",
                            field_path=f"subparts[{s_idx}]",
                            is_fatal=True
                        ))
                    seen_ids.add(sid)
                    if not s.statement.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_SUBPART_STATEMENT",
                            message="Subpart statement cannot be empty.",
                            field_path=f"subparts[{s_idx}].statement",
                            is_fatal=True
                        ))
                    elif len(s.statement) > MAX_SUBPART_STATEMENT_CHARS:
                        issues.append(ValidationIssue(
                            code="SUBPART_STATEMENT_TOO_LONG",
                            message="Subpart statement exceeds maximum allowed character length.",
                            field_path=f"subparts[{s_idx}].statement",
                            is_fatal=True
                        ))

        # -------------------------------------------------------------------
        # Step 4: Validate Category Cardinality, Variables, and Constraints (Task 1, 2, 4)
        # -------------------------------------------------------------------
        # 4a. Category Cardinality (Task 1)
        if ir.problem_category in {
            ProblemCategory.EQUATION_SINGLE,
            ProblemCategory.INEQUALITY_SINGLE,
            ProblemCategory.EXPRESSION_SIMPLIFY,
            ProblemCategory.DIFFERENTIATION,
            ProblemCategory.INTEGRATION,
        }:
            if len(ir.primary_expressions) != 1:
                issues.append(ValidationIssue(
                    code="INVALID_EXPRESSION_CARDINALITY",
                    message="Single mathematical operation category requires exactly one primary expression.",
                    field_path="primary_expressions",
                    is_fatal=True
                ))

        # 4b. Target variables
        needs_target_vars = ir.problem_category in {
            ProblemCategory.EQUATION_SINGLE,
            ProblemCategory.EQUATION_SYSTEM,
            ProblemCategory.INEQUALITY_SINGLE,
            ProblemCategory.DIFFERENTIATION,
            ProblemCategory.INTEGRATION,
        }

        if needs_target_vars and (not ir.target_variables or len(ir.target_variables) == 0):
            issues.append(ValidationIssue(
                code="MISSING_TARGET_VARIABLE",
                message="Problem category requires explicit target_variables.",
                field_path="target_variables",
                is_fatal=True
            ))

        for v_idx, v in enumerate(ir.target_variables):
            if not IDENTIFIER_PATTERN.match(v):
                issues.append(ValidationIssue(
                    code="INVALID_VARIABLE_IDENTIFIER",
                    message="Target variable contains invalid identifier characters.",
                    field_path=f"target_variables[{v_idx}]",
                    is_fatal=True
                ))

        for p_idx, p in enumerate(ir.parameters):
            if not IDENTIFIER_PATTERN.match(p):
                issues.append(ValidationIssue(
                    code="INVALID_PARAMETER_IDENTIFIER",
                    message="Parameter contains invalid identifier characters.",
                    field_path=f"parameters[{p_idx}]",
                    is_fatal=True
                ))

        # Disjoint target_variables and parameters
        overlap = set(ir.target_variables) & set(ir.parameters)
        if overlap:
            issues.append(ValidationIssue(
                code="OVERLAPPING_VARIABLES_AND_PARAMETERS",
                message="Target variables and parameters must be disjoint sets.",
                field_path="parameters",
                is_fatal=True
            ))

        # 4c. Constraint Source Fidelity (Task 2)
        for idx, c in enumerate(ir.extracted_constraints):
            if not IDENTIFIER_PATTERN.match(c.variable):
                issues.append(ValidationIssue(
                    code="INVALID_CONSTRAINT_VARIABLE",
                    message="Constraint variable identifier is invalid.",
                    field_path=f"extracted_constraints[{idx}].variable",
                    is_fatal=True
                ))
            if c.relation not in ALLOWED_CONSTRAINT_RELATIONS:
                issues.append(ValidationIssue(
                    code="INVALID_CONSTRAINT_RELATION",
                    message="Constraint relation is not supported.",
                    field_path=f"extracted_constraints[{idx}].relation",
                    is_fatal=True
                ))
            if not c.bound_expression.strip():
                issues.append(ValidationIssue(
                    code="EMPTY_CONSTRAINT_BOUND",
                    message="Constraint bound expression cannot be empty.",
                    field_path=f"extracted_constraints[{idx}].bound_expression",
                    is_fatal=True
                ))
            elif len(c.bound_expression) > MAX_EXPRESSION_CHARS:
                issues.append(ValidationIssue(
                    code="CONSTRAINT_BOUND_TOO_LONG",
                    message="Constraint bound expression exceeds maximum allowed character length.",
                    field_path=f"extracted_constraints[{idx}].bound_expression",
                    is_fatal=True
                ))
            else:
                # Syntax check on bound expression
                try:
                    parse_cas_expression(c.bound_expression)
                except Exception:
                    issues.append(ValidationIssue(
                        code="INVALID_CONSTRAINT_SYNTAX",
                        message="Constraint bound expression failed syntax parsing.",
                        field_path=f"extracted_constraints[{idx}].bound_expression",
                        is_fatal=True
                    ))

            # Student-stated constraint must have matching source evidence (Task 2)
            if not c.is_inferred:
                if c.source_span is None:
                    issues.append(ValidationIssue(
                        code="MISSING_CONSTRAINT_PROVENANCE",
                        message="Explicit student constraint lacks required source span evidence.",
                        field_path=f"extracted_constraints[{idx}].source_span",
                        is_fatal=True
                    ))
                else:
                    # Validate span bounds and text
                    c_span = c.source_span
                    if c_span.start_char < 0 or c_span.end_char <= c_span.start_char or c_span.end_char > len(raw_query):
                        issues.append(ValidationIssue(
                            code="SOURCE_SPAN_OUT_OF_BOUNDS",
                            message="Constraint source span character offsets exceed raw query bounds.",
                            field_path=f"extracted_constraints[{idx}].source_span",
                            is_fatal=True
                        ))
                    elif raw_query[c_span.start_char:c_span.end_char] != c_span.source_fragment:
                        issues.append(ValidationIssue(
                            code="SOURCE_FRAGMENT_MISMATCH",
                            message="Constraint source fragment text does not match character range in raw query.",
                            field_path=f"extracted_constraints[{idx}].source_span",
                            is_fatal=True
                        ))
            else:
                # Inferred constraint blocks CAS readiness
                uncertainties.append(UncertaintyFlag(
                    code="UNCONFIRMED_INFERRED_CONSTRAINT",
                    message="Model-inferred mathematical constraint is unconfirmed and blocks automatic CAS execution.",
                    severity="ERROR"
                ))

        # -------------------------------------------------------------------
        # Step 5: Verify Source-Span Integrity (Phase 2 Fidelity)
        # -------------------------------------------------------------------
        all_spans: List[SourceSpan] = list(ir.source_spans)
        for s in ir.subparts:
            if s.source_span:
                all_spans.append(s.source_span)

        for s_idx, span in enumerate(all_spans):
            if span.start_char < 0 or span.end_char < 0 or span.start_char >= span.end_char or span.end_char > len(raw_query):
                issues.append(ValidationIssue(
                    code="SOURCE_SPAN_OUT_OF_BOUNDS",
                    message="Source span character offsets exceed raw query bounds.",
                    field_path=f"source_spans[{s_idx}]",
                    is_fatal=True
                ))
            else:
                expected_sub = raw_query[span.start_char:span.end_char]
                if expected_sub != span.source_fragment:
                    issues.append(ValidationIssue(
                        code="SOURCE_FRAGMENT_MISMATCH",
                        message="Source fragment text does not match character range in raw query.",
                        field_path=f"source_spans[{s_idx}]",
                        is_fatal=True
                    ))

        # -------------------------------------------------------------------
        # Step 6: Per-Expression Provenance & Semantic Role Verification (Task 1)
        # -------------------------------------------------------------------
        # Determine valid allowed semantic roles for primary expressions
        allowed_roles_map = {
            ProblemCategory.EQUATION_SINGLE: {"EQUATION", "STEM", "PROBLEM_STATEMENT"},
            ProblemCategory.EQUATION_SYSTEM: {"SYSTEM", "EQUATION", "STEM", "PROBLEM_STATEMENT"},
            ProblemCategory.INEQUALITY_SINGLE: {"INEQUALITY", "STEM", "PROBLEM_STATEMENT"},
            ProblemCategory.EXPRESSION_SIMPLIFY: {"EXPRESSION", "STEM", "PROBLEM_STATEMENT"},
            ProblemCategory.DIFFERENTIATION: {"EXPRESSION", "STEM", "PROBLEM_STATEMENT"},
            ProblemCategory.INTEGRATION: {"EXPRESSION", "STEM", "PROBLEM_STATEMENT"},
        }
        allowed_roles = allowed_roles_map.get(ir.problem_category, {"STEM", "PROBLEM_STATEMENT", "EQUATION", "EXPRESSION"})

        per_expr_literal_verified: List[bool] = []
        per_expr_transformed: List[bool] = []

        if not ir.source_spans or len(ir.source_spans) == 0:
            issues.append(ValidationIssue(
                code="MISSING_EXPRESSION_PROVENANCE",
                message="Primary mathematical expression lacks required source span provenance.",
                field_path="source_spans",
                is_fatal=True
            ))
        else:
            for expr_idx, expr in enumerate(ir.primary_expressions):
                clean_expr = expr.strip()
                matched_literal = False
                matched_transformed = False

                for span in ir.source_spans:
                    clean_frag = span.source_fragment.strip()
                    role_upper = span.semantic_role.upper()

                    if role_upper not in allowed_roles:
                        # Span is from an option (e.g. OPTION_A) or subpart, cannot be primary equation!
                        continue

                    if clean_frag == clean_expr:
                        matched_literal = True
                        break
                    else:
                        matched_transformed = True

                if matched_literal:
                    per_expr_literal_verified.append(True)
                    per_expr_transformed.append(False)
                elif matched_transformed:
                    per_expr_literal_verified.append(False)
                    per_expr_transformed.append(True)
                else:
                    per_expr_literal_verified.append(False)
                    per_expr_transformed.append(False)
                    issues.append(ValidationIssue(
                        code="UNLINKED_EXPRESSION_PROVENANCE",
                        message="Primary expression has no corresponding source span reference.",
                        field_path=f"primary_expressions[{expr_idx}]",
                        is_fatal=True
                    ))

        # Semantic verification status determination
        all_literal = (len(per_expr_literal_verified) == len(ir.primary_expressions)) and all(per_expr_literal_verified)
        any_transformed = any(per_expr_transformed)
        any_unlinked = any(not lit and not trans for lit, trans in zip(per_expr_literal_verified, per_expr_transformed)) if per_expr_literal_verified else True

        semantic_status: SemanticVerificationStatus
        if all_literal and not any_unlinked and len(ir.primary_expressions) > 0:
            semantic_status = SemanticVerificationStatus.VERIFIED_LITERAL
        elif any_transformed and not any_unlinked:
            semantic_status = SemanticVerificationStatus.UNVERIFIED_TRANSFORMATION
            uncertainties.append(UncertaintyFlag(
                code="UNVERIFIED_SEMANTIC_TRANSFORMATION",
                message="Primary expression is a normalized or inferred transformation.",
                severity="WARNING"
            ))
        else:
            semantic_status = SemanticVerificationStatus.UNLINKED

        # -------------------------------------------------------------------
        # Step 7: Problem Category Scope & Target Operation Mapping
        # -------------------------------------------------------------------
        target_op: Optional[str] = None
        is_unsupported_category = False

        if ir.problem_category == ProblemCategory.EQUATION_SINGLE:
            target_op = OperationType.SOLVE.value
        elif ir.problem_category == ProblemCategory.EQUATION_SYSTEM:
            target_op = OperationType.SOLVE_SYSTEM.value
        elif ir.problem_category == ProblemCategory.INEQUALITY_SINGLE:
            target_op = OperationType.SOLVE_INEQUALITY.value
        elif ir.problem_category == ProblemCategory.EXPRESSION_SIMPLIFY:
            target_op = OperationType.SIMPLIFY.value
        elif ir.problem_category == ProblemCategory.DIFFERENTIATION:
            target_op = OperationType.DIFFERENTIATE.value
        elif ir.problem_category == ProblemCategory.INTEGRATION:
            target_op = OperationType.INTEGRATE.value
        elif ir.problem_category in {ProblemCategory.WORD_PROBLEM, ProblemCategory.PARAMETER_ANALYSIS, ProblemCategory.UNKNOWN_UNSUPPORTED}:
            is_unsupported_category = True
            issues.append(ValidationIssue(
                code="UNSUPPORTED_PROBLEM_CATEGORY",
                message="Problem category is not supported for automated CAS proof.",
                field_path="problem_category",
                is_fatal=True
            ))

        # -------------------------------------------------------------------
        # Step 8: Syntactic AST Validation Using Frozen CAS Parsers (No Execution)
        # -------------------------------------------------------------------
        for expr_idx, expr in enumerate(ir.primary_expressions):
            if not isinstance(expr, str) or not expr.strip():
                issues.append(ValidationIssue(
                    code="EMPTY_PRIMARY_EXPRESSION",
                    message="Primary mathematical expression cannot be empty.",
                    field_path=f"primary_expressions[{expr_idx}]",
                    is_fatal=True
                ))
                continue

            if len(expr) > MAX_EXPRESSION_CHARS:
                issues.append(ValidationIssue(
                    code="EXPRESSION_TOO_LONG",
                    message="Primary expression exceeds maximum allowed character length.",
                    field_path=f"primary_expressions[{expr_idx}]",
                    is_fatal=True
                ))
                continue

            # Bracket depth complexity check
            bracket_depth = 0
            max_depth_seen = 0
            for ch in expr:
                if ch in "([{":
                    bracket_depth += 1
                    max_depth_seen = max(max_depth_seen, bracket_depth)
                elif ch in ")]}":
                    bracket_depth = max(0, bracket_depth - 1)
            if max_depth_seen > MAX_BRACKET_DEPTH:
                issues.append(ValidationIssue(
                    code="EXCESSIVE_NESTING_DEPTH",
                    message="Expression exceeds maximum allowed bracket nesting depth.",
                    field_path=f"primary_expressions[{expr_idx}]",
                    is_fatal=True
                ))
                continue

            # Parse with appropriate frozen CAS parser for syntactic validity
            if not is_unsupported_category:
                try:
                    if ir.problem_category == ProblemCategory.EQUATION_SINGLE:
                        parse_cas_equation(expr)
                    elif ir.problem_category == ProblemCategory.EQUATION_SYSTEM:
                        parse_cas_system(expr)
                    elif ir.problem_category == ProblemCategory.INEQUALITY_SINGLE:
                        parse_cas_inequality(expr)
                    elif ir.problem_category in {ProblemCategory.EXPRESSION_SIMPLIFY, ProblemCategory.DIFFERENTIATION, ProblemCategory.INTEGRATION}:
                        parse_cas_expression(expr)
                except ParserError:
                    issues.append(ValidationIssue(
                        code="MATH_SYNTAX_ERROR",
                        message="Primary expression failed mathematical syntax parsing.",
                        field_path=f"primary_expressions[{expr_idx}]",
                        is_fatal=True
                    ))
                except Exception:
                    issues.append(ValidationIssue(
                        code="MATH_SYNTAX_ERROR",
                        message="Primary expression failed mathematical syntax parsing.",
                        field_path=f"primary_expressions[{expr_idx}]",
                        is_fatal=True
                    ))

        # Syntactic validation on subpart expressions if provided
        for s_idx, s in enumerate(ir.subparts):
            if s.extracted_expression and s.extracted_expression.strip():
                sub_expr = s.extracted_expression.strip()
                if len(sub_expr) > MAX_EXPRESSION_CHARS:
                    issues.append(ValidationIssue(
                        code="SUBPART_EXPRESSION_TOO_LONG",
                        message="Subpart expression exceeds maximum allowed character length.",
                        field_path=f"subparts[{s_idx}].extracted_expression",
                        is_fatal=True
                    ))
                    continue

                sub_depth = 0
                max_sub_depth = 0
                for ch in sub_expr:
                    if ch in "([{":
                        sub_depth += 1
                        max_sub_depth = max(max_sub_depth, sub_depth)
                    elif ch in ")]}":
                        sub_depth = max(0, sub_depth - 1)
                if max_sub_depth > MAX_BRACKET_DEPTH:
                    issues.append(ValidationIssue(
                        code="SUBPART_EXCESSIVE_NESTING_DEPTH",
                        message="Subpart expression exceeds maximum allowed bracket nesting depth.",
                        field_path=f"subparts[{s_idx}].extracted_expression",
                        is_fatal=True
                    ))
                    continue

                try:
                    if "=" in sub_expr:
                        parse_cas_equation(sub_expr)
                    elif any(op in sub_expr for op in [">=", "<=", ">", "<"]):
                        parse_cas_inequality(sub_expr)
                    else:
                        parse_cas_expression(sub_expr)
                except Exception:
                    issues.append(ValidationIssue(
                        code="SUBPART_SYNTAX_ERROR",
                        message="Subpart expression failed mathematical syntax parsing.",
                        field_path=f"subparts[{s_idx}].extracted_expression",
                        is_fatal=True
                    ))

        # If question is multipart or multiple-choice, emit flag stating CAS solving requires downstream stages
        if is_multipart_format:
            uncertainties.append(UncertaintyFlag(
                code="MULTI_PART_AWAITING_STAGE",
                message="Multi-part and multiple-choice questions are structurally validated but require downstream stage evaluation.",
                severity="WARNING"
            ))

        # -------------------------------------------------------------------
        # Step 9: Assemble Deterministic ValidationResult
        # -------------------------------------------------------------------
        fatal_issues = [i for i in issues if i.is_fatal]
        has_blocking_uncertainty = any(u.severity in {"ERROR", "CRITICAL"} for u in uncertainties)

        is_structurally_valid = not any(
            i.code in {
                "SCHEMA_VALIDATION_ERROR",
                "INVALID_PAYLOAD_TYPE",
                "UNSUPPORTED_SCHEMA_VERSION",
                "OVERSIZED_INPUT",
                "EMPTY_RAW_QUERY",
                "RAW_QUERY_MISMATCH",
                "MISSING_OPTIONS",
                "INVALID_OPTION_KEYS",
                "EMPTY_OPTION_TEXT",
                "OPTION_TEXT_TOO_LONG",
                "INVALID_TRUE_FALSE_SUBPARTS_COUNT",
                "INVALID_TRUE_FALSE_SUBPART_IDS",
                "EMPTY_SUBPART_STATEMENT",
                "SUBPART_STATEMENT_TOO_LONG",
                "MISSING_SUBPARTS",
                "DUPLICATE_SUBPART_ID",
                "MISSING_TARGET_VARIABLE",
                "INVALID_VARIABLE_IDENTIFIER",
                "INVALID_PARAMETER_IDENTIFIER",
                "OVERLAPPING_VARIABLES_AND_PARAMETERS",
                "INVALID_CONSTRAINT_VARIABLE",
                "INVALID_CONSTRAINT_RELATION",
                "EMPTY_CONSTRAINT_BOUND",
                "CONSTRAINT_BOUND_TOO_LONG",
                "EXCESSIVE_METADATA_ENTRIES",
                "INVALID_EXPRESSION_CARDINALITY",
                "MISSING_CONSTRAINT_PROVENANCE",
            }
            for i in issues
        )

        is_syntactically_valid = not any(
            i.code in {
                "EMPTY_PRIMARY_EXPRESSION",
                "EXPRESSION_TOO_LONG",
                "EXCESSIVE_NESTING_DEPTH",
                "MATH_SYNTAX_ERROR",
                "SUBPART_EXPRESSION_TOO_LONG",
                "SUBPART_EXCESSIVE_NESTING_DEPTH",
                "SUBPART_SYNTAX_ERROR",
                "INVALID_CONSTRAINT_SYNTAX",
            }
            for i in issues
        )

        is_source_faithful = not any(
            i.code in {
                "RAW_QUERY_MISMATCH",
                "SOURCE_SPAN_OUT_OF_BOUNDS",
                "SOURCE_FRAGMENT_MISMATCH",
                "MISSING_EXPRESSION_PROVENANCE",
                "UNLINKED_EXPRESSION_PROVENANCE",
                "MISSING_CONSTRAINT_PROVENANCE",
            }
            for i in issues
        )

        # CAS readiness requires:
        # 1. Zero fatal issues
        # 2. Fully verified literal expression provenance for ALL primary expressions
        # 3. No blocking uncertainty (such as unconfirmed inferred constraints)
        # 4. Supported category mapped to CAS OperationType
        # 5. Not a multipart/multiple-choice format (which requires downstream candidate analysis)
        # 6. Source fidelity, syntactic validity, structural validity
        is_cas_ready = (
            (len(fatal_issues) == 0)
            and (semantic_status == SemanticVerificationStatus.VERIFIED_LITERAL)
            and (not has_blocking_uncertainty)
            and (target_op is not None)
            and (not is_multipart_format)
            and is_source_faithful
            and is_syntactically_valid
            and is_structurally_valid
        )

        status: str
        if is_cas_ready:
            status = "VALID"
        elif is_unsupported_category:
            status = "UNSUPPORTED"
        elif has_blocking_uncertainty:
            status = "AMBIGUOUS"
        elif semantic_status == SemanticVerificationStatus.UNVERIFIED_TRANSFORMATION:
            status = "UNVERIFIED_SEMANTICS"
        elif is_multipart_format and is_structurally_valid and is_syntactically_valid and is_source_faithful:
            status = "UNVERIFIED_SEMANTICS"
        else:
            status = "INVALID"

        return ValidationResult(
            is_valid=is_cas_ready,
            is_structurally_valid=is_structurally_valid,
            is_syntactically_valid=is_syntactically_valid,
            is_source_faithful=is_source_faithful,
            semantic_status=semantic_status,
            is_cas_ready=is_cas_ready,
            status=status,
            issues=issues,
            uncertainties=uncertainties,
            validated_ir=ir if (is_structurally_valid and not any(i.code == "RAW_QUERY_MISMATCH" for i in issues)) else None,
            target_operation=target_op if is_cas_ready else None
        )
