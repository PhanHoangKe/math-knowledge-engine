import React from 'react';
import type { RevisionHistoryEntry } from '../../state/useAlgebraWorkspace';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import styles from './RevisionHistoryPanel.module.css';

export interface RevisionHistoryPanelProps {
  history: RevisionHistoryEntry[];
}

export const RevisionHistoryPanel: React.FC<RevisionHistoryPanelProps> = ({
  history,
}) => {
  const { t } = usePreferences();

  return (
    <div className={styles.card} data-testid="revision-history-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <svg
            className={styles.titleIcon}
            viewBox="0 0 20 20"
            fill="currentColor"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.cardTitle}>{t('panel_revision_history')}</h2>
          <span className={styles.countBadge} data-testid="revision-history-count">
            {history.length}
          </span>
        </div>
      </div>

      {history.length === 0 ? (
        <p className={styles.emptyMessage} data-testid="revision-history-empty">
          {t('lbl_history_empty')}
        </p>
      ) : (
        <div className={styles.historyList}>
          {history.map((entry, index) => {
            const isCoeffMode = entry.source_mode === 'COEFFICIENTS';
            const badgeClass = isCoeffMode ? styles.badgeCoeff : styles.badgeRaw;
            const badgeLabel = isCoeffMode ? t('badge_source_coefficients') : t('badge_source_raw');

            return (
              <div
                key={`${entry.semantic_revision_hash}-${index}`}
                className={styles.historyItem}
                data-testid="revision-history-item"
              >
                <div className={styles.itemMain}>
                  <div className={styles.itemHeader}>
                    <span className={`${styles.provenanceBadge} ${badgeClass}`}>
                      {badgeLabel}
                    </span>
                    <span className={styles.problemTypeBadge}>
                      {entry.problem_type}
                    </span>
                    <span className={styles.classificationText}>
                      {entry.classification}
                    </span>
                  </div>

                  <div className={styles.equationPreview}>
                    <MathLatex latex={entry.equation_latex} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
