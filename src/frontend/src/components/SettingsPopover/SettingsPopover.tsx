import React, { useState, useRef, useEffect, useCallback } from 'react';
import { usePreferences, type Theme } from '../../state/preferences';
import type { Language } from '../../i18n';
import styles from './SettingsPopover.module.css';

export const SettingsPopover: React.FC = () => {
  const { language, theme, setLanguage, setTheme, t } = usePreferences();
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const closePopover = useCallback(() => {
    setIsOpen(false);
    triggerRef.current?.focus();
  }, []);

  // Keyboard navigation: Escape key closes popover
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closePopover();
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, closePopover]);

  return (
    <div className={styles.container}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.triggerButton}
        onClick={toggleOpen}
        aria-label={t('settings_trigger_aria')}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        title={t('settings_title')}
      >
        <svg
          className={styles.triggerIcon}
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      </button>

      {isOpen && (
        <div
          ref={popoverRef}
          className={styles.popover}
          role="dialog"
          aria-label={t('settings_title')}
        >
          <div className={styles.popoverHeader}>
            <span className={styles.popoverTitle}>{t('settings_title')}</span>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>{t('theme_title')}</div>
            <div className={styles.buttonGroup}>
              {(['auto', 'light', 'dark'] as const).map((mode) => {
                const isActive = theme === mode;
                const label =
                  mode === 'auto'
                    ? t('theme_auto')
                    : mode === 'light'
                    ? t('theme_light')
                    : t('theme_dark');

                return (
                  <button
                    key={mode}
                    type="button"
                    className={`${styles.optionBtn} ${isActive ? styles.optionActive : ''}`}
                    onClick={() => setTheme(mode as Theme)}
                    aria-pressed={isActive}
                  >
                    <span>{label}</span>
                    {isActive && <span className={styles.checkIcon}>✓</span>}
                  </button>
                );
              })}
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>{t('lang_title')}</div>
            <div className={styles.buttonGroup}>
              {(['vi', 'en'] as const).map((langCode) => {
                const isActive = language === langCode;
                const label = langCode === 'vi' ? t('lang_vi') : t('lang_en');

                return (
                  <button
                    key={langCode}
                    type="button"
                    className={`${styles.optionBtn} ${isActive ? styles.optionActive : ''}`}
                    onClick={() => setLanguage(langCode as Language)}
                    aria-pressed={isActive}
                  >
                    <span>{label}</span>
                    {isActive && <span className={styles.checkIcon}>✓</span>}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
