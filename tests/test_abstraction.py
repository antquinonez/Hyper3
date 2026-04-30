from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory


class TestAbstractionBasic:
    def test_collapse_subgraph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="connects")
        mem.relate("B", "C", label="connects")
        result = mem.collapse_subgraph({"B", "C"}, summary_label="BC")
        assert result is not None
        assert result.summary_node.label == "BC"
        assert len(result.mapping.detail_labels) == 2

    def test_collapse_empty_set(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.collapse_subgraph(set())
        assert result is None

    def test_collapse_with_external_connections(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        mem.store("A")
        mem.store("B")
        mem.relate("X", "A", label="feeds")
        mem.relate("A", "B", label="internal")
        result = mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        assert result is not None
        assert result.external_connections >= 1

    def test_expand_summary(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connects")
        mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        result = mem.expand_summary("AB")
        assert result is not None
        assert result.summary_removed is True

    def test_expand_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.expand_summary("ghost")
        assert result is None

    def test_list_summaries(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="x")
        mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        summaries = mem.list_summaries()
        assert len(summaries) >= 1
        assert summaries[0].summary_label == "AB"

    def test_list_summaries_empty(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        summaries = mem.list_summaries()
        assert summaries == []


class TestAbstractionNavigator:
    def test_collapse_preserves_external_edges(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("ext_in")
        mem.store("A")
        mem.store("B")
        mem.store("ext_out")
        mem.relate("ext_in", "A", label="feeds")
        mem.relate("A", "B", label="internal")
        mem.relate("B", "ext_out", label="outputs")
        mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        summary = mem.graph.get_node_by_label("AB")
        assert summary is not None
        edges_in = [e for e in mem.graph.edges if summary.id in e.target_ids]
        edges_out = [e for e in mem.graph.edges if summary.id in e.source_ids]
        assert len(edges_in) >= 1
        assert len(edges_out) >= 1

    def test_collapse_removes_internal_edges(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="internal")
        mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        summary = mem.graph.get_node_by_label("AB")
        assert summary is not None
        internal_edges = [
            e for e in mem.graph.edges
            if e.source_ids == frozenset({summary.id}) and e.target_ids == frozenset({summary.id})
        ]
        assert len(internal_edges) == 0

    def test_expand_restores_external_connections(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        mem.store("A")
        mem.store("B")
        mem.relate("X", "A", label="feeds")
        mem.relate("A", "B", label="internal")
        mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        mem.expand_summary("AB")
        a_edges = mem.graph.edges_for(mem.graph.get_node_by_label("A").id)
        assert len(a_edges) >= 1

    def test_abstraction_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.abstraction is None
        mem.collapse_subgraph({"anything"}, summary_label="S")
        assert mem.abstraction is not None

    def test_nodes_at_layer(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import AbstractionLayer
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("detail_node")
        nav = AbstractionNavigator(mem.graph)
        result = nav.nodes_at_layer(AbstractionLayer.DETAIL)
        assert isinstance(result, list)

    def test_multiple_collapses(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.store("D")
        mem.relate("A", "B", label="x")
        mem.relate("C", "D", label="y")
        r1 = mem.collapse_subgraph({"A", "B"}, summary_label="AB")
        r2 = mem.collapse_subgraph({"C", "D"}, summary_label="CD")
        assert r1 is not None
        assert r2 is not None
        summaries = mem.list_summaries()
        assert len(summaries) == 2
