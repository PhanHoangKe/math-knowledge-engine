import React from 'react';
import { usePreferences } from '../../state/preferences';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheckSquare, faArrowRight } from '@fortawesome/free-solid-svg-icons';
import { MathLatex } from '../MathLatex/MathLatex';
import styles from './ProBannerWidget.module.css';

export interface ProBannerWidgetProps {
  onOpenStepByStep?: () => void;
}

export const ProBannerWidget: React.FC<ProBannerWidgetProps> = ({ onOpenStepByStep }) => {
  const { t } = usePreferences();

  return (
    <aside className={styles.proWidget} data-testid="pro-banner-widget">
      <div className={styles.widgetHeader}>
        <h3 className={styles.widgetTitle}>{t('pro_widget_title')}</h3>
      </div>
      <div className={styles.widgetBody}>
        <div className={styles.stepPreviewBox}>
          <span className={styles.stepTag}>STEP 1</span>
          <p className={styles.stepDesc}>
            {t('pro_widget_desc')}
          </p>
          <div className={styles.stepFormula}>
            <MathLatex latex="\Delta = b^2 - 4ac" displayMode />
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
