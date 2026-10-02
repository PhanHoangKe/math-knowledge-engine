/**
 * MKE MVP V1 — Pure Typed API Client for S1 Algebraic Services.
 * 
 * Interacts exclusively with POST /api/v1/algebra/solve via native fetch.
 * Implements strict runtime response discrimination without client-side mathematical derivation.
 */

import type {
  SolveRequest,
  SolveResponse200,
  TransportErrorResponse,
  TransportErrorCode,
  LocalizedText,
  CurriculumRef,
  MethodKnowledge,
  ConceptKnowledge,
  FormulaKnowledge,
  TheoremKnowledge,
  GraphModel,
  KnowledgeApiErrorResponse,
  KnowledgeApiErrorCode,
} from './contract';

export type ApiSolveResult =
  | { kind: 'application'; status: number; response: SolveResponse200 }
  | { kind: 'transport-error'; status: number; response: TransportErrorResponse };

export class ProtocolError extends Error {
  public readonly status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ProtocolError';
    this.status = status;
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network unavailable') {
    super(message);
    this.name = 'NetworkError';
  }
}

export class KnowledgeApiError extends Error {
  public readonly status: number;
  public readonly errorCode: KnowledgeApiErrorCode;
  public readonly errorResponse: KnowledgeApiErrorResponse;

  constructor(errorResponse: KnowledgeApiErrorResponse, status: number = 404) {
    super(errorResponse.message_en);
    this.name = 'KnowledgeApiError';
    this.status = status;
    this.errorCode = errorResponse.error_code;
    this.errorResponse = errorResponse;
  }
}

const FROZEN_TRANSPORT_ERROR_CODES: ReadonlySet<TransportErrorCode> = new Set<TransportErrorCode>([
  'MALFORMED_JSON',
  'REQUEST_VALIDATION_FAILED',
  'PAYLOAD_TOO_LARGE',
  'UNSUPPORTED_MEDIA_TYPE',
  'API_NOT_FOUND',
  'INTERNAL_TRANSPORT_ERROR',
]);

/**
 * Hardened structural runtime discriminator for Application SolveResponse200.
 */
export function isApplicationResponse(data: unknown): data is SolveResponse200 {
  if (typeof data !== 'object' || data === null) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  const status = obj.response_status;

  if (status === 'SOLVED') {
    return (
      typeof obj.problem === 'object' &&
      obj.problem !== null &&
      typeof obj.solution === 'object' &&
      obj.solution !== null &&
      Array.isArray(obj.available_methods) &&
      typeof obj.selected_method_id === 'string'
    );
  }

  if (status === 'ANALYZED_NO_EXECUTION') {
    return (
      typeof obj.problem === 'object' &&
      obj.problem !== null &&
      typeof obj.reason_code === 'string' &&
      (obj.available_methods === undefined || Array.isArray(obj.available_methods))
    );
  }

  if (status === 'ERROR') {
    return (
      typeof obj.error_code === 'string' &&
      typeof obj.message_vi === 'string' &&
      typeof obj.message_en === 'string'
    );
  }

  return false;
}

/**
 * Hardened structural runtime discriminator for TransportErrorResponse.
 */
export function isTransportErrorResponse(data: unknown): data is TransportErrorResponse {
  if (typeof data !== 'object' || data === null) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  return (
    obj.transport_status === 'ERROR' &&
    typeof obj.transport_error_code === 'string' &&
    FROZEN_TRANSPORT_ERROR_CODES.has(obj.transport_error_code as TransportErrorCode) &&
    typeof obj.message_vi === 'string' &&
    typeof obj.message_en === 'string'
  );
}

/**
 * Execute equation solve/analysis request against the backend transport adapter.
 * 
 * @param request SolveRequest payload (RAW_TEXT or COEFFICIENTS mode)
 * @param signal Optional AbortSignal for request cancellation
 * @returns ApiSolveResult (application response or transport error)
 */
