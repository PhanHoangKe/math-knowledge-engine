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
      case 'SQUARE':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnBox} />
            <span className={styles.btnSuperText}>2</span>
          </span>
        );
      case 'POWER':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnBox} />
            <span className={styles.btnSuperBox} />
          </span>
        );
      case 'EXP_POW':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnText}>e</span>
            <span className={styles.btnSuperBox} />
          </span>
        );
      case 'LN':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>ln</span>(
            <span className={styles.btnBox} />)
          </span>
        );
      case 'LOG_BASE':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>log</span>
            <span className={styles.btnSubBox} />(
            <span className={styles.btnBox} />)
          </span>
        );
      case 'LOG_10':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>log</span>
            <span className={styles.btnSubText}>10</span>(
            <span className={styles.btnBox} />)
          </span>
        );
      case 'ABS':
        return (
          <span className={styles.btnInlineFunc}>
            |<span className={styles.btnBox} />|
          </span>
        );
      case 'LE':
        return (
          <span className={styles.btnRel}>
            <span className={styles.btnBox} /> ≤ <span className={styles.btnBox} />
          </span>
        );
      case 'GE':
        return (
          <span className={styles.btnRel}>
            <span className={styles.btnBox} /> ≥ <span className={styles.btnBox} />
          </span>
        );
      case 'NE':
        return (
          <span className={styles.btnRel}>
            <span className={styles.btnBox} /> ≠ <span className={styles.btnBox} />
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
            <span className={styles.btnRootIdx}><span className={styles.btnMicroBox} /></span>
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
              <span className={styles.btnSuperText}>2</span>
            </span>
          </span>
        );
      case 'PARTIAL':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnText}>∂</span>
            <span className={styles.btnFracBar} />
            <span className={styles.btnDerivDen}>
              <span className={styles.btnText}>∂</span>
              <span className={styles.btnBox} />
            </span>
          </span>
        );
      case 'SECOND_PARTIAL':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnText}>∂²</span>
            <span className={styles.btnFracBar} />
            <span className={styles.btnDerivDen}>
              <span className={styles.btnText}>∂</span>
              <span className={styles.btnBox} />
              <span className={styles.btnSuperText}>2</span>
            </span>
          </span>
        );
      case 'MIXED_PARTIAL':
        return (
          <span className={styles.btnFrac}>
            <span className={styles.btnText}>∂²</span>
            <span className={styles.btnFracBar} />
            <span className={styles.btnDerivDen}>
              <span className={styles.btnText}>∂</span>
              <span className={styles.btnBox} />
              <span className={styles.btnText}>∂</span>
              <span className={styles.btnBox} />
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
      case 'DOUBLE_INT':
        return (
          <span className={styles.btnInt}>
            <span className={styles.btnIntSym}>∬</span>
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'TRIPLE_INT':
        return (
          <span className={styles.btnInt}>
            <span className={styles.btnIntSym}>∭</span>
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'CONTOUR_INT':
        return (
          <span className={styles.btnInt}>
            <span className={styles.btnIntSym}>∮</span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'SURFACE_INT':
        return (
          <span className={styles.btnInt}>
            <span className={styles.btnIntSym}>∯</span>
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
      case 'DEF_DOUBLE_INT':
        return (
          <span className={styles.btnDefInt}>
            <span className={styles.btnDefIntLimits}>
              <span className={styles.btnTinyBox} />
              <span className={styles.btnIntSym}>∫</span>
              <span className={styles.btnTinyBox} />
            </span>
            <span className={styles.btnDefIntLimits}>
              <span className={styles.btnTinyBox} />
              <span className={styles.btnIntSym}>∫</span>
              <span className={styles.btnTinyBox} />
            </span>
            <span className={styles.btnBox} />
          </span>
        );
      case 'DEF_TRIPLE_INT':
        return (
          <span className={styles.btnDefInt}>
            <span className={styles.btnDefIntLimits}>
              <span className={styles.btnTinyBox} />
              <span className={styles.btnIntSym}>∫</span>
              <span className={styles.btnTinyBox} />
            </span>
            <span className={styles.btnDefIntLimits}>
              <span className={styles.btnTinyBox} />
              <span className={styles.btnIntSym}>∫</span>
              <span className={styles.btnTinyBox} />
            </span>
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
      case 'PRODUCT':
        return (
          <span className={styles.btnSum}>
            <span className={styles.btnTinyBox} />
            <span className={styles.btnSumSym}>∏</span>
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
      case 'LIMIT_LEFT':
        return (
          <span className={styles.btnLim}>
            <span className={styles.btnLimText}>lim</span>
            <span className={styles.btnLimSub}>
              <span className={styles.btnMicroBox} />→<span className={styles.btnMicroBox} />⁻
            </span>
          </span>
        );
      case 'LIMIT_RIGHT':
        return (
          <span className={styles.btnLim}>
            <span className={styles.btnLimText}>lim</span>
            <span className={styles.btnLimSub}>
              <span className={styles.btnMicroBox} />→<span className={styles.btnMicroBox} />⁺
            </span>
          </span>
        );
      case 'LIMIT_2D':
        return (
          <span className={styles.btnLim}>
            <span className={styles.btnLimText}>lim</span>
            <span className={styles.btnLimSub}>
              <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />→<span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
            </span>
          </span>
        );
      case 'STEP_FUNC':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>θ</span>(
            <span className={styles.btnBox} />)
          </span>
        );
      case 'DELTA_FUNC':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>δ</span>(
            <span className={styles.btnBox} />)
          </span>
        );
      case 'PIECEWISE_2':
        return (
          <span className={styles.btnPiecewise}>
            <span className={styles.btnBrace}>{'{'}</span>
            <span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
            </span>
          </span>
        );
      case 'PIECEWISE_3':
        return (
          <span className={styles.btnPiecewise}>
            <span className={styles.btnBrace}>{'{'}</span>
            <span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} />
                <span className={styles.btnMicroBox} />
              </span>
            </span>
          </span>
        );
      case 'LAPLACE':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnScriptFont}>ℒ</span>
            <span className={styles.btnSubBox} />
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'INV_LAPLACE':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnScriptFont}>ℒ</span>
            <span className={styles.btnSuperText}>-1</span>
            <span className={styles.btnSubBox} />
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'FOURIER':
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnScriptFont}>ℱ</span>
            <span className={styles.btnSubBox} />
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'INV_FOURIER':
        return (
          <span className={styles.btnPower}>
            <span className={styles.btnScriptFont}>ℱ</span>
            <span className={styles.btnSuperText}>-1</span>
            <span className={styles.btnSubBox} />
            <span className={styles.btnBox} />
            <span className={styles.btnBox} />
          </span>
        );
      case 'VEC_2':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnMicroBox} />,<span className={styles.btnMicroBox} />]
          </span>
        );
      case 'VEC_3':
      case 'VECTOR':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnMicroBox} />,<span className={styles.btnMicroBox} />,<span className={styles.btnMicroBox} />]
          </span>
        );
      case 'VEC_4':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnNanoBox} />,<span className={styles.btnNanoBox} />,<span className={styles.btnNanoBox} />,<span className={styles.btnNanoBox} />]
          </span>
        );
      case 'COL_VEC_2':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnColGrid}>
              <span className={styles.btnMicroBox} />
              <span className={styles.btnMicroBox} />
            </span>]
          </span>
        );
      case 'COL_VEC_3':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnColGrid}>
              <span className={styles.btnMicroBox} />
              <span className={styles.btnMicroBox} />
              <span className={styles.btnMicroBox} />
            </span>]
          </span>
        );
      case 'COL_VEC_4':
        return (
          <span className={styles.btnVec}>
            [<span className={styles.btnColGrid}>
              <span className={styles.btnNanoBox} />
              <span className={styles.btnNanoBox} />
              <span className={styles.btnNanoBox} />
              <span className={styles.btnNanoBox} />
            </span>]
          </span>
        );
      case 'MAT_2X2':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
            </span>)
          </span>
        );
      case 'MAT_3X3':
      case 'MATRIX':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
            </span>)
          </span>
        );
      case 'MAT_2X3':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} /><span className={styles.btnMicroBox} />
              </span>
            </span>)
          </span>
        );
      case 'MAT_3X4':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
            </span>)
          </span>
        );
      case 'MAT_4X4':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
            </span>)
          </span>
        );
      case 'MAT_5X5':
        return (
          <span className={styles.btnMat}>
            (<span className={styles.btnMatGrid}>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
              <span className={styles.btnMatRow}>
                <span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} /><span className={styles.btnNanoBox} />
              </span>
            </span>)
          </span>
        );
      case 'SIN':
      case 'COS':
      case 'TAN':
      case 'SEC':
      case 'CSC':
      case 'COT':
      case 'SINH':
      case 'COSH':
      case 'TANH':
      case 'SECH':
      case 'CSCH':
      case 'COTH': {
        const funcName = btn.actionId.toLowerCase();
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnText}>{funcName}</span>
            <span className={styles.btnBox} />
          </span>
        );
      }
      case 'ARCSIN':
      case 'ARCCOS':
      case 'ARCTAN': {
        const baseFunc = btn.actionId === 'ARCSIN' ? 'sin' : btn.actionId === 'ARCCOS' ? 'cos' : 'tan';
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnPower}>
              <span className={styles.btnText}>{baseFunc}</span>
              <span className={styles.btnSuperText}>-1</span>
            </span>
            <span className={styles.btnBox} />
          </span>
        );
      }
      case 'ARSINH':
      case 'ARCOSH':
      case 'ARTANH':
      case 'ARSECH':
      case 'ARCSCH':
      case 'ARCOTH': {
        const baseFunc = btn.actionId.replace('AR', '').toLowerCase();
        return (
          <span className={styles.btnInlineFunc}>
            <span className={styles.btnPower}>
              <span className={styles.btnText}>{baseFunc}</span>
              <span className={styles.btnSuperText}>-1</span>
            </span>
            <span className={styles.btnBox} />
          </span>
        );
      }
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
