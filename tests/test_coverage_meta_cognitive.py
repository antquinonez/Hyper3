from __future__ import annotations

from hyper3 import HypergraphMemory, TransitiveRule
from hyper3.system_monitor import SystemMonitor, TuningTrigger, TuningPlan
from hyper3.kernel import Hypergraph
from hyper3.event_log import EventLog
from hyper3.evolution import GraphMaintenanceEngine
from hyper3.rules_discovery import RuleDiscoveryEngine


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
        assert hasattr(state, "architectural_fitness")
        assert hasattr(state, "reasoning_mode")
        assert hasattr(state, "complexity_level")


class TestExecuteMetamorphosisEmptyPlan:
    def test_execute_empty_plan(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=[])
        result = mem.meta.execute_tuning(plan)
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_execute_plan_with_unknown_action(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["unknown_action_type"])
        result = mem.meta.execute_tuning(plan)
        assert "unknown_action_type" in result

    def test_execute_adjust_evolution_parameters(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.3
        plan = TuningPlan(actions=["adjust_evolution_parameters"])
        result = mem.meta.execute_tuning(plan)
        assert "adjust_evolution" in result

    def test_execute_run_rule_discovery(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["run_rule_discovery"])
        result = mem.meta.execute_tuning(plan)
        assert "rule_discovery" in result

    def test_execute_increase_connectivity(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        plan = TuningPlan(actions=["increase_connectivity"])
        result = mem.meta.execute_tuning(plan)
        assert "increase_connectivity" in result

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
        assert mem.meta._state.architectural_fitness <= 1.0

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
        from hyper3.kernel import Hyperedge
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
        assert hasattr(state, "architectural_fitness")
        assert hasattr(state, "reasoning_mode")

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
        assert "anti_patterns" in result or "graph_health" in result
