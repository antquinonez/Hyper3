"""
Gaps: NetworkX Features Not in Hyper3
========================================
Documents capabilities present in NetworkX that Hyper3 now implements.
Previously gap markers, now bridged with test code.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def _build_community_graph():
    import networkx as nx
    from hyper3 import HypergraphMemory

    nx_g = nx.karate_club_graph()
    mem = HypergraphMemory(evolve_interval=0)
    for n in nx_g.nodes():
        mem.ensure(f"n{n}")
    for u, v in nx_g.edges():
        mem.link(f"n{u}", f"n{v}", label="e", bidirectional=True)
    return nx_g, mem


def _build_cycle_graph():
    import networkx as nx
    from hyper3 import HypergraphMemory

    edges = [
        ("a", "b"), ("b", "c"), ("c", "a"),
        ("c", "d"), ("d", "e"), ("e", "c"),
        ("a", "f"), ("f", "g"), ("g", "a"),
    ]
    nx_g = nx.Graph(edges)
    mem = HypergraphMemory(evolve_interval=0)
    for s, t in edges:
        mem.ensure(s)
        mem.ensure(t)
    for s, t in edges:
        mem.link(s, t, label="cyc", bidirectional=True)
    return nx_g, mem


def _build_matching_graph():
    import networkx as nx
    from hyper3 import HypergraphMemory

    edges = [
        ("a", "d", 4.0), ("a", "e", 2.0),
        ("b", "d", 3.0), ("b", "f", 5.0),
        ("c", "e", 6.0), ("c", "f", 1.0),
    ]
    nx_g = nx.Graph()
    for u, v, w in edges:
        nx_g.add_edge(u, v, weight=w)
    mem = HypergraphMemory(evolve_interval=0)
    for u, v, _w in edges:
        mem.ensure(u)
        mem.ensure(v)
    for u, v, w in edges:
        mem.link(u, v, label="m", weight=w, bidirectional=True)
    return nx_g, mem


def _build_bipartite_graph():
    import networkx as nx
    from hyper3 import HypergraphMemory

    edges = [
        ("a1", "b1", 3.0), ("a1", "b2", 1.0),
        ("a2", "b1", 2.0), ("a2", "b3", 4.0),
        ("a3", "b2", 5.0), ("a3", "b3", 2.0),
    ]
    nx_g = nx.Graph()
    for u, v, w in edges:
        nx_g.add_edge(u, v, weight=w)
    mem = HypergraphMemory(evolve_interval=0)
    for u, v, _w in edges:
        mem.ensure(u)
        mem.ensure(v)
    for u, v, w in edges:
        mem.link(u, v, label="bp", weight=w, bidirectional=True)
    return nx_g, mem


def _test_girvan_newman(t: EquivRunner) -> None:
    import networkx as nx

    nx_g, mem = _build_community_graph()

    from networkx.algorithms.community import girvan_newman as nx_gn
    nx_comm = tuple(nx_gn(nx_g))
    nx_top = nx_comm[0]
    nx_num_top = len(nx_top)

    h3_result = mem.analyze.communities(method="girvan_newman")
    t.check("girvan_newman/produces_result", h3_result.community_count > 0)
    t.check_int("girvan_newman/community_count", h3_result.community_count, nx_num_top)

    h3_total_members = sum(c.size for c in h3_result.communities)
    t.check_int("girvan_newman/total_members", h3_total_members, nx_g.number_of_nodes())


def _test_minimum_cycle_basis(t: EquivRunner) -> None:
    import networkx as nx

    nx_g, mem = _build_cycle_graph()

    nx_cycles = nx.minimum_cycle_basis(nx_g)
    h3_cycles = mem.minimum_cycle_basis()

    t.check_int("minimum_cycle_basis/count", len(h3_cycles), len(nx_cycles))

    nx_cycle_sets = set(frozenset(c) for c in nx_cycles)
    h3_cycle_sets = set(frozenset(c) for c in h3_cycles)
    t.check_set_equal("minimum_cycle_basis/unique_node_sets", h3_cycle_sets, nx_cycle_sets)


def _test_max_weight_matching(t: EquivRunner) -> None:
    import networkx as nx

    nx_g, mem = _build_matching_graph()

    nx_matching = nx.max_weight_matching(nx_g)
    nx_weight = sum(nx_g[u][v]["weight"] for u, v in nx_matching)

    h3_matching = mem.max_weight_matching()
    h3_weight = 0.0
    for pair in h3_matching:
        u, v = sorted(pair)
        edge_data = nx_g.get_edge_data(u, v)
        if edge_data:
            h3_weight += edge_data["weight"]

    t.check_int("max_weight_matching/count", len(h3_matching), len(nx_matching))
    t.check_close("max_weight_matching/total_weight", h3_weight, nx_weight, tol=0.01)


def _test_bipartite_maximum_matching(t: EquivRunner) -> None:
    import networkx as nx

    nx_g, mem = _build_bipartite_graph()

    left = {"a1", "a2", "a3"}
    right = {"b1", "b2", "b3"}

    nx_matching = nx.bipartite.maximum_matching(nx_g, top_nodes=left)
    nx_match_set = {frozenset({k, v}) for k, v in nx_matching.items() if k in left}

    h3_matching = mem.bipartite_maximum_matching(left, right)

    t.check_int("bipartite_maximum_matching/count", len(h3_matching), len(nx_match_set))


def run() -> EquivRunner:
    t = EquivRunner("gaps_nx")

    _test_girvan_newman(t)
    _test_minimum_cycle_basis(t)
    _test_max_weight_matching(t)
    _test_bipartite_maximum_matching(t)

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
