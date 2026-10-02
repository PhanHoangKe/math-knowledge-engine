import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { MethodCatalogPanel } from '../components/MethodCatalogPanel/MethodCatalogPanel';
import type { MethodOptionView } from '../api/contract';
import {
  mockMethodKnowledgeStandard,
  mockConceptDiscriminant,
  mockFormulaStandard,
  mockTheoremQuadraticRoots,
} from './fixtures/knowledgeFixtures';

describe('MethodCatalogPanel Component with Knowledge Surfaces', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const mockMethods: MethodOptionView[] = [
    {
      method_id: 'QUAD_FORMULA_STANDARD',
      title_vi: 'Công thức nghiệm chuẩn tắc (Delta)',
      pedagogical_priority: 1,
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'AVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      support_status: 'SUPPORTED',
      verification_capability: 'HOST_VERIFIABLE',
      has_trace_available: true,
      reasons: ['Phương trình bậc hai tổng quát'],
      prerequisites: [
        {
          prerequisite_id: 'PREREQ_QUADRATIC_DEGREE',
          description_vi: 'Bậc phương trình đúng bằng 2',
          is_satisfied: true,
        },
      ],
    },
    {
      method_id: 'QUAD_COMPLETE_SQUARE',
      title_vi: 'Phương pháp biến đổi bình phương hoàn chỉnh',
      pedagogical_priority: 3,
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'UNAVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      support_status: 'SUPPORTED',
      verification_capability: 'HOST_VERIFIABLE',
      has_trace_available: false,
      reasons: ['Hệ số bậc 2 hợp lệ'],
    },
    {
      method_id: 'QUAD_GRAPHICAL_ANALYSIS',
      title_vi: 'Phương pháp đồ thị (Hình học Parabol)',
      pedagogical_priority: 4,
      mathematical_applicability: 'NOT_APPLICABLE',
      execution_availability: 'UNAVAILABLE',
      pedagogical_recommendation: 'DISCOURAGED',
      support_status: 'UNSUPPORTED',
      verification_capability: 'NOT_APPLICABLE',
      has_trace_available: false,
      reasons: ['Không áp dụng trực tiếp giải nghiệm đại số giải tích'],
    },
  ];

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
      if (url.includes('/api/v1/knowledge/methods/QUAD_COMPLETE_SQUARE')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ...mockMethodKnowledgeStandard,
              method_id: 'QUAD_COMPLETE_SQUARE',
              title: {
                vi: 'Phương pháp biến đổi bình phương hoàn chỉnh',
                en: 'Completing the Square Method',
              },
              summary: {
                vi: 'Đưa phương trình về dạng (x + p)^2 = q',
                en: 'Transform equation into (x + p)^2 = q form',
              },
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        );
      }
      if (url.includes('/api/v1/knowledge/methods/QUAD_GRAPHICAL_ANALYSIS')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ...mockMethodKnowledgeStandard,
              method_id: 'QUAD_GRAPHICAL_ANALYSIS',
              title: {
                vi: 'Phương pháp đồ thị (Parabol)',
                en: 'Graphical Analysis Method (Parabola)',
              },
              summary: {
                vi: 'Tìm giao điểm của Parabol y = ax^2 + bx + c với trục hoành Ox',
                en: 'Find intersection points of parabola y = ax^2 + bx + c with x-axis',
              },
            }),
            {
              status: 200,
              headers: { 'Content-Type': 'application/json' },
            }
          )
        );
      }
      if (url.includes('/api/v1/knowledge/concepts/')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockConceptDiscriminant), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/formulas/')) {
        return Promise.resolve(
          new Response(JSON.stringify(mockFormulaStandard), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      if (url.includes('/api/v1/knowledge/theorems/')) {
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

  it('renders method cards with "Why this method?" and "Switch method" buttons', () => {
    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodCatalogPanel
          methods={mockMethods}
          selectedMethodId="QUAD_FORMULA_STANDARD"
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('why-method-btn-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    expect(screen.getByTestId('why-method-btn-QUAD_COMPLETE_SQUARE')).toBeInTheDocument();
    expect(screen.getByTestId('why-method-btn-QUAD_GRAPHICAL_ANALYSIS')).toBeInTheDocument();
    expect(screen.getByTestId('select-method-btn-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    expect(screen.getByTestId('select-method-btn-QUAD_COMPLETE_SQUARE')).toBeInTheDocument();
    expect(screen.getByTestId('select-method-btn-QUAD_GRAPHICAL_ANALYSIS')).toBeInTheDocument();
  });

  it('toggles knowledge surface when "Why this method?" is clicked without calling onSelectMethod', async () => {
    setupMockFetch();
    const onSelectMethodMock = vi.fn();

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodCatalogPanel
          methods={mockMethods}
          selectedMethodId="QUAD_FORMULA_STANDARD"
          onSelectMethod={onSelectMethodMock}
        />
      </PreferencesProvider>
    );

    const whyBtn = screen.getByTestId('why-method-btn-QUAD_FORMULA_STANDARD');
    expect(whyBtn).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByTestId('method-knowledge-surface-QUAD_FORMULA_STANDARD')
    ).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(whyBtn);

    expect(whyBtn).toHaveAttribute('aria-expanded', 'true');
    expect(onSelectMethodMock).not.toHaveBeenCalled();

    // Verify knowledge surface rendered
    const surface = screen.getByTestId('method-knowledge-surface-QUAD_FORMULA_STANDARD');
    expect(surface).toBeInTheDocument();

    await waitFor(() => {
      expect(
        within(surface).getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')
      ).toBeInTheDocument();
    });

    // Click to collapse
    fireEvent.click(whyBtn);
    expect(whyBtn).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByTestId('method-knowledge-surface-QUAD_FORMULA_STANDARD')
    ).not.toBeInTheDocument();
  });

  it('allows inspecting UNAVAILABLE method knowledge without calling onSelectMethod', async () => {
    setupMockFetch();
    const onSelectMethodMock = vi.fn();

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodCatalogPanel
          methods={mockMethods}
          selectedMethodId="QUAD_FORMULA_STANDARD"
          onSelectMethod={onSelectMethodMock}
        />
      </PreferencesProvider>
    );

    const whyCompleteSquareBtn = screen.getByTestId('why-method-btn-QUAD_COMPLETE_SQUARE');
    fireEvent.click(whyCompleteSquareBtn);

    expect(onSelectMethodMock).not.toHaveBeenCalled();
    const surface = screen.getByTestId('method-knowledge-surface-QUAD_COMPLETE_SQUARE');
    expect(surface).toBeInTheDocument();

    await waitFor(() => {
      expect(
        within(surface).getByText('Phương pháp biến đổi bình phương hoàn chỉnh')
      ).toBeInTheDocument();
      expect(
        within(surface).getByText('Đưa phương trình về dạng (x + p)^2 = q')
      ).toBeInTheDocument();
    });
  });

  it('allows inspecting NOT_APPLICABLE method knowledge without calling onSelectMethod', async () => {
    setupMockFetch();
    const onSelectMethodMock = vi.fn();

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodCatalogPanel
          methods={mockMethods}
          selectedMethodId="QUAD_FORMULA_STANDARD"
          onSelectMethod={onSelectMethodMock}
        />
      </PreferencesProvider>
    );

    const whyGraphicalBtn = screen.getByTestId('why-method-btn-QUAD_GRAPHICAL_ANALYSIS');
    fireEvent.click(whyGraphicalBtn);

    expect(onSelectMethodMock).not.toHaveBeenCalled();
    const surface = screen.getByTestId('method-knowledge-surface-QUAD_GRAPHICAL_ANALYSIS');
    expect(surface).toBeInTheDocument();

    await waitFor(() => {
      expect(
        within(surface).getByText('Phương pháp đồ thị (Parabol)')
      ).toBeInTheDocument();
      expect(
        within(surface).getByText(/Tìm giao điểm của Parabol/)
      ).toBeInTheDocument();
    });
  });
});
