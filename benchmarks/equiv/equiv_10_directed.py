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
    mem = build_directed_h3()

    h3_in = mem.in_degree()
    h3_out = mem.out_degree()

    t.check_int("directed_degrees/in_count", len(h3_in), mem.engine.graph.node_count)
    t.check_int("directed_degrees/out_count", len(h3_out), mem.engine.graph.node_count)

    if assert_hgx_available(t):
        H = build_directed_hgx()
        hgx_deg = H.degree_sequence()

        for node in range(8):
            label = f"n{node}"
            h3_total = h3_in.get(label, 0) + h3_out.get(label, 0)
            hgx_d = hgx_deg.get(node, 0)
            t.check_int(f"total_degree/{label}", h3_total, hgx_d)


def _test_directed_edge_queries(t: EquivRunner) -> None:
    mem = build_directed_h3()

    for sources, targets in DIRECTED_HYPEREDGES:
        src_labels = {f"n{j}" for j in sources}
        tgt_labels = {f"n{j}" for j in targets}
        for src in src_labels:
            out_n = mem.neighbors(src, direction="out")
            has_relevant = any(n in tgt_labels for n in out_n)
            t.check(f"directed_edge_query/{src}_has_out_neighbor", has_relevant or len(sources) > 1)
        for tgt in tgt_labels:
            in_n = mem.neighbors(tgt, direction="in")
            has_relevant = any(n in src_labels for n in in_n)
            t.check(f"directed_edge_query/{tgt}_has_in_neighbor", has_relevant or len(targets) > 1)

    if assert_hgx_available(t):
        H = build_directed_hgx()
        h3_in = mem.in_degree()
        h3_out = mem.out_degree()
        hgx_deg = H.degree_sequence()
        for node in range(8):
            label = f"n{node}"
            h3_total = h3_in.get(label, 0) + h3_out.get(label, 0)
            t.check_int(f"hgx_total_degree/{label}", h3_total, hgx_deg.get(node, 0))


def _test_directed_source_target(t: EquivRunner) -> None:
    mem = build_directed_h3()

    h3_edge_count = mem.engine.graph.edge_count
    t.check_int("directed_source_target/h3_edge_count", h3_edge_count, len(DIRECTED_HYPEREDGES))

    if assert_hgx_available(t):
        H = build_directed_hgx()

        hgx_sources = H.get_sources()
        hgx_targets = H.get_targets()
        t.check_int("directed_source_target/edge_count_matches", len(hgx_sources), len(DIRECTED_HYPEREDGES))
        t.check_int("directed_source_target/hgx_h3_edge_match", len(hgx_sources), h3_edge_count)

        for idx, (sources, targets) in enumerate(DIRECTED_HYPEREDGES):
            hgx_s = hgx_sources[idx]
            hgx_t = hgx_targets[idx]
            t.check_int(f"source_target/edge_{idx}_source_size", len(hgx_s), len(sources))
            t.check_int(f"source_target/edge_{idx}_target_size", len(hgx_t), len(targets))


if __name__ == "__main__":
    t = run()
    t.print_report()
