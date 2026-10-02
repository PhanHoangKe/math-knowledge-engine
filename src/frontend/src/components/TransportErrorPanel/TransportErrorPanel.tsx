import React from 'react';
import type { TransportErrorResponse } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './TransportErrorPanel.module.css';

export interface TransportErrorPanelProps {
  error: TransportErrorResponse;
  httpStatus?: number | null;
}

export const TransportErrorPanel: React.FC<TransportErrorPanelProps> = ({ error, httpStatus }) => {
  const { language, t } = usePreferences();
  const localizedMsg = language === 'en' ? error.message_en : error.message_vi;

  return (
    <div className={styles.card} data-testid="transport-error-panel">
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
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.cardTitle}>{t('err_transport_title')}</h2>
        </div>
        <div className={styles.badges}>
          {httpStatus && <span className={styles.statusBadge}>HTTP {httpStatus}</span>}
          <span className={styles.codeBadge} data-testid="transport-error-code">
            {error.transport_error_code}
          </span>
        </div>
      </div>

      <div className={styles.cardBody}>
        <p className={styles.errorMessage} data-testid="transport-error-message">
          {localizedMsg}
        </p>

        {error.details && Object.keys(error.details).length > 0 && (
          <div className={styles.detailsBox}>
            <span className={styles.detailsLabel}>{t('err_details_lbl')}:</span>
            <pre className={styles.detailsCode}>
              {JSON.stringify(error.details, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
