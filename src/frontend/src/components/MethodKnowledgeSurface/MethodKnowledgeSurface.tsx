import React, { useEffect, useState, useRef } from 'react';
import type { MethodKnowledge } from '../../api/contract';
import {
  getMethodKnowledge,
  KnowledgeApiError,
  NetworkError,
  ProtocolError,
} from '../../api/client';
import { usePreferences } from '../../state/preferences';
import { ConceptPrerequisiteList } from './ConceptPrerequisiteList';
import { FormulaCard } from './FormulaCard';
import { TheoremCard } from './TheoremCard';
import styles from './MethodKnowledgeSurface.module.css';

export interface MethodKnowledgeSurfaceProps {
  methodId: string;
  isOpen: boolean;
  onClose?: () => void;
  initialData?: MethodKnowledge;
}

export type KnowledgeErrorKind = 'not_found' | 'network' | 'protocol' | 'generic';

export const MethodKnowledgeSurface: React.FC<MethodKnowledgeSurfaceProps> = ({
  methodId,
  isOpen,
  onClose,
  initialData,
}) => {
  const { language, t } = usePreferences();
  const [data, setData] = useState<MethodKnowledge | undefined>(initialData);
  const [loading, setLoading] = useState<boolean>(!initialData && isOpen);
  const [errorKind, setErrorKind] = useState<KnowledgeErrorKind | null>(null);
  const activeRequestIdRef = useRef<number>(0);

  const loadKnowledge = (id: string) => {
    const requestId = ++activeRequestIdRef.current;
    setLoading(true);
    setErrorKind(null);

    const abortController = new AbortController();

    getMethodKnowledge(id, abortController.signal)
      .then((knowledge) => {
        if (activeRequestIdRef.current !== requestId) return;
        setData(knowledge);
        setLoading(false);
      })
      .catch((err) => {
        if (activeRequestIdRef.current !== requestId) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (err instanceof KnowledgeApiError) {
          setErrorKind('not_found');
        } else if (err instanceof NetworkError) {
          setErrorKind('network');
        } else if (err instanceof ProtocolError) {
          setErrorKind('protocol');
        } else {
          setErrorKind('generic');
        }
        setLoading(false);
      });

    return abortController;
  };

  useEffect(() => {
    // Invalidate any existing in-flight request on every state transition
    const requestId = ++activeRequestIdRef.current;

    if (!isOpen) {
      setLoading(false);
      return;
    }

    if (initialData) {
      setData(initialData);
      setLoading(false);
      setErrorKind(null);
      return;
    }

    setLoading(true);
    setErrorKind(null);
    const abortController = new AbortController();

    getMethodKnowledge(methodId, abortController.signal)
      .then((knowledge) => {
        if (activeRequestIdRef.current !== requestId) return;
        setData(knowledge);
        setLoading(false);
      })
      .catch((err) => {
        if (activeRequestIdRef.current !== requestId) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (err instanceof KnowledgeApiError) {
          setErrorKind('not_found');
        } else if (err instanceof NetworkError) {
          setErrorKind('network');
        } else if (err instanceof ProtocolError) {
          setErrorKind('protocol');
        } else {
          setErrorKind('generic');
        }
        setLoading(false);
      });

    return () => {
      abortController.abort();
    };
  }, [methodId, isOpen, initialData]);

  if (!isOpen) {
    return null;
  }

  const getErrorMessage = (): string => {
    switch (errorKind) {
      case 'not_found':
        return t('err_knowledge_not_found');
      case 'network':
        return t('err_network_msg');
      case 'protocol':
        return t('err_protocol_msg');
      case 'generic':
      default:
        return t('err_knowledge_generic');
    }
  };

  return (
    <div
      className={styles.surfaceContainer}
      data-testid={`method-knowledge-surface-${methodId}`}
      id={`knowledge-surface-${methodId}`}
    >
      <div className={styles.surfaceHeader}>
        <div className={styles.surfaceTitleGroup}>
          <h4 className={styles.surfaceHeading}>
            {t('panel_method_knowledge')}
          </h4>
          <span className={styles.methodBadge}>{methodId}</span>
        </div>
        {onClose && (
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label={t('btn_hide_knowledge')}
          >
            ✕ {t('btn_hide_knowledge')}
          </button>
        )}
      </div>

      {loading && (
        <div
          className={styles.loadingContainer}
          role="status"
          aria-live="polite"
          data-testid={`knowledge-loading-${methodId}`}
        >
          <span className={styles.loadingSpinner} />
          <span>{t('lbl_knowledge_loading')} ({methodId})</span>
        </div>
      )}

      {errorKind && !loading && (
        <div
          className={styles.errorContainer}
          role="alert"
          data-testid={`knowledge-error-${methodId}`}
        >
          <p className={styles.errorText}>
            {getErrorMessage()}
          </p>
          <button
            type="button"
            className={styles.retryBtn}
            onClick={() => loadKnowledge(methodId)}
            data-testid={`knowledge-retry-${methodId}`}
          >
            {t('btn_retry')}
          </button>
        </div>
      )}

      {!loading && !errorKind && data && (
        <div className={styles.surfaceBody}>
          {/* Method Title & Summary */}
          <div className={styles.summaryBlock}>
            <h4 className={styles.methodFullTitle}>
              {data.title[language] ?? data.title.vi}
            </h4>
            <p className={styles.summaryText}>
              {data.summary[language] ?? data.summary.vi}
            </p>
          </div>

          {/* Learning Objective & Formal Description */}
          <div className={styles.gridRow}>
            <div className={styles.infoCard}>
              <span className={styles.sectionLabel}>{t('lbl_learning_objective')}:</span>
              <p className={styles.cardText}>
                {data.learning_objective[language] ?? data.learning_objective.vi}
              </p>
            </div>
            <div className={styles.infoCard}>
              <span className={styles.sectionLabel}>{t('lbl_formal_description')}:</span>
              <p className={styles.cardText}>
                {data.formal_description[language] ?? data.formal_description.vi}
              </p>
            </div>
          </div>

          {/* Guidance Section: Applicability & Non-applicability */}
          <div className={styles.gridRow}>
            {data.applicability_guidance && data.applicability_guidance.length > 0 && (
              <div className={styles.guidanceCard}>
                <span className={styles.sectionLabel}>{t('lbl_applicability_guidance')}:</span>
                <ul className={styles.guidanceList}>
                  {data.applicability_guidance.map((g, idx) => (
                    <li key={idx}>{g[language] ?? g.vi}</li>
                  ))}
                </ul>
              </div>
            )}

            {data.non_applicability_guidance && data.non_applicability_guidance.length > 0 && (
              <div className={styles.guidanceCard}>
                <span className={styles.sectionLabel}>{t('lbl_non_applicability_guidance')}:</span>
                <ul className={styles.guidanceList}>
                  {data.non_applicability_guidance.map((g, idx) => (
                    <li key={idx}>{g[language] ?? g.vi}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Common Mistakes & Diagnostic Tips */}
          <div className={styles.gridRow}>
            {data.common_mistakes && data.common_mistakes.length > 0 && (
              <div className={styles.warningCard}>
                <span className={styles.sectionLabel}>{t('lbl_common_mistakes')}:</span>
                <ul className={styles.guidanceList}>
                  {data.common_mistakes.map((m, idx) => (
                    <li key={idx}>{m[language] ?? m.vi}</li>
                  ))}
                </ul>
              </div>
            )}

            {data.diagnostic_tips && data.diagnostic_tips.length > 0 && (
              <div className={styles.tipCard}>
                <span className={styles.sectionLabel}>{t('lbl_diagnostic_tips')}:</span>
                <ul className={styles.guidanceList}>
                  {data.diagnostic_tips.map((tip, idx) => (
                    <li key={idx}>{tip[language] ?? tip.vi}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Prerequisite Concepts */}
          <div className={styles.knowledgeSection}>
            <h5 className={styles.sectionHeading}>{t('lbl_prerequisite_concepts')}</h5>
            <ConceptPrerequisiteList
              conceptIds={data.prerequisite_concept_ids ?? []}
            />
          </div>

          {/* Formulas */}
          {data.formula_refs && data.formula_refs.length > 0 && (
            <div className={styles.knowledgeSection}>
              <h5 className={styles.sectionHeading}>{t('lbl_formula_cards')}</h5>
              <div className={styles.cardsGrid} data-testid="method-formula-grid">
                {data.formula_refs.map((fId) => (
                  <FormulaCard key={fId} formulaId={fId} />
                ))}
              </div>
            </div>
          )}

          {/* Theorems */}
          {data.theorem_refs && data.theorem_refs.length > 0 && (
            <div className={styles.knowledgeSection}>
              <h5 className={styles.sectionHeading}>{t('lbl_theorem_cards')}</h5>
              <div className={styles.cardsGrid} data-testid="method-theorem-grid">
                {data.theorem_refs.map((tId) => (
                  <TheoremCard key={tId} theoremId={tId} />
                ))}
              </div>
            </div>
          )}

          {/* Curriculum Standards */}
          {data.curriculum_refs && data.curriculum_refs.length > 0 && (
            <div className={styles.knowledgeSection}>
              <h5 className={styles.sectionHeading}>{t('lbl_curriculum_refs')}</h5>
              <div className={styles.curriculumGrid}>
                {data.curriculum_refs.map((cRef, idx) => (
                  <div key={idx} className={styles.curriculumCard}>
                    <div className={styles.curriculumHeader}>
                      <span className={styles.frameworkBadge}>{cRef.framework}</span>
                      <span className={styles.gradeBadge}>{cRef.grade_band}</span>
                      <span className={styles.statusBadge}>
                        {t(
                          cRef.status === 'VERIFIED_MAPPING'
                            ? 'enum_curric_VERIFIED_MAPPING'
                            : 'enum_curric_PROVISIONAL_MAPPING'
                        )}
                      </span>
                    </div>
                    <div className={styles.curriculumDetails}>
                      <p><strong>{t('lbl_curriculum_doc')}:</strong> {cRef.source_document}</p>
                      <p><strong>{t('lbl_curriculum_locator')}:</strong> {cRef.source_locator}</p>
                      <p><strong>{t('lbl_curriculum_topic')}:</strong> <code>{cRef.topic}</code></p>
                      {cRef.competency_ref && (
                        <p><strong>Standard:</strong> <code>{cRef.competency_ref}</code></p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Provenance */}
          {data.provenance_refs && data.provenance_refs.length > 0 && (
            <div className={styles.provenanceSection}>
              <span className={styles.sectionLabel}>{t('lbl_provenance_refs')}:</span>
              <div className={styles.provenanceTags}>
                {data.provenance_refs.map((pRef, idx) => (
                  <code key={idx} className={styles.provenanceTag}>{pRef}</code>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
