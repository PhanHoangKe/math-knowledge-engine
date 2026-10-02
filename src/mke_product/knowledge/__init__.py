"""MKE Product Knowledge Layer.

Provides static pedagogical knowledge models, dataset loaders,
and referential integrity verification for mathematical methods, concepts,
formulas, theorems, and source provenances.
"""

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
]
