"""Deterministic Pre-Dispatch MKE-IR Validator.

Phase 3, 4 & 5: Validates mathematical intermediate representations against strict
schemas, question format rules, source-span fidelity, variable declarations, and
syntactic AST validity using frozen CAS parsers without mathematical execution.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Union

from mke_product.ai.ir import (
    ProblemCategory,
    QuestionFormat,
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

MAX_RAW_QUERY_CHARS = 4000
MAX_EXPRESSION_CHARS = 1000
MAX_BRACKET_DEPTH = 20


class MKEIntakeValidator:
    """Deterministic Pre-Dispatch Validator for MKE AI Intake.

    Enforces:
    1. Size and input boundaries (no oversized or deeply nested inputs).
    2. Strict MKE-IR schema structure (no unexpected fields).
    3. Format and subpart completeness (A/B/C/D for MC4, a/b/c/d for TF4).
    4. Target variables, parameters, and domain constraint integrity.
    5. Source span fidelity against raw student query.
    6. Problem category scope mapping.
    7. Syntactic AST parsing via frozen CAS parsers without execution.
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
        # Step 1: Reject malformed or oversized input
        # -------------------------------------------------------------------
        if not isinstance(raw_query, str) or not raw_query.strip():
            return ValidationResult(
                is_valid=False,
                status="INVALID",
                issues=[ValidationIssue(
                    code="EMPTY_RAW_QUERY",
                    message="Raw student query must be a non-empty string",
                    field_path="raw_query",
                    is_fatal=True
                )]
            )

        if len(raw_query) > MAX_RAW_QUERY_CHARS:
            return ValidationResult(
                is_valid=False,
                status="INVALID",
                issues=[ValidationIssue(
                    code="OVERSIZED_INPUT",
                    message=f"Raw student query length exceeds maximum limit of {MAX_RAW_QUERY_CHARS} characters",
                    field_path="raw_query",
                    is_fatal=True
                )]
            )

        # -------------------------------------------------------------------
        # Step 2: Validate strict MKE-IR structure (Pydantic schema)
        # -------------------------------------------------------------------
        ir: MathIntermediateRepresentation
        if isinstance(ir_payload, MathIntermediateRepresentation):
            ir = ir_payload
        elif isinstance(ir_payload, dict):
            # Ensure raw_query is set or matched
            payload_copy = dict(ir_payload)
            if "raw_query" not in payload_copy or not payload_copy["raw_query"]:
                payload_copy["raw_query"] = raw_query
            try:
                ir = MathIntermediateRepresentation.model_validate(payload_copy)
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    status="INVALID",
                    issues=[ValidationIssue(
                        code="SCHEMA_VALIDATION_ERROR",
                        message=f"Payload failed MKE-IR schema validation: {str(e)}",
                        field_path="root",
                        is_fatal=True
                    )]
                )
        else:
            return ValidationResult(
                is_valid=False,
                status="INVALID",
                issues=[ValidationIssue(
                    code="INVALID_PAYLOAD_TYPE",
                    message="Payload must be a dictionary or MathIntermediateRepresentation instance",
                    field_path="root",
                    is_fatal=True
                )]
            )

        # Copy existing uncertainty flags from extraction
        uncertainties.extend(ir.uncertainty_flags)

        # -------------------------------------------------------------------
        # Step 3: Validate Question Format and Required Subparts
        # -------------------------------------------------------------------
        if ir.question_format == QuestionFormat.MULTIPLE_CHOICE_4:
            if not ir.given_options or not isinstance(ir.given_options, dict):
                issues.append(ValidationIssue(
                    code="MISSING_OPTIONS",
                    message="Multiple choice question format requires 4 options (A, B, C, D)",
                    field_path="given_options",
                    is_fatal=True
                ))
            else:
                expected_keys = {"A", "B", "C", "D"}
                normalized_keys = {k.upper(): v for k, v in ir.given_options.items()}
                if set(normalized_keys.keys()) != expected_keys:
                    issues.append(ValidationIssue(
                        code="INVALID_OPTION_KEYS",
                        message="Multiple choice question options must contain exactly keys 'A', 'B', 'C', and 'D'",
                        field_path="given_options",
                        is_fatal=True
                    ))
                for opt_key, opt_val in normalized_keys.items():
                    if not isinstance(opt_val, str) or not opt_val.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_OPTION_TEXT",
                            message=f"Multiple choice option '{opt_key}' cannot be empty",
                            field_path=f"given_options.{opt_key}",
                            is_fatal=True
                        ))

        elif ir.question_format == QuestionFormat.TRUE_FALSE_4:
            if len(ir.subparts) != 4:
                issues.append(ValidationIssue(
                    code="INVALID_TRUE_FALSE_SUBPARTS_COUNT",
                    message="Four-part True/False question must have exactly 4 subparts (a, b, c, d)",
                    field_path="subparts",
                    is_fatal=True
                ))
            else:
                expected_ids = {"a", "b", "c", "d"}
                actual_ids = {s.subpart_id.lower() for s in ir.subparts}
                if actual_ids != expected_ids:
                    issues.append(ValidationIssue(
                        code="INVALID_TRUE_FALSE_SUBPART_IDS",
                        message="Four-part True/False subparts must have IDs 'a', 'b', 'c', and 'd'",
                        field_path="subparts",
                        is_fatal=True
                    ))
                for s in ir.subparts:
                    if not s.statement.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_SUBPART_STATEMENT",
                            message=f"Subpart '{s.subpart_id}' statement cannot be empty",
                            field_path=f"subparts.{s.subpart_id}",
                            is_fatal=True
                        ))

        elif ir.question_format == QuestionFormat.MULTI_PART_STEM:
            if not ir.subparts or len(ir.subparts) == 0:
                issues.append(ValidationIssue(
                    code="MISSING_SUBPARTS",
                    message="Multi-part stem question format requires at least one subpart",
                    field_path="subparts",
                    is_fatal=True
                ))
            else:
                seen_ids: Set[str] = set()
                for s in ir.subparts:
                    sid = s.subpart_id.lower()
                    if sid in seen_ids:
                        issues.append(ValidationIssue(
                            code="DUPLICATE_SUBPART_ID",
                            message=f"Duplicate subpart ID '{s.subpart_id}' in multi-part question",
                            field_path=f"subparts.{s.subpart_id}",
                            is_fatal=True
                        ))
                    seen_ids.add(sid)
                    if not s.statement.strip():
                        issues.append(ValidationIssue(
                            code="EMPTY_SUBPART_STATEMENT",
                            message=f"Subpart '{s.subpart_id}' statement cannot be empty",
                            field_path=f"subparts.{s.subpart_id}",
                            is_fatal=True
                        ))

        # -------------------------------------------------------------------
        # Step 4: Validate Variables, Parameters, and Constraints
        # -------------------------------------------------------------------
        # Equation, System, Inequality, Calculus require explicit target variables
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
                message=f"Problem category '{ir.problem_category.value}' requires explicit target_variables",
                field_path="target_variables",
                is_fatal=True
            ))

        for v in ir.target_variables:
            if not IDENTIFIER_PATTERN.match(v):
                issues.append(ValidationIssue(
                    code="INVALID_VARIABLE_IDENTIFIER",
                    message=f"Target variable identifier '{v}' is invalid (must match [a-zA-Z][a-zA-Z0-9_]*)",
                    field_path="target_variables",
                    is_fatal=True
                ))

        for p in ir.parameters:
            if not IDENTIFIER_PATTERN.match(p):
                issues.append(ValidationIssue(
                    code="INVALID_PARAMETER_IDENTIFIER",
                    message=f"Parameter identifier '{p}' is invalid (must match [a-zA-Z][a-zA-Z0-9_]*)",
                    field_path="parameters",
                    is_fatal=True
                ))

        # Disjoint target_variables and parameters
        overlap = set(ir.target_variables) & set(ir.parameters)
        if overlap:
            issues.append(ValidationIssue(
                code="OVERLAPPING_VARIABLES_AND_PARAMETERS",
                message=f"Identifiers {sorted(list(overlap))} declared as both target variable and parameter",
                field_path="parameters",
                is_fatal=True
            ))

        # Constraint validation
        for idx, c in enumerate(ir.extracted_constraints):
            if not IDENTIFIER_PATTERN.match(c.variable):
                issues.append(ValidationIssue(
                    code="INVALID_CONSTRAINT_VARIABLE",
                    message=f"Constraint variable '{c.variable}' is invalid",
                    field_path=f"extracted_constraints[{idx}].variable",
                    is_fatal=True
                ))
            if c.relation not in ALLOWED_CONSTRAINT_RELATIONS:
                issues.append(ValidationIssue(
                    code="INVALID_CONSTRAINT_RELATION",
                    message=f"Constraint relation '{c.relation}' not supported (allowed: {sorted(list(ALLOWED_CONSTRAINT_RELATIONS))})",
                    field_path=f"extracted_constraints[{idx}].relation",
                    is_fatal=True
                ))
            if not c.bound_expression.strip():
                issues.append(ValidationIssue(
                    code="EMPTY_CONSTRAINT_BOUND",
                    message="Constraint bound expression cannot be empty",
                    field_path=f"extracted_constraints[{idx}].bound_expression",
                    is_fatal=True
                ))
            if c.is_inferred:
                uncertainties.append(UncertaintyFlag(
                    code="INFERRED_CONSTRAINT",
                    message=f"Constraint on '{c.variable}' was model-inferred rather than explicitly student-stated",
                    severity="WARNING"
                ))

        # -------------------------------------------------------------------
        # Step 5: Verify Source-Span Integrity (Phase 2 Fidelity)
        # -------------------------------------------------------------------
        all_spans: List[SourceSpan] = list(ir.source_spans)
        for c in ir.extracted_constraints:
            if c.source_span:
                all_spans.append(c.source_span)
        for s in ir.subparts:
            if s.source_span:
                all_spans.append(s.source_span)

        for s_idx, span in enumerate(all_spans):
            if span.start_char < 0 or span.end_char < 0 or span.start_char >= span.end_char or span.end_char > len(raw_query):
                issues.append(ValidationIssue(
                    code="SOURCE_SPAN_OUT_OF_BOUNDS",
                    message=f"Source span [{span.start_char}:{span.end_char}] exceeds raw query length of {len(raw_query)}",
                    field_path=f"source_spans[{s_idx}]",
                    is_fatal=True
                ))
            else:
                expected_sub = raw_query[span.start_char:span.end_char]
                if expected_sub != span.source_fragment:
                    issues.append(ValidationIssue(
                        code="SOURCE_FRAGMENT_MISMATCH",
                        message="Source fragment text does not match character range in raw query",
                        field_path=f"source_spans[{s_idx}]",
                        is_fatal=True
                    ))

        # -------------------------------------------------------------------
        # Step 6: Identify Problem Category Scope & Operation Mapping
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
                message=f"Problem category '{ir.problem_category.value}' is not supported for automated CAS proof",
                field_path="problem_category",
                is_fatal=True
            ))

        # -------------------------------------------------------------------
        # Step 7: Syntactic AST Validation Using Frozen CAS Parsers (No Execution)
        # -------------------------------------------------------------------
        for expr_idx, expr in enumerate(ir.primary_expressions):
            if not isinstance(expr, str) or not expr.strip():
                issues.append(ValidationIssue(
                    code="EMPTY_PRIMARY_EXPRESSION",
                    message="Primary mathematical expression cannot be empty",
                    field_path=f"primary_expressions[{expr_idx}]",
                    is_fatal=True
                ))
                continue

            if len(expr) > MAX_EXPRESSION_CHARS:
                issues.append(ValidationIssue(
                    code="EXPRESSION_TOO_LONG",
                    message=f"Expression length {len(expr)} exceeds limit of {MAX_EXPRESSION_CHARS} characters",
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
                    message=f"Expression bracket nesting depth {max_depth_seen} exceeds maximum allowed of {MAX_BRACKET_DEPTH}",
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
                except ParserError as pe:
                    issues.append(ValidationIssue(
                        code="MATH_SYNTAX_ERROR",
                        message="Primary expression failed mathematical syntax parsing",
                        field_path=f"primary_expressions[{expr_idx}]",
                        is_fatal=True
                    ))
                except Exception as ex:
                    issues.append(ValidationIssue(
                        code="MATH_SYNTAX_ERROR",
                        message="Primary expression failed mathematical syntax parsing",
                        field_path=f"primary_expressions[{expr_idx}]",
                        is_fatal=True
                    ))

        # Syntactic validation on subpart expressions if provided
        for s in ir.subparts:
            if s.extracted_expression and s.extracted_expression.strip():
                sub_expr = s.extracted_expression.strip()
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
                        message=f"Subpart '{s.subpart_id}' expression failed syntax parsing",
                        field_path=f"subparts.{s.subpart_id}.extracted_expression",
                        is_fatal=True
                    ))

        # -------------------------------------------------------------------
        # Step 8: Assemble Deterministic ValidationResult
        # -------------------------------------------------------------------
        fatal_issues = [i for i in issues if i.is_fatal]
        is_valid = len(fatal_issues) == 0

        status: str
        if is_valid:
            status = "VALID"
        elif is_unsupported_category:
            status = "UNSUPPORTED"
        elif any(u.severity == "CRITICAL" for u in uncertainties):
            status = "AMBIGUOUS"
        else:
            status = "INVALID"

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            issues=issues,
            uncertainties=uncertainties,
            validated_ir=ir if is_valid else None,
            target_operation=target_op if is_valid else None
        )
