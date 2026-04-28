from hyper3.frame_transform import FrameTransformer, TransformedConfig
from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule


def _make_mem():
    mem = CognitiveMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestFrameTransformerIdentity:

    def test_identity_classical(self):
        t = FrameTransformer()
        cfg = t.transform("classical", "classical")
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss == 0.0
        assert "all" in cfg.preserved_properties

    def test_identity_quantum(self):
        t = FrameTransformer()
        cfg = t.transform("quantum", "quantum")
        assert cfg.algorithm == "superposition"
        assert cfg.information_loss == 0.0

    def test_identity_hypergraph(self):
        t = FrameTransformer()
        cfg = t.transform("hypergraph", "hypergraph")
        assert cfg.algorithm == "pattern_match"

    def test_identity_probabilistic(self):
        t = FrameTransformer()
        cfg = t.transform("probabilistic", "probabilistic")
        assert cfg.algorithm == "probabilistic"


class TestFrameTransformerPairs:

    def test_classical_to_quantum(self):
        t = FrameTransformer()
        cfg = t.transform("classical", "quantum")
        assert cfg.algorithm == "superposition"
        assert cfg.information_loss == 0.0
        assert "reachability" in cfg.preserved_properties

    def test_quantum_to_classical(self):
        t = FrameTransformer()
        cfg = t.transform("quantum", "classical", parameters={"max_amplitude_sq": 0.8})
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss == pytest.approx(0.2, abs=0.01)

    def test_classical_to_probabilistic(self):
        t = FrameTransformer()
        cfg = t.transform("classical", "probabilistic")
        assert cfg.algorithm == "probabilistic"
        assert cfg.information_loss == 0.0

    def test_probabilistic_to_classical(self):
        t = FrameTransformer()
        cfg = t.transform("probabilistic", "classical", parameters={"best_probability": 0.7})
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss == pytest.approx(0.3, abs=0.01)

    def test_hypergraph_to_classical(self):
        t = FrameTransformer()
        cfg = t.transform("hypergraph", "classical", parameters={"arity_sum": 6})
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss > 0.0

    def test_quantum_to_probabilistic(self):
        t = FrameTransformer()
        cfg = t.transform("quantum", "probabilistic")
        assert cfg.algorithm == "probabilistic"
        assert cfg.information_loss == 0.0

    def test_probabilistic_to_quantum(self):
        t = FrameTransformer()
        cfg = t.transform("probabilistic", "quantum")
        assert cfg.algorithm == "superposition"
        assert cfg.information_loss == 0.0

    def test_all_pairs_produce_config(self):
        t = FrameTransformer()
        frames = ["classical", "quantum", "hypergraph", "probabilistic"]
        for src in frames:
            for dst in frames:
                cfg = t.transform(src, dst)
                assert isinstance(cfg, TransformedConfig)
                assert 0.0 <= cfg.information_loss <= 1.0


class TestInformationLoss:

    def test_loss_method_matches_transform(self):
        t = FrameTransformer()
        params = {"max_amplitude_sq": 0.6}
        cfg = t.transform("quantum", "classical", parameters=params)
        loss = t.information_loss("quantum", "classical", parameters=params)
        assert cfg.information_loss == loss

    def test_unknown_pair_full_loss(self):
        t = FrameTransformer()
        loss = t.information_loss("unknown_frame", "classical")
        assert loss == 1.0

    def test_identity_zero_loss(self):
        t = FrameTransformer()
        assert t.information_loss("classical", "classical") == 0.0


class TestReasonWithFrameTransform:

    def test_frame_config_in_result(self):
        mem = _make_mem()
        result = mem.reason_with_frame({"a", "b", "c"}, frame_name="quantum")
        assert "frame_config" in result
        assert result["frame_config"]["algorithm"] == "superposition"

    def test_different_frames_different_algorithms(self):
        mem = _make_mem()
        r_classical = mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        mem.commit_inferences()
        r_quantum = mem.reason_with_frame({"a", "b", "c"}, frame_name="quantum")
        assert r_classical["frame_config"]["algorithm"] != r_quantum["frame_config"]["algorithm"]

    def test_transform_config_on_perspective(self):
        mem = _make_mem()
        cfg = mem._perspective.transform_config("a", "classical", "quantum")
        assert cfg.algorithm == "superposition"
        assert cfg.information_loss == 0.0


import pytest
