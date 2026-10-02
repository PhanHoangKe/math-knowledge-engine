/**
 * MKE MVP V1 — Coefficient Input Validation & Conversion Utilities.
 * 
 * Strict input serialization and safe-integer guards only.
 * Contains ZERO mathematical solving, GCD, fraction reduction, or sign normalization.
 */

import type { RationalFraction } from '../api/contract';
import type { TranslationKey } from '../i18n/vi';

export const COEFFICIENT_EDIT_DEBOUNCE_MS = 350;

export interface CoefficientDraft {
  numeratorStr: string;
  denominatorStr: string;
}

export interface CoefficientsDraft {
  a: CoefficientDraft;
  b: CoefficientDraft;
  c: CoefficientDraft;
}

export type CoefficientFieldKey =
  | 'a_numerator'
  | 'a_denominator'
  | 'b_numerator'
  | 'b_denominator'
  | 'c_numerator'
  | 'c_denominator';

export interface FieldValidationResult {
  isValid: boolean;
  errorKey?: TranslationKey;
}

export type CoefficientsValidationErrors = Partial<Record<CoefficientFieldKey, TranslationKey>>;

/**
 * Validate an integer string input according to safe-integer constraints.
 * 
 * Allowed:
 * - Integer lexical string (optional leading '-', followed by decimal digits).
 * - Safe integer within Number.MIN_SAFE_INTEGER..Number.MAX_SAFE_INTEGER.
 * - For denominator: strictly positive integer >= 1.
 * 
 * Forbidden:
 * - Decimals, scientific notation, whitespace inside, NaN, Infinity, unsafe integers.
 */
export function validateIntegerString(
  input: string,
  mustBePositive: boolean = false
): FieldValidationResult {
  const trimmed = input.trim();
  if (!trimmed) {
    return { isValid: false, errorKey: 'err_coeff_empty' };
  }

  // Lexical integer validation
  if (mustBePositive) {
    if (!/^\d+$/.test(trimmed)) {
      return { isValid: false, errorKey: 'err_coeff_invalid_positive_int' };
    }
  } else {
    if (!/^-?\d+$/.test(trimmed)) {
      return { isValid: false, errorKey: 'err_coeff_invalid_int' };
    }
  }

  const num = Number(trimmed);
  if (!Number.isFinite(num) || !Number.isSafeInteger(num)) {
    return { isValid: false, errorKey: 'err_coeff_unsafe_integer' };
  }

  if (mustBePositive && num < 1) {
    return { isValid: false, errorKey: 'err_coeff_denominator_positive' };
  }

  return { isValid: true };
}

/**
 * Validate all six draft fields of a quadratic problem.
 */
export function validateCoefficientsDraft(draft: CoefficientsDraft): {
  isValid: boolean;
  errors: CoefficientsValidationErrors;
} {
  const errors: CoefficientsValidationErrors = {};

  const aNumVal = validateIntegerString(draft.a.numeratorStr, false);
  if (!aNumVal.isValid) errors.a_numerator = aNumVal.errorKey;

  const aDenVal = validateIntegerString(draft.a.denominatorStr, true);
  if (!aDenVal.isValid) errors.a_denominator = aDenVal.errorKey;

  const bNumVal = validateIntegerString(draft.b.numeratorStr, false);
  if (!bNumVal.isValid) errors.b_numerator = bNumVal.errorKey;

  const bDenVal = validateIntegerString(draft.b.denominatorStr, true);
  if (!bDenVal.isValid) errors.b_denominator = bDenVal.errorKey;

  const cNumVal = validateIntegerString(draft.c.numeratorStr, false);
  if (!cNumVal.isValid) errors.c_numerator = cNumVal.errorKey;

  const cDenVal = validateIntegerString(draft.c.denominatorStr, true);
  if (!cDenVal.isValid) errors.c_denominator = cDenVal.errorKey;

  const isValid = Object.keys(errors).length === 0;
  return { isValid, errors };
}

/**
 * Convert a valid draft to exact RationalFraction representations without client math.
 */
export function draftToRationalPayload(draft: CoefficientsDraft): {
  a: RationalFraction;
  b: RationalFraction;
  c: RationalFraction;
} {
  return {
    a: {
      numerator: Number(draft.a.numeratorStr.trim()),
      denominator: Number(draft.a.denominatorStr.trim()),
    },
    b: {
      numerator: Number(draft.b.numeratorStr.trim()),
      denominator: Number(draft.b.denominatorStr.trim()),
    },
    c: {
      numerator: Number(draft.c.numeratorStr.trim()),
      denominator: Number(draft.c.denominatorStr.trim()),
    },
  };
}

/**
 * Hydrate a draft from backend RationalFraction objects.
 */
export function hydrateDraftFromBackend(
  a: RationalFraction | undefined,
  b: RationalFraction,
  c: RationalFraction
): CoefficientsDraft {
  return {
    a: {
      numeratorStr: a ? String(a.numerator) : '0',
      denominatorStr: a ? String(a.denominator) : '1',
    },
    b: {
      numeratorStr: String(b.numerator),
      denominatorStr: String(b.denominator),
    },
    c: {
      numeratorStr: String(c.numerator),
      denominatorStr: String(c.denominator),
    },
  };
}
