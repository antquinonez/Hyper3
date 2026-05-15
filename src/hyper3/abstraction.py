"""AbstractionNavigator: hierarchical collapse and expansion of subgraphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
)
from hyper3.results import _SimpleResultBase


@dataclass
class AbstractionMapping(_SimpleResultBase):
    """Tracks the relationship between a summary node and the detail nodes it represents."""

    summary_node_id: str
    summary_label: str
    detail_node_ids: list[str]
    detail_labels: list[str]
    layer: AbstractionLayer


@dataclass
class AbstractionSummary(_SimpleResultBase):
    """Result of collapsing a subgraph into a single summary node."""

    summary_node: Hypernode
    mapping: AbstractionMapping
    edges_collapsed: int
    internal_edge_count: int
    external_connections: int


@dataclass
class ExpandResult(_SimpleResultBase):
    """Result of expanding a summary node back into its original detail nodes and edges."""

    expanded_nodes: list[str] = field(default_factory=list)
    expanded_edges: list[str] = field(default_factory=list)
    summary_removed: bool = False


class AbstractionNavigator:
    """Collapses subgraphs into summary nodes and expands them back, enabling hierarchical abstraction."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize with a reference hypergraph and empty mappings."""
        self._graph = graph
        self._mappings: dict[str, AbstractionMapping] = {}

    @property
    def mappings(self) -> dict[str, AbstractionMapping]:
        """Return a copy of all active summary-to-detail mappings."""
        return dict(self._mappings)

    def _classify_edges(
        self, node_ids: set[str]
    ) -> tuple[
        dict[str, list[tuple[str, float, Any]]],
        dict[str, list[tuple[str, float, Any]]],
        int,
    ]:
        """Partition edges into internal, incoming-external, and outgoing-external relative to *node_ids*."""
        external_edges_in: dict[str, list[tuple[str, float, Any]]] = {}
        external_edges_out: dict[str, list[tuple[str, float, Any]]] = {}
        internal_count = 0

        for edge in list(self._graph.edges):
            src_in = edge.source_ids & node_ids
            tgt_in = edge.target_ids & node_ids

            if src_in and tgt_in:
                internal_count += 1
                continue

            if src_in and not tgt_in:
                for external_tgt in edge.target_ids - node_ids:
                    external_edges_out.setdefault(external_tgt, []).append(
                        (edge.label, edge.weight, edge.data),
                    )
            elif tgt_in and not src_in:
                for external_src in edge.source_ids - node_ids:
                    external_edges_in.setdefault(external_src, []).append(
                        (edge.label, edge.weight, edge.data),
                    )

        return external_edges_in, external_edges_out, internal_count

    def _rewire_external_edges(
        self,
        external_edges_in: dict[str, list[tuple[str, float, Any]]],
        external_edges_out: dict[str, list[tuple[str, float, Any]]],
        summary_node_id: str,
    ) -> None:
        """Create new edges connecting external nodes to the summary node."""
        for ext_src, edge_infos in external_edges_in.items():
            edge_labels_seen: set[str] = set()
            for elabel, eweight, edata in edge_infos:
                if elabel not in edge_labels_seen:
                    self._graph.add_edge(
                        Hyperedge(
                            source_ids=frozenset({ext_src}),
                            target_ids=frozenset({summary_node_id}),
                            label=elabel,
                            weight=eweight,
                            data=edata,
                        )
                    )
                    edge_labels_seen.add(elabel)

        for ext_tgt, edge_infos in external_edges_out.items():
            edge_labels_seen: set[str] = set()
            for elabel, eweight, edata in edge_infos:
                if elabel not in edge_labels_seen:
                    self._graph.add_edge(
                        Hyperedge(
                            source_ids=frozenset({summary_node_id}),
                            target_ids=frozenset({ext_tgt}),
                            label=elabel,
                            weight=eweight,
                            data=edata,
                        )
                    )
                    edge_labels_seen.add(elabel)

    def _collect_expanded_nodes(
        self, mapping: AbstractionMapping
    ) -> list[str]:
        """Collect IDs of detail nodes that still exist for an expansion."""
        expanded_nodes: list[str] = []
        for nid in mapping.detail_node_ids:
            existing = self._graph.get_node(nid)
            if not existing:
                for lbl in mapping.detail_labels:
                    check = self._graph.get_node_by_label(lbl)
                    if check and check.id == nid:
                        expanded_nodes.append(nid)
                        break
            else:
                expanded_nodes.append(nid)
        return expanded_nodes

    def _expand_summary_edges(
        self, summary_node: Hypernode, mapping: AbstractionMapping
    ) -> list[str]:
        """Recreate edges from external nodes to detail nodes, then remove summary edges."""
        expanded_edges: list[str] = []
        summary_edges = list(self._graph.incident_edges(summary_node.id))
        for edge in summary_edges:
            is_incoming = summary_node.id in edge.target_ids
            for external_id in edge.source_ids | edge.target_ids:
                if external_id == summary_node.id:
                    continue
                for detail_id in mapping.detail_node_ids:
                    detail_node = self._graph.get_node(detail_id)
                    if not detail_node:
                        continue
                    if is_incoming:
                        new_edge = Hyperedge(
                            source_ids=frozenset({external_id}),
                            target_ids=frozenset({detail_id}),
                            label=edge.label,
                            weight=edge.weight,
                            data=edge.data,
                        )
                    else:
                        new_edge = Hyperedge(
                            source_ids=frozenset({detail_id}),
                            target_ids=frozenset({external_id}),
                            label=edge.label,
                            weight=edge.weight,
                            data=edge.data,
                        )
                    self._graph.add_edge(new_edge)
                    expanded_edges.append(new_edge.id)
        for edge in summary_edges:
            self._graph.remove_edge(edge.id)
        return expanded_edges

    def collapse_subgraph(
        self,
        node_labels: set[str],
        *,
        summary_label: str | None = None,
        summary_data: Any = None,
        layer: AbstractionLayer = AbstractionLayer.SUMMARY,
    ) -> AbstractionSummary | None:
        """Collapse a set of nodes into a single summary node, rewiring external edges."""
        node_ids: set[str] = set()
        for lbl in node_labels:
            node = self._graph.get_node_by_label(lbl)
            if node:
                node_ids.add(node.id)

        if not node_ids:
            return None

        label = summary_label or "+".join(sorted(node_labels)[:3])
        summary_node = Hypernode(
            label=label,
            data=summary_data,
            metadata=Metadata(abstraction_layer=layer),
        )
        self._graph.add_node(summary_node)

        external_edges_in, external_edges_out, internal_count = (
            self._classify_edges(node_ids)
        )

        for edge in list(self._graph.edges):
            if edge.source_ids & node_ids or edge.target_ids & node_ids:
                self._graph.remove_edge(edge.id)

        self._rewire_external_edges(
            external_edges_in, external_edges_out, summary_node.id
        )

        mapping = AbstractionMapping(
            summary_node_id=summary_node.id,
            summary_label=label,
            detail_node_ids=sorted(node_ids),
            detail_labels=sorted(node_labels),
            layer=layer,
        )
        self._mappings[summary_node.id] = mapping

        return AbstractionSummary(
            summary_node=summary_node,
            mapping=mapping,
            edges_collapsed=internal_count + len(external_edges_in) + len(external_edges_out),
            internal_edge_count=internal_count,
            external_connections=len(external_edges_in) + len(external_edges_out),
        )

    def expand_node(self, summary_label: str) -> ExpandResult | None:
        """Expand a summary node back into its original detail nodes and edges."""
        summary_node = self._graph.get_node_by_label(summary_label)
        if not summary_node:
            return None

        mapping = self._mappings.get(summary_node.id)
        if not mapping:
            return None

        expanded_nodes = self._collect_expanded_nodes(mapping)
        expanded_edges = self._expand_summary_edges(summary_node, mapping)

        self._graph.remove_node(summary_node.id)
        del self._mappings[summary_node.id]

        return ExpandResult(
            expanded_nodes=expanded_nodes,
            expanded_edges=expanded_edges,
            summary_removed=True,
        )

    def get_summary_for(self, label: str) -> AbstractionMapping | None:
        """Return the abstraction mapping for a node, or ``None``."""
        node = self._graph.get_node_by_label(label)
        if not node:
            return None
        return self._mappings.get(node.id)

    def get_summary_children(self, summary_label: str) -> list[str]:
        """Return the detail labels hidden under a summary node."""
        mapping = self.get_summary_for(summary_label)
        if not mapping:
            return []
        return mapping.detail_labels

    def list_summaries(self) -> list[AbstractionMapping]:
        """Return all active abstraction mappings."""
        return list(self._mappings.values())

    def nodes_at_layer(self, layer: AbstractionLayer) -> list[Hypernode]:
        """Return all nodes at a given abstraction layer."""
        return [n for n in self._graph.nodes if n.metadata.abstraction_layer == layer]
