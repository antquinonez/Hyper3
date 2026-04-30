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

    def test_reinforce_with_activation(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connected")
        mem.stimulate("A", energy=1.0)
        mem.spread_activation()
        result = mem.hebbian_reinforce()
        assert isinstance(result.edges_strengthened, int)

    def test_reinforce_pair(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connected")
        result = mem.hebbian_reinforce_pair("A", "B", strength=2.0)
        assert result is not None
        assert result.new_weight > result.old_weight

    def test_reinforce_pair_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.hebbian_reinforce_pair("X", "Y")
        assert result is None

    def test_decay_unused(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connected")
        count = mem.hebbian_decay_unused(threshold_access_count=0)
        assert count >= 0

    def test_strongest_associations(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="strong")
        mem.relate("A", "C", label="weak")
        mem.hebbian_reinforce_pair("A", "B", strength=10.0)
        results = mem.strongest_associations("A", top_k=2)
        assert len(results) <= 2
        if len(results) >= 1:
            assert results[0][0] in ("B", "C")


class TestHebbianConfig:
    def test_custom_config(self) -> None:
        config = HebbianConfig(learning_rate=0.5, decay_rate=0.05)
        assert config.learning_rate == 0.5
        assert config.decay_rate == 0.05

    def test_default_config(self) -> None:
        config = HebbianConfig()
        assert config.learning_rate == 0.1
        assert config.max_edge_weight == 100.0


class TestHebbianLearner:
    def test_history_tracking(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="link")
        assert mem.hebbian is None
        mem.hebbian_reinforce()
        assert mem.hebbian is not None
        assert len(mem.hebbian.history) == 1

    def test_reinforce_respects_max_weight(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        mem.store("Y")
        mem.relate("X", "Y", label="link")
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
        mem.store("X")
        mem.store("Y")
        edge = mem.relate("X", "Y", label="link")
        edge.weight = 0.5
        learner = HebbianLearner(mem.graph, mem._activation)
        updates = learner.decay_unused(threshold_access_count=0)
        for u in updates:
            assert u.new_weight >= 0.01
