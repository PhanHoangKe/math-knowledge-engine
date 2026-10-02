import React from 'react';
import { usePreferences } from '../../state/preferences';
import { PALETTE_GROUPS, type PaletteButtonDef } from './mathPaletteCapabilities';
import styles from './MathPalette.module.css';

export interface MathPaletteProps {
  onAction: (actionId: string) => void;
  disabled?: boolean;
}

export const MathPalette: React.FC<MathPaletteProps> = ({ onAction, disabled = false }) => {
  const { t } = usePreferences();

  const handleButtonClick = (e: React.MouseEvent, button: PaletteButtonDef) => {
    e.preventDefault(); // Prevent focus loss from input
    if (!disabled && button.isEnabled) {
      onAction(button.actionId);
    }
  };

  return (
    <div className={styles.paletteContainer} data-testid="math-palette" role="toolbar" aria-label={t('palette_group_basic')}>
      {PALETTE_GROUPS.filter((g) => g.isEnabled).map((group) => (
        <div key={group.groupId} className={styles.groupSection} data-testid={`palette-group-${group.groupId}`}>
          <span className={styles.groupTitle}>{t(group.titleKey as any)}</span>
          <div className={styles.buttonGrid}>
            {group.buttons.map((btn) => (
              <button
                key={btn.id}
                type="button"
                className={`${styles.paletteBtn} ${btn.actionId === 'CLEAR' ? styles.clearBtn : ''} ${
                  btn.actionId === 'BACKSPACE' ? styles.backspaceBtn : ''
                } ${btn.actionId === 'SQUARE' || btn.actionId === 'VAR_X' ? styles.primaryMathBtn : ''}`}
                onClick={(e) => handleButtonClick(e, btn)}
                disabled={disabled || !btn.isEnabled}
                aria-label={
                  btn.actionId.startsWith('DIGIT_')
                    ? `${t(btn.ariaKey as any)} ${btn.displayLabel}`
                    : t(btn.ariaKey as any)
                }
                data-testid={`palette-btn-${btn.actionId}`}
              >
                {btn.displayLabel}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
