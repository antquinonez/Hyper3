from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.results import _SimpleResultBase


@dataclass
class NodeDelta(_SimpleResultBase):
    node_id: str
    node_label: str
    change_type: str
    old_data: Any = None
    new_data: Any = None
    old_weight: float = 0.0
    new_weight: float = 0.0


@dataclass
class EdgeDelta(_SimpleResultBase):
    edge_id: str
    change_type: str
    old_label: str = ""
    new_label: str = ""
    old_weight: float = 0.0
    new_weight: float = 0.0
    source_label: str = ""
    target_label: str = ""


@dataclass
class GraphDelta(_SimpleResultBase):
    nodes_added: list[NodeDelta] = field(default_factory=list)
    nodes_removed: list[NodeDelta] = field(default_factory=list)
    nodes_modified: list[NodeDelta] = field(default_factory=list)
    edges_added: list[EdgeDelta] = field(default_factory=list)
    edges_removed: list[EdgeDelta] = field(default_factory=list)
    edges_modified: list[EdgeDelta] = field(default_factory=list)
    total_changes: int = 0
    node_count_before: int = 0
    node_count_after: int = 0
    edge_count_before: int = 0
    edge_count_after: int = 0


@dataclass
class GraphVersion(_SimpleResultBase):
    version_id: int
    timestamp: float
    node_count: int
    edge_count: int
    snapshot: dict[str, Any]


@dataclass
class GraphHistoryResult(_SimpleResultBase):
    versions: list[GraphVersion] = field(default_factory=list)
    total_versions: int = 0
    current_version: int = 0


