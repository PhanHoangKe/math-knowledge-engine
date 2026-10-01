"""MKE MVP V1 — Schema Versioning & JSON Schema Generation.

Provides deterministic JSON Schema export generated directly from the
Python Pydantic v2 domain models (SSOT).
"""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import TypeAdapter

from mke_product.domain.models import (
    Assumption,
    DegenerateEquationIR,
    DependencyNode,
    EquationClassificationType,
    GeometricPredicate,
    GeometricPrimitive,
    GeometricRelation,
    GeometryProblemIR,
    MathematicalApplicability,
    MethodAssessment,
    MethodDefinition,
    PedagogicalRecommendation,
    PrerequisiteStatus,
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

SCHEMA_VERSION: str = "1.0.0"


def export_mvp_v1_json_schema() -> Dict[str, Any]:
    """Generate the complete JSON Schema definition for MKE MVP V1 domain entities."""
    models_to_export = [
        ProblemIR,
        QuadraticProblemIR,
        DegenerateEquationIR,
        GeometryProblemIR,
        MethodDefinition,
        MethodAssessment,
        SolutionTrace,
        ProofTrace,
        VerificationCertificate,
        DependencyNode,
    ]

    definitions: Dict[str, Any] = {}
    for model in models_to_export:
        schema = model.model_json_schema()
        definitions[model.__name__] = schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MKE_MVP_V1_Domain_Schema",
        "version": SCHEMA_VERSION,
        "description": "Deterministic JSON Schema for MKE MVP V1 Math Knowledge Engine Domain Core",
        "definitions": definitions,
    }


def export_mvp_v1_json_schema_str(indent: int = 2) -> str:
    """Return formatted JSON string of the complete domain schema."""
    schema = export_mvp_v1_json_schema()
    return json.dumps(schema, indent=indent, sort_keys=True)
