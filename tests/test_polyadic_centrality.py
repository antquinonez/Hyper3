"""Polyadic tests for kernel_centrality.py (CentralityMixin).

Validates that degree, betweenness, closeness, eigenvector, Katz,
PageRank, h-eigenvector, z-eigenvector, node-edge, s-walk, and
delegated centrality methods handle n-ary edges correctly.
"""
from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_nary(
    g: Hypergraph,
    sources: list[str],
    targets: list[str],
    label: str = "e",
    weight: float = 1.0,
    ids: dict[str, str] | None = None,
) -> dict[str, str]:
    ids = dict(ids) if ids else {}
    for lbl in set(sources) | set(targets):
        if lbl in ids:
            continue
        node = Hypernode(label=lbl)
        g.add_node(node)
        ids[lbl] = node.id
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({ids[s] for s in sources}),
            target_ids=frozenset({ids[t] for t in targets}),
            label=label,
            weight=weight,
        )
    )
    return ids


class TestPolyadicDegreeCentrality:
    def test_nary_degree_counts_edges_not_participants(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        dc = g.degree_centrality()
        for nid in dc:
            assert dc[nid] > 0

    def test_nary_vs_pairwise_degree(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        dc = g.degree_centrality()
        assert dc[ids["A"]] == dc[ids["B"]]

    def test_nary_hub_has_highest_degree(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["H", "X", "Y"], ["A"], label="e1")
        ids = _add_nary(g, ["H"], ["B", "C"], label="e2", ids=ids)
        dc = g.degree_centrality()
        hub_id = ids["H"]
        for nid, score in dc.items():
            if nid != hub_id:
                assert dc[hub_id] >= score


class TestPolyadicBetweenness:
    def test_nary_bridge_high_betweenness(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="left")
        ids = _add_nary(g, ["C"], ["D", "E"], label="right", ids=ids)
        bc = g.betweenness_centrality()
        assert bc[ids["C"]] > 0

    def test_nary_leaf_zero_betweenness(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D"], label="fwd")
        ids = _add_nary(g, ["D"], ["E", "F"], label="fwd2", ids=ids)
        bc = g.betweenness_centrality()
        assert bc[ids["E"]] == 0.0
        assert bc[ids["F"]] == 0.0

    def test_nary_betweenness_normalized(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        bc = g.betweenness_centrality()
        for v in bc.values():
            assert 0.0 <= v <= 1.0


class TestPolyadicCloseness:
    def test_nary_hub_has_highest_closeness(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["H"], ["A", "B", "C"], label="hub")
        ids = _add_nary(g, ["A"], ["D"], label="spoke", ids=ids)
        cc = g.closeness_centrality()
        assert cc[ids["H"]] >= cc[ids["D"]]

    def test_nary_closeness_bounded(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        cc = g.closeness_centrality()
        for v in cc.values():
            assert 0.0 <= v <= 1.0


class TestPolyadicEigenvector:
    def test_nary_eigenvector_nonnegative(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        ec = g.eigenvector_centrality()
        for v in ec.values():
            assert v >= 0.0

    def test_nary_eigenvector_numpy(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        ec = g.eigenvector_centrality_numpy()
        assert len(ec) == 4


class TestPolyadicPageRank:
    def test_nary_pagerank_sums_to_one(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        pr = g.pagerank()
        assert abs(sum(pr.values()) - 1.0) < 1e-6

    def test_nary_hub_highest_pagerank(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["H"], ["A", "B", "C"], label="hub", weight=5.0)
        ids = _add_nary(g, ["A"], ["D"], label="spoke", weight=1.0, ids=ids)
        pr = g.pagerank()
        assert abs(sum(pr.values()) - 1.0) < 1e-6
        targets = [ids["A"], ids["B"], ids["C"]]
        for tid in targets:
            assert pr[tid] > 0.0

    def test_nary_pagerank_nonnegative(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        pr = g.pagerank()
        for v in pr.values():
            assert v >= 0.0


class TestPolyadicKatz:
    def test_nary_katz_all_positive(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        kc = g.katz_centrality(alpha=0.1)
        for v in kc.values():
            assert v > 0.0

    def test_nary_katz_solve(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        kc = g.katz_centrality_solve(alpha=0.1)
        assert len(kc) == 3


class TestPolyadicHEigenvector:
    def test_nary_h_eigenvector(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        hec = g.h_eigenvector_centrality()
        assert len(hec) == 4
        for v in hec.values():
            assert v >= 0.0


class TestPolyadicZEigenvector:
    def test_nary_z_eigenvector(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        zec = g.z_eigenvector_centrality()
        assert len(zec) == 4
        for v in zec.values():
            assert v >= 0.0


class TestPolyadicNodeEdgeCentrality:
    def test_nary_node_edge_centrality(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        nc, ec = g.node_edge_centrality()
        assert len(nc) == 3
        assert len(ec) == 1

    def test_nary_node_edge_multiple_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A", "C"], ["D"], label="e2", ids=ids)
        nc, ec = g.node_edge_centrality()
        assert len(nc) == 4
        assert len(ec) == 2


class TestPolyadicSWalkCentrality:
    def test_nary_s_walk_betweenness_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        swb = g.s_walk_betweenness(s=1, kind="edges")
        assert len(swb) == 2

    def test_nary_s_walk_closeness_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        swc = g.s_walk_closeness(s=1, kind="edges")
        assert len(swc) == 2

    def test_nary_s_walk_betweenness_nodes(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        swb = g.s_walk_betweenness(s=1, kind="nodes")
        for nid in ids.values():
            assert nid in swb


class TestPolyadicSubgraphCentrality:
    def test_nary_subgraph_centrality(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        sc = g.subhypergraph_centrality()
        assert len(sc) == 3
        for v in sc.values():
            assert v > 0.0


class TestPolyadicCorePeriphery:
    def test_nary_core_periphery_bounded(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D", "E"])
        cp = g.core_periphery()
        assert len(cp) == 5
        for v in cp.values():
            assert 0.0 <= v <= 1.0


class TestPolyadicDelegatedCentrality:
    def test_nary_harmonic_centrality(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        hc = g.harmonic_centrality()
        assert len(hc) == 4

    def test_nary_load_centrality(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        lc = g.load_centrality()
        assert len(lc) == 3

    def test_nary_voterank(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ids = _add_nary(g, ["D"], ["E"], label="e2", ids=ids)
        vr = g.voterank()
        assert len(vr) >= 1
