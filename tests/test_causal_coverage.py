import pytest
from hyper3 import (
    CausalInvarianceEngine,
    CausalInvariant,
    CognitiveMemory,
    CollapseTrigger,
    Hyperedge,
    Hypergraph,
    Hypernode,
    InterferencePattern,
    Interpretation,
    MeasurementBasis,
    Metadata,
    Modality,
    MultiwayEngine,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
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
        ci = CausalInvarianceEngine(g, mw.multiway)
        assert ci.compute_state_similarity(s1, s2) == 1.0

    def test_state_similarity_one_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        from hyper3.multiway import MultiwayState
        s1 = MultiwayState(active_node_ids=frozenset({"a"}))
        s2 = MultiwayState(active_node_ids=frozenset())
        ci = CausalInvarianceEngine(g, mw.multiway)
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
        ci = CausalInvarianceEngine(g, mw.multiway, threshold=0.3)
        r1 = ci.enforce()
        r2 = ci.enforce()
        assert r2["invariants_found"] == 0

    def test_invariants_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [], max_depth=1)
        ci = CausalInvarianceEngine(g, mw.multiway)
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
        ci = CausalInvarianceEngine(g, mw.multiway, threshold=0.3)
        report = ci.enforce()
        assert "reduction" in report
        assert isinstance(report["reduction"], int)


class TestQuantumCollapseDeep:
    def test_collapse_born_rule_distribution(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.9)
        qs.add_interpretation("b", 0.1)
        counts = {"a": 0, "b": 0}
        for _ in range(500):
            qs2 = QuantumState()
            qs2.add_interpretation("a", 0.9)
            qs2.add_interpretation("b", 0.1)
            result = qs2.collapse()
            counts[result.node_id] += 1
        assert counts["a"] > counts["b"]
        assert counts["a"] > 200

    def test_collapse_single_interpretation(self):
        qs = QuantumState()
        qs.add_interpretation("only", 1.0)
        result = qs.collapse()
        assert result.node_id == "only"

    def test_collapse_zero_total(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.0)
        qs.add_interpretation("b", 0.0)
        result = qs.collapse()
        assert result is not None

    def test_probability_uses_abs(self):
        qs = QuantumState()
        qs.add_interpretation("a", -0.5)
        assert abs(qs.interpretations[0].probability - 0.25) < 0.01

    def test_quantum_state_age_and_decoherence(self):
        qs = QuantumState(created_at=0.0, coherence_time=0.001)
        assert qs.is_decoherent
        assert qs.age > 0.0


