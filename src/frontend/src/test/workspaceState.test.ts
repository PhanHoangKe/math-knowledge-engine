import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAlgebraWorkspace } from '../state/useAlgebraWorkspace';
import * as clientModule from '../api/client';
import {
  mockSolvedTwoRoots,
  mockAnalyzedMethodNotExecutable,
} from './fixtures/responses';
import type { ApiSolveResult } from '../api/client';

describe('useAlgebraWorkspace State Management Hook', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes in idle state with empty query and null result', () => {
    const { result } = renderHook(() => useAlgebraWorkspace());
    expect(result.current.status).toBe('idle');
    expect(result.current.query).toBe('');
    expect(result.current.result).toBeNull();
    expect(result.current.currentQuadraticProblem).toBeNull();
  });

  it('submits raw equation query and transitions to application-response on success', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    act(() => {
      result.current.setQuery('x^2 - 5*x + 6 = 0');
    });

    await act(async () => {
      await result.current.submitRawSolve();
    });

    expect(solveSpy).toHaveBeenCalledWith(
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

    expect(result.current.status).toBe('application-response');
    expect(result.current.result?.kind).toBe('application');
    expect(result.current.currentQuadraticProblem?.classification).toBe('QUADRATIC');
  });

  it('immediately resets result to idle when query text is edited (Section 9 / 31.R)', async () => {
    vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.status).toBe('application-response');
    expect(result.current.result).not.toBeNull();

    // User edits query
    act(() => {
      result.current.setQuery('x^2 - 5*x + 7 = 0');
    });

    // Previous result must be cleared immediately
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
  });

  it('switches method using EXACT backend coefficients without client recalculation (Section 17 / 31.H)', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation')
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      })
      .mockResolvedValueOnce({
        kind: 'application',
        status: 200,
        response: mockAnalyzedMethodNotExecutable,
      });

    const { result } = renderHook(() => useAlgebraWorkspace());

    // 1. Initial Solve
    await act(async () => {
      await result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // 2. Switch Method using real method ID QUAD_COMPLETE_SQUARE
    await act(async () => {
      await result.current.switchMethod('QUAD_COMPLETE_SQUARE');
    });

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
        selected_method_id: 'QUAD_COMPLETE_SQUARE',
      },
      expect.any(AbortSignal)
    );

    expect(result.current.result?.kind).toBe('application');
    if (result.current.result?.kind === 'application') {
      expect(result.current.result.response.response_status).toBe('ANALYZED_NO_EXECUTION');
    }
  });

  it('preserves exact raw query text including leading and trailing whitespace', async () => {
    const solveSpy = vi.spyOn(clientModule, 'solveEquation').mockResolvedValue({
      kind: 'application',
      status: 200,
      response: mockSolvedTwoRoots,
    });

    const { result } = renderHook(() => useAlgebraWorkspace());

    const untrimmedQuery = '   x^2 - 5*x + 6 = 0   ';
    await act(async () => {
      await result.current.submitRawSolve(untrimmedQuery);
    });

    expect(solveSpy).toHaveBeenCalledWith(
      {
        schema_version: '1.0.0',
        input_payload: {
          input_mode: 'RAW_TEXT',
          raw_query: untrimmedQuery, // Sent verbatim without trim
          target_variable: 'x',
        },
        selected_method_id: null,
      },
      expect.any(AbortSignal)
    );
  });

  it('invalidates sequence on query edit so in-flight request that ignores AbortSignal cannot overwrite cleared state (Section 4)', async () => {
    let resolveA!: (value: ApiSolveResult) => void;
    const promiseA = new Promise<ApiSolveResult>((res) => {
      resolveA = res;
    });

    vi.spyOn(clientModule, 'solveEquation').mockImplementationOnce(() => promiseA);

    const { result } = renderHook(() => useAlgebraWorkspace());

    // 1. Request A starts
    let solvePromiseA: Promise<void>;
    act(() => {
      solvePromiseA = result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.status).toBe('loading');

    // 2. User edits query while A is still in-flight
    act(() => {
      result.current.setQuery('x^2 + 2*x + 1 = 0');
    });

    expect(result.current.query).toBe('x^2 + 2*x + 1 = 0');
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
    expect(result.current.httpStatus).toBeNull();

    // 3. Request A resolves (simulating fetch ignoring abort)
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      });
      await solvePromiseA;
    });

    // 4. Stale response A MUST NOT overwrite cleared workspace state
    expect(result.current.query).toBe('x^2 + 2*x + 1 = 0');
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
    expect(result.current.httpStatus).toBeNull();
  });

  it('invalidates sequence on clearWorkspace so in-flight request cannot restore old result (Section 5)', async () => {
    let resolveA!: (value: ApiSolveResult) => void;
    const promiseA = new Promise<ApiSolveResult>((res) => {
      resolveA = res;
    });

    vi.spyOn(clientModule, 'solveEquation').mockImplementationOnce(() => promiseA);

    const { result } = renderHook(() => useAlgebraWorkspace());

    // 1. Request A starts
    let solvePromiseA: Promise<void>;
    act(() => {
      solvePromiseA = result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    expect(result.current.status).toBe('loading');

    // 2. User clears workspace
    act(() => {
      result.current.clearWorkspace();
    });

    expect(result.current.query).toBe('');
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();

    // 3. Request A resolves later while ignoring abort
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      });
      await solvePromiseA;
    });

    // 4. Workspace remains cleared
    expect(result.current.query).toBe('');
    expect(result.current.status).toBe('idle');
    expect(result.current.result).toBeNull();
  });

  it('guarantees newer request B supersedes delayed older request A (Section 6 / Section 33)', async () => {
    let resolveA!: (value: ApiSolveResult) => void;
    let resolveB!: (value: ApiSolveResult) => void;

    const promiseA = new Promise<ApiSolveResult>((res) => {
      resolveA = res;
    });
    const promiseB = new Promise<ApiSolveResult>((res) => {
      resolveB = res;
    });

    vi.spyOn(clientModule, 'solveEquation')
      .mockImplementationOnce(() => promiseA)
      .mockImplementationOnce(() => promiseB);

    const { result } = renderHook(() => useAlgebraWorkspace());

    // Start Request A
    let solvePromiseA: Promise<void>;
    act(() => {
      solvePromiseA = result.current.submitRawSolve('x^2 - 5*x + 6 = 0');
    });

    // Start Request B later
    let solvePromiseB: Promise<void>;
    act(() => {
      solvePromiseB = result.current.submitRawSolve('x^2 - 4*x + 4 = 0');
    });

    // Complete B first
    await act(async () => {
      resolveB({
        kind: 'application',
        status: 200,
        response: {
          ...mockSolvedTwoRoots,
          problem: {
            ...mockSolvedTwoRoots.problem,
            equation_latex: 'x^2 - 4x + 4 = 0',
          },
        },
      });
      await solvePromiseB;
    });

    expect(result.current.result?.kind).toBe('application');
    if (result.current.result?.kind === 'application' && result.current.result.response.response_status !== 'ERROR') {
      expect(result.current.result.response.problem.equation_latex).toBe('x^2 - 4x + 4 = 0');
    }

    // Complete A later
    await act(async () => {
      resolveA({
        kind: 'application',
        status: 200,
        response: mockSolvedTwoRoots,
      });
      await solvePromiseA;
    });

    // Workspace state MUST remain B
    expect(result.current.result?.kind).toBe('application');
    if (result.current.result?.kind === 'application' && result.current.result.response.response_status !== 'ERROR') {
      expect(result.current.result.response.problem.equation_latex).toBe('x^2 - 4x + 4 = 0');
    }
  });
});
