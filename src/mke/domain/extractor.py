"""Domain extractor operating strictly on the UNREDUCED AST."""

from typing import List, Set, Union
from fractions import Fraction
import sympy

from mke.models.ast_nodes import ASTNode, BinaryOpNode
from mke.models.domain import DomainCondition, OriginalDomain
from mke.parsing.sympy_converter import ast_to_sympy, X_SYM


def extract_original_domain(unreduced_ast: ASTNode) -> OriginalDomain:
    """Traverse the unreduced AST to extract all domain constraints before any simplification."""
    divisions: List[BinaryOpNode] = unreduced_ast.collect_divisions()
    conditions: List[DomainCondition] = []

    for div_node in divisions:
        denom_ast = div_node.right
        denom_str = denom_ast.to_math_string()

        # Check if denominator contains 'x'
        var_set = denom_ast.collect_variables()
        try:
            denom_sympy = ast_to_sympy(denom_ast)
        except Exception:
            # Denominator cannot be converted (e.g. division by zero inside denominator)
            conditions.append(
                DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0",
                    excluded_values=set(),
                    source_description="unconvertible_denominator",
                    is_undetermined=True,
                )
            )
            continue

        if "x" in var_set:
            # Denominator depends on x
            # 1. Check if algebraically identically zero (e.g. x - x)
            try:
                simplified_denom = sympy.simplify(denom_sympy)
            except Exception:
                simplified_denom = denom_sympy

            if simplified_denom == 0 or simplified_denom.is_zero is True:
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0 (IDENTICALLY ZERO DENOMINATOR)",
                    excluded_values=set(),
                    source_description="algebraic_fraction_identically_zero",
                    is_empty_domain=True,
                )
                conditions.append(cond)
                continue

            # 2. Find real roots of denominator
            try:
                roots_sym = sympy.solveset(sympy.Eq(denom_sympy, 0), X_SYM, domain=sympy.S.Reals)
            except Exception:
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0",
                    excluded_values=set(),
                    source_description="algebraic_fraction_solveset_failed",
                    is_undetermined=True,
                )
                conditions.append(cond)
                continue

            excluded_vals: Set[Union[Fraction, sympy.Basic]] = set()

            if isinstance(roots_sym, sympy.FiniteSet):
                for r in roots_sym:
                    if r.is_rational:
                        frac_r = Fraction(int(r.p), int(r.q))
                        excluded_vals.add(frac_r)
                    else:
                        excluded_vals.add(r)
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0",
                    excluded_values=excluded_vals,
                    source_description="algebraic_fraction_denominator",
                )
                conditions.append(cond)
            elif roots_sym == sympy.S.Reals:
                # Denominator is identically zero for all real x
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0 (IDENTICALLY ZERO DENOMINATOR)",
                    excluded_values=set(),
                    source_description="algebraic_fraction_identically_zero",
                    is_empty_domain=True,
                )
                conditions.append(cond)
            elif roots_sym == sympy.S.EmptySet:
                # Denominator has no real zeros (e.g. x^2 + 1 != 0 for all real x)
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0",
                    excluded_values=set(),
                    source_description="algebraic_fraction_no_real_zeros",
                )
                conditions.append(cond)
            else:
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0",
                    excluded_values=set(),
                    source_description="algebraic_fraction_undetermined",
                    is_undetermined=True,
                )
                conditions.append(cond)
        else:
            # Denominator is a constant (no 'x')
            try:
                simplified_denom = sympy.simplify(denom_sympy)
            except Exception:
                simplified_denom = denom_sympy

            if simplified_denom == 0 or simplified_denom.is_zero is True:
                # Division by zero constant! e.g. x / 0 or 1 / (2 - 2)
                cond = DomainCondition(
                    raw_expression_str=denom_str,
                    condition_str=f"{denom_str} != 0 (CONSTANT ZERO DIVISION)",
                    excluded_values=set(),
                    source_description="constant_division_by_zero",
                    is_empty_domain=True,
                )
                conditions.append(cond)
            else:
                # Non-zero constant denominator (e.g. x / 2): no exclusion on x
                pass

    return OriginalDomain(conditions)
