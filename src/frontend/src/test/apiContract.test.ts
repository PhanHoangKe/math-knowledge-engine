import { describe, it, expect } from 'vitest';
import type {
  SolveRequest,
  SolveResponse200,
  SolvedResponse,
  AnalyzedNoExecutionResponse,
  ApplicationErrorResponse,
  TransportErrorResponse,
  HealthResponse,
} from '../api/contract';

describe('OpenAPI TypeScript Type Contracts', () => {
  it('compiles valid SolveRequest structures matching OpenAPI discriminator contracts', () => {
    const rawReq: SolveRequest = {
      input_payload: {
        input_mode: 'RAW_TEXT',
        raw_query: 'x^2 - 5*x + 6 = 0',
        target_variable: 'x',
      },
      selected_method_id: null,
      schema_version: '1.0.0',
    };

    const coeffReq: SolveRequest = {
      input_payload: {
        input_mode: 'COEFFICIENTS',
        a: { numerator: 1, denominator: 1 },
        b: { numerator: -5, denominator: 1 },
        c: { numerator: 6, denominator: 1 },
        target_variable: 'x',
      },
      selected_method_id: 'QUAD_FORMULA_STANDARD',
      schema_version: '1.0.0',
    };

    expect(rawReq.input_payload.input_mode).toBe('RAW_TEXT');
    expect(coeffReq.input_payload.input_mode).toBe('COEFFICIENTS');
  });

  it('compiles polymorphic response types matching the OpenAPI 200 discriminator contract', () => {
    const solvedSample: SolvedResponse = {
      response_status: 'SOLVED',
      problem: {
        problem_id: 'prob_test_1',
        semantic_revision_hash: 'hash_test_1',
        classification: 'QUADRATIC',
        category: 'ALGEBRA_QUADRATIC',
        problem_type: 'QUADRATIC',
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
        },
      },
      selected_method_id: 'QUAD_FORMULA_STANDARD',
      available_methods: [],
      solution: {
        method_id: 'QUAD_FORMULA_STANDARD',
        outcome: 'TWO_DISTINCT_REAL_ROOTS',
        final_answer_latex: 'x \\in \\{2, 3\\}',
        verification_scope: 'FINAL_SOLUTION',
        roots: [
          { root_type: 'RATIONAL', rational_value: { numerator: 2, denominator: 1 }, latex_str: '2' },
          { root_type: 'RATIONAL', rational_value: { numerator: 3, denominator: 1 }, latex_str: '3' },
        ],
        certificate: {
          certificate_id: 'cert_test_1',
          outcome: 'VERIFIED_COMPLETE',
          verified_at_utc: '2026-10-01T00:00:00Z',
          integrity_fingerprint: 'fp_test_1',
          problem_hash: 'hash_test_1',
          verifier_name: 'MKE_HOST_INDEPENDENT_VERIFIER_V1',
          verifier_version: '1.0.0',
          multiplicity_verified: true,
          no_real_roots_verified: false,
          vieta_relations_checked: true,
        },
        trace: {
          method_id: 'QUAD_FORMULA_STANDARD',
          solution_outcome: 'TWO_DISTINCT_REAL_ROOTS',
          steps: [],
          final_answer_latex: 'x \\in \\{2, 3\\}',
          is_complete: true,
        },
      },
    };

    const analyzedSample: AnalyzedNoExecutionResponse = {
      response_status: 'ANALYZED_NO_EXECUTION',
      reason_code: 'METHOD_NOT_APPLICABLE',
      analysis_message_vi: 'Phương trình suy biến tuyến tính',
      problem: {
        problem_id: 'prob_deg_1',
        semantic_revision_hash: 'hash_deg_1',
        classification: 'LINEAR',
        category: 'ALGEBRA_QUADRATIC',
        problem_type: 'DEGENERATE',
        b: { numerator: 2, denominator: 1 },
        c: { numerator: -4, denominator: 1 },
        equation_latex: '2x - 4 = 0',
      },
    };

    const errorSample: ApplicationErrorResponse = {
      response_status: 'ERROR',
      error_code: 'SYNTAX_ERROR',
      message_vi: 'Lỗi cú pháp',
      message_en: 'Syntax error',
      details: {},
    };

    const unionArray: SolveResponse200[] = [solvedSample, analyzedSample, errorSample];
    expect(unionArray.length).toBe(3);
  });

  it('compiles TransportErrorResponse and HealthResponse contracts', () => {
    const transportErr: TransportErrorResponse = {
      transport_status: 'ERROR',
      transport_error_code: 'REQUEST_VALIDATION_FAILED',
      message_vi: 'Yêu cầu không hợp lệ',
      message_en: 'Request validation failed',
      details: {},
    };

    const health: HealthResponse = {
      status: 'HEALTHY',
      version: '1.0.0',
      milestone: 'MVP_V1_S2',
      algebra_authority: 'mke_product.application.orchestrator.solve_request',
      supported_input_modes: ['RAW_TEXT', 'COEFFICIENTS'],
      registered_methods_count: 9,
      executable_methods_count: 4,
    };

    expect(transportErr.transport_status).toBe('ERROR');
    expect(health.status).toBe('HEALTHY');
  });
});
