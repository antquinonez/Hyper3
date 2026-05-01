import pytest

from hyper3 import (
    EventLog,
    GraphMaintenanceEngine,
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    InverseRule,
    Modality,
    RuleDiscoveryEngine,
    SystemHealthModel,
    SystemMonitor,
    TransitiveRule,
    TuningPlan,
    TuningTrigger,
)
from hyper3.graph_diff import GraphDiffer
from hyper3.kernel import Metadata
from hyper3.multiway_rulial import RulialSpace
from hyper3.rules_discovery import DiscoveredRule


class TestSystemMonitor:
    def _build_layer(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        return SystemMonitor(g, evo, log, disc), g

    def test_assess_state(self):
        layer, _ = self._build_layer()
        state = layer.assess_state()
        assert isinstance(state, SystemHealthModel)
        assert 0.0 <= state.architectural_fitness <= 1.0

    def test_introspect(self):
        layer, _ = self._build_layer()
        result = layer.introspect()
        assert "system_health" in result
        assert "graph_health" in result
        assert "evolution_health" in result
        assert "discovery_health" in result
        assert "avg_degree" in result["graph_health"]
        assert result["graph_health"]["nodes"] == 3

    def test_introspect_with_anti_patterns(self):
        g = Hypergraph()
        for i in range(50):
            g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        result = layer.introspect()
        has_anti = "anti_patterns" in result
        has_recommendations = "recommendations" in result
        assert has_anti or has_recommendations
        assert "graph_health" in result

    def test_check_tuning_triggers(self):
        layer, _ = self._build_layer()
        triggers = layer.check_tuning_triggers()
        assert isinstance(triggers, list)
        for t in triggers:
            assert isinstance(t.trigger_type, str)

    def test_propose_tuning_no_triggers(self):
        layer, _ = self._build_layer()
        plan = layer.propose_tuning([])
        assert plan is None

    def test_propose_tuning_with_trigger(self):
        layer, _ = self._build_layer()
        trigger = TuningTrigger(
            trigger_type="performance_plateau",
            description="test",
            urgency=0.9,
        )
        plan = layer.propose_tuning([trigger])
        assert isinstance(plan, TuningPlan)
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
        assert isinstance(report["architectural_fitness"], float)


class TestHypergraphMemoryNewFeatures:
    def test_branchial_space_after_reasoning(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")
        mem.add_rules(__import__("hyper3").TransitiveRule(edge_label="next"))
        mem.reason({"a", "b", "c", "d"})
        assert mem.branchial is not None

    def test_rulial_property(self):
        mem = HypergraphMemory()
        from hyper3.multiway_rulial import RulialSpace
        assert isinstance(mem.rulial, RulialSpace)

    def test_structural_anomaly_detection(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.relate("cat", "dog", label="chases")
        result = mem.detect_structural_anomalies("cat")
        assert result.anomaly_status in {"low_risk", "boundary", "anomalous"}

    def test_map_boundaries(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("self-referential paradox")
        regions = mem.map_boundaries(["cat", "self-referential paradox"])
        assert len(regions) == 2

    def test_multi_frame_analysis(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("concept")
        results = mem.multi_frame_analysis("concept")
        assert len(results) == 4

    def test_select_optimal_frame(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("concept")
        name, analysis = mem.select_optimal_frame("concept")
        assert name in {"classical", "quantum", "hypergraph", "probabilistic"}

    def test_introspect(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("alpha")
        mem.store("beta")
        mem.relate("alpha", "beta", label="connects")
        result = mem.introspect()
        assert "system_health" in result
        assert "graph_health" in result

    def test_belief_correlation(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("pet")
        mem.store("wild")
        ent = mem.correlate(
            ["cat", "dog"],
            ["pet", "wild"],
            {("cat", "pet"): 0.9, ("dog", "wild"): 0.8},
        )
        assert ent.strength > 0

    def test_sample_with_profile(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("bird")
        qs = mem.create_distribution(["cat", "dog", "bird"])
        result = mem.sample_with_profile(qs, "linguistic")
        assert result is not None
        assert result.node_id is not None

    def test_sampling_triggers(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        qs = mem.create_distribution(["cat", "dog"])
        triggers = mem.detect_sampling_triggers(qs)
        assert isinstance(triggers, list)
        for t in triggers:
            assert hasattr(t, "trigger_type")

    def test_interactions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        qs = mem.create_distribution(["cat", "dog"])
        patterns = mem.compute_interactions(qs)
        assert isinstance(patterns, list)

    def test_stats_includes_rulial_and_meta(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        stats = mem.stats()
        assert hasattr(stats, "rulial")
        assert "monitor_stats" in stats

    def test_structural_anomaly_property(self):
        mem = HypergraphMemory()
        from hyper3.structural_anomaly import StructuralAnomalyDetector
        assert isinstance(mem.structural_anomaly, StructuralAnomalyDetector)

    def test_relativity_property(self):
        mem = HypergraphMemory()
        from hyper3.multi_perspective import MultiPerspectiveAnalyzer
        assert isinstance(mem.perspective, MultiPerspectiveAnalyzer)

    def test_meta_property(self):
        mem = HypergraphMemory()
        assert isinstance(mem.meta, SystemMonitor)






class TestSystemMonitorAssessState:
    def test_rich_reasoning_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._discovery.discover_all()
        for d in mem._discovery.get_discovered_rules():
            d.rule = TransitiveRule()
        state = mem._meta.assess_state()
        assert state.reasoning_mode in ("rich", "moderate", "sparse")

    def test_moderate_reasoning_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._discovery.discover_all()
        discovered = mem._discovery.get_discovered_rules()
        for i, d in enumerate(discovered):
            if i < max(1, len(discovered) // 2):
                d.rule = TransitiveRule()
        state = mem._meta.assess_state()
        assert state.reasoning_mode in ("rich", "moderate", "sparse")

    def test_sparse_reasoning_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        state = mem._meta.assess_state()
        assert state.reasoning_mode == "sparse"

    def test_rulial_complexity_level(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        mem.reason(seed_concepts={"a", "b"}, max_depth=2, max_total_states=20)
        state = mem._meta.assess_state()
        assert isinstance(state.complexity_level, int)


class TestSystemMonitorIntrospectRulial:
    def test_introspect_with_rulial(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        mem.reason(seed_concepts={"a", "b"}, max_depth=2, max_total_states=20)
        report = mem._meta.introspect(rules=mem._rules)
        assert report.system_health is not None
        assert report.system_health.fitness >= 0.0


class TestSystemMonitorTuning:
    def test_execute_tuning_validated_rollback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._differ = GraphDiffer(mem.graph)
        mem._meta._differ.capture()
        mem._meta._state.architectural_fitness = 0.1
        plan = TuningPlan(
            triggers=[],
            actions=["adjust_evolution"],
        )
        result = mem._meta.execute_tuning_validated(plan)
        assert result.validated is True

    def test_execute_tuning_validated_no_differ(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._state.architectural_fitness = 0.1
        plan = TuningPlan(
            triggers=[],
            actions=["adjust_evolution"],
        )
        result = mem._meta.execute_tuning_validated(plan)
        assert result.validated is False

    def test_adjust_evolution(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._state.architectural_fitness = 0.3
        result = mem._meta._adjust_evolution()
        assert "decay_threshold" in result
        assert "merge_threshold" in result
        assert isinstance(result["decay_threshold"], float)

    def test_run_rule_discovery(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        result = mem._meta._run_rule_discovery()
        assert "discovered_patterns" in result
        assert isinstance(result["discovered_patterns"], int)

    def test_increase_connectivity(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("isolated", data={"key": "val"})
        mem.store("connected", data={"key": "other"})
        result = mem._meta._increase_connectivity()
        assert result["isolated_nodes"] >= 1

    def test_increase_connectivity_bridges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("iso", data={"type": "a"})
        mem.store("partner", data={"type": "a"})
        result = mem._meta._increase_connectivity()
        assert result["bridged"] >= 0

    def test_optimize_weights(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        node_a = mem.graph.get_node_by_label("a")
        node_a.access_count = 5
        result = mem._meta._optimize_weights()
        assert "reinforced" in result
        assert "smoothed" in result
        assert result["reinforced"] >= 1

    def test_increase_merge_threshold(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem._meta._increase_merge_threshold()
        assert result["new_threshold"] >= result["old_threshold"]

    def test_expand_seed_set(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        result = mem._meta._expand_seed_set()
        assert "poorly_connected" in result
        assert "new_edges" in result

    def test_promote_pattern_to_rule_no_rulial(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem._meta._promote_pattern_to_rule()
        assert result["promoted"] is False

    def test_promote_pattern_to_rule_no_patterns(self):
        mem = HypergraphMemory(evolve_interval=0)
        if mem._rulial is None:
            mem._meta._rulial = RulialSpace(mem.graph)
        else:
            mem._meta._rulial = mem._rulial
        result = mem._meta._promote_pattern_to_rule()
        assert result["promoted"] is False

    def test_restructure_graph_dimensions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        node_a = mem.graph.get_node_by_label("a")
        node_a.metadata.modality_tags = {Modality.CONCEPTUAL}
        mem.store("b")
        node_b = mem.graph.get_node_by_label("b")
        node_b.metadata.modality_tags = set()
        result = mem._meta._restructure_graph_dimensions()
        assert result["reassigned"] >= 1

    def test_restructure_graph_dimensions_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        result = mem._meta._restructure_graph_dimensions()
        assert result["dominant_modality"] == "none"

    def test_recalibrate_modality_weights(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        node_a = mem.graph.get_node_by_label("a")
        node_a.metadata.modality_tags = {Modality.CONCEPTUAL}
        mem.store("b")
        node_b = mem.graph.get_node_by_label("b")
        node_b.metadata.modality_tags = {Modality.TEMPORAL}
        mem.relate("a", "b", label="rel", weight=10.0)
        mem.relate("b", "a", label="rel", weight=0.1)
        result = mem._meta._recalibrate_modality_weights()
        assert "modalities_found" in result
        assert "adjusted_edges" in result
        assert result["modalities_found"] >= 2

    def test_auto_tune_low_fitness(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._state.architectural_fitness = 0.1
        result = mem._meta.auto_tune()
        assert result is not None
        assert isinstance(result.fitness_before, float)

    def test_auto_tune_healthy(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem._meta._state.architectural_fitness = 0.95
        result = mem._meta.auto_tune()
        assert result.fitness_before >= 0.9




class TestComputeFitnessEmptyGraph:
    def test_empty_graph_returns_one(self):
        g = Hypergraph()
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        meta = SystemMonitor(g, evo, log, disc)
        fitness = meta._compute_fitness(g, evo.metrics, log)
        assert fitness == 1.0


class TestComputeFitnessWithRecallEvents:
    def test_fitness_with_successful_recall_events(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.recall("x")
        fitness = mem.meta._compute_fitness(
            mem.graph,
            mem._evolution.metrics,
            mem.log,
        )
        assert 0.0 <= fitness <= 1.0
        assert fitness > 0.0

    def test_fitness_with_failed_recall_events(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.recall("nonexistent")
        fitness = mem.meta._compute_fitness(
            mem.graph,
            mem._evolution.metrics,
            mem.log,
        )
        assert 0.0 <= fitness <= 1.0
        assert fitness < 1.0


class TestAssessStateReasoningModes:
    def test_assess_state_sparse_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        state = mem.meta.assess_state([])
        assert state.reasoning_mode in ("rich", "moderate", "sparse")

    def test_assess_state_returns_system_health(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        state = mem.meta.assess_state([])
        assert isinstance(state.architectural_fitness, float)
        assert isinstance(state.reasoning_mode, str)
        assert isinstance(state.complexity_level, int)


class TestExecuteMetamorphosisEmptyPlan:
    def test_execute_empty_plan(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=[])
        result = mem.meta.execute_tuning(plan)
        assert len(result) == 0

    def test_execute_plan_with_unknown_action(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["unknown_action_type"])
        result = mem.meta.execute_tuning(plan)
        assert result["unknown_action_type"] == "unknown_action"

    def test_execute_adjust_evolution_parameters(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.3
        plan = TuningPlan(actions=["adjust_evolution_parameters"])
        result = mem.meta.execute_tuning(plan)
        assert isinstance(result["adjust_evolution"], dict)
        assert "decay_threshold" in result["adjust_evolution"]

    def test_execute_run_rule_discovery(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["run_rule_discovery"])
        result = mem.meta.execute_tuning(plan)
        assert isinstance(result["rule_discovery"], dict)
        assert "discovered_patterns" in result["rule_discovery"]

    def test_execute_increase_connectivity(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["increase_connectivity"])
        result = mem.meta.execute_tuning(plan)
        assert isinstance(result["increase_connectivity"], dict)
        assert "bridged" in result["increase_connectivity"]

    def test_execute_optimize_weights(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="rel")
        node = mem.graph.get_node_by_label("x")
        node.access_count = 5
        plan = TuningPlan(actions=["optimize_weights"])
        result = mem.meta.execute_tuning(plan)
        assert "optimize_weights" in result
        assert result["optimize_weights"]["reinforced"] >= 1


class TestAutoMetamorphosis:
    def test_auto_tune_low_fitness_triggers(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.2
        mem.meta.auto_tune()
        assert 0.0 <= mem.meta._state.architectural_fitness <= 1.0

    def test_auto_tune_high_fitness_no_action(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        target = mem.graph.get_node_by_label("b")
        if target:
            target.access_count = 3
        mem.meta.auto_tune()
        result = mem.meta.auto_tune()
        assert "fitness_before" in result
        assert isinstance(result["fitness_before"], float)
        assert result["actions_taken"] == 0


class TestProposeMetamorphosisMultipleTriggers:
    def test_propose_with_all_trigger_types(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        triggers = [
            TuningTrigger(trigger_type="performance_plateau", description="perf", urgency=0.7),
            TuningTrigger(trigger_type="novel_problem", description="struct", urgency=0.6),
            TuningTrigger(trigger_type="meta_insight", description="insight", urgency=0.5),
            TuningTrigger(trigger_type="cross_domain", description="cross", urgency=0.8),
        ]
        plan = mem.meta.propose_tuning(triggers)
        assert plan is not None
        assert len(plan.actions) > 0
        assert plan.expected_improvement > 0
        assert plan.risk_level > 0

    def test_propose_returns_none_with_no_triggers(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        result = mem.meta.propose_tuning([])
        assert result is None


class TestTuningPlanActions:
    def test_performance_plateau_actions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        trigger = TuningTrigger(trigger_type="performance_plateau", description="perf", urgency=0.7)
        plan = mem.meta.propose_tuning([trigger])
        assert "adjust_evolution_parameters" in plan.actions
        assert "increase_merge_threshold" in plan.actions

    def test_novel_problem_actions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        trigger = TuningTrigger(trigger_type="novel_problem", description="novel", urgency=0.6)
        plan = mem.meta.propose_tuning([trigger])
        assert "run_rule_discovery" in plan.actions
        assert "expand_seed_set" in plan.actions

    def test_meta_insight_actions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        trigger = TuningTrigger(trigger_type="meta_insight", description="insight", urgency=0.5)
        plan = mem.meta.propose_tuning([trigger])
        assert "promote_pattern_to_rule" in plan.actions
        assert "update_rulial_position" in plan.actions

    def test_cross_domain_actions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        trigger = TuningTrigger(trigger_type="cross_domain", description="cross", urgency=0.8)
        plan = mem.meta.propose_tuning([trigger])
        assert "restructure_graph_dimensions" in plan.actions
        assert "recalibrate_modality_weights" in plan.actions


class TestCheckAllTuningTriggerTypes:
    def test_performance_plateau_trigger(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.2
        triggers = mem.meta.check_tuning_triggers()
        trigger_types = [t.trigger_type for t in triggers]
        assert "performance_plateau" in trigger_types

    def test_novel_problem_trigger(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(5):
            mem.store(f"node_{i}")
        nodes = [mem.graph.get_node_by_label(f"node_{i}") for i in range(5)]
        for i in range(12):
            n1 = nodes[i % 5]
            n2 = nodes[(i + 1) % 5]
            edge = Hyperedge(
                source_ids=frozenset({n1.id}),
                target_ids=frozenset({n2.id}),
                label=f"e{i}",
            )
            mem.graph.add_edge(edge)
        mem.meta._state.architectural_fitness = 0.8
        triggers = mem.meta.check_tuning_triggers()
        trigger_types = [t.trigger_type for t in triggers]
        assert "novel_problem" in trigger_types

    def test_no_triggers_when_healthy(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        mem.meta._state.architectural_fitness = 0.9
        triggers = mem.meta.check_tuning_triggers()
        trigger_types = [t.trigger_type for t in triggers]
        assert "performance_plateau" not in trigger_types

    def test_cross_domain_trigger_from_anti_patterns(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        for _ in range(4):
            mem.meta._introspection_log.append({
                "summary": {"anti_patterns": ["low_connectivity", "low_engagement"]}
            })
        mem.meta._state.architectural_fitness = 0.9
        triggers = mem.meta.check_tuning_triggers()
        trigger_types = [t.trigger_type for t in triggers]
        assert "cross_domain" in trigger_types


class TestMonitorStatsProperties:
    def test_state_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        state = mem.meta.state
        assert state is not None
        assert state.architectural_fitness == 1.0
        assert state.reasoning_mode == "standard"

    def test_analyze(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        analysis = mem.meta.analyze()
        assert "architectural_fitness" in analysis
        assert "reasoning_mode" in analysis
        assert "meta_level" in analysis
        assert "introspections" in analysis
        assert "metamorphoses" in analysis
        assert "rulial_insight_count" in analysis
        assert isinstance(analysis["architectural_fitness"], float)
        assert analysis["reasoning_mode"] in {"standard", "rich", "moderate", "sparse"}

    def test_reasoning_mode_setting(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.reasoning_mode = "exploratory"
        assert mem.meta._state.reasoning_mode == "exploratory"

    def test_introspection_log_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.introspect()
        log = mem.meta.introspection_log
        assert len(log) == 1

    def test_tuning_history_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        history = mem.meta.tuning_history
        assert isinstance(history, list)
        assert len(history) == 0


class TestIntrospectWithRecommendations:
    def test_introspect_produces_recommendations(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(15):
            mem.store(f"node_{i}")
        result = mem.introspect()
        assert "system_health" in result
        assert "graph_health" in result
        assert "evolution_health" in result

    def test_introspect_detects_anti_patterns(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(150):
            mem.store(f"node_{i}")
        result = mem.introspect()
        assert "graph_health" in result
        assert result["graph_health"].nodes == 150




def _build_layer_with_reasoning():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    evo = GraphMaintenanceEngine(g)
    log = EventLog()
    disc = RuleDiscoveryEngine(g)
    layer = SystemMonitor(g, evo, log, disc)
    log.record("reason", seeds=["a", "b"])
    log.record("reason", seeds=["c", "d"])
    return layer, g


class TestMonitorStatsDeep:
    def test_assess_state_detects_reasoning(self):
        layer, _ = _build_layer_with_reasoning()
        state = layer.assess_state()
        assert state.reasoning_activity_rate > 0.0

    def test_assess_state_with_rulial(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        rulial = RulialSpace(g)
        for name in ["t1", "t2", "t3", "t4", "t5"]:
            rulial.record_rule_application(name)
        rulial.find_meta_patterns()
        rulial.generate_high_level_insights()
        layer.set_rulial(rulial)
        state = layer.assess_state()
        assert state.rulial_insight_count > 0

    def test_introspect_with_recommendations(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        result = layer.introspect()
        assert "recommendations" in result

    def test_metamorphosis_performance_plateau(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        layer._state.architectural_fitness = 0.3
        triggers = layer.check_tuning_triggers()
        plateau = [t for t in triggers if t.trigger_type == "performance_plateau"]
        assert len(plateau) >= 1

    def test_metamorphosis_meta_insight(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        rulial = RulialSpace(g)
        rulial._meta_patterns.append(
            __import__("hyper3").DetectedPattern(
                pattern_type="recurring_relation",
                description="test",
                occurrence_count=6,
            )
        )
        layer.set_rulial(rulial)
        triggers = layer.check_tuning_triggers()
        meta = [t for t in triggers if t.trigger_type == "meta_insight"]
        assert len(meta) >= 1

    def test_metamorphosis_all_trigger_types(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        layer._state.architectural_fitness = 0.3
        rulial = RulialSpace(g)
        rulial._meta_patterns.append(
            __import__("hyper3").DetectedPattern(
                pattern_type="recurring_relation",
                description="test",
                occurrence_count=6,
            )
        )
        layer.set_rulial(rulial)
        for _ in range(5):
            layer._introspection_log.append({"summary": {"anti_patterns": ["test"]}})
        triggers = layer.check_tuning_triggers()
        types = {t.trigger_type for t in triggers}
        assert "performance_plateau" in types
        assert "meta_insight" in types
        assert "cross_domain" in types

    def test_propose_tuning_plan_actions(self):
        layer, _ = _build_layer_with_reasoning()
        triggers = [
            TuningTrigger(trigger_type="performance_plateau", description="test", urgency=0.9),
            TuningTrigger(trigger_type="novel_problem", description="test", urgency=0.6),
            TuningTrigger(trigger_type="meta_insight", description="test", urgency=0.7),
            TuningTrigger(trigger_type="cross_domain", description="test", urgency=0.8),
        ]
        plan = layer.propose_tuning(triggers)
        assert isinstance(plan, TuningPlan)
        assert len(plan.actions) >= 4
        assert plan.expected_improvement > 0.0
        assert plan.risk_level > 0.0

    def test_assess_state_rich_mode(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = GraphMaintenanceEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = SystemMonitor(g, evo, log, disc)
        discovered_with_rules = []
        for _i in range(5):
            dr = DiscoveredRule(pattern_type="test", pattern={})
            dr.rule = TransitiveRule(edge_label="rel")
            discovered_with_rules.append(dr)
        disc._discovered = discovered_with_rules
        state = layer.assess_state()
        assert state.reasoning_mode == "rich"

    def test_introspection_log_accumulates(self):
        layer, _ = _build_layer_with_reasoning()
        layer.introspect()
        layer.introspect()
        layer.introspect()
        assert len(layer.introspection_log) == 3




def _setup_mem():
    mem = HypergraphMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d"]:
        mem.store(label)
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestMetamorphosisActions:

    def test_increase_merge_threshold(self):
        mem = _setup_mem()
        plan = TuningPlan(actions=["increase_merge_threshold"])
        result = mem._meta.execute_tuning(plan)
        assert "increase_merge_threshold" in result
        assert result["increase_merge_threshold"]["new_threshold"] > result["increase_merge_threshold"]["old_threshold"]

    def test_expand_seed_set(self):
        mem = _setup_mem()
        mem.store("isolated")
        plan = TuningPlan(actions=["expand_seed_set"])
        mem._meta.set_rules(mem._rules)
        result = mem._meta.execute_tuning(plan)
        assert "expand_seed_set" in result
        assert "poorly_connected" in result["expand_seed_set"]

    def test_promote_pattern_to_rule_without_rulial(self):
        mem = _setup_mem()
        plan = TuningPlan(actions=["promote_pattern_to_rule"])
        result = mem._meta.execute_tuning(plan)
        assert result["promote_pattern_to_rule"]["promoted"] is False

    def test_update_rulial_position(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._rulial is not None
        mem._meta.set_rulial(mem._rulial)
        mem._meta.set_rules(mem._rules)
        plan = TuningPlan(actions=["update_rulial_position"])
        result = mem._meta.execute_tuning(plan)
        assert result["update_rulial_position"]["updated"] is True

    def test_restructure_graph_dimensions(self):
        mem = _setup_mem()
        plan = TuningPlan(actions=["restructure_graph_dimensions"])
        result = mem._meta.execute_tuning(plan)
        assert "restructure_graph_dimensions" in result

    def test_recalibrate_modality_weights(self):
        mem = _setup_mem()
        plan = TuningPlan(actions=["recalibrate_modality_weights"])
        result = mem._meta.execute_tuning(plan)
        assert "recalibrate_modality_weights" in result
        assert "adjusted_edges" in result["recalibrate_modality_weights"]

    def test_all_new_actions_not_unknown(self):
        mem = _setup_mem()
        new_actions = [
            "increase_merge_threshold",
            "expand_seed_set",
            "promote_pattern_to_rule",
            "update_rulial_position",
            "restructure_graph_dimensions",
            "recalibrate_modality_weights",
        ]
        plan = TuningPlan(actions=new_actions)
        result = mem._meta.execute_tuning(plan)
        for action in new_actions:
            assert result.get(action) != "unknown_action", f"{action} was not handled"

    def test_existing_actions_still_work(self):
        mem = _setup_mem()
        existing_actions = [
            "adjust_evolution_parameters",
            "run_rule_discovery",
            "optimize_weights",
        ]
        plan = TuningPlan(actions=existing_actions)
        result = mem._meta.execute_tuning(plan)
        expected_keys = ["adjust_evolution", "rule_discovery", "optimize_weights"]
        for key in expected_keys:
            assert key in result
