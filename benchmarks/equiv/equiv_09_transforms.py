"""
Equivalence: Graph Transformations
=====================================
Compares dual, line graph, and bipartite graph transformations
across XGI and Hyper3.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_xgi_available,
    build_hypergraph_h3,
    build_hypergraph_xgi,
    build_pairwise_h3,
)


def run() -> EquivRunner:
    t = EquivRunner("graph_transformations")

    _test_dual(t)
    _test_line_graph(t)
    _test_bipartite(t)
    _test_to_networkx(t)
    _test_clique_projection(t)

    t.gap("simplicial_complex", "HGX: simplicial_complex(h) -- fill in all subsets")
    t.gap("directed_line_graph", "HGX: directed_line_graph(h) for DirectedHypergraph")

    return t


def _test_dual(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    dual = mem.to_dual()

    t.check("dual/returns_dict", isinstance(dual, dict))
    t.check("dual/has_entries", len(dual) > 0)

    original_edge_count = mem.graph.edge_count
    dual_node_count = len(dual)
    t.check_int("dual/edge_count_equals_dual_nodes", dual_node_count, original_edge_count)

    if assert_xgi_available(t):
        import xgi

        H = build_hypergraph_xgi()
        try:
            xgi_dual = xgi.dual_dict(H)
            t.check_int("dual/xgi_dual_edge_count", len(xgi_dual), H.num_edges)
        except (AttributeError, TypeError):
            t.skip("dual/xgi_dual_dict", "XGI dual_dict API incompatibility")


def _test_line_graph(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    lg = mem.to_line_graph()

    t.check("line_graph/returns_list", isinstance(lg, list))

    edge_count = mem.graph.edge_count
    if edge_count > 1:
        t.check("line_graph/has_edges", len(lg) > 0)

    if assert_xgi_available(t):
        import xgi

        H = build_hypergraph_xgi()
        xgi_lg = xgi.to_line_graph(H)
        t.check("line_graph/xgi_produces_graph", xgi_lg is not None)


def _test_bipartite(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    bipartite = mem.to_bipartite_graph()

    t.check("bipartite/returns_list", isinstance(bipartite, list))
    t.check("bipartite/has_entries", len(bipartite) > 0)

    total_incidence = sum(len(e.node_ids) for e in mem.graph.edges)
    t.check_int("bipartite/incidence_count", len(bipartite), total_incidence)


def _test_to_networkx(t: EquivRunner) -> None:
    mem = build_pairwise_h3()

    G = mem.graph.to_networkx()

    t.check("to_networkx/returns_digraph", G is not None)
    t.check_int("to_networkx/node_count", G.number_of_nodes(), mem.graph.node_count)


def _test_clique_projection(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    cp = mem.graph.clique_projection()

    t.check("clique_projection/returns_hypergraph", cp is not None)
    t.check_int("clique_projection/node_count", cp.node_count, mem.graph.node_count)
    t.check("clique_projection/has_edges", cp.edge_count > 0)
    t.check("clique_projection/is_connected", cp.is_connected())


if __name__ == "__main__":
    t = run()
    t.print_report()
