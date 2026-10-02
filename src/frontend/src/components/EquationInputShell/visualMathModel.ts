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
  | { type: 'derivative'; id: string; order: number; isPartial?: boolean; wrt: MathBlock[]; wrt2?: MathBlock[]; expr: MathBlock[] }
  | { type: 'integral'; id: string; isDefinite: boolean; multiplicity?: number; lower?: MathBlock[]; upper?: MathBlock[]; lower2?: MathBlock[]; upper2?: MathBlock[]; lower3?: MathBlock[]; upper3?: MathBlock[]; expr: MathBlock[]; wrt: MathBlock[]; wrt2?: MathBlock[]; wrt3?: MathBlock[] }
  | { type: 'sum'; id: string; isProduct?: boolean; variable?: MathBlock[]; from?: MathBlock[]; to?: MathBlock[]; expr: MathBlock[] }
  | { type: 'limit'; id: string; direction?: 'both' | 'left' | 'right'; is2D?: boolean; variable?: MathBlock[]; target?: MathBlock[]; variable2?: MathBlock[]; target2?: MathBlock[]; expr: MathBlock[] }
  | { type: 'abs'; id: string; content: MathBlock[] }
  | { type: 'log_base'; id: string; base: MathBlock[]; expr: MathBlock[] }
  | { type: 'piecewise'; id: string; rows: number; cases: { expr: MathBlock[]; condition: MathBlock[] }[] }
  | { type: 'transform'; id: string; transformType: 'laplace' | 'inv_laplace' | 'fourier' | 'inv_fourier'; wrt?: MathBlock[]; expr: MathBlock[] }
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

