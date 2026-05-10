"""
Equivalence: Shortest Paths
=============================
Compares shortest path algorithms across HGX, XGI, NetworkX, and Hyper3.
On pairwise graphs, path lengths should match exactly.
"""

from __future__ import annotations

import networkx as nx

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
    _test_s_walk_paths(t)
    _test_s_walk_distances(t)

    t.gap("ho_shortest_paths", "HGX: calc_ho_shortest_paths(hg) -- higher-order s-walk")

    return t


def _test_shortest_path_pairwise(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    pairs = [("n0", "n3"), ("n1", "n6"), ("n0", "n4"), ("n2", "n7")]
    for src, tgt in pairs:
        h3_path = mem.shortest_path(src, tgt, weighted=False)
        nx_path = nx.shortest_path(G.to_undirected(), src, tgt)
        if h3_path is not None and nx_path is not None:
            t.check_int(f"shortest_path_len/{src}->{tgt}", len(h3_path), len(nx_path))


def _test_shortest_path_length_pairwise(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    src = "n0"
    h3_lens = mem.single_source_distances(src, weighted=False)
    nx_lens = nx.single_source_shortest_path_length(G.to_undirected(), src)

    for tgt in nx_lens:
        t.check_int(f"shortest_path_length/{src}->{tgt}", int(h3_lens.get(tgt, -1)), nx_lens[tgt])


def _test_has_path(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_path = mem.shortest_path("n0", "n7", weighted=False)
    nx_path = nx.shortest_path(G.to_undirected(), "n0", "n7")

    t.check("has_path/n0_starts_correct", h3_path is not None and h3_path[0] == nx_path[0])
    t.check("has_path/n7_ends_correct", h3_path is not None and h3_path[-1] == nx_path[-1])
    t.check_int("has_path/length_matches_nx", len(h3_path) if h3_path else 0, len(nx_path))


def _test_find_paths(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    paths = mem.find_paths("n0", "n3", max_depth=5, max_paths=10)
    t.check("find_paths/has_results", len(paths) > 0)

    for i, p in enumerate(paths):
        t.check(f"find_paths/valid_path/{i}", p[0] == "n0" and p[-1] == "n3")

    nx_paths = list(nx.all_simple_paths(G.to_undirected(), "n0", "n3", cutoff=5))
    for h3_p in paths:
        nx_lengths = [len(nxp) for nxp in nx_paths]
        t.check(f"find_paths/length_exists_in_nx/{len(h3_p)}", len(h3_p) in nx_lengths)


def _test_hyperedge_paths(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    path = mem.shortest_path("n0", "n4", weighted=False)
    t.check("hyperedge_path/n0->n4", path is not None)

    if path is not None:
        t.check("hyperedge_path/starts_at_n0", path[0] == "n0")
        t.check("hyperedge_path/ends_at_n4", path[-1] == "n4")

        node_id_to_label = {n.id: n.label for n in mem.engine.graph.nodes}
        G_clique = nx.Graph()
        for e in mem.engine.graph.edges:
            members = list(e.node_ids)
            labels = [node_id_to_label[m] for m in members]
            for i in range(len(labels)):
                for j in range(i + 1, len(labels)):
                    G_clique.add_edge(labels[i], labels[j])
        nx_path_len = nx.shortest_path_length(G_clique, path[0], path[-1])
        t.check("hyperedge_path/length_valid", len(path) - 1 >= nx_path_len)


def _test_s_walk_paths(t: EquivRunner) -> None:
    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(5)]
    for n in nodes:
        g.add_node(n)
    edges = []
    for i in range(4):
        e = Hyperedge(source_ids=frozenset({nodes[i].id, nodes[i + 1].id}), target_ids=frozenset())
        g.add_edge(e)
        edges.append(e.id)
    e5 = Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset())
    g.add_edge(e5)
    edges.append(e5.id)

    path = g.s_walk_shortest_path(edges[0], edges[3], s=1)
    t.check("s_walk_path/exists", path is not None, f"path={path}")
    if path is not None:
        t.check("s_walk_path/starts_correct", path[0] == edges[0])
        t.check("s_walk_path/ends_correct", path[-1] == edges[3])
        length = g.s_walk_shortest_path_length(edges[0], edges[3], s=1)
        t.check_int("s_walk_path/length", int(length), len(path) - 1)

    self_dist = g.s_walk_shortest_path_length(edges[0], edges[0], s=1)
    t.check("s_walk_path/self_distance_zero", self_dist == 0.0, f"self_dist={self_dist}")

    no_path = g.s_walk_shortest_path(edges[0], "nonexistent", s=1)
    t.check("s_walk_path/nonexistent_returns_none", no_path is None)


def _test_s_walk_distances(t: EquivRunner) -> None:
    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(4)]
    for n in nodes:
        g.add_node(n)
    edges = []
    for i in range(3):
        e = Hyperedge(source_ids=frozenset({nodes[i].id, nodes[i + 1].id}), target_ids=frozenset())
        g.add_edge(e)
        edges.append(e.id)

    dm = g.s_walk_distance_matrix(s=1)
    t.check_int("s_walk_dist/matrix_size", len(dm), 3)
    t.check("s_walk_dist/self_zero", dm[edges[0]][edges[0]] == 0.0)
    t.check("s_walk_dist/adjacent_1", dm[edges[0]][edges[1]] == 1.0)
    t.check("s_walk_dist/distant_2", dm[edges[0]][edges[2]] == 2.0)
    t.check("s_walk_dist/symmetric", dm[edges[2]][edges[0]] == 2.0)

    G_nx = nx.path_graph(3)
    for i in range(3):
        for j in range(3):
            t.check_int(f"s_walk_dist/nx_match_{i}_{j}",
                        int(dm[edges[i]][edges[j]]),
                        nx.shortest_path_length(G_nx, i, j))


if __name__ == "__main__":
    t = run()
    t.print_report()
