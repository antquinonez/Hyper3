from hyper3.memory import HypergraphMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.multi_perspective import RobustReachabilityDetector, RobustReachabilitySet


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("core")
    mem.store("bridge")
    mem.store("periphery_a")
    mem.store("periphery_b")
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
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        bridge = mem.graph.get_node_by_label("bridge")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert core.id in inv.invariant_nodes
        assert bridge.id in inv.invariant_nodes

    def test_confidence_is_ratio(self):
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert 0.0 <= inv.confidence <= 1.0

    def test_frame_count_matches(self):
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert inv.frame_count == 4

    def test_empty_seeds(self):
        mem = _make_mem()
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([], mem.graph)
        assert inv.invariant_nodes == set()

    def test_frame_unique_populated(self):
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        assert isinstance(inv.frame_unique, dict)


class TestMarkInvariants:

    def test_nodes_get_metadata(self):
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        detector.mark_invariants(inv, mem.graph)
        assert core.metadata.custom.get("invariant") is True
        assert "invariant_confidence" in core.metadata.custom

    def test_edges_get_metadata(self):
        mem = _make_mem()
        core = mem.graph.get_node_by_label("core")
        detector = RobustReachabilityDetector(mem._perspective)
        inv = detector.find_invariants([core.id], mem.graph)
        detector.mark_invariants(inv, mem.graph)
        for edge in mem.graph.edges:
            if edge.id in inv.invariant_edges:
                assert edge.metadata.custom.get("invariant") is True


class TestReasonWithConsensus:

    def test_returns_consensus_report(self):
        mem = _make_mem()
        result = mem.reason_robust({"core", "bridge"})
        assert "invariant_nodes" in result
        assert "confidence" in result
        assert "frame_count" in result

    def test_invariant_count_positive(self):
        mem = _make_mem()
        result = mem.reason_robust({"core"})
        assert result["invariant_nodes"] > 0

    def test_empty_seeds_returns_error(self):
        mem = _make_mem()
        result = mem.reason_robust({"nonexistent"})
        assert "error" in result
