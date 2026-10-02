"""MKE MVP V1 — Graph Service & Graph Exporters.

Implements graph exporters for Knowledge Graph, Prerequisite Learning DAG,
and read-only Reactive Dependency DAG projections from S1 application results.
Enforces strict graph contract schemas and structural integrity validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from mke_product.application.dto import SolvedResponse
from mke_product.knowledge.graph_models import (
    GraphEdge,
    GraphEdgeType,
    GraphKind,
    GraphModel,
    GraphNode,
    GraphNodeType,
)
from mke_product.knowledge.repository import KnowledgeRepository
from mke_product.knowledge.schemas import LocalizedText


class UnsupportedReactiveProjectionError(Exception):
    """Raised when attempting to project a Reactive DAG from an unsupported response state."""


class GraphIntegrityError(Exception):
    """Raised when a generated GraphModel violates internal referential or acyclicity constraints."""


def validate_graph_model(graph: GraphModel) -> None:
    """Validates structural integrity, referential completeness, and DAG acyclicity."""
    # 1. Unique node IDs
    node_ids: Set[str] = set()
    for node in graph.nodes:
        if node.node_id in node_ids:
            raise GraphIntegrityError(f"Duplicate node_id '{node.node_id}' in graph '{graph.graph_id}'.")
        node_ids.add(node.node_id)

    # 2. Edge endpoints exist & symmetric ordering
    seen_edges: Set[Tuple[str, str, str]] = set()
    for edge in graph.edges:
        if edge.source not in node_ids:
            raise GraphIntegrityError(
                f"Edge source '{edge.source}' not found in node set for graph '{graph.graph_id}'."
            )
        if edge.target not in node_ids:
            raise GraphIntegrityError(
                f"Edge target '{edge.target}' not found in node set for graph '{graph.graph_id}'."
            )

        edge_key = (edge.source, edge.target, edge.relation_type.value)
        if edge_key in seen_edges:
            raise GraphIntegrityError(
                f"Duplicate edge '{edge_key}' detected in graph '{graph.graph_id}'."
            )
        seen_edges.add(edge_key)

        if edge.is_symmetric:
            if edge.source >= edge.target:
                raise GraphIntegrityError(
                    f"Symmetric edge must have canonical ordering source < target: got ({edge.source}, {edge.target})."
                )

    # 3. Acyclicity validation if marked acyclic
    if graph.is_acyclic:
        adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}

        for edge in graph.edges:
            if edge.is_directed:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        queue = [nid for nid in node_ids if in_degree[nid] == 0]
        visited_count = 0
        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(node_ids):
            raise GraphIntegrityError(
                f"Cycle detected in graph '{graph.graph_id}' marked as acyclic."
            )


class KnowledgeGraphService:
    """Service providing graph exports and reactive projections for MKE."""

    def __init__(self, repository: Optional[KnowledgeRepository] = None) -> None:
        self._repository = repository or KnowledgeRepository()

    @property
    def repository(self) -> KnowledgeRepository:
        """Returns the active KnowledgeRepository instance."""
        return self._repository

    # ------------------------------------------------------------------------
    # 1. Knowledge Graph Exporter (All 29 Static Entities, 84 Edges)
    # ------------------------------------------------------------------------

    def export_knowledge_graph(self) -> GraphModel:
        """Exports the complete 29-node Knowledge Graph over concepts, methods, formulas, and theorems.

        Encodes canonical symmetric deduplication for associative and alternative relations.
        Total edge count = 84 (17 Concept REQUIRES + 18 RELATED_TO + 30 Method REQUIRES + 6 USES_FORMULA + 3 USES_THEOREM + 10 ALTERNATIVE_TO).
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_symmetric_edges: Set[Tuple[str, str, str]] = set()

        # 1. Concepts (14 nodes)
        for concept in self._repository.list_concepts():
            c_node_id = f"concept:{concept.concept_id}"
            nodes.append(
                GraphNode(
                    node_id=c_node_id,
                    node_type=GraphNodeType.CONCEPT,
                    label=concept.title,
                    knowledge_ref=concept.concept_id,
                    metadata={"version": concept.version},
                )
            )

            # Concept -> Prerequisite Concept (REQUIRES, 17 edges across dataset)
            for prereq_id in sorted(concept.prerequisite_concept_ids):
                edges.append(
                    GraphEdge(
                        source=c_node_id,
                        target=f"concept:{prereq_id}",
                        relation_type=GraphEdgeType.REQUIRES,
                        is_directed=True,
                        is_symmetric=False,
                    )
                )

            # Concept <-> Related Concept (RELATED_TO, 18 unique symmetric edges across dataset)
            for rel_id in sorted(concept.related_concept_ids):
                target_node_id = f"concept:{rel_id}"
                u, v = (c_node_id, target_node_id) if c_node_id < target_node_id else (target_node_id, c_node_id)
                key = (u, v, GraphEdgeType.RELATED_TO.value)
                if key not in seen_symmetric_edges:
                    seen_symmetric_edges.add(key)
                    edges.append(
                        GraphEdge(
                            source=u,
                            target=v,
                            relation_type=GraphEdgeType.RELATED_TO,
                            is_directed=False,
                            is_symmetric=True,
                        )
                    )

        # 2. Methods (9 nodes)
        for method in self._repository.list_methods():
            m_node_id = f"method:{method.method_id}"
            nodes.append(
                GraphNode(
                    node_id=m_node_id,
                    node_type=GraphNodeType.METHOD,
                    label=method.title,
                    knowledge_ref=method.method_id,
                    metadata={"version": method.version},
                )
            )

            # Method -> Prerequisite Concept (REQUIRES, 30 edges across dataset)
            for prereq_id in sorted(method.prerequisite_concept_ids):
                edges.append(
                    GraphEdge(
                        source=m_node_id,
                        target=f"concept:{prereq_id}",
                        relation_type=GraphEdgeType.REQUIRES,
                        is_directed=True,
                        is_symmetric=False,
                    )
                )

            # Method -> Formula (USES_FORMULA, 6 edges across dataset)
            for formula_id in sorted(method.formula_refs):
                edges.append(
                    GraphEdge(
                        source=m_node_id,
                        target=f"formula:{formula_id}",
                        relation_type=GraphEdgeType.USES_FORMULA,
                        is_directed=True,
                        is_symmetric=False,
                    )
                )

            # Method -> Theorem (USES_THEOREM, 3 edges across dataset)
            for theorem_id in sorted(method.theorem_refs):
                edges.append(
                    GraphEdge(
                        source=m_node_id,
                        target=f"theorem:{theorem_id}",
                        relation_type=GraphEdgeType.USES_THEOREM,
                        is_directed=True,
                        is_symmetric=False,
                    )
                )

            # Method <-> Related Method (ALTERNATIVE_TO, 10 unique symmetric edges across dataset)
            for rel_method_id in sorted(method.related_method_ids):
                target_node_id = f"method:{rel_method_id}"
                u, v = (m_node_id, target_node_id) if m_node_id < target_node_id else (target_node_id, m_node_id)
                key = (u, v, GraphEdgeType.ALTERNATIVE_TO.value)
                if key not in seen_symmetric_edges:
                    seen_symmetric_edges.add(key)
                    edges.append(
                        GraphEdge(
                            source=u,
                            target=v,
                            relation_type=GraphEdgeType.ALTERNATIVE_TO,
                            is_directed=False,
                            is_symmetric=True,
                        )
                    )

        # 3. Formulas (5 nodes)
        for formula in self._repository.list_formulas():
            f_node_id = f"formula:{formula.formula_id}"
            nodes.append(
                GraphNode(
                    node_id=f_node_id,
                    node_type=GraphNodeType.FORMULA,
                    label=formula.title,
                    knowledge_ref=formula.formula_id,
                    metadata={
                        "latex_template": formula.latex_template,
                        "version": formula.version,
                    },
                )
            )

        # 4. Theorems (1 node)
        for theorem in self._repository.list_theorems():
            t_node_id = f"theorem:{theorem.theorem_id}"
            nodes.append(
                GraphNode(
                    node_id=t_node_id,
                    node_type=GraphNodeType.THEOREM,
                    label=theorem.title,
                    knowledge_ref=theorem.theorem_id,
                    metadata={
                        "formal_statement_latex": theorem.formal_statement_latex,
                        "version": theorem.version,
                    },
                )
            )

        # Sort nodes and edges canonically for determinism
        nodes.sort(key=lambda n: n.node_id)
        edges.sort(key=lambda e: (e.source, e.target, e.relation_type.value))

        graph = GraphModel(
            graph_id="knowledge_graph_quadratics_v1",
            graph_kind=GraphKind.KNOWLEDGE_GRAPH,
            title=LocalizedText(
                vi="Đồ thị tri thức phương trình bậc hai",
                en="Quadratic Equations Knowledge Graph",
            ),
            nodes=nodes,
            edges=edges,
            is_acyclic=False,
            version="1.0.0",
        )
        validate_graph_model(graph)
        return graph

    # ------------------------------------------------------------------------
    # 2. Prerequisite Learning DAG Exporter (14 Concept Nodes, 17 Edges)
    # ------------------------------------------------------------------------

    def export_prerequisite_dag(self) -> GraphModel:
        """Exports the strict 14-node concept learning prerequisite DAG.

        Edges point from prerequisite -> dependent concept with relation LEARN_BEFORE (17 edges).
        """
        topological_concepts = self._repository.get_topological_prerequisite_order()
        nodes: List[GraphNode] = [
            GraphNode(
                node_id=f"concept:{c.concept_id}",
                node_type=GraphNodeType.CONCEPT,
                label=c.title,
                knowledge_ref=c.concept_id,
                metadata={"version": c.version},
            )
            for c in topological_concepts
        ]

        edges: List[GraphEdge] = []
        for concept in topological_concepts:
            dependent_node_id = f"concept:{concept.concept_id}"
            for prereq_id in sorted(concept.prerequisite_concept_ids):
                prereq_node_id = f"concept:{prereq_id}"
                edges.append(
                    GraphEdge(
                        source=prereq_node_id,
                        target=dependent_node_id,
                        relation_type=GraphEdgeType.LEARN_BEFORE,
                        is_directed=True,
                        is_symmetric=False,
                    )
                )

        edges.sort(key=lambda e: (e.source, e.target, e.relation_type.value))

        graph = GraphModel(
            graph_id="prerequisite_dag_concepts_v1",
            graph_kind=GraphKind.PREREQUISITE_DAG,
            title=LocalizedText(
                vi="Đồ thị phân cấp tiên quyết khái niệm",
                en="Concept Prerequisite Learning DAG",
            ),
            nodes=nodes,
            edges=edges,
            is_acyclic=True,
            version="1.0.0",
        )
        validate_graph_model(graph)
        return graph

    # ------------------------------------------------------------------------
    # 3. Read-Only Reactive Dependency DAG Projection (from S1 SolveResponse)
    # ------------------------------------------------------------------------

    def project_reactive_dependency_dag(self, response: Any) -> GraphModel:
        """Projects a deterministic, read-only computational dependency DAG from an accepted S1 response.

        Guarantees zero mutation and zero recalculation of S1 mathematical truth.
        """
        if not isinstance(response, SolvedResponse):
            raise UnsupportedReactiveProjectionError(
                f"Reactive DAG projection is currently supported only for SolvedResponse instances, got: {type(response).__name__}"
            )

        problem = response.problem
        solution = response.solution

        nodes: List[GraphNode] = [
            # 1. Parameter Nodes
            GraphNode(
                node_id="parameter:a",
                node_type=GraphNodeType.PARAMETER,
                label=LocalizedText(vi="Hệ số bậc hai a", en="Quadratic Coefficient a"),
                dependency_ref="a",
                metadata={
                    "numerator": problem.a.numerator,
                    "denominator": problem.a.denominator,
                    "latex": problem.a.to_latex(),
                },
            ),
            GraphNode(
                node_id="parameter:b",
                node_type=GraphNodeType.PARAMETER,
                label=LocalizedText(vi="Hệ số bậc một b", en="Linear Coefficient b"),
                dependency_ref="b",
                metadata={
                    "numerator": problem.b.numerator,
                    "denominator": problem.b.denominator,
                    "latex": problem.b.to_latex(),
                },
            ),
            GraphNode(
                node_id="parameter:c",
                node_type=GraphNodeType.PARAMETER,
                label=LocalizedText(vi="Hệ số tự do c", en="Constant Coefficient c"),
                dependency_ref="c",
                metadata={
                    "numerator": problem.c.numerator,
                    "denominator": problem.c.denominator,
                    "latex": problem.c.to_latex(),
                },
            ),
            # 2. Computation Nodes
            GraphNode(
                node_id="computation:discriminant",
                node_type=GraphNodeType.COMPUTATION,
                label=LocalizedText(vi="Tính toán biệt thức Delta", en="Discriminant Evaluation"),
                dependency_ref="discriminant",
                metadata={
                    "value": problem.discriminant.value.model_dump(),
                    "is_positive": problem.discriminant.is_positive,
                    "is_zero": problem.discriminant.is_zero,
                    "is_negative": problem.discriminant.is_negative,
                    "is_rational_square": problem.discriminant.is_rational_square,
                    "square_root_rational": (
                        problem.discriminant.square_root_rational.model_dump()
                        if problem.discriminant.square_root_rational is not None
                        else None
                    ),
                    "squarefree_kernel": problem.discriminant.squarefree_kernel,
                    "extracted_factor": (
                        problem.discriminant.extracted_factor.model_dump()
                        if problem.discriminant.extracted_factor is not None
                        else None
                    ),
                },
            ),
            GraphNode(
                node_id="computation:selected_method",
                node_type=GraphNodeType.COMPUTATION,
                label=LocalizedText(vi="Lựa chọn phương pháp giải", en="Method Selection Resolution"),
                dependency_ref="selected_method",
                metadata={
                    "selected_method_id": response.selected_method_id,
                },
            ),
            GraphNode(
                node_id="computation:solution_trace",
                node_type=GraphNodeType.COMPUTATION,
                label=LocalizedText(vi="Tiến trình lời giải và nghiệm", en="Solution Trace Execution"),
                dependency_ref="solution_trace",
                metadata={
                    "outcome": solution.outcome.value,
                    "roots_count": len(solution.roots),
                    "final_answer_latex": solution.final_answer_latex,
                },
            ),
            GraphNode(
                node_id="computation:verification_certificate",
                node_type=GraphNodeType.COMPUTATION,
                label=LocalizedText(vi="Chứng chỉ xác minh độc lập", en="Host Verification Certificate"),
                dependency_ref="verification_certificate",
                metadata={
                    "certificate_id": solution.certificate.certificate_id,
                    "outcome": solution.certificate.outcome.value,
                    "problem_hash": solution.certificate.problem_hash,
                    "certificate_signature": solution.certificate.certificate_signature,
                },
            ),
        ]

        edges: List[GraphEdge] = [
            # Parameters -> Discriminant
            GraphEdge(
                source="parameter:a",
                target="computation:discriminant",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:b",
                target="computation:discriminant",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:c",
                target="computation:discriminant",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            # Discriminant & Parameters -> Method Selection
            GraphEdge(
                source="computation:discriminant",
                target="computation:selected_method",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:a",
                target="computation:selected_method",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:b",
                target="computation:selected_method",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:c",
                target="computation:selected_method",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            # Method Selection -> Solution Trace
            GraphEdge(
                source="computation:selected_method",
                target="computation:solution_trace",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            # Solution Trace & Parameters -> Verification Certificate
            GraphEdge(
                source="computation:solution_trace",
                target="computation:verification_certificate",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:a",
                target="computation:verification_certificate",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:b",
                target="computation:verification_certificate",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
            GraphEdge(
                source="parameter:c",
                target="computation:verification_certificate",
                relation_type=GraphEdgeType.COMPUTATIONAL_DEPENDENCY,
                is_directed=True,
                is_symmetric=False,
            ),
        ]

        nodes.sort(key=lambda n: n.node_id)
        edges.sort(key=lambda e: (e.source, e.target, e.relation_type.value))

        graph = GraphModel(
            graph_id=f"reactive_dag_{problem.problem_id}",
            graph_kind=GraphKind.REACTIVE_DEPENDENCY_DAG,
            title=LocalizedText(
                vi="Đồ thị phụ thuộc tính toán phản ứng",
                en="Reactive Computational Dependency DAG",
            ),
            nodes=nodes,
            edges=edges,
            is_acyclic=True,
            version="1.0.0",
        )
        validate_graph_model(graph)
        return graph
