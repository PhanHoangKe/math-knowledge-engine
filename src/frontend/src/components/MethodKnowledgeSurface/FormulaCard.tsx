import React, { useEffect, useState } from 'react';
import type { FormulaKnowledge } from '../../api/contract';
import { getFormulaKnowledge } from '../../api/client';
import { MathLatex } from '../MathLatex/MathLatex';
import { usePreferences } from '../../state/preferences';
import styles from './MethodKnowledgeSurface.module.css';

export interface FormulaCardProps {
  formulaId: string;
  initialData?: FormulaKnowledge;
}

export const FormulaCard: React.FC<FormulaCardProps> = ({ formulaId, initialData }) => {
  const { language, t } = usePreferences();
  const [data, setData] = useState<FormulaKnowledge | undefined>(initialData);
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

    getFormulaKnowledge(formulaId, abortController.signal)
      .then((formula) => {
        setData(formula);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err.message ?? 'Failed to load formula');
        setLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [formulaId, initialData]);

  if (loading) {
    return (
      <div className={styles.formulaCardLoading} data-testid={`formula-loading-${formulaId}`}>
        <span className={styles.loadingSpinner} />
        <span>{t('lbl_knowledge_loading')} ({formulaId})</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={styles.formulaCardError} data-testid={`formula-error-${formulaId}`}>
        <code className={styles.entityId}>{formulaId}</code>
        <span className={styles.errorText}>{t('lbl_knowledge_error')}</span>
      </div>
    );
  }

  const localizedTitle = data.title[language] ?? data.title.vi;
  const localizedDomain = data.domain_conditions[language] ?? data.domain_conditions.vi;

  return (
    <div className={styles.formulaCard} data-testid={`formula-card-${formulaId}`}>
      <div className={styles.cardHeader}>
        <h5 className={styles.cardTitle}>{localizedTitle}</h5>
        <code className={styles.entityId}>{data.formula_id}</code>
      </div>

      <div className={styles.latexContainer} data-testid={`formula-latex-${formulaId}`}>
        <MathLatex latex={data.latex_template} displayMode={true} />
      </div>

      <div className={styles.cardSection}>
        <span className={styles.sectionLabel}>{t('lbl_domain_conditions')}:</span>
        <p className={styles.domainConditions}>{localizedDomain}</p>
      </div>

      {data.variables_description && Object.keys(data.variables_description).length > 0 && (
        <div className={styles.cardSection}>
          <span className={styles.sectionLabel}>{t('lbl_variables_description')}:</span>
          <ul className={styles.variablesList}>
            {Object.entries(data.variables_description).map(([varKey, varText]) => (
              <li key={varKey}>
                <code>{varKey}</code>: {varText[language] ?? varText.vi}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
