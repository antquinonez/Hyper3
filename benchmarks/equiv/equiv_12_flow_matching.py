"""
Equivalence: Flow & Matching Algorithms
=========================================
Compares flow, cut, matching, and cycle algorithms across NetworkX and Hyper3.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
)


def run() -> EquivRunner:
    t = EquivRunner("flow_matching")

    _test_max_flow(t)
    _test_min_cut_st(t)
    _test_min_cut_global(t)
    _test_max_weight_matching(t)
    _test_bipartite_maximum_matching(t)
    _test_bipartite_max_weight_matching(t)
    _test_min_edge_cover(t)
    _test_minimum_cycle_basis(t)

    return t


def _build_flow_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(6):
        mem.ensure(f"n{i}")
    mem.link("n0", "n1", weight=10.0)
    mem.link("n0", "n2", weight=5.0)
    mem.link("n1", "n2", weight=15.0)
    mem.link("n1", "n3", weight=10.0)
    mem.link("n2", "n4", weight=10.0)
    mem.link("n3", "n5", weight=10.0)
    mem.link("n4", "n5", weight=10.0)
    return mem


def _build_flow_nx():
    import networkx as nx

    G = nx.DiGraph()
    for i in range(6):
        G.add_node(f"n{i}")
    edges = [
        ("n0", "n1", 10.0),
        ("n0", "n2", 5.0),
        ("n1", "n2", 15.0),
        ("n1", "n3", 10.0),
        ("n2", "n4", 10.0),
        ("n3", "n5", 10.0),
        ("n4", "n5", 10.0),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, capacity=w)
    return G


def _build_undirected_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(4):
        mem.ensure(f"n{i}")
    mem.link("n0", "n1", weight=3.0, bidirectional=True)
    mem.link("n1", "n2", weight=1.0, bidirectional=True)
    mem.link("n2", "n3", weight=3.0, bidirectional=True)
    mem.link("n0", "n2", weight=2.0, bidirectional=True)
    mem.link("n1", "n3", weight=2.0, bidirectional=True)
    return mem


def _build_undirected_nx():
    import networkx as nx

    G = nx.Graph()
    for i in range(4):
        G.add_node(f"n{i}")
    edges = [
        ("n0", "n1", 3.0),
        ("n1", "n2", 1.0),
        ("n2", "n3", 3.0),
        ("n0", "n2", 2.0),
        ("n1", "n3", 2.0),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G


def _test_max_flow(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_flow_h3()
    G = _build_flow_nx()

    h3_val, _ = mem.max_flow("n0", "n5")
    nx_val = nx.maximum_flow_value(G, "n0", "n5")
    t.check_close("max_flow/value", h3_val, nx_val, tol=1e-6)


def _test_min_cut_st(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_flow_h3()
    G = _build_flow_nx()

    h3_val, _ = mem.min_cut_st("n0", "n5")
    nx_val = nx.minimum_cut_value(G, "n0", "n5")
    t.check_close("min_cut_st/value", h3_val, nx_val, tol=1e-6)


def _test_min_cut_global(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_undirected_h3()
    G = _build_undirected_nx()

    h3_val, _ = mem.min_cut_global()
    nx_val, _ = nx.stoer_wagner(G)
    t.check_close("min_cut_global/value", h3_val, nx_val * 2.0, tol=1e-6)


def _test_max_weight_matching(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_undirected_h3()
    G = _build_undirected_nx()

    h3_matching = mem.max_weight_matching()
    nx_matching = nx.max_weight_matching(G)
    h3_weight = sum(G[u][v]["weight"] for u, v in nx_matching if u in dict(G.nodes()) and v in dict(G.nodes()))
    h3_weight_actual = 0.0
    for pair in h3_matching:
        pair_list = list(pair)
        if len(pair_list) == 2 and G.has_edge(pair_list[0], pair_list[1]):
            h3_weight_actual += G[pair_list[0]][pair_list[1]]["weight"]
    t.check("max_weight_matching/covers_all", len(h3_matching) >= 2)
    total_w = sum(
        G[pair_list[0]][pair_list[1]]["weight"]
        for pair in h3_matching
        if len(pair_list := list(pair)) == 2 and G.has_edge(pair_list[0], pair_list[1])
    )
    t.check("max_weight_matching/optimal_or_near", total_w >= h3_weight * 0.5)


def _test_bipartite_maximum_matching(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(6):
        mem.ensure(f"n{i}")
    mem.link("n0", "n3", weight=1.0)
    mem.link("n0", "n4", weight=1.0)
    mem.link("n1", "n3", weight=1.0)
    mem.link("n1", "n5", weight=1.0)
    mem.link("n2", "n4", weight=1.0)

    G = nx.DiGraph()
    for i in range(6):
        G.add_node(f"n{i}", bipartite=0 if i < 3 else 1)
    for u, v in [("n0", "n3"), ("n0", "n4"), ("n1", "n3"), ("n1", "n5"), ("n2", "n4")]:
        G.add_edge(u, v)

    left = {f"n{i}" for i in range(3)}
    right = {f"n{i}" for i in range(3, 6)}

    h3_matching = mem.bipartite_maximum_matching(left, right)
    nx_matching = nx.bipartite.maximum_matching(G.to_undirected())
    nx_match_count = len(nx_matching) // 2
    t.check_int("bipartite_maximum_matching/size", len(h3_matching), nx_match_count)


def _test_bipartite_max_weight_matching(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(4):
        mem.ensure(f"n{i}")
    mem.link("n0", "n2", weight=5.0)
    mem.link("n0", "n3", weight=1.0)
    mem.link("n1", "n3", weight=3.0)

    G = nx.Graph()
    for i in range(4):
        G.add_node(f"n{i}", bipartite=0 if i < 2 else 1)
    G.add_edge("n0", "n2", weight=5.0)
    G.add_edge("n0", "n3", weight=1.0)
    G.add_edge("n1", "n3", weight=3.0)

    left = {"n0", "n1"}
    right = {"n2", "n3"}

    h3_matching = mem.bipartite_max_weight_matching(left, right)
    nx_matching = nx.bipartite.maximum_matching(G)
    nx_match_count = len(nx_matching) // 2
    t.check_int("bipartite_max_weight_matching/size", len(h3_matching), nx_match_count)


def _test_min_edge_cover(t: EquivRunner) -> None:
    import networkx as nx

    mem = _build_undirected_h3()
    G = _build_undirected_nx()

    h3_cover = mem.min_edge_cover()
    nx_cover = nx.min_edge_cover(G)
    t.check("min_edge_cover/covers_all_nodes", len(h3_cover) >= 2)
    t.check("min_edge_cover/valid_cover", len(h3_cover) <= len(G.edges))


def _test_minimum_cycle_basis(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(4):
        mem.ensure(f"n{i}")
    mem.link("n0", "n1", bidirectional=True)
    mem.link("n1", "n2", bidirectional=True)
    mem.link("n2", "n0", bidirectional=True)
    mem.link("n2", "n3", bidirectional=True)
    mem.link("n3", "n0", bidirectional=True)

    G = nx.Graph()
    for i in range(4):
        G.add_node(f"n{i}")
    G.add_edge("n0", "n1")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n0")
    G.add_edge("n2", "n3")
    G.add_edge("n3", "n0")

    h3_basis = mem.minimum_cycle_basis()
    nx_basis = nx.minimum_cycle_basis(G)
    t.check_int("minimum_cycle_basis/count", len(h3_basis), len(nx_basis))
    for cycle in h3_basis:
        t.check(
            f"minimum_cycle_basis/valid_cycle/{sorted(cycle)}",
            len(cycle) >= 3,
        )


if __name__ == "__main__":
    t = run()
    t.print_report()
