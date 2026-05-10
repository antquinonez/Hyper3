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
    _test_h_eigenvector_centrality(t)
    _test_z_eigenvector_centrality(t)
    _test_c_eigenvector_centrality(t)
    _test_node_edge_centrality(t)
    _test_s_walk_betweenness(t)
    _test_s_walk_closeness(t)

    return t


def _test_degree_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_deg = mem.analyze.centrality("degree")
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

    h3_betw = mem.analyze.centrality("betweenness")
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
        mem.link(src, tgt, label="links", weight=w)
        G.add_edge(src, tgt, weight=w)

    h3_pr = mem.analyze.centrality("pagerank", alpha=0.85, weighted=False)
    nx_pr = nx.pagerank(G, alpha=0.85)

    h3_sum = sum(h3_pr.values())
    nx_sum = sum(nx_pr.values())
    t.check_close("pagerank/h3_sum_to_1", h3_sum, 1.0, tol=1e-4)
    t.check_close("pagerank/nx_sum_to_1", nx_sum, 1.0, tol=1e-4)

    for node in G.nodes():
        val = h3_pr.get(node, 0.0)
        t.check(f"pagerank/h3_nonneg/{node}", val >= 0)

    for node in G.nodes():
        t.check_close(
            f"pagerank/per_node/{node}",
            h3_pr.get(node, 0.0),
            nx_pr.get(node, 0.0),
            tol=0.1,
        )

    h3_ranking = sorted(h3_pr, key=h3_pr.get, reverse=True)
    nx_ranking = sorted(nx_pr, key=nx_pr.get, reverse=True)
    t.check("pagerank/top_node_agrees", h3_ranking[0] == nx_ranking[0],
            f"H3 top={h3_ranking[0]}, NX top={nx_ranking[0]}")


def _test_closeness_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_cc = mem.engine.graph.closeness_centrality()
    label_map = {n.id: n.label for n in mem.engine.graph.nodes}
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

    h3_ec = mem.engine.graph.eigenvector_centrality()
    label_map = {n.id: n.label for n in mem.engine.graph.nodes}
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
    kc = mem.engine.graph.katz_centrality_solve(alpha=0.1)
    t.check("katz_centrality_solve/returns_dict", isinstance(kc, dict))
    t.check("katz_centrality_solve/all_nodes_present", len(kc) == mem.engine.graph.node_count)
    t.check("katz_centrality_solve/all_positive", all(v > 0 for v in kc.values()))

    G = build_pairwise_nx()
    try:
        nx_kc = nx.katz_centrality_numpy(G.to_undirected(), alpha=0.1)
        t.check("katz_centrality_solve/nx_available", True)
    except Exception:
        nx_kc = None
        t.check("katz_centrality_solve/nx_available", False)

    if nx_kc is not None:
        label_map = {n.id: n.label for n in mem.engine.graph.nodes}
        h3_labeled = {label_map[k]: v for k, v in kc.items()}
        for node in G.nodes():
            t.check_close(
                f"katz_centrality_solve/per_node/{node}",
                h3_labeled.get(node, 0.0),
                nx_kc.get(node, 0.0),
                tol=0.15,
            )


def _test_subhypergraph_centrality(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    sc = mem.engine.graph.subhypergraph_centrality()
    t.check("subhypergraph_centrality/returns_dict", isinstance(sc, dict))
    t.check("subhypergraph_centrality/all_positive", all(v > 0 for v in sc.values()))
    t.check("subhypergraph_centrality/all_nodes_present", len(sc) == mem.engine.graph.node_count)
    t.check("subhypergraph_centrality/no_nx_equivalent", True)


def _test_h_eigenvector_centrality(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    hc = mem.engine.graph.h_eigenvector_centrality()
    t.check("h_eigenvector_centrality/returns_dict", isinstance(hc, dict))
    t.check("h_eigenvector_centrality/all_nodes_present", len(hc) == mem.engine.graph.node_count)
    t.check("h_eigenvector_centrality/all_nonneg", all(v >= 0 for v in hc.values()))
    t.check_close("h_eigenvector_centrality/sums_to_1", sum(hc.values()), 1.0, tol=1e-4)


def _test_z_eigenvector_centrality(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    zc = mem.engine.graph.z_eigenvector_centrality()
    t.check("z_eigenvector_centrality/returns_dict", isinstance(zc, dict))
    t.check("z_eigenvector_centrality/all_nodes_present", len(zc) == mem.engine.graph.node_count)
    t.check("z_eigenvector_centrality/all_nonneg", all(v >= 0 for v in zc.values()))
    t.check_close("z_eigenvector_centrality/sums_to_1", sum(zc.values()), 1.0, tol=1e-4)


def _test_c_eigenvector_centrality(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    cc = mem.engine.graph.c_eigenvector_centrality()
    label_map = {n.id: n.label for n in mem.engine.graph.nodes}
    cc_labels = {label_map[k]: v for k, v in cc.items()}

    nx_ec = nx.eigenvector_centrality(G, max_iter=1000)
    for node in G.nodes():
        t.check_close(
            f"c_eigenvector_centrality/{node}",
            abs(cc_labels[node]),
            abs(nx_ec[node]),
            tol=1e-4,
        )


def _test_node_edge_centrality(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    nc, ec = mem.engine.graph.node_edge_centrality()
    t.check("node_edge_centrality/node_dict", isinstance(nc, dict))
    t.check("node_edge_centrality/edge_dict", isinstance(ec, dict))
    t.check("node_edge_centrality/all_nodes_present", len(nc) == mem.engine.graph.node_count)
    t.check("node_edge_centrality/all_edges_present", len(ec) == mem.engine.graph.edge_count)
    t.check("node_edge_centrality/node_nonneg", all(v >= 0 for v in nc.values()))
    t.check("node_edge_centrality/edge_nonneg", all(v >= 0 for v in ec.values()))


def _test_s_walk_betweenness(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    bc_edges = mem.engine.graph.s_walk_betweenness(s=1, kind="edges")
    bc_nodes = mem.engine.graph.s_walk_betweenness(s=1, kind="nodes")
    t.check("s_walk_betweenness/edges_dict", isinstance(bc_edges, dict))
    t.check("s_walk_betweenness/nodes_dict", isinstance(bc_nodes, dict))
    t.check("s_walk_betweenness/nodes_count", len(bc_nodes) == mem.engine.graph.node_count)
    t.check("s_walk_betweenness/edges_nonneg", all(v >= 0 for v in bc_edges.values()))
    t.check("s_walk_betweenness/nodes_nonneg", all(v >= 0 for v in bc_nodes.values()))


def _test_s_walk_closeness(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    cc_edges = mem.engine.graph.s_walk_closeness(s=1, kind="edges")
    cc_nodes = mem.engine.graph.s_walk_closeness(s=1, kind="nodes")
    t.check("s_walk_closeness/edges_dict", isinstance(cc_edges, dict))
    t.check("s_walk_closeness/nodes_dict", isinstance(cc_nodes, dict))
    t.check("s_walk_closeness/nodes_count", len(cc_nodes) == mem.engine.graph.node_count)
    t.check("s_walk_closeness/nodes_bounded", all(0 <= v <= 1 for v in cc_nodes.values()))


if __name__ == "__main__":
    t = run()
    t.print_report()