export async function solveEquation(
  request: SolveRequest,
  signal?: AbortSignal
): Promise<ApiSolveResult> {
  let response: Response;
  try {
    response = await fetch('/api/v1/algebra/solve', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    // Generic sanitized network exception
    throw new NetworkError('Network request failed');
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ProtocolError('Invalid JSON response received from server', response.status);
  }

  // 1. Check for Application Response (HTTP 200 or HTTP 500 application error)
  if (isApplicationResponse(data)) {
    return {
      kind: 'application',
      status: response.status,
      response: data,
    };
  }

  // 2. Check for Transport Error Response (HTTP 400, 413, 415, 422, 500)
  if (isTransportErrorResponse(data)) {
    return {
      kind: 'transport-error',
      status: response.status,
      response: data,
    };
  }

  // 3. Unrecognized payload structure - treat as protocol failure
  throw new ProtocolError(
    `Unrecognized response schema from server with HTTP status ${response.status}`,
    response.status
  );
}

/**
 * Reusable runtime structural validation primitives.
 */
export function isRecord(data: unknown): data is Record<string, unknown> {
  return typeof data === 'object' && data !== null && !Array.isArray(data);
}

export function isStringArray(data: unknown): data is string[] {
  return Array.isArray(data) && data.every((item) => typeof item === 'string');
}

export function isLocalizedText(data: unknown): data is LocalizedText {
  return (
    isRecord(data) &&
    typeof data.vi === 'string' &&
    typeof data.en === 'string'
  );
}

export function isLocalizedTextArray(data: unknown): data is LocalizedText[] {
  return Array.isArray(data) && data.every(isLocalizedText);
}

export function isCurriculumRef(data: unknown): data is CurriculumRef {
  if (!isRecord(data)) return false;
  return (
    typeof data.framework === 'string' &&
    typeof data.grade_band === 'string' &&
    typeof data.subject === 'string' &&
    typeof data.topic === 'string' &&
    typeof data.source_document === 'string' &&
    typeof data.source_locator === 'string' &&
    (data.status === 'VERIFIED_MAPPING' || data.status === 'PROVISIONAL_MAPPING') &&
    (data.competency_ref === undefined || data.competency_ref === null || typeof data.competency_ref === 'string')
  );
}

export function isCurriculumRefArray(data: unknown): data is CurriculumRef[] {
  return Array.isArray(data) && data.every(isCurriculumRef);
}

/**
 * Structural runtime validator for MethodKnowledge.
 */
export function isMethodKnowledge(data: unknown): data is MethodKnowledge {
  if (!isRecord(data)) return false;
  return (
    typeof data.method_id === 'string' &&
    typeof data.version === 'string' &&
    isLocalizedText(data.title) &&
    isLocalizedText(data.summary) &&
    isLocalizedText(data.learning_objective) &&
    isLocalizedText(data.formal_description) &&
    (data.prerequisite_concept_ids === undefined || isStringArray(data.prerequisite_concept_ids)) &&
    (data.formula_refs === undefined || isStringArray(data.formula_refs)) &&
    (data.theorem_refs === undefined || isStringArray(data.theorem_refs)) &&
    (data.related_method_ids === undefined || isStringArray(data.related_method_ids)) &&
    (data.provenance_refs === undefined || isStringArray(data.provenance_refs)) &&
    (data.applicability_guidance === undefined || isLocalizedTextArray(data.applicability_guidance)) &&
    (data.non_applicability_guidance === undefined || isLocalizedTextArray(data.non_applicability_guidance)) &&
    (data.common_mistakes === undefined || isLocalizedTextArray(data.common_mistakes)) &&
    (data.diagnostic_tips === undefined || isLocalizedTextArray(data.diagnostic_tips)) &&
    (data.curriculum_refs === undefined || isCurriculumRefArray(data.curriculum_refs))
  );
}

/**
 * Structural runtime validator for ConceptKnowledge.
 */
export function isConceptKnowledge(data: unknown): data is ConceptKnowledge {
  if (!isRecord(data)) return false;
  return (
    typeof data.concept_id === 'string' &&
    typeof data.version === 'string' &&
    isLocalizedText(data.title) &&
    isLocalizedText(data.definition) &&
    (data.prerequisite_concept_ids === undefined || isStringArray(data.prerequisite_concept_ids)) &&
    (data.related_concept_ids === undefined || isStringArray(data.related_concept_ids)) &&
    (data.formula_refs === undefined || isStringArray(data.formula_refs)) &&
    (data.method_refs === undefined || isStringArray(data.method_refs)) &&
    (data.provenance_refs === undefined || isStringArray(data.provenance_refs)) &&
    (data.curriculum_refs === undefined || isCurriculumRefArray(data.curriculum_refs))
  );
}

/**
 * Structural runtime validator for FormulaKnowledge.
 */
export function isFormulaKnowledge(data: unknown): data is FormulaKnowledge {
  if (!isRecord(data)) return false;
  if (
    typeof data.formula_id !== 'string' ||
    typeof data.version !== 'string' ||
    !isLocalizedText(data.title) ||
    typeof data.latex_template !== 'string' ||
    !isLocalizedText(data.domain_conditions)
  ) {
    return false;
  }
  if (data.related_concept_ids !== undefined && !isStringArray(data.related_concept_ids)) {
    return false;
  }
  if (data.provenance_refs !== undefined && !isStringArray(data.provenance_refs)) {
    return false;
  }
  if (data.variables_description !== undefined) {
    if (!isRecord(data.variables_description)) return false;
    for (const val of Object.values(data.variables_description)) {
      if (!isLocalizedText(val)) return false;
    }
  }
  return true;
}

/**
 * Structural runtime validator for TheoremKnowledge.
 */
export function isTheoremKnowledge(data: unknown): data is TheoremKnowledge {
  if (!isRecord(data)) return false;
  return (
    typeof data.theorem_id === 'string' &&
    typeof data.version === 'string' &&
    isLocalizedText(data.title) &&
    isLocalizedText(data.statement) &&
    typeof data.formal_statement_latex === 'string' &&
    (data.hypotheses === undefined || isLocalizedTextArray(data.hypotheses)) &&
    (data.conclusions === undefined || isLocalizedTextArray(data.conclusions)) &&
    (data.related_concept_ids === undefined || isStringArray(data.related_concept_ids)) &&
    (data.provenance_refs === undefined || isStringArray(data.provenance_refs))
  );
}

/**
 * Structural runtime validator for GraphModel.
 */
export function isGraphModel(data: unknown): data is GraphModel {
  if (!isRecord(data)) return false;
  if (
    typeof data.graph_id !== 'string' ||
    typeof data.graph_kind !== 'string' ||
    !isLocalizedText(data.title) ||
    typeof data.version !== 'string' ||
    typeof data.is_acyclic !== 'boolean'
  ) {
    return false;
  }
  if (data.nodes !== undefined) {
    if (!Array.isArray(data.nodes)) return false;
    for (const node of data.nodes) {
      if (!isRecord(node)) return false;
      if (typeof node.node_id !== 'string' || typeof node.node_type !== 'string' || !isLocalizedText(node.label)) {
        return false;
      }
    }
  }
  if (data.edges !== undefined) {
    if (!Array.isArray(data.edges)) return false;
    for (const edge of data.edges) {
      if (!isRecord(edge)) return false;
      if (typeof edge.source !== 'string' || typeof edge.target !== 'string' || typeof edge.relation_type !== 'string' || typeof edge.is_directed !== 'boolean') {
        return false;
      }
    }
  }
  return true;
}

/**
 * Hardened structural runtime discriminator for KnowledgeApiErrorResponse.
 */
export function isKnowledgeApiErrorResponse(data: unknown): data is KnowledgeApiErrorResponse {
  if (!isRecord(data)) {
    return false;
  }
  return (
    data.status === 'error' &&
    data.error_code === 'KNOWLEDGE_ENTITY_NOT_FOUND' &&
    typeof data.entity_type === 'string' &&
    typeof data.entity_id === 'string' &&
    typeof data.message_vi === 'string' &&
    typeof data.message_en === 'string'
  );
}

/**
 * Generic internal fetch helper for immutable knowledge endpoints with strict runtime validation.
 */
async function fetchKnowledgeEntity<T>(
  url: string,
  validator: (data: unknown) => data is T,
  signal?: AbortSignal
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    throw new NetworkError('Network request failed');
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ProtocolError('Invalid JSON response received from server', response.status);
  }

  if (response.ok) {
    if (validator(data)) {
      return data;
    }
    throw new ProtocolError(
      `Invalid knowledge response schema from server for ${url}`,
      response.status
    );
  }

  if (response.status === 404 && isKnowledgeApiErrorResponse(data)) {
    throw new KnowledgeApiError(data, response.status);
  }

  if (isTransportErrorResponse(data)) {
    throw new ProtocolError(
      `Transport error: ${data.transport_error_code} (${data.message_en})`,
      response.status
    );
  }

  throw new ProtocolError(
    `Unrecognized response from ${url} with HTTP status ${response.status}`,
    response.status
  );
}

