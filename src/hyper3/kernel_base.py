from __future__ import annotations

from typing import Any

from hyper3.exceptions import NodeNotFoundError
from hyper3.kernel_types import Hyperedge, Hypernode


class _GraphBase:
    _nodes: dict[str, Hypernode]
    _edges: dict[str, Hyperedge]
    _node_to_edges: dict[str, set[str]]
    _dimension_index: dict[str, set[str]]
    _label_index: dict[str, str]
    _neighbor_cache: dict[str, list[str]] | None
    _batch_mode: bool
    _cache_invalidated_in_batch: bool

    def incident_edges(self, node_id: str) -> list[Hyperedge]: ...
    def outgoing_edges(self, node_id: str) -> list[Hyperedge]: ...
    def neighbors(self, node_id: str) -> list[str]: ...
    def remove_edge(self, edge_id: str) -> bool: ...
    def adjacency_matrix(self) -> tuple[Any, list[str]]: ...
    def adjacency_tensor(self, *, order: int | None = None, dense: bool = False) -> Any: ...
    def normalized_laplacian(self) -> tuple[Any, list[str]]: ...
    def hypergraph_laplacian(self) -> Any: ...
    def incidence_matrix_unsigned(self) -> tuple[Any, list[str], list[str]]: ...
    def connected_components(self, *, s: int = 1) -> list[set[str]]: ...
    def subgraph(self, node_ids: set[str]) -> Any: ...
    def _bfs_all_distances(self, source: str) -> dict[str, float]: ...


class CoreMixin(_GraphBase):

    def __init__(self) -> None:
        """Initialize an empty hypergraph with fresh indexes."""
        self._nodes: dict[str, Hypernode] = {}
        self._edges: dict[str, Hyperedge] = {}
        self._node_to_edges: dict[str, set[str]] = {}
        self._dimension_index: dict[str, set[str]] = {}
        self._label_index: dict[str, str] = {}
        self._neighbor_cache: dict[str, list[str]] | None = None
        self._batch_mode: bool = False
        self._cache_invalidated_in_batch: bool = False

    def add_node(self, node: Hypernode) -> Hypernode:
        """Add a node to the graph if not already present.

        Updates the label and dimension indexes.  Returns the existing
        node unchanged if its ID already exists.

        Args:
            node: The hypernode to add.

        Returns:
            The added or existing node.
        """
        if node.id in self._nodes:
            return self._nodes[node.id]
        self._nodes[node.id] = node
        self._node_to_edges[node.id] = set()
        if node.label:
            self._label_index[node.label] = node.id
        for modality in node.metadata.modality_tags:
            self._dimension_index.setdefault(modality.value, set()).add(node.id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return node

    def get_node(self, node_id: str) -> Hypernode | None:
        """Retrieve a node by its ID.

        Args:
            node_id: The unique identifier of the node.

        Returns:
            The hypernode, or None if not found.
        """
        return self._nodes.get(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        """Retrieve a node by its human-readable label.

        Args:
            label: The label to look up.

        Returns:
            The hypernode, or None if no node has this label.
        """
        nid = self._label_index.get(label)
        if nid:
            return self._nodes.get(nid)
        return None

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all edges connected to it.

        Args:
            node_id: The ID of the node to remove.

        Returns:
            True if the node was removed, False if it was not found.
        """
        if node_id not in self._nodes:
            return False
        edge_ids_to_remove = list(self._node_to_edges.get(node_id, set()))
        for edge_id in edge_ids_to_remove:
            self.remove_edge(edge_id)
        node = self._nodes[node_id]
        if node.label:
            self._label_index.pop(node.label, None)
        del self._nodes[node_id]
        del self._node_to_edges[node_id]
        for dim_set in self._dimension_index.values():
            dim_set.discard(node_id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def add_edge(self, edge: Hyperedge) -> Hyperedge:
        """Add an edge to the graph if not already present.

        Accepts edges with any cardinality: pairwise (1:1 source:target)
        or true hyperedges (n:m source:target).  All referenced nodes
        must already exist.

        Args:
            edge: The hyperedge to add.

        Returns:
            The added or existing edge.

        Raises:
            NodeNotFoundError: If any referenced node does not exist.
        """
        if edge.id in self._edges:
            return self._edges[edge.id]
        for nid in edge.node_ids:
            if nid not in self._nodes:
                raise NodeNotFoundError(nid)
            self._node_to_edges[nid].add(edge.id)
        self._edges[edge.id] = edge
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return edge

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        """Retrieve an edge by its ID.

        Args:
            edge_id: The unique identifier of the edge.

        Returns:
            The hyperedge, or None if not found.
        """
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph.

        Args:
            edge_id: The ID of the edge to remove.

        Returns:
            True if the edge was removed, False if it was not found.
        """
        if edge_id not in self._edges:
            return False
        edge = self._edges[edge_id]
        for nid in edge.node_ids:
            if nid in self._node_to_edges:
                self._node_to_edges[nid].discard(edge_id)
        del self._edges[edge_id]
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
        """Merge the secondary node into the primary node.

        Rewires all edges referencing the secondary to reference the
        primary instead, accumulates access counts and modality tags,
        and records the secondary's label as an alias on the primary.

        Args:
            primary_id: ID of the surviving node.
            secondary_id: ID of the node to absorb and remove.

        Returns:
            The merged primary node, or None if either node is missing.
        """
        primary = self._nodes.get(primary_id)
        secondary = self._nodes.get(secondary_id)
        if not primary or not secondary:
            return None
        if primary_id == secondary_id:
            return None
        primary.access_count += secondary.access_count
        primary.weight = max(primary.weight, secondary.weight)
        if primary.label and secondary.label and primary.label != secondary.label:
            if not primary.metadata.custom.get("aliases"):
                primary.metadata.custom["aliases"] = []
            if secondary.label not in primary.metadata.custom["aliases"]:
                primary.metadata.custom["aliases"].append(secondary.label)
        if secondary.label and secondary.label in self._label_index:
            del self._label_index[secondary.label]
        for modality in secondary.metadata.modality_tags:
            primary.metadata.modality_tags.add(modality)
        edges_to_rewire = list(self._node_to_edges.get(secondary_id, set()))
        for edge_id in edges_to_rewire:
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            new_source = (edge.source_ids - {secondary_id}) | {primary_id}
            new_target = (edge.target_ids - {secondary_id}) | {primary_id}
            edge.source_ids = frozenset(new_source)
            edge.target_ids = frozenset(new_target)
            self._node_to_edges[primary_id].add(edge_id)
        self._node_to_edges[secondary_id].clear()
        self.remove_node(secondary_id)
        return primary

    def begin_batch(self) -> None:
        """Defer neighbor-cache invalidation until end_batch is called."""
        self._batch_mode = True
        self._cache_invalidated_in_batch = False

    def end_batch(self) -> None:
        """End batch mode and invalidate the neighbor cache if needed."""
        self._batch_mode = False
        if self._cache_invalidated_in_batch:
            self._neighbor_cache = None
            self._cache_invalidated_in_batch = False
