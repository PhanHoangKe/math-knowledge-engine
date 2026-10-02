/**
 * Presentation Formatters for MKE Frontend.
 * 
 * STRICT COMPLIANCE:
 * These helpers perform DISPLAY FORMATTING ONLY.
 * They do NOT perform arithmetic, sign changes, or fraction simplification.
 * Backend canonical numbers remain authoritative.
 */

import type { RationalFraction } from '../api/contract';

/**
 * Format a backend RationalFraction for human-readable display.
 * e.g. denominator === 1 -> "5", denominator !== 1 -> "5/6"
 */
export function formatRational(frac: RationalFraction | null | undefined): string {
  if (!frac) return '0';
  if (frac.denominator === 1) {
    return `${frac.numerator}`;
  }
  return `${frac.numerator}/${frac.denominator}`;
}

/**
 * Format a backend RationalFraction for LaTeX rendering.
 * e.g. denominator === 1 -> "5", denominator !== 1 -> "\frac{5}{6}"
 */
export function formatRationalLatex(frac: RationalFraction | null | undefined): string {
  if (!frac) return '0';
  if (frac.denominator === 1) {
    return `${frac.numerator}`;
  }
  return `\\frac{${frac.numerator}}{${frac.denominator}}`;
}
