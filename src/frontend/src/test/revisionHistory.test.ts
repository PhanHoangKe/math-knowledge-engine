import { describe, it, expect } from 'vitest';
import type { RevisionHistoryEntry } from '../state/useAlgebraWorkspace';

describe('Bounded In-Memory Session Revision History (Section 35)', () => {
  function appendRevision(
    history: RevisionHistoryEntry[],
    newEntry: RevisionHistoryEntry,
    limit: number = 15
  ): RevisionHistoryEntry[] {
    if (history.length > 0 && history[0]?.semantic_revision_hash === newEntry.semantic_revision_hash) {
      return history;
    }
    return [newEntry, ...history.slice(0, limit - 1)];
  }

  const createEntry = (hash: string, eq: string, source: 'RAW_TEXT' | 'COEFFICIENTS'): RevisionHistoryEntry => ({
    problem_id: `prob_${hash}`,
    semantic_revision_hash: hash,
    problem_type: 'QUADRATIC',
    classification: 'REAL_DISTINCT_ROOTS',
    equation_latex: eq,
    source_mode: source,
    timestamp_frontend_received: new Date().toISOString(),
    a: { numerator: 1, denominator: 1 },
    b: { numerator: -5, denominator: 1 },
    c: { numerator: 6, denominator: 1 },
  });

  it('records distinct revisions and places newest first', () => {
    let history: RevisionHistoryEntry[] = [];

    const e1 = createEntry('hash1', 'x^2 - 5x + 6 = 0', 'RAW_TEXT');
    history = appendRevision(history, e1);
    expect(history).toHaveLength(1);
    expect(history[0]!.semantic_revision_hash).toBe('hash1');

    const e2 = createEntry('hash2', 'x^2 - 5x + 7 = 0', 'COEFFICIENTS');
    history = appendRevision(history, e2);
    expect(history).toHaveLength(2);
    expect(history[0]!.semantic_revision_hash).toBe('hash2');
    expect(history[1]!.semantic_revision_hash).toBe('hash1');
  });

  it('deduplicates consecutive responses having the exact same semantic revision hash', () => {
    let history: RevisionHistoryEntry[] = [];

    const e1 = createEntry('hash_identical', 'x^2 - 5x + 6 = 0', 'RAW_TEXT');
    history = appendRevision(history, e1);
    expect(history).toHaveLength(1);

    // Same hash again
    const e2 = createEntry('hash_identical', 'x^2 - 5x + 6 = 0', 'COEFFICIENTS');
    history = appendRevision(history, e2);
    expect(history).toHaveLength(1);
    expect(history[0]!.semantic_revision_hash).toBe('hash_identical');
  });

  it('strictly bounds revision history to a maximum of 15 entries (FIFO oldest drop)', () => {
    let history: RevisionHistoryEntry[] = [];

    for (let i = 1; i <= 20; i++) {
      const entry = createEntry(`hash_${i}`, `x^2 - 5x + ${i} = 0`, 'COEFFICIENTS');
      history = appendRevision(history, entry, 15);
    }

    expect(history).toHaveLength(15);
    expect(history[0]!.semantic_revision_hash).toBe('hash_20');
    expect(history[14]!.semantic_revision_hash).toBe('hash_6'); // 1..5 dropped
  });
});
