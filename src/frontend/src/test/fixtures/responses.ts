/**
 * Test Fixtures for MKE Live Workspace.
 * 
 * Strictly typed against generated OpenAPI DTO models.
 * Test-only; never imported in production runtime code.
 */

import type {
  SolvedResponse,
  AnalyzedNoExecutionResponse,
  ApplicationErrorResponse,
  TransportErrorResponse,
} from '../../api/contract';

export const mockSolvedTwoRoots: SolvedResponse = {
  response_status: 'SOLVED',
  selected_method_id: 'QUAD_FORMULA_STANDARD',
  problem: {
    category: 'ALGEBRA_QUADRATIC',
    problem_type: 'QUADRATIC',
    classification: 'QUADRATIC',
    equation_latex: 'x^2 - 5x + 6 = 0',
    a: { numerator: 1, denominator: 1 },
    b: { numerator: -5, denominator: 1 },
    c: { numerator: 6, denominator: 1 },
    discriminant: {
      value: { numerator: 1, denominator: 1 },
      is_positive: true,
      is_zero: false,
      is_negative: false,
      is_rational_square: true,
      squarefree_kernel: 1,
      square_root_rational: { numerator: 1, denominator: 1 },
    },
    problem_id: 'prob_quad_x2_minus_5x_plus_6',
    semantic_revision_hash: 'rev_hash_abc123',
    raw_query: 'x^2 - 5*x + 6 = 0',
  },
  available_methods: [
    {
      method_id: 'QUAD_FORMULA_STANDARD',
      title_vi: 'Công thức nghiệm tổng quát (Biệt thức Delta)',
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'AVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      pedagogical_priority: 1,
      verification_capability: 'HOST_VERIFIABLE',
      support_status: 'SUPPORTED',
      has_trace_available: true,
      reasons: ['Phương trình bậc hai hợp lệ với hệ số a != 0.'],
      prerequisites: [
        {
          prerequisite_id: 'PREREQ_QUAD_STD_FORM',
          description_vi: 'Đã đưa về dạng chuẩn tắc ax^2 + bx + c = 0',
          is_satisfied: true,
        },
      ],
    },
    {
      method_id: 'QUAD_FORMULA_REDUCED',
      title_vi: 'Công thức nghiệm thu gọn (Biệt thức Delta phẩy)',
      mathematical_applicability: 'NOT_APPLICABLE',
      execution_availability: 'AVAILABLE',
      pedagogical_recommendation: 'DISCOURAGED',
      pedagogical_priority: 2,
      verification_capability: 'HOST_VERIFIABLE',
      support_status: 'SUPPORTED',
      has_trace_available: true,
      reasons: ['Hệ số b = -5 là số lẻ, không áp dụng được b = 2b\'.'],
    },
    {
      method_id: 'QUAD_COMPLETE_SQUARE',
      title_vi: 'Phương pháp biến đổi thêm bớt tạo bình phương hoàn thức',
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'UNAVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      pedagogical_priority: 3,
      verification_capability: 'HOST_VERIFIABLE',
      support_status: 'SUPPORTED',
      has_trace_available: false,
      reasons: ['Biệt thức Delta là số chính phương hữu tỉ.'],
    },
  ],
  solution: {
    method_id: 'QUAD_FORMULA_STANDARD',
    outcome: 'TWO_DISTINCT_REAL_ROOTS',
    final_answer_latex: 'S = \\{2, 3\\}',
    verification_scope: 'FINAL_SOLUTION',
    roots: [
      {
        root_type: 'RATIONAL',
        latex_str: '2',
        rational_value: { numerator: 2, denominator: 1 },
        approximate_float: 2.0,
      },
      {
        root_type: 'RATIONAL',
        latex_str: '3',
        rational_value: { numerator: 3, denominator: 1 },
        approximate_float: 3.0,
      },
    ],
    trace: {
      method_id: 'QUAD_FORMULA_STANDARD',
      solution_outcome: 'TWO_DISTINCT_REAL_ROOTS',
      final_answer_latex: 'S = \\{2, 3\\}',
      is_complete: true,
      steps: [
        {
          step_number: 1,
          explanation_vi: 'Xác định các hệ số của phương trình bậc hai:',
          latex_expression: 'a = 1,\\; b = -5,\\; c = 6',
          rule_or_theorem_used: 'Xác định hệ số chuẩn tắc',
          why_this_step_vi: 'Chuẩn bị dữ liệu cho công thức biệt thức',
        },
        {
          step_number: 2,
          explanation_vi: 'Tính biệt thức Delta:',
          latex_expression: '\\Delta = b^2 - 4ac = (-5)^2 - 4(1)(6) = 25 - 24 = 1',
          rule_or_theorem_used: 'Định nghĩa biệt thức Delta',
          why_this_step_vi: 'Xác định số lượng nghiệm thực',
        },
        {
          step_number: 3,
          explanation_vi: 'Vì Delta > 0, phương trình có 2 nghiệm thực phân biệt:',
          latex_expression: 'x_1 = \\frac{-(-5) - \\sqrt{1}}{2(1)} = 2,\\quad x_2 = \\frac{-(-5) + \\sqrt{1}}{2(1)} = 3',
          rule_or_theorem_used: 'Công thức nghiệm bậc hai',
          why_this_step_vi: 'Tính toán giá trị các nghiệm',
        },
      ],
    },
    certificate: {
      certificate_id: 'cert_quad_std_test_001',
      outcome: 'VERIFIED_COMPLETE',
      problem_hash: 'hash_prob_123',
      integrity_fingerprint: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      verifier_name: 'MKE_HOST_INDEPENDENT_VERIFIER_V1',
      verifier_version: '1.0.0',
      verified_at_utc: '2026-10-02T00:00:00Z',
      multiplicity_verified: true,
      no_real_roots_verified: false,
      vieta_relations_checked: true,
      algebraic_identities_passed: ['(x - 2)(x - 3) = x^2 - 5x + 6'],
      residual_checks: ['P(2) = 0', 'P(3) = 0'],
    },
  },
};

