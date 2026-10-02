import React from 'react';
import type { CanonicalQuadraticProblemView, RealRootView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './NumberLinePod.module.css';

export interface NumberLinePodProps {
  quad: CanonicalQuadraticProblemView;
  roots?: RealRootView[];
}

export const NumberLinePod: React.FC<NumberLinePodProps> = ({ roots }) => {
  const { t } = usePreferences();

  if (!roots || roots.length === 0) {
    return null;
  }

  const r1 = roots[0].approximate_float ?? 0;
  const r2 = roots.length > 1 && roots[1] ? (roots[1].approximate_float ?? r1) : r1;

  const minR = Math.min(r1, r2);
  const maxR = Math.max(r1, r2);

  const svgWidth = 440;
  const svgHeight = 65;
  const padLeft = 40;
  const padRight = 40;
  const lineY = 22;
  const plotW = svgWidth - padLeft - padRight;

  const span = Math.max(maxR - minR, 0.5);
  const minVal = Number((minR - span * 0.1).toFixed(1));
  const maxVal = Number((maxR + span * 0.1).toFixed(1));

  // Generate 5-6 nice ticks between minVal and maxVal
  const ticksCount = 6;
  const step = (maxVal - minVal) / (ticksCount - 1);
  const ticks: number[] = [];
  for (let i = 0; i < ticksCount; i++) {
    ticks.push(Number((minVal + i * step).toFixed(1)));
  }

  const toSvgX = (val: number) => padLeft + ((val - minVal) / (maxVal - minVal)) * plotW;

  return (
    <div className={styles.podCard} data-testid="number-line-pod">
      <div className={styles.podHeader}>
        <span className={styles.podTitle}>{t('lbl_number_line') || 'Number line:'}</span>
      </div>
      <div className={styles.podBody}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className={styles.lineSvg}
          role="img"
          aria-label="Real number line with roots"
        >
          {/* Main axis line */}
          <line
            x1={padLeft - 10}
            y1={lineY}
            x2={svgWidth - padRight + 10}
            y2={lineY}
            stroke="#94a3b8"
            strokeWidth="1.5"
          />

          {/* Tick marks and labels */}
          {ticks.map((val, idx) => {
            const sx = toSvgX(val);
            return (
              <g key={`tick-${idx}`}>
                <line x1={sx} y1={lineY - 4} x2={sx} y2={lineY + 4} stroke="#64748b" strokeWidth="1" />
                <text x={sx} y={lineY + 18} textAnchor="middle" className={styles.tickLabel}>
                  {val.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Root markers (blue dots matching Wolfram) */}
          <circle cx={toSvgX(r1)} cy={lineY} r="4.5" fill="#3b82f6" stroke="#ffffff" strokeWidth="1.5" />
          {r1 !== r2 && (
            <circle cx={toSvgX(r2)} cy={lineY} r="4.5" fill="#3b82f6" stroke="#ffffff" strokeWidth="1.5" />
          )}
        </svg>
      </div>
    </div>
  );
};
