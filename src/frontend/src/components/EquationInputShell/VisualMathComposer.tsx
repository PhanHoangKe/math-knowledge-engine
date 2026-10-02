import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import {
  MathBlock,
  parseStringToBlocks,
  blocksToVisualString,
  findNodeAndParent,
  findEnclosingBlockAndParent,
  findFirstTextNodeId,
  createEmptyTextNode,
  createDefaultFraction,
  createDefaultSqrt,
  createDefaultNthRoot,
  createDefaultPower,
  createDefaultDerivative,
  createDefaultIntegral,
  createDefaultSum,
  createDefaultLimit,
  createDefaultVector,
  createDefaultMatrix,
} from './visualMathModel';
import { toMathModeFormat } from '../../utils/mathInputSerialization';
import styles from './VisualMathComposer.module.css';

export interface VisualMathComposerHandle {
  insertPaletteAction: (actionId: string) => void;
  clear: () => void;
  focus: () => void;
}

export interface VisualMathComposerProps {
  rawQuery: string;
  onChange: (newRawQuery: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  'data-testid'?: string;
}

export const VisualMathComposer = forwardRef<VisualMathComposerHandle, VisualMathComposerProps>(
  (
    {
      rawQuery,
      onChange,
      onSubmit,
      disabled = false,
      placeholder = 'x² − 5x + 6 = 0',
      'data-testid': testId = 'visual-math-composer',
    },
    ref
  ) => {
    const [blocks, setBlocks] = useState<MathBlock[]>(() => parseStringToBlocks(rawQuery));
    const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const inputRefs = useRef<Map<string, HTMLInputElement>>(new Map());

    // Synchronize local blocks if external rawQuery changes drastically
    useEffect(() => {
      const currentVisual = blocksToVisualString(blocks);
      const cleanedCurrent = currentVisual.replace(/\s+/g, '');
      const cleanedIncoming = rawQuery.replace(/\s+/g, '');

      if (cleanedCurrent !== cleanedIncoming) {
        setBlocks(parseStringToBlocks(rawQuery));
      }
    }, [rawQuery]);

    const setInputRef = (key: string, el: HTMLInputElement | null) => {
      if (el) {
        inputRefs.current.set(key, el);
      } else {
        inputRefs.current.delete(key);
      }
    };

    const notifyChange = (updatedBlocks: MathBlock[]) => {
      setBlocks(updatedBlocks);
      const visual = blocksToVisualString(updatedBlocks);
      onChange(visual);
    };

    // Expose imperative handle for palette actions and external controls
    useImperativeHandle(ref, () => ({
      clear: () => {
        const initial = [createEmptyTextNode('')];
        setBlocks(initial);
        onChange('');
      },
      focus: () => {
        const firstKey = Array.from(inputRefs.current.keys())[0];
        if (firstKey) {
          inputRefs.current.get(firstKey)?.focus();
        }
      },
      insertPaletteAction: (actionId: string) => {
        handleApplyPaletteAction(actionId);
      },
    }));

    const updateTextNode = (textId: string, newValue: string) => {
      const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
      const res = findNodeAndParent(cloned, textId);
      if (res && res.node.type === 'text') {
        res.node.value = newValue;
        notifyChange(cloned);
      }
    };

    const handleApplyPaletteAction = (actionId: string) => {
      if (actionId === 'CLEAR') {
        const initial = [createEmptyTextNode('')];
        notifyChange(initial);
        return;
      }

      let templateToInsert: MathBlock | null = null;
      let preferBaseFocus = false;

      switch (actionId) {
        case 'FRACTION':
          templateToInsert = createDefaultFraction();
          break;
        case 'SQUARE': {
          const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
          const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
          const res = findNodeAndParent(cloned, targetId);
          if (res && res.node.type === 'text') {
            if (
              res.node.value &&
              !res.node.value.endsWith(' ') &&
              !res.node.value.endsWith('+') &&
              !res.node.value.endsWith('-') &&
              !res.node.value.endsWith('−') &&
              !res.node.value.endsWith('=')
            ) {
              res.node.value += '²';
              notifyChange(cloned);
              return;
            }
          }
          templateToInsert = createDefaultPower('', '2');
          preferBaseFocus = true;
          break;
        }
        case 'POWER': {
          const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
          const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
          const res = findNodeAndParent(cloned, targetId);
          if (res && res.node.type === 'text' && res.node.value) {
            const match = res.node.value.match(/([a-zA-Z0-9_]+)$/);
            if (match) {
              const baseStr = match[1]!;
              res.node.value = res.node.value.slice(0, res.node.value.length - baseStr.length);
              templateToInsert = createDefaultPower(baseStr, '');
              insertBlockAtFocus(templateToInsert, false);
              return;
            }
          }
          templateToInsert = createDefaultPower('', '');
          preferBaseFocus = true;
          break;
        }
        case 'EXP_POW':
          templateToInsert = createDefaultPower('e', '');
          break;
        case 'SQRT':
          templateToInsert = createDefaultSqrt();
          break;
        case 'CUBE_ROOT':
          templateToInsert = createDefaultNthRoot('3');
          break;
        case 'NTH_ROOT':
          templateToInsert = createDefaultNthRoot('');
          preferBaseFocus = true;
          break;
        case 'ABS':
          templateToInsert = createDefaultAbs();
          break;
        case 'LN':
          templateToInsert = createDefaultLogBase('');
          break;
        case 'LOG_10':
          templateToInsert = createDefaultLogBase('10');
          break;
        case 'LOG_BASE':
          templateToInsert = createDefaultLogBase('');
          preferBaseFocus = true;
          break;
        case 'DERIVATIVE':
          templateToInsert = createDefaultDerivative(1, false, false);
          break;
        case 'SECOND_DERIVATIVE':
          templateToInsert = createDefaultDerivative(2, false, false);
          break;
        case 'PARTIAL':
          templateToInsert = createDefaultDerivative(1, true, false);
          break;
        case 'SECOND_PARTIAL':
          templateToInsert = createDefaultDerivative(2, true, false);
          break;
        case 'MIXED_PARTIAL':
          templateToInsert = createDefaultDerivative(2, true, true);
          break;
        case 'INTEGRAL':
          templateToInsert = createDefaultIntegral(false, 1);
          break;
        case 'DOUBLE_INT':
          templateToInsert = createDefaultIntegral(false, 2);
          break;
        case 'TRIPLE_INT':
          templateToInsert = createDefaultIntegral(false, 3);
          break;
        case 'DEF_INTEGRAL':
          templateToInsert = createDefaultIntegral(true, 1);
          break;
        case 'DEF_DOUBLE_INT':
          templateToInsert = createDefaultIntegral(true, 2);
          break;
        case 'DEF_TRIPLE_INT':
          templateToInsert = createDefaultIntegral(true, 3);
          break;
        case 'SUM':
          templateToInsert = createDefaultSum(false);
          break;
        case 'PRODUCT':
          templateToInsert = createDefaultSum(true);
          break;
        case 'LIMIT':
          templateToInsert = createDefaultLimit('both', false);
          break;
        case 'LIMIT_LEFT':
          templateToInsert = createDefaultLimit('left', false);
          break;
        case 'LIMIT_RIGHT':
          templateToInsert = createDefaultLimit('right', false);
          break;
        case 'LIMIT_2D':
          templateToInsert = createDefaultLimit('both', true);
          break;
        case 'PIECEWISE_2':
          templateToInsert = createDefaultPiecewise(2);
          break;
        case 'PIECEWISE_3':
          templateToInsert = createDefaultPiecewise(3);
          break;
        case 'LAPLACE':
          templateToInsert = createDefaultTransform('laplace');
          break;
        case 'INV_LAPLACE':
          templateToInsert = createDefaultTransform('inv_laplace');
          break;
        case 'FOURIER':
          templateToInsert = createDefaultTransform('fourier');
          break;
        case 'INV_FOURIER':
          templateToInsert = createDefaultTransform('inv_fourier');
          break;
        case 'VEC_2':
          templateToInsert = createDefaultVector(2);
          break;
        case 'VEC_3':
        case 'VECTOR':
          templateToInsert = createDefaultVector(3);
          break;
        case 'VEC_4':
          templateToInsert = createDefaultVector(4);
          break;
        case 'COL_VEC_2':
          templateToInsert = createDefaultMatrix(2, 1);
          break;
        case 'COL_VEC_3':
          templateToInsert = createDefaultMatrix(3, 1);
          break;
        case 'COL_VEC_4':
          templateToInsert = createDefaultMatrix(4, 1);
          break;
        case 'MAT_2X2':
          templateToInsert = createDefaultMatrix(2, 2);
          break;
        case 'MAT_3X3':
        case 'MATRIX':
          templateToInsert = createDefaultMatrix(3, 3);
          break;
        case 'MAT_2X3':
          templateToInsert = createDefaultMatrix(2, 3);
          break;
        case 'MAT_3X4':
          templateToInsert = createDefaultMatrix(3, 4);
          break;
        case 'MAT_4X4':
          templateToInsert = createDefaultMatrix(4, 4);
          break;
        case 'MAT_5X5':
          templateToInsert = createDefaultMatrix(5, 5);
          break;
        default:
          break;
      }

      if (templateToInsert) {
        insertBlockAtFocus(templateToInsert, preferBaseFocus);
        return;
      }

      // Map standard token actions
      let snippet = '';
      switch (actionId) {
        case 'VAR_X': snippet = 'x'; break;
        case 'VAR_Y': snippet = 'y'; break;
        case 'EXP_E': snippet = 'e'; break;
        case 'INFINITY': snippet = '∞'; break;
        case 'NEG_INFINITY': snippet = '-∞'; break;
        case 'STEP_FUNC': snippet = 'θ('; break;
        case 'DELTA_FUNC': snippet = 'δ('; break;
        case 'PLUS': snippet = ' + '; break;
        case 'MINUS': snippet = ' − '; break;
        case 'MULTIPLY': snippet = '*'; break;
        case 'DIVIDE': snippet = '/'; break;
        case 'EQUALS': snippet = ' = '; break;
        case 'LE': snippet = ' ≤ '; break;
        case 'GE': snippet = ' ≥ '; break;
        case 'NE': snippet = ' ≠ '; break;
        case 'LPAREN': snippet = '('; break;
        case 'RPAREN': snippet = ')'; break;
        case 'PLUS_MINUS': snippet = '±'; break;
        case 'DELTA': snippet = 'Δ'; break;
        case 'PI': snippet = 'π'; break;
        case 'DEGREE': snippet = '°'; break;
        case 'RADIAN': snippet = ' rad'; break;
        // Trig and Hyperbolic
        case 'SIN': snippet = 'sin('; break;
        case 'COS': snippet = 'cos('; break;
        case 'TAN': snippet = 'tan('; break;
        case 'SEC': snippet = 'sec('; break;
        case 'CSC': snippet = 'csc('; break;
        case 'COT': snippet = 'cot('; break;
        case 'ARCSIN': snippet = 'arcsin('; break;
        case 'ARCCOS': snippet = 'arccos('; break;
        case 'ARCTAN': snippet = 'arctan('; break;
        case 'SINH': snippet = 'sinh('; break;
        case 'COSH': snippet = 'cosh('; break;
        case 'TANH': snippet = 'tanh('; break;
        case 'SECH': snippet = 'sech('; break;
        case 'CSCH': snippet = 'csch('; break;
        case 'COTH': snippet = 'coth('; break;
        case 'ARSINH': snippet = 'arcsinh('; break;
        case 'ARCOSH': snippet = 'arccosh('; break;
        case 'ARTANH': snippet = 'arctanh('; break;
        case 'ARSECH': snippet = 'arcsech('; break;
        case 'ARCSCH': snippet = 'arccsch('; break;
        case 'ARCOTH': snippet = 'arccoth('; break;
        // Greek & Math Symbols
        case 'FORALL': snippet = '∀'; break;
        case 'EXISTS': snippet = '∃'; break;
        case 'UNION': snippet = '∪'; break;
        case 'INTERSECT': snippet = '∩'; break;
        case 'NABLA': snippet = '∇'; break;
        case 'DELTA_CAP': snippet = 'Δ'; break;
        case 'ALPHA': snippet = 'α'; break;
        case 'BETA': snippet = 'β'; break;
        case 'GAMMA': snippet = 'γ'; break;
        case 'DELTA': snippet = 'δ'; break;
        case 'EPSILON': snippet = 'ε'; break;
        case 'ZETA': snippet = 'ζ'; break;
        case 'ETA': snippet = 'η'; break;
        case 'THETA': snippet = 'θ'; break;
        case 'KAPPA': snippet = 'κ'; break;
        case 'LAMBDA': snippet = 'λ'; break;
        case 'MU': snippet = 'μ'; break;
        case 'NU': snippet = 'ν'; break;
        case 'XI': snippet = 'ξ'; break;
        case 'RHO': snippet = 'ρ'; break;
        case 'SIGMA': snippet = 'σ'; break;
        case 'TAU': snippet = 'τ'; break;
        case 'PHI': snippet = 'φ'; break;
        case 'CHI': snippet = 'χ'; break;
        case 'PSI': snippet = 'ψ'; break;
        case 'OMEGA': snippet = 'ω'; break;
        case 'GAMMA_CAP': snippet = 'Γ'; break;
        case 'THETA_CAP': snippet = 'Θ'; break;
        case 'LAMBDA_CAP': snippet = 'Λ'; break;
        case 'XI_CAP': snippet = 'Ξ'; break;
        case 'UPSILON_CAP': snippet = 'Υ'; break;
        case 'PHI_CAP': snippet = 'Φ'; break;
        case 'PSI_CAP': snippet = 'Ψ'; break;
        case 'OMEGA_CAP': snippet = 'Ω'; break;
        case 'MHO': snippet = '℧'; break;
        case 'ANGSTROM': snippet = 'Å'; break;
        case 'HBAR': snippet = 'ħ'; break;
        case 'ALEPH': snippet = 'ℵ'; break;
        case 'HARPOONS': snippet = '⇄'; break;
        case 'RARROW': snippet = '→'; break;
        case 'OPLUS': snippet = '⊕'; break;
        case 'ODOT': snippet = '⊙'; break;
        case 'NE_SYM': snippet = ' ≠ '; break;
        case 'GE_SYM': snippet = ' ≥ '; break;
        case 'LE_SYM': snippet = ' ≤ '; break;
        case 'LOG': snippet = 'log('; break;
        case 'LOG_10': snippet = 'log10('; break;
        case 'LOG_BASE': snippet = 'log_'; break;
        case 'LN': snippet = 'ln('; break;
        case 'EXP': snippet = 'exp('; break;
        case 'DIGIT_0': snippet = '0'; break;
        case 'DIGIT_1': snippet = '1'; break;
        case 'DIGIT_2': snippet = '2'; break;
        case 'DIGIT_3': snippet = '3'; break;
        case 'DIGIT_4': snippet = '4'; break;
        case 'DIGIT_5': snippet = '5'; break;
        case 'DIGIT_6': snippet = '6'; break;
        case 'DIGIT_7': snippet = '7'; break;
        case 'DIGIT_8': snippet = '8'; break;
        case 'DIGIT_9': snippet = '9'; break;
        case 'DOT': snippet = '.'; break;
        case 'BACKSPACE':
          handleBackspaceOnFocus();
          return;
        default:
          snippet = actionId;
      }

      insertTextAtFocus(snippet);
    };

    const insertBlockAtFocus = (newBlock: MathBlock, preferBase = false) => {
      const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
      const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
      const res = findNodeAndParent(cloned, targetId);

      const trailingText = createEmptyTextNode('');
      if (res && res.node.type === 'text') {
        if (!res.node.value) {
          res.parent.splice(res.index, 1, newBlock, trailingText);
        } else {
          res.parent.splice(res.index + 1, 0, newBlock, trailingText);
        }
      } else {
        cloned.push(newBlock, trailingText);
      }

      notifyChange(cloned);

      let focusTargetId = findFirstTextNodeId(newBlock);
      if (preferBase && newBlock.type === 'power') {
        focusTargetId = findFirstTextNodeId(newBlock.base) || focusTargetId;
      }
      if (focusTargetId) {
        setFocusedNodeId(focusTargetId);
        requestAnimationFrame(() => {
          inputRefs.current.get(focusTargetId)?.focus();
        });
      }
    };

    const insertTextAtFocus = (text: string) => {
      const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
      const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
      const res = findNodeAndParent(cloned, targetId);

      if (res && res.node.type === 'text') {
        res.node.value += text;
        notifyChange(cloned);
      } else {
        const newText = createEmptyTextNode(text);
        cloned.push(newText);
        notifyChange(cloned);
        setFocusedNodeId(newText.id);
      }
    };

    const handleBackspaceOnFocus = () => {
      if (!focusedNodeId) return;
      const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
      const res = findNodeAndParent(cloned, focusedNodeId);
      if (!res) return;

      if (res.node.type === 'text') {
        if (res.node.value.length > 0) {
          res.node.value = res.node.value.slice(0, -1);
          notifyChange(cloned);
        } else if (res.index > 0) {
          res.parent.splice(res.index - 1, 1);
          if (res.parent.length === 0) {
            res.parent.push(createEmptyTextNode(''));
          }
          notifyChange(cloned);
        } else {
          const enclosing = findEnclosingBlockAndParent(cloned, focusedNodeId);
          if (enclosing) {
            enclosing.parent.splice(enclosing.index, 1);
            if (enclosing.parent.length === 0) {
              enclosing.parent.push(createEmptyTextNode(''));
            }
            const focusTarget = findFirstTextNodeId(enclosing.parent) || findFirstTextNodeId(cloned);
            if (focusTarget) {
              setFocusedNodeId(focusTarget);
              requestAnimationFrame(() => {
                inputRefs.current.get(focusTarget)?.focus();
              });
            }
            notifyChange(cloned);
          }
        }
      }
    };

    const handleSlotKeyDown = (
      e: React.KeyboardEvent<HTMLInputElement>,
      nodeId: string
    ) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onSubmit();
        return;
      }

      if (e.key === 'Backspace') {
        const inputEl = e.currentTarget;
        if (inputEl.selectionStart === 0 && inputEl.selectionEnd === 0) {
          const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
          const res = findNodeAndParent(cloned, nodeId);
          if (res) {
            if (res.node.type === 'text' && !res.node.value) {
              if (res.index > 0) {
                e.preventDefault();
                res.parent.splice(res.index - 1, 1);
                if (res.parent.length === 0) {
                  res.parent.push(createEmptyTextNode(''));
                }
                notifyChange(cloned);
              } else {
                const enclosing = findEnclosingBlockAndParent(cloned, nodeId);
                if (enclosing) {
                  e.preventDefault();
                  enclosing.parent.splice(enclosing.index, 1);
                  if (enclosing.parent.length === 0) {
                    enclosing.parent.push(createEmptyTextNode(''));
                  }
                  const focusTarget = findFirstTextNodeId(enclosing.parent) || findFirstTextNodeId(cloned);
                  if (focusTarget) {
                    setFocusedNodeId(focusTarget);
                    requestAnimationFrame(() => {
                      inputRefs.current.get(focusTarget)?.focus();
                    });
                  }
                  notifyChange(cloned);
                }
              }
            }
          }
        }
      }
    };

