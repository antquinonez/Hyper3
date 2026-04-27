import time
import pytest
from hyper3 import (
    CausalInvarianceEngine,
    CausalInvariant,
    Hypergraph,
    Hypernode,
    Hyperedge,
    Interpretation,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
    NodeNotFoundError,
    QuantumCognitiveLayer,
    QuantumState,
    TransitiveRule,
    InverseRule,
    CognitiveMemory,
    Modality,
)


class TestCausalInvarianceEngine:
    def _build_multiway(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = MultiwayEngine(g)
        engine.expand({"a", "b", "c", "d"}, [TransitiveRule(edge_label="rel")], max_depth=2)
        return g, engine

    def test_state_similarity_identical(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        states = mw.states
        if len(states) >= 2:
            ci = CausalInvarianceEngine(g, mw)
            sim = ci.compute_state_similarity(states[0], states[0])
            assert sim == 1.0

    def test_state_similarity_different(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = CausalInvarianceEngine(g, mw)
        root = mw.get_root()
        leaves = mw.get_leaves()
        if root and leaves:
            sim = ci.compute_state_similarity(root, leaves[0])
            assert 0.0 <= sim <= 1.0

    def test_find_invariants(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
        invariants = ci.find_invariants()
        assert isinstance(invariants, list)

    def test_merge_invariant_states(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
        merged = ci.merge_invariant_states()
        assert isinstance(merged, list)
        for inv in merged:
            assert isinstance(inv, CausalInvariant)
            assert inv.merged_into is not None

    def test_enforce(self):
        g, engine = self._build_multiway()
        mw = engine.multiway
        ci = CausalInvarianceEngine(g, mw, threshold=0.3)
        report = ci.enforce()
        assert "invariants_found" in report
        assert "states_before" in report
        assert "states_after" in report


class TestQuantumState:
    def test_create(self):
        qs = QuantumState()
        assert not qs.collapsed
        assert qs.superposition_count == 0

    def test_add_interpretation(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.7)
        qs.add_interpretation("b", 0.3)
        assert qs.superposition_count == 2

    def test_normalize(self):
        qs = QuantumState()
        qs.add_interpretation("a", 3.0)
        qs.add_interpretation("b", 4.0)
        qs.normalize()
        total_prob = sum(i.probability for i in qs.interpretations)
        assert abs(total_prob - 1.0) < 0.01

    def test_collapse(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.9)
        qs.add_interpretation("b", 0.1)
        selected = qs.collapse()
        assert selected is not None
        assert qs.collapsed
        assert qs.collapsed_to is not None

    def test_collapse_with_context(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.5)
        qs.add_interpretation("b", 0.5)
        counts = {"a": 0, "b": 0}
        for _ in range(200):
            qs2 = QuantumState()
            qs2.add_interpretation("a", 0.5)
            qs2.add_interpretation("b", 0.5)
            result = qs2.collapse(context_weights={"b": 10.0})
            counts[result.node_id] += 1
        assert counts["b"] > counts["a"]

    def test_collapse_empty(self):
        qs = QuantumState()
        assert qs.collapse() is None

    def test_probability(self):
        qs = QuantumState()
        qs.add_interpretation("a", 0.6)
        qs.add_interpretation("b", 0.8)
        qs.normalize()
        total = sum(i.probability for i in qs.interpretations)
        assert abs(total - 1.0) < 0.01


class TestQuantumCognitiveLayer:
    def test_create_superposition(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        assert qs.superposition_count == 2

    def test_create_from_labels(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="concept_x"))
        g.add_node(Hypernode(id="y", label="concept_y"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_from_labels(["concept_x", "concept_y"])
        assert qs.superposition_count == 2

    def test_collapse_state(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        result = ql.collapse(qs.id)
        assert result is not None
        assert qs.collapsed

    def test_evolve_amplitudes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        ql.evolve_amplitudes(qs.id, {"a": 5.0, "b": 0.1})
        for interp in qs.interpretations:
            if interp.node_id == "a":
                assert interp.amplitude > 0.5

    def test_active_and_collapsed(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        ql = QuantumCognitiveLayer(g)
        qs1 = ql.create_superposition(["a"])
        qs2 = ql.create_superposition(["a"])
        assert len(ql.active_superpositions) == 2
        ql.collapse(qs1.id)
        assert len(ql.active_superpositions) == 1
        assert len(ql.collapsed_states) == 1

    def test_get_state(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        assert ql.get_state("nonexistent") is None


class TestCognitiveMemoryIntegration:
    def test_reason_with_rules(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        result = mem.reason({"a", "b", "c"})
        assert "expansion" in result
        assert result["expansion"]["rules_applied"] > 0

    def test_reason_no_rules(self):
        mem = CognitiveMemory()
        mem.store("a")
        result = mem.reason({"a"})
        assert "error" in result

    def test_reason_no_seed(self):
        mem = CognitiveMemory()
        mem.add_rules(TransitiveRule())
        result = mem.reason({"nonexistent"})
        assert "error" in result

    def test_superpose_and_collapse(self):
        mem = CognitiveMemory()
        mem.store("cat")
        mem.store("bank_river")
        mem.store("bank_finance")
        qs = mem.superpose(["cat", "bank_river", "bank_finance"])
        assert qs.superposition_count == 3
        result = mem.collapse(qs, context={"bank_finance": 5.0})
        assert result is not None
        assert qs.collapsed

    def test_superpose_empty(self):
        mem = CognitiveMemory()
        with pytest.raises(NodeNotFoundError):
            mem.superpose(["nonexistent"])

    def test_lateral_insights(self):
        mem = CognitiveMemory()
        for label in ["a", "b", "c"]:
            mem.store(label)
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"), InverseRule(edge_label="rel", inverse_label="inv"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        insights = mem.lateral_insights("a")
        assert isinstance(insights, list)

    def test_lateral_insights_no_multiway(self):
        mem = CognitiveMemory()
        assert mem.lateral_insights("x") == []

    def test_stats_includes_new_fields(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        stats = mem.stats()
        assert "multiway_states" in stats
        assert "quantum_active" in stats
        assert "quantum_collapsed" in stats

    def test_multiway_property(self):
        mem = CognitiveMemory()
        assert mem.multiway is None
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"a", "b"})
        assert mem.multiway is not None

    def test_quantum_property(self):
        mem = CognitiveMemory()
        assert mem.quantum is not None

    def test_full_pipeline(self):
        mem = CognitiveMemory(evolve_interval=0)
        for label in ["rain", "clouds", "wet_ground", "flooding", "umbrella"]:
            mem.store(label, modalities={Modality.CONCEPTUAL})
        mem.relate("rain", "wet_ground", label="causes")
        mem.relate("wet_ground", "flooding", label="causes")
        mem.relate("clouds", "rain", label="leads_to")
        mem.relate("umbrella", "rain", label="protects_from")
        mem.add_rules(
            TransitiveRule(edge_label="causes"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
        )
        result = mem.reason({"rain", "clouds", "wet_ground", "flooding", "umbrella"}, max_depth=3)
        assert result["expansion"]["rules_applied"] > 0
        qs = mem.superpose(["rain", "clouds", "umbrella"])
        assert qs.superposition_count == 3
        selected = mem.collapse(qs)
        assert selected is not None
        mem.evolve()
        stats = mem.stats()
        assert stats["nodes"] >= 5
        assert stats["multiway_states"] > 0
