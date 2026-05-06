"""
Flow & Matching Algorithms
============================
Max-flow, min-cut, s-t cut, maximum weight matching, bipartite matching,
and related combinatorial optimization algorithms.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("flows_matching")

    t.gap("max_flow", "nx.maximum_flow(G, s, t) -- Edmonds-Karp / Dinic")
    t.gap("min_cut", "nx.minimum_cut(G, s, t) -- Stoer-Wagner global min cut")
    t.gap("min_cut_st", "nx.minimum_st_cut(G, s, t) -- s-t minimum cut")
    t.gap("max_weight_matching", "nx.max_weight_matching(G) -- Blossom algorithm")
    t.gap("bipartite_maximum_matching", "nx.bipartite.maximum_matching(G) -- Hopcroft-Karp")
    t.gap("bipartite_maximum_weight_matching", "nx.bipartite.maximum_weight_matching(G) -- weighted bipartite matching")
    t.gap("minimum_edge_cover", "nx.min_edge_cover(G) -- smallest set of edges covering all nodes")
    t.gap("minimum_cycle_basis", "nx.minimum_cycle_basis(G) -- Horton algorithm")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
