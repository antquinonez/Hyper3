from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.results import _SimpleResultBase


@dataclass
class NodeDelta(_SimpleResultBase):
    """Records a change (addition, removal, or modification) to a single node between graph versions."""

    node_id: str
    node_label: str
    change_type: str
    old_data: Any = None
    new_data: Any = None
    old_weight: float = 0.0
    new_weight: float = 0.0


@dataclass
class EdgeDelta(_SimpleResultBase):
    """Records a change (addition, removal, or modification) to a single edge between graph versions."""

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
    """Complete diff between two graph snapshots, listing all node and edge changes."""

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
    """A point-in-time snapshot of the graph, stored as a versioned checkpoint for diffing and rollback."""

    version_id: int
    timestamp: float
    node_count: int
    edge_count: int
    snapshot: dict[str, Any]


@dataclass
class GraphHistoryResult(_SimpleResultBase):
    """Summary of all captured graph versions with the current version pointer."""

    versions: list[GraphVersion] = field(default_factory=list)
    total_versions: int = 0
    current_version: int = 0


class GraphDiffer:
    """Captures graph versions, computes deltas between snapshots, and supports rollback to prior versions."""

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize with a hypergraph reference, empty version history, and zeroed version counter."""
        self._graph = graph
        self._history: list[GraphVersion] = []
        self._version_counter = 0

    def capture(self) -> GraphVersion:
        """Snapshot the current graph state as a versioned capture."""
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
        """Compute delta between a stored version and the live graph."""
        version = self._find_version(version_id)
        if not version:
            return None
        current = self._graph_snapshot()
        return self._compute_delta(version.snapshot, current)

    def diff_between_versions(self, v1: int, v2: int) -> GraphDelta | None:
        """Compute delta between two stored versions."""
        version_a = self._find_version(v1)
        version_b = self._find_version(v2)
        if not version_a or not version_b:
            return None
        return self._compute_delta(version_a.snapshot, version_b.snapshot)

    def diff_from_snapshot(self, snapshot: dict[str, Any]) -> GraphDelta:
        """Compute delta between a snapshot and the live graph."""
        current = self._graph_snapshot()
        return self._compute_delta(snapshot, current)

    def rollback_to_version(self, version_id: int) -> GraphDelta | None:
        """Restore the graph to a previously captured version."""
        version = self._find_version(version_id)
        if not version:
            return None

        current = self._graph_snapshot()
        delta = self._compute_delta(version.snapshot, current)

        self._remove_extra_edges(version.snapshot)
        self._revert_modified_nodes(delta)
        self._revert_modified_edges(delta)
        self._remove_extra_nodes(version.snapshot)
        self._restore_missing_nodes(version.snapshot)
        self._restore_missing_edges(version.snapshot)

        return delta

    def _remove_extra_edges(self, snapshot: dict[str, Any]) -> None:
        """Remove edges present in the target but not the current state."""
        snapshot_edges = set(snapshot.get("edges", {}).keys())
        for edge in list(self._graph.edges):
            if edge.id not in snapshot_edges:
                self._graph.remove_edge(edge.id)

    def _revert_modified_nodes(self, delta: GraphDelta) -> None:
        """Revert nodes whose data differs from the target state."""
        for nd in delta.nodes_modified:
            node = self._graph.get_node(nd.node_id)
            if node:
                node.weight = nd.old_weight
                node.data = nd.old_data

    def _revert_modified_edges(self, delta: GraphDelta) -> None:
        """Revert edges whose attributes differ from the target state."""
        for ed in delta.edges_modified:
            edge = self._graph.get_edge(ed.edge_id)
            if edge:
                edge.weight = ed.old_weight
                edge.label = ed.old_label

    def _remove_extra_nodes(self, snapshot: dict[str, Any]) -> None:
        """Remove nodes present in the current state but not the target."""
        snapshot_nodes = snapshot.get("nodes", {})
        for node in list(self._graph.nodes):
            if node.id not in snapshot_nodes:
                self._graph.remove_node(node.id)

    def _restore_missing_nodes(self, snapshot: dict[str, Any]) -> None:
        """Re-add nodes present in the target but missing from the current state."""
        snapshot_nodes = snapshot.get("nodes", {})
        for nid, ndata in snapshot_nodes.items():
            if not self._graph.get_node(nid):
                restored = Hypernode(
                    id=nid,
                    label=ndata.get("label", ""),
                    data=ndata.get("data"),
                    weight=ndata.get("weight", 1.0),
                )
                self._graph.add_node(restored)

    def _restore_missing_edges(self, snapshot: dict[str, Any]) -> None:
        """Re-add edges present in the target but missing from the current state."""
        for eid, edata in snapshot.get("edges", {}).items():
            if not self._graph.get_edge(eid):
                self._graph.add_edge(
                    Hyperedge(
                        id=eid,
                        source_ids=frozenset(edata.get("source_ids", set())),
                        target_ids=frozenset(edata.get("target_ids", set())),
                        label=edata.get("label", ""),
                        weight=edata.get("weight", 1.0),
                        data=edata.get("data"),
                    )
                )

    @property
    def history(self) -> GraphHistoryResult:
        """Return the list of captured version identifiers."""
        return GraphHistoryResult(
            versions=list(self._history),
            total_versions=len(self._history),
            current_version=self._version_counter - 1 if self._history else -1,
        )

    def _graph_snapshot(self) -> dict[str, Any]:
        """Capture a full snapshot of node and edge state."""
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
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> GraphDelta:
        """Compare two snapshots and produce a ``GraphDelta``."""
        before_nodes = before.get("nodes", {})
        after_nodes = after.get("nodes", {})
        before_edges = before.get("edges", {})
        after_edges = after.get("edges", {})

        nodes_added, nodes_removed, nodes_modified = self._compute_node_deltas(
            before_nodes, after_nodes,
        )
        edges_added, edges_removed, edges_modified = self._compute_edge_deltas(
            before_edges, after_edges, after_nodes, before_nodes,
        )

        total = (
            len(nodes_added)
            + len(nodes_removed)
            + len(nodes_modified)
            + len(edges_added)
            + len(edges_removed)
            + len(edges_modified)
        )

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

    def _compute_node_deltas(
        self,
        before_nodes: dict[str, Any],
        after_nodes: dict[str, Any],
    ) -> tuple[list[NodeDelta], list[NodeDelta], list[NodeDelta]]:
        """Compute node-level additions, removals, and modifications."""
        added: list[NodeDelta] = []
        removed: list[NodeDelta] = []
        modified: list[NodeDelta] = []

        for nid, ndata in after_nodes.items():
            if nid not in before_nodes:
                added.append(
                    NodeDelta(
                        node_id=nid,
                        node_label=ndata.get("label", ""),
                        change_type="added",
                        new_data=ndata.get("data"),
                        new_weight=ndata.get("weight", 0.0),
                    )
                )
            else:
                old = before_nodes[nid]
                if old.get("weight") != ndata.get("weight") or old.get("data") != ndata.get("data"):
                    modified.append(
                        NodeDelta(
                            node_id=nid,
                            node_label=ndata.get("label", ""),
                            change_type="modified",
                            old_data=old.get("data"),
                            new_data=ndata.get("data"),
                            old_weight=old.get("weight", 0.0),
                            new_weight=ndata.get("weight", 0.0),
                        )
                    )

        for nid, ndata in before_nodes.items():
            if nid not in after_nodes:
                removed.append(
                    NodeDelta(
                        node_id=nid,
                        node_label=ndata.get("label", ""),
                        change_type="removed",
                        old_data=ndata.get("data"),
                        old_weight=ndata.get("weight", 0.0),
                    )
                )

        return added, removed, modified

    def _compute_edge_deltas(
        self,
        before_edges: dict[str, Any],
        after_edges: dict[str, Any],
        after_nodes: dict[str, Any],
        before_nodes: dict[str, Any],
    ) -> tuple[list[EdgeDelta], list[EdgeDelta], list[EdgeDelta]]:
        """Compute edge-level additions, removals, and modifications."""
        added: list[EdgeDelta] = []
        removed: list[EdgeDelta] = []
        modified: list[EdgeDelta] = []

        for eid, edata in after_edges.items():
            if eid not in before_edges:
                added.append(
                    EdgeDelta(
                        edge_id=eid,
                        change_type="added",
                        new_label=edata.get("label", ""),
                        new_weight=edata.get("weight", 0.0),
                        source_label=self._resolve_edge_labels(edata, "source", after_nodes),
                        target_label=self._resolve_edge_labels(edata, "target", after_nodes),
                    )
                )
            else:
                old = before_edges[eid]
                if old.get("weight") != edata.get("weight") or old.get("label") != edata.get("label"):
                    modified.append(
                        EdgeDelta(
                            edge_id=eid,
                            change_type="modified",
                            old_label=old.get("label", ""),
                            new_label=edata.get("label", ""),
                            old_weight=old.get("weight", 0.0),
                            new_weight=edata.get("weight", 0.0),
                        )
                    )

        for eid, edata in before_edges.items():
            if eid not in after_edges:
                removed.append(
                    EdgeDelta(
                        edge_id=eid,
                        change_type="removed",
                        old_label=edata.get("label", ""),
                        old_weight=edata.get("weight", 0.0),
                        source_label=self._resolve_edge_labels(edata, "source", before_nodes),
                        target_label=self._resolve_edge_labels(edata, "target", before_nodes),
                    )
                )

        return added, removed, modified

    def _resolve_edge_labels(
        self,
        edata: dict[str, Any],
        direction: str,
        node_map: dict[str, Any],
    ) -> str:
        """Resolve edge node IDs to labels for readability."""
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
        """Look up a version by index or ID; raises ``ValueError`` if not found."""
        for v in self._history:
            if v.version_id == version_id:
                return v
        return None

    def _now(self) -> float:
        """Return the current timestamp as a float."""
        return time.time()
