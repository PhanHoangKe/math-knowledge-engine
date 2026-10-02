import React from 'react';
import type { TransportErrorResponse } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './TransportErrorPanel.module.css';

export interface TransportErrorPanelProps {
  error: TransportErrorResponse;
  httpStatus?: number | null;
}

const SAFE_WHITELIST_KEYS = new Set([
  'expected_content_type',
  'max_bytes',
  'actual_bytes',
  'safe_expected_field',
  'field',
  'reason',
  'path',
]);

interface SafeValidationError {
  loc?: string;
  msg?: string;
  type?: string;
}

interface SafeDetailItem {
  key: string;
  value: string;
}

function extractSafeDetails(details: Record<string, unknown> | undefined): {
  validationErrors: SafeValidationError[];
  scalarDetails: SafeDetailItem[];
} {
  const validationErrors: SafeValidationError[] = [];
  const scalarDetails: SafeDetailItem[] = [];

  if (!details || typeof details !== 'object') {
    return { validationErrors, scalarDetails };
  }

  // If details has an errors array or detail array (e.g., Pydantic validation items)
  const candidateArray = Array.isArray(details)
    ? details
    : Array.isArray(details.errors)
    ? details.errors
    : Array.isArray(details.detail)
    ? details.detail
    : null;

  if (candidateArray) {
    for (const item of candidateArray) {
      if (item && typeof item === 'object') {
        const errObj = item as Record<string, unknown>;
        const loc = Array.isArray(errObj.loc)
          ? errObj.loc.map(String).join(' → ')
          : typeof errObj.loc === 'string'
          ? errObj.loc
          : undefined;
        const msg = typeof errObj.msg === 'string' ? errObj.msg : undefined;
        const type = typeof errObj.type === 'string' ? errObj.type : undefined;
        if (loc || msg || type) {
          validationErrors.push({ loc, msg, type });
        }
      }
    }
  }

  // Process scalar keys against strict whitelist
  for (const [key, val] of Object.entries(details)) {
    if (SAFE_WHITELIST_KEYS.has(key)) {
      if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
        scalarDetails.push({ key, value: String(val) });
      }
    }
  }

  return { validationErrors, scalarDetails };
}

export const TransportErrorPanel: React.FC<TransportErrorPanelProps> = ({ error, httpStatus }) => {
  const { language, t } = usePreferences();
  const localizedMsg = language === 'en' ? error.message_en : error.message_vi;

  const { validationErrors, scalarDetails } = extractSafeDetails(
    error.details as Record<string, unknown> | undefined
  );
  const hasDetails = validationErrors.length > 0 || scalarDetails.length > 0;

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

        {hasDetails && (
          <div className={styles.detailsBox} data-testid="transport-error-details">
            <span className={styles.detailsLabel}>{t('err_details_lbl')}:</span>
            {scalarDetails.map((item) => (
              <div key={item.key} className={styles.detailRow}>
                <span className={styles.detailKey}>{item.key}:</span>
                <span className={styles.detailValue}>{item.value}</span>
              </div>
            ))}
            {validationErrors.map((err, idx) => (
              <div key={idx} className={styles.validationItem} data-testid={`validation-error-${idx}`}>
                {err.loc && (
                  <div>
                    <strong>{t('lbl_validation_error_loc')}:</strong> <code>{err.loc}</code>
                  </div>
                )}
                {err.msg && (
                  <div>
                    <strong>{t('lbl_validation_error_msg')}:</strong> {err.msg}
                  </div>
                )}
                {err.type && (
                  <div>
                    <strong>{t('lbl_validation_error_type')}:</strong> <code>{err.type}</code>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
