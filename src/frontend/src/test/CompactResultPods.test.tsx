import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { SelectedMethodPod } from '../components/SelectedMethodPod/SelectedMethodPod';
import { VerificationSummaryPod } from '../components/VerificationSummaryPod/VerificationSummaryPod';
import { TraceSummaryPod } from '../components/TraceSummaryPod/TraceSummaryPod';
import App from '../App';
import * as clientModule from '../api/client';
import { mockSolvedTwoRoots } from './fixtures/responses';

describe('Compact Result Pods Component & Integration Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, '', '/');
    vi.restoreAllMocks();
  });

  describe('<SelectedMethodPod />', () => {
    it('renders selected method summary, badges and toggle controls', () => {
      const onToggleShowAll = vi.fn();
      const onSelectMethod = vi.fn();

      render(
        <PreferencesProvider>
          <SelectedMethodPod
            methods={mockSolvedTwoRoots.available_methods}
            selectedMethodId="QUAD_FORMULA_STANDARD"
            onSelectMethod={onSelectMethod}
            showAllMethods={false}
            onToggleShowAllMethods={onToggleShowAll}
          />
        </PreferencesProvider>
      );

      expect(screen.getByTestId('selected-method-summary-pod')).toBeInTheDocument();
      expect(screen.getByText('Công thức nghiệm tổng quát (Biệt thức Delta)')).toBeInTheDocument();
      expect(screen.getByText('QUAD_FORMULA_STANDARD')).toBeInTheDocument();

      const toggleBtn = screen.getByTestId('toggle-methods-btn');
      expect(toggleBtn).toBeInTheDocument();
      fireEvent.click(toggleBtn);
      expect(onToggleShowAll).toHaveBeenCalledTimes(1);

      const whyBtn = screen.getByTestId('why-method-btn-QUAD_FORMULA_STANDARD');
      expect(whyBtn).toBeInTheDocument();
    });

    it('renders full method catalog when showAllMethods is true', () => {
      const onToggleShowAll = vi.fn();
      const onSelectMethod = vi.fn();

      render(
        <PreferencesProvider>
          <SelectedMethodPod
            methods={mockSolvedTwoRoots.available_methods}
            selectedMethodId="QUAD_FORMULA_STANDARD"
            onSelectMethod={onSelectMethod}
            showAllMethods={true}
            onToggleShowAllMethods={onToggleShowAll}
          />
        </PreferencesProvider>
      );

      expect(screen.getByTestId('method-catalog-panel')).toBeInTheDocument();
      expect(screen.getByTestId('method-card-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    });
  });

  describe('<VerificationSummaryPod />', () => {
    it('renders verification summary, criteria check items, disclaimer and technical details', () => {
      render(
        <PreferencesProvider>
          <VerificationSummaryPod
            certificate={mockSolvedTwoRoots.solution.certificate}
            verificationScope={mockSolvedTwoRoots.solution.verification_scope}
            solutionOutcome={mockSolvedTwoRoots.solution.outcome}
          />
        </PreferencesProvider>
      );

      expect(screen.getByTestId('verification-summary-pod')).toBeInTheDocument();
      expect(screen.getByTestId('verification-outcome-badge')).toHaveTextContent('Xác thực Toàn diện Thành công');
      expect(screen.getByTestId('verification-disclaimer')).toBeInTheDocument();
      expect(screen.getByTestId('check-vieta')).toBeInTheDocument();
      expect(screen.getByTestId('check-multiplicity')).toBeInTheDocument();
      expect(screen.getByTestId('check-no-real-roots')).toBeInTheDocument();

      // Technical details
      expect(screen.getByTestId('verification-technical-details')).toBeInTheDocument();
      expect(screen.getByTestId('certificate-id')).toBeInTheDocument();
      expect(screen.getByTestId('integrity-fingerprint')).toBeInTheDocument();

      // Toggle full verification button
      const toggleBtn = screen.getByTestId('toggle-verification-btn');
      expect(toggleBtn).toBeInTheDocument();
      expect(screen.queryByTestId('verification-panel')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(toggleBtn);
      expect(screen.getByTestId('verification-panel')).toBeInTheDocument();
    });
  });

  describe('<TraceSummaryPod />', () => {
    it('renders trace header, disclaimer, step 1 preview and expands to full trace', () => {
      render(
        <PreferencesProvider>
          <TraceSummaryPod trace={mockSolvedTwoRoots.solution.trace} />
        </PreferencesProvider>
      );

      expect(screen.getByTestId('trace-summary-pod')).toBeInTheDocument();
      expect(screen.getByTestId('trace-disclaimer')).toBeInTheDocument();
      expect(screen.getByTestId('trace-step-1')).toBeInTheDocument();
      expect(screen.queryByTestId('trace-panel')).not.toBeInTheDocument();

      // Click toggle button to view full trace panel
      const toggleBtn = screen.getByTestId('toggle-trace-btn');
      fireEvent.click(toggleBtn);

      expect(screen.getByTestId('trace-panel')).toBeInTheDocument();
    });
  });

  describe('Full Workspace Pod Layout Integration in <App />', () => {
    it('renders solved workspace organized into compact pods with collapsed coefficient editor', async () => {
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
        expect(screen.getByTestId('solved-workspace')).toBeInTheDocument();
      });

      // Assert all compact Pods exist in the solved workspace
      expect(screen.getByTestId('canonical-problem-panel')).toBeInTheDocument();
      expect(screen.getByTestId('solution-summary-panel')).toBeInTheDocument();
      expect(screen.getByTestId('verification-summary-pod')).toBeInTheDocument();
      expect(screen.getByTestId('selected-method-summary-pod')).toBeInTheDocument();
      expect(screen.getByTestId('trace-summary-pod')).toBeInTheDocument();
      expect(screen.getByTestId('coefficient-editor-disclosure')).toBeInTheDocument();

      // Coefficient Editor is collapsed by default
      expect(screen.queryByTestId('coefficient-editor-panel')).not.toBeInTheDocument();

      // Expand Coefficient Editor via disclosure button
      const coeffToggleBtn = screen.getByTestId('toggle-coeff-editor-btn');
      fireEvent.click(coeffToggleBtn);

      expect(screen.getByTestId('coefficient-editor-panel')).toBeInTheDocument();
      expect(screen.getByTestId('coeff-a-num')).toBeInTheDocument();
      expect(screen.getByTestId('coeff-b-num')).toBeInTheDocument();
      expect(screen.getByTestId('coeff-c-num')).toBeInTheDocument();
    });
  });
});
