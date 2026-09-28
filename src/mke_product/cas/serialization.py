"""Serialization and LaTeX presentation formatting for CAS results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import sympy


def format_sympy_symbolic(obj: Any) -> str:
    """Generate clean symbolic string (using ^ for powers)."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj.replace("**", "^")
    return str(obj).replace("**", "^")


def format_sympy_latex(obj: Any) -> str:
    """Generate clean LaTeX string for a SymPy expression or mathematical object."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    return sympy.latex(obj)


def format_solution_set_symbolic(roots: Sequence[Any]) -> str:
    """Format a set of roots in standard mathematical set notation: e.g. {-2, 2}."""
    if not roots:
        return "{}"
    formatted = [format_sympy_symbolic(r) for r in sorted(roots, key=lambda x: str(x))]
    return "{" + ", ".join(formatted) + "}"


def format_solution_set_latex(roots: Sequence[Any]) -> str:
    """Format a set of roots in LaTeX set notation: e.g. \\{-2, 2\\}."""
    if not roots:
        return "\\emptyset"
    formatted = [sympy.latex(r) for r in sorted(roots, key=lambda x: str(x))]
    return "\\left\\{ " + ", ".join(formatted) + " \\right\\}"


def format_integral_symbolic(antiderivative: Any) -> str:
    """Format indefinite integral symbolic result with + C."""
    return f"{format_sympy_symbolic(antiderivative)} + C"


def format_integral_latex(antiderivative: Any) -> str:
    """Format indefinite integral LaTeX result with + C."""
    return f"{sympy.latex(antiderivative)} + C"


def format_interval_symbolic(interval_set: Any, var: str = "x") -> str:
    """Format SymPy interval or union in clean mathematical notation."""
    if interval_set == sympy.EmptySet:
        return "No real solution"
    if interval_set == sympy.S.Reals:
        return "(-oo, oo)"
    if isinstance(interval_set, sympy.Interval):
        l_brack = "(" if interval_set.left_open else "["
        r_brack = ")" if interval_set.right_open else "]"
        start_str = format_sympy_symbolic(interval_set.start)
        end_str = format_sympy_symbolic(interval_set.end)
        return f"{l_brack}{start_str}, {end_str}{r_brack}"
    if isinstance(interval_set, sympy.FiniteSet):
        formatted = [format_sympy_symbolic(a) for a in sorted(interval_set.args, key=lambda x: str(x))]
        return "{" + ", ".join(formatted) + "}"
    if isinstance(interval_set, sympy.Union):
        return " U ".join(format_interval_symbolic(arg, var) for arg in interval_set.args)
    
    # SymPy string representation with standard interval bounds fallback
    s = str(interval_set).replace("**", "^").replace("oo", "inf")
    return s.replace("inf", "oo")


def format_interval_latex(interval_set: Any, var: str = "x") -> str:
    """Format SymPy interval or union in LaTeX notation."""
    if interval_set == sympy.EmptySet:
        return "\\emptyset"
    if interval_set == sympy.S.Reals:
        return "\\mathbb{R}"
    
    return sympy.latex(interval_set)


def format_system_symbolic(sol_dict: Dict[str, Any]) -> str:
    """Format 2x2 system solution: e.g. x = 8/5, y = 3/5."""
    parts = []
    for var, val in sorted(sol_dict.items()):
        parts.append(f"{var} = {format_sympy_symbolic(val)}")
    return ", ".join(parts)


def format_system_latex(sol_dict: Dict[str, Any]) -> str:
    """Format 2x2 system solution in clean LaTeX."""
    parts = []
    for var, val in sorted(sol_dict.items()):
        parts.append(f"{var} = {format_sympy_latex(val)}")
    return ",\\; ".join(parts)

