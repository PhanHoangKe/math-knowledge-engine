import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  solveEquation,
  NetworkError,
  ProtocolError,
} from '../api/client';
import {
  mockSolvedTwoRoots,
  mockAnalyzedDegenerateLinear,
  mockApplicationErrorSyntax,
  mockTransportError422,
  mockTransportError413,
  mockTransportError415,
} from './fixtures/responses';
import type { SolveRequest } from '../api/contract';

describe('MKE Typed API Client (POST /api/v1/algebra/solve)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const dummyRawRequest: SolveRequest = {
    schema_version: '1.0.0',
    input_payload: {
      input_mode: 'RAW_TEXT',
      raw_query: 'x^2 - 5*x + 6 = 0',
      target_variable: 'x',
    },
    selected_method_id: null,
  };

  it('sends POST to relative URL /api/v1/algebra/solve with application/json header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockSolvedTwoRoots), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    global.fetch = fetchMock;

    const result = await solveEquation(dummyRawRequest);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/algebra/solve',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dummyRawRequest),
      })
    );

    expect(result.kind).toBe('application');
    expect(result.status).toBe(200);
    if (result.kind === 'application') {
      expect(result.response.response_status).toBe('SOLVED');
    }
  });

  it('classifies HTTP 200 ANALYZED_NO_EXECUTION as application response', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockAnalyzedDegenerateLinear), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('application');
    expect(result.status).toBe(200);
    if (result.kind === 'application') {
      expect(result.response.response_status).toBe('ANALYZED_NO_EXECUTION');
    }
  });

  it('classifies HTTP 200 ErrorResponse as application response', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockApplicationErrorSyntax), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('application');
    expect(result.status).toBe(200);
    if (result.kind === 'application') {
      expect(result.response.response_status).toBe('ERROR');
    }
  });

  it('classifies HTTP 422 DTO validation error as TransportErrorResponse', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockTransportError422), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('transport-error');
    expect(result.status).toBe(422);
    if (result.kind === 'transport-error') {
      expect(result.response.transport_status).toBe('ERROR');
      expect(result.response.transport_error_code).toBe('REQUEST_VALIDATION_FAILED');
    }
  });

  it('classifies HTTP 400 MALFORMED_JSON as TransportErrorResponse', async () => {
    const malformedJsonError = {
      transport_status: 'ERROR' as const,
      transport_error_code: 'MALFORMED_JSON' as const,
      message_vi: 'Dữ liệu JSON trong yêu cầu không hợp lệ.',
      message_en: 'Malformed JSON payload in request.',
    };
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(malformedJsonError), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('transport-error');
    expect(result.status).toBe(400);
    if (result.kind === 'transport-error') {
      expect(result.response.transport_status).toBe('ERROR');
      expect(result.response.transport_error_code).toBe('MALFORMED_JSON');
    }
  });

  it('classifies HTTP 413 Payload Too Large as TransportErrorResponse', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockTransportError413), {
        status: 413,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('transport-error');
    expect(result.status).toBe(413);
    if (result.kind === 'transport-error') {
      expect(result.response.transport_error_code).toBe('PAYLOAD_TOO_LARGE');
    }
  });

  it('classifies HTTP 415 Unsupported Media Type as TransportErrorResponse', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(mockTransportError415), {
        status: 415,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('transport-error');
    expect(result.status).toBe(415);
    if (result.kind === 'transport-error') {
      expect(result.response.transport_error_code).toBe('UNSUPPORTED_MEDIA_TYPE');
    }
  });

  it('classifies HTTP 500 Application ErrorResponse properly', async () => {
    const internalAppError = {
      response_status: 'ERROR' as const,
      error_code: 'INTERNAL_ERROR' as const,
      message_vi: 'Lỗi nội bộ phía ứng dụng',
      message_en: 'Internal application error',
    };
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(internalAppError), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('application');
    expect(result.status).toBe(500);
    if (result.kind === 'application') {
      expect(result.response.response_status).toBe('ERROR');
    }
  });

  it('classifies HTTP 500 TransportErrorResponse properly', async () => {
    const internalTransportError = {
      transport_status: 'ERROR' as const,
      transport_error_code: 'INTERNAL_TRANSPORT_ERROR' as const,
      message_vi: 'Lỗi truyền tải nội bộ',
      message_en: 'Internal transport error',
    };
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(internalTransportError), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const result = await solveEquation(dummyRawRequest);

    expect(result.kind).toBe('transport-error');
    expect(result.status).toBe(500);
    if (result.kind === 'transport-error') {
      expect(result.response.transport_error_code).toBe('INTERNAL_TRANSPORT_ERROR');
    }
  });

  it('throws NetworkError when native fetch fails (e.g. network disconnect)', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(NetworkError);
  });

  it('throws ProtocolError when response contains invalid non-JSON body', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response('<html>502 Bad Gateway</html>', {
        status: 502,
        headers: { 'Content-Type': 'text/html' },
      })
    );

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(ProtocolError);
  });

  it('throws ProtocolError when JSON structure is unrecognized', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ unexpected_field: 123 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(ProtocolError);
  });

  it('throws ProtocolError when response_status is SOLVED but missing required structural fields', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ response_status: 'SOLVED' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(ProtocolError);
  });

  it('throws ProtocolError when response_status is ERROR but missing localized messages', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ response_status: 'ERROR', error_code: 'SYNTAX_ERROR' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(ProtocolError);
  });

  it('throws ProtocolError when transport_error_code is not in frozen enum set', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          transport_status: 'ERROR',
          transport_error_code: 'UNKNOWN_CUSTOM_CODE',
          message_vi: 'Lỗi không xác định',
          message_en: 'Unknown error',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    );

    await expect(solveEquation(dummyRawRequest)).rejects.toThrow(ProtocolError);
  });
});
