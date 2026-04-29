"""
Bench 8: Scalability
======================

Compares Hyper3's operation latency against raw networkx as the
graph grows from small to medium sizes.

Operations tested:
  1. Graph construction (add nodes + edges)
  2. Single-source shortest path
  3. Betweenness centrality
  4. BFS traversal (recall)
  5. Pattern matching (edge filtering)

Graph sizes: 50, 100, 250, 500, 1000 nodes.

Run:
    .venv/bin/python benchmarks/bench_08_scalability.py
"""

from __future__ import annotations

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import networkx as nx

from hyper3 import HypergraphMemory, Modality
from shared import Timer, print_header, print_comparison_table


def generate_random_graph(
    n_nodes: int,
    n_edges: int,
    edge_labels: list[str],
    seed: int = 42,
) -> tuple[list[tuple[str, dict]], list[tuple[str, str, str]]]:
    rng = random.Random(seed)
    nodes = [(f"n{i}", {"idx": i, "group": rng.randint(0, 4)}) for i in range(n_nodes)]
    edges_set: set[tuple[str, str, str]] = set()
    while len(edges_set) < n_edges:
        src_idx = rng.randint(0, n_nodes - 1)
        tgt_idx = rng.randint(0, n_nodes - 1)
        if src_idx == tgt_idx:
            continue
        label = rng.choice(edge_labels)
        edges_set.add((f"n{src_idx}", f"n{tgt_idx}", label))
    return nodes, list(edges_set)


SIZES = [50, 100, 250, 500, 1000]
EDGE_LABELS = ["connects_to", "depends_on", "related_to", "influences", "part_of"]


def main() -> None:
    print_header("Bench 8: Scalability")
    print(f"\n  Sizes: {SIZES}")
    print(f"  Edge labels: {EDGE_LABELS}")

    all_results: list[list[str]] = []

    for n_nodes in SIZES:
        n_edges = n_nodes * 3
        print_header(f"Graph size: {n_nodes} nodes, {n_edges} edges")

        nodes, edges = generate_random_graph(n_nodes, n_edges, EDGE_LABELS)

        # --- Construction ---
        with Timer() as t_nx:
            g = nx.DiGraph()
            for label, data in nodes:
                g.add_node(label, **data)
            for src, tgt, lbl in edges:
                g.add_edge(src, tgt, label=lbl)
        nx_build = t_nx.elapsed

        with Timer() as t_h3:
            mem = HypergraphMemory(evolve_interval=0)
            for label, data in nodes:
                mem.store(label, data=data, modalities={Modality.CONCEPTUAL})
            for src, tgt, lbl in edges:
                mem.relate(src, tgt, label=lbl)
        h3_build = t_h3.elapsed

        # --- Shortest Path ---
        test_pair = ("n0", f"n{n_nodes // 2}")
        with Timer() as t_nx:
            try:
                nx_path = nx.shortest_path(g, test_pair[0], test_pair[1])
            except nx.NetworkXNoPath:
                nx_path = None
        nx_sp = t_nx.elapsed

        with Timer() as t_h3:
            h3_path = mem.shortest_path(test_pair[0], test_pair[1])
        h3_sp = t_h3.elapsed

        # --- Betweenness Centrality ---
        with Timer() as t_nx:
            nx_bc = nx.betweenness_centrality(g)
        nx_bc_t = t_nx.elapsed

        with Timer() as t_h3:
            h3_bc = mem.betweenness_centrality()
        h3_bc_t = t_h3.elapsed

        # --- BFS Traversal ---
        with Timer() as t_nx:
            nx_bfs = list(nx.bfs_tree(g, "n0"))
        nx_bfs_t = t_nx.elapsed

        with Timer() as t_h3:
            h3_recall = mem.recall("n0", max_depth=3)
        h3_bfs_t = t_h3.elapsed

        # --- Pattern Matching ---
        with Timer() as t_nx:
            nx_matches = [(u, v) for u, v, d in g.edges(data=True) if d.get("label") == "depends_on"]
        nx_pm_t = t_nx.elapsed

        with Timer() as t_h3:
            h3_matches = mem.pattern_match(edge_label="depends_on")
        h3_pm_t = t_h3.elapsed

        row = [
            str(n_nodes),
            f"{h3_build*1000:.0f} / {nx_build*1000:.0f}",
            f"{h3_sp*1000:.1f} / {nx_sp*1000:.1f}",
            f"{h3_bc_t*1000:.0f} / {nx_bc_t*1000:.0f}",
            f"{h3_bfs_t*1000:.1f} / {nx_bfs_t*1000:.1f}",
            f"{h3_pm_t*1000:.1f} / {nx_pm_t*1000:.1f}",
            str(len(h3_matches)),
            str(len(nx_matches)),
        ]
        all_results.append(row)

        print(f"  Build:       H3={h3_build*1000:.0f}ms  nx={nx_build*1000:.0f}ms")
        print(f"  Shortest:    H3={h3_sp*1000:.1f}ms  nx={nx_sp*1000:.1f}ms")
        print(f"  Betweenness: H3={h3_bc_t*1000:.0f}ms  nx={nx_bc_t*1000:.0f}ms")
        print(f"  BFS/Recall:  H3={h3_bfs_t*1000:.1f}ms  nx={nx_bfs_t*1000:.1f}ms")
        print(f"  Pattern:     H3={h3_pm_t*1000:.1f}ms  nx={nx_pm_t*1000:.1f}ms")

    print_header("Summary (H3 / networkx in ms)")
    headers = ["Nodes", "Build", "Shortest", "Betweenness", "BFS/Recall", "Pattern", "H3 PM Hits", "nx PM Hits"]
    print_comparison_table(headers, all_results)

    # --- Overhead analysis ---
    print_header("Overhead Analysis")
    print("  Hyper3 adds overhead per operation for:")
    print("    - Event logging (append-only log)")
    print("    - Label index maintenance")
    print("    - Neighbor cache invalidation")
    print("    - Metadata wrapping (Metadata dataclass)")
    print("    - Frozenset edge endpoints (vs tuples)")
    print()
    print("  Expected overhead: 2-5x for simple operations on small graphs.")
    print("  Overhead should decrease as a fraction for complex operations (centrality)")
    print("  where the algorithm cost dominates the wrapper cost.")

    print()


if __name__ == "__main__":
    main()