export function createDefaultNthRoot(indexStr = ''): MathBlock {
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

export function createDefaultDerivative(order = 1, isPartial = false, isMixed = false): MathBlock {
  return {
    type: 'derivative',
    id: genId(),
    order,
    isPartial,
    wrt: [createEmptyTextNode('x')],
    wrt2: isMixed ? [createEmptyTextNode('y')] : undefined,
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultIntegral(isDefinite = false, multiplicity = 1): MathBlock {
  return {
    type: 'integral',
    id: genId(),
    isDefinite,
    multiplicity,
    lower: isDefinite ? [createEmptyTextNode('a')] : undefined,
    upper: isDefinite ? [createEmptyTextNode('b')] : undefined,
    lower2: isDefinite && multiplicity >= 2 ? [createEmptyTextNode('c')] : undefined,
    upper2: isDefinite && multiplicity >= 2 ? [createEmptyTextNode('d')] : undefined,
    lower3: isDefinite && multiplicity >= 3 ? [createEmptyTextNode('e')] : undefined,
    upper3: isDefinite && multiplicity >= 3 ? [createEmptyTextNode('f')] : undefined,
    expr: [createEmptyTextNode('')],
    wrt: [createEmptyTextNode('x')],
    wrt2: multiplicity >= 2 ? [createEmptyTextNode('y')] : undefined,
    wrt3: multiplicity >= 3 ? [createEmptyTextNode('z')] : undefined,
  };
}

export function createDefaultSum(isProduct = false): MathBlock {
  return {
    type: 'sum',
    id: genId(),
    isProduct,
    variable: [createEmptyTextNode('i')],
    from: [createEmptyTextNode('1')],
    to: [createEmptyTextNode('n')],
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultLimit(direction: 'both' | 'left' | 'right' = 'both', is2D = false): MathBlock {
  return {
    type: 'limit',
    id: genId(),
    direction,
    is2D,
    variable: [createEmptyTextNode('x')],
    target: [createEmptyTextNode('0')],
    variable2: is2D ? [createEmptyTextNode('y')] : undefined,
    target2: is2D ? [createEmptyTextNode('0')] : undefined,
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultAbs(): MathBlock {
  return {
    type: 'abs',
    id: genId(),
    content: [createEmptyTextNode('')],
  };
}

export function createDefaultLogBase(baseStr = ''): MathBlock {
  return {
    type: 'log_base',
    id: genId(),
    base: [createEmptyTextNode(baseStr)],
    expr: [createEmptyTextNode('')],
  };
}

export function createDefaultPiecewise(rows = 2): MathBlock {
  return {
    type: 'piecewise',
    id: genId(),
    rows,
    cases: Array.from({ length: rows }, () => ({
      expr: [createEmptyTextNode('')],
      condition: [createEmptyTextNode('')],
    })),
  };
}

export function createDefaultTransform(transformType: 'laplace' | 'inv_laplace' | 'fourier' | 'inv_fourier'): MathBlock {
  const defWrt = transformType.startsWith('laplace') ? 't' : 'x';
  return {
    type: 'transform',
    id: genId(),
    transformType,
    wrt: [createEmptyTextNode(defWrt)],
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
      if (current.wrt2) {
        const inWrt2 = findNodeAndParent(current.wrt2, targetId, current.wrt2);
        if (inWrt2) return inWrt2;
      }
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
      if (current.lower2) {
        const inLow2 = findNodeAndParent(current.lower2, targetId, current.lower2);
        if (inLow2) return inLow2;
      }
      if (current.upper2) {
        const inUp2 = findNodeAndParent(current.upper2, targetId, current.upper2);
        if (inUp2) return inUp2;
      }
      if (current.lower3) {
        const inLow3 = findNodeAndParent(current.lower3, targetId, current.lower3);
        if (inLow3) return inLow3;
      }
      if (current.upper3) {
        const inUp3 = findNodeAndParent(current.upper3, targetId, current.upper3);
        if (inUp3) return inUp3;
      }
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
      const inWrt = findNodeAndParent(current.wrt, targetId, current.wrt);
      if (inWrt) return inWrt;
      if (current.wrt2) {
        const inWrt2 = findNodeAndParent(current.wrt2, targetId, current.wrt2);
        if (inWrt2) return inWrt2;
      }
      if (current.wrt3) {
        const inWrt3 = findNodeAndParent(current.wrt3, targetId, current.wrt3);
        if (inWrt3) return inWrt3;
      }
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
      if (current.variable2) {
        const inVar2 = findNodeAndParent(current.variable2, targetId, current.variable2);
        if (inVar2) return inVar2;
      }
      if (current.target2) {
        const inTgt2 = findNodeAndParent(current.target2, targetId, current.target2);
        if (inTgt2) return inTgt2;
      }
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
    } else if (current.type === 'abs') {
      const inContent = findNodeAndParent(current.content, targetId, current.content);
      if (inContent) return inContent;
    } else if (current.type === 'log_base') {
      const inBase = findNodeAndParent(current.base, targetId, current.base);
      if (inBase) return inBase;
      const inExpr = findNodeAndParent(current.expr, targetId, current.expr);
      if (inExpr) return inExpr;
    } else if (current.type === 'piecewise') {
      for (const c of current.cases) {
        const inExpr = findNodeAndParent(c.expr, targetId, c.expr);
        if (inExpr) return inExpr;
        const inCond = findNodeAndParent(c.condition, targetId, c.condition);
        if (inCond) return inCond;
      }
    } else if (current.type === 'transform') {
      if (current.wrt) {
        const inWrt = findNodeAndParent(current.wrt, targetId, current.wrt);
        if (inWrt) return inWrt;
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
      if (
        findNodeAndParent(block.wrt, childId) ||
        (block.wrt2 && findNodeAndParent(block.wrt2, childId)) ||
        findNodeAndParent(block.expr, childId)
      ) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'integral') {
      if (
        findNodeAndParent(block.expr, childId) ||
        findNodeAndParent(block.wrt, childId) ||
        (block.wrt2 && findNodeAndParent(block.wrt2, childId)) ||
        (block.wrt3 && findNodeAndParent(block.wrt3, childId)) ||
        (block.lower && findNodeAndParent(block.lower, childId)) ||
        (block.upper && findNodeAndParent(block.upper, childId)) ||
        (block.lower2 && findNodeAndParent(block.lower2, childId)) ||
        (block.upper2 && findNodeAndParent(block.upper2, childId)) ||
        (block.lower3 && findNodeAndParent(block.lower3, childId)) ||
        (block.upper3 && findNodeAndParent(block.upper3, childId))
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
        (block.target && findNodeAndParent(block.target, childId)) ||
        (block.variable2 && findNodeAndParent(block.variable2, childId)) ||
        (block.target2 && findNodeAndParent(block.target2, childId))
      ) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'abs') {
      if (findNodeAndParent(block.content, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'log_base') {
      if (findNodeAndParent(block.base, childId) || findNodeAndParent(block.expr, childId)) {
        return { enclosingBlock: block, parent: parentArray, index: i };
      }
    } else if (block.type === 'piecewise') {
      for (const c of block.cases) {
        if (findNodeAndParent(c.expr, childId) || findNodeAndParent(c.condition, childId)) {
          return { enclosingBlock: block, parent: parentArray, index: i };
        }
      }
    } else if (block.type === 'transform') {
      if ((block.wrt && findNodeAndParent(block.wrt, childId)) || findNodeAndParent(block.expr, childId)) {
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
    if (b.type === 'abs') return findFirstTextNodeId(b.content);
    if (b.type === 'log_base') return findFirstTextNodeId(b.expr) || findFirstTextNodeId(b.base);
    if (b.type === 'piecewise') return findFirstTextNodeId(b.cases[0]?.expr || []);
    if (b.type === 'transform') return findFirstTextNodeId(b.expr);
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
        res += `(${blocksToRawSolverString(b.radicand)})^(1/(${blocksToRawSolverString(b.index)}))`;
        break;
      case 'derivative':
        if (b.wrt2) {
          res += `D(${blocksToRawSolverString(b.expr)}, ${blocksToRawSolverString(b.wrt)}, ${blocksToRawSolverString(b.wrt2)})`;
        } else if (b.order === 2) {
          res += `D(${blocksToRawSolverString(b.expr)}, {${blocksToRawSolverString(b.wrt)}, 2})`;
        } else {
          res += `d/d${blocksToRawSolverString(b.wrt)}(${blocksToRawSolverString(b.expr)})`;
        }
        break;
      case 'integral': {
        const wrtStr = blocksToRawSolverString(b.wrt);
        const wrt2Str = b.wrt2 ? blocksToRawSolverString(b.wrt2) : '';
        const wrt3Str = b.wrt3 ? blocksToRawSolverString(b.wrt3) : '';
        if (b.isDefinite) {
          if (b.multiplicity === 3) {
            res += `Integrate(${blocksToRawSolverString(b.expr)}, {${wrtStr}, ${blocksToRawSolverString(b.lower || [])}, ${blocksToRawSolverString(b.upper || [])}}, {${wrt2Str}, ${blocksToRawSolverString(b.lower2 || [])}, ${blocksToRawSolverString(b.upper2 || [])}}, {${wrt3Str}, ${blocksToRawSolverString(b.lower3 || [])}, ${blocksToRawSolverString(b.upper3 || [])}})`;
          } else if (b.multiplicity === 2) {
            res += `Integrate(${blocksToRawSolverString(b.expr)}, {${wrtStr}, ${blocksToRawSolverString(b.lower || [])}, ${blocksToRawSolverString(b.upper || [])}}, {${wrt2Str}, ${blocksToRawSolverString(b.lower2 || [])}, ${blocksToRawSolverString(b.upper2 || [])}})`;
          } else {
            res += `int_${blocksToRawSolverString(b.lower || [])}^${blocksToRawSolverString(b.upper || [])} (${blocksToRawSolverString(b.expr)}) d${wrtStr}`;
          }
        } else {
          if (b.multiplicity === 3) {
            res += `int (${blocksToRawSolverString(b.expr)}) d${wrtStr} d${wrt2Str} d${wrt3Str}`;
          } else if (b.multiplicity === 2) {
            res += `int (${blocksToRawSolverString(b.expr)}) d${wrtStr} d${wrt2Str}`;
          } else {
            res += `int (${blocksToRawSolverString(b.expr)}) d${wrtStr}`;
          }
        }
        break;
      }
      case 'sum':
        res += b.isProduct
          ? `product_${blocksToRawSolverString(b.variable || [])}=${blocksToRawSolverString(b.from || [])}^${blocksToRawSolverString(b.to || [])} (${blocksToRawSolverString(b.expr)})`
          : `sum_${blocksToRawSolverString(b.variable || [])}=${blocksToRawSolverString(b.from || [])}^${blocksToRawSolverString(b.to || [])} (${blocksToRawSolverString(b.expr)})`;
        break;
      case 'limit':
        if (b.is2D) {
          res += `lim_(${blocksToRawSolverString(b.variable || [])},${blocksToRawSolverString(b.variable2 || [])})->(${blocksToRawSolverString(b.target || [])},${blocksToRawSolverString(b.target2 || [])}) (${blocksToRawSolverString(b.expr)})`;
        } else {
          const dirSuffix = b.direction === 'left' ? '-' : b.direction === 'right' ? '+' : '';
          res += `lim_${blocksToRawSolverString(b.variable || [])}->${blocksToRawSolverString(b.target || [])}${dirSuffix} (${blocksToRawSolverString(b.expr)})`;
        }
        break;
      case 'abs':
        res += `Abs(${blocksToRawSolverString(b.content)})`;
        break;
      case 'log_base': {
        const baseStr = blocksToRawSolverString(b.base).trim();
        const exprStr = blocksToRawSolverString(b.expr);
        if (baseStr === '10') {
          res += `log10(${exprStr})`;
        } else if (!baseStr || baseStr === 'e') {
          res += `ln(${exprStr})`;
        } else {
          res += `log(${exprStr}, ${baseStr})`;
        }
        break;
      }
      case 'piecewise':
        res += `Piecewise([${b.cases.map((c) => `[${blocksToRawSolverString(c.expr)}, ${blocksToRawSolverString(c.condition)}]`).join(', ')}])`;
        break;
      case 'transform': {
        const exprStr = blocksToRawSolverString(b.expr);
        const wrtStr = blocksToRawSolverString(b.wrt || []);
        if (b.transformType === 'laplace') res += `LaplaceTransform(${exprStr}, ${wrtStr}, s)`;
        else if (b.transformType === 'inv_laplace') res += `InverseLaplaceTransform(${exprStr}, s, ${wrtStr})`;
        else if (b.transformType === 'fourier') res += `FourierTransform(${exprStr}, ${wrtStr}, w)`;
        else if (b.transformType === 'inv_fourier') res += `InverseFourierTransform(${exprStr}, w, ${wrtStr})`;
        break;
      }
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
        res += b.isProduct ? `∏ ${blocksToVisualString(b.expr)}` : `∑ ${blocksToVisualString(b.expr)}`;
        break;
      case 'limit':
        res += `lim ${blocksToVisualString(b.expr)}`;
        break;
      case 'abs':
        res += `|${blocksToVisualString(b.content)}|`;
        break;
      case 'log_base':
        res += `log_${blocksToVisualString(b.base)}(${blocksToVisualString(b.expr)})`;
        break;
      case 'piecewise':
        res += `{ ${b.cases.map((c) => `${blocksToVisualString(c.expr)}, ${blocksToVisualString(c.condition)}`).join('; ')}`;
        break;
      case 'transform':
        res += `${b.transformType}(${blocksToVisualString(b.expr)})`;
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
