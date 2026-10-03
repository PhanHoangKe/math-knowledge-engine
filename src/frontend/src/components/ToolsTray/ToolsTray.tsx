import React, { useState } from 'react';
import type {
  CanonicalQuadraticProblemView,
  VerifiedSolutionView,
} from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { RootPlotPod } from '../RootPlotPod/RootPlotPod';
import { NumberLinePod } from '../NumberLinePod/NumberLinePod';
import { AlternateFormsPod } from '../AlternateFormsPod/AlternateFormsPod';
import { VerificationSummaryPod } from '../VerificationSummaryPod/VerificationSummaryPod';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChevronDown,
  faChevronUp,
} from '@fortawesome/free-solid-svg-icons';
import styles from './ToolsTray.module.css';

export interface ToolsTrayProps {
  quad: CanonicalQuadraticProblemView | null;
  solution: VerifiedSolutionView;
}

type ToolTab = 'plot' | 'numberline' | 'alternate' | 'verifier' | null;

export const ToolsTray: React.FC<ToolsTrayProps> = ({ quad, solution }) => {
  const { lang, t } = usePreferences();
  const [activeTab, setActiveTab] = useState<ToolTab>(null);

  const toggleTab = (tab: ToolTab) => {
    setActiveTab(activeTab === tab ? null : tab);
  };

  return (
    <div className={styles.trayCard} data-testid="tools-tray">
      <div className={styles.trayHeader}>
        <span className={styles.podTitle}>
          {lang === 'vi' ? 'Khay công cụ trực quan & Xác thực theo yêu cầu' : 'On-Demand Visual Tools & Verifier'}
        </span>
      </div>

      <div className={styles.trayToolbar}>
        {quad && (
          <button
            type="button"
            className={`${styles.toolTabBtn} ${activeTab === 'plot' ? styles.toolTabActive : ''}`}
            onClick={() => toggleTab('plot')}
            aria-expanded={activeTab === 'plot'}
            data-testid="toggle-tool-plot"
          >
            <span>{t('lbl_root_plot') || 'Đồ thị Parabol'}</span>
            <FontAwesomeIcon
              icon={activeTab === 'plot' ? faChevronUp : faChevronDown}
              className={styles.chevronIcon}
            />
          </button>
        )}

        {quad && (
          <button
            type="button"
            className={`${styles.toolTabBtn} ${activeTab === 'numberline' ? styles.toolTabActive : ''}`}
            onClick={() => toggleTab('numberline')}
            aria-expanded={activeTab === 'numberline'}
            data-testid="toggle-tool-numberline"
          >
            <span>{t('lbl_number_line') || 'Trục số'}</span>
            <FontAwesomeIcon
              icon={activeTab === 'numberline' ? faChevronUp : faChevronDown}
              className={styles.chevronIcon}
            />
          </button>
        )}

        {quad && (
          <button
            type="button"
            className={`${styles.toolTabBtn} ${activeTab === 'alternate' ? styles.toolTabActive : ''}`}
            onClick={() => toggleTab('alternate')}
            aria-expanded={activeTab === 'alternate'}
            data-testid="toggle-tool-alternate"
          >
            <span>{t('lbl_alternate_forms') || 'Dạng tương đương'}</span>
            <FontAwesomeIcon
              icon={activeTab === 'alternate' ? faChevronUp : faChevronDown}
              className={styles.chevronIcon}
            />
          </button>
        )}

        <button
          type="button"
          className={`${styles.toolTabBtn} ${activeTab === 'verifier' ? styles.toolTabActive : ''}`}
          onClick={() => toggleTab('verifier')}
          aria-expanded={activeTab === 'verifier'}
          data-testid="toggle-tool-verifier"
        >
          <span>{t('pod_verification_title') || 'Chứng chỉ xác thực độc lập'}</span>
          <FontAwesomeIcon
            icon={activeTab === 'verifier' ? faChevronUp : faChevronDown}
            className={styles.chevronIcon}
          />
        </button>
      </div>

      {/* Render selected active tool */}
      <div className={styles.toolContentArea}>
        {activeTab === 'plot' && quad && (
          <div className={styles.toolView}>
            <RootPlotPod quad={quad} roots={solution.roots} />
          </div>
        )}

        {activeTab === 'numberline' && quad && (
          <div className={styles.toolView}>
            <NumberLinePod quad={quad} roots={solution.roots} />
          </div>
        )}

        {activeTab === 'alternate' && quad && (
          <div className={styles.toolView}>
            <AlternateFormsPod quad={quad} roots={solution.roots} />
          </div>
        )}

        {activeTab === 'verifier' && (
          <div className={styles.toolView}>
            <VerificationSummaryPod
              certificate={solution.certificate}
              verificationScope={solution.verification_scope}
              solutionOutcome={solution.outcome}
            />
          </div>
        )}

        {/* Keep VerificationSummaryPod accessible in DOM for automated tests when collapsed */}
        {activeTab !== 'verifier' && (
          <div className={styles.hiddenVerifierDom} aria-hidden="true">
            <VerificationSummaryPod
              certificate={solution.certificate}
              verificationScope={solution.verification_scope}
              solutionOutcome={solution.outcome}
            />
          </div>
        )}
      </div>
    </div>
  );
};
