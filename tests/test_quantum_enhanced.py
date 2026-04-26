import pytest
from hyper3 import (
    CollapseTrigger,
    Hyperedge,
    Hypergraph,
    Hypernode,
    InterferencePattern,
    Interpretation,
    MeasurementBasis,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)


def _build_graph():
    g = Hypergraph()
    for label in ["cat", "dog", "bird", "fish"]:
        g.add_node(Hypernode(id=label, label=label))
    return g


class TestQuantumEntanglement:
    def test_create_entanglement(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        ent = ql.create_entanglement(
            ["cat", "dog"],
            ["bird", "fish"],
            {("cat", "bird"): 0.8, ("dog", "fish"): -0.6},
        )
        assert isinstance(ent, QuantumEntanglement)
        assert ent.strength > 0
        assert "cat" in ent.group_a_node_ids
        assert "fish" in ent.group_b_node_ids

    def test_entanglement_predict(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): 0.9},
        )
        preds = ent.predict("a", "pet")
        assert "b" in preds
        assert preds["b"] == "pet"

    def test_entanglement_negative_correlation(self):
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset({"a"}),
            group_b_node_ids=frozenset({"b"}),
            correlation_matrix={("a", "b"): -0.9},
        )
        preds = ent.predict("a", "pet")
        assert preds["b"] == "opposite"


class TestInterference:
    def test_compute_interference(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["cat", "dog", "bird"], [0.7, -0.5, 0.3])
        patterns = ql.compute_interference(qs.id)
        assert isinstance(patterns, list)

    def test_interference_pattern_properties(self):
        p = InterferencePattern(node_id="n1", constructive=0.8, destructive=0.0, net_amplitude=0.8)
        assert p.is_constructive
        assert not p.is_destructive

    def test_destructive_interference(self):
        p = InterferencePattern(node_id="n1", constructive=0.0, destructive=-0.5, net_amplitude=-0.5)
        assert p.is_destructive
        assert not p.is_constructive


class TestMeasurementBasis:
    def test_builtin_bases(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        assert "linguistic" in ql.bases
        assert "temporal" in ql.bases
        assert "emotional" in ql.bases
        assert "pragmatic" in ql.bases

    def test_add_custom_basis(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        custom = MeasurementBasis(name="custom", dimensions=["x", "y"], weights={"x": 0.6, "y": 0.4})
        ql.add_basis(custom)
        assert ql.get_basis("custom") is not None
        assert custom.weight_for("x") == 0.6
        assert custom.weight_for("z") == 0.5

    def test_collapse_with_basis(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["cat", "dog", "bird"])
        result = ql.collapse_with_basis(qs.id, "linguistic")
        assert isinstance(result, Interpretation)
        assert result.node_id in {"cat", "dog", "bird"}


class TestCollapseTriggers:
    def test_decoherence_trigger(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState(created_at=0.0, coherence_time=0.001)
        qs.add_interpretation("cat", 0.7)
        ql._states[qs.id] = qs
        triggers = ql.detect_collapse_triggers(qs.id)
        assert any(t.trigger_type == "decoherence_timeout" for t in triggers)

    def test_single_interpretation_trigger(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["cat"])
        triggers = ql.detect_collapse_triggers(qs.id)
        assert any(t.trigger_type == "single_interpretation" for t in triggers)

    def test_no_triggers_for_fresh_state(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["cat", "dog", "bird"])
        triggers = ql.detect_collapse_triggers(qs.id)
        decoherence = [t for t in triggers if t.trigger_type == "decoherence_timeout"]
        assert len(decoherence) == 0


class TestCollapseEntangled:
    def test_collapse_entangled(self):
        g = _build_graph()
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["cat", "dog"])
        ent = ql.create_entanglement(
            ["cat", "dog"], ["bird", "fish"],
            {("cat", "bird"): 0.9, ("dog", "fish"): 0.8},
        )
        preds = ql.collapse_entangled(qs.id, "cat")
        assert isinstance(preds, dict)
