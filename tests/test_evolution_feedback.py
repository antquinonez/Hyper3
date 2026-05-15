from __future__ import annotations

import pytest

from hyper3.evolution import GraphMaintenanceEngine
from hyper3.evolution_feedback import (
    EvolutionSignals,
    FeedbackAwareEvolution,
    FeedbackEvolveResult,
)
from hyper3.feedback import OperationFeedback
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.rule_analytics import RuleAnalytics


def _make_graph(*labels: str) -> Hypergraph:
    g = Hypergraph()
    for label in labels:
        node = Hypernode(label=label)
        node.weight = 1.0
        g.add_node(node)
    return g


def _add_edge(
    graph: Hypergraph,
    src_label: str,
    tgt_label: str,
    label: str = "",
    rule: str | None = None,
) -> None:
    src = graph.get_node_by_label(src_label)
    tgt = graph.get_node_by_label(tgt_label)
    custom = {"rule": rule} if rule else {}
    edge = Hyperedge(
        source_ids=frozenset({src.id}),
        target_ids=frozenset({tgt.id}),
        label=label,
        metadata=Metadata(custom=custom),
    )
    graph.add_edge(edge)


class TestEvolutionSignals:
    def test_default_values(self):
        sig = EvolutionSignals()
        assert sig.low_activation_nodes == []
        assert sig.low_relevance_nodes == []
        assert sig.low_effectiveness_rules == []
        assert sig.high_failure_regions == []
        assert sig.fitness_trend == "stable"
        assert sig.fitness_value == 0.0

    def test_dict_like_access(self):
        sig = EvolutionSignals(fitness_trend="declining", fitness_value=0.3)
        assert sig["fitness_trend"] == "declining"
        assert sig["fitness_value"] == 0.3
        assert "fitness_trend" in sig

    def test_keys_and_items(self):
        sig = EvolutionSignals()
        assert "fitness_trend" in sig
        assert "fitness_trend" in dict(sig.items())


class TestFeedbackEvolveResult:
    def test_default_values(self):
        result = FeedbackEvolveResult()
        assert result.base_result is None
        assert result.extra_pruned == 0
        assert result.extra_reinforced == 0
        assert result.rule_demotions == 0
        assert result.signals is None

    def test_with_base_result(self):
        from hyper3.results import EvolveResult

        base = EvolveResult(decayed=2, pruned=1, merged=0, node_count=5, edge_count=3)
        result = FeedbackEvolveResult(base_result=base, extra_pruned=3)
        assert result.base_result.decayed == 2
        assert result.extra_pruned == 3

    def test_dict_like_access(self):
        result = FeedbackEvolveResult(extra_pruned=5, rule_demotions=2)
        assert result["extra_pruned"] == 5
        assert result["rule_demotions"] == 2


class TestFeedbackAwareEvolutionConstruction:
    def test_wraps_evolution_engine(self):
        g = _make_graph("a", "b")
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        assert fae._evolution is engine


class TestCollectSignals:
    def test_no_sources_returns_empty_signals(self):
        g = _make_graph("a", "b")
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g)
        assert signals.low_activation_nodes == []
        assert signals.low_effectiveness_rules == []
        assert signals.fitness_trend == "stable"
        assert signals.fitness_value == 0.0

    def test_with_activation_populates_low_activation_nodes(self):
        g = _make_graph("a", "b", "c")
        activation = SpreadingActivation(g)
        node_a = g.get_node_by_label("a")
        activation.stimulate(node_a.id, 0.5)
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g, activation=activation)
        assert node_a.id not in signals.low_activation_nodes
        node_b = g.get_node_by_label("b")
        node_c = g.get_node_by_label("c")
        assert node_b.id in signals.low_activation_nodes
        assert node_c.id in signals.low_activation_nodes

    def test_all_high_activation_no_low_nodes(self):
        g = _make_graph("a", "b")
        activation = SpreadingActivation(g)
        for node in g.nodes:
            activation.stimulate(node.id, 1.0)
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g, activation=activation)
        assert signals.low_activation_nodes == []

    def test_with_rule_analytics_populates_low_effectiveness(self):
        g = _make_graph("a", "b", "c")
        _add_edge(g, "a", "b")
        _add_edge(g, "b", "c")
        analytics = RuleAnalytics(g)
        analytics.record_rule_outcome("bad_rule", "applied")
        analytics.record_rule_outcome("good_rule", "useful")
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g, rule_analytics=analytics)
        assert "bad_rule" in signals.low_effectiveness_rules
        assert "good_rule" not in signals.low_effectiveness_rules

    def test_with_feedback_extracts_fitness_trend(self):
        g = _make_graph("a")
        feedback = OperationFeedback(g)
        feedback.record_evolution_outcome(0.9)
        feedback.record_evolution_outcome(0.7)
        feedback.record_evolution_outcome(0.5)
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g, feedback=feedback)
        assert signals.fitness_trend == "declining"

    def test_collect_signals_does_not_modify_source_state(self):
        g = _make_graph("a", "b")
        activation = SpreadingActivation(g)
        node_a = g.get_node_by_label("a")
        activation.stimulate(node_a.id, 0.5)
        state_before = dict(activation.activations)
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        fae.collect_signals(g, activation=activation)
        assert activation.activations == state_before


