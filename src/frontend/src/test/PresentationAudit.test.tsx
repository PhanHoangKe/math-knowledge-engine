import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { CanonicalProblemPanel } from '../components/CanonicalProblemPanel/CanonicalProblemPanel';
import { VerificationPanel } from '../components/VerificationPanel/VerificationPanel';
import { TracePanel } from '../components/TracePanel/TracePanel';
import { SolutionSummaryPanel } from '../components/SolutionSummaryPanel/SolutionSummaryPanel';
import { RevisionHistoryPanel } from '../components/RevisionHistoryPanel/RevisionHistoryPanel';
import type {
  CanonicalQuadraticProblemView,
  VerificationCertificate,
  SolutionTrace,
  VerifiedSolutionView,
} from '../api/contract';
import type { RevisionHistoryEntry } from '../state/useAlgebraWorkspace';

describe('Presentation & UX Audit Tests (S3-04-R3)', () => {
  const mockQuadProblem: CanonicalQuadraticProblemView = {
    problem_id: 'PROB_QUAD_EX_1',
    semantic_revision_hash: 'hash_abc123',
    problem_type: 'QUADRATIC',
    category: 'ALGEBRA_QUADRATIC',
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
    },
  };

  const mockCertificate: VerificationCertificate = {
    certificate_id: 'CERT_12345',
    integrity_fingerprint: 'sha256_abcdef987654',
    problem_hash: 'hash_abc123',
    outcome: 'VERIFIED_COMPLETE',
    verifier_name: 'MKE_DETERMINISTIC_VERIFIER',
    verifier_version: '1.0.0',
    verified_at_utc: '2026-10-02T12:00:00Z',
    multiplicity_verified: false,
    vieta_relations_checked: true,
    no_real_roots_verified: false,
    residual_checks: ['(2)^2 - 5(2) + 6 = 0', '(3)^2 - 5(3) + 6 = 0'],
    algebraic_identities_passed: ['(x-2)(x-3) \\equiv x^2 - 5x + 6'],
  };

  const mockTrace: SolutionTrace = {
    method_id: 'QUAD_FORMULA_STANDARD',
    solution_outcome: 'TWO_DISTINCT_REAL_ROOTS',
    final_answer_latex: 'S = \\{2, 3\\}',
    is_complete: true,
    steps: [
      {
        step_number: 1,
        explanation_vi: 'Xác định các hệ số a, b, c',
        latex_expression: 'a = 1, b = -5, c = 6',
        why_this_step_vi: 'Chuẩn bị dữ liệu để tính biệt thức Delta',
      },
    ],
  };

  const mockSolution: VerifiedSolutionView = {
    method_id: 'QUAD_FORMULA_STANDARD',
    verification_scope: 'FINAL_SOLUTION',
    outcome: 'TWO_DISTINCT_REAL_ROOTS',
    final_answer_latex: 'S = \\{2, 3\\}',
    roots: [
      {
        root_type: 'RATIONAL',
        latex_str: '2',
        approximate_float: 2.0,
      },
      {
        root_type: 'RATIONAL',
        latex_str: '3',
        approximate_float: 3.0,
      },
    ],
    certificate: mockCertificate,
    trace: mockTrace,
  };

  const mockHistory: RevisionHistoryEntry[] = [
    {
      problem_id: 'PROB_QUAD_EX_1',
      semantic_revision_hash: 'hash_abc123',
      problem_type: 'QUADRATIC',
      classification: 'QUADRATIC',
      equation_latex: 'x^2 - 5x + 6 = 0',
      source_mode: 'RAW_TEXT',
      timestamp_frontend_received: '2026-10-02T12:00:00Z',
      a: { numerator: 1, denominator: 1 },
      b: { numerator: -5, denominator: 1 },
      c: { numerator: 6, denominator: 1 },
    },
  ];

  it('CanonicalProblemPanel hides technical identifiers inside collapsible details and formats Delta cleanly', () => {
    const { unmount } = render(
      <PreferencesProvider initialLanguage="vi">
        <CanonicalProblemPanel problem={mockQuadProblem} />
      </PreferencesProvider>
    );

    // Collapsible details element
    const details = screen.getByTestId('canonical-technical-details');
    expect(details).toBeInTheDocument();
    expect(screen.getByText('Chi tiết kỹ thuật')).toBeInTheDocument();
    expect(screen.getByText('PROB_QUAD_EX_1')).toBeInTheDocument();
    expect(screen.getByText('hash_abc123')).toBeInTheDocument();

    // Discriminant delta label and flags in Vietnamese
    expect(screen.getByText('Biệt thức Δ:')).toBeInTheDocument();
    expect(screen.getByText('Dương (Δ > 0)')).toBeInTheDocument();
    expect(screen.getByText('Chính phương trong ℚ')).toBeInTheDocument();

    unmount();

    // English rendering
    render(
      <PreferencesProvider initialLanguage="en">
        <CanonicalProblemPanel problem={mockQuadProblem} />
      </PreferencesProvider>
    );

    expect(screen.getByText('Technical Details')).toBeInTheDocument();
    expect(screen.getByText('Discriminant Δ:')).toBeInTheDocument();
    expect(screen.getByText('Positive (Δ > 0)')).toBeInTheDocument();
    expect(screen.getByText('Rational Square in ℚ')).toBeInTheDocument();
  });

  it('VerificationPanel renders explicit verification status text and collapsible metadata', () => {
    const { unmount } = render(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={mockCertificate}
          solutionOutcome="TWO_DISTINCT_REAL_ROOTS"
        />
      </PreferencesProvider>
    );

    // Check explicit check status text (no ambiguous dashes)
    expect(screen.queryByText('—')).not.toBeInTheDocument();
    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✓ Đã kiểm tra');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Không áp dụng');

    // Collapsible metadata
    const details = screen.getByTestId('verification-technical-details');
    expect(details).toBeInTheDocument();
    expect(screen.getByText('Chi tiết kỹ thuật')).toBeInTheDocument();
    expect(screen.getByTestId('certificate-id')).toHaveTextContent('CERT_12345');
    expect(screen.getByTestId('integrity-fingerprint')).toHaveTextContent('sha256_abcdef987654');

    unmount();

    // English rendering
    render(
      <PreferencesProvider initialLanguage="en">
        <VerificationPanel
          certificate={mockCertificate}
          solutionOutcome="TWO_DISTINCT_REAL_ROOTS"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✓ Verified');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('Not applicable');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Not applicable');
    expect(screen.getByText('Technical Details')).toBeInTheDocument();
  });

  it('VerificationPanel enforces exact verification criterion applicability matrix for all solution outcomes', () => {
    // 1. TWO_DISTINCT_REAL_ROOTS with vieta=true, mult=false, no_real=false
    const twoRootsCert: VerificationCertificate = {
      ...mockCertificate,
      vieta_relations_checked: true,
      multiplicity_verified: false,
      no_real_roots_verified: false,
    };

    const { rerender } = render(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={twoRootsCert}
          solutionOutcome="TWO_DISTINCT_REAL_ROOTS"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✓ Đã kiểm tra');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Không áp dụng');

    // 2. ONE_REPEATED_REAL_ROOT with vieta=true, mult=true, no_real=false
    const repeatedRootCert: VerificationCertificate = {
      ...mockCertificate,
      vieta_relations_checked: true,
      multiplicity_verified: true,
      no_real_roots_verified: false,
    };

    rerender(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={repeatedRootCert}
          solutionOutcome="ONE_REPEATED_REAL_ROOT"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✓ Đã kiểm tra');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('✓ Đã kiểm tra');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Không áp dụng');

    // 3. NO_REAL_ROOTS with vieta=false, mult=false, no_real=true
    const noRootsCert: VerificationCertificate = {
      ...mockCertificate,
      vieta_relations_checked: false,
      multiplicity_verified: false,
      no_real_roots_verified: true,
    };

    rerender(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={noRootsCert}
          solutionOutcome="NO_REAL_ROOTS"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-vieta')).toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('✓ Đã kiểm tra');

    // 4. Applicable FAILED criterion in ONE_REPEATED_REAL_ROOT (multiplicity=false, outcome=VERIFICATION_FAILED)
    const failedMultCert: VerificationCertificate = {
      ...mockCertificate,
      outcome: 'VERIFICATION_FAILED',
      vieta_relations_checked: true,
      multiplicity_verified: false,
      no_real_roots_verified: false,
    };

    rerender(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={failedMultCert}
          solutionOutcome="ONE_REPEATED_REAL_ROOT"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('✗ Không đạt');
    expect(screen.getByTestId('check-multiplicity')).not.toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✓ Đã kiểm tra');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Không áp dụng');

    // 5. Applicable FAILED criterion in TWO_DISTINCT_REAL_ROOTS (vieta=false, outcome=VERIFICATION_FAILED)
    const failedVietaCert: VerificationCertificate = {
      ...mockCertificate,
      outcome: 'VERIFICATION_FAILED',
      vieta_relations_checked: false,
      multiplicity_verified: false,
      no_real_roots_verified: false,
    };

    rerender(
      <PreferencesProvider initialLanguage="vi">
        <VerificationPanel
          certificate={failedVietaCert}
          solutionOutcome="TWO_DISTINCT_REAL_ROOTS"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('check-vieta')).toHaveTextContent('✗ Không đạt');
    expect(screen.getByTestId('check-vieta')).not.toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-multiplicity')).toHaveTextContent('Không áp dụng');
    expect(screen.getByTestId('check-no-real-roots')).toHaveTextContent('Không áp dụng');
  });

  it('TracePanel renders exact "Vì sao làm bước này?" / "Why this step?" label without trailing colon', () => {
    const { unmount } = render(
      <PreferencesProvider initialLanguage="vi">
        <TracePanel trace={mockTrace} />
      </PreferencesProvider>
    );

    expect(screen.getByText('Lời giải từng bước')).toBeInTheDocument();
    expect(screen.getByText('Vì sao làm bước này?')).toBeInTheDocument();
    expect(screen.queryByText('Vì sao làm bước này?:')).not.toBeInTheDocument();
    expect(screen.getByText('Chuẩn bị dữ liệu để tính biệt thức Delta')).toBeInTheDocument();

    unmount();

    render(
      <PreferencesProvider initialLanguage="en">
        <TracePanel trace={mockTrace} />
      </PreferencesProvider>
    );

    expect(screen.getByText('Step-by-Step Solution')).toBeInTheDocument();
    expect(screen.getByText('Why this step?')).toBeInTheDocument();
    expect(screen.queryByText('Why this step?:')).not.toBeInTheDocument();
  });

  it('SolutionSummaryPanel and RevisionHistoryPanel render cleaned copy without raw LaTeX leaks', () => {
    const { unmount } = render(
      <PreferencesProvider initialLanguage="vi">
        <SolutionSummaryPanel solution={mockSolution} />
        <RevisionHistoryPanel history={mockHistory} />
      </PreferencesProvider>
    );

    expect(screen.getByText('Lịch sử phiên làm việc')).toBeInTheDocument();
    expect(screen.getByText('Tập nghiệm S:')).toBeInTheDocument();

    unmount();

    render(
      <PreferencesProvider initialLanguage="en">
        <SolutionSummaryPanel solution={mockSolution} />
        <RevisionHistoryPanel history={mockHistory} />
      </PreferencesProvider>
    );

    expect(screen.getByText('Session Revision History')).toBeInTheDocument();
    expect(screen.getByText('Solution Set S:')).toBeInTheDocument();
  });
});
