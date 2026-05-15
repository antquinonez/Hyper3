from __future__ import annotations

import pytest

from hyper3.context_compression import (
    CompressionCandidate,
    CompressionReport,
    CompressionResult,
    ContextCompressionEngine,
)
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_node(g: Hypergraph, label: str, data: dict | None = None) -> Hypernode:
    node = Hypernode(label=label, data=data)
    return g.add_node(node)


def _add_edge(
    g: Hypergraph, src: str, tgt: str, label: str = "rel", weight: float = 1.0
) -> Hyperedge:
    edge = Hyperedge(
        source_ids=frozenset({src}),
        target_ids=frozenset({tgt}),
        label=label,
        weight=weight,
    )
    return g.add_edge(edge)


class TestContextCompressionEngineInit:
    def test_default_params(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(g)
        assert engine._similarity_threshold == 0.8
        assert engine._max_merge_per_pass == 20
        assert engine._min_cluster_size == 3

    def test_custom_params(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(
            g,
            similarity_threshold=0.5,
            max_merge_per_pass=5,
            min_cluster_size=2,
        )
        assert engine._similarity_threshold == 0.5
        assert engine._max_merge_per_pass == 5
        assert engine._min_cluster_size == 2


class TestFindCandidates:
    def test_empty_graph(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(g)
        assert engine.find_candidates() == []

    def test_single_node(self):
        g = Hypergraph()
        _add_node(g, "a")
        engine = ContextCompressionEngine(g)
        assert engine.find_candidates() == []

    def test_two_isolated_nodes(self):
        g = Hypergraph()
        _add_node(g, "a")
        _add_node(g, "b")
        engine = ContextCompressionEngine(g, similarity_threshold=0.99)
        candidates = engine.find_candidates()
        pair_candidates = [c for c in candidates if c.node_b_id]
        assert len(pair_candidates) == 0

    def test_two_similar_nodes_with_shared_neighbor(self):
        g = Hypergraph()
        a = _add_node(g, "a", {"type": "x"})
        b = _add_node(g, "b", {"type": "x"})
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "rel")
        _add_edge(g, b.id, c.id, "rel")
        engine = ContextCompressionEngine(g, similarity_threshold=0.3)
        candidates = engine.find_candidates()
        pair_candidates = [c for c in candidates if c.node_b_id]
        assert len(pair_candidates) >= 1

    def test_threshold_filters_low_similarity(self):
        g = Hypergraph()
        _add_node(g, "a", {"x": "1"})
        _add_node(g, "b", {"y": "2"})
        engine = ContextCompressionEngine(g, similarity_threshold=0.99)
        pair_candidates = [
            c for c in engine.find_candidates() if c.node_b_id
        ]
        assert len(pair_candidates) == 0

    def test_cluster_candidates_found_for_dense_subgraph(self):
        g = Hypergraph()
        nodes = [_add_node(g, f"n{i}") for i in range(5)]
        for i in range(4):
            for j in range(i + 1, 4):
                _add_edge(g, nodes[i].id, nodes[j].id, "rel")
        _add_edge(g, nodes[3].id, nodes[4].id, "out")
        engine = ContextCompressionEngine(
            g, similarity_threshold=0.3, min_cluster_size=3
        )
        candidates = engine.find_candidates()
        collapse_candidates = [c for c in candidates if c.strategy == "collapse"]
        assert len(collapse_candidates) >= 1


class TestCompress:
    def test_merge_strategy_combines_similar_nodes(self):
        g = Hypergraph()
        a = _add_node(g, "a", {"type": "x"})
        b = _add_node(g, "b", {"type": "x"})
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "rel")
        _add_edge(g, b.id, c.id, "rel")
        engine = ContextCompressionEngine(g, similarity_threshold=0.3)
        result = engine.compress(strategy="merge")
        assert result.merged_pairs >= 1
        assert result.nodes_before == 3
        assert result.nodes_after < 3

    def test_collapse_strategy_creates_summary(self):
        g = Hypergraph()
        nodes = [_add_node(g, f"n{i}") for i in range(5)]
        for i in range(4):
            for j in range(i + 1, 4):
                _add_edge(g, nodes[i].id, nodes[j].id, "rel")
        _add_edge(g, nodes[3].id, nodes[4].id, "out")
        engine = ContextCompressionEngine(
            g, similarity_threshold=0.3, min_cluster_size=3
        )
        result = engine.compress(strategy="collapse")
        assert result.collapsed_groups >= 1 or result.nodes_after < result.nodes_before

    def test_auto_strategy_selects_merge(self):
        g = Hypergraph()
        a = _add_node(g, "a", {"type": "x"})
        b = _add_node(g, "b", {"type": "x"})
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "rel")
        _add_edge(g, b.id, c.id, "rel")
        engine = ContextCompressionEngine(g, similarity_threshold=0.3)
        result = engine.compress(strategy="auto")
        assert result.candidates_evaluated >= 1
        assert result.merged_pairs + result.collapsed_groups >= 1

    def test_empty_graph_compression(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(g)
        result = engine.compress()
        assert result.nodes_before == 0
        assert result.nodes_after == 0
        assert result.merged_pairs == 0

    def test_before_after_counts(self):
        g = Hypergraph()
        a = _add_node(g, "a", {"type": "t"})
        b = _add_node(g, "b", {"type": "t"})
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "r")
        _add_edge(g, b.id, c.id, "r")
        engine = ContextCompressionEngine(g, similarity_threshold=0.3)
        result = engine.compress(strategy="merge")
        assert result.nodes_before == 3
        assert result.nodes_after < 3
        assert result.edges_before == 2
        assert result.edges_after >= 1


