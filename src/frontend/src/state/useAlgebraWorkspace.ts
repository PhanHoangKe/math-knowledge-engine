import { useState, useCallback, useRef, useEffect } from 'react';
import {
  solveEquation,
  type ApiSolveResult,
  NetworkError,
  ProtocolError,
} from '../api/client';
import type {
  SolveRequest,
  CanonicalQuadraticProblemView,
  SolvedResponse,
  AnalyzedNoExecutionResponse,
} from '../api/contract';

export type WorkspaceStatus =
  | 'idle'
  | 'loading'
  | 'application-response'
  | 'transport-error'
  | 'network-error'
  | 'protocol-error';

export interface UseAlgebraWorkspaceReturn {
  query: string;
  setQuery: (newQuery: string) => void;
  status: WorkspaceStatus;
  result: ApiSolveResult | null;
  httpStatus: number | null;
  submitRawSolve: (overrideQuery?: string) => Promise<void>;
  switchMethod: (methodId: string) => Promise<void>;
  clearWorkspace: () => void;
  currentQuadraticProblem: CanonicalQuadraticProblemView | null;
}

/**
 * Custom React Hook managing the live deterministic algebra workspace state.
 * Enforces race-condition guards (sequence counter + AbortController)
 * and stale result clearing upon query modification.
 */
export function useAlgebraWorkspace(): UseAlgebraWorkspaceReturn {
  const [query, setQueryState] = useState<string>('');
  const [status, setStatus] = useState<WorkspaceStatus>('idle');
  const [result, setResult] = useState<ApiSolveResult | null>(null);
  const [httpStatus, setHttpStatus] = useState<number | null>(null);

  const sequenceRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Abort pending request and invalidate sequence on unmount
  useEffect(() => {
    return () => {
      sequenceRef.current += 1;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  /**
   * Update query text.
   * Section 1 & 9: Invalidate sequence counter, abort in-flight request,
   * and reset workspace state on query modification.
   */
  const setQuery = useCallback((newQuery: string) => {
    sequenceRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setQueryState(newQuery);
    setStatus('idle');
    setResult(null);
    setHttpStatus(null);
  }, []);

  const clearWorkspace = useCallback(() => {
    sequenceRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setQueryState('');
    setStatus('idle');
    setResult(null);
    setHttpStatus(null);
  }, []);

  /**
   * Internal executor with sequence IDs and AbortController.
   */
  const executeSolve = useCallback(async (request: SolveRequest) => {
    // Cancel previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    const currentSeq = ++sequenceRef.current;

    setStatus('loading');

    try {
      const solveResult = await solveEquation(request, controller.signal);

      // Guard: only accept result if this request is still the latest
      if (currentSeq !== sequenceRef.current) {
        return;
      }

      setHttpStatus(solveResult.status);
      setResult(solveResult);
      if (solveResult.kind === 'application') {
        setStatus('application-response');
      } else {
        setStatus('transport-error');
      }
    } catch (err: unknown) {
      if (currentSeq !== sequenceRef.current) {
        return;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        // Silently ignore aborted requests
        return;
      }

      setResult(null);
      if (err instanceof ProtocolError) {
        setHttpStatus(err.status ?? null);
        setStatus('protocol-error');
      } else if (err instanceof NetworkError) {
        setHttpStatus(null);
        setStatus('network-error');
      } else {
        setHttpStatus(null);
        setStatus('network-error');
      }
    }
  }, []);

  /**
   * Submit raw mathematical query equation.
   * Section 12: Preserves verbatim user text (including spaces) without trimming raw_query.
   */
  const submitRawSolve = useCallback(async (overrideQuery?: string) => {
    const candidate = overrideQuery !== undefined ? overrideQuery : query;
    if (!candidate.trim()) return;

    if (overrideQuery !== undefined) {
      setQueryState(overrideQuery);
    }

    const request: SolveRequest = {
      schema_version: '1.0.0',
      input_payload: {
        input_mode: 'RAW_TEXT',
        raw_query: candidate,
        target_variable: 'x',
      },
      selected_method_id: null,
    };

    await executeSolve(request);
  }, [query, executeSolve]);

  /**
   * Extract current quadratic problem if available for method switching.
   */
  let currentQuadraticProblem: CanonicalQuadraticProblemView | null = null;
  if (result && result.kind === 'application') {
    const resp = result.response;
    if (resp.response_status === 'SOLVED') {
      const solved = resp as SolvedResponse;
      if (solved.problem.problem_type === 'QUADRATIC') {
        currentQuadraticProblem = solved.problem;
      }
    } else if (resp.response_status === 'ANALYZED_NO_EXECUTION') {
      const analyzed = resp as AnalyzedNoExecutionResponse;
      if (analyzed.problem.problem_type === 'QUADRATIC') {
        currentQuadraticProblem = analyzed.problem;
      }
    }
  }

  /**
   * Switch method using exact backend coefficients.
   */
  const switchMethod = useCallback(async (methodId: string) => {
    if (!currentQuadraticProblem) return;

    // Send COEFFICIENTS mode using EXACT backend numbers without client recalculation
    const request: SolveRequest = {
      schema_version: '1.0.0',
      input_payload: {
        input_mode: 'COEFFICIENTS',
        a: currentQuadraticProblem.a,
        b: currentQuadraticProblem.b,
        c: currentQuadraticProblem.c,
        target_variable: 'x',
      },
      selected_method_id: methodId,
    };

    await executeSolve(request);
  }, [currentQuadraticProblem, executeSolve]);

  return {
    query,
    setQuery,
    status,
    result,
    httpStatus,
    submitRawSolve,
    switchMethod,
    clearWorkspace,
    currentQuadraticProblem,
  };
}
