"""MKE MVP V1 Domain Core Package.

Canonical Single Source of Truth (SSOT) domain models, exact arithmetic kernel,
deterministic Method Registry, Host Independent Verifier, and reactive DAG engine.
"""

from mke_product.domain.models import (
    Assumption,
    DegenerateEquationIR,
    DependencyNode,
    EquationClassificationType,
    ExecutionAvailability,
    GeometricPredicate,
    GeometricPrimitive,
    GeometricRelation,
    GeometryProblemIR,
    MathematicalApplicability,
    MethodAssessment,
    MethodDefinition,
    PedagogicalRecommendation,
    PrerequisiteStatus,
    PrimitiveType,
    ProblemCategory,
    ProblemIR,
    ProofOutcome,
    ProofStep,
    ProofTrace,
    QuadraticDiscriminant,
    QuadraticProblemIR,
    RationalFraction,
    RealRootValue,
    SolutionOutcome,
    SolutionRootType,
    SolutionStep,
    SolutionTrace,
    SupportStatus,
    VerificationCapability,
    VerificationCertificate,
    VerificationOutcome,
)
from mke_product.domain.exact import (
    classify_univariate_degree2,
    compute_quadratic_discriminant,
    decompose_integer_squarefree,
    decompose_rational_squarefree,
    solve_exact_quadratic,
)
from mke_product.domain.registry import MethodRegistry
from mke_product.domain.verifier import HostIndependentVerifier
from mke_product.domain.dag import (
    CycleDetectedError,
    DependencyGraph,
    NodeNotFoundError,
    build_quadratic_workspace_dag,
)
from mke_product.domain.identity import (
    compute_computation_cache_identity,
    compute_engine_config_identity,
    compute_semantic_quadratic_identity,
)
from mke_product.domain.schema import (
    SCHEMA_VERSION,
    export_mvp_v1_json_schema,
    export_mvp_v1_json_schema_str,
)

__all__ = [
    # Taxonomy & Enums
    "ProblemCategory",
    "EquationClassificationType",
    "SolutionOutcome",
    "SolutionRootType",
    "MathematicalApplicability",
    "SupportStatus",
    "ExecutionAvailability",
    "PedagogicalRecommendation",
    "VerificationCapability",
    "VerificationOutcome",
    "PrimitiveType",
    "GeometricPredicate",
    "ProofOutcome",
    # Domain Models
    "RationalFraction",
    "QuadraticDiscriminant",
    "RealRootValue",
    "Assumption",
    "ProblemIR",
    "QuadraticProblemIR",
    "DegenerateEquationIR",
    "PrerequisiteStatus",
    "MethodDefinition",
    "MethodAssessment",
    "SolutionStep",
    "SolutionTrace",
    "GeometricPrimitive",
    "GeometricRelation",
    "GeometryProblemIR",
    "ProofStep",
    "ProofTrace",
    "VerificationCertificate",
    "DependencyNode",
    # Exact Arithmetic
    "decompose_integer_squarefree",
    "decompose_rational_squarefree",
    "compute_quadratic_discriminant",
    "classify_univariate_degree2",
    "solve_exact_quadratic",
    # Method Registry
    "MethodRegistry",
    # Verifier
    "HostIndependentVerifier",
    # DAG Engine
    "CycleDetectedError",
    "DependencyGraph",
    "NodeNotFoundError",
    "build_quadratic_workspace_dag",
    # Identity & Hashing
    "compute_semantic_quadratic_identity",
    "compute_engine_config_identity",
    "compute_computation_cache_identity",
    # Schema Versioning
    "SCHEMA_VERSION",
    "export_mvp_v1_json_schema",
    "export_mvp_v1_json_schema_str",
]
