"""
Equivalence: Shortest Paths
=============================
Compares shortest path algorithms across HGX, XGI, NetworkX, and Hyper3.
On pairwise graphs, path lengths should match exactly.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    build_hypergraph_h3,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("shortest_paths")

    _test_shortest_path_pairwise(t)
    _test_shortest_path_length_pairwise(t)
    _test_has_path(t)
    _test_find_paths(t)
    _test_hyperedge_paths(t)

    t.gap("ho_shortest_paths", "HGX: calc_ho_shortest_paths(hg) -- higher-order s-walk")
    t.gap("s_walk_distances", "XGI: shortest_path_length(H, s=2) -- s-walk distance")

    return t


def _test_shortest_path_pairwise(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    pairs = [("n0", "n3"), ("n1", "n6"), ("n0", "n4"), ("n2", "n7")]
    for src, tgt in pairs:
        h3_path = mem.shortest_path(src, tgt, weighted=False)
        nx_path = nx.shortest_path(G.to_undirected(), src, tgt)
        if h3_path is not None and nx_path is not None:
            t.check_int(
                f"shortest_path_len/{src}->{tgt}",
                len(h3_path),
                len(nx_path),
            )
        else:
            t.check(f"shortest_path_exists/{src}->{tgt}", h3_path is not None)


def _test_shortest_path_length_pairwise(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    src = "n0"
    h3_lens = mem.single_source_distances(src, weighted=False)
    nx_lens = nx.single_source_shortest_path_length(G.to_undirected(), src)

    for tgt in nx_lens:
        t.check_int(
            f"shortest_path_length/{src}->{tgt}",
            int(h3_lens.get(tgt, -1)),
            nx_lens[tgt],
        )


def _test_has_path(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    path = mem.shortest_path("n0", "n7", weighted=False)
    t.check("has_path/n0->n7", path is not None)
    t.check("has_path/n0_starts_correct", path is not None and path[0] == "n0")
    t.check("has_path/n7_ends_correct", path is not None and path[-1] == "n7")

    nx_has = nx.has_path(G.to_undirected(), "n0", "n7")
    t.check("has_path/nx_matches", path is not None and nx_has)


def _test_find_paths(t: EquivRunner) -> None:
    mem = build_pairwise_h3()

    paths = mem.find_paths("n0", "n3", max_depth=5, max_paths=10)
    t.check("find_paths/has_results", len(paths) > 0)
    for i, p in enumerate(paths):
        t.check(f"find_paths/valid_path/{i}", p[0] == "n0" and p[-1] == "n3")


def _test_hyperedge_paths(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    path = mem.shortest_path("n0", "n4", weighted=False)
    t.check("hyperedge_path/n0->n4", path is not None)

    if path is not None:
        t.check("hyperedge_path/starts_at_n0", path[0] == "n0")
        t.check("hyperedge_path/ends_at_n4", path[-1] == "n4")


if __name__ == "__main__":
    t = run()
    t.print_report()
