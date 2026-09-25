"""Script to generate handcrafted DEV_PILOT dataset files for DEV-02A.

Generates:
- data/dev_pilot/families.jsonl
- data/dev_pilot/problems.jsonl
- data/dev_pilot/annotations.jsonl
- data/dev_pilot/transfer_pairs.jsonl
- data/dev_pilot/manifest.json
"""

import sys
sys.path.insert(0, "src")
from pathlib import Path
import json

from mke.models.enums import (
    MethodAdmissibility,
    MethodId,
    ObligationId,
    Split,
    TransferValidity,
)
from mke.knowledge.schemas import (
    EquationClass,
    FamilyRecord,
    MethodAnnotation,
    ProblemRecord,
    ReviewStatus,
    TransferCategory,
    TransferPairRecord,
)
from mke.parsing.parser import Parser
from mke.parsing.normalizer import normalize_equation
from mke.knowledge.provenance import write_canonical_jsonl, compute_file_sha256


def build_dev_pilot_dataset():
    # 1. 15 Seed Families
    families = [
        # Linear (3 families)
        FamilyRecord(
            family_id="FAM_01_LIN_BASIC",
            name="Phương trình bậc nhất cơ bản",
            description="Các phương trình dạng ax + b = 0 với a != 0, nghiệm duy nhất trên R",
            equation_class=EquationClass.LINEAR,
            split_group_id="SG_LIN_BASIC",
            dependent_family_ids=[],
            supported_methods=[MethodId.M1_LINEAR_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_02_LIN_DEGEN",
            name="Phương trình tuyến tính suy biến",
            description="Phương trình dạng 0x = 0 (đồng nhất thức) hoặc 0x = c (vô nghiệm mâu thuẫn)",
            equation_class=EquationClass.LINEAR,
            split_group_id="SG_LIN_DEGEN",
            dependent_family_ids=[],
            supported_methods=[MethodId.M1_LINEAR_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_03_LIN_RATIONAL_COEFF",
            name="Phương trình bậc nhất hệ số hữu tỉ cụ thể",
            description="Phương trình tuyến tính với các hệ số hữu tỉ cụ thể, không chứa tham số",
            equation_class=EquationClass.LINEAR,
            split_group_id="SG_LIN_RATIONAL_COEFF",
            dependent_family_ids=[],
            supported_methods=[MethodId.M1_LINEAR_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),

        # Quadratic (3 families)
        FamilyRecord(
            family_id="FAM_04_QUAD_TWO_ROOTS",
            name="Phương trình bậc hai hai nghiệm phân biệt",
            description="Phương trình bậc hai có biệt thức delta > 0, giải được bằng công thức nghiệm hoặc phân tích nhân tử",
            equation_class=EquationClass.QUADRATIC,
            split_group_id="SG_QUAD_RAT_TRANSFER",  # Shared split group with FAM_11!
            dependent_family_ids=[],
            supported_methods=[MethodId.M2_QUADRATIC_FORMULA, MethodId.M3_FACTORIZATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_05_QUAD_DOUBLE_ROOT",
            name="Phương trình bậc hai có nghiệm kép",
            description="Phương trình bậc hai có delta = 0, bình phương đúng",
            equation_class=EquationClass.QUADRATIC,
            split_group_id="SG_QUAD_DOUBLE_ROOT",
            dependent_family_ids=[],
            supported_methods=[MethodId.M2_QUADRATIC_FORMULA, MethodId.M3_FACTORIZATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_06_QUAD_NO_REAL",
            name="Phương trình bậc hai vô nghiệm thực",
            description="Phương trình bậc hai có delta < 0, vô nghiệm trên R",
            equation_class=EquationClass.QUADRATIC,
            split_group_id="SG_QUAD_NO_REAL",
            dependent_family_ids=[],
            supported_methods=[MethodId.M2_QUADRATIC_FORMULA],
            review_status=ReviewStatus.PROVISIONAL,
        ),

        # Factorization (3 families)
        FamilyRecord(
            family_id="FAM_07_FACT_COMMON_X",
            name="Phân tích nhân tử đặt biến chung x",
            description="Đa thức thiếu hệ số tự do, phân tích được x*(ax + b) = 0",
            equation_class=EquationClass.FACTORIZATION,
            split_group_id="SG_FACT_COMMON_X",
            dependent_family_ids=[],
            supported_methods=[MethodId.M3_FACTORIZATION, MethodId.M2_QUADRATIC_FORMULA],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_08_FACT_DIFF_SQ",
            name="Phân tích hằng đẳng thức hiệu hai bình phương",
            description="Phương trình dạng a^2*x^2 - b^2 = 0 đưa về (ax - b)(ax + b) = 0",
            equation_class=EquationClass.FACTORIZATION,
            split_group_id="SG_FACT_DIFF_SQ",
            dependent_family_ids=[],
            supported_methods=[MethodId.M3_FACTORIZATION, MethodId.M2_QUADRATIC_FORMULA],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_09_FACT_TRINOMIAL",
            name="Phân tích tam thức bậc hai thành nhân tử",
            description="Tích hai nhân tử bậc nhất (ax + b)(cx + d) = 0",
            equation_class=EquationClass.FACTORIZATION,
            split_group_id="SG_FACT_TRINOMIAL",
            dependent_family_ids=[],
            supported_methods=[MethodId.M3_FACTORIZATION, MethodId.M2_QUADRATIC_FORMULA],
            review_status=ReviewStatus.PROVISIONAL,
        ),

        # Rational (3 families)
        FamilyRecord(
            family_id="FAM_10_RAT_SOLVABLE",
            name="Phương trình phân thức hữu tỉ có nghiệm",
            description="Phân thức có mẫu số chứa ẩn, nghiệm tử số không vi phạm mẫu số",
            equation_class=EquationClass.RATIONAL,
            split_group_id="SG_RAT_SOLVABLE",
            dependent_family_ids=[],
            supported_methods=[MethodId.M4_RATIONAL_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_11_RAT_EXTRANEOUS_TRANSFER",
            name="Phương trình phân thức có nghiệm ngoại lai từ bài toán nguồn",
            description="Tử số giống bài toán nguồn nhưng mẫu số loại bớt nghiệm; bắt buộc phụ thuộc FAM_04",
            equation_class=EquationClass.RATIONAL,
            split_group_id="SG_QUAD_RAT_TRANSFER",  # Shared split group with FAM_04!
            dependent_family_ids=["FAM_04_QUAD_TWO_ROOTS"],
            supported_methods=[MethodId.M4_RATIONAL_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_12_RAT_DOMAIN_BOUNDARIES",  # Renamed as per Coordinator adjustment 4
            name="Phương trình phân thức biên miền xác định",
            description="Khảo sát ranh giới miền xác định: đồng nhất thức có lỗ thủng vs miền xác định rỗng hoàn toàn",
            equation_class=EquationClass.RATIONAL,
            split_group_id="SG_RAT_DOMAIN_BOUNDARIES",
            dependent_family_ids=[],
            supported_methods=[MethodId.M4_RATIONAL_EQUATION],
            review_status=ReviewStatus.PROVISIONAL,
        ),

        # Biquadratic (3 families)
        FamilyRecord(
            family_id="FAM_13_BIQ_FOUR_ROOTS",
            name="Phương trình trùng phương 4 nghiệm thực",
            description="Phương trình ax^4 + bx^2 + c = 0 có hai nghiệm phụ t1, t2 > 0",
            equation_class=EquationClass.BIQUADRATIC,
            split_group_id="SG_BIQ_FOUR_ROOTS",
            dependent_family_ids=[],
            supported_methods=[MethodId.M5_BIQUADRATIC_SUBSTITUTION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_14_BIQ_TWO_ROOTS",
            name="Phương trình trùng phương 2 nghiệm thực",
            description="Phương trình trùng phương có một nghiệm phụ t >= 0 và một nghiệm phụ t < 0 bị loại",
            equation_class=EquationClass.BIQUADRATIC,
            split_group_id="SG_BIQ_TWO_ROOTS",
            dependent_family_ids=[],
            supported_methods=[MethodId.M5_BIQUADRATIC_SUBSTITUTION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
        FamilyRecord(
            family_id="FAM_15_BIQ_NO_REAL",
            name="Phương trình trùng phương vô nghiệm thực",
            description="Phương trình trùng phương có hai nghiệm phụ t < 0 hoặc delta_t < 0",
            equation_class=EquationClass.BIQUADRATIC,
            split_group_id="SG_BIQ_NO_REAL",
            dependent_family_ids=[],
            supported_methods=[MethodId.M5_BIQUADRATIC_SUBSTITUTION],
            review_status=ReviewStatus.PROVISIONAL,
        ),
    ]

    # Raw problem specifications: (problem_id, family_id, variant_id, expr_str, category, expected_roots, is_identity, is_empty_domain)
    raw_problem_specs = [
        # FAM_01
        ("PROB_FAM01_V01", "FAM_01_LIN_BASIC", "V01", "2*x + 4 = 0", TransferCategory.POSITIVE, ["-2"], False, False),
        ("PROB_FAM01_V02", "FAM_01_LIN_BASIC", "V02", "x^2 + 2*x + 4 = 0", TransferCategory.METHOD_NEAR_MISS, [], False, False),
        ("PROB_FAM01_V03", "FAM_01_LIN_BASIC", "V03", "x = 0", TransferCategory.BOUNDARY_CASE, ["0"], False, False),

        # FAM_02
        ("PROB_FAM02_V01", "FAM_02_LIN_DEGEN", "V01", "0*x = 0", TransferCategory.BOUNDARY_CASE, None, True, False),
        ("PROB_FAM02_V02", "FAM_02_LIN_DEGEN", "V02", "0*x + 5 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),
        ("PROB_FAM02_V03", "FAM_02_LIN_DEGEN", "V03", "5*x = 0", TransferCategory.POSITIVE, ["0"], False, False),

        # FAM_03
        ("PROB_FAM03_V01", "FAM_03_LIN_RATIONAL_COEFF", "V01", "(1/2)*x + 3/4 = 0", TransferCategory.POSITIVE, ["-3/2"], False, False),
        ("PROB_FAM03_V02", "FAM_03_LIN_RATIONAL_COEFF", "V02", "(2/3)*x - 4/5 = 0", TransferCategory.POSITIVE, ["6/5"], False, False),
        ("PROB_FAM03_V03", "FAM_03_LIN_RATIONAL_COEFF", "V03", "(1/2)*x + 3/4 = 1/4", TransferCategory.TRANSFER_NEAR_MISS, ["-1"], False, False),

        # FAM_04
        ("PROB_FAM04_V01", "FAM_04_QUAD_TWO_ROOTS", "V01", "x^2 - 5*x + 6 = 0", TransferCategory.MULTI_METHOD, ["2", "3"], False, False),
        ("PROB_FAM04_V02", "FAM_04_QUAD_TWO_ROOTS", "V02", "x^2 - 7*x + 12 = 0", TransferCategory.POSITIVE, ["3", "4"], False, False),
        ("PROB_FAM04_V03", "FAM_04_QUAD_TWO_ROOTS", "V03", "x^3 - 5*x + 6 = 0", TransferCategory.METHOD_NEAR_MISS, None, False, False),

        # FAM_05
        ("PROB_FAM05_V01", "FAM_05_QUAD_DOUBLE_ROOT", "V01", "x^2 - 4*x + 4 = 0", TransferCategory.BOUNDARY_CASE, ["2"], False, False),
        ("PROB_FAM05_V02", "FAM_05_QUAD_DOUBLE_ROOT", "V02", "4*x^2 + 12*x + 9 = 0", TransferCategory.BOUNDARY_CASE, ["-3/2"], False, False),

        # FAM_06
        ("PROB_FAM06_V01", "FAM_06_QUAD_NO_REAL", "V01", "x^2 + x + 1 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),
        ("PROB_FAM06_V02", "FAM_06_QUAD_NO_REAL", "V02", "x^2 + 4 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),

        # FAM_07
        ("PROB_FAM07_V01", "FAM_07_FACT_COMMON_X", "V01", "x*(x - 3) = 0", TransferCategory.POSITIVE, ["0", "3"], False, False),
        ("PROB_FAM07_V02", "FAM_07_FACT_COMMON_X", "V02", "2*x^2 - 6*x = 0", TransferCategory.POSITIVE, ["0", "3"], False, False),
        ("PROB_FAM07_V03", "FAM_07_FACT_COMMON_X", "V03", "x*(x - 3) = 4", TransferCategory.METHOD_NEAR_MISS, ["-1", "4"], False, False),

        # FAM_08
        ("PROB_FAM08_V01", "FAM_08_FACT_DIFF_SQ", "V01", "x^2 - 9 = 0", TransferCategory.POSITIVE, ["-3", "3"], False, False),
        ("PROB_FAM08_V02", "FAM_08_FACT_DIFF_SQ", "V02", "4*x^2 - 25 = 0", TransferCategory.POSITIVE, ["-5/2", "5/2"], False, False),
        ("PROB_FAM08_V03", "FAM_08_FACT_DIFF_SQ", "V03", "x^2 + 9 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),

        # FAM_09
        ("PROB_FAM09_V01", "FAM_09_FACT_TRINOMIAL", "V01", "(x - 1)*(x + 2) = 0", TransferCategory.MULTI_METHOD, ["-2", "1"], False, False),
        ("PROB_FAM09_V02", "FAM_09_FACT_TRINOMIAL", "V02", "(2*x - 1)*(x + 3) = 0", TransferCategory.POSITIVE, ["-3", "1/2"], False, False),
        ("PROB_FAM09_V03", "FAM_09_FACT_TRINOMIAL", "V03", "(x - 1)*(x + 2) = 4", TransferCategory.TRANSFER_NEAR_MISS, ["-3", "2"], False, False),

        # FAM_10
        ("PROB_FAM10_V01", "FAM_10_RAT_SOLVABLE", "V01", "(x - 1)/(x + 2) = 0", TransferCategory.POSITIVE, ["1"], False, False),
        ("PROB_FAM10_V02", "FAM_10_RAT_SOLVABLE", "V02", "(2*x + 6)/(x - 3) = 0", TransferCategory.POSITIVE, ["-3"], False, False),
        ("PROB_FAM10_V03", "FAM_10_RAT_SOLVABLE", "V03", "1/(x - 1) + 1/(x + 1) = 0", TransferCategory.BOUNDARY_CASE, ["0"], False, False),

        # FAM_11
        ("PROB_FAM11_V01", "FAM_11_RAT_EXTRANEOUS_TRANSFER", "V01", "(x^2 - 5*x + 6)/(x - 2) = 0", TransferCategory.TRANSFER_NEAR_MISS, ["3"], False, False),
        ("PROB_FAM11_V02", "FAM_11_RAT_EXTRANEOUS_TRANSFER", "V02", "(x^2 - 5*x + 6)/(x - 3) = 0", TransferCategory.TRANSFER_NEAR_MISS, ["2"], False, False),
        ("PROB_FAM11_V03", "FAM_11_RAT_EXTRANEOUS_TRANSFER", "V03", "(x^2 - 5*x + 6)/((x - 2)*(x - 3)) = 0", TransferCategory.BOUNDARY_CASE, [], False, False),

        # FAM_12 (RAT_DOMAIN_BOUNDARIES)
        ("PROB_FAM12_V01", "FAM_12_RAT_DOMAIN_BOUNDARIES", "V01", "(x - 2)/(x - 2) = 1", TransferCategory.BOUNDARY_CASE, None, True, False),
        ("PROB_FAM12_V02", "FAM_12_RAT_DOMAIN_BOUNDARIES", "V02", "x/(x - x) = 0", TransferCategory.BOUNDARY_CASE, [], False, True),
        ("PROB_FAM12_V03", "FAM_12_RAT_DOMAIN_BOUNDARIES", "V03", "1/(x - 2) = 0", TransferCategory.BOUNDARY_CASE, [], False, False),

        # FAM_13
        ("PROB_FAM13_V01", "FAM_13_BIQ_FOUR_ROOTS", "V01", "x^4 - 5*x^2 + 4 = 0", TransferCategory.POSITIVE, ["-2", "-1", "1", "2"], False, False),
        ("PROB_FAM13_V02", "FAM_13_BIQ_FOUR_ROOTS", "V02", "x^4 - 10*x^2 + 9 = 0", TransferCategory.POSITIVE, ["-3", "-1", "1", "3"], False, False),
        ("PROB_FAM13_V03", "FAM_13_BIQ_FOUR_ROOTS", "V03", "x^4 - 5*x^3 + 4 = 0", TransferCategory.METHOD_NEAR_MISS, None, False, False),

        # FAM_14
        ("PROB_FAM14_V01", "FAM_14_BIQ_TWO_ROOTS", "V01", "x^4 - 3*x^2 - 4 = 0", TransferCategory.BOUNDARY_CASE, ["-2", "2"], False, False),
        ("PROB_FAM14_V02", "FAM_14_BIQ_TWO_ROOTS", "V02", "x^4 - 8*x^2 - 9 = 0", TransferCategory.BOUNDARY_CASE, ["-3", "3"], False, False),

        # FAM_15
        ("PROB_FAM15_V01", "FAM_15_BIQ_NO_REAL", "V01", "x^4 + 5*x^2 + 4 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),
        ("PROB_FAM15_V02", "FAM_15_BIQ_NO_REAL", "V02", "x^4 + 1 = 0", TransferCategory.BOUNDARY_CASE, [], False, False),
    ]

    # Map family_id to EquationClass
    fam_to_class = {f.family_id: f.equation_class for f in families}

    problems = []
    annotations = []

    for pid, fid, vid, expr, cat, exp_roots, is_ident, is_empty in raw_problem_specs:
        ast = Parser.from_text(expr).parse_equation()
        norm = normalize_equation(ast, raw_text=expr)
        domain_str = norm.domain.format_domain()
        excluded = sorted([str(v) for v in norm.domain.excluded_values])

        eq_class = fam_to_class[fid]

        canon_str = (
            f"({norm.numerator_sym}) / ({norm.denominator_sym}) = 0"
            if norm.denominator_sym != 1
            else f"{norm.numerator_sym} = 0"
        )

        prob = ProblemRecord(
            problem_id=pid,
            family_id=fid,
            variant_id=vid,
            split=Split.DEV,
            original_expression=expr,
            canonical_representation=canon_str,
            raw_ast=ast.to_dict(),
            domain_str=domain_str,
            excluded_points=excluded,
            equation_class=eq_class,
            near_miss_category=cat,
            expected_roots=exp_roots,
            is_identity_on_domain=is_ident,
            is_empty_domain=is_empty,
            provenance="DEV02A_PILOT_HANDCRAFTED",
            license_status="CC-BY-4.0",
            review_status=ReviewStatus.PROVISIONAL,
        )
        problems.append(prob)

        # Generate primary and alternative method annotations for the problem
        ann_id = f"ANN_{pid}_PRIMARY"
        # Determine primary method based on equation class
        if eq_class == EquationClass.LINEAR:
            pmethod = MethodId.M1_LINEAR_EQUATION
            admiss = MethodAdmissibility.APPLICABLE if cat != TransferCategory.METHOD_NEAR_MISS else MethodAdmissibility.NOT_APPLICABLE
        elif eq_class == EquationClass.QUADRATIC:
            pmethod = MethodId.M2_QUADRATIC_FORMULA
            admiss = MethodAdmissibility.APPLICABLE if cat != TransferCategory.METHOD_NEAR_MISS else MethodAdmissibility.NOT_APPLICABLE
        elif eq_class == EquationClass.FACTORIZATION:
            pmethod = MethodId.M3_FACTORIZATION
            admiss = MethodAdmissibility.APPLICABLE if cat != TransferCategory.METHOD_NEAR_MISS else MethodAdmissibility.NOT_APPLICABLE
        elif eq_class == EquationClass.RATIONAL:
            pmethod = MethodId.M4_RATIONAL_EQUATION
            admiss = MethodAdmissibility.APPLICABLE_WITH_OBLIGATIONS if not is_empty else MethodAdmissibility.APPLICABLE
        elif eq_class == EquationClass.BIQUADRATIC:
            pmethod = MethodId.M5_BIQUADRATIC_SUBSTITUTION
            admiss = MethodAdmissibility.APPLICABLE if cat != TransferCategory.METHOD_NEAR_MISS else MethodAdmissibility.NOT_APPLICABLE
        else:
            pmethod = MethodId.M1_LINEAR_EQUATION
            admiss = MethodAdmissibility.UNKNOWN

        ann1 = MethodAnnotation(
            annotation_id=ann_id,
            problem_id=pid,
            method_id=pmethod,
            method_version="1.0.0",
            method_instance_id=f"INST_{pid}_{pmethod.name[:2]}",
            admissibility=admiss,
            structural_guards=[{"guard": "degree_and_form_check", "passed": (admiss != MethodAdmissibility.NOT_APPLICABLE)}],
            mathematical_guards=[{"guard": "domain_and_discriminant_check", "passed": True}],
            proof_obligations=[ObligationId.ORIGINAL_DOMAIN, ObligationId.COMPLETENESS],
            explanation=f"Annotation for {expr} with method {pmethod.value}",
            annotation_evidence=f"Handcrafted annotation for {cat.value} pilot case",
            review_status=ReviewStatus.PROVISIONAL,
            provenance="DEV02A_PILOT_ANNOTATION",
        )
        annotations.append(ann1)

        # Multi-method support: FAM_04_V01 can be solved by both M2 and M3
        if pid == "PROB_FAM04_V01":
            ann2 = MethodAnnotation(
                annotation_id=f"ANN_{pid}_ALT_FACTORIZATION",
                problem_id=pid,
                method_id=MethodId.M3_FACTORIZATION,
                method_version="1.0.0",
                method_instance_id=f"INST_{pid}_M3",
                admissibility=MethodAdmissibility.APPLICABLE,
                structural_guards=[{"guard": "polynomial_degree_2", "passed": True}],
                mathematical_guards=[{"guard": "factors_over_Q", "passed": True}],
                proof_obligations=[ObligationId.TRANSFORMATION_EQUIVALENCE, ObligationId.ORIGINAL_DOMAIN, ObligationId.COMPLETENESS],
                explanation="Quadratic x^2 - 5x + 6 factors over Q into (x - 2)(x - 3) = 0",
                annotation_evidence="Discriminant delta=1 is perfect square, admits rational factoring",
                review_status=ReviewStatus.PROVISIONAL,
                provenance="DEV02A_PILOT_ANNOTATION",
            )
            annotations.append(ann2)

        # Multi-method support: FAM_09_V01 can be solved by both M3 and M2
        if pid == "PROB_FAM09_V01":
            ann2 = MethodAnnotation(
                annotation_id=f"ANN_{pid}_ALT_QUADRATIC",
                problem_id=pid,
                method_id=MethodId.M2_QUADRATIC_FORMULA,
                method_version="1.0.0",
                method_instance_id=f"INST_{pid}_M2",
                admissibility=MethodAdmissibility.APPLICABLE,
                structural_guards=[{"guard": "expands_to_degree_2", "passed": True}],
                mathematical_guards=[{"guard": "delta_positive", "passed": True}],
                proof_obligations=[ObligationId.NONZERO_GUARD, ObligationId.ORIGINAL_DOMAIN, ObligationId.COMPLETENESS],
                explanation="Factored equation expands to x^2 + x - 2 = 0 which is solvable by quadratic formula",
                annotation_evidence="Expansion yields valid degree 2 polynomial with delta=9 > 0",
                review_status=ReviewStatus.PROVISIONAL,
                provenance="DEV02A_PILOT_ANNOTATION",
            )
            annotations.append(ann2)

    # Transfer Pairs: Explicit source-target transfer relationships
    transfer_pairs = [
        # Mandatory Example: FAM_04_V01 -> FAM_11_V01
        TransferPairRecord(
            pair_id="PAIR_MANDATORY_FAM04_FAM11_01",
            source_problem_id="PROB_FAM04_V01",
            target_problem_id="PROB_FAM11_V01",
            method_id=MethodId.M4_RATIONAL_EQUATION,
            method_version="1.0.0",
            proposed_method_instance={"source_equation": "x^2 - 5*x + 6 = 0", "target_equation": "(x^2 - 5*x + 6)/(x - 2) = 0"},
            transfer_category=TransferCategory.TRANSFER_NEAR_MISS,
            guard_obligations=[ObligationId.ORIGINAL_DOMAIN, ObligationId.SOURCE_RESULT_NONTRANSFER],
            proposed_transfer_status=TransferValidity.UNSAFE_COPY,
            annotation_evidence="Source equation has roots {2, 3}. Copying {2, 3} directly is UNSAFE_COPY because target denominator x - 2 requires x != 2. Target valid root set is strictly {3}.",
            review_status=ReviewStatus.PROVISIONAL,
            provenance="DEV02A_PILOT_TRANSFER",
        ),
        # Mandatory Example variant: FAM_04_V01 -> FAM_11_V02
        TransferPairRecord(
            pair_id="PAIR_MANDATORY_FAM04_FAM11_02",
            source_problem_id="PROB_FAM04_V01",
            target_problem_id="PROB_FAM11_V02",
            method_id=MethodId.M4_RATIONAL_EQUATION,
            method_version="1.0.0",
            proposed_method_instance={"source_equation": "x^2 - 5*x + 6 = 0", "target_equation": "(x^2 - 5*x + 6)/(x - 3) = 0"},
            transfer_category=TransferCategory.TRANSFER_NEAR_MISS,
            guard_obligations=[ObligationId.ORIGINAL_DOMAIN, ObligationId.SOURCE_RESULT_NONTRANSFER],
            proposed_transfer_status=TransferValidity.UNSAFE_COPY,
            annotation_evidence="Source equation has roots {2, 3}. Target denominator x - 3 requires x != 3, excluding root 3. Copying {2, 3} is UNSAFE_COPY; target root is {2}.",
            review_status=ReviewStatus.PROVISIONAL,
            provenance="DEV02A_PILOT_TRANSFER",
        ),
        # All roots excluded: FAM_04_V01 -> FAM_11_V03
        TransferPairRecord(
            pair_id="PAIR_MANDATORY_FAM04_FAM11_03",
            source_problem_id="PROB_FAM04_V01",
            target_problem_id="PROB_FAM11_V03",
            method_id=MethodId.M4_RATIONAL_EQUATION,
            method_version="1.0.0",
            proposed_method_instance={"source_equation": "x^2 - 5*x + 6 = 0", "target_equation": "(x^2 - 5*x + 6)/((x - 2)*(x - 3)) = 0"},
            transfer_category=TransferCategory.BOUNDARY_CASE,
            guard_obligations=[ObligationId.ORIGINAL_DOMAIN, ObligationId.SOURCE_RESULT_NONTRANSFER],
            proposed_transfer_status=TransferValidity.UNSAFE_COPY,
            annotation_evidence="Both source roots {2, 3} are excluded by target denominator conditions x != 2 and x != 3. Solution set is strictly empty.",
            review_status=ReviewStatus.PROVISIONAL,
            provenance="DEV02A_PILOT_TRANSFER",
        ),
        # Factorization variant near-miss: FAM_09_V01 -> FAM_09_V03
        TransferPairRecord(
            pair_id="PAIR_FAM09_V01_V03",
            source_problem_id="PROB_FAM09_V01",
            target_problem_id="PROB_FAM09_V03",
            method_id=MethodId.M3_FACTORIZATION,
            method_version="1.0.0",
            proposed_method_instance={"source_equation": "(x - 1)*(x + 2) = 0", "target_equation": "(x - 1)*(x + 2) = 4"},
            transfer_category=TransferCategory.TRANSFER_NEAR_MISS,
            guard_obligations=[ObligationId.TRANSFORMATION_EQUIVALENCE],
            proposed_transfer_status=TransferValidity.INAPPLICABLE_INSTANCE,
            annotation_evidence="Right-hand side changed from 0 to 4. Factored form product property does not apply to non-zero RHS without expansion.",
            review_status=ReviewStatus.PROVISIONAL,
            provenance="DEV02A_PILOT_TRANSFER",
        ),
    ]

    out_dir = Path("data/dev_pilot")
    out_dir.mkdir(parents=True, exist_ok=True)

    f_fam = out_dir / "families.jsonl"
    f_prob = out_dir / "problems.jsonl"
    f_ann = out_dir / "annotations.jsonl"
    f_pair = out_dir / "transfer_pairs.jsonl"

    c_fam = write_canonical_jsonl(f_fam, families, sort_key_attr="family_id")
    c_prob = write_canonical_jsonl(f_prob, problems, sort_key_attr="problem_id")
    c_ann = write_canonical_jsonl(f_ann, annotations, sort_key_attr="annotation_id")
    c_pair = write_canonical_jsonl(f_pair, transfer_pairs, sort_key_attr="pair_id")

    manifest = {
        "manifest_version": "1.0.0",
        "dataset_name": "MKE_PILOT_DEV_DATASET",
        "split": "DEV",
        "file_hashes": {
            "families.jsonl": compute_file_sha256(f_fam),
            "problems.jsonl": compute_file_sha256(f_prob),
            "annotations.jsonl": compute_file_sha256(f_ann),
            "transfer_pairs.jsonl": compute_file_sha256(f_pair),
        },
        "record_counts": {
            "families": c_fam,
            "problems": c_prob,
            "annotations": c_ann,
            "transfer_pairs": c_pair,
        },
        "schema_version": "2.0.0",
        "created_at": "2026-09-25T10:00:00Z",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Generated {c_fam} families, {c_prob} problems, {c_ann} annotations, and {c_pair} transfer pairs.")


if __name__ == "__main__":
    build_dev_pilot_dataset()
