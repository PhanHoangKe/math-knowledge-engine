import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAlgebraWorkspace } from '../state/useAlgebraWorkspace';
import * as apiClient from '../api/client';
import { mockSolvedTwoRoots, mockAnalyzedDegenerateLinear } from './fixtures/responses';
import type { SolvedResponse } from '../api/contract';

describe('Reactive Coefficients & Revision Flow (Sections 25-30, 34-39)', () => {
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
      problem_id: 'prob_quad_2',
      equation_latex: 'x^2 - 5x + 7 = 0',
      semantic_revision_hash: 'hash_quad_7',
      c: { numerator: 7, denominator: 1 },
    },
  };

  it('debounces coefficient keystrokes (350ms) and resets selected_method_id to null', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedQuadratic7Response,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // User edits c numerator from 6 to 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });

    // Reactive status should be debouncing
    expect(result.current.reactiveStatus).toBe('debouncing');
    expect(solveSpy).not.toHaveBeenCalled();

    // Fast-forward timer by 349ms (still debouncing)
    act(() => {
      vi.advanceTimersByTime(349);
    });
    expect(solveSpy).not.toHaveBeenCalled();

    // Fast-forward by 1ms (hits 350ms)
    await act(async () => {
      vi.advanceTimersByTime(1);
    });

    // Solver spy must be called with COEFFICIENTS input_mode and selected_method_id: null
    expect(solveSpy).toHaveBeenCalledTimes(1);
    expect(solveSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: 0, denominator: 1 },
          c: { numerator: 7, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: null,
      }),
      expect.any(AbortSignal)
    );

    // After resolution
    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    expect(result.current.reactiveStatus).toBe('updated');
    expect(result.current.revisionHistory).toHaveLength(1);
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('hash_quad_7');
  });

  it('switches method preserving latest coefficients and passing selected_method_id', async () => {
    vi.spyOn(apiClient, 'solveEquation').mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Submit initial solve
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5x + 6 = 0');
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_abc123');

    const switchSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValueOnce({
      kind: 'application',
      status: 200,
      response: {
        ...mockSolvedTwoRoots,
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      },
    });

    // Switch method
    await act(async () => {
      await result.current.switchMethod('QUAD_FORMULA_REDUCED');
    });

    expect(switchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: -5, denominator: 1 },
          c: { numerator: 6, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      }),
      expect.any(AbortSignal)
    );
  });

  it('handles quadratic to degenerate transitions atomically', async () => {
    vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockAnalyzedDegenerateLinear,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Edit a numerator to 0 (Degenerate)
    act(() => {
      result.current.updateCoefficientField('a', 'numerator', '0');
      result.current.updateCoefficientField('b', 'numerator', '2');
      result.current.updateCoefficientField('c', 'numerator', '-4');
    });

    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.currentProblem?.problem_type).toBe('DEGENERATE');
    expect(result.current.revisionHistory[0]?.problem_type).toBe('DEGENERATE');
  });

  it('invalidates pending coefficient debounce on raw query text edit', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Start coefficient edit
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '9');
    });
    expect(result.current.reactiveStatus).toBe('debouncing');

    // Type into raw query box before debounce expires
    act(() => {
      result.current.setQuery('x^2 - 4 = 0');
    });

    // Advance past original debounce time
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    // Solve should NOT have been called for the cancelled coefficient debounce
    expect(solveSpy).not.toHaveBeenCalled();
  });
});
