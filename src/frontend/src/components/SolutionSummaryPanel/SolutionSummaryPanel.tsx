import React from 'react';
import type { VerifiedSolutionView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { SOLUTION_OUTCOME_I18N } from '../../i18n/enumMappings';
import { MathLatex } from '../MathLatex/MathLatex';
import styles from './SolutionSummaryPanel.module.css';

export interface SolutionSummaryPanelProps {
  solution: VerifiedSolutionView;
}

export const SolutionSummaryPanel: React.FC<SolutionSummaryPanelProps> = ({ solution }) => {
  const { t } = usePreferences();

  return (
    <div className={styles.card} data-testid="solution-summary-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <h2 className={styles.cardTitle}>{t('panel_solution_summary')}</h2>
        </div>
        <span className={styles.outcomeBadge} data-testid="solution-outcome-badge">
          {t(SOLUTION_OUTCOME_I18N[solution.outcome])}
        </span>
      </div>

      <div className={styles.cardBody}>
        {/* Final Solution Set Latex */}
        <div className={styles.finalAnswerSection}>
          <span className={styles.sectionLabel}>{t('lbl_final_answer')}:</span>
          <div className={styles.finalAnswerDisplay} data-testid="final-answer-latex">
            <MathLatex latex={solution.final_answer_latex} displayMode />
          </div>
        </div>

        {/* Real Roots List (if present) */}
        {solution.roots && solution.roots.length > 0 && (
          <div className={styles.rootsSection} data-testid="roots-list">
            <span className={styles.sectionLabel}>{t('lbl_roots_list')}:</span>
            <div className={styles.rootsGrid}>
              {solution.roots.map((root, idx) => (
                <div key={idx} className={styles.rootCard} data-testid={`root-item-${idx}`}>
                  <div className={styles.rootHeader}>
                    <span className={styles.rootIndex}>
                      <MathLatex latex={`x_{${idx + 1}}`} />
                    </span>
                    <span className={styles.rootTypeBadge}>{root.root_type}</span>
                  </div>
                  <div className={styles.rootLatex} data-testid={`root-latex-${idx}`}>
                    <MathLatex latex={`x_${idx + 1} = ${root.latex_str}`} />
                  </div>
                  {root.approximate_float !== undefined && root.approximate_float !== null && (
                    <div className={styles.rootApprox} data-testid={`root-approx-${idx}`}>
                      <span className={styles.approxLabel}>{t('lbl_root_approx')}:</span>
                      <code className={styles.approxValue}>≈ {root.approximate_float}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {solution.outcome === 'NO_REAL_ROOTS' && (
          <div className={styles.noRootsNotice} data-testid="no-real-roots-notice">
            <p>{t('lbl_no_roots')}</p>
          </div>
        )}
      </div>
    </div>
  );
};
