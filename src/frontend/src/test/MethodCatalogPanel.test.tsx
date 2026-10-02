import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { MethodCatalogPanel } from '../components/MethodCatalogPanel/MethodCatalogPanel';
import type { MethodOptionView } from '../api/contract';
import {
  mockMethodKnowledgeStandard,
  mockConceptDiscriminant,
  mockConceptQuadraticEquation,
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
      method_id: 'VIETA_ROOT_RELATIONS',
      title_vi: 'Định lý Viète',
      pedagogical_priority: 2,
      mathematical_applicability: 'APPLICABLE',
      execution_availability: 'AVAILABLE',
      pedagogical_recommendation: 'RECOMMENDED',
      support_status: 'SUPPORTED',
      verification_capability: 'HOST_VERIFIABLE',
      has_trace_available: true,
      reasons: ['Hệ số hữu tỉ'],
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
    expect(screen.getByTestId('why-method-btn-VIETA_ROOT_RELATIONS')).toBeInTheDocument();
    expect(screen.getByTestId('select-method-btn-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    expect(screen.getByTestId('select-method-btn-VIETA_ROOT_RELATIONS')).toBeInTheDocument();
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
    expect(
      screen.getByTestId('method-knowledge-surface-QUAD_FORMULA_STANDARD')
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Công thức nghiệm chuẩn tắc (Biệt thức Delta)')).toBeInTheDocument();
    });

    // Click to collapse
    fireEvent.click(whyBtn);
    expect(whyBtn).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByTestId('method-knowledge-surface-QUAD_FORMULA_STANDARD')
    ).not.toBeInTheDocument();
  });
});
