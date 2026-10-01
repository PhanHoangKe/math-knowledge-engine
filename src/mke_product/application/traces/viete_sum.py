"""MKE MVP V1 — Viète Special Sum Solution Trace Generator.

Generates deterministic, structured pedagogical solution steps using the
special Viète sum rule: a + b + c = 0 => x1 = 1, x2 = c/a.
"""

from __future__ import annotations

from typing import List

from mke_product.application.traces.base import (
    BaseTraceGenerator,
    RULE_CONCLUSION,
    RULE_VIETE_PRODUCT,
    RULE_VIETE_SPECIAL_SUM,
    TraceMethodNotApplicableError,
)
from mke_product.core.rational import Rational
from mke_product.domain.models import (
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionStep,
)


class VieteSpecialSumTraceGenerator(BaseTraceGenerator):
    """Deterministic trace generator for method QUAD_VIETE_SPECIAL_SUM."""

    METHOD_ID: str = "QUAD_VIETE_SPECIAL_SUM"

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
        sum_coeffs = a + b + c
        if not sum_coeffs.is_zero:
            raise TraceMethodNotApplicableError(
                f"Method QUAD_VIETE_SPECIAL_SUM requires a + b + c == 0, got a+b+c = {sum_coeffs}."
            )

        steps: List[SolutionStep] = []

        a_lat = RationalFraction.from_rational(a).to_latex()
        b_lat = RationalFraction.from_rational(b).to_latex()
        c_lat = RationalFraction.from_rational(c).to_latex()

        # Step 1: Check special sum condition a + b + c = 0
        steps.append(
            SolutionStep(
                step_number=1,
                latex_expression=f"a + b + c = {a_lat} + ({b_lat}) + ({c_lat}) = 0",
                explanation_vi="Kiểm tra điều kiện nhẩm nghiệm tổng hệ số a + b + c = 0.",
                rule_or_theorem_used=RULE_VIETE_SPECIAL_SUM,
                why_this_step_vi="Khi tổng các hệ số bằng 0, phương trình luôn nhận x = 1 làm một nghiệm.",
            )
        )

        # Step 2: First root x1 = 1
        steps.append(
            SolutionStep(
                step_number=2,
                latex_expression="x_1 = 1",
                explanation_vi="Theo định lý nhẩm nghiệm Viète đặc biệt, phương trình có một nghiệm là x = 1.",
                rule_or_theorem_used=RULE_VIETE_SPECIAL_SUM,
                why_this_step_vi="Thay x = 1 vào phương trình bậc hai thỏa mãn đẳng thức a(1)^2 + b(1) + c = a + b + c = 0.",
            )
        )

        # Step 3: Second root x2 = c/a via Viète product relation
        r2 = c / a
        r2_lat = RationalFraction.from_rational(r2).to_latex()
        steps.append(
            SolutionStep(
                step_number=3,
                latex_expression=f"x_1 \\cdot x_2 = \\frac{{c}}{{a}} \\implies 1 \\cdot x_2 = \\frac{{{c_lat}}}{{{a_lat}}} = {r2_lat} \\implies x_2 = {r2_lat}",
                explanation_vi="Sử dụng hệ thức tích hai nghiệm của định lý Viète để tìm nghiệm thứ hai.",
                rule_or_theorem_used=RULE_VIETE_PRODUCT,
                why_this_step_vi="Tích hai nghiệm x1 * x2 = c/a giúp suy ra nghiệm còn lại x2 = c/a mà không cần tính biệt thức.",
            )
        )

        # Step 4: Conclusion matching canonical kernel outcome
        if kernel_outcome == SolutionOutcome.ONE_REPEATED_REAL_ROOT:
            steps.append(
                SolutionStep(
                    step_number=4,
                    latex_expression="x_1 = x_2 = 1",
                    explanation_vi="Vì hai nghiệm trùng nhau nên phương trình có nghiệm kép x = 1.",
                    rule_or_theorem_used=RULE_CONCLUSION,
                    why_this_step_vi="Kết luận nghiệm kép của phương trình bậc hai khi c/a = 1.",
                )
            )
        else:
            r1_lat = kernel_roots[0].latex_str
            r2_lat = kernel_roots[1].latex_str
            steps.append(
                SolutionStep(
                    step_number=4,
                    latex_expression=f"x_1 = {r1_lat}, \\quad x_2 = {r2_lat}",
                    explanation_vi="Kết luận hai nghiệm phân biệt của phương trình.",
                    rule_or_theorem_used=RULE_CONCLUSION,
                    why_this_step_vi="Trình bày tập nghiệm theo thứ tự chuẩn hóa.",
                )
            )

        return steps
