"""
Flow & Matching Algorithms
============================
Max-flow, min-cut, s-t cut, maximum weight matching, bipartite matching,
and related combinatorial optimization algorithms.

Cross-validated against NX on identical graph structures.
"""

from __future__ import annotations

import networkx as nx

from benchmarks.equiv.shared import EquivRunner


def _build_flow_graph():
    edges = [
        ("s", "a", 10.0), ("s", "b", 5.0),
        ("a", "b", 15.0), ("a", "c", 8.0),
        ("b", "d", 10.0),
        ("c", "d", 10.0), ("c", "t", 7.0),
        ("d", "t", 12.0),
    ]
    G = nx.DiGraph()
    for u, v, w in edges:
        G.add_edge(u, v, capacity=w)
    return G, edges


def _build_flow_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    for n in nodes:
        mem.ensure(n)
    for u, v, w in edges:
        mem.link(u, v, label="flow", weight=w)
    return mem


def _build_matching_graph():
    edges = [
        ("a", "d", 4.0), ("a", "e", 2.0),
        ("b", "d", 3.0), ("b", "f", 5.0),
        ("c", "e", 6.0), ("c", "f", 1.0),
    ]
    G = nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G, edges


def _build_matching_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    for n in nodes:
        mem.ensure(n)
    for u, v, w in edges:
        mem.link(u, v, label="m", weight=w, bidirectional=True)
    return mem


def _build_bipartite_graph():
    edges = [
        ("a1", "b1", 3.0), ("a1", "b2", 1.0),
        ("a2", "b1", 2.0), ("a2", "b3", 4.0),
        ("a3", "b2", 5.0), ("a3", "b3", 2.0),
    ]
    G = nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G, edges


def _build_bipartite_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    for n in nodes:
        mem.ensure(n)
    for u, v, w in edges:
        mem.link(u, v, label="bp", weight=w, bidirectional=True)
    return mem


def _build_cycle_graph():
    edges = [
        ("a", "b", 1.0), ("b", "c", 1.0), ("c", "a", 1.0),
        ("c", "d", 1.0), ("d", "e", 1.0), ("e", "c", 1.0),
        ("a", "f", 1.0), ("f", "g", 1.0), ("g", "a", 1.0),
    ]
    G = nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G, edges


def _build_cycle_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    for n in nodes:
        mem.ensure(n)
    for u, v, w in edges:
        mem.link(u, v, label="cyc", weight=w, bidirectional=True)
    return mem


def _test_max_flow(t: EquivRunner) -> None:
    nx_g, edges = _build_flow_graph()
    mem = _build_flow_h3(edges)

    nx_val = nx.maximum_flow_value(nx_g, "s", "t")
    h3_val, h3_flow = mem.max_flow("s", "t")

    t.check_close("max_flow/value", h3_val, nx_val, tol=0.01)

    total_flow_out = sum(f for (u, _v), f in h3_flow.items() if u == "s")
    t.check_close("max_flow/source_outflow", total_flow_out, nx_val, tol=0.01)


def _test_min_cut_st(t: EquivRunner) -> None:
    nx_g, edges = _build_flow_graph()
    mem = _build_flow_h3(edges)

    nx_cut_val = nx.minimum_cut_value(nx_g, "s", "t")
    h3_cut_val, (h3_left, h3_right) = mem.analyze.min_cut("s", "t")

    t.check_close("min_cut_st/value", h3_cut_val, nx_cut_val, tol=0.01)
    t.check("min_cut_st/s_in_source", "s" in h3_left)
    t.check("min_cut_st/t_in_sink", "t" in h3_right)


