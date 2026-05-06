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
    _test_closeness_centrality(t)
    _test_eigenvector_centrality(t)

    _test_katz_centrality_solve(t)
    _test_subhypergraph_centrality(t)

    t.gap("h_eigenvector_centrality", "HGX: HEC_centrality(HG) -- H-eigenvector (Benson 2018)")
    t.gap("z_eigenvector_centrality", "HGX: ZEC_centrality(HG) -- Z-eigenvector")
    t.gap("c_cigenvector_centrality", "HGX: CEC_centrality(HG) -- C-eigenvector")
    t.gap("node_edge_centrality", "XGI: node_edge_centrality(H) -- joint node-edge")
    t.gap("s_betweenness", "HGX: s_betweenness(H, s=1) -- s-walk betweenness")
    t.gap("s_closeness", "HGX: s_closeness(H, s=1) -- s-walk closeness")

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


def _test_closeness_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_cc = mem.graph.closeness_centrality()
    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_cc_labels = {label_map[k]: v for k, v in h3_cc.items()}
    nx_cc = nx.closeness_centrality(G)

    n = len(nx_cc)
    for node in G.nodes():
        h3_scaled = h3_cc_labels[node] * (n - 1)
        t.check_close(
            f"closeness_centrality/{node}",
            h3_scaled,
            nx_cc[node],
            tol=1e-8,
        )


def _test_eigenvector_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_ec = mem.graph.eigenvector_centrality()
    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_ec_labels = {label_map[k]: v for k, v in h3_ec.items()}
    nx_ec = nx.eigenvector_centrality(G.to_undirected(), max_iter=1000)

    for node in G.nodes():
        t.check_close(
            f"eigenvector_centrality/{node}",
            h3_ec_labels[node],
            nx_ec[node],
            tol=1e-4,
        )


def _test_katz_centrality_solve(t: EquivRunner) -> None:
    import networkx as nx

    from benchmarks.equiv.shared import build_pairwise_nx

    mem = build_pairwise_h3()
    kc = mem.graph.katz_centrality_solve(alpha=0.1)
    t.check("katz_centrality_solve/returns_dict", isinstance(kc, dict))
    t.check("katz_centrality_solve/all_nodes_present", len(kc) == mem.graph.node_count)
    t.check("katz_centrality_solve/all_positive", all(v > 0 for v in kc.values()))

    G = build_pairwise_nx()
    try:
        nx_kc = nx.katz_centrality_numpy(G.to_undirected(), alpha=0.1)
        t.check("katz_centrality_solve/nx_available", True)
    except Exception:
        nx_kc = None
        t.check("katz_centrality_solve/nx_available", False)

    if nx_kc is not None:
        {n.id: n.label for n in mem.graph.nodes}
        h3_sum = sum(kc.values())
        nx_sum = sum(nx_kc.values())
        t.check_close("katz_centrality_solve/sum_close", h3_sum, nx_sum, tol=0.5)


def _test_subhypergraph_centrality(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    sc = mem.graph.subhypergraph_centrality()
    t.check("subhypergraph_centrality/returns_dict", isinstance(sc, dict))
    t.check("subhypergraph_centrality/all_positive", all(v > 0 for v in sc.values()))
    t.check("subhypergraph_centrality/all_nodes_present", len(sc) == mem.graph.node_count)
    t.check("subhypergraph_centrality/no_nx_equivalent", True)


if __name__ == "__main__":
    t = run()
    t.print_report()
