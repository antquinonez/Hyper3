import pytest
from hyper3 import (
    AnalysisPreset,
    MultiPerspectiveAnalyzer,
    PresetAnalysis,
    FrameTransformation,
    Hyperedge,
    Hypergraph,
    Hypernode,
)


def _build_graph():
    g = Hypergraph()
    for label in ["concept_a", "concept_b", "concept_c"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"concept_a"}), target_ids=frozenset({"concept_b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"concept_b"}), target_ids=frozenset({"concept_c"}), label="rel"))
    return g


class TestAnalysisPreset:
    def test_complexity_empty_metrics(self):
        f = AnalysisPreset(name="test")
        assert f.complexity() == 0.0

    def test_complexity_with_metrics(self):
        f = AnalysisPreset(name="test", metrics={"a": 0.5, "b": 0.3})
        assert abs(f.complexity() - 0.4) < 0.01


class TestMultiPerspectiveAnalyzer:
    def test_builtin_frames(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        assert "classical" in cr.frames
        assert "quantum" in cr.frames
        assert "hypergraph" in cr.frames
        assert "probabilistic" in cr.frames

    def test_add_custom_frame(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="custom", frame_type="neural", metrics={"training_convergence": 0.5})
        cr.add_frame(custom)
        assert cr.get_frame("custom") is not None

    def test_analyze_in_frame(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        analysis = cr.analyze_in_frame("concept_a", "classical")
        assert isinstance(analysis, PresetAnalysis)
        assert analysis.complexity >= 0.0
        assert analysis.solution_approach

    def test_multi_frame_analysis(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        results = cr.multi_frame_analysis("concept_a")
        assert len(results) == 4
        for name, analysis in results.items():
            assert isinstance(analysis, PresetAnalysis)
            assert analysis.frame_name == name

    def test_select_optimal_frame(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        name, analysis = cr.select_optimal_frame("concept_a")
        assert name in cr.frames
        assert isinstance(analysis, PresetAnalysis)

    def test_transform_between_frames(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        t = cr.transform_between_frames("concept_a", "classical", "quantum")
        assert isinstance(t, FrameTransformation)
        assert t.source_frame == "classical"
        assert t.target_frame == "quantum"
        assert t.transformation_cost >= 0.0

    def test_unknown_frame(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        analysis = cr.analyze_in_frame("concept_a", "nonexistent")
        assert analysis.complexity == float("inf")

    def test_concept_not_found(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        analysis = cr.analyze_in_frame("nonexistent", "classical")
        assert analysis.complexity == float("inf")

    def test_analyze(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        report = cr.analyze()
        assert "available_frames" in report
        assert "transformations_computed" in report
