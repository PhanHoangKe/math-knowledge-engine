import React from 'react';
import type { CanonicalQuadraticProblemView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { formatRational } from '../../utils/formatters';
import styles from './RootPropertiesPod.module.css';

export interface RootPropertiesPodProps {
  quad: CanonicalQuadraticProblemView;
}

export const RootPropertiesPod: React.FC<RootPropertiesPodProps> = ({ quad }) => {
  const { t } = usePreferences();

  const aNum = quad.a.numerator;
  const aDen = quad.a.denominator;
  const bNum = quad.b.numerator;
  const bDen = quad.b.denominator;
  const cNum = quad.c.numerator;
  const cDen = quad.c.denominator;

  // Sum of roots: S = -b / a = - (bNum/bDen) / (aNum/aDen) = - (bNum * aDen) / (bDen * aNum)
  const sumNum = -bNum * aDen;
  const sumDen = bDen * aNum;
  const sumStr = formatRational({ numerator: sumNum, denominator: sumDen });

  // Product of roots: P = c / a = (cNum/cDen) / (aNum/aDen) = (cNum * aDen) / (cDen * aNum)
  const prodNum = cNum * aDen;
  const prodDen = cDen * aNum;
  const prodStr = formatRational({ numerator: prodNum, denominator: prodDen });

  return (
    <>
      {/* Sum of Roots Pod */}
      <div className={styles.podCard} data-testid="sum-of-roots-pod">
        <div className={styles.podHeader}>
          <span className={styles.podTitle}>{t('lbl_sum_of_roots') || 'Sum of roots:'}</span>
        </div>
        <div className={styles.podBody}>
          <div className={styles.valueRow}>
            <MathLatex latex={sumStr} displayMode />
          </div>
        </div>
      </div>

      {/* Product of Roots Pod */}
      <div className={styles.podCard} data-testid="product-of-roots-pod">
        <div className={styles.podHeader}>
          <span className={styles.podTitle}>{t('lbl_product_of_roots') || 'Product of roots:'}</span>
        </div>
        <div className={styles.podBody}>
          <div className={styles.valueRow}>
            <MathLatex latex={prodStr} displayMode />
          </div>
        </div>
      </div>
    </>
  );
};
