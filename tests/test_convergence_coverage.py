import pytest
from hyper3 import (
    StateConvergenceEngine,
    ConvergenceRecord,
    HypergraphMemory,
    SamplingTrigger,
    Hyperedge,
    Hypergraph,
    Hypernode,
    EvidenceInteraction,
    Outcome,
    SamplingProfile,
    Metadata,
    Modality,
    MultiwayEngine,
    BeliefLayer,
    ConceptCorrelation,
    BeliefState,
    TransitiveRule,
)


class TestCausalInvarianceDeep:
    def test_state_similarity_both_empty(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        mw.expand(set(), [], max_depth=1)
        from hyper3.multiway import MultiwayState
        s1 = MultiwayState(active_node_ids=frozenset())
        s2 = MultiwayState(active_node_ids=frozenset())
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.compute_state_similarity(s1, s2) == 1.0

    def test_state_similarity_one_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        from hyper3.multiway import MultiwayState
        s1 = MultiwayState(active_node_ids=frozenset({"a"}))
        s2 = MultiwayState(active_node_ids=frozenset())
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.compute_state_similarity(s1, s2) == 0.0

    def test_no_duplicate_merges_on_repeated_enforce(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a"}, [rule], max_depth=2, max_total_states=20)
        ci = StateConvergenceEngine(g, mw.multiway, threshold=0.3)
        r1 = ci.enforce()
        r2 = ci.enforce()
        assert r2["merges_performed"] == 0

    def test_invariants_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        ci = StateConvergenceEngine(g, mw.multiway)
        assert ci.invariants == []

    def test_enforce_reports_reduction(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a"}, [rule], max_depth=2, max_total_states=20)
        ci = StateConvergenceEngine(g, mw.multiway, threshold=0.3)
        report = ci.enforce()
        assert "reduction" in report
        assert isinstance(report["reduction"], int)


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
        assert result is not None

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
        assert result is not None

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
        assert ql.get_basis("linguistic") is not None
        assert ql.get_basis("nonexistent") is None

    def test_evolve_amplitudes_missing(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        ql.evolve_amplitudes("nonexistent", {"a": 2.0})

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
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        for a_id, b_id, sim in pairs:
            assert l1.id not in (a_id, b_id)

    def test_find_invariants_pair_found(self):
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        assert len(pairs) >= 1
        assert pairs[0][2] >= 0.3

    def test_merge_invariant_states_full(self):
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        assert len(merged) >= 1
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
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        assert result is not None

    def test_detect_sampling_triggers_interference_maxima(self):
        import time as _time
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
        assert isinstance(result, dict)

    def test_correlations_property(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        ql.create_correlation(["a"], ["b"], {("a", "b"): 0.5})
        ents = ql.correlations
        assert len(ents) == 1

    def test_merge_consumed_second_pair(self):
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        assert len(merged) >= 1

    def test_merge_missing_state(self):
        from hyper3.multiway import MultiwayGraph, MultiwayState
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
        assert result is not None

    def test_detect_sampling_triggers_single_outcome(self):
        import time as _time
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
        assert isinstance(result, dict)

    def test_add_basis_and_bases_property(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        profile = SamplingProfile(name="custom_test", dimensions=["d1"], weights={"d1": 1.0})
        ql.add_basis(profile)
        assert ql.get_basis("custom_test") is not None
        all_bases = ql.bases
        assert "custom_test" in all_bases

    def test_sample_with_profile_negative_metadata_no_crash(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="n1", metadata=Metadata(custom={"semantic": -2.0})))
        g.add_node(Hypernode(id="n2", metadata=Metadata(custom={"semantic": 1.0})))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["n1", "n2"])
        result = ql.sample_with_profile(qs.id, "linguistic")
        assert result is not None
