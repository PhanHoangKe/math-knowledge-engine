import React from 'react';
import type { CanonicalQuadraticProblemView, RealRootView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { formatRational } from '../../utils/formatters';
import styles from './AlternateFormsPod.module.css';

export interface AlternateFormsPodProps {
  quad: CanonicalQuadraticProblemView;
  roots?: RealRootView[];
}

export const AlternateFormsPod: React.FC<AlternateFormsPodProps> = ({ quad, roots }) => {
  const { t } = usePreferences();

  const aNum = quad.a.numerator;
  const aDen = quad.a.denominator;
  const bNum = quad.b.numerator;
  const bDen = quad.b.denominator;
  const cNum = quad.c.numerator;
  const cDen = quad.c.denominator;

  const a = aDen !== 0 ? aNum / aDen : 1;
  const b = bDen !== 0 ? bNum / bDen : 0;
  const c = cDen !== 0 ? cNum / cDen : 0;

  const forms: string[] = [];

  // Form 1: Factored form (using backend provided roots)
  if (roots && roots.length > 0) {
    const lead = a !== 1 ? (a === -1 ? '-' : `${formatRational(quad.a)}`) : '';
    if (roots.length === 1) {
      const r = roots[0].latex_str;
      const term = r === '0' ? 'x' : `(x - ${r})`;
      forms.push(`${lead}${term}^2 = 0`);
    } else if (roots.length === 2) {
      const r1 = roots[0].latex_str;
      const r2 = roots[1].latex_str;
      const term1 = r1 === '0' ? 'x' : `(x - ${r1})`;
      const term2 = r2 === '0' ? 'x' : `(x - ${r2})`;
      forms.push(`${lead}${term2}${term1} = 0`);
    }
  }

  // Form 2: Isolated linear term (e.g. x^2 + 6 = 5x)
  if (b !== 0) {
    const quadPart = a === 1 ? 'x^2' : a === -1 ? '-x^2' : `${formatRational(quad.a)}x^2`;
    const constSign = c > 0 ? ` + ${formatRational(quad.c)}` : c < 0 ? ` - ${formatRational({ numerator: -cNum, denominator: cDen })}` : '';
    const rhsSign = -b === 1 ? 'x' : -b === -1 ? '-x' : `${formatRational({ numerator: -bNum, denominator: bDen })}x`;
    forms.push(`${quadPart}${constSign} = ${rhsSign}`);
  }

  // Form 3: Completing the square / Vertex form (x - h)^2 + k = 0
  const hNum = -bNum * aDen;
  const hDen = 2 * aNum * bDen;
  const hStr = formatRational({ numerator: Math.abs(hNum), denominator: Math.abs(hDen) });
  const hSign = (hNum / hDen) >= 0 ? ` - ${hStr}` : ` + ${hStr}`;
  
  // Use backend discriminant for k = -delta / (4a)
  const deltaNum = quad.discriminant.value.numerator;
  const deltaDen = quad.discriminant.value.denominator;
  const kNum = -deltaNum * aDen;
  const kDen = 4 * deltaDen * aNum;
  const kRational = { numerator: Math.abs(kNum), denominator: Math.abs(kDen) };
  const kStr = (kNum / kDen) !== 0 ? ((kNum / kDen) > 0 ? ` + ${formatRational(kRational)}` : ` - ${formatRational(kRational)}`) : '';

  const squareBase = hStr === '0' ? 'x^2' : `\\left(x${hSign}\\right)^2`;
  const leadSquare = a !== 1 ? (a === -1 ? '-' : `${formatRational(quad.a)}`) : '';
  forms.push(`${leadSquare}${squareBase}${kStr} = 0`);

  if (forms.length === 0) {
    return null;
  }

  return (
    <div className={styles.podCard} data-testid="alternate-forms-pod">
      <div className={styles.podHeader}>
        <span className={styles.podTitle}>{t('lbl_alternate_forms') || 'Alternate forms:'}</span>
      </div>
      <div className={styles.podBody}>
        {forms.map((formLatex, idx) => (
          <div key={idx} className={styles.formRow} data-testid={`alternate-form-${idx}`}>
            <MathLatex latex={formLatex} displayMode />
          </div>
        ))}
      </div>
    </div>
  );
};
