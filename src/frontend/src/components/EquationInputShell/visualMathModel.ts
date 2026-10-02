/**
 * Visual Math AST Model & Parser for WolframAlpha / Casio style interactive math editor.
 */

export type MathBlock =
  | { type: 'text'; id: string; value: string }
  | { type: 'power'; id: string; base: string; exponent: string }
  | { type: 'fraction'; id: string; num: string; den: string }
  | { type: 'sqrt'; id: string; radicand: string }
  | { type: 'nth_root'; id: string; index: string; radicand: string }
  | { type: 'derivative'; id: string; order: number; wrt: string; expr: string }
  | { type: 'integral'; id: string; isDefinite: boolean; lower?: string; upper?: string; expr: string; wrt: string }
  | { type: 'sum'; id: string; variable: string; from: string; to: string; expr: string }
  | { type: 'limit'; id: string; variable: string; target: string; expr: string }
  | { type: 'vector'; id: string; items: string[] };

let idCounter = 0;
export function genId(): string {
  idCounter += 1;
  return `mb_${Date.now()}_${idCounter}`;
}

/**
 * Parses a raw or math formatted string into interactive MathBlocks.
 */
export function parseStringToBlocks(input: string): MathBlock[] {
  if (!input || !input.trim()) {
    return [{ type: 'text', id: genId(), value: '' }];
  }

  const blocks: MathBlock[] = [];
  let remaining = input;

  // Regex patterns
  // Fraction: \frac{num}{den} or (num)/(den)
  // Power: ([a-zA-Z0-9]+)\^([0-9a-zA-Z]+) or ([a-zA-Z0-9]+)²
  // Sqrt: \sqrt{rad} or sqrt(rad) or √(rad)
  // Derivative: d/dx(expr)
  // Integral: int_a^b (expr) dx

  while (remaining.length > 0) {
    // 1. Check for fraction: \frac{num}{den} or (num)/(den)
    const fracMatch = remaining.match(/^\\frac\{([^}]*)\}\{([^}]*)\}/) || remaining.match(/^\(([^)]*)\)\/\(([^)]*)\)/);
    if (fracMatch) {
      blocks.push({
        type: 'fraction',
        id: genId(),
        num: fracMatch[1] ?? '',
        den: fracMatch[2] ?? '',
      });
      remaining = remaining.slice(fracMatch[0].length);
      continue;
    }

    // 2. Check for derivative: d/dx(...) or d²/dx²(...)
    const derivMatch = remaining.match(/^d(\^?2?)\/d([a-zA-Z0-9]+)\^?2?\(([^)]*)\)/);
    if (derivMatch) {
      blocks.push({
        type: 'derivative',
        id: genId(),
        order: derivMatch[1] ? 2 : 1,
        wrt: derivMatch[2] ?? 'x',
        expr: derivMatch[3] ?? '',
      });
      remaining = remaining.slice(derivMatch[0].length);
      continue;
    }

    // 3. Check for nth root: \sqrt[n]{rad} or ³√(rad)
    const nthRootMatch = remaining.match(/^³√\(([^)]*)\)/) || remaining.match(/^\\sqrt\[([^\]]*)\]\{([^}]*)\}/);
    if (nthRootMatch) {
      const isCube = nthRootMatch[0].startsWith('³√');
      blocks.push({
        type: 'nth_root',
        id: genId(),
        index: isCube ? '3' : nthRootMatch[1] ?? 'n',
        radicand: isCube ? (nthRootMatch[1] ?? '') : (nthRootMatch[2] ?? ''),
      });
      remaining = remaining.slice(nthRootMatch[0].length);
      continue;
    }

    // 4. Check for square root: \sqrt{rad} or sqrt(rad) or √(rad)
    const sqrtMatch = remaining.match(/^\\sqrt\{([^}]*)\}/) || remaining.match(/^sqrt\(([^)]*)\)/) || remaining.match(/^√\(([^)]*)\)/);
    if (sqrtMatch) {
      blocks.push({
        type: 'sqrt',
        id: genId(),
        radicand: sqrtMatch[1] ?? '',
      });
      remaining = remaining.slice(sqrtMatch[0].length);
      continue;
    }

    // 5. Check for power: ([a-zA-Z0-9]+)\^([0-9a-zA-Z]+) or Power[x,2] or x²
    const powerMatch =
      remaining.match(/^Power\[([a-zA-Z0-9]+),\s*([0-9a-zA-Z]+)\]/) ||
      remaining.match(/^([a-zA-Z0-9]+)\^([0-9a-zA-Z]+)/) ||
      remaining.match(/^([a-zA-Z0-9]+)(²|³|⁰)/);

    if (powerMatch) {
      const base = powerMatch[1] ?? 'x';
      let exponent = powerMatch[2] ?? '2';
      if (exponent === '²') exponent = '2';
      if (exponent === '³') exponent = '3';
      if (exponent === '⁰') exponent = '0';

      blocks.push({
        type: 'power',
        id: genId(),
        base,
        exponent,
      });
      remaining = remaining.slice(powerMatch[0].length);
      continue;
    }

    // 6. Otherwise consume plain text up to next special block or end
    const nextSpecial = remaining.search(/(\\frac|\(|\^|²|³|Power|\\sqrt|sqrt|√|d\/dx)/);
    if (nextSpecial === -1) {
      // Consume all remaining text
      blocks.push({
        type: 'text',
        id: genId(),
        value: remaining,
      });
      break;
    } else if (nextSpecial === 0) {
      // Single character token fallback
      blocks.push({
        type: 'text',
        id: genId(),
        value: remaining[0] ?? '',
      });
      remaining = remaining.slice(1);
    } else {
      blocks.push({
        type: 'text',
        id: genId(),
        value: remaining.slice(0, nextSpecial),
      });
      remaining = remaining.slice(nextSpecial);
    }
  }

  // Merge adjacent text blocks
  const merged: MathBlock[] = [];
  for (const b of blocks) {
    if (b.type === 'text' && merged.length > 0 && merged[merged.length - 1]?.type === 'text') {
      const prev = merged[merged.length - 1] as { type: 'text'; id: string; value: string };
      prev.value += b.value;
    } else {
      merged.push(b);
    }
  }

  return merged.length > 0 ? merged : [{ type: 'text', id: genId(), value: '' }];
}

