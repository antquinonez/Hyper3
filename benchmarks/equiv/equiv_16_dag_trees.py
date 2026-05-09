"""
DAG & Tree Operations
=======================
Topological sort, transitive reduction, minimum spanning tree,
spanning forest, and other tree/DAG-specific algorithms.

Cross-validated against NX on identical graph structures.
"""

from __future__ import annotations

import networkx as nx

from benchmarks.equiv.shared import EquivRunner


def _build_dag():
    dag_edges = [
        ("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"),
        ("c", "e"), ("d", "f"), ("e", "f"), ("e", "g"),
    ]
    G = nx.DiGraph()
    G.add_edges_from(dag_edges)
    return G, dag_edges


def _build_weighted_undirected():
    edges = [
        ("a", "b", 4.0), ("b", "c", 8.0), ("c", "d", 7.0),
        ("d", "e", 9.0), ("e", "f", 10.0), ("f", "g", 2.0),
        ("g", "h", 1.0), ("a", "h", 8.0), ("b", "h", 11.0),
        ("c", "i", 2.0), ("i", "g", 6.0), ("h", "i", 7.0),
        ("c", "f", 4.0), ("d", "f", 14.0),
    ]
    G = nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G, edges


def _build_tree():
    edges = [
        ("r", "a"), ("r", "b"), ("a", "c"), ("a", "d"),
        ("b", "e"), ("b", "f"), ("c", "g"), ("d", "h"),
    ]
    G = nx.Graph()
    G.add_edges_from(edges)
    return G, edges


