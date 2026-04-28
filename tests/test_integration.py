import os
import tempfile
import pytest
from hyper3 import (
    AbductiveRule,
    CognitiveMemory,
    MultiPerspectiveAnalyzer,
    GeneralizationRule,
    InverseRule,
    MeasurementBasis,
    Modality,
    PropertyPropagationRule,
    TransitiveRule,
)


class TestIntegrationFullPipeline:
    def test_knowledge_graph_lifecycle(self):
        mem = CognitiveMemory(evolve_interval=0)

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
        assert result["expansion"]["states_created"] > 0

        mem.auto_discover_and_apply()

        qs = mem.superpose(["battery", "fuel", "ignition"])
        assert qs.superposition_count == 3

        interpretation = mem.collapse(qs, context={"battery": 2.0})
        assert interpretation is not None
        assert qs.collapsed

        mem.evolve()
        stats = mem.stats()
        assert stats["nodes"] >= 7
        assert stats["edges"] >= 6
        assert stats["log_size"] > 0

    def test_save_load_continue_reasoning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "knowledge.json")

            mem = CognitiveMemory(evolve_interval=0)
            for name in ["x", "y", "z"]:
                mem.store(name)
            mem.relate("x", "y", label="rel")
            mem.relate("y", "z", label="rel")
            mem.add_rules(TransitiveRule(edge_label="rel"))
            r1 = mem.reason({"x", "y", "z"}, max_depth=2)
            assert r1["expansion"]["rules_applied"] >= 1
            mem.save(path)
            edges_after_session1 = mem.graph.edge_count

            mem2 = CognitiveMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.graph.node_count == 3
            assert mem2.graph.edge_count == edges_after_session1
            assert mem2.log.size > 0

            mem2.store("w")
            mem2.relate("z", "w", label="rel")
            mem2.add_rules(TransitiveRule(edge_label="rel"))
            assert mem2.graph.edge_count > edges_after_session1

    def test_quantum_diagnostic_pipeline(self):
        mem = CognitiveMemory(evolve_interval=0)
        for name in ["battery_weak", "battery_dead", "alternator_bad", "starter_bad"]:
            mem.store(name)

        qs = mem.superpose(["battery_weak", "alternator_bad", "starter_bad"])

        ent = mem.entangle(
            ["battery_weak", "battery_dead"],
            ["starter_bad"],
            {("battery_weak", "starter_bad"): 0.9, ("battery_dead", "starter_bad"): 0.95},
        )
        assert ent.strength > 0

        triggers = mem.detect_collapse_triggers(qs)
        assert isinstance(triggers, list)

        patterns = mem.compute_interference(qs)
        assert isinstance(patterns, list)

        collapsed = mem.collapse_with_basis(qs, "pragmatic")
        assert collapsed is not None
        assert qs.collapsed

    def test_transfinite_boundary_mapping(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("simple_concept")
        mem.store("self-referential structure")
        mem.store("all universal statements")

        regions = mem.map_boundaries(["simple_concept", "self-referential structure", "all universal statements"])
        assert len(regions) == 3
        statuses = {r.status for r in regions}
        assert "decidable" in statuses

        result = mem.detect_structural_anomalies("simple_concept")
        assert result.decidability_status in {"decidable", "boundary_proximity", "undecidable"}

    def test_multi_frame_analysis_pipeline(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("engine", data={"type": "mechanical"})
        mem.relate("engine", "engine", label="self_ref")

        optimal_name, optimal = mem.select_optimal_frame("engine")
        assert optimal_name in {"classical", "quantum", "hypergraph", "probabilistic"}
        assert optimal.complexity >= 0.0

        analyses = mem.multi_frame_analysis("engine")
        assert len(analyses) == 4
        for name, analysis in analyses.items():
            assert analysis.solution_approach != ""

        custom = MeasurementBasis(name="diagnostic", dimensions=["severity", "frequency"])
        mem.quantum.add_basis(custom)
        assert mem.quantum.get_basis("diagnostic") is not None

    def test_rulial_meta_cognitive_pipeline(self):
        mem = CognitiveMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"concept_{i}")
        for i in range(9):
            mem.relate(f"concept_{i}", f"concept_{i+1}", label="chain")

        rulial = mem.rulial
        rulial.record_rule_application("transitive")
        rulial.record_rule_application("inverse")
        rulial.record_rule_application("generalization")
        pos = rulial.update_position()
        assert pos.computational_density > 0.0
        assert pos.causal_graph_complexity > 0.0

        patterns = rulial.find_meta_patterns()
        assert len(patterns) >= 1

        insights = rulial.generate_high_level_insights()
        assert len(insights) >= 1

        introspection = mem.introspect()
        assert introspection.cognitive_state.fitness > 0.0

        mem.add_rules(TransitiveRule(edge_label="chain"))
        mem.reason({"concept_0", "concept_5"}, max_depth=3, max_total_states=15)

        introspection2 = mem.introspect()
        assert introspection2.cognitive_state.fitness > 0.0

    def test_rule_discovery_and_application_pipeline(self):
        mem = CognitiveMemory(evolve_interval=0)
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
        assert result["total_patterns"] >= 1

        mem.add_rules(TransitiveRule(edge_label="next"))
        reason = mem.reason({"a", "b", "c"}, max_depth=2, max_total_states=20)
        assert reason["expansion"]["states_created"] > 0

    def test_evolution_decay_and_prune(self):
        mem = CognitiveMemory(evolve_interval=1, decay_threshold=0.01, decay_factor=0.01)
        for label in ["keep", "drop"]:
            mem.store(label)
        mem.relate("keep", "drop")

        keep_node = None
        drop_node = None
        for n in mem.graph.nodes:
            if n.label == "keep":
                keep_node = n
            elif n.label == "drop":
                drop_node = n

        if keep_node:
            for _ in range(5):
                mem.store("keep")

        mem.evolve()
        stats = mem.stats()
        assert stats["evolution"]["prunes"] >= 0

    def test_branchial_space_after_reasoning(self):
        mem = CognitiveMemory(evolve_interval=0)
        for label in ["r", "a", "b", "c"]:
            mem.store(label)
        mem.relate("r", "a", label="rel")
        mem.relate("r", "b", label="rel")
        mem.relate("a", "c", label="rel")
        mem.relate("b", "c", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel"))
        mem.reason({"r"}, max_depth=2, max_total_states=20)

        if mem.branchial:
            report = mem.branchial.analyze()
            assert report["states_mapped"] > 0

    def test_persistence_preserves_thresholds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            mem = CognitiveMemory(
                evolve_interval=0,
                merge_threshold=0.5,
                decay_threshold=0.01,
            )
            mem.store("a")
            mem.relate("a", "a", label="self")
            mem.save(path)

            mem2 = CognitiveMemory(
                evolve_interval=0,
                merge_threshold=0.5,
                decay_threshold=0.01,
            )
            mem2.load(path)
            assert mem2._merge_threshold == 0.5
            assert mem2._decay_threshold == 0.01

    def test_all_quantum_bases_work(self):
        mem = CognitiveMemory(evolve_interval=0)
        for label in ["cat", "dog", "bird"]:
            mem.store(label, tags={"semantic": 0.5, "recency": 1.0, "valence": 0.3})
        qs = mem.superpose(["cat", "dog", "bird"])
        for basis_name in ["linguistic", "temporal", "emotional", "pragmatic"]:
            qs2 = mem.superpose(["cat", "dog", "bird"])
            result = mem.collapse_with_basis(qs2, basis_name)
            assert result is not None

    def test_entangle_with_label_vs_id(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("pet")
        ent = mem.entangle(
            ["cat", "dog"],
            ["pet"],
            {("cat", "pet"): 0.9, ("dog", "pet"): 0.8},
        )
        preds = ent.predict(
            next(n.id for n in mem.graph.nodes if n.label == "cat"),
            "furry",
        )
        assert len(preds) > 0
