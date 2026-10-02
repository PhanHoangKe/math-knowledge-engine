import React, { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import {
  MathBlock,
  parseStringToBlocks,
  blocksToVisualString,
  genId,
} from './visualMathModel';
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

interface FocusTarget {
  blockId: string;
  slot: string; // 'value' | 'base' | 'exponent' | 'num' | 'den' | 'radicand' | 'index' | 'expr' | 'wrt'
}

export const VisualMathComposer = forwardRef<VisualMathComposerHandle, VisualMathComposerProps>(
  ({ rawQuery, onChange, onSubmit, disabled = false, placeholder = 'x² − 5x + 6 = 0', 'data-testid': testId = 'visual-math-composer' }, ref) => {
    const [blocks, setBlocks] = useState<MathBlock[]>(() => parseStringToBlocks(rawQuery));
    const [focusedTarget, setFocusedTarget] = useState<FocusTarget | null>(null);
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
        const initial: MathBlock[] = [{ type: 'text', id: genId(), value: '' }];
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

    const handleApplyPaletteAction = (actionId: string) => {
      if (actionId === 'CLEAR') {
        const initial: MathBlock[] = [{ type: 'text', id: genId(), value: '' }];
        notifyChange(initial);
        return;
      }

      // Check template insertions
      if (actionId === 'FRACTION') {
        const newFrac: MathBlock = { type: 'fraction', id: genId(), num: '', den: '' };
        insertBlockAtFocus(newFrac, 'num');
        return;
      }

      if (actionId === 'POWER' || actionId === 'SQUARE') {
        const exponentVal = actionId === 'SQUARE' ? '2' : '';
        let baseVal = 'x';
        const updated = [...blocks];

        let targetIdx = -1;
        if (focusedTarget) {
          targetIdx = updated.findIndex((b) => b.id === focusedTarget.blockId);
        } else if (updated.length > 0) {
          targetIdx = updated.length - 1;
        }

        if (targetIdx !== -1) {
          const targetBlock = updated[targetIdx];
          if (targetBlock && targetBlock.type === 'text') {
            if (targetBlock.value.endsWith('x')) {
              targetBlock.value = targetBlock.value.slice(0, -1);
              baseVal = 'x';
            } else if (targetBlock.value) {
              baseVal = targetBlock.value.slice(-1);
              targetBlock.value = targetBlock.value.slice(0, -1);
            }
          }
        }

        const newPow: MathBlock = { type: 'power', id: genId(), base: baseVal, exponent: exponentVal };
        const insertIdx = targetIdx !== -1 ? targetIdx + 1 : updated.length;
        updated.splice(insertIdx, 0, newPow);

        if (actionId === 'SQUARE') {
          // For square (x²), automatically append a trailing text slot so subsequent actions continue after x²
          const trailingText: MathBlock = { type: 'text', id: genId(), value: '' };
          updated.splice(insertIdx + 1, 0, trailingText);
          const cleaned = updated.filter((b, i) => !(b.type === 'text' && !b.value && i < updated.length - 1));
          notifyChange(cleaned);
          setFocusedTarget({ blockId: trailingText.id, slot: 'value' });
          requestAnimationFrame(() => {
            const el = inputRefs.current.get(`${trailingText.id}_value`);
            el?.focus();
          });
        } else {
          // For power template (□^□), focus the exponent slot
          const cleaned = updated.filter((b, i) => !(b.type === 'text' && !b.value && i < updated.length - 1));
          notifyChange(cleaned);
          setFocusedTarget({ blockId: newPow.id, slot: 'exponent' });
          requestAnimationFrame(() => {
            const el = inputRefs.current.get(`${newPow.id}_exponent`);
            el?.focus();
          });
        }
        return;
      }

      if (actionId === 'SQRT') {
        const newSqrt: MathBlock = { type: 'sqrt', id: genId(), radicand: '' };
        insertBlockAtFocus(newSqrt, 'radicand');
        return;
      }

      if (actionId === 'CUBE_ROOT') {
        const newCube: MathBlock = { type: 'nth_root', id: genId(), index: '3', radicand: '' };
        insertBlockAtFocus(newCube, 'radicand');
        return;
      }

      if (actionId === 'NTH_ROOT') {
        const newNth: MathBlock = { type: 'nth_root', id: genId(), index: 'n', radicand: '' };
        insertBlockAtFocus(newNth, 'radicand');
        return;
      }

      if (actionId === 'DERIVATIVE') {
        const newDeriv: MathBlock = { type: 'derivative', id: genId(), order: 1, wrt: 'x', expr: '' };
        insertBlockAtFocus(newDeriv, 'expr');
        return;
      }

      if (actionId === 'SECOND_DERIVATIVE') {
        const newDeriv: MathBlock = { type: 'derivative', id: genId(), order: 2, wrt: 'x', expr: '' };
        insertBlockAtFocus(newDeriv, 'expr');
        return;
      }

      if (actionId === 'INTEGRAL') {
        const newInt: MathBlock = { type: 'integral', id: genId(), isDefinite: false, expr: '', wrt: 'x' };
        insertBlockAtFocus(newInt, 'expr');
        return;
      }

      if (actionId === 'DEF_INTEGRAL') {
        const newInt: MathBlock = { type: 'integral', id: genId(), isDefinite: true, lower: 'a', upper: 'b', expr: '', wrt: 'x' };
        insertBlockAtFocus(newInt, 'expr');
        return;
      }

      if (actionId === 'SUM') {
        const newSum: MathBlock = { type: 'sum', id: genId(), variable: 'i', from: '1', to: 'n', expr: '' };
        insertBlockAtFocus(newSum, 'expr');
        return;
      }

      if (actionId === 'LIMIT') {
        const newLim: MathBlock = { type: 'limit', id: genId(), variable: 'x', target: '0', expr: '' };
        insertBlockAtFocus(newLim, 'expr');
        return;
      }

      if (actionId === 'VEC_3' || actionId === 'VECTOR') {
        const newVec: MathBlock = { type: 'vector', id: genId(), items: ['', '', ''] };
        insertBlockAtFocus(newVec, 'item_0');
        return;
      }

      if (actionId === 'MAT_3X3' || actionId === 'MATRIX') {
        const newMat: MathBlock = {
          type: 'matrix',
          id: genId(),
          rows: 3,
          cols: 3,
          cells: [
            ['', '', ''],
            ['', '', ''],
            ['', '', ''],
          ],
        };
        insertBlockAtFocus(newMat, 'cell_0_0');
        return;
      }

      // Map standard token actions
      let snippet = '';
      switch (actionId) {
        case 'VAR_X': snippet = 'x'; break;
        case 'VAR_Y': snippet = 'y'; break;
        case 'PLUS': snippet = ' + '; break;
        case 'MINUS': snippet = ' − '; break;
        case 'MULTIPLY': snippet = '*'; break;
        case 'DIVIDE': snippet = '/'; break;
        case 'EQUALS': snippet = ' = '; break;
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

    const insertBlockAtFocus = (newBlock: MathBlock, focusSlot: string) => {
      let updated = [...blocks];
      let insertIdx = updated.length;

      // If the composer only contains 1 empty text block, replace it with new template block + trailing text
      if (updated.length === 1 && updated[0]?.type === 'text' && !updated[0].value) {
        const trailingText: MathBlock = { type: 'text', id: genId(), value: '' };
        updated = [newBlock, trailingText];
      } else {
        if (focusedTarget) {
          const found = updated.findIndex((b) => b.id === focusedTarget.blockId);
          if (found !== -1) {
            insertIdx = found + 1;
          }
        }
        const trailingText: MathBlock = { type: 'text', id: genId(), value: '' };
        updated.splice(insertIdx, 0, newBlock, trailingText);
      }

      notifyChange(updated);
      setFocusedTarget({ blockId: newBlock.id, slot: focusSlot });
      requestAnimationFrame(() => {
        const el = inputRefs.current.get(`${newBlock.id}_${focusSlot}`);
        el?.focus();
      });
    };

    const insertTextAtFocus = (text: string) => {
      const updated = [...blocks];
      let targetBlock = focusedTarget ? updated.find((b) => b.id === focusedTarget.blockId) : null;
      if (!targetBlock) {
        // Fallback to last block or create a new text block
        const last = updated[updated.length - 1];
        if (last && last.type === 'text') {
          targetBlock = last;
          setFocusedTarget({ blockId: last.id, slot: 'value' });
        } else {
          const newTextBlock: MathBlock = { type: 'text', id: genId(), value: '' };
          updated.push(newTextBlock);
          targetBlock = newTextBlock;
          setFocusedTarget({ blockId: newTextBlock.id, slot: 'value' });
        }
      }

      if (targetBlock.type === 'text') {
        targetBlock.value += text;
      } else if (targetBlock.type === 'power') {
        if (focusedTarget?.slot === 'exponent') targetBlock.exponent += text;
        else targetBlock.base += text;
      } else if (targetBlock.type === 'fraction') {
        if (focusedTarget?.slot === 'num') targetBlock.num += text;
        else targetBlock.den += text;
      } else if (targetBlock.type === 'sqrt' || targetBlock.type === 'nth_root') {
        if (focusedTarget?.slot === 'radicand') targetBlock.radicand += text;
        else if (targetBlock.type === 'nth_root') targetBlock.index += text;
      } else if (targetBlock.type === 'derivative') {
        if (focusedTarget?.slot === 'wrt') targetBlock.wrt += text;
        else targetBlock.expr += text;
      } else if (targetBlock.type === 'integral') {
        if (focusedTarget?.slot === 'wrt') targetBlock.wrt += text;
        else if (focusedTarget?.slot === 'upper') targetBlock.upper = (targetBlock.upper || '') + text;
        else if (focusedTarget?.slot === 'lower') targetBlock.lower = (targetBlock.lower || '') + text;
        else targetBlock.expr += text;
      }

      notifyChange(updated);
    };

    const handleBackspaceOnFocus = () => {
      if (!focusedTarget) return;
      const updated = [...blocks];
      const idx = updated.findIndex((b) => b.id === focusedTarget.blockId);
      if (idx === -1) return;

      const targetBlock = updated[idx];
      if (!targetBlock) return;

      if (targetBlock.type === 'text') {
        if (targetBlock.value.length > 0) {
          targetBlock.value = targetBlock.value.slice(0, -1);
          notifyChange(updated);
        } else if (idx > 0) {
          // Remove empty text block and previous block
          updated.splice(idx - 1, 2);
          if (updated.length === 0) {
            updated.push({ type: 'text', id: genId(), value: '' });
          }
          notifyChange(updated);
        }
      } else {
        // Delete block directly
        updated.splice(idx, 1);
        if (updated.length === 0) {
          updated.push({ type: 'text', id: genId(), value: '' });
        }
        notifyChange(updated);
      }
    };

    const handleSlotKeyDown = (
      e: React.KeyboardEvent<HTMLInputElement>,
      block: MathBlock,
      slot: string,
      index: number
    ) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onSubmit();
        return;
      }

      if (e.key === 'ArrowRight') {
        const inputEl = e.currentTarget;
        if (inputEl.selectionStart === inputEl.value.length) {
          const nextIdx = index + 1;
          if (nextIdx < blocks.length) {
            e.preventDefault();
            const nextBlock = blocks[nextIdx]!;
            const nextSlot = nextBlock.type === 'text' ? 'value' : 'exponent';
            setFocusedTarget({ blockId: nextBlock.id, slot: nextSlot });
            requestAnimationFrame(() => {
              const el = inputRefs.current.get(`${nextBlock.id}_${nextSlot}`);
              el?.focus();
              el?.setSelectionRange(0, 0);
            });
          }
          return;
        }
      }

      if (e.key === 'ArrowLeft') {
        const inputEl = e.currentTarget;
        if (inputEl.selectionStart === 0 && inputEl.selectionEnd === 0) {
          const prevIdx = index - 1;
          if (prevIdx >= 0) {
            e.preventDefault();
            const prevBlock = blocks[prevIdx]!;
            const prevSlot = prevBlock.type === 'text' ? 'value' : 'expr';
            setFocusedTarget({ blockId: prevBlock.id, slot: prevSlot });
            requestAnimationFrame(() => {
              const el =
                inputRefs.current.get(`${prevBlock.id}_${prevSlot}`) ??
                inputRefs.current.get(`${prevBlock.id}_expr`) ??
                inputRefs.current.get(`${prevBlock.id}_den`) ??
                inputRefs.current.get(`${prevBlock.id}_radicand`) ??
                inputRefs.current.get(`${prevBlock.id}_value`);
              el?.focus();
              if (el) {
                el.setSelectionRange(el.value.length, el.value.length);
              }
            });
          }
          return;
        }
      }

      if (e.key === 'ArrowDown' || e.key === 'Tab') {
        if (block.type === 'fraction' && slot === 'num') {
          e.preventDefault();
          setFocusedTarget({ blockId: block.id, slot: 'den' });
          requestAnimationFrame(() => {
            inputRefs.current.get(`${block.id}_den`)?.focus();
          });
          return;
        }
      }

      if (e.key === 'ArrowUp') {
        if (block.type === 'fraction' && slot === 'den') {
          e.preventDefault();
          setFocusedTarget({ blockId: block.id, slot: 'num' });
          requestAnimationFrame(() => {
            inputRefs.current.get(`${block.id}_num`)?.focus();
          });
          return;
        }
      }

      if (e.key === 'Backspace') {
        const inputEl = e.currentTarget;
        if (inputEl.selectionStart === 0 && inputEl.selectionEnd === 0) {
          // If in text block and empty, delete previous block!
          if (block.type === 'text' && !block.value && index > 0) {
            e.preventDefault();
            const updated = [...blocks];
            // Remove previous block and current empty text block if needed
            updated.splice(index - 1, 1);
            notifyChange(updated);
            const focusIdx = Math.max(0, index - 2);
            const focusBlock = updated[focusIdx] ?? updated[0];
            if (focusBlock) {
              const slotToFocus = focusBlock.type === 'text' ? 'value' : 'value';
              setFocusedTarget({ blockId: focusBlock.id, slot: slotToFocus });
              requestAnimationFrame(() => {
                const el =
                  inputRefs.current.get(`${focusBlock.id}_${slotToFocus}`) ??
                  inputRefs.current.get(`${focusBlock.id}_value`);
                el?.focus();
              });
            }
            return;
          }

          // If in a template block and slot is empty, delete or collapse the block!
          if (block.type !== 'text') {
            e.preventDefault();
            const updated = [...blocks];
            if (block.type === 'power' && block.base) {
              const collapsedBlock: MathBlock = { type: 'text', id: genId(), value: block.base };
              updated.splice(index, 1, collapsedBlock);
              notifyChange(updated);
              setFocusedTarget({ blockId: collapsedBlock.id, slot: 'value' });
              requestAnimationFrame(() => {
                const el = inputRefs.current.get(`${collapsedBlock.id}_value`);
                el?.focus();
                if (el) {
                  el.setSelectionRange(el.value.length, el.value.length);
                }
              });
              return;
            }

            updated.splice(index, 1);
            if (updated.length === 0) {
              updated.push({ type: 'text', id: genId(), value: '' });
            }
            notifyChange(updated);
            const focusIdx = Math.max(0, index - 1);
            const focusBlock = updated[focusIdx] ?? updated[0]!;
            const slotToFocus = focusBlock.type === 'text' ? 'value' : 'value';
            setFocusedTarget({ blockId: focusBlock.id, slot: slotToFocus });
            requestAnimationFrame(() => {
              const el = inputRefs.current.get(`${focusBlock.id}_${slotToFocus}`);
              el?.focus();
            });
            return;
          }
        }
      }
    };

    const updateBlock = (blockId: string, updates: Partial<MathBlock>) => {
      const updated: MathBlock[] = [];
      for (const b of blocks) {
        if (b.id === blockId) {
          const merged = { ...b, ...updates } as MathBlock;
          if (merged.type === 'text' && (merged.value.includes('^') || merged.value.includes('\\frac') || merged.value.includes('sqrt('))) {
            const parsed = parseStringToBlocks(merged.value);
            updated.push(...parsed);
          } else {
            updated.push(merged);
          }
        } else {
          updated.push(b);
        }
      }

      // Merge adjacent text blocks
      const mergedBlocks: MathBlock[] = [];
      for (const b of updated) {
        if (b.type === 'text' && mergedBlocks.length > 0 && mergedBlocks[mergedBlocks.length - 1]?.type === 'text') {
          const prev = mergedBlocks[mergedBlocks.length - 1] as { type: 'text'; id: string; value: string };
          prev.value += b.value;
        } else {
          mergedBlocks.push(b);
        }
      }

      notifyChange(mergedBlocks);
    };

    return (
      <div
        ref={containerRef}
        className={styles.composerContainer}
        data-testid={testId}
        onClick={(e) => {
          if (e.target === containerRef.current || (styles.composerContainer && (e.target as HTMLElement).classList.contains(styles.composerContainer))) {
            const updated = [...blocks];
            const last = updated[updated.length - 1];
            if (!last || last.type !== 'text') {
              const newTrailing: MathBlock = { type: 'text', id: genId(), value: '' };
              updated.push(newTrailing);
              notifyChange(updated);
              setFocusedTarget({ blockId: newTrailing.id, slot: 'value' });
              requestAnimationFrame(() => {
                inputRefs.current.get(`${newTrailing.id}_value`)?.focus();
              });
            } else {
              setFocusedTarget({ blockId: last.id, slot: 'value' });
              requestAnimationFrame(() => {
                const el = inputRefs.current.get(`${last.id}_value`);
                el?.focus();
                if (el) {
                  el.setSelectionRange(el.value.length, el.value.length);
                }
              });
            }
          }
        }}
      >
        {blocks.map((b, idx) => {
          if (b.type === 'text') {
            const isSingleEmpty = blocks.length === 1 && !b.value;
            const isTrailing = idx === blocks.length - 1;
            const inputWidth = isSingleEmpty
              ? `${placeholder.length * 0.85}ch`
              : b.value
              ? `${Math.max(1, b.value.length) * 0.85 + 0.2}ch`
              : isTrailing
              ? 'auto'
              : '8px';

            return (
              <input
                key={b.id}
                ref={(el) => setInputRef(`${b.id}_value`, el)}
                type="text"
                className={isTrailing && !b.value ? styles.trailingTextInput : styles.textInput}
                style={{ width: isTrailing && !b.value ? undefined : inputWidth }}
                value={b.value}
                placeholder={isSingleEmpty ? placeholder : ''}
                onChange={(e) => updateBlock(b.id, { value: e.target.value })}
                onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'value' })}
                onKeyDown={(e) => handleSlotKeyDown(e, b, 'value', idx)}
                disabled={disabled}
                autoComplete="off"
                spellCheck="false"
              />
            );
          }

          if (b.type === 'power') {
            const expWidth = Math.max(1, (b.exponent || ' ').length) * 1.1 + 0.4;
            return (
              <span key={b.id} className={styles.powerBlock}>
                <span className={styles.powerBase}>{b.base}</span>
                <input
                  ref={(el) => setInputRef(`${b.id}_exponent`, el)}
                  type="text"
                  className={`${styles.slotExponent} ${!b.exponent ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${expWidth}ch` }}
                  value={b.exponent}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { exponent: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'exponent' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'exponent', idx)}
                  disabled={disabled}
                  aria-label="Số mũ"
                  data-testid={`exponent-slot-${b.id}`}
                />
              </span>
            );
          }

          if (b.type === 'fraction') {
            const numWidth = Math.max(1, (b.num || ' ').length) * 1.1 + 0.6;
            const denWidth = Math.max(1, (b.den || ' ').length) * 1.1 + 0.6;
            return (
              <span key={b.id} className={styles.fractionBlock}>
                <input
                  ref={(el) => setInputRef(`${b.id}_num`, el)}
                  type="text"
                  className={`${styles.slotNumerator} ${!b.num ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${numWidth}ch` }}
                  value={b.num}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { num: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'num' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'num', idx)}
                  disabled={disabled}
                  aria-label="Tử số"
                  data-testid={`fraction-num-${b.id}`}
                />
                <div className={styles.fractionBar} />
                <input
                  ref={(el) => setInputRef(`${b.id}_den`, el)}
                  type="text"
                  className={`${styles.slotDenominator} ${!b.den ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${denWidth}ch` }}
                  value={b.den}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { den: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'den' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'den', idx)}
                  disabled={disabled}
                  aria-label="Mẫu số"
                  data-testid={`fraction-den-${b.id}`}
                />
              </span>
            );
          }

          if (b.type === 'sqrt') {
            const radWidth = Math.max(1, (b.radicand || ' ').length) * 1.1 + 0.6;
            return (
              <span key={b.id} className={styles.sqrtBlock}>
                <span className={styles.sqrtSymbol}>√</span>
                <input
                  ref={(el) => setInputRef(`${b.id}_radicand`, el)}
                  type="text"
                  className={`${styles.slotRadicand} ${!b.radicand ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${radWidth}ch` }}
                  value={b.radicand}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { radicand: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'radicand' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'radicand', idx)}
                  disabled={disabled}
                  aria-label="Biểu thức dưới căn"
                  data-testid={`sqrt-slot-${b.id}`}
                />
              </span>
            );
          }

          if (b.type === 'nth_root') {
            const radWidth = Math.max(1, (b.radicand || ' ').length) * 1.1 + 0.6;
            return (
              <span key={b.id} className={styles.nthRootBlock}>
                <input
                  ref={(el) => setInputRef(`${b.id}_index`, el)}
                  type="text"
                  className={`${styles.slotNthIndex} ${!b.index ? styles.emptySlot : styles.filledSlot}`}
                  value={b.index}
                  placeholder="n"
                  onChange={(e) => updateBlock(b.id, { index: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'index' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'index', idx)}
                  disabled={disabled}
                  aria-label="Bậc căn"
                />
                <span className={styles.sqrtSymbol}>√</span>
                <input
                  ref={(el) => setInputRef(`${b.id}_radicand`, el)}
                  type="text"
                  className={`${styles.slotRadicand} ${!b.radicand ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${radWidth}ch` }}
                  value={b.radicand}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { radicand: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'radicand' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'radicand', idx)}
                  disabled={disabled}
                  aria-label="Biểu thức dưới căn"
                />
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
                    <input
                      ref={(el) => setInputRef(`${b.id}_wrt`, el)}
                      type="text"
                      className={`${styles.mathSlot} ${!b.wrt ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.wrt || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.wrt}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { wrt: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'wrt' })}
                      disabled={disabled}
                    />
                    {b.order === 2 && <span className={styles.fractionSymbol}>²</span>}
                  </span>
                </span>
                <input
                  ref={(el) => setInputRef(`${b.id}_expr`, el)}
                  type="text"
                  className={`${styles.mathSlot} ${!b.expr ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${Math.max(1, (b.expr || ' ').length) * 1.1 + 0.6}ch` }}
                  value={b.expr}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { expr: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'expr' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'expr', idx)}
                  disabled={disabled}
                />
              </span>
            );
          }

          if (b.type === 'integral') {
            return (
              <span key={b.id} className={styles.integralBlock}>
                {b.isDefinite ? (
                  <span className={styles.defIntegralSymbolWrap}>
                    <input
                      ref={(el) => setInputRef(`${b.id}_upper`, el)}
                      type="text"
                      className={`${styles.slotSuper} ${!b.upper ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.upper || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.upper ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { upper: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'upper' })}
                      disabled={disabled}
                    />
                    <span className={styles.integralSymbol}>∫</span>
                    <input
                      ref={(el) => setInputRef(`${b.id}_lower`, el)}
                      type="text"
                      className={`${styles.slotSub} ${!b.lower ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.lower || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.lower ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { lower: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'lower' })}
                      disabled={disabled}
                    />
                  </span>
                ) : (
                  <span className={styles.integralSymbol}>∫</span>
                )}
                <input
                  ref={(el) => setInputRef(`${b.id}_expr`, el)}
                  type="text"
                  className={`${styles.mathSlot} ${!b.expr ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${Math.max(1, (b.expr || ' ').length) * 1.1 + 0.6}ch` }}
                  value={b.expr}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { expr: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'expr' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'expr', idx)}
                  disabled={disabled}
                />
                <span className={styles.differentialD}>d</span>
                <input
                  ref={(el) => setInputRef(`${b.id}_wrt`, el)}
                  type="text"
                  className={`${styles.mathSlot} ${!b.wrt ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${Math.max(1, (b.wrt || ' ').length) * 1.1 + 0.6}ch` }}
                  value={b.wrt}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { wrt: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'wrt' })}
                  disabled={disabled}
                />
              </span>
            );
          }

          if (b.type === 'sum') {
            return (
              <span key={b.id} className={styles.sumBlock}>
                <span className={styles.sumSymbolWrap}>
                  <input
                    ref={(el) => setInputRef(`${b.id}_upper`, el)}
                    type="text"
                    className={`${styles.slotSuper} ${!b.to ? styles.emptySlot : styles.filledSlot}`}
                    style={{ width: `${Math.max(1, (b.to || ' ').length) * 1.1 + 0.6}ch` }}
                    value={b.to ?? ''}
                    placeholder=""
                    onChange={(e) => updateBlock(b.id, { to: e.target.value })}
                    onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'upper' })}
                    disabled={disabled}
                  />
                  <span className={styles.sumSymbol}>∑</span>
                  <span className={styles.sumLowerRow}>
                    <input
                      ref={(el) => setInputRef(`${b.id}_var`, el)}
                      type="text"
                      className={`${styles.slotSub} ${!b.variable ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.variable || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.variable ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { variable: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'var' })}
                      disabled={disabled}
                    />
                    <span style={{ fontSize: '0.75rem' }}>=</span>
                    <input
                      ref={(el) => setInputRef(`${b.id}_lower`, el)}
                      type="text"
                      className={`${styles.slotSub} ${!b.from ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.from || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.from ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { from: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'lower' })}
                      disabled={disabled}
                    />
                  </span>
                </span>
                <input
                  ref={(el) => setInputRef(`${b.id}_expr`, el)}
                  type="text"
                  className={`${styles.mathSlot} ${!b.expr ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${Math.max(1, (b.expr || ' ').length) * 1.1 + 0.6}ch` }}
                  value={b.expr}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { expr: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'expr' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'expr', idx)}
                  disabled={disabled}
                />
              </span>
            );
          }

          if (b.type === 'limit') {
            return (
              <span key={b.id} className={styles.limitBlock}>
                <span className={styles.limitSymbolWrap}>
                  <span className={styles.limitText}>lim</span>
                  <span className={styles.limitSubRow}>
                    <input
                      ref={(el) => setInputRef(`${b.id}_var`, el)}
                      type="text"
                      className={`${styles.slotSub} ${!b.variable ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.variable || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.variable ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { variable: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'var' })}
                      disabled={disabled}
                    />
                    <span style={{ fontSize: '0.75rem' }}>→</span>
                    <input
                      ref={(el) => setInputRef(`${b.id}_target`, el)}
                      type="text"
                      className={`${styles.slotSub} ${!b.target ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (b.target || ' ').length) * 1.1 + 0.6}ch` }}
                      value={b.target ?? ''}
                      placeholder=""
                      onChange={(e) => updateBlock(b.id, { target: e.target.value })}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'target' })}
                      disabled={disabled}
                    />
                  </span>
                </span>
                <input
                  ref={(el) => setInputRef(`${b.id}_expr`, el)}
                  type="text"
                  className={`${styles.mathSlot} ${!b.expr ? styles.emptySlot : styles.filledSlot}`}
                  style={{ width: `${Math.max(1, (b.expr || ' ').length) * 1.1 + 0.6}ch` }}
                  value={b.expr}
                  placeholder=""
                  onChange={(e) => updateBlock(b.id, { expr: e.target.value })}
                  onFocus={() => setFocusedTarget({ blockId: b.id, slot: 'expr' })}
                  onKeyDown={(e) => handleSlotKeyDown(e, b, 'expr', idx)}
                  disabled={disabled}
                />
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
                    <input
                      ref={(el) => setInputRef(`${b.id}_item_${itIdx}`, el)}
                      type="text"
                      className={`${styles.mathSlot} ${!item ? styles.emptySlot : styles.filledSlot}`}
                      style={{ width: `${Math.max(1, (item || ' ').length) * 1.1 + 0.6}ch` }}
                      value={item}
                      placeholder=""
                      onChange={(e) => {
                        const newItems = [...b.items];
                        newItems[itIdx] = e.target.value;
                        updateBlock(b.id, { items: newItems });
                      }}
                      onFocus={() => setFocusedTarget({ blockId: b.id, slot: `item_${itIdx}` })}
                      onKeyDown={(e) => handleSlotKeyDown(e, b, `item_${itIdx}`, idx)}
                      disabled={disabled}
                    />
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
                        <input
                          key={cIdx}
                          ref={(el) => setInputRef(`${b.id}_cell_${rIdx}_${cIdx}`, el)}
                          type="text"
                          className={`${styles.mathSlot} ${!cell ? styles.emptySlot : styles.filledSlot}`}
                          style={{ width: `${Math.max(1, (cell || ' ').length) * 1.1 + 0.6}ch` }}
                          value={cell}
                          placeholder=""
                          onChange={(e) => {
                            const newCells = b.cells.map((r, ri) =>
                              ri === rIdx ? r.map((c, ci) => (ci === cIdx ? e.target.value : c)) : r
                            );
                            updateBlock(b.id, { cells: newCells });
                          }}
                          onFocus={() => setFocusedTarget({ blockId: b.id, slot: `cell_${rIdx}_${cIdx}` })}
                          onKeyDown={(e) => handleSlotKeyDown(e, b, `cell_${rIdx}_${cIdx}`, idx)}
                          disabled={disabled}
                        />
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
      </div>
    );
  }
);
