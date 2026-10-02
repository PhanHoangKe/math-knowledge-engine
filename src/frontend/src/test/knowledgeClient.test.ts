import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getMethodKnowledge,
  getConceptKnowledge,
  getFormulaKnowledge,
  getTheoremKnowledge,
  getKnowledgeGraph,
  KnowledgeApiError,
  NetworkError,
  ProtocolError,
} from '../api/client';
import {
  mockMethodKnowledgeStandard,
  mockConceptDiscriminant,
  mockFormulaStandard,
  mockTheoremQuadraticRoots,
} from './fixtures/knowledgeFixtures';
import type { GraphModel } from '../api/contract';

describe('MKE Knowledge API Client Functions', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('1. fetches method knowledge successfully from /api/v1/knowledge/methods/{id}', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockMethodKnowledgeStandard), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    global.fetch = fetchMock;

    const result = await getMethodKnowledge('QUAD_FORMULA_STANDARD');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD',
      expect.objectContaining({
        method: 'GET',
        headers: { Accept: 'application/json' },
      })
    );
    expect(result.method_id).toBe('QUAD_FORMULA_STANDARD');
    expect(result.title.vi).toContain('Công thức nghiệm chuẩn tắc');
  });

  it('2. fetches concept knowledge successfully from /api/v1/knowledge/concepts/{id}', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConceptDiscriminant), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    const result = await getConceptKnowledge('concept_discriminant');
    expect(result.concept_id).toBe('concept_discriminant');
    expect(result.title.vi).toBe('Biệt thức Delta');
  });

  it('3. fetches formula knowledge successfully from /api/v1/knowledge/formulas/{id}', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockFormulaStandard), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    const result = await getFormulaKnowledge('FORMULA_QUADRATIC_STANDARD');
    expect(result.formula_id).toBe('FORMULA_QUADRATIC_STANDARD');
    expect(result.latex_template).toContain('\\frac{-b');
  });

  it('4. fetches theorem knowledge successfully from /api/v1/knowledge/theorems/{id}', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockTheoremQuadraticRoots), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    const result = await getTheoremKnowledge('THEOREM_QUADRATIC_ROOTS');
    expect(result.theorem_id).toBe('THEOREM_QUADRATIC_ROOTS');
    expect(result.formal_statement_latex).toContain('\\Delta > 0');
  });

  it('5. fetches knowledge graph successfully from /api/v1/knowledge/graph', async () => {
    const mockGraph: GraphModel = {
      graph_id: 'mke_knowledge_graph_v1',
      graph_kind: 'KNOWLEDGE_GRAPH',
      title: { vi: 'Đồ thị tri thức', en: 'Knowledge Graph' },
      version: '1.0.0',
      is_acyclic: false,
      nodes: [],
      edges: [],
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockGraph), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    const result = await getKnowledgeGraph();
    expect(result.graph_id).toBe('mke_knowledge_graph_v1');
    expect(result.graph_kind).toBe('KNOWLEDGE_GRAPH');
  });

  it('6. throws KnowledgeApiError on HTTP 404 with structured error envelope', async () => {
    const notFoundError = {
      status: 'error' as const,
      error_code: 'KNOWLEDGE_ENTITY_NOT_FOUND' as const,
      entity_type: 'method',
      entity_id: 'NON_EXISTENT_METHOD',
      message_vi: 'Không tìm thấy thực thể tri thức: NON_EXISTENT_METHOD',
      message_en: 'Knowledge entity not found: NON_EXISTENT_METHOD',
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(notFoundError), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(getMethodKnowledge('NON_EXISTENT_METHOD')).rejects.toThrow(KnowledgeApiError);

    try {
      await getMethodKnowledge('NON_EXISTENT_METHOD');
    } catch (err) {
      expect(err).toBeInstanceOf(KnowledgeApiError);
      const apiErr = err as KnowledgeApiError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.errorCode).toBe('KNOWLEDGE_ENTITY_NOT_FOUND');
      expect(apiErr.errorResponse.entity_id).toBe('NON_EXISTENT_METHOD');
    }
  });

  it('7. throws ProtocolError on HTTP 500 with TransportErrorResponse structure', async () => {
    const transportError = {
      transport_status: 'ERROR',
      transport_error_code: 'INTERNAL_TRANSPORT_ERROR',
      message_vi: 'Lỗi máy chủ nội bộ',
      message_en: 'Internal server error occurred',
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(transportError), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(getMethodKnowledge('QUAD_FORMULA_STANDARD')).rejects.toThrow(ProtocolError);
    try {
      await getMethodKnowledge('QUAD_FORMULA_STANDARD');
    } catch (err) {
      expect(err).toBeInstanceOf(ProtocolError);
      expect((err as ProtocolError).status).toBe(500);
      expect((err as ProtocolError).message).toContain('INTERNAL_TRANSPORT_ERROR');
    }
  });

  it('8. throws ProtocolError on non-JSON response (HTML or plain text)', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response('<html><body>502 Bad Gateway</body></html>', {
          status: 502,
          headers: { 'Content-Type': 'text/html' },
        })
      )
    );
    await expect(getFormulaKnowledge('FORMULA_QUADRATIC_STANDARD')).rejects.toThrow(ProtocolError);
  });

  it('9. throws ProtocolError on HTTP 200 with malformed/missing required fields', async () => {
    const malformedPayload = {
      foo: 'bar',
      baz: 123,
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(malformedPayload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(getMethodKnowledge('QUAD_FORMULA_STANDARD')).rejects.toThrow(ProtocolError);
  });

  it('10. throws ProtocolError on HTTP 200 when nested LocalizedText or array is malformed', async () => {
    // Missing 'en' in title LocalizedText
    const brokenLocalizedText = {
      ...mockMethodKnowledgeStandard,
      title: { vi: 'Chỉ có tiếng Việt' },
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(brokenLocalizedText), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(getMethodKnowledge('QUAD_FORMULA_STANDARD')).rejects.toThrow(ProtocolError);

    // Invalid prerequisite_concept_ids (numbers instead of strings)
    const brokenArray = {
      ...mockMethodKnowledgeStandard,
      prerequisite_concept_ids: [1, 2, 3],
    };
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(brokenArray), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );

    await expect(getMethodKnowledge('QUAD_FORMULA_STANDARD')).rejects.toThrow(ProtocolError);
  });

  it('11. properly encodes URL parameters with reserved characters using encodeURIComponent', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockConceptDiscriminant), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    global.fetch = fetchMock;

    await getConceptKnowledge('concept/special?query=1&test=true');
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/knowledge/concepts/concept%2Fspecial%3Fquery%3D1%26test%3Dtrue',
      expect.any(Object)
    );
  });

  it('12. ensures knowledge GET requests do not include a request body', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockFormulaStandard), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    global.fetch = fetchMock;

    await getFormulaKnowledge('FORMULA_QUADRATIC_STANDARD');
    const callArgs = fetchMock.mock.calls[0] as [string, RequestInit | undefined] | undefined;
    expect(callArgs?.[1]?.body).toBeUndefined();
    expect(callArgs?.[1]?.method).toBe('GET');
  });

  it('13. throws NetworkError when network fetch rejects', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(getConceptKnowledge('concept_discriminant')).rejects.toThrow(NetworkError);
  });

  it('14. properly aborts fetch when signal is cancelled', async () => {
    const controller = new AbortController();
    global.fetch = vi.fn().mockImplementation((_url, opts) => {
      return new Promise((_, reject) => {
        if (opts.signal) {
          opts.signal.addEventListener('abort', () => {
            const err = new DOMException('The operation was aborted', 'AbortError');
            reject(err);
          });
        }
      });
    });

    const promise = getMethodKnowledge('QUAD_FORMULA_STANDARD', controller.signal);
    controller.abort();

    await expect(promise).rejects.toThrow('The operation was aborted');
  });
});
