import React from 'react';
import { usePreferences } from '../../state/preferences';
import { HeaderBar } from '../HeaderBar/HeaderBar';
import { EquationInputShell } from '../EquationInputShell/EquationInputShell';
import { WorkspaceEmptyState } from '../WorkspaceEmptyState/WorkspaceEmptyState';
import styles from './AppShell.module.css';

export const AppShell: React.FC = () => {
  const { t } = usePreferences();

  return (
    <div className={styles.appRoot}>
      {/* Global Header */}
      <HeaderBar />

      {/* Main Workspace Surface */}
      <main className={styles.mainContent}>
        <EquationInputShell />
        <WorkspaceEmptyState />

        {/* MKE Architecture Flow Banner */}
        <section className={styles.flowBanner} aria-label={t('flow_tagline')}>
          <div className={styles.flowTagline}>{t('flow_tagline')}</div>
          <div className={styles.flowPipeline}>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-math)' }}>
                1
              </span>
              <span className={styles.flowLabel}>{t('flow_ast')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              +
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-science)' }}>
                2
              </span>
              <span className={styles.flowLabel}>{t('flow_rational')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              +
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-society)' }}>
                3
              </span>
              <span className={styles.flowLabel}>{t('flow_symbolic')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              ➔
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-life)' }}>
                4
              </span>
              <span className={styles.flowLabel}>{t('flow_cert')}</span>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={styles.appFooter}>
        <div className={styles.footerContainer}>
          <p className={styles.copyright}>{t('footer_copyright')}</p>
        </div>
      </footer>
    </div>
  );
};
