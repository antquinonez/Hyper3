from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.multi_perspective import ProblemFeatures


def _make_mem():
    mem = CognitiveMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d", "e"]:
        mem.store(label)
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem.relate("c", "d", label="rel")
    mem.relate("d", "e", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


def _seed_ids(mem):
    return [mem.graph.get_node_by_label(l).id for l in ["a", "b", "c"]]


class TestExtractProblemFeatures:

    def test_basic_features(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        assert isinstance(features, ProblemFeatures)
        assert features.graph_density >= 0
        assert features.seed_degree >= 0
        assert features.avg_weight > 0

    def test_empty_seeds(self):
        mem = _make_mem()
        features = mem._perspective.extract_problem_features([])
        assert features.seed_degree == 0.0
        assert features.connectivity == 0.0

    def test_connectivity_connected_seeds(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        assert features.connectivity > 0

    def test_to_vector_shape(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        vec = features.to_vector()
        assert vec.shape == (6,)


class TestRecordProblemOutcome:

    def test_history_stored(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        mem._perspective.record_problem_outcome(features, "classical", True)
        assert len(mem._perspective._problem_history) == 1
        vec, frame, success = mem._perspective._problem_history[0]
        assert frame == "classical"
        assert success is True

    def test_multiple_recordings(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        mem._perspective.record_problem_outcome(features, "classical", True)
        mem._perspective.record_problem_outcome(features, "quantum", False)
        assert len(mem._perspective._problem_history) == 2


class TestRecommendFrame:

    def test_no_history_returns_none(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        assert mem._perspective.recommend_frame(ids) is None

    def test_returns_best_frame_from_history(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
        for _ in range(5):
            mem._perspective.record_problem_outcome(features, "classical", True)
        for _ in range(5):
            mem._perspective.record_problem_outcome(features, "quantum", False)
        recommended = mem._perspective.recommend_frame(ids)
        assert recommended == "classical"

    def test_similar_problems_weighted(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features_a = mem._perspective.extract_problem_features(ids)
        for _ in range(10):
            mem._perspective.record_problem_outcome(features_a, "hypergraph", True)
            mem._perspective.record_problem_outcome(features_a, "classical", False)
        recommended = mem._perspective.recommend_frame(ids)
        assert recommended == "hypergraph"


class TestReasonWithFrameAutoRecording:

    def test_outcomes_recorded_on_reason(self):
        mem = _make_mem()
        mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        eff = mem._perspective.get_frame_effectiveness()
        assert "classical" in eff
        history = mem._perspective._problem_history
        assert len(history) >= 1
        _, frame, _ = history[0]
        assert frame == "classical"

    def test_multiple_frames_accumulate(self):
        mem = _make_mem()
        mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        mem.reason_with_frame({"a", "b", "c"}, frame_name="quantum")
        eff = mem._perspective.get_frame_effectiveness()
        assert "classical" in eff
        assert "quantum" in eff
        assert len(mem._perspective._problem_history) == 2


class TestTop2Rrf:

    def test_top2_rrf_strategy(self):
        mem = _make_mem()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="top2_rrf")
        assert len(analyses) == 4
        rrf_count = sum(1 for a in analyses.values() if "rrf_merged" in a.strengths)
        assert rrf_count == 2

    def test_top2_rrf_adds_rrf_score(self):
        mem = _make_mem()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="top2_rrf")
        for name, analysis in analyses.items():
            if "rrf_merged" in analysis.strengths:
                assert "rrf_score" in (analysis.parameters or {})

    def test_best_strategy_unchanged(self):
        mem = _make_mem()
        analyses = mem._perspective.multi_frame_analysis("a", strategy="best")
        for analysis in analyses.values():
            assert "rrf_merged" not in analysis.strengths


class TestSelectOptimalFrameLearned:

    def test_learned_shifts_with_outcomes(self):
        mem = _make_mem()
        ids = _seed_ids(mem)
        features = mem._perspective.extract_problem_features(ids)
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
