import pytest
from hyper3 import (
    CognitiveMemory,
    CognitiveStateModel,
    Hyperedge,
    Hypergraph,
    Hypernode,
    MetaCognitiveLayer,
    MetamorphosisPlan,
    MetamorphosisTrigger,
    Modality,
    SelfEvolutionEngine,
    EventLog,
    RuleDiscoveryEngine,
)


class TestMetaCognitiveLayer:
    def _build_layer(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        return MetaCognitiveLayer(g, evo, log, disc), g

    def test_assess_state(self):
        layer, _ = self._build_layer()
        state = layer.assess_state()
        assert isinstance(state, CognitiveStateModel)
        assert 0.0 <= state.architectural_fitness <= 1.0

    def test_introspect(self):
        layer, _ = self._build_layer()
        result = layer.introspect()
        assert "cognitive_state" in result
        assert "graph_health" in result
        assert "evolution_health" in result
        assert "discovery_health" in result
        assert "avg_degree" in result["graph_health"]

    def test_introspect_with_anti_patterns(self):
        g = Hypergraph()
        for i in range(50):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        result = layer.introspect()
        has_anti = "anti_patterns" in result
        has_recommendations = "recommendations" in result
        assert has_anti or has_recommendations

    def test_check_metamorphosis_triggers(self):
        layer, _ = self._build_layer()
        triggers = layer.check_metamorphosis_triggers()
        assert isinstance(triggers, list)

    def test_propose_metamorphosis_no_triggers(self):
        layer, _ = self._build_layer()
        plan = layer.propose_metamorphosis([])
        assert plan is None

    def test_propose_metamorphosis_with_trigger(self):
        layer, _ = self._build_layer()
        trigger = MetamorphosisTrigger(
            trigger_type="performance_plateau",
            description="test",
            urgency=0.9,
        )
        plan = layer.propose_metamorphosis([trigger])
        assert isinstance(plan, MetamorphosisPlan)
        assert len(plan.actions) > 0

    def test_introspection_log(self):
        layer, _ = self._build_layer()
        layer.introspect()
        layer.introspect()
        assert len(layer.introspection_log) == 2

    def test_analyze(self):
        layer, _ = self._build_layer()
        report = layer.analyze()
        assert "architectural_fitness" in report
        assert "reasoning_mode" in report
        assert "meta_level" in report


class TestCognitiveMemoryNewFeatures:
    def test_branchial_space_after_reasoning(self):
        mem = CognitiveMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")
        mem.add_rules(__import__("hyper3").TransitiveRule(edge_label="next"))
        mem.reason({"a", "b", "c", "d"})
        assert mem.branchial is not None

    def test_rulial_property(self):
        mem = CognitiveMemory()
        assert mem.rulial is not None

    def test_transfinite_reasoning(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.relate("cat", "dog", label="chases")
        result = mem.detect_structural_anomalies("cat")
        assert result.decidability_status in {"decidable", "boundary_proximity", "undecidable"}

    def test_map_boundaries(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("self-referential paradox")
        regions = mem.map_boundaries(["cat", "self-referential paradox"])
        assert len(regions) == 2

    def test_multi_frame_analysis(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("concept")
        results = mem.multi_frame_analysis("concept")
        assert len(results) == 4

    def test_select_optimal_frame(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("concept")
        name, analysis = mem.select_optimal_frame("concept")
        assert name in {"classical", "quantum", "hypergraph", "probabilistic"}

    def test_introspect(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("alpha")
        mem.store("beta")
        mem.relate("alpha", "beta", label="connects")
        result = mem.introspect()
        assert "cognitive_state" in result
        assert "graph_health" in result

    def test_quantum_entanglement(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("pet")
        mem.store("wild")
        ent = mem.entangle(
            ["cat", "dog"],
            ["pet", "wild"],
            {("cat", "pet"): 0.9, ("dog", "wild"): 0.8},
        )
        assert ent.strength > 0

    def test_collapse_with_basis(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("bird")
        qs = mem.superpose(["cat", "dog", "bird"])
        result = mem.collapse_with_basis(qs, "linguistic")
        assert result is not None

    def test_collapse_triggers(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        qs = mem.superpose(["cat", "dog"])
        triggers = mem.detect_collapse_triggers(qs)
        assert isinstance(triggers, list)

    def test_interference(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        qs = mem.superpose(["cat", "dog"])
        patterns = mem.compute_interference(qs)
        assert isinstance(patterns, list)

    def test_stats_includes_rulial_and_meta(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("test")
        stats = mem.stats()
        assert hasattr(stats, "rulial")
        assert "meta_cognitive" in stats

    def test_transfinite_property(self):
        mem = CognitiveMemory()
        assert mem.structural_anomaly is not None

    def test_relativity_property(self):
        mem = CognitiveMemory()
        assert mem.perspective is not None

    def test_meta_property(self):
        mem = CognitiveMemory()
        assert mem.meta is not None
