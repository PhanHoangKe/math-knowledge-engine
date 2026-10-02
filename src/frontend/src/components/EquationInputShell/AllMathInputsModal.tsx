import React from 'react';
import { usePreferences } from '../../state/preferences';
import styles from './AllMathInputsModal.module.css';

export interface AllMathInputsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAction: (actionId: string) => void;
}

interface MathGroup {
  id: string;
  titleKey: string;
  buttons: Array<{
    label: string;
    actionId: string;
    isTemplate?: boolean;
  }>;
}

export const AllMathInputsModal: React.FC<AllMathInputsModalProps> = ({
  isOpen,
  onClose,
  onSelectAction,
}) => {
  const { t } = usePreferences();

  if (!isOpen) return null;

  const groups: MathGroup[] = [
    {
      id: 'basic',
      titleKey: 'modal_group_basic',
      buttons: [
        { label: '□/□', actionId: 'FRACTION', isTemplate: true },
        { label: '□²', actionId: 'SQUARE', isTemplate: true },
        { label: '□^□', actionId: 'POWER', isTemplate: true },
        { label: '√□', actionId: 'SQRT', isTemplate: true },
        { label: '³√□', actionId: 'CUBE_ROOT', isTemplate: true },
        { label: 'ⁿ√□', actionId: 'NTH_ROOT', isTemplate: true },
        { label: '∞', actionId: 'INFINITY' },
        { label: '-∞', actionId: 'NEG_INFINITY' },
        { label: 'π', actionId: 'PI' },
        { label: 'e', actionId: 'EXP_E' },
        { label: 'e^□', actionId: 'EXP_POW', isTemplate: true },
        { label: 'ln(□)', actionId: 'LN', isTemplate: true },
        { label: 'log_□(□)', actionId: 'LOG_BASE', isTemplate: true },
        { label: 'log₁₀(□)', actionId: 'LOG', isTemplate: true },
        { label: '|□|', actionId: 'ABS', isTemplate: true },
        { label: '□ ≤ □', actionId: 'LE', isTemplate: true },
        { label: '□ ≥ □', actionId: 'GE', isTemplate: true },
        { label: '□ ≠ □', actionId: 'NE', isTemplate: true },
      ],
    },
    {
      id: 'calculus',
      titleKey: 'modal_group_calculus',
      buttons: [
        { label: 'd/d□', actionId: 'DERIVATIVE', isTemplate: true },
        { label: 'd²/d□²', actionId: 'SECOND_DERIVATIVE', isTemplate: true },
        { label: '∂/∂□', actionId: 'PARTIAL', isTemplate: true },
        { label: '∂²/∂□²', actionId: 'SECOND_PARTIAL', isTemplate: true },
        { label: '∂²/∂□∂□', actionId: 'MIXED_PARTIAL', isTemplate: true },
        { label: '∫□', actionId: 'INTEGRAL', isTemplate: true },
        { label: '∬□□', actionId: 'DOUBLE_INT', isTemplate: true },
        { label: '∭□□□', actionId: 'TRIPLE_INT', isTemplate: true },
        { label: '∫_□^□', actionId: 'DEF_INTEGRAL', isTemplate: true },
        { label: '∬_□^□', actionId: 'DEF_DOUBLE_INT', isTemplate: true },
        { label: '∭_□^□', actionId: 'DEF_TRIPLE_INT', isTemplate: true },
        { label: '∑_□^□', actionId: 'SUM', isTemplate: true },
        { label: '∏_□^□', actionId: 'PRODUCT', isTemplate: true },
        { label: 'lim □→□', actionId: 'LIMIT', isTemplate: true },
        { label: 'lim □→□⁻', actionId: 'LIMIT_LEFT', isTemplate: true },
        { label: 'lim □→□⁺', actionId: 'LIMIT_RIGHT', isTemplate: true },
        { label: 'lim □□→□□', actionId: 'LIMIT_MULTI', isTemplate: true },
        { label: 'θ(□)', actionId: 'STEP_FUNC', isTemplate: true },
        { label: 'δ(□)', actionId: 'DELTA_FUNC', isTemplate: true },
        { label: '[▦ 2x2]', actionId: 'MAT_2X2', isTemplate: true },
        { label: '[▦ 3x3]', actionId: 'MAT_3X3', isTemplate: true },
        { label: 'ℒ_□□', actionId: 'LAPLACE', isTemplate: true },
        { label: 'ℒ⁻¹_□□', actionId: 'INV_LAPLACE', isTemplate: true },
        { label: 'ℱ_□□', actionId: 'FOURIER', isTemplate: true },
        { label: 'ℱ⁻¹_□□', actionId: 'INV_FOURIER', isTemplate: true },
      ],
    },
    {
      id: 'matrices',
      titleKey: 'modal_group_matrices',
      buttons: [
        { label: '[□,□]', actionId: 'VEC_2', isTemplate: true },
        { label: '[□,□,□]', actionId: 'VEC_3', isTemplate: true },
        { label: '[□,□,□,□]', actionId: 'VEC_4', isTemplate: true },
        { label: '[□; □]', actionId: 'COL_2', isTemplate: true },
        { label: '[□; □; □]', actionId: 'COL_3', isTemplate: true },
        { label: '[□; □; □; □]', actionId: 'COL_4', isTemplate: true },
        { label: '(▦ 2x2)', actionId: 'MAT_2X2', isTemplate: true },
        { label: '(▦ 3x3)', actionId: 'MAT_3X3', isTemplate: true },
        { label: '(▦ 4x4)', actionId: 'MAT_4X4', isTemplate: true },
        { label: '(▦ 2x3)', actionId: 'MAT_2X3', isTemplate: true },
        { label: '(▦ 3x2)', actionId: 'MAT_3X2', isTemplate: true },
        { label: '(▦ matrix n)', actionId: 'MAT_N', isTemplate: true },
      ],
    },
    {
      id: 'trig',
      titleKey: 'modal_group_trig',
      buttons: [
        { label: 'π', actionId: 'PI' },
        { label: '°', actionId: 'DEGREE' },
        { label: 'rad', actionId: 'RADIAN' },
        { label: 'sin □', actionId: 'SIN', isTemplate: true },
        { label: 'cos □', actionId: 'COS', isTemplate: true },
        { label: 'tan □', actionId: 'TAN', isTemplate: true },
        { label: 'sec □', actionId: 'SEC', isTemplate: true },
        { label: 'csc □', actionId: 'CSC', isTemplate: true },
        { label: 'cot □', actionId: 'COT', isTemplate: true },
        { label: 'sin⁻¹□', actionId: 'ASIN', isTemplate: true },
        { label: 'cos⁻¹□', actionId: 'ACOS', isTemplate: true },
        { label: 'tan⁻¹□', actionId: 'ATAN', isTemplate: true },
        { label: 'sinh □', actionId: 'SINH', isTemplate: true },
        { label: 'cosh □', actionId: 'COSH', isTemplate: true },
        { label: 'tanh □', actionId: 'TANH', isTemplate: true },
        { label: 'sech □', actionId: 'SECH', isTemplate: true },
        { label: 'csch □', actionId: 'CSCH', isTemplate: true },
        { label: 'coth □', actionId: 'COTH', isTemplate: true },
        { label: 'sinh⁻¹□', actionId: 'ASINH', isTemplate: true },
        { label: 'cosh⁻¹□', actionId: 'ACOSH', isTemplate: true },
        { label: 'tanh⁻¹□', actionId: 'ATANH', isTemplate: true },
        { label: 'sech⁻¹□', actionId: 'ASECH', isTemplate: true },
        { label: 'csch⁻¹□', actionId: 'ACSCH', isTemplate: true },
        { label: 'coth⁻¹□', actionId: 'ACOTH', isTemplate: true },
      ],
    },
    {
      id: 'symbols',
      titleKey: 'modal_group_symbols',
      buttons: [
        { label: 'π', actionId: 'PI' },
        { label: '°', actionId: 'DEGREE' },
        { label: '∞', actionId: 'INFINITY' },
        { label: '∀', actionId: 'FOR_ALL' },
        { label: '∃', actionId: 'EXISTS' },
        { label: '∪', actionId: 'UNION' },
        { label: '∩', actionId: 'INTERSECT' },
        { label: '∇', actionId: 'NABLA' },
        { label: 'Δ', actionId: 'DELTA' },
        { label: 'α', actionId: 'ALPHA' },
        { label: 'β', actionId: 'BETA' },
        { label: 'γ', actionId: 'GAMMA' },
        { label: 'δ', actionId: 'DELTA_LOWER' },
        { label: 'ε', actionId: 'EPSILON' },
        { label: 'ζ', actionId: 'ZETA' },
        { label: 'η', actionId: 'ETA' },
        { label: 'θ', actionId: 'THETA' },
        { label: 'κ', actionId: 'KAPPA' },
        { label: 'λ', actionId: 'LAMBDA' },
        { label: 'μ', actionId: 'MU' },
        { label: 'ν', actionId: 'NU' },
        { label: 'ξ', actionId: 'XI' },
        { label: 'ρ', actionId: 'RHO' },
        { label: 'σ', actionId: 'SIGMA' },
        { label: 'τ', actionId: 'TAU' },
        { label: 'φ', actionId: 'PHI' },
        { label: 'χ', actionId: 'CHI' },
        { label: 'ψ', actionId: 'PSI' },
        { label: 'ω', actionId: 'OMEGA' },
        { label: 'Γ', actionId: 'GAMMA_CAP' },
        { label: 'Θ', actionId: 'THETA_CAP' },
        { label: 'Λ', actionId: 'LAMBDA_CAP' },
        { label: 'Ξ', actionId: 'XI_CAP' },
        { label: 'Υ', actionId: 'UPSILON_CAP' },
        { label: 'Φ', actionId: 'PHI_CAP' },
        { label: 'Ψ', actionId: 'PSI_CAP' },
        { label: 'Ω', actionId: 'OMEGA_CAP' },
        { label: '℧', actionId: 'MHO' },
        { label: 'Å', actionId: 'ANGSTROM' },
        { label: 'ℏ', actionId: 'HBAR' },
        { label: 'ℵ', actionId: 'ALEPH' },
        { label: '⇌', actionId: 'EQUILIBRIUM' },
        { label: '→', actionId: 'R_ARROW' },
        { label: '⊕', actionId: 'OPLUS' },
        { label: '⊙', actionId: 'ODOT' },
        { label: '≠', actionId: 'NE' },
        { label: '≥', actionId: 'GE' },
        { label: '≤', actionId: 'LE' },
      ],
    },
  ];

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>{t('all_math_inputs_title')}</h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label={t('close_modal_aria')}
          >
            ✕
          </button>
        </div>

        <div className={styles.groupsContainer}>
          {groups.map((grp) => (
            <div key={grp.id} className={styles.groupSection}>
              <h3 className={styles.groupTitle}>{t(grp.titleKey as any)}</h3>
              <div className={styles.buttonsGrid}>
                {grp.buttons.map((btn, idx) => (
                  <button
                    key={`${btn.actionId}_${idx}`}
                    type="button"
                    className={styles.mathKeyTile}
                    onClick={() => {
                      onSelectAction(btn.actionId);
                    }}
                    title={btn.label}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