export const mockSolvedNoRealRoots: SolvedResponse = {
  response_status: 'SOLVED',
  selected_method_id: 'QUAD_FORMULA_STANDARD',
  problem: {
    category: 'ALGEBRA_QUADRATIC',
    problem_type: 'QUADRATIC',
    classification: 'QUADRATIC',
    equation_latex: 'x^2 + 1 = 0',
    a: { numerator: 1, denominator: 1 },
    b: { numerator: 0, denominator: 1 },
    c: { numerator: 1, denominator: 1 },
    discriminant: {
      value: { numerator: -4, denominator: 1 },
      is_positive: false,
      is_zero: false,
      is_negative: true,
      is_rational_square: false,
      squarefree_kernel: null,
    },
    problem_id: 'prob_quad_x2_plus_1',
    semantic_revision_hash: 'rev_hash_no_roots',
  },
  available_methods: [
    {
      method_id: 'QUAD_FORMULA_STANDARD',
      title_vi: 'Công thức nghiệm tổng quát',
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'AVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      pedagogical_priority: 1,
      verification_capability: 'HOST_VERIFIABLE',
      support_status: 'SUPPORTED',
      has_trace_available: true,
    },
  ],
  solution: {
    method_id: 'QUAD_FORMULA_STANDARD',
    outcome: 'NO_REAL_ROOTS',
    final_answer_latex: 'S = \\emptyset',
    verification_scope: 'FINAL_SOLUTION',
    roots: [],
    trace: {
      method_id: 'QUAD_FORMULA_STANDARD',
      solution_outcome: 'NO_REAL_ROOTS',
      final_answer_latex: 'S = \\emptyset',
      is_complete: true,
      steps: [
        {
          step_number: 1,
          explanation_vi: 'Tính biệt thức Delta:',
          latex_expression: '\\Delta = 0^2 - 4(1)(1) = -4 < 0',
        },
      ],
    },
    certificate: {
      certificate_id: 'cert_quad_no_roots_001',
      outcome: 'VERIFIED_COMPLETE',
      problem_hash: 'hash_no_roots',
      integrity_fingerprint: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
      verifier_name: 'MKE_HOST_INDEPENDENT_VERIFIER_V1',
      verifier_version: '1.0.0',
      multiplicity_verified: false,
      no_real_roots_verified: true,
      vieta_relations_checked: false,
    },
  },
};

