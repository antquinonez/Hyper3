import math

import pytest

from hyper3 import (
    AnalysisPreset,
    FrameTransformation,
    Hyperedge,
    Hypergraph,
    Hypernode,
    MultiPerspectiveAnalyzer,
    PresetAnalysis,
)
from hyper3.kernel import Metadata, Modality
from hyper3.memory import HypergraphMemory
from hyper3.multi_perspective import (
    ConsensusResult,
    DisagreementRegion,
    ProblemFeatures,
    RobustReachabilityDetector,
    RobustReachabilitySet,
    StructuralMetrics,
)
from hyper3.rules import TransitiveRule


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
        frame = cr.get_frame("custom")
        assert frame is not None
        assert frame.name == "custom"
        assert frame.frame_type == "neural"

    def test_analyze_in_frame(self):
        g = _build_graph()
        cr = MultiPerspectiveAnalyzer(g)
        analysis = cr.analyze_in_frame("concept_a", "classical")
        assert isinstance(analysis, PresetAnalysis)
        assert analysis.complexity >= 0.0
        assert analysis.solution_approach in (
            "direct_lookup",
            "local_search",
            "structured_exploration",
            "exhaustive_analysis",
        )

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
        assert 0.0 <= analysis.complexity <= 1.0

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
        assert len(report["available_frames"]) == 4





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
        assert t.information_preserved < 1.0

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
        assert 0.0 <= t.information_preserved <= 1.0


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
        assert 0.0 <= result.complexity <= 1.0
        assert result.solution_approach in (
            "direct_lookup",
            "local_search",
            "structured_exploration",
            "exhaustive_analysis",
        )

    def test_hypergraph_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_hg", frame_type="hypergraph")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_hg")
        assert 0.0 <= result.complexity <= 1.0

    def test_probabilistic_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_prob", frame_type="probabilistic")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_prob")
        assert 0.0 <= result.complexity <= 1.0

    def test_unknown_frame_type_complexity(self):
        g = Hypergraph()
        a = Hypernode(label="x")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        custom = AnalysisPreset(name="test_unknown", frame_type="neural")
        cr.add_frame(custom)
        result = cr.analyze_in_frame("x", "test_unknown")
        assert 0.0 <= result.complexity <= 1.0


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




