/**
 * Math Input Serialization & Visual Formatting Utilities.
 * 
 * Provides deterministic mapping between visual math representations
 * and backend-safe RAW_TEXT expressions.
 * 
 * Invariants:
 * - Deterministic serialization to standard MKE backend raw format (e.g. x^2 - 5*x + 6 = 0).
 * - Multiplications × serialize to * for the backend parser.
 * - Visual formatting creates clean LaTeX without altering mathematical semantics.
 * - Cursor-aware snippet insertion and deletion.
 */

export interface CursorSelection {
  start: number;
  end: number;
}

export interface SerializationResult {
  newQuery: string;
  newCursorPos: number;
}

/**
 * Inserts a snippet into current query at cursor position, or at the end if no selection provided.
 */
export function insertSnippet(
  query: string,
  snippet: string,
  selection?: CursorSelection
): SerializationResult {
  const start = selection?.start ?? query.length;
  const end = selection?.end ?? query.length;

  const before = query.slice(0, start);
  const after = query.slice(end);

  const newQuery = before + snippet + after;
  const newCursorPos = start + snippet.length;

  return { newQuery, newCursorPos };
}

/**
 * Handles backspace deletion at cursor position.
 */
export function handleBackspace(
  query: string,
  selection?: CursorSelection
): SerializationResult {
  const start = selection?.start ?? query.length;
  const end = selection?.end ?? query.length;

  if (start !== end) {
    // Range selected: delete range
    const before = query.slice(0, start);
    const after = query.slice(end);
    return { newQuery: before + after, newCursorPos: start };
  }

  if (start <= 0) {
    return { newQuery: query, newCursorPos: 0 };
  }

  // Single character before cursor
  const before = query.slice(0, start - 1);
  const after = query.slice(start);
  return { newQuery: before + after, newCursorPos: start - 1 };
}

/**
 * Handles specialized palette actions like squaring, fractions, operators.
 */
export function serializePaletteAction(
  query: string,
  actionId: string,
  selection?: CursorSelection
): SerializationResult {
  switch (actionId) {
    case 'SQUARE': {
      // If cursor is right after 'x', insert '^2', otherwise insert 'x^2'
      const start = selection?.start ?? query.length;
      const charBefore = start > 0 ? query[start - 1] : '';
      const snippet = charBefore === 'x' ? '^2' : 'x^2';
      return insertSnippet(query, snippet, selection);
    }
    case 'POWER':
      return insertSnippet(query, '^', selection);
    case 'MULTIPLY':
      return insertSnippet(query, '*', selection);
    case 'DIVIDE':
      return insertSnippet(query, '/', selection);
    case 'PLUS':
      return insertSnippet(query, ' + ', selection);
    case 'MINUS':
      return insertSnippet(query, ' - ', selection);
    case 'EQUALS':
      return insertSnippet(query, ' = ', selection);
    case 'VAR_X':
      return insertSnippet(query, 'x', selection);
    case 'LPAREN':
      return insertSnippet(query, '(', selection);
    case 'RPAREN':
      return insertSnippet(query, ')', selection);
    case 'DOT':
      return insertSnippet(query, '.', selection);
    case 'FRACTION': {
      // Fraction template: (/) with cursor placed between ( and /
      const start = selection?.start ?? query.length;
      const res = insertSnippet(query, '(/)', selection);
      return { newQuery: res.newQuery, newCursorPos: start + 1 };
    }
    case 'CLEAR':
      return { newQuery: '', newCursorPos: 0 };
    case 'BACKSPACE':
      return handleBackspace(query, selection);
    default:
      if (actionId.startsWith('DIGIT_')) {
        const digit = actionId.replace('DIGIT_', '');
        return insertSnippet(query, digit, selection);
      }
      return insertSnippet(query, actionId, selection);
  }
}

/**
 * Converts a raw backend expression into clean visual LaTeX for live KaTeX preview.
 * 
 * Example:
 * 'x^2 - 5*x + 6 = 0' -> 'x^{2} - 5x + 6 = 0'
 * '3*x^2 + 2/3*x = 0' -> '3x^{2} + \\frac{2}{3}x = 0'
 */
export function toVisualLatex(query: string): string {
  if (!query || !query.trim()) {
    return '';
  }

  let latex = query.trim();

  // Normalize duplicate spaces
  latex = latex.replace(/\s+/g, ' ');

  // Format power expressions: ^(\d+) or ^\d+ -> ^{n}
  latex = latex.replace(/\^([0-9a-zA-Z]+)/g, '^{$1}');

  // Convert simple numerical fractions: (\d+)/(\d+) or \d+/\d+ into \frac{a}{b}
  latex = latex.replace(/(\d+)\s*\/\s*(\d+)/g, '\\frac{$1}{$2}');

  // Remove explicit * before variable x: 5*x -> 5x, or replace isolated * with \cdot
  latex = latex.replace(/(\d+)\s*\*\s*([a-zA-Z])/g, '$1$2');
  latex = latex.replace(/\s*\*\s*/g, ' \\cdot ');

  // Clean up binary operator spacing in LaTeX
  latex = latex.replace(/\s*\+\s*/g, ' + ');
  latex = latex.replace(/\s*-\s*/g, ' - ');
  latex = latex.replace(/\s*=\s*/g, ' = ');

  return latex;
}

/**
 * Validates whether an expression can be safely represented and edited in assisted mode.
 */
export function isSupportedByComposer(query: string): boolean {
  if (!query) return true;
  // Disallow unsupported advanced multi-variable or complex matrix structures
  const unsupportedPatterns = [
    /\bsin\b/i,
    /\bcos\b/i,
    /\btan\b/i,
    /\blog\b/i,
    /\bln\b/i,
    /\bint\b/i,
    /\bdet\b/i,
  ];
  return !unsupportedPatterns.some((pattern) => pattern.test(query));
}
