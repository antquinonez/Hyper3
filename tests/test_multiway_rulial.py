import tempfile
from pathlib import Path

import pytest

from hyper3 import (
    DetectedPattern,
    HighLevelInsight,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Modality,
    MultiwayEngine,
    RulialPosition,
    RulialSpace,
    TransitiveRule,
)
from hyper3.memory import HypergraphMemory
from hyper3.rules import AbductiveRule


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
        assert 0.0 <= pos.graph_activity_density <= 1.0
        assert 0.0 <= pos.structural_complexity <= 1.0

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
        assert isinstance(report["explored_rules"], list)
        assert report["rule_diversity"] >= 0.0

    def test_find_meta_patterns(self):
        g = _build_graph()
        rs = RulialSpace(g)
        patterns = rs.find_meta_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) >= 1
        types = {p.pattern_type for p in patterns}
        assert "recurring_relation" in types
        for p in patterns:
            assert p.significance >= 0.0
            assert p.occurrence_count >= 1

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
            assert len(insight.principle) > 0
            assert 0.0 <= insight.confidence <= 1.0

    def test_analyze(self):
        g = _build_graph()
        rs = RulialSpace(g)
        rs.update_position()
        report = rs.analyze()
        assert "graph_activity_density" in report
        assert "rule_diversity" in report
        assert "meta_patterns" in report
        assert isinstance(report["graph_activity_density"], float)
        assert isinstance(report["rule_diversity"], (int, float))

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




def _setup_chain():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.store("d")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem.relate("c", "d", label="rel")
    return mem


class TestRuleEffectivenessTracking:

    def test_effectiveness_recorded_after_reasoning(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._rulial is not None
        eff = mem._rulial.get_rule_effectiveness()
        assert len(eff) > 0
        for rule_name, stats in eff.items():
            assert stats["applications"] > 0
            assert isinstance(rule_name, str)

    def test_useful_recorded_for_surviving_edges(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        has_useful = False
        for outcomes in mem._rulial._rule_outcomes.values():
            if outcomes.get("useful", 0) > 0:
                has_useful = True
        assert has_useful

    def test_get_recommended_rules(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        recommended = mem._rulial.get_recommended_rules()
        assert len(recommended) >= 1
        for name in recommended:
            assert isinstance(name, str)

    def test_get_rule_priority(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        for name in mem._rulial._rule_outcomes:
            priority = mem._rulial.get_rule_priority(name)
            assert 0.0 <= priority <= 1.0

    def test_unknown_rule_has_default_priority(self):
        mem = _setup_chain()
        mem._ensure_multiway()
        priority = mem._rulial.get_rule_priority("NonExistentRule")
        assert priority == 0.5

    def test_rules_sorted_by_effectiveness_during_expansion(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._multiway_engine is not None
        assert mem._multiway_engine._rulial is not None
        eff = mem._multiway_engine._rulial.get_rule_effectiveness()
        assert len(eff) > 0

    def test_effectiveness_preserved_in_snapshot(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)

        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "test.json")
            mem.save_state(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            for node in mem._graph.nodes:
                mem2._graph.add_node(node)
            for edge in mem._graph.edges:
                mem2._graph.add_edge(edge)
            mem2._rules = [TransitiveRule()]
            mem2.load_state(path)

            assert mem2._rulial is not None
            eff = mem2._rulial.get_rule_effectiveness()
            assert len(eff) > 0
            original_eff = mem._rulial.get_rule_effectiveness()
            assert set(eff.keys()) == set(original_eff.keys())

    def test_multiple_rules_tracked(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule(), AbductiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._rulial is not None
        recommended = mem._rulial.get_recommended_rules()
        assert len(recommended) >= 1
        eff = mem._rulial.get_rule_effectiveness()
        assert len(eff) >= 1




def _build_graph_with_multiway():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    mw = MultiwayEngine(g)
    return g, mw


class TestComputeDensityMap:
    def test_returns_resolution_x_resolution_grid(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        grid = rs.compute_density_map(resolution=5)
        assert len(grid) == 5
        assert all(len(row) == 5 for row in grid)

    def test_empty_history_returns_zero_grid(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        grid = rs.compute_density_map()
        assert len(grid) == 10
        assert all(v == 0.0 for row in grid for v in row)

    def test_with_history_returns_nonzero(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.record_rule_application("inverse")
        rs.update_position()
        grid = rs.compute_density_map()
        assert any(v > 0.0 for row in grid for v in row)

    def test_normalized_max_one(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.update_position()
        grid = rs.compute_density_map()
        if any(v > 0.0 for row in grid for v in row):
            assert max(max(row) for row in grid) == pytest.approx(1.0)


class TestIdentifyFrontiers:
    def test_frontiers_respect_bounds(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.update_position()
        frontiers = rs.identify_frontiers(min_density=0.1, max_density=0.9)
        grid = rs.compute_density_map()
        for r, c in frontiers:
            val = grid[int(r)][int(c)]
            assert 0.1 <= val <= 0.9

    def test_no_frontiers_on_empty(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        frontiers = rs.identify_frontiers()
        assert frontiers == []


class TestPerRuleEffectivenessTracking:
    def test_record_outcomes(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_outcome("transitive(A)", "applied")
        rs.record_rule_outcome("transitive(A)", "useful")
        rs.record_rule_outcome("transitive(A)", "reinforced")
        rs.record_rule_outcome("inverse(X)", "applied")
        rs.record_rule_outcome("inverse(X)", "pruned")
        outcomes = rs.rule_outcomes
        assert outcomes["transitive(A)"]["applications"] == 2
        assert outcomes["transitive(A)"]["useful"] == 1
        assert outcomes["transitive(A)"]["reinforced"] == 1
        assert outcomes["inverse(X)"]["pruned"] == 1

    def test_effectiveness_scores(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        for _ in range(5):
            rs.record_rule_outcome("good_rule", "useful")
        for _ in range(5):
            rs.record_rule_outcome("bad_rule", "applied")
        eff = rs.get_rule_effectiveness()
        assert eff["good_rule"]["effectiveness"] == pytest.approx(1.0)
        assert eff["bad_rule"]["effectiveness"] == pytest.approx(0.0)

    def test_best_rules(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        for _ in range(3):
            rs.record_rule_outcome("rule_a", "useful")
        for _ in range(3):
            rs.record_rule_outcome("rule_b", "applied")
        best = rs.get_best_rules(top_k=2)
        assert best[0][0] == "rule_a"
        assert best[0][1] > best[1][1]

    def test_record_rule_application_tracks_outcome(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_application("transitive(X)")
        outcomes = rs.rule_outcomes
        assert "transitive(X)" in outcomes
        assert outcomes["transitive(X)"]["applications"] == 1

    def test_analyze_includes_effectiveness(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        rs.record_rule_outcome("test_rule", "useful")
        analysis = rs.analyze()
        assert "rule_effectiveness" in analysis
        assert "test_rule" in analysis["rule_effectiveness"]

