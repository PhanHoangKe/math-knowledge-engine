"""SymPy CAS engine adapter implementation for MKE Product."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Sequence, Set
import sympy

from mke_product.parser.ast import ASTNode, Equation
from .ast_bridge import ast_to_sympy, ast_to_sympy_expr
from .cas_parser import parse_cas_equation, parse_cas_expression
from .contracts import (
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
    extract_domain_restrictions,
    inspect_ast_safety,
    parse_safe_numeric_bound,
    sanitize_execution_options,
)
from .serialization import (
    format_integral_latex,
    format_integral_symbolic,
    format_solution_set_latex,
    format_solution_set_symbolic,
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
            if request.operation in (OperationType.SOLVE, OperationType.CHECK_CANDIDATE) and "=" in input_text:
                ast_node = parse_cas_equation(input_text)
            else:
                ast_node = parse_cas_expression(input_text)

        # 3. Inspect AST safety & extract domain constraints
        inspect_ast_safety(ast_node)
        domain_restrictions = extract_domain_restrictions(ast_node)
        response.domain_restrictions = domain_restrictions

        # 4. Convert AST to SymPy object via secure typed bridge (no eval / no sympify)
        sym_obj = ast_to_sympy(ast_node)

        # 5. Dispatch to specific mathematical operation
        if request.operation == OperationType.SOLVE:
            _execute_solve(ast_node, sym_obj, response)
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
            if request.operation == OperationType.CHECK_CANDIDATE:
                response.verification_status = VerificationStatus.CANDIDATE_CHECKED
            else:
                response.verification_status = VerificationStatus.COMPUTED
        elif response.mathematical_status == EngineStatus.PARTIAL:
            response.verification_status = VerificationStatus.PARTIAL
        elif response.mathematical_status == EngineStatus.UNRESOLVED:
            response.verification_status = VerificationStatus.UNRESOLVED
        else:
            response.verification_status = VerificationStatus.ERROR

    except DomainRestrictionError as ex:
        response.mathematical_status = EngineStatus.DOMAIN_ERROR
        response.verification_status = VerificationStatus.ERROR
        response.error_message = str(ex)
        response.warnings.append(str(ex))
    except SafetyError as ex:
        response.mathematical_status = EngineStatus.RESOURCE_EXHAUSTED
        response.verification_status = VerificationStatus.ERROR
        response.error_message = str(ex)
    except ValueError as ex:
        response.mathematical_status = EngineStatus.INVALID_INPUT
        response.verification_status = VerificationStatus.ERROR
        response.error_message = str(ex)
    except Exception as ex:
        response.mathematical_status = EngineStatus.INTERNAL_ERROR
        response.verification_status = VerificationStatus.ERROR
        response.error_message = f"{type(ex).__name__}: {str(ex)}"
    finally:
        response.execution_duration_sec = time.monotonic() - start_time

    return response


def _execute_solve(ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
    """Solve an equation or expression in the real domain."""
    x = sympy.Symbol("x", real=True)
    if isinstance(sym_obj, sympy.Eq):
        eq = sym_obj
    else:
        eq = sympy.Eq(sym_obj, 0)

    # Check for identity equation with domain restrictions, e.g. (x-1)/(x-1) = 1
    diff_expr = sympy.cancel(eq.lhs - eq.rhs)

    if diff_expr == 0:
        if response.domain_restrictions:
            excluded_str = ", ".join(response.domain_restrictions)
            response.symbolic_result = f"All real numbers except {excluded_str}"
            response.latex_output = "\\mathbb{R} \\setminus \\{ " + ", ".join([r.replace("x != ", "") for r in response.domain_restrictions]) + " \\}"
            response.mathematical_status = EngineStatus.SUCCESS
            return
        else:
            response.symbolic_result = "All real numbers"
            response.latex_output = "\\mathbb{R}"
            response.mathematical_status = EngineStatus.SUCCESS
            return

    # Solve for roots in real domain using sympy.solve
    try:
        raw_roots = sympy.solve(eq, x)
    except NotImplementedError:
        response.mathematical_status = EngineStatus.UNRESOLVED
        response.error_message = "SymPy could not find closed-form analytic roots."
        return

    if not isinstance(raw_roots, (list, tuple, set)):
        raw_roots = [raw_roots]

    # Filter real roots using exact algebraic methods (never float heuristics)
    real_roots = []
    for r in raw_roots:
        if isinstance(r, dict):
            r = r.get(x, r)

        # Exact realness check
        is_exact_real = False
        if hasattr(r, "is_real") and r.is_real is True:
            is_exact_real = True
        elif isinstance(r, (int, float, sympy.Integer, sympy.Rational)):
            is_exact_real = True
        else:
            try:
                # Check if imaginary component is symbolically zero
                imag_part = sympy.im(r)
                if imag_part == 0 or sympy.simplify(imag_part) == 0:
                    is_exact_real = True
            except Exception:
                pass

        if is_exact_real:
            real_roots.append(r)

    # Filter against domain restrictions
    valid_roots = []
    for r in real_roots:
        is_valid = True
        for restriction in response.domain_restrictions:
            if restriction.startswith("x != "):
                try:
                    excluded_val_node = parse_cas_expression(restriction.replace("x != ", ""))
                    excluded_val = ast_to_sympy_expr(excluded_val_node)
                    if sympy.simplify(r - excluded_val) == 0:
                        is_valid = False
                        break
                except Exception:
                    pass
        if is_valid:
            valid_roots.append(r)

    # Sort roots if comparable
    try:
        valid_roots.sort(key=lambda item: float(item.evalf()) if hasattr(item, "evalf") else float(item))
    except Exception:
        pass

    response.symbolic_result = format_solution_set_symbolic(valid_roots)
    response.latex_output = format_solution_set_latex(valid_roots)
    response.mathematical_status = EngineStatus.SUCCESS
    response.verification_evidence = {
        "root_count": len(valid_roots),
        "roots": [str(r) for r in valid_roots],
        "solution_set": [str(r) for r in valid_roots],
        "domain": "Reals",
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
