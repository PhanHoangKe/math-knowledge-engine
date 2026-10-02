import type React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { PreferencesProvider, usePreferences } from '../state/preferences';
import { MethodKnowledgeSurface } from '../components/MethodKnowledgeSurface/MethodKnowledgeSurface';
import {
  mockMethodKnowledgeStandard,
  mockConceptDiscriminant,
  mockConceptQuadraticEquation,
  mockFormulaStandard,
  mockTheoremQuadraticRoots,
} from './fixtures/knowledgeFixtures';
import type { MethodKnowledge } from '../api/contract';

describe('MethodKnowledgeSurface Component', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const setupMockFetch = () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockMethodKnowledgeStandard), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/concepts/concept_discriminant')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptDiscriminant), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/concepts/concept_quadratic_equation')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptQuadraticEquation), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/formulas/FORMULA_QUADRATIC_STANDARD')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockFormulaStandard), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/formulas/FORMULA_DISCRIMINANT_DELTA')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ...mockFormulaStandard,
              formula_id: 'FORMULA_DISCRIMINANT_DELTA',
              title: { vi: 'Công thức Delta', en: 'Delta formula' },
              latex_template: '\\Delta = b^2 - 4ac',
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        );
      }
      if (url.includes('/api/v1/knowledge/theorems/THEOREM_QUADRATIC_ROOTS')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockTheoremQuadraticRoots), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });
  };

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={false} />
      </PreferencesProvider>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders loading state and then full knowledge surface content in Vietnamese', async () => {
    setupMockFetch();

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={true} />
      </PreferencesProvider>
    );

    // Initial loading indicator with accessible attributes
    const loadingElem = screen.getByTestId('knowledge-loading-QUAD_FORMULA_STANDARD');
    expect(loadingElem).toBeInTheDocument();
    expect(loadingElem).toHaveAttribute('role', 'status');
    expect(loadingElem).toHaveAttribute('aria-live', 'polite');

    // Wait for loaded content
    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')).toBeInTheDocument();
    });

    // Check summary & objectives
    expect(
      screen.getByText(/Phương pháp giải tổng quát cho mọi phương trình bậc hai/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Học sinh nắm vững cách tính Delta/)
    ).toBeInTheDocument();

    // Check guidance sections
    expect(
      screen.getByText(/Áp dụng cho mọi phương trình bậc hai ax\^2 \+ bx \+ c = 0/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Không áp dụng khi hệ số a = 0/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Nhầm lẫn dấu của hệ số b/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Kiểm tra kỹ dấu của tích ac/)
    ).toBeInTheDocument();

    // Check prerequisite concepts
    await waitFor(() => {
      expect(screen.getByText('Biệt thức Delta')).toBeInTheDocument();
      expect(screen.getByText('Phương trình bậc hai một ẩn')).toBeInTheDocument();
    });

    // Check formula cards
    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm bậc hai')).toBeInTheDocument();
      expect(screen.getByTestId('formula-latex-FORMULA_QUADRATIC_STANDARD')).toBeInTheDocument();
    });

    // Check theorem cards
    await waitFor(() => {
      expect(screen.getByText('Định lý về số nghiệm của phương trình bậc hai')).toBeInTheDocument();
      expect(screen.getByTestId('theorem-latex-THEOREM_QUADRATIC_ROOTS')).toBeInTheDocument();
    });

    // Check curriculum references
    expect(screen.getByText('GDPT_2018')).toBeInTheDocument();
    expect(screen.getByText('GRADE_9')).toBeInTheDocument();
  });

  it('renders bilingual content dynamically when language is English', async () => {
    setupMockFetch();

    render(
      <PreferencesProvider initialLanguage="en">
        <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={true} />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByText('Standard Quadratic Formula (Discriminant Delta)')
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText(/General solution method for any quadratic equation/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Students master Delta calculation/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Applicable to any quadratic equation/)
    ).toBeInTheDocument();
  });

  it('triggers onClose callback when close button is clicked', async () => {
    setupMockFetch();
    const onCloseMock = vi.fn();

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface
          methodId="QUAD_FORMULA_STANDARD"
          isOpen={true}
          onClose={onCloseMock}
        />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')).toBeInTheDocument();
    });

    const closeBtn = screen.getByRole('button', { name: /Ẩn tri thức sư phạm/i });
    fireEvent.click(closeBtn);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('sanitizes error UX without leaking raw exception message on 404 and network error', async () => {
    // 1. Test 404 response
    const notFoundPayload = {
      status: 'error',
      error_code: 'KNOWLEDGE_ENTITY_NOT_FOUND',
      entity_type: 'method',
      entity_id: 'UNKNOWN_METHOD',
      message_vi: 'Không tìm thấy thực thể tri thức: UNKNOWN_METHOD',
      message_en: 'Sensitive internal error message should not leak directly',
    };
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(notFoundPayload), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="UNKNOWN_METHOD" isOpen={true} />
      </PreferencesProvider>
    );

    await waitFor(() => {
      const errorContainer = screen.getByTestId('knowledge-error-UNKNOWN_METHOD');
      expect(errorContainer).toBeInTheDocument();
      expect(errorContainer).toHaveAttribute('role', 'alert');
    });

    // Sanitized localized message rendered, not the raw English exception
    expect(
      screen.getByText('Không tìm thấy thông tin tri thức trên máy chủ.')
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Sensitive internal error message should not leak directly/)
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('knowledge-retry-UNKNOWN_METHOD')).toBeInTheDocument();
  });

  it('allows retrying in-place via retry button after an initial network failure', async () => {
    let methodFetchCount = 0;
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/knowledge/methods/QUAD_FORMULA_STANDARD')) {
        methodFetchCount++;
        if (methodFetchCount === 1) {
          return Promise.reject(new Error('Network connection failed'));
        }
        return Promise.resolve(
          new Response(JSON.stringify(mockMethodKnowledgeStandard), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify(mockConceptDiscriminant), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={true} />
      </PreferencesProvider>
    );

    // Should first show error
    await waitFor(() => {
      expect(screen.getByTestId('knowledge-error-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    });
    expect(
      screen.getByText('Không thể kết nối đến máy chủ toán học MKE. Vui lòng kiểm tra kết nối mạng và thử lại.')
    ).toBeInTheDocument();

    // Click retry
    const retryBtn = screen.getByTestId('knowledge-retry-QUAD_FORMULA_STANDARD');
    fireEvent.click(retryBtn);

    // Should load successfully
    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('knowledge-error-QUAD_FORMULA_STANDARD')).not.toBeInTheDocument();
    expect(methodFetchCount).toBe(2);
  });

  it('handles out-of-order responses with activeRequestIdRef (latest-request-wins token guard)', async () => {
    let resolveFirstRequest: ((value: Response) => void) | null = null;

    const methodAData: MethodKnowledge = {
      ...mockMethodKnowledgeStandard,
      method_id: 'METHOD_SLOW_A',
      title: { vi: 'Phương pháp chậm A', en: 'Slow Method A' },
    };

    const methodBData: MethodKnowledge = {
      ...mockMethodKnowledgeStandard,
      method_id: 'METHOD_FAST_B',
      title: { vi: 'Phương pháp nhanh B', en: 'Fast Method B' },
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('METHOD_SLOW_A')) {
        return new Promise<Response>((resolve) => {
          resolveFirstRequest = resolve;
        });
      }
      if (url.includes('METHOD_FAST_B')) {
        return Promise.resolve(
          new Response(JSON.stringify(methodBData), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('Not Found', { status: 404 }));
    });

    const { rerender } = render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="METHOD_SLOW_A" isOpen={true} />
      </PreferencesProvider>
    );

    // Loading first method
    expect(screen.getByTestId('knowledge-loading-METHOD_SLOW_A')).toBeInTheDocument();

    // Change prop to METHOD_FAST_B before slow request A resolves
    rerender(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="METHOD_FAST_B" isOpen={true} />
      </PreferencesProvider>
    );

    // Fast request B resolves immediately
    await waitFor(() => {
      expect(screen.getByText('Phương pháp nhanh B')).toBeInTheDocument();
    });

    // Now resolve the late slow request A
    act(() => {
      if (resolveFirstRequest) {
        resolveFirstRequest(
          new Response(JSON.stringify(methodAData), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
    });

    // Wait a tick and verify METHOD_FAST_B remains rendered, NOT overwritten by late METHOD_SLOW_A
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByText('Phương pháp nhanh B')).toBeInTheDocument();
    expect(screen.queryByText('Phương pháp chậm A')).not.toBeInTheDocument();
  });

  it('reactively updates language switch (VI -> EN) on already mounted component', async () => {
    setupMockFetch();

    // Helper component with a language toggle button
    const LanguageSwitchWrapper: React.FC = () => {
      const { setLanguage } = usePreferences();
      return (
        <div>
          <button
            type="button"
            data-testid="toggle-en-btn"
            onClick={() => setLanguage('en')}
          >
            Switch to EN
          </button>
          <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={true} />
        </div>
      );
    };

    render(
      <PreferencesProvider initialLanguage="vi">
        <LanguageSwitchWrapper />
      </PreferencesProvider>
    );

    // Starts in Vietnamese
    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Phương pháp giải tổng quát cho mọi phương trình bậc hai/)
    ).toBeInTheDocument();

    // Trigger reactive language switch
    const toggleBtn = screen.getByTestId('toggle-en-btn');
    fireEvent.click(toggleBtn);

    // Immediately reflects English text without remounting or breaking
    await waitFor(() => {
      expect(
        screen.getByText('Standard Quadratic Formula (Discriminant Delta)')
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/General solution method for any quadratic equation/)
    ).toBeInTheDocument();
  });

  it('renders safely when prerequisite_concept_ids, formula_refs, or theorem_refs are empty or omitted', async () => {
    const minimalMethod: MethodKnowledge = {
      method_id: 'MINIMAL_METHOD',
      version: '1.0.0',
      title: { vi: 'Phương pháp tối giản', en: 'Minimal Method' },
      summary: { vi: 'Tóm tắt tối giản', en: 'Minimal summary' },
      learning_objective: { vi: 'Mục tiêu tối giản', en: 'Minimal objective' },
      formal_description: { vi: 'Mô tả hình thức', en: 'Formal description' },
      prerequisite_concept_ids: [],
      formula_refs: [],
      theorem_refs: [],
    };

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface
          methodId="MINIMAL_METHOD"
          isOpen={true}
          initialData={minimalMethod}
        />
      </PreferencesProvider>
    );

    expect(screen.getByText('Phương pháp tối giản')).toBeInTheDocument();
    expect(screen.getByText('Không có khái niệm tiên quyết nào.')).toBeInTheDocument();
    expect(screen.queryByTestId('method-formula-grid')).not.toBeInTheDocument();
    expect(screen.queryByTestId('method-theorem-grid')).not.toBeInTheDocument();
  });
});
