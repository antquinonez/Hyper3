from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory, TransitiveRule
from hyper3.graph_diff import GraphDiffer, GraphHistoryResult, GraphVersion


class TestGraphDiffBasic:
    def test_capture_version(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        v = mem.capture_version()
        assert v["version_id"] == 0
        assert v["node_count"] == 1
        assert v["edge_count"] == 0

    def test_diff_no_changes(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert delta.total_changes == 0
        assert delta.node_count_before == 1
        assert delta.node_count_after == 1

    def test_diff_node_added(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_added) == 1
        assert delta.total_changes == 1
        assert delta.nodes_added[0].change_type == "added"
        assert delta.nodes_added[0].node_label == "B"

    def test_diff_node_removed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        node_b = mem.graph.get_node_by_label("B")
        mem.graph.remove_node(node_b.id)
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_removed) == 1
        assert delta.nodes_removed[0].node_label == "B"

    def test_diff_edge_added(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        mem.relate("A", "B", label="connects")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_added) == 1
        assert delta.edge_count_after == 1
        assert delta.edges_added[0].new_label == "connects"
        assert delta.edges_added[0].source_label == "A"
        assert delta.edges_added[0].target_label == "B"

    def test_diff_edge_removed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="connects")
        mem.capture_version()
        mem.graph.remove_edge(edge.id)
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_removed) == 1
        assert delta.edges_removed[0].old_label == "connects"

    def test_diff_between_versions(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        v0 = mem.capture_version()
        mem.store("B")
        v1 = mem.capture_version()
        mem.store("C")
        delta = mem.diff_between_versions(v0["version_id"], v1["version_id"])
        assert delta is not None
        assert len(delta.nodes_added) == 1
        assert delta.nodes_added[0].node_label == "B"

    def test_diff_between_versions_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.capture_version()
        delta = mem.diff_between_versions(0, 999)
        assert delta is None

    def test_diff_nonexistent_version(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        delta = mem.diff_from_version(999)
        assert delta is None

    def test_version_history(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        mem.capture_version()
        history = mem.version_history()
        assert history.total_versions == 2
        assert history.current_version == 1
        assert len(history.versions) == 2

    def test_differ_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.differ is None
        mem.capture_version()
        assert isinstance(mem.differ, GraphDiffer)
        assert mem.differ.history.total_versions == 1


class TestGraphDiffModified:
    def test_node_weight_change(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        node = mem.graph.get_node_by_label("A")
        node.weight = 5.0
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_modified) == 1
        assert delta.nodes_modified[0].old_weight == 1.0
        assert delta.nodes_modified[0].new_weight == 5.0

    def test_edge_weight_change(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="link")
        mem.capture_version()
        edge.weight = 10.0
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_modified) == 1
        assert delta.edges_modified[0].old_weight == 1.0
        assert delta.edges_modified[0].new_weight == 10.0

    def test_multiple_changes(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="link")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert delta.node_count_before == 1
        assert delta.node_count_after == 3
        assert len(delta.nodes_added) == 2
        assert len(delta.edges_added) == 1
        assert delta.edge_count_after == 1
        assert delta.total_changes == 3


class TestGraphDiffIntegration:
    def test_reasoning_diff(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.capture_version()
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="transitively_implies"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_added) == 1
        assert delta.edges_added[0].new_label == "transitively_implies"

    def test_diff_counts(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        mem.relate("A", "B", label="connects")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert delta.edge_count_before == 0
        assert delta.edge_count_after == 1


class TestGraphDiffRollback:
    def test_rollback_restores_removed_node(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        node_b = mem.graph.get_node_by_label("B")
        mem.graph.remove_node(node_b.id)
        assert mem.graph.node_count == 1
        mem.differ.rollback_to_version(0)
        assert mem.graph.node_count == 2
        assert mem.graph.get_node_by_label("B") is not None

    def test_rollback_restores_removed_edge(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="connects")
        mem.capture_version()
        mem.graph.remove_edge(edge.id)
        assert mem.graph.edge_count == 0
        mem.differ.rollback_to_version(0)
        assert mem.graph.edge_count == 1
        restored_edge = list(mem.graph.edges)[0]
        assert restored_edge.label == "connects"
        assert mem.graph.get_node(list(restored_edge.source_ids)[0]).label == "A"
        assert mem.graph.get_node(list(restored_edge.target_ids)[0]).label == "B"

    def test_rollback_restores_modified_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        node = mem.graph.get_node_by_label("A")
        node.weight = 1.0
        mem.capture_version()
        node.weight = 99.0
        mem.differ.rollback_to_version(0)
        node_after = mem.graph.get_node_by_label("A")
        assert node_after.weight == 1.0

    def test_rollback_nonexistent_version_returns_none(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.capture_version()
        result = mem.differ.rollback_to_version(999)
        assert result is None

    def test_rollback_removes_added_edges(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        mem.relate("A", "B", label="new_edge")
        assert mem.graph.edge_count == 1
        mem.differ.rollback_to_version(0)
        assert mem.graph.edge_count == 0
        assert not any(e.label == "new_edge" for e in mem.graph.edges)

    def test_rollback_removes_added_nodes(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        assert mem.graph.node_count == 2
        mem.differ.rollback_to_version(0)
        assert mem.graph.node_count == 1
        assert mem.graph.get_node_by_label("A") is not None
        assert mem.graph.get_node_by_label("B") is None

    def test_rollback_restores_modified_edge_label_and_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="original", weight=2.0)
        mem.capture_version()
        edge.weight = 10.0
        edge.label = "changed"
        mem.differ.rollback_to_version(0)
        edge_after = mem.graph.get_edge(edge.id)
        assert edge_after is not None
        assert edge_after.weight == 2.0
        assert edge_after.label == "original"


class TestGraphDiffSnapshot:
    def test_diff_from_empty_snapshot(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        snap = {"nodes": {}, "edges": {}}
        differ = GraphDiffer(mem.graph)
        delta = differ.diff_from_snapshot(snap)
        assert len(delta.nodes_added) == 2
        assert delta.node_count_before == 0

    def test_diff_between_versions_first_has_more(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        v0 = mem.capture_version()
        mem.graph.remove_node(mem.graph.get_node_by_label("B").id)
        v1 = mem.capture_version()
        delta = mem.diff_between_versions(v0["version_id"], v1["version_id"])
        assert delta is not None
        assert len(delta.nodes_removed) == 1
        assert delta.node_count_before == 2
        assert delta.node_count_after == 1
        assert delta.nodes_removed[0].node_label == "B"


class TestResolveEdgeLabelsFallback:
    def test_resolve_labels_missing_node(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        differ = GraphDiffer(mem.graph)
        edata = {"source_ids": {"nonexistent_id"}, "target_ids": set()}
        result = differ._resolve_edge_labels(edata, "source", {})
        assert len(result) == 8


class TestGraphHistoryResultDataclass:
    def test_defaults(self) -> None:
        r = GraphHistoryResult()
        assert r.versions == []
        assert r.total_versions == 0
        assert r.current_version == 0

    def test_with_values(self) -> None:
        v = GraphVersion(version_id=0, timestamp=1.0, node_count=5, edge_count=3, snapshot={})
        r = GraphHistoryResult(versions=[v], total_versions=1, current_version=0)
        assert len(r.versions) == 1
        assert r.versions[0].version_id == 0
        assert r.total_versions == 1
        assert r.current_version == 0

    def test_bracket_access(self) -> None:
        r = GraphHistoryResult(total_versions=3, current_version=2)
        assert r["total_versions"] == 3
        assert r["current_version"] == 2

    def test_keys(self) -> None:
        r = GraphHistoryResult()
        assert set(r.keys()) == {"versions", "total_versions", "current_version"}

    def test_contains(self) -> None:
        r = GraphHistoryResult(total_versions=1)
        assert "total_versions" in r
        assert "current_version" in r
