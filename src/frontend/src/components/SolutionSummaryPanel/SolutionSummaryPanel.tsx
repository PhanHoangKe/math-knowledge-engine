import React from 'react';
import type { VerifiedSolutionView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { SOLUTION_OUTCOME_I18N } from '../../i18n/enumMappings';
import { MathLatex } from '../MathLatex/MathLatex';
import styles from './SolutionSummaryPanel.module.css';

export interface SolutionSummaryPanelProps {
  solution: VerifiedSolutionView;
  onOpenStepByStep?: () => void;
}

export const SolutionSummaryPanel: React.FC<SolutionSummaryPanelProps> = ({
  solution,
  onOpenStepByStep,
}) => {
  const { t } = usePreferences();

  return (
    <div className={styles.card} data-testid="solution-summary-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <span className={styles.podTitle}>
            {t('lbl_solutions') || 'Solutions:'}
          </span>
          <span className={styles.outcomeBadge} data-testid="solution-outcome-badge">
            {t(SOLUTION_OUTCOME_I18N[solution.outcome])}
          </span>
        </div>
        {onOpenStepByStep && (
          <button
            type="button"
            className={styles.stepByStepBtn}
            onClick={onOpenStepByStep}
            data-testid="solution-step-by-step-btn"
          >
            <span>{t('lbl_step_by_step_solution') || 'Step-by-step solution'}</span>
          </button>
        )}
      </div>

      <div className={styles.cardBody}>
        {/* Real Roots List (Clean rows matching WolframAlpha) */}
        {solution.roots && solution.roots.length > 0 && (
          <div className={styles.rootsSection} data-testid="roots-list">
            <div className={styles.rootsList}>
              {solution.roots.map((root, idx) => (
                <div key={idx} className={styles.rootRow} data-testid={`root-item-${idx}`}>
                  <div className={styles.rootLatex} data-testid={`root-latex-${idx}`}>
                    <MathLatex latex={`x_${idx + 1} = ${root.latex_str}`} displayMode />
                  </div>
                  {root.approximate_float !== undefined && root.approximate_float !== null && (
                    <div className={styles.rootApprox} data-testid={`root-approx-${idx}`}>
                      <span className={styles.approxLabel}>≈</span>
                      <code className={styles.approxValue}>{root.approximate_float}</code>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Final Solution Set Latex */}
        <div className={styles.finalAnswerSection}>
          <span className={styles.sectionLabel}>{t('lbl_final_answer')}:</span>
          <div className={styles.finalAnswerDisplay} data-testid="final-answer-latex">
            <MathLatex latex={solution.final_answer_latex} displayMode />
          </div>
        </div>

        {solution.outcome === 'NO_REAL_ROOTS' && (
          <div className={styles.noRootsNotice} data-testid="no-real-roots-notice">
            <p>{t('lbl_no_roots')}</p>
          </div>
        )}
      </div>
    </div>
  );
};
