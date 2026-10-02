import {
  toMathModeFormat,
  toNaturalModeFormat,
  SUPERSCRIPT_MAP,
} from '../../utils/mathInputSerialization';

export type MathBlock =
  | { type: 'text'; id: string; value: string }
  | { type: 'power'; id: string; base: MathBlock[]; exponent: MathBlock[] }
  | { type: 'fraction'; id: string; num: MathBlock[]; den: MathBlock[] }
  | { type: 'sqrt'; id: string; radicand: MathBlock[] }
  | { type: 'nth_root'; id: string; index: MathBlock[]; radicand: MathBlock[] }
  | { type: 'derivative'; id: string; order: number; wrt: MathBlock[]; expr: MathBlock[] }
  | { type: 'integral'; id: string; isDefinite: boolean; lower?: MathBlock[]; upper?: MathBlock[]; expr: MathBlock[]; wrt: MathBlock[] }
  | { type: 'sum'; id: string; variable?: MathBlock[]; from?: MathBlock[]; to?: MathBlock[]; expr: MathBlock[] }
  | { type: 'limit'; id: string; variable?: MathBlock[]; target?: MathBlock[]; expr: MathBlock[] }
  | { type: 'vector'; id: string; items: MathBlock[][] }
  | { type: 'matrix'; id: string; rows: number; cols: number; cells: MathBlock[][][] };

let idCounter = 0;
export function genId(): string {
  idCounter += 1;
  return `mb_${Date.now()}_${idCounter}`;
}

export function createEmptyTextNode(val = ''): MathBlock {
  return { type: 'text', id: genId(), value: val };
}

export function createDefaultFraction(): MathBlock {
  return {
    type: 'fraction',
    id: genId(),
    num: [createEmptyTextNode('')],
    den: [createEmptyTextNode('')],
  };
}

export function createDefaultSqrt(): MathBlock {
  return {
    type: 'sqrt',
    id: genId(),
    radicand: [createEmptyTextNode('')],
  };
}

export function createDefaultNthRoot(indexStr = '3'): MathBlock {
  return {
    type: 'nth_root',
    id: genId(),
    index: [createEmptyTextNode(indexStr)],
    radicand: [createEmptyTextNode('')],
  };
}

export function createDefaultPower(baseStr = '', expStr = ''): MathBlock {
  return {
    type: 'power',
    id: genId(),
    base: [createEmptyTextNode(baseStr)],
    exponent: [createEmptyTextNode(expStr)],
  };
}

