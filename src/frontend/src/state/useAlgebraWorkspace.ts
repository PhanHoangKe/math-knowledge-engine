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
  lastAcceptedResponse: SolvedResponse | AnalyzedNoExecutionResponse | null;
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
  const [lastAcceptedResponse, setLastAcceptedResponse] = useState<SolvedResponse | AnalyzedNoExecutionResponse | null>(null);
  const [lastFailedRequest, setLastFailedRequest] = useState<{ origin: RequestOrigin; solveRequest: SolveRequest } | null>(null);

  const sequenceRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const coeffDraftRef = useRef<CoefficientsDraft>(INITIAL_COEFF_DRAFT);

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
    setLastAcceptedResponse(null);
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
    setLastAcceptedResponse(null);
    setReactiveStatus('idle');
    setSourceMode('RAW_TEXT');
    coeffDraftRef.current = INITIAL_COEFF_DRAFT;
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
          setLastAcceptedResponse(resp);

          // Freeze provenance semantics:
          // RAW_TEXT -> RAW_TEXT
          // COEFFICIENT_EDIT -> COEFFICIENTS
          // METHOD_SWITCH -> preserve current sourceMode
          if (origin === 'RAW_TEXT') {
            setSourceMode('RAW_TEXT');
          } else if (origin === 'COEFFICIENT_EDIT') {
            setSourceMode('COEFFICIENTS');
          }

          // Rehydrate draft from authoritative backend values and keep ref synchronized
          if (prob.problem_type === 'QUADRATIC') {
            const freshDraft = hydrateDraftFromBackend(prob.a, prob.b, prob.c);
            coeffDraftRef.current = freshDraft;
            setCoeffDraft(freshDraft);
          } else {
            const freshDraft: CoefficientsDraft = {
              a: coeffDraftRef.current.a.numeratorStr === '0' ? coeffDraftRef.current.a : { numeratorStr: '0', denominatorStr: '1' },
              b: { numeratorStr: String(prob.b.numerator), denominatorStr: String(prob.b.denominator) },
              c: { numeratorStr: String(prob.c.numerator), denominatorStr: String(prob.c.denominator) },
            };
            coeffDraftRef.current = freshDraft;
            setCoeffDraft(freshDraft);
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
   * StrictMode-Safe Pure updateCoefficientField.
   * Maintains coeffDraftRef and schedules debounce timer directly outside state updaters.
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

    // 4. Compute nextDraft purely from ref
    const fieldKey = `${part}Str` as const;
    const nextCoeff = { ...coeffDraftRef.current[coeff], [fieldKey]: value };
    const nextDraft: CoefficientsDraft = { ...coeffDraftRef.current, [coeff]: nextCoeff };

    // 5. Update ref and state
    coeffDraftRef.current = nextDraft;
    setCoeffDraft(nextDraft);

    // 6. Validate nextDraft
    const { isValid, errors } = validateCoefficientsDraft(nextDraft);
    setCoeffValidationErrors(errors);

    if (!isValid) {
      setReactiveStatus('invalid');
      return;
    }

    setReactiveStatus('debouncing');

    // 7. Schedule exactly ONE debounce timer outside any React state updater
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
  }, [executeSolve, cancelDebounce]);

  /**
   * Reset coefficient drafts to current accepted backend canonical values.
   * Invalidates active in-flight requests and restores draft.
   */
  const resetCoefficientsToBackend = useCallback(() => {
    cancelDebounce();
    sequenceRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    const targetProblem = currentProblem || lastAcceptedResponse?.problem;
    if (!targetProblem) return;

    if (targetProblem.problem_type === 'QUADRATIC') {
      const freshDraft = hydrateDraftFromBackend(targetProblem.a, targetProblem.b, targetProblem.c);
      coeffDraftRef.current = freshDraft;
      setCoeffDraft(freshDraft);
      setCoeffValidationErrors({});
      setReactiveStatus('idle');
    } else {
      const freshDraft: CoefficientsDraft = {
        a: { numeratorStr: '0', denominatorStr: '1' },
        b: { numeratorStr: String(targetProblem.b.numerator), denominatorStr: String(targetProblem.b.denominator) },
        c: { numeratorStr: String(targetProblem.c.numerator), denominatorStr: String(targetProblem.c.denominator) },
      };
      coeffDraftRef.current = freshDraft;
      setCoeffDraft(freshDraft);
      setCoeffValidationErrors({});
      setReactiveStatus('idle');
    }
  }, [currentProblem, lastAcceptedResponse, cancelDebounce]);

  /**
   * Switch method using newest backend canonical coefficients.
   */
  const switchMethod = useCallback(async (methodId: string) => {
    const targetProblem = currentQuadraticProblem || (lastAcceptedResponse?.problem?.problem_type === 'QUADRATIC' ? lastAcceptedResponse.problem : null);
    if (!targetProblem) return;

    const request: SolveRequest = {
      schema_version: '1.0.0',
      input_payload: {
        input_mode: 'COEFFICIENTS',
        a: targetProblem.a,
        b: targetProblem.b,
        c: targetProblem.c,
        target_variable: 'x',
      },
      selected_method_id: methodId,
    };

    await executeSolve(request, 'METHOD_SWITCH');
  }, [currentQuadraticProblem, lastAcceptedResponse, executeSolve]);

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
    lastAcceptedResponse,
    lastFailedRequestOrigin: lastFailedRequest?.origin ?? null,
    updateCoefficientField,
    resetCoefficientsToBackend,
    submitRawSolve,
    switchMethod,
    retryLastRequest,
    clearWorkspace,
  };
}
