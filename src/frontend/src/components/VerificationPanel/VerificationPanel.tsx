import React from 'react';
import type { VerificationCertificate } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './VerificationPanel.module.css';

export interface VerificationPanelProps {
  certificate: VerificationCertificate;
  verificationScope?: 'FINAL_SOLUTION' | string;
}

export const VerificationPanel: React.FC<VerificationPanelProps> = ({
  certificate,
  verificationScope = 'FINAL_SOLUTION',
}) => {
  const { t } = usePreferences();
  const isComplete = certificate.outcome === 'VERIFIED_COMPLETE';

  return (
    <div className={styles.card} data-testid="verification-panel">
      <div className={styles.cardHeader}>
        <div className={styles.headerLeft}>
          <svg
            className={styles.shieldIcon}
            viewBox="0 0 20 20"
            fill="currentColor"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className={styles.cardTitle}>{t('panel_verification')}</h2>
        </div>
        <span
          className={`${styles.outcomeBadge} ${isComplete ? styles.badgeSuccess : styles.badgeFailed}`}
          data-testid="verification-outcome-badge"
        >
          {t(`enum_ver_out_${certificate.outcome}` as any)}
        </span>
      </div>

      {/* Honesty disclaimer regarding SHA-256 content identifier vs digital signature */}
      <div className={styles.disclaimerBox} data-testid="verification-disclaimer">
        <span className={styles.disclaimerText}>{t('lbl_cert_disclaimer')}</span>
      </div>

      <div className={styles.cardBody}>
        {/* Certificate Metadata Grid */}
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

        {/* Verification Check Badges */}
        <div className={styles.checksSection}>
          <h3 className={styles.checksTitle}>Các tiêu chí kiểm chứng toán học:</h3>
          <div className={styles.checksGrid}>
            <div
              className={`${styles.checkItem} ${certificate.multiplicity_verified ? styles.checkPass : styles.checkNeutral}`}
              data-testid="check-multiplicity"
            >
              <span className={styles.checkIcon}>
                {certificate.multiplicity_verified ? '✓' : '—'}
              </span>
              <span>{t('lbl_cert_multiplicity')}</span>
            </div>

            <div
              className={`${styles.checkItem} ${certificate.vieta_relations_checked ? styles.checkPass : styles.checkNeutral}`}
              data-testid="check-vieta"
            >
              <span className={styles.checkIcon}>
                {certificate.vieta_relations_checked ? '✓' : '—'}
              </span>
              <span>{t('lbl_cert_vieta')}</span>
            </div>

            {certificate.no_real_roots_verified && (
              <div
                className={`${styles.checkItem} ${styles.checkPass}`}
                data-testid="check-no-real-roots"
              >
                <span className={styles.checkIcon}>✓</span>
                <span>Xác thực không có nghiệm thực</span>
              </div>
            )}
          </div>

          {certificate.algebraic_identities_passed &&
            certificate.algebraic_identities_passed.length > 0 && (
              <div className={styles.identitiesBox}>
                <span className={styles.identitiesLabel}>
                  {t('lbl_cert_identities')}:
                </span>
                <ul className={styles.identitiesList}>
                  {certificate.algebraic_identities_passed.map((id, i) => (
                    <li key={i}>{id}</li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      </div>
    </div>
  );
};
