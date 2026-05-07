"""
DAG & Tree Operations
=======================
Topological sort, transitive reduction, minimum spanning tree,
spanning forest, and other tree/DAG-specific algorithms.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("dag_trees")

    t.gap("topological_sort", "nx.topological_sort(G) -- linear ordering respecting edge direction")
    t.gap("is_dag", "nx.is_directed_acyclic_graph(G) -- DAG check")
    t.gap("transitive_closure", "nx.transitive_closure(G) -- compute reachability edges")
    t.gap("transitive_reduction", "nx.transitive_reduction(G) -- remove redundant edges")
    t.gap("dag_longest_path", "nx.dag_longest_path(G) -- longest path in DAG")
    t.gap("dag_longest_path_length", "nx.dag_longest_path_length(G) -- length of longest path in DAG")
    t.gap("minimum_spanning_tree", "nx.minimum_spanning_tree(G) -- Kruskal/Prim MST")
    t.gap("minimum_spanning_edges", "nx.minimum_spanning_edges(G) -- MST edge iterator")
    t.gap("spanning_tree_count", "nx.number_of_spanning_trees(G) -- Kirchhoff matrix-tree theorem")
    t.gap("is_tree", "nx.is_tree(G) -- tree check")
    t.gap("is_forest", "nx.is_forest(G) -- forest check")
    t.gap("tree_center", "Center of tree (one or two nodes with minimum eccentricity)")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
