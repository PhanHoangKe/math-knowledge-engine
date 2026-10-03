import React from 'react';
import type { CanonicalQuadraticProblemView } from '../../api/contract';
import { usePreferences } from '../../state/preferences';
import { MathLatex } from '../MathLatex/MathLatex';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLightbulb, faArrowRight } from '@fortawesome/free-solid-svg-icons';
import styles from './RelatedProblemsPod.module.css';

export interface RelatedProblemsPodProps {
  quad: CanonicalQuadraticProblemView;
  onSelectEquation: (eq: string) => void;
}

interface RelatedItem {
  equation: string;
  latex: string;
  labelVi: string;
  labelEn: string;
}

export const RelatedProblemsPod: React.FC<RelatedProblemsPodProps> = ({
  quad,
  onSelectEquation,
}) => {
  const { lang, t } = usePreferences();

  // Generate 3 contextual practice problems based on current equation parameters
  const a = quad.a.numerator / quad.a.denominator;
  const b = quad.b.numerator / quad.b.denominator;
  const c = quad.c.numerator / quad.c.denominator;

  const generateRelated = (): RelatedItem[] => {
    // If integer coefficients
    if (
      quad.a.denominator === 1 &&
      quad.b.denominator === 1 &&
      quad.c.denominator === 1
    ) {
      if (a === 1 && b === -5 && c === 6) {
        return [
          {
            equation: 'x^2 - 7*x + 12 = 0',
            latex: 'x^2 - 7x + 12 = 0',
            labelVi: 'Cùng dạng 2 nghiệm nguyên dương (x = 3, 4)',
            labelEn: 'Same form with 2 positive integer roots (x = 3, 4)',
          },
          {
            equation: '2*x^2 - 5*x + 2 = 0',
            latex: '2x^2 - 5x + 2 = 0',
            labelVi: 'Dạng có hệ số a ≠ 1 (x = 2, 1/2)',
            labelEn: 'Form with leading coefficient a ≠ 1 (x = 2, 1/2)',
          },
          {
            equation: 'x^2 - 6*x + 9 = 0',
            latex: 'x^2 - 6x + 9 = 0',
            labelVi: 'Dạng hằng đẳng thức, nghiệm kép Δ = 0 (x = 3)',
            labelEn: 'Perfect square form, double root Δ = 0 (x = 3)',
          },
          {
            equation: 'x^2 + 5*x + 6 = 0',
            latex: 'x^2 + 5x + 6 = 0',
            labelVi: 'Đổi dấu hệ số b (x = -2, -3)',
            labelEn: 'Inverted linear sign (x = -2, -3)',
          },
        ];
      }

      // Generic quadratic generator
      const items: RelatedItem[] = [];
      
      // Variation 1: Shift b
      const newB = b > 0 ? b + 2 : b - 2;
      items.push({
        equation: `${a !== 1 ? a : ''}x^2 ${newB >= 0 ? '+ ' + newB : '- ' + Math.abs(newB)}*x ${c >= 0 ? '+ ' + c : '- ' + Math.abs(c)} = 0`,
        latex: `${a !== 1 ? (a === -1 ? '-' : a) : ''}x^2 ${newB >= 0 ? '+ ' + newB : '- ' + Math.abs(newB)}x ${c >= 0 ? '+ ' + c : '- ' + Math.abs(c)} = 0`,
        labelVi: 'Biến thể thay đổi hệ số b',
        labelEn: 'Variation with modified linear coefficient b',
      });

      // Variation 2: Leading coefficient multiplier
      const newA = a === 1 ? 2 : 1;
      items.push({
        equation: `${newA !== 1 ? newA : ''}x^2 ${b >= 0 ? '+ ' + b : '- ' + Math.abs(b)}*x ${c >= 0 ? '+ ' + c : '- ' + Math.abs(c)} = 0`,
        latex: `${newA !== 1 ? (newA === -1 ? '-' : newA) : ''}x^2 ${b >= 0 ? '+ ' + b : '- ' + Math.abs(b)}x ${c >= 0 ? '+ ' + c : '- ' + Math.abs(c)} = 0`,
        labelVi: 'Biến thể thay đổi hệ số bậc hai a',
        labelEn: 'Variation with modified quadratic coefficient a',
      });

      // Variation 3: Perfect square companion
      items.push({
        equation: 'x^2 - 4*x + 4 = 0',
        latex: 'x^2 - 4x + 4 = 0',
        labelVi: 'Dạng hằng đẳng thức (x - 2)² = 0',
        labelEn: 'Perfect square trinomial (x - 2)² = 0',
      });

      return items;
    }

    return [
      {
        equation: 'x^2 - 5*x + 6 = 0',
        latex: 'x^2 - 5x + 6 = 0',
        labelVi: 'Phương trình bậc 2 cơ bản',
        labelEn: 'Standard quadratic equation',
      },
      {
        equation: '2*x^2 - 7*x + 3 = 0',
        latex: '2x^2 - 7x + 3 = 0',
        labelVi: 'Phương trình có hệ số a > 1',
        labelEn: 'Quadratic equation with a > 1',
      },
    ];
  };

  const relatedList = generateRelated();

  return (
    <div className={styles.podCard} data-testid="related-problems-pod">
      <div className={styles.podHeader}>
        <div className={styles.headerLeft}>
          <FontAwesomeIcon icon={faLightbulb} className={styles.headerIcon} />
          <span className={styles.podTitle}>
            {lang === 'vi' ? 'Dạng bài liên quan & Luyện tập nhanh' : 'Related Problems & Quick Practice'}
          </span>
        </div>
      </div>
      <div className={styles.podBody}>
        <div className={styles.problemsGrid}>
          {relatedList.map((item, idx) => (
            <button
              key={idx}
              type="button"
              className={styles.problemCard}
              onClick={() => onSelectEquation(item.equation)}
              title={lang === 'vi' ? `Giải: ${item.equation}` : `Solve: ${item.equation}`}
              data-testid={`related-problem-btn-${idx}`}
            >
              <div className={styles.problemTop}>
                <div className={styles.problemLatex}>
                  <MathLatex latex={item.latex} />
                </div>
                <FontAwesomeIcon icon={faArrowRight} className={styles.actionArrow} />
              </div>
              <div className={styles.problemNote}>
                {lang === 'vi' ? item.labelVi : item.labelEn}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
