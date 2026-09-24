"""Method templates, catalogue, and solve interfaces."""

from mke.methods.base import BaseMethod, MethodSolveOutput
from mke.methods.catalogue import CATALOGUE, MethodCatalogue
from mke.methods.m1_linear import LinearEquationMethod
from mke.methods.m2_quadratic import QuadraticFormulaMethod
from mke.methods.m3_factorization import FactorizationMethod, audit_division_step
from mke.methods.m4_rational import RationalEquationMethod
from mke.methods.m5_biquadratic import BiquadraticSubstitutionMethod

__all__ = [
    "BaseMethod",
    "MethodSolveOutput",
    "MethodCatalogue",
    "CATALOGUE",
    "LinearEquationMethod",
    "QuadraticFormulaMethod",
    "FactorizationMethod",
    "audit_division_step",
    "RationalEquationMethod",
    "BiquadraticSubstitutionMethod",
]
