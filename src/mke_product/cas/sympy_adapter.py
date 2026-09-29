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
    FunctionCall,
    Group,
    IntegerLiteral,
    NamedConstant,
    Power,
    Radical,
    UnaryOp,
    Variable,
)

from .ast_bridge import ast_to_sympy, ast_to_sympy_expr
from .cas_parser import (
    CASPower,
    Inequality,
    LinearSystem,
    is_top_level_system,
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
                # Auto-detect system (presence of top-level , or ; with =) or inequality
                if is_top_level_system(input_text) and "=" in input_text:
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
            if isinstance(n, (Power, CASPower)) and isinstance(n.exponent, IntegerLiteral) and n.exponent.value == 0:
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

            elif isinstance(n, FunctionCall):
                if n.name in ("log", "ln"):
                    if len(n.args[0].variables()) == 0:
                        sym_arg = ast_to_sympy_expr(n.args[0])
                        try:
                            simplified_arg = sympy.simplify(sym_arg)
                            if simplified_arg.is_number and (simplified_arg.is_nonpositive or (hasattr(simplified_arg, "evalf") and float(simplified_arg.evalf()) <= 0)):
                                raise DomainRestrictionError("Logarithm of non-positive real number is undefined in real domain.")
                        except DomainRestrictionError:
                            raise
                        except Exception as exc:
                            response.mathematical_status = EngineStatus.UNRESOLVED
                            response.verification_status = VerificationStatus.UNRESOLVED
                            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                            response.error_message = f"Undecidable logarithm argument definedness: {exc}"
                            return response
                    if n.name == "log" and len(n.args) == 2 and len(n.args[1].variables()) == 0:
                        sym_base = ast_to_sympy_expr(n.args[1])
                        try:
                            simplified_base = sympy.simplify(sym_base)
                            if simplified_base.is_number and (simplified_base.is_nonpositive or (hasattr(simplified_base, "evalf") and float(simplified_base.evalf()) <= 0) or simplified_base == 1):
                                raise DomainRestrictionError("Logarithm base must be positive and not equal to 1.")
                        except DomainRestrictionError:
                            raise
                        except Exception as exc:
                            response.mathematical_status = EngineStatus.UNRESOLVED
                            response.verification_status = VerificationStatus.UNRESOLVED
                            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                            response.error_message = f"Undecidable logarithm base definedness: {exc}"
                            return response
                elif n.name == "tan":
                    if len(n.args[0].variables()) == 0:
                        sym_arg = ast_to_sympy_expr(n.args[0])
                        try:
                            cos_val = sympy.simplify(sympy.cos(sym_arg))
                            if cos_val == 0 or cos_val.is_zero is True:
                                raise DomainRestrictionError("Tangent is undefined when cosine is zero.")
                        except DomainRestrictionError:
                            raise
                        except Exception as exc:
                            response.mathematical_status = EngineStatus.UNRESOLVED
                            response.verification_status = VerificationStatus.UNRESOLVED
                            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                            response.error_message = f"Undecidable tangent definedness: {exc}"
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
            if response.domain_certainty is None:
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
        elif response.mathematical_status == EngineStatus.OUT_OF_SCOPE:
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

        # Logarithmic sum/diff transformation: e.g. log(f, b) + log(g, b) = c -> f * g = b^c
        if isinstance(left_ast, BinaryOp) and left_ast.op in ("+", "-"):
            if (
                isinstance(left_ast.left, FunctionCall)
                and left_ast.left.name in ("log", "ln")
                and isinstance(left_ast.right, FunctionCall)
                and left_ast.right.name in ("log", "ln")
            ):
                f_sym = ast_to_sympy_expr(left_ast.left.args[0])
                g_sym = ast_to_sympy_expr(left_ast.right.args[0])
                base_ast = left_ast.left.args[1] if len(left_ast.left.args) == 2 else None
                base_sym = ast_to_sympy_expr(base_ast) if base_ast is not None else (sympy.E if left_ast.left.name == "ln" else 10)
                if left_ast.op == "+":
                    alg_eq = sympy.Eq(f_sym * g_sym, base_sym ** rhs_sym)
                else:
                    alg_eq = sympy.Eq(f_sym, g_sym * (base_sym ** rhs_sym))
                try:
                    roots = sympy.solve(alg_eq, var)
                    if not isinstance(roots, (list, tuple, set)):
                        roots = [roots]
                    candidates.extend(roots)
                except Exception:
                    pass

        # Logarithmic equations: logcombine
        try:
            log_comb = sympy.logcombine(lhs_sym - rhs_sym, force=True)
            roots = sympy.solve(log_comb, var)
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

    # 5. Check all logarithmic and trigonometric domain conditions
    for n in ast_node.walk():
        if isinstance(n, FunctionCall):
            if n.name in ("log", "ln"):
                arg_sym = ast_to_sympy_expr(n.args[0])
                val = arg_sym.subs(var, r)
                try:
                    simplified_val = sympy.simplify(val)
                    if simplified_val.is_negative is True or simplified_val == 0 or simplified_val.is_zero is True:
                        return False, "non_positive_log_argument"
                    if simplified_val.is_number and simplified_val <= 0:
                        return False, "non_positive_log_argument"
                    if simplified_val.is_positive is False:
                        return False, "non_positive_log_argument"
                except Exception:
                    return False, "evaluation_failed"

                if n.name == "log" and len(n.args) == 2:
                    base_sym = ast_to_sympy_expr(n.args[1])
                    b_val = base_sym.subs(var, r)
                    try:
                        simplified_b = sympy.simplify(b_val)
                        if simplified_b.is_negative is True or simplified_b == 0 or simplified_b.is_zero is True or simplified_b == 1:
                            return False, "invalid_log_base"
                        if simplified_b.is_number and (simplified_b <= 0 or simplified_b == 1):
                            return False, "invalid_log_base"
                    except Exception:
                        return False, "evaluation_failed"

            elif n.name == "tan":
                arg_sym = ast_to_sympy_expr(n.args[0])
                val = arg_sym.subs(var, r)
                try:
                    cos_val = sympy.simplify(sympy.cos(val))
                    if cos_val == 0 or cos_val.is_zero is True:
                        return False, "tan_undefined_pole"
                except Exception:
                    return False, "evaluation_failed"

    # 6. Check LHS vs RHS substitution exact identity without float epsilon
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


def format_family_symbolic(c0: Any, ck: Any) -> str:
    """Format a periodic root family C0 + Ck * k * pi in clean mathematical notation."""
    c0_s = sympy.nsimplify(c0)
    ck_s = sympy.nsimplify(ck)
    parts = []
    if c0_s != 0:
        parts.append(format_sympy_symbolic(c0_s))
    if ck_s == 1:
        parts.append("k*pi")
    elif ck_s == 2:
        parts.append("2*k*pi")
    elif ck_s == -1:
        parts.append("-k*pi")
    elif ck_s == -2:
        parts.append("-2*k*pi")
    elif isinstance(ck_s, (int, sympy.Integer)):
        parts.append(f"{ck_s}*k*pi")
    elif isinstance(ck_s, sympy.Rational):
        if ck_s.q == 1:
            parts.append(f"{ck_s.p}*k*pi")
        elif ck_s.p == 1:
            parts.append(f"k*pi/{ck_s.q}")
        else:
            parts.append(f"{ck_s.p}*k*pi/{ck_s.q}")
    else:
        parts.append(f"{format_sympy_symbolic(ck_s)}*k*pi")

    if len(parts) == 1:
        return parts[0]
    return " + ".join(parts)


def format_family_latex(c0: Any, ck: Any) -> str:
    """Format a periodic root family C0 + Ck * k * pi in clean LaTeX."""
    c0_s = sympy.nsimplify(c0)
    ck_s = sympy.nsimplify(ck)
    parts = []
    if c0_s != 0:
        parts.append(format_sympy_latex(c0_s))
    if ck_s == 1:
        parts.append("k\\pi")
    elif ck_s == 2:
        parts.append("2k\\pi")
    elif isinstance(ck_s, (int, sympy.Integer)):
        parts.append(f"{ck_s}k\\pi")
    elif isinstance(ck_s, sympy.Rational):
        if ck_s.q == 1:
            parts.append(f"{ck_s.p}k\\pi")
        elif ck_s.p == 1:
            parts.append(f"\\frac{{k\\pi}}{{{ck_s.q}}}")
        else:
            parts.append(f"\\frac{{{ck_s.p}k\\pi}}{{{ck_s.q}}}")
    else:
        parts.append(f"{format_sympy_latex(ck_s)}k\\pi")

    if len(parts) == 1:
        return parts[0]
    return " + ".join(parts)


def _solve_periodic_trigonometric(
    ast_node: ASTNode,
    eq: sympy.Eq,
    var: sympy.Symbol,
    response: ExecutionResponse,
) -> None:
    """Solve elementary periodic trigonometric equations sin(ax+b)=m, cos(ax+b)=m, tan(ax+b)=m."""
    func_name: Optional[str] = None
    arg_sym: Optional[sympy.Expr] = None
    rhs_sym: Optional[sympy.Expr] = None

    if isinstance(ast_node, Equation):
        left_ast = ast_node.left
        right_ast = ast_node.right
        if isinstance(left_ast, FunctionCall) and left_ast.name in ("sin", "cos", "tan") and len(right_ast.variables()) == 0:
            func_name = left_ast.name
            arg_sym = ast_to_sympy_expr(left_ast.args[0])
            rhs_sym = ast_to_sympy_expr(right_ast)
        elif isinstance(right_ast, FunctionCall) and right_ast.name in ("sin", "cos", "tan") and len(left_ast.variables()) == 0:
            func_name = right_ast.name
            arg_sym = ast_to_sympy_expr(right_ast.args[0])
            rhs_sym = ast_to_sympy_expr(left_ast)

    if func_name is None:
        diff = sympy.simplify(eq.lhs - eq.rhs)
        for cand_func in (sympy.sin, sympy.cos, sympy.tan):
            matches = diff.atoms(cand_func)
            if len(matches) == 1:
                term = list(matches)[0]
                t_arg = term.args[0]
                if len(t_arg.free_symbols) == 1 and var in t_arg.free_symbols:
                    term_dummy = sympy.Symbol("__trig_term__")
                    diff_sub = diff.subs(term, term_dummy)
                    term_sol = sympy.solve(diff_sub, term_dummy)
                    if term_sol and len(term_sol) == 1 and len(term_sol[0].free_symbols) == 0:
                        func_name = cand_func.__name__.lower()
                        arg_sym = t_arg
                        rhs_sym = term_sol[0]
                        break

    if func_name is None or arg_sym is None or rhs_sym is None:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.verification_status = VerificationStatus.UNRESOLVED
        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        response.error_message = "Nonlinear or unclassified periodic trigonometric equation is out of scope for exact family solver"
        return

    try:
        poly = sympy.Poly(arg_sym, var)
        if poly.degree() != 1:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.verification_status = VerificationStatus.UNRESOLVED
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
            response.error_message = "Nonlinear argument in trigonometric equation is out of scope for exact family solver"
            return
        coeffs = poly.all_coeffs()
        a = coeffs[0]
        b = coeffs[1]
    except Exception as exc:
        response.mathematical_status = EngineStatus.UNRESOLVED
        response.verification_status = VerificationStatus.UNRESOLVED
        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        response.error_message = f"Failed to analyze trigonometric argument: {exc}"
        return

    m = sympy.simplify(rhs_sym)

    if func_name in ("sin", "cos"):
        if (m.is_number and (m > 1 or m < -1)) or (hasattr(m, "evalf") and abs(float(m.evalf())) > 1.0 + 1e-12):
            response.symbolic_result = "{}"
            response.latex_output = "\\emptyset"
            response.mathematical_status = EngineStatus.SUCCESS
            response.domain_certainty = DomainCertainty.PROVEN_REALS
            response.verification_evidence = {
                "solution_type": "empty_set",
                "solution_set": [],
            }
            return

        if func_name == "sin":
            alpha = sympy.asin(m)
            if m == 0:
                c0 = sympy.simplify(-b / a)
                ck = sympy.simplify(sympy.Rational(1, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 1 / abs(a))
                families = [(c0, ck)]
            elif m == 1:
                c0 = sympy.simplify((sympy.pi/2 - b) / a)
                ck = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0, ck)]
            elif m == -1:
                c0 = sympy.simplify((-sympy.pi/2 - b) / a)
                ck = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0, ck)]
            else:
                c0_1 = sympy.simplify((alpha - b) / a)
                ck_1 = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                c0_2 = sympy.simplify((sympy.pi - alpha - b) / a)
                ck_2 = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0_1, ck_1), (c0_2, ck_2)]

        elif func_name == "cos":
            alpha = sympy.acos(m)
            if m == 1:
                c0 = sympy.simplify(-b / a)
                ck = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0, ck)]
            elif m == -1:
                c0 = sympy.simplify((sympy.pi - b) / a)
                ck = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0, ck)]
            elif m == 0:
                c0 = sympy.simplify((sympy.pi/2 - b) / a)
                ck = sympy.simplify(sympy.Rational(1, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 1 / abs(a))
                families = [(c0, ck)]
            else:
                c0_1 = sympy.simplify((alpha - b) / a)
                ck_1 = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                c0_2 = sympy.simplify((-alpha - b) / a)
                ck_2 = sympy.simplify(sympy.Rational(2, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 2 / abs(a))
                families = [(c0_1, ck_1), (c0_2, ck_2)]

    elif func_name == "tan":
        alpha = sympy.atan(m)
        c0 = sympy.simplify((alpha - b) / a)
        ck = sympy.simplify(sympy.Rational(1, abs(a)) if hasattr(a, "is_integer") and a.is_integer else 1 / abs(a))
        families = [(c0, ck)]
    else:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.verification_status = VerificationStatus.UNRESOLVED
        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        response.error_message = f"Unsupported trigonometric function: {func_name}"
        return

    sym_family_strs = []
    latex_family_strs = []
    evidence_family_strs = []
    for c0_val, ck_val in families:
        s_fam = format_family_symbolic(c0_val, ck_val)
        l_fam = format_family_latex(c0_val, ck_val)
        sym_family_strs.append(f"x = {s_fam}")
        latex_family_strs.append(f"x = {l_fam}")
        evidence_family_strs.append(s_fam)

    response.symbolic_result = ", ".join(sym_family_strs) + " (k in Z)"
    response.latex_output = " \\quad \\lor \\quad ".join(latex_family_strs) + " \\quad (k \\in \\mathbb{Z})"
    response.mathematical_status = EngineStatus.SUCCESS
    response.domain_certainty = DomainCertainty.PROVEN_REALS if func_name != "tan" else DomainCertainty.EXPLICIT_EXCLUSIONS
    response.verification_evidence = {
        "solution_type": "periodic_family",
        "families": evidence_family_strs,
        "solution_set": evidence_family_strs,
        "parameter": "k in Z",
    }


def _collect_variable_positions(
    node: ASTNode,
    var_name: str,
    in_exp: bool = False,
    in_log: bool = False,
    in_trig: bool = False,
) -> Tuple[bool, bool, bool, bool]:
    """Inspect AST positions where variable appears: (in_poly, in_exp, in_log, in_trig)."""
    if isinstance(node, Variable):
        if node.name == var_name:
            return (not in_exp and not in_log and not in_trig, in_exp, in_log, in_trig)
        return (False, False, False, False)

    if isinstance(node, (Power, CASPower)):
        b_poly, b_exp, b_log, b_trig = _collect_variable_positions(node.base, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)
        e_poly, e_exp, e_log, e_trig = _collect_variable_positions(node.exponent, var_name, in_exp=True, in_log=in_log, in_trig=in_trig)
        return (b_poly or e_poly, b_exp or e_exp, b_log or e_log, b_trig or e_trig)

    if isinstance(node, FunctionCall):
        if node.name == "exp":
            res = [_collect_variable_positions(arg, var_name, in_exp=True, in_log=in_log, in_trig=in_trig) for arg in node.args]
        elif node.name in ("log", "ln"):
            res = [_collect_variable_positions(arg, var_name, in_exp=in_exp, in_log=True, in_trig=in_trig) for arg in node.args]
        elif node.name in ("sin", "cos", "tan"):
            res = [_collect_variable_positions(arg, var_name, in_exp=in_exp, in_log=in_log, in_trig=True) for arg in node.args]
        else:
            res = [_collect_variable_positions(arg, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig) for arg in node.args]
        p = any(r[0] for r in res)
        e = any(r[1] for r in res)
        l = any(r[2] for r in res)
        t = any(r[3] for r in res)
        return (p, e, l, t)

    if isinstance(node, AbsoluteValue):
        return _collect_variable_positions(node.inner, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)

    if isinstance(node, Radical):
        return _collect_variable_positions(node.radicand, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)

    if isinstance(node, Group):
        return _collect_variable_positions(node.inner, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)

    if isinstance(node, UnaryOp):
        return _collect_variable_positions(node.operand, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)

    if isinstance(node, BinaryOp):
        l_res = _collect_variable_positions(node.left, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)
        r_res = _collect_variable_positions(node.right, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)
        return (l_res[0] or r_res[0], l_res[1] or r_res[1], l_res[2] or r_res[2], l_res[3] or r_res[3])

    if isinstance(node, Equation):
        l_res = _collect_variable_positions(node.left, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)
        r_res = _collect_variable_positions(node.right, var_name, in_exp=in_exp, in_log=in_log, in_trig=in_trig)
        return (l_res[0] or r_res[0], l_res[1] or r_res[1], l_res[2] or r_res[2], l_res[3] or r_res[3])

    return (False, False, False, False)


def _has_non_elementary_atoms(expr: Any) -> bool:
    """Check if expression contains non-elementary or unresolved symbolic constructs."""
    if expr is None:
        return False
    if hasattr(expr, "atoms"):
        for atom in expr.atoms():
            name = type(atom).__name__
            if name in ("LambertW", "RootOf", "Integral", "Derivative", "AccumBounds", "Piecewise", "ConditionSet"):
                return True
    return False


def _extract_exponential_atoms(ast_node: ASTNode, var_name: str) -> List[Tuple[Any, ASTNode]]:
    """Extract all exponential atoms containing var_name as (base_expr_or_node, exp_ast)."""
    atoms: List[Tuple[Any, ASTNode]] = []
    for n in ast_node.walk():
        if isinstance(n, (Power, CASPower)):
            if var_name in n.exponent.variables():
                atoms.append((n.base, n.exponent))
        elif isinstance(n, FunctionCall) and n.name == "exp":
            if var_name in n.args[0].variables():
                atoms.append((sympy.E, n.args[0]))
    return atoms


def _get_primary_base(base_sym: Any) -> Optional[Tuple[Any, int]]:
    """Determine primary positive base b0 and power k such that base_sym == b0^k."""
    try:
        if base_sym == sympy.E or base_sym == sympy.exp(1):
            return (sympy.E, 1)
        if isinstance(base_sym, (int, sympy.Integer)) and base_sym > 1:
            val = int(base_sym)
            for b0 in (2, 3, 5, 6, 7, 10):
                temp = val
                k = 0
                while temp > 1 and temp % b0 == 0:
                    temp //= b0
                    k += 1
                if temp == 1 and k > 0:
                    return (sympy.Integer(b0), k)
            return (sympy.Integer(val), 1)
        if isinstance(base_sym, sympy.Rational) and base_sym > 0 and base_sym != 1:
            return (base_sym, 1)
    except Exception:
        pass
    return None


def _is_certified_exponential_equation(
    ast_node: ASTNode,
    eq: sympy.Eq,
    var: sympy.Symbol,
    valid_roots: List[Any],
    candidates: List[Any],
) -> Tuple[bool, str, str]:
    """Certify whether an exponential equation matches an algebraically exhaustive solvable family."""
    var_name = var.name
    exp_atoms = _extract_exponential_atoms(ast_node, var_name)
    if not exp_atoms:
        return False, "NO_EXP_ATOMS", "No exponential atoms found"

    # Check that all bases containing var are constant and compatible single primary base
    primary_bases = set()
    for base_item, _ in exp_atoms:
        if isinstance(base_item, ASTNode):
            if var_name in base_item.variables():
                return False, "VARIABLE_EXP_BASE", "Variable in exponential base is out of scope for complete certification"
            b_sym = ast_to_sympy_expr(base_item)
        else:
            b_sym = base_item
        p_base = _get_primary_base(b_sym)
        if p_base is None:
            return False, "INCOMPATIBLE_EXP_BASE", f"Unsupported exponential base {b_sym}"
        primary_bases.add(p_base[0])

    if len(primary_bases) != 1:
        return False, "MULTI_BASE_EXPONENTIAL", "Multiple incompatible exponential bases cannot be certified as complete"

    common_b0 = list(primary_bases)[0]

    # Verify linear degree of all exponents
    for _, exp_ast in exp_atoms:
        exp_sym = ast_to_sympy_expr(exp_ast)
        try:
            poly = sympy.Poly(exp_sym, var)
            if poly.degree() != 1:
                return False, "NONLINEAR_EXPONENT", "Nonlinear exponent is out of scope for complete certification"
        except Exception:
            return False, "NON_POLYNOMIAL_EXPONENT", "Non-polynomial exponent is out of scope"

    diff = sympy.cancel(eq.lhs - eq.rhs)

    # Empty solution set verification: must have explicit constructive proof
    if not valid_roots:
        if isinstance(ast_node, Equation):
            l_atoms = _extract_exponential_atoms(ast_node.left, var_name)
            r_atoms = _extract_exponential_atoms(ast_node.right, var_name)
            if len(l_atoms) == 1 and not r_atoms:
                rhs_sym = ast_to_sympy_expr(ast_node.right)
                if rhs_sym.is_number and rhs_sym <= 0:
                    return True, "PROVEN_EMPTY_EXPONENTIAL", "Exponential expression is strictly positive; RHS <= 0 has no real solutions"
            elif len(r_atoms) == 1 and not l_atoms:
                lhs_sym = ast_to_sympy_expr(ast_node.left)
                if lhs_sym.is_number and lhs_sym <= 0:
                    return True, "PROVEN_EMPTY_EXPONENTIAL", "Exponential expression is strictly positive; LHS <= 0 has no real solutions"

        try:
            u = sympy.Symbol("__u__", positive=True)
            diff_u = diff
            if common_b0 == 2:
                diff_u = diff_u.subs(4**var, u**2).subs(2**var, u)
            elif common_b0 == sympy.E:
                diff_u = diff_u.subs(sympy.exp(2*var), u**2).subs(sympy.exp(var), u)

            u_poly = sympy.Poly(diff_u, u)
            if u_poly.degree() == 2:
                coeffs = u_poly.all_coeffs()
                A, B, C = coeffs[0], coeffs[1], coeffs[2]
                delta = B**2 - 4*A*C
                if delta < 0:
                    return True, "PROVEN_EMPTY_EXP_QUADRATIC", "Discriminant < 0 in exponential quadratic substitution proves no real solutions"
                u_roots = sympy.solve(u_poly, u)
                if all(hasattr(ur, "is_real") and ur.is_real and ur <= 0 for ur in u_roots):
                    return True, "PROVEN_EMPTY_EXP_QUADRATIC", "All auxiliary roots u <= 0 prove no real solutions for exponential equation"
        except Exception:
            pass

        return False, "UNPROVEN_EMPTY_EXPONENTIAL", "Empty exponential solution set cannot be certified without a constructive proof"

    return True, "CERTIFIED_SINGLE_BASE_EXPONENTIAL", "Single-base elementary exponential equation completeness certified"


def _extract_logarithmic_atoms(ast_node: ASTNode, var_name: str) -> List[Tuple[ASTNode, Any]]:
    """Extract all logarithmic atoms containing var_name as (arg_ast, base_expr_or_ast)."""
    atoms: List[Tuple[ASTNode, Any]] = []
    for n in ast_node.walk():
        if isinstance(n, FunctionCall):
            if n.name == "ln" and var_name in n.args[0].variables():
                atoms.append((n.args[0], sympy.E))
            elif n.name == "log" and var_name in n.args[0].variables():
                b_item = n.args[1] if len(n.args) == 2 else 10
                atoms.append((n.args[0], b_item))
    return atoms


def _is_certified_logarithmic_equation(
    ast_node: ASTNode,
    eq: sympy.Eq,
    var: sympy.Symbol,
    valid_roots: List[Any],
    candidates: List[Any],
) -> Tuple[bool, str, str]:
    """Certify whether a logarithmic equation matches an algebraically exhaustive solvable family."""
    var_name = var.name
    log_atoms = _extract_logarithmic_atoms(ast_node, var_name)
    if not log_atoms:
        return False, "NO_LOG_ATOMS", "No logarithmic atoms found"

    # Check all bases are compatible constant base
    bases = set()
    for _, b_item in log_atoms:
        if isinstance(b_item, ASTNode):
            if var_name in b_item.variables():
                return False, "VARIABLE_LOG_BASE", "Variable log base is out of scope for complete certification"
            b_sym = ast_to_sympy_expr(b_item)
        else:
            b_sym = b_item
        bases.add(b_sym)

    if len(bases) != 1:
        return False, "MULTI_BASE_LOGARITHMIC", "Multiple log bases cannot be certified as complete"

    # Check argument polynomials are degree <= 2
    for arg_ast, _ in log_atoms:
        arg_sym = ast_to_sympy_expr(arg_ast)
        try:
            poly = sympy.Poly(arg_sym, var)
            if poly.degree() > 2:
                return False, "HIGH_DEGREE_LOG_ARG", "Log argument degree > 2 is out of scope for complete certification"
        except Exception:
            return False, "NON_POLYNOMIAL_LOG_ARG", "Non-polynomial log argument is out of scope"

    if not valid_roots:
        if candidates and all(_validate_root_in_ast(c, ast_node, var, eq.lhs, eq.rhs)[0] is False for c in candidates):
            return True, "PROVEN_EMPTY_LOGARITHMIC", "All algebraic candidates proved extraneous by domain constraints"
        return False, "UNPROVEN_EMPTY_LOGARITHMIC", "Empty logarithmic solution set cannot be certified without proof"

    return True, "CERTIFIED_SINGLE_BASE_LOGARITHMIC", "Single-base elementary logarithmic equation completeness certified"


def _is_certified_algebraic_equation(
    ast_node: ASTNode,
    eq: sympy.Eq,
    var: sympy.Symbol,
    valid_roots: List[Any],
    candidates: List[Any],
) -> Tuple[bool, str, str]:
    """Certify radical, rational, absolute value, and polynomial algebraic equations."""
    var_name = var.name

    # Polynomial equations
    if is_polynomial_ast(ast_node):
        diff = sympy.simplify(eq.lhs - eq.rhs)
        try:
            poly = sympy.Poly(diff, var)
            deg = poly.degree()
            if deg == 1:
                return True, "POLYNOMIAL_LINEAR", "Linear polynomial root completeness proven"
            if deg == 2:
                coeffs = poly.all_coeffs()
                A, B, C = coeffs[0], coeffs[1], coeffs[2]
                delta = B**2 - 4*A*C
                if delta < 0:
                    return True, "POLYNOMIAL_QUADRATIC_EMPTY", "Quadratic discriminant < 0 proves empty real solution set"
                return True, "POLYNOMIAL_QUADRATIC", "Quadratic polynomial roots completeness proven"
            if deg > 2:
                if valid_roots:
                    return True, "POLYNOMIAL_HIGHER_DEGREE", "Higher degree polynomial roots algebraically verified"
                real_r = poly.real_roots()
                if len(real_r) == 0:
                    return True, "POLYNOMIAL_HIGHER_DEGREE_EMPTY", "Sturm sequence proves polynomial has no real roots"
        except Exception:
            pass

    has_radical = any(isinstance(n, Radical) and var_name in n.variables() for n in ast_node.walk())
    has_abs = any(isinstance(n, AbsoluteValue) and var_name in n.variables() for n in ast_node.walk())
    has_division = any(isinstance(n, BinaryOp) and n.op == "/" and var_name in n.right.variables() for n in ast_node.walk())

    if has_radical or has_abs or has_division:
        if not valid_roots:
            if candidates and all(_validate_root_in_ast(c, ast_node, var, eq.lhs, eq.rhs)[0] is False for c in candidates):
                return True, "PROVEN_EMPTY_ALGEBRAIC", "All algebraic candidates proved extraneous by domain/singularity constraints"
            return False, "UNPROVEN_EMPTY_ALGEBRAIC", "Empty algebraic solution set cannot be certified without proof"

        return True, "CERTIFIED_ALGEBRAIC", "Algebraic equation candidate completeness and domain verification certified"

    return False, "UNCERTIFIED_ALGEBRAIC", "Equation does not match recognized algebraic complete forms"


def _certify_equation_completeness(
    ast_node: ASTNode,
    eq: sympy.Eq,
    var: sympy.Symbol,
    valid_roots: List[Any],
    unique_candidates: List[Any],
) -> Tuple[bool, str, str]:
    """Certify whether the equation and computed solution set are mathematically guaranteed exhaustive and complete.
    
    Returns (is_certified, category, reason).
    """
    var_name = var.name

    # 1. Reject non-elementary symbolic objects in candidate roots (e.g. LambertW)
    for c in unique_candidates:
        if _has_non_elementary_atoms(c):
            return False, "NON_ELEMENTARY", "Candidates contain non-elementary functions (e.g. LambertW/RootOf)"
    for r in valid_roots:
        if _has_non_elementary_atoms(r):
            return False, "NON_ELEMENTARY", "Valid roots contain non-elementary functions (e.g. LambertW/RootOf)"

    # 2. Check variable positions across the AST
    has_poly, has_exp, has_log, has_trig = _collect_variable_positions(ast_node, var_name)

    # 3. Reject mixed transcendental equations (Task A mandatory counterexamples)
    if has_exp and has_poly:
        return False, "MIXED_EXP_POLY", "Mixed exponential-polynomial equation is out of scope for complete certified solving"

    if has_log and has_poly:
        return False, "MIXED_LOG_POLY", "Mixed logarithmic-polynomial equation is out of scope for complete certified solving"

    if has_trig and (has_poly or has_exp or has_log):
        return False, "MIXED_TRIG_TRANSCENDENTAL", "Mixed trigonometric-transcendental equation is out of scope for complete certified solving"

    if has_exp and has_log:
        return False, "MIXED_EXP_LOG", "Mixed exponential-logarithmic equation is out of scope for complete certified solving"

    # 4. Pure Exponential Equations (narrowly recognized single-base forms)
    if has_exp and not has_poly and not has_log and not has_trig:
        is_cert, cat, reason = _is_certified_exponential_equation(ast_node, eq, var, valid_roots, unique_candidates)
        return is_cert, cat, reason

    # 5. Pure Logarithmic Equations (narrowly recognized single-base forms)
    if has_log and not has_poly and not has_exp and not has_trig:
        is_cert, cat, reason = _is_certified_logarithmic_equation(ast_node, eq, var, valid_roots, unique_candidates)
        return is_cert, cat, reason

    # 6. Pure Polynomial & Algebraic Equations (Radical, Rational, Absolute Value)
    if not has_exp and not has_log and not has_trig:
        is_cert, cat, reason = _is_certified_algebraic_equation(ast_node, eq, var, valid_roots, unique_candidates)
        return is_cert, cat, reason

    # Default fail-closed for unclassified expressions
    return False, "UNCLASSIFIED_NON_ELEMENTARY", "Equation class is not certified for exhaustive completeness"


def _execute_solve(ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
    """Solve an equation or expression in the real domain."""
    x = sympy.Symbol("x", real=True)
    if isinstance(sym_obj, sympy.Eq):
        eq = sym_obj
    else:
        eq = sympy.Eq(sym_obj, 0)

    # Check for identity equation with domain restrictions, e.g. (x-1)/(x-1) = 1, sqrt(x) = sqrt(x), ln(x) = ln(x), tan(x) = tan(x)
    diff_expr = sympy.cancel(eq.lhs - eq.rhs)

    if diff_expr == 0 or sympy.simplify(eq.lhs - eq.rhs) == 0:
        domain_set = sympy.S.Reals
        has_radical_or_interval = False
        excluded_points: List[Any] = []
        periodic_exclusions: List[Tuple[str, Any, Any]] = []

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

            # 4. Logarithms require argument > 0 and base > 0, base != 1
            elif isinstance(n, FunctionCall) and n.name in ("log", "ln"):
                has_radical_or_interval = True
                try:
                    arg_sym = ast_to_sympy_expr(n.args[0])
                    arg_domain = sympy.solveset(arg_sym > 0, x, domain=sympy.S.Reals)
                    if isinstance(arg_domain, sympy.ConditionSet):
                        response.mathematical_status = EngineStatus.UNRESOLVED
                        response.verification_status = VerificationStatus.UNRESOLVED
                        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                        response.error_message = f"Logarithm argument condition {arg_sym} > 0 could not be fully determined"
                        return
                    domain_set = domain_set.intersect(arg_domain)

                    if n.name == "log" and len(n.args) == 2:
                        base_sym = ast_to_sympy_expr(n.args[1])
                        base_pos = sympy.solveset(base_sym > 0, x, domain=sympy.S.Reals)
                        base_not_one = sympy.solveset(sympy.Ne(base_sym, 1), x, domain=sympy.S.Reals)
                        if isinstance(base_pos, sympy.ConditionSet) or isinstance(base_not_one, sympy.ConditionSet):
                            response.mathematical_status = EngineStatus.UNRESOLVED
                            response.verification_status = VerificationStatus.UNRESOLVED
                            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                            response.error_message = f"Logarithm base conditions could not be fully determined"
                            return
                        domain_set = domain_set.intersect(base_pos).intersect(base_not_one)
                except Exception as ex:
                    response.mathematical_status = EngineStatus.UNRESOLVED
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = f"Failed to compute logarithm domain constraint for {n}: {ex}"
                    return

            # 5. Tangent requires cos(arg) != 0 -> arg != pi/2 + k*pi
            elif isinstance(n, FunctionCall) and n.name == "tan":
                try:
                    arg_sym = ast_to_sympy_expr(n.args[0])
                    if len(arg_sym.free_symbols) == 1 and x in arg_sym.free_symbols:
                        poly = sympy.Poly(arg_sym, x)
                        if poly.degree() == 1:
                            a_coeff = poly.all_coeffs()[0]
                            b_coeff = poly.all_coeffs()[1]
                            periodic_exclusions.append(("tan", a_coeff, b_coeff))
                        else:
                            response.mathematical_status = EngineStatus.UNRESOLVED
                            response.verification_status = VerificationStatus.UNRESOLVED
                            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                            response.error_message = f"Non-linear tangent periodic domain could not be fully determined"
                            return
                except Exception as ex:
                    response.mathematical_status = EngineStatus.UNRESOLVED
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = f"Failed to compute tangent domain constraint for {n}: {ex}"
                    return

        # Check periodic exclusions
        if periodic_exclusions:
            unique_periodic: List[Tuple[str, Any, Any]] = []
            for item in periodic_exclusions:
                if not any(item[0] == u[0] and sympy.simplify(item[1] - u[1]) == 0 and sympy.simplify(item[2] - u[2]) == 0 for u in unique_periodic):
                    unique_periodic.append(item)

            if domain_set == sympy.S.Reals and len(unique_periodic) == 1:
                _, a_val, b_val = unique_periodic[0]
                c0 = sympy.nsimplify((sympy.pi/2 - b_val) / a_val)
                ck = sympy.nsimplify(sympy.Rational(1, a_val) if hasattr(a_val, "is_integer") and a_val.is_integer else 1 / a_val)

                excl_sym = format_family_symbolic(c0, ck)
                excl_lat = format_family_latex(c0, ck)
                response.symbolic_result = f"All real numbers except {excl_sym} (k integer)"
                response.latex_output = "\\mathbb{R} \\setminus \\left\\{ " + excl_lat + " \\;\\middle|\\; k \\in \\mathbb{Z} \\right\\}"
                response.mathematical_status = EngineStatus.SUCCESS
                response.domain_certainty = DomainCertainty.EXPLICIT_EXCLUSIONS
                response.verification_evidence = {
                    "solution_type": "identity_periodic_exclusions",
                    "periodic_exclusions": [f"{excl_sym}, k in Z"],
                }
                return
            else:
                response.mathematical_status = EngineStatus.UNRESOLVED
                response.verification_status = VerificationStatus.UNRESOLVED
                response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                response.error_message = "Composite or intersected periodic domain could not be fully determined"
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

        # If only isolated point exclusions and no radicals / intervals
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

        # Otherwise format domain interval/set (e.g. (0, oo), (1, oo), [0, oo) or [2, 5) U (5, oo))
        response.symbolic_result = format_interval_symbolic(domain_set, var="x")
        response.latex_output = format_interval_latex(domain_set, var="x")
        response.mathematical_status = EngineStatus.SUCCESS
        response.domain_certainty = DomainCertainty.PROVEN_REALS
        response.verification_evidence = {
            "solution_type": "identity_interval",
            "domain_set": str(domain_set),
        }
        return

    # Check if the equation involves periodic trigonometric functions with variables
    has_trig_vars = False
    for n in ast_node.walk():
        if isinstance(n, FunctionCall) and n.name in ("sin", "cos", "tan"):
            if len(n.variables()) > 0:
                has_trig_vars = True
                break

    if has_trig_vars:
        _solve_periodic_trigonometric(ast_node, eq, x, response)
        return

    # Pre-dispatch soundness gate: fail closed immediately for mixed transcendentals and multi-base systems
    has_poly, has_exp, has_log, has_trig = _collect_variable_positions(ast_node, x.name)
    if (has_exp and has_poly) or (has_log and has_poly) or (has_trig and (has_poly or has_exp or has_log)) or (has_exp and has_log):
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.verification_status = VerificationStatus.UNRESOLVED
        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        response.symbolic_result = None
        response.latex_output = None
        response.error_message = "Mixed transcendental equations are out of scope for complete certified solving"
        return

    if has_exp and not has_poly and not has_log and not has_trig:
        exp_atoms = _extract_exponential_atoms(ast_node, x.name)
        primary_bases = set()
        for base_item, _ in exp_atoms:
            if isinstance(base_item, ASTNode):
                if x.name in base_item.variables():
                    response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = "Variable in exponential base is out of scope"
                    return
                b_sym = ast_to_sympy_expr(base_item)
            else:
                b_sym = base_item
            p_base = _get_primary_base(b_sym)
            if p_base is None:
                response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                response.verification_status = VerificationStatus.UNRESOLVED
                response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                response.error_message = f"Unsupported exponential base {b_sym}"
                return
            primary_bases.add(p_base[0])
        if len(primary_bases) > 1:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.verification_status = VerificationStatus.UNRESOLVED
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
            response.error_message = "Multi-base exponential equations are out of scope for complete certified solving"
            return

    if has_log and not has_poly and not has_exp and not has_trig:
        log_atoms = _extract_logarithmic_atoms(ast_node, x.name)
        bases = set()
        for _, b_item in log_atoms:
            if isinstance(b_item, ASTNode):
                if x.name in b_item.variables():
                    response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                    response.verification_status = VerificationStatus.UNRESOLVED
                    response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
                    response.error_message = "Variable in log base is out of scope"
                    return
                b_sym = ast_to_sympy_expr(b_item)
            else:
                b_sym = b_item
            bases.add(b_sym)
        if len(bases) > 1:
            response.mathematical_status = EngineStatus.OUT_OF_SCOPE
            response.verification_status = VerificationStatus.UNRESOLVED
            response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
            response.error_message = "Multi-base logarithmic equations are out of scope for complete certified solving"
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

    # Certify mathematical completeness before declaring SUCCESS
    is_certified, cert_cat, cert_reason = _certify_equation_completeness(
        ast_node, eq, x, valid_roots, unique_candidates
    )

    if not is_certified:
        response.mathematical_status = EngineStatus.OUT_OF_SCOPE
        response.verification_status = VerificationStatus.UNRESOLVED
        response.domain_certainty = DomainCertainty.NOT_FULLY_DETERMINED
        response.symbolic_result = None
        response.latex_output = None
        response.error_message = f"Equation cannot be certified as an exhaustive complete solution set: {cert_reason}"
        return

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
        "completeness_category": cert_cat,
        "completeness_certified": True,
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
