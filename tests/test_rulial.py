import pytest
from hyper3 import (
    Hyperedge,
    Hypergraph,
    Hypernode,
    MetaComputationalPattern,
    Modality,
    RulialPosition,
    RulialSpace,
    HighLevelInsight,
    TransitiveRule,
    MultiwayEngine,
)


def _build_graph():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(
            id=label,
            label=label,
            metadata=__import__("hyper3").Metadata(modality_tags={Modality.CONCEPTUAL}),
        ))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    return g


class TestRulialPosition:
    def test_distance_to_self(self):
        p = RulialPosition(graph_activity_density=0.5, structural_complexity=0.3)
        assert p.distance_to(p) == 0.0

    def test_distance_to_different(self):
        p1 = RulialPosition(graph_activity_density=0.5, structural_complexity=0.3)
        p2 = RulialPosition(graph_activity_density=0.8, structural_complexity=0.6)
        assert p1.distance_to(p2) > 0.0


class TestRulialSpace:
    def test_update_position(self):
        g = _build_graph()
        rs = RulialSpace(g)
        pos = rs.update_position()
        assert isinstance(pos, RulialPosition)
        assert pos.graph_activity_density >= 0.0
        assert pos.structural_complexity >= 0.0

    def test_record_rule_application(self):
        g = _build_graph()
        rs = RulialSpace(g)
        rs.record_rule_application("transitive")
        rs.record_rule_application("transitive")
        rs.record_rule_application("inverse")
        assert rs.explored_rules["transitive"] == 2
        assert rs.explored_rules["inverse"] == 1

    def test_explore_rule_neighborhood(self):
        g = _build_graph()
        mw = MultiwayEngine(g)
        rs = RulialSpace(g, mw)
        rules = [TransitiveRule(edge_label="rel")]
        report = rs.explore_rule_neighborhood(rules)
        assert "explored_rules" in report
        assert "rule_diversity" in report
        assert "coverage" in report

    def test_find_meta_patterns(self):
        g = _build_graph()
        rs = RulialSpace(g)
        patterns = rs.find_meta_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) >= 1
        types = {p.pattern_type for p in patterns}
        assert "recurring_relation" in types

    def test_generate_high_level_insights(self):
        g = _build_graph()
        rs = RulialSpace(g)
        rs.record_rule_application("transitive")
        rs.record_rule_application("inverse")
        rs.record_rule_application("generalization")
        rs.update_position()
        rs.find_meta_patterns()
        insights = rs.generate_high_level_insights()
        assert isinstance(insights, list)
        assert len(insights) >= 1
        for insight in insights:
            assert isinstance(insight, HighLevelInsight)
            assert insight.principle
            assert insight.confidence >= 0.0

    def test_analyze(self):
        g = _build_graph()
        rs = RulialSpace(g)
        rs.update_position()
        report = rs.analyze()
        assert "graph_activity_density" in report
        assert "rule_diversity" in report
        assert "meta_patterns" in report

    def test_position_history(self):
        g = _build_graph()
        rs = RulialSpace(g)
        rs.update_position()
        rs.update_position()
        assert len(rs.position_history) == 2

    def test_with_multiway(self):
        g = _build_graph()
        mw = MultiwayEngine(g)
        rs = RulialSpace(g, mw)
        pos = rs.update_position()
        assert isinstance(pos.branchial_coordinates, list)
