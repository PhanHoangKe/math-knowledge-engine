import React, { useEffect, useState, useRef } from 'react';
import type { TheoremKnowledge } from '../../api/contract';
import {
  getTheoremKnowledge,
  KnowledgeApiError,
  NetworkError,
  ProtocolError,
} from '../../api/client';
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
  const [errorKind, setErrorKind] = useState<'not_found' | 'network' | 'protocol' | 'generic' | null>(null);
  const activeRequestIdRef = useRef<number>(0);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      setLoading(false);
      setErrorKind(null);
      return;
    }

    const requestId = ++activeRequestIdRef.current;
    const abortController = new AbortController();
    setLoading(true);
    setErrorKind(null);

    getTheoremKnowledge(theoremId, abortController.signal)
      .then((theorem) => {
        if (activeRequestIdRef.current !== requestId) return;
        setData(theorem);
        setLoading(false);
      })
      .catch((err) => {
        if (activeRequestIdRef.current !== requestId) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        let kind: 'not_found' | 'network' | 'protocol' | 'generic' = 'generic';
        if (err instanceof KnowledgeApiError) kind = 'not_found';
        else if (err instanceof NetworkError) kind = 'network';
        else if (err instanceof ProtocolError) kind = 'protocol';
        setErrorKind(kind);
        setLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [theoremId, initialData]);

  if (loading) {
    return (
      <div
        className={styles.theoremCardLoading}
        role="status"
        aria-live="polite"
        data-testid={`theorem-loading-${theoremId}`}
      >
        <span className={styles.loadingSpinner} />
        <span>{t('lbl_knowledge_loading')} ({theoremId})</span>
      </div>
    );
  }

  if (errorKind || !data) {
    return (
      <div
        className={styles.theoremCardError}
        role="alert"
        data-testid={`theorem-error-${theoremId}`}
      >
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