/**
 * Serializes MathBlocks into a backend-compatible raw equation (e.g. x^2 - 5*x + 6 = 0).
 */
export function blocksToRawSolverString(blocks: MathBlock[]): string {
  let res = '';
  for (const b of blocks) {
    switch (b.type) {
      case 'text':
        res += b.value;
        break;
      case 'power':
        res += b.exponent ? `${b.base}^${b.exponent}` : `${b.base}^2`;
        break;
      case 'fraction':
        res += `(${b.num})/(${b.den})`;
        break;
      case 'sqrt':
        res += `sqrt(${b.radicand})`;
        break;
      case 'nth_root':
        res += `(${b.radicand})^(1/${b.index || '2'})`;
        break;
      case 'derivative':
        res += `d/d${b.wrt}(${b.expr})`;
        break;
      case 'integral':
        res += b.isDefinite
          ? `int_${b.lower || '0'}^${b.upper || '1'} (${b.expr}) d${b.wrt}`
          : `int (${b.expr}) d${b.wrt}`;
        break;
      case 'sum':
        res += `sum_${b.variable}=${b.from}^${b.to} (${b.expr})`;
        break;
      case 'limit':
        res += `lim_${b.variable}->${b.target} (${b.expr})`;
        break;
      case 'vector':
        res += `[${b.items.join(', ')}]`;
        break;
    }
  }

  // Convert unicode minus − to -
  res = res.replace(/−/g, '-');
  // Ensure explicit multiplication e.g. 5x -> 5*x
  res = res.replace(/(\d+)([a-zA-Z])/g, '$1*$2');
  return res.trim();
}

/**
 * Serializes MathBlocks into visual string for display in Math mode.
 */
export function blocksToVisualString(blocks: MathBlock[]): string {
  let res = '';
  for (const b of blocks) {
    switch (b.type) {
      case 'text':
        res += b.value;
        break;
      case 'power':
        if (b.exponent === '2' || !b.exponent) res += `${b.base}²`;
        else if (b.exponent === '3') res += `${b.base}³`;
        else if (b.exponent === '0') res += `${b.base}⁰`;
        else res += `${b.base}^${b.exponent}`;
        break;
      case 'fraction':
        res += `(${b.num})/(${b.den})`;
        break;
      case 'sqrt':
        res += `√(${b.radicand})`;
        break;
      case 'nth_root':
        res += `${b.index}√(${b.radicand})`;
        break;
      case 'derivative':
        res += `d/d${b.wrt}(${b.expr})`;
        break;
      case 'integral':
        res += b.isDefinite ? `∫_${b.lower}^${b.upper} ${b.expr} d${b.wrt}` : `∫ ${b.expr} d${b.wrt}`;
        break;
      case 'sum':
        res += `∑ ${b.expr}`;
        break;
      case 'limit':
        res += `lim ${b.expr}`;
        break;
      case 'vector':
        res += `[${b.items.join(', ')}]`;
        break;
    }
  }
  return res;
}
