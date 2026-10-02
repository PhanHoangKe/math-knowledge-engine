import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CoefficientEditorPanel } from '../components/CoefficientEditorPanel/CoefficientEditorPanel';
import { PreferencesProvider } from '../state/preferences';
import {
  validateCoefficientsDraft,
  draftToRationalPayload,
  hydrateDraftFromBackend,
  type CoefficientsDraft,
} from '../utils/coefficients';

describe('CoefficientEditorPanel & utils/coefficients (Section 34)', () => {
  const defaultDraft: CoefficientsDraft = {
    a: { numeratorStr: '1', denominatorStr: '1' },
    b: { numeratorStr: '-5', denominatorStr: '1' },
    c: { numeratorStr: '6', denominatorStr: '1' },
  };

  it('validates strictly valid integers without reducing fractions', () => {
    const draft: CoefficientsDraft = {
      a: { numeratorStr: '2', denominatorStr: '4' },
      b: { numeratorStr: '-6', denominatorStr: '2' },
      c: { numeratorStr: '0', denominatorStr: '1' },
    };

    const { isValid, errors } = validateCoefficientsDraft(draft);
    expect(isValid).toBe(true);
    expect(Object.keys(errors)).toHaveLength(0);

    const payload = draftToRationalPayload(draft);
    expect(payload).not.toBeNull();
    // Must preserve exact unreduced rational fractions
    expect(payload?.a).toEqual({ numerator: 2, denominator: 4 });
    expect(payload?.b).toEqual({ numerator: -6, denominator: 2 });
    expect(payload?.c).toEqual({ numerator: 0, denominator: 1 });
  });

  it('rejects empty, non-integer, negative or zero denominator, and unsafe integers', () => {
    // Empty field
    const emptyDraft: CoefficientsDraft = {
      a: { numeratorStr: '', denominatorStr: '1' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(emptyDraft).errors.a_numerator).toBe('err_coeff_empty');

    // Float string
    const floatDraft: CoefficientsDraft = {
      a: { numeratorStr: '1.5', denominatorStr: '1' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(floatDraft).errors.a_numerator).toBe('err_coeff_invalid_int');

    // Non-numeric string
    const abcDraft: CoefficientsDraft = {
      a: { numeratorStr: 'abc', denominatorStr: '1' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(abcDraft).errors.a_numerator).toBe('err_coeff_invalid_int');

    // Zero denominator
    const zeroDenomDraft: CoefficientsDraft = {
      a: { numeratorStr: '1', denominatorStr: '0' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(zeroDenomDraft).errors.a_denominator).toBe('err_coeff_denominator_positive');

    // Negative denominator
    const negDenomDraft: CoefficientsDraft = {
      a: { numeratorStr: '1', denominatorStr: '-2' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(negDenomDraft).errors.a_denominator).toBe('err_coeff_invalid_positive_int');

    // Unsafe integer > Number.MAX_SAFE_INTEGER
    const unsafeDraft: CoefficientsDraft = {
      a: { numeratorStr: '9007199254740992', denominatorStr: '1' },
      b: { numeratorStr: '1', denominatorStr: '1' },
      c: { numeratorStr: '1', denominatorStr: '1' },
    };
    expect(validateCoefficientsDraft(unsafeDraft).errors.a_numerator).toBe('err_coeff_unsafe_integer');
  });

  it('hydrates draft from backend canonical rational fractions correctly', () => {
    const hydrated = hydrateDraftFromBackend(
      { numerator: 3, denominator: 2 },
      { numerator: -7, denominator: 1 },
      { numerator: 12, denominator: 5 }
    );
    expect(hydrated.a).toEqual({ numeratorStr: '3', denominatorStr: '2' });
    expect(hydrated.b).toEqual({ numeratorStr: '-7', denominatorStr: '1' });
    expect(hydrated.c).toEqual({ numeratorStr: '12', denominatorStr: '5' });
  });

  it('renders inputs, triggers onUpdateField and onReset callback', () => {
    const handleUpdate = vi.fn();
    const handleReset = vi.fn();

    render(
      <PreferencesProvider>
        <CoefficientEditorPanel
          draft={defaultDraft}
          errors={{}}
          reactiveStatus="idle"
          sourceMode="COEFFICIENTS"
          onUpdateField={handleUpdate}
          onReset={handleReset}
        />
      </PreferencesProvider>
    );

    // Verify all 6 input fields exist
    expect(screen.getByTestId('coeff-a-num')).toHaveValue('1');
    expect(screen.getByTestId('coeff-a-den')).toHaveValue('1');
    expect(screen.getByTestId('coeff-b-num')).toHaveValue('-5');
    expect(screen.getByTestId('coeff-b-den')).toHaveValue('1');
    expect(screen.getByTestId('coeff-c-num')).toHaveValue('6');
    expect(screen.getByTestId('coeff-c-den')).toHaveValue('1');

    // Change c numerator
    const cNumInput = screen.getByTestId('coeff-c-num');
    fireEvent.change(cNumInput, { target: { value: '7' } });
    expect(handleUpdate).toHaveBeenCalledWith('c', 'numerator', '7');

    // Click reset button
    const resetBtn = screen.getByTestId('reset-coeffs-btn');
    fireEvent.click(resetBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });

  it('renders validation error messages and reactive status badges', () => {
    const { rerender } = render(
      <PreferencesProvider>
        <CoefficientEditorPanel
          draft={defaultDraft}
          errors={{ c_numerator: 'err_coeff_invalid_int' }}
          reactiveStatus="invalid"
          sourceMode="COEFFICIENTS"
          onUpdateField={vi.fn()}
          onReset={vi.fn()}
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('error-c-num')).toBeInTheDocument();
    expect(screen.getByTestId('reactive-status')).toBeInTheDocument();

    // Rerender with debouncing status
    rerender(
      <PreferencesProvider>
        <CoefficientEditorPanel
          draft={defaultDraft}
          errors={{}}
          reactiveStatus="debouncing"
          sourceMode="RAW_TEXT"
          onUpdateField={vi.fn()}
          onReset={vi.fn()}
        />
      </PreferencesProvider>
    );

    expect(screen.getByTestId('reactive-status')).toBeInTheDocument();
    expect(screen.getByTestId('coefficient-editor-panel')).toBeInTheDocument();
  });
});
