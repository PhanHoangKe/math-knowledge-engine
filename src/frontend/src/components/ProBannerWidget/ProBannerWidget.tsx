import React from 'react';
import { usePreferences } from '../../state/preferences';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheckSquare, faArrowRight, faWandMagicSparkles } from '@fortawesome/free-solid-svg-icons';
import styles from './ProBannerWidget.module.css';

export interface ProBannerWidgetProps {
  onOpenStepByStep?: () => void;
}

export const ProBannerWidget: React.FC<ProBannerWidgetProps> = ({ onOpenStepByStep }) => {
  const { t } = usePreferences();

  return (
    <aside className={styles.proWidget} data-testid="pro-banner-widget">
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>{t('pro_widget_title') || 'Get help with that first step (and all the others)'}</h3>
      </div>
      <div className={styles.widgetBody}>
        <div className={styles.stepPreviewBox}>
          <span className={styles.stepTag}>STEP 1</span>
          <p className={styles.stepDesc}>
            {t('pro_widget_desc') || 'Calculate the discriminant Δ and apply the quadratic formula to find all real roots:'}
          </p>
          <div className={styles.stepFormula}>
            \Delta = b^2 - 4ac
          </div>
        </div>
        <button
          type="button"
          className={styles.proCtaBtn}
          onClick={onOpenStepByStep}
          data-testid="pro-widget-cta"
        >
          <div className={styles.btnContent}>
            <span className={styles.btnIcon}>
              <FontAwesomeIcon icon={faCheckSquare} />
            </span>
            <div className={styles.btnTextCol}>
              <span className={styles.btnTitle}>Step-by-Step Solutions</span>
              <span className={styles.btnSub}>with MKE Knowledge Engine</span>
            </div>
          </div>
          <span className={styles.ctaBadge}>
            Explore <FontAwesomeIcon icon={faArrowRight} style={{ marginLeft: 4 }} />
          </span>
        </button>
      </div>
    </aside>
  );
};
