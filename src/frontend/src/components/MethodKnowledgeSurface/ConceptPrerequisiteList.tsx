import React, { useEffect, useState } from 'react';
import type { ConceptKnowledge } from '../../api/contract';
import { getConceptKnowledge } from '../../api/client';
import { usePreferences } from '../../state/preferences';
import styles from './MethodKnowledgeSurface.module.css';

export interface ConceptPrerequisiteListProps {
  conceptIds: string[];
}

interface ConceptState {
  loading: boolean;
  data?: ConceptKnowledge;
  error?: string;
}

export const ConceptPrerequisiteList: React.FC<ConceptPrerequisiteListProps> = ({ conceptIds }) => {
  const { language, t } = usePreferences();
  const [concepts, setConcepts] = useState<Record<string, ConceptState>>({});

  useEffect(() => {
    if (!conceptIds || conceptIds.length === 0) {
      setConcepts({});
      return;
    }

    const abortController = new AbortController();

    // Initialize loading states
    const initial: Record<string, ConceptState> = {};
    conceptIds.forEach((id) => {
      initial[id] = { loading: true };
    });
    setConcepts(initial);

    conceptIds.forEach((id) => {
      getConceptKnowledge(id, abortController.signal)
        .then((data) => {
          setConcepts((prev) => ({
            ...prev,
            [id]: { loading: false, data },
          }));
        })
        .catch((err) => {
          if (err instanceof DOMException && err.name === 'AbortError') return;
          setConcepts((prev) => ({
            ...prev,
            [id]: { loading: false, error: err.message ?? 'Error' },
          }));
        });
    });

    return () => {
      abortController.abort();
    };
  }, [conceptIds]);

  if (!conceptIds || conceptIds.length === 0) {
    return (
      <div className={styles.emptyNotice} data-testid="concept-list-empty">
        {t('lbl_knowledge_empty_prereqs')}
      </div>
    );
  }

  return (
    <div className={styles.conceptList} data-testid="concept-prerequisite-list">
      {conceptIds.map((id) => {
        const state = concepts[id];
        if (!state || state.loading) {
          return (
            <div key={id} className={styles.conceptCardLoading} data-testid={`concept-loading-${id}`}>
              <span className={styles.loadingSpinner} />
              <span>{t('lbl_knowledge_loading')} ({id})</span>
            </div>
          );
        }

        if (state.error || !state.data) {
          return (
            <div key={id} className={styles.conceptCardError} data-testid={`concept-error-${id}`}>
              <code className={styles.entityId}>{id}</code>
              <span className={styles.errorText}>{t('lbl_knowledge_error')}</span>
            </div>
          );
        }

        const concept = state.data;
        const localizedTitle = concept.title[language] ?? concept.title.vi;
        const localizedDefinition = concept.definition[language] ?? concept.definition.vi;

        return (
          <div key={id} className={styles.conceptCard} data-testid={`concept-card-${id}`}>
            <div className={styles.conceptHeader}>
              <h5 className={styles.conceptTitle}>{localizedTitle}</h5>
              <code className={styles.entityId}>{concept.concept_id}</code>
            </div>
            <p className={styles.conceptDefinition}>{localizedDefinition}</p>
          </div>
        );
      })}
    </div>
  );
};
