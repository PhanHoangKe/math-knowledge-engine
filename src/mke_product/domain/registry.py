"""MKE MVP V1 — Method Registry & Orthogonal Assessment Engine.

Implements the deterministic registry of mathematical solution methods and
evaluates multi-dimensional applicability profiles for problem instances.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from mke_product.core.rational import Rational
from mke_product.domain.exact import compute_quadratic_discriminant
from mke_product.domain.models import (
    ExecutionAvailability,
    MathematicalApplicability,
    MethodAssessment,
    MethodDefinition,
    PedagogicalRecommendation,
    PrerequisiteStatus,
    ProblemCategory,
    QuadraticProblemIR,
    SupportStatus,
    VerificationCapability,
)


class MethodRegistry:
    """Deterministic catalog of mathematical solution methods."""

    def __init__(self) -> None:
        self._registry: Dict[str, MethodDefinition] = {}
        self._register_default_mvp_methods()

    def register(self, definition: MethodDefinition) -> None:
        """Register a new method definition with validation."""
        if definition.method_id in self._registry:
            raise ValueError(f"Method with ID '{definition.method_id}' is already registered.")
        self._registry[definition.method_id] = definition

    def get(self, method_id: str) -> MethodDefinition:
        """Retrieve a method definition by ID."""
        if method_id not in self._registry:
            raise KeyError(f"Method '{method_id}' not found in registry.")
        return self._registry[method_id]

    def list_all(self) -> List[MethodDefinition]:
        """List all registered methods in deterministic insertion order."""
        return list(self._registry.values())

    def list_for_family(self, family: ProblemCategory) -> List[MethodDefinition]:
        """List methods registered for a specific problem category."""
        return [m for m in self._registry.values() if m.problem_family == family]

    def _register_default_mvp_methods(self) -> None:
        """Register the canonical MVP V1 quadratic solution methods."""
        # 1. Standard Quadratic Formula
        self.register(
            MethodDefinition(
                method_id="QUAD_FORMULA_STANDARD",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Công thức nghiệm tổng quát",
                description_vi="Tính biệt thức Δ = b² - 4ac và áp dụng công thức nghiệm tổng quát.",
                curriculum_level="Toán 9 (Học kỳ 2)",
                relative_complexity=1,
                prerequisite_ids=["PREREQ_RADICALS", "PREREQ_POLYNOMIAL_COEFF"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 2. Reduced Quadratic Formula
        self.register(
            MethodDefinition(
                method_id="QUAD_FORMULA_REDUCED",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Công thức nghiệm thu gọn",
                description_vi="Đặt b = 2b', tính biệt thức thu gọn Δ' = (b')² - ac để đơn giản hóa tính toán.",
                curriculum_level="Toán 9 (Học kỳ 2)",
                relative_complexity=1,
                prerequisite_ids=["PREREQ_RADICALS", "PREREQ_EVEN_COEFF"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 3. Factorization over Q
        self.register(
            MethodDefinition(
                method_id="QUAD_FACTORIZATION_Q",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Phân tích nhân tử trên ℚ (Tách ac)",
                description_vi="Tìm u, v sao cho u+v=b và u*v=ac để phân tích ax² + bx + c thành nhân tử bậc nhất hữu tỉ.",
                curriculum_level="Toán 8, Toán 9",
                relative_complexity=2,
                prerequisite_ids=["PREREQ_FACTORING_ALGEBRA"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 4. Factorization over R
        self.register(
            MethodDefinition(
                method_id="QUAD_FACTORIZATION_R",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Phân tích nhân tử trên ℝ",
                description_vi="Phân tích thành a(x - x₁)(x - x₂) = 0 với nghiệm thực vô tỉ.",
                curriculum_level="Toán 9, Toán 10",
                relative_complexity=3,
                prerequisite_ids=["PREREQ_REAL_SURDS"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 5. Completing the Square
        self.register(
            MethodDefinition(
                method_id="QUAD_COMPLETE_SQUARE",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Biến đổi tách bình phương",
                description_vi="Đưa phương trình về dạng a(x + b/(2a))² = Δ / (4a) để khai căn bậc hai.",
                curriculum_level="Toán 8, Toán 9",
                relative_complexity=3,
                prerequisite_ids=["PREREQ_PERFECT_SQUARE_IDENTITY"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 6. Viète Special Sum (a + b + c = 0)
        self.register(
            MethodDefinition(
                method_id="QUAD_VIETE_SPECIAL_SUM",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Nhẩm nghiệm đặc biệt a + b + c = 0",
                description_vi="Trường hợp đặc biệt khi tổng các hệ số bằng 0, suy ra x₁ = 1, x₂ = c/a.",
                curriculum_level="Toán 9 (Học kỳ 2)",
                relative_complexity=1,
                prerequisite_ids=["PREREQ_VIETE_THEOREM"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 7. Viète Special Difference (a - b + c = 0)
        self.register(
            MethodDefinition(
                method_id="QUAD_VIETE_SPECIAL_DIF",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Nhẩm nghiệm đặc biệt a - b + c = 0",
                description_vi="Trường hợp đặc biệt khi a - b + c = 0, suy ra x₁ = -1, x₂ = -c/a.",
                curriculum_level="Toán 9 (Học kỳ 2)",
                relative_complexity=1,
                prerequisite_ids=["PREREQ_VIETE_THEOREM"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 8. Viète Guessing (Sum & Product)
        self.register(
            MethodDefinition(
                method_id="QUAD_VIETE_SUM_PRODUCT",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Tìm hai số theo Tổng và Tích (Hệ thức Viète)",
                description_vi="Nhẩm hai số u, v có tổng S = -b/a và tích P = c/a khi S, P là các số nguyên đơn giản.",
                curriculum_level="Toán 9 (Học kỳ 2)",
                relative_complexity=2,
                prerequisite_ids=["PREREQ_VIETE_THEOREM"],
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
            )
        )
        # 9. Graphical Parabola Analysis
        self.register(
            MethodDefinition(
                method_id="QUAD_GRAPHICAL_ANALYSIS",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                title_vi="Khảo sát hình học đồ thị Parabol",
                description_vi="Khảo sát đỉnh, trục đối xứng và giao điểm của parabol y = ax² + bx + c với trục hoành Ox.",
                curriculum_level="Toán 9, Toán 10",
                relative_complexity=2,
                prerequisite_ids=["PREREQ_PARABOLA_GRAPH"],
                verification_capability=VerificationCapability.NOT_APPLICABLE,
            )
        )

    def assess_quadratic(self, a_rat: Rational, b_rat: Rational, c_rat: Rational) -> List[MethodAssessment]:
        """Evaluate orthogonal method assessments for a quadratic equation a*x^2 + b*x + c = 0.

        Precondition: a != 0.
        """
        if a_rat.is_zero:
            raise ValueError("assess_quadratic requires a != 0")

        disc = compute_quadratic_discriminant(a_rat, b_rat, c_rat)
        assessments: List[MethodAssessment] = []

        sum_abc = a_rat + b_rat + c_rat
        dif_abc = a_rat - b_rat + c_rat
        has_special_sum = sum_abc.is_zero
        has_special_dif = dif_abc.is_zero

        # Check if b is integer even
        b_is_int_even = b_rat.is_integer and (b_rat.numerator % 2 == 0)

        # 1. Standard Formula
        std_reasons = ["Biệt thức Δ tính được cho mọi phương trình bậc hai với a ≠ 0."]
        if disc.is_negative:
            std_reasons.append("Δ < 0 chứng minh phương trình vô nghiệm thực.")
        elif disc.is_zero:
            std_reasons.append("Δ = 0 suy ra phương trình có nghiệm kép.")
        else:
            std_reasons.append("Δ > 0 suy ra phương trình có hai nghiệm phân biệt.")

        assessments.append(
            MethodAssessment(
                method_id="QUAD_FORMULA_STANDARD",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED
                    if not (has_special_sum or has_special_dif)
                    else PedagogicalRecommendation.NEUTRAL
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=std_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(prerequisite_id="PREREQ_RADICALS", is_satisfied=True, description_vi="Phép tính căn bậc hai số học"),
                ],
                pedagogical_priority=2 if (has_special_sum or has_special_dif) else 1,
            )
        )

        # 2. Reduced Formula
        red_reasons = ["b/2 tồn tại trong ℚ cho mọi hệ số hữu tỉ."]
        if b_is_int_even:
            red_reasons.append(f"Hệ số b = {b_rat} chẵn (b' = {b_rat.numerator // 2}), áp dụng công thức thu gọn giúp tối ưu tính toán.")
        else:
            red_reasons.append("Hệ số b không là số nguyên chẵn, việc chia 2 không làm giảm độ phức tạp tính toán.")

        assessments.append(
            MethodAssessment(
                method_id="QUAD_FORMULA_REDUCED",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED if b_is_int_even else PedagogicalRecommendation.NEUTRAL
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=red_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_EVEN_COEFF",
                        is_satisfied=b_is_int_even,
                        description_vi="Hệ số b là số nguyên chẵn",
                    )
                ],
                pedagogical_priority=1 if b_is_int_even else 4,
            )
        )

        # 3. Factorization over Q
        fact_q_app = (disc.is_positive and disc.is_rational_square) or disc.is_zero
        fact_q_reasons: List[str]
        if fact_q_app:
            fact_q_reasons = ["Δ là số chính phương hữu tỉ, đa thức phân tích được thành nhân tử bậc nhất trên ℚ."]
        elif disc.is_negative:
            fact_q_reasons = ["Δ < 0, đa thức không có nghiệm thực nên không phân tích được thành nhân tử trên ℚ."]
        else:
            fact_q_reasons = [f"Δ = {disc.value} không là số chính phương (d = {disc.squarefree_kernel} > 1), không phân tích được thành nhân tử trên ℚ."]

        assessments.append(
            MethodAssessment(
                method_id="QUAD_FACTORIZATION_Q",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=(
                    MathematicalApplicability.APPLICABLE if fact_q_app else MathematicalApplicability.NOT_APPLICABLE
                ),
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED if fact_q_app else PedagogicalRecommendation.DISCOURAGED
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=fact_q_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_FACTORING_ALGEBRA",
                        is_satisfied=fact_q_app,
                        description_vi="Δ là số chính phương hữu tỉ",
                    )
                ],
                pedagogical_priority=1 if (fact_q_app and not has_special_sum and not has_special_dif) else 3,
            )
        )

        # 4. Factorization over R
        fact_r_app = not disc.is_negative
        fact_r_reasons: List[str]
        if fact_r_app:
            fact_r_reasons = ["Δ ≥ 0, đa thức phân tích được thành nhân tử bậc nhất trên ℝ."]
        else:
            fact_r_reasons = ["Δ < 0, đa thức bất khả quy trên ℝ."]

        assessments.append(
            MethodAssessment(
                method_id="QUAD_FACTORIZATION_R",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=(
                    MathematicalApplicability.APPLICABLE if fact_r_app else MathematicalApplicability.NOT_APPLICABLE
                ),
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED
                    if (fact_q_app)
                    else (PedagogicalRecommendation.NEUTRAL if fact_r_app else PedagogicalRecommendation.DISCOURAGED)
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=fact_r_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_REAL_SURDS",
                        is_satisfied=fact_r_app,
                        description_vi="Biệt thức Δ ≥ 0",
                    )
                ],
                pedagogical_priority=3,
            )
        )

        # 5. Completing the Square
        assessments.append(
            MethodAssessment(
                method_id="QUAD_COMPLETE_SQUARE",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.NEUTRAL,
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=["Biến đổi hằng đẳng thức tách bình phương áp dụng được cho mọi phương trình bậc hai."],
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_PERFECT_SQUARE_IDENTITY",
                        is_satisfied=True,
                        description_vi="Hằng đẳng thức bình phương một tổng/hiệu",
                    )
                ],
                pedagogical_priority=5,
            )
        )

        # 6. Viète Special Sum (a + b + c = 0)
        viete_sum_reasons = (
            [f"Tổng hệ số a + b + c = {a_rat} + ({b_rat}) + {c_rat} = 0. Nghiệm là x₁ = 1, x₂ = {c_rat / a_rat}."]
            if has_special_sum
            else [f"Tổng hệ số a + b + c = {sum_abc} ≠ 0. Không thỏa mãn điều kiện nhẩm nghiệm."]
        )
        assessments.append(
            MethodAssessment(
                method_id="QUAD_VIETE_SPECIAL_SUM",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=(
                    MathematicalApplicability.APPLICABLE if has_special_sum else MathematicalApplicability.NOT_APPLICABLE
                ),
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED if has_special_sum else PedagogicalRecommendation.DISCOURAGED
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=viete_sum_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_VIETE_THEOREM",
                        is_satisfied=has_special_sum,
                        description_vi="Điều kiện a + b + c = 0",
                    )
                ],
                pedagogical_priority=1 if has_special_sum else 9,
            )
        )

        # 7. Viète Special Difference (a - b + c = 0)
        viete_dif_reasons = (
            [f"Hệ số a - b + c = {a_rat} - ({b_rat}) + {c_rat} = 0. Nghiệm là x₁ = -1, x₂ = {-c_rat / a_rat}."]
            if has_special_dif
            else [f"Hệ số a - b + c = {dif_abc} ≠ 0. Không thỏa mãn điều kiện nhẩm nghiệm."]
        )
        assessments.append(
            MethodAssessment(
                method_id="QUAD_VIETE_SPECIAL_DIF",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=(
                    MathematicalApplicability.APPLICABLE if has_special_dif else MathematicalApplicability.NOT_APPLICABLE
                ),
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED if has_special_dif else PedagogicalRecommendation.DISCOURAGED
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=viete_dif_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_VIETE_THEOREM",
                        is_satisfied=has_special_dif,
                        description_vi="Điều kiện a - b + c = 0",
                    )
                ],
                pedagogical_priority=1 if has_special_dif else 9,
            )
        )

        # 8. Viète Guessing (Sum & Product)
        viete_guess_app = fact_q_app and (not disc.is_negative)
        viete_guess_reasons: List[str]
        if viete_guess_app:
            viete_guess_reasons = [f"Tổng S = {-b_rat / a_rat}, Tích P = {c_rat / a_rat} hữu tỉ đẹp, nhẩm nghiệm thuận tiện."]
        else:
            viete_guess_reasons = ["Nghiệm vô tỉ hoặc phương trình vô nghiệm thực, không nhẩm được bằng phân tích ước số."]

        assessments.append(
            MethodAssessment(
                method_id="QUAD_VIETE_SUM_PRODUCT",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=(
                    MathematicalApplicability.APPLICABLE if viete_guess_app else MathematicalApplicability.NOT_APPLICABLE
                ),
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=(
                    PedagogicalRecommendation.RECOMMENDED if (viete_guess_app and a_rat == Rational(1, 1)) else PedagogicalRecommendation.NEUTRAL
                ),
                verification_capability=VerificationCapability.HOST_VERIFIABLE,
                reasons=viete_guess_reasons,
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_VIETE_THEOREM",
                        is_satisfied=viete_guess_app,
                        description_vi="Tổng và tích là số hữu tỉ có thể nhẩm",
                    )
                ],
                pedagogical_priority=2 if viete_guess_app else 8,
            )
        )

        # 9. Graphical Parabola Analysis
        assessments.append(
            MethodAssessment(
                method_id="QUAD_GRAPHICAL_ANALYSIS",
                problem_family=ProblemCategory.ALGEBRA_QUADRATIC,
                mathematical_applicability=MathematicalApplicability.APPLICABLE,
                support_status=SupportStatus.SUPPORTED,
                execution_availability=ExecutionAvailability.AVAILABLE,
                pedagogical_recommendation=PedagogicalRecommendation.RECOMMENDED,
                verification_capability=VerificationCapability.NOT_APPLICABLE,
                reasons=["Minh họa trực quan hình học hình dạng parabol và vị trí tương đối với trục hoành."],
                prerequisite_status=[
                    PrerequisiteStatus(
                        prerequisite_id="PREREQ_PARABOLA_GRAPH",
                        is_satisfied=True,
                        description_vi="Đồ thị hàm số bậc hai y = ax² + bx + c",
                    )
                ],
                pedagogical_priority=6,
            )
        )

        return assessments
