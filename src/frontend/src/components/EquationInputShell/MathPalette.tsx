import React from 'react';
import { usePreferences } from '../../state/preferences';
import { PALETTE_CATEGORIES, type PaletteButtonDef } from './mathPaletteCapabilities';
import styles from './MathPalette.module.css';

export interface MathPaletteProps {
  selectedCategory?: string;
  onAction: (actionId: string) => void;
  disabled?: boolean;
}

export const MathPalette: React.FC<MathPaletteProps> = ({
  selectedCategory = 'COMMON',
  onAction,
  disabled = false,
}) => {
  const { t } = usePreferences();

  const currentCategory =
    PALETTE_CATEGORIES.find((cat) => cat.categoryId === selectedCategory) ||
    PALETTE_CATEGORIES[0]!;

  const handleButtonClick = (e: React.MouseEvent, button: PaletteButtonDef) => {
    e.preventDefault();
    if (!disabled && button.isEnabled) {
      onAction(button.actionId);
    }
  };

  const renderVisualButtonContent = (btn: PaletteButtonDef) => {
    switch (btn.actionId) {
      case 'FRACTION':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnBox} />
            <span className={styles.btnFracBar} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'POWER':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnBox} />
            <span className={styles.btnSuperBox} />
          </span>
        );
      case 'SQRT':
        return (
          <span className={styles.btnSqrt}>
            <span className={styles.btnSqrtSym}>√</span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'CUBE_ROOT':
        return (
          <span className={styles.btnNthRoot}>
            <span className={styles.btnRootIdx}>3</span>
            <span className={styles.btnSqrtSym}>√</span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'NTH_ROOT':
        return (
          <span className={styles.btnNthRoot}>
            <span className={styles.btnRootIdx}><span className={styles.btnTinyBox} /></span>
            <span className={styles.btnSqrtSym}>√</span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'DERIVATIVE':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnText}>d</span>
            <span className={styles.btnFracBar} />
            <span className={styles.btnDerivDen}>
              <span className={styles.btnText}>d</span>
              <span className={styles.btnBox} />
            </span>
          </span>
        );
      case 'SECOND_DERIVATIVE':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnText}>d²</span>
            <span className={styles.btnFracBar} />
            <span className={styles.btnDerivDen}>
              <span className={styles.btnText}>d</span>
              <span className={styles.btnBox} />
              <span className={styles.btnText}>²</span>
            </span>
          </span>
        );
      case 'INTEGRAL':
        return (
          <span className={styles.btnInt}>
            <span className={styles.btnIntSym}>∫</span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'DEF_INTEGRAL':
        return (
          <span className={styles.btnDefInt}>
            <span className={styles.btnDefIntLimits}>
              <span className={styles.btnTinyBox} />
              <span className={styles.btnIntSym}>∫</span>
              <span className={styles.btnTinyBox} />
            </span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'SUM':
        return (
          <span className={styles.btnSum}>
            <span className={styles.btnTinyBox} />
            <span className={styles.btnSumSym}>∑</span>
            <span className={styles.btnSubBoxes}>
              <span className={styles.btnTinyBox} /><span className={styles.btnTinyBox} />
            </span>
          </span>
        );
      case 'LIMIT':
        return (
          <span className={styles.btnLim}>
            <span className={styles.btnLimText}>lim</span>
            <span className={styles.btnLimSub}>
              <span className={styles.btnMicroBox} />→<span className={styles.btnMicroBox} />
            </span>
          </span>
        );
      case 'VEC_3':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnMicroBox} />,<span className={styles.btnMicroBox} />,<span className={styles.btnMicroBox} />]
          </span>
        );
      case 'MAT_3X3':
      case 'MATRIX':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
            </span>)
          </span>
        );
      default:
        return btn.displayLabel;
    }
  };

  return (
    <div
      className={styles.paletteContainer}
      data-testid="math-palette"
      role="toolbar"
      aria-label={t(currentCategory.titleKey as any)}
    >
      <div className={styles.tilesRow} data-testid={`palette-category-${currentCategory.categoryId}`}>
        {currentCategory.buttons.map((btn) => (
          <button
            key={btn.id}
            type="button"
            className={`${styles.paletteTile} ${btn.actionId === 'CLEAR' ? styles.clearTile : ''} ${
              btn.actionId === 'BACKSPACE' ? styles.backspaceTile : ''
            }`}
            onClick={(e) => handleButtonClick(e, btn)}
            disabled={disabled || !btn.isEnabled}
            aria-label={
              btn.actionId.startsWith('DIGIT_')
                ? `${t(btn.ariaKey as any)} ${btn.displayLabel}`
                : t(btn.ariaKey as any)
            }
            data-testid={`palette-btn-${btn.actionId}`}
            title={btn.displayLabel}
          >
            {renderVisualButtonContent(btn)}
          </button>
        ))}
      </div>
    </div>
  );
};
