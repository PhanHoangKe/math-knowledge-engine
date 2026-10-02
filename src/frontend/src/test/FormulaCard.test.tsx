import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { FormulaCard } from '../components/MethodKnowledgeSurface/FormulaCard';
import { mockFormulaStandard } from './fixtures/knowledgeFixtures';
import type { FormulaKnowledge } from '../api/contract';

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

    const loadingElem = screen.getByTestId('formula-loading-FORMULA_QUADRATIC_STANDARD');
    expect(loadingElem).toBeInTheDocument();
    expect(loadingElem).toHaveAttribute('role', 'status');
    expect(loadingElem).toHaveAttribute('aria-live', 'polite');

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

  it('handles race conditions / out-of-order responses with activeRequestIdRef', async () => {
    let resolveFirstRequest: ((value: Response) => void) | null = null;

    const formulaA: FormulaKnowledge = {
      ...mockFormulaStandard,
      formula_id: 'FORMULA_A',
      title: { vi: 'Công thức chậm A', en: 'Slow Formula A' },
    };

    const formulaB: FormulaKnowledge = {
      ...mockFormulaStandard,
      formula_id: 'FORMULA_B',
      title: { vi: 'Công thức nhanh B', en: 'Fast Formula B' },
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('FORMULA_A')) {
        return new Promise<Response>((resolve) => {
          resolveFirstRequest = resolve;
        });
      }
      if (url.includes('FORMULA_B')) {
        return Promise.resolve(
          new Response(JSON.stringify(formulaB), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    const { rerender } = render(
      <PreferencesProvider initialLanguage="vi">
        <FormulaCard formulaId="FORMULA_A" />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('formula-loading-FORMULA_A')).toBeInTheDocument();

    // Rerender with FORMULA_B before FORMULA_A resolves
    rerender(
      <PreferencesProvider initialLanguage="vi">
        <FormulaCard formulaId="FORMULA_B" />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Công thức nhanh B')).toBeInTheDocument();
    });

    // Now resolve slow request A
    act(() => {
      if (resolveFirstRequest) {
        resolveFirstRequest(
          new Response(JSON.stringify(formulaA), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
    });

    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByText('Công thức nhanh B')).toBeInTheDocument();
    expect(screen.queryByText('Công thức chậm A')).not.toBeInTheDocument();
  });
});
