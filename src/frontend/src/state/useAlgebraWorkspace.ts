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
  CanonicalDegenerateProblemView,
  SolvedResponse,
  AnalyzedNoExecutionResponse,
  RationalFraction,
} from '../api/contract';
import {
  type CoefficientsDraft,
  type CoefficientsValidationErrors,
  COEFFICIENT_EDIT_DEBOUNCE_MS,
  validateCoefficientsDraft,
  draftToRationalPayload,
  hydrateDraftFromBackend,
} from '../utils/coefficients';

export type WorkspaceStatus =
  | 'idle'
  | 'loading'
  | 'application-response'
  | 'transport-error'
  | 'network-error'
  | 'protocol-error';

export type RequestOrigin = 'RAW_TEXT' | 'COEFFICIENT_EDIT' | 'METHOD_SWITCH';
export type WorkspaceSourceMode = 'RAW_TEXT' | 'COEFFICIENTS';
export type ReactiveCoeffStatus =
  | 'idle'
  | 'debouncing'
  | 'recomputing'
  | 'invalid'
  | 'updated'
  | 'error';

export interface RevisionHistoryEntry {
  problem_id: string;
  semantic_revision_hash: string;
  problem_type: 'QUADRATIC' | 'DEGENERATE';
  classification: string;
  equation_latex: string;
  source_mode: WorkspaceSourceMode;
  timestamp_frontend_received: string;
  a?: RationalFraction;
  b: RationalFraction;
  c: RationalFraction;
}

export interface UseAlgebraWorkspaceReturn {
  query: string;
  setQuery: (newQuery: string) => void;
  status: WorkspaceStatus;
  result: ApiSolveResult | null;
  httpStatus: number | null;
  sourceMode: WorkspaceSourceMode;
  coeffDraft: CoefficientsDraft;
  coeffValidationErrors: CoefficientsValidationErrors;
  reactiveStatus: ReactiveCoeffStatus;
  revisionHistory: RevisionHistoryEntry[];
  currentProblem: CanonicalQuadraticProblemView | CanonicalDegenerateProblemView | null;
  currentQuadraticProblem: CanonicalQuadraticProblemView | null;
  lastFailedRequestOrigin: RequestOrigin | null;
  updateCoefficientField: (coeff: 'a' | 'b' | 'c', part: 'numerator' | 'denominator', value: string) => void;
  resetCoefficientsToBackend: () => void;
  submitRawSolve: (overrideQuery?: string) => Promise<void>;
  switchMethod: (methodId: string) => Promise<void>;
  retryLastRequest: () => Promise<void>;
  clearWorkspace: () => void;
}

const INITIAL_COEFF_DRAFT: CoefficientsDraft = {
  a: { numeratorStr: '1', denominatorStr: '1' },
  b: { numeratorStr: '0', denominatorStr: '1' },
  c: { numeratorStr: '0', denominatorStr: '1' },
};

/**
 * Custom React Hook managing the live deterministic algebra workspace state,
 * reactive coefficient editing, request provenance, and session revision history.
 */
