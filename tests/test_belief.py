import math
import time
import time as _time

import numpy as np
import pytest

from hyper3 import (
    BeliefLayer,
    BeliefState,
    ConceptCorrelation,
    EvidenceInteraction,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
    MultiwayEngine,
    Outcome,
    SamplingProfile,
    SamplingTrigger,
    StateConvergenceEngine,
    TransitiveRule,
)
from hyper3.belief import PotentialFieldConfig
from hyper3.exceptions import NodeNotFoundError
from hyper3.kernel import Hyperedge
from hyper3.memory import HypergraphMemory
from hyper3.multiway import MultiwayGraph, MultiwayState


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("x")
    mem.store("y")
    mem.store("z")
    return mem


class TestDecayStaleStates:

    def test_no_stale_states(self):
        mem = _make_mem()
        mem.create_distribution(["x", "y", "z"])
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_stale_state_decayed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._belief.decay_stale_states()
        assert len(result) == 1
        assert qs.resolved is True

    def test_max_age_filter(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 0.0
        qs.base_coherence_time = 0.0
        time.sleep(0.01)
        result = mem._belief.decay_stale_states(max_age=3600.0)
        assert result == []

    def test_non_stale_not_decayed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.coherence_time = 99999.0
        qs.base_coherence_time = 99999.0
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_already_resolved_skipped(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        qs.resolved = True
        result = mem._belief.decay_stale_states()
        assert result == []

    def test_amplitudes_reduced(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y", "z"])
        amps_before = [abs(i.amplitude) for i in qs.outcomes]
        qs.coherence_time = 0.001
        qs.base_coherence_time = 0.001
        qs.created_at = time.time() - 10.0
        mem._belief.decay_stale_states()
        amps_after = [abs(i.amplitude) for i in qs.outcomes]
        assert qs.resolved or sum(amps_after) < sum(amps_before)


class TestCleanupResolved:

    def test_no_resolved(self):
        mem = _make_mem()
        mem.create_distribution(["x", "y"])
        result = mem._belief.cleanup_resolved(threshold_age=0.0)
        assert result == 0

    def test_old_resolved_removed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.resolved = True
        qs.created_at = time.time() - 7200
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 1
        assert mem._belief.get_state(qs.id) is None

    def test_recent_resolved_kept(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.resolved = True
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 0
        assert mem._belief.get_state(qs.id) is not None

    def test_active_not_removed(self):
        mem = _make_mem()
        qs = mem.create_distribution(["x", "y"])
        qs.created_at = time.time() - 7200
        result = mem._belief.cleanup_resolved(threshold_age=3600.0)
        assert result == 0





def _build_graph():
    g = Hypergraph()
    for label in ["cat", "dog", "bird", "fish"]:
        g.add_node(Hypernode(id=label, label=label))
    return g


class TestConceptCorrelation:
    def test_create_correlation(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        ent = ql.create_correlation(
            ["cat", "dog"],
            ["bird", "fish"],
            {("cat", "bird"): 0.8, ("dog", "fish"): -0.6},
        )
        assert isinstance(ent, ConceptCorrelation)
        assert ent.strength > 0
        assert "cat" in ent.group_a_node_ids
        assert "fish" in ent.group_b_node_ids

    def test_correlation_predict(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.9},
        )
        preds = ent.predict("a", "pet")
        assert "b" in preds
        assert preds["b"] == "pet"

    def test_correlation_negative_correlation(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): -0.9},
        )
        preds = ent.predict("a", "pet")
        assert preds["b"] == "opposite"


class TestInterference:
    def test_compute_interactions(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["cat", "dog", "bird"], [0.7, -0.5, 0.3])
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 0

    def test_evidence_interaction_properties(self):
        p = EvidenceInteraction(node_id="n1", constructive=0.8, destructive=0.0, net_amplitude=0.8)
        assert p.is_constructive
        assert not p.is_destructive

    def test_destructive_interference(self):
        p = EvidenceInteraction(node_id="n1", constructive=0.0, destructive=-0.5, net_amplitude=-0.5)
        assert p.is_destructive
        assert not p.is_constructive


class TestSamplingProfile:
    def test_builtin_bases(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        assert "linguistic" in ql.bases
        assert "temporal" in ql.bases
        assert "emotional" in ql.bases
        assert "pragmatic" in ql.bases

    def test_add_custom_basis(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        custom = SamplingProfile(name="custom", dimensions=["x", "y"], weights={"x": 0.6, "y": 0.4})
        ql.add_basis(custom)
        assert ql.get_basis("custom") is not None
        assert custom.weight_for("x") == 0.6
        assert custom.weight_for("z") == 0.5

    def test_sample_with_profile(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["cat", "dog", "bird"])
        result = ql.sample_with_profile(qs.id, "linguistic")
        assert isinstance(result, Outcome)
        assert result.node_id in {"cat", "dog", "bird"}


class TestSamplingTriggers:
    def test_staleness_trigger(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = BeliefState(created_at=0.0, coherence_time=0.001)
        qs.add_outcome("cat", 0.7)
        ql._states[qs.id] = qs
        triggers = ql.detect_sampling_triggers(qs.id)
        assert any(t.trigger_type == "staleness_timeout" for t in triggers)

    def test_single_outcome_trigger(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["cat"])
        triggers = ql.detect_sampling_triggers(qs.id)
        assert any(t.trigger_type == "single_outcome" for t in triggers)

    def test_no_triggers_for_fresh_state(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["cat", "dog", "bird"])
        triggers = ql.detect_sampling_triggers(qs.id)
        staleness = [t for t in triggers if t.trigger_type == "staleness_timeout"]
        assert len(staleness) == 0


class TestSampleCorrelated:
    def test_sample_correlated(self):
        g = _build_graph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["cat", "dog"])
        ql.create_correlation(
            ["cat", "dog"], ["bird", "fish"],
            {("cat", "bird"): 0.9, ("dog", "fish"): 0.8},
        )
        preds = ql.sample_correlated(qs.id, "cat")
        assert "bird" in preds
        assert preds["bird"] == "cat"




class TestBeliefSampleDeep:
    def test_sample_born_rule_distribution(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.9)
        qs.add_outcome("b", 0.1)
        counts = {"a": 0, "b": 0}
        for _ in range(500):
            qs2 = BeliefState()
            qs2.add_outcome("a", 0.9)
            qs2.add_outcome("b", 0.1)
            result = qs2.sample()
            counts[result.node_id] += 1
        assert counts["a"] > counts["b"]
        assert counts["a"] > 200

    def test_sample_single_outcome(self):
        qs = BeliefState()
        qs.add_outcome("only", 1.0)
        result = qs.sample()
        assert result.node_id == "only"

    def test_sample_zero_total(self):
        qs = BeliefState()
        qs.add_outcome("a", 0.0)
        qs.add_outcome("b", 0.0)
        result = qs.sample()
        assert result.node_id == "a"

    def test_probability_uses_abs(self):
        qs = BeliefState()
        qs.add_outcome("a", -0.5)
        assert abs(qs.outcomes[0].probability - 0.25) < 0.01

    def test_belief_state_age_and_staleness(self):
        qs = BeliefState(created_at=0.0, coherence_time=0.001)
        assert qs.is_stale
        assert qs.age > 0.0


class TestBeliefLayerDeep:
    def test_sample_with_profile_missing_profile(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a"])
        result = ql.sample_with_profile(qs.id, "nonexistent_profile")
        assert isinstance(result, Outcome)
        assert result.node_id == "a"

    def test_sample_with_profile_empty_state(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        result = ql.sample_with_profile("nonexistent", "linguistic")
        assert result is None

    def test_get_correlation(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = BeliefLayer(g)
        assert ql.get_correlation("nonexistent") is None

    def test_get_basis(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        assert ql.get_basis("linguistic").name == "linguistic"
        assert ql.get_basis("nonexistent") is None

    def test_evolve_amplitudes_missing(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        state_count_before = len(ql._states)
        ql.evolve_amplitudes("nonexistent", {"a": 2.0})
        assert len(ql._states) == state_count_before

    def test_correlation_predict_no_match(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.9},
        )
        preds = ent.predict("nonexistent", "value")
        assert preds == {}

    def test_correlation_predict_zero_correlation(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.0},
        )
        preds = ent.predict("a", "value")
        assert preds == {}

    def test_interference_constructive(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState()
        qs.add_outcome("a", 0.5)
        qs.add_outcome("a", 0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_constructive
        assert not patterns[0].is_destructive

    def test_interference_destructive(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState()
        qs.add_outcome("a", 0.5)
        qs.add_outcome("a", -0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_destructive
        assert not patterns[0].is_constructive

    def test_interference_single_outcome(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a"])
        patterns = ql.compute_interactions(qs.id)
        assert patterns == []

    def test_sample_correlated_missing(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        result = ql.sample_correlated("nonexistent", "a")
        assert result == {}

    def test_sample_triggers_already_resolved(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a"])
        qs.resolved = True
        triggers = ql.detect_sampling_triggers(qs.id)
        assert triggers == []

    def test_sample_triggers_dominant(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState(created_at=0.0, coherence_time=0.0)
        qs.add_outcome("a", 0.95)
        qs.add_outcome("b", 0.01)
        ql._states[qs.id] = qs
        triggers = ql.detect_sampling_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "staleness_timeout" in types

    def test_sampling_profile_default_weight(self):
        profile = SamplingProfile(name="test", dimensions=["x"])
        assert profile.weight_for("y") == 1.0

    def test_find_invariants_empty_node_ids(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset())
        l2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset())
        mw.add_state(l1)
        mw.add_state(l2)
        ci = StateConvergenceEngine(g, mw)
        assert ci.find_invariants() == []

    def test_find_invariants_consumed_states(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(p1)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}))
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        l2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(l0)
        mw.add_state(l1)
        mw.add_state(l2)
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        ci._consumed_states.add(l1.id)
        pairs = ci.find_invariants()
        for a_id, b_id, _sim in pairs:
            assert l1.id not in (a_id, b_id)

    def test_find_invariants_pair_found(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(p1)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}))
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(l0)
        mw.add_state(l1)
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        pairs = ci.find_invariants()
        assert len(pairs) == 1
        assert pairs[0][2] == 1.0

    def test_merge_invariant_states_full(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(p1)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}), rule_applied="rule_x")
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}), rule_applied="rule_y")
        mw.add_state(l0)
        mw.add_state(l1)
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        assert len(merged) == 1
        inv = merged[0]
        assert inv.state_a_id in (l0.id, l1.id)
        assert inv.state_b_id in (l0.id, l1.id)
        assert inv.merged_into is not None
        assert l0.id in ci._consumed_states
        assert l1.id in ci._consumed_states
        merged_state = mw.get_state(inv.merged_into)
        assert merged_state is not None
        assert "rule_x" in merged_state.rule_applied
        assert "rule_y" in merged_state.rule_applied

    def test_merge_invariant_states_already_consumed(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(p1)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}))
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        l2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(l0)
        mw.add_state(l1)
        mw.add_state(l2)
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        ci._consumed_states.add(l0.id)
        ci._consumed_states.add(l2.id)
        merged = ci.merge_invariant_states()
        for inv in merged:
            assert l0.id not in (inv.state_a_id, inv.state_b_id)
            assert l2.id not in (inv.state_a_id, inv.state_b_id)

    def test_correlation_predict_node_b_match(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.8},
        )
        preds = ent.predict("b", "value_a")
        assert "a" in preds
        assert preds["a"] == "value_a"

    def test_correlation_predict_negative_correlation(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): -0.5},
        )
        preds = ent.predict("b", "value_a")
        assert preds["a"] == "opposite"

    def test_sample_nonexistent_state(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        assert ql.sample("nonexistent_id") is None

    def test_sample_with_profile_missing_node(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["ghost_node"])
        result = ql.sample_with_profile(qs.id, "linguistic")
        assert result.node_id == "ghost_node"

    def test_detect_sampling_triggers_interference_maxima(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState(created_at=_time.time())
        qs.add_outcome("a", 0.6)
        qs.add_outcome("a", 0.5)
        ql._states[qs.id] = qs
        triggers = ql.detect_sampling_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "interference_maxima" in types
        it = next(t for t in triggers if t.trigger_type == "interference_maxima")
        assert it.details["amplitude"] > 0.7

    def test_sample_correlated_empty_outcomes(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState()
        ql._states[qs.id] = qs
        result = ql.sample_correlated(qs.id, "a")
        assert result == {}

    def test_sample_correlated_fake_correlation(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a"])
        qs.correlation_ids.append("fake_ent_id")
        result = ql.sample_correlated(qs.id, "a")
        assert result == {}

    def test_correlations_property(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        ql.create_correlation(["a"], ["b"], {("a", "b"): 0.5})
        ents = ql.correlations
        assert len(ents) == 1

    def test_merge_consumed_second_pair(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a"}))
        p2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a"}))
        mw.add_state(p1)
        mw.add_state(p2)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}))
        l1 = MultiwayState(parent_id=p2.id, active_node_ids=frozenset({"a", "b"}))
        l2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(l0)
        mw.add_state(l1)
        mw.add_state(l2)
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        assert len(merged) == 1

    def test_merge_missing_state(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"x"}))
        mw.add_state(root)
        p1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(p1)
        l0 = MultiwayState(parent_id=p1.id, active_node_ids=frozenset({"a", "b"}))
        l1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b"}))
        mw.add_state(l0)
        mw.add_state(l1)
        mw.get_leaves()
        del mw._states[l0.id]
        ci = StateConvergenceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        for inv in merged:
            assert inv.state_a_id != l0.id

    def test_correlation_predict_node_a_match(self):
        ent = ConceptCorrelation(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.8},
        )
        preds = ent.predict("a", "value_a")
        assert "b" in preds
        assert preds["b"] == "value_a"

    def test_sample_with_profile_node_with_metadata(self):
        g = Hypergraph()
        node = Hypernode(id="a", label="a")
        node.metadata.custom = {"semantic": 0.8, "syntactic": 0.5, "pragmatic": 0.3}
        g.add_node(node)
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a"])
        result = ql.sample_with_profile(qs.id, "linguistic")
        assert result.node_id == "a"

    def test_detect_sampling_triggers_single_outcome(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState(created_at=_time.time())
        qs.add_outcome("a", 1.0)
        ql._states[qs.id] = qs
        triggers = ql.detect_sampling_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "single_outcome" in types

    def test_create_correlation_links_active_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        ent = ql.create_correlation(["a"], ["b"], {("a", "b"): 0.8})
        assert ent.id in qs.correlation_ids

    def test_sample_correlated_with_predictions(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        ql.create_correlation(["a"], ["b"], {("a", "b"): 0.8})
        result = ql.sample_correlated(qs.id, "a")
        assert "b" in result

    def test_add_basis_and_bases_property(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        profile = SamplingProfile(name="custom_test", dimensions=["d1"], weights={"d1": 1.0})
        ql.add_basis(profile)
        assert ql.get_basis("custom_test") is profile
        all_bases = ql.bases
        assert "custom_test" in all_bases

    def test_sample_with_profile_negative_metadata_no_crash(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="n1", metadata=Metadata(custom={"semantic": -2.0})))
        g.add_node(Hypernode(id="n2", metadata=Metadata(custom={"semantic": 1.0})))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["n1", "n2"])
        result = ql.sample_with_profile(qs.id, "linguistic")
        assert result.node_id in {"n1", "n2"}





def _make_graph_with_nodes_1(n: int = 4) -> tuple[Hypergraph, list[Hypernode]]:
    graph = Hypergraph()
    nodes = [Hypernode(label=f"n{i}") for i in range(n)]
    for node in nodes:
        graph.add_node(node)
    return graph, nodes


class TestUnitaryEvolution:
    def test_hadamard_creates_equal_superposition(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id])
        assert qs.outcome_count == 1
        qs.add_outcome(nodes[1].id, 0.0)
        qs.normalize()
        H = BeliefLayer.hadamard_2x2()
        ql._states[qs.id] = qs
        ql.evolve_unitary(qs.id, H)
        probs = [abs(i.amplitude) ** 2 for i in qs.outcomes]
        assert abs(probs[0] - 0.5) < 0.01
        assert abs(probs[1] - 0.5) < 0.01

    def test_phase_shift_rotates_phase(self):
        graph, nodes = _make_graph_with_nodes_1(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        U = BeliefLayer.phase_shift(np.pi / 2, 3, 1)
        ql.evolve_unitary(qs.id, U)
        amp_1 = qs.outcomes[1].amplitude
        assert abs(np.angle(complex(amp_1)) - np.pi / 2) < 0.01 or abs(np.angle(complex(amp_1)) + np.pi / 2) < 0.01

    def test_unitary_preserves_norm(self):
        graph, nodes = _make_graph_with_nodes_1(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        total_before = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        U = BeliefLayer.phase_shift(0.7, 3, 0)
        ql.evolve_unitary(qs.id, U)
        total_after = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        assert abs(total_before - total_after) < 0.01

    def test_evolve_unitary_wrong_shape_ignored(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id])
        amp_before = qs.outcomes[0].amplitude
        wrong_U = np.eye(3, dtype=complex)
        ql.evolve_unitary(qs.id, wrong_U)
        assert qs.outcomes[0].amplitude == amp_before


class TestDensityMatrix:
    def test_density_matrix_pure_state(self):
        graph, nodes = _make_graph_with_nodes_1(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        rho = ql.compute_density_matrix(qs.id)
        assert rho is not None
        assert rho.shape == (3, 3)
        purity = np.trace(rho @ rho)
        assert abs(purity - 1.0) < 0.01

    def test_von_neumann_entropy_pure(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id])
        rho = ql.compute_density_matrix(qs.id)
        assert rho is not None
        entropy = BeliefLayer.von_neumann_entropy(rho)
        assert abs(entropy) < 0.01

    def test_von_neumann_entropy_maximally_mixed(self):
        rho = np.eye(4, dtype=complex) / 4
        entropy = BeliefLayer.von_neumann_entropy(rho)
        assert abs(entropy - 2.0) < 0.01

    def test_partial_trace(self):
        rho = np.eye(4, dtype=complex) / 4
        result = BeliefLayer.partial_trace(rho, [0], [2, 2])
        assert result.shape == (2, 2)

    def test_density_matrix_none_for_missing(self):
        graph = Hypergraph()
        ql = BeliefLayer(graph)
        result = ql.compute_density_matrix("nonexistent")
        assert result is None


class TestComplexAmplitudeInterference:
    def test_constructive_interference(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        ql = BeliefLayer(graph)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, 0.7)
        qs.add_outcome(nodes[0].id, 0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_constructive

    def test_destructive_interference(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        ql = BeliefLayer(graph)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, 0.7)
        qs.add_outcome(nodes[0].id, -0.5)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].net_amplitude < abs(0.7)
        assert patterns[0].destructive >= 0

    def test_normalize_complex_amplitudes(self):
        graph, nodes = _make_graph_with_nodes_1(2)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, complex(0.6, 0.3))
        qs.add_outcome(nodes[1].id, complex(0.1, -0.2))
        qs.normalize()
        total = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        assert abs(total - 1.0) < 0.01





