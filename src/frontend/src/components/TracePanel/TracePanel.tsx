import React from 'react';
import type { SolutionTrace, SolutionStep } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import styles from './TracePanel.module.css';

export interface TracePanelProps {
  trace: SolutionTrace;
}

const StepItem: React.FC<{ step: SolutionStep; depth?: number }> = ({ step, depth = 0 }) => {
  const { t } = usePreferences();

  return (
    <div
      className={`${styles.stepItem} ${depth > 0 ? styles.subStep : ''}`}
      data-testid={`trace-step-${step.step_number}`}
    >
      <div className={styles.stepHeader}>
        <span className={styles.stepNumberBadge}>
          {t('lbl_trace_step')} {step.step_number}
        </span>
        {step.rule_or_theorem_used && (
          <span className={styles.ruleBadge} data-testid={`step-rule-${step.step_number}`}>
            {step.rule_or_theorem_used}
          </span>
        )}
      </div>

      <div className={styles.stepContent}>
        <p className={styles.stepExplanation}>{step.explanation_vi}</p>
        
        {step.latex_expression && (
          <div className={styles.stepMath} data-testid={`step-latex-${step.step_number}`}>
            <MathLatex latex={step.latex_expression} displayMode />
          </div>
        )}

        {step.why_this_step_vi && (
          <div className={styles.whyBox}>
            <span className={styles.whyLabel}>{t('lbl_trace_why')}</span>
            <span className={styles.whyText}>{step.why_this_step_vi}</span>
          </div>
        )}
      </div>

      {step.sub_steps && step.sub_steps.length > 0 && (
        <div className={styles.subStepsContainer}>
          {step.sub_steps.map((sub, i) => (
            <StepItem key={i} step={sub} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const TracePanel: React.FC<TracePanelProps> = ({ trace }) => {
  const { t } = usePreferences();

  return (
    <div className={styles.card} data-testid="trace-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <h2 className={styles.cardTitle}>{t('panel_solution_trace')}</h2>
          <code className={styles.methodCode}>{trace.method_id}</code>
        </div>
      </div>

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

      <div className={styles.stepsList}>
        {trace.steps && trace.steps.length > 0 ? (
          trace.steps.map((step) => <StepItem key={step.step_number} step={step} />)
        ) : (
          <div className={styles.emptySteps}>{t('lbl_trace_empty')}</div>
        )}
      </div>
    </div>
  );
};
