"""MKE MVP V1 — S3 Graph Data Contracts.

Defines the Python Single Source of Truth (SSOT) data models for Knowledge Graph,
Prerequisite DAG, and Reactive Dependency DAG representations in MKE S3.
All models enforce Pydantic v2 strict validation, immutability (frozen=True),
and extra field rejection.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

from mke_product.knowledge.schemas import LocalizedText


class GraphNodeType(str, Enum):
    """Categorical taxonomy for nodes in MKE graph representations."""

    CONCEPT = "CONCEPT"
    METHOD = "METHOD"
    FORMULA = "FORMULA"
    THEOREM = "THEOREM"
    PARAMETER = "PARAMETER"
    COMPUTATION = "COMPUTATION"


class GraphEdgeType(str, Enum):
    """Semantic relation types for edges in MKE graph representations."""

    REQUIRES = "REQUIRES"
    USES_FORMULA = "USES_FORMULA"
    USES_THEOREM = "USES_THEOREM"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    SPECIAL_CASE_OF = "SPECIAL_CASE_OF"
    RELATED_TO = "RELATED_TO"
    LEARN_BEFORE = "LEARN_BEFORE"
    COMPUTATIONAL_DEPENDENCY = "COMPUTATIONAL_DEPENDENCY"


class GraphKind(str, Enum):
    """Structural classification of graph models."""

    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    PREREQUISITE_DAG = "PREREQUISITE_DAG"
    REACTIVE_DEPENDENCY_DAG = "REACTIVE_DEPENDENCY_DAG"


class GraphNode(BaseModel):
    """Immutable graph node with strict typing and localized label."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    node_id: str = Field(..., description="Deterministic unique prefixed identifier, e.g. 'concept:concept_discriminant'")
    node_type: GraphNodeType = Field(..., description="Categorical node type")
    label: LocalizedText = Field(..., description="Bilingual display label")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata properties")


class GraphEdge(BaseModel):
    """Immutable directed or canonical symmetric relationship between graph nodes."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    edge_type: GraphEdgeType = Field(..., description="Semantic relation type")
    is_symmetric: bool = Field(default=False, description="Whether the edge represents a symmetric bidirectional relationship")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata properties")


class GraphModel(BaseModel):
    """Top-level container for a validated mathematical knowledge graph or DAG."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )

    graph_id: str = Field(..., description="Deterministic unique graph identifier")
    graph_kind: GraphKind = Field(..., description="Graph category")
    title: LocalizedText = Field(..., description="Bilingual title of the graph")
    nodes: List[GraphNode] = Field(default_factory=list, description="Ordered list of graph nodes")
    edges: List[GraphEdge] = Field(default_factory=list, description="Ordered list of graph edges")
    is_acyclic: bool = Field(..., description="Whether the graph is guaranteed to be a Directed Acyclic Graph")
    version: str = Field(default="1.0.0", description="Graph contract version")
