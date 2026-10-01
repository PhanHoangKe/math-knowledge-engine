"""MKE MVP V1 — Reduced Quadratic Formula Solution Trace Generator.

Generates deterministic, structured pedagogical solution steps using the
reduced quadratic formula: b' = b/2, Delta' = (b')^2 - ac, x = (-b' +/- sqrt(Delta')) / a.
Applicable for all quadratic equations with rational coefficients.
"""

from __future__ import annotations

from typing import List

from mke_product.application.traces.base import (
    BaseTraceGenerator,
    RULE_IDENTIFY_COEFFICIENTS,
    RULE_REAL_DISCRIMINANT_SIGN,
    RULE_REDUCED_DISCRIMINANT,
    RULE_REDUCED_QUADRATIC_FORMULA,
)
from mke_product.core.rational import Rational
from mke_product.domain.exact import _format_surd_latex, compute_quadratic_discriminant
from mke_product.domain.models import (
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionStep,
)


class ReducedQuadraticFormulaTraceGenerator(BaseTraceGenerator):
    """Deterministic trace generator for method QUAD_FORMULA_REDUCED."""

    METHOD_ID: str = "QUAD_FORMULA_REDUCED"

    @property
    def method_id(self) -> str:
        return self.METHOD_ID

    def _generate_trace_steps(
        self,
        a: Rational,
        b: Rational,
        c: Rational,
        kernel_outcome: SolutionOutcome,
        kernel_roots: List[RealRootValue],
    ) -> List[SolutionStep]:
        steps: List[SolutionStep] = []

        b_prime = b / Rational(2, 1)
        delta_prime = (b_prime * b_prime) - (a * c)

        a_lat = RationalFraction.from_rational(a).to_latex()
        b_prime_lat = RationalFraction.from_rational(b_prime).to_latex()
        c_lat = RationalFraction.from_rational(c).to_latex()
        delta_prime_lat = RationalFraction.from_rational(delta_prime).to_latex()

        # Step 1: Identify reduced coefficients
        steps.append(
            SolutionStep(
                step_number=1,
                latex_expression=f"a = {a_lat}, \\quad b' = \\frac{{b}}{{2}} = {b_prime_lat}, \\quad c = {c_lat}",
                explanation_vi="Xác định các hệ số a, b' = b/2 và c của phương trình.",
                rule_or_theorem_used=RULE_IDENTIFY_COEFFICIENTS,
                why_this_step_vi="Chuẩn bị các hệ số thu gọn để tính biệt thức thu gọn Delta'.",
            )
        )

        # Step 2: Compute reduced discriminant Delta'
        steps.append(
            SolutionStep(
                step_number=2,
                latex_expression=f"\\Delta' = (b')^2 - ac = ({b_prime_lat})^2 - ({a_lat})({c_lat}) = {delta_prime_lat}",
                explanation_vi="Tính biệt thức thu gọn Delta'.",
                rule_or_theorem_used=RULE_REDUCED_DISCRIMINANT,
                why_this_step_vi="Dấu của biệt thức thu gọn Delta' (tương đương Delta / 4) quyết định số nghiệm thực của phương trình.",
            )
        )

        # Step 3+ : Branch on Delta' sign
        disc = compute_quadratic_discriminant(a, b, c)

        if delta_prime.is_negative:
            steps.append(
                SolutionStep(
                    step_number=3,
                    latex_expression=f"\\Delta' = {delta_prime_lat} < 0",
                    explanation_vi="Vì Delta' < 0 nên phương trình vô nghiệm trong tập số thực R.",
                    rule_or_theorem_used=RULE_REAL_DISCRIMINANT_SIGN,
                    why_this_step_vi="Biệt thức thu gọn âm tương đương Delta < 0, phương trình không có nghiệm thực.",
                )
            )
        elif delta_prime.is_zero:
            root_lat = kernel_roots[0].latex_str
            steps.append(
                SolutionStep(
                    step_number=3,
                    latex_expression=f"x_1 = x_2 = -\\frac{{b'}}{{a}} = -\\frac{{{b_prime_lat}}}{{{a_lat}}} = {root_lat}",
                    explanation_vi="Vì Delta' = 0 nên phương trình có nghiệm kép.",
                    rule_or_theorem_used=RULE_REDUCED_QUADRATIC_FORMULA,
                    why_this_step_vi="Áp dụng công thức nghiệm thu gọn khi biệt thức Delta' bằng 0.",
                )
            )
        else:  # delta_prime.is_positive
            if disc.is_rational_square:
                assert disc.square_root_rational is not None
                sqrt_delta_prime_rat = disc.square_root_rational.to_rational() / Rational(2, 1)
                sqrt_delta_prime_lat = RationalFraction.from_rational(sqrt_delta_prime_rat).to_latex()
                steps.append(
                    SolutionStep(
                        step_number=3,
                        latex_expression=f"\\sqrt{{\\Delta'}} = \\sqrt{{{delta_prime_lat}}} = {sqrt_delta_prime_lat}",
                        explanation_vi="Tính căn bậc hai của biệt thức thu gọn Delta'.",
                        rule_or_theorem_used=RULE_REDUCED_DISCRIMINANT,
                        why_this_step_vi="Delta' là số chính phương hữu tỉ nên căn bậc hai là một số hữu tỉ chính xác.",
                    )
                )
                r1_lat = kernel_roots[0].latex_str
                r2_lat = kernel_roots[1].latex_str
                steps.append(
                    SolutionStep(
                        step_number=4,
                        latex_expression=f"x_1 = \\frac{{-b' - \\sqrt{{\\Delta'}}}}{{a}} = {r1_lat}, \\quad x_2 = \\frac{{-b' + \\sqrt{{\\Delta'}}}}{{a}} = {r2_lat}",
                        explanation_vi="Vì Delta' > 0 nên phương trình có hai nghiệm phân biệt.",
                        rule_or_theorem_used=RULE_REDUCED_QUADRATIC_FORMULA,
                        why_this_step_vi="Áp dụng công thức nghiệm thu gọn để tính hai nghiệm phân biệt.",
                    )
                )
            else:
                assert disc.squarefree_kernel is not None
                assert disc.extracted_factor is not None
                d = disc.squarefree_kernel
                s_prime_rat = disc.extracted_factor.to_rational() / Rational(2, 1)
                sqrt_delta_prime_lat = _format_surd_latex(Rational(0, 1), s_prime_rat, d)
                steps.append(
                    SolutionStep(
                        step_number=3,
                        latex_expression=f"\\sqrt{{\\Delta'}} = \\sqrt{{{delta_prime_lat}}} = {sqrt_delta_prime_lat}",
                        explanation_vi="Rút gọn căn thức của biệt thức thu gọn Delta'.",
                        rule_or_theorem_used=RULE_REDUCED_DISCRIMINANT,
                        why_this_step_vi="Khai căn phần chính phương của Delta' để rút gọn biểu thức nghiệm vô tỉ.",
                    )
                )
                r1_lat = kernel_roots[0].latex_str
                r2_lat = kernel_roots[1].latex_str
                steps.append(
                    SolutionStep(
                        step_number=4,
                        latex_expression=f"x_1 = \\frac{{-b' - \\sqrt{{\\Delta'}}}}{{a}} = {r1_lat}, \\quad x_2 = \\frac{{-b' + \\sqrt{{\\Delta'}}}}{{a}} = {r2_lat}",
                        explanation_vi="Vì Delta' > 0 nên phương trình có hai nghiệm phân biệt.",
                        rule_or_theorem_used=RULE_REDUCED_QUADRATIC_FORMULA,
                        why_this_step_vi="Áp dụng công thức nghiệm thu gọn cho phương trình có nghiệm vô tỉ.",
                    )
                )

        return steps
