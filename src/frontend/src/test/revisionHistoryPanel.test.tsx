import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RevisionHistoryPanel } from '../components/RevisionHistoryPanel/RevisionHistoryPanel';
import { PreferencesProvider } from '../state/preferences';
import type { RevisionHistoryEntry } from '../state/useAlgebraWorkspace';

describe('RevisionHistoryPanel Component (Section 35 & 38)', () => {
  const mockEntries: RevisionHistoryEntry[] = [
    {
      problem_id: 'prob_1',
      semantic_revision_hash: 'hash_coeff_edit_1234567890',
      problem_type: 'QUADRATIC',
      classification: 'REAL_DISTINCT_ROOTS',
      equation_latex: 'x^2 - 5x + 7 = 0',
      source_mode: 'COEFFICIENTS',
      timestamp_frontend_received: '2026-10-02T01:00:00Z',
      a: { numerator: 1, denominator: 1 },
      b: { numerator: -5, denominator: 1 },
      c: { numerator: 7, denominator: 1 },
    },
    {
      problem_id: 'prob_2',
      semantic_revision_hash: 'hash_raw_solve_0987654321',
      problem_type: 'DEGENERATE',
      classification: 'LINEAR_UNIQUE_ROOT',
      equation_latex: '2x - 4 = 0',
      source_mode: 'RAW_TEXT',
      timestamp_frontend_received: '2026-10-02T00:55:00Z',
      b: { numerator: 2, denominator: 1 },
      c: { numerator: -4, denominator: 1 },
    },
  ];

  it('renders empty state message when history list is empty', () => {
    render(
      <PreferencesProvider>
        <RevisionHistoryPanel history={[]} />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('revision-history-panel')).toBeInTheDocument();
    expect(screen.getByTestId('revision-history-empty')).toBeInTheDocument();
    expect(screen.getByTestId('revision-history-count')).toHaveTextContent('0');
  });

  it('renders history items with provenance badges, problem classification, and equation', () => {
    const handleRestore = vi.fn();

    render(
      <PreferencesProvider>
        <RevisionHistoryPanel history={mockEntries} onRestoreRevision={handleRestore} />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('revision-history-count')).toHaveTextContent('2');
    const items = screen.getAllByTestId('revision-history-item');
    expect(items).toHaveLength(2);

    // Verify first item (COEFFICIENTS mode)
    expect(items[0]).toHaveTextContent('QUADRATIC');
    expect(items[0]).toHaveTextContent('REAL_DISTINCT_ROOTS');

    // Verify restore button interaction
    const restoreBtn = screen.getByTestId('restore-revision-button-0');
    fireEvent.click(restoreBtn);
    expect(handleRestore).toHaveBeenCalledWith(mockEntries[0]);
  });
});
