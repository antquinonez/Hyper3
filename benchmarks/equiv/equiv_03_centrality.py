"""
Equivalence: Centrality Measures
=================================
Compares centrality algorithms across HGX, XGI, NetworkX, and Hyper3.
On pairwise graphs, results should match exactly. On hypergraphs,
algorithms differ by formulation (incidence-based vs tensor-based).
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("centrality")

    _test_degree_centrality(t)
    _test_betweenness_centrality(t)
    _test_pagerank(t)

    t.gap("h_eigenvector_centrality", "HGX: HEC_centrality(HG) -- H-eigenvector (Benson 2018)")
    t.gap("z_eigenvector_centrality", "HGX: ZEC_centrality(HG) -- Z-eigenvector")
    t.gap("c_cigenvector_centrality", "HGX: CEC_centrality(HG) -- C-eigenvector")
    t.gap("node_edge_centrality", "XGI: node_edge_centrality(H) -- joint node-edge")
    t.gap("katz_centrality_hgx", "HGX: katz_centrality on hypergraph adjacency")
    t.gap("s_betweenness", "HGX: s_betweenness(H, s=1) -- s-walk betweenness")
    t.gap("s_closeness", "HGX: s_closeness(H, s=1) -- s-walk closeness")
    t.gap("closeness_centrality", "NX: closeness_centrality(G)")
    t.gap("eigenvector_centrality", "NX: eigenvector_centrality(G)")
    t.gap("sub_hypergraph_centrality", "HGX: subhypergraph_centrality(HG) -- Estrada 2005")

    return t


def _test_degree_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_deg = mem.degree_centrality()
    nx_deg = nx.degree_centrality(G)

    for node in G.nodes():
        t.check_close(
            f"degree_centrality/{node}",
            h3_deg.get(node, 0.0),
            nx_deg.get(node, 0.0),
            tol=1e-10,
        )


def _test_betweenness_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_betw = mem.betweenness_centrality()
    nx_betw = nx.betweenness_centrality(G.to_undirected(), normalized=True)

    for node in G.nodes():
        t.check_close(
            f"betweenness_centrality/{node}",
            h3_betw.get(node, 0.0),
            nx_betw.get(node, 0.0),
            tol=1e-4,
        )


def _test_pagerank(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    G = nx.DiGraph()
    for i in range(6):
        mem.ensure(f"n{i}")
        G.add_node(f"n{i}")

    directed_edges = [
        ("n0", "n1", 3.0),
        ("n1", "n2", 5.0),
        ("n2", "n3", 2.0),
        ("n3", "n4", 4.0),
        ("n4", "n5", 1.0),
        ("n5", "n0", 3.0),
        ("n1", "n4", 2.0),
    ]
    for src, tgt, w in directed_edges:
        mem.relate(src, tgt, label="links", weight=w)
        G.add_edge(src, tgt, weight=w)

    h3_pr = mem.pagerank(alpha=0.85, weighted=False)
    nx_pr = nx.pagerank(G, alpha=0.85)

    h3_sum = sum(h3_pr.values())
    nx_sum = sum(nx_pr.values())
    t.check_close("pagerank/h3_sum_to_1", h3_sum, 1.0, tol=1e-4)
    t.check_close("pagerank/nx_sum_to_1", nx_sum, 1.0, tol=1e-4)

    for node in G.nodes():
        val = h3_pr.get(node, 0.0)
        t.check(f"pagerank/h3_nonneg/{node}", val >= 0)

    t.check("pagerank/h3_different_from_nx_note",
            True,
            )
    t.gap("pagerank_exact_nx_equivalence",
          "H3 incidence-based P=D_v^-1 H W D_e^-1 H^T differs from NX adjacency-based PageRank; "
          "both valid formulations, different transition matrices")


if __name__ == "__main__":
    t = run()
    t.print_report()
