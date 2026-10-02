"""MKE Product Knowledge Layer.

Provides static pedagogical knowledge models, dataset loaders,
in-memory repository, and graph exporters for mathematical methods,
concepts, formulas, theorems, and reactive dependency projections.
"""

from mke_product.knowledge.graph_models import (
    GraphEdge,
    GraphEdgeType,
    GraphKind,
    GraphModel,
    GraphNode,
    GraphNodeType,
)
from mke_product.knowledge.graph_service import (
    KnowledgeGraphService,
    UnsupportedReactiveProjectionError,
)
from mke_product.knowledge.loader import (
    compute_dataset_content_hash,
    load_concepts,
    load_formulas,
    load_knowledge_dataset,
    load_methods,
    load_provenances,
    load_theorems,
    validate_knowledge_dataset,
)
from mke_product.knowledge.repository import (
    EntityNotFoundError,
    KnowledgeRepository,
    KnowledgeRepositoryError,
    PrerequisiteCycleError,
)
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    CurriculumMappingStatus,
    CurriculumRef,
    FormulaKnowledge,
    LocalizedText,
    MethodKnowledge,
    ProvenanceStatus,
    SourceProvenance,
    TheoremKnowledge,
)

__all__ = [
    "LocalizedText",
    "CurriculumMappingStatus",
    "CurriculumRef",
    "ProvenanceStatus",
    "SourceProvenance",
    "FormulaKnowledge",
    "TheoremKnowledge",
    "ConceptKnowledge",
    "MethodKnowledge",
    "load_provenances",
    "load_formulas",
    "load_theorems",
    "load_concepts",
    "load_methods",
    "load_knowledge_dataset",
    "validate_knowledge_dataset",
    "compute_dataset_content_hash",
    "GraphNodeType",
    "GraphEdgeType",
    "GraphKind",
    "GraphNode",
    "GraphEdge",
    "GraphModel",
    "KnowledgeRepository",
    "KnowledgeRepositoryError",
    "EntityNotFoundError",
    "PrerequisiteCycleError",
    "KnowledgeGraphService",
    "UnsupportedReactiveProjectionError",
]
