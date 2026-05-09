from __future__ import annotations

import pytest

from hyper3.belief import BeliefLayer
from hyper3.interference_reasoning import (
    InterferenceInsight,
    InterferencePattern,
    InterferenceReasoningEngine,
    InterferenceReport,
)
from hyper3.kernel import Hypergraph, Hypernode


def _make_graph_with_nodes(n: int) -> tuple[Hypergraph, list[str]]:
    g = Hypergraph()
    ids = []
    for i in range(n):
        node = Hypernode(label=f"n{i}")
        g.add_node(node)
        ids.append(node.id)
    return g, ids


def _make_engine() -> tuple[Hypergraph, BeliefLayer, InterferenceReasoningEngine]:
    g = Hypergraph()
    bl = BeliefLayer(g)
    engine = InterferenceReasoningEngine(g, bl)
    return g, bl, engine


class TestInterferenceReasoningEngineConstruction:
    def test_construction(self):
        g, bl, engine = _make_engine()
        assert engine.report().total_patterns == 0

    def test_to_dict_empty(self):
        _, _, engine = _make_engine()
        d = engine.to_dict()
        assert d["scan_count"] == 0
        assert d["pattern_history"] == {}


class TestCrossInterference:
    def test_empty_state_ids(self):
        _, _, engine = _make_engine()
        assert engine.compute_cross_interference([]) == []

    def test_single_state(self):
        g, bl, engine = _make_engine()
        node = Hypernode(label="a")
        g.add_node(node)
        qs = bl.create_distribution([node.id])
        assert engine.compute_cross_interference([qs.id]) == []

    def test_two_states_no_shared_nodes(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        qs1 = bl.create_distribution([n1.id])
        qs2 = bl.create_distribution([n2.id])
        result = engine.compute_cross_interference([qs1.id, qs2.id])
        assert result == []

    def test_two_states_shared_node_constructive(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        qs2 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        result = engine.compute_cross_interference([qs1.id, qs2.id])
        shared_patterns = [p for p in result if p.node_id == shared.id]
        assert len(shared_patterns) == 1
        assert shared_patterns[0].is_constructive

    def test_two_states_shared_node_destructive(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.9, 0.1])
        qs2 = bl.create_distribution([shared.id, unique.id], [-0.8, 0.2])
        result = engine.compute_cross_interference([qs1.id, qs2.id])
        shared_patterns = [p for p in result if p.node_id == shared.id]
        assert len(shared_patterns) == 1
        assert shared_patterns[0].is_constructive or shared_patterns[0].is_destructive

    def test_three_states_shared_node(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        other = Hypernode(label="other")
        g.add_node(shared)
        g.add_node(other)
        qs1 = bl.create_distribution([shared.id], [0.7])
        qs2 = bl.create_distribution([shared.id, other.id], [0.5, 0.5])
        qs3 = bl.create_distribution([shared.id, other.id], [0.6, 0.4])
        result = engine.compute_cross_interference([qs1.id, qs2.id, qs3.id])
        shared_patterns = [p for p in result if p.node_id == shared.id]
        assert len(shared_patterns) == 1
        assert len(shared_patterns[0].contributing_states) == 3

    def test_resolved_state_excluded(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id])
        qs2 = bl.create_distribution([shared.id, unique.id])
        qs1.resolved = True
        qs1.resolved_to = qs1.outcomes[0].node_id
        result = engine.compute_cross_interference([qs1.id, qs2.id])
        assert result == []


class TestContradictionDetection:
    def test_no_contradictions(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        qs2 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        result = engine.detect_contradictions([qs1.id, qs2.id])
        contradiction_types = [i for i in result if i.insight_type == "contradiction"]
        assert len(contradiction_types) == 0

    def test_contradiction_above_threshold(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.9, 0.1])
        qs2 = bl.create_distribution([shared.id, unique.id], [-0.8, 0.2])
        result = engine.detect_contradictions([qs1.id, qs2.id], threshold=0.3)
        assert len(result) >= 1
        assert result[0].insight_type == "contradiction"
        assert result[0].suggested_action == "flag_contradiction"

    def test_contradiction_below_threshold(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.6, 0.4])
        qs2 = bl.create_distribution([shared.id, unique.id], [-0.4, 0.6])
        result = engine.detect_contradictions([qs1.id, qs2.id], threshold=0.99)
        assert len(result) == 0


