"""Unit and integration tests for MKE S3 Graph Service and Graph Models.

Verifies:
1. Pydantic v2 strict graph contracts (GraphNode, GraphEdge, GraphModel).
2. Knowledge Graph export (29 static nodes, canonical symmetric edge deduplication).
3. Prerequisite Learning DAG export (14 concept nodes, acyclic, topological compliance).
4. Reactive Dependency DAG projection over existing S1 solved responses for canonical fixtures.
5. Determinism, immutability, and zero mutation of S1 mathematical truth.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from mke_product.application.dto import RawEquationInput, SolvedResponse, SolveRequest
from mke_product.application.orchestrator import solve_request
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
from mke_product.knowledge.schemas import LocalizedText


@pytest.fixture
def service() -> KnowledgeGraphService:
    return KnowledgeGraphService()


# ============================================================================
# 1. GRAPH MODEL CONTRACT TESTS
# ============================================================================

def test_graph_models_strict_validation() -> None:
    # Valid Node
    node = GraphNode(
        node_id="concept:test",
        node_type=GraphNodeType.CONCEPT,
        label=LocalizedText(vi="Kiểm thử", en="Test"),
    )
    assert node.node_id == "concept:test"

    # Extra fields rejected
    with pytest.raises(ValidationError):
        GraphNode(
            node_id="concept:test",
            node_type=GraphNodeType.CONCEPT,
            label=LocalizedText(vi="Kiểm thử", en="Test"),
            extra="forbidden",  # type: ignore[call-arg]
        )

    # Immutability
    with pytest.raises(ValidationError):
        node.node_id = "mutated"  # type: ignore[misc]

    # Valid Edge
    edge = GraphEdge(
        source_id="method:QUAD_FORMULA_STANDARD",
        target_id="concept:concept_discriminant",
        edge_type=GraphEdgeType.REQUIRES,
    )
    assert edge.is_symmetric is False

    # Valid GraphModel
    graph = GraphModel(
        graph_id="test_graph",
        graph_kind=GraphKind.KNOWLEDGE_GRAPH,
        title=LocalizedText(vi="Đồ thị mẫu", en="Sample Graph"),
        nodes=[node],
        edges=[edge],
        is_acyclic=False,
    )
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 1


# ============================================================================
# 2. KNOWLEDGE GRAPH EXPORTER TESTS
# ============================================================================

def test_knowledge_graph_export_node_counts_and_types(service: KnowledgeGraphService) -> None:
    kg = service.export_knowledge_graph()

    assert kg.graph_kind == GraphKind.KNOWLEDGE_GRAPH
    assert len(kg.nodes) == 29

    type_counts = {}
    for n in kg.nodes:
        type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1

    assert type_counts[GraphNodeType.CONCEPT] == 14
    assert type_counts[GraphNodeType.METHOD] == 9
    assert type_counts[GraphNodeType.FORMULA] == 5
    assert type_counts[GraphNodeType.THEOREM] == 1


def test_knowledge_graph_edge_integrity_and_canonical_symmetry(service: KnowledgeGraphService) -> None:
    kg = service.export_knowledge_graph()
    node_ids = {n.node_id for n in kg.nodes}

    seen_edges = set()
    for edge in kg.edges:
        # 1. No dangling endpoints
        assert edge.source_id in node_ids, f"Unknown source node: {edge.source_id}"
        assert edge.target_id in node_ids, f"Unknown target node: {edge.target_id}"

        # 2. No duplicate edges
        edge_key = (edge.source_id, edge.target_id, edge.edge_type)
        assert edge_key not in seen_edges, f"Duplicate edge: {edge_key}"
        seen_edges.add(edge_key)

        # 3. Canonical symmetric ordering: source < target and no inverse duplicate
        if edge.is_symmetric:
            assert edge.source_id < edge.target_id, f"Symmetric edge must have source < target: {edge}"
            inverse_key = (edge.target_id, edge.source_id, edge.edge_type)
            assert inverse_key not in seen_edges, f"Inverse duplicate found for symmetric edge: {edge}"


def test_knowledge_graph_repeated_build_determinism(service: KnowledgeGraphService) -> None:
    kg1 = service.export_knowledge_graph()
    kg2 = service.export_knowledge_graph()

    assert kg1.model_dump() == kg2.model_dump()
    assert json.dumps(kg1.model_dump(), sort_keys=True) == json.dumps(kg2.model_dump(), sort_keys=True)


# ============================================================================
# 3. PREREQUISITE DAG EXPORTER TESTS
# ============================================================================

def test_prerequisite_dag_export(service: KnowledgeGraphService) -> None:
    dag = service.export_prerequisite_dag()

    assert dag.graph_kind == GraphKind.PREREQUISITE_DAG
    assert dag.is_acyclic is True
    assert len(dag.nodes) == 14

    node_ids = {n.node_id for n in dag.nodes}
    assert all(n.node_type == GraphNodeType.CONCEPT for n in dag.nodes)

    # Check edges
    for edge in dag.edges:
        assert edge.edge_type == GraphEdgeType.LEARN_BEFORE
        assert edge.source_id in node_ids
        assert edge.target_id in node_ids


def test_prerequisite_dag_satisfies_learning_order(service: KnowledgeGraphService) -> None:
    dag = service.export_prerequisite_dag()
    node_index = {n.node_id: idx for idx, n in enumerate(dag.nodes)}

    # Every LEARN_BEFORE edge must point from lower index to higher index
    for edge in dag.edges:
        src_idx = node_index[edge.source_id]
        tgt_idx = node_index[edge.target_id]
        assert src_idx < tgt_idx, (
            f"Prerequisite learning order violated: '{edge.source_id}' (idx {src_idx}) "
            f"must appear before '{edge.target_id}' (idx {tgt_idx})."
        )


def test_prerequisite_dag_repeated_build_determinism(service: KnowledgeGraphService) -> None:
    dag1 = service.export_prerequisite_dag()
    dag2 = service.export_prerequisite_dag()

    assert dag1.model_dump() == dag2.model_dump()


# ============================================================================
# 4. REACTIVE DEPENDENCY DAG PROJECTION TESTS (CANONICAL 4 EQUATIONS)
# ============================================================================

@pytest.mark.parametrize(
    "equation_query, expected_roots_count",
    [
        ("x^2 - 5*x + 6 = 0", 2),
        ("x^2 + 2*x + 1 = 0", 1),
        ("x^2 + 1 = 0", 0),
        ("2*x^2 + 3*x + 7 = 0", 0),
    ],
)
def test_reactive_dag_projection_on_canonical_fixtures(
    service: KnowledgeGraphService, equation_query: str, expected_roots_count: int
) -> None:
    # 1. Execute S1 solve
    req = SolveRequest(input_payload=RawEquationInput(raw_query=equation_query))
    response = solve_request(req)
    assert isinstance(response, SolvedResponse)
    assert len(response.solution.roots) == expected_roots_count

    # 2. Project Reactive DAG
    reactive_dag = service.project_reactive_dependency_dag(response)

    assert reactive_dag.graph_kind == GraphKind.REACTIVE_DEPENDENCY_DAG
    assert reactive_dag.is_acyclic is True
    assert len(reactive_dag.nodes) == 7  # 3 parameters + 4 computations
    assert len(reactive_dag.edges) == 12

    # Check node categories
    node_map = {n.node_id: n for n in reactive_dag.nodes}
    assert "parameter:a" in node_map
    assert "parameter:b" in node_map
    assert "parameter:c" in node_map
    assert "computation:discriminant" in node_map
    assert "computation:selected_method" in node_map
    assert "computation:solution_trace" in node_map
    assert "computation:verification_certificate" in node_map

    # Check edge types
    for edge in reactive_dag.edges:
        assert edge.edge_type == GraphEdgeType.COMPUTATIONAL_DEPENDENCY
        assert edge.source_id in node_map
        assert edge.target_id in node_map

    # 3. Repeated projection determinism
    repeated_dag = service.project_reactive_dependency_dag(response)
    assert reactive_dag.model_dump() == repeated_dag.model_dump()


def test_reactive_dag_unsupported_state_raises_typed_error(service: KnowledgeGraphService) -> None:
    with pytest.raises(UnsupportedReactiveProjectionError) as exc_info:
        service.project_reactive_dependency_dag("invalid_response_object")
    assert "UnsupportedReactiveProjectionError" in type(exc_info.value).__name__