export function useAlgebraWorkspace(): UseAlgebraWorkspaceReturn {
  const [query, setQueryState] = useState<string>('');
  const [status, setStatus] = useState<WorkspaceStatus>('idle');
  const [result, setResult] = useState<ApiSolveResult | null>(null);
  const [httpStatus, setHttpStatus] = useState<number | null>(null);

  const [sourceMode, setSourceMode] = useState<WorkspaceSourceMode>('RAW_TEXT');
  const [coeffDraft, setCoeffDraft] = useState<CoefficientsDraft>(INITIAL_COEFF_DRAFT);
  const [coeffValidationErrors, setCoeffValidationErrors] = useState<CoefficientsValidationErrors>({});
  const [reactiveStatus, setReactiveStatus] = useState<ReactiveCoeffStatus>('idle');
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistoryEntry[]>([]);
  const [lastFailedRequest, setLastFailedRequest] = useState<{ origin: RequestOrigin; solveRequest: SolveRequest } | null>(null);

  const sequenceRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear debounce timer helper
  const cancelDebounce = useCallback(() => {
    if (debounceTimerRef.current !== null) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelDebounce();
      sequenceRef.current += 1;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [cancelDebounce]);

  /**
   * Update raw query text.
   * Invalidates sequence counter, aborts pending requests, cancels debounce,
   * and clears prior mathematical outcomes.
   */
  const setQuery = useCallback((newQuery: string) => {
    cancelDebounce();
    sequenceRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setQueryState(newQuery);
    setStatus('idle');
    setResult(null);
    setHttpStatus(null);
    setLastFailedRequest(null);
    setReactiveStatus('idle');
  }, [cancelDebounce]);

  /**
   * Clear entire workspace.
   */
  const clearWorkspace = useCallback(() => {
    cancelDebounce();
    sequenceRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setQueryState('');
    setStatus('idle');
    setResult(null);
    setHttpStatus(null);
    setLastFailedRequest(null);
    setReactiveStatus('idle');
    setSourceMode('RAW_TEXT');
    setCoeffDraft(INITIAL_COEFF_DRAFT);
    setCoeffValidationErrors({});
  }, [cancelDebounce]);

  /**
   * Internal executor with sequence guards and request provenance.
   */
  const executeSolve = useCallback(async (
    request: SolveRequest,
    origin: RequestOrigin
  ) => {
    cancelDebounce();

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

      if (currentSeq !== sequenceRef.current) {
        return;
      }

      setHttpStatus(solveResult.status);
      setResult(solveResult);

      if (solveResult.kind === 'application') {
        setStatus('application-response');
        setLastFailedRequest(null);

        const resp = solveResult.response;
        if (resp.response_status === 'SOLVED' || resp.response_status === 'ANALYZED_NO_EXECUTION') {
          const prob = resp.problem;

          // Freeze provenance semantics:
          // RAW_TEXT -> RAW_TEXT
          // COEFFICIENT_EDIT -> COEFFICIENTS
          // METHOD_SWITCH -> preserve current sourceMode
          if (origin === 'RAW_TEXT') {
            setSourceMode('RAW_TEXT');
          } else if (origin === 'COEFFICIENT_EDIT') {
            setSourceMode('COEFFICIENTS');
          }

          // Rehydrate draft from authoritative backend values
          if (prob.problem_type === 'QUADRATIC') {
            setCoeffDraft(hydrateDraftFromBackend(prob.a, prob.b, prob.c));
          } else {
            setCoeffDraft((prev) => ({
              a: prev.a.numeratorStr === '0' ? prev.a : { numeratorStr: '0', denominatorStr: '1' },
              b: { numeratorStr: String(prob.b.numerator), denominatorStr: String(prob.b.denominator) },
              c: { numeratorStr: String(prob.c.numerator), denominatorStr: String(prob.c.denominator) },
            }));
          }
          setCoeffValidationErrors({});
          setReactiveStatus('updated');

          // Record observational revision entry in bounded session history
          const newEntry: RevisionHistoryEntry = {
            problem_id: prob.problem_id,
            semantic_revision_hash: prob.semantic_revision_hash,
            problem_type: prob.problem_type,
            classification: prob.classification,
            equation_latex: prob.equation_latex,
            source_mode: origin === 'COEFFICIENT_EDIT' ? 'COEFFICIENTS' : origin === 'RAW_TEXT' ? 'RAW_TEXT' : sourceMode,
            timestamp_frontend_received: new Date().toISOString(),
            a: prob.problem_type === 'QUADRATIC' ? prob.a : undefined,
            b: prob.b,
            c: prob.c,
          };

          setRevisionHistory((prevHistory) => {
            // Deduplicate across entire session history using backend semantic_revision_hash
            if (prevHistory.some((entry) => entry.semantic_revision_hash === prob.semantic_revision_hash)) {
              return prevHistory;
            }
            return [newEntry, ...prevHistory.slice(0, 14)];
          });
        }
      } else {
        setStatus('transport-error');
        setLastFailedRequest({ origin, solveRequest: request });
        if (origin === 'COEFFICIENT_EDIT') {
          setReactiveStatus('error');
        }
      }
    } catch (err: unknown) {
      if (currentSeq !== sequenceRef.current) {
        return;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }

      setLastFailedRequest({ origin, solveRequest: request });
      if (origin === 'COEFFICIENT_EDIT') {
        setReactiveStatus('error');
      }

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
  }, [cancelDebounce, sourceMode]);

  /**
   * Submit raw mathematical query equation.
   */
  const submitRawSolve = useCallback(async (overrideQuery?: string) => {
    cancelDebounce();
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

    await executeSolve(request, 'RAW_TEXT');
  }, [query, executeSolve, cancelDebounce]);

  /**
   * Extract current active problem views from accepted response.
   */
  let currentProblem: CanonicalQuadraticProblemView | CanonicalDegenerateProblemView | null = null;
  let currentQuadraticProblem: CanonicalQuadraticProblemView | null = null;

  if (result && result.kind === 'application') {
    const resp = result.response;
    if (resp.response_status === 'SOLVED') {
      const solved = resp as SolvedResponse;
      currentProblem = solved.problem;
      if (solved.problem.problem_type === 'QUADRATIC') {
        currentQuadraticProblem = solved.problem;
      }
    } else if (resp.response_status === 'ANALYZED_NO_EXECUTION') {
      const analyzed = resp as AnalyzedNoExecutionResponse;
      currentProblem = analyzed.problem;
      if (analyzed.problem.problem_type === 'QUADRATIC') {
        currentQuadraticProblem = analyzed.problem;
      }
    }
  }

  /**
   * Update an individual coefficient input field with validation and debounced recomputation.
   * On EVERY edit:
   * - cancel pending debounce
   * - immediately increment sequenceRef.current
   * - abort in-flight request if present
   */
  const updateCoefficientField = useCallback((
    coeff: 'a' | 'b' | 'c',
    part: 'numerator' | 'denominator',
    value: string
  ) => {
    // 1. Cancel pending debounce
    cancelDebounce();

    // 2. Immediately increment sequence counter to invalidate ANY in-flight request
    sequenceRef.current += 1;

    // 3. Abort in-flight request if present
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setCoeffDraft((prev) => {
      const fieldKey = `${part}Str` as const;
      const nextCoeff = { ...prev[coeff], [fieldKey]: value };
      const nextDraft: CoefficientsDraft = { ...prev, [coeff]: nextCoeff };

      const { isValid, errors } = validateCoefficientsDraft(nextDraft);
      setCoeffValidationErrors(errors);

      if (!isValid) {
        setReactiveStatus('invalid');
        return nextDraft;
      }

      setReactiveStatus('debouncing');

      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null;
        setReactiveStatus('recomputing');
        const payload = draftToRationalPayload(nextDraft);
        if (!payload) {
          setReactiveStatus('invalid');
          return;
        }

        const solveRequest: SolveRequest = {
          schema_version: '1.0.0',
          input_payload: {
            input_mode: 'COEFFICIENTS',
            a: payload.a,
            b: payload.b,
            c: payload.c,
            target_variable: 'x',
          },
          selected_method_id: null, // Reset selected_method_id for fresh revision
        };
        executeSolve(solveRequest, 'COEFFICIENT_EDIT');
      }, COEFFICIENT_EDIT_DEBOUNCE_MS);

      return nextDraft;
    });
  }, [executeSolve, cancelDebounce]);

  /**
   * Reset coefficient drafts to current accepted backend canonical values.
   */
  const resetCoefficientsToBackend = useCallback(() => {
    cancelDebounce();
    if (!currentProblem) return;

    if (currentProblem.problem_type === 'QUADRATIC') {
      const freshDraft = hydrateDraftFromBackend(currentProblem.a, currentProblem.b, currentProblem.c);
      setCoeffDraft(freshDraft);
      setCoeffValidationErrors({});
      setReactiveStatus('idle');
    } else {
      const freshDraft: CoefficientsDraft = {
        a: { numeratorStr: '0', denominatorStr: '1' },
        b: { numeratorStr: String(currentProblem.b.numerator), denominatorStr: String(currentProblem.b.denominator) },
        c: { numeratorStr: String(currentProblem.c.numerator), denominatorStr: String(currentProblem.c.denominator) },
      };
      setCoeffDraft(freshDraft);
      setCoeffValidationErrors({});
      setReactiveStatus('idle');
    }
  }, [currentProblem, cancelDebounce]);

  /**
   * Switch method using newest backend canonical coefficients.
   */
  const switchMethod = useCallback(async (methodId: string) => {
    if (!currentQuadraticProblem) return;

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

    await executeSolve(request, 'METHOD_SWITCH');
  }, [currentQuadraticProblem, executeSolve]);

  /**
   * Retry the exact failed request according to its original provenance.
   */
  const retryLastRequest = useCallback(async () => {
    if (!lastFailedRequest) return;
    await executeSolve(lastFailedRequest.solveRequest, lastFailedRequest.origin);
  }, [lastFailedRequest, executeSolve]);

  return {
    query,
    setQuery,
    status,
    result,
    httpStatus,
    sourceMode,
    coeffDraft,
    coeffValidationErrors,
    reactiveStatus,
    revisionHistory,
    currentProblem,
    currentQuadraticProblem,
    lastFailedRequestOrigin: lastFailedRequest?.origin ?? null,
    updateCoefficientField,
    resetCoefficientsToBackend,
    submitRawSolve,
    switchMethod,
    retryLastRequest,
    clearWorkspace,
  };
}
