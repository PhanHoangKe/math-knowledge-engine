"""MKE MVP V1 — Reactive Dependency DAG & Invalidation Engine.

Manages reactive dependencies and selective invalidation cascades for
interactive workspace parameter mutation.
"""

from __future__ import annotations

from typing import Dict, List, Set

from mke_product.domain.models import DependencyNode


class CycleDetectedError(Exception):
    """Raised when an edge insertion would create a cycle in the DAG."""
    pass


class NodeNotFoundError(Exception):
    """Raised when referencing an unknown node ID."""
    pass


class DependencyGraph:
    """Deterministic Directed Acyclic Graph (DAG) for workspace node dependencies."""

    def __init__(self) -> None:
        self._nodes: Dict[str, DependencyNode] = {}
        # adjacency: source_id -> list of target_ids (nodes that depend on source)
        self._downstream: Dict[str, List[str]] = {}
        # reverse adjacency: target_id -> list of source_ids (prerequisites)
        self._upstream: Dict[str, List[str]] = {}

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: str = "COMPUTED",
        is_valid: bool = True,
    ) -> DependencyNode:
        """Add a node to the graph."""
        if node_id in self._nodes:
            raise ValueError(f"Node '{node_id}' already exists in DependencyGraph.")
        node = DependencyNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            is_valid=is_valid,
        )
        self._nodes[node_id] = node
        self._downstream[node_id] = []
        self._upstream[node_id] = []
        return node

    def get_node(self, node_id: str) -> DependencyNode:
        """Get a node by ID."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in DependencyGraph.")
        return self._nodes[node_id]

    def has_node(self, node_id: str) -> bool:
        """Check if a node ID exists."""
        return node_id in self._nodes

    def list_nodes(self) -> List[DependencyNode]:
        """List all nodes in deterministic insertion order."""
        return list(self._nodes.values())

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Add a directed dependency edge: target_id depends on source_id.

        If adding this edge would create a cycle, raises CycleDetectedError.
        """
        if source_id not in self._nodes:
            raise NodeNotFoundError(f"Source node '{source_id}' not found.")
        if target_id not in self._nodes:
            raise NodeNotFoundError(f"Target node '{target_id}' not found.")
        if source_id == target_id:
            raise CycleDetectedError(f"Self-loop on node '{source_id}' is forbidden.")

        if target_id in self._downstream[source_id]:
            return  # Edge already exists

        # Check if source_id is reachable from target_id (which would create a cycle)
        if self._is_reachable(target_id, source_id):
            raise CycleDetectedError(
                f"Adding dependency edge '{source_id}' -> '{target_id}' creates a cycle in the graph."
            )

        self._downstream[source_id].append(target_id)
        self._upstream[target_id].append(source_id)

    def _is_reachable(self, start_id: str, target_id: str) -> bool:
        """Check reachability from start_id to target_id via DFS."""
        visited: Set[str] = set()
        stack = [start_id]
        while stack:
            curr = stack.pop()
            if curr == target_id:
                return True
            if curr not in visited:
                visited.add(curr)
                for nxt in self._downstream.get(curr, []):
                    if nxt not in visited:
                        stack.append(nxt)
        return False

    def invalidate(self, node_id: str) -> List[str]:
        """Mark node_id and all its transitive downstream descendants as invalid.

        Returns:
            List of all invalidated node IDs in deterministic topological order.
        """
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")

        # Find all transitive downstream nodes
        affected_set: Set[str] = set()
        stack = [node_id]
        while stack:
            curr = stack.pop()
            if curr not in affected_set:
                affected_set.add(curr)
                for nxt in self._downstream.get(curr, []):
                    if nxt not in affected_set:
                        stack.append(nxt)

        # Mark all affected as invalid
        for nid in affected_set:
            self._nodes[nid].is_valid = False

        # Sort affected nodes in topological order
        sorted_order: List[str] = []
        visited_topo: Set[str] = set()

        def dfs_topo(n: str) -> None:
            visited_topo.add(n)
            for child in self._downstream.get(n, []):
                if child in affected_set and child not in visited_topo:
                    dfs_topo(child)
            sorted_order.append(n)

        # Perform DFS on node_id to get reverse postorder
        dfs_topo(node_id)
        sorted_order.reverse()
        return sorted_order

    def validate(self, node_id: str) -> None:
        """Mark a single node as valid."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")
        self._nodes[node_id].is_valid = True

    def is_valid(self, node_id: str) -> bool:
        """Check if a node is currently valid."""
        return self.get_node(node_id).is_valid

    def get_downstream_nodes(self, node_id: str) -> List[str]:
        """Get all transitive downstream node IDs."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")
        visited: Set[str] = set()
        stack = list(self._downstream.get(node_id, []))
        while stack:
            curr = stack.pop()
            if curr not in visited:
                visited.add(curr)
                for nxt in self._downstream.get(curr, []):
                    if nxt not in visited:
                        stack.append(nxt)
        return sorted(list(visited))

    def get_upstream_nodes(self, node_id: str) -> List[str]:
        """Get all transitive upstream prerequisite node IDs."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found.")
        visited: Set[str] = set()
        stack = list(self._upstream.get(node_id, []))
        while stack:
            curr = stack.pop()
            if curr not in visited:
                visited.add(curr)
                for prv in self._upstream.get(curr, []):
                    if prv not in visited:
                        stack.append(prv)
        return sorted(list(visited))


def build_quadratic_workspace_dag() -> DependencyGraph:
    """Build the canonical workspace dependency DAG for quadratic equations."""
    dag = DependencyGraph()

    # Input nodes
    dag.add_node("coefficients", "Hệ số a, b, c", node_type="INPUT")

    # Computed nodes
    dag.add_node("discriminant", "Biệt thức Delta", node_type="COMPUTED")
    dag.add_node("root_classification", "Phân loại nghiệm", node_type="COMPUTED")
    dag.add_node("roots", "Tập nghiệm thực", node_type="COMPUTED")
    dag.add_node("method_assessments", "Đánh giá phương pháp", node_type="COMPUTED")
    dag.add_node("solution_traces", "Các bước giải chi tiết", node_type="COMPUTED")
    dag.add_node("verification_certificate", "Chứng chỉ xác thực độc lập", node_type="COMPUTED")
    dag.add_node("graph_visualization", "Khảo sát đồ thị Parabol", node_type="COMPUTED")
    dag.add_node("pedagogical_view", "Trình bày sư phạm tiếng Việt", node_type="PRESENTATION")

    # Edges
    dag.add_edge("coefficients", "discriminant")
    dag.add_edge("discriminant", "root_classification")
    dag.add_edge("root_classification", "roots")
    dag.add_edge("discriminant", "method_assessments")
    dag.add_edge("roots", "solution_traces")
    dag.add_edge("roots", "verification_certificate")
    dag.add_edge("roots", "graph_visualization")
    dag.add_edge("method_assessments", "pedagogical_view")
    dag.add_edge("solution_traces", "pedagogical_view")
    dag.add_edge("graph_visualization", "pedagogical_view")

    return dag
