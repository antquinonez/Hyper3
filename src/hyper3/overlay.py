from __future__ import annotations

from hyper3.kernel import (
    Hyperedge,
    Hypergraph,
    Hypernode,
    Modality,
)


class HypergraphOverlay:
    def __init__(self, base: Hypergraph) -> None:
        """Initialize an overlay on top of the given base graph.

        Args:
            base: The underlying hypergraph to wrap.
        """
        self._base = base
        self._overlay_nodes: dict[str, Hypernode] = {}
        self._overlay_edges: dict[str, Hyperedge] = {}
        self._overlay_node_to_edges: dict[str, set[str]] = {}
        self._overlay_label_index: dict[str, str] = {}
        self._confidence: dict[str, float] = {}

    def add_node(self, node: Hypernode) -> Hypernode:
        """Add a node to the overlay layer.

        Args:
            node: The hypernode to add.

        Returns:
            The added or existing overlay node.
        """
        if node.id in self._overlay_nodes:
            return self._overlay_nodes[node.id]
        self._overlay_nodes[node.id] = node
        self._overlay_node_to_edges[node.id] = set()
        if node.label:
            self._overlay_label_index[node.label] = node.id
        return node

    def get_node(self, node_id: str) -> Hypernode | None:
        """Retrieve a node from the overlay, falling back to the base graph.

        Args:
            node_id: The unique identifier of the node.

        Returns:
            The hypernode, or None if not found in either layer.
        """
        return self._overlay_nodes.get(node_id) or self._base.get_node(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        """Retrieve a node by label from the overlay, falling back to the base graph.

        Args:
            label: The human-readable label to look up.

        Returns:
            The hypernode, or None if not found.
        """
        nid = self._overlay_label_index.get(label)
        if nid:
            return self._overlay_nodes.get(nid)
        return self._base.get_node_by_label(label)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the overlay layer along with its overlay edges.

        Does not affect the base graph.

        Args:
            node_id: The ID of the node to remove.

        Returns:
            True if the node was removed, False if it was not in the overlay.
        """
        if node_id in self._overlay_nodes:
            edge_ids = list(self._overlay_node_to_edges.get(node_id, set()))
            for eid in edge_ids:
                self._remove_overlay_edge(eid)
            node = self._overlay_nodes[node_id]
            if node.label:
                self._overlay_label_index.pop(node.label, None)
            del self._overlay_nodes[node_id]
            if node_id in self._overlay_node_to_edges:
                del self._overlay_node_to_edges[node_id]
            return True
        return False

    def add_edge(self, edge: Hyperedge) -> Hyperedge:
        """Add an edge to the overlay layer.

        Unlike the base graph, this does not require referenced nodes to
        already exist.

        Args:
            edge: The hyperedge to add.

        Returns:
            The added or existing overlay edge.
        """
        if edge.id in self._overlay_edges:
            return self._overlay_edges[edge.id]
        for nid in edge.node_ids:
            self._overlay_node_to_edges.setdefault(nid, set()).add(edge.id)
        self._overlay_edges[edge.id] = edge
        return edge

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        """Retrieve an edge from the overlay, falling back to the base graph.

        Args:
            edge_id: The unique identifier of the edge.

        Returns:
            The hyperedge, or None if not found in either layer.
        """
        return self._overlay_edges.get(edge_id) or self._base.get_edge(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the overlay layer.

        Args:
            edge_id: The ID of the edge to remove.

        Returns:
            True if the edge was removed, False if it was not in the overlay.
        """
        if edge_id in self._overlay_edges:
            self._remove_overlay_edge(edge_id)
            return True
        return False

    def edges_for(self, node_id: str) -> list[Hyperedge]:
        """Return all edges for a node from both base and overlay layers.

        Args:
            node_id: The ID of the node.

        Returns:
            Combined list of base and overlay edges.
        """
        base_edges = self._base.edges_for(node_id)
        overlay_ids = self._overlay_node_to_edges.get(node_id, set())
        overlay_edges = [self._overlay_edges[eid] for eid in overlay_ids if eid in self._overlay_edges]
        return base_edges + overlay_edges

    def neighbors(self, node_id: str) -> list[str]:
        """Return neighbor IDs from both the base graph and overlay.

        Args:
            node_id: The ID of the node.

        Returns:
            Deduplicated list of neighboring node IDs.
        """
        base_nbrs = set(self._base.neighbors(node_id))
        overlay_nbrs: set[str] = set()
        for eid in self._overlay_node_to_edges.get(node_id, set()):
            edge = self._overlay_edges.get(eid)
            if edge:
                for nid in edge.node_ids:
                    if nid != node_id:
                        overlay_nbrs.add(nid)
        return list(base_nbrs | overlay_nbrs)

    def query_dimension(self, modality: Modality) -> list[Hypernode]:
        """Return nodes matching a modality from both base and overlay layers.

        Args:
            modality: The modality to filter by.

        Returns:
            Combined list of matching nodes.
        """
        base = self._base.query_dimension(modality)
        overlay = [
            n for n in self._overlay_nodes.values()
            if modality in n.metadata.modality_tags
        ]
        return base + overlay

    def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
        """Merge secondary into primary across both overlay and base graph.

        If the secondary node exists in the overlay, removes it and remaps
        all overlay edges so that ``secondary_id`` is replaced by
        ``primary_id`` in source/target frozensets.  If the primary is not
        already in the overlay but exists in the base graph, a **deep copy**
        is placed into the overlay to avoid dual-ownership of the same
        object.  Finally delegates to ``base.merge_node()`` for the
        permanent base-graph merge.
        """
        if secondary_id in self._overlay_nodes:
            secondary = self._overlay_nodes.pop(secondary_id)
            if secondary.label:
                self._overlay_label_index.pop(secondary.label, None)
            for eid in list(self._overlay_node_to_edges.get(secondary_id, set())):
                edge = self._overlay_edges.get(eid)
                if edge:
                    new_source = (edge.source_ids - {secondary_id}) | {primary_id}
                    new_target = (edge.target_ids - {secondary_id}) | {primary_id}
                    edge.source_ids = frozenset(new_source)
                    edge.target_ids = frozenset(new_target)
                    for nid in new_source | new_target:
                        self._overlay_node_to_edges.setdefault(nid, set()).add(eid)
                    self._overlay_node_to_edges.pop(secondary_id, None)
            primary_in_overlay = primary_id in self._overlay_nodes
            if not primary_in_overlay:
                primary_base = self._base.get_node(primary_id)
                if primary_base:
                    import copy
                    self._overlay_nodes[primary_id] = copy.deepcopy(primary_base)
        result = self._base.merge_node(primary_id, secondary_id)
        if result and result.label:
            self._overlay_label_index[result.label] = result.id
        return result

    @property
    def nodes(self) -> list[Hypernode]:
        """All nodes from both base and overlay (overlay takes precedence on ID collision)."""
        base_nodes = {n.id: n for n in self._base.nodes}
        base_nodes.update(self._overlay_nodes)
        return list(base_nodes.values())

    @property
    def edges(self) -> list[Hyperedge]:
        """All edges from both base and overlay (overlay takes precedence on ID collision)."""
        base_edges = {e.id: e for e in self._base.edges}
        base_edges.update(self._overlay_edges)
        return list(base_edges.values())

    @property
    def node_count(self) -> int:
        """Total unique node count across base and overlay."""
        base_ids = {n.id for n in self._base.nodes}
        overlay_ids = set(self._overlay_nodes.keys())
        return len(base_ids | overlay_ids)

    @property
    def edge_count(self) -> int:
        """Total unique edge count across base and overlay."""
        base_ids = {e.id for e in self._base.edges}
        overlay_ids = set(self._overlay_edges.keys())
        return len(base_ids | overlay_ids)

    def commit(self) -> tuple[list[str], list[str]]:
        """Merge all overlay nodes and edges into the base graph.

        Stamps confidence values onto edge metadata before merging.
        Edges that fail to add (e.g. missing nodes) are excluded from
        the returned edge ID list.  Clears the overlay after committing.

        Returns:
            Tuple of (committed_node_ids, committed_edge_ids).
        """
        node_ids = list(self._overlay_nodes.keys())
        edge_ids = list(self._overlay_edges.keys())
        for eid, conf in self._confidence.items():
            edge = self._overlay_edges.get(eid)
            if edge:
                edge.metadata.custom["confidence"] = conf
        for node in self._overlay_nodes.values():
            self._base.add_node(node)
        failed: list[str] = []
        for edge in self._overlay_edges.values():
            try:
                self._base.add_edge(edge)
            except Exception:
                failed.append(edge.id)
        self._overlay_nodes.clear()
        self._overlay_edges.clear()
        self._overlay_node_to_edges.clear()
        self._overlay_label_index.clear()
        self._confidence.clear()
        edge_ids = [eid for eid in edge_ids if eid not in failed]
        return node_ids, edge_ids

    def rollback(self) -> None:
        """Discard all overlay nodes, edges, and confidence data."""
        self._overlay_nodes.clear()
        self._overlay_edges.clear()
        self._overlay_node_to_edges.clear()
        self._overlay_label_index.clear()
        self._confidence.clear()

    def is_overlay_edge(self, edge_id: str) -> bool:
        """Check whether an edge exists in the overlay layer.

        Args:
            edge_id: The edge ID to check.

        Returns:
            True if the edge is in the overlay.
        """
        return edge_id in self._overlay_edges

    def is_overlay_node(self, node_id: str) -> bool:
        """Check whether a node exists in the overlay layer.

        Args:
            node_id: The node ID to check.

        Returns:
            True if the node is in the overlay.
        """
        return node_id in self._overlay_nodes

    def set_confidence(self, edge_id: str, confidence: float) -> None:
        """Store a confidence score for an overlay edge.

        Args:
            edge_id: The edge to annotate.
            confidence: Confidence value in [0, 1].
        """
        self._confidence[edge_id] = confidence

    def get_confidence(self, edge_id: str) -> float:
        """Retrieve the confidence score for an edge.

        Falls back to the confidence stored in edge metadata, then to 1.0.

        Args:
            edge_id: The edge to look up.

        Returns:
            The confidence score.
        """
        if edge_id in self._confidence:
            return self._confidence[edge_id]
        edge = self._overlay_edges.get(edge_id) or self._base.get_edge(edge_id)
        if edge and isinstance(edge.metadata.custom.get("confidence"), (int, float)):
            return float(edge.metadata.custom["confidence"])
        return 1.0

    @property
    def overlay_node_ids(self) -> set[str]:
        """IDs of nodes that exist only in the overlay layer."""
        return set(self._overlay_nodes.keys())

    @property
    def overlay_edge_ids(self) -> set[str]:
        """IDs of edges that exist only in the overlay layer."""
        return set(self._overlay_edges.keys())

    def _resolve_label(self, node_id: str) -> str:
        """Resolve a node ID to its label, with fallback to truncated ID."""
        node = self._overlay_nodes.get(node_id) or self._base.get_node(node_id)
        return node.label if node and node.label else node_id[:8]

    @property
    def labeled_edges(self) -> list[dict[str, str]]:
        """Overlay edges with source/target labels resolved.

        Returns:
            List of dicts with keys: id, source_labels, target_labels, label, confidence.
        """
        result: list[dict[str, str]] = []
        for edge in self._overlay_edges.values():
            result.append({
                "id": edge.id,
                "source_labels": ", ".join(sorted(self._resolve_label(nid) for nid in edge.source_ids)),
                "target_labels": ", ".join(sorted(self._resolve_label(nid) for nid in edge.target_ids)),
                "label": edge.label,
                "confidence": f"{self.get_confidence(edge.id):.2f}",
            })
        return result

    @property
    def base(self) -> Hypergraph:
        """The underlying base graph."""
        return self._base

    def _remove_overlay_edge(self, edge_id: str) -> None:
        """Remove an edge from overlay indexes and clean up confidence data."""
        edge = self._overlay_edges.pop(edge_id, None)
        if edge:
            for nid in edge.node_ids:
                if nid in self._overlay_node_to_edges:
                    self._overlay_node_to_edges[nid].discard(edge_id)
        self._confidence.pop(edge_id, None)
