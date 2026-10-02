import React, { useState } from 'react';
import type { MethodOptionView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import {
  MATHEMATICAL_APPLICABILITY_I18N,
  EXECUTION_AVAILABILITY_I18N,
  PEDAGOGICAL_RECOMMENDATION_I18N,
  VERIFICATION_CAPABILITY_I18N,
} from '../../i18n/enumMappings';
import { MethodKnowledgeSurface } from '../MethodKnowledgeSurface/MethodKnowledgeSurface';
import { MethodCatalogPanel } from '../MethodCatalogPanel/MethodCatalogPanel';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBullseye, faBookOpen, faListUl } from '@fortawesome/free-solid-svg-icons';
import styles from './SelectedMethodPod.module.css';

export interface SelectedMethodPodProps {
  methods: MethodOptionView[];
  selectedMethodId: string;
  onSelectMethod?: (methodId: string) => void;
  showAllMethods: boolean;
  onToggleShowAllMethods: () => void;
  isLoading?: boolean;
}

export const SelectedMethodPod: React.FC<SelectedMethodPodProps> = ({
  methods,
  selectedMethodId,
  onSelectMethod,
  showAllMethods,
  onToggleShowAllMethods,
  isLoading = false,
}) => {
  const { t } = usePreferences();
  const [isKnowledgeExpanded, setIsKnowledgeExpanded] = useState(false);

  const selectedMethod = methods.find((m) => m.method_id === selectedMethodId) || methods[0];

  if (!selectedMethod) {
    return null;
  }

  const isApplicable = selectedMethod.mathematical_applicability === 'APPLICABLE';
  const isAvailable = selectedMethod.execution_availability === 'AVAILABLE';

  return (
    <div className={styles.podContainer} data-testid="selected-method-summary-pod">
      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.headerLeft}>
            <span className={styles.podIcon}>
              <FontAwesomeIcon icon={faBullseye} />
            </span>
            <div>
              <h2 className={styles.podTitle}>{t('pod_method_title')}</h2>
              <span className={styles.methodTitle}>{selectedMethod.title_vi}</span>
            </div>
          </div>
          <code className={styles.methodId}>{selectedMethod.method_id}</code>
        </div>

        <div className={styles.badgeRow}>
          {/* Applicability Badge */}
          <span
            className={`${styles.badge} ${isApplicable ? styles.badgeSuccess : styles.badgeMuted}`}
            title={t('lbl_method_applicability')}
          >
            {t(MATHEMATICAL_APPLICABILITY_I18N[selectedMethod.mathematical_applicability])}
          </span>
          {/* Execution Availability Badge */}
          <span
            className={`${styles.badge} ${isAvailable ? styles.badgeSuccess : styles.badgeMuted}`}
            title={t('lbl_method_execution')}
          >
            {t(EXECUTION_AVAILABILITY_I18N[selectedMethod.execution_availability])}
          </span>
          {/* Recommendation Badge */}
          <span
            className={`${styles.badge} ${selectedMethod.pedagogical_recommendation === 'RECOMMENDED' ? styles.badgePrimary : styles.badgeNeutral}`}
            title={t('lbl_method_recommendation')}
          >
            {t(PEDAGOGICAL_RECOMMENDATION_I18N[selectedMethod.pedagogical_recommendation])}
          </span>
          {/* Verification Capability */}
          <span
            className={`${styles.badge} ${selectedMethod.verification_capability === 'HOST_VERIFIABLE' ? styles.badgeVerifiable : styles.badgeNeutral}`}
            title={t('lbl_method_verification')}
          >
            {t(VERIFICATION_CAPABILITY_I18N[selectedMethod.verification_capability])}
          </span>
        </div>

        {/* Action Controls */}
        <div className={styles.actionRow}>
          <button
            type="button"
            className={styles.whyMethodBtn}
            onClick={() => setIsKnowledgeExpanded(!isKnowledgeExpanded)}
            aria-expanded={isKnowledgeExpanded}
            data-testid={`why-method-btn-${selectedMethod.method_id}`}
          >
            <FontAwesomeIcon icon={faBookOpen} style={{ marginRight: 6 }} />
            {isKnowledgeExpanded ? t('btn_hide_knowledge') : t('btn_why_method')}
          </button>

          <button
            type="button"
            className={styles.toggleCatalogBtn}
            onClick={onToggleShowAllMethods}
            aria-expanded={showAllMethods}
            data-testid="toggle-methods-btn"
          >
            <FontAwesomeIcon icon={faListUl} style={{ marginRight: 6 }} />
            {showAllMethods
              ? t('btn_hide_all_methods')
              : t('btn_show_all_methods').replace('{count}', methods.length.toString())}
          </button>
        </div>

        {/* Knowledge Surface Drawer */}
        {isKnowledgeExpanded && (
          <MethodKnowledgeSurface
            methodId={selectedMethod.method_id}
            isOpen={isKnowledgeExpanded}
            onClose={() => setIsKnowledgeExpanded(false)}
          />
        )}
      </div>

      {/* Expanded Full Method Catalog */}
      {showAllMethods && (
        <div className={styles.expandedCatalogSection}>
          <MethodCatalogPanel
            methods={methods}
            selectedMethodId={selectedMethodId}
            onSelectMethod={onSelectMethod}
            isLoading={isLoading}
          />
        </div>
      )}
    </div>
  );
};
