"""Enumerations for Math Knowledge Engine (MKE) Verification Foundation."""

from enum import Enum


class MethodAdmissibility(str, Enum):
    """Admissibility status of a mathematical method for a given problem instance."""
    APPLICABLE = "APPLICABLE"
    APPLICABLE_WITH_OBLIGATIONS = "APPLICABLE_WITH_OBLIGATIONS"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ObligationStatus(str, Enum):
    """Status of a mathematical proof obligation."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


class TransferValidity(str, Enum):
    """Validity status of transferring a solution from a source problem to a target."""
    REINSTANTIATED_VALID = "REINSTANTIATED_VALID"
    UNSAFE_COPY = "UNSAFE_COPY"
    INAPPLICABLE_INSTANCE = "INAPPLICABLE_INSTANCE"
    UNRESOLVED = "UNRESOLVED"


class SolutionProofStatus(str, Enum):
    """Rigorous evaluation of solution set soundness and completeness."""
    SOUND_AND_COMPLETE_IN_SCOPE = "SOUND_AND_COMPLETE_IN_SCOPE"
    SOUND_PARTIAL = "SOUND_PARTIAL"
    REFUTED = "REFUTED"
    UNDETERMINED = "UNDETERMINED"


class ObligationId(str, Enum):
    """Standardized identifiers for proof obligations."""
    ORIGINAL_DOMAIN = "ORIGINAL_DOMAIN"
    NONZERO_GUARD = "NONZERO_GUARD"
    PARAMETER_BRANCH = "PARAMETER_BRANCH"
    TRANSFORMATION_EQUIVALENCE = "TRANSFORMATION_EQUIVALENCE"
    SIGN_CONSTRAINT = "SIGN_CONSTRAINT"
    SOURCE_RESULT_NONTRANSFER = "SOURCE_RESULT_NONTRANSFER"
    ROOT_SUBSTITUTION = "ROOT_SUBSTITUTION"
    COMPLETENESS = "COMPLETENESS"


class MethodId(str, Enum):
    """Stable identifiers for supported mathematical methods."""
    M1_LINEAR_EQUATION = "M1:LINEAR_EQUATION"
    M2_QUADRATIC_FORMULA = "M2:QUADRATIC_FORMULA"
    M3_FACTORIZATION = "M3:FACTORIZATION"
    M4_RATIONAL_EQUATION = "M4:RATIONAL_EQUATION"
    M5_BIQUADRATIC_SUBSTITUTION = "M5:BIQUADRATIC_SUBSTITUTION"


class Split(str, Enum):
    """Dataset partition for research reproducibility."""
    DEV = "DEV"
    VALIDATION = "VALIDATION"
    TEST = "TEST"
