import React, { useCallback } from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './EquationInputShell.module.css';

export interface EquationInputShellProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onClear: () => void;
  isLoading?: boolean;
  statusText?: string;
}

export const EquationInputShell: React.FC<EquationInputShellProps> = ({
  query,
  onQueryChange,
  onSubmit,
  onClear,
  isLoading = false,
  statusText,
}) => {
  const { t } = usePreferences();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onQueryChange(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  const insertQuickKey = useCallback(
    (snippet: string) => {
      onQueryChange(query + snippet);
    },
    [query, onQueryChange]
  );

  const isSubmitDisabled = !query.trim() || isLoading;

  return (
    <section className={styles.wrapper} aria-label={t('input_aria')}>
      {/* Super & Hero Motto */}
      <div className={styles.heroSection}>
        <div className={styles.heroSuper}>{t('hero_super')}</div>
        <h1 className={styles.heroTitle}>{t('hero_title')}</h1>
        <p className={styles.heroTagline}>{t('hero_tagline')}</p>
      </div>

      {/* Capsule Equation Input Container */}
      <div className={`${styles.capsuleBox} ${isLoading ? styles.capsuleLoading : ''}`}>
        <label htmlFor="equation-input" className="sr-only">
          {t('input_label')}
        </label>
        <input
          id="equation-input"
          type="text"
          className={styles.inputField}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={t('input_placeholder')}
          autoComplete="off"
          spellCheck="false"
          disabled={isLoading}
          data-testid="equation-input"
        />

        {query.length > 0 && !isLoading && (
          <button
            type="button"
            className={styles.clearBtn}
            onClick={onClear}
            aria-label={t('clear_btn_aria')}
            title={t('clear_btn_aria')}
            data-testid="clear-btn"
          >
            ×
          </button>
        )}

        {/* Compute Button */}
        <button
          type="button"
          className={styles.computeBtn}
          aria-label={t('compute_btn_aria')}
          title={t('compute_btn_aria')}
          onClick={onSubmit}
          disabled={isSubmitDisabled}
          aria-disabled={isSubmitDisabled}
          data-testid="compute-btn"
        >
          {isLoading ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            t('compute_btn_text')
          )}
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
              disabled={isLoading}
            >
              {keySymbol}
            </button>
          ))}
        </div>

        <div className={styles.statusNote}>
          <span
            className={`${styles.statusDot} ${isLoading ? styles.statusDotActive : ''}`}
            aria-hidden="true"
          />
          <span data-testid="shell-status-text">
            {statusText || (isLoading ? t('shell_status_loading') : t('shell_status_idle'))}
          </span>
        </div>
      </div>
    </section>
  );
};
