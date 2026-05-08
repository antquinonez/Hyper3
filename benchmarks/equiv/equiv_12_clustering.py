"""
Equivalence: Clustering Coefficient
======================================
Compares clustering coefficient computations between NetworkX and Hyper3
on pairwise graphs where both libraries should agree.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("clustering_coefficient")

    _test_local_clustering(t)
    _test_average_clustering(t)
    _test_transitivity(t)

    _test_square_clustering(t)
    _test_triangles(t)

    return t


def _test_local_clustering(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    nx_cluster = nx.clustering(G.to_undirected())

    for node in G.nodes():
        h3_cc = mem.clustering_coefficient(node)
        nx_cc = nx_cluster.get(node, 0.0)
        t.check_close(
            f"local_clustering/{node}",
            h3_cc,
            nx_cc,
            tol=1e-4,
        )


def _test_average_clustering(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_avg = mem.average_clustering_coefficient()
    nx_avg = nx.average_clustering(G.to_undirected())

    t.check_close("average_clustering", h3_avg, nx_avg, tol=1e-4)


def _test_transitivity(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_trans = mem.engine.graph.transitivity()
    nx_trans = nx.transitivity(G.to_undirected())

    t.check_close("transitivity", h3_trans, nx_trans, tol=1e-10)


def _test_square_clustering(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    nx_sq = nx.square_clustering(G.to_undirected())

    label_map = {n.id: n.label for n in mem.engine.graph.nodes}
    for node in G.nodes():
        node_id = None
        for nid, label in label_map.items():
            if label == node:
                node_id = nid
                break
        if node_id:
            h3_sc = mem.engine.graph.square_clustering(node_id)
            t.check_close(
                f"square_clustering/{node}",
                h3_sc,
                nx_sq.get(node, 0.0),
                tol=1e-4,
            )


def _test_triangles(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    nx_tri = nx.triangles(G.to_undirected())

    label_map = {n.id: n.label for n in mem.engine.graph.nodes}
    for node in G.nodes():
        node_id = None
        for nid, label in label_map.items():
            if label == node:
                node_id = nid
                break
        if node_id:
            h3_tri = mem.engine.graph.triangles(node_id)
            t.check_int(
                f"triangles/{node}",
                h3_tri,
                nx_tri.get(node, 0),
            )


if __name__ == "__main__":
    t = run()
    t.print_report()