def _make_mem_ctx():
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

    def test_field_has_entries_for_all_outcomes(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        field = mem._belief.compute_potential_field(qs.id)
        assert len(field) == 3

    def test_high_weight_node_dominates(self):
        mem = _make_mem_ctx()
        h = mem.graph.get_node_by_label("high")
        h.weight = 10.0
        m = mem.graph.get_node_by_label("medium")
        m.weight = 1.0
        l = mem.graph.get_node_by_label("low")
        l.weight = 0.1
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        field = mem._belief.compute_potential_field(qs.id)
        assert field[h.id] > field[l.id]

    def test_field_sums_to_one(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        field = mem._belief.compute_potential_field(qs.id)
        assert abs(sum(field.values()) - 1.0) < 1e-10

    def test_custom_config(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        cfg = PotentialFieldConfig(
            weight_field=1.0,
            structural_field=0.0,
            recency_field=0.0,
            activation_field=0.0,
            edge_field=0.0,
        )
        field = mem._belief.compute_potential_field(qs.id, config=cfg)
        assert len(field) == 3

    def test_activation_values_influence_field(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        h = mem.graph.get_node_by_label("high")
        m = mem.graph.get_node_by_label("medium")
        l = mem.graph.get_node_by_label("low")
        activations = {h.id: 0.0, m.id: 0.0, l.id: 1.0}
        field = mem._belief.compute_potential_field(qs.id, activation_values=activations)
        assert field[l.id] > field[h.id]

    def test_empty_state_returns_empty(self):
        mem = _make_mem_ctx()
        with pytest.raises(NodeNotFoundError):
            mem.create_distribution(["nonexistent"], use_context_field=False)


class TestEvolveInContext:

    def test_amplitudes_change_after_evolution(self):
        mem = _make_mem_ctx()
        h = mem.graph.get_node_by_label("high")
        h.weight = 10.0
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        amps_before = [abs(i.amplitude) for i in qs.outcomes]
        mem._belief.evolve_in_context(qs.id)
        amps_after = [abs(i.amplitude) for i in qs.outcomes]
        assert amps_before != amps_after

    def test_coherence_time_reduced_for_dominant_state(self):
        mem = _make_mem_ctx()
        h = mem.graph.get_node_by_label("high")
        h.weight = 100.0
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        qs.outcomes[0].amplitude = 0.9
        qs.outcomes[1].amplitude = 0.1
        qs.outcomes[2].amplitude = 0.01
        qs.normalize()
        original_coherence = qs.coherence_time
        mem._belief.evolve_in_context(qs.id)
        assert qs.coherence_time < original_coherence

    def test_coherence_time_extended_for_uniform(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(label=label))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b", "c"])
        for outcome in qs.outcomes:
            outcome.amplitude = 1.0 / math.sqrt(3)
        qs.normalize()
        ql._states[qs.id] = qs
        ql.evolve_in_context(qs.id)
        assert qs.coherence_time == qs.base_coherence_time * 2.0


class TestCreateDistributionWithContextField:

    def test_context_field_applied_by_default(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"])
        amps = [abs(i.amplitude) for i in qs.outcomes]
        assert len(amps) == 3
        assert abs(sum(a ** 2 for a in amps) - 1.0) < 1e-10

    def test_context_field_disabled(self):
        mem = _make_mem_ctx()
        qs = mem.create_distribution(["high", "medium", "low"], use_context_field=False)
        amps = [abs(i.amplitude) for i in qs.outcomes]
        assert all(abs(a - amps[0]) < 1e-10 for a in amps)


class TestUseContextField:
    def test_context_field_biases_collapse(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["hub", "spoke1", "spoke2", "spoke3"]:
            mem.store(label)
        mem.relate("hub", "spoke1", label="connects")
        mem.relate("hub", "spoke2", label="connects")
        mem.relate("hub", "spoke3", label="connects")
        mem.relate("spoke1", "spoke2", label="connects")
        qs = mem.create_distribution(
            ["hub", "spoke1", "spoke2", "spoke3"],
            use_context_field=True,
        )
        assert qs.outcome_count == 4

    def test_context_field_changes_probabilities(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["connected", "isolated_a", "isolated_b"]:
            mem.store(label)
        mem.relate("connected", "isolated_a", label="e")
        qs_no_ctx = mem.create_distribution(
            ["connected", "isolated_a", "isolated_b"],
            use_context_field=False,
        )
        probs_plain = [abs(i.amplitude) ** 2 for i in qs_no_ctx.outcomes]
        qs_ctx = mem.create_distribution(
            ["connected", "isolated_a", "isolated_b"],
            use_context_field=True,
        )
        probs_ctx = [abs(i.amplitude) ** 2 for i in qs_ctx.outcomes]
        total_plain = sum(probs_plain)
        total_ctx = sum(probs_ctx)
        assert abs(total_plain - 1.0) < 1e-10
        assert abs(total_ctx - 1.0) < 1e-10
        assert probs_ctx != probs_plain

    def test_single_concept_context_field_no_effect(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("only")
        qs = mem.create_distribution(["only"], use_context_field=True)
        assert qs.outcome_count == 1


class TestSampleContextLabelRemapping:
    def test_context_with_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("bird")
        qs = mem.create_distribution(["cat", "dog", "bird"])
        result = mem.sample(qs, context={"dog": 10.0})
        assert result.label in {"cat", "dog", "bird"}

    def test_context_with_mixed_labels_and_ids(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        qs = mem.create_distribution(["x", "y"])
        x_node = mem.graph.get_node_by_label("x")
        assert x_node is not None
        result = mem.sample(qs, context={"x": 5.0, x_node.id: 5.0})
        assert result.label in {"x", "y"}

    def test_context_with_nonexistent_label_passes_through(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        qs = mem.create_distribution(["a", "b"])
        result = mem.sample(qs, context={"nonexistent_key": 5.0})
        assert result.label in {"a", "b"}


class TestSamplingProfileLearning:
    def test_record_profile_outcome(self):
        g = Hypergraph()
        qcl = BeliefLayer(g)
        qcl.record_basis_outcome("linguistic", True)
        qcl.record_basis_outcome("linguistic", True)
        qcl.record_basis_outcome("linguistic", False)
        eff = qcl.basis_effectiveness
        assert eff["linguistic"] == pytest.approx(2.0 / 3.0)

    def test_get_effective_profile_returns_valid(self):
        g = Hypergraph()
        qcl = BeliefLayer(g)
        profile = qcl.get_effective_basis()
        assert profile in qcl.bases

    def test_effective_bias_favors_successful(self):
        g = Hypergraph()
        n1 = Hypernode(label="test1")
        g.add_node(n1)
        qcl = BeliefLayer(g)
        for _ in range(50):
            qcl.record_basis_outcome("temporal", True)
        for _ in range(50):
            qcl.record_basis_outcome("linguistic", False)
        counts: dict[str, int] = {}
        for _ in range(100):
            b = qcl.get_effective_basis()
            counts[b] = counts.get(b, 0) + 1
        assert counts.get("temporal", 0) > counts.get("linguistic", 0)


class TestAdaptiveCoherenceTime:
    def test_adapt_scales_with_interpretations(self):
        qs = BeliefState(created_at=time.time())
        qs.add_outcome("n1", 0.5)
        qs.add_outcome("n2", 0.5)
        qs.normalize()
        qs.adapt_coherence(2)
        assert qs.coherence_time > qs.base_coherence_time

    def test_urgency_shortens_coherence(self):
        qs = BeliefState(created_at=time.time())
        qs.adapt_coherence(1, urgency=10.0)
        assert qs.coherence_time < qs.base_coherence_time

    def test_create_distribution_adapts(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl))
        qcl = BeliefLayer(g)
        ids = [g.get_node_by_label(lbl).id for lbl in "ABCD"]
        qs = qcl.create_distribution(ids)
        assert qs.coherence_time != qs.base_coherence_time


class TestSamplingTriggerDataclass:
    def test_defaults(self):
        t = SamplingTrigger(trigger_type="staleness_timeout", confidence=0.5)
        assert t.trigger_type == "staleness_timeout"
        assert t.confidence == 0.5
        assert t.details == {}

    def test_with_details(self):
        t = SamplingTrigger(
            trigger_type="single_outcome",
            confidence=1.0,
            details={"outcome": "cat", "amplitude": 0.95},
        )
        assert t.details["outcome"] == "cat"
        assert t.details["amplitude"] == 0.95

    def test_confidence_bounds(self):
        low = SamplingTrigger(trigger_type="x", confidence=0.0)
        high = SamplingTrigger(trigger_type="x", confidence=1.0)
        assert low.confidence == 0.0
        assert high.confidence == 1.0

    def test_details_not_shared(self):
        t1 = SamplingTrigger(trigger_type="a", confidence=0.5, details={"k": "v1"})
        t2 = SamplingTrigger(trigger_type="b", confidence=0.5, details={"k": "v2"})
        assert t1.details is not t2.details

