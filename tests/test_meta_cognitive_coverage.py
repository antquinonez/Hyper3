import pytest
from hyper3 import (
    CognitiveMemory,
    CognitiveStateModel,
    EventLog,
    Hyperedge,
    Hypergraph,
    Hypernode,
    MetaCognitiveLayer,
    MetamorphosisPlan,
    MetamorphosisTrigger,
    Modality,
    RuleDiscoveryEngine,
    SelfEvolutionEngine,
    TransitiveRule,
    InverseRule,
)


def _build_layer_with_reasoning():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    evo = SelfEvolutionEngine(g)
    log = EventLog()
    disc = RuleDiscoveryEngine(g)
    layer = MetaCognitiveLayer(g, evo, log, disc)
    log.record("reason", seeds=["a", "b"])
    log.record("reason", seeds=["c", "d"])
    return layer, g


class TestMetaCognitiveDeep:
    def test_assess_state_detects_reasoning(self):
        layer, _ = _build_layer_with_reasoning()
        state = layer.assess_state()
        assert state.boundary_navigation_success > 0.0

    def test_assess_state_with_rulial(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        from hyper3.rulial import RulialSpace
        rulial = RulialSpace(g)
        for name in ["t1", "t2", "t3", "t4", "t5"]:
            rulial.record_rule_application(name)
        rulial.find_meta_patterns()
        rulial.generate_transcendental_insights()
        layer.attach_rulial(rulial)
        state = layer.assess_state()
        assert state.transcendental_yield > 0

    def test_introspect_with_recommendations(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        result = layer.introspect()
        assert "recommendations" in result

    def test_metamorphosis_performance_plateau(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        layer._state.architectural_fitness = 0.3
        triggers = layer.check_metamorphosis_triggers()
        plateau = [t for t in triggers if t.trigger_type == "performance_plateau"]
        assert len(plateau) >= 1

    def test_metamorphosis_meta_insight(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        from hyper3.rulial import RulialSpace
        rulial = RulialSpace(g)
        rulial._meta_patterns.append(
            __import__("hyper3").MetaComputationalPattern(
                pattern_type="recurring_relation",
                description="test",
                occurrence_count=6,
            )
        )
        layer.attach_rulial(rulial)
        triggers = layer.check_metamorphosis_triggers()
        meta = [t for t in triggers if t.trigger_type == "meta_insight"]
        assert len(meta) >= 1

    def test_metamorphosis_all_trigger_types(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        layer._state.architectural_fitness = 0.3
        from hyper3.rulial import RulialSpace
        rulial = RulialSpace(g)
        rulial._meta_patterns.append(
            __import__("hyper3").MetaComputationalPattern(
                pattern_type="recurring_relation",
                description="test",
                occurrence_count=6,
            )
        )
        layer.attach_rulial(rulial)
        for _ in range(5):
            layer._introspection_log.append({"summary": {"anti_patterns": ["test"]}})
        triggers = layer.check_metamorphosis_triggers()
        types = {t.trigger_type for t in triggers}
        assert "performance_plateau" in types
        assert "meta_insight" in types
        assert "cross_domain" in types

    def test_propose_metamorphosis_plan_actions(self):
        layer, _ = _build_layer_with_reasoning()
        triggers = [
            MetamorphosisTrigger(trigger_type="performance_plateau", description="test", urgency=0.9),
            MetamorphosisTrigger(trigger_type="novel_problem", description="test", urgency=0.6),
            MetamorphosisTrigger(trigger_type="meta_insight", description="test", urgency=0.7),
            MetamorphosisTrigger(trigger_type="cross_domain", description="test", urgency=0.8),
        ]
        plan = layer.propose_metamorphosis(triggers)
        assert isinstance(plan, MetamorphosisPlan)
        assert len(plan.actions) >= 4
        assert plan.expected_improvement > 0.0
        assert plan.risk_level > 0.0

    def test_assess_state_rich_mode(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        evo = SelfEvolutionEngine(g)
        log = EventLog()
        disc = RuleDiscoveryEngine(g)
        layer = MetaCognitiveLayer(g, evo, log, disc)
        from hyper3.discovery import DiscoveredRule
        discovered_with_rules = []
        for i in range(5):
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
