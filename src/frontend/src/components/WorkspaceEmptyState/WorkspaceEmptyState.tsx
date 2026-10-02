import React from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './WorkspaceEmptyState.module.css';

export interface WorkspaceEmptyStateProps {
  onSelectEquation?: (equation: string) => void;
}

interface TopicCardItem {
  id: string;
  titleKey: string;
  sampleEquation: string;
  iconType: string;
}

interface TopicColumn {
  id: string;
  titleKey: string;
  colorVar: string;
  items: TopicCardItem[];
}

export const WorkspaceEmptyState: React.FC<WorkspaceEmptyStateProps> = ({ onSelectEquation }) => {
  const { t } = usePreferences();

  const topicColumns: TopicColumn[] = [
    {
      id: 'math',
      titleKey: 'topic_col_math',
      colorVar: 'var(--col-math)',
      items: [
        { id: 'step_by_step', titleKey: 'topic_step_by_step', sampleEquation: 'x^2 - 5*x + 6 = 0', iconType: 'step' },
        { id: 'quadratic_eq', titleKey: 'topic_quadratic_eq', sampleEquation: '2*x^2 - 4*x + 2 = 0', iconType: 'quad' },
        { id: 'viete_method', titleKey: 'topic_viete', sampleEquation: 'x^2 - 7*x + 10 = 0', iconType: 'viete' },
        { id: 'delta_analysis', titleKey: 'topic_delta', sampleEquation: '3*x^2 - 5*x + 2 = 0', iconType: 'delta' },
        { id: 'factoring_id', titleKey: 'topic_factoring', sampleEquation: 'x^2 - 9 = 0', iconType: 'factor' },
      ],
    },
    {
      id: 'knowledge',
      titleKey: 'topic_col_knowledge',
      colorVar: 'var(--col-science)',
      items: [
        { id: 'theorems_lib', titleKey: 'topic_theorems', sampleEquation: 'x^2 - 4 = 0', iconType: 'theorem' },
        { id: 'formula_table', titleKey: 'topic_formulas', sampleEquation: 'x^2 + 2*x + 1 = 0', iconType: 'formula' },
        { id: 'verification', titleKey: 'topic_verification', sampleEquation: 'x^2 - 2 = 0', iconType: 'verify' },
        { id: 'rational_field', titleKey: 'topic_rational', sampleEquation: 'x^2 + 1 = 0', iconType: 'rational' },
      ],
    },
    {
      id: 'functions',
      titleKey: 'topic_col_functions',
      colorVar: 'var(--col-society)',
      items: [
        { id: 'parabola_plot', titleKey: 'topic_parabola', sampleEquation: 'x^2 - 6*x + 5 = 0', iconType: 'parabola' },
        { id: 'vertex_axis', titleKey: 'topic_vertex', sampleEquation: '2*x^2 - 8*x + 6 = 0', iconType: 'vertex' },
        { id: 'intercepts', titleKey: 'topic_intercepts', sampleEquation: 'x^2 - 3*x = 0', iconType: 'intercept' },
        { id: 'roots_class', titleKey: 'topic_roots_class', sampleEquation: '4*x^2 - 12*x + 9 = 0', iconType: 'roots' },
      ],
    },
    {
      id: 'tools',
      titleKey: 'topic_col_tools',
      colorVar: 'var(--col-life)',
      items: [
        { id: 'multi_methods', titleKey: 'topic_multi_methods', sampleEquation: 'x^2 - 5*x + 6 = 0', iconType: 'compare' },
        { id: 'reactive_coeffs', titleKey: 'topic_reactive', sampleEquation: 'x^2 - 4*x + 3 = 0', iconType: 'reactive' },
        { id: 'latex_export', titleKey: 'topic_latex', sampleEquation: '3*x^2 - 6*x = 0', iconType: 'latex' },
        { id: 'history_audit', titleKey: 'topic_history', sampleEquation: 'x^2 + 2*x - 8 = 0', iconType: 'history' },
      ],
    },
  ];

  const handleCardClick = (eq: string) => {
    if (onSelectEquation) {
      onSelectEquation(eq);
    }
  };

  const renderCardIcon = (iconType: string, color: string) => {
    switch (iconType) {
      case 'step':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
          </svg>
        );
      case 'quad':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="1.8">
            <text x="2" y="16" fill={color} fontSize="14" fontWeight="bold" fontFamily="serif">x²-1</text>
          </svg>
        );
      case 'viete':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="1.8">
            <text x="2" y="16" fill={color} fontSize="13" fontWeight="bold" fontFamily="serif">x₁+x₂</text>
          </svg>
        );
      case 'delta':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="1.8">
            <text x="4" y="17" fill={color} fontSize="16" fontWeight="bold" fontFamily="serif">Δ</text>
          </svg>
        );
      case 'factor':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="1.8">
            <text x="2" y="16" fill={color} fontSize="12" fontWeight="bold" fontFamily="serif">(x-a)</text>
          </svg>
        );
      case 'theorem':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          </svg>
        );
      case 'formula':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
        );
      case 'verify':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        );
      case 'rational':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="1.8">
            <text x="4" y="17" fill={color} fontSize="16" fontWeight="bold" fontFamily="serif">ℝ ℚ</text>
          </svg>
        );
      case 'parabola':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="M6 7c4 10 8 10 12 0" />
          </svg>
        );
      case 'vertex':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3v18M3 12h18" />
            <circle cx="12" cy="12" r="3" fill={color} />
          </svg>
        );
      case 'intercept':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 20L20 4M4 4h4v4M20 20h-4v-4" />
          </svg>
        );
      case 'roots':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
        );
      case 'compare':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="4" width="8" height="16" rx="1" />
            <rect x="14" y="4" width="8" height="16" rx="1" />
          </svg>
        );
      case 'reactive':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
          </svg>
        );
      case 'latex':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
          </svg>
        );
      case 'history':
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
        );
      default:
        return (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke={color} strokeWidth="2">
            <circle cx="12" cy="12" r="8" />
          </svg>
        );
    }
  };

  return (
    <section
      className={styles.container}
      aria-label={t('empty_workspace_title')}
      data-testid="workspace-empty-state"
    >
      {/* Central Welcome / Status Banner */}
      <div className={styles.emptyCard}>
        <div className={styles.iconCircle} aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="28"
            height="28"
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
      </div>

      {/* 4-Column Topic Directory Grid - Authentic WolframAlpha Style */}
      <div className={styles.topicsGrid}>
        {topicColumns.map((col) => (
          <div key={col.id} className={styles.topicColumn}>
            <h2 className={styles.columnHeader} style={{ color: col.colorVar }}>
              <span>{t(col.titleKey as any)}</span>
              <span className={styles.headerArrow} aria-hidden="true"> ›</span>
            </h2>

            <div className={styles.cardsList}>
              {col.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={styles.topicCard}
                  onClick={() => handleCardClick(item.sampleEquation)}
                  title={`Ví dụ: ${item.sampleEquation}`}
                >
                  <span className={styles.cardIconWrapper} aria-hidden="true">
                    {renderCardIcon(item.iconType, col.colorVar)}
                  </span>
                  <span className={styles.cardTitle}>{t(item.titleKey as any)}</span>
                </button>
              ))}
              <button
                type="button"
                className={styles.moreTopicsCard}
                onClick={() => handleCardClick(col.items[0]?.sampleEquation ?? 'x^2 - 5*x + 6 = 0')}
                title={t('more_topics')}
                style={{ borderColor: col.colorVar }}
              >
                <span className={styles.cardIconWrapper} aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill={col.colorVar}>
                    <circle cx="6" cy="6" r="2" />
                    <circle cx="12" cy="6" r="2" />
                    <circle cx="18" cy="6" r="2" />
                    <circle cx="6" cy="18" r="2" />
                    <circle cx="12" cy="18" r="2" />
                    <circle cx="18" cy="18" r="2" />
                  </svg>
                </span>
                <span className={styles.moreCardTitle} style={{ color: col.colorVar }}>
                  {t('more_topics')}
                </span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Engine Technology Pipeline Banner */}
      <div className={styles.pipelineBanner}>
        <div className={styles.pipelineHeader}>
          <span className={styles.pipelineTitle}>
            Được thực hiện nhờ Kiến trúc CAS Tất định — Dựa trên Cơ sở Tri thức Toán học Hình thức
          </span>
        </div>
        <div className={styles.pipelineFlow}>
          <span className={styles.pipelineStep} style={{ borderColor: 'var(--col-math)', color: 'var(--col-math)' }}>
            <strong>MKE Engine</strong>
          </span>
          <span className={styles.pipelineOperator}>=</span>
          <span className={styles.pipelineStep}>
            Chuẩn hóa & AST
          </span>
          <span className={styles.pipelineOperator}>+</span>
          <span className={styles.pipelineStep}>
            Tri thức Định lý & Công thức
          </span>
          <span className={styles.pipelineOperator}>+</span>
          <span className={styles.pipelineStep}>
            CAS Giải tất định trên ℝ
          </span>
          <span className={styles.pipelineOperator}>➔</span>
          <span className={styles.pipelineStepFinal}>
            Lời giải từng bước + Xác minh độc lập
          </span>
        </div>
      </div>
    </section>
  );
};