/**
 * Fetch immutable MethodKnowledge by canonical method ID.
 */
export async function getMethodKnowledge(
  methodId: string,
  signal?: AbortSignal
): Promise<MethodKnowledge> {
  return fetchKnowledgeEntity<MethodKnowledge>(
    `/api/v1/knowledge/methods/${encodeURIComponent(methodId)}`,
    isMethodKnowledge,
    signal
  );
}

/**
 * Fetch immutable ConceptKnowledge by canonical concept ID.
 */
export async function getConceptKnowledge(
  conceptId: string,
  signal?: AbortSignal
): Promise<ConceptKnowledge> {
  return fetchKnowledgeEntity<ConceptKnowledge>(
    `/api/v1/knowledge/concepts/${encodeURIComponent(conceptId)}`,
    isConceptKnowledge,
    signal
  );
}

/**
 * Fetch immutable FormulaKnowledge by canonical formula ID.
 */
export async function getFormulaKnowledge(
  formulaId: string,
  signal?: AbortSignal
): Promise<FormulaKnowledge> {
  return fetchKnowledgeEntity<FormulaKnowledge>(
    `/api/v1/knowledge/formulas/${encodeURIComponent(formulaId)}`,
    isFormulaKnowledge,
    signal
  );
}

/**
 * Fetch immutable TheoremKnowledge by canonical theorem ID.
 */
export async function getTheoremKnowledge(
  theoremId: string,
  signal?: AbortSignal
): Promise<TheoremKnowledge> {
  return fetchKnowledgeEntity<TheoremKnowledge>(
    `/api/v1/knowledge/theorems/${encodeURIComponent(theoremId)}`,
    isTheoremKnowledge,
    signal
  );
}

/**
 * Fetch full immutable mathematical GraphModel.
 */
export async function getKnowledgeGraph(signal?: AbortSignal): Promise<GraphModel> {
  return fetchKnowledgeEntity<GraphModel>(
    '/api/v1/knowledge/graph',
    isGraphModel,
    signal
  );
}
