import React from 'react';
import { usePreferences } from '../../state/preferences';
import { SettingsPopover } from '../SettingsPopover/SettingsPopover';
import styles from './HeaderBar.module.css';

export const HeaderBar: React.FC = () => {
  const { t } = usePreferences();

  return (
    <header className={styles.appHeader}>
      <div className={styles.headerContainer}>
        {/* Brand & Identity */}
        <div className={styles.brand} role="banner">
          <div className={styles.brandIconWrapper} aria-hidden="true">
            <svg
              className={styles.brandIcon}
              viewBox="0 0 32 32"
              width="28"
              height="28"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="16" cy="16" r="13" />
              <path d="M10 16h12M16 10v12" />
              <path d="M12 12l8 8M20 12l-8 8" strokeWidth="1.4" opacity="0.6" />
            </svg>
          </div>
          <div className={styles.brandText}>
            <span className={styles.brandTitle}>
              MKE<span className={styles.brandTitleAccent}>{t('brand_alpha')}</span>
            </span>
            <span className={styles.brandSub}>{t('app_subtitle')}</span>
          </div>
          <span className={styles.prototypeBadge} title={t('product_badge_title')}>
            {t('product_badge')}
          </span>
        </div>

        {/* Navigation & Controls */}
        <div className={styles.headerRightGroup}>
          <nav className={styles.navLinks} aria-label={t('nav_main_aria')}>
            <button type="button" className={`${styles.navBtn} ${styles.navBtnActive}`}>
              {t('nav_home')}
            </button>
            <button type="button" className={styles.navBtn}>
              {t('nav_workspace')}
            </button>
            <button type="button" className={styles.navBtn}>
              {t('nav_syntax')}
            </button>
          </nav>

          <button type="button" className={styles.signInBtn} title={t('header_signin')}>
            {t('header_signin')}
          </button>

          <div className={styles.divider} aria-hidden="true" />

          <SettingsPopover />
        </div>
      </div>
    </header>
  );
};
