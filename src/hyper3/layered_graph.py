from __future__ import annotations

from dataclasses import dataclass

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


@dataclass
class LayerInfo:
    name: str
    graph: Hypergraph
    weight: float = 1.0
    derived: bool = True
    _build_primary_node_count: int = 0
    _build_primary_edge_count: int = 0

    def check_dirty(self, primary: Hypergraph) -> bool:
        if not self.derived:
            return False
        return (
            primary.node_count != self._build_primary_node_count
            or primary.edge_count != self._build_primary_edge_count
        )

    def mark_clean(self, primary: Hypergraph) -> None:
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
        self._layers[name] = LayerInfo(
            name=name,
            graph=graph,
            weight=weight,
            derived=derived,
        )
        if derived:
            self._layers[name].mark_clean(self._primary)

    def unregister(self, name: str) -> bool:
        if name in self._layers:
            del self._layers[name]
            return True
        return False

    def layer(self, name: str) -> Hypergraph | None:
        info = self._layers.get(name)
        return info.graph if info else None

    @property
    def layer_names(self) -> list[str]:
        return list(self._layers.keys())

    @property
    def primary(self) -> Hypergraph:
        return self._primary

    def layer_dirty(self, name: str) -> bool:
        info = self._layers.get(name)
        if info is None:
            return False
        return info.check_dirty(self._primary)

    def any_dirty(self) -> bool:
        return any(info.check_dirty(self._primary) for info in self._layers.values())

    def _resolve_layers(
        self, layers: list[str] | None
    ) -> list[Hypergraph]:
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
        return self._primary.get_node(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        return self._primary.get_node_by_label(label)

    def get_edge(self, edge_id: str) -> Hyperedge | None:
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
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.incident_edges(node_id))
        return result

    def outgoing_edges(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[Hyperedge]:
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.outgoing_edges(node_id))
        return result

    def incoming_edges(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[Hyperedge]:
        graphs = self._resolve_layers(layers)
        result: list[Hyperedge] = []
        for g in graphs:
            result.extend(g.incoming_edges(node_id))
        return result

    def neighbors(
        self, node_id: str, *, layers: list[str] | None = None
    ) -> list[str]:
        graphs = self._resolve_layers(layers)
        ids: set[str] = set()
        for g in graphs:
            ids.update(g.neighbors(node_id))
        return list(ids)

    @property
    def nodes(self) -> list[Hypernode]:
        return self._primary.nodes

    @property
    def edges(self) -> list[Hyperedge]:
        result = list(self._primary.edges)
        for info in self._layers.values():
            result.extend(info.graph.edges)
        return result

    @property
    def node_count(self) -> int:
        return self._primary.node_count

    @property
    def edge_count(self) -> int:
        total = self._primary.edge_count
        for info in self._layers.values():
            total += info.graph.edge_count
        return total

    @property
    def layers_info(self) -> dict[str, LayerInfo]:
        return dict(self._layers)


LayeredGraph = LayerStack
