import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { TheoremCard } from '../components/MethodKnowledgeSurface/TheoremCard';
import { mockTheoremQuadraticRoots } from './fixtures/knowledgeFixtures';
import type { TheoremKnowledge } from '../api/contract';

describe('TheoremCard Component', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('renders theorem with initialData immediately without fetching', () => {
    render(
      <PreferencesProvider initialLanguage="vi">
        <TheoremCard
          theoremId="THEOREM_QUADRATIC_ROOTS"
          initialData={mockTheoremQuadraticRoots}
        />
      </PreferencesProvider>
    );

    expect(
      screen.getByText('Định lý về số nghiệm của phương trình bậc hai')
    ).toBeInTheDocument();
    expect(screen.getByText('THEOREM_QUADRATIC_ROOTS')).toBeInTheDocument();
    expect(screen.getByTestId('theorem-latex-THEOREM_QUADRATIC_ROOTS')).toBeInTheDocument();
    expect(screen.getByText(/Delta > 0: 2 nghiệm phân biệt/)).toBeInTheDocument();
  });

  it('fetches theorem knowledge via API when no initialData is supplied', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockTheoremQuadraticRoots), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    render(
      <PreferencesProvider initialLanguage="vi">
        <TheoremCard theoremId="THEOREM_QUADRATIC_ROOTS" />
      </PreferencesProvider>
    );

    const loadingElem = screen.getByTestId('theorem-loading-THEOREM_QUADRATIC_ROOTS');
    expect(loadingElem).toBeInTheDocument();
    expect(loadingElem).toHaveAttribute('role', 'status');
    expect(loadingElem).toHaveAttribute('aria-live', 'polite');

    await waitFor(() => {
      expect(
        screen.getByText('Định lý về số nghiệm của phương trình bậc hai')
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId('theorem-latex-THEOREM_QUADRATIC_ROOTS')).toBeInTheDocument();
  });

  it('switches theorem texts on English preference', () => {
    render(
      <PreferencesProvider initialLanguage="en">
        <TheoremCard
          theoremId="THEOREM_QUADRATIC_ROOTS"
          initialData={mockTheoremQuadraticRoots}
        />
      </PreferencesProvider>
    );

    expect(
      screen.getByText('Theorem on Number of Quadratic Roots')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Delta > 0: 2 distinct real roots/)
    ).toBeInTheDocument();
  });

  it('handles race conditions / out-of-order responses with activeRequestIdRef', async () => {
    let resolveFirstRequest: ((value: Response) => void) | null = null;

    const theoremA: TheoremKnowledge = {
      ...mockTheoremQuadraticRoots,
      theorem_id: 'THEOREM_A',
      title: { vi: 'Định lý chậm A', en: 'Slow Theorem A' },
    };

    const theoremB: TheoremKnowledge = {
      ...mockTheoremQuadraticRoots,
      theorem_id: 'THEOREM_B',
      title: { vi: 'Định lý nhanh B', en: 'Fast Theorem B' },
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('THEOREM_A')) {
        return new Promise<Response>((resolve) => {
          resolveFirstRequest = resolve;
        });
      }
      if (url.includes('THEOREM_B')) {
        return Promise.resolve(
          new Response(JSON.stringify(theoremB), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    const { rerender } = render(
      <PreferencesProvider initialLanguage="vi">
        <TheoremCard theoremId="THEOREM_A" />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('theorem-loading-THEOREM_A')).toBeInTheDocument();

    // Switch prop to THEOREM_B before THEOREM_A resolves
    rerender(
      <PreferencesProvider initialLanguage="vi">
        <TheoremCard theoremId="THEOREM_B" />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Định lý nhanh B')).toBeInTheDocument();
    });

    // Now resolve slow request A
    act(() => {
      if (resolveFirstRequest) {
        resolveFirstRequest(
          new Response(JSON.stringify(theoremA), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
    });

    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByText('Định lý nhanh B')).toBeInTheDocument();
    expect(screen.queryByText('Định lý chậm A')).not.toBeInTheDocument();
  });
});
