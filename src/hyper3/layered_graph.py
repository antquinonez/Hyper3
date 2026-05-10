from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class LayeredGraph:
    """Read-only adapter that merges edges from a primary and secondary hypergraph.

    Node operations delegate to the primary graph. Edge operations merge
    results from both layers. The secondary graph typically holds
    embedding-derived semantic edges (``label="semantic_sim"``).

    This adapter implements only the read methods that ``SpreadingActivation``,
    ``ScoringPipeline``, and ``SearchEngine`` call on the graph. No mutation
    methods are provided -- both underlying graphs are managed independently.
    """

    def __init__(self, primary: Hypergraph, secondary: Hypergraph) -> None:
        self._primary = primary
        self._secondary = secondary

    @property
    def primary(self) -> Hypergraph:
        return self._primary

    @property
    def secondary(self) -> Hypergraph:
        return self._secondary

    def get_node(self, node_id: str) -> Hypernode | None:
        return self._primary.get_node(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        return self._primary.get_node_by_label(label)

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        return self._primary.get_edge(edge_id) or self._secondary.get_edge(edge_id)

    def incident_edges(self, node_id: str) -> list[Hyperedge]:
        return self._primary.incident_edges(node_id) + self._secondary.incident_edges(node_id)

    def outgoing_edges(self, node_id: str) -> list[Hyperedge]:
        return self._primary.outgoing_edges(node_id) + self._secondary.outgoing_edges(node_id)

    def incoming_edges(self, node_id: str) -> list[Hyperedge]:
        return self._primary.incoming_edges(node_id) + self._secondary.incoming_edges(node_id)

    def neighbors(self, node_id: str) -> list[str]:
        primary_ids = set(self._primary.neighbors(node_id))
        secondary_ids = set(self._secondary.neighbors(node_id))
        return list(primary_ids | secondary_ids)

    @property
    def nodes(self) -> list[Hypernode]:
        return self._primary.nodes

    @property
    def edges(self) -> list[Hyperedge]:
        return self._primary.edges + self._secondary.edges

    @property
    def node_count(self) -> int:
        return self._primary.node_count

    @property
    def edge_count(self) -> int:
        return self._primary.edge_count + self._secondary.edge_count
