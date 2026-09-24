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
        denom_sympy = ast_to_sympy(denom_ast)

        if "x" in var_set:
            # Denominator depends on x -> find its real roots
            roots_sym = sympy.solveset(sympy.Eq(denom_sympy, 0), X_SYM, domain=sympy.S.Reals)
            excluded_vals: Set[Union[Fraction, sympy.Basic]] = set()

            if isinstance(roots_sym, sympy.FiniteSet):
                for r in roots_sym:
                    if r.is_rational:
                        frac_r = Fraction(int(r.p), int(r.q))
                        excluded_vals.add(frac_r)
                    else:
                        excluded_vals.add(r)
            elif roots_sym == sympy.S.Reals:
                # Denominator is identically zero for all real x!
                # Entire domain is empty.
                pass

            cond = DomainCondition(
                raw_expression_str=denom_str,
                condition_str=f"{denom_str} != 0",
                excluded_values=excluded_vals,
                source_description="algebraic_fraction_denominator",
            )
            conditions.append(cond)
        else:
            # Denominator is a constant
            try:
                const_val = float(denom_sympy)
                if abs(const_val) < 1e-12:
                    # Division by zero constant! e.g. x / 0
                    cond = DomainCondition(
                        raw_expression_str=denom_str,
                        condition_str=f"{denom_str} != 0 (CONSTANT ZERO DIVISION)",
                        excluded_values={sympy.S.Reals},
                        source_description="constant_division_by_zero",
                    )
                    conditions.append(cond)
            except Exception:
                pass

    return OriginalDomain(conditions)
