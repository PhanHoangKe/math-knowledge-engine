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
