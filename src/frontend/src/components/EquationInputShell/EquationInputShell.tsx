import React, { useState, useRef, useCallback } from 'react';
import { usePreferences } from '../../state/preferences';
import { MathPalette } from './MathPalette';
import { AllMathInputsModal } from './AllMathInputsModal';
import { PALETTE_CATEGORIES } from './mathPaletteCapabilities';
import {
  VisualMathComposer,
  VisualMathComposerHandle,
} from './VisualMathComposer';
import {
  serializePaletteAction,
  toMathModeFormat,
  toNaturalModeFormat,
  normalizeForSolver,
} from '../../utils/mathInputSerialization';
import {
  GearIcon,
  MathSymbolsIcon,
  CameraIcon,
  StarIcon,
  SquareRootIcon,
  CalculusIcon,
  MatrixIcon,
  WaveIcon,
  GreekIcon,
  EllipsisIcon,
  KeyboardIcon,
  GridIcon,
  UploadIcon,
  ShuffleIcon,
  TimesCircleIcon,
  EqualsIcon,
} from '../common/Icons';
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

export const NATURAL_MATH_KEYS: string[][] = [
  ['π', '°', '∞', '√', '∫', 'Σ', '∂', 'Π', '∀', '∃', '∪', '∩', '∇', 'Δ', 'α', 'β'],
  ['γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'κ', 'λ', 'μ', 'ν', 'ξ', 'ρ', 'σ', 'τ', 'φ', 'χ'],
  ['ψ', 'ω', 'Γ', 'Θ', 'Λ', 'Ξ', 'Υ', 'Φ', 'Ψ', 'Ω', '℧', 'Å', 'ħ', 'ℵ', '⇄', '→'],
  ['⊕', '⊙', '♂', '♀', '†', '≠', '≥', '≤'],
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
  const [isAllMathModalOpen, setIsAllMathModalOpen] = useState<boolean>(false);
  const [showMoreMenu, setShowMoreMenu] = useState<boolean>(false);

  const mainInputRef = useRef<HTMLInputElement>(null);
  const composerRef = useRef<VisualMathComposerHandle>(null);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawVal = e.target.value;
    if (mode === 'math') {
      onQueryChange(toMathModeFormat(rawVal));
    } else {
      onQueryChange(rawVal);
    }
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
    if (catId === 'MORE') {
      setShowMoreMenu((prev) => !prev);
      return;
    }
    setShowMoreMenu(false);
    if (activeCategory === catId) {
      setActiveCategory(null);
    } else {
      setActiveCategory(catId);
    }
  };

  const handlePaletteAction = useCallback(
    (actionId: string) => {
      if (actionId === 'CLEAR') {
        if (composerRef.current) {
          composerRef.current.clear();
        }
        if (onClear) {
          onClear();
        } else {
          onQueryChange('');
        }
        return;
      }

      if (mode === 'math' && composerRef.current) {
        composerRef.current.insertPaletteAction(actionId);
        return;
      }

      const input = mainInputRef.current;
      const selection = input
        ? { start: input.selectionStart ?? query.length, end: input.selectionEnd ?? query.length }
        : { start: query.length, end: query.length };

      const { newQuery, newCursorPos } = serializePaletteAction(query, actionId, selection);
      const formatted = mode === 'math' ? toMathModeFormat(newQuery) : newQuery;
      onQueryChange(formatted);

      requestAnimationFrame(() => {
        if (input) {
          input.focus();
          input.setSelectionRange(newCursorPos, newCursorPos);
        }
      });
    },
    [query, onQueryChange, onClear, mode]
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
      'Tính năng Tải lên tệp / OCR nhận diện đang được phát triển ở các phiên bản tiếp theo.'
    );
    setTimeout(() => setCameraNote(null), 3500);
  };

  const handleScrollToTopics = () => {
    const elem = document.querySelector('[data-testid="workspace-empty-state"]');
    if (elem) {
      elem.scrollIntoView({ behavior: 'smooth' });
    } else {
      handleRandomSample();
    }
  };

  const handleClearAll = () => {
    if (composerRef.current) {
      composerRef.current.clear();
    }
    onClear();
  };

  const isSubmitDisabled = !query.trim() || isLoading;

  const renderCategoryIcon = (catId: string) => {
    switch (catId) {
      case 'COMMON': return <StarIcon size={14} />;
      case 'ALGEBRA': return <SquareRootIcon size={14} />;
      case 'CALCULUS': return <CalculusIcon size={14} />;
      case 'MATRICES': return <MatrixIcon size={14} />;
      case 'PLOTS': return <WaveIcon size={14} />;
      case 'GREEK': return <GreekIcon size={14} />;
      case 'MORE': return <EllipsisIcon size={14} />;
      default: return <StarIcon size={14} />;
    }
  };

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

        {mode === 'math' ? (
          /* Visual Interactive Math Composer (x² with editable slot [2], Casio templates, etc.) */
          <>
            <input
              type="hidden"
              id="equation-input"
              value={query}
              data-testid="equation-input"
              readOnly
            />
            <VisualMathComposer
              ref={composerRef}
              rawQuery={query}
              onChange={onQueryChange}
              onSubmit={handleExecuteSolve}
              disabled={isLoading}
              placeholder={t('input_placeholder')}
              data-testid="visual-math-composer"
            />
          </>
        ) : (
          /* Natural Language Raw Text Input */
          <input
            ref={mainInputRef}
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
        )}

        {/* Circular Clear Button (FontAwesome Circle Xmark) */}
        {query.length > 0 && !isLoading && (
          <button
            type="button"
            className={styles.clearCircleBtn}
            onClick={handleClearAll}
            aria-label={t('clear_btn_aria')}
            title={t('clear_btn_aria')}
            data-testid="clear-btn"
          >
            <TimesCircleIcon size={16} />
          </button>
        )}

        {/* Square Compute Button (FontAwesome Equals) */}
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
            <EqualsIcon size={18} />
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
            <span className={styles.modeIcon} aria-hidden="true">
              <GearIcon size={14} />
            </span>
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
            <span className={styles.modeIcon} aria-hidden="true">
              <MathSymbolsIcon size={15} />
            </span>
            <span>{t('mode_math_input')}</span>
          </button>

          <button
            type="button"
            className={styles.iconActionBtn}
            onClick={handleCameraClick}
            aria-label={t('tooltip_camera')}
            title={t('tooltip_camera')}
          >
            <CameraIcon size={15} />
          </button>
        </div>

        {/* Right Side: Category Tabs in Math mode, Quick Actions in Natural mode */}
        <div className={styles.toolbarRight}>
          {mode === 'math' ? (
            <div className={styles.mathCategoriesBar} role="tablist">
              {PALETTE_CATEGORIES.map((cat, idx) => {
                const isMore = cat.categoryId === 'MORE';
                return (
                  <React.Fragment key={cat.categoryId}>
                    {idx === PALETTE_CATEGORIES.length - 1 && (
                      <span className={styles.categoryDivider} aria-hidden="true">|</span>
                    )}
                    {isMore ? (
                      <div className={styles.moreMenuWrapper} ref={moreMenuRef}>
                        <button
                          type="button"
                          role="tab"
                          aria-selected={showMoreMenu}
                          className={`${styles.categoryTabBtn} ${showMoreMenu ? styles.categoryTabActive : ''}`}
                          onClick={() => toggleCategory('MORE')}
                          title={t('cat_more')}
                          aria-label={t('cat_more')}
                        >
                          {renderCategoryIcon(cat.categoryId)}
                          {showMoreMenu && (
                            <span className={styles.tabMarkerArrow} aria-hidden="true" />
                          )}
                        </button>
                        {showMoreMenu && (
                          <div className={styles.moreMenuPopover} role="menu">
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                setIsAllMathModalOpen(true);
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <GridIcon size={14} />
                              </span>
                              <span>{t('all_math_inputs_title')}</span>
                            </button>
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                handleRandomSample();
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <StarIcon size={14} />
                              </span>
                              <span>Ví Dụ</span>
                            </button>
                            <div className={styles.moreMenuSectionHeader}>TẢI LÊN VÀ PHÂN TÍCH</div>
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                handleCameraClick();
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <CameraIcon size={14} />
                              </span>
                              <span>Đầu Vào Hình Ảnh</span>
                            </button>
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                setCameraNote('Nhập dữ liệu bảng / file khả dụng ở các bản phát hành tiếp theo.');
                                setTimeout(() => setCameraNote(null), 3500);
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <MatrixIcon size={14} />
                              </span>
                              <span>Nhập Dữ Liệu</span>
                            </button>
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                handleCameraClick();
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <UploadIcon size={14} />
                              </span>
                              <span>Tải Lên Tệp</span>
                            </button>
                            <button
                              type="button"
                              className={styles.moreMenuItem}
                              onClick={() => {
                                setShowMoreMenu(false);
                                handleRandomSample();
                              }}
                            >
                              <span className={styles.moreMenuItemIcon}>
                                <ShuffleIcon size={14} />
                              </span>
                              <span>Ngẫu Nhiên</span>
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
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
                        {renderCategoryIcon(cat.categoryId)}
                        {activeCategory === cat.categoryId && (
                          <span className={styles.tabMarkerArrow} aria-hidden="true" />
                        )}
                      </button>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          ) : (
            <div className={styles.naturalActionsBar}>
              <button
                type="button"
                className={`${styles.naturalTabBtn} ${showQuickKeys ? styles.naturalTabActive : ''}`}
                onClick={() => setShowQuickKeys((prev) => !prev)}
                title={t('tooltip_keyboard')}
                aria-label={t('tooltip_keyboard')}
                aria-expanded={showQuickKeys}
              >
                <KeyboardIcon size={15} />
              </button>
              <button
                type="button"
                className={styles.naturalActionIconBtn}
                onClick={handleScrollToTopics}
                title={t('tooltip_samples')}
                aria-label={t('tooltip_samples')}
              >
                <GridIcon size={15} />
              </button>
              <button
                type="button"
                className={styles.naturalActionIconBtn}
                onClick={handleCameraClick}
                title={t('tooltip_upload')}
                aria-label={t('tooltip_upload')}
              >
                <UploadIcon size={15} />
              </button>
              <button
                type="button"
                className={styles.naturalActionIconBtn}
                onClick={handleRandomSample}
                title={t('tooltip_random')}
                aria-label={t('tooltip_random')}
              >
                <ShuffleIcon size={15} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Math Palette Bar */}
      {mode === 'math' && activeCategory && activeCategory !== 'MORE' && (
        <div className={styles.paletteDrawerWrapper}>
          <MathPalette
            selectedCategory={activeCategory}
            onAction={handlePaletteAction}
            disabled={isLoading}
          />
        </div>
      )}

      {/* Expanded Natural Math Drawer in Natural Mode if toggled */}
      {mode === 'natural' && showQuickKeys && (
        <div className={styles.naturalMathDrawer} data-testid="natural-math-drawer">
          <div className={styles.naturalMathGrid}>
            {NATURAL_MATH_KEYS.map((row, rowIdx) => (
              <div key={rowIdx} className={styles.naturalMathRow}>
                {row.map((symbol) => (
                  <button
                    key={symbol}
                    type="button"
                    className={styles.naturalMathKeyBtn}
                    onClick={() => handlePaletteAction(symbol)}
                    disabled={isLoading}
                    title={`Chèn ${symbol}`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            ))}
          </div>
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

      {/* All Math Inputs Modal */}
      <AllMathInputsModal
        isOpen={isAllMathModalOpen}
        onClose={() => setIsAllMathModalOpen(false)}
        onSelectAction={handlePaletteAction}
      />
    </section>
  );
};

