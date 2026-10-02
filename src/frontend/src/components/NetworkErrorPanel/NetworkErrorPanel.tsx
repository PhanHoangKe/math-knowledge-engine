import React from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './NetworkErrorPanel.module.css';

export interface NetworkErrorPanelProps {
  isProtocolError?: boolean;
  onRetry?: () => void;
}

export const NetworkErrorPanel: React.FC<NetworkErrorPanelProps> = ({
  isProtocolError = false,
  onRetry,
}) => {
  const { t } = usePreferences();

  return (
    <div className={styles.card} data-testid="network-error-panel">
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
              d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.366zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.366zM18 10a8 8 0 11-16 0 8 8 0 0116 0z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.cardTitle}>
            {isProtocolError ? t('err_protocol_title') : t('err_network_title')}
          </h2>
        </div>
      </div>

      <div className={styles.cardBody}>
        <p className={styles.errorMessage} data-testid="network-error-message">
          {isProtocolError ? t('err_protocol_msg') : t('err_network_msg')}
        </p>

        {onRetry && (
          <div className={styles.actionRow}>
            <button
              type="button"
              className={styles.retryBtn}
              onClick={onRetry}
              data-testid="network-retry-btn"
            >
              {t('btn_retry')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
