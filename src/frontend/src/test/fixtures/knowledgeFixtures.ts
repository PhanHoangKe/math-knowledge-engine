import type {
  MethodKnowledge,
  ConceptKnowledge,
  FormulaKnowledge,
  TheoremKnowledge,
} from '../../api/contract';

export const mockMethodKnowledgeStandard: MethodKnowledge = {
  method_id: 'QUAD_FORMULA_STANDARD',
  version: '1.0.0',
  title: {
    vi: 'Công thức nghiệm chuẩn tắc (Biệt thức Delta)',
    en: 'Standard Quadratic Formula (Discriminant Delta)',
  },
  summary: {
    vi: 'Phương pháp giải tổng quát cho mọi phương trình bậc hai thông qua biệt thức Delta.',
    en: 'General solution method for any quadratic equation using discriminant Delta.',
  },
  learning_objective: {
    vi: 'Học sinh nắm vững cách tính Delta, phân loại số nghiệm và áp dụng công thức nghiệm.',
    en: 'Students master Delta calculation, root classification, and quadratic formula application.',
  },
  formal_description: {
    vi: 'Tính Delta = b^2 - 4ac, từ đó suy ra nghiệm x = (-b +- sqrt(Delta)) / (2a).',
    en: 'Compute Delta = b^2 - 4ac, yielding roots x = (-b +- sqrt(Delta)) / (2a).',
  },
  prerequisite_concept_ids: ['concept_discriminant', 'concept_quadratic_equation'],
  formula_refs: ['FORMULA_QUADRATIC_STANDARD', 'FORMULA_DISCRIMINANT_DELTA'],
  theorem_refs: ['THEOREM_QUADRATIC_ROOTS'],
  applicability_guidance: [
    {
      vi: 'Áp dụng cho mọi phương trình bậc hai ax^2 + bx + c = 0 với a khác 0.',
      en: 'Applicable to any quadratic equation ax^2 + bx + c = 0 with a != 0.',
    },
  ],
  non_applicability_guidance: [
    {
      vi: 'Không áp dụng khi hệ số a = 0 (phương trình suy biến bậc nhất).',
      en: 'Not applicable when coefficient a = 0 (degenerate linear equation).',
    },
  ],
  common_mistakes: [
    {
      vi: 'Nhầm lẫn dấu của hệ số b khi tính (-b) hoặc quên nhân 4ac.',
      en: 'Confusing sign of coefficient b in (-b) or forgetting to multiply 4ac.',
    },
  ],
  diagnostic_tips: [
    {
      vi: 'Kiểm tra kỹ dấu của tích ac: nếu ac < 0 thì luôn có 2 nghiệm phân biệt.',
      en: 'Check sign of ac: if ac < 0, there are always 2 distinct real roots.',
    },
  ],
  curriculum_refs: [
    {
      framework: 'GDPT_2018',
      grade_band: 'GRADE_9',
      subject: 'TOAN',
      topic: 'PHUONG_TRINH_BAC_HAI_MOT_AN',
      source_document: 'Chuong trinh GDPT 2018 Mon Toan',
      source_locator: 'Muc IV.2 - Phuong trinh bac hai',
      status: 'VERIFIED_MAPPING',
      competency_ref: 'TOAN9_PTBH_01',
    },
  ],
  provenance_refs: ['SRC_VIETNAM_MOET_MATH_9_T2', 'SRC_GELFAND_ALGEBRA'],
};

export const mockConceptDiscriminant: ConceptKnowledge = {
  concept_id: 'concept_discriminant',
  version: '1.0.0',
  title: {
    vi: 'Biệt thức Delta',
    en: 'Discriminant Delta',
  },
  definition: {
    vi: 'Biệt thức của tam thức bậc hai ax^2 + bx + c là đại lượng Delta = b^2 - 4ac.',
    en: 'The discriminant of a quadratic polynomial ax^2 + bx + c is Delta = b^2 - 4ac.',
  },
  prerequisite_concept_ids: ['concept_quadratic_equation'],
  formula_refs: ['FORMULA_DISCRIMINANT_DELTA'],
  provenance_refs: ['SRC_VIETNAM_MOET_MATH_9_T2'],
};

export const mockConceptQuadraticEquation: ConceptKnowledge = {
  concept_id: 'concept_quadratic_equation',
  version: '1.0.0',
  title: {
    vi: 'Phương trình bậc hai một ẩn',
    en: 'Quadratic equation in one variable',
  },
  definition: {
    vi: 'Phương trình dạng ax^2 + bx + c = 0 trong đó a khác 0.',
    en: 'Equation of form ax^2 + bx + c = 0 where a != 0.',
  },
  prerequisite_concept_ids: [],
  provenance_refs: ['SRC_VIETNAM_MOET_MATH_9_T2'],
};

export const mockFormulaStandard: FormulaKnowledge = {
  formula_id: 'FORMULA_QUADRATIC_STANDARD',
  version: '1.0.0',
  title: {
    vi: 'Công thức nghiệm bậc hai',
    en: 'Quadratic formula',
  },
  latex_template: 'x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}',
  domain_conditions: {
    vi: 'a \\neq 0 \\text{ và } \\Delta \\ge 0',
    en: 'a \\neq 0 \\text{ and } \\Delta \\ge 0',
  },
  variables_description: {
    a: { vi: 'Hệ số bậc hai (a != 0)', en: 'Quadratic coefficient (a != 0)' },
    b: { vi: 'Hệ số bậc nhất', en: 'Linear coefficient' },
    Delta: { vi: 'Biệt thức b^2 - 4ac', en: 'Discriminant b^2 - 4ac' },
  },
  provenance_refs: ['SRC_VIETNAM_MOET_MATH_9_T2'],
};

export const mockTheoremQuadraticRoots: TheoremKnowledge = {
  theorem_id: 'THEOREM_QUADRATIC_ROOTS',
  version: '1.0.0',
  title: {
    vi: 'Định lý về số nghiệm của phương trình bậc hai',
    en: 'Theorem on Number of Quadratic Roots',
  },
  statement: {
    vi: 'Số nghiệm thực của ax^2 + bx + c = 0 (a != 0) phụ thuộc hoàn toàn vào dấu của Delta.',
    en: 'Number of real roots of ax^2 + bx + c = 0 (a != 0) depends strictly on the sign of Delta.',
  },
  formal_statement_latex: '\\Delta > 0 \\implies |S|=2, \\; \\Delta = 0 \\implies |S|=1, \\; \\Delta < 0 \\implies S=\\emptyset',
  hypotheses: [
    { vi: 'a, b, c thuộc R với a != 0', en: 'a, b, c in R with a != 0' },
    { vi: 'Delta = b^2 - 4ac', en: 'Delta = b^2 - 4ac' },
  ],
  conclusions: [
    { vi: 'Delta > 0: 2 nghiệm phân biệt', en: 'Delta > 0: 2 distinct real roots' },
    { vi: 'Delta = 0: 1 nghiệm kép', en: 'Delta = 0: 1 repeated real root' },
    { vi: 'Delta < 0: vô nghiệm trên R', en: 'Delta < 0: no real roots in R' },
  ],
  provenance_refs: ['SRC_VIETNAM_MOET_MATH_9_T2'],
};
