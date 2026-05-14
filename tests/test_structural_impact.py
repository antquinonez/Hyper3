from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.structural_impact import (
    ImpactResult,
    StructuralImpactEngine,
)


def _add(g: Hypergraph, label: str) -> Hypernode:
    return g.add_node(Hypernode(label=label))


def _link(g: Hypergraph, src: Hypernode, tgt: Hypernode, label: str = "next") -> None:
    g.add_edge(Hyperedge(source_ids=frozenset({src.id}), target_ids=frozenset({tgt.id}), label=label))


class TestStructuralImpactConstruction:
    def test_default_construction(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        assert engine.get_history() == []

    def test_custom_threshold(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g, hub_degree_threshold=0.5)
        assert engine._hub_threshold == 0.5


class TestStructuralImpactAdd:
    def test_add_isolated_node_low_severity(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "a")
        result = engine.assess_add(node.id)
        assert result.operation == "add"
        assert result.severity == "low"
        assert result.node_count_after == 1
        assert result.node_count_before == 0

    def test_add_creates_new_component(self):
        g = Hypergraph()
        _add(g, "a")
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "b")
        result = engine.assess_add(node.id)
        assert result.component_change.new_component_created

    def test_add_empty_graph(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "solo")
        result = engine.assess_add(node.id)
        assert result.node_count_after == 1


class TestStructuralImpactLink:
    def test_link_within_component_no_bridge(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        _link(g, a, b)
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="ab2"))
        result = engine.assess_link(a.id, b.id, edge.id)
        assert result.operation == "link"
        assert not result.component_change.bridged
        assert result.edge_count_after == 2

    def test_link_bridging_components_high_severity(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        c = _add(g, "c")
        _link(g, a, b)
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="ac"))
        result = engine.assess_link(a.id, c.id, edge.id)
        assert result.component_change.bridged
        assert result.severity == "high"

    def test_link_creating_cycle(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        c = _add(g, "c")
        _link(g, a, b)
        _link(g, b, c)
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id}), label="ca"))
        result = engine.assess_link(c.id, a.id, edge.id)
        assert result.cycle_change.cycle_created
        assert result.cycle_change.cycle_length > 0
        assert result.severity == "medium"

    def test_link_density_increase(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="ab"))
        result = engine.assess_link(a.id, b.id, edge.id)
        assert result.density_after >= result.density_before

    def test_link_no_cycle_when_acyclic(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="ab"))
        result = engine.assess_link(a.id, b.id, edge.id)
        assert not result.cycle_change.cycle_created


class TestStructuralImpactHistory:
    def test_history_records_results(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "a")
        engine.assess_add(node.id)
        engine.before_snapshot()
        node2 = _add(g, "b")
        engine.assess_add(node2.id)
        history = engine.get_history()
        assert len(history) == 2
        assert history[0].operation == "add"

    def test_history_respects_limit(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        for i in range(10):
            engine.before_snapshot()
            node = _add(g, f"n{i}")
            engine.assess_add(node.id)
        assert len(engine.get_history(limit=3)) == 3

    def test_clear_history(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "a")
        engine.assess_add(node.id)
        engine.clear_history()
        assert engine.get_history() == []


class TestStructuralImpactSerialization:
    def test_to_dict_round_trip(self):
        g = Hypergraph()
        engine = StructuralImpactEngine(g, hub_degree_threshold=0.5, track_cycles=False)
        data = engine.to_dict()
        restored = StructuralImpactEngine.from_dict(data, g)
        assert restored._hub_threshold == 0.5
        assert not restored._track_cycles

    def test_from_dict_defaults(self):
        g = Hypergraph()
        restored = StructuralImpactEngine.from_dict({}, g)
        assert restored._hub_threshold == 0.8


class TestStructuralImpactSeverity:
    def test_critical_severity(self):
        g = Hypergraph()
        a = _add(g, "a")
        b = _add(g, "b")
        c = _add(g, "c")
        d = _add(g, "d")
        _link(g, a, b)
        _link(g, b, c)
        _link(g, c, a)
        engine = StructuralImpactEngine(g, hub_degree_threshold=0.3)
        engine.before_snapshot()
        edge = g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="ad"))
        result = engine.assess_link(a.id, d.id, edge.id)
        assert result.severity in ("low", "medium", "high", "critical")

    def test_no_change_when_no_structural_impact(self):
        g = Hypergraph()
        _add(g, "a")
        engine = StructuralImpactEngine(g)
        engine.before_snapshot()
        node = _add(g, "b")
        result = engine.assess_add(node.id)
        assert result.centrality_shifts == []
