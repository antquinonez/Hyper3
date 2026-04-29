import pytest
from hyper3 import (
    SamplingTrigger,
    Hyperedge,
    Hypergraph,
    Hypernode,
    EvidenceInteraction,
    Outcome,
    SamplingProfile,
    BeliefLayer,
    ConceptCorrelation,
    BeliefState,
)


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
        assert isinstance(patterns, list)

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
        ent = ql.create_correlation(
            ["cat", "dog"], ["bird", "fish"],
            {("cat", "bird"): 0.9, ("dog", "fish"): 0.8},
        )
        preds = ql.sample_correlated(qs.id, "cat")
        assert isinstance(preds, dict)
