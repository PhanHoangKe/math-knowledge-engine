import React from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './AppFooter.module.css';

export const AppFooter: React.FC = () => {
  const { t } = usePreferences();

  return (
    <footer className={styles.footerContainer} role="contentinfo">
      {/* Top Tier Nav */}
      <div className={styles.topNavRow}>
        <a href="#pro" className={styles.footerLink}>{t('footer_pro')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#mobile" className={styles.footerLink}>{t('footer_mobile')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#products" className={styles.footerLink}>{t('footer_products')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#business" className={styles.footerLink}>{t('footer_business')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#api" className={styles.footerLink}>{t('footer_api')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#llm" className={styles.footerLink}>{t('footer_llm')}</a>
      </div>

      {/* Middle Tier: Resources & Social Icons */}
      <div className={styles.middleRow}>
        <div className={styles.resourcesLinks}>
          <a href="#resources" className={styles.footerLink}>{t('footer_resources')}</a>
          <span className={styles.linkDivider}>|</span>
          <a href="#about" className={styles.footerLink}>{t('footer_about')}</a>
          <span className={styles.linkDivider}>|</span>
          <a href="#contact" className={styles.footerLink}>{t('footer_contact')}</a>
          <span className={styles.linkDivider}>|</span>
          <span className={styles.connectLabel}>{t('footer_connect')}</span>
        </div>

        <div className={styles.socialIcons}>
          {/* Facebook */}
          <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" className={styles.socialBtn} aria-label="Facebook">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95C18.05 21.45 22 17.19 22 12z" />
            </svg>
          </a>
          {/* X / Twitter */}
          <a href="https://x.com" target="_blank" rel="noopener noreferrer" className={styles.socialBtn} aria-label="X">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </a>
          {/* Instagram */}
          <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" className={styles.socialBtn} aria-label="Instagram">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
            </svg>
          </a>
          {/* LinkedIn */}
          <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className={styles.socialBtn} aria-label="LinkedIn">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.25a1.62 1.62 0 1 0 0 3.24 1.62 1.62 0 0 0 0-3.24z" />
            </svg>
          </a>
        </div>
      </div>

      {/* Copyright & Legal Row */}
      <div className={styles.copyrightRow}>
        <span>© 2026 Math Knowledge Engine (MKE)</span>
        <span className={styles.linkDivider}>|</span>
        <a href="#terms" className={styles.footerLink}>{t('footer_terms')}</a>
        <span className={styles.linkDivider}>|</span>
        <a href="#privacy" className={styles.footerLink}>{t('footer_privacy')}</a>
      </div>

      {/* Ecosystem Sub-links */}
      <div className={styles.ecosystemRow}>
        <div className={styles.ecosystemBrand}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="#cb1000" className={styles.spikeyIcon}>
            <polygon points="12,2 15,9 22,9 17,14 19,21 12,17 5,21 7,14 2,9 9,9" />
          </svg>
          <strong className={styles.ecosystemTitle}>MKE</strong>
        </div>
        <div className={styles.ecosystemLinks}>
          <a href="#engine" className={styles.subLink}>mke.org</a>
          <span className={styles.subDivider}>|</span>
          <a href="#cas" className={styles.subLink}>CAS Tất Định</a>
          <span className={styles.subDivider}>|</span>
          <a href="#proofs" className={styles.subLink}>Chứng Minh Hình Thức</a>
          <span className={styles.subDivider}>|</span>
          <a href="#examples" className={styles.subLink}>Thư Viện Bài Toán Mẫu</a>
          <span className={styles.subDivider}>|</span>
          <a href="#edu" className={styles.subLink}>MKE Cho Giáo Dục</a>
          <span className={styles.subDivider}>|</span>
          <a href="#mathworld" className={styles.subLink}>MathWorld</a>
        </div>
      </div>
    </footer>
  );
};
