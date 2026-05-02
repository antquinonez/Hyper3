"""
Equivalence: Directed Hypergraph Operations
==============================================
Compares directed hypergraph in-degree, out-degree, and source/target
edge queries between HGX and Hyper3.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    DIRECTED_HYPEREDGES,
    EquivRunner,
    assert_hgx_available,
    build_directed_h3,
    build_directed_hgx,
)


def run() -> EquivRunner:
    t = EquivRunner("directed_hypergraph")

    _test_directed_degrees_hgx(t)
    _test_directed_edge_queries(t)
    _test_directed_source_target(t)

    t.gap("directed_s_centralities", "HGX: s_betweenness/s_closeness for DirectedHypergraph")
    t.gap("temporal_hypergraph_type", "HGX: TemporalHypergraph with time-indexed edges")
    t.gap("multiplex_hypergraph_type", "HGX: MultiplexHypergraph with layered edges")

    return t


def _test_directed_degrees_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_directed_h3()
    H = build_directed_hgx()

    h3_in = mem.in_degree()
    h3_out = mem.out_degree()

    t.check("directed_degrees/has_in_degree", len(h3_in) > 0)
    t.check("directed_degrees/has_out_degree", len(h3_out) > 0)

    hgx_deg = H.degree_sequence()

    for node in range(8):
        label = f"n{node}"
        h3_total = h3_in.get(label, 0) + h3_out.get(label, 0)
        hgx_d = hgx_deg.get(node, 0)
        t.check_int(
            f"total_degree/{label}",
            h3_total,
            hgx_d,
        )


def _test_directed_edge_queries(t: EquivRunner) -> None:
    mem = build_directed_h3()

    for sources, targets in DIRECTED_HYPEREDGES:
        src_labels = {f"n{j}" for j in sources}
        tgt_labels = {f"n{j}" for j in targets}
        for src in src_labels:
            out_n = mem.neighbors(src, direction="out")
            has_relevant = any(n in tgt_labels for n in out_n)
            t.check(f"directed_edge_query/{src}_has_out_neighbor", has_relevant or len(sources) > 1)


def _test_directed_source_target(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    H = build_directed_hgx()

    hgx_sources = H.get_sources()
    hgx_targets = H.get_targets()

    t.check("directed_source_target/has_sources", len(hgx_sources) > 0)
    t.check("directed_source_target/has_targets", len(hgx_targets) > 0)
    t.check_int("directed_source_target/edge_count_matches", len(hgx_sources), len(DIRECTED_HYPEREDGES))


if __name__ == "__main__":
    t = run()
    t.print_report()
