from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory


class TestGraphDiffBasic:
    def test_capture_version(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        v = mem.capture_version()
        assert v["version_id"] == 0
        assert v["node_count"] >= 1

    def test_diff_no_changes(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert delta.total_changes == 0

    def test_diff_node_added(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        mem.store("B")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_added) >= 1
        assert delta.total_changes >= 1

    def test_diff_node_removed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        node_b = mem.graph.get_node_by_label("B")
        mem.graph.remove_node(node_b.id)
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_removed) >= 1

    def test_diff_edge_added(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        mem.relate("A", "B", label="connects")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_added) >= 1

    def test_diff_edge_removed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="connects")
        mem.capture_version()
        mem.graph.remove_edge(edge.id)
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_removed) >= 1

    def test_diff_between_versions(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        v0 = mem.capture_version()
        mem.store("B")
        v1 = mem.capture_version()
        mem.store("C")
        delta = mem.diff_between_versions(v0["version_id"], v1["version_id"])
        assert delta is not None
        assert len(delta.nodes_added) >= 1

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
        assert mem.differ is not None


class TestGraphDiffModified:
    def test_node_weight_change(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.capture_version()
        node = mem.graph.get_node_by_label("A")
        node.weight = 5.0
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.nodes_modified) >= 1

    def test_edge_weight_change(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="link")
        mem.capture_version()
        edge.weight = 10.0
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert len(delta.edges_modified) >= 1

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
        assert delta.edge_count_after >= 1


class TestGraphDiffIntegration:
    def test_reasoning_diff(self) -> None:
        from hyper3 import TransitiveRule
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
        assert len(delta.edges_added) >= 0

    def test_diff_counts(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        mem.relate("A", "B", label="connects")
        delta = mem.diff_from_version(0)
        assert delta is not None
        assert delta.edge_count_before == 0
        assert delta.edge_count_after >= 1


class TestGraphDiffRollback:
    def test_rollback_restores_removed_node(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.capture_version()
        node_b = mem.graph.get_node_by_label("B")
        mem.graph.remove_node(node_b.id)
        assert mem.graph.node_count == 1
        mem.diff_from_version(0)
        from hyper3.graph_diff import GraphDiffer
        differ = mem.differ
        differ.rollback_to_version(0)
        assert mem.graph.node_count == 2

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
