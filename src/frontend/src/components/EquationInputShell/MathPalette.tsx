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
            {btn.displayLabel}
          </button>
        ))}
      </div>
    </div>
  );
};