class TestEvolve:
    def test_no_signals_runs_base_evolution_only(self):
        g = _make_graph("a", "b")
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals()
        result = fae.evolve(g, signals)
        assert result.base_result is not None
        assert result.extra_pruned == 0
        assert result.extra_reinforced == 0
        assert result.rule_demotions == 0

    def test_declining_fitness_prunes_low_activation_low_weight_nodes(self):
        g = _make_graph("a", "b", "c")
        node_a = g.get_node_by_label("a")
        node_b = g.get_node_by_label("b")
        node_c = g.get_node_by_label("c")
        node_a.weight = 1.0
        node_b.weight = 0.3
        node_c.weight = 0.3
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(
            low_activation_nodes=[node_b.id, node_c.id],
            fitness_trend="declining",
        )
        result = fae.evolve(g, signals)
        assert result.extra_pruned == 2
        assert g.get_node(node_b.id) is None
        assert g.get_node(node_c.id) is None
        assert g.get_node(node_a.id) is not None

    def test_declining_fitness_skips_high_weight_low_activation(self):
        g = _make_graph("a", "b")
        node_a = g.get_node_by_label("a")
        node_b = g.get_node_by_label("b")
        node_a.weight = 1.0
        node_b.weight = 0.9
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(
            low_activation_nodes=[node_b.id],
            fitness_trend="declining",
        )
        result = fae.evolve(g, signals)
        assert result.extra_pruned == 0
        assert g.get_node(node_b.id) is not None

    def test_stable_fitness_reinforces_top_active_nodes(self):
        g = _make_graph("a", "b", "c", "d")
        node_a = g.get_node_by_label("a")
        node_b = g.get_node_by_label("b")
        node_c = g.get_node_by_label("c")
        node_d = g.get_node_by_label("d")
        node_a.weight = 0.5
        node_b.weight = 0.8
        node_c.weight = 0.6
        node_d.weight = 0.9
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(
            low_activation_nodes=[node_a.id],
            fitness_trend="stable",
        )
        weights_before = {n.id: n.weight for n in g.nodes}
        result = fae.evolve(g, signals)
        assert result.extra_reinforced == 3
        reinforced_ids = {n.id for n in g.nodes if n.weight > weights_before.get(n.id, 0)}
        assert len(reinforced_ids) >= 3

    def test_low_effectiveness_rules_removes_tagged_edges(self):
        g = _make_graph("a", "b", "c")
        _add_edge(g, "a", "b", label="rel", rule="bad_rule")
        _add_edge(g, "b", "c", label="rel", rule="good_rule")
        assert g.edge_count == 2
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(
            low_effectiveness_rules=["bad_rule"],
        )
        result = fae.evolve(g, signals)
        assert result.rule_demotions == 1
        assert g.edge_count == 1

    def test_no_rules_applied_no_demotions(self):
        g = _make_graph("a", "b")
        _add_edge(g, "a", "b", label="rel")
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(low_effectiveness_rules=["missing_rule"])
        result = fae.evolve(g, signals)
        assert result.rule_demotions == 0

    def test_empty_graph_no_crash(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals()
        result = fae.evolve(g, signals)
        assert result.base_result is not None
        assert result.extra_pruned == 0
        assert result.extra_reinforced == 0

    def test_signals_attached_to_result(self):
        g = _make_graph("a")
        engine = GraphMaintenanceEngine(g, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(fitness_trend="improving")
        result = fae.evolve(g, signals)
        assert result.signals is signals
        assert result.signals.fitness_trend == "improving"

    def test_round_trip_collect_then_evolve(self):
        g = _make_graph("a", "b", "c")
        node_b = g.get_node_by_label("b")
        node_c = g.get_node_by_label("c")
        node_b.weight = 0.2
        node_c.weight = 0.2
        activation = SpreadingActivation(g)
        node_a = g.get_node_by_label("a")
        activation.stimulate(node_a.id, 1.0)
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = fae.collect_signals(g, activation=activation)
        assert node_b.id in signals.low_activation_nodes
        assert node_c.id in signals.low_activation_nodes
        signals.fitness_trend = "declining"
        result = fae.evolve(g, signals)
        assert result.extra_pruned == 2
        assert g.node_count == 1


class TestIntegration:
    def test_evolve_with_feedback_returns_feedback_result(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="rel")
        from hyper3.evolution_feedback import FeedbackAwareEvolution

        mem._feedback_aware = FeedbackAwareEvolution(mem._evolution)
        result = mem.evolve_with_feedback()
        assert isinstance(result, FeedbackEvolveResult)
        assert result.base_result is not None
        assert result.signals is not None

    def test_evolve_with_feedback_without_aware_engine(self):
        from hyper3.memory import HypergraphMemory
        from hyper3.results import EvolveResult

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="rel")
        result = mem.evolve_with_feedback()
        assert isinstance(result, EvolveResult)

    def test_reinforcement_actually_increases_weight(self):
        g = _make_graph("a", "b", "c", "d")
        for n in g.nodes:
            n.weight = 0.5
        node_a = g.get_node_by_label("a")
        node_d = g.get_node_by_label("d")
        node_d.weight = 0.9
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01, merge_threshold=1.0)
        fae = FeedbackAwareEvolution(engine)
        signals = EvolutionSignals(
            low_activation_nodes=[node_a.id],
            fitness_trend="stable",
        )
        weights_before = {n.id: n.weight for n in g.nodes}
        fae.evolve(g, signals)
        any_increased = any(
            g.get_node(nid).weight > weights_before[nid]
            for nid in weights_before
            if g.get_node(nid) is not None
        )
        assert any_increased