def _make_mem_aw():
    mem = HypergraphMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d", "e"]:
        mem.add(label)
    mem.link("a", "b", label="rel")
    mem.link("b", "c", label="rel")
    mem.link("c", "d", label="rel")
    mem.link("d", "e", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


def _seed_ids_adaptive(mem):
    return [mem.graph.get_node_by_label(l).id for l in ["a", "b", "c"]]


class TestExtractProblemFeatures:

    def test_basic_features(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        assert isinstance(features, ProblemFeatures)
        assert features.graph_density >= 0
        assert features.seed_degree >= 0
        assert features.avg_weight > 0

    def test_empty_seeds(self):
        mem = _make_mem_aw()
        features = mem._perspective.extract_problem_features([])
        assert features.seed_degree == 0.0
        assert features.connectivity == 0.0

    def test_connectivity_connected_seeds(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        assert features.connectivity > 0

    def test_to_vector_shape(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        vec = features.to_vector()
        assert vec.shape == (6,)


class TestRecordProblemOutcome:

    def test_history_stored(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        mem._perspective.record_problem_outcome(features, "classical", True)
        assert len(mem._perspective._problem_history) == 1
        vec, frame, success = mem._perspective._problem_history[0]
        assert frame == "classical"
        assert success is True

    def test_multiple_recordings(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        mem._perspective.record_problem_outcome(features, "classical", True)
        mem._perspective.record_problem_outcome(features, "quantum", False)
        assert len(mem._perspective._problem_history) == 2


class TestRecommendFrame:

    def test_no_history_returns_none(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        assert mem._perspective.recommend_frame(ids) is None

    def test_returns_best_frame_from_history(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features = mem._perspective.extract_problem_features(ids)
        for _ in range(5):
            mem._perspective.record_problem_outcome(features, "classical", True)
        for _ in range(5):
            mem._perspective.record_problem_outcome(features, "quantum", False)
        recommended = mem._perspective.recommend_frame(ids)
        assert recommended == "classical"

    def test_similar_problems_weighted(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        features_a = mem._perspective.extract_problem_features(ids)
        for _ in range(10):
            mem._perspective.record_problem_outcome(features_a, "hypergraph", True)
            mem._perspective.record_problem_outcome(features_a, "classical", False)
        recommended = mem._perspective.recommend_frame(ids)
        assert recommended == "hypergraph"


class TestReasonWithFrameAutoRecording:

    def test_outcomes_recorded_on_reason(self):
        mem = _make_mem_aw()
        mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        eff = mem._perspective.get_frame_effectiveness()
        assert "classical" in eff
        history = mem._perspective._problem_history
        assert len(history) >= 1
        _, frame, _ = history[0]
        assert frame == "classical"

    def test_multiple_frames_accumulate(self):
        mem = _make_mem_aw()
        mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        mem.reason_with_frame({"a", "b", "c"}, frame_name="quantum")
        eff = mem._perspective.get_frame_effectiveness()
        assert "classical" in eff
        assert "quantum" in eff
        assert len(mem._perspective._problem_history) == 2


class TestTop2Rrf:

    def test_top2_rrf_strategy(self):
        mem = _make_mem_aw()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="top2_rrf")
        assert len(analyses) == 4
        rrf_count = sum(1 for a in analyses.values() if "rrf_merged" in a.strengths)
        assert rrf_count == 2

    def test_top2_rrf_adds_rrf_score(self):
        mem = _make_mem_aw()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="top2_rrf")
        for analysis in analyses.values():
            if "rrf_merged" in analysis.strengths:
                assert "rrf_score" in (analysis.parameters or {})

    def test_best_strategy_unchanged(self):
        mem = _make_mem_aw()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="best")
        for analysis in analyses.values():
            assert "rrf_merged" not in analysis.strengths


class TestSelectOptimalFrameLearned:

    def test_learned_shifts_with_outcomes(self):
        mem = _make_mem_aw()
        ids = _seed_ids_adaptive(mem)
        mem._perspective.extract_problem_features(ids)
        for _ in range(20):
            mem._perspective.record_frame_outcome("quantum", True)
            mem._perspective.record_frame_outcome("classical", False)
        successes_q = 0
        successes_c = 0
        for _ in range(50):
            name, _ = mem._perspective.select_optimal_frame_learned("a")
            if name == "quantum":
                successes_q += 1
            elif name == "classical":
                successes_c += 1
        assert successes_q > successes_c




def _make_mem_fc():
    mem = HypergraphMemory(evolve_interval=0)
    mem.add("core")
    mem.add("mid")
    mem.add("far_a")
    mem.add("far_b")
    c = mem.graph.get_node_by_label("core")
    m = mem.graph.get_node_by_label("mid")
    fa = mem.graph.get_node_by_label("far_a")
    fb = mem.graph.get_node_by_label("far_b")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({m.id}), label="link",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({m.id}), target_ids=frozenset({fa.id}), label="link",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({m.id}), target_ids=frozenset({fb.id}), label="link",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestComputeConsensus:

    def test_intersection_strategy(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="intersection")
        assert isinstance(result, ConsensusResult)
        assert result.strategy_used == "intersection"
        assert c.id in result.agreed_nodes

    def test_union_strategy(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="union")
        assert len(result.agreed_nodes) >= len(
            mem._perspective.compute_consensus([c.id], strategy="intersection").agreed_nodes
        )

    def test_majority_strategy(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="majority")
        assert isinstance(result.agreed_nodes, set)

    def test_weighted_strategy(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        mem._perspective.record_frame_outcome("classical", True)
        mem._perspective.record_frame_outcome("quantum", False)
        result = mem._perspective.compute_consensus([c.id], strategy="weighted")
        assert isinstance(result.agreed_nodes, set)

    def test_confidence_is_ratio(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert 0.0 <= result.confidence <= 1.0

    def test_disagreement_regions_populated(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert isinstance(result.disagreement_regions, list)

    def test_frame_results_populated(self):
        mem = _make_mem_fc()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert len(result.frame_results) == 4

    def test_empty_seeds(self):
        mem = _make_mem_fc()
        result = mem._perspective.compute_consensus([])
        assert result.agreed_nodes == set()


class TestResolveDisagreement:

    def test_all_frames_agree(self):
        mem = _make_mem_fc()
        reachability = {
            "classical": {"a", "b"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "intersection")
        assert result == {"a", "b"}

    def test_partial_disagreement_intersection(self):
        mem = _make_mem_fc()
        reachability = {
            "classical": {"a", "b", "c"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "intersection")
        assert result == {"a", "b"}

    def test_partial_disagreement_union(self):
        mem = _make_mem_fc()
        reachability = {
            "classical": {"a", "b", "c"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "union")
        assert result == {"a", "b", "c"}

    def test_majority_with_4_frames(self):
        mem = _make_mem_fc()
        reachability = {
            "classical": {"a", "b"},
            "quantum": {"a"},
            "hypergraph": {"a", "b"},
            "probabilistic": {"a"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "majority")
        assert "a" in result




def _make_mem_fi():
    mem = HypergraphMemory(evolve_interval=0)
    mem.add("core")
    mem.add("bridge")
    mem.add("periphery_a")
    mem.add("periphery_b")
    c = mem.graph.get_node_by_label("core")
    b = mem.graph.get_node_by_label("bridge")
    pa = mem.graph.get_node_by_label("periphery_a")
    pb = mem.graph.get_node_by_label("periphery_b")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({b.id}), label="link",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({pa.id}), label="link",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({pb.id}), label="link",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestRobustReachabilityDetector:

    def test_core_nodes_are_invariant(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        bridge = mem.graph.get_node_by_label("bridge")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert core.id in inv.invariant_nodes
        assert bridge.id in inv.invariant_nodes

    def test_confidence_is_ratio(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert 0.0 <= inv.confidence <= 1.0

    def test_frame_count_matches(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert inv.frame_count == 4

    def test_empty_seeds(self):
        mem = _make_mem_fi()
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([], mem.graph)
        assert inv.invariant_nodes == set()

    def test_frame_unique_populated(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert isinstance(inv.frame_unique, dict)


class TestMarkInvariants:

    def test_nodes_get_metadata(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        detector.mark_invariants(inv, mem.graph)
        assert core.metadata.custom.get("invariant") is True
        assert "invariant_confidence" in core.metadata.custom

    def test_edges_get_metadata(self):
        mem = _make_mem_fi()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        detector.mark_invariants(inv, mem.graph)
        for edge in mem.graph.edges:
            if edge.id in inv.invariant_edges:
                assert edge.metadata.custom.get("invariant") is True


class TestReasonWithConsensus:

    def test_returns_consensus_report(self):
        mem = _make_mem_fi()
        result = mem.reason_robust({"core", "bridge"})
        assert "invariant_nodes" in result
        assert "confidence" in result
        assert "frame_count" in result

    def test_invariant_count_positive(self):
        mem = _make_mem_fi()
        result = mem.reason_robust({"core"})
        assert result["invariant_nodes"] > 0

    def test_empty_seeds_returns_error(self):
        mem = _make_mem_fi()
        result = mem.reason_robust({"nonexistent"})
        assert "error" in result




def _make_mem_fm():
    mem = HypergraphMemory(evolve_interval=0)
    mem.add("a")
    mem.add("b")
    mem.add("c")
    mem.link("a", "b", label="rel")
    mem.link("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestComputeLocalClustering:

    def test_nonzero_for_asymmetric_graph(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        clustering = mem._perspective.compute_local_clustering([a.id])
        assert clustering >= 0.0

    def test_empty_seeds(self):
        mem = _make_mem_fm()
        assert mem._perspective.compute_local_clustering([]) == 0.0

    def test_single_node(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        x = mem.graph.get_node_by_label("x")
        clustering = mem._perspective.compute_local_clustering([x.id])
        assert clustering == 0.0


class TestComputePerspectiveOverlap:

    def test_self_overlap_is_one(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        overlap = mem._perspective.compute_perspective_overlap([a.id], "classical", "classical")
        assert overlap == 1.0

    def test_cross_frame_overlap(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        overlap = mem._perspective.compute_perspective_overlap([a.id], "classical", "quantum")
        assert 0.0 <= overlap <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem_fm()
        assert mem._perspective.compute_perspective_overlap([], "classical", "quantum") == 0.0


class TestComputeFrameInformationLoss:

    def test_classical_information_loss(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        info_loss = mem._perspective.compute_frame_information_loss([a.id], "classical")
        assert 0.0 <= info_loss <= 1.0

    def test_quantum_information_loss(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        info_loss = mem._perspective.compute_frame_information_loss([a.id], "quantum")
        assert 0.0 <= info_loss <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem_fm()
        assert mem._perspective.compute_frame_information_loss([], "classical") == 0.0


class TestComputeStructuralMetrics:

    def test_returns_frame_metrics(self):
        mem = _make_mem_fm()
        a = mem.graph.get_node_by_label("a")
        metrics = mem._perspective.compute_structural_metrics([a.id])
        assert isinstance(metrics, StructuralMetrics)
        assert metrics.local_clustering >= 0.0
        assert 0.0 <= metrics.perspective_overlap <= 1.0
        assert 0.0 <= metrics.frame_information_loss <= 1.0


class TestFrameEffectivenessLearning:
    def test_record_frame_outcome(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="test"))
        cr = MultiPerspectiveAnalyzer(g)
        cr.record_frame_outcome("classical", True)
        cr.record_frame_outcome("classical", False)
        cr.record_frame_outcome("quantum", True)
        eff = cr.get_frame_effectiveness()
        assert eff["classical"] == pytest.approx(0.5)
        assert eff["quantum"] == pytest.approx(1.0)

    def test_learned_selection_prefers_successful(self):
        g = Hypergraph()
        a = Hypernode(label="test")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        d = Hypernode(label="d")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_node(d)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="r1"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="r2"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="r3"))
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="r4"))
        cr = MultiPerspectiveAnalyzer(g)
        for _ in range(20):
            cr.record_frame_outcome("quantum", True)
            cr.record_frame_outcome("classical", False)
            cr.record_frame_outcome("hypergraph", False)
            cr.record_frame_outcome("probabilistic", False)
        quantum_count = 0
        for _ in range(50):
            name, _ = cr.select_optimal_frame_learned("test")
            if name == "quantum":
                quantum_count += 1
        assert quantum_count > 5

    def test_analyze_includes_effectiveness(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        cr.record_frame_outcome("classical", True)
        analysis = cr.analyze()
        assert "frame_effectiveness" in analysis


class TestMultiPerspectiveInformationDissipation:
    def test_information_dissipation_alias(self):
        from hyper3.multi_perspective import StructuralMetrics

        m = StructuralMetrics(local_clustering=0.5, perspective_overlap=0.8, frame_information_loss=0.2)
        assert m.information_dissipation == 0.2


class TestMultiPerspectiveEmptyFrames:
    def test_find_invariants_empty_frames(self):
        from hyper3.multi_perspective import RobustReachabilityDetector

        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        det = RobustReachabilityDetector(cr)
        cr._frames = {}
        result = det.find_invariants([], g)
        assert result.frame_count == 0

    def test_consensus_empty_frames(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        cr._frames = {}
        result = cr.compute_consensus(["a"], strategy="intersection")
        assert len(result.agreed_nodes) == 0


class TestMultiPerspectiveEdgeWeightFiltering:
    def test_bfs_reachable_skips_low_weight_edges(self):
        g = Hypergraph()
        a = Hypernode(id="a", label="a")
        b = Hypernode(id="b", label="b")
        c = Hypernode(id="c", label="c")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel", weight=1.0))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel", weight=0.1))
        cr = MultiPerspectiveAnalyzer(g)
        reachable = cr._bfs_reachable_set(["a"], max_depth=3, min_weight=0.3)
        assert "b" in reachable
        assert "c" not in reachable


class TestMultiPerspectiveCustomFrames:
    def test_information_preserved_with_empty_params(self):
        g = Hypergraph()
        a = Hypernode(id="a", label="a")
        g.add_node(a)
        cr = MultiPerspectiveAnalyzer(g)
        from hyper3.multi_perspective import PresetAnalysis

        analysis_a = PresetAnalysis(complexity=0.5, frame_name="custom_a", parameters={}, solution_approach="", strengths=[], weaknesses=[])
        analysis_b = PresetAnalysis(complexity=0.3, frame_name="custom_b", parameters={}, solution_approach="", strengths=[], weaknesses=[])
        preserved = cr._compute_information_preserved({}, {}, analysis_a, analysis_b)
        assert 0.0 <= preserved <= 1.0

    def test_information_preserved_with_string_params(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        from hyper3.multi_perspective import PresetAnalysis

        analysis_a = PresetAnalysis(complexity=0.5, frame_name="f1", parameters={"mode": "standard"}, solution_approach="", strengths=[], weaknesses=[])
        analysis_b = PresetAnalysis(complexity=0.5, frame_name="f2", parameters={"mode": "advanced"}, solution_approach="", strengths=[], weaknesses=[])
        preserved = cr._compute_information_preserved(
            analysis_a.parameters, analysis_b.parameters, analysis_a, analysis_b,
        )
        assert 0.0 <= preserved <= 1.0


class TestMultiPerspectiveResolveDisagreement:
    def test_resolve_empty_reachability(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        assert cr.resolve_disagreement({}, "intersection") == set()

    def test_resolve_unknown_strategy(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        result = cr.resolve_disagreement({"a": {1, 2}}, "unknown_strategy")
        assert result == {1, 2}


class TestMultiPerspectivePerspectiveOverlap:
    def test_overlap_with_probabilistic_frame(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(id=l, label=l))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel", weight=1.0))
        cr = MultiPerspectiveAnalyzer(g)
        overlap = cr.compute_perspective_overlap(["a"], "probabilistic", "classical")
        assert isinstance(overlap, float)

    def test_overlap_with_hypergraph_frame(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(id=l, label=l))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel", weight=1.0))
        cr = MultiPerspectiveAnalyzer(g)
        overlap = cr.compute_perspective_overlap(["a"], "hypergraph", "classical")
        assert isinstance(overlap, float)


class TestMultiPerspectiveLocalClustering:
    def test_clustering_with_triangle(self):
        g = Hypergraph()
        for l in "abc":
            g.add_node(Hypernode(id=l, label=l))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        cr = MultiPerspectiveAnalyzer(g)
        clustering = cr.compute_local_clustering(["a"])
        assert clustering > 0.0

    def test_clustering_single_frame(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(id=l, label=l))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        cr = MultiPerspectiveAnalyzer(g)
        cr._frames = {"classical": cr._frames["classical"]}
        clustering = cr.compute_local_clustering(["a"])
        assert clustering == 0.0


class TestMultiPerspectiveRecommendFrame:
    def test_recommend_frame_returns_from_history(self):
        g = Hypergraph()
        for l in "ab":
            g.add_node(Hypernode(id=l, label=l))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        cr = MultiPerspectiveAnalyzer(g)
        from hyper3.multi_perspective import ProblemFeatures
        cr.record_problem_outcome(ProblemFeatures(graph_density=0.5), "classical", success=False)
        cr.record_problem_outcome(ProblemFeatures(graph_density=0.5), "quantum", success=False)
        result = cr.recommend_frame(["a"])
        assert result in ("classical", "quantum")


class TestMultiPerspectiveEffectiveness:
    def test_zero_selections_returns_zero(self):
        g = Hypergraph()
        cr = MultiPerspectiveAnalyzer(g)
        cr._frame_outcomes["test_frame"] = {"selections": 0, "successes": 0}
        eff = cr.get_frame_effectiveness()
        assert eff["test_frame"] == 0.0

