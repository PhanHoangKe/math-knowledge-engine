import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PreferencesProvider } from '../state/preferences';
import { EquationInputShell } from '../components/EquationInputShell/EquationInputShell';
import {
  insertSnippet,
  handleBackspace,
  toVisualLatex,
  toMathModeFormat,
  toNaturalModeFormat,
  normalizeForSolver,
  isSupportedByComposer,
  serializePaletteAction,
} from '../utils/mathInputSerialization';

describe('MathInputComposer & Serialization Utilities', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('mathInputSerialization pure utility functions', () => {
    it('insertSnippet inserts text at cursor and returns new cursor position', () => {
      const res = insertSnippet('x + 1', '^2', { start: 1, end: 1 });
      expect(res.newQuery).toBe('x^2 + 1');
      expect(res.newCursorPos).toBe(3);
    });

    it('insertSnippet replaces selection range', () => {
      const res = insertSnippet('x + 1', 'y', { start: 0, end: 1 });
      expect(res.newQuery).toBe('y + 1');
      expect(res.newCursorPos).toBe(1);
    });

    it('handleBackspace deletes character before cursor', () => {
      const res = handleBackspace('x² − 5', { start: 3, end: 3 });
      expect(res.newQuery).toBe('x²− 5');
      expect(res.newCursorPos).toBe(2);
    });

    it('handleBackspace deletes entire active selection', () => {
      const res = handleBackspace('x^2 - 5', { start: 1, end: 3 });
      expect(res.newQuery).toBe('x - 5');
      expect(res.newCursorPos).toBe(1);
    });

    it('toMathModeFormat and toNaturalModeFormat convert bidirectionally', () => {
      const raw = 'x^2 - 5*x + 6 = 0';
      const math = toMathModeFormat(raw);
      expect(math).toBe('x² − 5x + 6 = 0');

      const convertedBack = toNaturalModeFormat(math);
      expect(convertedBack).toBe('x^2 - 5*x + 6 = 0');
    });

    it('normalizeForSolver normalizes math input to backend grammar', () => {
      expect(normalizeForSolver('x² − 5x + 6 = 0')).toBe('x^2 - 5*x + 6 = 0');
      expect(normalizeForSolver('2x² − 4x + 2 = 0')).toBe('2*x^2 - 4*x + 2 = 0');
      expect(normalizeForSolver('Power[x,2] - 5*x + 6 = 0')).toBe('x^2 - 5*x + 6 = 0');
    });

    it('serializePaletteAction maps math operators deterministically', () => {
      expect(serializePaletteAction('', 'VAR_X').newQuery).toBe('x');
      expect(serializePaletteAction('', 'SQUARE').newQuery).toBe('x²');
      expect(serializePaletteAction('x', 'SQUARE', { start: 1, end: 1 }).newQuery).toBe('x²');
      expect(serializePaletteAction('', 'POWER').newQuery).toBe('^');
      expect(serializePaletteAction('', 'FRACTION').newQuery).toBe('(/)');
      expect(serializePaletteAction('', 'PLUS').newQuery).toBe(' + ');
      expect(serializePaletteAction('', 'MINUS').newQuery).toBe(' − ');
      expect(serializePaletteAction('', 'MULTIPLY').newQuery).toBe('*');
      expect(serializePaletteAction('', 'DIVIDE').newQuery).toBe('/');
      expect(serializePaletteAction('', 'EQUALS').newQuery).toBe(' = ');
      expect(serializePaletteAction('', 'LPAREN').newQuery).toBe('(');
      expect(serializePaletteAction('', 'RPAREN').newQuery).toBe(')');
      expect(serializePaletteAction('', 'DIGIT_7').newQuery).toBe('7');
      expect(serializePaletteAction('', 'DOT').newQuery).toBe('.');
    });

    it('toVisualLatex formats raw strings into LaTeX', () => {
      expect(toVisualLatex('x^2 - 5*x + 6 = 0')).toBe('x^{2} - 5x + 6 = 0');
      expect(toVisualLatex('x² − 5x + 6 = 0')).toBe('x^{2} - 5x + 6 = 0');
      expect(toVisualLatex('3/4*x^2')).toBe('\\frac{3}{4} \\cdot x^{2}');
      expect(toVisualLatex('(2/3)*x')).toBe('(\\frac{2}{3}) \\cdot x');
    });

    it('isSupportedByComposer detects basic algebra and flags unsupported special tokens', () => {
      expect(isSupportedByComposer('x^2 - 5*x + 6 = 0')).toBe(true);
      expect(isSupportedByComposer('(1/2)*x^2 + 3*x - 4 = 0')).toBe(true);
      expect(isSupportedByComposer('\\sin(x) = 0')).toBe(false);
      expect(isSupportedByComposer('tan(x) = 0')).toBe(false);
    });
  });

  describe('<EquationInputShell /> Dual-Mode Composer UI', () => {
    it('renders Natural Language mode by default with tabs and input box', () => {
      const onQueryChange = vi.fn();
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      render(
        <PreferencesProvider>
          <EquationInputShell
            query="x^2 - 5*x + 6 = 0"
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      expect(screen.getByTestId('mode-quick-btn')).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('mode-math-btn')).toHaveAttribute('aria-selected', 'false');
      expect(screen.queryByTestId('math-palette')).not.toBeInTheDocument();
    });

    it('switches to Math Input mode and formats directly to x² − 5x + 6 = 0', () => {
      const onQueryChange = vi.fn();
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      render(
        <PreferencesProvider>
          <EquationInputShell
            query="x^2 - 5*x + 6 = 0"
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      const mathTab = screen.getByTestId('mode-math-btn');
      fireEvent.click(mathTab);

      expect(mathTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('mode-quick-btn')).toHaveAttribute('aria-selected', 'false');
      expect(screen.getByTestId('math-palette')).toBeInTheDocument();
      expect(onQueryChange).toHaveBeenCalledWith('x² − 5x + 6 = 0');
    });

    it('clicking palette category tabs and buttons inserts deterministic symbols and updates query', () => {
      let queryValue = '';
      const onQueryChange = vi.fn((val: string) => {
        queryValue = val;
      });
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      const { rerender } = render(
        <PreferencesProvider>
          <EquationInputShell
            query={queryValue}
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      // Switch to Math mode
      fireEvent.click(screen.getByTestId('mode-math-btn'));

      // Click the Algebra category tab (√)
      const algebraCategoryBtn = screen.getByTitle('Đại số & Căn thức');
      fireEvent.click(algebraCategoryBtn);

      // Click 'x'
      const btnX = screen.getByTestId('palette-btn-VAR_X');
      fireEvent.click(btnX);
      expect(onQueryChange).toHaveBeenCalledWith('x');

      // Update props and click 'x²'
      queryValue = 'x';
      rerender(
        <PreferencesProvider>
          <EquationInputShell
            query={queryValue}
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      const btnSquare = screen.getByTestId('palette-btn-SQUARE');
      fireEvent.click(btnSquare);
      expect(onQueryChange).toHaveBeenCalledWith('x²');
    });

    it('clicking fraction button creates Casio 2-tier interactive slots', () => {
      let queryValue = '';
      const onQueryChange = vi.fn((val: string) => {
        queryValue = val;
      });
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      render(
        <PreferencesProvider>
          <EquationInputShell
            query={queryValue}
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      // Switch to Math mode
      fireEvent.click(screen.getByTestId('mode-math-btn'));

      // Click Fraction button (□/□)
      const btnFraction = screen.getByTestId('palette-btn-FRACTION');
      fireEvent.click(btnFraction);

      expect(onQueryChange).toHaveBeenCalledWith('()/()');
    });

    it('clicking Clear button in palette or input shell calls onClear', () => {
      const onQueryChange = vi.fn();
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      render(
        <PreferencesProvider>
          <EquationInputShell
            query="x^2 - 4 = 0"
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
          />
        </PreferencesProvider>
      );

      // Switch to math mode
      fireEvent.click(screen.getByTestId('mode-math-btn'));

      // Click CLEAR palette button
      const clearBtn = screen.getByTestId('palette-btn-CLEAR');
      fireEvent.click(clearBtn);

      expect(onClear).toHaveBeenCalled();
    });

    it('palette buttons are disabled when isLoading is true', () => {
      const onQueryChange = vi.fn();
      const onSubmit = vi.fn();
      const onClear = vi.fn();

      render(
        <PreferencesProvider>
          <EquationInputShell
            query="x^2 - 4 = 0"
            onQueryChange={onQueryChange}
            onSubmit={onSubmit}
            onClear={onClear}
            isLoading={true}
          />
        </PreferencesProvider>
      );

      // Switch to math mode
      fireEvent.click(screen.getByTestId('mode-math-btn'));

      const btnFraction = screen.getByTestId('palette-btn-FRACTION');
      expect(btnFraction).toBeDisabled();
      const btnCompute = screen.getByTestId('compute-btn');
      expect(btnCompute).toBeDisabled();
    });
  });
});