class GraphDiffer:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._history: list[GraphVersion] = []
        self._version_counter = 0

    def capture(self) -> GraphVersion:
        snapshot = self._graph_snapshot()
        version = GraphVersion(
            version_id=self._version_counter,
            timestamp=self._now(),
            node_count=snapshot["node_count"],
            edge_count=snapshot["edge_count"],
            snapshot=snapshot,
        )
        self._history.append(version)
        self._version_counter += 1
        return version

    def diff_from_version(self, version_id: int) -> GraphDelta | None:
        version = self._find_version(version_id)
        if not version:
            return None
        current = self._graph_snapshot()
        return self._compute_delta(version.snapshot, current)

    def diff_between_versions(self, v1: int, v2: int) -> GraphDelta | None:
        version_a = self._find_version(v1)
        version_b = self._find_version(v2)
        if not version_a or not version_b:
            return None
        return self._compute_delta(version_a.snapshot, version_b.snapshot)

    def diff_from_snapshot(self, snapshot: dict[str, Any]) -> GraphDelta:
        current = self._graph_snapshot()
        return self._compute_delta(snapshot, current)

    def rollback_to_version(self, version_id: int) -> GraphDelta | None:
        version = self._find_version(version_id)
        if not version:
            return None

        current = self._graph_snapshot()
        delta = self._compute_delta(version.snapshot, current)

        snapshot_edges = set(version.snapshot.get("edges", {}).keys())
        for edge in list(self._graph.edges):
            if edge.id not in snapshot_edges:
                self._graph.remove_edge(edge.id)

        for nd in delta.nodes_modified:
            node = self._graph.get_node(nd.node_id)
            if node:
                node.weight = nd.old_weight
                node.data = nd.old_data

        for ed in delta.edges_modified:
            edge = self._graph.get_edge(ed.edge_id)
            if edge:
                edge.weight = ed.old_weight
                edge.label = ed.old_label

        snapshot_nodes = version.snapshot.get("nodes", {})
        for node in list(self._graph.nodes):
            if node.id not in snapshot_nodes:
                self._graph.remove_node(node.id)

        for nid, ndata in snapshot_nodes.items():
            if not self._graph.get_node(nid):
                restored = Hypernode(
                    id=nid,
                    label=ndata.get("label", ""),
                    data=ndata.get("data"),
                    weight=ndata.get("weight", 1.0),
                )
                self._graph.add_node(restored)

        for eid, edata in version.snapshot.get("edges", {}).items():
            if not self._graph.get_edge(eid):
                self._graph.add_edge(Hyperedge(
                    id=eid,
                    source_ids=frozenset(edata.get("source_ids", set())),
                    target_ids=frozenset(edata.get("target_ids", set())),
                    label=edata.get("label", ""),
                    weight=edata.get("weight", 1.0),
                    data=edata.get("data"),
                ))

        return delta

    @property
    def history(self) -> GraphHistoryResult:
        return GraphHistoryResult(
            versions=list(self._history),
            total_versions=len(self._history),
            current_version=self._version_counter - 1 if self._history else -1,
        )

    def _graph_snapshot(self) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        for node in self._graph.nodes:
            nodes[node.id] = {
                "label": node.label,
                "data": node.data,
                "weight": node.weight,
                "access_count": node.access_count,
            }

        edges: dict[str, dict[str, Any]] = {}
        for edge in self._graph.edges:
            edges[edge.id] = {
                "label": edge.label,
                "weight": edge.weight,
                "data": edge.data,
                "source_ids": set(edge.source_ids),
                "target_ids": set(edge.target_ids),
            }

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def _compute_delta(
        self, before: dict[str, Any], after: dict[str, Any],
    ) -> GraphDelta:
        before_nodes = before.get("nodes", {})
        after_nodes = after.get("nodes", {})
        before_edges = before.get("edges", {})
        after_edges = after.get("edges", {})

        nodes_added: list[NodeDelta] = []
        nodes_removed: list[NodeDelta] = []
        nodes_modified: list[NodeDelta] = []

        for nid, ndata in after_nodes.items():
            if nid not in before_nodes:
                nodes_added.append(NodeDelta(
                    node_id=nid,
                    node_label=ndata.get("label", ""),
                    change_type="added",
                    new_data=ndata.get("data"),
                    new_weight=ndata.get("weight", 0.0),
                ))
            else:
                old = before_nodes[nid]
                if old.get("weight") != ndata.get("weight") or old.get("data") != ndata.get("data"):
                    nodes_modified.append(NodeDelta(
                        node_id=nid,
                        node_label=ndata.get("label", ""),
                        change_type="modified",
                        old_data=old.get("data"),
                        new_data=ndata.get("data"),
                        old_weight=old.get("weight", 0.0),
                        new_weight=ndata.get("weight", 0.0),
                    ))

        for nid, ndata in before_nodes.items():
            if nid not in after_nodes:
                nodes_removed.append(NodeDelta(
                    node_id=nid,
                    node_label=ndata.get("label", ""),
                    change_type="removed",
                    old_data=ndata.get("data"),
                    old_weight=ndata.get("weight", 0.0),
                ))

        edges_added: list[EdgeDelta] = []
        edges_removed: list[EdgeDelta] = []
        edges_modified: list[EdgeDelta] = []

        for eid, edata in after_edges.items():
            if eid not in before_edges:
                edges_added.append(EdgeDelta(
                    edge_id=eid,
                    change_type="added",
                    new_label=edata.get("label", ""),
                    new_weight=edata.get("weight", 0.0),
                    source_label=self._resolve_edge_labels(edata, "source", after_nodes),
                    target_label=self._resolve_edge_labels(edata, "target", after_nodes),
                ))
            else:
                old = before_edges[eid]
                if old.get("weight") != edata.get("weight") or old.get("label") != edata.get("label"):
                    edges_modified.append(EdgeDelta(
                        edge_id=eid,
                        change_type="modified",
                        old_label=old.get("label", ""),
                        new_label=edata.get("label", ""),
                        old_weight=old.get("weight", 0.0),
                        new_weight=edata.get("weight", 0.0),
                    ))

        for eid, edata in before_edges.items():
            if eid not in after_edges:
                edges_removed.append(EdgeDelta(
                    edge_id=eid,
                    change_type="removed",
                    old_label=edata.get("label", ""),
                    old_weight=edata.get("weight", 0.0),
                    source_label=self._resolve_edge_labels(edata, "source", before_nodes),
                    target_label=self._resolve_edge_labels(edata, "target", before_nodes),
                ))

        total = (len(nodes_added) + len(nodes_removed) + len(nodes_modified)
                 + len(edges_added) + len(edges_removed) + len(edges_modified))

        return GraphDelta(
            nodes_added=nodes_added,
            nodes_removed=nodes_removed,
            nodes_modified=nodes_modified,
            edges_added=edges_added,
            edges_removed=edges_removed,
            edges_modified=edges_modified,
            total_changes=total,
            node_count_before=len(before_nodes),
            node_count_after=len(after_nodes),
            edge_count_before=len(before_edges),
            edge_count_after=len(after_edges),
        )

    def _resolve_edge_labels(
        self, edata: dict[str, Any], direction: str, node_map: dict[str, Any],
    ) -> str:
        ids = edata.get(f"{direction}_ids", set())
        labels: list[str] = []
        for nid in ids:
            ndata = node_map.get(nid)
            if ndata:
                labels.append(ndata.get("label", nid[:8]))
            else:
                labels.append(nid[:8])
        return ",".join(labels)

    def _find_version(self, version_id: int) -> GraphVersion | None:
        for v in self._history:
            if v.version_id == version_id:
                return v
        return None

    def _now(self) -> float:
        return time.time()
