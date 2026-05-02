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

    t.gap("square_clustering", "NX: square_clustering(G)")
    t.gap("transitivity", "NX: transitivity(G) -- global clustering coefficient")
    t.gap("triangles", "NX: triangles(G) -- triangle count per node")

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


if __name__ == "__main__":
    t = run()
    t.print_report()
