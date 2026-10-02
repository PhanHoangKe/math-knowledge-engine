import React from 'react';
import type { CanonicalQuadraticProblemView, RealRootView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import styles from './RootPlotPod.module.css';

export interface RootPlotPodProps {
  quad: CanonicalQuadraticProblemView;
  roots?: RealRootView[];
}

export const RootPlotPod: React.FC<RootPlotPodProps> = ({ quad, roots }) => {
  const { t } = usePreferences();

  const a = quad.a.denominator !== 0 ? quad.a.numerator / quad.a.denominator : 1;
  const b = quad.b.denominator !== 0 ? quad.b.numerator / quad.b.denominator : 0;
  const c = quad.c.denominator !== 0 ? quad.c.numerator / quad.c.denominator : 0;

  const hasRealRoots = Boolean(roots && roots.length > 0);
  const r1 = hasRealRoots && roots[0] ? (roots[0].approximate_float ?? 0) : 0;
  const r2 = hasRealRoots && roots.length > 1 && roots[1] ? (roots[1].approximate_float ?? r1) : r1;

  const vertexX = -b / (2 * a);

  // SVG canvas bounds
  const svgWidth = 440;
  const svgHeight = 220;
  const padLeft = 46;
  const padRight = 30;
  const padTop = 20;
  const padBottom = 35;

  const plotW = svgWidth - padLeft - padRight;
  const plotH = svgHeight - padTop - padBottom;

  // Domain & Range
  let minX: number;
  let maxX: number;
  if (hasRealRoots) {
    const span = Math.max(Math.abs(r2 - r1), 1);
    minX = Math.min(r1, r2) - span * 0.35;
    maxX = Math.max(r1, r2) + span * 0.35;
  } else {
    minX = vertexX - 2.5;
    maxX = vertexX + 2.5;
  }

  // Calculate curve points
  const numSteps = 50;
  const points: { x: number; y: number }[] = [];
  let minY = Infinity;
  let maxY = -Infinity;

  for (let i = 0; i <= numSteps; i++) {
    const xVal = minX + (i / numSteps) * (maxX - minX);
    const yVal = a * xVal * xVal + b * xVal + c;
    points.push({ x: xVal, y: yVal });
    if (yVal < minY) minY = yVal;
    if (yVal > maxY) maxY = yVal;
  }

  // Ensure 0 is in the range
  if (minY > 0) minY = -0.1 * (maxY - minY);
  if (maxY < 0) maxY = 0.1 * (maxY - minY);

  const yMargin = (maxY - minY) * 0.15 || 0.5;
  minY -= yMargin;
  maxY += yMargin;

  const toSvgX = (x: number) => padLeft + ((x - minX) / (maxX - minX)) * plotW;
  const toSvgY = (y: number) => padTop + plotH - ((y - minY) / (maxY - minY)) * plotH;

  const pathData = points.reduce((acc, pt, idx) => {
    const sx = toSvgX(pt.x).toFixed(1);
    const sy = toSvgY(pt.y).toFixed(1);
    return idx === 0 ? `M ${sx} ${sy}` : `${acc} L ${sx} ${sy}`;
  }, '');

  // Ticks
  const xTicks = [
    minX + (maxX - minX) * 0.15,
    minX + (maxX - minX) * 0.5,
    minX + (maxX - minX) * 0.85,
  ];
  if (hasRealRoots) {
    xTicks.length = 0;
    xTicks.push(Math.min(r1, r2), (r1 + r2) / 2, Math.max(r1, r2));
    if (r1 !== r2) {
      xTicks.unshift(Math.min(r1, r2) - Math.abs(r2 - r1) * 0.3);
      xTicks.push(Math.max(r1, r2) + Math.abs(r2 - r1) * 0.3);
    }
  }

  const yTicks = [
    minY + (maxY - minY) * 0.15,
    0,
    maxY - (maxY - minY) * 0.15,
  ];

  const zeroY = toSvgY(0);

  return (
    <div className={styles.podCard} data-testid="root-plot-pod">
      <div className={styles.podHeader}>
        <span className={styles.podTitle}>{t('lbl_root_plot') || 'Root plot:'}</span>
      </div>
      <div className={styles.podBody}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className={styles.plotSvg}
          role="img"
          aria-label="Root plot 2D graph"
        >
          {/* Subtle grid lines */}
          {yTicks.map((yVal, idx) => {
            const sy = toSvgY(yVal);
            return (
              <line
                key={`gy-${idx}`}
                x1={padLeft}
                y1={sy}
                x2={svgWidth - padRight}
                y2={sy}
                stroke="var(--border-subtle, #e2e8f0)"
                strokeDasharray={yVal === 0 ? 'none' : '3 3'}
                strokeWidth={yVal === 0 ? 1.2 : 0.8}
              />
            );
          })}

          {xTicks.map((xVal, idx) => {
            const sx = toSvgX(xVal);
            return (
              <line
                key={`gx-${idx}`}
                x1={sx}
                y1={padTop}
                x2={sx}
                y2={svgHeight - padBottom}
                stroke="var(--border-subtle, #e2e8f0)"
                strokeDasharray="3 3"
                strokeWidth="0.8"
              />
            );
          })}

          {/* Coordinate axes */}
          <line
            x1={padLeft}
            y1={zeroY >= padTop && zeroY <= svgHeight - padBottom ? zeroY : svgHeight - padBottom}
            x2={svgWidth - padRight}
            y2={zeroY >= padTop && zeroY <= svgHeight - padBottom ? zeroY : svgHeight - padBottom}
            stroke="#718096"
            strokeWidth="1.2"
          />

          {/* Y Axis labels */}
          {yTicks.map((yVal, idx) => {
            const sy = toSvgY(yVal);
            return (
              <text
                key={`yl-${idx}`}
                x={padLeft - 6}
                y={sy + 3.5}
                textAnchor="end"
                className={styles.axisLabel}
              >
                {yVal.toFixed(1)}
              </text>
            );
          })}

          {/* X Axis labels */}
          {xTicks.map((xVal, idx) => {
            const sx = toSvgX(xVal);
            return (
              <text
                key={`xl-${idx}`}
                x={sx}
                y={svgHeight - padBottom + 16}
                textAnchor="middle"
                className={styles.axisLabel}
              >
                {xVal.toFixed(1)}
              </text>
            );
          })}

          {/* Parabola curve */}
          <path d={pathData} fill="none" stroke="#5b86b6" strokeWidth="2.2" strokeLinecap="round" />

          {/* Highlighted real root points from backend */}
          {hasRealRoots && (
            <>
              <circle
                cx={toSvgX(r1)}
                cy={toSvgY(0)}
                r="4.5"
                fill="#e53e3e"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
              {r1 !== r2 && (
                <circle
                  cx={toSvgX(r2)}
                  cy={toSvgY(0)}
                  r="4.5"
                  fill="#e53e3e"
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              )}
            </>
          )}
        </svg>
      </div>
    </div>
  );
};
