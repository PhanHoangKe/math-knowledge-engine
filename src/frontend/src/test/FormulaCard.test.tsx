import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { FormulaCard } from '../components/MethodKnowledgeSurface/FormulaCard';
import { mockFormulaStandard } from './fixtures/knowledgeFixtures';

describe('FormulaCard Component', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('renders formula with initialData immediately without fetching', () => {
    render(
      <PreferencesProvider initialLanguage="vi">
        <FormulaCard
          formulaId="FORMULA_QUADRATIC_STANDARD"
          initialData={mockFormulaStandard}
        />
      </PreferencesProvider>
    );

    expect(screen.getByText('Công thức nghiệm bậc hai')).toBeInTheDocument();
    expect(screen.getByText('FORMULA_QUADRATIC_STANDARD')).toBeInTheDocument();
    expect(screen.getByTestId('formula-latex-FORMULA_QUADRATIC_STANDARD')).toBeInTheDocument();
    expect(screen.getByText(/Hệ số bậc hai/)).toBeInTheDocument();
  });

  it('fetches formula knowledge via API when no initialData is supplied', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockFormulaStandard), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    render(
      <PreferencesProvider initialLanguage="vi">
        <FormulaCard formulaId="FORMULA_QUADRATIC_STANDARD" />
      </PreferencesProvider>
    );

    expect(
      screen.getByTestId('formula-loading-FORMULA_QUADRATIC_STANDARD')
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm bậc hai')).toBeInTheDocument();
    });

    expect(screen.getByTestId('formula-latex-FORMULA_QUADRATIC_STANDARD')).toBeInTheDocument();
  });

  it('switches variables description language on English preference', () => {
    render(
      <PreferencesProvider initialLanguage="en">
        <FormulaCard
          formulaId="FORMULA_QUADRATIC_STANDARD"
          initialData={mockFormulaStandard}
        />
      </PreferencesProvider>
    );

    expect(screen.getByText('Quadratic formula')).toBeInTheDocument();
    expect(screen.getByText(/Quadratic coefficient/)).toBeInTheDocument();
  });
});
