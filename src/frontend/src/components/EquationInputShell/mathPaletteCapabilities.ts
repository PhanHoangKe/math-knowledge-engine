/**
 * Math Palette Capability Architecture.
 * 
 * Defines structured button groups and supported capabilities for assisted mathematical entry.
 * Designed for modular capability expansion in future stages (e.g. TRIG, CALCULUS)
 * while strictly enabling only accepted MVP V1 capabilities today.
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

export interface PaletteGroupDef {
  groupId: string;
  titleKey: string;
  capability: MathCapability;
  isEnabled: boolean;
  buttons: PaletteButtonDef[];
}

export const PALETTE_GROUPS: PaletteGroupDef[] = [
  {
    groupId: 'GROUP_VARIABLES_POWERS',
    titleKey: 'palette_group_powers',
    capability: 'QUADRATIC',
    isEnabled: true,
    buttons: [
      {
        id: 'btn_var_x',
        displayLabel: 'x',
        actionId: 'VAR_X',
        ariaKey: 'aria_insert_var_x',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_square',
        displayLabel: 'x²',
        actionId: 'SQUARE',
        ariaKey: 'aria_insert_square',
        capability: 'QUADRATIC',
        isEnabled: true,
      },
      {
        id: 'btn_power',
        displayLabel: 'xⁿ',
        actionId: 'POWER',
        ariaKey: 'aria_insert_power',
        capability: 'POWER',
        isEnabled: true,
      },
      {
        id: 'btn_fraction',
        displayLabel: 'a/b',
        actionId: 'FRACTION',
        ariaKey: 'aria_insert_fraction',
        capability: 'FRACTION',
        isEnabled: true,
      },
    ],
  },
  {
    groupId: 'GROUP_OPERATORS',
    titleKey: 'palette_group_basic',
    capability: 'ALGEBRA_BASIC',
    isEnabled: true,
    buttons: [
      {
        id: 'btn_plus',
        displayLabel: '+',
        actionId: 'PLUS',
        ariaKey: 'aria_insert_plus',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_minus',
        displayLabel: '−',
        actionId: 'MINUS',
        ariaKey: 'aria_insert_minus',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_multiply',
        displayLabel: '×',
        actionId: 'MULTIPLY',
        ariaKey: 'aria_insert_multiply',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_divide',
        displayLabel: '÷',
        actionId: 'DIVIDE',
        ariaKey: 'aria_insert_divide',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_equals',
        displayLabel: '=',
        actionId: 'EQUALS',
        ariaKey: 'aria_insert_equals',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_lparen',
        displayLabel: '(',
        actionId: 'LPAREN',
        ariaKey: 'aria_insert_lparen',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
      {
        id: 'btn_rparen',
        displayLabel: ')',
        actionId: 'RPAREN',
        ariaKey: 'aria_insert_rparen',
        capability: 'ALGEBRA_BASIC',
        isEnabled: true,
      },
    ],
  },
  {
    groupId: 'GROUP_DIGITS',
    titleKey: 'palette_group_digits',
    capability: 'DIGITS',
    isEnabled: true,
    buttons: [
      { id: 'btn_digit_7', displayLabel: '7', actionId: 'DIGIT_7', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_8', displayLabel: '8', actionId: 'DIGIT_8', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_9', displayLabel: '9', actionId: 'DIGIT_9', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_4', displayLabel: '4', actionId: 'DIGIT_4', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_5', displayLabel: '5', actionId: 'DIGIT_5', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_6', displayLabel: '6', actionId: 'DIGIT_6', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_1', displayLabel: '1', actionId: 'DIGIT_1', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_2', displayLabel: '2', actionId: 'DIGIT_2', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_3', displayLabel: '3', actionId: 'DIGIT_3', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_digit_0', displayLabel: '0', actionId: 'DIGIT_0', ariaKey: 'aria_insert_digit', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_dot', displayLabel: '.', actionId: 'DOT', ariaKey: 'aria_insert_dot', capability: 'DIGITS', isEnabled: true },
      { id: 'btn_backspace', displayLabel: '⌫', actionId: 'BACKSPACE', ariaKey: 'aria_backspace', capability: 'EDITING', isEnabled: true },
      { id: 'btn_clear', displayLabel: 'C', actionId: 'CLEAR', ariaKey: 'aria_clear_all', capability: 'EDITING', isEnabled: true },
    ],
  },
];
