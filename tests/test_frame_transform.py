import pytest

from hyper3.frame_transform import (
    FrameTransformer,
    TransformedConfig,
    _classical_to_hypergraph,
    _classical_to_probabilistic,
    _classical_to_quantum,
    _hypergraph_to_classical,
    _hypergraph_to_probabilistic,
    _hypergraph_to_quantum,
    _probabilistic_to_classical,
    _probabilistic_to_hypergraph,
    _probabilistic_to_quantum,
    _quantum_to_classical,
    _quantum_to_hypergraph,
    _quantum_to_probabilistic,
)
from hyper3.memory import HypergraphMemory
from hyper3.rules import TransitiveRule


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.add("a")
    mem.add("b")
    mem.add("c")
    mem.link("a", "b", label="rel")
    mem.link("b", "c", label="rel")
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
        assert cfg.information_loss == pytest.approx(2.0 / 3.0, abs=0.01)

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
                assert cfg.algorithm in {"bfs", "superposition", "probabilistic", "pattern_match"}
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





class TestTransformFunctionsDeep:
    def test_quantum_to_classical_with_amplitudes(self):
        result = _quantum_to_classical({"amplitudes": [0.6, 0.8]})
        assert result["algorithm"] == "bfs"
        assert result["info_loss"] == pytest.approx(1.0 - 0.64, abs=0.01)

    def test_quantum_to_classical_empty_amplitudes(self):
        result = _quantum_to_classical({"amplitudes": []})
        assert result["algorithm"] == "bfs"
        assert result["info_loss"] == pytest.approx(0.75, abs=0.01)

    def test_classical_to_probabilistic_with_weights(self):
        result = _classical_to_probabilistic({"weights": [1.0, 3.0]})
        assert result["algorithm"] == "probabilistic"
        assert result["parameters"]["normalize_weights"] is True
        assert result["parameters"]["total_weight"] == 4.0

    def test_classical_to_probabilistic_empty_weights(self):
        result = _classical_to_probabilistic({"weights": []})
        assert result["algorithm"] == "probabilistic"
        assert result["info_loss"] == 0.0

    def test_classical_to_probabilistic_zero_weights(self):
        result = _classical_to_probabilistic({"weights": [0.0, 0.0]})
        assert result["info_loss"] == 1.0

    def test_probabilistic_to_classical_with_probs(self):
        result = _probabilistic_to_classical({"probabilities": [0.3, 0.7]})
        assert result["algorithm"] == "bfs"
        assert result["parameters"]["cutoff_probability"] == pytest.approx(0.56, abs=0.01)

    def test_quantum_to_probabilistic_with_amplitudes(self):
        result = _quantum_to_probabilistic({"amplitudes": [0.6, 0.8]})
        assert result["algorithm"] == "probabilistic"
        assert "born_rule" in result["parameters"]
        assert len(result["parameters"]["probabilities"]) == 2

    def test_probabilistic_to_quantum_with_probs(self):
        result = _probabilistic_to_quantum({"probabilities": [0.3, 0.7]})
        assert result["algorithm"] == "superposition"
        assert len(result["parameters"]["amplitudes"]) == 2
        assert result["parameters"]["sqrt_transform"] is True

    def test_probabilistic_to_quantum_empty(self):
        result = _probabilistic_to_quantum({"probabilities": []})
        assert result["parameters"]["amplitudes"] == []
        assert result["info_loss"] == 0.0

    def test_hypergraph_to_probabilistic_with_weights(self):
        result = _hypergraph_to_probabilistic({"hyperedge_weights": [1.0, 2.0, 3.0]})
        assert result["algorithm"] == "probabilistic"
        assert result["info_loss"] == pytest.approx(0.07938, abs=0.001)

    def test_hypergraph_to_probabilistic_empty(self):
        result = _hypergraph_to_probabilistic({"hyperedge_weights": []})
        assert result["info_loss"] == 0.0

    def test_probabilistic_to_hypergraph_with_probs(self):
        result = _probabilistic_to_hypergraph({"probabilities": [0.4, 0.6]})
        assert result["algorithm"] == "pattern_match"
        assert result["info_loss"] == pytest.approx(0.0, abs=0.01)

    def test_probabilistic_to_hypergraph_empty(self):
        result = _probabilistic_to_hypergraph({"probabilities": []})
        assert result["info_loss"] == 0.0


class TestFrameTransformerUnsupported:
    def test_unsupported_pair(self):
        t = FrameTransformer()
        cfg = t.transform("unknown_frame", "also_unknown")
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss == 1.0
        assert cfg.preserved_properties == []

    def test_transform_passes_parameters(self):
        t = FrameTransformer()
        cfg = t.transform("classical", "quantum", parameters={"branching_factor": 4})
        assert cfg.parameters.get("branching_factor") == 4

    def test_transform_preserves_depth_and_branches(self):
        t = FrameTransformer()
        cfg = t.transform("classical", "quantum", max_depth=10, max_branches=20, max_total_states=100)
        assert cfg.max_depth == 10
        assert cfg.max_branches == 20
        assert cfg.max_total_states == 100


class TestTransformedConfig:
    def test_config_defaults(self):
        cfg = TransformedConfig(algorithm="test")
        assert cfg.max_depth == 3
        assert cfg.max_branches == 10
        assert cfg.max_total_states == 30
        assert cfg.parameters == {}
        assert cfg.information_loss == 0.0
        assert cfg.preserved_properties == []

    def test_config_fields(self):
        cfg = TransformedConfig(
            algorithm="bfs",
            information_loss=0.5,
            max_depth=5,
            preserved_properties=["reachability"],
        )
        assert cfg.algorithm == "bfs"
        assert cfg.information_loss == 0.5
        assert cfg.max_depth == 5
        assert "reachability" in cfg.preserved_properties
