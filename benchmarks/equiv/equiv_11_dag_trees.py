"""
Equivalence: DAG & Tree Operations
====================================
Compares DAG and tree algorithms across NetworkX and Hyper3.
On pairwise graphs, results should match exactly.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("dag_trees")

    _test_is_dag(t)
    _test_topological_sort(t)
    _test_transitive_closure(t)
    _test_transitive_reduction(t)
    _test_dag_longest_path_length(t)
    _test_is_tree(t)
    _test_is_forest(t)
    _test_minimum_spanning_tree(t)
    _test_minimum_spanning_edges(t)
    _test_spanning_tree_count(t)
    _test_tree_center(t)

    return t


def _build_dag_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(6):
        mem.ensure(f"n{i}")
    mem.relate("n0", "n1")
    mem.relate("n0", "n2")
    mem.relate("n1", "n3")
    mem.relate("n2", "n3")
    mem.relate("n3", "n4")
    mem.relate("n3", "n5")
    return mem


def _build_dag_nx():
    import networkx as nx

    G = nx.DiGraph()
    for i in range(6):
        G.add_node(f"n{i}")
    for u, v in [("n0", "n1"), ("n0", "n2"), ("n1", "n3"), ("n2", "n3"), ("n3", "n4"), ("n3", "n5")]:
        G.add_edge(u, v)
    return G


def _build_tree_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(7):
        mem.ensure(f"n{i}")
    tree_edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
    for u, v in tree_edges:
        mem.relate(f"n{u}", f"n{v}", bidirectional=True)
    return mem


def _build_tree_nx():
    import networkx as nx

    G = nx.Graph()
    for i in range(7):
        G.add_node(f"n{i}")
    tree_edges = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
    for u, v in tree_edges:
        G.add_edge(f"n{u}", f"n{v}")
    return G


def _test_is_dag(t: EquivRunner) -> None:
    import networkx as nx

    dag_mem = _build_dag_h3()
    dag_nx = _build_dag_nx()
    t.check("is_dag/true", dag_mem.is_dag() is True)
    t.check("is_dag/nx_matches", dag_mem.is_dag() == nx.is_directed_acyclic_graph(dag_nx))

    mem_cycle = build_pairwise_h3()
    G_cycle = build_pairwise_nx()
    t.check("is_dag/false_on_cycle", mem_cycle.is_dag() is False)
    t.check("is_dag/nx_cycle_matches", mem_cycle.is_dag() == nx.is_directed_acyclic_graph(G_cycle))


def _test_topological_sort(t: EquivRunner) -> None:
    import networkx as nx

    dag_mem = _build_dag_h3()
    dag_nx = _build_dag_nx()
    h3_order = dag_mem.topological_sort()
    nx_order = list(nx.topological_sort(dag_nx))
    t.check("topological_sort/returns_list", h3_order is not None)
    if h3_order is not None:
        t.check_int("topological_sort/length", len(h3_order), len(nx_order))
        for u, v in dag_nx.edges():
            t.check(
                f"topological_sort/order/{u}->{v}",
                h3_order.index(u) < h3_order.index(v),
            )

    mem_cycle = build_pairwise_h3()
    t.check("topological_sort/cycle_returns_none", mem_cycle.topological_sort() is None)


def _test_transitive_closure(t: EquivRunner) -> None:
    import networkx as nx

    dag_mem = _build_dag_h3()
    dag_nx = _build_dag_nx()
    h3_closure = dag_mem.transitive_closure()
    nx_closure = set(nx.transitive_closure(dag_nx).edges())
    t.check_set_equal(
        "transitive_closure/pairs",
        h3_closure,
        nx_closure,
    )


def _test_transitive_reduction(t: EquivRunner) -> None:
    import networkx as nx

    dag_mem = _build_dag_h3()
    dag_nx = _build_dag_nx()
    h3_red = dag_mem.transitive_reduction()
    nx_red = set(nx.transitive_reduction(dag_nx).edges())
    t.check_set_equal(
        "transitive_reduction/pairs",
        h3_red,
        nx_red,
    )


def _test_dag_longest_path_length(t: EquivRunner) -> None:
    import networkx as nx

    dag_mem = _build_dag_h3()
    dag_nx = _build_dag_nx()
    h3_len = dag_mem.dag_longest_path_length()
    nx_len = nx.dag_longest_path_length(dag_nx)
    t.check_int("dag_longest_path_length", h3_len, nx_len)


def _test_is_tree(t: EquivRunner) -> None:
    import networkx as nx

    tree_mem = _build_tree_h3()
    tree_nx = _build_tree_nx()
    t.check("is_tree/true", tree_mem.is_tree() is True)
    t.check("is_tree/nx_matches", tree_mem.is_tree() == nx.is_tree(tree_nx))

    cycle_mem = build_pairwise_h3()
    cycle_nx = build_pairwise_nx().to_undirected()
    t.check("is_tree/false_on_cycle", cycle_mem.is_tree() is False)
    t.check("is_tree/nx_cycle_matches", cycle_mem.is_tree() == nx.is_tree(cycle_nx))


def _test_is_forest(t: EquivRunner) -> None:
    import networkx as nx

    tree_mem = _build_tree_h3()
    tree_nx = _build_tree_nx()
    t.check("is_forest/tree_is_forest", tree_mem.is_forest() is True)
    t.check("is_forest/nx_tree_matches", tree_mem.is_forest() == nx.is_forest(tree_nx))

    cycle_mem = build_pairwise_h3()
    cycle_nx = build_pairwise_nx().to_undirected()
    t.check("is_forest/false_on_cycle", cycle_mem.is_forest() is False)
    t.check("is_forest/nx_cycle_matches", cycle_mem.is_forest() == nx.is_forest(cycle_nx))


def _test_minimum_spanning_tree(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()
    h3_mst = mem.minimum_spanning_tree()
    nx_mst = list(nx.minimum_spanning_edges(G, data=False))
    t.check_int("minimum_spanning_tree/edge_count", len(h3_mst), len(nx_mst))


def _test_minimum_spanning_edges(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()
    h3_edges = mem.minimum_spanning_edges()
    nx_mst = list(nx.minimum_spanning_edges(G, data=False))
    t.check_int("minimum_spanning_edges/count", len(h3_edges), len(nx_mst))


def _test_spanning_tree_count(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(4):
        mem.ensure(f"n{i}")
    for i in range(4):
        for j in range(i + 1, 4):
            mem.relate(f"n{i}", f"n{j}", bidirectional=True)

    import networkx as nx

    G = nx.complete_graph(4)
    L = nx.laplacian_matrix(G).toarray()
    import numpy as np

    expected = round(float(np.linalg.det(L[1:, 1:])))
    actual = mem.spanning_tree_count()
    t.check_int("spanning_tree_count/k4", actual, expected)


def _test_tree_center(t: EquivRunner) -> None:
    tree_mem = _build_tree_h3()
    center = tree_mem.tree_center()
    t.check("tree_center/has_center", len(center) > 0)
    t.check("tree_center/at_most_2", len(center) <= 2)
    for node in center:
        t.check(f"tree_center/valid_node/{node}", node.startswith("n"))


if __name__ == "__main__":
    t = run()
    t.print_report()
