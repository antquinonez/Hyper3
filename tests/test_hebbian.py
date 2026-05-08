from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory
from hyper3.hebbian import HebbianConfig, HebbianLearner


class TestHebbianBasic:
    def test_reinforce_empty_graph(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.hebbian_reinforce()
        assert result.edges_strengthened == 0
        assert result.edges_weakened == 0
        assert result.total_co_activations == 0
        assert result.avg_weight_change == 0.0

    def test_reinforce_with_activation(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="connected")
        mem.search.activate("A", energy=1.0)
        result = mem.hebbian_reinforce()
        assert result.edges_strengthened == 1
        assert result.edges_weakened == 0
        assert result.total_co_activations == 1
        assert result.avg_weight_change >= 0.29

    def test_reinforce_pair(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="connected")
        result = mem.hebbian_reinforce_pair("A", "B", strength=2.0)
        assert result is not None
        assert result.old_weight == 1.0
        assert abs(result.new_weight - 1.2) < 1e-9

    def test_reinforce_pair_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.hebbian_reinforce_pair("X", "Y")
        assert result is None

    def test_reinforce_pair_no_edge(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        result = mem.hebbian_reinforce_pair("A", "B")
        assert result is None

    def test_decay_unused(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        edge = mem.link("A", "B", label="connected")
        edge.weight = 0.5
        learner = HebbianLearner(mem.graph, mem._activation)
        updates = learner.decay_unused(threshold_access_count=1)
        assert len(updates) == 1
        assert updates[0].old_weight == 0.5
        assert abs(updates[0].new_weight - 0.49) < 1e-9

    def test_strongest_associations(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="strong")
        mem.link("A", "C", label="weak")
        mem.hebbian_reinforce_pair("A", "B", strength=10.0)
        results = mem.strongest_associations("A", top_k=2)
        assert len(results) == 2
        assert results[0][0] == "B"
        assert results[0][1] > results[1][1]

    def test_strongest_associations_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        results = mem.strongest_associations("Z", top_k=5)
        assert results == []


class TestHebbianConfig:
    def test_custom_config(self) -> None:
        config = HebbianConfig(learning_rate=0.5, decay_rate=0.05)
        assert config.learning_rate == 0.5
        assert config.decay_rate == 0.05

    def test_default_config(self) -> None:
        config = HebbianConfig()
        assert config.learning_rate == 0.1
        assert config.max_edge_weight == 100.0

    def test_config_via_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.hebbian_reinforce()
        config = mem.hebbian.config
        assert config.learning_rate == 0.1


class TestHebbianLearner:
    def test_history_tracking(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="link")
        assert mem.hebbian is None
        result = mem.hebbian_reinforce()
        assert mem.hebbian is not None
        assert len(mem.hebbian.history) == 1
        assert result.edges_strengthened == 0
        assert result.edges_weakened == 0
        assert result.total_co_activations == 0
        assert result.avg_weight_change == 0.0

    def test_reinforce_respects_max_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("X")
        mem.add("Y")
        mem.link("X", "Y", label="link")
        for _ in range(50):
            mem.hebbian_reinforce_pair("X", "Y", strength=50.0)
        edge = None
        for e in mem.graph.edges:
            edge = e
            break
        assert edge is not None
        assert edge.weight <= 100.0

    def test_decay_respects_min_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("X")
        mem.add("Y")
        edge = mem.link("X", "Y", label="link")
        edge.weight = 0.5
        learner = HebbianLearner(mem.graph, mem._activation)
        updates = learner.decay_unused(threshold_access_count=1)
        for u in updates:
            assert u.new_weight >= 0.01

    def test_low_co_activation_decays_edge(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="link")
        a = mem.graph.get_node_by_label("A")
        b = mem.graph.get_node_by_label("B")
        assert a is not None
        assert b is not None
        mem._activation.stimulate(a.id, 0.2)
        mem._activation.stimulate(b.id, 0.2)
        config = HebbianConfig(activation_threshold=0.3)
        learner = HebbianLearner(mem.graph, mem._activation, config=config)
        result = learner.reinforce_from_activation()
        assert result.edges_weakened == 1
        assert result.edges_strengthened == 0
        assert len(result.updates) == 1
        assert result.updates[0].new_weight < result.updates[0].old_weight

    def test_non_activated_edge_unchanged(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.add("C")
        mem.link("A", "B", label="activated")
        mem.link("A", "C", label="dormant")
        a = mem.graph.get_node_by_label("A")
        b = mem.graph.get_node_by_label("B")
        assert a is not None
        assert b is not None
        mem._activation.stimulate(a.id, 1.0)
        mem._activation.stimulate(b.id, 1.0)
        result = mem.hebbian_reinforce()
        assert result.edges_strengthened == 1
        assert result.avg_weight_change > 0.0
        c_node = mem.graph.get_node_by_label("C")
        a_node = mem.graph.get_node_by_label("A")
        for e in mem.graph.edges:
            if a_node.id in e.source_ids and c_node.id in e.target_ids:
                assert e.weight == 1.0

    def test_reinforce_exact_weight_delta(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("A")
        mem.add("B")
        mem.link("A", "B", label="link")
        result = mem.hebbian_reinforce_pair("A", "B", strength=1.0)
        assert result is not None
        assert result.old_weight == 1.0
        assert abs(result.new_weight - 1.1) < 1e-9
