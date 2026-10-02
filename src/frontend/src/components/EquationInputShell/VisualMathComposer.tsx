import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import {
  MathBlock,
  parseStringToBlocks,
  blocksToVisualString,
  findNodeAndParent,
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
      switch (actionId) {
        case 'FRACTION':
          templateToInsert = createDefaultFraction();
          break;
        case 'SQUARE': {
          const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
          const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
          const res = findNodeAndParent(cloned, targetId);
          if (res && res.node.type === 'text') {
            if (!res.node.value || res.node.value.endsWith(' ') || res.node.value.endsWith('+') || res.node.value.endsWith('-') || res.node.value.endsWith('−') || res.node.value.endsWith('=')) {
              res.node.value += 'x²';
            } else {
              res.node.value += '²';
            }
            notifyChange(cloned);
            return;
          }
          templateToInsert = createDefaultPower('x', '2');
          break;
        }
        case 'POWER':
          templateToInsert = createDefaultPower('', '');
          break;
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
          templateToInsert = createDefaultNthRoot('n');
          break;
        case 'DERIVATIVE':
          templateToInsert = createDefaultDerivative(1);
          break;
        case 'SECOND_DERIVATIVE':
          templateToInsert = createDefaultDerivative(2);
          break;
        case 'INTEGRAL':
          templateToInsert = createDefaultIntegral(false);
          break;
        case 'DEF_INTEGRAL':
          templateToInsert = createDefaultIntegral(true);
          break;
        case 'SUM':
          templateToInsert = createDefaultSum();
          break;
        case 'LIMIT':
          templateToInsert = createDefaultLimit();
          break;
        case 'VEC_3':
        case 'VECTOR':
          templateToInsert = createDefaultVector(3);
          break;
        case 'MAT_3X3':
        case 'MATRIX':
          templateToInsert = createDefaultMatrix(3, 3);
          break;
        default:
          break;
      }

      if (templateToInsert) {
        insertBlockAtFocus(templateToInsert);
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
        case 'PLUS': snippet = ' + '; break;
        case 'MINUS': snippet = ' − '; break;
        case 'MULTIPLY': snippet = '*'; break;
        case 'DIVIDE': snippet = '/'; break;
        case 'EQUALS': snippet = ' = '; break;
        case 'LE': snippet = ' <= '; break;
        case 'GE': snippet = ' >= '; break;
        case 'NE': snippet = ' != '; break;
        case 'ABS': snippet = '|'; break;
        case 'LPAREN': snippet = '('; break;
        case 'RPAREN': snippet = ')'; break;
        case 'PLUS_MINUS': snippet = '±'; break;
        case 'DELTA': snippet = 'Δ'; break;
        case 'PI': snippet = 'π'; break;
        case 'ALPHA': snippet = 'α'; break;
        case 'BETA': snippet = 'β'; break;
        case 'GAMMA': snippet = 'γ'; break;
        case 'THETA': snippet = 'θ'; break;
        case 'LAMBDA': snippet = 'λ'; break;
        case 'MU': snippet = 'μ'; break;
        case 'SIGMA': snippet = 'σ'; break;
        case 'OMEGA': snippet = 'ω'; break;
        case 'SIN': snippet = 'sin('; break;
        case 'COS': snippet = 'cos('; break;
        case 'TAN': snippet = 'tan('; break;
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

    const insertBlockAtFocus = (newBlock: MathBlock) => {
      const cloned = JSON.parse(JSON.stringify(blocks)) as MathBlock[];
      const targetId = focusedNodeId || findFirstTextNodeId(cloned) || '';
      const res = findNodeAndParent(cloned, targetId);

      const trailingText = createEmptyTextNode('');
      if (res && res.node.type === 'text') {
        if (!res.node.value) {
          // Replace empty text slot with template + trailing text
          res.parent.splice(res.index, 1, newBlock, trailingText);
        } else {
          res.parent.splice(res.index + 1, 0, newBlock, trailingText);
        }
      } else {
        cloned.push(newBlock, trailingText);
      }

      notifyChange(cloned);

      const firstTextId = findFirstTextNodeId(newBlock);
      if (firstTextId) {
        setFocusedNodeId(firstTextId);
        requestAnimationFrame(() => {
          inputRefs.current.get(firstTextId)?.focus();
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
            if (res.node.type === 'text' && !res.node.value && res.index > 0) {
              e.preventDefault();
              res.parent.splice(res.index - 1, 1);
              if (res.parent.length === 0) {
                res.parent.push(createEmptyTextNode(''));
              }
              notifyChange(cloned);
            }
          }
        }
      }
    };

    /**
     * Recursive Slot List Renderer.
     */
    const renderSlotList = (
      slotNodes: MathBlock[],
      isRoot = false,
      slotLabel = ''
    ): React.ReactNode => {
      return (
        <span className={styles.slotWrap}>
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
                    {renderSlotList(b.num, false, 'Tử số')}
                  </div>
                  <div className={styles.fractionBar} />
                  <div className={styles.fractionDenWrap}>
                    {renderSlotList(b.den, false, 'Mẫu số')}
                  </div>
                </span>
              );
            }

            if (b.type === 'power') {
              return (
                <span key={b.id} className={styles.powerBlock}>
                  <div className={styles.powerBaseWrap}>
                    {renderSlotList(b.base, false, 'Cơ số')}
                  </div>
                  <div className={styles.powerExpWrap}>
                    {renderSlotList(b.exponent, false, 'Số mũ')}
                  </div>
                </span>
              );
            }

            if (b.type === 'sqrt') {
              return (
                <span key={b.id} className={styles.sqrtBlock}>
                  <span className={styles.sqrtSymbol}>√</span>
                  <div className={styles.slotRadicandWrap}>
                    {renderSlotList(b.radicand, false, 'Biểu thức dưới căn')}
                  </div>
                </span>
              );
            }

            if (b.type === 'nth_root') {
              return (
                <span key={b.id} className={styles.nthRootBlock}>
                  <div className={styles.slotNthIndexWrap}>
                    {renderSlotList(b.index, false, 'Bậc căn')}
                  </div>
                  <span className={styles.sqrtSymbol}>√</span>
                  <div className={styles.slotRadicandWrap}>
                    {renderSlotList(b.radicand, false, 'Biểu thức dưới căn')}
                  </div>
                </span>
              );
            }

            if (b.type === 'derivative') {
              return (
                <span key={b.id} className={styles.derivativeBlock}>
                  <span className={styles.fractionBlock}>
                    <span className={styles.fractionSymbol}>{b.order === 2 ? 'd²' : 'd'}</span>
                    <div className={styles.fractionBar} />
                    <span className={styles.derivativeDenRow}>
                      <span className={styles.fractionSymbol}>d</span>
                      {renderSlotList(b.wrt, false, 'Biến vi phân')}
                      {b.order === 2 && <span className={styles.fractionSymbol}>²</span>}
                    </span>
                  </span>
                  {renderSlotList(b.expr, false, 'Hàm số vi phân')}
                </span>
              );
            }

            if (b.type === 'integral') {
              return (
                <span key={b.id} className={styles.integralBlock}>
                  {b.isDefinite ? (
                    <span className={styles.defIntegralSymbolWrap}>
                      <div className={styles.slotSuper}>
                        {renderSlotList(b.upper || [], false, 'Cận trên')}
                      </div>
                      <span className={styles.integralSymbol}>∫</span>
                      <div className={styles.slotSub}>
                        {renderSlotList(b.lower || [], false, 'Cận dưới')}
                      </div>
                    </span>
                  ) : (
                    <span className={styles.integralSymbol}>∫</span>
                  )}
                  {renderSlotList(b.expr, false, 'Hàm số tích phân')}
                  <span className={styles.differentialD}>d</span>
                  {renderSlotList(b.wrt, false, 'Biến tích phân')}
                </span>
              );
            }

            if (b.type === 'sum') {
              return (
                <span key={b.id} className={styles.sumBlock}>
                  <span className={styles.sumSymbolWrap}>
                    <div className={styles.slotSuper}>
                      {renderSlotList(b.to || [], false, 'Giới hạn trên')}
                    </div>
                    <span className={styles.sumSymbol}>∑</span>
                    <span className={styles.sumLowerRow}>
                      {renderSlotList(b.variable || [], false, 'Biến tổng')}
                      <span style={{ fontSize: '0.75rem' }}>=</span>
                      {renderSlotList(b.from || [], false, 'Giá trị đầu')}
                    </span>
                  </span>
                  {renderSlotList(b.expr, false, 'Biểu thức tổng')}
                </span>
              );
            }

            if (b.type === 'limit') {
              return (
                <span key={b.id} className={styles.limitBlock}>
                  <span className={styles.limitSymbolWrap}>
                    <span className={styles.limitText}>lim</span>
                    <span className={styles.limitSubRow}>
                      {renderSlotList(b.variable || [], false, 'Biến giới hạn')}
                      <span style={{ fontSize: '0.75rem' }}>→</span>
                      {renderSlotList(b.target || [], false, 'Điểm giới hạn')}
                    </span>
                  </span>
                  {renderSlotList(b.expr, false, 'Biểu thức')}
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
                      {renderSlotList(item, false, `Thành phần ${itIdx + 1}`)}
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
                            {renderSlotList(cell, false, `Phần tử [${rIdx + 1},${cIdx + 1}]`)}
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
        {renderSlotList(blocks, true)}
      </div>
    );
  }
);
