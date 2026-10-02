import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as clientModule from '../api/client';
import {
  mockSolvedTwoRoots,
  mockAnalyzedDegenerateLinear,
  mockAnalyzedMethodNotExecutable,
  mockAnalyzedMethodNotApplicable,
  mockApplicationErrorSyntax,
  mockTransportError422,
} from './fixtures/responses';
import { NetworkError, ProtocolError } from '../api/client';

describe('MKE Live Algebra Workspace UI Component (<App />)', () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, '', '/');
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('A & B: submits exact RAW_TEXT SolveRequest when clicking compute button and renders loading state', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation').mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(
            () =>
              resolve({
                kind: 'application',
                status: 200,
                response: mockSolvedTwoRoots,
              }),
            50
          );
        })
    );

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });

    const computeBtn = screen.getByTestId('compute-btn');
    expect(computeBtn).not.toBeDisabled();

    fireEvent.click(computeBtn);

    // Assert loading state appears
    expect(screen.getByTestId('workspace-loading')).toBeInTheDocument();
    expect(computeBtn).toBeDisabled();

    // Await response resolution
    await waitFor(() => {
      expect(screen.getByTestId('solved-workspace')).toBeInTheDocument();
    });

    expect(solveSpy).toHaveBeenCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'RAW_TEXT',
          raw_query: 'x^2 - 5*x + 6 = 0',
          target_variable: 'x',
        },
        selected_method_id: null,
      },
      expect.any(AbortSignal)
    );
  });

  it('C: submits equation on Enter keydown in input field', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByTestId('solved-workspace')).toBeInTheDocument();
    });

    expect(solveSpy).toHaveBeenCalledTimes(1);
  });

  it('D & E: renders canonical equation, solution outcome, final answer and root.latex_str from backend', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('canonical-problem-panel')).toBeInTheDocument();
    });

    // Canonical equation
    expect(screen.getByTestId('canonical-equation-latex')).toBeInTheDocument();
    // Solution outcome badge
    expect(screen.getByTestId('solution-outcome-badge')).toHaveTextContent('2 nghiệm thực phân biệt');
    // Final answer latex
    expect(screen.getByTestId('final-answer-latex')).toBeInTheDocument();
    // Roots rendered from root.latex_str
    expect(screen.getByTestId('root-latex-0')).toHaveTextContent('x_1 = 2');
    expect(screen.getByTestId('root-latex-1')).toHaveTextContent('x_2 = 3');
  });

  it('F & G: dynamically renders exactly the number of method cards returned by backend (not hardcoded to 9)', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots, // Contains exactly 3 available methods in fixture
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('method-catalog-panel')).toBeInTheDocument();
    });

    // Must render all 3 cards from fixture
    expect(screen.getByTestId('method-card-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    expect(screen.getByTestId('method-card-QUAD_FORMULA_REDUCED')).toBeInTheDocument();
    expect(screen.getByTestId('method-card-QUAD_VIETA_FACTORING_TRIAL')).toBeInTheDocument();

    // Verify count badge
    expect(screen.getByText('3 phương thức')).toBeInTheDocument();
  });

  it('H & I: switches method sending COEFFICIENTS mode with exact backend a/b/c without client math derivation', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockAnalyzedMethodNotExecutable,
      });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('method-card-QUAD_VIETA_FACTORING_TRIAL')).toBeInTheDocument();
    });

    // Click switch method button on QUAD_VIETA_FACTORING_TRIAL card
    const methodCard = screen.getByTestId('method-card-QUAD_VIETA_FACTORING_TRIAL');
    const selectBtn = methodCard.querySelector('button')!;
    fireEvent.click(selectBtn);

    await waitFor(() => {
      expect(screen.getByTestId('method-not-executable-panel')).toBeInTheDocument();
    });

    expect(solveSpy).toHaveBeenLastCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: -5, denominator: 1 },
          c: { numerator: 6, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: 'QUAD_VIETA_FACTORING_TRIAL',
      },
      expect.any(AbortSignal)
    );
  });

  it('J: METHOD_NOT_EXECUTABLE renders honestly with no solution fallback', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockAnalyzedMethodNotExecutable,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('method-not-executable-panel')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('solution-summary-panel')).not.toBeInTheDocument();
    expect(screen.getByTestId('analysis-message-vi')).toHaveTextContent(
      'Phương pháp được chọn chưa hỗ trợ động cơ giải chi tiết.'
    );
  });

  it('K: METHOD_NOT_APPLICABLE renders honestly', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockAnalyzedMethodNotApplicable,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('method-not-executable-panel')).toBeInTheDocument();
    });

    expect(screen.getByTestId('analysis-message-vi')).toHaveTextContent(
      'Phương pháp được chọn không áp dụng được về mặt toán học cho phương trình này.'
    );
  });

  it('L: Degenerate linear equation renders exact linear solution and no quadratic method catalog', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockAnalyzedDegenerateLinear,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: '2*x - 4 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('degenerate-workspace')).toBeInTheDocument();
    });

    expect(screen.getByTestId('degenerate-outcome-badge')).toHaveTextContent('1 nghiệm bậc nhất duy nhất');
    expect(screen.getByTestId('degenerate-linear-root')).toHaveTextContent('x = 2');
    expect(screen.queryByTestId('method-catalog-panel')).not.toBeInTheDocument();
    expect(screen.queryByTestId('discriminant-display')).not.toBeInTheDocument();
  });

  it('M: Application ERROR renders localized message according to active language', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockApplicationErrorSyntax,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 ++ 5 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('application-error-panel')).toBeInTheDocument();
    });

    // Default Vietnamese
    expect(screen.getByTestId('application-error-code')).toHaveTextContent('SYNTAX_ERROR');
    expect(screen.getByTestId('application-error-message')).toHaveTextContent(
      'Lỗi cú pháp: Biểu thức toán học không hợp lệ tại vị trí đã chỉ định.'
    );
    expect(screen.getByTestId('error-span')).toHaveTextContent('[3, 7)');

    // Switch to English
    fireEvent.click(
      screen.getByRole('button', { name: /Tùy chọn chủ đề & ngôn ngữ|Theme & Language/i })
    );
    fireEvent.click(screen.getByRole('button', { name: /English/i }));

    expect(screen.getByTestId('application-error-message')).toHaveTextContent(
      'Syntax error: Mathematical expression is invalid at the specified location.'
    );
  });

  it('N: Transport errors (422, 413) render via TransportErrorPanel', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'transport-error',
      status: 422,
      response: mockTransportError422,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('transport-error-panel')).toBeInTheDocument();
    });

    expect(screen.getByTestId('transport-error-code')).toHaveTextContent('REQUEST_VALIDATION_FAILED');
  });

  it('O: Network exceptions render generic message without raw exception string leakage', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockRejectedValue(
      new NetworkError('Failed to fetch at secret_url:8000')
    );

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 1 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('network-error-panel')).toBeInTheDocument();
    });

    // Ensure raw exception string is not rendered to user
    const errorText = screen.getByTestId('network-error-message').textContent ?? '';
    expect(errorText).not.toContain('secret_url');
    expect(errorText).toContain('Không thể kết nối đến máy chủ toán học MKE');
  });

  it('P: Protocol / unrecognized JSON errors render safe protocol error panel', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockRejectedValue(
      new ProtocolError('Unrecognized response schema', 500)
    );

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('network-error-panel')).toBeInTheDocument();
    });

    expect(screen.getByText('Phản hồi không hợp lệ')).toBeInTheDocument();
  });

  it('S: Certificate renders VERIFIED_COMPLETE and fingerprint with unkeyed digest disclaimer', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('verification-panel')).toBeInTheDocument();
    });

    expect(screen.getByTestId('verification-outcome-badge')).toHaveTextContent(
      'Xác thực Toàn diện Thành công'
    );
    expect(screen.getByTestId('certificate-id')).toHaveTextContent('cert_quad_std_test_001');
    expect(screen.getByTestId('integrity-fingerprint')).toHaveTextContent(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    );

    // Disclaimer confirming unkeyed SHA-256 digest
    const disclaimer = screen.getByTestId('verification-disclaimer');
    expect(disclaimer.textContent).toContain('mã băm SHA-256 không khóa');
    expect(disclaimer.textContent).toContain('không phải là chữ ký số mật mã học');
  });

  it('T: Trace UI displays pedagogical explanation disclaimer', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    render(<App />);

    const input = screen.getByTestId('equation-input');
    fireEvent.change(input, { target: { value: 'x^2 - 5*x + 6 = 0' } });
    fireEvent.click(screen.getByTestId('compute-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('trace-panel')).toBeInTheDocument();
    });

    const disclaimer = screen.getByTestId('trace-disclaimer');
    expect(disclaimer.textContent).toContain('diễn giải sư phạm tất định');
    expect(disclaimer.textContent).toContain('Phạm vi xác thực toán học độc lập là kết quả nghiệm cuối cùng');
  });
});
