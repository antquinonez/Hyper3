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
        a_edges = mem.graph.incident_edges(mem.graph.get_node_by_label("A").id)
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


class TestAbstractionCoverage:
    def test_mappings_property(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import Hypergraph, Hypernode

        graph = Hypergraph()
        nav = AbstractionNavigator(graph)
        assert nav.mappings == {}
        graph.add_node(Hypernode(label="A"))
        graph.add_node(Hypernode(label="B"))
        nav.collapse_subgraph({"A", "B"}, summary_label="AB")
        mappings = nav.mappings
        assert len(mappings) == 1
        assert all(m.summary_label == "AB" for m in mappings.values())

    def test_expand_node_no_mapping(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import Hypergraph, Hypernode

        graph = Hypergraph()
        nav = AbstractionNavigator(graph)
        graph.add_node(Hypernode(label="orphan"))
        result = nav.expand_node("orphan")
        assert result is None

    def test_expand_with_removed_detail_and_outgoing_edge(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import Hyperedge, Hypergraph, Hypernode

        graph = Hypergraph()
        nav = AbstractionNavigator(graph)
        a = Hypernode(label="A")
        b = Hypernode(label="B")
        ext = Hypernode(label="EXT")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(ext)
        graph.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="internal",
        ))
        graph.add_edge(Hyperedge(
            source_ids=frozenset({b.id}),
            target_ids=frozenset({ext.id}),
            label="out",
        ))
        graph.add_edge(Hyperedge(
            source_ids=frozenset({ext.id}),
            target_ids=frozenset({a.id}),
            label="in",
        ))
        nav.collapse_subgraph({"A", "B"}, summary_label="AB")
        graph.remove_node(a.id)
        result = nav.expand_node("AB")
        assert result is not None
        assert result.summary_removed is True
        assert b.id in result.expanded_nodes
        assert a.id not in result.expanded_nodes

    def test_get_summary_for(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import Hypergraph, Hypernode

        graph = Hypergraph()
        nav = AbstractionNavigator(graph)
        assert nav.get_summary_for("nothing") is None
        graph.add_node(Hypernode(label="X"))
        assert nav.get_summary_for("X") is None
        graph.add_node(Hypernode(label="A"))
        graph.add_node(Hypernode(label="B"))
        nav.collapse_subgraph({"A", "B"}, summary_label="AB")
        mapping = nav.get_summary_for("AB")
        assert mapping is not None
        assert mapping.summary_label == "AB"

    def test_get_summary_children(self) -> None:
        from hyper3.abstraction import AbstractionNavigator
        from hyper3.kernel import Hypergraph, Hypernode

        graph = Hypergraph()
        nav = AbstractionNavigator(graph)
        assert nav.get_summary_children("nothing") == []
        graph.add_node(Hypernode(label="A"))
        graph.add_node(Hypernode(label="B"))
        nav.collapse_subgraph({"A", "B"}, summary_label="AB")
        children = nav.get_summary_children("AB")
        assert children == ["A", "B"]


class TestExpandResultDataclass:
    def test_defaults(self) -> None:
        from hyper3.abstraction import ExpandResult

        r = ExpandResult()
        assert r.expanded_nodes == []
        assert r.expanded_edges == []
        assert r.summary_removed is False

    def test_with_values(self) -> None:
        from hyper3.abstraction import ExpandResult

        r = ExpandResult(
            expanded_nodes=["n1", "n2"],
            expanded_edges=["e1"],
            summary_removed=True,
        )
        assert r.expanded_nodes == ["n1", "n2"]
        assert r.expanded_edges == ["e1"]
        assert r.summary_removed is True

    def test_bracket_access(self) -> None:
        from hyper3.abstraction import ExpandResult

        r = ExpandResult(expanded_nodes=["x"], summary_removed=True)
        assert r["expanded_nodes"] == ["x"]
        assert r["summary_removed"] is True

    def test_contains(self) -> None:
        from hyper3.abstraction import ExpandResult

        r = ExpandResult(summary_removed=False)
        assert "summary_removed" in r
        assert "expanded_nodes" in r

    def test_keys(self) -> None:
        from hyper3.abstraction import ExpandResult

        r = ExpandResult()
        assert set(r.keys()) == {"expanded_nodes", "expanded_edges", "summary_removed"}


class TestAbstractionMappingDataclass:
    def test_fields(self) -> None:
        from hyper3.abstraction import AbstractionMapping
        from hyper3.kernel import AbstractionLayer

        m = AbstractionMapping(
            summary_node_id="sum1",
            summary_label="SUM",
            detail_node_ids=["d1", "d2"],
            detail_labels=["A", "B"],
            layer=AbstractionLayer.SUMMARY,
        )
        assert m.summary_node_id == "sum1"
        assert m.summary_label == "SUM"
        assert m.detail_node_ids == ["d1", "d2"]
        assert m.detail_labels == ["A", "B"]
        assert m.layer == AbstractionLayer.SUMMARY

    def test_bracket_access(self) -> None:
        from hyper3.abstraction import AbstractionMapping
        from hyper3.kernel import AbstractionLayer

        m = AbstractionMapping(
            summary_node_id="s",
            summary_label="S",
            detail_node_ids=[],
            detail_labels=[],
            layer=AbstractionLayer.DETAIL,
        )
        assert m["summary_label"] == "S"
        assert m["layer"] == AbstractionLayer.DETAIL
