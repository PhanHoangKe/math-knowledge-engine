import React from 'react';
import type { ApplicationErrorResponse } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './ApplicationErrorPanel.module.css';

export interface ApplicationErrorPanelProps {
  error: ApplicationErrorResponse;
}

export const ApplicationErrorPanel: React.FC<ApplicationErrorPanelProps> = ({ error }) => {
  const { language, t } = usePreferences();
  const localizedMsg = language === 'en' ? error.message_en : error.message_vi;

  return (
    <div className={styles.card} data-testid="application-error-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <svg
            className={styles.errorIcon}
            viewBox="0 0 20 20"
            fill="currentColor"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.cardTitle}>{t('err_app_title')}</h2>
        </div>
        <span className={styles.codeBadge} data-testid="application-error-code">
          {error.error_code}
        </span>
      </div>

      <div className={styles.cardBody}>
        <p className={styles.errorMessage} data-testid="application-error-message">
          {localizedMsg}
        </p>

        {error.span && (
          <div className={styles.spanRow} data-testid="error-span">
            <span className={styles.spanLabel}>{t('err_span_lbl')}:</span>
            <code className={styles.spanValue}>
              [{error.span.start}, {error.span.end})
            </code>
          </div>
        )}
      </div>
    </div>
  );
};
