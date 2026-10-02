import React, { useState } from 'react';
import type { SolutionTrace, SolutionStep } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { TracePanel } from '../TracePanel/TracePanel';
import styles from './TraceSummaryPod.module.css';

export interface TraceSummaryPodProps {
  trace: SolutionTrace;
}

export const TraceSummaryPod: React.FC<TraceSummaryPodProps> = ({ trace }) => {
  const { t } = usePreferences();
  const [isExpanded, setIsExpanded] = useState(false);

  const stepsCount = trace.steps ? trace.steps.length : 0;
  const firstStep: SolutionStep | undefined = trace.steps && trace.steps.length > 0 ? trace.steps[0] : undefined;

  return (
    <div className={styles.podContainer} data-testid="trace-summary-pod">
      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.headerLeft}>
            <span className={styles.podIcon} aria-hidden="true">📝</span>
            <div>
              <h2 className={styles.podTitle}>{t('pod_trace_title')}</h2>
              <span className={styles.stepCount}>
                {stepsCount} {t('lbl_trace_steps_unit')}
              </span>
            </div>
          </div>
          <code className={styles.methodCode}>{trace.method_id}</code>
        </div>

        {/* Disclaimer */}
        <div className={styles.disclaimerBox} data-testid="trace-disclaimer">
          <svg
            className={styles.infoIcon}
            viewBox="0 0 20 20"
            fill="currentColor"
            width="16"
            height="16"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <span className={styles.disclaimerText}>{t('lbl_trace_disclaimer')}</span>
        </div>

        {/* Preview of Step 1 (when collapsed) */}
        {!isExpanded && firstStep && (
          <div className={styles.stepPreview} data-testid={`trace-step-${firstStep.step_number}`}>
            <div className={styles.previewHeader}>
              <span className={styles.stepNumberBadge}>
                {t('lbl_trace_step')} {firstStep.step_number} ({t('lbl_preview')})
              </span>
              {firstStep.rule_or_theorem_used && (
                <span className={styles.ruleBadge} data-testid={`step-rule-${firstStep.step_number}`}>
                  {firstStep.rule_or_theorem_used}
                </span>
              )}
            </div>
            <p className={styles.stepExplanation}>{firstStep.explanation_vi}</p>
            {firstStep.latex_expression && (
              <div className={styles.stepMath} data-testid={`step-latex-${firstStep.step_number}`}>
                <MathLatex latex={firstStep.latex_expression} displayMode />
              </div>
            )}
            {firstStep.why_this_step_vi && (
              <div className={styles.whyBox}>
                <span className={styles.whyLabel}>{t('lbl_trace_why')}</span>
                <span className={styles.whyText}>{firstStep.why_this_step_vi}</span>
              </div>
            )}
          </div>
        )}

        {/* Action Toggle for Full Steps */}
        <div className={styles.actionRow}>
          <button
            type="button"
            className={styles.toggleTraceBtn}
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            data-testid="toggle-trace-btn"
          >
            {isExpanded
              ? t('btn_hide_full_trace')
              : t('btn_show_full_trace').replace('{count}', stepsCount.toString())}
          </button>
        </div>
      </div>

      {/* Expanded Full Trace Panel */}
      {isExpanded && (
        <div className={styles.expandedTraceSection}>
          <TracePanel trace={trace} />
        </div>
      )}
    </div>
  );
};
