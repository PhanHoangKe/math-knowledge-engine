import type { TranslationKey } from './vi';
import type {
  SolutionOutcome,
  MathematicalApplicability,
  ExecutionAvailability,
  PedagogicalRecommendation,
  VerificationCapability,
  VerificationOutcome,
  NoExecutionReasonCode,
} from '../api/contract';

export const SOLUTION_OUTCOME_I18N: Record<SolutionOutcome, TranslationKey> = {
  TWO_DISTINCT_REAL_ROOTS: 'enum_out_TWO_DISTINCT_REAL_ROOTS',
  ONE_REPEATED_REAL_ROOT: 'enum_out_ONE_REPEATED_REAL_ROOT',
  NO_REAL_ROOTS: 'enum_out_NO_REAL_ROOTS',
  ONE_REAL_LINEAR_ROOT: 'enum_out_ONE_REAL_LINEAR_ROOT',
  INFINITE_REAL_SOLUTIONS: 'enum_out_INFINITE_REAL_SOLUTIONS',
  NO_REAL_SOLUTIONS_CONTRADICTION: 'enum_out_NO_REAL_SOLUTIONS_CONTRADICTION',
};

export const MATHEMATICAL_APPLICABILITY_I18N: Record<MathematicalApplicability, TranslationKey> = {
  APPLICABLE: 'enum_app_APPLICABLE',
  NOT_APPLICABLE: 'enum_app_NOT_APPLICABLE',
  UNKNOWN: 'enum_app_UNKNOWN',
};

export const EXECUTION_AVAILABILITY_I18N: Record<ExecutionAvailability, TranslationKey> = {
  AVAILABLE: 'enum_exec_AVAILABLE',
  UNAVAILABLE: 'enum_exec_UNAVAILABLE',
};

export const PEDAGOGICAL_RECOMMENDATION_I18N: Record<PedagogicalRecommendation, TranslationKey> = {
  RECOMMENDED: 'enum_rec_RECOMMENDED',
  NEUTRAL: 'enum_rec_NEUTRAL',
  DISCOURAGED: 'enum_rec_DISCOURAGED',
};

export const VERIFICATION_CAPABILITY_I18N: Record<VerificationCapability, TranslationKey> = {
  HOST_VERIFIABLE: 'enum_ver_HOST_VERIFIABLE',
  UNVERIFIED: 'enum_ver_UNVERIFIED',
  NOT_APPLICABLE: 'enum_ver_NOT_APPLICABLE',
};

export const VERIFICATION_OUTCOME_I18N: Record<VerificationOutcome, TranslationKey> = {
  VERIFIED_COMPLETE: 'enum_ver_out_VERIFIED_COMPLETE',
  VERIFICATION_FAILED: 'enum_ver_out_VERIFICATION_FAILED',
  NOT_APPLICABLE: 'enum_ver_out_NOT_APPLICABLE',
};

export const NO_EXECUTION_REASON_I18N: Record<NoExecutionReasonCode, TranslationKey> = {
  METHOD_NOT_EXECUTABLE: 'lbl_reason_METHOD_NOT_EXECUTABLE',
  METHOD_NOT_APPLICABLE: 'lbl_reason_METHOD_NOT_APPLICABLE',
  DEGENERATE_EXACT_SOLUTION: 'lbl_reason_DEGENERATE_EXACT_SOLUTION',
};
