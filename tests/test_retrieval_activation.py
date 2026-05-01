from __future__ import annotations

import pytest

from hyper3.exceptions import NodeNotFoundError
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.memory import HypergraphMemory
from hyper3.retrieval_activation import ActivationConfig, ActivationResult, SpreadingActivation


def _add_node(graph: Hypergraph, label: str) -> Hypernode:
    node = Hypernode(label=label)
    graph.add_node(node)
    return node


def _add_edge(graph: Hypergraph, src: Hypernode, tgt: Hypernode, label: str = "", weight: float = 1.0) -> Hyperedge:
    edge = Hyperedge(
        source_ids=frozenset({src.id}),
        target_ids=frozenset({tgt.id}),
        label=label,
        weight=weight,
    )
    graph.add_edge(edge)
    return edge


def _make_chain() -> tuple[Hypergraph, list[Hypernode]]:
    graph = Hypergraph()
    nodes = [_add_node(graph, lbl) for lbl in ("A", "B", "C")]
    _add_edge(graph, nodes[0], nodes[1])
    _add_edge(graph, nodes[1], nodes[2])
    return graph, nodes


class TestBasicStimulateAndSpread:
    def test_chain_propagation(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 1.0)
        result = sa.spread()
        assert nodes[0].id in result
        assert nodes[1].id in result
        assert nodes[2].id in result
        assert result[nodes[1].id] > result[nodes[2].id]

    def test_activation_accumulates(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 0.5)
        sa.stimulate(nodes[0].id, 0.5)
        assert sa.activations[nodes[0].id] == pytest.approx(1.0)


class TestDecay:
    def test_decay_reduces_activation(self):
        graph, nodes = _make_chain()
        config = ActivationConfig(decay_factor=0.5, normalize_per_step=False)
        sa = SpreadingActivation(graph, config=config)
        sa.stimulate(nodes[0].id, 1.0)
        sa.spread(iterations=1)
        r2 = sa.activations
        assert r2[nodes[1].id] < 1.0


class TestEdgeWeight:
    def test_heavier_edge_propagates_more(self):
        graph = Hypergraph()
        a = _add_node(graph, "A")
        b = _add_node(graph, "B")
        c = _add_node(graph, "C")
        _add_edge(graph, a, b, weight=2.0)
        _add_edge(graph, a, c, weight=0.5)
        config = ActivationConfig(normalize_per_step=False)
        sa = SpreadingActivation(graph, config=config)
        sa.stimulate(a.id, 1.0)
        result = sa.spread(iterations=1)
        assert result[b.id] > result[c.id]


class TestLabelRates:
    def test_label_specific_rates(self):
        graph = Hypergraph()
        a = _add_node(graph, "A")
        b = _add_node(graph, "B")
        c = _add_node(graph, "C")
        _add_edge(graph, a, b, label="strong")
        _add_edge(graph, a, c, label="weak")
        config = ActivationConfig(
            label_rates={"strong": 2.0, "weak": 0.1},
            normalize_per_step=False,
        )
        sa = SpreadingActivation(graph, config=config)
        sa.stimulate(a.id, 1.0)
        result = sa.spread(iterations=1)
        assert result[b.id] > result[c.id]


class TestMinActivation:
    def test_weak_nodes_filtered(self):
        graph = Hypergraph()
        a = _add_node(graph, "A")
        b = _add_node(graph, "B")
        _add_edge(graph, a, b)
        config = ActivationConfig(
            min_activation=0.5,
            decay_factor=0.1,
            normalize_per_step=False,
        )
        sa = SpreadingActivation(graph, config=config)
        sa.stimulate(a.id, 1.0)
        result = sa.spread(iterations=1)
        if b.id in result:
            assert result[b.id] >= 0.5


