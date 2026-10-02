import React from 'react';
import type { MethodOptionView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './MethodCatalogPanel.module.css';

export interface MethodCatalogPanelProps {
  methods: MethodOptionView[];
  selectedMethodId?: string | null;
  onSelectMethod?: (methodId: string) => void;
  isLoading?: boolean;
}

export const MethodCatalogPanel: React.FC<MethodCatalogPanelProps> = ({
  methods,
  selectedMethodId,
  onSelectMethod,
  isLoading = false,
}) => {
  const { t } = usePreferences();

  if (!methods || methods.length === 0) {
    return null;
  }

  return (
    <div className={styles.card} data-testid="method-catalog-panel">
      <div className={styles.cardHeader}>
        <h2 className={styles.cardTitle}>{t('panel_method_catalog')}</h2>
        <span className={styles.methodCountBadge}>
          {methods.length} phương thức
        </span>
      </div>

      <div className={styles.grid}>
        {methods.map((method) => {
          const isSelected = selectedMethodId === method.method_id;
          const isApplicable = method.mathematical_applicability === 'APPLICABLE';
          const isAvailable = method.execution_availability === 'AVAILABLE';

          return (
            <div
              key={method.method_id}
              className={`${styles.methodCard} ${isSelected ? styles.cardSelected : ''} ${!isApplicable ? styles.cardInapplicable : ''}`}
              data-testid={`method-card-${method.method_id}`}
            >
              <div className={styles.methodCardHeader}>
                <div className={styles.titleGroup}>
                  <h3 className={styles.methodTitle}>{method.title_vi}</h3>
                  <code className={styles.methodId}>{method.method_id}</code>
                </div>
                <div className={styles.badgeRow}>
                  {/* Applicability Badge */}
                  <span
                    className={`${styles.badge} ${isApplicable ? styles.badgeSuccess : styles.badgeMuted}`}
                    title={t('lbl_method_applicability')}
                  >
                    {t(`enum_app_${method.mathematical_applicability}` as any)}
                  </span>
                  {/* Execution Availability Badge */}
                  <span
                    className={`${styles.badge} ${isAvailable ? styles.badgeSuccess : styles.badgeMuted}`}
                    title={t('enum_exec_AVAILABLE')}
                  >
                    {t(`enum_exec_${method.execution_availability}` as any)}
                  </span>
                  {/* Recommendation Badge */}
                  <span
                    className={`${styles.badge} ${method.pedagogical_recommendation === 'RECOMMENDED' ? styles.badgePrimary : styles.badgeNeutral}`}
                    title={t('lbl_method_recommendation')}
                  >
                    {t(`enum_rec_${method.pedagogical_recommendation}` as any)}
                  </span>
                  {/* Verification Capability */}
                  <span
                    className={`${styles.badge} ${method.verification_capability === 'HOST_VERIFIABLE' ? styles.badgeVerifiable : styles.badgeNeutral}`}
                    title={t('lbl_method_verification')}
                  >
                    {t(`enum_ver_${method.verification_capability}` as any)}
                  </span>
                </div>
              </div>

              {/* Reasons */}
              {method.reasons && method.reasons.length > 0 && (
                <div className={styles.reasonsList}>
                  <span className={styles.sectionLabel}>{t('lbl_method_reasons')}:</span>
                  <ul>
                    {method.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Prerequisites */}
              {method.prerequisites && method.prerequisites.length > 0 && (
                <div className={styles.prereqList}>
                  <span className={styles.sectionLabel}>{t('lbl_method_prerequisites')}:</span>
                  <div className={styles.prereqItems}>
                    {method.prerequisites.map((p) => (
                      <span
                        key={p.prerequisite_id}
                        className={`${styles.prereqTag} ${p.is_satisfied ? styles.prereqSatisfied : styles.prereqUnsatisfied}`}
                      >
                        {p.is_satisfied ? '✓ ' : '✗ '} {p.description_vi}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Button */}
              <div className={styles.actionRow}>
                <button
                  type="button"
                  className={`${styles.selectBtn} ${isSelected ? styles.btnActive : ''}`}
                  onClick={() => onSelectMethod?.(method.method_id)}
                  disabled={isLoading || isSelected}
                  aria-pressed={isSelected}
                >
                  {isSelected ? t('btn_selected_method') : t('btn_switch_method')}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
