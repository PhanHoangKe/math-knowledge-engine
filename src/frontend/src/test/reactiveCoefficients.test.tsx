import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAlgebraWorkspace } from '../state/useAlgebraWorkspace';
import * as apiClient from '../api/client';
import {
  mockSolvedTwoRoots,
  mockAnalyzedDegenerateLinear,
} from './fixtures/responses';
import type { SolvedResponse } from '../api/contract';

describe('Reactive Coefficients & Revision Flow (Sections 2-17, 20)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const mockSolvedQuadratic7Response: SolvedResponse = {
    ...mockSolvedTwoRoots,
    problem: {
      ...mockSolvedTwoRoots.problem,
      problem_id: 'prob_quad_7',
      equation_latex: 'x^2 - 5x + 7 = 0',
      semantic_revision_hash: 'rev_hash_quad_7',
      a: { numerator: 1, denominator: 1 },
      b: { numerator: -5, denominator: 1 },
      c: { numerator: 7, denominator: 1 },
    },
  };

  const mockSolvedQuadratic8Response: SolvedResponse = {
    ...mockSolvedTwoRoots,
    problem: {
      ...mockSolvedTwoRoots.problem,
      problem_id: 'prob_quad_8',
      equation_latex: 'x^2 - 5x + 8 = 0',
      semantic_revision_hash: 'rev_hash_quad_8',
      a: { numerator: 1, denominator: 1 },
      b: { numerator: -5, denominator: 1 },
      c: { numerator: 8, denominator: 1 },
    },
  };

  const mockSolvedFractionalResponse: SolvedResponse = {
    ...mockSolvedTwoRoots,
    problem: {
      ...mockSolvedTwoRoots.problem,
      problem_id: 'prob_quad_frac',
      equation_latex: '\\frac{1}{2}x^2 - \\frac{5}{2}x + 3 = 0',
      semantic_revision_hash: 'rev_hash_frac_1',
      a: { numerator: 1, denominator: 2 },
      b: { numerator: -5, denominator: 2 },
      c: { numerator: 3, denominator: 1 },
    },
  };

  it('c=6 -> 7 acceptance: hydrates from raw solve, edits ONLY c numerator, and sends exact COEFFICIENTS payload', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // 1. Initial raw solve hydrates: a=1/1, b=-5/1, c=6/1
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.coeffDraft.a).toEqual({ numeratorStr: '1', denominatorStr: '1' });
    expect(result.current.coeffDraft.b).toEqual({ numeratorStr: '-5', denominatorStr: '1' });
    expect(result.current.coeffDraft.c).toEqual({ numeratorStr: '6', denominatorStr: '1' });

    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: mockSolvedQuadratic7Response,
    });

    // 2. User edits ONLY c numerator from 6 to 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });

    expect(result.current.reactiveStatus).toBe('debouncing');

    // 3. Fast-forward 350ms debounce
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    // Request MUST be exact COEFFICIENTS with selected_method_id: null
    expect(solveSpy).toHaveBeenLastCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: -5, denominator: 1 },
          c: { numerator: 7, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: null,
      },
      expect.any(AbortSignal)
    );

    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    expect(result.current.reactiveStatus).toBe('updated');
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_quad_7');
  });

  it('stale in-flight request A does NOT overwrite newer draft B or pollute state', async () => {
    let resolveA!: (value: any) => void;
    const promiseA = new Promise((resolve) => {
      resolveA = resolve;
    });

    vi.spyOn(apiClient, 'solveEquation')
      // First solve to hydrate workspace
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // Request A hangs
      .mockReturnValueOnce(promiseA as any)
      // Request B resolves immediately
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic8Response,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // Edit A: c -> 7 (fires request A after 350ms)
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.reactiveStatus).toBe('recomputing');

    // Edit B: c -> 8 (before A resolves)
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '8');
    });
    expect(result.current.coeffDraft.c.numeratorStr).toBe('8');
    expect(result.current.reactiveStatus).toBe('debouncing');

    // Request A resolves late ignoring abort
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });
    });

    // A MUST NOT overwrite B draft or append hash 7
    expect(result.current.coeffDraft.c.numeratorStr).toBe('8');
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_abc123'); // Still the initial hash

    // Now advance B debounce timer
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    // B response is authoritative
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_quad_8');
    expect(result.current.coeffDraft.c.numeratorStr).toBe('8');
  });

  it('invalid coefficient edit immediately invalidates in-flight request and leaves draft invalid', async () => {
    let resolveA!: (value: any) => void;
    const promiseA = new Promise((resolve) => {
      resolveA = resolve;
    });

    vi.spyOn(apiClient, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      .mockReturnValueOnce(promiseA as any);

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // Edit A: c -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.reactiveStatus).toBe('recomputing');

    // User changes denominator to invalid "0"
    act(() => {
      result.current.updateCoefficientField('c', 'denominator', '0');
    });

    expect(result.current.reactiveStatus).toBe('invalid');
    expect(result.current.coeffValidationErrors.c_denominator).toBe('err_coeff_denominator_positive');

    // A resolves late
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });
    });

    // Draft remains invalid user draft, A is discarded
    expect(result.current.coeffDraft.c.denominatorStr).toBe('0');
    expect(result.current.reactiveStatus).toBe('invalid');
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_abc123');
  });

  it('preserves sourceMode = COEFFICIENTS and uses newest backend coefficients upon METHOD_SWITCH', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });
    expect(result.current.sourceMode).toBe('RAW_TEXT');

    // Edit c: 6 -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    expect(result.current.revisionHistory).toHaveLength(2);

    solveSpy.mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: {
        ...mockSolvedQuadratic7Response,
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      },
    });

    // Method switch
    await act(async () => {
      await result.current.switchMethod('QUAD_FORMULA_REDUCED');
    });

    // Method switch MUST send newest backend coefficients (c=7)
    expect(solveSpy).toHaveBeenLastCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: -5, denominator: 1 },
          c: { numerator: 7, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      },
      expect.any(AbortSignal)
    );

    // Source mode MUST remain COEFFICIENTS
    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    // History count does NOT increase for identical semantic revision hash
    expect(result.current.revisionHistory).toHaveLength(2);
  });

  it('restarts debounce on rapid keystrokes (6 -> 7 -> 8 -> 9) sending ONLY one final request', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });
    expect(solveSpy).toHaveBeenCalledTimes(1);

    // Rapid edits
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '8');
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '9');
    });

    // Before 350ms from last edit
    act(() => {
      vi.advanceTimersByTime(349);
    });
    expect(solveSpy).toHaveBeenCalledTimes(1); // No new request yet

    // Complete 350ms for last edit
    await act(async () => {
      vi.advanceTimersByTime(1);
    });

    expect(solveSpy).toHaveBeenCalledTimes(2);
    expect(solveSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        input_payload: expect.objectContaining({
          c: { numerator: 9, denominator: 1 },
        }),
      }),
      expect.any(AbortSignal)
    );
  });

  it('transmits exact unreduced fractional payload (a=1/2, b=-5/2, c=3/1)', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedFractionalResponse,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    act(() => {
      result.current.updateCoefficientField('a', 'numerator', '1');
      result.current.updateCoefficientField('a', 'denominator', '2');
      result.current.updateCoefficientField('b', 'numerator', '-5');
      result.current.updateCoefficientField('b', 'denominator', '2');
      result.current.updateCoefficientField('c', 'numerator', '3');
      result.current.updateCoefficientField('c', 'denominator', '1');
    });

    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(solveSpy).toHaveBeenCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 2 },
          b: { numerator: -5, denominator: 2 },
          c: { numerator: 3, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: null,
      },
      expect.any(AbortSignal)
    );
  });

  it('transitions Degenerate -> Quadratic seamlessly when editing a numerator from 0 to 1', async () => {
    vi.spyOn(apiClient, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockAnalyzedDegenerateLinear,
      })
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // 1. Initial degenerate state
    await act(async () => {
      await result.current.submitRawSolve('2*x - 4 = 0');
    });

    expect(result.current.currentProblem?.problem_type).toBe('DEGENERATE');
    expect(result.current.currentQuadraticProblem).toBeNull();

    // 2. User edits a numerator to 1
    act(() => {
      result.current.updateCoefficientField('a', 'numerator', '1');
    });

    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.currentProblem?.problem_type).toBe('QUADRATIC');
    expect(result.current.currentQuadraticProblem).not.toBeNull();
  });

  it('handles race conditions: RAW_TEXT submit supersedes in-flight coefficient edit', async () => {
    let resolveCoeff!: (value: any) => void;
    const coeffPromise = new Promise((resolve) => {
      resolveCoeff = resolve;
    });

    vi.spyOn(apiClient, 'solveEquation')
      .mockReturnValueOnce(coeffPromise as any)
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Trigger coefficient edit
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(350);
    });
    expect(result.current.reactiveStatus).toBe('recomputing');

    // Raw text submit occurs while coefficient solve is in flight
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.sourceMode).toBe('RAW_TEXT');

    // In-flight coefficient promise resolves late
    await act(async () => {
      resolveCoeff({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });
    });

    // Raw result remains authoritative
    expect(result.current.sourceMode).toBe('RAW_TEXT');
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_abc123');
  });

  it('cancels pending debounce on clearWorkspace, setQuery, and unmount', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result, unmount } = renderHook(() => useAlgebraWorkspace());

    // Test clearWorkspace cancellation
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    expect(result.current.reactiveStatus).toBe('debouncing');
    act(() => {
      result.current.clearWorkspace();
    });
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(solveSpy).not.toHaveBeenCalled();

    // Test unmount cancellation
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '8');
    });
    expect(result.current.reactiveStatus).toBe('debouncing');
    unmount();
    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(solveSpy).not.toHaveBeenCalled();
  });

  it('retries failed requests with exact original provenance', async () => {
    vi.spyOn(apiClient, 'solveEquation')
      // First solve succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // Coefficient edit fails with network error
      .mockRejectedValueOnce(new apiClient.NetworkError('Failed to fetch'))
      // Retry succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // Coefficient edit fails
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.status).toBe('network-error');
    expect(result.current.reactiveStatus).toBe('error');
    expect(result.current.lastFailedRequestOrigin).toBe('COEFFICIENT_EDIT');

    // Retry
    await act(async () => {
      await result.current.retryLastRequest();
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    expect(result.current.reactiveStatus).toBe('updated');
  });
});
