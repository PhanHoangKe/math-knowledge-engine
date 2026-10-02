/**
 * MKE MVP V1 — API Type Contract Module.
 * 
 * Provides type aliases for frontend consumption derived strictly
 * from the auto-generated backend OpenAPI TypeScript contracts.
 * 
 * DO NOT manually redefine DTO fields here; all structures derive from api.generated.ts.
 */

import type { paths, operations, components } from '../types/api.generated';

// --- Paths & Operations ---
export type ApiPaths = paths;
export type SolveOperation = operations['solve_algebra_v1'];
export type HealthOperation = operations['health_v1'];

// --- Solve Request Intake Types ---
export type SolveRequest = components['schemas']['SolveRequest'];
export type RawEquationInput = components['schemas']['RawEquationInput'];
export type CanonicalCoefficientInput = components['schemas']['CanonicalCoefficientInput'];
export type InputPayloadUnion = SolveRequest['input_payload'];

// --- Solve Response Types ---
export type SolveResponse200 = SolveOperation['responses']['200']['content']['application/json'];
export type SolvedResponse = components['schemas']['SolvedResponse'];
export type AnalyzedNoExecutionResponse = components['schemas']['AnalyzedNoExecutionResponse'];
export type ApplicationErrorResponse = components['schemas']['ErrorResponse'];

// --- Transport Errors ---
export type TransportErrorResponse = components['schemas']['TransportErrorResponse'];
export type TransportErrorCode = components['schemas']['TransportErrorCode'];

// --- Problem Views & Classification ---
export type CanonicalQuadraticProblemView = components['schemas']['CanonicalQuadraticProblemView'];
export type CanonicalDegenerateProblemView = components['schemas']['CanonicalDegenerateProblemView'];
export type CanonicalProblemViewUnion = SolvedResponse['problem'] | AnalyzedNoExecutionResponse['problem'];
export type QuadraticDiscriminant = components['schemas']['QuadraticDiscriminant'];

// --- Solution, Trace & Certificate Types ---
export type VerifiedSolutionView = components['schemas']['VerifiedSolutionView'];
export type DegenerateSolutionView = components['schemas']['DegenerateSolutionView'];
export type RealRootValue = components['schemas']['RealRootValue'];
export type SolutionOutcome = components['schemas']['SolutionOutcome'];
export type SolutionRootType = components['schemas']['SolutionRootType'];
export type SolutionTrace = components['schemas']['SolutionTrace'];
export type SolutionStep = components['schemas']['SolutionStep'];
export type VerificationCertificate = components['schemas']['VerificationCertificate'];
export type VerificationOutcome = components['schemas']['VerificationOutcome'];

// --- Method Assessment Profile ---
export type MethodOptionView = components['schemas']['MethodOptionView'];
export type PrerequisiteStatus = components['schemas']['PrerequisiteStatus'];
export type MathematicalApplicability = components['schemas']['MathematicalApplicability'];
export type ExecutionAvailability = components['schemas']['ExecutionAvailability'];
export type PedagogicalRecommendation = components['schemas']['PedagogicalRecommendation'];
export type SupportStatus = components['schemas']['SupportStatus'];
export type VerificationCapability = components['schemas']['VerificationCapability'];

// --- Reason & Error Codes ---
export type NoExecutionReasonCode = components['schemas']['NoExecutionReasonCode'];
export type ApplicationErrorCode = components['schemas']['ApplicationErrorCode'];
export type Span = components['schemas']['Span'];

// --- Rational Numbers & Health ---
export type RationalFraction = components['schemas']['RationalFraction'];
export type HealthResponse = components['schemas']['HealthResponse'];
