/**
 * Math Input Serialization & Visual Formatting Utilities.
 * 
 * Provides deterministic mapping between visual math representations
 * and backend-safe RAW_TEXT expressions.
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

  // Check if character before cursor is part of a surrogate pair or multi-char token
  const before = query.slice(0, start - 1);
  const after = query.slice(start);
  return { newQuery: before + after, newCursorPos: start - 1 };
}

/**
 * Converts a raw / natural language expression into clean Mathematical visual format.
 * Example: 'x^2 - 5*x + 6 = 0' -> 'x² − 5x + 6 = 0'
 */
export function toMathModeFormat(query: string): string {
  if (!query) return '';
  let res = query;

  // Convert Power[x,2] or Power(x,2) to x²
  res = res.replace(/Power\[([a-zA-Z0-9]+),\s*2\]/g, '$1²');
  res = res.replace(/Power\(([a-zA-Z0-9]+),\s*2\)/g, '$1²');

  // Convert x^2 -> x², x^3 -> x³, x^0 -> x⁰
  res = res.replace(/([a-zA-Z0-9]+)\^2/g, '$1²');
  res = res.replace(/([a-zA-Z0-9]+)\^3/g, '$1³');
  res = res.replace(/([a-zA-Z0-9]+)\^0/g, '$1⁰');

  // Convert 5*x -> 5x
  res = res.replace(/(\d+)\s*\*\s*([a-zA-Z])/g, '$1$2');

  // Convert standard minus to mathematical minus −
  res = res.replace(/\s+-\s+/g, ' − ');
  res = res.replace(/^-\s*/g, '−');

  return res;
}

/**
 * Converts a Math Mode expression (e.g. 'x² − 5x + 6 = 0') into standard Natural / Raw expression (e.g. 'x^2 - 5*x + 6 = 0').
 */
export function toNaturalModeFormat(query: string): string {
  if (!query) return '';
  let res = query;

  // Convert unicode superscripts: x² -> x^2, x³ -> x^3, x⁰ -> x^0
  res = res.replace(/²([a-zA-Z0-9]*)/g, '^2$1');
  res = res.replace(/³([a-zA-Z0-9]*)/g, '^3$1');
  res = res.replace(/⁰([a-zA-Z0-9]*)/g, '^0$1');

  // Convert mathematical minus − to standard minus -
  res = res.replace(/−/g, '-');

  // Convert Power[x, 2] or Power(x, 2) to x^2
  res = res.replace(/Power\[([a-zA-Z0-9]+),\s*([0-9]+)\]/g, '$1^$2');
  res = res.replace(/Power\(([a-zA-Z0-9]+),\s*([0-9]+)\)/g, '$1^$2');

  // Convert Sqrt[x] or Sqrt(x) to sqrt(x)
  res = res.replace(/Sqrt\[([^\]]+)\]/g, 'sqrt($1)');
  res = res.replace(/Sqrt\(([^)]+)\)/g, 'sqrt($1)');

  // Convert implicit multiplication 5x -> 5*x
  res = res.replace(/(\d+)([a-zA-Z])/g, '$1*$2');

  return res;
}

/**
 * Normalizes any math or natural language string before sending to backend solver.
 */
export function normalizeForSolver(query: string): string {
  if (!query) return '';
  let res = toNaturalModeFormat(query);
  // Replace unicode minus or symbols
  res = res.replace(/−/g, '-');
  res = res.replace(/×/g, '*');
  res = res.replace(/÷/g, '/');
  // Ensure explicit multiplication 5x -> 5*x
  res = res.replace(/(\d+)([a-zA-Z])/g, '$1*$2');
  // Clean up any double spaces
  res = res.replace(/\s+/g, ' ');
  return res.trim();
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
      const start = selection?.start ?? query.length;
      const charBefore = start > 0 ? query[start - 1] : '';
      const snippet = charBefore === 'x' ? '²' : 'x²';
      return insertSnippet(query, snippet, selection);
    }
    case 'POWER':
      return insertSnippet(query, '^', selection);
    case 'SQRT':
      return insertSnippet(query, '√()', selection);
    case 'CUBE_ROOT':
      return insertSnippet(query, '³√()', selection);
    case 'NTH_ROOT':
      return insertSnippet(query, 'ⁿ√()', selection);
    case 'DERIVATIVE':
      return insertSnippet(query, 'd/dx()', selection);
    case 'SECOND_DERIVATIVE':
      return insertSnippet(query, 'd²/dx²()', selection);
    case 'INTEGRAL':
      return insertSnippet(query, '∫ ', selection);
    case 'DEF_INTEGRAL':
      return insertSnippet(query, '∫_a^b ', selection);
    case 'SUM':
      return insertSnippet(query, '∑ ', selection);
    case 'LIMIT':
      return insertSnippet(query, 'lim ', selection);
    case 'VECTOR':
      return insertSnippet(query, '[x, y]', selection);
    case 'MATRIX':
      return insertSnippet(query, '[[a, b], [c, d]]', selection);
    case 'MULTIPLY':
      return insertSnippet(query, '*', selection);
    case 'DIVIDE':
      return insertSnippet(query, '/', selection);
    case 'PLUS':
      return insertSnippet(query, ' + ', selection);
    case 'MINUS':
      return insertSnippet(query, ' − ', selection);
    case 'EQUALS':
      return insertSnippet(query, ' = ', selection);
    case 'VAR_X':
      return insertSnippet(query, 'x', selection);
    case 'VAR_Y':
      return insertSnippet(query, 'y', selection);
    case 'PLUS_MINUS':
      return insertSnippet(query, '±', selection);
    case 'DELTA':
      return insertSnippet(query, 'Δ', selection);
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
    // Greek symbols
    case 'ALPHA': return insertSnippet(query, 'α', selection);
    case 'BETA': return insertSnippet(query, 'β', selection);
    case 'GAMMA': return insertSnippet(query, 'γ', selection);
    case 'THETA': return insertSnippet(query, 'θ', selection);
    case 'LAMBDA': return insertSnippet(query, 'λ', selection);
    case 'MU': return insertSnippet(query, 'μ', selection);
    case 'PI': return insertSnippet(query, 'π', selection);
    case 'SIGMA': return insertSnippet(query, 'σ', selection);
    case 'OMEGA': return insertSnippet(query, 'ω', selection);
    // Functions
    case 'SIN': return insertSnippet(query, 'sin()', selection);
    case 'COS': return insertSnippet(query, 'cos()', selection);
    case 'TAN': return insertSnippet(query, 'tan()', selection);
    case 'LOG': return insertSnippet(query, 'log()', selection);
    case 'LN': return insertSnippet(query, 'ln()', selection);
    case 'EXP': return insertSnippet(query, 'exp()', selection);
    case 'PLOT': return insertSnippet(query, 'plot ', selection);
    default:
      if (actionId.startsWith('DIGIT_')) {
        const digit = actionId.replace('DIGIT_', '');
        return insertSnippet(query, digit, selection);
      }
      return insertSnippet(query, actionId, selection);
  }
}

/**
 * Converts a raw backend expression into clean visual LaTeX for rendering.
 */
export function toVisualLatex(query: string): string {
  if (!query || !query.trim()) {
    return '';
  }

  let latex = toNaturalModeFormat(query.trim());

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
