import React, { useState, useCallback } from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './EquationInputShell.module.css';

export interface EquationInputShellProps {
  initialQuery?: string;
  onQueryChange?: (query: string) => void;
}

export const EquationInputShell: React.FC<EquationInputShellProps> = ({
  initialQuery = '',
  onQueryChange,
}) => {
  const { t } = usePreferences();
  const [query, setQuery] = useState(initialQuery);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onQueryChange?.(val);
  };

  const handleClear = useCallback(() => {
    setQuery('');
    onQueryChange?.('');
  }, [onQueryChange]);

  const insertQuickKey = useCallback(
    (snippet: string) => {
      setQuery((prev) => {
        const next = prev + snippet;
        onQueryChange?.(next);
        return next;
      });
    },
    [onQueryChange]
  );

  return (
    <section className={styles.wrapper} aria-label={t('input_aria')}>
      {/* Super & Hero Motto */}
      <div className={styles.heroSection}>
        <div className={styles.heroSuper}>{t('hero_super')}</div>
        <h1 className={styles.heroTitle}>{t('hero_title')}</h1>
        <p className={styles.heroTagline}>{t('hero_tagline')}</p>
      </div>

      {/* Capsule Equation Input Container */}
      <div className={styles.capsuleBox}>
        <label htmlFor="equation-input" className="sr-only">
          {t('input_label')}
        </label>
        <input
          id="equation-input"
          type="text"
          className={styles.inputField}
          value={query}
          onChange={handleInputChange}
          placeholder={t('input_placeholder')}
          autoComplete="off"
          spellCheck="false"
        />

        {query.length > 0 && (
          <button
            type="button"
            className={styles.clearBtn}
            onClick={handleClear}
            aria-label={t('clear_btn_aria')}
            title={t('clear_btn_aria')}
          >
            ×
          </button>
        )}

        {/* Compute Button — Intentionally non-functional in S2-03 shell */}
        <button
          type="button"
          className={styles.computeBtn}
          aria-label={t('compute_btn_aria')}
          title={t('compute_btn_aria')}
          disabled
          aria-disabled="true"
        >
          {t('compute_btn_text')}
        </button>
      </div>

      {/* Sub-toolbar: Quick Math Keys & Status */}
      <div className={styles.subToolbar}>
        <div className={styles.quickKeysGroup} aria-label={t('quick_keys_label')}>
          <span className={styles.quickKeysLabel}>{t('quick_keys_label')}</span>
          {['*', 'x', '^2', '^0', '/', '=', '(', ')'].map((keySymbol) => (
            <button
              key={keySymbol}
              type="button"
              className={styles.quickKeyBtn}
              onClick={() => insertQuickKey(keySymbol)}
            >
              {keySymbol}
            </button>
          ))}
        </div>

        <div className={styles.statusNote}>
          <span className={styles.statusDot} aria-hidden="true" />
          <span>{t('shell_status_idle')}</span>
        </div>
      </div>
    </section>
  );
};
