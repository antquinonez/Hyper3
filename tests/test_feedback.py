from __future__ import annotations

import pytest

from hyper3.kernel import Hypergraph, Hypernode, Hyperedge
from hyper3.feedback import OperationFeedback, FeedbackSignal


def _make_graph(n: int = 4) -> Hypergraph:
    graph = Hypergraph()
    nodes = [Hypernode(label=f"n{i}") for i in range(n)]
    for node in nodes:
        graph.add_node(node)
    for i in range(n - 1):
        edge = Hyperedge(
            source_ids=frozenset({nodes[i].id}),
            target_ids=frozenset({nodes[i + 1].id}),
            label="next",
        )
        graph.add_edge(edge)
    return graph


class TestOperationFeedback:
    def test_record_collapse_outcome(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        n0 = graph.get_node_by_label("n0")
        assert n0 is not None
        fb.record_collapse_outcome("qs_1", n0.id, correct=True)
        assert fb.collapse_accuracy() == 1.0
        assert fb.signal_count == 1

    def test_collapse_accuracy_mixed(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        n0 = graph.get_node_by_label("n0")
        n1 = graph.get_node_by_label("n1")
        assert n0 and n1
        fb.record_collapse_outcome("qs_1", n0.id, correct=True)
        fb.record_collapse_outcome("qs_1", n1.id, correct=True)
        fb.record_collapse_outcome("qs_1", n0.id, correct=False)
        assert abs(fb.collapse_accuracy() - 2 / 3) < 0.01

    def test_collapse_accuracy_no_data(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        assert fb.collapse_accuracy() == 0.5

    def test_record_retrieval_outcome(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        n0 = graph.get_node_by_label("n0")
        n1 = graph.get_node_by_label("n1")
        n2 = graph.get_node_by_label("n2")
        assert n0 and n1 and n2
        fb.record_retrieval_outcome("test_query", {n0.id, n1.id}, {n2.id})
        assert abs(fb.retrieval_precision() - 2 / 3) < 0.01
        assert fb.signal_count == 3

    def test_retrieval_precision_no_data(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        assert fb.retrieval_precision() == 0.5

    def test_record_inference_outcome(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        fb.record_inference_outcome("edge_1", accepted=True)
        fb.record_inference_outcome("edge_2", accepted=True)
        fb.record_inference_outcome("edge_3", accepted=False)
        assert abs(fb.inference_acceptance_rate() - 2 / 3) < 0.01

    def test_inference_acceptance_rate_no_data(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        assert fb.inference_acceptance_rate() == 0.5

    def test_record_evolution_outcome(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        fb.record_evolution_outcome(0.8)
        fb.record_evolution_outcome(0.85)
        fb.record_evolution_outcome(0.9)
        assert fb.get_fitness_trend() == "improving"

    def test_fitness_trend_declining(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        fb.record_evolution_outcome(0.9)
        fb.record_evolution_outcome(0.8)
        fb.record_evolution_outcome(0.6)
        assert fb.get_fitness_trend() == "declining"

    def test_fitness_trend_stable(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        fb.record_evolution_outcome(0.7)
        fb.record_evolution_outcome(0.71)
        fb.record_evolution_outcome(0.7)
        assert fb.get_fitness_trend() == "stable"

    def test_fitness_trend_insufficient(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        assert fb.get_fitness_trend() == "insufficient_data"

    def test_get_reinforced_nodes(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        n0 = graph.get_node_by_label("n0")
        n1 = graph.get_node_by_label("n1")
        assert n0 and n1
        fb.record_retrieval_outcome("q", {n0.id}, set())
        fb.record_retrieval_outcome("q", {n0.id}, set())
        fb.record_retrieval_outcome("q", {n1.id}, set())
        reinforced = fb.get_reinforced_nodes(min_signals=2)
        assert n0.id in reinforced
        assert n1.id not in reinforced

    def test_get_suppressed_nodes(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        n0 = graph.get_node_by_label("n0")
        assert n0 is not None
        fb.record_retrieval_outcome("q", set(), {n0.id})
        fb.record_retrieval_outcome("q", set(), {n0.id})
        suppressed = fb.get_suppressed_nodes(min_signals=2)
        assert n0.id in suppressed

    def test_signals_property(self):
        graph = _make_graph()
        fb = OperationFeedback(graph)
        fb.record_collapse_outcome("qs", "node_1", True)
        signals = fb.signals
        assert len(signals) == 1
        assert isinstance(signals[0], FeedbackSignal)
        assert signals[0].signal_type == "collapse"


class TestEquivalenceEngineUpgrade:
    def test_structural_similarity_detects_equivalence(self):
        graph = Hypergraph()
        a = Hypernode(label="cat", data={"type": "animal"})
        b = Hypernode(label="dog", data={"type": "animal"})
        c = Hypernode(label="mammal")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_node(c)
        graph.add_edge(Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({c.id}),
            label="is_a",
        ))
        graph.add_edge(Hyperedge(
            source_ids=frozenset({b.id}),
            target_ids=frozenset({c.id}),
            label="is_a",
        ))
        from hyper3.kernel import EquivalenceEngine
        eq = EquivalenceEngine(graph, threshold=0.3)
        pairs = eq.find_equivalences()
        assert len(pairs) >= 1
        pair_ids = {(p[0], p[1]) for p in pairs}
        assert (a.id, b.id) in pair_ids or (b.id, a.id) in pair_ids

    def test_blocking_key_includes_edge_labels(self):
        graph = Hypergraph()
        a = Hypernode(label="x", data={"k": "v"})
        b = Hypernode(label="y", data={"k": "v"})
        graph.add_node(a)
        graph.add_node(b)
        from hyper3.kernel import EquivalenceEngine
        eq = EquivalenceEngine(graph)
        key_a = eq._blocking_key(a)
        key_b = eq._blocking_key(b)
        assert key_a == key_b