class TestReinforcementDetection:
    def test_reinforcement_above_threshold(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        qs2 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        result = engine.detect_reinforcements([qs1.id, qs2.id], threshold=0.3)
        assert len(result) >= 1
        assert result[0].insight_type == "reinforcement"
        assert result[0].suggested_action == "reinforce_edge"

    def test_cross_reinforcement_three_states(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        other = Hypernode(label="other")
        g.add_node(shared)
        g.add_node(other)
        qs1 = bl.create_distribution([shared.id], [0.7])
        qs2 = bl.create_distribution([shared.id, other.id], [0.6, 0.4])
        qs3 = bl.create_distribution([shared.id, other.id], [0.6, 0.4])
        result = engine.detect_reinforcements(
            [qs1.id, qs2.id, qs3.id], threshold=0.3
        )
        cross = [
            i for i in result if i.insight_type == "cross_reinforcement"
        ]
        assert len(cross) >= 1
        assert cross[0].suggested_action == "merge_nodes"


class TestGenerateInsights:
    def test_combined_output(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        qs2 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
        result = engine.generate_insights([qs1.id, qs2.id])
        assert len(result) >= 1
        types = {i.insight_type for i in result}
        assert "reinforcement" in types


class TestHistoryAndReport:
    def test_patterns_accumulate(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id])
        qs2 = bl.create_distribution([shared.id, unique.id])
        engine.compute_cross_interference([qs1.id, qs2.id])
        engine.compute_cross_interference([qs1.id, qs2.id])
        r = engine.report()
        assert r.total_patterns >= 2
        assert engine._scan_count == 2

    def test_report_empty(self):
        _, _, engine = _make_engine()
        r = engine.report()
        assert r.total_patterns == 0
        assert r.strongest_constructive is None
        assert r.strongest_destructive is None
        assert r.contradiction_nodes == []
        assert r.reinforcement_nodes == []

    def test_persistent_contradiction_nodes(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        for _ in range(4):
            qs1 = bl.create_distribution([shared.id, unique.id], [0.9, 0.1])
            qs2 = bl.create_distribution([shared.id, unique.id], [-0.8, 0.2])
            engine.compute_cross_interference([qs1.id, qs2.id])
        r = engine.report()
        assert shared.id in r.contradiction_nodes

    def test_persistent_reinforcement_nodes(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        for _ in range(4):
            qs1 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
            qs2 = bl.create_distribution([shared.id, unique.id], [0.7, 0.3])
            engine.compute_cross_interference([qs1.id, qs2.id])
        r = engine.report()
        assert shared.id in r.reinforcement_nodes


class TestSerialization:
    def test_round_trip(self):
        g, bl, engine = _make_engine()
        shared = Hypernode(label="shared")
        unique = Hypernode(label="unique")
        g.add_node(shared)
        g.add_node(unique)
        qs1 = bl.create_distribution([shared.id, unique.id])
        qs2 = bl.create_distribution([shared.id, unique.id])
        engine.compute_cross_interference([qs1.id, qs2.id])

        data = engine.to_dict()
        restored = InterferenceReasoningEngine.from_dict(data, g, bl)
        assert restored._scan_count == engine._scan_count
        assert len(restored._pattern_history) == len(engine._pattern_history)

    def test_round_trip_empty(self):
        g, bl, engine = _make_engine()
        data = engine.to_dict()
        restored = InterferenceReasoningEngine.from_dict(data, g, bl)
        assert restored.report().total_patterns == 0


class TestDictLikeAccess:
    def test_pattern_bracket_access(self):
        p = InterferencePattern(node_id="abc", constructive=0.5)
        assert p["node_id"] == "abc"
        assert p["constructive"] == 0.5

    def test_insight_bracket_access(self):
        i = InterferenceInsight(insight_type="contradiction", confidence=0.8)
        assert i["insight_type"] == "contradiction"

    def test_report_bracket_access(self):
        r = InterferenceReport(total_patterns=5, constructive_count=3)
        assert r["total_patterns"] == 5
        assert "constructive_count" in r