class TestQuantumLayerDeep:
    def test_collapse_with_basis_missing_basis(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a"])
        result = ql.collapse_with_basis(qs.id, "nonexistent_basis")
        assert result is not None

    def test_collapse_with_basis_empty_state(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        result = ql.collapse_with_basis("nonexistent", "linguistic")
        assert result is None

    def test_get_entanglement(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = QuantumCognitiveLayer(g)
        assert ql.get_entanglement("nonexistent") is None

    def test_get_basis(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        assert ql.get_basis("linguistic") is not None
        assert ql.get_basis("nonexistent") is None

    def test_evolve_amplitudes_missing(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        ql.evolve_amplitudes("nonexistent", {"a": 2.0})

    def test_entanglement_predict_no_match(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.9},
        )
        preds = ent.predict("nonexistent", "value")
        assert preds == {}

    def test_entanglement_predict_zero_correlation(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.0},
        )
        preds = ent.predict("a", "value")
        assert preds == {}

    def test_interference_constructive(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState()
        qs.add_interpretation("a", 0.5)
        qs.add_interpretation("a", 0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interference(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_constructive
        assert not patterns[0].is_destructive

    def test_interference_destructive(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState()
        qs.add_interpretation("a", 0.5)
        qs.add_interpretation("a", -0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interference(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_destructive
        assert not patterns[0].is_constructive

    def test_interference_single_interpretation(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a"])
        patterns = ql.compute_interference(qs.id)
        assert patterns == []

    def test_collapse_entangled_missing(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        result = ql.collapse_entangled("nonexistent", "a")
        assert result == {}

    def test_collapse_triggers_already_collapsed(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a"])
        qs.collapsed = True
        triggers = ql.detect_collapse_triggers(qs.id)
        assert triggers == []

    def test_collapse_triggers_dominant(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState(created_at=0.0, coherence_time=0.0)
        qs.add_interpretation("a", 0.95)
        qs.add_interpretation("b", 0.01)
        ql._states[qs.id] = qs
        triggers = ql.detect_collapse_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "decoherence_timeout" in types

    def test_measurement_basis_default_weight(self):
        basis = MeasurementBasis(name="test", dimensions=["x"])
        assert basis.weight_for("y") == 1.0

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
        ci = CausalInvarianceEngine(g, mw)
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
        ci._consumed_states.add(l0.id)
        ci._consumed_states.add(l2.id)
        merged = ci.merge_invariant_states()
        for inv in merged:
            assert l0.id not in (inv.state_a_id, inv.state_b_id)
            assert l2.id not in (inv.state_a_id, inv.state_b_id)

    def test_entanglement_predict_node_b_match(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.8},
        )
        preds = ent.predict("b", "value_a")
        assert "a" in preds
        assert preds["a"] == "value_a"

    def test_entanglement_predict_negative_correlation(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): -0.5},
        )
        preds = ent.predict("b", "value_a")
        assert preds["a"] == "opposite"

    def test_collapse_nonexistent_state(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        assert ql.collapse("nonexistent_id") is None

    def test_collapse_with_basis_missing_node(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["ghost_node"])
        result = ql.collapse_with_basis(qs.id, "linguistic")
        assert result is not None

    def test_detect_collapse_triggers_interference_maxima(self):
        import time as _time
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState(created_at=_time.time())
        qs.add_interpretation("a", 0.6)
        qs.add_interpretation("a", 0.5)
        ql._states[qs.id] = qs
        triggers = ql.detect_collapse_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "interference_maxima" in types
        it = next(t for t in triggers if t.trigger_type == "interference_maxima")
        assert it.details["amplitude"] > 0.7

    def test_collapse_entangled_empty_interpretations(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState()
        ql._states[qs.id] = qs
        result = ql.collapse_entangled(qs.id, "a")
        assert result == {}

    def test_collapse_entangled_fake_entanglement(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a"])
        qs.entanglement_ids.append("fake_ent_id")
        result = ql.collapse_entangled(qs.id, "a")
        assert isinstance(result, dict)

    def test_entanglements_property(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        ql.create_entanglement(["a"], ["b"], {("a", "b"): 0.5})
        ents = ql.entanglements
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
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
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        for inv in merged:
            assert inv.state_a_id != l0.id

    def test_entanglement_predict_node_a_match(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.8},
        )
        preds = ent.predict("a", "value_a")
        assert "b" in preds
        assert preds["b"] == "value_a"

    def test_collapse_with_basis_node_with_metadata(self):
        g = Hypergraph()
        node = Hypernode(id="a", label="a")
        node.metadata.custom = {"semantic": 0.8, "syntactic": 0.5, "pragmatic": 0.3}
        g.add_node(node)
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a"])
        result = ql.collapse_with_basis(qs.id, "linguistic")
        assert result is not None

    def test_detect_collapse_triggers_single_interpretation(self):
        import time as _time
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState(created_at=_time.time())
        qs.add_interpretation("a", 1.0)
        ql._states[qs.id] = qs
        triggers = ql.detect_collapse_triggers(qs.id)
        types = [t.trigger_type for t in triggers]
        assert "single_interpretation" in types

    def test_create_entanglement_links_active_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        ent = ql.create_entanglement(["a"], ["b"], {("a", "b"): 0.8})
        assert ent.id in qs.entanglement_ids

    def test_collapse_entangled_with_predictions(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        ql.create_entanglement(["a"], ["b"], {("a", "b"): 0.8})
        result = ql.collapse_entangled(qs.id, "a")
        assert isinstance(result, dict)

    def test_add_basis_and_bases_property(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        basis = MeasurementBasis(name="custom_test", dimensions=["d1"], weights={"d1": 1.0})
        ql.add_basis(basis)
        assert ql.get_basis("custom_test") is not None
        all_bases = ql.bases
        assert "custom_test" in all_bases

    def test_collapse_with_basis_negative_metadata_no_crash(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="n1", metadata=Metadata(custom={"semantic": -2.0})))
        g.add_node(Hypernode(id="n2", metadata=Metadata(custom={"semantic": 1.0})))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["n1", "n2"])
        result = ql.collapse_with_basis(qs.id, "linguistic")
        assert result is not None
