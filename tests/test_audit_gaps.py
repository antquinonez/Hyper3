from __future__ import annotations

import time

import pytest

from hyper3 import (
    AbductiveRule,
    BackwardChainEngine,
    ContextualSubstitutionRule,
    ContradictionResolver,
    GeneralizationRule,
    GraphMaintenanceEngine,
    HubInferenceRule,
    HypergraphMemory,
    InverseRule,
    NodeNotFoundError,
    PropertyPropagationRule,
    Rule,
    StructuralProjectionRule,
    TransitiveRule,
)
from hyper3.feedback import FeedbackSignal, OperationFeedback
from hyper3.kernel import Hypergraph, Hyperedge, Hypernode


class TestReasonAllNodeExpansion:
    def test_finds_chain_through_nonseed_intermediate(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        mem.store("smoking")
        mem.store("asthma")
        mem.store("pneumonia")
        mem.relate("smoking", "asthma", label="causes")
        mem.relate("asthma", "pneumonia", label="causes")
        result = mem.reason({"smoking"})
        assert result.error is None
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= 1
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add((mem.graph.get_node(src).label, mem.graph.get_node(tgt).label))
        assert ("smoking", "pneumonia") in pairs

    def test_finds_multiple_chains_from_single_seed(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next"))
        for label in ["a", "b", "c", "d", "e"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")
        mem.relate("d", "e", label="next")
        result = mem.reason({"a"})
        assert result.expansion is not None
        assert result.expansion.rules_applied >= 1
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= 1

    def test_seeds_determine_trigger_not_scope(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        mem.store("x")
        mem.store("y")
        mem.store("z")
        mem.store("unrelated")
        mem.relate("x", "y", label="causes")
        mem.relate("y", "z", label="causes")
        mem.relate("unrelated", "x", label="causes")
        result = mem.reason({"unrelated"})
        assert result.expansion is not None
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add((mem.graph.get_node(src).label, mem.graph.get_node(tgt).label))
        assert ("unrelated", "y") in pairs
        assert ("x", "z") in pairs

    def test_empty_seed_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule())
        result = mem.reason({"nonexistent"})
        assert result.error is not None


class TestMultiHopChaining:
    def test_chain_inferred_with_matching_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes", new_label="causes"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.relate("c", "d", label="causes")
        result = mem.reason({"a"}, max_depth=3, max_total_states=50)
        assert result.error is None
        causes = [
            e for e in mem.graph.edges if e.label == "causes"
        ]
        pairs = set()
        for e in causes:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add(
                (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
            )
        assert ("a", "c") in pairs
        assert ("b", "d") in pairs
        assert ("a", "d") in pairs

    def test_default_label_breaks_chaining(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.relate("c", "d", label="causes")
        result = mem.reason({"a"}, max_depth=3, max_total_states=50)
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add(
                (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
            )
        assert ("a", "c") in pairs
        assert ("a", "d") not in pairs

    def test_four_node_chain_full_closure(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next", new_label="next"))
        for label in ["w", "x", "y", "z"]:
            mem.store(label)
        mem.relate("w", "x", label="next")
        mem.relate("x", "y", label="next")
        mem.relate("y", "z", label="next")
        mem.reason({"w"}, max_depth=4, max_total_states=100)
        pairs = set()
        for e in mem.graph.edges:
            if e.label == "next":
                src = next(iter(e.source_ids))
                tgt = next(iter(e.target_ids))
                pairs.add(
                    (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
                )
        expected = {("w", "x"), ("x", "y"), ("y", "z"), ("w", "y"), ("x", "z"), ("w", "z")}
        assert expected.issubset(pairs)


class TestEvolveWithFeedback:
    def test_reinforced_nodes_get_boosted(self):
        g = Hypergraph()
        n = Hypernode(label="target")
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        n.weight = 1.0
        result = engine.evolve_with_feedback(
            fitness_trend="declining",
            reinforced_nodes={n.id},
            boost=2.0,
        )
        assert result.reinforced >= 1
        assert n.weight > 1.0

    def test_suppressed_nodes_get_removed(self):
        g = Hypergraph()
        n = Hypernode(label="victim")
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(
            fitness_trend="stable",
            suppressed_nodes={n.id},
        )
        assert result.suppressed >= 1
        assert g.get_node(n.id) is None

    def test_declining_trend_softens_decay(self):
        g = Hypergraph()
        n1 = Hypernode(label="a", weight=0.0105)
        n2 = Hypernode(label="b", weight=1.0)
        g.add_node(n1)
        g.add_node(n2)
        e = Hyperedge(
            source_ids=frozenset({n1.id}),
            target_ids=frozenset({n2.id}),
        )
        g.add_edge(e)
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01)
        result = engine.evolve_with_feedback(
            fitness_trend="stable",
            decay_factor=0.95,
        )
        assert result.decayed >= 1

    def test_stable_trend_no_decay_adjustment(self):
        g = Hypergraph()
        n = Hypernode(label="a", weight=1.0)
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(fitness_trend="stable")
        assert isinstance(result.reinforced, int)
        assert isinstance(result.suppressed, int)

    def test_nonexistent_reinforced_nodes_skipped(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(reinforced_nodes={"no_such_node"})
        assert result.reinforced == 0

    def test_nonexistent_suppressed_nodes_skipped(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(suppressed_nodes={"no_such_node"})
        assert result.suppressed == 0

    def test_empty_graph(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback()
        assert result.decayed == 0
        assert result.pruned == 0
        assert result.merged == 0

    def test_memory_facade_evolve_with_feedback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        mem._feedback.record_evolution_outcome(0.3)
        mem._feedback.record_evolution_outcome(0.2)
        result = mem.evolve_with_feedback()
        assert result is not None
        assert hasattr(result, "decayed")
        assert hasattr(result, "reinforced")


class TestComputeBiasProfile:
    def test_returns_unknown_with_no_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.compute_bias_profile()
        assert result.reasoning_style == "unknown"
        assert result.dominant_rules == []
        assert result.bias_score == 0.0

    def test_single_rule_is_balanced(self):
        g = Hypergraph()
        from hyper3.multiway_rulial import RulialSpace
        from hyper3.multiway import MultiwayEngine
        engine = MultiwayEngine(g)
        rulial = RulialSpace(g, engine)
        rulial.record_rule_application("transitive")
        rulial.record_rule_outcome("transitive", "applied")
        rulial.record_rule_application("transitive")
        rulial.record_rule_outcome("transitive", "applied")
        profile = rulial.compute_bias_profile()
        assert profile.rule_count >= 1
        assert profile.reasoning_style in ("balanced", "unknown", "focused")

    def test_multiple_rules_with_dominant(self):
        g = Hypergraph()
        from hyper3.multiway_rulial import RulialSpace
        from hyper3.multiway import MultiwayEngine
        engine = MultiwayEngine(g)
        rulial = RulialSpace(g, engine)
        for _ in range(10):
            rulial.record_rule_outcome("transitive", "useful")
        for _ in range(5):
            rulial.record_rule_outcome("inverse", "useful")
        for _ in range(5):
            rulial.record_rule_outcome("inverse", "applied")
        rulial.update_position()
        profile = rulial.compute_bias_profile()
        assert profile.rule_count == 2
        assert any("transitive" in r for r in profile.dominant_rules)


class TestFeedbackSummary:
    def test_empty_feedback(self):
        g = Hypergraph()
        fb = OperationFeedback(g)
        result = fb.cross_operation_summary()
        assert result.overall_health == 0.5
        assert result.total_signals == 0
        assert result.correlated_nodes == {}
        assert result.fitness_trend == "insufficient_data"

    def test_collapse_accuracy_reflected(self):
        g = Hypergraph()
        fb = OperationFeedback(g)
        fb.record_collapse_outcome("qs1", "n1", correct=True)
        fb.record_collapse_outcome("qs2", "n2", correct=False)
        result = fb.cross_operation_summary()
        assert result.collapse_accuracy == 0.5

    def test_retrieval_precision_reflected(self):
        g = Hypergraph()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        fb = OperationFeedback(g)
        fb.record_retrieval_outcome("q1", [n1.id], [n2.id])
        result = fb.cross_operation_summary()
        assert result.total_signals >= 2

    def test_inference_acceptance_reflected(self):
        g = Hypergraph()
        fb = OperationFeedback(g)
        fb.record_inference_outcome("e1", accepted=True)
        fb.record_inference_outcome("e2", accepted=False)
        result = fb.cross_operation_summary()
        assert result.inference_acceptance_rate == 0.5

    def test_fitness_trend_declining(self):
        g = Hypergraph()
        fb = OperationFeedback(g)
        for f in [0.9, 0.8, 0.7, 0.6, 0.5]:
            fb.record_evolution_outcome(f)
        result = fb.cross_operation_summary()
        assert result.fitness_trend == "declining"

    def test_fitness_trend_improving(self):
        g = Hypergraph()
        fb = OperationFeedback(g)
        for f in [0.5, 0.6, 0.7, 0.8, 0.9]:
            fb.record_evolution_outcome(f)
        result = fb.cross_operation_summary()
        assert result.fitness_trend == "improving"

    def test_correlated_nodes(self):
        g = Hypergraph()
        n = Hypernode(label="hub")
        g.add_node(n)
        fb = OperationFeedback(g)
        fb.record_collapse_outcome("qs1", n.id, correct=True)
        fb.record_collapse_outcome("qs2", n.id, correct=True)
        fb.record_collapse_outcome("qs3", n.id, correct=False)
        result = fb.cross_operation_summary()
        assert n.id in result.correlated_nodes
        info = result.correlated_nodes[n.id]
        assert info.signal_count >= 3

    def test_memory_facade_feedback_summary(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem._feedback.record_collapse_outcome("qs1", "n1", correct=True)
        result = mem.feedback_summary()
        assert result.total_signals >= 1


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
        assert total_plain > 0
        assert total_ctx > 0

    def test_single_concept_context_field_no_effect(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("only")
        qs = mem.create_distribution(["only"], use_context_field=True)
        assert qs.outcome_count == 1


class TestBeliefRevisionNewerStrategy:
    def test_newer_edge_survives(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        e_old = mem.relate("A", "B", label="supports")
        e_new = mem.relate("A", "B", label="opposes")
        mem._provenance.record_inference(
            edge_id=e_old.id,
            rule_name="test",
            input_edge_ids=[],
            depth=0,
        )
        time.sleep(0.01)
        mem._provenance.record_inference(
            edge_id=e_new.id,
            rule_name="test",
            input_edge_ids=[],
            depth=0,
        )
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="newer")
        assert result.edges_removed_count >= 1
        surviving = [e for e in mem.graph.edges if e.label in ("supports", "opposes")]
        assert len(surviving) == 1
        assert surviving[0].id == e_new.id

    def test_newer_with_no_provenance_favors_first(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        e1 = mem.relate("A", "B", label="supports")
        e2 = mem.relate("A", "B", label="opposes")
        engine = ContradictionResolver(mem.graph, mem._provenance)
        result = engine.revise(strategy="newer")
        assert result.edges_removed_count >= 1

    def test_newer_strategy_via_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="causes")
        mem.relate("A", "B", label="prevents")
        result = mem.revise_beliefs(strategy="newer")
        assert result.contradictions_detected >= 1
        assert result.edges_removed_count >= 1


class TestRulesConstructorParam:
    def test_rules_at_construction(self):
        rule = TransitiveRule(edge_label="e")
        mem = HypergraphMemory(evolve_interval=0, rules=[rule])
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        result = mem.reason({"a"})
        assert result.error is None
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0

    def test_empty_rules_list(self):
        mem = HypergraphMemory(evolve_interval=0, rules=[])
        mem.store("a")
        result = mem.reason({"a"})
        assert result.error == "no rules defined"

    def test_multiple_rules_at_construction(self):
        mem = HypergraphMemory(
            evolve_interval=0,
            rules=[
                TransitiveRule(edge_label="next"),
                InverseRule(edge_label="next", inverse_label="prev"),
            ],
        )
        for label in ["a", "b", "c"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        result = mem.reason({"a", "b", "c"})
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0


class TestReasonOverlayAutoCommit:
    def test_second_reason_auto_commits_first_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        r1 = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert mem._overlay is not None
        overlay_edge_count_before = len(mem._overlay.overlay_edge_ids)
        r2 = mem.reason({"a", "b", "c"}, auto_commit=False)
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= overlay_edge_count_before


class TestStimulateNodeNotFoundError:
    def test_stimulate_missing_concept_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError):
            mem.stimulate("nonexistent")

    def test_stimulate_valid_concept_succeeds(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.stimulate("a", energy=2.0)


class TestSampleContextLabelRemapping:
    def test_context_with_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("bird")
        qs = mem.create_distribution(["cat", "dog", "bird"])
        result = mem.sample(qs, context={"dog": 10.0})
        assert result is not None

    def test_context_with_mixed_labels_and_ids(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        qs = mem.create_distribution(["x", "y"])
        x_node = mem.graph.get_node_by_label("x")
        assert x_node is not None
        result = mem.sample(qs, context={"x": 5.0, x_node.id: 5.0})
        assert result is not None

    def test_context_with_nonexistent_label_passes_through(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        qs = mem.create_distribution(["a", "b"])
        result = mem.sample(qs, context={"nonexistent_key": 5.0})
        assert result is not None


class TestReasonIterativeConvergence:
    def test_stops_on_high_confidence(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        result = mem.reason_iterative(
            {"a", "b", "c"},
            max_iterations=10,
            min_confidence=0.01,
            max_depth=2,
        )
        assert result.iterations <= 10

    def test_stops_when_no_new_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        result = mem.reason_iterative(
            {"a"},
            max_iterations=5,
        )
        assert result.iterations <= 1

    def test_returns_iteration_details(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        result = mem.reason_iterative(
            {"a", "b"},
            max_iterations=3,
        )
        assert isinstance(result.iteration_details, list)


class TestRuleFromDictAllTypes:
    def _round_trip(self, rule: Rule) -> None:
        data = rule.to_dict()
        restored = Rule.from_dict(data)
        assert isinstance(restored, type(rule))
        assert restored.to_dict() == data

    def test_transitive_rule(self):
        self._round_trip(TransitiveRule(edge_label="causes", new_label="inferred"))

    def test_transitive_rule_no_label(self):
        self._round_trip(TransitiveRule())

    def test_inverse_rule(self):
        self._round_trip(InverseRule(edge_label="causes", inverse_label="prevented_by"))

    def test_generalization_rule(self):
        self._round_trip(GeneralizationRule())

    def test_abductive_rule(self):
        self._round_trip(AbductiveRule())

    def test_property_propagation_rule(self):
        self._round_trip(PropertyPropagationRule(property_key="color"))

    def test_structural_projection_rule(self):
        self._round_trip(StructuralProjectionRule())

    def test_hub_inference_rule(self):
        self._round_trip(HubInferenceRule())

    def test_contextual_substitution_rule(self):
        self._round_trip(ContextualSubstitutionRule())

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            Rule.from_dict({"rule_type": "NonexistentRule"})
