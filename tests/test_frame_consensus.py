from hyper3.memory import HypergraphMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.multi_perspective import ConsensusResult, DisagreementRegion


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("core")
    mem.store("mid")
    mem.store("far_a")
    mem.store("far_b")
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
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="intersection")
        assert isinstance(result, ConsensusResult)
        assert result.strategy_used == "intersection"
        assert c.id in result.agreed_nodes

    def test_union_strategy(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="union")
        assert len(result.agreed_nodes) >= len(
            mem._perspective.compute_consensus([c.id], strategy="intersection").agreed_nodes
        )

    def test_majority_strategy(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id], strategy="majority")
        assert isinstance(result.agreed_nodes, set)

    def test_weighted_strategy(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        mem._perspective.record_frame_outcome("classical", True)
        mem._perspective.record_frame_outcome("quantum", False)
        result = mem._perspective.compute_consensus([c.id], strategy="weighted")
        assert isinstance(result.agreed_nodes, set)

    def test_confidence_is_ratio(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert 0.0 <= result.confidence <= 1.0

    def test_disagreement_regions_populated(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert isinstance(result.disagreement_regions, list)

    def test_frame_results_populated(self):
        mem = _make_mem()
        c = mem.graph.get_node_by_label("core")
        result = mem._perspective.compute_consensus([c.id])
        assert len(result.frame_results) == 4

    def test_empty_seeds(self):
        mem = _make_mem()
        result = mem._perspective.compute_consensus([])
        assert result.agreed_nodes == set()


class TestResolveDisagreement:

    def test_all_frames_agree(self):
        mem = _make_mem()
        reachability = {
            "classical": {"a", "b"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "intersection")
        assert result == {"a", "b"}

    def test_partial_disagreement_intersection(self):
        mem = _make_mem()
        reachability = {
            "classical": {"a", "b", "c"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "intersection")
        assert result == {"a", "b"}

    def test_partial_disagreement_union(self):
        mem = _make_mem()
        reachability = {
            "classical": {"a", "b", "c"},
            "quantum": {"a", "b"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "union")
        assert result == {"a", "b", "c"}

    def test_majority_with_4_frames(self):
        mem = _make_mem()
        reachability = {
            "classical": {"a", "b"},
            "quantum": {"a"},
            "hypergraph": {"a", "b"},
            "probabilistic": {"a"},
        }
        result = mem._perspective.resolve_disagreement(reachability, "majority")
        assert "a" in result
