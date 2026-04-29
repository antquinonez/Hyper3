"""Tests for hypergraph-native algorithms and n-ary edge support."""

from __future__ import annotations

import pytest

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.memory import HypergraphMemory


def _make_graph_with_edges():
    g = Hypergraph()
    a = Hypernode(label="A")
    b = Hypernode(label="B")
    c = Hypernode(label="C")
    d = Hypernode(label="D")
    for n in [a, b, c, d]:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel", weight=2.0))
    g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel", weight=3.0))
    g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="rel", weight=1.0))
    return g, a, b, c, d


def _make_hyperedge_graph():
    g = Hypergraph()
    a = Hypernode(label="A")
    b = Hypernode(label="B")
    c = Hypernode(label="C")
    d = Hypernode(label="D")
    e = Hypernode(label="E")
    for n in [a, b, c, d, e]:
        g.add_node(n)
    g.add_edge(Hyperedge(
        source_ids=frozenset({a.id, b.id}),
        target_ids=frozenset({c.id, d.id}),
        label="joint_produces",
        weight=2.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({c.id}),
        target_ids=frozenset({e.id}),
        label="leads_to",
        weight=1.0,
    ))
    g.add_edge(Hyperedge(
        source_ids=frozenset({d.id, e.id}),
        target_ids=frozenset({a.id}),
        label="feeds_back",
        weight=1.5,
    ))
    return g, a, b, c, d, e


