import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { TheoremCard } from '../components/MethodKnowledgeSurface/TheoremCard';
import { mockTheoremQuadraticRoots } from './fixtures/knowledgeFixtures';

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

    expect(
      screen.getByTestId('theorem-loading-THEOREM_QUADRATIC_ROOTS')
    ).toBeInTheDocument();

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
});