    /**
     * Recursive Slot List Renderer with progressive depth font-scaling.
     */
    const renderSlotList = (
      slotNodes: MathBlock[],
      isRoot = false,
      depth = 0,
      slotLabel = ''
    ): React.ReactNode => {
      const depthClass =
        depth === 1
          ? styles.nestingLevel1
          : depth === 2
          ? styles.nestingLevel2
          : depth >= 3
          ? styles.nestingLevel3
          : '';

      return (
        <span className={`${styles.slotWrap} ${depthClass}`}>
          {slotNodes.map((b, idx) => {
            if (b.type === 'text') {
              const isOnlyChild = slotNodes.length === 1 && !b.value;
              const isRootSingleEmpty = isRoot && isOnlyChild;
              const isTrailing = isRoot && idx === slotNodes.length - 1;

              const inputClass = isRootSingleEmpty
                ? styles.trailingTextInput
                : isOnlyChild && !isRoot
                ? `${styles.mathSlot} ${styles.emptySlot}`
                : isTrailing && !b.value
                ? styles.trailingTextInput
                : styles.textInput;

              const inputWidth = isRootSingleEmpty
                ? `${(placeholder || '').length * 0.85}ch`
                : isOnlyChild && !isRoot
                ? '16px'
                : b.value
                ? `${Math.max(1, b.value.length) * 0.85 + 0.2}ch`
                : isTrailing
                ? 'auto'
                : '6px';

              return (
                <input
                  key={b.id}
                  ref={(el) => setInputRef(b.id, el)}
                  type="text"
                  className={inputClass}
                  style={{ width: isTrailing && !b.value && isRoot ? undefined : inputWidth }}
                  value={b.value}
                  placeholder={isRootSingleEmpty ? placeholder : ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    const formatted = toMathModeFormat(val);
                    updateTextNode(b.id, formatted);
                  }}
                  onFocus={() => setFocusedNodeId(b.id)}
                  onKeyDown={(e) => handleSlotKeyDown(e, b.id)}
                  disabled={disabled}
                  autoComplete="off"
                  spellCheck="false"
                  aria-label={slotLabel || 'Ô nhập toán học'}
                  data-testid={`slot-${b.id}`}
                />
              );
            }

            if (b.type === 'fraction') {
              return (
                <span key={b.id} className={styles.fractionBlock}>
                  <div className={styles.fractionNumWrap}>
                    {renderSlotList(b.num, false, depth + 1, 'Tử số')}
                  </div>
                  <div className={styles.fractionBar} />
                  <div className={styles.fractionDenWrap}>
                    {renderSlotList(b.den, false, depth + 1, 'Mẫu số')}
                  </div>
                </span>
              );
            }

            if (b.type === 'power') {
              const isFixedSquare =
                b.exponent.length === 1 &&
                b.exponent[0]?.type === 'text' &&
                b.exponent[0].value === '2';

              return (
                <span key={b.id} className={styles.powerBlock}>
                  <div className={styles.powerBaseWrap}>
                    {renderSlotList(b.base, false, depth, 'Cơ số')}
                  </div>
                  <div className={styles.powerExpWrap}>
                    {isFixedSquare ? (
                      <span className={styles.powerSuperText}>2</span>
                    ) : (
                      renderSlotList(b.exponent, false, depth + 1, 'Số mũ')
                    )}
                  </div>
                </span>
              );
            }

            if (b.type === 'sqrt') {
              return (
                <span key={b.id} className={styles.sqrtBlock}>
                  <svg className={styles.sqrtRadicalSvg} viewBox="0 0 12 36" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 1 20 L 3.5 20 L 6.5 33 L 11 2 L 12 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <div className={styles.slotRadicandWrap}>
                    {renderSlotList(b.radicand, false, depth + 1, 'Biểu thức dưới căn')}
                  </div>
                </span>
              );
            }

            if (b.type === 'nth_root') {
              return (
                <span key={b.id} className={styles.nthRootBlock}>
                  <div className={styles.slotNthIndexWrap}>
                    {renderSlotList(b.index, false, depth + 1, 'Bậc căn')}
                  </div>
                  <svg className={styles.sqrtRadicalSvg} viewBox="0 0 12 36" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 1 20 L 3.5 20 L 6.5 33 L 11 2 L 12 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <div className={styles.slotRadicandWrap}>
                    {renderSlotList(b.radicand, false, depth + 1, 'Biểu thức dưới căn')}
                  </div>
                </span>
              );
            }

            if (b.type === 'derivative') {
              const sym = b.isPartial ? (b.order === 2 ? '∂²' : '∂') : (b.order === 2 ? 'd²' : 'd');
              const denSym = b.isPartial ? '∂' : 'd';
              return (
                <span key={b.id} className={styles.derivativeBlock}>
                  <span className={styles.fractionBlock}>
                    <span className={styles.fractionSymbol}>{sym}</span>
                    <div className={styles.fractionBar} />
                    <span className={styles.derivativeDenRow}>
                      <span className={styles.fractionSymbol}>{denSym}</span>
                      {renderSlotList(b.wrt, false, depth + 1, 'Biến vi phân 1')}
                      {b.wrt2 ? (
                        <>
                          <span className={styles.fractionSymbol}>{denSym}</span>
                          {renderSlotList(b.wrt2, false, depth + 1, 'Biến vi phân 2')}
                        </>
                      ) : (
                        b.order === 2 && <span className={styles.fractionSymbol}>²</span>
                      )}
                    </span>
                  </span>
                  {renderSlotList(b.expr, false, depth + 1, 'Hàm số vi phân')}
                </span>
              );
            }

            if (b.type === 'integral') {
              return (
                <span key={b.id} className={styles.integralBlock}>
                  {b.isDefinite ? (
                    <>
                      <span className={styles.defIntegralSymbolWrap}>
                        <span className={styles.integralSymbol}>∫</span>
                        <div className={styles.integralLimitsCol}>
                          <div className={styles.slotSuper}>
                            {renderSlotList(b.upper || [], false, depth + 1, 'Cận trên')}
                          </div>
                          <div className={styles.slotSub}>
                            {renderSlotList(b.lower || [], false, depth + 1, 'Cận dưới')}
                          </div>
                        </div>
                      </span>
                      {b.multiplicity && b.multiplicity >= 2 && (
                        <span className={styles.defIntegralSymbolWrap}>
                          <span className={styles.integralSymbol}>∫</span>
                          <div className={styles.integralLimitsCol}>
                            <div className={styles.slotSuper}>
                              {renderSlotList(b.upper2 || [], false, depth + 1, 'Cận trên 2')}
                            </div>
                            <div className={styles.slotSub}>
                              {renderSlotList(b.lower2 || [], false, depth + 1, 'Cận dưới 2')}
                            </div>
                          </div>
                        </span>
                      )}
                      {b.multiplicity && b.multiplicity >= 3 && (
                        <span className={styles.defIntegralSymbolWrap}>
                          <span className={styles.integralSymbol}>∫</span>
                          <div className={styles.integralLimitsCol}>
                            <div className={styles.slotSuper}>
                              {renderSlotList(b.upper3 || [], false, depth + 1, 'Cận trên 3')}
                            </div>
                            <div className={styles.slotSub}>
                              {renderSlotList(b.lower3 || [], false, depth + 1, 'Cận dưới 3')}
                            </div>
                          </div>
                        </span>
                      )}
                    </>
                  ) : (
                    <span className={styles.integralSymbol}>
                      {b.multiplicity === 3 ? '∭' : b.multiplicity === 2 ? '∬' : '∫'}
                    </span>
                  )}
                  {renderSlotList(b.expr, false, depth + 1, 'Hàm số tích phân')}
                  <span className={styles.differentialD}>d</span>
                  {renderSlotList(b.wrt, false, depth + 1, 'Biến tích phân 1')}
                  {b.wrt2 && (
                    <>
                      <span className={styles.differentialD}>d</span>
                      {renderSlotList(b.wrt2, false, depth + 1, 'Biến tích phân 2')}
                    </>
                  )}
                  {b.wrt3 && (
                    <>
                      <span className={styles.differentialD}>d</span>
                      {renderSlotList(b.wrt3, false, depth + 1, 'Biến tích phân 3')}
                    </>
                  )}
                </span>
              );
            }

            if (b.type === 'sum') {
              return (
                <span key={b.id} className={styles.sumBlock}>
                  <span className={styles.sumSymbolWrap}>
                    <div className={styles.slotSuper}>
                      {renderSlotList(b.to || [], false, depth + 1, 'Giới hạn trên')}
                    </div>
                    <span className={styles.sumSymbol}>{b.isProduct ? '∏' : '∑'}</span>
                    <span className={styles.sumLowerRow}>
                      {renderSlotList(b.variable || [], false, depth + 1, 'Biến tổng')}
                      <span style={{ fontSize: '0.75rem' }}>=</span>
                      {renderSlotList(b.from || [], false, depth + 1, 'Giá trị đầu')}
                    </span>
                  </span>
                  {renderSlotList(b.expr, false, depth + 1, 'Biểu thức tổng')}
                </span>
              );
            }

            if (b.type === 'limit') {
              const dirSuffix = b.direction === 'left' ? '⁻' : b.direction === 'right' ? '⁺' : '';
              return (
                <span key={b.id} className={styles.limitBlock}>
                  <span className={styles.limitSymbolWrap}>
                    <span className={styles.limitText}>lim</span>
                    {b.is2D ? (
                      <span className={styles.limitSubRow}>
                        ({renderSlotList(b.variable || [], false, depth + 1, 'Biến 1')},
                        {renderSlotList(b.variable2 || [], false, depth + 1, 'Biến 2')})→(
                        {renderSlotList(b.target || [], false, depth + 1, 'Điểm 1')},
                        {renderSlotList(b.target2 || [], false, depth + 1, 'Điểm 2')})
                      </span>
                    ) : (
                      <span className={styles.limitSubRow}>
                        {renderSlotList(b.variable || [], false, depth + 1, 'Biến giới hạn')}
                        <span style={{ fontSize: '0.75rem' }}>→</span>
                        {renderSlotList(b.target || [], false, depth + 1, 'Điểm giới hạn')}
                        {dirSuffix && <span style={{ fontSize: '0.8rem' }}>{dirSuffix}</span>}
                      </span>
                    )}
                  </span>
                  {renderSlotList(b.expr, false, depth + 1, 'Biểu thức')}
                </span>
              );
            }

            if (b.type === 'abs') {
              return (
                <span key={b.id} className={styles.absBlock}>
                  <span className={styles.absBar}>|</span>
                  {renderSlotList(b.content, false, depth + 1, 'Giá trị tuyệt đối')}
                  <span className={styles.absBar}>|</span>
                </span>
              );
            }

            if (b.type === 'log_base') {
              return (
                <span key={b.id} className={styles.logBaseBlock}>
                  <span className={styles.logBaseText}>log</span>
                  <div className={styles.logBaseSubWrap}>
                    {renderSlotList(b.base, false, depth + 1, 'Cơ số log')}
                  </div>
                  <span className={styles.parenSymbol}>(</span>
                  {renderSlotList(b.expr, false, depth + 1, 'Biểu thức log')}
                  <span className={styles.parenSymbol}>)</span>
                </span>
              );
            }

            if (b.type === 'piecewise') {
              return (
                <span key={b.id} className={styles.piecewiseBlock}>
                  <span className={styles.piecewiseBrace}>{'{'}</span>
                  <div className={styles.piecewiseGrid}>
                    {b.cases.map((c, cIdx) => (
                      <div key={cIdx} className={styles.piecewiseRow}>
                        {renderSlotList(c.expr, false, depth + 1, `Trường hợp ${cIdx + 1}`)}
                        <span className={styles.piecewiseIfText}>, nếu</span>
                        {renderSlotList(c.condition, false, depth + 1, `Điều kiện ${cIdx + 1}`)}
                      </div>
                    ))}
                  </div>
                </span>
              );
            }

            if (b.type === 'transform') {
              const sym =
                b.transformType === 'laplace'
                  ? 'ℒ'
                  : b.transformType === 'inv_laplace'
                  ? 'ℒ⁻¹'
                  : b.transformType === 'fourier'
                  ? 'ℱ'
                  : 'ℱ⁻¹';
              return (
                <span key={b.id} className={styles.transformBlock}>
                  <span className={styles.transformSymbol}>{sym}</span>
                  <span className={styles.parenSymbol}>{'{'}</span>
                  {renderSlotList(b.expr, false, depth + 1, 'Hàm biến đổi')}
                  <span className={styles.parenSymbol}>{'}'}</span>
                </span>
              );
            }

            if (b.type === 'vector') {
              return (
                <span key={b.id} className={styles.vectorBlock}>
                  <svg className={styles.vectorBracketSvg} viewBox="0 0 6 24" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 4.5 2 C 1.5 7 1.5 17 4.5 22" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                  {b.items.map((item, itIdx) => (
                    <React.Fragment key={itIdx}>
                      {itIdx > 0 && <span className={styles.vectorComma}>,</span>}
                      {renderSlotList(item, false, depth + 1, `Thành phần ${itIdx + 1}`)}
                    </React.Fragment>
                  ))}
                  <svg className={styles.vectorBracketSvg} viewBox="0 0 6 24" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 1.5 2 C 4.5 7 4.5 17 1.5 22" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                </span>
              );
            }

            if (b.type === 'matrix') {
              return (
                <span key={b.id} className={styles.matrixBlock}>
                  <svg className={styles.matrixBracketSvg} viewBox="0 0 8 72" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 6.5 2 C 1 18 1 54 6.5 70" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                  <div className={styles.matrixGrid}>
                    {b.cells.map((row, rIdx) => (
                      <div key={rIdx} className={styles.matrixRow}>
                        {row.map((cell, cIdx) => (
                          <React.Fragment key={cIdx}>
                            {renderSlotList(cell, false, depth + 1, `Phần tử [${rIdx + 1},${cIdx + 1}]`)}
                          </React.Fragment>
                        ))}
                      </div>
                    ))}
                  </div>
                  <svg className={styles.matrixBracketSvg} viewBox="0 0 8 72" fill="none" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M 1.5 2 C 7 18 7 54 1.5 70" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                  </svg>
                </span>
              );
            }

            return null;
          })}
        </span>
      );
    };

    return (
      <div
        ref={containerRef}
        className={styles.composerContainer}
        data-testid={testId}
        onClick={(e) => {
          if (
            e.target === containerRef.current ||
            (styles.composerContainer &&
              (e.target as HTMLElement).classList.contains(styles.composerContainer))
          ) {
            const firstId = findFirstTextNodeId(blocks);
            if (firstId) {
              const el = inputRefs.current.get(firstId);
              el?.focus();
            }
          }
        }}
      >
        {renderSlotList(blocks, true, 0)}
      </div>
    );
  }
);