export const mockAnalyzedDegenerateLinear: AnalyzedNoExecutionResponse = {
  response_status: 'ANALYZED_NO_EXECUTION',
  reason_code: 'DEGENERATE_EXACT_SOLUTION',
  analysis_message_vi: 'Phương trình suy biến thành phương trình bậc nhất có nghiệm duy nhất.',
  problem: {
    category: 'ALGEBRA_QUADRATIC',
    problem_type: 'DEGENERATE',
    classification: 'LINEAR',
    equation_latex: '2x - 4 = 0',
    b: { numerator: 2, denominator: 1 },
    c: { numerator: -4, denominator: 1 },
    linear_root: { numerator: 2, denominator: 1 },
    problem_id: 'prob_degen_2x_minus_4',
    semantic_revision_hash: 'rev_hash_degen_1',
  },
  available_methods: [],
  degenerate_solution: {
    classification: 'LINEAR',
    outcome: 'ONE_REAL_LINEAR_ROOT',
    final_answer_latex: 'S = \\{2\\}',
    linear_root: { numerator: 2, denominator: 1 },
    verification_scope: 'FINAL_SOLUTION',
    certificate: {
      certificate_id: 'cert_degen_linear_001',
      outcome: 'VERIFIED_COMPLETE',
      problem_hash: 'hash_degen_1',
      integrity_fingerprint: 'bc614e7a6da0a4f54e1564f9b87df346e9df1bc1e3bc7c5b6b19803ae4ff57d4',
      verifier_name: 'MKE_HOST_INDEPENDENT_VERIFIER_V1',
      verifier_version: '1.0.0',
      multiplicity_verified: false,
      no_real_roots_verified: false,
      vieta_relations_checked: false,
      residual_checks: ['2(2) - 4 = 0'],
    },
  },
};

export const mockAnalyzedMethodNotExecutable: AnalyzedNoExecutionResponse = {
  response_status: 'ANALYZED_NO_EXECUTION',
  reason_code: 'METHOD_NOT_EXECUTABLE',
  analysis_message_vi: 'Phương pháp được chọn chưa hỗ trợ động cơ giải chi tiết.',
  selected_method_id: 'QUAD_COMPLETE_SQUARE',
  problem: mockSolvedTwoRoots.problem,
  available_methods: mockSolvedTwoRoots.available_methods,
};

export const mockAnalyzedMethodNotApplicable: AnalyzedNoExecutionResponse = {
  response_status: 'ANALYZED_NO_EXECUTION',
  reason_code: 'METHOD_NOT_APPLICABLE',
  analysis_message_vi: 'Phương pháp được chọn không áp dụng được về mặt toán học cho phương trình này.',
  selected_method_id: 'QUAD_FORMULA_REDUCED',
  problem: mockSolvedTwoRoots.problem,
  available_methods: mockSolvedTwoRoots.available_methods,
};

export const mockApplicationErrorSyntax: ApplicationErrorResponse = {
  response_status: 'ERROR',
  error_code: 'SYNTAX_ERROR',
  message_vi: 'Lỗi cú pháp: Biểu thức toán học không hợp lệ tại vị trí đã chỉ định.',
  message_en: 'Syntax error: Mathematical expression is invalid at the specified location.',
  span: {
    start: 3,
    end: 7,
  },
};

export const mockTransportError400: TransportErrorResponse = {
  transport_status: 'ERROR',
  transport_error_code: 'MALFORMED_JSON',
  message_vi: 'Dữ liệu JSON trong yêu cầu không hợp lệ.',
  message_en: 'Malformed JSON payload in request.',
};

export const mockTransportError422: TransportErrorResponse = {
  transport_status: 'ERROR',
  transport_error_code: 'REQUEST_VALIDATION_FAILED',
  message_vi: 'Dữ liệu gửi lên không đúng định dạng schema API quy định.',
  message_en: 'Request payload validation failed against API DTO schema.',
  details: {
    field: 'raw_query',
    error: 'Input string length exceeds maximum allowed limit.',
  },
};

export const mockTransportError413: TransportErrorResponse = {
  transport_status: 'ERROR',
  transport_error_code: 'PAYLOAD_TOO_LARGE',
  message_vi: 'Kích thước payload vượt quá giới hạn 64 KiB cho phép.',
  message_en: 'Request payload exceeds the 64 KiB size limit.',
};

export const mockTransportError415: TransportErrorResponse = {
  transport_status: 'ERROR',
  transport_error_code: 'UNSUPPORTED_MEDIA_TYPE',
  message_vi: 'Loại nội dung không được hỗ trợ. Vui lòng gửi application/json.',
  message_en: 'Unsupported Media Type. Expected application/json.',
};

export const mockTransportErrorWithSecretDetail: TransportErrorResponse = {
  transport_status: 'ERROR',
  transport_error_code: 'REQUEST_VALIDATION_FAILED',
  message_vi: 'Lỗi xác thực dữ liệu kiểm tra rò rỉ chi tiết.',
  message_en: 'Validation error for testing detail leakage.',
  details: {
    reason: 'Safe validation summary',
    SECRET_UNKNOWN_DETAIL_SENTINEL: 'MUST_NOT_RENDER',
  },
};
