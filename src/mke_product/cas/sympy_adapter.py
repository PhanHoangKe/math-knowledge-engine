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
)
from .safety import (
    DomainRestrictionError,
    SafetyError,
    extract_domain_restrictions,
    inspect_ast_safety,
)
from .serialization import (
    format_integral_latex,
    format_integral_symbolic,
    format_solution_set_latex,
    format_solution_set_symbolic,
    format_sympy_latex,
    format_sympy_symbolic,
)


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
        start_time = time.monotonic()
        input_text = request.raw_input or request.expression
        response = ExecutionResponse(
            schema_version=SCHEMA_VERSION_P03A,
            request_id=request.request_id,
            operation=request.operation.value if isinstance(request.operation, OperationType) else str(request.operation),
            original_input=input_text,
            selected_engine=self.ENGINE_ID,
        )

        try:
            # 1. Parse AST if not already provided
            ast_node = request.ast
            if ast_node is None:
                if request.operation == OperationType.SOLVE and "=" in input_text:
                    ast_node = parse_cas_equation(input_text)
                else:
                    ast_node = parse_cas_expression(input_text)

            # 2. Inspect AST safety & domain constraints
            inspect_ast_safety(ast_node)
            domain_restrictions = extract_domain_restrictions(ast_node)
            response.domain_restrictions = domain_restrictions

            # 3. Convert AST to SymPy object
            sym_obj = ast_to_sympy(ast_node)

            # 4. Dispatch to specific mathematical operation
            if request.operation == OperationType.SOLVE:
                self._execute_solve(ast_node, sym_obj, response)
            elif request.operation == OperationType.SIMPLIFY:
                self._execute_simplify(sym_obj, response)
            elif request.operation == OperationType.DIFFERENTIATE:
                self._execute_differentiate(sym_obj, request.variable, request.options, response)
            elif request.operation == OperationType.INTEGRATE:
                self._execute_integrate(sym_obj, request.variable, request.options, response)
            elif request.operation == OperationType.PLOT_2D:
                self._execute_plot_2d(sym_obj, request.variable, request.options, response)
            else:
                response.mathematical_status = EngineStatus.OUT_OF_SCOPE
                response.error_message = f"Unsupported operation: {request.operation}"

        except DomainRestrictionError as ex:
            response.mathematical_status = EngineStatus.DOMAIN_ERROR
            response.error_message = str(ex)
            response.warnings.append(str(ex))
        except SafetyError as ex:
            response.mathematical_status = EngineStatus.RESOURCE_EXHAUSTED
            response.error_message = str(ex)
        except Exception as ex:
            response.mathematical_status = EngineStatus.INTERNAL_ERROR
            response.error_message = f"{type(ex).__name__}: {str(ex)}"
        finally:
            response.execution_duration_sec = time.monotonic() - start_time

        return response

    def _execute_solve(self, ast_node: ASTNode, sym_obj: Any, response: ExecutionResponse) -> None:
        """Solve an equation or expression in the real domain."""
        x = sympy.Symbol("x", real=True)
        if isinstance(sym_obj, sympy.Eq):
            eq = sym_obj
        else:
            eq = sympy.Eq(sym_obj, 0)

        # Check for identity equation with domain restrictions, e.g. (x-1)/(x-1) = 1
        diff_expr = eq.lhs - eq.rhs
        simplified_diff = sympy.simplify(diff_expr)

        if simplified_diff == 0:
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

        # Solve for roots in real domain
        raw_roots = sympy.solve(eq, x)
        if not isinstance(raw_roots, (list, tuple, set)):
            raw_roots = [raw_roots]

        # Filter real roots
        real_roots = []
        for r in raw_roots:
            if isinstance(r, dict):
                r = r.get(x, r)
            if hasattr(r, "is_real") and r.is_real is True:
                real_roots.append(r)
            elif isinstance(r, (int, float, sympy.Integer, sympy.Rational, sympy.Float)):
                real_roots.append(r)
            elif hasattr(r, "is_real") and r.is_real is None:
                # Numerical evaluation check
                try:
                    ev = complex(r.evalf())
                    if abs(ev.imag) < 1e-10:
                        real_roots.append(r)
                except Exception:
                    pass

        # Filter against domain restrictions
        valid_roots = []
        for r in real_roots:
            is_valid = True
            for restriction in response.domain_restrictions:
                if restriction.startswith("x != "):
                    try:
                        excluded_val = sympy.sympify(restriction.replace("x != ", ""))
                        if r == excluded_val:
                            is_valid = False
                            break
                    except Exception:
                        pass
            if is_valid:
                valid_roots.append(r)

        response.symbolic_result = format_solution_set_symbolic(valid_roots)
        response.latex_output = format_solution_set_latex(valid_roots)
        response.mathematical_status = EngineStatus.SUCCESS
        response.verification_evidence = {
            "root_count": len(valid_roots),
            "roots": [str(r) for r in valid_roots],
            "solution_set": [str(r) for r in valid_roots],
            "domain": "Reals",
        }

    def _execute_simplify(self, sym_obj: Any, response: ExecutionResponse) -> None:
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
        self,
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
        self,
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
            lower_val = sympy.sympify(lower)
            upper_val = sympy.sympify(upper)
            definite_res = sympy.integrate(sym_obj, (var, lower_val, upper_val))
            response.symbolic_result = format_sympy_symbolic(definite_res)
            response.latex_output = format_sympy_latex(definite_res)
        else:
            antiderivative = sympy.integrate(sym_obj, var)
            response.symbolic_result = format_integral_symbolic(antiderivative)
            response.latex_output = format_integral_latex(antiderivative)

        response.mathematical_status = EngineStatus.SUCCESS

    def _execute_plot_2d(
        self,
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

        segments: List[Dict[str, List[float]]] = []
        cur_x: List[float] = []
        cur_y: List[float] = []
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
            nonlocal cur_x, cur_y
            if cur_x:
                segments.append({"x": cur_x, "y": cur_y})
                cur_x = []
                cur_y = []

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
                    cur_x.append(round(xi, 4))
                    cur_y.append(round(clipped_yi, 4))
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
            "points_count": sum(len(seg["x"]) for seg in segments),
        }
        response.mathematical_status = EngineStatus.SUCCESS
