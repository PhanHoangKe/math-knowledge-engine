import React from 'react';
import { usePreferences } from '../../state/preferences';
import { useAlgebraWorkspace } from '../../state/useAlgebraWorkspace';
import { HeaderBar } from '../HeaderBar/HeaderBar';
import { EquationInputShell } from '../EquationInputShell/EquationInputShell';
import { WorkspaceEmptyState } from '../WorkspaceEmptyState/WorkspaceEmptyState';
import { CanonicalProblemPanel } from '../CanonicalProblemPanel/CanonicalProblemPanel';
import { MethodCatalogPanel } from '../MethodCatalogPanel/MethodCatalogPanel';
import { SolutionSummaryPanel } from '../SolutionSummaryPanel/SolutionSummaryPanel';
import { TracePanel } from '../TracePanel/TracePanel';
import { VerificationPanel } from '../VerificationPanel/VerificationPanel';
import { DegenerateSolutionPanel } from '../DegenerateSolutionPanel/DegenerateSolutionPanel';
import { MethodNotExecutablePanel } from '../MethodNotExecutablePanel/MethodNotExecutablePanel';
import { CoefficientEditorPanel } from '../CoefficientEditorPanel/CoefficientEditorPanel';
import { RevisionHistoryPanel } from '../RevisionHistoryPanel/RevisionHistoryPanel';
import { ApplicationErrorPanel } from '../ApplicationErrorPanel/ApplicationErrorPanel';
import { TransportErrorPanel } from '../TransportErrorPanel/TransportErrorPanel';
import { NetworkErrorPanel } from '../NetworkErrorPanel/NetworkErrorPanel';
import type {
  SolvedResponse,
  AnalyzedNoExecutionResponse,
  ApplicationErrorResponse,
  TransportErrorResponse,
} from '../../api/contract';
import styles from './AppShell.module.css';

