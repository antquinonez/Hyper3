from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.multi_perspective import StructuralMetrics


def _make_mem():
    mem = CognitiveMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestComputeLocalClustering:

    def test_nonzero_for_asymmetric_graph(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        clustering = mem._perspective.compute_local_clustering([a.id])
        assert clustering >= 0.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._perspective.compute_local_clustering([]) == 0.0

    def test_single_node(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("x")
        x = mem.graph.get_node_by_label("x")
        clustering = mem._perspective.compute_local_clustering([x.id])
        assert clustering >= 0.0


class TestComputePerspectiveOverlap:

    def test_self_dragging_is_one(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        dragging = mem._perspective.compute_perspective_overlap([a.id], "classical", "classical")
        assert dragging == 1.0

    def test_cross_frame_dragging(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        dragging = mem._perspective.compute_perspective_overlap([a.id], "classical", "quantum")
        assert 0.0 <= dragging <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._perspective.compute_perspective_overlap([], "classical", "quantum") == 0.0


class TestComputeInformationDissipation:

    def test_classical_redshift(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        redshift = mem._perspective.compute_information_dissipation([a.id], "classical")
        assert 0.0 <= redshift <= 1.0

    def test_quantum_redshift(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        redshift = mem._perspective.compute_information_dissipation([a.id], "quantum")
        assert 0.0 <= redshift <= 1.0

    def test_empty_seeds(self):
        mem = _make_mem()
        assert mem._perspective.compute_information_dissipation([], "classical") == 0.0


class TestComputeStructuralMetrics:

    def test_returns_frame_metrics(self):
        mem = _make_mem()
        a = mem.graph.get_node_by_label("a")
        metrics = mem._perspective.compute_structural_metrics([a.id])
        assert isinstance(metrics, StructuralMetrics)
        assert metrics.local_clustering >= 0.0
        assert 0.0 <= metrics.perspective_overlap <= 1.0
        assert 0.0 <= metrics.information_dissipation <= 1.0
