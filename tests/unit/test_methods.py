"""Unit tests for the 5 catalogue methods and their guards."""

import sympy
from mke.methods.catalogue import CATALOGUE
from mke.methods.m1_linear import LinearEquationMethod
from mke.methods.m2_quadratic import QuadraticFormulaMethod
from mke.methods.m3_factorization import FactorizationMethod
from mke.methods.m4_rational import RationalEquationMethod
from mke.methods.m5_biquadratic import BiquadraticSubstitutionMethod
from mke.models.enums import MethodAdmissibility, MethodId
from mke.parsing.normalizer import normalize_equation
from mke.parsing.parser import Parser


def test_m1_linear_standard_and_degenerate():
    m1 = LinearEquationMethod()

    # Standard linear: 2*x - 6 = 0 => x = 3
    ast1 = Parser.from_text("2*x - 6 = 0").parse_equation()
    norm1 = normalize_equation(ast1)
    assert m1.evaluate_admissibility(norm1) == MethodAdmissibility.APPLICABLE
    out1 = m1.solve_instance(norm1)
    assert out1.candidate_roots == [sympy.Integer(3)]

    # Degenerate identity: 0*x = 0
    ast2 = Parser.from_text("0*x = 0").parse_equation()
    norm2 = normalize_equation(ast2)
    assert m1.evaluate_admissibility(norm2) == MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS
    out2 = m1.solve_instance(norm2)
    assert out2.is_identity_on_domain


def test_m2_quadratic_a_zero_rejection_and_discriminants():
    m2 = QuadraticFormulaMethod()

    # a != 0, Delta > 0: x^2 - 5*x + 6 = 0 => {2, 3}
    ast1 = Parser.from_text("x^2 - 5*x + 6 = 0").parse_equation()
    norm1 = normalize_equation(ast1)
    assert m2.evaluate_admissibility(norm1) == MethodAdmissibility.APPLICABLE
    out1 = m2.solve_instance(norm1)
    assert out1.candidate_roots == [sympy.Integer(2), sympy.Integer(3)]

    # a = 0: 0*x^2 + 2*x - 4 = 0 => M2 strictly NOT_APPLICABLE
    ast2 = Parser.from_text("0*x^2 + 2*x - 4 = 0").parse_equation()
    norm2 = normalize_equation(ast2)
    assert m2.evaluate_admissibility(norm2) == MethodAdmissibility.NOT_APPLICABLE

    # Delta < 0: x^2 + 1 = 0 => M2 is APPLICABLE, candidate roots empty
    ast3 = Parser.from_text("x^2 + 1 = 0").parse_equation()
    norm3 = normalize_equation(ast3)
    assert m2.evaluate_admissibility(norm3) == MethodAdmissibility.APPLICABLE
    out3 = m2.solve_instance(norm3)
    assert out3.candidate_roots == []


def test_m3_factorization():
    m3 = FactorizationMethod()
    ast = Parser.from_text("x * (x - 1) = 0").parse_equation()
    norm = normalize_equation(ast)
    assert m3.evaluate_admissibility(norm) == MethodAdmissibility.APPLICABLE
    out = m3.solve_instance(norm)
    assert out.candidate_roots == [sympy.Integer(0), sympy.Integer(1)]


def test_m4_rational_extraneous_root():
    m4 = RationalEquationMethod()
    ast = Parser.from_text("(x^2 - 5*x + 6) / (x - 2) = 0").parse_equation()
    norm = normalize_equation(ast)
    assert m4.evaluate_admissibility(norm) == MethodAdmissibility.APPLICABLE
    out = m4.solve_instance(norm)
    # 2 is extraneous, only 3 is valid
    assert out.candidate_roots == [sympy.Integer(3)]
    assert len(out.rejected_intermediates) == 1
    assert out.rejected_intermediates[0]["root"] == "2"


def test_m5_biquadratic_sign_constraint():
    m5 = BiquadraticSubstitutionMethod()
    ast = Parser.from_text("x^4 + x^2 - 2 = 0").parse_equation()
    norm = normalize_equation(ast)
    assert m5.evaluate_admissibility(norm) == MethodAdmissibility.APPLICABLE
    out = m5.solve_instance(norm)
    # t = 1 => x = {-1, 1}; t = -2 is rejected
    assert out.candidate_roots == [sympy.Integer(-1), sympy.Integer(1)]
    assert len(out.rejected_intermediates) == 1
    assert "t = -2" in out.rejected_intermediates[0]["intermediate"]
