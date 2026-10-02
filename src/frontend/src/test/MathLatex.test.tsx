import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MathLatex } from '../components/MathLatex/MathLatex';

describe('MathLatex Component (Offline & Security Verification)', () => {
  const originalKatex = window.katex;

  beforeEach(() => {
    delete (window as any).katex;
  });

  afterEach(() => {
    (window as any).katex = originalKatex;
  });

  it('fails gracefully and displays raw LaTeX as text when global KaTeX is absent (Section 31.U)', () => {
    render(<MathLatex latex="x^2 - 5x + 6 = 0" />);

    const el = screen.getByLabelText('x^2 - 5x + 6 = 0');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('x^2 - 5x + 6 = 0');
  });

  it('strips outer math delimiters \\(...\\) before rendering', () => {
    render(<MathLatex latex={'\\(S = \\{2, 3\\}\\)'} />);

    const el = screen.getByLabelText('S = \\{2, 3\\}');
    expect(el).toBeInTheDocument();
    expect(el.textContent).toBe('S = \\{2, 3\\}');
  });

  it('invokes window.katex.render with trust: false and throwOnError: false (Section 31.V)', () => {
    const renderSpy = vi.fn();
    (window as any).katex = {
      render: renderSpy,
      renderToString: vi.fn(),
    };

    render(<MathLatex latex="x^2 + 1 = 0" displayMode />);

    expect(renderSpy).toHaveBeenCalledTimes(1);
    expect(renderSpy).toHaveBeenCalledWith(
      'x^2 + 1 = 0',
      expect.any(HTMLElement),
      expect.objectContaining({
        displayMode: true,
        throwOnError: false,
        trust: false,
      })
    );
  });
});
