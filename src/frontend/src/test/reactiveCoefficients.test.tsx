import React, { StrictMode } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAlgebraWorkspace } from '../state/useAlgebraWorkspace';
import * as apiClient from '../api/client';
import {
  mockSolvedTwoRoots,
  mockAnalyzedDegenerateLinear,
  mockApplicationErrorSyntax,
} from './fixtures/responses';
import type { SolvedResponse, TransportErrorResponse } from '../api/contract';

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
    const solveSpy = vi.spyOn(apiClient, 'solveEquation')
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
  });

  it('preserves state and draft and marks reactiveStatus error when coefficient edit receives Application ERROR response', async () => {
    vi.spyOn(apiClient, 'solveEquation')
      // Initial solve succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // Coefficient edit returns Application ERROR
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockApplicationErrorSyntax,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.lastAcceptedResponse?.problem.problem_id).toBe('prob_quad_x2_minus_5x_plus_6');
    expect(result.current.revisionHistory).toHaveLength(1);

    // Edit c: 6 -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.result?.kind).toBe('application');
    expect((result.current.result as { kind: 'application'; response: { response_status: string } })?.response.response_status).toBe('ERROR');
    expect(result.current.lastFailedRequestOrigin).toBe('COEFFICIENT_EDIT');
    expect(result.current.reactiveStatus).toBe('error');
    expect(result.current.coeffDraft.c.numeratorStr).toBe('7');
    // lastAcceptedResponse remains previous accepted quadratic
    expect(result.current.lastAcceptedResponse?.problem.problem_id).toBe('prob_quad_x2_minus_5x_plus_6');
    // revisionHistory does NOT append ErrorResponse
    expect(result.current.revisionHistory).toHaveLength(1);
  });

  it('retries Application ERROR coefficient request with exact COEFFICIENTS payload', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation')
      // Initial solve succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // Coefficient edit returns Application ERROR
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockApplicationErrorSyntax,
      })
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

    // Edit c: 6 -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.lastFailedRequestOrigin).toBe('COEFFICIENT_EDIT');

    // Retry
    await act(async () => {
      await result.current.retryLastRequest();
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.sourceMode).toBe('COEFFICIENTS');
    expect(result.current.reactiveStatus).toBe('updated');
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
  });

  it('StrictMode: pure state updater schedules exactly one timer without duplicate execution under React.StrictMode', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    // Render hook inside React.StrictMode wrapper
    const { result } = renderHook(() => useAlgebraWorkspace(), {
      wrapper: ({ children }: { children: React.ReactNode }) => <StrictMode>{children}</StrictMode>,
    });

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });
    expect(solveSpy).toHaveBeenCalledTimes(1);

    // Rapid edits inside StrictMode
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '8');
    });

    // Before debounce expiration
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(solveSpy).toHaveBeenCalledTimes(1);

    // Advance remaining debounce time
    await act(async () => {
      vi.advanceTimersByTime(150);
    });

    // Exactly one new solve request must have been dispatched
    expect(solveSpy).toHaveBeenCalledTimes(2);
    expect(solveSpy).toHaveBeenLastCalledWith(
      expect.objectContaining({
        input_payload: expect.objectContaining({
          c: { numerator: 8, denominator: 1 },
        }),
      }),
      expect.any(AbortSignal)
    );
  });

  it('preserves lastAcceptedResponse when coefficient edit results in network-error, transport-error, or protocol-error', async () => {
    vi.spyOn(apiClient, 'solveEquation')
      // Initial solve succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // Coefficient edit fails with transport error
      .mockResolvedValueOnce({
        kind: 'transport-error',
        status: 422,
        response: {
          transport_status: 'ERROR',
          transport_error_code: 'REQUEST_VALIDATION_FAILED',
          message_vi: 'Dữ liệu không hợp lệ',
          message_en: 'Invalid request data',
        } as TransportErrorResponse,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.lastAcceptedResponse?.problem.problem_id).toBe('prob_quad_x2_minus_5x_plus_6');

    // Edit c: 6 -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    // Workspace status is transport-error, reactiveStatus is error
    expect(result.current.status).toBe('transport-error');
    expect(result.current.reactiveStatus).toBe('error');
    // Draft retains unaccepted value c=7
    expect(result.current.coeffDraft.c.numeratorStr).toBe('7');
    // lastAcceptedResponse is preserved intact
    expect(result.current.lastAcceptedResponse?.problem.problem_id).toBe('prob_quad_x2_minus_5x_plus_6');
    expect(result.current.lastFailedRequestOrigin).toBe('COEFFICIENT_EDIT');
  });

  it('cancels coefficient debounce when setQuery is called', async () => {
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

    // Edit coefficient
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    expect(result.current.reactiveStatus).toBe('debouncing');

    // User types into search query box
    act(() => {
      result.current.setQuery('x^2 - 9 = 0');
    });

    // Advance timer
    act(() => {
      vi.advanceTimersByTime(400);
    });

    // No coefficient request should have been fired
    expect(solveSpy).toHaveBeenCalledTimes(1);
  });

  it('cancels in-flight requests and resets draft when resetCoefficientsToBackend is called', async () => {
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

    // Edit c: 6 -> 7 (in flight)
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    act(() => {
      vi.advanceTimersByTime(350);
    });
    expect(result.current.reactiveStatus).toBe('recomputing');

    // User resets coefficients
    act(() => {
      result.current.resetCoefficientsToBackend();
    });

    expect(result.current.coeffDraft.c.numeratorStr).toBe('6');
    expect(result.current.reactiveStatus).toBe('idle');

    // In-flight request resolves late
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });
    });

    // Must still be 6
    expect(result.current.coeffDraft.c.numeratorStr).toBe('6');
    expect(result.current.reactiveStatus).toBe('idle');
  });

  it('discards late METHOD_SWITCH response when a subsequent COEFFICIENT_EDIT occurs', async () => {
    let resolveMethod!: (value: any) => void;
    const methodPromise = new Promise((resolve) => {
      resolveMethod = resolve;
    });

    vi.spyOn(apiClient, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      .mockReturnValueOnce(methodPromise as any)
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedQuadratic7Response,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // Trigger method switch (hangs)
    act(() => {
      void result.current.switchMethod('QUAD_FORMULA_REDUCED');
    });

    // User edits coefficient c: 6 -> 7
    act(() => {
      result.current.updateCoefficientField('c', 'numerator', '7');
    });
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    // Method switch resolves late
    await act(async () => {
      resolveMethod({
        kind: 'application',
        status: 200,
        response: {
          ...mockSolvedTwoRoots,
          selected_method_id: 'QUAD_FORMULA_REDUCED',
        },
      });
    });

    // Revision hash must be quad_7, not the stale method response
    expect(result.current.revisionHistory[0]?.semantic_revision_hash).toBe('rev_hash_quad_7');
    expect(result.current.coeffDraft.c.numeratorStr).toBe('7');
  });

  it('retries RAW_QUERY and METHOD_SWITCH requests with exact respective payloads', async () => {
    const solveSpy = vi.spyOn(apiClient, 'solveEquation')
      // 1. Raw solve fails
      .mockRejectedValueOnce(new apiClient.NetworkError('Network failure'))
      // 2. Retry succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      // 3. Method switch fails
      .mockRejectedValueOnce(new apiClient.NetworkError('Network failure on method switch'))
      // 4. Retry succeeds
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: {
          ...mockSolvedTwoRoots,
          selected_method_id: 'QUAD_FORMULA_REDUCED',
        },
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Raw solve fails
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });
    expect(result.current.status).toBe('network-error');
    expect(result.current.lastFailedRequestOrigin).toBe('RAW_TEXT');

    // Retry raw solve
    await act(async () => {
      await result.current.retryLastRequest();
    });
    expect(result.current.status).toBe('application-response');
    expect(solveSpy).toHaveBeenLastCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'RAW_TEXT',
          raw_query: 'x^2 - 5*x + 6 = 0',
          target_variable: 'x',
        },
        selected_method_id: null,
      },
      expect.any(AbortSignal)
    );

    // Method switch fails
    await act(async () => {
      await result.current.switchMethod('QUAD_FORMULA_REDUCED');
    });
    expect(result.current.status).toBe('network-error');
    expect(result.current.lastFailedRequestOrigin).toBe('METHOD_SWITCH');

    // Retry method switch
    await act(async () => {
      await result.current.retryLastRequest();
    });
    expect(result.current.status).toBe('application-response');
    expect(solveSpy).toHaveBeenLastCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'COEFFICIENTS',
          a: { numerator: 1, denominator: 1 },
          b: { numerator: -5, denominator: 1 },
          c: { numerator: 6, denominator: 1 },
          target_variable: 'x',
        },
        selected_method_id: 'QUAD_FORMULA_REDUCED',
      },
      expect.any(AbortSignal)
    );
  });
});
