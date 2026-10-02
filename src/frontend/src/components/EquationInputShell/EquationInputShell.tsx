import React, { useState, useRef, useCallback } from 'react';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { MathPalette } from './MathPalette';
import {
  serializePaletteAction,
  toVisualLatex,
  isSupportedByComposer,
} from '../../utils/mathInputSerialization';
import styles from './EquationInputShell.module.css';

export type InputMode = 'quick' | 'math';

export interface EquationInputShellProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  isLoading?: boolean;
  statusText?: string;
  initialMode?: InputMode;
}

export const EquationInputShell: React.FC<EquationInputShellProps> = ({
  query,
  onQueryChange,
  onSubmit,
  onClear,
  isLoading = false,
  statusText,
  initialMode = 'quick',
}) => {
  const { t } = usePreferences();
  const [mode, setMode] = useState<InputMode>(initialMode);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onQueryChange(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  const handlePaletteAction = useCallback(
    (actionId: string) => {
      if (actionId === 'CLEAR') {
        if (onClear) {
          onClear();
        } else {
          onQueryChange('');
        }
        return;
      }

      const input = inputRef.current;
      const selection = input
        ? { start: input.selectionStart ?? query.length, end: input.selectionEnd ?? query.length }
        : { start: query.length, end: query.length };

      const { newQuery, newCursorPos } = serializePaletteAction(query, actionId, selection);
      onQueryChange(newQuery);

      // Restore cursor focus smoothly
      requestAnimationFrame(() => {
        if (input) {
          input.focus();
          input.setSelectionRange(newCursorPos, newCursorPos);
        }
      });
    },
    [query, onQueryChange, onClear]
  );

  const insertQuickKey = useCallback(
    (snippet: string) => {
      handlePaletteAction(snippet);
    },
    [handlePaletteAction]
  );

  const isSubmitDisabled = !query.trim() || isLoading;
  const isComposerSupported = isSupportedByComposer(query);
  const visualLatex = toVisualLatex(query);

  return (
    <section className={styles.wrapper} aria-label={t('input_aria')}>
      {/* Super & Hero Motto */}
      <div className={styles.heroSection}>
        <div className={styles.heroSuper}>{t('hero_super')}</div>
        <h1 className={styles.heroTitle}>{t('hero_title')}</h1>
        <p className={styles.heroTagline}>{t('hero_tagline')}</p>
      </div>

      {/* Mode Switcher Tabs */}
      <div className={styles.modeSwitcher} role="tablist" aria-label={t('input_label')}>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'quick'}
          className={`${styles.modeTab} ${mode === 'quick' ? styles.modeTabActive : ''}`}
          onClick={() => setMode('quick')}
          data-testid="mode-quick-btn"
        >
          {t('mode_quick_input')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'math'}
          className={`${styles.modeTab} ${mode === 'math' ? styles.modeTabActive : ''}`}
          onClick={() => setMode('math')}
          data-testid="mode-math-btn"
        >
          {t('mode_math_input')}
        </button>
      </div>

      {/* Visual Math Preview Box in Math Input Mode */}
      {mode === 'math' && (
        <div className={styles.mathPreviewBox} data-testid="math-preview-box">
          <span className={styles.previewLabel}>{t('lbl_math_preview')}:</span>
          <div className={styles.previewDisplay}>
            {visualLatex ? (
              <MathLatex latex={visualLatex} displayMode />
            ) : (
              <span className={styles.previewPlaceholder}>{t('math_preview_placeholder')}</span>
            )}
          </div>
          {!isComposerSupported && (
            <div className={styles.unsupportedNotice}>
              <span>ℹ️ {t('lbl_unsupported_assisted_math')}</span>
            </div>
          )}
        </div>
      )}

      {/* Capsule Equation Input Container */}
      <div className={`${styles.capsuleBox} ${isLoading ? styles.capsuleLoading : ''}`}>
        <label htmlFor="equation-input" className="sr-only">
          {t('input_label')}
        </label>
        <input
          ref={inputRef}
          id="equation-input"
          type="text"
          className={styles.inputField}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={t('input_placeholder')}
          autoComplete="off"
          spellCheck="false"
          disabled={isLoading}
          data-testid="equation-input"
        />

        {query.length > 0 && !isLoading && (
          <button
            type="button"
            className={styles.clearBtn}
            onClick={onClear}
            aria-label={t('clear_btn_aria')}
            title={t('clear_btn_aria')}
            data-testid="clear-btn"
          >
            ×
          </button>
        )}

        {/* Compute Button */}
        <button
          type="button"
          className={styles.computeBtn}
          aria-label={t('compute_btn_aria')}
          title={t('compute_btn_aria')}
          onClick={onSubmit}
          disabled={isSubmitDisabled}
          aria-disabled={isSubmitDisabled}
          data-testid="compute-btn"
        >
          {isLoading ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            t('compute_btn_text')
          )}
        </button>
      </div>

      {/* Mode-Specific Toolbar: Full Palette in 'math' mode vs Quick Keys in 'quick' mode */}
      {mode === 'math' ? (
        <MathPalette onAction={handlePaletteAction} disabled={isLoading} />
      ) : (
        <div className={styles.subToolbar}>
          <div className={styles.quickKeysGroup} aria-label={t('quick_keys_label')}>
            <span className={styles.quickKeysLabel}>{t('quick_keys_label')}</span>
            {['*', 'x', '^2', '^0', '/', '=', '(', ')'].map((keySymbol) => (
              <button
                key={keySymbol}
                type="button"
                className={styles.quickKeyBtn}
                onClick={() => insertQuickKey(keySymbol)}
                disabled={isLoading}
              >
                {keySymbol}
              </button>
            ))}
          </div>

          <div className={styles.statusNote}>
            <span
              className={`${styles.statusDot} ${isLoading ? styles.statusDotActive : ''}`}
              aria-hidden="true"
            />
            <span data-testid="shell-status-text">
              {statusText || (isLoading ? t('shell_status_loading') : t('shell_status_idle'))}
            </span>
          </div>
        </div>
      )}
    </section>
  );
};
