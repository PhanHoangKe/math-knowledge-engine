import React, { useEffect, useState } from 'react';
import type { TheoremKnowledge } from '../../api/contract';
import { getTheoremKnowledge } from '../../api/client';
import { MathLatex } from '../MathLatex/MathLatex';
import { usePreferences } from '../../state/preferences';
import styles from './MethodKnowledgeSurface.module.css';

export interface TheoremCardProps {
  theoremId: string;
  initialData?: TheoremKnowledge;
}

export const TheoremCard: React.FC<TheoremCardProps> = ({ theoremId, initialData }) => {
  const { language, t } = usePreferences();
  const [data, setData] = useState<TheoremKnowledge | undefined>(initialData);
  const [loading, setLoading] = useState<boolean>(!initialData);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      setLoading(false);
      return;
    }

    const abortController = new AbortController();
    setLoading(true);
    setError(null);

    getTheoremKnowledge(theoremId, abortController.signal)
      .then((theorem) => {
        setData(theorem);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err.message ?? 'Failed to load theorem');
        setLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [theoremId, initialData]);

  if (loading) {
    return (
      <div className={styles.theoremCardLoading} data-testid={`theorem-loading-${theoremId}`}>
        <span className={styles.loadingSpinner} />
        <span>{t('lbl_knowledge_loading')} ({theoremId})</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={styles.theoremCardError} data-testid={`theorem-error-${theoremId}`}>
        <code className={styles.entityId}>{theoremId}</code>
        <span className={styles.errorText}>{t('lbl_knowledge_error')}</span>
      </div>
    );
  }

  const localizedTitle = data.title[language] ?? data.title.vi;
  const localizedStatement = data.statement[language] ?? data.statement.vi;

  return (
    <div className={styles.theoremCard} data-testid={`theorem-card-${theoremId}`}>
      <div className={styles.cardHeader}>
        <h5 className={styles.cardTitle}>{localizedTitle}</h5>
        <code className={styles.entityId}>{data.theorem_id}</code>
      </div>

      <div className={styles.cardSection}>
        <span className={styles.sectionLabel}>{t('lbl_theorem_statement')}:</span>
        <p className={styles.theoremStatement}>{localizedStatement}</p>
      </div>

      {data.formal_statement_latex && (
        <div className={styles.cardSection}>
          <span className={styles.sectionLabel}>{t('lbl_formal_statement')}:</span>
          <div className={styles.latexContainer} data-testid={`theorem-latex-${theoremId}`}>
            <MathLatex latex={data.formal_statement_latex} displayMode={true} />
          </div>
        </div>
      )}

      {data.hypotheses && data.hypotheses.length > 0 && (
        <div className={styles.cardSection}>
          <span className={styles.sectionLabel}>{t('lbl_hypotheses')}:</span>
          <ul className={styles.hypothesesList}>
            {data.hypotheses.map((h, i) => (
              <li key={i}>{h[language] ?? h.vi}</li>
            ))}
          </ul>
        </div>
      )}

      {data.conclusions && data.conclusions.length > 0 && (
        <div className={styles.cardSection}>
          <span className={styles.sectionLabel}>{t('lbl_conclusions')}:</span>
          <ul className={styles.conclusionsList}>
            {data.conclusions.map((c, i) => (
              <li key={i}>{c[language] ?? c.vi}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
