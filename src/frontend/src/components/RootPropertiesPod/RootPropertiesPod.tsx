import React from 'react';
import type { CanonicalQuadraticProblemView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { formatRational } from '../../utils/formatters';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBolt, faCheckDouble } from '@fortawesome/free-solid-svg-icons';
import styles from './RootPropertiesPod.module.css';

export interface RootPropertiesPodProps {
  quad: CanonicalQuadraticProblemView;
}

export const RootPropertiesPod: React.FC<RootPropertiesPodProps> = ({ quad }) => {
  const { lang, t } = usePreferences();

  const aNum = quad.a.numerator;
  const aDen = quad.a.denominator;
  const bNum = quad.b.numerator;
  const bDen = quad.b.denominator;
  const cNum = quad.c.numerator;
  const cDen = quad.c.denominator;

  // S = -b / a
  const sumNum = -bNum * aDen;
  const sumDen = bDen * aNum;
  const sumStr = formatRational({ numerator: sumNum, denominator: sumDen });

  // P = c / a
  const prodNum = cNum * aDen;
  const prodDen = cDen * aNum;
  const prodStr = formatRational({ numerator: prodNum, denominator: prodDen });

  // Floating values for conditional checks
  const aVal = aNum / aDen;
  const bVal = bNum / bDen;
  const cVal = cNum / cDen;
  const deltaVal = quad.discriminant.value.numerator / quad.discriminant.value.denominator;
  const sumVal = sumNum / sumDen;
  const prodVal = prodNum / prodDen;

  // Detect special mental math cases
  const isSumCoeffZero = Math.abs(aVal + bVal + cVal) < 1e-9;
  const isDiffCoeffZero = Math.abs(aVal - bVal + cVal) < 1e-9;
  const isEvenB = quad.b.denominator === 1 && Math.abs(quad.b.numerator) % 2 === 0;

  return (
    <div className={styles.podCard} data-testid="root-properties-container">
      <div className={styles.podHeader}>
        <div className={styles.headerLeft}>
          <FontAwesomeIcon icon={faBolt} className={styles.headerIcon} />
          <span className={styles.podTitle}>
            {lang === 'vi' ? 'Mẹo giải nhanh & Nhận xét (Định lý Viète)' : 'Quick Tips & Properties (Viète Theorem)'}
          </span>
        </div>
      </div>

      <div className={styles.podBody}>
        {/* Viète Sum & Product Grid */}
        <div className={styles.vieteGrid}>
          {/* Sum of Roots Pod */}
          <div className={styles.subPod} data-testid="sum-of-roots-pod">
            <div className={styles.subHeader}>
              <span className={styles.subTitle}>{t('lbl_sum_of_roots') || 'Sum of roots:'}</span>
            </div>
            <div className={styles.subBody}>
              <MathLatex latex={`S = x_1 + x_2 = -\\frac{b}{a} = ${sumStr}`} displayMode />
            </div>
          </div>

          {/* Product of Roots Pod */}
          <div className={styles.subPod} data-testid="product-of-roots-pod">
            <div className={styles.subHeader}>
              <span className={styles.subTitle}>{t('lbl_product_of_roots') || 'Product of roots:'}</span>
            </div>
            <div className={styles.subBody}>
              <MathLatex latex={`P = x_1 \\cdot x_2 = \\frac{c}{a} = ${prodStr}`} displayMode />
            </div>
          </div>
        </div>

        {/* Mental Math Shortcuts & Sign Insights */}
        <div className={styles.insightsList}>
          {isSumCoeffZero && (
            <div className={styles.insightRow}>
              <FontAwesomeIcon icon={faCheckDouble} className={styles.insightIconSuccess} />
              <span className={styles.insightText}>
                <strong>{lang === 'vi' ? 'Mẹo đặc biệt a + b + c = 0:' : 'Special Case a + b + c = 0:'}</strong>{' '}
                {lang === 'vi'
                  ? `Phương trình có ngay 2 nghiệm nhẩm: x₁ = 1 và x₂ = c/a = ${prodStr}`
                  : `Roots can be directly derived: x₁ = 1 and x₂ = c/a = ${prodStr}`}
              </span>
            </div>
          )}

          {isDiffCoeffZero && (
            <div className={styles.insightRow}>
              <FontAwesomeIcon icon={faCheckDouble} className={styles.insightIconSuccess} />
              <span className={styles.insightText}>
                <strong>{lang === 'vi' ? 'Mẹo đặc biệt a − b + c = 0:' : 'Special Case a − b + c = 0:'}</strong>{' '}
                {lang === 'vi'
                  ? `Phương trình có ngay 2 nghiệm nhẩm: x₁ = -1 và x₂ = -c/a = ${formatRational({ numerator: -prodNum, denominator: prodDen })}`
                  : `Roots can be directly derived: x₁ = -1 and x₂ = -c/a = ${formatRational({ numerator: -prodNum, denominator: prodDen })}`}
              </span>
            </div>
          )}

          {isEvenB && !isSumCoeffZero && !isDiffCoeffZero && (
            <div className={styles.insightRow}>
              <FontAwesomeIcon icon={faCheckDouble} className={styles.insightIconInfo} />
              <span className={styles.insightText}>
                <strong>{lang === 'vi' ? 'Mẹo hệ số b chẵn:' : 'Even b Coefficient Trick:'}</strong>{' '}
                {lang === 'vi'
                  ? `Hệ số b = ${bVal} là số chẵn. Có thể dùng biệt thức thu gọn Δ' = b'² − ac để tính toán nhanh hơn.`
                  : `Coefficient b = ${bVal} is even. You can use reduced discriminant Δ' = b'² − ac for faster calculation.`}
              </span>
            </div>
          )}

          {/* Root sign classification */}
          {deltaVal > 0 && prodVal > 0 && sumVal > 0 && (
            <div className={styles.insightRow}>
              <span className={styles.insightBullet}>•</span>
              <span className={styles.insightText}>
                {lang === 'vi'
                  ? `Vì Δ > 0, P > 0 và S > 0 nên phương trình có hai nghiệm dương phân biệt (0 < x₁ < x₂).`
                  : `Since Δ > 0, P > 0 and S > 0, the equation has two distinct positive roots (0 < x₁ < x₂).`}
              </span>
            </div>
          )}

          {deltaVal > 0 && prodVal > 0 && sumVal < 0 && (
            <div className={styles.insightRow}>
              <span className={styles.insightBullet}>•</span>
              <span className={styles.insightText}>
                {lang === 'vi'
                  ? `Vì Δ > 0, P > 0 và S < 0 nên phương trình có hai nghiệm âm phân biệt (x₁ < x₂ < 0).`
                  : `Since Δ > 0, P > 0 and S < 0, the equation has two distinct negative roots (x₁ < x₂ < 0).`}
              </span>
            </div>
          )}

          {deltaVal > 0 && prodVal < 0 && (
            <div className={styles.insightRow}>
              <span className={styles.insightBullet}>•</span>
              <span className={styles.insightText}>
                {lang === 'vi'
                  ? `Vì P = c/a < 0 (hệ số a và c trái dấu) nên phương trình luôn có hai nghiệm trái dấu (x₁ < 0 < x₂).`
                  : `Since P = c/a < 0 (a and c have opposite signs), the equation has two roots of opposite signs (x₁ < 0 < x₂).`}
              </span>
            </div>
          )}

          {deltaVal === 0 && (
            <div className={styles.insightRow}>
              <span className={styles.insightBullet}>•</span>
              <span className={styles.insightText}>
                {lang === 'vi'
                  ? `Vì Δ = 0 nên phương trình có nghiệm kép x₁ = x₂ = -b/(2a).`
                  : `Since Δ = 0, the equation has a double root x₁ = x₂ = -b/(2a).`}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
