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
            mem.store(name, modalities={Modality.CONCEPTUAL})

        mem.relate("battery", "electricity", label="powers")
        mem.relate("electricity", "ignition", label="causes")
        mem.relate("ignition", "combustion", label="causes")
        mem.relate("fuel", "combustion", label="enables")
        mem.relate("combustion", "heat", label="causes")
        mem.relate("combustion", "rotation", label="causes")

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
                mem.store(name)
            mem.relate("x", "y", label="rel")
            mem.relate("y", "z", label="rel")
            mem.add_rules(TransitiveRule(edge_label="rel"))
            r1 = mem.reason({"x", "y", "z"}, max_depth=2)
            assert r1["expansion"]["rules_applied"] == 1
            mem.save(path)
            edges_after_session1 = mem.graph.edge_count
            assert edges_after_session1 == 3

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.graph.node_count == 3
            assert mem2.graph.edge_count == edges_after_session1
            assert mem2.log.size == 7

            mem2.store("w")
            mem2.relate("z", "w", label="rel")
            mem2.add_rules(TransitiveRule(edge_label="rel"))
            assert mem2.graph.edge_count == 4

    def test_belief_diagnostic_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for name in ["battery_weak", "battery_dead", "alternator_bad", "starter_bad"]:
            mem.store(name)

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
        mem.store("simple_concept")
        mem.store("self-referential structure")
        mem.store("all universal statements")

        regions = mem.map_boundaries(["simple_concept", "self-referential structure", "all universal statements"])
        assert len(regions) == 3
        statuses = {r.status for r in regions}
        assert statuses == {"low_risk"}

        result = mem.detect_structural_anomalies("simple_concept")
        assert result.anomaly_status == "low_risk"
        assert result.boundary_score == pytest.approx(0.05, abs=0.01)

    def test_multi_frame_analysis_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("engine", data={"type": "mechanical"})
        mem.relate("engine", "engine", label="self_ref")

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
        mem.belief.add_basis(custom)
        basis = mem.belief.get_basis("diagnostic")
        assert basis is not None
        assert basis.name == "diagnostic"

    def test_rulial_monitor_stats_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"concept_{i}")
        for i in range(9):
            mem.relate(f"concept_{i}", f"concept_{i+1}", label="chain")

        rulial = mem.rulial
        rulial.record_rule_application("transitive")
        rulial.record_rule_application("inverse")
        rulial.record_rule_application("generalization")
        pos = rulial.update_position()
        assert 0.0 < pos.graph_activity_density <= 1.0
        assert 0.0 < pos.structural_complexity <= 1.0

        patterns = rulial.find_meta_patterns()
        pattern_types = {p.pattern_type for p in patterns}
        assert "recurring_relation" in pattern_types
        assert "chain_motif" in pattern_types

        insights = rulial.generate_high_level_insights()
        principles = [ins.principle for ins in insights]
        assert any("Dominant relation" in p for p in principles)

        introspection = mem.introspect()
        assert 0.8 < introspection.system_health.fitness <= 1.0

    def test_rule_discovery_and_application_pipeline(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d", "e"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")
        mem.relate("d", "e", label="next")
        mem.relate("b", "a", label="prev")
        mem.relate("c", "b", label="prev")
        mem.relate("d", "c", label="prev")

        result = mem.auto_discover_and_apply()
        assert result["total_patterns"] == 4

        mem.add_rules(TransitiveRule(edge_label="next"))
        reason = mem.reason({"a", "b", "c"}, max_depth=2, max_total_states=20)
        assert reason["expansion"]["states_created"] == 11
        assert reason["expansion"]["rules_applied"] == 10

    def test_evolution_decay_and_prune(self):
        mem = HypergraphMemory(evolve_interval=0, decay_threshold=0.5)
        mem.store("heavy")
        mem.store("light")
        mem.relate("heavy", "light")

        for _ in range(9):
            mem.store("heavy")

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

    def test_branchial_space_after_reasoning(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["r", "a", "b", "c"]:
            mem.store(label)
        mem.relate("r", "a", label="rel")
        mem.relate("r", "b", label="rel")
        mem.relate("a", "c", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"r"}, max_depth=2, max_total_states=20)

        assert mem.branchial is not None
        report = mem.branchial.analyze()
        assert report["states_mapped"] == 3
        assert "clusters" in report
        assert "correlations" in report

    def test_persistence_preserves_graph_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            mem = HypergraphMemory(evolve_interval=0)
            mem.store("a")
            mem.store("b")
            mem.relate("a", "b", label="connected", weight=5.0)
            mem.save(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.graph.node_count == 2
            assert mem2.graph.edge_count == 1
            labels = {n.label for n in mem2.graph.nodes}
            assert labels == {"a", "b"}
            edge = list(mem2.graph.edges)[0]
            assert edge.label == "connected"
            assert edge.weight == 5.0
            assert mem2.log.size == 4

    def test_all_belief_profiles_work(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["cat", "dog", "bird"]:
            mem.store(label, tags={"semantic": 0.5, "recency": 1.0, "valence": 0.3})
        mem.create_distribution(["cat", "dog", "bird"])
        for profile_name in ["linguistic", "temporal", "emotional", "pragmatic"]:
            qs2 = mem.create_distribution(["cat", "dog", "bird"])
            result = mem.sample_with_profile(qs2, profile_name)
            assert result is not None
            assert result.label in {"cat", "dog", "bird"}

    def test_correlate_with_label_vs_id(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("pet")
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
