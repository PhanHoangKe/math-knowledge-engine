import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { MethodKnowledgeSurface } from '../components/MethodKnowledgeSurface/MethodKnowledgeSurface';
import {
  mockMethodKnowledgeStandard,
  mockConceptDiscriminant,
  mockConceptQuadraticEquation,
  mockFormulaStandard,
  mockTheoremQuadraticRoots,
} from './fixtures/knowledgeFixtures';

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

    // Initial loading indicator
    expect(screen.getByTestId('knowledge-loading-QUAD_FORMULA_STANDARD')).toBeInTheDocument();

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

  it('renders error state cleanly on network failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    render(
      <PreferencesProvider initialLanguage="vi">
        <MethodKnowledgeSurface methodId="QUAD_FORMULA_STANDARD" isOpen={true} />
      </PreferencesProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('knowledge-error-QUAD_FORMULA_STANDARD')).toBeInTheDocument();
    });
  });
});
