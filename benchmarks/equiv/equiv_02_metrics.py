"""
Equivalence: Basic Metrics
===========================
Compares degree sequences, density, edge size distributions,
and isolated node detection across HGX, XGI, and Hyper3.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_hgx_available,
    assert_xgi_available,
    build_hypergraph_h3,
    build_hypergraph_hgx,
    build_hypergraph_xgi,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("basic_metrics")

    _test_degree_pairwise(t)
    _test_degree_hypergraph_hgx(t)
    _test_degree_hypergraph_xgi(t)
    _test_density(t)
    _test_edge_size_distribution(t)

    _test_degree_correlation(t)

    t.gap("lazy_stat_objects", "XGI: nodes.degree.asdict()/.aslist()/.aspandas()")
    t.gap("multi_stat_dataframes", "XGI: nodes.multi(['degree']).aspandas()")

    return t


def _test_degree_pairwise(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_deg = mem.degree()
    nx_deg = dict(G.degree())

    for node in G.nodes():
        t.check_int(
            f"degree_pairwise/{node}",
            h3_deg.get(node, 0),
            nx_deg[node],
        )


def _test_degree_hypergraph_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    h3_deg = mem.degree()
    hgx_deg = H.degree_sequence()

    for node in range(8):
        label = f"n{node}"
        h3_d = h3_deg.get(label, 0)
        hgx_d = hgx_deg.get(node, 0)
        t.check_int(
            f"degree_hgx/{label}",
            h3_d,
            hgx_d,
        )


def _test_degree_hypergraph_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    h3_deg = mem.degree()
    xgi_deg = H.nodes.degree.asdict()

    for node in range(8):
        label = f"n{node}"
        h3_d = h3_deg.get(label, 0)
        xgi_d = xgi_deg.get(node, 0)
        t.check_int(
            f"degree_xgi/{label}",
            h3_d,
            xgi_d,
        )


def _test_density(t: EquivRunner) -> None:
    import networkx as nx

    G = build_pairwise_nx()
    mem = build_pairwise_h3()

    nx_density = nx.density(G)
    h3_density = mem.density()

    t.check_close("density/pairwise", h3_density, nx_density, tol=1e-10)


def _test_edge_size_distribution(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    H = build_hypergraph_hgx()
    hgx_dist = H.distribution_sizes()

    mem = build_hypergraph_h3()
    h3_sizes = {}
    for edge in mem.graph.edges:
        size = len(edge.node_ids)
        h3_sizes[size] = h3_sizes.get(size, 0) + 1

    for size in sorted(set(hgx_dist) | set(h3_sizes)):
        t.check_int(
            f"edge_size_dist/size_{size}",
            h3_sizes.get(size, 0),
            hgx_dist.get(size, 0),
        )


def _test_degree_correlation(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    dc = mem.graph.degree_correlation()

    t.check("degree_correlation/is_float", isinstance(dc, float))
    t.check("degree_correlation/in_range", -1.0 <= dc <= 1.0)


if __name__ == "__main__":

    t = run()
    t.print_report()
