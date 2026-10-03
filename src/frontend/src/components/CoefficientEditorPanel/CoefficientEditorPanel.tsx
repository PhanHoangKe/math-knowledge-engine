import React from 'react';
import { usePreferences } from '../../state/preferences';
import type {
  CoefficientsDraft,
  CoefficientsValidationErrors,
} from '../../utils/coefficients';
import type {
  WorkspaceSourceMode,
  ReactiveCoeffStatus,
} from '../../state/useAlgebraWorkspace';
import styles from './CoefficientEditorPanel.module.css';

export interface CoefficientEditorPanelProps {
  draft: CoefficientsDraft;
  errors: CoefficientsValidationErrors;
  reactiveStatus: ReactiveCoeffStatus;
  sourceMode: WorkspaceSourceMode;
  isLoading?: boolean;
  isDegenerate?: boolean;
  onUpdateField: (coeff: 'a' | 'b' | 'c', part: 'numerator' | 'denominator', value: string) => void;
  onReset: () => void;
}

export const CoefficientEditorPanel: React.FC<CoefficientEditorPanelProps> = ({
  draft,
  errors,
  reactiveStatus,
  sourceMode,
  isLoading = false,
  isDegenerate = false,
  onUpdateField,
  onReset,
}) => {
  const { t } = usePreferences();

  const getStatusText = () => {
    switch (reactiveStatus) {
      case 'debouncing':
        return t('status_coeff_debouncing');
      case 'recomputing':
        return t('status_coeff_recomputing');
      case 'updated':
        return t('status_coeff_updated');
      case 'invalid':
        return t('status_coeff_invalid');
      case 'error':
        return t('status_coeff_error');
      default:
        return t('status_coeff_idle');
    }
  };

  const getStatusClass = () => {
    switch (reactiveStatus) {
      case 'debouncing':
        return styles.statusDebouncing;
      case 'recomputing':
        return styles.statusRecomputing;
      case 'updated':
        return styles.statusUpdated;
      case 'invalid':
      case 'error':
        return styles.statusInvalid;
      default:
        return '';
    }
  };

  return (
    <div className={styles.card} data-testid="coefficient-editor-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <h2 className={styles.cardTitle}>{t('panel_coefficient_editor')}</h2>
        </div>

        <div className={styles.headerRight}>
          {sourceMode === 'COEFFICIENTS' && (
            <span className={styles.sourceBadge} data-testid="source-mode-badge">
              {t('badge_source_coefficients')}
            </span>
          )}
          <button
            type="button"
            className={styles.resetBtn}
            onClick={onReset}
            disabled={isLoading}
            data-testid="reset-coeffs-btn"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
                clipRule="evenodd"
              />
            </svg>
            {t('btn_reset_coefficients')}
          </button>
        </div>
      </div>

      <div className={styles.cardBody}>
        <div className={styles.grid}>
          {/* Coefficient a */}
          <div className={styles.coeffBox} data-testid="coeff-box-a">
            <span className={styles.coeffSymbol}>a =</span>
            <div className={styles.fractionWidget}>
              <input
                id="coeff-a-num"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.numInput} ${errors.a_numerator ? styles.inputError : ''}`}
                value={draft.a.numeratorStr}
                onChange={(e) => onUpdateField('a', 'numerator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-a-num"
                aria-label={t('lbl_numerator')}
                aria-describedby={errors.a_numerator ? 'err-a-num' : undefined}
              />
              <div className={styles.fractionBar} />
              <input
                id="coeff-a-den"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.denInput} ${errors.a_denominator ? styles.inputError : ''}`}
                value={draft.a.denominatorStr}
                onChange={(e) => onUpdateField('a', 'denominator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-a-den"
                aria-label={t('lbl_denominator')}
                aria-describedby={errors.a_denominator ? 'err-a-den' : undefined}
              />
              {(errors.a_numerator || errors.a_denominator) && (
                <div className={styles.errorStack}>
                  {errors.a_numerator && (
                    <span id="err-a-num" className={styles.fieldError} data-testid="error-a-num">
                      {t(errors.a_numerator)}
                    </span>
                  )}
                  {errors.a_denominator && (
                    <span id="err-a-den" className={styles.fieldError} data-testid="error-a-den">
                      {t(errors.a_denominator)}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Coefficient b */}
          <div className={styles.coeffBox} data-testid="coeff-box-b">
            <span className={styles.coeffSymbol}>b =</span>
            <div className={styles.fractionWidget}>
              <input
                id="coeff-b-num"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.numInput} ${errors.b_numerator ? styles.inputError : ''}`}
                value={draft.b.numeratorStr}
                onChange={(e) => onUpdateField('b', 'numerator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-b-num"
                aria-label={t('lbl_numerator')}
                aria-describedby={errors.b_numerator ? 'err-b-num' : undefined}
              />
              <div className={styles.fractionBar} />
              <input
                id="coeff-b-den"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.denInput} ${errors.b_denominator ? styles.inputError : ''}`}
                value={draft.b.denominatorStr}
                onChange={(e) => onUpdateField('b', 'denominator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-b-den"
                aria-label={t('lbl_denominator')}
                aria-describedby={errors.b_denominator ? 'err-b-den' : undefined}
              />
              {(errors.b_numerator || errors.b_denominator) && (
                <div className={styles.errorStack}>
                  {errors.b_numerator && (
                    <span id="err-b-num" className={styles.fieldError} data-testid="error-b-num">
                      {t(errors.b_numerator)}
                    </span>
                  )}
                  {errors.b_denominator && (
                    <span id="err-b-den" className={styles.fieldError} data-testid="error-b-den">
                      {t(errors.b_denominator)}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Coefficient c */}
          <div className={styles.coeffBox} data-testid="coeff-box-c">
            <span className={styles.coeffSymbol}>c =</span>
            <div className={styles.fractionWidget}>
              <input
                id="coeff-c-num"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.numInput} ${errors.c_numerator ? styles.inputError : ''}`}
                value={draft.c.numeratorStr}
                onChange={(e) => onUpdateField('c', 'numerator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-c-num"
                aria-label={t('lbl_numerator')}
                aria-describedby={errors.c_numerator ? 'err-c-num' : undefined}
              />
              <div className={styles.fractionBar} />
              <input
                id="coeff-c-den"
                type="text"
                inputMode="numeric"
                className={`${styles.fractionInput} ${styles.denInput} ${errors.c_denominator ? styles.inputError : ''}`}
                value={draft.c.denominatorStr}
                onChange={(e) => onUpdateField('c', 'denominator', e.target.value)}
                disabled={isLoading}
                data-testid="coeff-c-den"
                aria-label={t('lbl_denominator')}
                aria-describedby={errors.c_denominator ? 'err-c-den' : undefined}
              />
              {(errors.c_numerator || errors.c_denominator) && (
                <div className={styles.errorStack}>
                  {errors.c_numerator && (
                    <span id="err-c-num" className={styles.fieldError} data-testid="error-c-num">
                      {t(errors.c_numerator)}
                    </span>
                  )}
                  {errors.c_denominator && (
                    <span id="err-c-den" className={styles.fieldError} data-testid="error-c-den">
                      {t(errors.c_denominator)}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Informational notice if degenerate equation retains draft a=0 */}
        {isDegenerate && (
          <div className={styles.degenerateNotice} data-testid="draft-editor-notice">
            {t('lbl_draft_editor_notice')}
          </div>
        )}

        {/* Polite live reactive status bar */}
        <div
          className={`${styles.statusBar} ${getStatusClass()}`}
          data-testid="reactive-status"
          aria-live="polite"
        >
          <span>{getStatusText()}</span>
        </div>
      </div>
    </div>
  );
};
