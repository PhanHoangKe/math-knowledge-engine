"""SymPy CAS engine adapter implementation for MKE Product."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Sequence, Set
import sympy

from mke_product.parser.ast import (
    AbsoluteValue,
    ASTNode,
    BinaryOp,
    Equation,
    Power,
    Radical,
)

from .ast_bridge import ast_to_sympy, ast_to_sympy_expr
from .cas_parser import (
    Inequality,
    LinearSystem,
    parse_cas_equation,
    parse_cas_expression,
    parse_cas_inequality,
    parse_cas_system,
)
from .contracts import (
    DomainCertainty,
    EngineCapability,
    EngineStatus,
    ExecutionRequest,
    ExecutionResponse,
    MathEngine,
    OperationType,
    SCHEMA_VERSION_P03A,
    VerificationStatus,
)
from .safety import (
    DomainRestrictionError,
    SafetyError,
    assess_domain_certainty,
    extract_domain_restrictions,
    inspect_ast_safety,
    is_polynomial_ast,
    parse_safe_numeric_bound,
    sanitize_execution_options,
)
from .serialization import (
    format_integral_latex,
    format_integral_symbolic,
    format_interval_latex,
    format_interval_symbolic,
    format_solution_set_latex,
    format_solution_set_symbolic,
    format_system_latex,
    format_system_symbolic,
    format_sympy_latex,
    format_sympy_symbolic,
)


def execute_sympy_direct(request: ExecutionRequest) -> ExecutionResponse:
    """Core mathematical execution logic for SymPy algorithms."""
    start_time = time.monotonic()
    input_text = request.raw_input or request.expression
    response = ExecutionResponse(
        schema_version=SCHEMA_VERSION_P03A,
        request_id=request.request_id,
        operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
        original_input=input_text,
        selected_engine="sympy_cas_v0",
    )

    try:
        # 1. Sanitize options
        sanitized_opts = sanitize_execution_options(request.options)
        request.options = sanitized_opts

        # 2. Parse AST if not already provided
        ast_node = request.ast
        if ast_node is None:
            if request.operation == OperationType.SOLVE_SYSTEM:
                ast_node = parse_cas_system(input_text)
            elif request.operation == OperationType.SOLVE_INEQUALITY:
                ast_node = parse_cas_inequality(input_text)
            elif request.operation in (OperationType.SOLVE, OperationType.CHECK_CANDIDATE):
                # Auto-detect system (presence of , or ; with =) or inequality
                if ("," in input_text or ";" in input_text) and "=" in input_text:
                    ast_node = parse_cas_system(input_text)
                    request.operation = OperationType.SOLVE_SYSTEM
                elif any(op in input_text for op in ("<=", ">=", "≤", "≥", "<", ">")):
                    ast_node = parse_cas_inequality(input_text)
                    request.operation = OperationType.SOLVE_INEQUALITY
                elif "=" in input_text:
                    ast_node = parse_cas_equation(input_text)
                else:
                    ast_node = parse_cas_expression(input_text)
            else:
                ast_node = parse_cas_expression(input_text)

        # 3. Inspect AST safety & extract domain constraints (lightweight structural checks)
        inspect_ast_safety(ast_node)

        # Substantive symbolic domain validations executed under the supervised worker
        from mke_product.parser.ast import BinaryOp, Power
        from .cas_parser import CASPower
        from .safety import prove_constant_zero_status, DivisionByZeroError
        for n in ast_node.walk():
            if isinstance(n, (Power, CASPower)) and n.exponent.value == 0:
                zero_status = prove_constant_zero_status(n.base) if len(n.base.variables()) == 0 else "UNDECIDABLE"
                if zero_status == "ZERO":
                    raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
                elif zero_status == "UNDECIDABLE":
                    sym_base = ast_to_sympy_expr(n.base)
                    try:
                        simplified_base = sympy.simplify(sym_base)
                        if simplified_base == 0:
                            raise DomainRestrictionError("Indeterminate form 0^0 is undefined in real domain.")
                    except DomainRestrictionError:
                        raise
                    except Exception as exc:
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Undecidable zero-power base definedness: {exc}"
                        return response

            elif isinstance(n, BinaryOp) and n.op == "/":
                zero_status = prove_constant_zero_status(n.right) if len(n.right.variables()) == 0 else "UNDECIDABLE"
                if zero_status == "ZERO":
                    raise DivisionByZeroError("Division by zero expression is undefined in real domain.")
                elif zero_status == "UNDECIDABLE":
                    sym_denom = ast_to_sympy_expr(n.right)
                    try:
                        simplified_denom = sympy.simplify(sym_denom)
                        if simplified_denom == 0:
                            raise DivisionByZeroError("Division by zero expression is undefined in real domain.")
                    except DivisionByZeroError:
                        raise
                    except Exception as exc:
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Undecidable denominator definedness: {exc}"
                        return response

            elif isinstance(n, Radical):
                if len(n.radicand.variables()) == 0:
                    sym_rad = ast_to_sympy_expr(n.radicand)
                    try:
                        simplified_rad = sympy.simplify(sym_rad)
                        if simplified_rad.is_number and (simplified_rad.is_negative or (hasattr(simplified_rad, "evalf") and float(simplified_rad.evalf()) < -1e-9)):
                            raise DomainRestrictionError("Square root of negative real number is undefined in real domain.")
                    except DomainRestrictionError:
                        raise
                    except Exception as exc:
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Undecidable radical definedness: {exc}"
                        return response

        domain_restrictions = extract_domain_restrictions(ast_node)

        response.domain_restrictions = domain_restrictions

        # 4. Convert AST to SymPy object via secure typed bridge (no eval / no sympify)
        sym_obj = ast_to_sympy(ast_node)

        # 5. Dispatch to specific mathematical operation
        if request.operation == OperationType.SOLVE:
            _execute_solve(ast_node, sym_obj, response)
        elif request.operation == OperationType.SOLVE_SYSTEM:
            _execute_solve_system(ast_node, sym_obj, response)
        elif request.operation == OperationType.SOLVE_INEQUALITY:
            _execute_solve_inequality(ast_node, sym_obj, response)
        elif request.operation == OperationType.SIMPLIFY:
            _execute_simplify(sym_obj, response)
        elif request.operation == OperationType.DIFFERENTIATE:
            _execute_differentiate(sym_obj, request.variable, sanitized_opts, response)
        elif request.operation == OperationType.INTEGRATE:
            _execute_integrate(sym_obj, request.variable, sanitized_opts, response)
        elif request.operation == OperationType.PLOT_2D:
            _execute_plot_2d(sym_obj, request.variable, sanitized_opts, response)
        else:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.error_message = f"Unsupported operation: {request.operation}"

        if response.mathematical_status == EngineStatus.SUCCESS:
            certainty_str = assess_domain_certainty(ast_node, response.domain_restrictions)
            response.domain_certainty = DomainCertainty(certainty_str)
            if request.operation == OperationType.CHECK_CANDIDATE:
                response.verification_status = VerificationStatus.CANDIDATE_CHECKED
            else:
                response.verification_status = VerificationStatus.COMPUTED
        elif response.mathematical_status == EngineStatus.PARTIAL:
            response.verification_status = VerificationStatus.PARTIAL
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        elif response.mathematical_status == EngineStatus.UNRESOLVED:
            response.verification_status = VerificationStatus.UNRESOLVED
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        else:
            response.verification_status = VerificationStatus.ERROR
            response.domain_certainty = DomainCertainty.NOT_APPLICABLE

    except DomainRestrictionError as ex:
        response.mathematical_status = EngineStatus.DOMAIN_ERROR
        response.verification_status = VerificationStatus.ERROR
        response.domain_certainty = DomainCertainty.NOT_APPLICABLE
        response.error_message = str(ex)
        response.warnings.append(str(ex))
    except SafetyError as ex:
        response.mathematical_status = EngineStatus.RESOURCE_EXHAUSTED
        response.verification_status = VerificationStatus.ERROR
        response.domain_certainty = DomainCertainty.NOT_APPLICABLE
        response.error_message = str(ex)
    except ValueError as ex:
        response.mathematical_status = EngineStatus.INVALID_INPUT
        response.verification_status = VerificationStatus.ERROR
        response.domain_certainty = DomainCertainty.NOT_APPLICABLE
        response.error_message = str(ex)
    except Exception as ex:
        response.mathematical_status = EngineStatus.INTERNAL_ERROR
        response.verification_status = VerificationStatus.ERROR
        response.domain_certainty = DomainCertainty.NOT_APPLICABLE
        response.error_message = f"{type(ex).__name__}: {str(ex)}"
    finally:
        response.execution_duration_sec = time.monotonic() - start_time

    return response


def _collect_algebraic_candidates(ast_node: ASTNode, sym_eq: sympy.Eq, var: sympy.Symbol) -> List[Any]:
    """Collect candidate roots for radical, rational, absolute value, and polynomial equations."""
    candidates: List[Any] = []

    # 1. Direct SymPy solve
    try:
        raw = sympy.solve(sym_eq, var)
        if not isinstance(raw, (list, tuple, set)):
            raw = [raw]
        for r in raw:
            if isinstance(r, dict):
                r = r.get(var, r)
            candidates.append(r)
    except Exception:
        pass

    # 2. Pattern-based algebraic transformations for equations
    if isinstance(ast_node, Equation):
        left_ast = ast_node.left
        right_ast = ast_node.right
        lhs_sym = ast_to_sympy_expr(left_ast)
        rhs_sym = ast_to_sympy_expr(right_ast)

        # Radical: sqrt(f) = sqrt(g)
        if isinstance(left_ast, Radical) and isinstance(right_ast, Radical):
            f_sym = ast_to_sympy_expr(left_ast.radicand)
            g_sym = ast_to_sympy_expr(right_ast.radicand)
            try:
                roots = sympy.solve(sympy.Eq(f_sym, g_sym), var)
                if not isinstance(roots, (list, tuple, set)):
                    roots = [roots]
                candidates.extend(roots)
            except Exception:
                pass

        # Radical: sqrt(f) = g
        elif isinstance(left_ast, Radical):
            f_sym = ast_to_sympy_expr(left_ast.radicand)
            try:
                roots = sympy.solve(sympy.Eq(f_sym, rhs_sym**2), var)
                if not isinstance(roots, (list, tuple, set)):
                    roots = [roots]
                candidates.extend(roots)
            except Exception:
                pass

        # Radical: g = sqrt(f)
        elif isinstance(right_ast, Radical):
            f_sym = ast_to_sympy_expr(right_ast.radicand)
            try:
                roots = sympy.solve(sympy.Eq(lhs_sym**2, f_sym), var)
                if not isinstance(roots, (list, tuple, set)):
                    roots = [roots]
                candidates.extend(roots)
            except Exception:
                pass

        # Absolute value: |f| = |g|
        if isinstance(left_ast, AbsoluteValue) and isinstance(right_ast, AbsoluteValue):
            f_sym = ast_to_sympy_expr(left_ast.inner)
            g_sym = ast_to_sympy_expr(right_ast.inner)
            try:
                candidates.extend(sympy.solve(sympy.Eq(f_sym, g_sym), var))
                candidates.extend(sympy.solve(sympy.Eq(f_sym, -g_sym), var))
            except Exception:
                pass

        # Absolute value: |f| = g
        elif isinstance(left_ast, AbsoluteValue):
            f_sym = ast_to_sympy_expr(left_ast.inner)
            try:
                candidates.extend(sympy.solve(sympy.Eq(f_sym, rhs_sym), var))
                candidates.extend(sympy.solve(sympy.Eq(f_sym, -rhs_sym), var))
            except Exception:
                pass

        # Absolute value: g = |f|
        elif isinstance(right_ast, AbsoluteValue):
            f_sym = ast_to_sympy_expr(right_ast.inner)
            try:
                candidates.extend(sympy.solve(sympy.Eq(lhs_sym, f_sym), var))
                candidates.extend(sympy.solve(sympy.Eq(lhs_sym, -f_sym), var))
            except Exception:
                pass

        # Rational equations: cross multiply or together numerator
        try:
            diff = sympy.together(lhs_sym - rhs_sym)
            num, _ = sympy.fraction(diff)
            roots = sympy.solve(num, var)
            if not isinstance(roots, (list, tuple, set)):
                roots = [roots]
            candidates.extend(roots)
        except Exception:
            pass

    return candidates


def _validate_root_in_ast(
    r: Any,
    ast_node: ASTNode,
    var: sympy.Symbol,
    lhs_sym: sympy.Expr,
    rhs_sym: sympy.Expr,
) -> Tuple[bool, str]:
    """Strictly validate candidate root r against the original AST domain constraints and equation identity."""
    # 1. Exact realness check
    is_real = False
    if hasattr(r, "is_real") and r.is_real is True:
        is_real = True
    elif isinstance(r, (int, sympy.Integer, sympy.Rational)):
        is_real = True
    elif isinstance(r, float):
        is_real = True
    else:
        try:
            imag_part = sympy.im(r)
            if imag_part == 0 or sympy.simplify(imag_part) == 0:
                is_real = True
        except Exception:
            pass
    if not is_real:
        return False, "non_real"

    # 2. Check all division denominators in original AST
    for n in ast_node.walk():
        if isinstance(n, BinaryOp) and n.op == "/":
            denom_sym = ast_to_sympy_expr(n.right)
            val = denom_sym.subs(var, r)
            try:
                simplified_val = sympy.simplify(val)
                if simplified_val == 0 or simplified_val.is_zero is True:
                    return False, "division_by_zero"
                if simplified_val.is_zero is None and not (simplified_val.is_number and simplified_val != 0):
                    return False, "undecidable_denominator"
            except Exception:
                return False, "undecidable_denominator"

    # 3. Check all zero exponents: base != 0
    for n in ast_node.walk():
        if isinstance(n, Power) and getattr(n, "exponent", None) is not None and getattr(n.exponent, "value", None) == 0:
            base_sym = ast_to_sympy_expr(n.base)
            val = base_sym.subs(var, r)
            try:
                simplified_val = sympy.simplify(val)
                if simplified_val == 0 or simplified_val.is_zero is True:
                    return False, "zero_power_zero_base"
                if simplified_val.is_zero is None and not (simplified_val.is_number and simplified_val != 0):
                    return False, "undecidable_base"
            except Exception:
                return False, "undecidable_base"

    # 4. Check all radicals in original AST (radicand >= 0)
    for n in ast_node.walk():
        if isinstance(n, Radical):
            rad_sym = ast_to_sympy_expr(n.radicand)
            val = rad_sym.subs(var, r)
            try:
                simplified_val = sympy.simplify(val)
                if simplified_val.is_negative is True:
                    return False, "negative_radicand"
                if simplified_val.is_number and simplified_val < 0:
                    return False, "negative_radicand"
                if simplified_val.is_nonnegative is False:
                    return False, "negative_radicand"
                if simplified_val.is_nonnegative is None and not simplified_val.is_number:
                    if sympy.simplify(simplified_val < 0) is sympy.S.true:
                        return False, "negative_radicand"
            except Exception:
                return False, "evaluation_failed"

    # 5. Check LHS vs RHS substitution exact identity without float epsilon
    try:
        lhs_val = lhs_sym.subs(var, r)
        rhs_val = rhs_sym.subs(var, r)
        diff = sympy.simplify(lhs_val - rhs_val)
        if diff == 0 or diff.is_zero is True:
            return True, "valid"
        elif diff.is_zero is False:
            return False, "lhs_rhs_mismatch"
        elif diff.is_number and diff != 0:
            return False, "lhs_rhs_mismatch"
        else:
            # Soundness requirement: undecidable equality must not be accepted
            return False, "undecidable_equality"
    except Exception:
        return False, "evaluation_failed"


def _execute_solve(ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
    """Solve an equation or expression in the real domain."""
    x = sympy.Symbol("x", real=True)
    if isinstance(sym_obj, sympy.Eq):
        eq = sym_obj
    else:
        eq = sympy.Eq(sym_obj, 0)

    # Check for identity equation with domain restrictions, e.g. (x-1)/(x-1) = 1, sqrt(x) = sqrt(x)
    diff_expr = sympy.cancel(eq.lhs - eq.rhs)

    if diff_expr == 0:
        domain_set = sympy.S.Reals
        has_radical_or_interval = False
        excluded_points: List[Any] = []

        for n in ast_node.walk():
            # 1. Radicals require radicand >= 0
            if isinstance(n, Radical):
                has_radical_or_interval = True
                try:
                    rad_sym = ast_to_sympy_expr(n.radicand)
                    rad_domain = sympy.solveset(rad_sym >= 0, x, domain=sympy.S.Reals)
                    if isinstance(rad_domain, sympy.ConditionSet):
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Radical domain condition {rad_sym} >= 0 could not be fully determined"
                        return
                    domain_set = domain_set.intersect(rad_domain)
                except Exception as ex:
                    response.mathematical_status = EngineStatus.UNRESOLVED
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = f"Failed to compute radical domain constraint for {n}: {ex}"
                    return

            # 2. Denominators require denom != 0
            elif isinstance(n, BinaryOp) and n.op == "/":
                try:
                    denom_sym = ast_to_sympy_expr(n.right)
                    denom_zeros = sympy.solveset(sympy.Eq(denom_sym, 0), x, domain=sympy.S.Reals)
                    if isinstance(denom_zeros, sympy.ConditionSet):
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Denominator singularity condition {denom_sym} = 0 could not be fully determined"
                        return
                    domain_set = domain_set - denom_zeros
                    if isinstance(denom_zeros, sympy.FiniteSet):
                        excluded_points.extend(list(denom_zeros))
                    elif hasattr(denom_zeros, "__iter__"):
                        excluded_points.extend(list(denom_zeros))
                except Exception as ex:
                    response.mathematical_status = EngineStatus.UNRESOLVED
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = f"Failed to compute denominator singularity constraint for {n}: {ex}"
                    return

            # 3. Base != 0 for 0-exponent
            elif isinstance(n, Power) and getattr(n, "exponent", None) is not None and getattr(n.exponent, "value", None) == 0:
                try:
                    base_sym = ast_to_sympy_expr(n.base)
                    base_zeros = sympy.solveset(sympy.Eq(base_sym, 0), x, domain=sympy.S.Reals)
                    if isinstance(base_zeros, sympy.ConditionSet):
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Base singularity condition {base_sym} = 0 could not be fully determined"
                        return
                    domain_set = domain_set - base_zeros
                    if isinstance(base_zeros, sympy.FiniteSet):
                        excluded_points.extend(list(base_zeros))
                except Exception as ex:
                    response.mathematical_status = EngineStatus.UNRESOLVED
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = f"Failed to compute zero-exponent base constraint for {n}: {ex}"
                    return

        # Check if resulting domain_set is unresolved (e.g. ConditionSet)
        if isinstance(domain_set, sympy.ConditionSet):
            response.mathematical_status = EngineStatus.UNRESOLVED
            response.verification_status = VerificationStatus.UNRESOLVED
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
            response.error_message = "Identity equation domain completeness could not be established"
            return

        if domain_set == sympy.S.Reals:
            response.symbolic_result = "All real numbers"
            response.latex_output = "\\mathbb{R}"
            response.mathematical_status = EngineStatus.SUCCESS
            response.domain_certainty = DomainCertainty.PROVEN_REALS
            response.verification_evidence = {
                "solution_type": "identity",
                "domain": "Reals",
            }
            return

        if domain_set == sympy.EmptySet or domain_set == sympy.S.EmptySet:
            response.symbolic_result = "{}"
            response.latex_output = "\\emptyset"
            response.mathematical_status = EngineStatus.SUCCESS
            response.verification_evidence = {
                "solution_type": "empty_set",
                "solution_set": [],
            }
            return

        # If only isolated point exclusions and no radicals
        if not has_radical_or_interval and excluded_points:
            unique_excl: List[Any] = []
            for p in excluded_points:
                if not any(sympy.simplify(p - u) == 0 for u in unique_excl):
                    unique_excl.append(p)
            try:
                unique_excl.sort(key=lambda item: float(item.evalf()) if hasattr(item, "evalf") else float(item))
            except Exception:
                pass
            excl_str = ", ".join([f"x != {format_sympy_symbolic(p)}" for p in unique_excl])
            latex_excl = ", ".join([format_sympy_latex(p) for p in unique_excl])
            response.symbolic_result = f"All real numbers except {excl_str}"
            response.latex_output = f"\\mathbb{{R}} \\setminus \\{{ {latex_excl} \\}}"
            response.mathematical_status = EngineStatus.SUCCESS
            response.domain_certainty = DomainCertainty.EXPLICIT_EXCLUSIONS
            response.verification_evidence = {
                "solution_type": "identity_with_exclusions",
                "excluded_points": [str(p) for p in unique_excl],
            }
            return

        # Otherwise format domain interval/set (e.g. [0, oo) or [2, 5) U (5, oo))
        response.symbolic_result = format_interval_symbolic(domain_set, var="x")
        response.latex_output = format_interval_latex(domain_set, var="x")
        response.mathematical_status = EngineStatus.SUCCESS
        response.domain_certainty = DomainCertainty.PROVEN_REALS
        response.verification_evidence = {
            "solution_type": "identity_interval",
            "domain_set": str(domain_set),
        }
        return

    # Collect all candidate roots from SymPy solve and pattern-based algebraic transformations
    raw_candidates = _collect_algebraic_candidates(ast_node, eq, x)

    # Deduplicate candidate roots
    unique_candidates: List[Any] = []
    for c in raw_candidates:
        if c is None:
            continue
        if not any(sympy.simplify(c - u) == 0 for u in unique_candidates):
            unique_candidates.append(c)

    # Validate each candidate against the original AST and domain constraints
    valid_roots: List[Any] = []
    extraneous_roots: List[Any] = []

    for c in unique_candidates:
        is_valid, reason = _validate_root_in_ast(c, ast_node, x, eq.lhs, eq.rhs)
        if is_valid:
            # Check against explicit string domain restrictions if any
            restr_valid = True
            for restriction in response.domain_restrictions:
                if restriction.startswith("x != "):
                    try:
                        excluded_val_node = parse_cas_expression(restriction.replace("x != ", ""))
                        excluded_val = ast_to_sympy_expr(excluded_val_node)
                        if sympy.simplify(c - excluded_val) == 0:
                            restr_valid = False
                            break
                    except Exception:
                        pass
            if restr_valid:
                valid_roots.append(c)
            else:
                extraneous_roots.append(c)
        else:
            if reason != "non_real":
                extraneous_roots.append(c)

    # Sort roots if comparable
    try:
        valid_roots.sort(key=lambda item: float(item.evalf()) if hasattr(item, "evalf") else float(item))
    except Exception:
        pass

    try:
        extraneous_roots.sort(key=lambda item: float(item.evalf()) if hasattr(item, "evalf") else float(item))
    except Exception:
        pass

    if extraneous_roots:
        response.warnings.append(
            f"Eliminated {len(extraneous_roots)} extraneous root(s): {', '.join(str(r) for r in extraneous_roots)}"
        )

    response.symbolic_result = format_solution_set_symbolic(valid_roots)
    response.latex_output = format_solution_set_latex(valid_roots)
    response.mathematical_status = EngineStatus.SUCCESS
    response.verification_evidence = {
        "root_count": len(valid_roots),
        "roots": [str(r) for r in valid_roots],
        "solution_set": [str(r) for r in valid_roots],
        "extraneous_roots": [str(r) for r in extraneous_roots],
        "domain": "Reals",
    }



def _execute_solve_system(ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
    """Solve a 2x2 linear equation system in the real domain."""
    if not isinstance(ast_node, LinearSystem) or not isinstance(sym_obj, (list, tuple)):
        response.mathematical_status = EngineStatus.INVALID_INPUT
        response.error_message = "Expected a system of linear equations"
        return

    # Enforce original AST polynomial scope: must not contain variable denominators
    if not is_polynomial_ast(ast_node):
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = "Systems with variable denominators or non-polynomial terms are out of scope for linear solver v0"
        return

    # Enforce original AST variable count: maximum 2 variables in original input
    orig_vars = sorted(list(ast_node.variables()))
    if len(orig_vars) > 2:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = f"Linear system has {len(orig_vars)} variables in original input; maximum 2 variables supported in v0"
        return

    if len(ast_node.equations) != 2 or len(sym_obj) != 2:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = "Only 2x2 linear systems are supported in v0"
        return

    # Extract equations and diffs
    eq1, eq2 = sym_obj[0], sym_obj[1]
    lhs1 = eq1.lhs if isinstance(eq1, sympy.Eq) else eq1
    rhs1 = eq1.rhs if isinstance(eq1, sympy.Eq) else 0
    lhs2 = eq2.lhs if isinstance(eq2, sympy.Eq) else eq2
    rhs2 = eq2.rhs if isinstance(eq2, sympy.Eq) else 0

    diff1 = sympy.cancel(lhs1 - rhs1)
    diff2 = sympy.cancel(lhs2 - rhs2)

    free_syms = sorted(list(diff1.free_symbols | diff2.free_symbols), key=lambda s: s.name)
    if len(free_syms) > 2:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = f"Linear system has {len(free_syms)} variables; maximum 2 variables supported"
        return

    # Select canonical variables based on original AST input variables
    if len(orig_vars) == 2:
        sym_vars = [sympy.Symbol(v, real=True) for v in orig_vars]
    elif len(orig_vars) == 1:
        primary = orig_vars[0]
        other_name = "y" if primary != "y" else "x"
        sym_vars = [sympy.Symbol(primary, real=True), sympy.Symbol(other_name, real=True)]
    elif len(free_syms) == 2:
        sym_vars = free_syms
    elif len(free_syms) == 1:
        primary = free_syms[0]
        other_name = "y" if primary.name != "y" else "x"
        sym_vars = [primary, sympy.Symbol(other_name, real=True)]
    else:
        sym_vars = [sympy.Symbol("x", real=True), sympy.Symbol("y", real=True)]

    # Verify linear degree <= 1 for all variables
    try:
        p1 = sympy.Poly(diff1, *sym_vars)
        p2 = sympy.Poly(diff2, *sym_vars)
        if p1.total_degree() > 1 or p2.total_degree() > 1:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.error_message = "Non-linear equations are out of scope for the linear system solver"
            return
    except Exception:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = "Non-polynomial equations in system are out of scope"
        return

    # Solve via linsolve
    try:
        sol_set = sympy.linsolve([diff1, diff2], sym_vars)
    except Exception as ex:
        response.mathematical_status = EngineStatus.INTERNAL_ERROR
        response.error_message = f"Failed to solve linear system: {ex}"
        return

    if sol_set == sympy.EmptySet or len(sol_set) == 0:
        response.symbolic_result = "No solution (Inconsistent system)"
        response.latex_output = "\\emptyset"
        response.mathematical_status = EngineStatus.SUCCESS
        response.verification_evidence = {
            "system_type": "inconsistent",
            "variables": [str(v) for v in sym_vars],
            "solution_count": 0,
            "solution_set": [],
        }
        return

    sol_tuple = list(sol_set)[0]
    has_free_parameters = any(val.free_symbols for val in sol_tuple)
    sol_dict = {str(v): val for v, val in zip(sym_vars, sol_tuple)}

    if has_free_parameters:
        response.symbolic_result = f"Infinitely many solutions (Dependent system: {format_system_symbolic(sol_dict)})"
        response.latex_output = format_system_latex(sol_dict)
        response.mathematical_status = EngineStatus.SUCCESS
        response.verification_evidence = {
            "system_type": "dependent",
            "variables": [str(v) for v in sym_vars],
            "parametric_form": {str(k): format_sympy_symbolic(v) for k, v in sol_dict.items()},
            "solution_set": [format_system_symbolic(sol_dict)],
        }
    else:
        response.symbolic_result = format_system_symbolic(sol_dict)
        response.latex_output = format_system_latex(sol_dict)
        response.mathematical_status = EngineStatus.SUCCESS
        response.verification_evidence = {
            "system_type": "unique",
            "variables": [str(v) for v in sym_vars],
            "solution": {str(k): format_sympy_symbolic(v) for k, v in sol_dict.items()},
            "solution_set": [format_system_symbolic(sol_dict)],
        }


def _execute_solve_inequality(ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
    """Solve a univariate real polynomial inequality with degree <= 2."""
    if not isinstance(ast_node, Inequality) or not hasattr(sym_obj, "lhs"):
        response.mathematical_status = EngineStatus.INVALID_INPUT
        response.error_message = "Expected an inequality relation"
        return

    # Enforce original AST polynomial scope: must not contain variable denominators
    if not is_polynomial_ast(ast_node):
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = "Inequalities with variable denominators or non-polynomial expressions are out of scope for v0 polynomial inequality solver"
        return

    # Enforce original AST variable count: maximum 1 variable in original input
    orig_vars = sorted(list(ast_node.variables()))
    if len(orig_vars) > 1:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = f"Multivariate inequalities with {len(orig_vars)} variables in original input are out of scope for v0 single-variable inequality solver"
        return

    diff_expr = sympy.cancel(sym_obj.lhs - sym_obj.rhs)
    free_syms = sorted(list(diff_expr.free_symbols), key=lambda s: s.name)

    if len(free_syms) > 1:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = f"Multivariate inequalities with {len(free_syms)} variables are out of scope"
        return

    if not free_syms:
        is_true = bool(sympy.simplify(sym_obj))
        if is_true:
            response.symbolic_result = "(-oo, oo)"
            response.latex_output = "\\mathbb{R}"
            response.verification_evidence = {"solution_set": ["(-oo, oo)"]}
        else:
            response.symbolic_result = "No real solution"
            response.latex_output = "\\emptyset"
            response.verification_evidence = {"solution_set": []}
        response.mathematical_status = EngineStatus.SUCCESS
        return

    var = free_syms[0]
    try:
        poly = sympy.Poly(diff_expr, var)
        deg = poly.degree()
        if deg > 2:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.error_message = f"Polynomial inequalities with degree {deg} > 2 are out of scope"
            return
    except Exception:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.error_message = "Non-polynomial inequalities are out of scope"
        return

    try:
        sol_set = sympy.solveset(sym_obj, var, domain=sympy.S.Reals)
    except Exception as ex:
        response.mathematical_status = EngineStatus.INTERNAL_ERROR
        response.error_message = f"Failed to solve inequality: {ex}"
        return

    response.symbolic_result = format_interval_symbolic(sol_set, var=var.name)
    response.latex_output = format_interval_latex(sol_set, var=var.name)
    response.mathematical_status = EngineStatus.SUCCESS
    response.verification_evidence = {
        "variable": var.name,
        "degree": deg,
        "interval_symbolic": response.symbolic_result,
        "interval_latex": response.latex_output,
        "solution_set": [response.symbolic_result] if response.symbolic_result != "No real solution" else [],
    }


def _execute_simplify(sym_obj: Any, response: ExecutionResponse) -> None:
    """Simplify an algebraic expression."""
    if isinstance(sym_obj, sympy.Eq):
        simplified = sympy.Eq(
            sympy.cancel(sympy.simplify(sym_obj.lhs)),
            sympy.cancel(sympy.simplify(sym_obj.rhs)),
        )
    else:
        simplified = sympy.cancel(sympy.simplify(sym_obj))
        expanded = sympy.expand(sym_obj)
        if str(expanded) != str(sym_obj) and str(simplified) == str(sym_obj):
            simplified = expanded

    if hasattr(simplified, "has") and simplified.has(sympy.I):
        raise DomainRestrictionError("Expression result is complex and undefined in real domain.")

    response.symbolic_result = format_sympy_symbolic(simplified)
    response.latex_output = format_sympy_latex(simplified)
    response.mathematical_status = EngineStatus.SUCCESS



def _execute_differentiate(
    sym_obj: Any,
    var_name: str,
    options: Dict[str, Any],
    response: ExecutionResponse,
) -> None:
    """Differentiate expression with respect to var_name."""
    if isinstance(sym_obj, sympy.Eq):
        raise DomainRestrictionError("Differentiation requires an expression, not an equation.")
    var = sympy.Symbol(var_name, real=True)
    order = int(options.get("order", 1))
    derivative = sympy.diff(sym_obj, var, order)
    response.symbolic_result = format_sympy_symbolic(derivative)
    response.latex_output = format_sympy_latex(derivative)
    response.mathematical_status = EngineStatus.SUCCESS


def _execute_integrate(
    sym_obj: Any,
    var_name: str,
    options: Dict[str, Any],
    response: ExecutionResponse,
) -> None:
    """Integrate expression (definite if bounds given, else indefinite)."""
    if isinstance(sym_obj, sympy.Eq):
        raise DomainRestrictionError("Integration requires an expression, not an equation.")
    var = sympy.Symbol(var_name, real=True)
    lower = options.get("lower")
    upper = options.get("upper")

    if lower is not None and upper is not None:
        # Bounds are already strictly parsed numeric types/rationals
        definite_res = sympy.integrate(sym_obj, (var, lower, upper))
        response.symbolic_result = format_sympy_symbolic(definite_res)
        response.latex_output = format_sympy_latex(definite_res)
    else:
        antiderivative = sympy.integrate(sym_obj, var)
        response.symbolic_result = format_integral_symbolic(antiderivative)
        response.latex_output = format_integral_latex(antiderivative)

    response.mathematical_status = EngineStatus.SUCCESS


def _execute_plot_2d(
    sym_obj: Any,
    var_name: str,
    options: Dict[str, Any],
    response: ExecutionResponse,
) -> None:
    """Generate bounded 2D plot sampling data, splitting across discontinuities."""
    if isinstance(sym_obj, sympy.Eq):
        raise DomainRestrictionError("2D Function plotting requires an expression, not an equation.")

    x_min = float(options.get("x_min", -10.0))
    x_max = float(options.get("x_max", 10.0))
    num_points = int(options.get("num_points", options.get("points", 201)))
    num_points = max(20, min(num_points, 1000))

    if x_min >= x_max:
        x_min, x_max = -10.0, 10.0

    var = sympy.Symbol(var_name, real=True)
    step = (x_max - x_min) / (num_points - 1)

    segments: List[List[Dict[str, float]]] = []
    current_segment: List[Dict[str, float]] = []
    discontinuities: List[float] = []

    known_discontinuities: Set[float] = set()
    for r in response.domain_restrictions:
        if r.startswith("x != "):
            try:
                disc_val = float(sympy.sympify(r.replace("x != ", "")).evalf())
                known_discontinuities.add(disc_val)
                discontinuities.append(disc_val)
            except Exception:
                pass

    f = sympy.lambdify(var, sym_obj, modules=["math", {"zoo": math.nan}])

    def flush_segment():
        nonlocal current_segment
        if current_segment:
            segments.append(current_segment)
            current_segment = []

    for i in range(num_points):
        xi = x_min + i * step
        is_near_disc = any(abs(xi - d) < (step * 0.75) for d in known_discontinuities)

        if is_near_disc:
            flush_segment()
            continue

        try:
            yi_val = f(xi)
            if isinstance(yi_val, complex):
                if abs(yi_val.imag) < 1e-9:
                    yi_val = yi_val.real
                else:
                    flush_segment()
                    continue

            yi = float(yi_val)
            if math.isnan(yi) or math.isinf(yi):
                flush_segment()
            else:
                clipped_yi = max(-1000.0, min(yi, 1000.0))
                current_segment.append({"x": round(xi, 4), "y": round(clipped_yi, 4)})
        except (ZeroDivisionError, ValueError, OverflowError):
            flush_segment()

    flush_segment()

    response.symbolic_result = format_sympy_symbolic(sym_obj)
    response.latex_output = format_sympy_latex(sym_obj)
    response.plot_data = {
        "x_min": x_min,
        "x_max": x_max,
        "segments": segments,
        "discontinuities": sorted(discontinuities),
        "points_count": sum(len(seg) for seg in segments),
    }
    response.mathematical_status = EngineStatus.SUCCESS


class SymPyAdapter(MathEngine):
    """Adapter wrapping mature SymPy CAS symbolic algorithms."""

    ENGINE_ID = "sympy_cas_v0"

    def __init__(self) -> None:
        self._version = sympy.__version__

    @property
    def engine_id(self) -> str:
        return self.ENGINE_ID

    def get_capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.ENGINE_ID,
            engine_name="SymPy CAS Engine",
            version=self._version,
            license="3-clause BSD",
            supported_operations={
                OperationType.SOLVE,
                OperationType.SOLVE_SYSTEM,
                OperationType.SOLVE_INEQUALITY,
                OperationType.SIMPLIFY,
                OperationType.DIFFERENTIATE,
                OperationType.INTEGRATE,
                OperationType.PLOT_2D,
            },
            is_installed=True,
            is_verified_kernel=False,
            description="Mature symbolic computer algebra system for general algebraic manipulation, calculus, and plotting.",
        )

    def can_handle(self, request: ExecutionRequest) -> bool:
        caps = self.get_capabilities()
        return request.operation in caps.supported_operations

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute request using supervised process worker or direct execution."""
        # Check if in-process execution is requested (e.g., inside worker target or unit tests)
        if request.options.get("in_process", False):
            return execute_sympy_direct(request)

        # By default, run inside supervised child process with hard timeout
        from .process_runner import run_in_supervised_process
        return run_in_supervised_process(request)
