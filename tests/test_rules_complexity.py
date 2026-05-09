from __future__ import annotations

import pytest

from hyper3.kernel import Hypergraph, Hypernode
from hyper3.multi_perspective import MultiPerspectiveAnalyzer, PresetAnalysis
from hyper3.rules import RuleMatch
from hyper3.rules_complexity import ComplexityComparisonRule


class FakePerspective:
    def __init__(self, results: dict[str, dict[str, PresetAnalysis]] | None = None):
        self._results = results or {}

    def multi_frame_analysis(self, concept: str) -> dict[str, PresetAnalysis]:
        return self._results.get(concept, {
            "classical": PresetAnalysis(frame_name="classical", complexity=0.5, solution_approach="test"),
            "quantum": PresetAnalysis(frame_name="quantum", complexity=0.3, solution_approach="test"),
        })


def _make_rule(perspective=None) -> tuple[Hypergraph, ComplexityComparisonRule]:
    g = Hypergraph()
    p = perspective or FakePerspective()
    r = ComplexityComparisonRule(p)
    return g, r


class TestConstruction:
    def test_name(self):
        _, r = _make_rule()
        assert r.name == "complexity_comparison"

    def test_custom_frames(self):
        p = FakePerspective()
        r = ComplexityComparisonRule(p, frames=["a", "b"])
        assert r._frames == ["a", "b"]


class TestFindMatches:
    def test_no_active_nodes(self):
        g, r = _make_rule()
        assert r.find_matches(g, frozenset()) == []

    def test_node_without_data(self):
        g, r = _make_rule()
        n = Hypernode(label="x")
        g.add_node(n)
        matches = r.find_matches(g, frozenset({n.id}))
        assert len(matches) == 1
        assert matches[0].bindings["concept"] == n.id

    def test_node_with_existing_data(self):
        g, r = _make_rule()
        n = Hypernode(label="x", data={"complexity_comparison": {"frames": {}}})
        g.add_node(n)
        matches = r.find_matches(g, frozenset({n.id}))
        assert matches == []


class TestApply:
    def test_stores_complexity_data(self):
        g, r = _make_rule()
        n = Hypernode(label="x")
        g.add_node(n)
        match = RuleMatch(
            rule_name="complexity_comparison",
            bindings={"concept": n.id},
            context={"label": "x"},
        )
        new_nodes, new_edges = r.apply(g, match)
        assert new_nodes == []
        assert new_edges == []
        assert "complexity_comparison" in n.data
        assert "frames" in n.data["complexity_comparison"]
        assert "optimal" in n.data["complexity_comparison"]

    def test_optimal_frame_is_lowest(self):
        g, r = _make_rule()
        n = Hypernode(label="x")
        g.add_node(n)
        match = RuleMatch(
            rule_name="complexity_comparison",
            bindings={"concept": n.id},
            context={"label": "x"},
        )
        r.apply(g, match)
        frames = n.data["complexity_comparison"]["frames"]
        optimal = n.data["complexity_comparison"]["optimal"]
        assert optimal == min(frames, key=frames.get)

    def test_node_not_found(self):
        g, r = _make_rule()
        match = RuleMatch(
            rule_name="complexity_comparison",
            bindings={"concept": "nonexistent"},
            context={"label": "y"},
        )
        assert r.apply(g, match) == ([], [])

    def test_perspective_exception(self):
        class ErrorPerspective:
            def multi_frame_analysis(self, concept):
                raise ValueError("boom")

        g, r = _make_rule(ErrorPerspective())
        n = Hypernode(label="x", data={})
        g.add_node(n)
        match = RuleMatch(
            rule_name="complexity_comparison",
            bindings={"concept": n.id},
            context={"label": "x"},
        )
        assert r.apply(g, match) == ([], [])
        assert "complexity_comparison" not in n.data
