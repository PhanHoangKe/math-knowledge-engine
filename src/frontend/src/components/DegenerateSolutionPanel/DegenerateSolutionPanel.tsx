import React from 'react';
import type { DegenerateSolutionView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { SOLUTION_OUTCOME_I18N } from '../../i18n/enumMappings';
import { MathLatex } from '../MathLatex/MathLatex';
import { VerificationPanel } from '../VerificationPanel/VerificationPanel';
import { formatRational } from '../../utils/formatters';
import styles from './DegenerateSolutionPanel.module.css';

export interface DegenerateSolutionPanelProps {
  solution: DegenerateSolutionView;
}

export const DegenerateSolutionPanel: React.FC<DegenerateSolutionPanelProps> = ({ solution }) => {
  const { t } = usePreferences();

  return (
    <div className={styles.container} data-testid="degenerate-solution-panel">
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <div className={styles.headerLeft}>
            <h2 className={styles.cardTitle}>{t('panel_degenerate_solution')}</h2>
          </div>
          <span className={styles.outcomeBadge} data-testid="degenerate-outcome-badge">
            {t(SOLUTION_OUTCOME_I18N[solution.outcome])}
          </span>
        </div>

        <div className={styles.cardBody}>
          <div className={styles.finalAnswerSection}>
            <span className={styles.sectionLabel}>{t('lbl_final_answer')}:</span>
            <div className={styles.finalAnswerDisplay} data-testid="degenerate-final-answer">
              <MathLatex latex={solution.final_answer_latex} displayMode />
            </div>
          </div>

          {solution.linear_root && (
            <div className={styles.rootSection} data-testid="degenerate-linear-root">
              <span className={styles.sectionLabel}>{t('lbl_linear_single_root')}</span>
              <div className={styles.rootDisplay}>
                <MathLatex latex={`x = ${formatRational(solution.linear_root)}`} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Verification Certificate for Degenerate Equation with explicit verification scope */}
      {solution.certificate && (
        <VerificationPanel
          certificate={solution.certificate}
          verificationScope={solution.verification_scope}
        />
      )}
    </div>
  );
};