export const AppShell: React.FC = () => {
  const { t } = usePreferences();
  const {
    query,
    setQuery,
    status,
    result,
    httpStatus,
    sourceMode,
    coeffDraft,
    coeffValidationErrors,
    reactiveStatus,
    revisionHistory,
    updateCoefficientField,
    resetCoefficientsToBackend,
    submitRawSolve,
    switchMethod,
    retryLastRequest,
    restoreRevision,
    clearWorkspace,
  } = useAlgebraWorkspace();

  const getStatusText = (): string => {
    switch (status) {
      case 'loading':
        return t('shell_status_loading');
      case 'application-response':
        if (result && result.kind === 'application') {
          if (result.response.response_status === 'SOLVED') {
            return t('shell_status_solved');
          }
          if (result.response.response_status === 'ANALYZED_NO_EXECUTION') {
            return t('shell_status_analyzed');
          }
          if (result.response.response_status === 'ERROR') {
            return t('shell_status_error');
          }
        }
        return t('shell_status_idle');
      case 'transport-error':
      case 'network-error':
      case 'protocol-error':
        return t('shell_status_error');
      default:
        return t('shell_status_idle');
    }
  };

  return (
    <div className={styles.appRoot}>
      {/* Global Header */}
      <HeaderBar />

      {/* Main Workspace Surface */}
      <main className={styles.mainContent}>
        <EquationInputShell
          query={query}
          onQueryChange={setQuery}
          onSubmit={() => submitRawSolve()}
          onClear={clearWorkspace}
          isLoading={status === 'loading'}
          statusText={getStatusText()}
        />

        {/* Live Workspace Container */}
        <section
          className={styles.workspaceSection}
          aria-live="polite"
          aria-busy={status === 'loading'}
        >
          {status === 'idle' && <WorkspaceEmptyState />}

          {status === 'loading' && (
            <div className={styles.loadingContainer} data-testid="workspace-loading">
              <div className={styles.loadingSpinner} />
              <p className={styles.loadingText}>{t('state_loading')}</p>
            </div>
          )}

          {status === 'network-error' && (
            <NetworkErrorPanel onRetry={() => retryLastRequest()} />
          )}

          {status === 'protocol-error' && (
            <NetworkErrorPanel isProtocolError onRetry={() => retryLastRequest()} />
          )}

          {status === 'transport-error' && result && result.kind === 'transport-error' && (
            <TransportErrorPanel
              error={result.response as TransportErrorResponse}
              httpStatus={httpStatus}
            />
          )}

          {status === 'application-response' && result && result.kind === 'application' && (
            <>
              {/* SOLVED Response */}
              {result.response.response_status === 'SOLVED' && (() => {
                const resp = result.response as SolvedResponse;
                return (
                  <div className={styles.solvedLayout} data-testid="solved-workspace">
                    <CanonicalProblemPanel problem={resp.problem} />
                    <CoefficientEditorPanel
                      draft={coeffDraft}
                      errors={coeffValidationErrors}
                      reactiveStatus={reactiveStatus}
                      sourceMode={sourceMode}
                      isLoading={reactiveStatus === 'recomputing'}
                      isDegenerate={false}
                      onUpdateField={updateCoefficientField}
                      onReset={resetCoefficientsToBackend}
                    />
                    <SolutionSummaryPanel solution={resp.solution} />
                    <MethodCatalogPanel
                      methods={resp.available_methods}
                      selectedMethodId={resp.selected_method_id}
                      onSelectMethod={switchMethod}
                    />
                    <TracePanel trace={resp.solution.trace} />
                    <VerificationPanel
                      certificate={resp.solution.certificate}
                      verificationScope={resp.solution.verification_scope}
                    />
                  </div>
                );
              })()}

              {/* ANALYZED_NO_EXECUTION Response */}
              {result.response.response_status === 'ANALYZED_NO_EXECUTION' && (() => {
                const resp = result.response as AnalyzedNoExecutionResponse;
                const isDegenerate =
                  resp.reason_code === 'DEGENERATE_EXACT_SOLUTION' &&
                  resp.degenerate_solution;

                if (isDegenerate && resp.degenerate_solution) {
                  return (
                    <div className={styles.degenerateLayout} data-testid="degenerate-workspace">
                      <CanonicalProblemPanel problem={resp.problem} />
                      <CoefficientEditorPanel
                        draft={coeffDraft}
                        errors={coeffValidationErrors}
                        reactiveStatus={reactiveStatus}
                        sourceMode={sourceMode}
                        isLoading={reactiveStatus === 'recomputing'}
                        isDegenerate={true}
                        onUpdateField={updateCoefficientField}
                        onReset={resetCoefficientsToBackend}
                      />
                      <DegenerateSolutionPanel solution={resp.degenerate_solution} />
                    </div>
                  );
                }

                return (
                  <div className={styles.analyzedLayout} data-testid="analyzed-workspace">
                    <CanonicalProblemPanel problem={resp.problem} />
                    <CoefficientEditorPanel
                      draft={coeffDraft}
                      errors={coeffValidationErrors}
                      reactiveStatus={reactiveStatus}
                      sourceMode={sourceMode}
                      isLoading={reactiveStatus === 'recomputing'}
                      isDegenerate={resp.problem.problem_type === 'DEGENERATE'}
                      onUpdateField={updateCoefficientField}
                      onReset={resetCoefficientsToBackend}
                    />
                    <MethodNotExecutablePanel
                      reasonCode={resp.reason_code}
                      analysisMessageVi={resp.analysis_message_vi}
                      selectedMethodId={resp.selected_method_id}
                    />
                    {resp.available_methods && resp.available_methods.length > 0 && (
                      <MethodCatalogPanel
                        methods={resp.available_methods}
                        selectedMethodId={resp.selected_method_id}
                        onSelectMethod={switchMethod}
                      />
                    )}
                  </div>
                );
              })()}

              {/* Application ERROR Response */}
              {result.response.response_status === 'ERROR' && (
                <ApplicationErrorPanel
                  error={result.response as ApplicationErrorResponse}
                />
              )}
            </>
          )}

          {/* Session Revision History */}
          {revisionHistory.length > 0 && (
            <RevisionHistoryPanel
              history={revisionHistory}
              onRestoreRevision={restoreRevision}
            />
          )}
        </section>

        {/* MKE Architecture Flow Banner */}
        <section className={styles.flowBanner} aria-label={t('flow_tagline')}>
          <div className={styles.flowTagline}>{t('flow_tagline')}</div>
          <div className={styles.flowPipeline}>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-math)' }}>
                1
              </span>
              <span className={styles.flowLabel}>{t('flow_ast')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              +
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-science)' }}>
                2
              </span>
              <span className={styles.flowLabel}>{t('flow_rational')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              +
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-society)' }}>
                3
              </span>
              <span className={styles.flowLabel}>{t('flow_symbolic')}</span>
            </div>
            <span className={styles.flowArrow} aria-hidden="true">
              ➔
            </span>
            <div className={styles.flowStep}>
              <span className={styles.flowBadge} style={{ backgroundColor: 'var(--col-life)' }}>
                4
              </span>
              <span className={styles.flowLabel}>{t('flow_cert')}</span>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className={styles.appFooter}>
        <div className={styles.footerContainer}>
          <p className={styles.copyright}>{t('footer_copyright')}</p>
        </div>
      </footer>
    </div>
  );
};
