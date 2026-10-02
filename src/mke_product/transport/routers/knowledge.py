"""Versioned Static Knowledge REST API router for MKE MVP V1."""

from functools import lru_cache
from fastapi import APIRouter, Depends

from mke_product.knowledge.graph_models import GraphModel
from mke_product.knowledge.graph_service import KnowledgeGraphService
from mke_product.knowledge.repository import KnowledgeRepository
from mke_product.knowledge.schemas import (
    ConceptKnowledge,
    FormulaKnowledge,
    MethodKnowledge,
    TheoremKnowledge,
)
from mke_product.transport.models import (
    KnowledgeApiErrorResponse,
    TransportErrorResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge"])


@lru_cache(maxsize=1)
def get_knowledge_repository() -> KnowledgeRepository:
    """Provides a process-level cached singleton instance of KnowledgeRepository."""
    return KnowledgeRepository()


@lru_cache(maxsize=1)
def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Provides a process-level cached singleton instance of KnowledgeGraphService."""
    return KnowledgeGraphService(repository=get_knowledge_repository())


@router.get(
    "/methods/{method_id}",
    operation_id="get_knowledge_method_v1",
    response_model=MethodKnowledge,
    responses={
        200: {"model": MethodKnowledge, "description": "Method knowledge details"},
        404: {"model": KnowledgeApiErrorResponse, "description": "Knowledge method entity not found"},
        500: {"model": TransportErrorResponse, "description": "Internal transport failure"},
    },
)
async def get_method_endpoint(
    method_id: str,
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
) -> MethodKnowledge:
    """Retrieves an immutable MethodKnowledge definition by its canonical ID."""
    return repository.get_method(method_id)


@router.get(
    "/concepts/{concept_id}",
    operation_id="get_knowledge_concept_v1",
    response_model=ConceptKnowledge,
    responses={
        200: {"model": ConceptKnowledge, "description": "Concept knowledge details"},
        404: {"model": KnowledgeApiErrorResponse, "description": "Knowledge concept entity not found"},
        500: {"model": TransportErrorResponse, "description": "Internal transport failure"},
    },
)
async def get_concept_endpoint(
    concept_id: str,
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
) -> ConceptKnowledge:
    """Retrieves an immutable ConceptKnowledge definition by its canonical ID."""
    return repository.get_concept(concept_id)


@router.get(
    "/formulas/{formula_id}",
    operation_id="get_knowledge_formula_v1",
    response_model=FormulaKnowledge,
    responses={
        200: {"model": FormulaKnowledge, "description": "Formula knowledge details"},
        404: {"model": KnowledgeApiErrorResponse, "description": "Knowledge formula entity not found"},
        500: {"model": TransportErrorResponse, "description": "Internal transport failure"},
    },
)
async def get_formula_endpoint(
    formula_id: str,
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
) -> FormulaKnowledge:
    """Retrieves an immutable FormulaKnowledge definition by its canonical ID."""
    return repository.get_formula(formula_id)


@router.get(
    "/theorems/{theorem_id}",
    operation_id="get_knowledge_theorem_v1",
    response_model=TheoremKnowledge,
    responses={
        200: {"model": TheoremKnowledge, "description": "Theorem knowledge details"},
        404: {"model": KnowledgeApiErrorResponse, "description": "Knowledge theorem entity not found"},
        500: {"model": TransportErrorResponse, "description": "Internal transport failure"},
    },
)
async def get_theorem_endpoint(
    theorem_id: str,
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
) -> TheoremKnowledge:
    """Retrieves an immutable TheoremKnowledge definition by its canonical ID."""
    return repository.get_theorem(theorem_id)


@router.get(
    "/graph",
    operation_id="get_knowledge_graph_v1",
    response_model=GraphModel,
    responses={
        200: {"model": GraphModel, "description": "Full mathematical knowledge graph"},
        500: {"model": TransportErrorResponse, "description": "Internal transport failure"},
    },
)
async def get_knowledge_graph_endpoint(
    graph_service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphModel:
    """Exports the complete 29-node / 84-edge mathematical knowledge graph."""
    return graph_service.export_knowledge_graph()
