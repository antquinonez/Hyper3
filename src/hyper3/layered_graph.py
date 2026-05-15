"""Layered graph adapter that merges edges from a primary hypergraph with named secondary layers.

Node operations delegate to the primary graph. Edge operations merge
results from the primary and all registered secondary layers, controlled
by a per-call ``layers`` filter.
"""

from __future__ import annotations

from dataclasses import dataclass

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


@dataclass
class LayerInfo:
    """Metadata and dirtiness tracking for a single secondary layer."""
    name: str
    graph: Hypergraph
    weight: float = 1.0
    derived: bool = True
    _build_primary_node_count: int = 0
    _build_primary_edge_count: int = 0

    def check_dirty(self, primary: Hypergraph) -> bool:
        """Return True if the primary graph has changed since this layer was last marked clean.

        Non-derived layers are never dirty.

        Args:
            primary: The primary hypergraph to compare against.

        Returns:
            Whether this layer is out-of-date relative to the primary graph.
        """
        if not self.derived:
            return False
        return (
            primary.node_count != self._build_primary_node_count
            or primary.edge_count != self._build_primary_edge_count
        )

    def mark_clean(self, primary: Hypergraph) -> None:
        """Snapshot the current primary graph node/edge counts so future dirtiness checks pass.

        Args:
            primary: The primary hypergraph whose counts to record.
        """
        self._build_primary_node_count = primary.node_count
        self._build_primary_edge_count = primary.edge_count