class TestNaryEdgeCreation:
    def test_create_and_query_hyperedge(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        hyperedges = [edge for edge in g.edges if len(edge.source_ids) > 1 or len(edge.target_ids) > 1]
        assert len(hyperedges) == 2
        joint = next(e for e in hyperedges if e.label == "joint_produces")
        assert joint.source_ids == frozenset({a.id, b.id})
        assert joint.target_ids == frozenset({c.id, d.id})

    def test_relate_hyperedge_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("gene_a")
        mem.store("gene_b")
        mem.store("protein_complex")
        mem.store("pathway")
        edge = mem.relate_hyperedge(
            {"gene_a", "gene_b"},
            {"protein_complex", "pathway"},
            label="jointly_encodes",
            weight=5.0,
        )
        assert edge.weight == 5.0
        assert len(edge.source_ids) == 2
        assert len(edge.target_ids) == 2
        assert edge.label == "jointly_encodes"

    def test_query_hyperedges_by_cardinality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.store("z")
        mem.relate("x", "y", label="pair")
        mem.relate_hyperedge({"x", "y"}, {"z"}, label="nary")

        pairwise = mem.query_hyperedges(min_source_cardinality=1, min_target_cardinality=1)
        assert len(pairwise) == 2

        nary_only = mem.query_hyperedges(min_source_cardinality=2)
        assert len(nary_only) == 1
        assert nary_only[0].label == "nary"

    def test_query_hyperedges_by_containing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate_hyperedge({"a", "b"}, {"c"}, label="abc")
        mem.relate("a", "b", label="ab")

        edges_with_a = mem.query_hyperedges(containing="a")
        assert len(edges_with_a) == 2

        edges_with_c = mem.query_hyperedges(containing="c")
        assert len(edges_with_c) == 1
        assert edges_with_c[0].label == "abc"

    def test_hyperedge_neighbors(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        nbrs = g.hyperedge_neighbors(a.id)
        assert b.id in nbrs
        assert c.id in nbrs
        assert d.id in nbrs
        assert len(nbrs[b.id]) == 1
        assert len(nbrs[c.id]) == 1

    def test_hyperedge_neighbors_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate_hyperedge({"a", "b"}, {"c"}, label="joint")
        nbrs = mem.hyperedge_neighbors("a")
        assert "b" in nbrs
        assert "c" in nbrs


class TestStar:
    def test_star_returns_incident_edges(self):
        g, a, b, c, d = _make_graph_with_edges()
        edges = g.star(b.id)
        assert len(edges) == 2
        labels = {e.label for e in edges}
        assert labels == {"rel"}

    def test_star_empty_for_unknown(self):
        g = Hypergraph()
        assert g.star("nonexistent") == []


class TestHyperedgeCocoverage:
    def test_cocoverage_counts(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        cov = g.hyperedge_cocoverage(a.id)
        assert cov[b.id] == 1
        assert cov[c.id] == 1
        assert cov[d.id] == 2
        assert cov[e.id] == 1


class TestConnectedComponents:
    def test_pairwise_components(self):
        g, a, b, c, d = _make_graph_with_edges()
        comps = g.connected_components()
        assert len(comps) == 1
        assert {a.id, b.id, c.id, d.id} == comps[0]

    def test_disconnected_components(self):
        g = Hypergraph()
        a, b, c, d = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C"), Hypernode(label="D")
        for n in [a, b, c, d]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        comps = g.connected_components()
        assert len(comps) == 3
        sizes = sorted(len(c) for c in comps)
        assert sizes == [1, 1, 2]

    def test_hyperedge_connects_all_members(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps = g.connected_components()
        assert len(comps) == 1
        assert {a.id, b.id, c.id, d.id, e.id} == comps[0]

    def test_s_components_high_s_splits(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps_s1 = g.connected_components(s=1)
        assert len(comps_s1) == 1
        comps_s3 = g.connected_components(s=3)
        assert len(comps_s3) >= 2


class TestShortestPath:
    def test_pairwise_shortest_path(self):
        g, a, b, c, d = _make_graph_with_edges()
        path = g.shortest_path(a.id, d.id, weighted=False)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == d.id
        assert len(path) == 4

    def test_no_path(self):
        g = Hypergraph()
        a, b = Hypernode(label="A"), Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        assert g.shortest_path(a.id, b.id) is None

    def test_weighted_shortest_path(self):
        g, a, b, c, d = _make_graph_with_edges()
        path = g.shortest_path(a.id, d.id, weighted=True)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == d.id

    def test_hyperedge_shortest_path(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        path = g.shortest_path(a.id, e.id, weighted=False)
        assert path is not None
        assert path[0] == a.id
        assert path[-1] == e.id

    def test_same_node(self):
        g, a, *_ = _make_graph_with_edges()
        path = g.shortest_path(a.id, a.id)
        assert path == [a.id]


class TestCycleDetection:
    def test_no_cycle(self):
        g, a, b, c, d = _make_graph_with_edges()
        assert g.has_cycle() is False

    def test_detect_cycle(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id})))
        assert g.has_cycle() is True

    def test_detect_cycles_returns_list(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C")
        for n in [a, b, c]:
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id})))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id})))
        cycles = g.detect_cycles()
        assert len(cycles) >= 1

    def test_hyperedge_cycle(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        assert g.has_cycle() is True


class TestBetweennessCentrality:
    def test_basic_centrality(self):
        g, a, b, c, d = _make_graph_with_edges()
        bc = g.betweenness_centrality()
        assert len(bc) == 4
        assert all(0.0 <= v <= 1.0 for v in bc.values())
        assert bc[b.id] > 0 or bc[c.id] > 0

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.betweenness_centrality() == {}

    def test_approximate_with_sampling(self):
        g, a, b, c, d = _make_graph_with_edges()
        bc = g.betweenness_centrality(max_samples=5)
        assert len(bc) == 4


class TestPageRank:
    def test_basic_pagerank(self):
        g, a, b, c, d = _make_graph_with_edges()
        pr = g.pagerank()
        assert len(pr) == 4
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01

    def test_pagerank_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="rel")
        mem.relate("B", "C", label="rel")
        pr = mem.pagerank()
        assert len(pr) == 3
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01

    def test_empty_graph(self):
        g = Hypergraph()
        pr = g.pagerank()
        assert pr == {}

    def test_no_edges(self):
        g = Hypergraph()
        a, b = Hypernode(label="A"), Hypernode(label="B")
        g.add_node(a)
        g.add_node(b)
        pr = g.pagerank()
        assert len(pr) == 2
        assert abs(pr[a.id] - pr[b.id]) < 0.01


