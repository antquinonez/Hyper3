from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory, TransitiveRule
from hyper3.system_monitor import SystemMonitor
from hyper3.graph_diff import GraphDiffer


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


class TestSystemMonitorTuning:
    def test_execute_tuning_validated_rollback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._differ = GraphDiffer(mem.graph)
        mem._meta._differ.capture()
        mem._meta._state.architectural_fitness = 0.1
        from hyper3.system_monitor import TuningPlan
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
        from hyper3.system_monitor import TuningPlan
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

    def test_run_rule_discovery(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        result = mem._meta._run_rule_discovery()
        assert "discovered_patterns" in result

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
        e = mem.relate("a", "b", label="rel")
        node_a = mem.graph.get_node_by_label("a")
        node_a.access_count = 5
        result = mem._meta._optimize_weights()
        assert "reinforced" in result
        assert "smoothed" in result

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
            from hyper3.multiway_rulial import RulialSpace
            mem._meta._rulial = RulialSpace(mem.graph)
        else:
            mem._meta._rulial = mem._rulial
        result = mem._meta._promote_pattern_to_rule()
        assert result["promoted"] is False

    def test_restructure_graph_dimensions(self):
        mem = HypergraphMemory(evolve_interval=0)
        from hyper3.kernel import Metadata, Modality
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
        from hyper3.kernel import Metadata, Modality
        mem.store("a")
        node_a = mem.graph.get_node_by_label("a")
        node_a.metadata.modality_tags = {Modality.CONCEPTUAL}
        mem.store("b")
        node_b = mem.graph.get_node_by_label("b")
        node_b.metadata.modality_tags = {Modality.TEMPORAL}
        e1 = mem.relate("a", "b", label="rel", weight=10.0)
        e2 = mem.relate("b", "a", label="rel", weight=0.1)
        result = mem._meta._recalibrate_modality_weights()
        assert "modalities_found" in result
        assert "adjusted_edges" in result

    def test_auto_tune_low_fitness(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem._meta._state.architectural_fitness = 0.1
        result = mem._meta.auto_tune()
        assert result is not None

    def test_auto_tune_healthy(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem._meta._state.architectural_fitness = 0.95
        result = mem._meta.auto_tune()
        assert result.fitness_before >= 0.9
