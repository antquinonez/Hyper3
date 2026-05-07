import os
import tempfile

import pytest

from hyper3 import (
    AbductiveRule,
    GeneralizationRule,
    HypergraphMemory,
    InverseRule,
    Modality,
    MultiPerspectiveAnalyzer,
    PropertyPropagationRule,
    SamplingProfile,
    TransitiveRule,
)


class TestIntegrationFullPipeline:
    def test_knowledge_graph_lifecycle(self):
        mem = HypergraphMemory(evolve_interval=0)

        for name in ["ignition", "fuel", "combustion", "heat", "rotation", "electricity", "battery"]:
            mem.add(name, modalities={Modality.CONCEPTUAL})

        mem.link("battery", "electricity", label="powers")
        mem.link("electricity", "ignition", label="causes")
        mem.link("ignition", "combustion", label="causes")
        mem.link("fuel", "combustion", label="enables")
        mem.link("combustion", "heat", label="causes")
        mem.link("combustion", "rotation", label="causes")

        mem.add_rules(
            TransitiveRule(edge_label="causes"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
        )

        result = mem.reason({"battery", "fuel"}, max_depth=3, max_total_states=30)
        assert result["expansion"]["states_created"] == 8
        assert result["expansion"]["rules_applied"] == 7

        mem.auto_discover_and_apply()

        qs = mem.create_distribution(["battery", "fuel", "ignition"])
        assert qs.outcome_count == 3

        interpretation = mem.sample(qs, context={"battery": 2.0})
        assert interpretation is not None
        assert qs.resolved
        assert interpretation.label in {"battery", "fuel", "ignition"}

        mem.evolve()
        stats = mem.stats()
        assert stats["nodes"] == 7
        assert stats["edges"] == 13
        assert stats["log_size"] > 0

    def test_save_load_continue_reasoning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "knowledge.json")

            mem = HypergraphMemory(evolve_interval=0)
            for name in ["x", "y", "z"]:
                mem.add(name)
            mem.link("x", "y", label="rel")
            mem.link("y", "z", label="rel")
            mem.add_rules(TransitiveRule(edge_label="rel"))
            r1 = mem.reason({"x", "y", "z"}, max_depth=2)
            assert r1["expansion"]["rules_applied"] == 1
            mem.save(path)
            edges_after_session1 = mem.size[1]
            assert edges_after_session1 == 3

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.size[0] == 3
            assert mem2.size[1] == edges_after_session1
            assert mem2.log.size == 7

            mem2.add("w")
            mem2.link("z", "w", label="rel")
            mem2.add_rules(TransitiveRule(edge_label="rel"))
            assert mem2.size[1] == 4

    def test_belief_diagnostic_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for name in ["battery_weak", "battery_dead", "alternator_bad", "starter_bad"]:
            mem.add(name)

        qs = mem.create_distribution(["battery_weak", "alternator_bad", "starter_bad"])

        ent = mem.correlate(
            ["battery_weak", "battery_dead"],
            ["starter_bad"],
            {("battery_weak", "starter_bad"): 0.9, ("battery_dead", "starter_bad"): 0.95},
        )
        assert ent.strength == pytest.approx(0.925, abs=0.01)

        collapsed = mem.sample_with_profile(qs, "pragmatic")
        assert collapsed is not None
        assert collapsed.label in {"battery_weak", "alternator_bad", "starter_bad"}
        assert qs.resolved

    def test_anomaly_boundary_mapping(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("simple_concept")
        mem.add("self-referential structure")
        mem.add("all universal statements")

        regions = mem.map_boundaries(["simple_concept", "self-referential structure", "all universal statements"])
        assert len(regions) == 3
        statuses = {r.status for r in regions}
        assert statuses == {"low_risk"}

        result = mem.detect_structural_anomalies("simple_concept")
        assert result.anomaly_status == "low_risk"
        assert result.boundary_score == pytest.approx(0.05, abs=0.01)

    def test_multi_frame_analysis_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("engine", data={"type": "mechanical"})
        mem.link("engine", "engine", label="self_ref")

        optimal_name, optimal = mem.select_optimal_frame("engine")
        assert optimal_name in {"classical", "quantum", "hypergraph", "probabilistic"}
        assert 0.0 <= optimal.complexity <= 1.0

        analyses = mem.multi_frame_analysis("engine")
        assert len(analyses) == 4
        expected_approaches = {
            "classical": "exhaustive_analysis",
            "quantum": "single_interpretation",
            "hypergraph": "multi_dimensional_traversal",
            "probabilistic": "importance_sampling",
        }
        for frame, analysis in analyses.items():
            assert analysis.solution_approach == expected_approaches[frame]

        custom = SamplingProfile(name="diagnostic", dimensions=["severity", "frequency"])
        mem.belief_layer.add_basis(custom)
        basis = mem.belief_layer.get_basis("diagnostic")
        assert basis is not None
        assert basis.name == "diagnostic"

    def test_rule_analytics_monitor_stats_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.add(f"concept_{i}")
        for i in range(9):
            mem.link(f"concept_{i}", f"concept_{i+1}", label="chain")

        rule_analytics = mem.rule_analytics
        rule_analytics.record_rule_application("transitive")
        rule_analytics.record_rule_application("inverse")
        rule_analytics.record_rule_application("generalization")
        pos = rule_analytics.update_position()
        assert 0.0 < pos.graph_activity_density <= 1.0
        assert 0.0 < pos.structural_complexity <= 1.0

        patterns = rule_analytics.find_meta_patterns()
        pattern_types = {p.pattern_type for p in patterns}
        assert "recurring_relation" in pattern_types
        assert "chain_motif" in pattern_types

        insights = rule_analytics.generate_high_level_insights()
        principles = [ins.principle for ins in insights]
        assert any("Dominant relation" in p for p in principles)

        introspection = mem.introspect()
        assert 0.8 < introspection.system_health.fitness <= 1.0

    def test_rule_discovery_and_application_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d", "e"]:
            mem.add(label)
        mem.link("a", "b", label="next")
        mem.link("b", "c", label="next")
        mem.link("c", "d", label="next")
        mem.link("d", "e", label="next")
        mem.link("b", "a", label="prev")
        mem.link("c", "b", label="prev")
        mem.link("d", "c", label="prev")

        result = mem.auto_discover_and_apply()
        assert result["total_patterns"] == 4

        mem.add_rules(TransitiveRule(edge_label="next"))
        reason = mem.reason({"a", "b", "c"}, max_depth=2, max_total_states=20)
        assert reason["expansion"]["states_created"] == 11
        assert reason["expansion"]["rules_applied"] == 10

    def test_evolution_decay_and_prune(self):
        mem = HypergraphMemory(evolve_interval=0, decay_threshold=0.5)
        mem.add("heavy")
        mem.add("light")
        mem.link("heavy", "light")

        for _ in range(9):
            mem.add("heavy")

        initial_weights = {n.label: n.weight for n in mem.graph.nodes}
        assert initial_weights["heavy"] > initial_weights["light"]

        r = mem.evolve()
        assert r.decayed == 0

        post_weights = {n.label: n.weight for n in mem.graph.nodes}
        assert post_weights["heavy"] < initial_weights["heavy"]
        assert post_weights["light"] < initial_weights["light"]
        assert post_weights["heavy"] > post_weights["light"]

        total_decayed = 0
        for _ in range(14):
            r = mem.evolve()
            total_decayed += r.decayed
        assert total_decayed == 1

        weights_after_decay = {n.label: n.weight for n in mem.graph.nodes}
        assert weights_after_decay["light"] < mem._decay_threshold

    def test_state_clustering_after_reasoning(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["r", "a", "b", "c"]:
            mem.add(label)
        mem.link("r", "a", label="rel")
        mem.link("r", "b", label="rel")
        mem.link("a", "c", label="rel")
        mem.link("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"r"}, max_depth=2, max_total_states=20)

        assert mem.state_clustering is not None
        report = mem.state_clustering.analyze()
        assert report["states_mapped"] == 3
        assert "clusters" in report
        assert "correlations" in report

    def test_persistence_preserves_graph_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            mem = HypergraphMemory(evolve_interval=0)
            mem.add("a")
            mem.add("b")
            mem.link("a", "b", label="connected", weight=5.0)
            mem.save(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.size[0] == 2
            assert mem2.size[1] == 1
            labels = {n.label for n in mem2.graph.nodes}
            assert labels == {"a", "b"}
            edge = list(mem2.graph.edges)[0]
            assert edge.label == "connected"
            assert edge.weight == 5.0
            assert mem2.log.size == 4

    def test_all_belief_profiles_work(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["cat", "dog", "bird"]:
            mem.add(label, tags={"semantic": 0.5, "recency": 1.0, "valence": 0.3})
        mem.create_distribution(["cat", "dog", "bird"])
        for profile_name in ["linguistic", "temporal", "emotional", "pragmatic"]:
            qs2 = mem.create_distribution(["cat", "dog", "bird"])
            result = mem.sample_with_profile(qs2, profile_name)
            assert result is not None
            assert result.label in {"cat", "dog", "bird"}

    def test_correlate_with_label_vs_id(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("cat")
        mem.add("dog")
        mem.add("pet")
        ent = mem.correlate(
            ["cat", "dog"],
            ["pet"],
            {("cat", "pet"): 0.9, ("dog", "pet"): 0.8},
        )
        assert ent.strength == pytest.approx(0.85, abs=0.01)

        cat_id = next(n.id for n in mem.graph.nodes if n.label == "cat")
        preds = ent.predict(cat_id, "furry")
        assert len(preds) == 1
        pet_id = next(n.id for n in mem.graph.nodes if n.label == "pet")
        assert preds[pet_id] == "furry"
