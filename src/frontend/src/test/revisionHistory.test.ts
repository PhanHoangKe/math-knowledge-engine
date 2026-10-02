import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAlgebraWorkspace } from '../state/useAlgebraWorkspace';
import * as apiClient from '../api/client';
import { mockSolvedTwoRoots } from './fixtures/responses';
import type { SolvedResponse } from '../api/contract';

describe('Bounded In-Memory Session Revision History via useAlgebraWorkspace (Sections 7, 8, 9)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const createMockSolvedResponse = (hash: string, eqLatex: string, cNum: number): SolvedResponse => ({
    ...mockSolvedTwoRoots,
    problem: {
      ...mockSolvedTwoRoots.problem,
      problem_id: `prob_${hash}`,
      equation_latex: eqLatex,
      semantic_revision_hash: hash,
      c: { numerator: cNum, denominator: 1 },
    },
  });

  it('records distinct revisions, preserves deduplication on identical hash and method switches', async () => {
    const respA = createMockSolvedResponse('hash_A', 'x^2 - 5x + 6 = 0', 6);
    const respB = createMockSolvedResponse('hash_B', 'x^2 - 5x + 7 = 0', 7);

    const solveSpy = vi.spyOn(apiClient, 'solveEquation');

    const { result } = renderHook(() => useAlgebraWorkspace());

    // A. Raw solve hash A -> exactly 1 entry
    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: respA,
    });
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.revisionHistory).toHaveLength(1);
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('hash_A');
    expect(result.current.revisionHistory[0]?.source_mode).toBe('RAW_TEXT');

    // B. Coefficient edit hash B -> exactly 2 entries
    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: respB,
    });
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.revisionHistory).toHaveLength(2);
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('hash_B');
    expect(result.current.revisionHistory[0]?.source_mode).toBe('COEFFICIENTS');
    expect(result.current.revisionHistory[1]?.semantic_revision_hash).toBe('hash_A');

    // C. Method switch on hash B -> still exactly 2 entries
    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: {
        ...respB,
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      },
    });
    await act(async () => {
      await result.current.switchMethod('QUAD_FORMULA_REDUCED');
    });

    expect(result.current.revisionHistory).toHaveLength(2);
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('hash_B');

    // D. Return to hash A again (A -> B -> A) -> does not create duplicate A in history!
    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: respA,
    });
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '6');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.revisionHistory).toHaveLength(2);
  });

  it('strictly bounds session history to a maximum of 15 entries through the hook', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation');
    const { result } = renderHook(() => useAlgebraWorkspace());

    // Generate 20 distinct backend problem responses
    for (let i = 1; i <= 20; i++) {
      const resp = createMockSolvedResponse(`hash_rev_${i}`, `x^2 - 5x + ${i} = 0`, i);
      solveSpy.mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: resp,
      });

      act(() => {
        result.current.updateCoefficientField('c', 'numerator', String(i));
      });
      await act(async () => {
        vi.advanceTimersByTime(350);
      });
    }

    // Exactly 15 entries retained, newest first
    expect(result.current.revisionHistory).toHaveLength(15);
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('hash_rev_20');
    expect(result.current.revisionHistory[14]?.semantic_revision_hash).toBe('hash_rev_6');
  });
});
