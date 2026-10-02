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

/**
 * Minimal safe runtime discriminator for Application SolveResponse200.
 */
export function isApplicationResponse(data: unknown): data is SolveResponse200 {
  if (typeof data !== 'object' || data === null) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  const status = obj.response_status;
  return status === 'SOLVED' || status === 'ANALYZED_NO_EXECUTION' || status === 'ERROR';
}

/**
 * Minimal safe runtime discriminator for TransportErrorResponse.
 */
export function isTransportErrorResponse(data: unknown): data is TransportErrorResponse {
  if (typeof data !== 'object' || data === null) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  return obj.transport_status === 'ERROR' && typeof obj.transport_error_code === 'string';
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