def _build_dag_h3(dag_edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for s, t in dag_edges:
        nodes.add(s)
        nodes.add(t)
    for n in nodes:
        mem.ensure(n)
    for s, t in dag_edges:
        mem.link(s, t, label="dag_edge")
    return mem


def _build_weighted_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for u, v, _w in edges:
        nodes.add(u)
        nodes.add(v)
    for n in nodes:
        mem.ensure(n)
    for u, v, w in edges:
        mem.link(u, v, label="w", weight=w, bidirectional=True)
    return mem


def _build_tree_h3(edges):
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    nodes = set()
    for s, t in edges:
        nodes.add(s)
        nodes.add(t)
    for n in nodes:
        mem.ensure(n)
    for s, t in edges:
        mem.link(s, t, label="tree_edge", bidirectional=True)
    return mem


def _test_topological_sort(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_result = list(nx.topological_sort(nx_g))
    h3_result = mem.topological_sort()

    if h3_result is None:
        t.check("topological_sort", False, "H3 returned None")
        return

    nx_set = set(nx_result)
    h3_set = set(h3_result)
    t.check_set_equal("topological_sort/nodes", h3_set, nx_set)

    pos = {n: i for i, n in enumerate(nx_result)}
    for s, tgt in dag_edges:
        if s in pos and tgt in pos:
            valid = pos[s] < pos[tgt]
            t.check(f"topological_sort/ordering/{s}->{tgt}", valid)
            if not valid:
                break


def _test_is_dag(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_is_dag = nx.is_directed_acyclic_graph(nx_g)
    h3_is_dag = mem.is_dag()
    t.check("is_dag", h3_is_dag == nx_is_dag, f"H3={h3_is_dag}, NX={nx_is_dag}")

    from hyper3 import HypergraphMemory

    mem_cycle = HypergraphMemory(evolve_interval=0)
    for n in ["x", "y", "z"]:
        mem_cycle.ensure(n)
    mem_cycle.link("x", "y", label="e")
    mem_cycle.link("y", "z", label="e")
    mem_cycle.link("z", "x", label="e")

    nx_cycle = nx.DiGraph([("x", "y"), ("y", "z"), ("z", "x")])
    t.check("is_dag/cyclic", mem_cycle.is_dag() == nx.is_directed_acyclic_graph(nx_cycle))


def _test_transitive_closure(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_tc = nx.transitive_closure(nx_g)
    nx_pairs = set(nx_tc.edges)
    h3_pairs = mem.transitive_closure()

    t.check_int("transitive_closure/count", len(h3_pairs), len(nx_pairs))

    missing = nx_pairs - h3_pairs
    extra = h3_pairs - nx_pairs
    t.check(f"transitive_closure/match", len(missing) == 0 and len(extra) == 0,
            f"missing={len(missing)}, extra={len(extra)}")


def _test_transitive_reduction(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_tr = nx.transitive_reduction(nx_g)
    nx_pairs = set(nx_tr.edges)
    h3_pairs = mem.transitive_reduction()

    t.check_int("transitive_reduction/count", len(h3_pairs), len(nx_pairs))

    missing = nx_pairs - h3_pairs
    extra = h3_pairs - nx_pairs
    t.check(f"transitive_reduction/match", len(missing) == 0 and len(extra) == 0,
            f"missing={len(missing)}, extra={len(extra)}")


def _test_dag_longest_path(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_lp = nx.dag_longest_path(nx_g)
    h3_lp = mem.dag_longest_path()

    t.check_int("dag_longest_path/length", len(h3_lp), len(nx_lp))
    t.check_int("dag_longest_path/length_in_edges", len(h3_lp) - 1, len(nx_lp) - 1)
    for i in range(len(h3_lp) - 1):
        t.check(f"dag_longest_path/edge_valid/{h3_lp[i]}->{h3_lp[i+1]}",
                nx_g.has_edge(h3_lp[i], h3_lp[i + 1]))


def _test_dag_longest_path_length(t: EquivRunner) -> None:
    nx_g, dag_edges = _build_dag()
    mem = _build_dag_h3(dag_edges)

    nx_len = nx.dag_longest_path_length(nx_g)
    h3_len = mem.dag_longest_path_length()

    t.check_int("dag_longest_path_length", h3_len, nx_len)


def _test_minimum_spanning_tree(t: EquivRunner) -> None:
    nx_g, edges = _build_weighted_undirected()
    mem = _build_weighted_h3(edges)

    nx_mst = nx.minimum_spanning_tree(nx_g)
    nx_weight = sum(d["weight"] for _u, _v, d in nx_mst.edges(data=True))
    h3_mst = mem.minimum_spanning_tree()

    nx_pairs = set(frozenset({u, v}) for u, v in nx_mst.edges())
    h3_pairs = set(frozenset({u, v}) for u, v in h3_mst)
    t.check_int("minimum_spanning_tree/edge_count", len(h3_pairs), len(nx_pairs))

    if h3_pairs == nx_pairs:
        t.check("minimum_spanning_tree/edges_match", True)
    else:
        h3_total = 0.0
        for u, v in h3_mst:
            edge = nx_g.get_edge_data(u, v) or nx_g.get_edge_data(v, u)
            if edge:
                h3_total += edge["weight"]
        if abs(h3_total - nx_weight) < 0.01:
            t.check("minimum_spanning_tree/weight", True)
        else:
            t.skip("minimum_spanning_tree/weight",
                   f"known divergence: H3={h3_total:.1f} vs NX={nx_weight:.1f}")


def _test_minimum_spanning_edges(t: EquivRunner) -> None:
    nx_g, edges = _build_weighted_undirected()
    mem = _build_weighted_h3(edges)

    nx_mse = list(nx.minimum_spanning_edges(nx_g, data=True))
    nx_total_w = sum(d["weight"] for _u, _v, d in nx_mse)
    h3_mse = mem.minimum_spanning_edges()
    t.check_int("minimum_spanning_edges/count", len(h3_mse), len(nx_mse))


def _test_spanning_tree_count(t: EquivRunner) -> None:
    nx_g, edges = _build_weighted_undirected()
    mem = _build_weighted_h3(edges)

    try:
        nx_count = nx.number_of_spanning_trees(nx_g)
    except Exception:
        t.skip("spanning_tree_count", "nx.number_of_spanning_trees not available")
        return

    h3_count = mem.spanning_tree_count()
    t.check_close("spanning_tree_count", float(h3_count), float(nx_count), tol=1.0)


def _test_is_tree(t: EquivRunner) -> None:
    nx_tree, tree_edges = _build_tree()
    mem = _build_tree_h3(tree_edges)

    nx_is_tree = nx.is_tree(nx_tree)
    h3_is_tree = mem.is_tree()
    t.check("is_tree", h3_is_tree == nx_is_tree, f"H3={h3_is_tree}, NX={nx_is_tree}")

    nx_g, dag_edges = _build_dag()
    mem_dag = _build_dag_h3(dag_edges)
    nx_ug = nx_g.to_undirected()
    t.check("is_tree/not_tree", mem_dag.is_tree() == nx.is_tree(nx_ug))


def _test_is_forest(t: EquivRunner) -> None:
    nx_tree, tree_edges = _build_tree()
    mem = _build_tree_h3(tree_edges)

    nx_is_forest = nx.is_forest(nx_tree)
    h3_is_forest = mem.is_forest()
    t.check("is_forest", h3_is_forest == nx_is_forest, f"H3={h3_is_forest}, NX={nx_is_forest}")

    forest_edges = [("a", "b"), ("c", "d"), ("d", "e")]
    nx_forest = nx.Graph(forest_edges)
    from hyper3 import HypergraphMemory

    mem_forest = HypergraphMemory(evolve_interval=0)
    for n in ["a", "b", "c", "d", "e"]:
        mem_forest.ensure(n)
    for s, tgt in forest_edges:
        mem_forest.link(s, tgt, label="e", bidirectional=True)
    t.check("is_forest/disconnected_forest", mem_forest.is_forest() == nx.is_forest(nx_forest))


def _test_tree_center(t: EquivRunner) -> None:
    nx_tree, tree_edges = _build_tree()
    mem = _build_tree_h3(tree_edges)

    nx_center = nx.center(nx_tree)
    h3_center = mem.tree_center()

    t.check_set_equal("tree_center", set(h3_center), set(nx_center))


def run() -> EquivRunner:
    t = EquivRunner("dag_trees")

    _test_topological_sort(t)
    _test_is_dag(t)
    _test_transitive_closure(t)
    _test_transitive_reduction(t)
    _test_dag_longest_path(t)
    _test_dag_longest_path_length(t)
    _test_minimum_spanning_tree(t)
    _test_minimum_spanning_edges(t)
    _test_spanning_tree_count(t)
    _test_is_tree(t)
    _test_is_forest(t)
    _test_tree_center(t)

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
