"""
Equivalence: Construction & CRUD
=================================
Tests that Hyper3, HGX, XGI, and NetworkX can represent the same graph
structures and produce consistent node/edge counts, membership queries,
and basic CRUD operations.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    HYPEREDGES,
    EquivRunner,
    assert_hgx_available,
    assert_xgi_available,
    build_directed_h3,
    build_directed_hgx,
    build_hypergraph_h3,
    build_hypergraph_hgx,
    build_hypergraph_xgi,
    build_pairwise_h3,
    build_pairwise_nx,
)


def run() -> EquivRunner:
    t = EquivRunner("construction_and_crud")

    _test_pairwise_h3_nx(t)
    _test_hypergraph_h3_hgx(t)
    _test_hypergraph_h3_xgi(t)
    _test_directed_h3_hgx(t)
    _test_h3_crud(t)

    t.gap("hif_import", "HGX/XGI: read_hif/write_hif standard format")
    t.gap("metadata_filtering", "HGX: filter_hypergraph with node/edge criteria")
    t.gap("subhypergraph_by_order", "HGX: subhypergraph_by_orders(size=3)")

    return t


def _test_pairwise_h3_nx(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    t.check_int("pairwise/node_count", mem.graph.node_count, G.number_of_nodes())
    t.check_int(
        "pairwise/edge_count",
        mem.graph.edge_count,
        G.number_of_edges(),
    )

    for node in G.nodes():
        t.check(
            f"pairwise/has_node/{node}",
            mem.has_node(node),
        )

    for src, tgt in G.edges():
        has_edge = any(
            e.source_ids == {mem.graph.get_node_by_label(src).id}
            and e.target_ids == {mem.graph.get_node_by_label(tgt).id}
            for e in mem.graph.edges
        )
        t.check(f"pairwise/has_edge/{src}->{tgt}", has_edge)


def _test_hypergraph_h3_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    t.check_int("hypergraph_hgx/node_count", mem.graph.node_count, H.num_nodes())
    t.check_int("hypergraph_hgx/edge_count", mem.graph.edge_count, H.num_edges())

    for hyperedge in HYPEREDGES:
        hgx_has = H.check_edge(hyperedge)
        t.check(f"hypergraph_hgx/edge_exists/{hyperedge}", hgx_has)

    hgx_sizes = sorted(H.distribution_sizes().keys())
    h3_sizes = sorted(mem.graph.unique_edge_sizes())
    t.check(
        "hypergraph_hgx/edge_sizes_match",
        hgx_sizes == h3_sizes,
        f"hgx={hgx_sizes}, h3={h3_sizes}",
    )


def _test_hypergraph_h3_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return


    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    t.check_int("hypergraph_xgi/node_count", mem.graph.node_count, H.num_nodes)
    t.check_int("hypergraph_xgi/edge_count", mem.graph.edge_count, H.num_edges)

    for e_id in H.edges:
        members = H.edges.members(e_id)
        t.check(
            f"hypergraph_xgi/edge_members/{e_id}",
            len(members) in (2, 3),
        )


def _test_directed_h3_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_directed_h3()
    H = build_directed_hgx()

    t.check_int("directed_hgx/node_count", mem.graph.node_count, H.num_nodes())
    t.check_int("directed_hgx/edge_count", mem.graph.edge_count, H.num_edges())

    from benchmarks.equiv.shared import DIRECTED_HYPEREDGES

    for sources, targets in DIRECTED_HYPEREDGES:
        hgx_has = H.check_edge((set(sources), set(targets)))
        t.check(f"directed_hgx/edge_exists/{sources}->{targets}", hgx_has)


def _test_h3_crud(t: EquivRunner) -> None:
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    mem.store("alpha", data={"type": "test"})
    mem.store("beta", data={"type": "test"})
    t.check("crud/store_creates_node", mem.has_node("alpha"))
    t.check("crud/store_creates_second", mem.has_node("beta"))

    e = mem.relate("alpha", "beta", label="links", weight=2.0)
    t.check("crud/relate_creates_edge", e is not None)
    t.check_int("crud/edge_count_after_relate", mem.graph.edge_count, 1)

    t.check("crud/has_node_after_remove", mem.has_node("alpha"))
    mem.graph.remove_node(mem.graph.get_node_by_label("alpha").id)
    t.check("crud/node_gone_after_remove", not mem.has_node("alpha"))


if __name__ == "__main__":
    t = run()
    t.print_report()
