import React from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './WorkspaceEmptyState.module.css';

export const WorkspaceEmptyState: React.FC = () => {
  const { t } = usePreferences();

  const skeletonPanels = [
    {
      id: 'input-analysis',
      titleKey: 'panel_skeleton_input_analysis' as const,
      colorVar: 'var(--col-math)',
      iconLetter: 'P',
    },
    {
      id: 'canonical-form',
      titleKey: 'panel_skeleton_canonical_form' as const,
      colorVar: 'var(--col-science)',
      iconLetter: 'C',
    },
    {
      id: 'applicable-methods',
      titleKey: 'panel_skeleton_methods' as const,
      colorVar: 'var(--col-society)',
      iconLetter: 'M',
    },
    {
      id: 'solution-trace',
      titleKey: 'panel_skeleton_solution_trace' as const,
      colorVar: 'var(--col-life)',
      iconLetter: 'S',
    },
  ];

  return (
    <section className={styles.container} aria-label={t('empty_workspace_title')}>
      {/* Central Truthful Empty State Banner */}
      <div className={styles.emptyCard}>
        <div className={styles.iconCircle} aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="32"
            height="32"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            <path d="M9 7h6M9 11h6" />
          </svg>
        </div>

        <h2 className={styles.emptyTitle}>{t('empty_workspace_title')}</h2>
        <p className={styles.emptyMessage}>{t('empty_workspace_msg')}</p>
        <p className={styles.emptySub}>{t('empty_workspace_sub')}</p>
        <div className={styles.shellNote}>{t('shell_status_note')}</div>
      </div>

      {/* Structural Skeletons for Future S2-04 Result Panels (Inactive/Awaiting Query) */}
      <div className={styles.skeletonsGrid} aria-hidden="true">
        {skeletonPanels.map((panel) => (
          <div key={panel.id} className={styles.skeletonCard}>
            <div className={styles.skeletonHeader}>
              <span
                className={styles.skeletonBadge}
                style={{ backgroundColor: panel.colorVar }}
              >
                {panel.iconLetter}
              </span>
              <span className={styles.skeletonTitle}>{t(panel.titleKey)}</span>
            </div>
            <div className={styles.skeletonBody}>
              <div className={styles.skeletonLineLong} />
              <div className={styles.skeletonLineShort} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