class LayerStack:
    """Read-only adapter that merges edges from a primary hypergraph and N named secondary layers.

    Node operations delegate to the primary graph. Edge operations merge
    results from the primary and all registered secondary layers.

    Secondary layers are registered via ``register()`` and removed via
    ``unregister()``. Each layer has a name, a ``Hypergraph``, an
    optional ``weight`` (for future per-layer activation scaling), and
    a ``derived`` flag (derived layers track dirtiness against the
    primary graph).

    The ``layers`` parameter on edge-access methods controls which
    layers contribute to the result. ``None`` (default) merges all
    registered layers plus the primary. ``["structural"]`` returns
    only primary edges. ``["structural", "semantic"]`` merges primary
    plus the named ``"semantic"`` layer.
    """

    def __init__(self, primary: Hypergraph) -> None:
        """Initialize the layer stack with a primary hypergraph.

        Args:
            primary: The base hypergraph that owns all nodes and serves as the ``"structural"`` layer.
        """
        self._primary = primary
        self._layers: dict[str, LayerInfo] = {}

    def register(
        self,
        name: str,
        graph: Hypergraph,
        *,
        weight: float = 1.0,
        derived: bool = True,
    ) -> None:
        """Register a secondary layer.

        Args:
            name: Unique layer name. Referenced in ``layers`` filters on edge-access methods.
            graph: The hypergraph backing this layer.
            weight: Per-layer activation scaling weight (reserved for future use).
            derived: If True, the layer tracks dirtiness against the primary graph.
        """
        self._layers[name] = LayerInfo(
            name=name,
            graph=graph,
            weight=weight,
            derived=derived,
        )
        if derived:
            self._layers[name].mark_clean(self._primary)

    def unregister(self, name: str) -> bool:
        """Remove a previously registered secondary layer.

        Args:
            name: The layer name to remove.

        Returns:
            True if the layer existed and was removed, False otherwise.
        """
        if name in self._layers:
            del self._layers[name]
            return True
        return False

    def layer(self, name: str) -> Hypergraph | None:
        """Retrieve the hypergraph for a named secondary layer.

        Args:
            name: The layer name.

        Returns:
            The layer's hypergraph, or None if no layer is registered under that name.
        """
        info = self._layers.get(name)
        return info.graph if info else None

    @property
    def layer_names(self) -> list[str]:
        """Names of all registered secondary layers, in insertion order."""
        return list(self._layers.keys())

    @property
    def primary(self) -> Hypergraph:
        """The base hypergraph that owns all nodes."""
        return self._primary

    def layer_dirty(self, name: str) -> bool:
        """Check whether a specific derived layer is dirty relative to the primary graph.

        Args:
            name: The layer name.

        Returns:
            True if the layer is derived and the primary has changed since it was last marked clean.
        """
        info = self._layers.get(name)
        if info is None:
            return False
        return info.check_dirty(self._primary)

    def any_dirty(self) -> bool:
        """Return True if any derived layer is dirty relative to the primary graph."""
        return any(info.check_dirty(self._primary) for info in self._layers.values())

    def _resolve_layers(
        self, layers: list[str] | None
    ) -> list[Hypergraph]:
        """Translate a layer-name filter into a list of concrete hypergraphs.

        Args:
            layers: ``None`` means all layers (primary + secondaries).
                A list of names selects those layers; ``"structural"``
                maps to the primary graph.

        Returns:
            Ordered list of hypergraphs matching the filter.
        """
        if layers is None:
            return [self._primary] + [info.graph for info in self._layers.values()]
        graphs: list[Hypergraph] = []
        if "structural" in layers:
            graphs.append(self._primary)
        for name in layers:
            if name == "structural":
                continue
            info = self._layers.get(name)
            if info:
                graphs.append(info.graph)
        return graphs

    def get_node(self, node_id: str) -> Hypernode | None:
        """Look up a node by ID in the primary graph.

        Args:
            node_id: The internal node identifier.

        Returns:
            The matching Hypernode, or None if not found.
        """
        return self._primary.get_node(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        """Look up a node by human-readable label in the primary graph.

        Args:
            label: The node label string.

        Returns:
            The matching Hypernode, or None if not found.
        """
        return self._primary.get_node_by_label(label)

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        """Look up an edge by ID across the primary and all secondary layers.

        Args:
            edge_id: The internal edge identifier.

        Returns:
            The matching Hyperedge, or None if not found in any layer.
        """
        edge = self._primary.get_edge(edge_id)
        if edge is not None:
            return edge
        for info in self._layers.values():
            edge = info.graph.get_edge(edge_id)
            if edge is not None:
                return edge
        return None

    def incident_edges(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[Hyperedge]:
        """Return edges where the node participates as source or target, merged across layers.

        Args:
            node_id: Internal node identifier.
            layers: Layer-name filter. None merges all layers.

        Returns:
            Combined list of incident edges from the selected layers.
        """
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.incident_edges(node_id))
        return result

    def outgoing_edges(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[Hyperedge]:
        """Return edges where the node is in source_ids, merged across layers.

        Args:
            node_id: Internal node identifier.
            layers: Layer-name filter. None merges all layers.

        Returns:
            Combined list of outgoing edges from the selected layers.
        """
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.outgoing_edges(node_id))
        return result

    def incoming_edges(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[Hyperedge]:
        """Return edges where the node is in target_ids, merged across layers.

        Args:
            node_id: Internal node identifier.
            layers: Layer-name filter. None merges all layers.

        Returns:
            Combined list of incoming edges from the selected layers.
        """
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.incoming_edges(node_id))
        return result

    def neighbors(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[str]:
        """Return deduplicated neighbor node IDs across the selected layers.

        Args:
            node_id: Internal node identifier.
            layers: Layer-name filter. None merges all layers.

        Returns:
            Unique neighbor node IDs from all selected layers.
        """
        graphs = self._resolve_layers(layers)
        ids: set[str] = set()
        for g in graphs:
            ids.update(g.neighbors(node_id))
        return list(ids)

    @property
    def nodes(self) -> list[Hypernode]:
        """All nodes from the primary graph."""
        return self._primary.nodes

    @property
    def edges(self) -> list[Hyperedge]:
        """All edges from the primary graph and every registered secondary layer."""
        result = list(self._primary.edges)
        for info in self._layers.values():
            result.extend(info.graph.edges)
        return result

    @property
    def node_count(self) -> int:
        """Number of nodes in the primary graph."""
        return self._primary.node_count

    @property
    def edge_count(self) -> int:
        """Total edge count across the primary graph and all secondary layers."""
        total = self._primary.edge_count
        for info in self._layers.values():
            total += info.graph.edge_count
        return total

    @property
    def layers_info(self) -> dict[str, LayerInfo]:
        """Snapshot of all registered secondary layers as a name-to-LayerInfo dict."""
        return dict(self._layers)


LayeredGraph = LayerStack
