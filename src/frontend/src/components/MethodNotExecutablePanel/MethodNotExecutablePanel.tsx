import React from 'react';
import type { NoExecutionReasonCode } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { NO_EXECUTION_REASON_I18N } from '../../i18n/enumMappings';
import styles from './MethodNotExecutablePanel.module.css';

export interface MethodNotExecutablePanelProps {
  reasonCode: NoExecutionReasonCode;
  analysisMessageVi: string;
  selectedMethodId?: string | null;
}

export const MethodNotExecutablePanel: React.FC<MethodNotExecutablePanelProps> = ({
  reasonCode,
  analysisMessageVi,
  selectedMethodId,
}) => {
  const { t } = usePreferences();

  return (
    <div className={styles.banner} data-testid="method-not-executable-panel">
      <div className={styles.bannerHeader}>
        <div className={styles.iconWrapper}>
          <svg
            viewBox="0 0 20 20"
            fill="currentColor"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className={styles.headerText}>
          <h2 className={styles.bannerTitle}>
            {t(NO_EXECUTION_REASON_I18N[reasonCode]) || t('lbl_reason_code')}
          </h2>
          {selectedMethodId && (
            <span className={styles.methodBadge}>
              {t('lbl_requested_method')} <code>{selectedMethodId}</code>
            </span>
          )}
        </div>
      </div>

      <div className={styles.bannerBody}>
        <p className={styles.messageText} data-testid="analysis-message-vi">
          {analysisMessageVi}
        </p>
      </div>
    </div>
  );
};
