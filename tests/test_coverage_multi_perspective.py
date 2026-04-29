from __future__ import annotations

import math

from hyper3.multi_perspective import (
    AnalysisPreset,
    MultiPerspectiveAnalyzer,
    PresetAnalysis,
)
from hyper3.kernel import Hypergraph, Hypernode, Hyperedge, Metadata, Modality


class TestCustomPresetAnalysis:
    def test_custom_frame_uses_custom_analysis(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="custom", frame_type="classical", metrics={"x": 0.5})
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "custom")
        assert result.frame_name == "custom"
        assert result.solution_approach == "exhaustive_analysis"
        assert "high_complexity" in result.weaknesses

    def test_custom_frame_high_complexity_adds_weakness(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        b = Hypernode(label="b")
        g.add_node(b)
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="connects",
        )
        g.add_edge(e)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="custom2", frame_type="classical", metrics={"x": 0.5})
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "custom2")
        assert result.frame_name == "custom2"
        assert "high_complexity" in result.weaknesses

    def test_custom_frame_low_complexity_adds_strength(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        for i in range(20):
            g.add_node(Hypernode(label=f"n{i}"))
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="custom_low", frame_type="classical")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "custom_low")
        assert "low_complexity" in result.strengths


class TestInformationPreserved:
    def test_no_shared_keys_returns_complexity_distance(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        t = cr.transform_between_frames("x", "classical", "quantum")
        assert 0.0 <= t.information_preserved <= 1.0

    def test_same_frame_high_preservation(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        t = cr.transform_between_frames("x", "classical", "classical")
        assert t.information_preserved == 1.0

    def test_shared_numeric_keys_agreement(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        t = cr.transform_between_frames("x", "classical", "hypergraph")
        assert t.information_preserved >= 0.0


class TestFrameStrengthsWeaknesses:
    def test_classical_strengths_populated(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "classical")
        assert "deterministic" in result.strengths
        assert "state_explosion" in result.weaknesses

    def test_classical_high_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        b = Hypernode(label="y")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="connects")
        g.add_edge(e)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "classical")
        assert "high_complexity" in result.weaknesses

    def test_quantum_multi_source_targets(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        b = Hypernode(label="y")
        g.add_node(a)
        g.add_node(b)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        e2 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="y")
        g.add_edge(e1)
        g.add_edge(e2)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "quantum")
        assert "multi_hypothesis" in result.strengths
        assert "multi_source_targets_detected" in result.strengths

    def test_hypergraph_multi_modal(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        b = Hypernode(label="y", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        c = Hypernode(label="z", metadata=Metadata(modality_tags={Modality.TEMPORAL}))
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        e2 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="x")
        g.add_edge(e1)
        g.add_edge(e2)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "hypergraph")
        assert "multi_arity" in result.strengths
        assert "multi_modal_structure" in result.strengths

    def test_probabilistic_sufficient_sample_size(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        for i in range(8):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
            e = Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({n.id}),
                label="x",
            )
            g.add_edge(e)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "probabilistic")
        assert "weighted_sampling" in result.strengths
        assert "sufficient_sample_size" in result.strengths


class TestComputeComplexityFrameTypes:
    def test_quantum_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        b = Hypernode(label="y")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_q", frame_type="quantum")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_q")
        assert result.complexity < float("inf")

    def test_hypergraph_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_hg", frame_type="hypergraph")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_hg")
        assert result.complexity < float("inf")

    def test_probabilistic_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_prob", frame_type="probabilistic")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_prob")
        assert result.complexity < float("inf")

    def test_unknown_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_unknown", frame_type="neural")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_unknown")
        assert result.complexity < float("inf")


class TestDeriveApproachLevels:
    def test_direct_lookup_approach(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        for i in range(5):
            n = Hypernode(label=f"n{i}")
            g.add_node(n)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_local", frame_type="classical")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_local")
        assert result.solution_approach in (
            "direct_lookup",
            "local_search",
            "structured_exploration",
            "exhaustive_analysis",
        )


class TestFramesProperty:
    def test_frames_returns_all_frames(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        frames = cr.frames
        assert "classical" in frames
        assert "quantum" in frames
        assert "hypergraph" in frames
        assert "probabilistic" in frames


class TestTransformationsProperty:
    def test_transformations_empty_initially(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        assert cr.transformations == []

    def test_transformations_populated_after_transform(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        cr.transform_between_frames("x", "classical", "quantum")
        assert len(cr.transformations) == 1


class TestAnalyzeUnknownFrame:
    def test_analyze_unknown_frame_name(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("x", "nonexistent_frame")
        assert result.frame_name == "nonexistent_frame"
        assert result.complexity == float("inf")
        assert result.solution_approach == "unknown_frame"


class TestNodeNotFound:
    def test_analyze_missing_node(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze_in_frame("missing", "classical")
        assert result.complexity == float("inf")
        assert result.solution_approach == "node_not_found"


class TestMultiPresetAnalysis:
    def test_multi_frame_analysis_returns_all(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        results = cr.multi_frame_analysis("x")
        assert "classical" in results
        assert "quantum" in results
        assert "hypergraph" in results
        assert "probabilistic" in results


class TestSelectOptimalFrame:
    def test_select_optimal_frame(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        name, analysis = cr.select_optimal_frame("x")
        assert name in cr.frames
        assert analysis.frame_name == name


class TestGetFrame:
    def test_get_existing_frame(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        f = cr.get_frame("classical")
        assert f is not None
        assert f.name == "classical"

    def test_get_missing_frame(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        assert cr.get_frame("nonexistent") is None


class TestAnalysisPresetComplexity:
    def test_empty_metrics_zero(self):
        f = AnalysisPreset(name="t")
        assert f.complexity() == 0.0

    def test_with_metrics(self):
        f = AnalysisPreset(name="t", metrics={"a": 1.0, "b": 3.0})
        assert f.complexity() == 2.0


class TestAnalyzeMethod:
    def test_analyze_returns_dict(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.analyze()
        assert "available_frames" in result
        assert "transformations_computed" in result
        assert isinstance(result["available_frames"], list)


class TestFindNodeAndCountNeighbors:
    def test_find_node_internal(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        assert cr._find_node("x") is not None
        assert cr._find_node("missing") is None

    def test_count_neighbors_internal(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        b = Hypernode(label="y")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e)
        cr = MultiPerspectiveAnalyzer(g)
        assert cr._count_neighbors(a.id) == 1