export function createDefaultDerivative(order = 1): MathBlock {
  return {
    type: 'derivative',
    id: genId(),
    order,
    wrt: [createEmptyTextNode('x')],
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultIntegral(isDefinite = false): MathBlock {
  return {
    type: 'integral',
    id: genId(),
    isDefinite,
    lower: isDefinite ? [createEmptyTextNode('a')] : undefined,
    upper: isDefinite ? [createEmptyTextNode('b')] : undefined,
    expr: [createEmptyTextNode('')],
    wrt: [createEmptyTextNode('x')],
  };
}

export function createDefaultSum(): MathBlock {
  return {
    type: 'sum',
    id: genId(),
    variable: [createEmptyTextNode('i')],
    from: [createEmptyTextNode('1')],
    to: [createEmptyTextNode('n')],
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultLimit(): MathBlock {
  return {
    type: 'limit',
    id: genId(),
    variable: [createEmptyTextNode('x')],
    target: [createEmptyTextNode('0')],
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultVector(size = 3): MathBlock {
  return {
    type: 'vector',
    id: genId(),
    items: Array.from({ length: size }, () => [createEmptyTextNode('')]),
  };
}

export function createDefaultMatrix(rows = 3, cols = 3): MathBlock {
  return {
    type: 'matrix',
    id: genId(),
    rows,
    cols,
    cells: Array.from({ length: rows }, () =>
      Array.from({ length: cols }, () => [createEmptyTextNode('')])
    ),
  };
}

/**
 * Recursively searches tree for node with matching ID and its parent array and index.
 */
export function findNodeAndParent(
  tree: MathBlock[],
  targetId: string,
  parentArray: MathBlock[] = tree
): { node: MathBlock; parent: MathBlock[]; index: number } | null {
  for (let i = 0; i < tree.length; i++) {
    const current = tree[i]!;
    if (current.id === targetId) {
      return { node: current, parent: parentArray, index: i };
    }

    // Traverse children slots
    if (current.type === 'fraction') {
      const inNum = findNodeAndParent(current.num, targetId, current.num);
      if (inNum) return inNum;
      const inDen = findNodeAndParent(current.den, targetId, current.den);
      if (inDen) return inDen;
    } else if (current.type === 'power') {
      const inBase = findNodeAndParent(current.base, targetId, current.base);
      if (inBase) return inBase;
      const inExp = findNodeAndParent(current.exponent, targetId, current.exponent);
      if (inExp) return inExp;
    } else if (current.type === 'sqrt') {
      const inRad = findNodeAndParent(current.radicand, targetId, current.radicand);
      if (inRad) return inRad;
    } else if (current.type === 'nth_root') {
      const inIdx = findNodeAndParent(current.index, targetId, current.index);
      if (inIdx) return inIdx;
      const inRad = findNodeAndParent(current.radicand, targetId, current.radicand);
      if (inRad) return inRad;
    } else if (current.type === 'derivative') {
      const inWrt = findNodeAndParent(current.wrt, targetId, current.wrt);
      if (inWrt) return inWrt;
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
    } else if (current.type === 'integral') {
      if (current.lower) {
        const inLow = findNodeAndParent(current.lower, targetId, current.lower);
        if (inLow) return inLow;
      }
      if (current.upper) {
        const inUp = findNodeAndParent(current.upper, targetId, current.upper);
        if (inUp) return inUp;
      }
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
      const inWrt = findNodeAndParent(current.wrt, targetId, current.wrt);
      if (inWrt) return inWrt;
    } else if (current.type === 'sum') {
      if (current.variable) {
        const inVar = findNodeAndParent(current.variable, targetId, current.variable);
        if (inVar) return inVar;
      }
      if (current.from) {
        const inFrom = findNodeAndParent(current.from, targetId, current.from);
        if (inFrom) return inFrom;
      }
      if (current.to) {
        const inTo = findNodeAndParent(current.to, targetId, current.to);
        if (inTo) return inTo;
      }
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
    } else if (current.type === 'limit') {
      if (current.variable) {
        const inVar = findNodeAndParent(current.variable, targetId, current.variable);
        if (inVar) return inVar;
      }
      if (current.target) {
        const inTgt = findNodeAndParent(current.target, targetId, current.target);
        if (inTgt) return inTgt;
      }
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
    } else if (current.type === 'vector') {
      for (const item of current.items) {
        const inItem = findNodeAndParent(item, targetId, item);
        if (inItem) return inItem;
      }
    } else if (current.type === 'matrix') {
      for (const row of current.cells) {
        for (const cell of row) {
          const inCell = findNodeAndParent(cell, targetId, cell);
          if (inCell) return inCell;
        }
      }
    }
  }

  return null;
}

/**
 * Recursively finds the enclosing composite template block that contains a given child text/slot ID.
 */
export function findEnclosingBlockAndParent(
  tree: MathBlock[],
  childId: string,
  parentArray: MathBlock[] = tree
): { enclosingBlock: MathBlock; parent: MathBlock[]; index: number } | null {
  for (let i = 0; i < tree.length; i++) {
    const block = tree[i]!;

    if (block.type === 'fraction') {
      if (findNodeAndParent(block.num, childId) || findNodeAndParent(block.den, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'power') {
      if (findNodeAndParent(block.base, childId) || findNodeAndParent(block.exponent, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'sqrt') {
      if (findNodeAndParent(block.radicand, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'nth_root') {
      if (findNodeAndParent(block.index, childId) || findNodeAndParent(block.radicand, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'derivative') {
      if (findNodeAndParent(block.wrt, childId) || findNodeAndParent(block.expr, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'integral') {
      if (
        findNodeAndParent(block.expr, childId) ||
        findNodeAndParent(block.wrt, childId) ||
        (block.lower && findNodeAndParent(block.lower, childId)) ||
        (block.upper && findNodeAndParent(block.upper, childId))
      ) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'sum') {
      if (
        findNodeAndParent(block.expr, childId) ||
        (block.variable && findNodeAndParent(block.variable, childId)) ||
        (block.from && findNodeAndParent(block.from, childId)) ||
        (block.to && findNodeAndParent(block.to, childId))
      ) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'limit') {
      if (
        findNodeAndParent(block.expr, childId) ||
        (block.variable && findNodeAndParent(block.variable, childId)) ||
        (block.target && findNodeAndParent(block.target, childId))
      ) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'vector') {
      for (const it of block.items) {
        if (findNodeAndParent(it, childId)) {
          return { enclosingBlock: block, parent: parentArray, index: i };
        }
      }
    } else if (block.type === 'matrix') {
      for (const row of block.cells) {
        for (const cell of row) {
          if (findNodeAndParent(cell, childId)) {
            return { enclosingBlock: block, parent: parentArray, index: i };
          }
        }
      }
    }
  }

  return null;
}

/**
 * Finds the first editable text node inside a MathBlock tree/subtree.
 */
export function findFirstTextNodeId(block: MathBlock | MathBlock[]): string | null {

  const list = Array.isArray(block) ? block : [block];
  for (const b of list) {
    if (b.type === 'text') return b.id;
    if (b.type === 'fraction') return findFirstTextNodeId(b.num) || findFirstTextNodeId(b.den);
    if (b.type === 'power') return findFirstTextNodeId(b.base) || findFirstTextNodeId(b.exponent);
    if (b.type === 'sqrt') return findFirstTextNodeId(b.radicand);
    if (b.type === 'nth_root') return findFirstTextNodeId(b.radicand) || findFirstTextNodeId(b.index);
    if (b.type === 'derivative') return findFirstTextNodeId(b.expr) || findFirstTextNodeId(b.wrt);
    if (b.type === 'integral') return findFirstTextNodeId(b.expr) || findFirstTextNodeId(b.wrt);
    if (b.type === 'sum') return findFirstTextNodeId(b.expr);
    if (b.type === 'limit') return findFirstTextNodeId(b.expr);
    if (b.type === 'vector' && b.items[0]) return findFirstTextNodeId(b.items[0]);
    if (b.type === 'matrix' && b.cells[0]?.[0]) return findFirstTextNodeId(b.cells[0][0]);
  }
  return null;
}

/**
 * Parses a raw or math formatted string into interactive MathBlocks.
 */
export function parseStringToBlocks(input: string): MathBlock[] {
  if (!input || !input.trim()) {
    return [createEmptyTextNode('')];
  }

  const formatted = toMathModeFormat(input);
  const blocks: MathBlock[] = [];
  let remaining = formatted;

  while (remaining.length > 0) {
    // 1. Fraction: \frac{num}{den} or (num)/(den)
    const fracMatch =
      remaining.match(/^\\frac\{([^}]*)\}\{([^}]*)\}/) ||
      remaining.match(/^\(([^)]*)\)\/\(([^)]*)\)/);
    if (fracMatch) {
      blocks.push({
        type: 'fraction',
        id: genId(),
        num: parseStringToBlocks(fracMatch[1] ?? ''),
        den: parseStringToBlocks(fracMatch[2] ?? ''),
      });
      remaining = remaining.slice(fracMatch[0].length);
      continue;
    }

    // 2. Derivative: d/dx(...) or d²/dx²(...)
    const derivMatch = remaining.match(/^d(\^?2?|²?)\/d([a-zA-Z0-9]+)(\^?2?|²?)\(([^)]*)\)/);
    if (derivMatch) {
      blocks.push({
        type: 'derivative',
        id: genId(),
        order: derivMatch[1] === '2' || derivMatch[1] === '²' ? 2 : 1,
        wrt: parseStringToBlocks(derivMatch[2] ?? 'x'),
        expr: parseStringToBlocks(derivMatch[4] ?? ''),
      });
      remaining = remaining.slice(derivMatch[0].length);
      continue;
    }

    // 3. Nth root: \sqrt[n]{rad} or ³√(rad)
    const nthRootMatch =
      remaining.match(/^³√\(([^)]*)\)/) || remaining.match(/^\\sqrt\[([^\]]*)\]\{([^}]*)\}/);
    if (nthRootMatch) {
      const isCube = nthRootMatch[0].startsWith('³√');
      blocks.push({
        type: 'nth_root',
        id: genId(),
        index: parseStringToBlocks(isCube ? '3' : nthRootMatch[1] ?? 'n'),
        radicand: parseStringToBlocks(isCube ? nthRootMatch[1] ?? '' : nthRootMatch[2] ?? ''),
      });
      remaining = remaining.slice(nthRootMatch[0].length);
      continue;
    }

    // 4. Square root: \sqrt{rad} or sqrt(rad) or √(rad)
    const sqrtMatch =
      remaining.match(/^\\sqrt\{([^}]*)\}/) ||
      remaining.match(/^sqrt\(([^)]*)\)/) ||
      remaining.match(/^√\(([^)]*)\)/);
    if (sqrtMatch) {
      blocks.push({
        type: 'sqrt',
        id: genId(),
        radicand: parseStringToBlocks(sqrtMatch[1] ?? ''),
      });
      remaining = remaining.slice(sqrtMatch[0].length);
      continue;
    }

    // 5. Plain text segment up to next special 2D block or end
    const nextSpecial = remaining.search(/(\\frac|\\sqrt|sqrt\(|√\(|d\/dx|d²\/dx²)/);
    if (nextSpecial === -1) {
      blocks.push(createEmptyTextNode(remaining));
      break;
    } else if (nextSpecial === 0) {
      blocks.push(createEmptyTextNode(remaining[0] ?? ''));
      remaining = remaining.slice(1);
    } else {
      blocks.push(createEmptyTextNode(remaining.slice(0, nextSpecial)));
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

  return merged.length > 0 ? merged : [createEmptyTextNode('')];
}

/**
 * Serializes MathBlocks into a backend-compatible raw equation (e.g. x^2 - 5*x + 6 = 0).
 */
export function blocksToRawSolverString(blocks: MathBlock[]): string {
  let res = '';
  for (const b of blocks) {
    switch (b.type) {
      case 'text':
        res += toNaturalModeFormat(b.value);
        break;
      case 'power':
        res += `(${blocksToRawSolverString(b.base)})^(${blocksToRawSolverString(b.exponent)})`;
        break;
      case 'fraction':
        res += `(${blocksToRawSolverString(b.num)})/(${blocksToRawSolverString(b.den)})`;
        break;
      case 'sqrt':
        res += `sqrt(${blocksToRawSolverString(b.radicand)})`;
        break;
      case 'nth_root':
        res += `(${blocksToRawSolverString(b.radicand)})^(1/${blocksToRawSolverString(b.index)})`;
        break;
      case 'derivative':
        res += `d/d${blocksToRawSolverString(b.wrt)}(${blocksToRawSolverString(b.expr)})`;
        break;
      case 'integral':
        res += b.isDefinite
          ? `int_${blocksToRawSolverString(b.lower || [])}^${blocksToRawSolverString(b.upper || [])} (${blocksToRawSolverString(b.expr)}) d${blocksToRawSolverString(b.wrt)}`
          : `int (${blocksToRawSolverString(b.expr)}) d${blocksToRawSolverString(b.wrt)}`;
        break;
      case 'sum':
        res += `sum_${blocksToRawSolverString(b.variable || [])}=${blocksToRawSolverString(b.from || [])}^${blocksToRawSolverString(b.to || [])} (${blocksToRawSolverString(b.expr)})`;
        break;
      case 'limit':
        res += `lim_${blocksToRawSolverString(b.variable || [])}->${blocksToRawSolverString(b.target || [])} (${blocksToRawSolverString(b.expr)})`;
        break;
      case 'vector':
        res += `[${b.items.map((it) => blocksToRawSolverString(it)).join(', ')}]`;
        break;
      case 'matrix':
        res += `[${b.cells.map((row) => `[${row.map((c) => blocksToRawSolverString(c)).join(', ')}]`).join(', ')}]`;
        break;
    }
  }

  res = res.replace(/−/g, '-');
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
      case 'power': {
        const baseStr = blocksToVisualString(b.base);
        const expStr = blocksToVisualString(b.exponent);
        if (expStr && SUPERSCRIPT_MAP[expStr]) {
          res += `${baseStr}${SUPERSCRIPT_MAP[expStr]}`;
        } else if (!expStr) {
          res += `${baseStr}²`;
        } else {
          res += `${baseStr}^${expStr}`;
        }
        break;
      }
      case 'fraction':
        res += `(${blocksToVisualString(b.num)})/(${blocksToVisualString(b.den)})`;
        break;
      case 'sqrt':
        res += `√(${blocksToVisualString(b.radicand)})`;
        break;
      case 'nth_root':
        res += `${blocksToVisualString(b.index)}√(${blocksToVisualString(b.radicand)})`;
        break;
      case 'derivative':
        res += `d/d${blocksToVisualString(b.wrt)}(${blocksToVisualString(b.expr)})`;
        break;
      case 'integral':
        res += b.isDefinite
          ? `∫_${blocksToVisualString(b.lower || [])}^${blocksToVisualString(b.upper || [])} ${blocksToVisualString(b.expr)} d${blocksToVisualString(b.wrt)}`
          : `∫ ${blocksToVisualString(b.expr)} d${blocksToVisualString(b.wrt)}`;
        break;
      case 'sum':
        res += `∑ ${blocksToVisualString(b.expr)}`;
        break;
      case 'limit':
        res += `lim ${blocksToVisualString(b.expr)}`;
        break;
      case 'vector':
        res += `[${b.items.map((it) => blocksToVisualString(it)).join(', ')}]`;
        break;
      case 'matrix':
        res += `[${b.cells.map((row) => `[${row.map((c) => blocksToVisualString(c)).join(', ')}]`).join(', ')}]`;
        break;
    }
  }
  return res;
}
