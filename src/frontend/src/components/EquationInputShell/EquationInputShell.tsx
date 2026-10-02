import React, { useState, useRef, useCallback } from 'react';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { MathPalette } from './MathPalette';
import { PALETTE_CATEGORIES } from './mathPaletteCapabilities';
import {
  serializePaletteAction,
  toVisualLatex,
  toMathModeFormat,
  toNaturalModeFormat,
  normalizeForSolver,
  isSupportedByComposer,
} from '../../utils/mathInputSerialization';
import styles from './EquationInputShell.module.css';

export type InputMode = 'quick' | 'math' | 'natural';

export interface EquationInputShellProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  isLoading?: boolean;
  statusText?: string;
  initialMode?: InputMode;
}

const SAMPLE_EQUATIONS = [
  'x^2 - 5*x + 6 = 0',
  '2*x^2 - 4*x + 2 = 0',
  'x^2 - 4 = 0',
  '3*x^2 - 6*x = 0',
  'x^2 + 2*x + 5 = 0',
  'x^2 - 2 = 0',
];

export const EquationInputShell: React.FC<EquationInputShellProps> = ({
  query,
  onQueryChange,
  onSubmit,
  onClear,
  isLoading = false,
  statusText,
  initialMode = 'natural',
}) => {
  const { t } = usePreferences();
  const [mode, setMode] = useState<'natural' | 'math'>(
    initialMode === 'math' ? 'math' : 'natural'
  );
  const [activeCategory, setActiveCategory] = useState<string | null>(
    initialMode === 'math' ? 'COMMON' : null
  );
  const [showQuickKeys, setShowQuickKeys] = useState<boolean>(false);
  const [sampleIdx, setSampleIdx] = useState<number>(0);
  const [cameraNote, setCameraNote] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onQueryChange(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !isLoading) {
        handleExecuteSolve();
      }
    }
  };

  const handleExecuteSolve = () => {
    const normalized = normalizeForSolver(query);
    if (normalized !== query) {
      onQueryChange(normalized);
    }
    onSubmit();
  };

  const switchMode = (newMode: 'natural' | 'math') => {
    if (newMode === mode) return;

    if (newMode === 'math') {
      setMode('math');
      const mathFormatted = toMathModeFormat(query);
      if (mathFormatted !== query) {
        onQueryChange(mathFormatted);
      }
      if (!activeCategory) {
        setActiveCategory('COMMON');
      }
    } else {
      setMode('natural');
      const naturalFormatted = toNaturalModeFormat(query);
      if (naturalFormatted !== query) {
        onQueryChange(naturalFormatted);
      }
      setActiveCategory(null);
    }
  };

  const toggleCategory = (catId: string) => {
    if (activeCategory === catId) {
      setActiveCategory(null);
    } else {
      setActiveCategory(catId);
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

      requestAnimationFrame(() => {
        if (input) {
          input.focus();
          input.setSelectionRange(newCursorPos, newCursorPos);
        }
      });
    },
    [query, onQueryChange, onClear]
  );

  const handleRandomSample = () => {
    const nextEq = SAMPLE_EQUATIONS[sampleIdx % SAMPLE_EQUATIONS.length] ?? 'x^2 - 5*x + 6 = 0';
    setSampleIdx((prev) => prev + 1);
    if (mode === 'math') {
      onQueryChange(toMathModeFormat(nextEq));
    } else {
      onQueryChange(nextEq);
    }
  };

  const handleCameraClick = () => {
    setCameraNote(
      t('tooltip_camera') + ' — Tính năng nhận diện hình ảnh/OCR sẵn sàng ở các phiên bản tiếp theo.'
    );
    setTimeout(() => setCameraNote(null), 3500);
  };

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

      {/* Main Pill / Capsule Input Box */}
      <div
        className={`${styles.capsuleBox} ${
          mode === 'natural' ? styles.capsuleNatural : styles.capsuleMath
        } ${isLoading ? styles.capsuleLoading : ''}`}
      >
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
            className={styles.clearCircleBtn}
            onClick={onClear}
            aria-label={t('clear_btn_aria')}
            title={t('clear_btn_aria')}
            data-testid="clear-btn"
          >
            ×
          </button>
        )}

        {/* Square Compute Button */}
        <button
          type="button"
          className={`${styles.computeBtn} ${
            mode === 'natural' ? styles.computeBtnOrange : styles.computeBtnPurple
          }`}
          aria-label={t('compute_btn_aria')}
          title={t('compute_btn_aria')}
          onClick={handleExecuteSolve}
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

      {/* Camera Note Toast if triggered */}
      {cameraNote && <div className={styles.cameraToast}>{cameraNote}</div>}

      {/* Bottom Toolbar Row (Directly below input pill) */}
      <div className={styles.toolbarRow}>
        {/* Left Side: Natural Language, Math Input, Camera */}
        <div className={styles.toolbarLeft}>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'natural'}
            className={`${styles.modePill} ${
              mode === 'natural' ? styles.modePillNaturalActive : styles.modePillInactive
            }`}
            onClick={() => switchMode('natural')}
            data-testid="mode-quick-btn"
          >
            <span className={styles.modeIcon} aria-hidden="true">⚙</span>
            <span>{t('mode_natural_input')}</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={mode === 'math'}
            className={`${styles.modePill} ${
              mode === 'math' ? styles.modePillMathActive : styles.modePillInactive
            }`}
            onClick={() => switchMode('math')}
            data-testid="mode-math-btn"
          >
            <span className={styles.modeIcon} aria-hidden="true">∫∑∂</span>
            <span>{t('mode_math_input')}</span>
          </button>

          <button
            type="button"
            className={styles.iconActionBtn}
            onClick={handleCameraClick}
            aria-label={t('tooltip_camera')}
            title={t('tooltip_camera')}
          >
            📷
          </button>
        </div>

        {/* Right Side: Category Tabs in Math mode, Quick Actions in Natural mode */}
        <div className={styles.toolbarRight}>
          {mode === 'math' ? (
            <div className={styles.mathCategoriesBar} role="tablist">
              {PALETTE_CATEGORIES.map((cat, idx) => (
                <React.Fragment key={cat.categoryId}>
                  {idx === PALETTE_CATEGORIES.length - 1 && (
                    <span className={styles.categoryDivider} aria-hidden="true">|</span>
                  )}
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeCategory === cat.categoryId}
                    className={`${styles.categoryTabBtn} ${
                      activeCategory === cat.categoryId ? styles.categoryTabActive : ''
                    }`}
                    onClick={() => toggleCategory(cat.categoryId)}
                    title={t(cat.titleKey as any)}
                    aria-label={t(cat.titleKey as any)}
                  >
                    {cat.symbol}
                    {activeCategory === cat.categoryId && (
                      <span className={styles.tabMarkerArrow} aria-hidden="true" />
                    )}
                  </button>
                </React.Fragment>
              ))}
            </div>
          ) : (
            <div className={styles.naturalActionsBar}>
              <button
                type="button"
                className={`${styles.iconActionBtn} ${showQuickKeys ? styles.iconActionActive : ''}`}
                onClick={() => setShowQuickKeys((prev) => !prev)}
                title={t('tooltip_keyboard')}
                aria-label={t('tooltip_keyboard')}
              >
                ⌨
              </button>
              <button
                type="button"
                className={styles.iconActionBtn}
                onClick={handleRandomSample}
                title={t('tooltip_samples')}
                aria-label={t('tooltip_samples')}
              >
                ▦
              </button>
              <button
                type="button"
                className={styles.iconActionBtn}
                onClick={handleCameraClick}
                title={t('tooltip_upload')}
                aria-label={t('tooltip_upload')}
              >
                ↑
              </button>
              <button
                type="button"
                className={styles.iconActionBtn}
                onClick={handleRandomSample}
                title={t('tooltip_random')}
                aria-label={t('tooltip_random')}
              >
                🔀
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Math Palette Bar (Picture 3) */}
      {mode === 'math' && activeCategory && (
        <div className={styles.paletteDrawerWrapper}>
          <MathPalette
            selectedCategory={activeCategory}
            onAction={handlePaletteAction}
            disabled={isLoading}
          />
        </div>
      )}

      {/* Expanded Quick Keys in Natural Mode if toggled */}
      {mode === 'natural' && showQuickKeys && (
        <div className={styles.quickKeysDrawer}>
          <span className={styles.quickKeysLabel}>{t('quick_keys_label')}</span>
          {['*', 'x', '^2', '^0', '/', '=', '(', ')'].map((keySymbol) => (
            <button
              key={keySymbol}
              type="button"
              className={styles.quickKeyBtn}
              onClick={() => handlePaletteAction(keySymbol)}
              disabled={isLoading}
            >
              {keySymbol}
            </button>
          ))}
        </div>
      )}

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

      {/* Status Note Indicator */}
      <div className={styles.statusNote}>
        <span
          className={`${styles.statusDot} ${isLoading ? styles.statusDotActive : ''}`}
          aria-hidden="true"
        />
        <span data-testid="shell-status-text">
          {statusText || (isLoading ? t('shell_status_loading') : t('shell_status_idle'))}
        </span>
      </div>
    </section>
  );
};