class TestSPersistence:
    def test_basic_filtration(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        filt = g.s_persistence()
        assert len(filt.levels) >= 1
        assert filt.levels[0].s == 1
        assert filt.levels[0].num_components >= 1
        if len(filt.levels) > 1:
            assert filt.levels[-1].num_components >= filt.levels[0].num_components

    def test_no_edges(self):
        g = Hypergraph()
        filt = g.s_persistence()
        assert len(filt.levels) == 0
        g2 = Hypergraph()
        a = Hypernode(label="A")
        g2.add_node(a)
        filt2 = g2.s_persistence()
        assert len(filt2.levels) == 1
        assert filt2.levels[0].num_components == 1

    def test_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate_hyperedge({"a", "b"}, {"c"}, label="abc")
        filt = mem.s_persistence()
        assert len(filt.levels) >= 1


class TestHyperedgeSimilarity:
    def test_jaccard_similarity(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        e1 = edges[0]
        result = g.hyperedge_similarity(e1.id, metric="jaccard")
        assert len(result.similar_edges) > 0
        assert all(0.0 <= score <= 1.0 for _, score in result.similar_edges)

    def test_sorensen_dice(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        e1 = edges[0]
        result = g.hyperedge_similarity(e1.id, metric="sorensen_dice")
        assert len(result.similar_edges) > 0

    def test_top_k(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        edges = list(g._edges.values())
        result = g.hyperedge_similarity(edges[0].id, top_k=1)
        assert len(result.similar_edges) <= 1


class TestSpectralEmbedding:
    def test_basic_embedding(self):
        g, a, b, c, d = _make_graph_with_edges()
        se = g.spectral_embedding(dimensions=2)
        assert len(se.node_ids) == 4
        assert se.embeddings.shape[0] == 4
        assert se.embeddings.shape[1] <= 2

    def test_empty_graph(self):
        g = Hypergraph()
        se = g.spectral_embedding()
        assert len(se.node_ids) == 0

    def test_via_memory(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="r")
        mem.relate("B", "C", label="r")
        result = mem.spectral_embedding(dimensions=2)
        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert len(result["A"]) <= 2


class TestSpreadHyperedge:
    def test_linear_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="r")
        mem.relate("B", "C", label="r")
        results = mem.spread_hyperedge("A", energy=1.0, mode="linear", iterations=3)
        labels = {r.label for r in results}
        assert "B" in labels

    def test_and_mode_requires_all_sources(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate_hyperedge({"A", "B"}, {"C"}, label="joint")
        results = mem.spread_hyperedge("A", energy=1.0, mode="and", iterations=3)
        labels = {r.label for r in results}
        assert "C" not in labels

    def test_and_mode_succeeds_with_all_sources(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate_hyperedge({"A", "B"}, {"C"}, label="joint")
        if mem._activation is None:
            from hyper3.retrieval_activation import SpreadingActivation
            mem._activation = SpreadingActivation(mem._graph)
        mem._activation.clear()
        a_node = mem._find_node("A")
        b_node = mem._find_node("B")
        mem._activation.stimulate(a_node.id, 1.0)
        mem._activation.stimulate(b_node.id, 1.0)
        mem._activation.spread_hyperedge(mode="and", iterations=3)
        activated = mem._activation.get_activated()
        labels = {r.label for r in activated}
        assert "C" in labels

    def test_or_mode(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate_hyperedge({"A", "B"}, {"C"}, label="joint")
        results = mem.spread_hyperedge("A", energy=1.0, mode="or", iterations=3)
        labels = {r.label for r in results}
        assert "C" in labels


class TestIncidenceMatrixUnsigned:
    def test_unsigned_incidence(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        H, node_ids, edge_ids = g.incidence_matrix_unsigned()
        assert H.shape[0] == 5
        assert H.shape[1] == 3
        for val in H.flat:
            assert val in (0.0, 1.0)
        import numpy as np
        assert np.sum(H) > 0


class TestGraphLevelMethods:
    def test_s_connected_components(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        comps = g.s_connected_components(s=1)
        assert len(comps) == 1
        comps_high = g.s_connected_components(s=10)
        assert len(comps_high) > 1

    def test_incidence_matrix_with_nary(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        H, node_ids, edge_ids = g.incidence_matrix()
        assert H.shape[0] == 5
        assert H.shape[1] == 3
        import numpy as np
        positive = np.sum(H > 0)
        negative = np.sum(H < 0)
        assert positive > 0
        assert negative > 0

    def test_laplacian_with_nary(self):
        g, a, b, c, d, e = _make_hyperedge_graph()
        L = g.hypergraph_laplacian()
        import numpy as np
        assert L.shape == (5, 5)
        assert np.allclose(L, L.T, atol=1e-10)
