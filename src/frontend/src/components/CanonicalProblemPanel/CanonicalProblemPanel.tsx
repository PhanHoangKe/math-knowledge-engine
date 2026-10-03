import React, { useState } from 'react';
import type {
  CanonicalQuadraticProblemView,
  CanonicalDegenerateProblemView,
} from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { formatRational } from '../../utils/formatters';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSliders,
  faCircleInfo,
  faMagnifyingGlassPlus,
  faDownload,
  faPalette,
  faFont,
  faCheck,
} from '@fortawesome/free-solid-svg-icons';
import styles from './CanonicalProblemPanel.module.css';

export interface CanonicalProblemPanelProps {
  problem: CanonicalQuadraticProblemView | CanonicalDegenerateProblemView;
  showCoeffEditor?: boolean;
  onToggleCoeffEditor?: () => void;
  coeffEditorSlot?: React.ReactNode;
}

export const CanonicalProblemPanel: React.FC<CanonicalProblemPanelProps> = ({
  problem,
  showCoeffEditor,
  onToggleCoeffEditor,
  coeffEditorSlot,
}) => {
  const { t } = usePreferences();
  const [isZoomed, setIsZoomed] = useState(false);
  const [copiedState, setCopiedState] = useState<'data' | 'text' | null>(null);

  const isQuadratic = problem.problem_type === 'QUADRATIC';
  const quad = isQuadratic ? (problem as CanonicalQuadraticProblemView) : null;
  const degen = !isQuadratic ? (problem as CanonicalDegenerateProblemView) : null;

  const handleCopyData = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(problem.equation_latex);
      setCopiedState('data');
      setTimeout(() => setCopiedState(null), 2000);
    }
  };

  const handleCopyPlainText = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      const plain = problem.equation_latex.replace(/\\left|\\right|[\{\}]/g, '');
      navigator.clipboard.writeText(plain);
      setCopiedState('text');
      setTimeout(() => setCopiedState(null), 2000);
    }
  };

  return (
    <div className={styles.card} data-testid="canonical-problem-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <span className={styles.podTitle}>{t('lbl_input')}</span>
        </div>
      </div>

      <div className={styles.cardBody}>
        {/* Canonical Equation Render */}
        <div
          className={`${styles.equationDisplay} ${isZoomed ? styles.equationZoomed : ''}`}
          data-testid="canonical-equation-latex"
        >
          <MathLatex latex={problem.equation_latex} displayMode />
        </div>

        {/* Coefficients & Metadata Details (Collapsible / Subtle) */}
        <div className={styles.metaGrid}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('lbl_coefficients')}:</span>
            <div className={styles.coefficientsList}>
              {isQuadratic && quad ? (
                <>
                  <span className={styles.coeffTag}>
                    a = {formatRational(quad.a)}
                  </span>
                  <span className={styles.coeffTag}>
                    b = {formatRational(quad.b)}
                  </span>
                  <span className={styles.coeffTag}>
                    c = {formatRational(quad.c)}
                  </span>
                </>
              ) : degen ? (
                <>
                  <span className={styles.coeffTag}>
                    b = {formatRational(degen.b)}
                  </span>
                  <span className={styles.coeffTag}>
                    c = {formatRational(degen.c)}
                  </span>
                </>
              ) : null}
            </div>
          </div>

          {/* Discriminant (Quadratic only) */}
          {isQuadratic && quad && (
            <div className={styles.metaItem} data-testid="discriminant-display">
              <span className={styles.metaLabel}>{t('lbl_discriminant')}:</span>
              <div className={styles.discriminantValue}>
                <span className={styles.deltaValue}>
                  <MathLatex latex={`\\Delta = ${formatRational(quad.discriminant.value)}`} />
                </span>
                <div className={styles.deltaFlags}>
                  {quad.discriminant.is_positive && (
                    <span className={`${styles.flagBadge} ${styles.flagPositive}`}>
                      {t('lbl_discriminant_positive')}
                    </span>
                  )}
                  {quad.discriminant.is_zero && (
                    <span className={`${styles.flagBadge} ${styles.flagZero}`}>
                      {t('lbl_discriminant_zero')}
                    </span>
                  )}
                  {quad.discriminant.is_negative && (
                    <span className={`${styles.flagBadge} ${styles.flagNegative}`}>
                      {t('lbl_discriminant_negative')}
                    </span>
                  )}
                  {quad.discriminant.is_rational_square && (
                    <span className={`${styles.flagBadge} ${styles.flagSquare}`}>
                      {t('lbl_discriminant_perfect_square')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Technical Details Disclosure */}
          <details className={styles.technicalDetails} data-testid="canonical-technical-details">
            <summary className={styles.technicalSummary}>
              <FontAwesomeIcon icon={faSliders} style={{ marginRight: 6 }} />
              {t('lbl_technical_details')}
            </summary>
            <div className={styles.idRow}>
              <div className={styles.idGroup}>
                <span className={styles.idLabel}>{t('lbl_category') || 'Category'}:</span>
                <code className={styles.idValue}>{problem.category}</code>
              </div>
              <div className={styles.idGroup}>
                <span className={styles.idLabel}>{t('lbl_classification') || 'Classification'}:</span>
                <code className={styles.idValue}>{problem.classification}</code>
              </div>
              <div className={styles.idGroup}>
                <span className={styles.idLabel}>{t('lbl_problem_id')}:</span>
                <code className={styles.idValue}>{problem.problem_id}</code>
              </div>
              <div className={styles.idGroup}>
                <span className={styles.idLabel}>{t('lbl_semantic_hash')}:</span>
                <code className={styles.idValue}>{problem.semantic_revision_hash}</code>
              </div>
            </div>
          </details>
        </div>

        {/* Embedded Reactive Coefficient Editor (Toggled via Hover Action Bar) */}
        {showCoeffEditor && coeffEditorSlot && (
          <div className={styles.coeffEditorContainer} data-testid="embedded-coefficient-editor">
            {coeffEditorSlot}
          </div>
        )}
      </div>

      {/* WolframAlpha Style Bottom Hover Action Bar */}
      <div
        className={styles.hoverActionBar}
        data-testid="coefficient-editor-disclosure"
      >
        <button
          type="button"
          className={`${styles.actionItemBtn} ${isZoomed ? styles.actionItemActive : ''}`}
          onClick={() => setIsZoomed(!isZoomed)}
          title={t('act_zoom')}
        >
          <FontAwesomeIcon icon={faMagnifyingGlassPlus} className={styles.actionItemIcon} />
          <span>{t('act_zoom')}</span>
        </button>

        <button
          type="button"
          className={styles.actionItemBtn}
          onClick={handleCopyData}
          title={t('act_data')}
        >
          <FontAwesomeIcon
            icon={copiedState === 'data' ? faCheck : faDownload}
            className={styles.actionItemIcon}
          />
          <span>{copiedState === 'data' ? t('act_copied') : t('act_data')}</span>
        </button>

        {onToggleCoeffEditor && (
          <button
            type="button"
            className={`${styles.actionItemBtn} ${showCoeffEditor ? styles.actionItemActive : ''}`}
            onClick={onToggleCoeffEditor}
            aria-expanded={showCoeffEditor}
            data-testid="toggle-coeff-editor-btn"
            title={t('act_customize')}
          >
            <FontAwesomeIcon icon={faPalette} className={styles.actionItemIcon} />
            <span>{t('act_customize')}</span>
          </button>
        )}

        <button
          type="button"
          className={styles.actionItemBtn}
          onClick={handleCopyPlainText}
          title={t('act_plain_text')}
        >
          <FontAwesomeIcon
            icon={copiedState === 'text' ? faCheck : faFont}
            className={styles.actionItemIcon}
          />
          <span>{copiedState === 'text' ? t('act_copied') : t('act_plain_text')}</span>
        </button>
      </div>
    </div>
  );
};