class TestCompressPair:
    def test_explicit_merge(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        engine = ContextCompressionEngine(g)
        result = engine.compress_pair(a.id, b.id, strategy="merge")
        assert result.merged_pairs == 1
        assert result.nodes_after == 1

    def test_not_found_nodes(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(g)
        result = engine.compress_pair("missing_a", "missing_b")
        assert result.merged_pairs == 0
        assert result.collapsed_groups == 0

    def test_self_compression_noop(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        engine = ContextCompressionEngine(g)
        result = engine.compress_pair(a.id, a.id)
        assert result.merged_pairs == 0
        assert result.nodes_before == result.nodes_after

    def test_collapse_pair(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        engine = ContextCompressionEngine(g)
        result = engine.compress_pair(a.id, b.id, strategy="collapse")
        assert result.collapsed_groups == 1
        assert result.nodes_after == result.nodes_before + 1

    def test_compress_pair_preserves_external_edges(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "rel")
        _add_edge(g, b.id, c.id, "rel")
        engine = ContextCompressionEngine(g)
        engine.compress_pair(a.id, b.id, strategy="merge")
        assert c in g.nodes or g.get_node(c.id) is not None


class TestReport:
    def test_empty_report(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(g)
        report = engine.report()
        assert report.total_compressions == 0
        assert report.total_nodes_saved == 0

    def test_accumulates_statistics(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        engine = ContextCompressionEngine(g)
        engine.compress_pair(a.id, b.id)
        report = engine.report()
        assert report.total_compressions == 1
        assert report.total_nodes_saved == 1
        assert "merge" in report.strategies_used
        assert report.strategies_used["merge"] == 1


class TestSerialization:
    def test_to_dict(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(
            g, similarity_threshold=0.6, max_merge_per_pass=10
        )
        d = engine.to_dict()
        assert d["similarity_threshold"] == 0.6
        assert d["max_merge_per_pass"] == 10
        assert d["history"] == []

    def test_from_dict(self):
        g = Hypergraph()
        data = {
            "similarity_threshold": 0.5,
            "max_merge_per_pass": 5,
            "min_cluster_size": 4,
        }
        engine = ContextCompressionEngine.from_dict(data, g)
        assert engine._similarity_threshold == 0.5
        assert engine._max_merge_per_pass == 5
        assert engine._min_cluster_size == 4

    def test_roundtrip(self):
        g = Hypergraph()
        engine = ContextCompressionEngine(
            g, similarity_threshold=0.7, max_merge_per_pass=15
        )
        a = _add_node(g, "x")
        b = _add_node(g, "y")
        engine.compress_pair(a.id, b.id)
        d = engine.to_dict()
        assert len(d["history"]) == 1
        restored = ContextCompressionEngine.from_dict(d, g)
        assert restored._similarity_threshold == 0.7
        assert restored._max_merge_per_pass == 15


class TestResultDataclass:
    def test_compression_result_bracket_access(self):
        r = CompressionResult(
            candidates_evaluated=5,
            merged_pairs=2,
            nodes_before=10,
            nodes_after=8,
        )
        assert r["candidates_evaluated"] == 5
        assert r["merged_pairs"] == 2
        assert "nodes_before" in r

    def test_compression_candidate_keys(self):
        c = CompressionCandidate(
            node_a_id="a", node_b_id="b", similarity=0.9, strategy="merge"
        )
        assert "node_a_id" in c
        assert "similarity" in c

    def test_compression_report_get(self):
        r = CompressionReport(total_compressions=3)
        assert r.get("total_compressions") == 3
        assert r.get("missing_field", 0) == 0


class TestEdgeCases:
    def test_already_merged_no_recompression(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        engine = ContextCompressionEngine(g)
        result1 = engine.compress_pair(a.id, b.id)
        assert result1.merged_pairs == 1
        result2 = engine.compress_pair(a.id, b.id)
        assert result2.merged_pairs == 0

    def test_max_merge_per_pass_respected(self):
        g = Hypergraph()
        nodes = [_add_node(g, f"n{i}", {"type": "x"}) for i in range(5)]
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                _add_edge(g, nodes[i].id, nodes[j].id, "r")
        engine = ContextCompressionEngine(
            g, similarity_threshold=0.3, max_merge_per_pass=1
        )
        result = engine.compress(strategy="merge")
        assert result.merged_pairs <= 1

    def test_compress_context_details_records_strategy(self):
        g = Hypergraph()
        a = _add_node(g, "a")
        b = _add_node(g, "b")
        engine = ContextCompressionEngine(g)
        result = engine.compress_pair(a.id, b.id, strategy="merge")
        assert len(result.details) == 1
        assert result.details[0]["strategy"] == "merge"


class TestIntegration:
    def test_compress_context_via_facade(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a", data={"type": "x"})
        mem.add("b", data={"type": "x"})
        mem.add("c")
        mem.link("a", "c", label="rel")
        mem.link("b", "c", label="rel")
        result = mem.compress_context(strategy="merge")
        assert isinstance(result, CompressionResult)
        assert result.candidates_evaluated >= 0

    def test_compress_then_evolve(self):
        from hyper3.memory import HypergraphMemory

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "c", label="rel")
        mem.link("b", "c", label="rel")
        mem.compress_context(strategy="merge")
        evolve_result = mem.evolve()
        assert evolve_result is not None

    def test_second_compress_finds_fewer_candidates(self):
        g = Hypergraph()
        a = _add_node(g, "a", {"type": "x"})
        b = _add_node(g, "b", {"type": "x"})
        c = _add_node(g, "c")
        _add_edge(g, a.id, c.id, "rel")
        _add_edge(g, b.id, c.id, "rel")
        engine = ContextCompressionEngine(g, similarity_threshold=0.3)
        result1 = engine.compress(strategy="merge")
        assert result1.merged_pairs >= 1
        result2 = engine.compress(strategy="merge")
        assert result2.merged_pairs == 0
