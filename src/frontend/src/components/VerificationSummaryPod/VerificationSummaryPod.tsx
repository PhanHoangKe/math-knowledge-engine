import React, { useState } from 'react';
import type { VerificationCertificate, SolutionOutcome } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { VERIFICATION_OUTCOME_I18N } from '../../i18n/enumMappings';
import { VerificationPanel } from '../VerificationPanel/VerificationPanel';
import styles from './VerificationSummaryPod.module.css';

export interface VerificationSummaryPodProps {
  certificate: VerificationCertificate;
  verificationScope?: 'FINAL_SOLUTION' | string;
  solutionOutcome?: SolutionOutcome;
}

type CriterionState = 'VERIFIED' | 'FAILED' | 'NOT_APPLICABLE';

function getCriterionState(applicable: boolean, passed: boolean): CriterionState {
  if (!applicable) return 'NOT_APPLICABLE';
  return passed ? 'VERIFIED' : 'FAILED';
}

export const VerificationSummaryPod: React.FC<VerificationSummaryPodProps> = ({
  certificate,
  verificationScope = 'FINAL_SOLUTION',
  solutionOutcome,
}) => {
  const { t } = usePreferences();
  const [isExpanded, setIsExpanded] = useState(false);

  const isComplete = certificate.outcome === 'VERIFIED_COMPLETE';

  const isVietaApplicable =
    solutionOutcome === 'TWO_DISTINCT_REAL_ROOTS' || solutionOutcome === 'ONE_REPEATED_REAL_ROOT';
  const isMultiplicityApplicable = solutionOutcome === 'ONE_REPEATED_REAL_ROOT';
  const isNoRealRootsApplicable = solutionOutcome === 'NO_REAL_ROOTS';

  const multiplicityState = getCriterionState(
    isMultiplicityApplicable,
    certificate.multiplicity_verified
  );
  const vietaState = getCriterionState(
    isVietaApplicable,
    certificate.vieta_relations_checked
  );
  const noRealRootsState = getCriterionState(
    isNoRealRootsApplicable,
    certificate.no_real_roots_verified
  );

  const getStatusLabel = (state: CriterionState): string => {
    switch (state) {
      case 'VERIFIED':
        return t('lbl_status_verified');
      case 'FAILED':
        return t('lbl_status_failed');
      case 'NOT_APPLICABLE':
      default:
        return t('lbl_status_not_applicable');
    }
  };

  const getStatusClass = (state: CriterionState): string => {
    switch (state) {
      case 'VERIFIED':
        return styles.checkPass ?? '';
      case 'FAILED':
        return styles.checkFail ?? '';
      case 'NOT_APPLICABLE':
      default:
        return styles.checkNeutral ?? '';
    }
  };

  return (
    <div className={styles.podContainer} data-testid="verification-summary-pod">
      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.headerLeft}>
            <div>
              <h2 className={styles.podTitle}>{t('pod_verification_title')}</h2>
              <span className={styles.verifierName}>
                {certificate.verifier_name} (v{certificate.verifier_version})
              </span>
            </div>
          </div>
          <span
            className={`${styles.outcomeBadge} ${isComplete ? styles.badgeSuccess : styles.badgeFailed}`}
            data-testid="verification-outcome-badge"
          >
            {t(VERIFICATION_OUTCOME_I18N[certificate.outcome])}
          </span>
        </div>

        {/* Disclaimer */}
        <div className={styles.disclaimerBox} data-testid="verification-disclaimer">
          <span className={styles.disclaimerText}>{t('lbl_cert_disclaimer')}</span>
        </div>

        {/* Quick Criteria Badges */}
        <div className={styles.criteriaGrid}>
          <div
            className={`${styles.checkItem} ${getStatusClass(multiplicityState)}`}
            data-testid="check-multiplicity"
          >
            <span className={styles.checkIcon}>{getStatusLabel(multiplicityState)}</span>
            <span className={styles.checkLabel}>{t('lbl_cert_multiplicity')}</span>
          </div>

          <div
            className={`${styles.checkItem} ${getStatusClass(vietaState)}`}
            data-testid="check-vieta"
          >
            <span className={styles.checkIcon}>{getStatusLabel(vietaState)}</span>
            <span className={styles.checkLabel}>{t('lbl_cert_vieta')}</span>
          </div>

          <div
            className={`${styles.checkItem} ${getStatusClass(noRealRootsState)}`}
            data-testid="check-no-real-roots"
          >
            <span className={styles.checkIcon}>{getStatusLabel(noRealRootsState)}</span>
            <span className={styles.checkLabel}>{t('lbl_cert_no_real_roots')}</span>
          </div>
        </div>

        {/* Technical Details Disclosure */}
        <details className={styles.technicalDetails} data-testid="verification-technical-details">
          <summary className={styles.technicalSummary}>
            {t('lbl_technical_details')}
          </summary>
          <div className={styles.metaGrid}>
            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t('lbl_cert_id')}:</span>
              <code className={styles.metaValue} data-testid="certificate-id">
                {certificate.certificate_id}
              </code>
            </div>

            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t('lbl_cert_fingerprint')}:</span>
              <code className={styles.metaValue} data-testid="integrity-fingerprint">
                {certificate.integrity_fingerprint}
              </code>
            </div>

            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t('lbl_cert_verifier')}:</span>
              <span className={styles.verifierText}>
                {certificate.verifier_name} (v{certificate.verifier_version})
              </span>
            </div>

            {certificate.verified_at_utc && (
              <div className={styles.metaRow}>
                <span className={styles.metaLabel}>{t('lbl_cert_timestamp')}:</span>
                <span className={styles.metaText}>{certificate.verified_at_utc}</span>
              </div>
            )}

            <div className={styles.metaRow}>
              <span className={styles.metaLabel}>{t('lbl_cert_scope')}:</span>
              <span className={styles.scopeBadge}>{verificationScope}</span>
            </div>
          </div>
        </details>

        {/* Action Toggle for Full Details */}
        <div className={styles.actionRow}>
          <button
            type="button"
            className={styles.toggleVerificationBtn}
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            data-testid="toggle-verification-btn"
          >
            {isExpanded ? t('btn_hide_full_verification') : t('btn_show_full_verification')}
          </button>
        </div>
      </div>

      {/* Expanded Full Verification Panel */}
      {isExpanded && (
        <div className={styles.expandedVerificationSection}>
          <VerificationPanel
            certificate={certificate}
            verificationScope={verificationScope}
            solutionOutcome={solutionOutcome}
          />
        </div>
      )}
    </div>
  );
};
