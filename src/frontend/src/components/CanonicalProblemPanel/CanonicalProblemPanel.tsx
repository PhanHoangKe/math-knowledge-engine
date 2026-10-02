import React from 'react';
import type {
  CanonicalQuadraticProblemView,
  CanonicalDegenerateProblemView,
} from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { formatRational } from '../../utils/formatters';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSliders, faCircleInfo } from '@fortawesome/free-solid-svg-icons';
import styles from './CanonicalProblemPanel.module.css';

export interface CanonicalProblemPanelProps {
  problem: CanonicalQuadraticProblemView | CanonicalDegenerateProblemView;
}

export const CanonicalProblemPanel: React.FC<CanonicalProblemPanelProps> = ({ problem }) => {
  const { t } = usePreferences();
  const isQuadratic = problem.problem_type === 'QUADRATIC';
  const quad = isQuadratic ? (problem as CanonicalQuadraticProblemView) : null;
  const degen = !isQuadratic ? (problem as CanonicalDegenerateProblemView) : null;

  return (
    <div className={styles.card} data-testid="canonical-problem-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <span className={styles.podTitle}>Input:</span>
          <span className={styles.categoryBadge}>{problem.category}</span>
        </div>
        <span className={styles.classificationBadge}>
          {problem.classification}
        </span>
      </div>

      <div className={styles.cardBody}>
        {/* Canonical Equation Render */}
        <div className={styles.equationDisplay} data-testid="canonical-equation-latex">
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
                    <strong>a</strong> = {formatRational(quad.a)}
                  </span>
                  <span className={styles.coeffTag}>
                    <strong>b</strong> = {formatRational(quad.b)}
                  </span>
                  <span className={styles.coeffTag}>
                    <strong>c</strong> = {formatRational(quad.c)}
                  </span>
                </>
              ) : degen ? (
                <>
                  <span className={styles.coeffTag}>
                    <strong>b</strong> = {formatRational(degen.b)}
                  </span>
                  <span className={styles.coeffTag}>
                    <strong>c</strong> = {formatRational(degen.c)}
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
      </div>
    </div>
  );
};