class TestGetActivated:
    def test_threshold_filter(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 1.0)
        sa.spread()
        high = sa.get_activated(threshold=0.5)
        low = sa.get_activated(threshold=0.001)
        assert len(high) == 3
        assert len(low) == 3

    def test_top_k(self):
        graph = Hypergraph()
        nodes = [_add_node(graph, str(i)) for i in range(10)]
        for i in range(9):
            _add_edge(graph, nodes[i], nodes[i + 1])
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 1.0)
        sa.spread()
        result = sa.get_activated(top_k=3)
        assert len(result) == 3

    def test_sorted_descending(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 1.0)
        sa.spread()
        result = sa.get_activated(threshold=0.0)
        for i in range(len(result) - 1):
            assert result[i].activation >= result[i + 1].activation

    def test_activation_result_comparison(self):
        low = ActivationResult("a", "A", 0.3, 0)
        high = ActivationResult("b", "B", 0.8, 1)
        assert low < high
        assert not (high < low)


class TestAssociativeRecall:
    def test_excludes_seed(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        result = sa.associative_recall("A")
        ids = {r.node_id for r in result}
        assert nodes[0].id not in ids

    def test_returns_related(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        result = sa.associative_recall("A")
        result_ids = {r.node_id for r in result}
        assert nodes[1].id in result_ids
        assert nodes[2].id in result_ids

    def test_unknown_concept_returns_empty(self):
        graph = Hypergraph()
        sa = SpreadingActivation(graph)
        assert sa.associative_recall("nonexistent") == []


class TestStimulateAndSpread:
    def test_multiple_seeds(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        seeds = {nodes[0].id: 0.5, nodes[2].id: 0.5}
        result = sa.stimulate_and_spread(seeds)
        assert len(result) == 3

    def test_seeds_by_label(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        seeds = {"A": 1.0}
        result = sa.stimulate_and_spread(seeds)
        labels = {r.label for r in result}
        assert "B" in labels


class TestClear:
    def test_clear_resets(self):
        graph, nodes = _make_chain()
        sa = SpreadingActivation(graph)
        sa.stimulate(nodes[0].id, 1.0)
        assert len(sa.activations) > 0
        sa.clear()
        assert len(sa.activations) == 0


class TestEmptyGraph:
    def test_no_crash_on_empty(self):
        graph = Hypergraph()
        sa = SpreadingActivation(graph)
        sa.stimulate("nonexistent", 1.0)
        result = sa.spread()
        assert "nonexistent" in result

    def test_get_activated_empty(self):
        graph = Hypergraph()
        sa = SpreadingActivation(graph)
        assert sa.get_activated() == []

    def test_associative_recall_empty(self):
        graph = Hypergraph()
        sa = SpreadingActivation(graph)
        assert sa.associative_recall("x") == []


class TestDiamondGraph:
    def test_convergence_boosts_target(self):
        graph = Hypergraph()
        a = _add_node(graph, "A")
        b = _add_node(graph, "B")
        c = _add_node(graph, "C")
        d = _add_node(graph, "D")
        _add_edge(graph, a, b)
        _add_edge(graph, a, c)
        _add_edge(graph, b, d)
        _add_edge(graph, c, d)
        config = ActivationConfig(normalize_per_step=False, decay_factor=0.9)
        sa = SpreadingActivation(graph, config=config)
        sa.stimulate(a.id, 1.0)
        result = sa.spread(iterations=2)
        assert d.id in result
        assert result[d.id] > 0
        assert result[d.id] > result.get(b.id, 0.0) * 0.5


class TestIntegrationMemory:
    def test_activate_end_to_end(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("dog")
        mem.store("cat")
        mem.store("mammal")
        mem.relate("mammal", "dog", label="is_a")
        mem.relate("mammal", "cat", label="is_a")
        result = mem.activate("mammal", top_k=5)
        labels = {r.label for r in result}
        assert "dog" in labels
        assert "cat" in labels
        assert "mammal" not in labels

    def test_stimulate_and_spread_methods(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y")
        mem.stimulate("x", energy=1.0)
        result = mem.spread_activation()
        assert len(result) == 2

    def test_clear_activations(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.stimulate("x", energy=1.0)
        mem.clear_activations()
        result = mem.spread_activation()
        assert len(result) == 0

    def test_load_reinitializes_activation(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        path = str(tmp_path / "test.json")
        mem.save(path)
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        result = mem2.activate("a", top_k=5)
        assert len(result) >= 1


class TestStimulateNodeNotFoundError:
    def test_stimulate_missing_concept_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError):
            mem.stimulate("nonexistent")

    def test_stimulate_valid_concept_succeeds(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.stimulate("a", energy=2.0)


class TestStimulateLabel:
    def test_stimulate_label_found(self):
        graph = Hypergraph()
        n = _add_node(graph, "X")
        sa = SpreadingActivation(graph)
        sa.stimulate_label("X", 0.7)
        assert abs(sa.activations[n.id] - 0.7) < 1e-9

    def test_stimulate_label_missing_is_noop(self):
        graph = Hypergraph()
        sa = SpreadingActivation(graph)
        sa.stimulate_label("missing", 1.0)
        assert len(sa.activations) == 0


class TestConfigProperty:
    def test_config_exposes_settings(self):
        config = ActivationConfig(decay_factor=0.7)
        sa = SpreadingActivation(Hypergraph(), config=config)
        assert sa.config.decay_factor == 0.7


class TestSpreadHyperedge:
    def test_empty_activations_returns_empty(self):
        sa = SpreadingActivation(Hypergraph())
        assert sa.spread_hyperedge(mode="and") == {}

    def test_empty_source_ids_skipped(self):
        graph = Hypergraph()
        t = _add_node(graph, "T")
        edge = Hyperedge(source_ids=frozenset(), target_ids=frozenset({t.id}))
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(t.id, 1.0)
        result = sa.spread_hyperedge(iterations=1)
        assert t.id in result

    def test_or_mode_propagates(self):
        graph = Hypergraph()
        s = _add_node(graph, "S")
        t = _add_node(graph, "T")
        edge = Hyperedge(source_ids=frozenset({s.id}), target_ids=frozenset({t.id}), weight=1.0)
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(s.id, 1.0)
        result = sa.spread_hyperedge(mode="or", iterations=1)
        assert t.id in result

    def test_majority_mode_with_two_of_three(self):
        graph = Hypergraph()
        s1 = _add_node(graph, "S1")
        s2 = _add_node(graph, "S2")
        s3 = _add_node(graph, "S3")
        t = _add_node(graph, "T")
        edge = Hyperedge(
            source_ids=frozenset({s1.id, s2.id, s3.id}),
            target_ids=frozenset({t.id}),
            weight=1.0,
        )
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(s1.id, 1.0)
        sa.stimulate(s2.id, 1.0)
        result = sa.spread_hyperedge(mode="majority", iterations=1)
        assert t.id in result
        assert result[t.id] > 0.0

    def test_and_mode_blocked_when_source_missing(self):
        graph = Hypergraph()
        s1 = _add_node(graph, "S1")
        s2 = _add_node(graph, "S2")
        t = _add_node(graph, "T")
        edge = Hyperedge(
            source_ids=frozenset({s1.id, s2.id}),
            target_ids=frozenset({t.id}),
            weight=1.0,
        )
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(s1.id, 1.0)
        result = sa.spread_hyperedge(mode="and", iterations=1)
        assert t.id not in result

    def test_and_mode_propagates_when_all_sources_active(self):
        graph = Hypergraph()
        s1 = _add_node(graph, "S1")
        s2 = _add_node(graph, "S2")
        t = _add_node(graph, "T")
        edge = Hyperedge(
            source_ids=frozenset({s1.id, s2.id}),
            target_ids=frozenset({t.id}),
            weight=1.0,
        )
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(s1.id, 1.0)
        sa.stimulate(s2.id, 1.0)
        result = sa.spread_hyperedge(mode="and", iterations=1)
        assert t.id in result
        assert result[t.id] > 0.0

    def test_majority_mode_blocked_with_one_of_three(self):
        graph = Hypergraph()
        s1 = _add_node(graph, "S1")
        s2 = _add_node(graph, "S2")
        s3 = _add_node(graph, "S3")
        t = _add_node(graph, "T")
        edge = Hyperedge(
            source_ids=frozenset({s1.id, s2.id, s3.id}),
            target_ids=frozenset({t.id}),
            weight=1.0,
        )
        graph.add_edge(edge)
        sa = SpreadingActivation(graph)
        sa.stimulate(s1.id, 1.0)
        result = sa.spread_hyperedge(mode="majority", iterations=1)
        assert t.id not in result
