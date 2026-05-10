"""
Equivalence: Graph Transformations
=====================================
Compares dual, line graph, bipartite graph, clique projection,
simplicial complex, and directed line graph transformations
across XGI, NetworkX, and Hyper3.
"""

from __future__ import annotations

import networkx as nx

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_xgi_available,
    build_hypergraph_h3,
    build_hypergraph_xgi,
    build_pairwise_h3,
)


def _clique_graph_nx(mem) -> nx.Graph:
    G = nx.Graph()
    for e in mem.engine.graph.edges:
        members = list(e.node_ids)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                G.add_edge(members[i], members[j])
    return G


def run() -> EquivRunner:
    t = EquivRunner("graph_transformations")

    _test_dual(t)
    _test_line_graph(t)
    _test_bipartite(t)
    _test_to_networkx(t)
    _test_clique_projection(t)
    _test_simplicial_complex(t)
    _test_directed_line_graph(t)

    return t


def _test_dual(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    dual = mem.to_dual()
    original_edge_count = mem.engine.graph.edge_count
    dual_node_count = len(dual)
    t.check_int("dual/edge_count_equals_dual_nodes", dual_node_count, original_edge_count)

    total_dual_members = sum(len(v) for v in dual.values())
    t.check("dual/has_entries", total_dual_members > 0)

    if assert_xgi_available(t):
        import xgi

        H = build_hypergraph_xgi()
        try:
            xgi_dual = xgi.dual_dict(H)
            t.check_int("dual/xgi_node_count", len(xgi_dual), H.num_edges)
            t.check_int("dual/xgi_edge_count", sum(len(v) for v in xgi_dual.values()),
                        sum(len(v) for v in dual.values()))
        except (AttributeError, TypeError):
            t.skip("dual/xgi_dual_dict", "XGI dual_dict API incompatibility")


def _test_line_graph(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    lg = mem.to_line_graph()
    edge_count = mem.engine.graph.edge_count
    t.check("line_graph/has_edges", len(lg) > 0)

    if assert_xgi_available(t):
        import xgi

        H = build_hypergraph_xgi()
        xgi_lg = xgi.to_line_graph(H)
        t.check("line_graph/xgi_produces_graph", xgi_lg is not None)
        t.check_int("line_graph/xgi_node_count", xgi_lg.number_of_nodes(), edge_count)


def _test_bipartite(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    bipartite = mem.to_bipartite_graph()
    total_incidence = sum(len(e.node_ids) for e in mem.engine.graph.edges)
    t.check_int("bipartite/incidence_count", len(bipartite), total_incidence)

    node_labels_in_bip = {u for u, v in bipartite if u.startswith("n")}
    t.check_int("bipartite/all_nodes_present", len(node_labels_in_bip), mem.engine.graph.node_count)


def _test_to_networkx(t: EquivRunner) -> None:
    mem = build_pairwise_h3()

    G = mem.engine.graph.to_networkx()
    t.check_int("to_networkx/node_count", G.number_of_nodes(), mem.engine.graph.node_count)
    t.check_int("to_networkx/edge_count", G.number_of_edges(), mem.engine.graph.edge_count)


def _test_clique_projection(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    cp = mem.engine.graph.clique_projection()
    t.check("clique_projection/is_connected", cp.is_connected())

    G_nx = _clique_graph_nx(mem)
    t.check_int("clique_projection/nx_node_count", G_nx.number_of_nodes(), cp.node_count)
    t.check_int("clique_projection/nx_edge_count", G_nx.number_of_edges(), cp.edge_count)


def _test_simplicial_complex(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    sc = mem.engine.graph.simplicial_complex()
    t.check("simplicial_complex/non_empty", len(sc) > 0)

    node_count = mem.engine.graph.node_count
    node_ids = {n.id for n in mem.engine.graph.nodes}
    singletons = sum(1 for s in sc if len(s) == 1)
    t.check("simplicial_complex/has_singletons", singletons > 0)
    t.check("simplicial_complex/singletons_leq_nodes", singletons <= node_count)

    if assert_xgi_available(t):
        import xgi

        H = build_hypergraph_xgi()
        try:
            xgi_sc = xgi.SimplicialComplex()
            xgi_sc.add_nodes_from(H.nodes)
            for e in H.edges.members():
                xgi_sc.add_simplex(e)
            t.check("simplicial_complex/xgi_comparable", xgi_sc.num_nodes > 0)
        except Exception:
            t.skip("simplicial_complex/xgi", "XGI SimplicialComplex construction failed")


def _test_directed_line_graph(t: EquivRunner) -> None:
    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(4)]
    for n in nodes:
        g.add_node(n)
    for i in range(3):
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))

    dlg = g.to_directed_line_graph()
    t.check_int("dlg/node_count", dlg.number_of_nodes(), 3)
    t.check_int("dlg/edge_count", dlg.number_of_edges(), 2)

    G_nx = nx.DiGraph([(0, 1), (1, 2), (2, 3)])
    nx_lg = nx.line_graph(G_nx)
    t.check_int("dlg/nx_line_graph_nodes", nx_lg.number_of_nodes(), dlg.number_of_nodes())
    t.check_int("dlg/nx_line_graph_edges", nx_lg.number_of_edges(), dlg.number_of_edges())

    edges = list(g._edges.keys())
    t.check("dlg/chain_directed", dlg.has_edge(edges[0], edges[1]))
    t.check("dlg/chain_directed_2", dlg.has_edge(edges[1], edges[2]))
    t.check("dlg/no_reverse", not dlg.has_edge(edges[1], edges[0]))

    g2 = Hypergraph()
    nodes2 = [Hypernode(label=str(i)) for i in range(3)]
    for n in nodes2:
        g2.add_node(n)
    for i in range(3):
        g2.add_edge(Hyperedge(source_ids=frozenset({nodes2[i].id}), target_ids=frozenset({nodes2[(i + 1) % 3].id})))
    dlg2 = g2.to_directed_line_graph()
    t.check_int("dlg/cycle_edges", dlg2.number_of_edges(), 3)
    t.check("dlg/cycle_is_strongly_connected", nx.is_strongly_connected(dlg2))

    G_nx_cycle = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
    nx_cycle_lg = nx.line_graph(G_nx_cycle)
    t.check_int("dlg/cycle_nx_nodes", nx_cycle_lg.number_of_nodes(), dlg2.number_of_nodes())
    t.check_int("dlg/cycle_nx_edges", nx_cycle_lg.number_of_edges(), dlg2.number_of_edges())


if __name__ == "__main__":
    t = run()
    t.print_report()
