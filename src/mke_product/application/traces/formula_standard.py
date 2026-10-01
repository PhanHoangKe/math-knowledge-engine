"""MKE MVP V1 — Standard Quadratic Formula Solution Trace Generator.

Generates deterministic, structured pedagogical solution steps using the
standard quadratic formula: x = (-b +/- sqrt(Delta)) / (2a).
"""

from __future__ import annotations

from typing import List

from mke_product.application.traces.base import (
    BaseTraceGenerator,
    RULE_IDENTIFY_COEFFICIENTS,
    RULE_QUADRATIC_DISCRIMINANT,
    RULE_QUADRATIC_FORMULA,
    RULE_REAL_DISCRIMINANT_SIGN,
)
from mke_product.core.rational import Rational
from mke_product.domain.exact import _format_surd_latex, compute_quadratic_discriminant
from mke_product.domain.models import (
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionStep,
)


class StandardQuadraticFormulaTraceGenerator(BaseTraceGenerator):
    """Deterministic trace generator for method QUAD_FORMULA_STANDARD."""

    METHOD_ID: str = "QUAD_FORMULA_STANDARD"

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

        a_lat = RationalFraction.from_rational(a).to_latex()
        b_lat = RationalFraction.from_rational(b).to_latex()
        c_lat = RationalFraction.from_rational(c).to_latex()

        # Step 1: Identify coefficients
        steps.append(
            SolutionStep(
                step_number=1,
                latex_expression=f"a = {a_lat}, \\quad b = {b_lat}, \\quad c = {c_lat}",
                explanation_vi="Xác định các hệ số a, b, c của phương trình bậc hai.",
                rule_or_theorem_used=RULE_IDENTIFY_COEFFICIENTS,
                why_this_step_vi="Chuẩn bị các hệ số để tính biệt thức Delta theo công thức nghiệm tổng quát.",
            )
        )

        # Step 2: Compute discriminant Delta
        disc = compute_quadratic_discriminant(a, b, c)
        delta_lat = disc.value.to_latex()
        steps.append(
            SolutionStep(
                step_number=2,
                latex_expression=f"\\Delta = b^2 - 4ac = ({b_lat})^2 - 4({a_lat})({c_lat}) = {delta_lat}",
                explanation_vi="Tính biệt thức Delta của phương trình.",
                rule_or_theorem_used=RULE_QUADRATIC_DISCRIMINANT,
                why_this_step_vi="Dấu của biệt thức Delta quyết định số nghiệm thực của phương trình bậc hai.",
            )
        )

        # Step 3+ : Branch on Delta sign
        if disc.is_negative:
            steps.append(
                SolutionStep(
                    step_number=3,
                    latex_expression=f"\\Delta = {delta_lat} < 0",
                    explanation_vi="Vì Delta < 0 nên phương trình vô nghiệm trong tập số thực R.",
                    rule_or_theorem_used=RULE_REAL_DISCRIMINANT_SIGN,
                    why_this_step_vi="Số âm không có căn bậc hai thực nên không tồn tại giá trị x thỏa mãn.",
                )
            )
        elif disc.is_zero:
            root_lat = kernel_roots[0].latex_str
            steps.append(
                SolutionStep(
                    step_number=3,
                    latex_expression=f"x_1 = x_2 = -\\frac{{b}}{{2a}} = -\\frac{{{b_lat}}}{{2 \\cdot ({a_lat})}} = {root_lat}",
                    explanation_vi="Vì Delta = 0 nên phương trình có nghiệm kép.",
                    rule_or_theorem_used=RULE_QUADRATIC_FORMULA,
                    why_this_step_vi="Khi biệt thức Delta triệt tiêu, hai nhánh nghiệm trùng nhau tạo thành nghiệm kép.",
                )
            )
        else:  # disc.is_positive
            if disc.is_rational_square:
                assert disc.square_root_rational is not None
                sqrt_delta_lat = disc.square_root_rational.to_latex()
                steps.append(
                    SolutionStep(
                        step_number=3,
                        latex_expression=f"\\sqrt{{\\Delta}} = \\sqrt{{{delta_lat}}} = {sqrt_delta_lat}",
                        explanation_vi="Tính căn bậc hai của biệt thức Delta.",
                        rule_or_theorem_used=RULE_QUADRATIC_DISCRIMINANT,
                        why_this_step_vi="Delta là số chính phương hữu tỉ nên căn bậc hai là một số hữu tỉ chính xác.",
                    )
                )
                r1_lat = kernel_roots[0].latex_str
                r2_lat = kernel_roots[1].latex_str
                steps.append(
                    SolutionStep(
                        step_number=4,
                        latex_expression=f"x_1 = \\frac{{-b - \\sqrt{{\\Delta}}}}{{2a}} = {r1_lat}, \\quad x_2 = \\frac{{-b + \\sqrt{{\\Delta}}}}{{2a}} = {r2_lat}",
                        explanation_vi="Vì Delta > 0 nên phương trình có hai nghiệm phân biệt.",
                        rule_or_theorem_used=RULE_QUADRATIC_FORMULA,
                        why_this_step_vi="Áp dụng công thức nghiệm tổng quát để tính chính xác hai nghiệm phân biệt.",
                    )
                )
            else:
                assert disc.squarefree_kernel is not None
                assert disc.extracted_factor is not None
                d = disc.squarefree_kernel
                s_rat = disc.extracted_factor.to_rational()
                sqrt_delta_lat = _format_surd_latex(Rational(0, 1), s_rat, d)
                steps.append(
                    SolutionStep(
                        step_number=3,
                        latex_expression=f"\\sqrt{{\\Delta}} = \\sqrt{{{delta_lat}}} = {sqrt_delta_lat}",
                        explanation_vi="Rút gọn căn thức của biệt thức Delta về dạng thừa số chính phương.",
                        rule_or_theorem_used=RULE_QUADRATIC_DISCRIMINANT,
                        why_this_step_vi="Khai căn phần chính phương giúp đơn giản hóa biểu thức nghiệm vô tỉ.",
                    )
                )
                r1_lat = kernel_roots[0].latex_str
                r2_lat = kernel_roots[1].latex_str
                steps.append(
                    SolutionStep(
                        step_number=4,
                        latex_expression=f"x_1 = \\frac{{-b - \\sqrt{{\\Delta}}}}{{2a}} = {r1_lat}, \\quad x_2 = \\frac{{-b + \\sqrt{{\\Delta}}}}{{2a}} = {r2_lat}",
                        explanation_vi="Vì Delta > 0 nên phương trình có hai nghiệm phân biệt.",
                        rule_or_theorem_used=RULE_QUADRATIC_FORMULA,
                        why_this_step_vi="Áp dụng công thức nghiệm tổng quát cho phương trình có nghiệm vô tỉ.",
                    )
                )

        return steps
