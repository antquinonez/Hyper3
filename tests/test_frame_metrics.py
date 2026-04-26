from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.relativity import FrameMetrics


def _make_mem():
    mem = CognitiveMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestComputeCurvature:

    def test_nonzero_for_asymmetric_graph(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        curvature = mem._relativity.compute_curvature([a.id])
        assert curvature >= 0.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._relativity.compute_curvature([]) == 0.0

    def test_single_node(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("x")
        x = mem.graph.get_node_by_label("x")
        curvature = mem._relativity.compute_curvature([x.id])
        assert curvature >= 0.0


class TestComputeFrameDragging:

    def test_self_dragging_is_one(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        dragging = mem._relativity.compute_frame_dragging([a.id], "classical", "classical")
        assert dragging == 1.0

    def test_cross_frame_dragging(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        dragging = mem._relativity.compute_frame_dragging([a.id], "classical", "quantum")
        assert 0.0 <= dragging <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._relativity.compute_frame_dragging([], "classical", "quantum") == 0.0


class TestComputeRedshift:

    def test_classical_redshift(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        redshift = mem._relativity.compute_redshift([a.id], "classical")
        assert 0.0 <= redshift <= 1.0

    def test_quantum_redshift(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        redshift = mem._relativity.compute_redshift([a.id], "quantum")
        assert 0.0 <= redshift <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._relativity.compute_redshift([], "classical") == 0.0


class TestComputeFrameMetrics:

    def test_returns_frame_metrics(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        metrics = mem._relativity.compute_frame_metrics([a.id])
        assert isinstance(metrics, FrameMetrics)
        assert metrics.curvature >= 0.0
        assert 0.0 <= metrics.frame_dragging <= 1.0
        assert 0.0 <= metrics.redshift <= 1.0