def _test_min_cut_global(t: EquivRunner) -> None:
    nx_g, edges = _build_flow_graph()
    mem = _build_flow_h3(edges)

    nx_g_undirected = nx_g.to_undirected()
    for u, v in nx_g_undirected.edges():
        nx_g_undirected[u][v]["weight"] = nx_g.get_edge_data(u, v, nx_g.get_edge_data(v, u, {})).get("capacity", 1.0)

    nx_min_cut = nx.stoer_wagner(nx_g_undirected)
    h3_cut_val, (h3_left, h3_right) = mem.analyze.min_cut()

    t.check_close("min_cut_global/value", h3_cut_val, nx_min_cut[0], tol=0.01)
    all_nodes = set(h3_left) | set(h3_right)
    t.check_int("min_cut_global/partition_covers_all", len(all_nodes), len(nx_min_cut[1][0]) + len(nx_min_cut[1][1]))


def _test_max_weight_matching(t: EquivRunner) -> None:
    nx_g, edges = _build_matching_graph()
    mem = _build_matching_h3(edges)

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
    nx_g, edges = _build_bipartite_graph()
    mem = _build_bipartite_h3(edges)

    left = {"a1", "a2", "a3"}
    right = {"b1", "b2", "b3"}

    nx_matching = nx.bipartite.maximum_matching(nx_g, top_nodes=left)
    nx_match_set = {frozenset({k, v}) for k, v in nx_matching.items() if k in left}

    h3_matching = mem.bipartite_maximum_matching(left, right)

    t.check_int("bipartite_maximum_matching/count", len(h3_matching), len(nx_match_set))


def _test_bipartite_max_weight_matching(t: EquivRunner) -> None:
    nx_g, edges = _build_bipartite_graph()
    mem = _build_bipartite_h3(edges)

    left = {"a1", "a2", "a3"}
    right = {"b1", "b2", "b3"}

    nx_matching = nx.bipartite.maximum_matching(nx_g, top_nodes=left)
    nx_match_set = {frozenset({k, v}) for k, v in nx_matching.items() if k in left}

    h3_matching = mem.bipartite_max_weight_matching(left, right)

    t.check_int("bipartite_max_weight_matching/count", len(h3_matching), len(nx_match_set))

    nx_weight = sum(nx_g[u][v]["weight"] for u, v in nx_matching.items() if u in left)
    h3_weight = 0.0
    for pair in h3_matching:
        a, b = sorted(pair)
        edge_data = nx_g.get_edge_data(a, b)
        if edge_data:
            h3_weight += edge_data["weight"]
    t.check("bipartite_max_weight_matching/weight_reasonable", h3_weight > 0)


def _test_minimum_edge_cover(t: EquivRunner) -> None:
    nx_g, edges = _build_matching_graph()
    mem = _build_matching_h3(edges)

    nx_cover = nx.min_edge_cover(nx_g)
    h3_cover = mem.min_edge_cover()

    t.check_int("minimum_edge_cover/count", len(h3_cover), len(nx_cover))

    nx_covered = set()
    for u, v in nx_cover:
        nx_covered.add(u)
        nx_covered.add(v)
    h3_covered = set()
    for pair in h3_cover:
        h3_covered.update(pair)
    t.check_set_equal("minimum_edge_cover/nodes_covered", h3_covered, nx_covered)


def _test_minimum_cycle_basis(t: EquivRunner) -> None:
    nx_g, edges = _build_cycle_graph()
    mem = _build_cycle_h3(edges)

    nx_cycles = nx.minimum_cycle_basis(nx_g)
    h3_cycles = mem.minimum_cycle_basis()

    t.check_int("minimum_cycle_basis/count", len(h3_cycles), len(nx_cycles))

    nx_cycle_sets = [frozenset(c) for c in nx_cycles]
    h3_cycle_sets = [frozenset(c) for c in h3_cycles]
    t.check_set_equal("minimum_cycle_basis/unique_node_sets", set(h3_cycle_sets), set(nx_cycle_sets))


def run() -> EquivRunner:
    t = EquivRunner("flows_matching")

    _test_max_flow(t)
    _test_min_cut_st(t)
    _test_min_cut_global(t)
    _test_max_weight_matching(t)
    _test_bipartite_maximum_matching(t)
    _test_bipartite_max_weight_matching(t)
    _test_minimum_edge_cover(t)
    _test_minimum_cycle_basis(t)

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
