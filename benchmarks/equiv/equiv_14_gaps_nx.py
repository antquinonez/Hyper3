"""
Gaps: NetworkX Features Not in Hyper3
========================================
Documents capabilities present in NetworkX that Hyper3 lacks.
All tests are marked as GAP to serve as a guiding backlog.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("gaps_nx")

    t.gap("girvan_newman", "nx.community.girvan_newman(G) -- hierarchical by edge betweenness")
    t.gap("minimum_cycle_basis", "nx.minimum_cycle_basis(G)")
    t.gap("max_weight_matching", "nx.max_weight_matching(G) -- Blossom algorithm")
    t.gap("bipartite_maximum_matching", "nx.bipartite.maximum_matching(G)")

    _test_sbm(t)

    return t


def _test_sbm(t: EquivRunner) -> None:
    import networkx as nx
    import numpy as np

    from hyper3.generators import random_sbm

    sizes = [10, 10, 10]
    n = sum(sizes)
    p_in = 0.6
    p_out = 0.05
    p_matrix = [[p_in, p_out, p_out], [p_out, p_in, p_out], [p_out, p_out, p_in]]

    G_nx = nx.stochastic_block_model(sizes, p_matrix, seed=42, sparse=False)
    G_h3 = random_sbm(n, 3, sizes, p_in=p_in, p_out=p_out, seed=42)

    t.check_int("sbm/nx_node_count", G_nx.number_of_nodes(), n)
    t.check_int("sbm/h3_node_count", G_h3.node_count, n)
    t.check("sbm/nx_has_edges", G_nx.number_of_edges() > 0)
    t.check("sbm/h3_has_edges", G_h3.edge_count > 0)

    G_nx2 = nx.stochastic_block_model(sizes, p_matrix, seed=42, sparse=False)
    t.check_int("sbm/nx_reproducible", G_nx2.number_of_edges(), G_nx.number_of_edges())

    G_h32 = random_sbm(n, 3, sizes, p_in=p_in, p_out=p_out, seed=42)
    t.check_int("sbm/h3_reproducible", G_h32.edge_count, G_h3.edge_count)

    nx_counts = [nx.stochastic_block_model(sizes, p_matrix, seed=s, sparse=False).number_of_edges() for s in range(50)]
    h3_counts = [random_sbm(n, 3, sizes, p_in=p_in, p_out=p_out, seed=s).edge_count for s in range(50)]
    t.check(
        "sbm/statistical_equivalence",
        abs(np.mean(nx_counts) - np.mean(h3_counts)) < 3.0,
    )

    from math import comb
    intra = sum(comb(s, 2) for s in sizes)
    cross = comb(n, 2) - intra
    expected = intra * p_in + cross * p_out
    t.check("sbm/h3_matches_expected", abs(np.mean(h3_counts) - expected) < 2 * np.std(h3_counts))
    t.check("sbm/nx_matches_expected", abs(np.mean(nx_counts) - expected) < 2 * np.std(nx_counts))


if __name__ == "__main__":
    t = run()
    t.print_report()
