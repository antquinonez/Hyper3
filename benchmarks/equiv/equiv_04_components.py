"""
Equivalence: Connected Components
===================================
Compares connected component detection across HGX, XGI, NetworkX, and Hyper3.
All libraries should identify the same components on the same graph.
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
    label_to_int,
)


def run() -> EquivRunner:
    t = EquivRunner("connected_components")

    _test_components_pairwise(t)
    _test_components_hypergraph_hgx(t)
    _test_components_hypergraph_xgi(t)
    _test_is_connected(t)
    _test_largest_component(t)
    _test_s_components(t)

    t.gap("s_components_by_size", "HGX: connected_components(size=3) -- order/size filtering")
    t.gap("biconnected_components", "NX: biconnected_components(G)")
    t.gap("strongly_connected", "NX: strongly_connected_components(G)")

    return t


def _test_components_pairwise(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_comp = mem.connected_components()
    nx_comp = list(nx.connected_components(G.to_undirected()))

    t.check_set_membership("components_pairwise", h3_comp, nx_comp)
    t.check_int("components_pairwise/count", len(h3_comp), len(nx_comp))


def _test_components_hypergraph_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    h3_comp = mem.connected_components()
    hgx_comp = H.connected_components()

    h3_as_ints = [{label_to_int(n) for n in comp} for comp in h3_comp]
    hgx_as_ints = [set(comp) for comp in hgx_comp]

    t.check_set_membership("components_hgx", h3_as_ints, hgx_as_ints)


def _test_components_hypergraph_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return

    import xgi

    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    h3_comp = mem.connected_components()
    xgi_comp = [set(comp) for comp in xgi.connected_components(H)]

    h3_as_ints = [{label_to_int(n) for n in comp} for comp in h3_comp]

    t.check_set_membership("components_xgi", h3_as_ints, xgi_comp)


def _test_is_connected(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    t.check("is_connected/pairwise", mem.is_connected() == nx.is_connected(G.to_undirected()))

    from hyper3 import HypergraphMemory

    mem2 = HypergraphMemory(evolve_interval=0)
    mem2.ensure("a")
    mem2.ensure("b")
    t.check("is_connected/disconnected", not mem2.is_connected())


def _test_largest_component(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_largest = mem.largest_connected_component()
    nx_largest = max(nx.connected_components(G.to_undirected()), key=len)

    t.check_set_equal("largest_component", h3_largest, nx_largest)


def _test_s_components(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(6):
        mem.ensure(f"n{i}")
    mem.relate_hyperedge(sources={"n0", "n1", "n2"}, targets={"n3"}, label="he1")
    mem.relate_hyperedge(sources={"n3", "n4"}, targets={"n5"}, label="he2")

    s1 = mem.connected_components()
    t.check_int("s_components/s1_count", len(s1), 1)
    t.check("s_components/s1_connected", mem.graph.is_connected())

    s2 = mem.graph.connected_components(s=2)
    t.check("s_components/s2_returns_list", isinstance(s2, list))

    sp = mem.s_persistence(max_s=3)
    t.check("s_persistence/returns_result", sp is not None)


if __name__ == "__main__":
    t = run()
    t.print_report()
