/**
 * Math Palette Capability Architecture.
 * 
 * Defines structured button groups and supported categories for assisted mathematical entry
 * matching modern WolframAlpha mathematical input palettes.
 */

export type MathCapability =
  | 'ALGEBRA_BASIC'
  | 'QUADRATIC'
  | 'FRACTION'
  | 'POWER'
  | 'DIGITS'
  | 'EDITING'
  | 'TRIG_FUTURE'
  | 'CALCULUS_FUTURE';

export interface PaletteButtonDef {
  id: string;
  displayLabel: string;
  visualSnippet?: string;
  actionId: string;
  ariaKey: string;
  capability: MathCapability;
  isEnabled: boolean;
}

export interface PaletteCategoryDef {
  categoryId: string;
  symbol: string;
  titleKey: string;
  isEnabled: boolean;
  buttons: PaletteButtonDef[];
}

export const PALETTE_CATEGORIES: PaletteCategoryDef[] = [
  {
    categoryId: 'COMMON',
    symbol: '★',
    titleKey: 'cat_common',
    isEnabled: true,
    buttons: [
      { id: 'btn_c_frac', displayLabel: '□/□', actionId: 'FRACTION', ariaKey: 'aria_insert_fraction', capability: 'FRACTION', isEnabled: true },
      { id: 'btn_c_pow', displayLabel: '□^□', actionId: 'POWER', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_c_sq', displayLabel: 'x²', actionId: 'SQUARE', ariaKey: 'aria_insert_square', capability: 'QUADRATIC', isEnabled: true },
      { id: 'btn_c_x', displayLabel: 'x', actionId: 'VAR_X', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_c_sqrt', displayLabel: '√□', actionId: 'SQRT', ariaKey: 'aria_insert_square', capability: 'QUADRATIC', isEnabled: true },
      { id: 'btn_c_cubert', displayLabel: '³√□', actionId: 'CUBE_ROOT', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_c_nthrt', displayLabel: 'ⁿ√□', actionId: 'NTH_ROOT', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_c_deriv', displayLabel: 'd/d□', actionId: 'DERIVATIVE', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_deriv2', displayLabel: 'd²/d□²', actionId: 'SECOND_DERIVATIVE', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_int', displayLabel: '∫□', actionId: 'INTEGRAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_defint', displayLabel: '∫_□^□', actionId: 'DEF_INTEGRAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_sum', displayLabel: '∑', actionId: 'SUM', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_lim', displayLabel: 'lim □→□', actionId: 'LIMIT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_c_vec', displayLabel: '[□,□,□]', actionId: 'VECTOR', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_c_mat', displayLabel: '(▦)', actionId: 'MATRIX', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_c_clear', displayLabel: 'C', actionId: 'CLEAR', ariaKey: 'aria_clear_all', capability: 'EDITING', isEnabled: true },
    ],
  },
  {
    categoryId: 'ALGEBRA',
    symbol: '√',
    titleKey: 'cat_algebra',
    isEnabled: true,
    buttons: [
      { id: 'btn_a_frac', displayLabel: '□/□', actionId: 'FRACTION', ariaKey: 'aria_insert_fraction', capability: 'FRACTION', isEnabled: true },
      { id: 'btn_a_x', displayLabel: 'x', actionId: 'VAR_X', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_y', displayLabel: 'y', actionId: 'VAR_Y', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_sq', displayLabel: '□²', actionId: 'SQUARE', ariaKey: 'aria_insert_square', capability: 'QUADRATIC', isEnabled: true },
      { id: 'btn_a_pow', displayLabel: '□^□', actionId: 'POWER', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_a_sqrt', displayLabel: '√□', actionId: 'SQRT', ariaKey: 'aria_insert_square', capability: 'QUADRATIC', isEnabled: true },
      { id: 'btn_a_cubert', displayLabel: '³√□', actionId: 'CUBE_ROOT', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_a_nthrt', displayLabel: 'ⁿ√□', actionId: 'NTH_ROOT', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_a_inf', displayLabel: '∞', actionId: 'INFINITY', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_ninf', displayLabel: '-∞', actionId: 'NEG_INFINITY', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_pi', displayLabel: 'π', actionId: 'PI', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_e', displayLabel: 'e', actionId: 'EXP_E', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_epow', displayLabel: 'e^□', actionId: 'EXP_POW', ariaKey: 'aria_insert_power', capability: 'POWER', isEnabled: true },
      { id: 'btn_a_ln', displayLabel: 'ln(□)', actionId: 'LN', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_logb', displayLabel: 'log_□(□)', actionId: 'LOG_BASE', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_log10', displayLabel: 'log₁₀(□)', actionId: 'LOG', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_abs', displayLabel: '|□|', actionId: 'ABS', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_le', displayLabel: '□ ≤ □', actionId: 'LE', ariaKey: 'aria_insert_equals', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_ge', displayLabel: '□ ≥ □', actionId: 'GE', ariaKey: 'aria_insert_equals', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_ne', displayLabel: '□ ≠ □', actionId: 'NE', ariaKey: 'aria_insert_equals', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_a_clear', displayLabel: 'C', actionId: 'CLEAR', ariaKey: 'aria_clear_all', capability: 'EDITING', isEnabled: true },
    ],
  },
  {
    categoryId: 'CALCULUS',
    symbol: '∂∫',
    titleKey: 'cat_calculus',
    isEnabled: true,
    buttons: [
      { id: 'btn_calc_d', displayLabel: 'd/d□', actionId: 'DERIVATIVE', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_d2', displayLabel: 'd²/d□²', actionId: 'SECOND_DERIVATIVE', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_part', displayLabel: '∂/∂□', actionId: 'PARTIAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_part2', displayLabel: '∂²/∂□²', actionId: 'SECOND_PARTIAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_partmix', displayLabel: '∂²/∂□∂□', actionId: 'MIXED_PARTIAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_int', displayLabel: '∫□', actionId: 'INTEGRAL', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_iint', displayLabel: '∬□', actionId: 'DOUBLE_INT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_iiint', displayLabel: '∭□', actionId: 'TRIPLE_INT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_oint', displayLabel: '∮□', actionId: 'CONTOUR_INT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_oiint', displayLabel: '∯□', actionId: 'SURFACE_INT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_sum', displayLabel: '∑', actionId: 'SUM', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_prod', displayLabel: '∏', actionId: 'PRODUCT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_lim', displayLabel: 'lim □→□', actionId: 'LIMIT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_limneg', displayLabel: 'lim □→□⁻', actionId: 'LIMIT_LEFT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_limpos', displayLabel: 'lim □→□⁺', actionId: 'LIMIT_RIGHT', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_theta', displayLabel: 'θ(□)', actionId: 'STEP_FUNC', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_delta', displayLabel: 'δ(□)', actionId: 'DELTA_FUNC', ariaKey: 'aria_insert_power', capability: 'CALCULUS_FUTURE', isEnabled: true },
      { id: 'btn_calc_m2', displayLabel: '[▦ 2x2]', actionId: 'MAT_2X2', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_calc_m3', displayLabel: '[▦ 3x3]', actionId: 'MAT_3X3', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
    ],
  },
  {
    categoryId: 'MATRICES',
    symbol: '(::)',
    titleKey: 'cat_matrices',
    isEnabled: true,
    buttons: [
      { id: 'btn_mat_vec', displayLabel: '[x, y]', actionId: 'VECTOR', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_mat_mat', displayLabel: '[[a,b],[c,d]]', actionId: 'MATRIX', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
    ],
  },
  {
    categoryId: 'PLOTS',
    symbol: '∿',
    titleKey: 'cat_plots',
    isEnabled: true,
    buttons: [
      { id: 'btn_p_plot', displayLabel: 'plot', actionId: 'PLOT', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_p_sin', displayLabel: 'sin', actionId: 'SIN', ariaKey: 'aria_insert_power', capability: 'TRIG_FUTURE', isEnabled: true },
      { id: 'btn_p_cos', displayLabel: 'cos', actionId: 'COS', ariaKey: 'aria_insert_power', capability: 'TRIG_FUTURE', isEnabled: true },
      { id: 'btn_p_tan', displayLabel: 'tan', actionId: 'TAN', ariaKey: 'aria_insert_power', capability: 'TRIG_FUTURE', isEnabled: true },
      { id: 'btn_p_log', displayLabel: 'log', actionId: 'LOG', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_p_ln', displayLabel: 'ln', actionId: 'LN', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_p_exp', displayLabel: 'exp', actionId: 'EXP', ariaKey: 'aria_insert_power', capability: 'ALGEBRA_BASIC', isEnabled: true },
    ],
  },
  {
    categoryId: 'GREEK',
    symbol: 'α_ω',
    titleKey: 'cat_greek',
    isEnabled: true,
    buttons: [
      { id: 'btn_g_alpha', displayLabel: 'α', actionId: 'ALPHA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_beta', displayLabel: 'β', actionId: 'BETA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_gamma', displayLabel: 'γ', actionId: 'GAMMA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_delta', displayLabel: 'δ', actionId: 'DELTA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_theta', displayLabel: 'θ', actionId: 'THETA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_lambda', displayLabel: 'λ', actionId: 'LAMBDA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_mu', displayLabel: 'μ', actionId: 'MU', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_pi', displayLabel: 'π', actionId: 'PI', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_sigma', displayLabel: 'σ', actionId: 'SIGMA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
      { id: 'btn_g_omega', displayLabel: 'ω', actionId: 'OMEGA', ariaKey: 'aria_insert_var_x', capability: 'ALGEBRA_BASIC', isEnabled: true },
    ],
  },
  {
    categoryId: 'MORE',
    symbol: '···',
    titleKey: 'cat_more',
    isEnabled: true,
    buttons: [
      { id: 'btn_d_7', displayLabel: '7', actionId: 'DIGIT_7', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_8', displayLabel: '8', actionId: 'DIGIT_8', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_9', displayLabel: '9', actionId: 'DIGIT_9', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_4', displayLabel: '4', actionId: 'DIGIT_4', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_5', displayLabel: '5', actionId: 'DIGIT_5', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_6', displayLabel: '6', actionId: 'DIGIT_6', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_1', displayLabel: '1', actionId: 'DIGIT_1', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_2', displayLabel: '2', actionId: 'DIGIT_2', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_3', displayLabel: '3', actionId: 'DIGIT_3', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_0', displayLabel: '0', actionId: 'DIGIT_0', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_dot', displayLabel: '.', actionId: 'DOT', ariaKey: 'aria_insert_dot', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_d_bs', displayLabel: '⌫', actionId: 'BACKSPACE', ariaKey: 'aria_backspace', capability: 'EDITING', isEnabled: true },
      { id: 'btn_d_c', displayLabel: 'C', actionId: 'CLEAR', ariaKey: 'aria_clear_all', capability: 'EDITING', isEnabled: true },
    ],
  },
];

// Retain PALETTE_GROUPS alias for existing unit tests
export const PALETTE_GROUPS = PALETTE_CATEGORIES.map((cat) => ({
  groupId: `GROUP_${cat.categoryId}`,
  titleKey: cat.titleKey,
  capability: 'QUADRATIC' as MathCapability,
  isEnabled: cat.isEnabled,
  buttons: cat.buttons,
}));
