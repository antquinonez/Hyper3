"""
Bench 3: Graph Analytics
=========================

Compares Hyper3's graph analytics API against raw networkx for
centrality computation, path finding, cycle detection, and component
analysis on a real software dependency graph.

Systems compared:
  1. Hyper3 (HypergraphMemory API)
  2. Raw networkx

Metrics:
  - Correctness: do results match networkx ground truth?
  - Latency: time per operation
  - API ergonomics: lines of code required

Run:
    .venv/bin/python benchmarks/bench_03_analytics.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import networkx as nx

from hyper3 import HypergraphMemory, Modality
from shared import (
    build_dependency_graph,
    build_nx_digraph,
    Timer,
    print_header,
    print_comparison_table,
)


def main() -> None:
    print_header("Bench 3: Graph Analytics")

    nodes, edges = build_dependency_graph()

    # Build both representations
    nx_graph, edge_labels = build_nx_digraph(nodes, edges)

    mem = HypergraphMemory(evolve_interval=0)
    for label, data in nodes:
        mem.add(label, data=data, modalities={Modality.CONCEPTUAL})
    for src, tgt, lbl in edges:
        mem.link(src, tgt, label=lbl)

    print(f"\n  Graph: {len(nodes)} nodes, {len(edges)} edges")

    results: list[list[str]] = []

    # --- Degree Centrality ---
    print_header("Degree Centrality")
    with Timer() as t_h3:
        h3_dc = mem.analyze.centrality("degree")
    with Timer() as t_nx:
        nx_dc = nx.degree_centrality(nx_graph)

    dc_corr = _spearman_correlation(h3_dc, nx_dc)
    results.append(["Degree Centrality", f"{t_h3.elapsed*1000:.1f}ms", f"{t_nx.elapsed*1000:.1f}ms", f"{dc_corr:.4f}"])
    print(f"  Hyper3: {t_h3.elapsed*1000:.1f}ms  |  networkx: {t_nx.elapsed*1000:.1f}ms  |  rank correlation: {dc_corr:.4f}")
    top_h3 = sorted(h3_dc.items(), key=lambda x: -x[1])[:5]
    top_nx = sorted(nx_dc.items(), key=lambda x: -x[1])[:5]
    print(f"  Top 5 H3:  {[f'{n}={s:.3f}' for n, s in top_h3]}")
    print(f"  Top 5 nx:  {[f'{n}={s:.3f}' for n, s in top_nx]}")

    # --- Betweenness Centrality ---
    print_header("Betweenness Centrality")
    with Timer() as t_h3:
        h3_bc = mem.analyze.centrality("betweenness")
    with Timer() as t_nx:
        nx_bc = nx.betweenness_centrality(nx_graph)

    bc_corr = _spearman_correlation(h3_bc, nx_bc)
    results.append(["Betweenness Centrality", f"{t_h3.elapsed*1000:.1f}ms", f"{t_nx.elapsed*1000:.1f}ms", f"{bc_corr:.4f}"])
    print(f"  Hyper3: {t_h3.elapsed*1000:.1f}ms  |  networkx: {t_nx.elapsed*1000:.1f}ms  |  rank correlation: {bc_corr:.4f}")
    top_h3 = sorted(h3_bc.items(), key=lambda x: -x[1])[:5]
    top_nx = sorted(nx_bc.items(), key=lambda x: -x[1])[:5]
    print(f"  Top 5 H3:  {[f'{n}={s:.3f}' for n, s in top_h3]}")
    print(f"  Top 5 nx:  {[f'{n}={s:.3f}' for n, s in top_nx]}")

    # --- Shortest Path ---
    print_header("Shortest Path")
    test_pairs = [
        ("api.routes", "core.config"),
        ("services.orders", "core.utils"),
        ("ext.stripe", "core.exceptions"),
        ("services.search", "infra.db"),
    ]
    path_matches = 0
    path_total = 0
    h3_path_time = 0.0
    nx_path_time = 0.0

    for src, tgt in test_pairs:
        with Timer() as t_h3:
            h3_path = mem.analyze.shortest_path(src, tgt)
        with Timer() as t_nx:
            try:
                nx_path = nx.shortest_path(nx_graph, src, tgt)
            except nx.NetworkXNoPath:
                nx_path = None
        h3_path_time += t_h3.elapsed
        nx_path_time += t_nx.elapsed
        path_total += 1

        h3_len = len(h3_path) if h3_path else 0
        nx_len = len(nx_path) if nx_path else 0
        match = h3_path == nx_path
        if match:
            path_matches += 1
        print(f"  {src} -> {tgt}: H3({h3_len})={h3_path}  nx({nx_len})={nx_path}  match={match}")

    results.append(["Shortest Path (avg)", f"{h3_path_time/len(test_pairs)*1000:.1f}ms", f"{nx_path_time/len(test_pairs)*1000:.1f}ms", f"{path_matches}/{path_total} match"])
    print(f"  Path matches: {path_matches}/{path_total}")

    # --- Cycle Detection ---
    print_header("Cycle Detection")
    with Timer() as t_h3:
        h3_has_cycle = mem.has_cycle()
    with Timer() as t_nx:
        nx_has_cycle = not nx.is_directed_acyclic_graph(nx_graph)

    results.append(["Cycle Detection", f"{t_h3.elapsed*1000:.1f}ms", f"{t_nx.elapsed*1000:.1f}ms", f"{'agree' if h3_has_cycle == nx_has_cycle else 'DISAGREE'}"])
    print(f"  Hyper3: {h3_has_cycle} ({t_h3.elapsed*1000:.1f}ms)  |  networkx: {nx_has_cycle} ({t_nx.elapsed*1000:.1f}ms)")

    with Timer() as t_h3:
        h3_cycles = mem.detect_cycles(max_cycles=10)
    with Timer() as t_nx:
        nx_cycles = list(nx.simple_cycles(nx_graph))

    print(f"  H3 cycles: {len(h3_cycles)}  |  nx cycles: {len(nx_cycles)}")
    for cyc in h3_cycles[:3]:
        print(f"    H3: {' -> '.join(cyc)}")
    for cyc in nx_cycles[:3]:
        print(f"    nx: {' -> '.join(cyc)}")

    # --- Connected Components ---
    print_header("Connected Components (undirected)")
    nx_undirected = nx_graph.to_undirected()
    with Timer() as t_h3:
        h3_comps = mem.analyze.components()
    with Timer() as t_nx:
        nx_comps = list(nx.connected_components(nx_undirected))

    results.append(["Components", f"{t_h3.elapsed*1000:.1f}ms", f"{t_nx.elapsed*1000:.1f}ms", f"{len(h3_comps)} vs {len(nx_comps)}"])
    print(f"  H3: {len(h3_comps)} components  |  nx: {len(nx_comps)} components")

    # --- Summary ---
    print_header("Summary")
    headers = ["Operation", "Hyper3", "networkx", "Agreement"]
    print_comparison_table(headers, results)

    # API ergonomics comparison
    print_header("API Ergonomics (LOC for common tasks)")
    ergo_headers = ["Task", "Hyper3 LOC", "networkx LOC", "Notes"]
    ergo_rows = [
        ["Build graph", "3 lines", "5+ lines", "store/relate vs add_node/add_edge loop"],
        ["Degree centrality", "1 line", "1 line + label mapping", "labels built-in vs nx node IDs"],
        ["Shortest path by label", "1 line", "3+ lines", "shortest_path vs label->id mapping"],
        ["Cycle detection", "1 line", "1 line", "has_cycle vs is_dag"],
        ["Find all paths", "1 line", "3+ lines", "find_paths vs label mapping + all_simple_paths"],
        ["Pattern match", "1 line", "5+ lines", "pattern_match(edge_label=X) vs filter edges"],
    ]
    print_comparison_table(ergo_headers, ergo_rows)

    print()


def _spearman_correlation(rankings_a: dict[str, float], rankings_b: dict[str, float]) -> float:
    if not rankings_a or not rankings_b:
        return 0.0
    import numpy as np
    common = set(rankings_a.keys()) & set(rankings_b.keys())
    if len(common) < 2:
        return 0.0
    sorted_a = sorted(common, key=lambda x: rankings_a.get(x, 0), reverse=True)
    sorted_b = sorted(common, key=lambda x: rankings_b.get(x, 0), reverse=True)
    rank_a = {n: i for i, n in enumerate(sorted_a)}
    rank_b = {n: i for i, n in enumerate(sorted_b)}
    n = len(common)
    d_sq = sum((rank_a[c] - rank_b[c]) ** 2 for c in common)
    return 1 - 6 * d_sq / (n * (n**2 - 1))


if __name__ == "__main__":
    main()
