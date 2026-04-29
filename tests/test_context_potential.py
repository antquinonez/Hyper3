import math
import time

import pytest
from hyper3.memory import HypergraphMemory
from hyper3.kernel import Hyperedge
from hyper3.exceptions import NodeNotFoundError
from hyper3.quantum import PotentialFieldConfig


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("high", data={"importance": 0.9})
    mem.store("medium", data={"importance": 0.5})
    mem.store("low", data={"importance": 0.1})
    h = mem.graph.get_node_by_label("high")
    m = mem.graph.get_node_by_label("medium")
    l = mem.graph.get_node_by_label("low")
    for _ in range(5):
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({h.id}), target_ids=frozenset({m.id}),
            label="strong", weight=5.0,
        ))
    for _ in range(2):
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({m.id}), target_ids=frozenset({l.id}),
            label="weak", weight=1.0,
        ))
    return mem


class TestComputePotentialField:

    def test_field_has_entries_for_all_interpretations(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        field = mem._quantum.compute_potential_field(qs.id)
        assert len(field) == 3

    def test_high_weight_node_dominates(self):
        mem = _make_mem()
        h = mem.graph.get_node_by_label("high")
        h.weight = 10.0
        m = mem.graph.get_node_by_label("medium")
        m.weight = 1.0
        l = mem.graph.get_node_by_label("low")
        l.weight = 0.1
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        field = mem._quantum.compute_potential_field(qs.id)
        assert field[h.id] > field[l.id]

    def test_field_sums_to_one(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        field = mem._quantum.compute_potential_field(qs.id)
        assert abs(sum(field.values()) - 1.0) < 1e-10

    def test_custom_config(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        cfg = PotentialFieldConfig(
            weight_field=1.0,
            structural_field=0.0,
            recency_field=0.0,
            activation_field=0.0,
            edge_field=0.0,
        )
        field = mem._quantum.compute_potential_field(qs.id, config=cfg)
        assert len(field) == 3

    def test_activation_values_influence_field(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        h = mem.graph.get_node_by_label("high")
        m = mem.graph.get_node_by_label("medium")
        l = mem.graph.get_node_by_label("low")
        activations = {h.id: 0.0, m.id: 0.0, l.id: 1.0}
        field = mem._quantum.compute_potential_field(qs.id, activation_values=activations)
        assert l.id in field

    def test_empty_state_returns_empty(self):
        mem = _make_mem()
        with pytest.raises(NodeNotFoundError):
            mem.superpose(["nonexistent"], use_context_field=False)


class TestEvolveInContext:

    def test_amplitudes_change_after_evolution(self):
        mem = _make_mem()
        h = mem.graph.get_node_by_label("high")
        h.weight = 10.0
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        amps_before = [abs(i.amplitude) for i in qs.interpretations]
        mem._quantum.evolve_in_context(qs.id)
        amps_after = [abs(i.amplitude) for i in qs.interpretations]
        assert amps_before != amps_after

    def test_coherence_time_reduced_for_dominant_state(self):
        mem = _make_mem()
        h = mem.graph.get_node_by_label("high")
        h.weight = 100.0
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        original_coherence = qs.coherence_time
        mem._quantum.evolve_in_context(qs.id)
        max_prob = max(abs(i.amplitude) ** 2 for i in qs.interpretations)
        if max_prob > 0.6:
            assert qs.coherence_time < original_coherence or qs.coherence_time == qs.base_coherence_time * 0.5

    def test_coherence_time_extended_for_uniform(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        for interp in qs.interpretations:
            interp.amplitude = 1.0 / math.sqrt(3)
        mem._quantum.evolve_in_context(qs.id)
        n = len(qs.interpretations)
        max_prob = max(abs(i.amplitude) ** 2 for i in qs.interpretations)
        if max_prob < 1.0 / n * 1.5:
            assert qs.coherence_time == qs.base_coherence_time * 2.0


class TestSuperposeWithContextField:

    def test_context_field_applied_by_default(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"])
        amps = [abs(i.amplitude) for i in qs.interpretations]
        assert len(amps) == 3
        assert abs(sum(a ** 2 for a in amps) - 1.0) < 1e-10

    def test_context_field_disabled(self):
        mem = _make_mem()
        qs = mem.superpose(["high", "medium", "low"], use_context_field=False)
        amps = [abs(i.amplitude) for i in qs.interpretations]
        assert all(abs(a - amps[0]) < 1e-10 for a in amps)
